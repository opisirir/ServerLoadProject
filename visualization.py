from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

import matplotlib.pyplot as plt

from models import ScheduleResult


def _bar(data: Dict, title: str, ylabel: str, path: Path):
    plt.figure(figsize=(10, 5))
    plt.bar(list(data.keys()), list(data.values()))
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=140)
    plt.close()


def generate_figures(result: ScheduleResult, output_dir: str | Path, all_results: Iterable[ScheduleResult] | None = None):
    fig_dir = Path(output_dir) / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    metrics = result.metrics

    _bar(metrics.get("exam_count_per_timeslot", {}), "Timeslot Basina Sinav Sayisi", "Sinav", fig_dir / "exam_count_per_timeslot.png")
    _bar(metrics.get("concurrent_students_per_timeslot", {}), "Timeslot Basina Ogrenci Sayisi", "Ogrenci", fig_dir / "students_per_timeslot.png")
    _bar(metrics.get("cpu_usage_per_timeslot", {}), "CPU Kullanimi", "CPU", fig_dir / "cpu_usage.png")
    _bar(metrics.get("ram_usage_per_timeslot", {}), "RAM Kullanimi", "RAM", fig_dir / "ram_usage.png")
    _bar(metrics.get("bandwidth_usage_per_timeslot", {}), "Bandwidth Kullanimi", "Bandwidth", fig_dir / "bandwidth_usage.png")

    plt.figure(figsize=(10, 5))
    plt.plot(list(metrics.get("concurrent_students_per_timeslot", {}).values()), marker="o")
    plt.title("Load Variance Grafigi")
    plt.ylabel("Ogrenci Yuk")
    plt.tight_layout()
    plt.savefig(fig_dir / "load_variance.png", dpi=140)
    plt.close()

    if result.history:
        plt.figure(figsize=(10, 5))
        plt.plot(result.history)
        plt.title(f"{result.solver_name.upper()} Objective Curve")
        plt.ylabel("Objective")
        plt.xlabel("Iteration")
        plt.tight_layout()
        name = "ga_convergence_curve.png" if result.solver_name == "ga" else "sa_objective_curve.png"
        if result.solver_name == "hybrid":
            name = "hybrid_objective_curve.png"
        plt.savefig(fig_dir / name, dpi=140)
        plt.close()

    if all_results:
        values = {r.solver_name: r.objective_value for r in all_results if r.metrics}
        if values:
            _bar(values, "Algoritma Karsilastirma Grafigi", "Objective", fig_dir / "algorithm_comparison.png")

