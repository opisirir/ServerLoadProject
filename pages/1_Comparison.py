import json
from server_profiles import DEFAULT_PROFILE, ASSUMPTION, build_server_config
from models import ServerConfig
from io import BytesIO
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from comparison_charts import aligned_curves, crop_day, daily_loads, hours_above, load_example, prepare_plan


st.set_page_config(page_title="Before / After Comparison", layout="wide")
st.title("Before / After Comparison")
st.caption("Compare scheduled and optimized exam loads over time. Exam enrollments are not unique student counts.")

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = Path.home() / "My Drive/Makale/Server Load"
COLORS = {"Before": "#D58038", "After": "#286CB0"}


@st.cache_data(show_spinner=False)
def example_data(stamps):
    return load_example(EXAMPLE_ROOT)


def draw(fig, filename):
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    st.download_button("Download chart as PNG", buf.getvalue(), filename, "image/png", key=filename)


def style_time_axis(ax):
    locator = mdates.AutoDateLocator(minticks=4, maxticks=10)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.set_xlabel("Date and time")
    ax.grid(axis="y", alpha=.2)
    ax.spines[["top", "right"]].set_visible(False)


with st.sidebar:
    st.page_link("app.py", label="Back to optimization")
    source = st.selectbox("Plans to compare", ["Provided CSV example", "Latest optimization"], index=1 if "comparison_plans" in st.session_state else 0)
    minutes = st.select_slider("Shared exam duration assumption (minutes)", options=[5, 10, 15, 30, 45, 60, 90, 120, 180], value=60)
    st.caption("The selected duration applies to both plans. This sensitivity scenario replaces the end times in the files.")

resource_config = build_server_config()
try:
    if source == "Provided CSV example":
        files = [EXAMPLE_ROOT / "HamVeriler/arasinavlar.xlsx", EXAMPLE_ROOT / "ExampleFiles/2/2026-06-29T10-55_export.csv", EXAMPLE_ROOT / "ExampleFiles/timeslots_program_ready.csv"]
        before, after, default_capacity = example_data(tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files))
        source_note = "Before: arasinavlar.xlsx / Page 1, raw records. After: 2026-06-29T10-55_export.csv. Capacity: timeslots_program_ready.csv."
        st.warning("This example moves a schedule spanning multiple days into one day and merges course codes. These charts do not verify timetable constraints or student conflicts.")
    elif "comparison_plans" in st.session_state:
        saved = st.session_state["comparison_plans"]
        before, after = prepare_plan(saved["before"]), prepare_plan(saved["after"])
        resource_config = build_server_config(saved.get("profile_id", DEFAULT_PROFILE))
        default_capacity = int(saved["capacity"])
        source_note = f"Latest optimization: {saved.get('source_name', 'current session')} · {saved.get('solver', 'saved result')}. Calculated from the records loaded and grouped by the application."
    else:
        folder = Path(st.session_state.get("comparison_output_dir", str(ROOT / "outputs_gui")))
        before = prepare_plan(pd.read_csv(folder / "planned_timeslot_summary.csv"))
        after = prepare_plan(pd.read_csv(folder / "optimized_timeslot_summary.csv"))
        profile_path = folder / "server_profile.json"
        if profile_path.exists():
            resource_config = ServerConfig(**json.loads(profile_path.read_text(encoding="utf-8"))["config"])
        else:
            st.warning("These older results have no saved server profile. Resource charts use the current default scenario; rerun optimization to apply it.")
        default_capacity = resource_config.max_concurrent_students
        source_note = f"Saved planned and optimized slot summaries: {folder.name}."
    st.caption(source_note)
except (OSError, ValueError, KeyError) as exc:
    st.info("Unable to read the selected plans. Choose another data source or run an optimization on the main page.")
    st.caption(str(exc))
    st.stop()

capacity = st.sidebar.number_input("Concurrent student capacity", min_value=1, value=default_capacity, step=100, key=f"comparison_capacity_{source}")
curves = aligned_curves(before, after, minutes)
daily = daily_loads(before, after)
if before.students.sum() != after.students.sum():
    st.error("Total exam enrollments differ between plans. A lower load cannot be attributed directly to optimization.")
st.info(f"These charts assume each exam lasts {minutes} minutes. Concurrent load includes exams with different start times whose durations overlap. These are model estimates, not measured server loads.")

