"""
ETL: Import Google Maps review data for developers.
Loads pre-scraped Google ratings from server files.
"""
import json
import os
from config.settings import save_json, BACKEND_DATA_DIR


def import_google_reviews() -> dict:
    """Load pre-scraped Google review ratings."""
    path = os.path.join("/tmp", "dev_google_reviews.json")
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        print(f"  Loaded {len(data)} Google review records")
        return data
    print("  [WARN] No Google reviews file found at /tmp/dev_google_reviews.json")
    return {}


def run():
    print("[ETL] Importing Google reviews...")
    reviews = import_google_reviews()
    result = {
        "reviews": reviews,
        "imported_at": __import__("datetime").datetime.now().isoformat(),
    }
    save_json(BACKEND_DATA_DIR / "google_warehouse.json", result)
    print(f"[ETL] Google warehouse saved: {len(reviews)} developers with reviews")
    return result


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    run()
