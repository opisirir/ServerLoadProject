"""Paper CP-SAT → Great Deluge method and selected mathematical baselines."""
from time import perf_counter
import numpy as np
from ortools.sat.python import cp_model
from .math_models import solve_mathematical

ALGORITHMS = {
    "cp_gd": "CP-SAT → Great Deluge",
    "mip": "Karma Tam Sayılı Programlama (CBC)",
    "ilp": "Tam Sayılı Lineer Programlama (CP-SAT)",
    "goal": "Hedef Programlama (CBC)",
}


class Budget:
    def __init__(self, problem, capacity, seconds, evaluations):
        self.p, self.capacity = problem, capacity
        self.start, self.seconds, self.limit = perf_counter(), seconds, evaluations
        self.evaluations = 0
        self.best, self.best_score = None, float("inf")
        self.history = []

    def active(self):
        return self.evaluations < self.limit and perf_counter() - self.start < self.seconds

    def evaluate(self, assignment):
        value = self.p.score(assignment, self.capacity)
        self.evaluations += 1
        if value < self.best_score:
            self.best, self.best_score = assignment.copy(), value
            self.history.append({"evaluation": self.evaluations, "seconds": perf_counter() - self.start,
                                 "peak": int(self.p.loads(assignment).max()),
                                 "feasible": value <= int(self.p.counts.sum())})
        return value


def neighbor(a, rng, slots):
    b = a.copy()
    i = int(rng.integers(len(a)))
    if len(a) > 1 and rng.random() < .3:
        j = int(rng.integers(len(a)))
        b[i], b[j] = b[j], b[i]
    else:
        b[i] = int(rng.integers(slots))
    return b


def cp_first(p, capacity, seconds, seed):
    started = perf_counter()
    model = cp_model.CpModel()
    # Equivalent to one-hot assignment and every elementary interval constraint,
    # but avoids constructing exams × slots Boolean variables on large datasets.
    offsets = (p.starts-p.starts.min()).astype("timedelta64[m]").astype(int).tolist()
    starts = [model.NewIntVarFromDomain(cp_model.Domain.FromValues(offsets), f"start_{i}") for i in range(len(p.ids))]
    intervals = [model.NewFixedSizeIntervalVar(s, p.minutes, f"exam_{i}") for i, s in enumerate(starts)]
    model.AddCumulative(intervals, p.counts.tolist(), capacity)
    solver = cp_model.CpSolver()
    remaining = seconds - (perf_counter()-started)
    if remaining <= 0:
        return None, "UNKNOWN"
    solver.parameters.max_time_in_seconds = remaining
    solver.parameters.stop_after_first_solution = True
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, solver.StatusName(status)
    lookup = {offset: t for t, offset in enumerate(offsets)}
    a = np.array([lookup[solver.Value(s)] for s in starts])
    return a, solver.StatusName(status)


def solve(name, p, capacity, seed=42, seconds=5, evaluations=2000):
    if name not in ALGORITHMS or capacity <= 0 or seconds <= 0 or evaluations < 1:
        raise ValueError("Invalid algorithm or search parameters.")
    if name != "cp_gd":
        return solve_mathematical(name, p, capacity, seed, seconds)
    rng = np.random.default_rng(seed)
    b = Budget(p, capacity, seconds, evaluations)
    n, m = len(p.ids), len(p.starts)
    details = {"lower_bound": p.lower_bound(), "optimal": False, "history_kind": "incumbents"}
    if name == "cp_gd":
        a, status = cp_first(p, capacity, seconds * .6, seed)
        details["cp_status"] = status
        if a is None:
            return {"algorithm": name, "seed": seed, "status": "no_solution", "cp_status": status,
                    "runtime_seconds": perf_counter()-b.start, "evaluations": 0, "history": [], "metrics": None, **details}
        score = b.evaluate(a)
        details["initial_peak"] = int(p.loads(a).max())
        details["cp_seconds"] = perf_counter() - b.start
        initial, lower = score, p.lower_bound()
        while b.active():
            trial = neighbor(a, rng, m)
            # The second stage never accepts a capacity violation.
            loads = p.loads(trial)
            value = b.evaluate(trial) if loads.max() <= capacity else None
            if value is None:
                b.evaluations += 1
            progress = max(b.evaluations / evaluations, (perf_counter()-b.start) / seconds)
            level = initial - (initial-lower) * min(progress, 1)
            if value is not None and (value <= score or value <= level):
                a, score = trial, value
    metrics = p.metrics(b.best, capacity)
    return {"algorithm": name, "seed": seed, "status": "feasible" if metrics["feasible"] else "infeasible_candidate",
            "runtime_seconds": perf_counter()-b.start, "evaluations": b.evaluations,
            "metrics": metrics, "assignment": b.best.tolist(), "history": b.history, **details}
