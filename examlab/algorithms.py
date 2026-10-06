"""Independent baseline implementations on one shared overlap-aware objective.

These are transparent reference baselines, not reproductions of named authors' code.
ANN is a continuous Hopfield-style energy relaxation, not a trained predictor.
"""
from time import perf_counter
import numpy as np
from ortools.sat.python import cp_model

ALGORITHMS = {
    "cp_gd": "CP-SAT → Great Deluge",
    "pso": "Parçacık Sürü Optimizasyonu (PSO)",
    "ga": "Genetik Algoritma (GA)",
    "ts": "Tabu Arama (TS)",
    "ac": "Karınca Kolonisi (AC)",
    "hs": "Harmony Search (HS)",
    "heuristic": "Probleme Özgü Sezgisel",
    "ann": "Yapay Sinir Ağı (enerji modeli)",
    "sa": "Benzetilmiş Tavlama (SA)",
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


def constructive(p, capacity, rng, randomized=False):
    """Largest exams first, assigning to the least overloaded overlap interval."""
    order = np.argsort(-p.counts if not randomized else -p.counts * rng.uniform(.8, 1.2, len(p.ids)))
    assignment = np.zeros(len(p.ids), dtype=int)
    loads = np.zeros(p.overlap.shape[1], dtype=np.int64)
    for i in order:
        candidates = loads[None, :] + p.counts[i] * p.overlap
        scores = np.maximum(candidates-capacity, 0).sum(axis=1) * (int(p.counts.sum())+1) + candidates.max(axis=1)
        choices = np.flatnonzero(scores == scores.min())
        t = int(rng.choice(choices))
        assignment[i] = t
        loads = candidates[t]
    return assignment


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


def solve(name, p, capacity, seed=42, seconds=5, evaluations=2000, population=20):
    if name not in ALGORITHMS or capacity <= 0 or seconds <= 0 or evaluations < 1 or population < 2:
        raise ValueError("Invalid algorithm or search parameters.")
    rng = np.random.default_rng(seed)
    b = Budget(p, capacity, seconds, evaluations)
    n, m = len(p.ids), len(p.starts)
    details = {}
    if name == "cp_gd":
        a, status = cp_first(p, capacity, seconds * .6, seed)
        details["cp_status"] = status
        if a is None:
            return {"algorithm": name, "seed": seed, "status": "no_solution", "cp_status": status,
                    "runtime_seconds": perf_counter()-b.start, "evaluations": 0, "history": [], "metrics": None}
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
    elif name in ("sa", "ts", "heuristic"):
        a = constructive(p, capacity, rng) if name == "heuristic" else rng.integers(m, size=n)
        score = b.evaluate(a)
        tabu, iteration = {}, 0
        while b.active():
            iteration += 1
            if name == "ts":
                candidates = []
                for _ in range(min(20, max(2, n))):
                    if not b.active():
                        break
                    i, t = int(rng.integers(n)), int(rng.integers(m))
                    trial = a.copy(); trial[i] = t
                    old_best = b.best_score
                    value = b.evaluate(trial)
                    if tabu.get((i, t), 0) <= iteration or value < old_best:
                        candidates.append((value, i, t, trial))
                if candidates:
                    score, i, t, trial = min(candidates, key=lambda item: item[0])
                    tabu[(i, int(a[i]))] = iteration + 7
                    a = trial
            else:
                trial = neighbor(a, rng, m)
                value = b.evaluate(trial)
                temperature = max(.01, float(p.counts.max()) * (1 - b.evaluations / evaluations))
                if value <= score or (name == "sa" and rng.random() < np.exp(-min(700, (value-score)/temperature))):
                    a, score = trial, value
    elif name in ("ga", "pso", "hs"):
        size = min(population, evaluations)
        pop = rng.integers(m, size=(size, n))
        scores = np.array([b.evaluate(a) for a in pop], dtype=float)
        personal, personal_scores = pop.copy(), scores.copy()
        velocity = np.zeros_like(pop, dtype=float)
        k = 0
        while b.active():
            k = (k + 1) % size
            if name == "ga":
                def tournament():
                    ids = rng.integers(size, size=3)
                    return pop[ids[np.argmin(scores[ids])]]
                a, c = tournament(), tournament()
                trial = np.where(rng.random(n) < .5, a, c)
                mask = rng.random(n) < max(1/n, .02)
                trial[mask] = rng.integers(m, size=int(mask.sum()))
            elif name == "pso":
                velocity[k] = .7*velocity[k] + 1.4*rng.random(n)*(personal[k]-pop[k]) + 1.4*rng.random(n)*(b.best-pop[k])
                trial = np.clip(np.rint(pop[k]+velocity[k]), 0, m-1).astype(int)
                # Mutation prevents quantized particles from freezing.
                mask = rng.random(n) < .02
                trial[mask] = rng.integers(m, size=int(mask.sum()))
            else:
                trial = pop[rng.integers(size, size=n), np.arange(n)].copy()
                fresh = rng.random(n) > .9
                trial[fresh] = rng.integers(m, size=int(fresh.sum()))
                pitch = rng.random(n) < .3
                trial[pitch] = (trial[pitch] + rng.choice([-1, 1], size=int(pitch.sum()))) % m
            value = b.evaluate(trial)
            if name == "pso":
                pop[k], scores[k] = trial, value
                if value < personal_scores[k]:
                    personal[k], personal_scores[k] = trial.copy(), value
            elif value <= scores.max():
                worst = int(np.argmax(scores)); pop[worst], scores[worst] = trial, value
    elif name == "ac":
        pheromone = np.ones((n, m))
        while b.active():
            a = np.zeros(n, dtype=int)
            loads = np.zeros(p.overlap.shape[1], dtype=np.int64)
            for i in rng.permutation(n):
                prospective = loads[None, :] + p.counts[i]*p.overlap
                cost = prospective.max(axis=1) + np.maximum(prospective-capacity, 0).sum(axis=1)*(int(p.counts.sum())+1)
                weights = pheromone[i] / np.maximum(cost, 1)**2
                t = int(rng.choice(m, p=weights/weights.sum()))
                a[i] = t; loads = prospective[t]
            value = b.evaluate(a)
            pheromone *= .9
            pheromone[np.arange(n), b.best] += 1
            np.clip(pheromone, .01, 10, out=pheromone)
    else:  # Continuous recurrent assignment neurons with mean-field energy updates.
        logits = rng.normal(0, .2, (n, m))
        scaled_counts = p.counts / max(float(p.counts.max()), 1)
        while b.active():
            probs = np.exp(logits-logits.max(axis=1, keepdims=True))
            probs /= probs.sum(axis=1, keepdims=True)
            trial = np.argmax(probs, axis=1)
            b.evaluate(trial)
            load = (p.counts @ probs) @ p.overlap
            # Gradient of squared load and squared capacity overflow energy.
            pressure = (load + 10*np.maximum(load-capacity, 0)) / max(capacity, 1)
            gradient = scaled_counts[:, None] * (p.overlap @ pressure)[None, :]
            logits -= .2 * (gradient - (probs*gradient).sum(axis=1, keepdims=True))
            logits += rng.normal(0, .01, logits.shape)
            np.clip(logits, -30, 30, out=logits)
    metrics = p.metrics(b.best, capacity)
    return {"algorithm": name, "seed": seed, "status": "feasible" if metrics["feasible"] else "infeasible_candidate",
            "runtime_seconds": perf_counter()-b.start, "evaluations": b.evaluations,
            "metrics": metrics, "assignment": b.best.tolist(), "history": b.history, **details}
