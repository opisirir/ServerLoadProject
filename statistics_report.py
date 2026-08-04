from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict

import pandas as pd

from evaluation import calculate_timeslot_loads
from models import Exam, ServerConfig, Timeslot


def department_summary(exams: Dict[str, Exam]) -> pd.DataFrame:
    rows = defaultdict(lambda: {"department_id": "", "exam_count": 0, "student_count": 0})
    for exam in exams.values():
        row = rows[exam.department_id]
        row["department_id"] = exam.department_id
        row["exam_count"] += 1
        row["student_count"] += exam.student_count
    df = pd.DataFrame(rows.values())
    if df.empty:
        return pd.DataFrame(columns=["department_id", "exam_count", "student_count"])
    return df.sort_values(["exam_count", "student_count"], ascending=False).reset_index(drop=True)


def top_exams(exams: Dict[str, Exam], limit: int = 20) -> pd.DataFrame:
    rows = [
        {
            "exam_id": exam.exam_id,
            "exam_name": exam.exam_name,
            "department_id": exam.department_id,
            "student_count": exam.student_count,
        }
        for exam in exams.values()
    ]
    return pd.DataFrame(rows).sort_values("student_count", ascending=False).head(limit).reset_index(drop=True)


def timeslot_summary(assignment: Dict[str, str], exams: Dict[str, Exam], timeslots: Dict[str, Timeslot], config: ServerConfig, label: str) -> pd.DataFrame:
    loads = calculate_timeslot_loads(assignment, exams, timeslots, config)
    rows = []
    for tid, slot in sorted(timeslots.items(), key=lambda item: item[1].order_index):
        load = loads.get(tid, {})
        rows.append(
            {
                "schedule": label,
                "timeslot_id": tid,
                "date": slot.date,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "exam_count": int(load.get("exam_count", 0)),
                "student_count": int(load.get("student_count", 0)),
                "cpu": float(load.get("cpu", 0.0)),
                "ram": float(load.get("ram", 0.0)),
                "bandwidth": float(load.get("bandwidth", 0.0)),
            }
        )
    return pd.DataFrame(rows)


def department_timeslot_concentration(assignment: Dict[str, str], exams: Dict[str, Exam], label: str) -> pd.DataFrame:
    counts = Counter()
    students = Counter()
    for exam_id, timeslot_id in assignment.items():
        exam = exams.get(exam_id)
        if not exam:
            continue
        key = (exam.department_id, timeslot_id)
        counts[key] += 1
        students[key] += exam.student_count

    rows = [
        {
            "schedule": label,
            "department_id": department,
            "timeslot_id": timeslot_id,
            "exam_count": exam_count,
            "student_count": students[(department, timeslot_id)],
        }
        for (department, timeslot_id), exam_count in counts.items()
    ]
    if not rows:
        return pd.DataFrame(columns=["schedule", "department_id", "timeslot_id", "exam_count", "student_count"])
    return pd.DataFrame(rows).sort_values(["exam_count", "student_count"], ascending=False).reset_index(drop=True)


def overall_summary(exams: Dict[str, Exam], timeslots: Dict[str, Timeslot]) -> Dict:
    department_df = department_summary(exams)
    total_students = sum(exam.student_count for exam in exams.values())
    return {
        "exam_count": len(exams),
        "timeslot_count": len(timeslots),
        "department_count": int(department_df["department_id"].nunique()) if not department_df.empty else 0,
        "total_student_count": int(total_students),
        "average_students_per_exam": float(total_students / len(exams)) if exams else 0.0,
        "largest_department_by_exams": department_df.iloc[0].to_dict() if not department_df.empty else {},
        "largest_department_by_students": department_df.sort_values("student_count", ascending=False).iloc[0].to_dict() if not department_df.empty else {},
    }

