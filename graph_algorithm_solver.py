from __future__ import annotations

import time
from typing import Dict

from collections import Counter

from evaluation import calculate_timeslot_loads, evaluate_schedule
from models import Exam, ScheduleResult, ServerConfig, Student, Timeslot


class GraphAlgorithmSolver:
    def __init__(self, repair_rounds: int = 2):
        self.repair_rounds = repair_rounds

    def _construct(self, exams: Dict[str, Exam], timeslots: Dict[str, Timeslot], config: ServerConfig) -> Dict[str, str]:
        ordered_exams = sorted(exams.values(), key=lambda exam: (-exam.student_count, exam.department_id, exam.exam_id))
        ordered_slots = sorted(timeslots, key=lambda tid: timeslots[tid].order_index)
        assignment: Dict[str, str] = {}
        student_loads = {tid: 0 for tid in ordered_slots}
        exam_loads = {tid: 0 for tid in ordered_slots}
        department_loads = {tid: Counter() for tid in ordered_slots}
        total_students = sum(exam.student_count for exam in exams.values())
        target_students = total_students / max(len(ordered_slots), 1)
        target_exams = len(exams) / max(len(ordered_slots), 1)

        for exam in ordered_exams:
            def score(tid: str) -> float:
                slot = timeslots[tid]
                next_students = student_loads[tid] + exam.student_count
                next_exams = exam_loads[tid] + 1
                cpu = next_students * config.cpu_per_student
                ram = next_students * config.ram_per_student
                bandwidth = next_students * config.bandwidth_per_student
                capacity_limit = min(slot.capacity, slot.max_concurrent_students)
                excess = (
                    max(0, next_students - capacity_limit) / max(capacity_limit, 1)
                    + max(0, cpu - slot.max_cpu) / max(slot.max_cpu, 1)
                    + max(0, ram - slot.max_ram) / max(slot.max_ram, 1)
                    + max(0, bandwidth - slot.max_bandwidth) / max(slot.max_bandwidth, 1)
                )
                balance = abs(next_students - target_students) + abs(next_exams - target_exams) * 25
                department_pressure = department_loads[tid][exam.department_id] + exam.student_count
                return excess * 1_000_000 + balance + department_pressure * 0.5

            best_tid = min(ordered_slots, key=score)
            assignment[exam.exam_id] = best_tid
            student_loads[best_tid] += exam.student_count
            exam_loads[best_tid] += 1
            department_loads[best_tid][exam.department_id] += exam.student_count
        return assignment

    def _repair(self, assignment: Dict[str, str], exams: Dict[str, Exam], timeslots: Dict[str, Timeslot], config: ServerConfig) -> Dict[str, str]:
        repaired = dict(assignment)
        for _ in range(self.repair_rounds):
            loads = calculate_timeslot_loads(repaired, exams, timeslots, config)
            overloaded = [
                tid
                for tid, load in loads.items()
                if load["student_count"] > min(timeslots[tid].capacity, timeslots[tid].max_concurrent_students)
                or load["cpu"] > timeslots[tid].max_cpu
                or load["ram"] > timeslots[tid].max_ram
                or load["bandwidth"] > timeslots[tid].max_bandwidth
            ]
            if not overloaded:
                break
            for tid in overloaded:
                candidate_exams = sorted(loads[tid]["exams"], key=lambda eid: exams[eid].student_count, reverse=True)
                for exam_id in candidate_exams:
                    exam = exams[exam_id]
                    current_score = evaluate_schedule(repaired, exams, {}, timeslots, config)["objective_value"]
                    partial = {k: v for k, v in repaired.items() if k != exam_id}
                    partial_loads = calculate_timeslot_loads(partial, exams, timeslots, config)

                    def move_score(target: str) -> float:
                        slot = timeslots[target]
                        next_students = partial_loads[target]["student_count"] + exam.student_count
                        cpu = next_students * config.cpu_per_student
                        ram = next_students * config.ram_per_student
                        bandwidth = next_students * config.bandwidth_per_student
                        capacity_limit = min(slot.capacity, slot.max_concurrent_students)
                        return (
                            max(0, next_students - capacity_limit) / max(capacity_limit, 1)
                            + max(0, cpu - slot.max_cpu) / max(slot.max_cpu, 1)
                            + max(0, ram - slot.max_ram) / max(slot.max_ram, 1)
                            + max(0, bandwidth - slot.max_bandwidth) / max(slot.max_bandwidth, 1)
                            + partial_loads[target]["student_count"] / max(capacity_limit, 1)
                        )

                    best_tid = min(timeslots, key=move_score)
                    trial = dict(repaired)
                    trial[exam_id] = best_tid
                    if evaluate_schedule(trial, exams, {}, timeslots, config)["objective_value"] <= current_score:
                        repaired = trial
                        break
        return repaired

    def solve(self, exams: Dict[str, Exam], students: Dict[str, Student], timeslots: Dict[str, Timeslot], config: ServerConfig) -> ScheduleResult:
        start = time.time()
        if not exams or not timeslots:
            raise ValueError("Sinav veya timeslot verisi bos. Graph solver baslatilamadi.")

        assignment = self._construct(exams, timeslots, config)
        assignment = self._repair(assignment, exams, timeslots, config)
        runtime = time.time() - start
        metrics = evaluate_schedule(assignment, exams, students, timeslots, config, runtime)
        return ScheduleResult(
            "graph",
            assignment,
            metrics["objective_value"],
            metrics,
            runtime,
            metrics["hard_constraint_violations"] == 0,
            [metrics["objective_value"]],
            "Greedy graph coloring style assignment with load-aware slot scoring.",
        )
