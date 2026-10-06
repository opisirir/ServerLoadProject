# Exam Balance

Makalenin V3 sürümündeki **CP-SAT → Great Deluge** yaklaşımı için örtüşen sınav yüklerini hesaplayan optimizasyon motoru ve GitHub Pages karşılaştırma sitesi.

## Çalıştırma

```powershell
python -m pip install -r requirements.txt
python main.py --input data/example_planned_schedule.csv --scenario all --minutes 60 --seeds 42,43,44 --seconds 10 --evaluations 3000 --output results/benchmark.json
python -m http.server 8765 --directory web
```

`http://localhost:8765` adresini açın. **Sonuç yükle** ile `results/benchmark.json` seçin. Dosya tarayıcıda işlenir, bir sunucuya yüklenmez. Sayfa örnek olarak gerçek algoritma koşularından üretilmiş, açıkça **sentetik** etiketli bir veri kümesi gösterir.

Eski Streamlit arayüzü kaldırıldı. GitHub Pages Python çalıştırmaz; deneyler yerel Python ortamında hesaplanır, JSON raporu statik sitede incelenir. Yükleme, senaryo/algoritma/tohum seçimi, karşılaştırma CSV'si ve seçilen çizelge indirmesi desteklenir.

## Sunucu senaryoları

| Senaryo | Maksimum eşzamanlı kullanıcı |
|---|---:|
| Senaryo 1 | 500 |
| Senaryo 2 | 2.500 |
| Senaryo 3 | 6.000 |

`--scenario paper` makaledeki **5.000** kapasiteli deney varsayımını seçer. Bu, Senaryo 3'ün maksimumu değildir. CPU/RAM/ağ katsayıları ve ayrıntılı donanım tabloları kaldırıldı; tek kaynak kısıtı eşzamanlı sınav katılımıdır.

## Ortak problem ve algoritmalar

Her sınav, dosyada gözlenen aday başlangıçlardan tam olarak birine atanır; sınav ve katılımcı grubu bölünmez. Tüm sınavlar için `--minutes` ortak süre varsayımı kullanılır (varsayılan 60). Bitiş saati dosyadan alınmaz. Yükler `[başlangıç, bitiş)` aralıklarında hesaplanır; farklı başlangıç saatleri, gece yarısı ve eşzamanlı bitiş/başlangıç doğru ele alınır. Amaç, kapasiteyi koruyarak **en yüksek eşzamanlı katılımı azaltmaktır**.

- **CP-SAT → GD:** CP-SAT amaç fonksiyonu olmadan ilk olurlu çözümde durur. Great Deluge azalan kabul eşiğiyle taşıma/takas komşuluğunda tepe yükü iyileştirir, olurluluğu korur ve en iyi çözümü saklar. Büyük veri için bire bir ikili atama matrisine eşdeğer, ayrık başlangıç alanlı interval/cumulative modeli kullanılır.
- **PSO:** ayrık zaman dilimlerine yuvarlanan hız/konum güncellemeleri, kişisel ve küresel en iyi, küçük mutasyon.
- **GA:** turnuva seçimi, uniform çaprazlama, mutasyon ve elitist en kötü birey değişimi.
- **TS:** taşıma komşuluğu, yedi iterasyonluk tabu süresi ve aspirasyon.
- **AC:** feromon buharlaşması, en iyi çözüm pekiştirmesi ve artımlı yük sezgiselliği.
- **HS:** harmony memory, bellekten seçim, pitch adjustment ve en kötü çözüm değişimi.
- **Probleme özgü sezgisel:** büyük sınavları önce yerleştirme ve iyileştiren taşıma/takas araması.
- **ANN:** sürekli Hopfield benzeri atama nöronları, karesel yük/kapasite enerjisi ve tekrarlayan güncellemeler. Eğitilmiş bir tahmin modeli değildir.
- **SA:** azalan sıcaklık ve Metropolis kabulü.

Baseline yöntemler aynı problem için referans uygulamalardır; kullanıcının andığı araştırmacıların özgün uygulamalarının birebir replikasyonu değildir. PSO: inertia 0,7 ve cognitive/social 1,4; GA: turnuva 3, mutasyon max(1/n, 0,02); AC: buharlaşma 0,1, heuristic üssü 2; HS: memory 0,9, pitch 0,3; ANN: adım 0,2, overflow ağırlığı 10; SA: başlangıç sıcaklığı en büyük sınav katılımı. Bu parametreler `examlab/algorithms.py` içinde açıktır.

Her yöntem aynı süre ve değerlendirme üst sınırını kullanır. CP-SAT iç arama sayıları bu sayaçla eşdeğer değildir; duvar saati ayrıca raporlanır. Model kurma veya tek bir pahalı adım süre sınırını aşabilir. Zaman sınırı baskınsa aynı tohum farklı makinelerde farklı sonuç verebilir. Başlangıç stratejileri algoritmanın parçasıdır; tümüne önerilen yöntemden iyi bir çizelge verilmez.

