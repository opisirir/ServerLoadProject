from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import mean, variance
from typing import Dict, Tuple

from config import PENALTY_WEIGHTS
from models import Exam, ServerConfig, Student, Timeslot


def calculate_timeslot_loads(assignment: Dict[str, str], exams: Dict[str, Exam], timeslots: Dict[str, Timeslot], config: ServerConfig):
    loads = {
        tid: {
            "exam_count": 0,
            "student_count": 0,
            "cpu": 0.0,
            "ram": 0.0,
            "bandwidth": 0.0,
            "departments": Counter(),
            "exams": [],
        }
        for tid in timeslots
    }
    for exam_id, timeslot_id in assignment.items():
        if exam_id not in exams or timeslot_id not in timeslots:
            continue
        exam = exams[exam_id]
        load = loads[timeslot_id]
        load["exam_count"] += 1
        load["student_count"] += exam.student_count
        load["cpu"] += exam.student_count * config.cpu_per_student
        load["ram"] += exam.student_count * config.ram_per_student
        load["bandwidth"] += exam.student_count * config.bandwidth_per_student
        load["departments"][exam.department_id] += exam.student_count
        load["exams"].append(exam_id)
    return loads


def _student_conflicts(assignment: Dict[str, str], students: Dict[str, Student]) -> int:
    conflicts = 0
    for student in students.values():
        seen = {}
        for exam_id in student.exam_ids:
            tid = assignment.get(exam_id)
            if not tid:
                continue
            if tid in seen:
                conflicts += 1
            seen[tid] = exam_id
    return conflicts


def _consecutive_penalty(assignment: Dict[str, str], students: Dict[str, Student], timeslots: Dict[str, Timeslot]) -> int:
    order = {tid: slot.order_index for tid, slot in timeslots.items()}
    penalty = 0
    for student in students.values():
        indices = sorted(order[assignment[e]] for e in student.exam_ids if e in assignment and assignment[e] in order)
        penalty += sum(1 for a, b in zip(indices, indices[1:]) if b - a == 1)
    return penalty


def _capacity_violations(loads: Dict, timeslots: Dict[str, Timeslot]) -> Tuple[int, float]:
    count = 0
    excess_score = 0.0
    for tid, load in loads.items():
        slot = timeslots[tid]
        checks = [
            (load["student_count"], slot.capacity),
            (load["student_count"], slot.max_concurrent_students),
            (load["cpu"], slot.max_cpu),
            (load["ram"], slot.max_ram),
            (load["bandwidth"], slot.max_bandwidth),
        ]
        for actual, limit in checks:
            if actual > limit:
                count += 1
                excess_score += float(actual - limit) / max(float(limit), 1.0)
    return count, excess_score


def evaluate_schedule(assignment: Dict[str, str], exams: Dict[str, Exam], students: Dict[str, Student], timeslots: Dict[str, Timeslot], config: ServerConfig, runtime_seconds: float = 0.0) -> Dict:
    loads = calculate_timeslot_loads(assignment, exams, timeslots, config)
    missing = len(set(exams) - set(assignment))
    conflicts = _student_conflicts(assignment, students)
    capacity_count, capacity_excess = _capacity_violations(loads, timeslots)
    hard_violations = missing + conflicts + capacity_count

    consecutive = _consecutive_penalty(assignment, students, timeslots)
    student_counts = [load["student_count"] for load in loads.values()] or [0]
    exam_counts = [load["exam_count"] for load in loads.values()] or [0]
    load_variance = variance(student_counts) if len(student_counts) > 1 else 0.0
    balance = variance(exam_counts) if len(exam_counts) > 1 else 0.0
    department_penalty = sum(max(counter.values()) - mean(counter.values()) for load in loads.values() for counter in [load["departments"]] if counter)

    total_soft = (
        PENALTY_WEIGHTS.consecutive_exam * consecutive
        + PENALTY_WEIGHTS.load_variance * load_variance
        + PENALTY_WEIGHTS.balance * balance
        + PENALTY_WEIGHTS.department * department_penalty
    )
    hard_penalty = PENALTY_WEIGHTS.hard_conflict * (missing + conflicts) + PENALTY_WEIGHTS.capacity * capacity_excess

    return {
        "hard_constraint_violations": int(hard_violations),
        "missing_exam_assignments": int(missing),
        "student_conflicts": int(conflicts),
        "capacity_violations": int(capacity_count),
        "total_soft_penalty": float(total_soft),
        "consecutive_exam_penalty": float(consecutive),
        "load_variance_penalty": float(load_variance),
        "balance_penalty": float(balance),
        "department_penalty": float(department_penalty),
        "cpu_usage_per_timeslot": {tid: round(load["cpu"], 4) for tid, load in loads.items()},
        "ram_usage_per_timeslot": {tid: round(load["ram"], 4) for tid, load in loads.items()},
        "bandwidth_usage_per_timeslot": {tid: round(load["bandwidth"], 4) for tid, load in loads.items()},
        "concurrent_students_per_timeslot": {tid: int(load["student_count"]) for tid, load in loads.items()},
        "exam_count_per_timeslot": {tid: int(load["exam_count"]) for tid, load in loads.items()},
        "max_load": float(max(student_counts) if student_counts else 0),
        "average_load": float(mean(student_counts) if student_counts else 0),
        "load_variance": float(load_variance),
        "runtime_seconds": float(runtime_seconds),
        "objective_value": float(hard_penalty + total_soft),
    }

