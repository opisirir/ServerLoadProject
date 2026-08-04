from __future__ import annotations

import time
from typing import Dict

from evaluation import evaluate_schedule
from models import Exam, ScheduleResult, ServerConfig, Student, Timeslot


class CPSATSolver:
    def __init__(self, time_limit: int = 60, workers: int = 8):
        self.time_limit = time_limit
        self.workers = workers

    def solve(self, exams: Dict[str, Exam], students: Dict[str, Student], timeslots: Dict[str, Timeslot], config: ServerConfig) -> ScheduleResult:
        try:
            from ortools.sat.python import cp_model
        except ImportError as exc:
            raise ImportError("CP-SAT icin OR-Tools gerekli. Kurulum: pip install ortools") from exc

        start = time.time()
        model = cp_model.CpModel()
        exam_ids = list(exams)
        timeslot_ids = list(timeslots)
        x = {(e, t): model.NewBoolVar(f"x_{e}_{t}") for e in exam_ids for t in timeslot_ids}

        for e in exam_ids:
            model.Add(sum(x[e, t] for t in timeslot_ids) == 1)

        for student in students.values():
            sinavlar = [e for e in student.exam_ids if e in exams]
            for t in timeslot_ids:
                if len(sinavlar) > 1:
                    model.Add(sum(x[e, t] for e in sinavlar) <= 1)

        scale = 1000
        for t in timeslot_ids:
            slot = timeslots[t]
            students_expr = sum(exams[e].student_count * x[e, t] for e in exam_ids)
            model.Add(students_expr <= min(slot.capacity, slot.max_concurrent_students))
            model.Add(sum(int(exams[e].student_count * config.cpu_per_student * scale) * x[e, t] for e in exam_ids) <= int(slot.max_cpu * scale))
            model.Add(sum(int(exams[e].student_count * config.ram_per_student * scale) * x[e, t] for e in exam_ids) <= int(slot.max_ram * scale))
            model.Add(sum(int(exams[e].student_count * config.bandwidth_per_student * scale) * x[e, t] for e in exam_ids) <= int(slot.max_bandwidth * scale))

        # Linear, solver-friendly soft objective: balance student and exam load around integer averages.
        avg_students = max(1, sum(e.student_count for e in exams.values()) // max(len(timeslot_ids), 1))
        avg_exams = max(1, len(exam_ids) // max(len(timeslot_ids), 1))
        penalties = []
        for t in timeslot_ids:
            student_load = sum(exams[e].student_count * x[e, t] for e in exam_ids)
            exam_load = sum(x[e, t] for e in exam_ids)
            s_dev = model.NewIntVar(0, max(sum(e.student_count for e in exams.values()), 1), f"sdev_{t}")
            e_dev = model.NewIntVar(0, max(len(exam_ids), 1), f"edev_{t}")
            model.AddAbsEquality(s_dev, student_load - avg_students)
            model.AddAbsEquality(e_dev, exam_load - avg_exams)
            penalties.extend([5 * s_dev, 20 * e_dev])

        order = {tid: slot.order_index for tid, slot in timeslots.items()}
        for student in students.values():
            sinavlar = [e for e in student.exam_ids if e in exams]
            for i, e1 in enumerate(sinavlar):
                for e2 in sinavlar[i + 1 :]:
                    for t1 in timeslot_ids:
                        for t2 in timeslot_ids:
                            if abs(order[t1] - order[t2]) == 1:
                                both = model.NewBoolVar(f"con_{e1}_{e2}_{t1}_{t2}")
                                model.Add(both <= x[e1, t1])
                                model.Add(both <= x[e2, t2])
                                model.Add(both >= x[e1, t1] + x[e2, t2] - 1)
                                penalties.append(50 * both)

        model.Minimize(sum(penalties))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit
        solver.parameters.num_search_workers = self.workers
        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return ScheduleResult("cp_sat", {}, float("inf"), {}, time.time() - start, False, [], "CP-SAT uygun cozum bulamadi.")

        assignment = {}
        for e in exam_ids:
            for t in timeslot_ids:
                if solver.Value(x[e, t]) == 1:
                    assignment[e] = t
                    break
        runtime = time.time() - start
        metrics = evaluate_schedule(assignment, exams, students, timeslots, config, runtime)
        return ScheduleResult("cp_sat", assignment, metrics["objective_value"], metrics, runtime, metrics["hard_constraint_violations"] == 0, [solver.ObjectiveValue()])
