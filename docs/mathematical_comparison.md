# Matematiksel karşılaştırma formülasyonu

Kaynak aileler: kullanıcının Excel dosyası, Table 1. MIP satırları 2, 4 ve 5; hedef programlama satırı 3; ILP / 0-1 model satırları 6, 8, 9 ve 10. Satır 7'deki sütun üretimi özgün fiyatlama modeli bulunmadığından ayrı uygulanmaz. Modeller aynı çevrimiçi kapasite problemine uyarlanmıştır.

E: sınavlar; T: aday başlangıçlar; H: başlangıç/bitişlerin oluşturduğu temel aralıklar.
`s_i`: katılım; `q_th`: t penceresi h aralığında etkinse 1; `C`: kapasite.

İkili temel model:

- `x_it ∈ {0,1}`; her i için `sum_t x_it = 1`.
- `L_h = sum_i sum_t s_i q_th x_it`.
- `L_h <= P <= C`.
- Amaç: `min P`.

Bu sürümde aynı katılım sayısına sahip sınavlar başka kısıtlarla ayrışmaz. Her c katılım sınıfında n_c sınav için `z_ct ∈ {0,...,n_c}`, `sum_t z_ct = n_c`, `L_h = sum_c sum_t c q_th z_ct` kullanılır. Her z çözümü aynı sınıftaki sınavlara birebir dağıtılır; sınav bölünmez.

MIP: z tam sayılı, P ve ara yükler süreklidir. CBC ile çözülür. Yüklerin eşitlik tanımları ve z'nin tamsayılılığı nedeniyle gerçekleşen yük yine tamsayıdır.

ILP: z, ara yükler ve P tam sayılıdır. Aynı lineer model CP-SAT ile çözülür. CP-SAT yalnız ilk çözümde durmaz; P'yi minimize eder.

Hedef programlama: B = max(en büyük sınav, toplam katılımcı-dakika / kullanılabilir dakika değerinin tavanı). `P=B+d`, `d>=0`, amaç `min d`. CBC kullanılır. Tek hedefli bu sürüm min P'ye eşdeğerdir; kullanıcı tercihi veya bulanık üyelik parametresi uydurulmaz.

Makale yöntemi: ayrık başlangıç alanları ve cumulative kapasite kısıtıyla CP-SAT ilk olurlu çözümü arar (zaman bütçesinin en çok %60'ı). Kalan bütçede GD taşıma/takas komşuluğu uygular; kapasite aşımı kabul edilmez. Bulunan en iyi çizelge korunur. Bu sürümde GD evrensel optimum kanıtı üretmez.

Bütün sonuçlar bağımsız zaman-aralığı yük hesabıyla doğrulanır. Matematiksel modellerin ortak alt sınırı, makale yönteminin sonucu dahil bütün olurlu çizelgelere uygulanabilir. Hiçbir kaynakta belirtilmeyen kurum/derslik/gözetmen kuralları bu modelde varmış gibi gösterilmez.
