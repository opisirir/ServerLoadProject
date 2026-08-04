from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from comparison import compare_metrics, compare_timeslots, evaluate_reference_schedule
from config import VARSAYILAN_CONFIG
from data_loader import load_all_data
from data_validator import validate_data
from genetic_algorithm import GeneticAlgorithmSolver
from graph_algorithm_solver import GraphAlgorithmSolver
from hybrid_solver import HybridSolver
from main import schedule_dataframe
from models import ServerConfig
from simulated_annealing import SimulatedAnnealingSolver
from statistics_report import department_summary, department_timeslot_concentration, overall_summary, timeslot_summary, top_exams
from visualization import generate_figures


st.set_page_config(page_title="Exam Timetabling Optimizer", layout="wide")
st.title("Exam Timetabling Optimizer")

with st.sidebar:
    solver_name = st.selectbox("Solver", ["all", "hybrid", "graph", "ga", "sa"])
    output_dir = st.text_input("Output folder", "outputs_gui")
    seed = st.number_input("Random seed", min_value=0, value=VARSAYILAN_CONFIG.random_seed)
    population_size = st.number_input("GA population", min_value=10, value=80)
    ga_generations = st.number_input("GA generations", min_value=10, value=250)
    max_iterations = st.number_input("SA iterations", min_value=100, value=3000)

planned_file = st.file_uploader("planned exam schedule", type=["csv", "xlsx", "xls", "json"])


def _save_upload(uploaded, folder: Path) -> str:
    path = folder / uploaded.name
    path.write_bytes(uploaded.getbuffer())
    return str(path)


def _make_solver():
    if solver_name == "graph":
        return GraphAlgorithmSolver()
    if solver_name == "ga":
        return GeneticAlgorithmSolver(population_size=int(population_size), generations=int(ga_generations), seed=int(seed))
    if solver_name == "sa":
        return SimulatedAnnealingSolver(iterations=int(max_iterations), seed=int(seed))
    return HybridSolver(
        ga_kwargs={"population_size": int(population_size), "generations": int(ga_generations), "seed": int(seed)},
        sa_kwargs={"iterations": int(max_iterations), "seed": int(seed)},
    )


def _make_solver_by_name(name: str):
    if name == "graph":
        return GraphAlgorithmSolver()
    if name == "ga":
        return GeneticAlgorithmSolver(population_size=int(population_size), generations=int(ga_generations), seed=int(seed))
    if name == "sa":
        return SimulatedAnnealingSolver(iterations=int(max_iterations), seed=int(seed))
    if name == "hybrid":
        return HybridSolver(
            ga_kwargs={"population_size": int(population_size), "generations": int(ga_generations), "seed": int(seed)},
            sa_kwargs={"iterations": int(max_iterations), "seed": int(seed)},
        )
    raise ValueError(f"Unknown solver: {name}")


