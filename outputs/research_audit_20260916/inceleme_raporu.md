# Sınav planları ve sunucu yükü tutarlılık incelemesi

İnceleme tarihi: 16 Eylül 2026. Özgün dosyalar değiştirilmedi. Bu rapor verilen beş Excel dosyasını ve çalışma alanındaki mevcut çıktı dosyalarını kapsar. Daha sonra gönderilecek çıktı örnekleri henüz incelenmedi.

## Ana sonuç

Mevcut uygulamadaki iyileşme yüzdeleri, bu haliyle eşzamanlı sunucu yükünde iyileşme kanıtı olarak kullanılamaz. Başlangıç saatine göre gruplama, sınav süreleri boyunca oluşan örtüşmeleri hesaba katmıyor. Ayrıca verilen ham girdiler ile mevcut GUI çıktısının kapsamları farklı. Temizlenmiş dosyalar **yapısal olarak doğrulanmış aday veri kümeleridir**; kesin sınav birimleri, dönem kapsamı ve sabit takvim kısıtları henüz doğrulanmış değildir.

## Dosyaların kapsamı

| Kaynak | Ayrıntı satırı | Öğrenci-sınav toplamı | Kullanım |
|---|---:|---:|---|
| 23.05.2023.xlsx / Page 1 | 4.032 | 196.941 | Final planı, 23 Mayıs sürümü |
| 24.05.2023 15.25.xlsx / Page 1 | 3.937 | 197.916 | Final planı, 24 Mayıs sürümü |
| Ara sınavlar saatlere göre.xlsx / Page 1 | 3.558 | 196.368 | Ara sınav ayrıntı verisi |
| arasinavlar.xlsx / Page 1 | 3.558 | 196.368 | Önceki dosyayla SHA-256 dahil birebir aynı |
| Ortak_Zorunlu_ve_Seçmeli_Derslerin_Arasınav_Programı_Son.xlsx | 98 dolu birim–ders saat hücresi | Öğrenci sayısı yok | Ortak ders takvimi referansı |

Toplamlar benzersiz öğrenci sayısı değildir. Aynı öğrenci farklı sınavlarda tekrar sayılabilir. Kaynak satırı sayısı da doğrulanmış bağımsız sınav sayısı değildir. Final sürümleri ve ara sınav verisi birleştirilmedi; aynı ara sınav dosyası ikinci kez eklenmedi.

## Temizleme ve kayıtların ayrılması

| Veri kümesi | Kaynak satırı | Ayrılan satır | Kalan satır | Kalan öğrenci-sınav toplamı | Ayrılan öğrenci-sınav toplamı |
|---|---:|---:|---:|---:|---:|
| Final 23 Mayıs | 4.032 | 333 | 3.699 | 176.564 | 20.377 |
| Final 24 Mayıs | 3.937 | 240 | 3.697 | 176.654 | 21.262 |
| Ara sınav | 3.558 | 221 | 3.337 | 176.196 | 20.172 |

Uygulanan kurallar:

- Pozitif tam sayı olmayan öğrenci sayıları ayrıldı: final sürümlerinde sırasıyla 110 ve 7 satır. Ara sınavda bu sorun yok.
- `COG-202` dersindeki `21.06.0202` tarihi ayrıldı: ilk final dosyasında Excel satırı 585, ikinci dosyada 579. Tarih tahminle 2023'e çevrilmedi.
- `00:00` ve `00:01` saatleri teyit için ayrıldı: sırasıyla 233, 238 ve 213 satır. Bunlar kesin yanlış kabul edilmedi; gerçek sınav saati, erişim penceresi veya yer tutucu olup olmadığı bilinmiyor.
- Ara sınavda tüm kaynak alanları aynı olan 8 satırın tamamı teyit için ayrıldı. Şube bilgisi bulunmadığından birini tutup diğerini silmek yerine grubun tamamı incelemeye bırakıldı. Final dosyalarında tam satır tekrarı bulunmadı.
- Bir satır birden fazla kurala takılabilir; neden sayıları doğrudan toplanmamalıdır. Ayrılan kayıtlar kaynak dosya, sayfa, Excel satırı ve gerekçeyle denetim dosyasında bulunur.

