
from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")

listings_path = RAW_DIR / "listings.csv.gz"
reviews_path = RAW_DIR / "reviews.csv.gz"

print("=" * 60)
print("1. İLAN VERİSİ")
print("=" * 60)

listings = pd.read_csv(listings_path, compression="gzip", low_memory=False)

print(f"Toplam ilan satırı: {len(listings):,}")
print(f"Toplam sütun: {len(listings.columns)}")
print(f"Tekil ilan ID sayısı: {listings['id'].nunique():,}"
      if "id" in listings.columns else "id sütunu bulunamadı")

print("\nSütunlar:")
print(list(listings.columns))

important_listing_cols = [
    "id", "name", "description", "neighborhood",
    "neighbourhood_cleansed", "property_type", "room_type",
    "price", "number_of_reviews", "review_scores_rating",
    "latitude", "longitude"
]

print("\nÖnemli sütunların eksik verileri:")
for col in important_listing_cols:
    if col in listings.columns:
        missing = listings[col].isna().sum()
        pct = missing / len(listings) * 100 if len(listings) else 0
        print(f"{col}: {missing:,} eksik (%{pct:.2f})")

if "id" in listings.columns:
    print(f"\nTekrarlanan ilan ID satırı: "
          f"{listings['id'].duplicated().sum():,}")

print("\n" + "=" * 60)
print("2. MİSAFİR YORUMLARI")
print("=" * 60)

reviews = pd.read_csv(
    reviews_path,
    compression="gzip",
    usecols=lambda col: col in {
        "listing_id", "id", "date", "reviewer_id", "comments"
    },
    low_memory=False
)

print(f"Toplam yorum satırı: {len(reviews):,}")
print(f"Toplam sütun: {len(reviews.columns)}")
print("\nYorum sütunları:")
print(list(reviews.columns))

if "listing_id" in reviews.columns:
    print(f"Yorumlardaki tekil ilan ID sayısı: "
          f"{reviews['listing_id'].nunique():,}")

if "id" in reviews.columns:
    print(f"Tekrarlanan yorum ID satırı: "
          f"{reviews['id'].duplicated().sum():,}")

if "comments" in reviews.columns:
    print(f"Boş yorum sayısı: {reviews['comments'].isna().sum():,}")

if "date" in reviews.columns:
    dates = pd.to_datetime(reviews["date"], errors="coerce")
    print(f"En eski yorum tarihi: {dates.min()}")
    print(f"En yeni yorum tarihi: {dates.max()}")

print("\n" + "=" * 60)
print("3. İLAN-YORUM EŞLEŞMESİ")
print("=" * 60)

if "id" in listings.columns and "listing_id" in reviews.columns:
    listing_ids = set(listings["id"].astype(str))
    review_listing_ids = set(reviews["listing_id"].dropna().astype(str))

    matched = listing_ids & review_listing_ids
    unmatched = review_listing_ids - listing_ids

    print(f"Yorum dosyasında eşleşen ilan sayısı: {len(matched):,}")
    print(f"İlan dosyasında bulunmayan yorum ilan ID'si: "
          f"{len(unmatched):,}")

print("\nİnceleme tamamlandı. Henüz hiçbir veri değiştirilmedi.")
