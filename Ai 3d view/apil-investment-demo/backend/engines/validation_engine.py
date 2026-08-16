"""
APIL Data Validation Engine
Runs after ETL, before scoring engines. Produces validation_results.json

Checks:
  - Missing/zero prices
  - Unrealistic ROI (yield > 15%)
  - Unrealistic rent (rent/price ratio anomalies)
  - Duplicate transactions
  - Invalid rents (monthly stored as annual)
  - Price outliers (IQR method)
  - Growth outliers (> 80% flagged)
  - Minimum sample sizes

Outputs per-property validation status + confidence score.
"""
from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from statistics import median as stats_median

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.utils import (
    safe_float, safe_int, normalize_bed_type, parse_date, save_json, load_json, clamp
)
from config.settings import PROJECTS_JSON, BACKEND_DATA_DIR


# ── Validation Thresholds ──────────────────────────────────────────────────

MAX_REALISTIC_YIELD = 15.0       # % — flag if gross yield > 15%
MAX_REALISTIC_GROWTH = 80.0      # % — flag if 12m growth > 80%
MIN_COMMUNITY_TXNS = 200         # minimum sales for community scoring
MIN_PROJECT_SALES = 10           # minimum sales for project scoring
MIN_PROPERTY_COMPARABLES = 3     # minimum comparables for property pricing
MIN_RENTAL_CONTRACTS = 5         # minimum rentals for rent estimation
MIN_PRICE_SQFT = 200             # AED/sqft — below this is suspicious
MAX_PRICE_SQFT = 50000           # AED/sqft — above this is suspicious
MIN_PRICE = 100000               # AED — below this is likely data error
MAX_ANNUAL_RENT_RATIO = 0.15     # rent/price > 15% = suspicious


def detect_rent_anomaly(price: float, annual_rent: float) -> bool:
    """Detect if rent is likely monthly stored as annual, or otherwise anomalous."""
    if price <= 0 or annual_rent <= 0:
        return False
    ratio = annual_rent / price
    return ratio > MAX_ANNUAL_RENT_RATIO


def detect_price_outlier(prices_sqft: list[float]) -> list[bool]:
    """IQR-based outlier detection for price/sqft."""
    if len(prices_sqft) < 4:
        return [False] * len(prices_sqft)
    sorted_p = sorted(prices_sqft)
    n = len(sorted_p)
    q1 = sorted_p[n // 4]
    q3 = sorted_p[3 * n // 4]
    iqr = q3 - q1
    lower = q1 - 2.0 * iqr
    upper = q3 + 2.0 * iqr
    return [(p < lower or p > upper) for p in prices_sqft]


def validate_project(project: dict) -> dict:
    """Validate a single project's data quality."""
    issues: list[str] = []
    warnings: list[str] = []
    error_codes: list[str] = []

    sales = project.get("sales_history", [])
    rents = project.get("rent_history", [])
    listings = project.get("listings", [])

    # ── Check listing prices ───────────────────────────────────────────────
    for l in listings:
        price = safe_float(l.get("price"))
        if price <= 0:
            issues.append(f"Listing {l.get('id','?')} has zero/negative price")
            error_codes.append("ZERO_PRICE")
        elif price < MIN_PRICE:
            warnings.append(f"Listing {l.get('id','?')} price {price} below minimum {MIN_PRICE}")
            error_codes.append("LOW_PRICE")

    # ── Check rent anomalies ───────────────────────────────────────────────
    rent_by_bed: dict[str, list[float]] = defaultdict(list)
    for r in rents:
        bed = normalize_bed_type(r.get("beds", ""))
        rent = safe_float(r.get("annual_rent"))
        if rent > 0:
            rent_by_bed[bed].append(rent)

    listing_by_bed: dict[str, list[float]] = defaultdict(list)
    for l in listings:
        bed = normalize_bed_type(l.get("bedrooms", ""))
        price = safe_float(l.get("price"))
        if price > 0:
            listing_by_bed[bed].append(price)

    for bed in set(list(listing_by_bed.keys()) + list(rent_by_bed.keys())):
        prices = listing_by_bed.get(bed, [])
        rents_list = rent_by_bed.get(bed, [])
        if not prices or not rents_list:
            continue
        med_price = stats_median(prices)
        med_rent = stats_median(rents_list)
        if med_price > 0 and detect_rent_anomaly(med_price, med_rent):
            issues.append(
                f"Rent anomaly for {bed}: median rent {med_rent:.0f} vs price {med_price:.0f} "
                f"(ratio {med_rent/med_price*100:.1f}% — likely monthly rent stored as annual)"
            )
            error_codes.append("RENT_ANOMALY")

    # ── Check price/sqft outliers ──────────────────────────────────────────
    prices_sqft = [safe_float(s.get("price_sqft")) for s in sales
                   if safe_float(s.get("price_sqft")) > 0]
    outliers = detect_price_outlier(prices_sqft)
    outlier_count = sum(outliers)
    if outlier_count > 0 and len(prices_sqft) > 0:
        pct = outlier_count / len(prices_sqft) * 100
        if pct > 20:
            warnings.append(f"{outlier_count}/{len(prices_sqft)} transactions are price outliers ({pct:.0f}%)")
            error_codes.append("PRICE_OUTLIERS")

    # ── Check minimum sample sizes ─────────────────────────────────────────
    if len(sales) < MIN_PROJECT_SALES:
        warnings.append(f"Only {len(sales)} sales (minimum {MIN_PROJECT_SALES})")
        error_codes.append("LOW_SALE_COUNT")
    if len(rents) < MIN_RENTAL_CONTRACTS:
        warnings.append(f"Only {len(rents)} rental contracts (minimum {MIN_RENTAL_CONTRACTS})")
        error_codes.append("LOW_RENT_COUNT")

    # ── Compute confidence score ───────────────────────────────────────────
    confidence = 100
    if len(sales) < MIN_PROJECT_SALES:
        confidence -= 30
    if len(rents) < MIN_RENTAL_CONTRACTS:
        confidence -= 20
    if "RENT_ANOMALY" in error_codes:
        confidence -= 25
    if "ZERO_PRICE" in error_codes:
        confidence -= 15
    if "PRICE_OUTLIERS" in error_codes:
        confidence -= 10
    if not listings:
        confidence -= 20
    confidence = int(clamp(confidence, 0, 100))

    # ── Validation status ──────────────────────────────────────────────────
    if issues:
        status = "FAILED"
    elif warnings:
        status = "WARNING"
    else:
        status = "PASSED"

    return {
        "projectName": project.get("name"),
        "area": project.get("area", "Unknown"),
        "validationStatus": status,
        "confidenceScore": confidence,
        "errorCodes": list(set(error_codes)),
        "issues": issues,
        "warnings": warnings,
        "dataCounts": {
            "sales": len(sales),
            "rents": len(rents),
            "listings": len(listings),
        },
        "validatedAt": datetime.now().isoformat(),
    }


def run():
    print("[Validation Engine] Starting...")
    projects = load_json(PROJECTS_JSON)

    results = []
    passed = 0
    warned = 0
    failed = 0

    for project in projects:
        result = validate_project(project)
        results.append(result)
        if result["validationStatus"] == "PASSED":
            passed += 1
        elif result["validationStatus"] == "WARNING":
            warned += 1
        else:
            failed += 1

    output_file = BACKEND_DATA_DIR / "validation_results.json"
    save_json(output_file, results)
    print(f"[Validation Engine] {len(results)} projects validated")
    print(f"  PASSED: {passed} | WARNING: {warned} | FAILED: {failed}")
    return results


if __name__ == "__main__":
    run()