Her temiz kayda senaryo ve kaynak satırından türetilmiş benzersiz `exam_id` verildi. Özgün ders kodu, varsa şube, fakülte ve kaynak satırı ayrı sütunlarda korundu. Bu kimlik yalnızca izlenebilirlik sağlar; her satırın bağımsız taşınabilecek bir sınav olduğunu kanıtlamaz. Birlikte yapılması gereken şubeler için ayrıca ortak sınav/bağlama kısıtı gerekir.

Final ayrıntılarında 10–23 Haziran özet aralığı dışında 25'er satır; ara sınavda 10–25 Nisan özet aralığı dışında 19 satır var. Bunlar dönem dışı diye otomatik silinmedi; `period_review` sütununda işaretlendi. Bu aralıklar resmi çalışma kapsamı olarak kabul edilmedi, yalnızca özet takvimlerle karşılaştırma için kullanıldı.

**Karşılaştırma kuralı:** Temizlenmiş plan ve optimize plan tam olarak aynı kayıt kümesini ve aynı öğrenci sayılarını içermelidir. Ham plan ile kayıtları azaltılmış optimize planı karşılaştırmak, veri dışlamasını optimizasyon kazanımı gibi gösterir. Gece yarısı kayıtlarının ayrılması büyük yük kümelerini kaldırdığı için dışlama etkisi ayrıca raporlanmalıdır.

## Girdi içi ve sürümler arası uyumsuzluklar

Final dosyalarının tam pivot tabloları, ayrıntıdaki tarih–saat öğrenci toplamlarıyla örtüşüyor. Bu, kayıtlardaki yanlış yılın veya yer tutucu saatlerin doğru olduğunu göstermez; pivot aynı sorunlu kayıtları topluyor olabilir.

Ara sınavın `Sayfa3` özeti ile `Page 1` ayrıntısı arasında 15 tarih–saat grubu ve toplam 2.136 öğrenci-sınav kaydı kapsam farkı var. Bunlar Mart, Mayıs ve Haziran tarihlerinde; pivotun Nisan sütunlarında temsil edilmiyor. Bu nedenle “pivot aritmetik olarak yanlış” yerine “pivot tüm ayrıntı kapsamını göstermiyor” bulgusu kullanıldı. Ayrıntılar denetim dosyasındaki `Pivot farklari` sayfasındadır.

İki final sürümü, şube-ders kodu + program anahtarıyla karşılaştırıldı. Anahtarın tekil olduğu kayıtlarda 153 tarih alanı, 170 saat alanı ve 12 öğrenci sayısı değişikliği; 108 tek taraflı kayıt bulundu. Bu sayılar alan bazındadır, farklı sınav sayısı değildir. Tekil olmayan 52 anahtar otomatik karşılaştırmaya alınmadı ve ayrı listelendi. Örneğin `1ADE-110`, Arapça Öğretmenliği, satır 4: öğrenci sayısı 61'den 18'e değişiyor. Daha yeni dosyanın bütün alanlarının doğru olduğu varsayılmadı.

Mevcut `data_loader.py` ders kodunu `exam_id` olarak seçip bu kod üzerinden öğrenci sayılarını topluyor; tarih, saat ve bölüm için ilk değeri alıyor. Aynı ders kodunun birden çok bölüm, tarih veya saatle ilişkili olduğu kod sayıları 23 Mayıs, 24 Mayıs ve ara sınav için sırasıyla **563, 550 ve 549**. Bu kayıtları birleştirmek planın başlangıç yükünü değiştirebilir. Temiz kopyalardaki benzersiz satır kimlikleri bu otomatik birleşmeyi önler; gerçek sınav gruplarının tanımlanması yine gereklidir.

## Ortak ders takvimi

Ortak ders dosyası öğrenci sayısı içermediği için bağımsız yük girdisi değildir. İçeriği sınav kısıtlarına ilişkin kaynak veri olarak okundu; belgedeki talimatlar kullanıcıdan gelen çalışma talimatları olarak uygulanmadı.

