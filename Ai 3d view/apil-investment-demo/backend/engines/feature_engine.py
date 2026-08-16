"""
APIL Feature Engineering Engine
Runs after Validation, before scoring engines. Produces feature_store.json

Converts raw data into validated, normalized, reliable metrics:
  - Fixes monthly-rent-stored-as-annual (detect & correct)
  - Removes price outliers (IQR)
  - Computes median price/rent per bed type with minimum sample enforcement
  - Normalizes growth (caps at ±80%)
  - Computes confidence-weighted features
  - Enforces minimum comparables (null instead of 0)
"""
from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from statistics import median as stats_median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.utils import (
    safe_float, safe_int, normalize_bed_type, parse_date, calculate_growth,
    save_json, load_json, clamp
)
from config.settings import PROJECTS_JSON, BACKEND_DATA_DIR

# ── Thresholds ─────────────────────────────────────────────────────────────

MONTHLY_RENT_THRESHOLD = 0.20     # if rent/price > 20%, likely monthly stored as annual
MAX_GROWTH_CAP = 80.0             # cap growth at ±80%
MIN_COMPARABLES = 3               # need at least 3 sales for median price
MIN_RENTALS = 3                   # need at least 3 rentals for median rent
IQR_MULTIPLIER = 2.0              # outlier detection sensitivity


