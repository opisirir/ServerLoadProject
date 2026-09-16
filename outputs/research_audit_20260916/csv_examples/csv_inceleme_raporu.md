# Gönderilen örnek CSV çıktısının tutarlılık incelemesi

İnceleme: 16 Eylül 2026. Özgün dosyalarda değişiklik yapılmadı.

İncelenen dosyalar:

- `ExampleFiles/2/2026-06-29T10-55_export.csv`: ders kodu başına bir satır içeren sonuç çizelgesi.
- `ExampleFiles/timeslots_program_ready.csv`: sonuç çizelgesinin kullandığı zaman dilimleri ve kapasite sınırları.
- Karşılaştırma kaynağı: `HamVeriler/arasinavlar.xlsx`, `Page 1`. Önceki incelemede diğer ara sınav Excel dosyasıyla birebir aynı olduğu doğrulanmıştı.

## Sonuç

**Dosyalar aritmetik ve zaman dilimi eşleştirmesi bakımından tutarlı; bilimsel olarak doğrulanmış bir sunucu yükü optimizasyonu sonucu kabul etmek için yeterli değiller.** Ders kodları ve toplam kayıt sayıları korunmuş; ancak çok günlük plan tek güne taşınmış, bölüm bilgileri birleştirmede bozulmuş ve gerçek sınav süreleri belirtilmemiş. Ortak ders takvimiyle de belirgin farklılıklar var.

Bu çıktı önce incelenen `outputs_gui` çıktısından farklıdır. Önceki rapordaki 144.467 toplam ve 7.898/8.577 tepe değerleri bu yeni CSV'ye ait değildir.

## Geçen kontroller

| Kontrol | Sonuç |
|---|---|
| Çıktı satırı / benzersiz ders kodu | 2.152 / 2.152 |
| Zaman dilimi sayısı | 43 |
| Öğrenci-sınav toplamı | 196.368 |
| Ham girdiye göre eksik/fazla ders kodu | 0 |
| Ders koduna göre toplanan öğrenci sayısı farkı | 0 |
| Tekrar eden çıktı kimliği / slot kimliği | 0 / 0 |
| Eksik hücre / geçersiz öğrenci sayısı | 0 / 0 |
| Tanımsız slot veya tarih/saat eşleşme hatası | 0 |
| Bildirilen slot toplamında aritmetik hata | 0 |
| CPU/RAM/bant genişliği formül hatası | 0 |
| Bitişi başlangıcından önce/eşit aralık | 0 |
| CSV'de tanımlanan slotlar arası örtüşme | 0 |

Kaynakta 3.558 satır var; bunlar ders koduna göre 2.152 satıra toplanmış. Toplam öğrenci-sınav sayısının korunması, bütün şube ve bölüm ilişkilerinin korunduğunu göstermez. Toplam benzersiz öğrenci sayısı değildir.

İsimsiz ilk sütun `Unnamed: 0`, 0–2.151 arasındaki tekil dışa aktarım indekslerini içeriyor. Çalışmanın anahtarı `exam_id` olmalı; bu indeks veri hatası veya ek öğrenci kaydı değildir.

## Dönem ve sınav birimi değişiklikleri

Ham ara sınav planı 28 Mart–12 Haziran 2023 arasında **25 farklı tarih** içeriyor. Gönderilen çıktı bütün kayıtları **10 Nisan 2023, 08:00–23:00** arasına yerleştiriyor. Ham veride 10 Nisan'a ait toplam 12.140 iken çıktıda aynı güne 196.368 öğrenci-sınav kaydı atanmış.

Bu değişiklik izinli gün kümesini daraltan ayrı bir deney senaryosudur. Kurumun bütün sınavları aynı güne taşıma izni, öğrenci çakışmaları ve ortak ders kısıtları doğrulanmadan gerçek takvimin geçerli bir alternatifi kabul edilemez. Girdideki 25 tarihin tamamının doğru olduğu da varsayılmadı; dönem dışı/gece yarısı kayıtları önceki raporda ayrıca işaretlenmişti.