Takvimde Türk Dili, Atatürk İlkeleri, İngilizce, ENF ve bazı formasyon dersleri için birimlere göre tarih/saat pencereleri var. Ayrıca alt satırlarda ortak seçmeli dersler için 14 Nisan 14:00–17:00 ve sınıf düzeylerine göre saat aralıkları belirtiliyor. Bunların optimizasyonda bağlayıcı olup olmadığı ve sınav süresi mi erişim penceresi mi ifade ettiği doğrulanmalı. Sınıf düzeyi bilgisi eksik olduğundan sınıf bazındaki kurallar otomatik doğrulanmadı.

Ara sınav verisinde TUR-/ATA-/ING-/ENF- kodları ve FRM-902/904/906 için sınırlı bir aday eşleştirme yapıldı. Fakülte adı eşleşmesi ve başlangıcın belirtilen tarih/pencereye düşmesi denetlendi: 210 aday kaydın 196'sı pencere dışında, 5'i içinde, 9'unda birim eşleşmesi yok. Bu bulgu kesin takvim ihlali kararı değildir; ders kapsamı ve ortak sınav eşleştirmesi onaylanmadı. Kayıtlar bu aday kontrolden dolayı ayrıca silinmedi. Denetim dosyasında kaynak ve referans satırları gösterilir.

## Mevcut girdiler ve çıktılar

`outputs_gui/schedule_output.csv`: 2.219 kayıt, 144.467 öğrenci-sınav toplamı; 28 Mart–12 Haziran 2023 tarihleri. Bu çıktı, çalışma alanındaki `data/Example_data.xlsx` dosyasının uygulama tarafından yüklenen kimlik ve öğrenci sayılarıyla birebir eşleşiyor. Ancak verilen beş ham dosyadan birinin doğrudan çıktısı olduğu doğrulanamıyor: kod kümeleri ve toplamlar farklı. Dönüşüm/filtreleme eşleme tablosu olmadan eksik kayıtlara ilişkin karar verilmedi.

Mevcut plan ve optimize slot özetlerinde toplam 144.467 korunuyor ve aynı 187 tarih–başlangıç saati kullanılıyor. Çıktıdaki satır öğrenci sayılarından slot toplamları doğru hesaplanmış. CPU = öğrenci × 0,02, RAM = öğrenci × 0,05 ve bant genişliği = öğrenci × 0,2 aritmetiği de tutarlı. Bunlar `config.py` varsayımlarıdır; sunucudan ölçülmüş CPU, RAM veya ağ kullanımı değildir.

`outputs_test` ve `outputs_test_all` çıktıları 2026 tarihli 10 kayıt ve 1.264 öğrenci-sınav toplamı içeriyor. Bunlar verilen 2023 ham dosyalarının optimizasyon sonucu olarak kullanılmamalıdır.

### Eşzamanlı yükte kritik fark

| Ölçüt | Plan | Optimize |
|---|---:|---:|
| Toplam öğrenci-sınav | 144.467 | 144.467 |
| En büyük aynı başlangıç saati yükü | 7.752 | 856 |
| İki saatlik örtüşmeler dahil en yüksek aktif yük | 7.898 | 8.577 |

İlk tepe için uygulama %88,96 azalma gösterir. Sınavların uygulamadaki varsayıma uygun olarak iki saat sürdüğü kabul edilip farklı başlangıç saatleri arasındaki örtüşmeler dahil edildiğinde tepe **%8,60 artar**. Plan tepesi 16 Nisan 00:01, optimize tepe 19 Nisan 13:25'tedir. İki saatlik varsayım altında her iki tepe de varsayılan 5.000 eşzamanlı öğrenci sınırını aşar.

Yeniden hesaplama yöntemi: her slotun öğrenci sayısını başlangıç olayında ekle, başlangıç + 2 saat olayında çıkar; aynı zaman damgasındaki değişimleri birleştir; sıralı kümülatif toplamın en büyüğünü al. Aralıklar `[başlangıç, bitiş)` olarak ele alındı; gece yarısı geçişi korunur. Bu sonuç gerçek katılım veya gerçek sunucu ölçümü değildir. Dosyalarda doğrulanmış süre/oturum telemetrisi bulunmadığından iki saat varsayımına bağlı bir model kontrolüdür.

