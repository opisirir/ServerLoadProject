from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Exam:
    exam_id: str
    exam_name: str
    student_count: int
    department_id: str = "UNKNOWN"


@dataclass
class Student:
    student_id: str
    exam_ids: List[str] = field(default_factory=list)
    department_id: str = "UNKNOWN"


@dataclass
class Timeslot:
    timeslot_id: str
    date: str
    start_time: str
    end_time: str
    capacity: int
    max_cpu: float
    max_ram: float
    max_bandwidth: float
    max_concurrent_students: int
    order_index: int = 0


@dataclass
class ServerConfig:
    cpu_per_student: float
    ram_per_student: float
    bandwidth_per_student: float
    max_cpu: float
    max_ram: float
    max_bandwidth: float
    max_concurrent_students: int


@dataclass
class ScheduleResult:
    solver_name: str
    assignment: Dict[str, str]
    objective_value: float
    metrics: Dict
    runtime_seconds: float
    feasible: bool
    history: List[float] = field(default_factory=list)
    message: Optional[str] = None

