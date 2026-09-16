from io import BytesIO
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from comparison_charts import aligned_curves, crop_day, daily_loads, hours_above, load_example, prepare_plan


st.set_page_config(page_title="Önce / Sonra Karşılaştırma", layout="wide")
st.title("Önce / Sonra Karşılaştırma")
st.caption("Planlanan ve optimize edilen sınavların zaman içindeki yükü. Öğrenci-sınav toplamları benzersiz öğrenci sayısı değildir.")

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ROOT = Path.home() / "My Drive/Makale/Server Load"
COLORS = {"Önce": "#D58038", "Sonra": "#286CB0"}


@st.cache_data(show_spinner=False)
def example_data(stamps):
    return load_example(EXAMPLE_ROOT)


def draw(fig, filename):
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    st.download_button("Grafiği PNG olarak indir", buf.getvalue(), filename, "image/png", key=filename)


def style_time_axis(ax):
    locator = mdates.AutoDateLocator(minticks=4, maxticks=10)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.set_xlabel("Tarih ve saat")
    ax.grid(axis="y", alpha=.2)
    ax.spines[["top", "right"]].set_visible(False)


with st.sidebar:
    st.page_link("app.py", label="Optimizasyona dön")
    source = st.selectbox("Karşılaştırılacak planlar", ["Gönderilen CSV örneği", "Son optimizasyon"], index=1 if "comparison_plans" in st.session_state else 0)
    minutes = st.select_slider("Ortak sınav süresi varsayımı (dakika)", options=[5, 10, 15, 30, 45, 60, 90, 120, 180], value=60)
    st.caption("Seçilen süre iki plana da uygulanır. Dosyalardaki bitiş saatlerinin yerine geçen bir duyarlılık senaryosudur.")

try:
    if source == "Gönderilen CSV örneği":
        files = [EXAMPLE_ROOT / "HamVeriler/arasinavlar.xlsx", EXAMPLE_ROOT / "ExampleFiles/2/2026-06-29T10-55_export.csv", EXAMPLE_ROOT / "ExampleFiles/timeslots_program_ready.csv"]
        before, after, default_capacity = example_data(tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files))
        source_note = "Önce: arasinavlar.xlsx / Page 1, ham kayıtlar. Sonra: 2026-06-29T10-55_export.csv. Kapasite: timeslots_program_ready.csv."
        st.warning("Bu örnekte çok günlük plan tek güne taşınmış ve ders kodları birleştirilmiştir. Grafikler takvim veya öğrenci çakışmalarının uygunluğunu onaylamaz.")
    elif "comparison_plans" in st.session_state:
        saved = st.session_state["comparison_plans"]
        before, after = prepare_plan(saved["before"]), prepare_plan(saved["after"])
        default_capacity = int(saved["capacity"])
        source_note = saved["label"]
    else:
        folder = Path(st.session_state.get("comparison_output_dir", str(ROOT / "outputs_gui")))
        before = prepare_plan(pd.read_csv(folder / "planned_timeslot_summary.csv"))
        after = prepare_plan(pd.read_csv(folder / "optimized_timeslot_summary.csv"))
        default_capacity = 5000
        source_note = f"Kaydedilmiş plan ve optimize slot özetleri: {folder.name}. Kapasite bilgisi kaydedilmediği için başlangıç değeri 5.000; gerekirse değiştirin."
    st.caption(source_note)
except (OSError, ValueError, KeyError) as exc:
    st.info("Seçilen planlar okunamadı. Diğer veri kaynağını seçin veya ana sayfada optimizasyon çalıştırın.")
    st.caption(str(exc))
    st.stop()

capacity = st.sidebar.number_input("Eşzamanlı öğrenci kapasitesi", min_value=1, value=default_capacity, step=100, key=f"comparison_capacity_{source}")
curves = aligned_curves(before, after, minutes)
daily = daily_loads(before, after)
if before.students.sum() != after.students.sum():
    st.error("Planların öğrenci-sınav toplamları farklı. Yük azalmasını doğrudan optimizasyon kazancı olarak yorumlamayın.")
st.info(f"Bu grafiklerde her sınav {minutes} dakika sürüyor varsayılır. Eşzamanlı yük, farklı saatlerde başlayıp süresi çakışan sınavları da içerir. Gerçek sunucu ölçümü değildir.")

a, b, c, d = st.columns(4)
a.metric("Önce · öğrenci-sınav toplamı", f"{before.students.sum():,}")
b.metric("Sonra · öğrenci-sınav toplamı", f"{after.students.sum():,}")
c.metric("Önce · eşzamanlı tepe", f"{curves['Önce'].max():,}")
d.metric("Sonra · eşzamanlı tepe", f"{curves['Sonra'].max():,}", delta=f"{curves['Sonra'].max() - curves['Önce'].max():+,}", delta_color="inverse")
st.caption(f"Tarih sayısı: önce {before.start.dt.date.nunique()}, sonra {after.start.dt.date.nunique()}. Özet göstergeleri tüm dönemi kapsar.")

