import tempfile
from pathlib import Path
import unittest
import numpy as np

from examlab.algorithms import ALGORITHMS, cp_first, solve
from examlab.data import load_problem
from examlab.model import Problem, SCENARIOS


class ModelTests(unittest.TestCase):
    def problem(self):
        return Problem(["A", "B", "C"], np.array([100, 150, 50]),
                       np.array(["2026-12-31T23:30", "2027-01-01T00:00", "2027-01-01T00:30"], dtype="datetime64[m]"),
                       np.array([0, 1, 2]), 60)

    def test_overlap_midnight_and_half_open_end(self):
        p = self.problem()
        self.assertEqual(p.loads(p.reference).tolist(), [100, 250, 200, 50])
        self.assertEqual(p.metrics(p.reference, 200)["minutes_above_capacity"], 30)
        self.assertFalse(p.metrics(p.reference, 200)["feasible"])
        self.assertTrue(p.metrics(p.reference, 250)["feasible"])

    def test_invalid_assignment_not_silently_ignored(self):
        p = self.problem()
        for bad in [np.array([0, 1]), np.array([0, 1, 3]), np.array([0., 1., 2.]), np.array([-1, 1, 2])]:
            with self.assertRaises(ValueError):
                p.loads(bad)

    def test_capacity_is_harder_than_peak_objective(self):
        p = self.problem()
        self.assertGreater(p.score(np.array([0, 0, 0]), 200), p.score(np.array([0, 2, 0]), 200))

    def test_cp_enforces_overlap_and_reports_infeasible(self):
        p = self.problem()
        a, _ = cp_first(p, 200, 2, 42)
        self.assertIsNotNone(a)
        self.assertTrue(p.metrics(a, 200)["feasible"])
        a, status = cp_first(p, 99, 2, 42)
        self.assertIsNone(a)
        self.assertEqual(status, "INFEASIBLE")

    def test_all_algorithms_return_complete_verified_assignments(self):
        p = self.problem()
        for name in ALGORITHMS:
            with self.subTest(name=name):
                r = solve(name, p, 250, seed=7, seconds=2, evaluations=50, population=5)
                self.assertIsNotNone(r["metrics"])
                self.assertEqual(r["metrics"], p.metrics(np.array(r["assignment"]), 250))
                self.assertLessEqual(r["evaluations"], 50)
                if name == "cp_gd":
                    self.assertTrue(r["metrics"]["feasible"])
                    self.assertLessEqual(r["metrics"]["peak"], r["initial_peak"])

    def test_seeded_search_reproducible_with_nonbinding_time(self):
        p = self.problem()
        for name in ALGORITHMS:
            a = solve(name, p, 300, seed=9, seconds=10, evaluations=30, population=5)
            b = solve(name, p, 300, seed=9, seconds=10, evaluations=30, population=5)
            self.assertEqual(a["assignment"], b["assignment"], name)

    def test_scenario_maxima(self):
        self.assertEqual(list(SCENARIOS.values()), [500, 2500, 6000])

    def test_loader_keeps_repeated_courses_and_explicit_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"input.csv"
            path.write_text("exam_id,student_count,date,start_time\nA,10,2026-01-01,23:30\nA,20,2026-01-02,00:00\nB,2.5,2026-01-02,25:00\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_problem(path)
            p, metadata = load_problem(path, drop_invalid=True)
            self.assertEqual(len(p.ids), 2)
            self.assertEqual(int(p.counts.sum()), 30)
            self.assertEqual(metadata["rejected_rows"], [4])
            self.assertEqual(metadata["repeated_course_ids"], 1)
