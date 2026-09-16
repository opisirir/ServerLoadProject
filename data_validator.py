from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def validate_data(kayit_df: pd.DataFrame, sinav_df: pd.DataFrame, slot_df: pd.DataFrame, output_dir: str | Path) -> dict:
    rapor = {"warnings": [], "errors": [], "summary": {}}

    rapor["summary"]["students_exam_rows"] = int(len(kayit_df))
    rapor["summary"]["exam_rows"] = int(len(sinav_df))
    rapor["summary"]["timeslot_rows"] = int(len(slot_df))
    aggregate_student_mode = "student_id" not in kayit_df.columns or bool(len(kayit_df) and kayit_df["student_id"].astype(str).str.startswith("AGG_").all())
    if aggregate_student_mode:
        rapor["summary"]["mode"] = "course_student_count"
    else:
        rapor["summary"]["mode"] = "student_exam_records"

    if not aggregate_student_mode:
        dup = int(kayit_df.duplicated(subset=["student_id", "exam_id"]).sum())
        if dup:
            rapor["warnings"].append(f"Duplicate student-exam kaydi: {dup}")

    for col in ["exam_id", "student_count"]:
        if col not in sinav_df.columns:
            rapor["errors"].append(f"exam_students icinde eksik kolon: {col}")
        else:
            eksik = int(sinav_df[col].isna().sum() + (sinav_df[col].astype(str).str.strip() == "").sum())
            if eksik:
                rapor["errors"].append(f"exam_students icinde eksik {col}: {eksik}")

    if "student_count" in sinav_df.columns:
        invalid_counts = int((pd.to_numeric(sinav_df["student_count"], errors="coerce") <= 0).fillna(True).sum())
        if invalid_counts:
            rapor["errors"].append(f"exam_students icinde gecersiz student_count: {invalid_counts}")

    for col in ["timeslot_id", "date", "start_time", "end_time"]:
        eksik = int(slot_df[col].isna().sum() + (slot_df[col].astype(str).str.strip() == "").sum())
        if eksik:
            rapor["errors"].append(f"timeslots icinde eksik {col}: {eksik}")

    if "student_count" in sinav_df.columns and not aggregate_student_mode:
        gercek = kayit_df.groupby("exam_id")["student_id"].nunique()
        for row in sinav_df.itertuples(index=False):
            exam_id = str(row.exam_id)
            beklenen = int(getattr(row, "student_count", 0))
            bulunan = int(gercek.get(exam_id, 0))
            if beklenen and bulunan and abs(beklenen - bulunan) > max(2, beklenen * 0.05):
                rapor["warnings"].append(f"{exam_id} student_count tutarsiz: dosya={beklenen}, kayit={bulunan}")

    parsed_start = pd.to_datetime(slot_df["date"].astype(str) + " " + slot_df["start_time"].astype(str), errors="coerce")
    end_dates = slot_df["end_date"] if "end_date" in slot_df.columns else slot_df["date"]
    parsed_end = pd.to_datetime(end_dates.astype(str) + " " + slot_df["end_time"].astype(str), errors="coerce")
    if parsed_start.isna().any() or parsed_end.isna().any():
        rapor["warnings"].append("Bazi timeslot tarih/saat degerleri parse edilemedi.")
    if (parsed_end <= parsed_start).fillna(False).any():
        rapor["errors"].append("Bitis saati baslangic saatinden once veya esit olan timeslot var.")

    for col in ["capacity", "max_cpu", "max_ram", "max_bandwidth", "max_concurrent_students"]:
        if col in slot_df.columns and (pd.to_numeric(slot_df[col], errors="coerce") <= 0).fillna(True).any():
            rapor["errors"].append(f"Mantiksiz kapasite degeri var: {col}")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "validation_report.json").open("w", encoding="utf-8") as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)
    return rapor