Ham kaynakta **549 ders kodu** birden fazla bölüm, tarih veya saatle ilişkili. Bunların tek bir `exam_id` altında toplanması, farklı sınav olaylarını birbirine bağlamış olabilir. Ayrıca **112 bölümün öğrenci-sınav toplamı**, ham kaynak ile çıktı arasında farklı:

| Bölüm | Ham kaynak | Çıktı | Fark |
|---|---:|---:|---:|
| İlahiyat (Arapça Hazırlık) | 9.029 | 17.901 | +8.872 |
| Hukuk | 7.428 | 13.481 | +6.053 |
| Halkla İlişkiler ve Tanıtım İ.Ö. | 3.035 | 1.177 | −1.858 |

Bunlar toplam öğrenci kaybı değil, öğrencilerin bölüm etiketleri altında yanlış/eksik temsil edilmesidir. Bir ders kodunun toplamını tek bölüm etiketi altında tutmak bölüm bazlı yük ve ceza hesaplarını değiştirir. Tam bölüm farkları `csv_kontrol_sonuclari.json` içindedir. Çıktıdan özgün şube dağılımı tek başına geri çıkarılamaz; ham veriyle yeniden üretilmelidir.

Bu çıktı önceki temiz aday ara sınav dosyasının sonucu değildir: temiz adayda 3.337 kaynak satırı ve 176.196 öğrenci-sınav kaydı vardı; burada 2.152 birleştirilmiş ders kodu ve ham toplam olan 196.368 var. Gece yarısı ve tam tekrar incelemelerindeki kayıtların sayıları da bu toplamın içindedir.

## Süre yorumu

43 slotun süre dağılımı:

| Süre | Slot sayısı |
|---|---:|
| 5 dakika | 5 |
| 10 dakika | 5 |
| 15 dakika | 15 |
| 30 dakika | 16 |
| 60 dakika | 2 |

Bu aralıkların gerçek sınav süresi mi yoksa yük ölçüm dilimi mi olduğu dosyada açıklanmıyor. Örneğin FRM-902 için 1.495 öğrenci 12:45–12:50 aralığına atanmış. Bunu doğrulanmış beş dakikalık sınav süresi saymak mümkün değil.

Eğer bunlar gerçek sınav süreleri ise dosyanın kendi bitiş saatleri altında en yüksek eşzamanlı öğrenci-sınav yükü **6.612** olur. Eğer ölçüm dilimleriyse, önceki dilimde başlayıp devam eden sınavların yükü sonraki dilimlere taşınmalıdır. Başlangıç saatlerine atanan öğrenci toplamlarını aktif sunucu yükü olarak yorumlamak yeterli değildir.

Gerçek süreler bilinmediği için yalnızca duyarlılık hesabı yapıldı. Aşağıdaki tabloda her senaryoda hem ham kaynağa hem çıktıya aynı sabit süre uygulanır. Hesap `[başlangıç, bitiş)` aralıklarında aktif öğrenci-sınav sayısını toplar; sıfır olmayan gece yarısı kayıtları ham veride aynen korunur.

| Varsayımsal sabit süre | Ham plan tepe yükü | Çıktı tepe yükü |
|---|---:|---:|
| 30 dakika | 16.899 | 17.775 |
| 60 dakika | 16.899 | 35.542 |
| 120 dakika | 16.981 | 55.649 |

Bu değerler ölçülmüş sunucu yükü veya gerçek süre tahmini değildir. Süre yorumunun sonucu ne kadar değiştirdiğini gösterir. Önceki rapordaki iki saat varsayımı bu CSV'nin doğrulanmış süresi olarak kabul edilmedi. Ölçüm dilimleri farklı uzunlukta olduğundan slotlar arası varyansın zaman boyunca yük varyansına eşit olduğu da varsayılmamalıdır; ortak zaman çözünürlüğü veya zaman ağırlıklı hesap gerekir.

## Kapasite tutarlılığı

