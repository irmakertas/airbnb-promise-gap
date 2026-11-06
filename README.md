# Airbnb Promise Gap

LLM tabanlı bu çalışma, Airbnb ilan açıklamalarındaki açık vaatleri misafir yorumlarında bildirilen deneyimlerle karşılaştırır ve vaat paylarının platform puanlarıyla ilişkisini inceler.

## Pipeline
- Inside Airbnb ilan/yorum verisi hazırlama.
- Deterministik örneklem ve en fazla beş yorum/ilan retrieval.
- LM Studio üzerinde Qwen 3.5 4B ile en fazla dört vaat çıkarımı.
- Strict JSON Schema, alıntı ve review ID doğrulama.
- İnsan denetimi: 100/100 ilan tamamlandı.
- İlan düzeyi istatistiksel analiz ve HC3-robust çok değişkenli regresyon.
- Etkileşimli BI dashboard: `project/dashboard_2000.html`.

## Kurulum
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
LM Studio'da `qwen3.5-4b` modelini yükleyip yerel API'yi başlatın.

## Veri kaynağı ve literatür
- Inside Airbnb İstanbul ilan ve yorum verileri ekip tarafından 29 Ekim 2026 tarihinde indirilmiştir. Resmî indirme sayfasında İstanbul için listelenen veri sürümü 25 Eylül 2026'dır; indirme tarihi ve snapshot/sürüm tarihi ayrı tutulmuştur.
- Hedefli literatür taraması ve APA biçimli kaynakça: `project/documentation/11_literatur_taramasi_ve_kaynakca.md` (Airbnb ilan-yorum uyumu, LLM bilgi çıkarımı, insan denetimi ve Inside Airbnb veri kalitesi çalışmaları).
- Veri kaynağı ve snapshot manifesti: `DATA_SNAPSHOT_MANIFEST.md`.

## Güncel bulgular
2.000 benzersiz ilan seçilmiş; 72 placeholder çıkarıldıktan sonra 7.907 vaat ve 1.981 tamamlanmış ilan analiz edilmiştir. İnsan denetiminde 100 ilanın %32'sinde vaat kapsamı tam, %68'inde kısmi bulunmuştur. Model negatif vaat payı ile rating arasında negatif ilişki görülmüş; kontrol değişkenli HC3-robust OLS sonuçları da aynı yönde kalmıştır. Bulgular gözlemseldir, nedensellik değildir.

## Veri uyarısı
Ham `data/` dosyaları bu arşivde yoktur. İndirme tarihi 29 Ekim 2026 olarak kaydedilmiştir; İstanbul 25 Eylül 2026 sürümüne ait resmî listings/reviews indirme URL’leri manifestte kaydedilmiştir. SHA-256 değerleri, orijinal dosyalar teslim arşivinde bulunmadığından ekip bilgisayarında hesaplanmalıdır. Ayrıntı için `DATA_SNAPSHOT_MANIFEST.md` dosyasına bakınız. Tam veri hazırlama/LLM çalıştırma süreci için bunlar ayrıca sağlanmalıdır.