Rapor ortalama/std. sapma/en iyi tepeyi **yalnız olurlu koşulardan**, başarı oranını ve süreyi **tüm koşulardan** hesaplar. Çözümsüzlük ile zaman aşımı ayrıdır. Tek koşuyu başarı oranı gibi sunmaz. Sıralama önce olurlu çözüm oranına, sonra ortalama tepeye göre yapılır. Makale yöntemi vurgulanır ama kazanan sonuçlar değiştirilmez.

## Veri ve sınırlar

CSV, XLSX ve JSON desteklenir. Gerekli kolonlar: `exam_id, student_count, date, start_time`. `DERS_ID`, `OGR_SAY`, `TARIH`, `PLANLANAN_SAAT` gibi Türkçe kolonlar eşlenir. Tekrarlanan ders kodları birleştirilmez; her satır ayrı sınav olayıdır. Çıktı kimlikleri anonimleştirilir. Negatif/kesirli katılım ve hatalı tarih/saat varsayılan olarak reddedilir. `--drop-invalid` açıkça dışlamaya izin verir; dışlanan satır numaraları rapora yazılır. Otomatik ek tarih aralığı filtresi uygulanmaz.

Bireysel öğrenci kayıtları olmadığı için öğrenci çakışması doğrulanmaz; bölüm etiketi öğrenci ortaklığı olarak kabul edilmez. Katılım toplamı tekil kişi değildir. Kapasite olurluluğu hizmet kesintisinin önlendiğini veya donanım azaltılabileceğini ispatlamaz. Bu sürümde aday tarihler arasında hareket serbesttir; bölüm/gün sabitlemesi veya farklı sınav süreleri ayrıca modellenmemiştir.

V3 taslağı 1.957 sınav, 118.964 katılım ve 149 aday başlangıçla 5.948 → 3.582 (%39,78) tek koşu bildirir. Depodaki `VerilerArasinav.xlsx` 2.219 sınav, 144.467 katılım ve 187 aday başlangıç içerir; bu farklı veri, makalenin filtrelenmiş deneyi gibi sunulmaz. Taslaktaki Tablo 3'ün kaynak/katsayı satırları tutarsız olduğundan fiziksel kaynak modeli türetilmemiştir.

## GitHub Pages yayını

1. Değişiklikleri GitHub'daki `main` dalına gönderin.
2. **Settings → Pages → Source → GitHub Actions** seçin.
3. `Publish comparison site` iş akışı yalnız `web/` klasörünü yayımlar.

[GitHub Pages özel iş akışları](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages). Ham kurumsal veriler ve yerel `results/` yayın paketine dahil değildir. Canlı yayına gönderme bu revizyon sırasında yapılmamıştır.

## Doğrulama

```powershell
python -m unittest discover -s tests
node --test tests/test_web.cjs
```

Örnek sonuçları yeniden üretmek için `python generate_demo.py` kullanın. Bu işlem sentetik örnek CSV'yi ve `web/data/benchmark.json` raporunu yeniden oluşturur.

## Dosya yapısı

- `examlab/`: veri okuma, zaman örtüşmesi, algoritmalar, benchmark raporu
- `main.py`: tek komut satırı giriş noktası
- `web/`: bağımlılıksız HTML/CSS/JS karşılaştırma sitesi
- `tests/`: model, tarih ve rapor/grafik testleri
- `data/`: sentetik örnek plan ve saklanan yerel gerçek veri
- `results/`: yerel deney sonuçları (Git tarafından yok sayılır)

## Kaynak

Onur Mahmut Pişirir ve Recep Çolak, *Algorithmic Exam Timetabling to Prevent Server Crash in Cloud-Based Learning Management Systems*, V3 taslağı. CP-SAT → GD iki aşaması, 60 dakika varsayımı, kapasite senaryoları ve bildirilen %39,78 bulgusu bu kullanıcı belgesinden alınmıştır. Model uygulaması için [OR-Tools CP-SAT belgeleri](https://developers.google.com/optimization/cp/cp_solver) esas alınır. Belgede tamamlanmamış bölümler ve literatür anlatımı, yazılıma yönelik talimat olarak işlenmez.

## Arayüz dilleri ve birleşik karşılaştırmalar

Üst menüde Türkçe / English seçimi bulunur; seçim tarayıcıda saklanır. Dil değişince rapor, senaryo, algoritma ve tohum seçimi korunur. Başlıklar, grafikler, sonuç yorumları ve hata mesajları çevrilir.

Süre–tepe yük dağılım grafiği, seçili tohumda tüm algoritmaların yakınsaması ve tüm senaryoları kapsayan sonuç matrisi eklendi. Makale yönteminin avantajları rapordaki başarı oranı, olurlu ortalama tepe ve süre değerlerinden hesaplanır. Daha iyi sonuç veren rakipler de gösterilir. Başarısız koşular sıfır yük olarak çizilmez. Örtüşme modeli bütün yöntemlerde ortak olduğu için yalnız makale yönteminin avantajı olarak sunulmaz.
