from __future__ import annotations

import random
import time
from typing import Dict, List, Optional

from evaluation import evaluate_schedule
from models import Exam, ScheduleResult, ServerConfig, Student, Timeslot


class GeneticAlgorithmSolver:
    def __init__(self, population_size: int = 80, generations: int = 300, mutation_rate: float = 0.08, elite_size: int = 4, seed: int = 42):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.elite_size = elite_size
        self.random = random.Random(seed)

    def _random_assignment(self, exam_ids: List[str], timeslot_ids: List[str]) -> Dict[str, str]:
        return {exam_id: self.random.choice(timeslot_ids) for exam_id in exam_ids}

    def _fitness(self, assignment, exams, students, timeslots, config) -> float:
        return evaluate_schedule(assignment, exams, students, timeslots, config)["objective_value"]

    def _tournament(self, population, scored, k: int = 3):
        adaylar = self.random.sample(list(zip(population, scored)), min(k, len(population)))
        return min(adaylar, key=lambda item: item[1])[0]

    def _crossover(self, a: Dict[str, str], b: Dict[str, str]) -> Dict[str, str]:
        child = {}
        for exam_id in a:
            child[exam_id] = a[exam_id] if self.random.random() < 0.5 else b[exam_id]
        return child

    def _mutate(self, assignment: Dict[str, str], timeslot_ids: List[str]):
        for exam_id in assignment:
            if self.random.random() < self.mutation_rate:
                assignment[exam_id] = self.random.choice(timeslot_ids)

    def _repair(self, assignment: Dict[str, str], exams: Dict[str, Exam], students: Dict[str, Student], timeslots: Dict[str, Timeslot], config: ServerConfig):
        timeslot_ids = list(timeslots)
        for student in students.values():
            used = {}
            for exam_id in student.exam_ids:
                tid = assignment.get(exam_id)
                if tid in used:
                    best_tid = min(timeslot_ids, key=lambda t: evaluate_schedule({**assignment, exam_id: t}, exams, students, timeslots, config)["objective_value"])
                    assignment[exam_id] = best_tid
                used[assignment.get(exam_id)] = exam_id
        return assignment

    def solve(self, exams: Dict[str, Exam], students: Dict[str, Student], timeslots: Dict[str, Timeslot], config: ServerConfig, initial_assignment: Optional[Dict[str, str]] = None) -> ScheduleResult:
        start = time.time()
        exam_ids = list(exams)
        timeslot_ids = list(timeslots)
        if not exam_ids or not timeslot_ids:
            raise ValueError("Sinav veya timeslot verisi bos. Optimizasyon baslatilamadi.")

        population = [self._random_assignment(exam_ids, timeslot_ids) for _ in range(self.population_size)]
        if initial_assignment:
            population[0] = dict(initial_assignment)
        history = []
        best = None
        best_score = float("inf")

        for _ in range(self.generations):
            scored = [self._fitness(ind, exams, students, timeslots, config) for ind in population]
            sirali = sorted(zip(population, scored), key=lambda item: item[1])
            if sirali[0][1] < best_score:
                best, best_score = dict(sirali[0][0]), float(sirali[0][1])
            history.append(best_score)

            yeni = [dict(ind) for ind, _ in sirali[: self.elite_size]]
            while len(yeni) < self.population_size:
                p1 = self._tournament(population, scored)
                p2 = self._tournament(population, scored)
                child = self._crossover(p1, p2)
                self._mutate(child, timeslot_ids)
                yeni.append(self._repair(child, exams, students, timeslots, config))
            population = yeni

        runtime = time.time() - start
        metrics = evaluate_schedule(best or {}, exams, students, timeslots, config, runtime)
        return ScheduleResult("ga", best or {}, metrics["objective_value"], metrics, runtime, metrics["hard_constraint_violations"] == 0, history)

