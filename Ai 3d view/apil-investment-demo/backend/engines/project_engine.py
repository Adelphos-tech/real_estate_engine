"""
APIL Project Intelligence Engine
Runs daily. Produces project_scores.json

Pipeline:
  Project → Transactions → Developer → Inventory → Supply →
  Demand → Growth → Project Score
"""
from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.utils import (
    clamp, median, safe_float, safe_int, normalize_bed_type,
    parse_date, calculate_growth, risk_from_score, save_json, load_json
)
from config.settings import PROJECT_SCORES_FILE, PROJECTS_JSON, DEVELOPER_SCORES_FILE


def load_developer_scores() -> dict[str, dict]:
    if DEVELOPER_SCORES_FILE.exists():
        devs = load_json(DEVELOPER_SCORES_FILE)
        return {d["name"]: d for d in devs}
    return {}


def match_developer_for_project(project_name: str, dev_scores: dict) -> dict | None:
    """Match project to developer using developer aliases from scores."""
    clean = project_name.upper().strip()
    for dev_name, dev_data in dev_scores.items():
        aliases = dev_data.get("aliases", [])
        for alias in aliases:
            if alias in clean:
                return dev_data
    return None


def compute_unit_scores(project: dict) -> list[dict]:
    bed_groups: dict[str, list[dict]] = defaultdict(list)
    rent_groups: dict[str, list[dict]] = defaultdict(list)

    for sale in project.get("sales_history", []):
        bed = normalize_bed_type(sale.get("beds", ""))
        price = safe_float(sale.get("price"))
        area = safe_float(sale.get("area_sqft"))
        if price <= 0 or area <= 0:
            continue
        # Skip sales with area > 5000 sqft — these are plot/land area, not unit area
        if area > 5000:
            continue
        sale = {**sale, "price_sqft": price / area}
        bed_groups[bed].append(sale)

    for rent in project.get("rent_history", []):
        bed = normalize_bed_type(rent.get("beds", ""))
        rent_groups[bed].append(rent)

    all_beds = set(list(bed_groups.keys()) + list(rent_groups.keys()))
    units = []

    for bed_type in all_beds:
        sales = bed_groups.get(bed_type, [])
        rents = rent_groups.get(bed_type, [])

        prices = [safe_float(s.get("price")) for s in sales if safe_float(s.get("price")) > 0]
        prices_sqft = [safe_float(s.get("price_sqft")) for s in sales if safe_float(s.get("price_sqft")) > 0]
        rents_annual = [safe_float(r.get("annual_rent")) for r in rents if safe_float(r.get("annual_rent")) > 0]
        areas = [safe_float(s.get("area_sqft")) for s in sales if safe_float(s.get("area_sqft")) > 0]

        # Remove IQR outliers from price/sqft
        if len(prices_sqft) >= 4:
            sorted_p = sorted(prices_sqft)
            n = len(sorted_p)
            q1 = sorted_p[n // 4]
            q3 = sorted_p[3 * n // 4]
            iqr = q3 - q1
            lower = q1 - 2.0 * iqr
            upper = q3 + 2.0 * iqr
            prices_sqft = [p for p in prices_sqft if lower <= p <= upper]

        med_price = median(prices)
        med_price_sqft = median(prices_sqft)
        med_rent = median(rents_annual)
        avg_area = median(areas)

        # Cap yield at 12%
        yield_pct = (med_rent / med_price * 100) if med_price > 0 and med_rent > 0 else 0
        if yield_pct > 12.0:
            yield_pct = 12.0
        txn_count = len(sales)
        demand_score = round(clamp(txn_count * 8, 0, 100))

        yield_score = clamp(yield_pct * 6, 0, 100)
        liquidity_score = clamp(txn_count * 7, 0, 100)
        stability_score = 70 if med_price_sqft > 0 else 40

        unit_score = round(
            yield_score * 0.35 + demand_score * 0.25 + stability_score * 0.20 + liquidity_score * 0.20
        )

        units.append({
            "bedType": bed_type,
            "unitScore": unit_score,
            "medianPrice": round(med_price),
            "medianPriceSqft": round(med_price_sqft),
            "medianRent": round(med_rent),
            "rentalYield": round(yield_pct, 2),
            "transactionCount": txn_count,
            "demandScore": demand_score,
            "avgAreaSqft": round(avg_area),
        })

    units.sort(key=lambda x: -x["unitScore"])
    return units


def compute_project_score(project: dict, dev_data: dict | None) -> dict:
    units = compute_unit_scores(project)

    sales = project.get("sales_history", [])
    rents = project.get("rent_history", [])

    # Only use sales with valid price AND area for price/sqft
    valid_sales = []
    for s in sales:
        price = safe_float(s.get("price"))
        area = safe_float(s.get("area_sqft"))
        if price > 0 and area > 0:
            # Skip sales with area > 5000 sqft — plot/land area, not unit area
            if area > 5000:
                continue
            valid_sales.append({**s, "price_sqft": price / area})
    prices_sqft = [s["price_sqft"] for s in valid_sales]
    prices = [safe_float(s.get("price")) for s in valid_sales]

    # Remove IQR outliers
    if len(prices_sqft) >= 4:
        sorted_p = sorted(prices_sqft)
        n = len(sorted_p)
        q1 = sorted_p[n // 4]
        q3 = sorted_p[3 * n // 4]
        iqr = q3 - q1
        lower = q1 - 2.0 * iqr
        upper = q3 + 2.0 * iqr
        prices_sqft = [p for p in prices_sqft if lower <= p <= upper]

    med_price = median(prices)
    med_price_sqft = median(prices_sqft)
    txn_volume = len(valid_sales)
    rent_volume = len(rents)

    yield_pct = safe_float(project.get("rental_yield_pct"))
    if yield_pct == 0 and units:
        valid_yields = [u["rentalYield"] for u in units if u["rentalYield"] > 0]
        if valid_yields:
            yield_pct = max(valid_yields)
    # Cap at 12%
    yield_pct = min(yield_pct, 12.0)

    growth_3m = calculate_growth(valid_sales, 3)
    growth_6m = calculate_growth(valid_sales, 6)
    growth_12m = calculate_growth(valid_sales, 12)

    demand_score = round(clamp(txn_volume * 7, 0, 100))
    liquidity_score = round(clamp(txn_volume * 6 + rent_volume * 4, 0, 100))
    yield_score = round(clamp(yield_pct * 6, 0, 100))
    # Cap growth in scoring
    capped_growth = max(-80.0, min(80.0, growth_12m))
    growth_score = round(clamp(50 + capped_growth * 2, 0, 100))

    # Project score: yield (25) + growth (25) + demand (20) + liquidity (15) + price stability (15)
    price_stability = 65 if med_price_sqft > 0 else 30
    project_score = round(
        yield_score * 0.25 +
        growth_score * 0.25 +
        demand_score * 0.20 +
        liquidity_score * 0.15 +
        price_stability * 0.15
    )

    # Confidence score
    confidence = 100
    if txn_volume < 10:
        confidence -= 25
    if rent_volume < 5:
        confidence -= 15
    if med_price_sqft == 0:
        confidence -= 20
    if dev_data is None:
        confidence -= 10
    confidence = int(clamp(confidence, 0, 100))

    status = "Off-Plan" if any(s.get("area_sqft") is None for s in sales[:3]) else "Ready"
    if not sales:
        status = "Unknown"

    dev_score = safe_int(dev_data.get("developerScore")) if dev_data else 0
    dev_name = dev_data.get("name", "Independent / Other") if dev_data else "Independent / Other"

    # Price change — capped, use growth_12m as basis
    price_change = max(-40.0, min(40.0, growth_12m))

    return {
        "name": project["name"],
        "slug": project.get("slug", project["name"].lower().replace(" ", "-")),
        "area": project.get("area", "Unknown"),
        "projectScore": project_score,
        "priceSqft": round(med_price_sqft),
        "medianPrice": round(med_price),
        "priceChangePct": round(price_change, 2),
        "rentalYield": round(yield_pct, 2),
        "transactionVolume": txn_volume,
        "rentVolume": rent_volume,
        "demandScore": demand_score,
        "liquidityScore": liquidity_score,
        "growthScore": growth_score,
        "yieldScore": yield_score,
        "growth3m": growth_3m,
        "growth6m": growth_6m,
        "growth12m": growth_12m,
        "riskLevel": risk_from_score(project_score),
        "status": status,
        "developerName": dev_name,
        "developerScore": dev_score,
        "unitTypes": units,
        "confidenceScore": confidence,
        "scoreBreakdown": {
            "yieldScore": yield_score,
            "growthScore": growth_score,
            "demandScore": demand_score,
            "liquidityScore": liquidity_score,
            "priceStabilityScore": price_stability,
            "weights": {"yield": 0.25, "growth": 0.25, "demand": 0.20, "liquidity": 0.15, "stability": 0.15},
        },
        "computedAt": datetime.now().isoformat(),
    }


def run():
    print("[Project Engine] Starting...")
    projects = load_json(PROJECTS_JSON)
    dev_scores = load_developer_scores()

    results = []
    for project in projects:
        dev_data = match_developer_for_project(project["name"], dev_scores)
        score = compute_project_score(project, dev_data)
        results.append(score)

    results.sort(key=lambda x: -x["projectScore"])
    save_json(PROJECT_SCORES_FILE, results)
    print(f"[Project Engine] Computed {len(results)} project scores")
    return results


if __name__ == "__main__":
    run()
