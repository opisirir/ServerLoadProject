from __future__ import annotations

import time
from typing import Dict

from evaluation import evaluate_schedule
from genetic_algorithm import GeneticAlgorithmSolver
from models import Exam, ScheduleResult, ServerConfig, Student, Timeslot
from simulated_annealing import SimulatedAnnealingSolver


class HybridSolver:
    def __init__(self, ga_kwargs=None, sa_kwargs=None):
        self.ga_kwargs = ga_kwargs or {}
        self.sa_kwargs = sa_kwargs or {}

    def solve(self, exams: Dict[str, Exam], students: Dict[str, Student], timeslots: Dict[str, Timeslot], config: ServerConfig) -> ScheduleResult:
        start = time.time()
        ga = GeneticAlgorithmSolver(**self.ga_kwargs)
        ga_result = ga.solve(exams, students, timeslots, config)
        sa = SimulatedAnnealingSolver(**self.sa_kwargs)
        sa_result = sa.solve(exams, students, timeslots, config, initial_assignment=ga_result.assignment)
        runtime = time.time() - start
        metrics = evaluate_schedule(sa_result.assignment, exams, students, timeslots, config, runtime)
        return ScheduleResult(
            "hybrid",
            sa_result.assignment,
            metrics["objective_value"],
            metrics,
            runtime,
            metrics["hard_constraint_violations"] == 0,
            ga_result.history + sa_result.history,
            "GA sonucu SA baslangic cozumu olarak iyilestirildi.",
        )

