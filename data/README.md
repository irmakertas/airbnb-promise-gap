# Veri klasörü

Ham Inside Airbnb `listings.csv.gz` ve `reviews.csv.gz` dosyaları bu teslim paketinde bulunmamaktadır. Yeniden üretilebilirlik için:
- Şehir / snapshot tarihini,
- Kaynak indirme URL'sini,
- Ham dosyaların SHA-256 checksum değerlerini,
- Hazırlama adımlarını
ayrı bir manifestte saklayın.

Bu paket, analiz CSV'leri ve model batch sonuçlarını içerir; ham veriyi içermediği için veri hazırlama aşaması doğrudan yeniden çalıştırılamaz.