Önceki “feasible” sonuçları mevcut kodun ayrı slot kontrollerini geçtiğini ifade eder. Süreleri örtüşen sınavlar için sunucu kapasitesinin sağlandığını veya öğrenci çakışmalarının olmadığını kanıtlamaz. Ders bazlı modda bireysel öğrenci kayıtları yoktur; kod öğrenci çakışmasını sıfır döndürse de gerçek çakışmasızlık doğrulanmış değildir.

## Bilimsel karşılaştırmanın hazırlanması

1. Ara sınav ve final için ayrı deney kümeleri belirle; final sürümünü yetkili kaynakla seç. Aynı ara sınav dosyasını iki kez kullanma.
2. Dışlama kurallarını deneyden önce sabitle. Eksik/gece yarısı kayıtlarının farklı ele alındığı duyarlılık senaryolarını ayrı raporla.
3. Gerçek sınav/şube birimini, ortak sınavları, süreleri, izinli tarih–saat pencerelerini ve sabit dersleri tanımla. Önceki kimliklerin yeni kimliklere dönüşümünü sakla.
4. Amaç fonksiyonu ve kapasite kontrolünü aktif zaman aralıklarındaki toplam yük üzerinden kur. CPU/RAM/ağ katsayılarını ölçümle destekle veya sonuçları açıkça varsayımsal model sonuçları olarak sun.
5. Her algoritma için aynı temiz başlangıç planını, aynı kısıtları ve karşılaştırılabilir hesaplama bütçesini kullan. Rastlantısal yöntemleri önceden belirlenmiş birden fazla seed ile çalıştır; dağılım ve başarısızlıkları raporla.
6. Yeni çıktılarda kimliklerin birebir korunmasını, kayıt/öğrenci toplamlarını, izinli zamanları, gerçek süre örtüşmelerini, kısıt ihlallerini ve metriklerin bağımsız yeniden hesabını kontrol et. Ortam sürümleri, seed, parametreler, kaynak dosya karması ve çalışma kimliğiyle çıktıyı arşivle.

Bu inceleme algoritmaları veya amaç fonksiyonunu değiştirmedi. Bulunan model sorunları giderilmeden yeni optimizasyon yüzdeleri bilimsel sonuç olarak onaylanmadı.

## Teslim ve doğrulama

- `tutarlilik_incelemesi.xlsx`: dosya özeti, ayrılan kayıtlar, kod çakışmaları, pivot farkları, sürüm farkları, tekil olmayan anahtarlar, mevcut çıktılar, eşzamanlı yük kontrolü, ortak ders referansı/kontrolü ve kaynak karmaları.
- `arasinav_temiz_aday.xlsx`: 3.337 satır, 176.196 öğrenci-sınav, 229 başlangıç slotu.
- `final_23mayis_temiz_aday.xlsx`: 3.699 satır, 176.564 öğrenci-sınav, 657 başlangıç slotu.
- `final_24mayis_temiz_aday.xlsx`: 3.697 satır, 176.654 öğrenci-sınav, 666 başlangıç slotu.
- `inceleme_ozeti.json`: sayısal bulgular, kaynak ve kullanılan kod karmaları, içe aktarma kontrolleri.

Üç temiz aday dosya mevcut uygulama yükleyicisiyle yeniden okundu. Kimlik tekilliği, satır sayısı, öğrenci toplamı ve tarih–başlangıç saati kümesi korundu. Her üç dosya da uygulamanın veri doğrulamasında sıfır hata ve sıfır uyarıyla geçti. Bu yapısal doğrulama, yukarıdaki bilimsel/model sınırlamalarını ortadan kaldırmaz. Denetim çalışma kitabı uygulamaya girdi olarak yüklenmemelidir; yalnızca `*_temiz_aday.xlsx` dosyaları girdi adayıdır.
