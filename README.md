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

Ana sayfadaki **Before / After Comparison charts** bağlantısı ayrı karşılaştırma sayfasını açar.
Bu sayfa gönderilen CSV örneğini veya son optimizasyonun plan/sonuç çiftini gösterir.
Eşzamanlı yük, günlük dağılım, tepe yük ve varsayımsal kaynak grafikleri bulunur;
grafikler PNG, hesaplanan yükler CSV olarak indirilebilir. Ortak süre seçimi her iki
plana da uygulanır ve süreleri örtüşen sınavlar birlikte sayılır. Süre ve kapasite
ayarları karşılaştırma senaryosudur; bu sayfa solver'ın amaç fonksiyonunu değiştirmez.
Oturumdaki son sonuç yoksa seçili çıktı klasöründeki plan/optimize slot özetleri okunur.

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

Varsayılan altyapı, firma belgesindeki **Moodle Senaryo 3** olarak güncellendi.

- App01 / App02 / App03+: her biri 16 vCPU, 32 GB RAM, 100 GB disk.
- Ayrı LB, NFS/GlusterFS depolama, SQL proxy, master/replica SQL ve Redis katmanları.
- Dış ağ: en az 1 Gbps; yerel ağ: 10 Gbps. SSD/NVMe depolama.
- Belgede 30.000–50.000+ aktif kullanıcı, 3.000–6.000 eşzamanlı kullanıcı belirtiliyor.
- Başlangıç planlama sınırı: 3.000 eşzamanlı sınav katılımı (aralığın alt sınırı).

Arayüzde `Server infrastructure` seçimi veya CLI ile diğer profiller seçilebilir:

```bash
python main.py --planned_schedule data/example_planned_schedule.csv --server_profile moodle_3 --solver graph --output outputs_moodle3
```

Profil, mimari ve hesaplama varsayımları her çalışmada `server_profile.json` dosyasına kaydedilir.
CPU vCPU, RAM GB, ağ Mbps birimindedir. Öğrenci başına katsayılar uygulama katmanı
kapasitesinin başlangıç kullanıcı sınırına bölünmesiyle türetilmiş doğrusal planlama
tahminleridir; firma ölçümü değildir. SQL/cache kaynakları uygulama havuzuna eklenmez.
Senaryo 3 için üç uygulama düğümü esas alınır; belgede yinelenen SQL2+ satırı ikinci
replica olarak envanterde tutulur. `+` işaretleri otomatik sınırsız ölçekleme anlamına gelmez.
Disk kapasitesi, IOPS, SQL yazma darboğazı ve düğüm arızaları solver tarafından modellenmez.
BigBlueButton ayrı bir iş yükü olduğu için Moodle kapasitesine eklenmez.
Aktif kullanıcı sayısı eşzamanlı sınav kapasitesi değildir; 6.000 üst sınırı yük testiyle
kalibre edilmeden garantili sınav kapasitesi sayılmaz.

Kaynak: `moodle_kullanım_2025-tech spect.docx - Google Dokümanlar.pdf`, sayfa 1–2.
Harici timeslot dosyasındaki açık kapasite/kaynak limitleri mevcut davranış gereği
profil varsayılanlarını geçersiz kılar. Önceki çıktı dosyaları eski modeli içerir;
yeni profil için optimizasyon yeniden çalıştırılmalıdır. Solver slot bazında çalışır;
farklı başlangıç saatlerinde örtüşen sınavları karşılaştırma sayfası ayrıca hesaplar.
