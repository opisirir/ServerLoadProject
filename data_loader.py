from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from config import VARSAYILAN_CONFIG
from models import Exam, ServerConfig, Student, Timeslot


ALAN_ESLESMELERI: Dict[str, List[str]] = {
    "student_id": ["ogrenci no", "ogrenci_no", "ogrenci", "student", "student_id", "student no", "number", "id"],
    "exam_id": ["sinav", "ders id", "ders_id", "ders kodu", "ders_kodu", "ders_kod", "ders_kod_6477", "sube_ders_kod", "sube_ders_kod_6477", "exam", "exam_id", "course", "course_code", "kod"],
    "exam_name": ["sinav adi", "sinav_adi", "ders adi", "ders_adi", "ders_ad", "ders_ad_6477", "exam_name", "name", "course_name"],
    "department_id": ["bolum", "bolum_id", "bolum adi", "department", "department_id", "department_name", "program", "prog_ad", "prog_ad_6477", "fak_ad", "fak_ad_6477"],
    "student_count": ["ogrenci sayisi", "ogrenci_sayisi", "ogr_say", "ogr_say_6477", "student_count", "count", "sayi", "enrollment"],
    "timeslot_id": ["saat", "slot", "zaman dilimi", "zaman_dilimi", "timeslot", "timeslot_id", "time_slot"],
    "date": ["tarih", "tarih_6477", "date", "gun", "day"],
    "start_time": ["baslangic", "baslangic saati", "planlanan_saat", "planlanan saat", "saat", "saat_6477", "start_time", "start", "begin"],
    "end_time": ["bitis", "bitis saati", "end_time", "end", "finish"],
    "capacity": ["capacity", "kapasite", "kontenjan"],
    "max_cpu": ["max_cpu", "cpu", "cpu_limit"],
    "max_ram": ["max_ram", "ram", "ram_limit", "memory"],
    "max_bandwidth": ["max_bandwidth", "bandwidth", "bw", "internet"],
    "max_concurrent_students": ["max_concurrent_students", "concurrent", "es_zamanli_ogrenci", "max_students"],
}


def normalize_column_name(ad: str) -> str:
    text = str(ad).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c")
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


def _alias_set(aliases: Iterable[str]) -> set:
    return {normalize_column_name(alias) for alias in aliases}


STANDART_ALIASLAR = {alan: _alias_set([alan, *aliases]) for alan, aliases in ALAN_ESLESMELERI.items()}


def oku_tablo(dosya_yolu: str | Path) -> pd.DataFrame:
    path = Path(dosya_yolu)
    if not path.exists():
        raise FileNotFoundError(f"Veri dosyasi bulunamadi: {path}")

    uzanti = path.suffix.lower()
    if uzanti == ".csv":
        return pd.read_csv(path)
    if uzanti in {".xlsx", ".xls"}:
        return _oku_excel_en_uygun_sayfa(path)
    if uzanti == ".json":
        with path.open("r", encoding="utf-8") as f:
            veri = json.load(f)
        if isinstance(veri, dict):
            for value in veri.values():
                if isinstance(value, list):
                    return pd.DataFrame(value)
        return pd.DataFrame(veri)
    raise ValueError(f"Desteklenmeyen dosya formati: {path.suffix}. Beklenen: CSV, XLSX veya JSON.")


def _kolon_skoru(columns: Iterable[str]) -> int:
    skor = 0
    normalized = {normalize_column_name(col) for col in columns}
    for aliases in STANDART_ALIASLAR.values():
        if normalized.intersection(aliases):
            skor += 1
    return skor


def _oku_excel_en_uygun_sayfa(path: Path) -> pd.DataFrame:
    sheets = pd.read_excel(path, sheet_name=None)
    if not sheets:
        raise ValueError(f"Excel dosyasinda okunabilir sayfa yok: {path}")
    adaylar = []
    for sheet_name, df in sheets.items():
        df = df.dropna(how="all").dropna(axis=1, how="all")
        score = _kolon_skoru(df.columns)
        bonus = 3 if normalize_column_name(sheet_name) in {"page_1", "detayli_gorunum_30dk", "detayli_gorunum_60dk"} else 0
        adaylar.append((score + bonus, score, sheet_name, df))
    adaylar.sort(key=lambda item: (item[0], item[1], len(item[3])), reverse=True)
    best_total, best_score, best_sheet, best_df = adaylar[0]
    if best_score == 0:
        sayfalar = ", ".join(str(name) for _, _, name, _ in adaylar)
        raise ValueError(f"{path.name} icinde beklenen kolonlara benzeyen bir Excel sayfasi bulunamadi. Sayfalar: {sayfalar}")
    best_df.attrs["source_sheet"] = best_sheet
    return best_df.reset_index(drop=True)