days = pd.date_range(curves.index.min().normalize(), curves.index.max().normalize(), freq="D")
day = st.selectbox("Zaman grafikleri için görünüm", ["Tüm dönem"] + days.strftime("%Y-%m-%d").tolist())
shown = curves if day == "Tüm dönem" else crop_day(curves, day)
load_tab, daily_tab, peak_tab, resource_tab = st.tabs(["Eşzamanlı yük", "Günlük dağılım", "Tepe yük ve kapasite", "Kaynak modeli"])

with load_tab:
    fig, ax = plt.subplots(figsize=(12, 4.5))
    for name in COLORS:
        ax.step(shown.index, shown[name], where="post", label=name, color=COLORS[name], linewidth=1.7)
    ax.axhline(capacity, color="#AD3340", linestyle="--", label=f"Kapasite: {capacity:,}")
    ax.set(title=f"Eşzamanlı yük · {minutes} dakika varsayımı · {day}", ylabel="Aktif öğrenci-sınav sayısı", ylim=(0, None))
    ax.legend(loc="upper right")
    style_time_axis(ax)
    draw(fig, f"eszamanli_yuk_{minutes}dk_{day}.png")

with daily_tab:
    st.caption("Günlük toplam, o gün başlayan sınavların öğrenci sayılarını toplar; eşzamanlı tepe yük değildir. Tüm dönem gösterilir.")
    fig, ax = plt.subplots(figsize=(12, 4.5))
    x = range(len(daily))
    ax.bar([i-.2 for i in x], daily['Önce'], width=.4, color=COLORS['Önce'], label="Önce")
    ax.bar([i+.2 for i in x], daily['Sonra'], width=.4, color=COLORS['Sonra'], label="Sonra")
    ax.set_xticks(list(x)); ax.set_xticklabels(daily.index.strftime("%d.%m.%Y"), rotation=60, ha="right")
    ax.set(title="Günlere göre öğrenci-sınav dağılımı", ylabel="Öğrenci-sınav toplamı")
    ax.grid(axis="y", alpha=.2); ax.legend()
    draw(fig, "gunluk_yuk_karsilastirmasi.png")

with peak_tab:
    peaks = curves.max()
    fig, ax = plt.subplots(figsize=(9, 4))
    bars = ax.bar(list(COLORS), [peaks[n] for n in COLORS], color=list(COLORS.values()), width=.5)
    ax.bar_label(bars, fmt="%.0f", padding=5)
    ax.axhline(capacity, linestyle="--", color="#AD3340", label=f"Kapasite: {capacity:,}")
    ax.set_ylim(0, max(capacity, peaks.max())*1.2)
    ax.set(title=f"Eşzamanlı tepe yük · {minutes} dakika varsayımı", ylabel="Aktif öğrenci-sınav sayısı")
    ax.legend(); ax.grid(axis="y", alpha=.2)
    draw(fig, f"tepe_yuk_{minutes}dk.png")
    st.dataframe(pd.DataFrame({"Plan":list(COLORS),"Tepe yük":[int(peaks[n]) for n in COLORS],"Kapasite üzerinde süre (saat)":[round(hours_above(curves[n],capacity),2) for n in COLORS]}), hide_index=True, use_container_width=True)

with resource_tab:
    st.caption("Varsayımsal kaynak modeli: öğrenci başına CPU 0,02; RAM 0,05; bant genişliği 0,2. Kaynak birimleri ve katsayılar ölçümle doğrulanmış değildir.")
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    for ax, (label, rate) in zip(axes, [("CPU", .02), ("RAM", .05), ("Bant genişliği", .2)]):
        for name in COLORS:
            ax.step(shown.index, shown[name]*rate, where="post", color=COLORS[name], label=name)
        ax.set_ylabel(f"{label}\n(model birimi)"); ax.set_ylim(bottom=0); style_time_axis(ax)
    axes[0].legend(); axes[0].set_title(f"Kaynak yükü modeli · {minutes} dakika varsayımı · {day}")
    draw(fig, f"kaynak_modeli_{minutes}dk_{day}.png")

with st.expander("Grafik verileri ve hesaplama"):
    st.write("Her başlangıçta öğrenci sayısı eklenir; seçilen süre sonunda çıkarılır. Aynı andaki başlangıç ve bitişler birlikte işlenir. Gece yarısı geçişleri korunur. Gün seçimi yalnızca zaman grafiklerini filtreler.")
    st.dataframe(curves.rename_axis("Tarih ve saat").reset_index(), hide_index=True, use_container_width=True)
    st.download_button("Hesaplanan yükleri CSV olarak indir", curves.rename_axis("timestamp").to_csv().encode("utf-8-sig"), f"karsilastirma_{minutes}dk.csv", "text/csv")
