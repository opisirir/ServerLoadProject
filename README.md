# Exam Balance

Makaledeki **CP-SAT → Great Deluge** yöntemi ile matematiksel optimizasyon modellerini karşılaştırır. Arayüz Türkçe ve İngilizcedir.

## Çalıştırma

```powershell
python -m pip install -r requirements.txt
python main.py --input data/VerilerArasinav.xlsx --scenario paper --seconds 15 --evaluations 1000000 --seeds 42,43,44 --output results/real_benchmark.json
python -m http.server 8765 --directory web
```

`http://localhost:8765` adresinde **Sonuç yükle** ile JSON raporu seçin. Dosya tarayıcıda işlenir. GitHub Pages hesaplama yapmaz; yerelde hesaplanan raporları gösterir.

## Modeller

| Kimlik | Model | Çözücü | Amaç |
|---|---|---|---|
| cp_gd | Makaledeki iki aşamalı yöntem | CP-SAT + GD | İlk olurlu çizelgeden tepe yükünü azaltma |
| mip | Karma tam sayılı programlama | CBC | Sürekli tepe değişkenini minimize etme |
| ilp | Tam sayılı lineer programlama | CP-SAT | Tamsayılı tepe değişkenini minimize etme |
| goal | Hedef programlama | CBC | Kanıtlanmış başlangıç alt hedefinden pozitif sapmayı minimize etme |

Modeller kullanıcının `Gerçek Dünya Uygulamalarında Kullanılan Algoritmalar.xlsx` dosyasındaki matematiksel model ailelerinden seçilmiştir. Kurumlara özgü modellerin birebir yeniden üretimi değildir. Excel'deki DSS, GAMS, AMPL, CPLEX ve Gurobi ifadeleri ayrı algoritmalar olarak sayılmaz. Sütun üretimi, çok aşamalı kurum modelleri ve bulanık kritiklik modeli gerekli formülasyon/veri bulunmadığı için uygulanmış gibi gösterilmez. Excel satırları `docs/comparison_source.json` içinde kaynak bilgisi olarak korunur.

Üç matematiksel model bu kapasite ve tepe yükü probleminde aynı optimumu hedefler. Hedef model tek hedeflidir; bulanık mantık iddiası yoktur. Modellerin ve çözücülerin süre sınırlı davranışı karşılaştırılır; sonuçlar bağımsız üç literatür algoritmasına karşı genel üstünlük kanıtı değildir. MIP ve hedef modelleri aynı CBC arka ucunu kullanır.

## Ortak problem

- Gözlenen tarih/başlangıçlar aday zaman pencereleridir.
- Her sınav tek pencereye atanır; sınav katılımı bölünmez.
- Tüm sınavların süresi `--minutes` ile belirlenir (varsayılan 60).
- Yük `[başlangıç, bitiş)` aralıklarında hesaplanır. Farklı saatlerde başlayan ve gece yarısını aşan sınavlar dahil edilir.
- Bütün modeller aynı kapasiteyi korur. Bireysel öğrenci kayıtları bulunmadığından öğrenci çakışması kısıtı yoktur.
- Katılım sayısı tekil öğrenci sayısı değildir.

Eşit katılımlı sınavlar, başka kısıt olmadığı için matematiksel modellerde tam sayılı adet değişkenleriyle gruplanır. Bu, büyük ikili atama matrisine eşdeğer bir azaltmadır; sonuç yeniden tek tek sınavlara açılır. Bölüm veya kişisel çakışma kısıtları eklenirse bu gruplama yeniden değerlendirilmelidir. Formülasyon: `docs/mathematical_comparison.md`.

## Kapasiteler

| Seçim | Maksimum eşzamanlı kullanıcı |
|---|---:|
| scenario_1 | 500 |
| scenario_2 | 2.500 |
| scenario_3 | 6.000 |
| paper | 5.000 (makaledeki deney varsayımı) |

`--scenario all` dört kapasiteyi çalıştırır. Varsayılan web raporu açıkça sentetik etiketlidir. `python generate_demo.py` bu raporu yeniden üretir.

## Sonuçların yorumu

Karşılaştırma önce olurlu çözüm oranını, ardından tepe yükü ve süreyi değerlendirir. Olurlu ortalama, standart sapma, en iyi tepe, çalışma süresi, eşleşmiş koşularda kazanma/eşitlik/kaybetme ve kanıtlanmış alt sınıra göre açıklık gösterilir. Başarısız koşular sıfır tepe olarak çizilmez.

Açıklık = `(tepe − ortak kanıtlanmış alt sınır) / tepe`. Sıfır açıklık optimumu kanıtlar. Pozitif açıklık gerçek optimuma uzaklığın üst sınırıdır, kesin fark değildir. Ortak alt sınır yalnız aynı veri/süre/kapasite deneyindeki geçerli matematiksel sınırlardan elde edilir.

Tüm modellerin zaman bütçesi model kurulumunu da içerir; solver sonlandırma/sonuç çıkarma masrafı sınırı bir miktar aşabilir. GD'nin ayrıca `--evaluations` üst sınırı vardır. Matematiksel çözücülerin iç düğüm aramaları aynı değerlendirme sayacıyla sınırlanmaz. CBC tekrarlarında rastgele tohum değişmez; süre dalgalanmaları olabilir. Küçük tekrar sayıları için istatistiksel anlamlılık iddiası kurulmaz. CBC yalnız son çözümü bildirir; yakınsama grafiğinde ara ilerleme uydurulmaz.

Makale V3'te raporlanan 5.948 → 3.582 (%39,78) ayrı bir tek koşu sonucudur. Depodaki gerçek veri 2.219 sınav/144.467 katılım içerir; makaledeki filtrelenmiş 1.957 sınav/118.964 katılım ile aynı değildir. Yazılım çıktısı sunucu kesintisinin önlendiğini veya donanım azaltılabileceğini kanıtlamaz.

## Veri

CSV, XLSX veya JSON: `exam_id, student_count, date, start_time`. Türkçe kolon eşlemesi desteklenir. Her satır ayrı sınavdır. Hatalı kayıtlar reddedilir; `--drop-invalid` açık dışlamaya izin verir ve satır numaraları rapora yazılır. Çıktı kimlikleri anonimleştirilir.

## Testler ve yayın

```powershell
python -m unittest discover -s tests
node --test tests/test_web.cjs
```

GitHub'da **Settings → Pages → Source → GitHub Actions** seçildiğinde `.github/workflows/pages.yml` yalnız `web/` klasörünü yayımlar. Yerel `results/` ve ham kurumsal dosyalar yayın paketine alınmaz. Bu revizyon canlı yayına gönderilmemiştir.

Uygulama referansları: [OR-Tools MIP](https://developers.google.com/optimization/mip/mip_example), [CP-SAT](https://developers.google.com/optimization/cp/cp_solver).
