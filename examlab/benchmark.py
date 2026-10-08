import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import numpy as np
import ortools

from .algorithms import ALGORITHMS, solve
from .data import load_problem
from .model import SCENARIOS, PAPER_CAPACITY


def run(p, metadata, scenarios, seeds, seconds, evaluations):
    experiments = []
    for scenario, capacity in scenarios.items():
        runs = []
        for name in ALGORITHMS:
            for seed in seeds:
                result = solve(name, p, capacity, seed, seconds, evaluations)
                runs.append(result)
                print(f"{scenario} {name} seed={seed}: {result['status']} peak={result['metrics']['peak'] if result['metrics'] else '-'}", flush=True)
        feasible_runs = [r for r in runs if r["metrics"] and r["metrics"]["feasible"]]
        shared_bound = max([p.lower_bound()] + [r.get("lower_bound", 0) for r in runs])
        if feasible_runs and shared_bound > min(r["metrics"]["peak"] for r in feasible_runs):
            raise RuntimeError("Certified lower bound exceeds a feasible peak")
        for r in runs:
            r["gap_pct"] = (100*(r["metrics"]["peak"]-shared_bound)/r["metrics"]["peak"]) if r["metrics"] else None
        summary = []
        for name in ALGORITHMS:
            selected = [r for r in runs if r["algorithm"] == name]
            feasible = [r for r in selected if r["metrics"] and r["metrics"]["feasible"]]
            peaks = [r["metrics"]["peak"] for r in feasible]
            summary.append({"algorithm": name, "runs": len(selected),
                            "feasible_runs": len(feasible), "success_rate": len(feasible)/len(selected)*100,
                            "mean_peak": float(np.mean(peaks)) if peaks else None,
                            "std_peak": float(np.std(peaks)) if peaks else None,
                            "best_peak": min(peaks) if peaks else None,
                            "mean_gap_pct": float(np.mean([r["gap_pct"] for r in feasible])) if feasible else None,
                            "proven_optimal_runs": sum(r["metrics"]["peak"] == shared_bound for r in feasible),
                            "mean_runtime": float(np.mean([r["runtime_seconds"] for r in selected]))})
        experiments.append({"scenario": scenario, "capacity": capacity,
                            "certified_lower_bound": shared_bound,
                            "reference": p.metrics(p.reference, capacity), "runs": runs, "summary": summary})
    return {"schema_version": 2, "created_at": datetime.now(timezone.utc).isoformat(),
            "dataset": {**metadata, "exams": len(p.ids), "enrollments": int(p.counts.sum()),
                        "slots": len(p.starts), "duration_minutes": p.minutes, "lower_bound": p.lower_bound()},
            "settings": {"seconds_per_run": seconds, "gd_max_evaluations": evaluations,
                         "seeds": seeds, "python": platform.python_version(), "ortools": ortools.__version__,
                         "numpy": np.__version__, "machine": platform.machine()},
            "algorithms": ALGORITHMS, "scenarios": SCENARIOS,
            "timeline": p.edges.astype(str).tolist(), "starts": p.starts.astype(str).tolist(),
            "exams": [{"exam_id": i, "student_count": int(c), "reference_slot": int(t)}
                      for i, c, t in zip(p.ids, p.counts, p.reference)],
            "experiments": experiments,
            "paper": {"title": "Algorithmic Exam Timetabling to Prevent Server Crash in Cloud-Based Learning Management Systems",
                      "version": "V3", "reported_before": 5948, "reported_after": 3582,
                      "reported_reduction_pct": 39.78, "capacity": 5000,
                      "note": "Manuscript single-run result; not reproduced by this demo."}}


def main():
    parser = argparse.ArgumentParser(description="CP-SAT + Great Deluge versus mathematical optimization models")
    parser.add_argument("--input", "--planned_schedule", default="data/example_planned_schedule.csv")
    parser.add_argument("--output", default="results/benchmark.json")
    parser.add_argument("--scenario", choices=[*SCENARIOS, "paper", "all"], default="all")
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--seconds", type=float, default=5)
    parser.add_argument("--evaluations", type=int, default=1000000)
    parser.add_argument("--drop-invalid", action="store_true")
    args = parser.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]
    if not seeds or len(set(seeds)) != len(seeds) or any(s < 0 or s > 2147483647 for s in seeds):
        parser.error("Seeds must be distinct integers from 0 to 2147483647.")
    p, metadata = load_problem(args.input, args.minutes, args.drop_invalid)
    metadata["sha256"] = hashlib.sha256(Path(args.input).read_bytes()).hexdigest()
    scenarios = {**SCENARIOS, "paper": PAPER_CAPACITY} if args.scenario == "all" else {args.scenario: PAPER_CAPACITY if args.scenario == "paper" else SCENARIOS[args.scenario]}
    report = run(p, metadata, scenarios, seeds, args.seconds, args.evaluations)
    path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Report: {path}")


if __name__ == "__main__":
    main()