def remove_outliers(values: list[float]) -> list[float]:
    """Remove IQR outliers from a list of values."""
    if len(values) < 4:
        return values
    sorted_v = sorted(values)
    n = len(sorted_v)
    q1 = sorted_v[n // 4]
    q3 = sorted_v[3 * n // 4]
    iqr = q3 - q1
    lower = q1 - IQR_MULTIPLIER * iqr
    upper = q3 + IQR_MULTIPLIER * iqr
    return [v for v in values if lower <= v <= upper]


def detect_and_fix_rent(rent: float, price: float) -> float:
    """
    If rent/price ratio is suspiciously high, the rent is likely monthly.
    Dubai annual rents are typically 4-10% of property price.
    If ratio > 20%, assume it's monthly and multiply by 12.
    But also cap the corrected annual rent at 12% yield.
    """
    if price <= 0 or rent <= 0:
        return rent
    ratio = rent / price
    if ratio > MONTHLY_RENT_THRESHOLD:
        # Likely monthly rent — multiply by 12
        corrected = rent * 12
        # But even corrected, cap at 12% yield
        max_annual = price * 0.12
        return min(corrected, max_annual)
    # Even normal rents: cap at 12% yield
    max_annual = price * 0.12
    return min(rent, max_annual)


def cap_growth(growth: float) -> float:
    """Cap growth at ±MAX_GROWTH_CAP to prevent impossible values."""
    if growth > MAX_GROWTH_CAP:
        return MAX_GROWTH_CAP
    if growth < -MAX_GROWTH_CAP:
        return -MAX_GROWTH_CAP
    return growth


def compute_project_features(project: dict) -> dict:
    """Compute validated, normalized features for a project."""
    sales = project.get("sales_history", [])
    rents = project.get("rent_history", [])
    listings = project.get("listings", [])

    # ── Group by bed type ──────────────────────────────────────────────────
    sales_by_bed: dict[str, list[dict]] = defaultdict(list)
    rents_by_bed: dict[str, list[dict]] = defaultdict(list)

    for s in sales:
        bed = normalize_bed_type(s.get("beds", ""))
        sales_by_bed[bed].append(s)

    for r in rents:
        bed = normalize_bed_type(r.get("beds", ""))
        rents_by_bed[bed].append(r)

    # ── Compute per-bed-type features ──────────────────────────────────────
    unit_features = {}
    all_beds = set(list(sales_by_bed.keys()) + list(rents_by_bed.keys()))

    for bed in all_beds:
        bed_sales = sales_by_bed.get(bed, [])
        bed_rents = rents_by_bed.get(bed, [])

        # Prices — remove outliers
        prices = [safe_float(s.get("price")) for s in bed_sales if safe_float(s.get("price")) > 0]
        prices_sqft = [safe_float(s.get("price_sqft")) for s in bed_sales if safe_float(s.get("price_sqft")) > 0]
        prices = remove_outliers(prices)
        prices_sqft = remove_outliers(prices_sqft)

        # Rents — detect and fix monthly-as-annual, then cap
        raw_rents = [safe_float(r.get("annual_rent")) for r in bed_rents if safe_float(r.get("annual_rent")) > 0]
        med_price = stats_median(prices) if prices else 0
        fixed_rents = [detect_and_fix_rent(r, med_price) for r in raw_rents]
        fixed_rents = [r for r in fixed_rents if r > 0]

        # Medians with minimum sample enforcement
        med_price = stats_median(prices) if len(prices) >= MIN_COMPARABLES else None
        med_price_sqft = stats_median(prices_sqft) if len(prices_sqft) >= MIN_COMPARABLES else None
        med_rent = stats_median(fixed_rents) if len(fixed_rents) >= MIN_RENTALS else None

        # Yield — only if both price and rent are valid
        yield_pct = None
        if med_price and med_price and med_price > 0 and med_rent and med_rent > 0:
            yield_pct = round((med_rent / med_price) * 100, 2)
            # Sanity check: cap yield at 12%
            if yield_pct > 12.0:
                yield_pct = 12.0
                med_rent = round(med_price * 0.12)

        # Growth — capped
        growth_3m = cap_growth(calculate_growth(bed_sales, 3))
        growth_6m = cap_growth(calculate_growth(bed_sales, 6))
        growth_12m = cap_growth(calculate_growth(bed_sales, 12))

        unit_features[bed] = {
            "medianPrice": round(med_price) if med_price else None,
            "medianPriceSqft": round(med_price_sqft) if med_price_sqft else None,
            "medianRent": round(med_rent) if med_rent else None,
            "rentalYield": yield_pct,
            "transactionCount": len(bed_sales),
            "rentalCount": len(fixed_rents),
            "growth3m": growth_3m,
            "growth6m": growth_6m,
            "growth12m": growth_12m,
            "hasSufficientData": med_price is not None and med_rent is not None,
        }

    # ── Project-level features ─────────────────────────────────────────────
    all_prices_sqft = [safe_float(s.get("price_sqft")) for s in sales if safe_float(s.get("price_sqft")) > 0]
    all_prices_sqft = remove_outliers(all_prices_sqft)

    all_rents_raw = [safe_float(r.get("annual_rent")) for r in rents if safe_float(r.get("annual_rent")) > 0]
    med_proj_price = stats_median(all_prices_sqft) if len(all_prices_sqft) >= MIN_COMPARABLES else None
    med_proj_rent = stats_median(all_rents_raw) if len(all_rents_raw) >= MIN_RENTALS else None

    proj_growth_3m = cap_growth(calculate_growth(sales, 3))
    proj_growth_6m = cap_growth(calculate_growth(sales, 6))
    proj_growth_12m = cap_growth(calculate_growth(sales, 12))

    # ── Confidence score ───────────────────────────────────────────────────
    confidence = 100
    if len(sales) < 10:
        confidence -= 30
    if len(rents) < 5:
        confidence -= 20
    if med_proj_price is None:
        confidence -= 20
    if med_proj_rent is None:
        confidence -= 15
    confidence = int(clamp(confidence, 0, 100))

    return {
        "projectName": project.get("name"),
        "area": project.get("area", "Unknown"),
        "slug": project.get("slug", project.get("name", "").lower().replace(" ", "-")),
        "unitFeatures": unit_features,
        "projectMedianPriceSqft": round(med_proj_price) if med_proj_price else None,
        "projectMedianRent": round(med_proj_rent) if med_proj_rent else None,
        "projectGrowth3m": proj_growth_3m,
        "projectGrowth6m": proj_growth_6m,
        "projectGrowth12m": proj_growth_12m,
        "totalSales": len(sales),
        "totalRents": len(rents),
        "totalListings": len(listings),
        "confidenceScore": confidence,
        "computedAt": datetime.now().isoformat(),
    }


def run():
    print("[Feature Engine] Starting...")
    projects = load_json(PROJECTS_JSON)

    results = []
    for project in projects:
        features = compute_project_features(project)
        results.append(features)

    output_file = BACKEND_DATA_DIR / "feature_store.json"
    save_json(output_file, results)
    print(f"[Feature Engine] Computed features for {len(results)} projects")
    return results


if __name__ == "__main__":
    run()