CSV'de her slot için kapasite ve eşzamanlı öğrenci sınırı **8.930**. Kaynak sınırları CPU 178,6; RAM 446,5; bant genişliği 1.786 olarak verilmiş. Satır hesaplarında öğrenci başına katsayılar sırasıyla 0,02; 0,05; 0,2 ve aritmetik tutarlı.

Tanımlanan bitiş saatleri ve CSV'nin bu sınırları altında kapasite aşımı yok. En yüksek slot yükü 6.612, en düşük 4.398; ortalama 4.566,70.

Ancak projedeki varsayılan sınırlar 5.000 öğrenci, CPU 100, RAM 256 ve bant genişliği 1.000. Bu sınırlar kullanıldığında üç slot ihlal ediyor:

| Slot | Başlangıç | Öğrenci-sınav yükü |
|---|---|---:|
| 114 | 12:00 | 6.612 |
| 136 | 18:30 | 5.415 |
| 139 | 20:30 | 6.581 |

Bu nedenle “kapasite ihlali yok” ifadesi ancak kullanılan kapasite senaryosu açıkça yazılarak kullanılabilir. 8.930 sınırının ölçüme veya onaylı sunucu konfigürasyonuna dayandığı dosyalardan doğrulanamıyor. CPU/RAM/ağ hesapları ölçüm değil, katsayılı model çıktılarıdır.

## Ortak ders takvimiyle karşılaştırma

Önceden verilen ortak ders takvimi referans alınırsa:

- `TUR-270` (Türk Dili II) çıktıda 10 Nisan 12:00'da; referans Türk Dili için 11 Nisan'ı gösteriyor.
- `ATA-260` çıktıda 10 Nisan 20:30'da; referansta birimlere göre verilen Atatürk İlkeleri pencereleri gündüz saatlerinde.
- `ING-102` çıktıda 10 Nisan 18:30'da; referanstaki İngilizce II penceresi 16:30–18:00.
- FRM-902/904/906 kayıtları 10 Nisan'a taşınmış; referanstaki ilgili formasyon dersleri 11 Nisan'da.

Bu eşleştirmeler ders kodu/adı üzerinden yapılmış aday kontrollerdir. Bütün birimlerin tek kayıtta birleştirilmesi birim bazlı kesin doğrulamayı engelliyor. Referans takvimin bu deneyde bağlayıcı olduğu onaylanırsa bu farklılıklar ihlal olarak ele alınmalıdır. Referans belgedeki açıklamalar çalışma talimatı olarak değil kısıt verisi olarak incelendi.

## Kullanım kararı ve düzeltme yolu

Bu CSV çifti, aktarım ve aritmetik kontrolü için tutarlı bir örnektir. Doğrulanmış bilimsel başarı sonuçlarına henüz dahil edilmemelidir. Uyumsuzlukların çoğu tekil bozuk satırdan değil, sınav birimi, süre, takvim ve kapasite modelinden kaynaklanıyor; bu nedenle rastgele kayıt silerek temiz çıktı üretilmedi. Özgün dosyalar korundu.

Sonuç yeniden üretilirken: onaylı temiz girdi seçilmeli, şube/bölüm ilişkileri korunmalı, izinli tarihler ve ortak dersler tanımlanmalı, gerçek süreler ya da açık süre senaryoları kullanılmalı, örtüşen yükler hesaplanmalı ve başlangıç/optimize plan aynı kapasite ile aynı kayıt kümesinde karşılaştırılmalıdır. Algoritma adı, seed, zaman bütçesi ve amaç fonksiyonu bu iki dosyada bulunmadığından algoritmanın başarı/tekrarlanabilirlik denetimi yapılamadı.

Kontroller `check_examples.py` ile tekrar üretilebilir. Dosya karmaları, tüm slot kontrolleri, bölüm farkları ve süre duyarlılığı `csv_kontrol_sonuclari.json` içinde saklandı. Bu inceleme dosyalardaki kayıtları veya uygulama kodunu değiştirmedi.