a, b, c, d = st.columns(4)
a.metric("Before · total exam enrollments", f"{before.students.sum():,}")
b.metric("After · total exam enrollments", f"{after.students.sum():,}")
c.metric("Before · peak concurrent load", f"{curves['Before'].max():,}")
d.metric("After · peak concurrent load", f"{curves['After'].max():,}", delta=f"{curves['After'].max() - curves['Before'].max():+,}", delta_color="inverse")
st.caption(f"Number of dates: before {before.start.dt.date.nunique()}, after {after.start.dt.date.nunique()}. Summary metrics cover the full period.")

days = pd.date_range(curves.index.min().normalize(), curves.index.max().normalize(), freq="D")
day = st.selectbox("Time chart view", ["Full period"] + days.strftime("%Y-%m-%d").tolist())
shown = curves if day == "Full period" else crop_day(curves, day)
load_tab, daily_tab, peak_tab, resource_tab = st.tabs(["Concurrent load", "Daily distribution", "Peak load and capacity", "Resource model"])

with load_tab:
    fig, ax = plt.subplots(figsize=(12, 4.5))
    for name in COLORS:
        ax.step(shown.index, shown[name], where="post", label=name, color=COLORS[name], linewidth=1.7)
    ax.axhline(capacity, color="#AD3340", linestyle="--", label=f"Capacity: {capacity:,}")
    ax.set(title=f"Concurrent load · {minutes} minute assumption · {day}", ylabel="Active exam enrollments", ylim=(0, None))
    ax.legend(loc="upper right")
    style_time_axis(ax)
    draw(fig, f"concurrent_load_{minutes}min_{day}.png")

with daily_tab:
    st.caption("Daily totals sum enrollments for exams starting on that day; they are not peak concurrent loads. The full period is shown.")
    fig, ax = plt.subplots(figsize=(12, 4.5))
    x = range(len(daily))
    ax.bar([i-.2 for i in x], daily['Before'], width=.4, color=COLORS['Before'], label="Before")
    ax.bar([i+.2 for i in x], daily['After'], width=.4, color=COLORS['After'], label="After")
    ax.set_xticks(list(x)); ax.set_xticklabels(daily.index.strftime("%d.%m.%Y"), rotation=60, ha="right")
    ax.set(title="Exam enrollments by date", ylabel="Total exam enrollments")
    ax.grid(axis="y", alpha=.2); ax.legend()
    draw(fig, "daily_load_comparison.png")

with peak_tab:
    peaks = curves.max()
    fig, ax = plt.subplots(figsize=(9, 4))
    bars = ax.bar(list(COLORS), [peaks[n] for n in COLORS], color=list(COLORS.values()), width=.5)
    ax.bar_label(bars, fmt="%.0f", padding=5)
    ax.axhline(capacity, linestyle="--", color="#AD3340", label=f"Capacity: {capacity:,}")
    ax.set_ylim(0, max(capacity, peaks.max())*1.2)
    ax.set(title=f"Peak concurrent load · {minutes} minute assumption", ylabel="Active exam enrollments")
    ax.legend(); ax.grid(axis="y", alpha=.2)
    draw(fig, f"peak_load_{minutes}min.png")
    st.dataframe(pd.DataFrame({"Plan":list(COLORS),"Peak load":[int(peaks[n]) for n in COLORS],"Time above capacity (hours)":[round(hours_above(curves[n],capacity),2) for n in COLORS]}), hide_index=True, use_container_width=True)

with resource_tab:
    st.caption(ASSUMPTION)
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    for ax, (label, rate) in zip(axes, [("CPU (vCPU)", resource_config.cpu_per_student), ("RAM (GB)", resource_config.ram_per_student), ("Bandwidth (Mbps)", resource_config.bandwidth_per_student)]):
        for name in COLORS:
            ax.step(shown.index, shown[name]*rate, where="post", color=COLORS[name], label=name)
        ax.set_ylabel(label); ax.set_ylim(bottom=0); style_time_axis(ax)
    axes[0].legend(); axes[0].set_title(f"Resource load model · {minutes} minute assumption · {day}")
    draw(fig, f"resource_model_{minutes}min_{day}.png")

with st.expander("Chart data and calculation"):
    st.write("Enrollments are added at each start and removed after the selected duration. Simultaneous starts and ends are processed together. Intervals crossing midnight are preserved. The date selection filters only the time charts.")
    st.dataframe(curves.rename_axis("Date and time").reset_index(), hide_index=True, use_container_width=True)
    st.download_button("Download calculated loads as CSV", curves.rename_axis("timestamp").to_csv().encode("utf-8-sig"), f"comparison_{minutes}min.csv", "text/csv")
