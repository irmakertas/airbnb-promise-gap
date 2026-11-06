# 2.000 İlan Detaylı Veri Analizi

Bu rapor 2.000 benzersiz ilanın LLM çıktılarını ilan düzeyinde birleştirir. 72 placeholder satırı çıkarılmıştır. Ana negatif vaat payı model etiketlerini temel alır; kanıt doğrulamasından geçen vaatler için ayrı duyarlılık ölçüsü hesaplanmıştır.

## 1. Veri kapsamı

- Seçilen ilan: **2.000**
- Ham vaat satırı: **7.979**
- Placeholder: **72**
- Analiz edilen vaat: **7.907**
- Vaat içeren tamamlanmış ilan: **1.981**
- Eksik/başarısız ilan: **19** (18 placeholder-only, 1 API/schema hatası)
- Otomatik kanıt kontrolünden geçen vaat: **7.033 / 7.907 (%88,95)**
- Kaynak yorumla eşleşen alıntı oranı: **%89,74**

## 2. Vaat etiketleri

| Etiket | Sayı | Oran |
|---|---:|---:|
| positive | 6.302 | %79,70 |
| negative | 982 | %12,42 |
| mixed | 590 | %7,46 |
| insufficient_evidence | 33 | %0,42 |

`insufficient_evidence` başarısız vaat değildir. `mixed` ana negatif oranında ayrı tutulmuştur.

## 3. Kategori analizi

| Kategori | Vaat | Negative | Gözlenen negatif oranı | Evidence valid |
|---|---:|---:|---:|---:|
| access | 237 | 107 | %45.73 | %81.86 |
| amenities | 539 | 161 | %30.32 | %87.38 |
| comfort | 607 | 157 | %25.91 | %91.27 |
| other | 1,169 | 286 | %24.68 | %84.69 |
| accuracy | 107 | 22 | %20.95 | %94.39 |
| safety_privacy | 69 | 12 | %17.65 | %85.51 |
| cleanliness | 1,706 | 145 | %8.53 | %90.15 |
| value | 97 | 6 | %6.25 | %92.78 |
| location | 1,520 | 57 | %3.75 | %85.53 |
| host_communication | 1,856 | 29 | %1.56 | %93.53 |

Kategori ataması keyword tabanlı ve tek etiketlidir. Oranlar keşifseldir; özellikle düşük sayılı kategoriler ve `other` grubu manuel inceleme gerektirir.

## 4. İlan düzeyinde puan ilişkisi

- Ortalama rating: **4,725** (SD=0,225; medyan=4,770).
- Ortalama model negatif vaat payı: **0,125** (SD=0,182; medyan=0).
- En az bir negatif etiketli ilan: **765/1.981 (%38,62)**.
- Negatif etiketli ilan rating ortalaması: **4,666**.
- Negatif etiketsiz ilan rating ortalaması: **4,762**.
- Ortalama fark: **-0,096** puan.
- Spearman: **rho=-0,255**, n=1.981, p=9,77×10⁻³¹.

## 5. İnsan denetimi

İlk 1.000 ilanlık setten tabakalı seçilmiş 100 ilan denetlenmiştir; 100/100 kayıt tamamlanmıştır.

- Vaat kapsamı: 32 complete (%32), 68 partial (%68), 0 missed.
- Etiket uyumu: 76 all_agree (%76), 24 some_disagree (%24), 0 all_disagree.
- Kanıt desteği: 68 all_supported (%68), 32 some_unsupported (%32), 0 all_unsupported.

Bu oranlar ilan düzeyinde denetim kategorileridir; precision/recall veya tüm 2.000 ilan için ağırlıklı doğruluk tahmini değildir. Çift kodlayıcı kaydı olmadığından Cohen kappa hesaplanamamıştır.

## 6. Çok değişkenli analiz

HC3-robust OLS modelleri yorum sayısı, oda tipi, mülk tipi ve mahalleyi kontrol eder. 20'den az gözlem içeren kategoriler `Other (<20)` altında birleştirilmiştir. Tasarım matrisi 24 sütunlu tam rank; maksimum leverage yaklaşık 0,080'dür.

Genel rating için model negatif vaat payı katsayısı **-0,302** (%95 GA [-0,361; -0,243], n=1.981, R²=0,159, Holm p=4,52×10⁻²²). Alt puanların yedisinde de katsayılar negatiftir.

Kanıt-geçerli `verified_negative_share` ölçüsüyle 1.967 ilan kalır. Genel rating katsayısı **-0,254** (%95 GA [-0,306; -0,203], Holm p=1,23×10⁻²⁰). Bu duyarlılık analizi ana sonucun yönünü korur.

## 7. Yorum

Model etiketli negatif vaat payı ile platform rating'i arasında negatif ilişki vardır. İlişki, gözlenen kontrol değişkenleri eklendiğinde ve otomatik kanıt kontrolünden geçen vaatlerle ölçüm tekrarlandığında da sürmektedir. İnsan denetiminde kısmi vaat kapsamı ve bazı desteklenmeyen kanıtlar bulunduğundan sonuçlar model ölçüm hatası riski taşır. Nedensellik çıkarılamaz.

## 8. Üretilen dosyalar

- `listing_level_analysis_2000.csv`: ilan başına tek satır; ana ve kanıt-geçerli oranlar.
- `category_analysis_2000.csv`: kategori ve etiket özeti.
- `promise_analysis_2000.csv`: tekrarlanan vaat ifadeleri.
- `analysis_summary.csv`: temel KPI'lar.
- `multivariable_regression_2000.json` ve `multivariable_regression_summary.csv`: regresyon ayrıntıları.
- `10_human_audit_raporu.md`: audit değerlendirmesi.
