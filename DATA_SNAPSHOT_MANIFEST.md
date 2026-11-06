# Veri Snapshot ve Kaynak Manifesti

## Veri kökeni

| Alan | Kayıt | Durum |
|---|---|---|
| Veri sağlayıcısı | Inside Airbnb (Housing Justice Data Lab) | Resmî kaynak |
| Şehir / market | Istanbul, Marmara, Turkey | Resmî indirme sayfasıyla eşleşiyor |
| Ekip tarafından bildirilen indirme tarihi | **29 Ekim 2026** | Kullanıcı/ekip beyanı |
| Inside Airbnb sayfasında görünen veri sürümü | **25 Eylül 2026** | Resmî sayfada İstanbul başlığı altında listeleniyor |
| İlan dosyası | `listings.csv.gz` | Resmî indirme bağlantısı |
| Yorum dosyası | `reviews.csv.gz` | Resmî indirme bağlantısı |
| İlan dosyası URL | https://data.insideairbnb.com/turkey/marmara/istanbul/2026-09-25/data/listings.csv.gz | Resmî bağlantı |
| Yorum dosyası URL | https://data.insideairbnb.com/turkey/marmara/istanbul/2026-09-25/data/reviews.csv.gz | Resmî bağlantı |
| İndirme sayfası | https://insideairbnb.com/get-the-data/ | Resmî kaynak |
| Veri politikası | https://insideairbnb.com/data-policies/ | Resmî kaynak |
| Lisans | Creative Commons Attribution 4.0 International (CC BY 4.0) | Inside Airbnb politika sayfasında belirtiliyor |

## İndirme tarihi ile snapshot tarihinin ayrımı

Ekip, dosyaları 29 Ekim 2026 tarihinde indirdiğini bildirmiştir. Inside Airbnb'nin veri indirme sayfası İstanbul verisini 25 Eylül 2026 sürümü altında listelemektedir. Bu nedenle 25 Eylül 2026, kullanılan veri setinin sayfada görünen sürüm/snapshot tarihi; 29 Ekim 2026 ise ekibin indirme tarihidir. İki tarih birbirinin yerine kullanılmamalıdır.

## Veri seti kapsamı ve analiz örneklemi

- Kaynak tablolar: `listings.csv.gz` ve `reviews.csv.gz`.
- Proje pipeline'ında iki ayrı 1.000 ilanlık örneklem işlenmiştir; ikinci örneklemde ilk grubun listing ID'leri dışlanmıştır.
- Birleştirilmiş analizde 2.000 benzersiz ilan seçilmiş, 72 placeholder çıktı dışlandıktan sonra 1.981 ilan ve 7.907 vaat analiz edilmiştir.
- İnsan denetimi, ilk 1.000 ilanlık gruptan seed `20261101` ile seçilen 100 ilanı kapsamaktadır.

## SHA-256 bütünlük doğrulaması

Ham `.csv.gz` dosyaları dokümantasyon paketine eklenmemiştir. Bu nedenle hash değerleri bu teslim sırasında hesaplanamamıştır. Dosyalar ekip bilgisayarında saklanıyorsa aşağıdaki komutlarla hash alınmalı ve çıktılar bu manifestin sonuna eklenmelidir:

```powershell
Get-FileHash .\listings.csv.gz -Algorithm SHA256
Get-FileHash .\reviews.csv.gz -Algorithm SHA256
```

| Dosya | SHA-256 |
|---|---|
| `listings.csv.gz` | Henüz hesaplanmadı – orijinal dosya yerel ortamda gerekli |
| `reviews.csv.gz` | Henüz hesaplanmadı – orijinal dosya yerel ortamda gerekli |

## Atıf ve kullanım

Önerilen veri atfı:

> Inside Airbnb. (2026). *Istanbul Airbnb listings and reviews data, 25 September 2026* [Data set]. Housing Justice Data Lab. https://insideairbnb.com/get-the-data/ (Downloaded 29 October 2026).

Inside Airbnb akademik yayınlarda veri sağlayıcısının, lokasyonun, veri toplama tarihinin ve kullanılan veri setlerinin belirtilmesini; ayrıca veri setinin kaynakçada ayrı bir kayıt olarak gösterilmesini istemektedir. Veri sağlayıcısının CC BY 4.0 lisans koşulları ve atıf talebi takip edilmelidir. Ham verinin tamamını proje ZIP'ine yeniden koymak yerine kaynak bağlantısını ve veri manifestini sunmak tercih edilmiştir.

## Kaynak kayıtları

- Inside Airbnb – Get the Data: https://insideairbnb.com/get-the-data/
- Inside Airbnb – Data Policies: https://insideairbnb.com/data-policies/
- İstanbul 25 Eylül 2026 listings: https://data.insideairbnb.com/turkey/marmara/istanbul/2026-09-25/data/listings.csv.gz
- İstanbul 25 Eylül 2026 reviews: https://data.insideairbnb.com/turkey/marmara/istanbul/2026-09-25/data/reviews.csv.gz

## SHA-256 Checksums

| File | SHA-256 |
|---|---|
| listings.csv.gz | 31F2E0429015E9111E06360F0124E2B4C6B1F24AC0D1B702290F4572E4BB8D21 |
| reviews.csv.gz | E66D7B1F3459067C2ADB529D184CA66EDE22420441373D072270989230B2EFA3 |