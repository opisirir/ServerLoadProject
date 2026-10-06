from dataclasses import dataclass
import numpy as np

SCENARIOS = {"scenario_1": 500, "scenario_2": 2500, "scenario_3": 6000}
PAPER_CAPACITY = 5000


@dataclass
class Problem:
    ids: list
    counts: np.ndarray
    starts: np.ndarray
    reference: np.ndarray
    minutes: int = 60

    def __post_init__(self):
        self.counts = np.asarray(self.counts, dtype=np.int64)
        self.starts = np.asarray(self.starts, dtype="datetime64[m]")
        self.reference = np.asarray(self.reference, dtype=int)
        if self.minutes <= 0 or not len(self.ids) or not len(self.starts):
            raise ValueError("Positive duration, exams and candidate starts are required.")
        if len(self.ids) != len(set(self.ids)) or len(self.counts) != len(self.ids):
            raise ValueError("Exam IDs must be unique and counts must match.")
        if np.any(self.counts < 0) or self.counts.sum() <= 0:
            raise ValueError("Counts must be nonnegative with a positive total.")
        if np.isnat(self.starts).any() or len(np.unique(self.starts)) != len(self.starts):
            raise ValueError("Candidate starts must be valid and unique.")
        self.validate(self.reference)
        ends = self.starts + np.timedelta64(self.minutes, "m")
        self.edges = np.unique(np.concatenate([self.starts, ends]))
        self.overlap = ((self.starts[:, None] <= self.edges[:-1]) &
                        (ends[:, None] > self.edges[:-1])).astype(np.int64)
        self.durations = np.diff(self.edges).astype("timedelta64[m]").astype(int)

    def validate(self, assignment):
        a = np.asarray(assignment)
        if a.shape != (len(self.ids),) or not np.issubdtype(a.dtype, np.integer):
            raise ValueError("Each exam must have exactly one integer slot assignment.")
        if np.any(a < 0) or np.any(a >= len(self.starts)):
            raise ValueError("Assignment refers to an unknown slot.")

    def loads(self, assignment):
        self.validate(assignment)
        slot_load = np.bincount(assignment, weights=self.counts, minlength=len(self.starts))
        return (slot_load.astype(np.int64) @ self.overlap)

    def metrics(self, assignment, capacity):
        loads = self.loads(assignment)
        excess = np.maximum(loads - capacity, 0)
        return {"peak": int(loads.max()), "feasible": bool(not excess.any()),
                "overloaded_intervals": int(np.count_nonzero(excess)),
                "minutes_above_capacity": int(self.durations[excess > 0].sum()),
                "excess_participant_minutes": int(excess @ self.durations),
                "load_variance": float(np.var(loads[self.overlap.any(axis=0)])),
                "loads": loads.tolist()}

    def score(self, assignment, capacity):
        loads = self.loads(assignment)
        # Any capacity violation ranks below every feasible assignment.
        return int(np.maximum(loads - capacity, 0).sum()) * (int(self.counts.sum()) + 1) + int(loads.max())

    def lower_bound(self):
        available_minutes = int(self.durations[self.overlap.any(axis=0)].sum())
        return max(int(self.counts.max()), int(np.ceil(self.counts.sum() * self.minutes / available_minutes)))
