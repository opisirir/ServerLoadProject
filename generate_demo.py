"""Deterministic synthetic public example; never represents the manuscript dataset."""
import csv
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import numpy as np
from examlab.data import load_problem
from examlab.benchmark import run
from examlab.model import SCENARIOS


def main():
    rng = np.random.default_rng(2026)
    slots = [datetime(2026, 4, 13+d, 9)+timedelta(minutes=30*t) for d in range(3) for t in range(12)]
    path = Path("data/example_planned_schedule.csv")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["exam_id", "exam_name", "student_count", "department_id", "date", "start_time"])
        for i in range(96):
            # All candidate starts appear; remaining exams cluster in the first morning.
            stamp = slots[i] if i < len(slots) else slots[int(rng.integers(4))]
            writer.writerow([f"EXAM_{i+1:04d}", f"Course_{i+1:04d}", int(rng.integers(20, 131)), f"Dept_{i%8+1:02d}", stamp.strftime("%Y-%m-%d"), stamp.strftime("%H:%M")])
    p, meta = load_problem(path)
    meta.update(synthetic=True, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    report = run(p, meta, SCENARIOS, [42, 43, 44], 2, 1000000)
    Path("web/data/benchmark.json").write_text(json.dumps(report, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    Path("web/data/example_planned_schedule.csv").write_bytes(path.read_bytes())


if __name__ == "__main__":
    main()
