from __future__ import annotations

import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd





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


def _default_end_datetime(date_values: pd.Series, start_values: pd.Series, hours: int = 2) -> pd.Series:
    combined = pd.to_datetime(_normalize_date_series(date_values) + " " + start_values.astype(str), errors="coerce", format="mixed")
    return combined + pd.to_timedelta(hours, unit="h")


def _temiz_str(seri: pd.Series, varsayilan: str = "") -> pd.Series:
    return seri.fillna(varsayilan).astype(str).str.strip()


def _normalize_date_series(seri: pd.Series) -> pd.Series:
    def normalize(value):
        if pd.isna(value):
            return ""
        # Excel readers already convert date-formatted cells to timestamps.
        # Converting these to numbers first produces nanoseconds, not Excel days.
        if isinstance(value, (date, datetime, pd.Timestamp)):
            return value.strftime("%Y-%m-%d")
        text = str(value).strip()
        numeric = pd.to_numeric(text, errors="coerce")
        if pd.notna(numeric):
            # Bound serials before pandas scales them to nanoseconds. Even with
            # errors='coerce', huge floats can overflow under NumPy's raise mode.
            if not -81182 <= numeric < 132321:
                return text
            parsed = pd.to_datetime(numeric, unit="D", origin="1899-12-30", errors="coerce")
        else:
            is_iso = re.match(r"^\d{4}-\d{2}-\d{2}(?:$|[ T])", text) is not None
            parsed = pd.to_datetime(text, errors="coerce", dayfirst=not is_iso)
        return parsed.strftime("%Y-%m-%d") if pd.notna(parsed) else text

    return seri.map(normalize)


def load_problem(path, minutes=60, drop_invalid=False):
    """Keep rows intact; never merge distinct exam occurrences by course ID."""
    import numpy as np
    from .model import Problem
    raw = oku_tablo(path)
    data, mapping, _ = kolonlari_esle(raw, ["exam_id", "student_count", "date"], "schedule")
    if "start_time" not in data and "timeslot_id" in data:
        data["start_time"] = data["timeslot_id"]
    if "start_time" not in data:
        raise ValueError("Missing start_time / PLANLANAN_SAAT / SAAT column.")
    dates = _normalize_date_series(data["date"])
    times = data["start_time"].astype(str).str.strip()
    valid_times = times.str.fullmatch(r"(?:[01]?\d|2[0-3]):[0-5]\d(?::00)?")
    starts = pd.to_datetime(dates + " " + times, format="mixed", errors="coerce")
    counts = pd.to_numeric(data["student_count"], errors="coerce")
    ids = data["exam_id"].fillna("").astype(str).str.strip()
    valid = starts.notna() & valid_times & np.isfinite(counts) & counts.ge(0) & counts.mod(1).eq(0) & ids.ne("")
    rejected = (np.flatnonzero(~valid.to_numpy()) + 2).tolist()
    if rejected and not drop_invalid:
        raise ValueError(f"Invalid rows (header counted): {rejected[:20]}. Use --drop-invalid to explicitly exclude them.")
    data = data.loc[valid].copy()
    stamps = starts.loc[valid].to_numpy(dtype="datetime64[m]")
    slots, reference = np.unique(stamps, return_inverse=True)
    # Anonymized occurrence IDs prevent repeated course codes from collapsing exams.
    occurrence_ids = [f"EXAM_{i+1:05d}" for i in range(len(data))]
    problem = Problem(occurrence_ids, counts.loc[valid].to_numpy(dtype=np.int64), slots, reference, minutes)
    metadata = {"source_name": Path(path).name, "source_sheet": raw.attrs.get("source_sheet"),
                "input_rows": len(raw), "accepted_rows": len(data), "rejected_rows": rejected,
                "repeated_course_ids": int(ids.loc[valid].duplicated().sum()),
                "departments": int(data["department_id"].nunique()) if "department_id" in data else None,
                "column_mapping": mapping}
    return problem, metadata