def kolonlari_esle(df: pd.DataFrame, gerekli_alanlar: Iterable[str], dosya_tipi: str, strict: bool = True) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
    mapping: Dict[str, str] = {}
    kullanilan = set()
    normalized_cols = {col: normalize_column_name(col) for col in df.columns}

    for standart, aliases in STANDART_ALIASLAR.items():
        for col, normalized in normalized_cols.items():
            if col in kullanilan:
                continue
            if normalized in aliases:
                mapping[col] = standart
                kullanilan.add(col)
                break

    eslesmis = df.rename(columns=mapping).copy()
    eksik = [alan for alan in gerekli_alanlar if alan not in eslesmis.columns]
    if eksik and strict:
        mevcut = ", ".join(map(str, df.columns))
        beklenen = ", ".join(gerekli_alanlar)
        raise ValueError(
            f"{dosya_tipi} dosyasinda gerekli kolonlar algilanamadi: {eksik}. "
            f"Beklenen standart alanlar: {beklenen}. Mevcut kolonlar: {mevcut}."
        )
    return eslesmis, mapping, eksik


def _default_end_time(date_values: pd.Series, start_values: pd.Series, hours: int = 2) -> pd.Series:
    combined = pd.to_datetime(date_values.astype(str) + " " + start_values.astype(str), errors="coerce", dayfirst=True)
    ended = combined + pd.to_timedelta(hours, unit="h")
    return ended.dt.strftime("%H:%M").fillna("")


def _temiz_str(seri: pd.Series, varsayilan: str = "") -> pd.Series:
    return seri.fillna(varsayilan).astype(str).str.strip()


def _normalize_date_series(seri: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(seri, errors="coerce")
    parsed_numeric = pd.to_datetime(numeric, unit="D", origin="1899-12-30", errors="coerce")
    parsed_text = pd.to_datetime(seri.astype(str), errors="coerce", dayfirst=True)
    parsed = parsed_numeric.fillna(parsed_text)
    fallback = _temiz_str(seri)
    return parsed.dt.strftime("%Y-%m-%d").fillna(fallback)


def _derive_timeslots_from_plan(sinav_df: pd.DataFrame, config: ServerConfig) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
    if "date" not in sinav_df.columns or "start_time" not in sinav_df.columns:
        raise ValueError("Planned schedule dosyasinda TARIH/date ve PLANLANAN_SAAT/start_time kolonlari gerekli.")

    slot_df = sinav_df[["date", "start_time"]].copy()
    slot_df["date"] = _normalize_date_series(slot_df["date"])
    slot_df["start_time"] = _temiz_str(slot_df["start_time"])
    slot_df = slot_df.drop_duplicates().sort_values(["date", "start_time"]).reset_index(drop=True)
    slot_df["timeslot_id"] = ["TS" + str(i + 1).zfill(4) for i in range(len(slot_df))]
    slot_df["end_time"] = _default_end_time(slot_df["date"], slot_df["start_time"])
    slot_df["capacity"] = config.max_concurrent_students
    slot_df["max_cpu"] = config.max_cpu
    slot_df["max_ram"] = config.max_ram
    slot_df["max_bandwidth"] = config.max_bandwidth
    slot_df["max_concurrent_students"] = config.max_concurrent_students
    return slot_df, {"derived_from": "planned_schedule"}, []


def _aggregate_kayit_df_from_sinav_df(sinav_df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "student_id": ["AGG_" + str(i) for i in range(len(sinav_df))],
            "exam_id": _temiz_str(sinav_df["exam_id"]),
            "department_id": _temiz_str(sinav_df.get("department_id", pd.Series(["UNKNOWN"] * len(sinav_df))), "UNKNOWN"),
        }
    )


