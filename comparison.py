from __future__ import annotations

from typing import Dict, Iterable

import pandas as pd

from evaluation import evaluate_schedule
from models import Exam, ServerConfig, Student, Timeslot


LOWER_IS_BETTER = {
    "objective_value",
    "hard_constraint_violations",
    "capacity_violations",
    "student_conflicts",
    "total_soft_penalty",
    "consecutive_exam_penalty",
    "load_variance",
    "load_variance_penalty",
    "balance_penalty",
    "department_penalty",
    "max_load",
}


def _clean(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def build_actual_assignment(sinav_df: pd.DataFrame, timeslots: Dict[str, Timeslot]) -> Dict[str, str]:
    if "exam_id" not in sinav_df.columns:
        return {}

    by_id = {tid: tid for tid in timeslots}
    by_date_time = {(_clean(slot.date), _clean(slot.start_time)): tid for tid, slot in timeslots.items()}
    assignment: Dict[str, str] = {}

    for row in sinav_df.itertuples(index=False):
        exam_id = _clean(getattr(row, "exam_id", ""))
        if not exam_id:
            continue

        direct_tid = _clean(getattr(row, "timeslot_id", ""))
        if direct_tid in by_id:
            assignment[exam_id] = by_id[direct_tid]
            continue

        date_value = _clean(getattr(row, "date", ""))
        start_value = _clean(getattr(row, "start_time", ""))
        tid = by_date_time.get((date_value, start_value))
        if tid:
            assignment[exam_id] = tid

    return assignment


def build_baseline_assignment(exams: Dict[str, Exam], timeslots: Dict[str, Timeslot]) -> Dict[str, str]:
    ordered_exams = sorted(exams.values(), key=lambda exam: (-exam.student_count, exam.exam_id))
    ordered_slots = sorted(timeslots.values(), key=lambda slot: slot.order_index)
    if not ordered_slots:
        return {}

    loads = {slot.timeslot_id: 0 for slot in ordered_slots}
    assignment: Dict[str, str] = {}
    cursor = 0

    for exam in ordered_exams:
        assigned = None
        for offset in range(len(ordered_slots)):
            slot = ordered_slots[(cursor + offset) % len(ordered_slots)]
            limit = min(slot.capacity, slot.max_concurrent_students)
            if loads[slot.timeslot_id] + exam.student_count <= limit:
                assigned = slot
                cursor = (cursor + offset + 1) % len(ordered_slots)
                break

        if assigned is None:
            assigned = min(ordered_slots, key=lambda slot: loads[slot.timeslot_id])

        assignment[exam.exam_id] = assigned.timeslot_id
        loads[assigned.timeslot_id] += exam.student_count

    return assignment


def compare_metrics(actual_metrics: Dict, optimized_metrics: Dict, metric_names: Iterable[str] | None = None) -> pd.DataFrame:
    names = list(
        metric_names
        or [
            "objective_value",
            "hard_constraint_violations",
            "capacity_violations",
            "student_conflicts",
            "total_soft_penalty",
            "consecutive_exam_penalty",
            "load_variance",
            "balance_penalty",
            "department_penalty",
            "max_load",
        ]
    )
    rows = []
    for name in names:
        real_value = float(actual_metrics.get(name, 0) or 0)
        optimized_value = float(optimized_metrics.get(name, 0) or 0)
        if name in LOWER_IS_BETTER:
            improvement = real_value - optimized_value
            improvement_pct = (improvement / real_value * 100.0) if real_value else 0.0
        else:
            improvement = optimized_value - real_value
            improvement_pct = (improvement / real_value * 100.0) if real_value else 0.0
        rows.append(
            {
                "metric": name,
                "reference": real_value,
                "optimized": optimized_value,
                "improvement": improvement,
                "improvement_pct": improvement_pct,
            }
        )
    return pd.DataFrame(rows)


def compare_timeslots(actual_metrics: Dict, optimized_metrics: Dict, timeslots: Dict[str, Timeslot]) -> pd.DataFrame:
    rows = []
    for tid, slot in sorted(timeslots.items(), key=lambda item: item[1].order_index):
        reference_students = actual_metrics.get("concurrent_students_per_timeslot", {}).get(tid, 0)
        opt_students = optimized_metrics.get("concurrent_students_per_timeslot", {}).get(tid, 0)
        reference_exams = actual_metrics.get("exam_count_per_timeslot", {}).get(tid, 0)
        opt_exams = optimized_metrics.get("exam_count_per_timeslot", {}).get(tid, 0)
        rows.append(
            {
                "timeslot_id": tid,
                "date": slot.date,
                "start_time": slot.start_time,
                "reference_students": reference_students,
                "optimized_students": opt_students,
                "student_delta": opt_students - reference_students,
                "reference_exams": reference_exams,
                "optimized_exams": opt_exams,
                "exam_delta": opt_exams - reference_exams,
                "reference_cpu": actual_metrics.get("cpu_usage_per_timeslot", {}).get(tid, 0),
                "optimized_cpu": optimized_metrics.get("cpu_usage_per_timeslot", {}).get(tid, 0),
                "reference_ram": actual_metrics.get("ram_usage_per_timeslot", {}).get(tid, 0),
                "optimized_ram": optimized_metrics.get("ram_usage_per_timeslot", {}).get(tid, 0),
                "reference_bandwidth": actual_metrics.get("bandwidth_usage_per_timeslot", {}).get(tid, 0),
                "optimized_bandwidth": optimized_metrics.get("bandwidth_usage_per_timeslot", {}).get(tid, 0),
            }
        )
    return pd.DataFrame(rows)


def evaluate_actual_schedule(sinav_df: pd.DataFrame, exams: Dict[str, Exam], students: Dict[str, Student], timeslots: Dict[str, Timeslot], config: ServerConfig):
    assignment = build_actual_assignment(sinav_df, timeslots)
    if not assignment:
        return {}, {}
    return assignment, evaluate_schedule(assignment, exams, students, timeslots, config)


def evaluate_reference_schedule(sinav_df: pd.DataFrame, exams: Dict[str, Exam], students: Dict[str, Student], timeslots: Dict[str, Timeslot], config: ServerConfig):
    actual_assignment = build_actual_assignment(sinav_df, timeslots)
    if actual_assignment:
        return "real", actual_assignment, evaluate_schedule(actual_assignment, exams, students, timeslots, config)

    baseline_assignment = build_baseline_assignment(exams, timeslots)
    if not baseline_assignment:
        return "none", {}, {}
    return "baseline", baseline_assignment, evaluate_schedule(baseline_assignment, exams, students, timeslots, config)
