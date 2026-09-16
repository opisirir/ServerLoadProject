"""Before/after load calculations, retaining overlapping exam intervals."""
from pathlib import Path

import numpy as np
import pandas as pd

from data_loader import _normalize_date_series, kolonlari_esle, oku_tablo


def prepare_plan(frame: pd.DataFrame) -> pd.DataFrame:
    data, _, _ = kolonlari_esle(frame, ["student_count", "date"], "comparison")
    if "start_time" not in data and "timeslot_id" in data:
        data["start_time"] = data["timeslot_id"]
    if "start_time" not in data:
        raise ValueError("Başlangıç saati bulunamadı.")
    counts = pd.to_numeric(data["student_count"], errors="coerce")
    dates = _normalize_date_series(data["date"])
    starts = pd.to_datetime(dates + " " + data["start_time"].astype(str).str.strip(), format="mixed", errors="coerce")
    if starts.isna().any() or (~np.isfinite(counts) | counts.lt(0) | counts.mod(1).ne(0)).any():
        raise ValueError("Karşılaştırma verisinde geçersiz tarih, saat veya öğrenci sayısı var.")
    if data.empty or counts.sum() <= 0:
        raise ValueError("Karşılaştırma için pozitif yük içeren bir plan gerekli.")
    return pd.DataFrame({"start": starts, "students": counts.astype(int)}).reset_index(drop=True)


def concurrent_curve(plan: pd.DataFrame, minutes: int) -> pd.Series:
    if minutes <= 0:
        raise ValueError("Süre sıfırdan büyük olmalı.")
    starts = pd.Series(plan.students.to_numpy(), index=pd.DatetimeIndex(plan.start))
    ends = pd.Series(-plan.students.to_numpy(), index=pd.DatetimeIndex(plan.start + pd.Timedelta(minutes=minutes)))
    # Net simultaneous starts/ends implement half-open [start, end) intervals.
    return pd.concat([starts, ends]).groupby(level=0).sum().sort_index().cumsum()


def aligned_curves(before: pd.DataFrame, after: pd.DataFrame, minutes: int) -> pd.DataFrame:
    a, b = concurrent_curve(before, minutes), concurrent_curve(after, minutes)
    grid = a.index.union(b.index).sort_values()
    return pd.DataFrame({"Önce": a.reindex(grid).ffill().fillna(0), "Sonra": b.reindex(grid).ffill().fillna(0)}).astype(int)


def daily_loads(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    def daily(plan):
        return plan.groupby(plan.start.dt.normalize()).students.sum()
    return pd.concat([daily(before).rename("Önce"), daily(after).rename("Sonra")], axis=1).fillna(0).sort_index().astype(int)


def hours_above(curve: pd.Series, capacity: int) -> float:
    durations = curve.index.to_series().shift(-1).sub(curve.index.to_series()).dt.total_seconds().fillna(0) / 3600
    return float(durations[curve.to_numpy() > capacity].sum())


def crop_day(curves: pd.DataFrame, day: str) -> pd.DataFrame:
    start = pd.Timestamp(day)
    end = start + pd.Timedelta(days=1)
    # Preserve the carried load at midnight, even without an event that day.
    grid = curves.index.union(pd.DatetimeIndex([start, end])).sort_values()
    expanded = curves.reindex(grid).ffill().fillna(0)
    return expanded.loc[(expanded.index >= start) & (expanded.index <= end)]


def load_example(root: Path):
    raw = root / "HamVeriler/arasinavlar.xlsx"
    result = root / "ExampleFiles/2/2026-06-29T10-55_export.csv"
    slots = root / "ExampleFiles/timeslots_program_ready.csv"
    return prepare_plan(oku_tablo(raw)), prepare_plan(pd.read_csv(result)), int(pd.read_csv(slots).max_concurrent_students.min())
