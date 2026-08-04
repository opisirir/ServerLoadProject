from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from config import VARSAYILAN_CONFIG
from cp_sat_solver import CPSATSolver
from data_loader import load_all_data
from data_validator import validate_data
from evaluation import calculate_timeslot_loads
from genetic_algorithm import GeneticAlgorithmSolver
from graph_algorithm_solver import GraphAlgorithmSolver
from hybrid_solver import HybridSolver
from models import ScheduleResult, ServerConfig
from simulated_annealing import SimulatedAnnealingSolver
from statistics_report import department_summary, department_timeslot_concentration, overall_summary, timeslot_summary, top_exams
from visualization import generate_figures


def parse_args():
    parser = argparse.ArgumentParser(description="Examination Timetabling Problem optimizasyon sistemi")
    parser.add_argument("--students_exams", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--planned_schedule", default=None)
    parser.add_argument("--exam_students", default=None)
    parser.add_argument("--timeslots", default=None)
    parser.add_argument("--solver", choices=["cp_sat", "graph", "ga", "sa", "hybrid", "all"], default="hybrid")
    parser.add_argument("--output", default="outputs")
    parser.add_argument("--time_limit", type=int, default=60)
    parser.add_argument("--max_iterations", type=int, default=3000)
    parser.add_argument("--ga_generations", type=int, default=250)
    parser.add_argument("--population_size", type=int, default=80)
    parser.add_argument("--seed", type=int, default=VARSAYILAN_CONFIG.random_seed)
    return parser.parse_args()


def solver_olustur(ad: str, args):
    if ad == "cp_sat":
        return CPSATSolver(time_limit=args.time_limit)
    if ad == "graph":
        return GraphAlgorithmSolver()
    if ad == "ga":
        return GeneticAlgorithmSolver(population_size=args.population_size, generations=args.ga_generations, seed=args.seed)
    if ad == "sa":
        return SimulatedAnnealingSolver(iterations=args.max_iterations, seed=args.seed)
    if ad == "hybrid":
        return HybridSolver(
            ga_kwargs={"population_size": args.population_size, "generations": args.ga_generations, "seed": args.seed},
            sa_kwargs={"iterations": args.max_iterations, "seed": args.seed},
        )
    raise ValueError(f"Bilinmeyen solver: {ad}")


def schedule_dataframe(result, exams, timeslots, config):
    loads = calculate_timeslot_loads(result.assignment, exams, timeslots, config)
    rows = []
    for exam_id, timeslot_id in result.assignment.items():
        exam = exams[exam_id]
        slot = timeslots[timeslot_id]
        rows.append(
            {
                "exam_id": exam.exam_id,
                "exam_name": exam.exam_name,
                "department_id": exam.department_id,
                "student_count": exam.student_count,
                "timeslot_id": slot.timeslot_id,
                "date": slot.date,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "cpu_usage": round(exam.student_count * config.cpu_per_student, 4),
                "ram_usage": round(exam.student_count * config.ram_per_student, 4),
                "bandwidth_usage": round(exam.student_count * config.bandwidth_per_student, 4),
                "timeslot_total_students": loads[timeslot_id]["student_count"],
            }
        )
    return pd.DataFrame(rows).sort_values(["date", "start_time", "exam_id"])


def main():
    args = parse_args()
    exam_students_path = args.planned_schedule or args.exam_students
    if not exam_students_path:
        raise ValueError("--planned_schedule veya --exam_students verilmelidir.")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    config = ServerConfig(
        cpu_per_student=VARSAYILAN_CONFIG.cpu_per_student,
        ram_per_student=VARSAYILAN_CONFIG.ram_per_student,
        bandwidth_per_student=VARSAYILAN_CONFIG.bandwidth_per_student,
        max_cpu=VARSAYILAN_CONFIG.max_cpu,
        max_ram=VARSAYILAN_CONFIG.max_ram,
        max_bandwidth=VARSAYILAN_CONFIG.max_bandwidth,
        max_concurrent_students=VARSAYILAN_CONFIG.max_concurrent_students,
    )

    kayit_df, sinav_df, slot_df, exams, students, timeslots, config, metadata = load_all_data(
        args.students_exams, exam_students_path, args.timeslots, config
    )
    validation = validate_data(kayit_df, sinav_df, slot_df, output)
    if validation["errors"]:
        raise ValueError("Validasyon hatalari bulundu: " + "; ".join(validation["errors"]))

    secilenler = ["graph", "cp_sat", "ga", "sa", "hybrid"] if args.solver == "all" else [args.solver]
    results = []
    for ad in secilenler:
        try:
            result = solver_olustur(ad, args).solve(exams, students, timeslots, config)
            results.append(result)
            print(f"{ad}: objective={result.objective_value:.2f}, feasible={result.feasible}, runtime={result.runtime_seconds:.2f}s")
        except Exception as exc:
            results.append(ScheduleResult(ad, {}, float("inf"), {}, 0.0, False, [], str(exc)))
            print(f"{ad} calistirilamadi: {exc}")

    successful_results = [result for result in results if result.metrics]
    if not successful_results:
        raise RuntimeError("Hicbir solver sonuc uretmedi.")

    best = min(successful_results, key=lambda r: r.objective_value)
    schedule_dataframe(best, exams, timeslots, config).to_csv(output / "schedule_output.csv", index=False)
    reference_assignment = {}
    if "date" in sinav_df.columns and "start_time" in sinav_df.columns:
        from comparison import build_actual_assignment

        reference_assignment = build_actual_assignment(sinav_df, timeslots)

    pd.DataFrame(
        [
            {
                "solver": r.solver_name,
                "objective_value": r.objective_value,
                "feasible": r.feasible,
                "runtime_seconds": r.runtime_seconds,
                "hard_constraint_violations": r.metrics.get("hard_constraint_violations"),
                "total_soft_penalty": r.metrics.get("total_soft_penalty"),
            }
            for r in results
        ]
    ).to_csv(output / "results.csv", index=False)
    best_objective = best.objective_value
    pd.DataFrame(
        [
            {
                "solver": r.solver_name,
                "success": bool(r.metrics),
                "feasible": bool(r.feasible),
                "is_best": r.objective_value == best_objective,
                "objective_value": r.objective_value,
                "hard_constraint_violations": r.metrics.get("hard_constraint_violations") if r.metrics else None,
                "total_soft_penalty": r.metrics.get("total_soft_penalty") if r.metrics else None,
                "load_variance": r.metrics.get("load_variance") if r.metrics else None,
                "max_load": r.metrics.get("max_load") if r.metrics else None,
                "runtime_seconds": r.runtime_seconds,
                "success_rate_pct": 100.0 if r.metrics and r.feasible else 0.0,
            }
            for r in results
        ]
    ).to_csv(output / "algorithm_comparison.csv", index=False)

    metrics = dict(best.metrics)
    metrics["best_solver"] = best.solver_name
    metrics["metadata"] = metadata
    metrics["planned_summary"] = overall_summary(exams, timeslots)
    with (output / "metrics_summary.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    department_summary(exams).to_csv(output / "department_summary.csv", index=False)
    top_exams(exams).to_csv(output / "top_exams.csv", index=False)
    timeslot_summary(best.assignment, exams, timeslots, config, "optimized").to_csv(output / "optimized_timeslot_summary.csv", index=False)
    if reference_assignment:
        from comparison import compare_metrics, compare_timeslots
        from evaluation import evaluate_schedule

        reference_metrics = evaluate_schedule(reference_assignment, exams, students, timeslots, config)
        compare_metrics(reference_metrics, best.metrics).to_csv(output / "planned_vs_optimized_metrics.csv", index=False)
        compare_timeslots(reference_metrics, best.metrics, timeslots).to_csv(output / "planned_vs_optimized_timeslots.csv", index=False)
        timeslot_summary(reference_assignment, exams, timeslots, config, "planned").to_csv(output / "planned_timeslot_summary.csv", index=False)
        department_timeslot_concentration(reference_assignment, exams, "planned").to_csv(output / "planned_department_timeslot_concentration.csv", index=False)
    department_timeslot_concentration(best.assignment, exams, "optimized").to_csv(output / "optimized_department_timeslot_concentration.csv", index=False)

    generate_figures(best, output, results)
    print(f"En iyi cozum: {best.solver_name}. Ciktilar: {output}")


if __name__ == "__main__":
    main()
