# Examination Timetabling Optimization

Gercek CSV, XLSX veya JSON dosyalarindan sinav cizelgesi ureten Python optimizasyon sistemi.

## Kurulum

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

OR-Tools kurulu degilse `cp_sat` calismaz, fakat `ga`, `sa` ve `hybrid` cozumleri kullanilabilir.

## Calistirma

```bash
python main.py \
  --planned_schedule data/planned_schedule.xlsx \
  --solver hybrid \
  --output outputs
```

Solver secenekleri: `cp_sat`, `graph`, `ga`, `sa`, `hybrid`, `all`.

Program ders bazli ogrenci sayisi ile calisir; bireysel `student_id` dosyasi istemez. Planlanmis sinav dosyasindaki `TARIH + PLANLANAN_SAAT` mevcut plan kabul edilir, ayni timeslot evreni icinde optimize edilir ve planned-vs-optimized karsilastirmasi uretilir. Referans Excel dosyalarinda `DERS_ID`, `DERS_KOD`, `DERS_AD`, `OGR_SAY`, `TARIH`, `PLANLANAN_SAAT`, `SAAT`, `BOLUM`, `PROG_AD` ve `_6477` son ekli kolonlar otomatik algilanir.

```bash
python main.py --planned_schedule "C:\Users\Honour\My Drive\Makale\Server Load\DüzenliVeriler\VerilerArasinav.xlsx" --solver hybrid --output outputs
```

## Gorsel arayuz

```bash
streamlit run app.py
```

Arayuzden tek planlanmis sinav dosyasi yuklenir. Solver secilir ve planlanan cizelge ile optimize cizelge birlikte goruntulenir. Grafikler ve CSV/JSON ciktilari secilen output klasorune kaydedilir.

Arayuz, yuklenen dosyadaki mevcut `TARIH + SAAT` atamasini gercek cizelge olarak yeniden kurabiliyorsa optimize sonuc ile ayni anda gosterir:

- `Overview`: objective, load variance, max load ve hard violation iyilesmeleri
- `Algorithms`: graph, GA, SA ve hybrid algoritmalarinin basari, objective, runtime ve load variance karsilastirmasi
- `Load comparison`: gercek ve optimize timeslot ogrenci/sinav dagilimi
- `Resource comparison`: CPU, RAM ve bandwidth karsilastirmasi
- `Improvements`: metrik bazli yuzde iyilesme grafigi
- `Statistics`: bolum bazli en cok sinav, ogrenci sayisi, en buyuk sinavlar ve bolum-timeslot yogunlugu
- `Schedule`: optimize cizelge ve gercek atama eslemesi

Ek karsilastirma ciktilari:

- `outputs_gui/real_vs_optimized_metrics.csv`
- `outputs_gui/real_vs_optimized_timeslots.csv`

Performans parametreleri:

```bash
python main.py --planned_schedule data/example_planned_schedule.csv --solver all --time_limit 60 --max_iterations 5000 --ga_generations 300 --population_size 100 --seed 42
```

## Beklenen dosya formatlari

`planned_schedule`:

```csv
exam_id,exam_name,student_count,department_id,date,start_time
MATH101,Calculus,120,Engineering,2026-07-01,09:00
PHY101,Physics,80,Engineering,2026-07-01,13:00
```
Turkce veya farkli kolon adlari otomatik eslenmeye calisilir. Ornekler: `DERS_ID`, `sinav`, `ders_kodu`, `ders_ad`, `bolum`, `ogrenci_sayisi`, `ogr_say`, `tarih`, `PLANLANAN_SAAT`, `saat`.

## Ciktilar

- `outputs/schedule_output.csv`
- `outputs/results.csv`
- `outputs/metrics_summary.json`
- `outputs/algorithm_comparison.csv`
- `outputs/validation_report.json`
- `outputs/department_summary.csv`
- `outputs/top_exams.csv`
- `outputs/planned_timeslot_summary.csv`
- `outputs/optimized_timeslot_summary.csv`
- `outputs/planned_department_timeslot_concentration.csv`
- `outputs/optimized_department_timeslot_concentration.csv`
- `outputs/figures/`

## Algoritma karsilastirmasi

`--solver all` ile birden fazla algoritma ayni dosya uzerinde calistirilir. Arayuzde `Solver = all` secildiginde `Algorithms` sekmesi acilir ve su bilgiler gosterilir:

- Hangi algoritma bu dosyada en iyi objective degerini verdi
- Hangi algoritmalar feasible cozum uretmeyi basardi
- Algoritma bazli runtime
- Algoritma bazli load variance
- Ortalama success rate

Graph solver, dersleri buyukten kucuge siralayan ve timeslotlari kapasite, yuk dengesi ve bolum yogunluguna gore puanlayan hizli bir graph-coloring benzeri sezgisel algoritmadir.

## Notlar

Varsayilan sunucu modeli:

- `cpu_per_student = 0.02`
- `ram_per_student = 0.05`
- `bandwidth_per_student = 0.2`
- `max_cpu = 100`
- `max_ram = 256`
- `max_bandwidth = 1000`
- `max_concurrent_students = 5000`

Eksik `department` alani `UNKNOWN`, eksik `exam_name` alani `exam_id`, eksik timeslot kaynak limitleri varsayilan config degerleri ile doldurulur.
