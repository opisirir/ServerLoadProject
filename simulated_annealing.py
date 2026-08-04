from __future__ import annotations

import random
import time
from typing import Dict, Optional

from evaluation import calculate_timeslot_loads, evaluate_schedule
from models import Exam, ScheduleResult, ServerConfig, Student, Timeslot


class SimulatedAnnealingSolver:
    def __init__(self, iterations: int = 5000, initial_temp: float = 1000.0, cooling_rate: float = 0.995, seed: int = 42):
        self.iterations = iterations
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.random = random.Random(seed)

    def _initial(self, exams, timeslots):
        tids = list(timeslots)
        return {eid: self.random.choice(tids) for eid in exams}

    def _neighbor(self, assignment: Dict[str, str], exams: Dict[str, Exam], timeslots: Dict[str, Timeslot], config: ServerConfig):
        yeni = dict(assignment)
        exam_ids = list(exams)
        tids = list(timeslots)
        hareket = self.random.random()
        if hareket < 0.45:
            yeni[self.random.choice(exam_ids)] = self.random.choice(tids)
        elif hareket < 0.80 and len(exam_ids) >= 2:
            a, b = self.random.sample(exam_ids, 2)
            yeni[a], yeni[b] = yeni[b], yeni[a]
        else:
            loads = calculate_timeslot_loads(yeni, exams, timeslots, config)
            yogun = max(loads, key=lambda tid: loads[tid]["student_count"])
            bos = min(loads, key=lambda tid: loads[tid]["student_count"])
            adaylar = [eid for eid, tid in yeni.items() if tid == yogun]
            if adaylar:
                yeni[self.random.choice(adaylar)] = bos
        return yeni

    def solve(self, exams: Dict[str, Exam], students: Dict[str, Student], timeslots: Dict[str, Timeslot], config: ServerConfig, initial_assignment: Optional[Dict[str, str]] = None) -> ScheduleResult:
        start = time.time()
        current = dict(initial_assignment) if initial_assignment else self._initial(exams, timeslots)
        current_score = evaluate_schedule(current, exams, students, timeslots, config)["objective_value"]
        best, best_score = dict(current), current_score
        temp = self.initial_temp
        history = [best_score]

        for _ in range(self.iterations):
            neighbor = self._neighbor(current, exams, timeslots, config)
            score = evaluate_schedule(neighbor, exams, students, timeslots, config)["objective_value"]
            delta = score - current_score
            if delta < 0 or self.random.random() < pow(2.718281828, -delta / max(temp, 1e-9)):
                current, current_score = neighbor, score
                if score < best_score:
                    best, best_score = dict(neighbor), score
            temp *= self.cooling_rate
            history.append(best_score)

        runtime = time.time() - start
        metrics = evaluate_schedule(best, exams, students, timeslots, config, runtime)
        return ScheduleResult("sa", best, metrics["objective_value"], metrics, runtime, metrics["hard_constraint_violations"] == 0, history)