def _algorithm_results_df(results):
    rows = []
    successful = [result for result in results if result.metrics]
    best_objective = min((result.objective_value for result in successful), default=None)
    for result in results:
        metrics = result.metrics or {}
        rows.append(
            {
                "solver": result.solver_name,
                "success": bool(result.metrics),
                "feasible": bool(result.feasible),
                "is_best": best_objective is not None and result.objective_value == best_objective,
                "objective_value": result.objective_value,
                "hard_constraint_violations": metrics.get("hard_constraint_violations"),
                "total_soft_penalty": metrics.get("total_soft_penalty"),
                "load_variance": metrics.get("load_variance"),
                "max_load": metrics.get("max_load"),
                "runtime_seconds": result.runtime_seconds,
                "success_rate_pct": 100.0 if result.metrics and result.feasible else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values(["success", "feasible", "objective_value"], ascending=[False, False, True])


def _plot_algorithm_comparison(df: pd.DataFrame, value_col: str, title: str, ylabel: str):
    if df.empty or value_col not in df.columns:
        st.info("No algorithm comparison data available.")
        return
    shown = df.copy()
    shown[value_col] = pd.to_numeric(shown[value_col], errors="coerce").replace([float("inf"), -float("inf")], pd.NA).fillna(0)
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#2f7d32" if bool(row.is_best) else "#4f6f8f" for row in shown.itertuples()]
    ax.bar(shown["solver"], shown[value_col].fillna(0), color=colors)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def _plot_grouped_bar(df: pd.DataFrame, columns: list[str], title: str, ylabel: str):
    if df.empty:
        st.info("No data available for this chart.")
        return
    missing = [col for col in columns if col not in df.columns]
    if missing:
        st.warning(f"Missing chart columns: {', '.join(missing)}")
        return
    chart_df = df.copy()
    for col in columns:
        chart_df[col] = pd.to_numeric(chart_df[col], errors="coerce").fillna(0)
    labels = chart_df["timeslot_id"].astype(str).tolist()
    x = range(len(labels))
    width = 0.38
    fig, ax = plt.subplots(figsize=(12, 5))
    for idx, col in enumerate(columns):
        offsets = [value + (idx - (len(columns) - 1) / 2) * width for value in x]
        ax.bar(offsets, chart_df[col].tolist(), width=width, label=col.replace("_", " ").title())
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend()
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def _plot_metric_improvement(metric_df: pd.DataFrame):
    shown = metric_df.copy()
    shown["metric"] = shown["metric"].str.replace("_", " ").str.title()
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#2f7d32" if value >= 0 else "#b3261e" for value in shown["improvement_pct"]]
    ax.barh(shown["metric"], shown["improvement_pct"], color=colors)
    ax.axvline(0, color="#444", linewidth=1)
    ax.set_xlabel("Improvement (%)")
    ax.set_title("Optimization Improvement By Metric")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def _plot_simple_bar(df: pd.DataFrame, x_col: str, y_col: str, title: str, ylabel: str, limit: int = 15):
    if df.empty:
        st.info("No data available for this chart.")
        return
    shown = df.head(limit)
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(shown[x_col].astype(str), shown[y_col])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(range(len(shown)))
    ax.set_xticklabels(shown[x_col].astype(str), rotation=45, ha="right")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def _metric_card(label: str, value: float, delta: float | None = None, suffix: str = ""):
    shown_value = f"{value:,.2f}{suffix}" if isinstance(value, float) else f"{value}{suffix}"
    shown_delta = None if delta is None else f"{delta:,.2f}{suffix}"
    st.metric(label, shown_value, delta=shown_delta)


if st.button("Optimize", type="primary", disabled=not planned_file):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        planned_path = _save_upload(planned_file, tmp_path)

        config = ServerConfig(
            cpu_per_student=VARSAYILAN_CONFIG.cpu_per_student,
            ram_per_student=VARSAYILAN_CONFIG.ram_per_student,
            bandwidth_per_student=VARSAYILAN_CONFIG.bandwidth_per_student,
            max_cpu=VARSAYILAN_CONFIG.max_cpu,
            max_ram=VARSAYILAN_CONFIG.max_ram,
            max_bandwidth=VARSAYILAN_CONFIG.max_bandwidth,
            max_concurrent_students=VARSAYILAN_CONFIG.max_concurrent_students,
        )

        try:
            kayit_df, sinav_df, slot_df, exams, students, timeslots, config, _ = load_all_data(None, planned_path, None, config)
            validation = validate_data(kayit_df, sinav_df, slot_df, output_dir)
            if validation["errors"]:
                st.error("Validation errors: " + "; ".join(validation["errors"]))
            else:
                with st.spinner("Optimization running..."):
                    selected_solvers = ["graph", "ga", "sa", "hybrid"] if solver_name == "all" else [solver_name]
                    algorithm_results = []
                    for selected_solver in selected_solvers:
                        try:
                            algorithm_results.append(_make_solver_by_name(selected_solver).solve(exams, students, timeslots, config))
                        except Exception as exc:
                            algorithm_results.append(
                                SimpleNamespace(**{
                                    "solver_name": selected_solver,
                                    "assignment": {},
                                    "objective_value": float("inf"),
                                    "metrics": {},
                                    "runtime_seconds": 0.0,
                                    "feasible": False,
                                    "history": [],
                                    "message": str(exc),
                                })
                            )
                    successful_results = [item for item in algorithm_results if item.metrics]
                    if not successful_results:
                        raise RuntimeError("No algorithm produced a schedule. Check the uploaded file and solver parameters.")
                    result = min(successful_results, key=lambda item: item.objective_value)
                    schedule = schedule_dataframe(result, exams, timeslots, config)
                    reference_label, reference_assignment, reference_metrics = evaluate_reference_schedule(sinav_df, exams, students, timeslots, config)
                    metric_comparison = compare_metrics(reference_metrics, result.metrics) if reference_metrics else pd.DataFrame()
                    timeslot_comparison = compare_timeslots(reference_metrics, result.metrics, timeslots) if reference_metrics else pd.DataFrame()
                    output = Path(output_dir)
                    output.mkdir(parents=True, exist_ok=True)
                    schedule.to_csv(output / "schedule_output.csv", index=False)
                    pd.DataFrame([result.metrics]).to_csv(output / "results.csv", index=False)
                    algorithm_df = _algorithm_results_df(algorithm_results)
                    algorithm_df.to_csv(output / "algorithm_comparison.csv", index=False)
                    if not metric_comparison.empty:
                        metric_comparison.to_csv(output / "real_vs_optimized_metrics.csv", index=False)
                        timeslot_comparison.to_csv(output / "real_vs_optimized_timeslots.csv", index=False)
                    department_df = department_summary(exams)
                    top_exam_df = top_exams(exams)
                    planned_slot_df = timeslot_summary(reference_assignment, exams, timeslots, config, "planned") if reference_assignment else pd.DataFrame()
                    optimized_slot_df = timeslot_summary(result.assignment, exams, timeslots, config, "optimized")
                    planned_dept_slot_df = department_timeslot_concentration(reference_assignment, exams, "planned") if reference_assignment else pd.DataFrame()
                    optimized_dept_slot_df = department_timeslot_concentration(result.assignment, exams, "optimized")
                    department_df.to_csv(output / "department_summary.csv", index=False)
                    top_exam_df.to_csv(output / "top_exams.csv", index=False)
                    planned_slot_df.to_csv(output / "planned_timeslot_summary.csv", index=False)
                    optimized_slot_df.to_csv(output / "optimized_timeslot_summary.csv", index=False)
                    planned_dept_slot_df.to_csv(output / "planned_department_timeslot_concentration.csv", index=False)
                    optimized_dept_slot_df.to_csv(output / "optimized_department_timeslot_concentration.csv", index=False)
                    generate_figures(result, output, algorithm_results)

                st.success(f"Best objective: {result.objective_value:.2f} | Feasible: {result.feasible}")
                if reference_label == "real":
                    st.info("Comparison uses the real schedule reconstructed from date/start_time or timeslot_id columns.")
                elif reference_label == "baseline":
                    st.info("The uploaded files do not contain a real pre-optimization assignment, so comparison uses an automatically generated baseline schedule.")
                else:
                    st.warning("Reference schedule could not be built. Check timeslot and exam files.")

                overview_tab, algorithm_tab, load_tab, resource_tab, improvement_tab, stats_tab, schedule_tab, metrics_tab = st.tabs(
                    ["Overview", "Algorithms", "Load comparison", "Resource comparison", "Improvements", "Statistics", "Schedule", "Raw metrics"]
                )

                with overview_tab:
                    if reference_metrics:
                        c1, c2, c3, c4 = st.columns(4)
                        objective_delta = reference_metrics.get("objective_value", 0) - result.metrics.get("objective_value", 0)
                        variance_delta = reference_metrics.get("load_variance", 0) - result.metrics.get("load_variance", 0)
                        max_load_delta = reference_metrics.get("max_load", 0) - result.metrics.get("max_load", 0)
                        hard_delta = reference_metrics.get("hard_constraint_violations", 0) - result.metrics.get("hard_constraint_violations", 0)
                        with c1:
                            _metric_card("Objective", float(result.metrics.get("objective_value", 0)), objective_delta)
                        with c2:
                            _metric_card("Load variance", float(result.metrics.get("load_variance", 0)), variance_delta)
                        with c3:
                            _metric_card("Max load", float(result.metrics.get("max_load", 0)), max_load_delta)
                        with c4:
                            _metric_card("Hard violations", float(result.metrics.get("hard_constraint_violations", 0)), hard_delta)
                        st.dataframe(metric_comparison, use_container_width=True)
                    else:
                        st.json(result.metrics)

                with algorithm_tab:
                    st.subheader("Algorithm Success Comparison")
                    best_row = algorithm_df[algorithm_df["is_best"]].head(1)
                    if not best_row.empty:
                        winner = best_row.iloc[0]
                        st.success(f"Best algorithm for this file: {winner['solver']} | objective={winner['objective_value']:.2f} | feasible={winner['feasible']}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Algorithms run", len(algorithm_df))
                    c2.metric("Feasible solutions", int(algorithm_df["feasible"].sum()))
                    c3.metric("Success rate", f"{algorithm_df['success_rate_pct'].mean():.1f}%")
                    _plot_algorithm_comparison(algorithm_df, "objective_value", "Objective By Algorithm", "Objective")
                    _plot_algorithm_comparison(algorithm_df, "runtime_seconds", "Runtime By Algorithm", "Seconds")
                    _plot_algorithm_comparison(algorithm_df, "load_variance", "Load Variance By Algorithm", "Load variance")
                    st.dataframe(algorithm_df, use_container_width=True)

                with load_tab:
                    if reference_metrics:
                        _plot_grouped_bar(timeslot_comparison, ["reference_students", "optimized_students"], "Students Per Timeslot", "Students")
                        _plot_grouped_bar(timeslot_comparison, ["reference_exams", "optimized_exams"], "Exams Per Timeslot", "Exams")
                        st.dataframe(
                            timeslot_comparison[
                                ["timeslot_id", "date", "start_time", "reference_students", "optimized_students", "student_delta", "reference_exams", "optimized_exams", "exam_delta"]
                            ],
                            use_container_width=True,
                        )
                    else:
                        st.info("Reference schedule comparison is unavailable.")

                with resource_tab:
                    if reference_metrics:
                        cpu_tab, ram_tab, bandwidth_tab = st.tabs(["CPU", "RAM", "Bandwidth"])
                        with cpu_tab:
                            _plot_grouped_bar(timeslot_comparison, ["reference_cpu", "optimized_cpu"], "CPU Usage Per Timeslot", "CPU")
                        with ram_tab:
                            _plot_grouped_bar(timeslot_comparison, ["reference_ram", "optimized_ram"], "RAM Usage Per Timeslot", "RAM")
                        with bandwidth_tab:
                            _plot_grouped_bar(timeslot_comparison, ["reference_bandwidth", "optimized_bandwidth"], "Bandwidth Usage Per Timeslot", "Bandwidth")
                        st.dataframe(
                            timeslot_comparison[
                                ["timeslot_id", "reference_cpu", "optimized_cpu", "reference_ram", "optimized_ram", "reference_bandwidth", "optimized_bandwidth"]
                            ],
                            use_container_width=True,
                        )
                    else:
                        st.info("Resource comparison is unavailable.")

                with improvement_tab:
                    if reference_metrics:
                        _plot_metric_improvement(metric_comparison)
                        positive = metric_comparison[metric_comparison["improvement"] > 0].sort_values("improvement_pct", ascending=False)
                        negative = metric_comparison[metric_comparison["improvement"] < 0].sort_values("improvement_pct")
                        left, right = st.columns(2)
                        with left:
                            st.subheader("Improved")
                            st.dataframe(positive, use_container_width=True)
                        with right:
                            st.subheader("Regressed or traded off")
                            st.dataframe(negative, use_container_width=True)
                    else:
                        st.info("Improvement view needs a reference schedule.")

                with stats_tab:
                    summary = overall_summary(exams, timeslots)
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Exams", summary["exam_count"])
                    c2.metric("Departments", summary["department_count"])
                    c3.metric("Total students", summary["total_student_count"])
                    c4.metric("Timeslots", summary["timeslot_count"])

                    left, right = st.columns(2)
                    with left:
                        st.subheader("Departments by exam count")
                        _plot_simple_bar(department_df.sort_values("exam_count", ascending=False), "department_id", "exam_count", "Departments With Most Exams", "Exam count")
                        st.dataframe(department_df, use_container_width=True)
                    with right:
                        st.subheader("Departments by student count")
                        dept_students = department_df.sort_values("student_count", ascending=False)
                        _plot_simple_bar(dept_students, "department_id", "student_count", "Departments With Most Students", "Student count")
                        st.dataframe(dept_students, use_container_width=True)

                    st.subheader("Largest exams")
                    _plot_simple_bar(top_exam_df, "exam_id", "student_count", "Largest Exams By Student Count", "Student count")
                    st.dataframe(top_exam_df, use_container_width=True)

                    st.subheader("Department concentration by timeslot")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.caption("Planned")
                        st.dataframe(planned_dept_slot_df.head(50), use_container_width=True)
                    with col_b:
                        st.caption("Optimized")
                        st.dataframe(optimized_dept_slot_df.head(50), use_container_width=True)

                with schedule_tab:
                    st.dataframe(schedule, use_container_width=True)
                    if reference_assignment:
                        reference_rows = schedule.copy()
                        reference_rows["timeslot_id"] = reference_rows["exam_id"].map(reference_assignment)
                        title = "Real assignment mapping" if reference_label == "real" else "Baseline assignment mapping"
                        st.subheader(title)
                        st.dataframe(reference_rows[["exam_id", "exam_name", "department_id", "student_count", "timeslot_id"]], use_container_width=True)

                with metrics_tab:
                    st.subheader("Optimized metrics")
                    st.json(result.metrics)
                    if reference_metrics:
                        title = "Real metrics" if reference_label == "real" else "Baseline metrics"
                        st.subheader(title)
                        st.json(reference_metrics)
        except Exception as exc:
            st.exception(exc)