def load_all_data(students_exams_path: str | None, exam_students_path: str, timeslots_path: str | None, server_config: ServerConfig | None = None):
    config = server_config or ServerConfig(
        cpu_per_student=VARSAYILAN_CONFIG.cpu_per_student,
        ram_per_student=VARSAYILAN_CONFIG.ram_per_student,
        bandwidth_per_student=VARSAYILAN_CONFIG.bandwidth_per_student,
        max_cpu=VARSAYILAN_CONFIG.max_cpu,
        max_ram=VARSAYILAN_CONFIG.max_ram,
        max_bandwidth=VARSAYILAN_CONFIG.max_bandwidth,
        max_concurrent_students=VARSAYILAN_CONFIG.max_concurrent_students,
    )

    sinav_df, sinav_mapping, _ = kolonlari_esle(oku_tablo(exam_students_path), ["exam_id"], "exam_students")

    sinav_df["exam_id"] = _temiz_str(sinav_df["exam_id"])
    sinav_df["exam_name"] = _temiz_str(sinav_df.get("exam_name", sinav_df["exam_id"]))
    sinav_df["department_id"] = _temiz_str(sinav_df.get("department_id", pd.Series(["UNKNOWN"] * len(sinav_df))), "UNKNOWN")
    if "start_time" not in sinav_df.columns and "timeslot_id" in sinav_df.columns:
        sinav_df["start_time"] = sinav_df["timeslot_id"]
    if "date" in sinav_df.columns:
        sinav_df["date"] = _normalize_date_series(sinav_df["date"])

    if "student_count" in sinav_df.columns:
        sinav_df["student_count"] = pd.to_numeric(sinav_df["student_count"], errors="coerce").fillna(0).astype(int)
    else:
        raise ValueError("exam_students dosyasinda student_count algilanamadi. Ders bazli optimizasyon icin exam_id ve student_count zorunludur.")

    if timeslots_path:
        slot_df, slot_mapping, slot_eksik = kolonlari_esle(oku_tablo(timeslots_path), ["date", "start_time"], "timeslots", strict=False)
        if "start_time" not in slot_df.columns and "timeslot_id" in slot_df.columns:
            slot_df["start_time"] = slot_df["timeslot_id"]
            slot_eksik = [alan for alan in slot_eksik if alan != "start_time"]
        if "date" not in slot_df.columns or "start_time" not in slot_df.columns:
            mevcut = ", ".join(map(str, slot_df.columns))
            raise ValueError(f"timeslots dosyasinda date/start_time algilanamadi. Mevcut kolonlar: {mevcut}")
    else:
        slot_df, slot_mapping, slot_eksik = _derive_timeslots_from_plan(sinav_df, config)

    kayit_mapping: Dict[str, str] = {}
    kayit_eksik: List[str] = []
    aggregate_student_mode = True
    if students_exams_path:
        kayit_df, kayit_mapping, kayit_eksik = kolonlari_esle(oku_tablo(students_exams_path), ["exam_id"], "students_exams", strict=False)
        if "exam_id" not in kayit_df.columns:
            kayit_df = _aggregate_kayit_df_from_sinav_df(sinav_df)
        else:
            has_real_students = "student_id" in kayit_df.columns and not kayit_df["student_id"].fillna("").astype(str).str.strip().eq("").all()
            aggregate_student_mode = not has_real_students
            if aggregate_student_mode:
                kayit_df["student_id"] = ["AGG_" + str(i) for i in range(len(kayit_df))]
            kayit_df["student_id"] = _temiz_str(kayit_df["student_id"])
            kayit_df["exam_id"] = _temiz_str(kayit_df["exam_id"])
            kayit_df["department_id"] = _temiz_str(kayit_df.get("department_id", pd.Series(["UNKNOWN"] * len(kayit_df))), "UNKNOWN")
    else:
        kayit_df = _aggregate_kayit_df_from_sinav_df(sinav_df)

    sinav_agg = {
        "exam_name": ("exam_name", "first"),
        "department_id": ("department_id", "first"),
        "student_count": ("student_count", "sum"),
    }
    if "date" in sinav_df.columns:
        sinav_df["date"] = _temiz_str(sinav_df["date"])
        sinav_agg["date"] = ("date", "first")
    if "start_time" in sinav_df.columns:
        sinav_df["start_time"] = _temiz_str(sinav_df["start_time"])
        sinav_agg["start_time"] = ("start_time", "first")
    if "timeslot_id" in sinav_df.columns:
        sinav_df["timeslot_id"] = _temiz_str(sinav_df["timeslot_id"])
        sinav_agg["timeslot_id"] = ("timeslot_id", "first")
    sinav_df = sinav_df.groupby("exam_id", as_index=False).agg(**sinav_agg)

    kayittan_sinavlar = set(kayit_df["exam_id"].dropna())
    eksik_sinavlar = kayittan_sinavlar - set(sinav_df["exam_id"])
    if eksik_sinavlar:
        ekler = pd.DataFrame({"exam_id": sorted(eksik_sinavlar)})
        ekler["exam_name"] = ekler["exam_id"]
        ekler["department_id"] = "UNKNOWN"
        ekler["student_count"] = ekler["exam_id"].map(kayit_df.groupby("exam_id")["student_id"].nunique()).fillna(0).astype(int)
        sinav_df = pd.concat([sinav_df, ekler], ignore_index=True)

    if "timeslot_id" not in slot_df.columns:
        slot_df["timeslot_id"] = _temiz_str(slot_df["date"]) + "_" + _temiz_str(slot_df["start_time"])
    if "end_time" not in slot_df.columns:
        slot_df["end_time"] = _default_end_time(slot_df["date"], slot_df["start_time"])
    slot_df = slot_df.drop_duplicates(subset=["timeslot_id", "date", "start_time"])
    slot_df["timeslot_id"] = _temiz_str(slot_df["timeslot_id"])
    slot_df["date"] = _normalize_date_series(slot_df["date"])
    slot_df["start_time"] = _temiz_str(slot_df["start_time"])
    slot_df["end_time"] = _temiz_str(slot_df["end_time"])
    if slot_df["timeslot_id"].duplicated().any():
        slot_df["timeslot_id"] = slot_df["date"] + "_" + slot_df["start_time"]

    defaults = {
        "capacity": config.max_concurrent_students,
        "max_cpu": config.max_cpu,
        "max_ram": config.max_ram,
        "max_bandwidth": config.max_bandwidth,
        "max_concurrent_students": config.max_concurrent_students,
    }
    for col, value in defaults.items():
        if col not in slot_df.columns:
            slot_df[col] = value
        slot_df[col] = pd.to_numeric(slot_df[col], errors="coerce").fillna(value)

    slot_df = slot_df.sort_values(["date", "start_time", "end_time"]).reset_index(drop=True)

    exams = {
        row.exam_id: Exam(str(row.exam_id), str(row.exam_name or row.exam_id), int(row.student_count), str(row.department_id or "UNKNOWN"))
        for row in sinav_df.drop_duplicates("exam_id").itertuples(index=False)
    }
    students = {}
    if not aggregate_student_mode:
        for sid, grup in kayit_df.groupby("student_id"):
            students[str(sid)] = Student(str(sid), sorted(set(map(str, grup["exam_id"]))), str(grup["department_id"].dropna().iloc[0] or "UNKNOWN"))

    timeslots = {
        row.timeslot_id: Timeslot(
            timeslot_id=str(row.timeslot_id),
            date=str(row.date),
            start_time=str(row.start_time),
            end_time=str(row.end_time),
            capacity=int(row.capacity),
            max_cpu=float(row.max_cpu),
            max_ram=float(row.max_ram),
            max_bandwidth=float(row.max_bandwidth),
            max_concurrent_students=int(row.max_concurrent_students),
            order_index=i,
        )
        for i, row in enumerate(slot_df.itertuples(index=False))
    }

    metadata = {
        "column_mappings": {"students_exams": kayit_mapping, "exam_students": sinav_mapping, "timeslots": slot_mapping},
        "missing_columns_filled": {"students_exams": kayit_eksik, "timeslots": slot_eksik},
        "aggregate_student_mode": aggregate_student_mode,
    }
    return kayit_df, sinav_df, slot_df, exams, students, timeslots, config, metadata
