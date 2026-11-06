
from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

listings = pd.read_csv(
    RAW_DIR / "listings.csv.gz",
    compression="gzip",
    low_memory=False
)

listings["id"] = listings["id"].astype(str)
listings["description"] = listings["description"].fillna("").str.strip()

listings["review_count"] = pd.to_numeric(
    listings["number_of_reviews"], errors="coerce"
)

listings["review_scores_rating"] = pd.to_numeric(
    listings["review_scores_rating"], errors="coerce"
)

eligible = listings[
    (listings["description"] != "")
    & (listings["review_count"] >= 10)
].copy()

rated = eligible[
    eligible["review_scores_rating"].notna()
    & (eligible["review_scores_rating"] > 0)
].copy()

eligible.to_csv(
    PROCESSED_DIR / "eligible_listings.csv",
    index=False,
    encoding="utf-8-sig"
)

rated.to_csv(
    PROCESSED_DIR / "rated_listings.csv",
    index=False,
    encoding="utf-8-sig"
)

reviews = pd.read_csv(
    RAW_DIR / "reviews.csv.gz",
    compression="gzip",
    low_memory=False
)

reviews["listing_id"] = reviews["listing_id"].astype(str)
reviews["comments"] = reviews["comments"].fillna("").str.strip()

reviews = reviews[reviews["comments"] != ""].copy()

eligible_ids = set(eligible["id"])
eligible_reviews = reviews[
    reviews["listing_id"].isin(eligible_ids)
].copy()

eligible_reviews.to_csv(
    PROCESSED_DIR / "eligible_reviews.csv",
    index=False,
    encoding="utf-8-sig"
)

print("=" * 50)
print("VERİ HAZIRLAMA RAPORU")
print("=" * 50)
print(f"Başlangıç ilan sayısı: {len(listings):,}")
print(f"Açıklaması dolu ve en az 10 yorumlu ilan: {len(eligible):,}")
print(f"Bunlardan puanı bulunan ilan: {len(rated):,}")
print(f"Temiz yorum sayısı: {len(reviews):,}")
print(f"Uygun ilanlara ait yorum sayısı: {len(eligible_reviews):,}")
print(f"Uygun ilanların yorum dosyasında bulunan ID sayısı: "
      f"{eligible_reviews['listing_id'].nunique():,}")
print("\nDosyalar data/processed klasörüne kaydedildi.")
