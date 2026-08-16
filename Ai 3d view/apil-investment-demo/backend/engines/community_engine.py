"""
APIL Community Intelligence Engine
Runs daily. Produces community_scores.json

Pipeline:
  Transactions → Price Index → Rental Index → Demand Index →
  Supply Index → Growth Index → Livability → Community Score
"""
from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.utils import (
    clamp, median, safe_float, parse_date, calculate_growth,
    risk_from_score, save_json, load_json
)
from config.settings import COMMUNITY_SCORES_FILE, PROJECTS_JSON, BACKEND_DATA_DIR


def compute_price_index(all_sales: list[dict]) -> dict:
    prices_sqft = [s["price_sqft"] for s in all_sales if s.get("price_sqft") and s["price_sqft"] > 0]
    return {
        "medianPriceSqft": round(median(prices_sqft)) if prices_sqft else 0,
        "totalSales": len(all_sales),
    }


def compute_rental_index(all_rents: list[dict]) -> dict:
    rents = [r["annual_rent"] for r in all_rents if r.get("annual_rent") and r["annual_rent"] > 0]
    return {
        "medianRent": round(median(rents)) if rents else 0,
        "totalRentContracts": len(all_rents),
    }


def compute_demand_index(sales_volume: int, rent_volume: int) -> int:
    # Demand based on transaction + rental activity
    return round(clamp(sales_volume * 0.5 + rent_volume * 0.3, 0, 100))


def compute_supply_index(total_supply: int, project_count: int) -> int:
    # Supply pressure: more projects under construction = more future supply
    # But also factor in total supply units
    supply_from_projects = round(clamp(project_count * 8, 0, 100))
    supply_from_units = round(clamp(100 - total_supply / 10, 0, 100))
    # Higher score = more supply risk (more competition)
    return round(clamp((supply_from_projects + supply_from_units) / 2, 0, 100))


def compute_growth_index(all_sales: list[dict]) -> dict:
    return {
        "growth3m": calculate_growth(all_sales, 3),
        "growth6m": calculate_growth(all_sales, 6),
        "growth12m": calculate_growth(all_sales, 12),
    }


def compute_livability_index(project_count: int) -> int:
    return round(clamp(project_count * 3, 0, 100))


def compute_transport_index() -> int:
    return 70


def compute_community_score(area_name: str, projects: list[dict]) -> dict:
    all_sales = []
    all_rents = []
    for p in projects:
        for s in p.get("sales_history", []):
            price = safe_float(s.get("price"))
            area = safe_float(s.get("area_sqft"))
            if price > 0 and area > 0:
                # Skip sales with area > 5000 sqft — plot/land area, not unit area
                if area > 5000:
                    continue
                all_sales.append({**s, "price_sqft": price / area})
        all_rents.extend(p.get("rent_history", []))

    price_idx = compute_price_index(all_sales)
    rental_idx = compute_rental_index(all_rents)
    growth_idx = compute_growth_index(all_sales)

    sales_volume = len(all_sales)
    rent_volume = len(all_rents)
    total_supply = sum(safe_float(p.get("sales_volume")) for p in projects)

    avg_yield = 0
    yields = [safe_float(p.get("rental_yield_pct")) for p in projects if p.get("rental_yield_pct")]
    if yields:
        avg_yield = sum(yields) / len(yields)

    demand_score = compute_demand_index(sales_volume, rent_volume)
    supply_score = compute_supply_index(total_supply, len(projects))
    livability_score = compute_livability_index(len(projects))
    transport_score = compute_transport_index()

    # Cap growth at ±40% — rolling median index already smooths data
    capped_growth_12m = max(-40.0, min(40.0, growth_idx["growth12m"]))
    growth_score = round(clamp(50 + capped_growth_12m * 2, 0, 100))
    yield_score = round(clamp(avg_yield * 6, 0, 100))
    liquidity_score = round(clamp(sales_volume * 0.8 + rent_volume * 0.5, 0, 100))
    transaction_score = round(clamp(sales_volume * 0.7, 0, 100))

    luxury_score = round(clamp(price_idx["medianPriceSqft"] / 30, 0, 100))

    investment_score = round(
        growth_score * 0.25 +
        yield_score * 0.25 +
        liquidity_score * 0.20 +
        transaction_score * 0.15 +
        (demand_score + livability_score + supply_score) / 3 * 0.15
    )

    # Score breakdown for transparency
    dls_avg = (demand_score + livability_score + supply_score) / 3
    score_breakdown = {
        "growth": {"score": growth_score, "max": 25, "contribution": round(growth_score * 0.25, 1)},
        "yield": {"score": yield_score, "max": 25, "contribution": round(yield_score * 0.25, 1)},
        "liquidity": {"score": liquidity_score, "max": 20, "contribution": round(liquidity_score * 0.20, 1)},
        "transactions": {"score": transaction_score, "max": 15, "contribution": round(transaction_score * 0.15, 1)},
        "demandLivabilitySupply": {"score": round(dls_avg), "max": 15, "contribution": round(dls_avg * 0.15, 1)},
    }

    risk_level = risk_from_score(investment_score)

    # Confidence score based on data volume
    confidence = 100
    if sales_volume < 200:
        confidence -= 30
    if rent_volume < 50:
        confidence -= 15
    if len(projects) < 3:
        confidence -= 15
    confidence = int(clamp(confidence, 0, 100))

    return {
        "name": area_name,
        "slug": area_name.lower().replace(" ", "-"),
        "communityScore": investment_score,
        "scoreBreakdown": score_breakdown,
        "priceIndex": price_idx,
        "rentalIndex": rental_idx,
        "demandIndex": demand_score,
        "supplyIndex": supply_score,
        "growthIndex": growth_idx,
        "livabilityIndex": livability_score,
        "transportIndex": transport_score,
        "luxuryIndex": luxury_score,
        "subScores": {
            "growth": growth_score,
            "yield": yield_score,
            "liquidity": liquidity_score,
            "transactions": transaction_score,
            "demand": demand_score,
            "rental": round(clamp(rent_volume * 0.5 + avg_yield * 5, 0, 100)),
            "luxury": luxury_score,
            "futureSupply": supply_score,
            "livability": livability_score,
            "transport": transport_score,
        },
        "medianPriceSqft": price_idx["medianPriceSqft"],
        "medianRent": rental_idx["medianRent"],
        "rentalYield": round(avg_yield, 2),
        "growth3m": growth_idx["growth3m"],
        "growth6m": growth_idx["growth6m"],
        "growth12m": max(-40.0, min(40.0, growth_idx["growth12m"])),
        "salesVolume": sales_volume,
        "rentVolume": rent_volume,
        "totalProjects": len(projects),
        "totalSupply": round(total_supply),
        "riskLevel": risk_level,
        "confidenceScore": confidence,
        "computedAt": datetime.now().isoformat(),
    }


def run():
    print("[Community Engine] Starting...")
    projects = load_json(PROJECTS_JSON)

    area_groups: dict[str, list[dict]] = defaultdict(list)
    for p in projects:
        area = p.get("area", "Unknown")
        area_groups[area].append(p)

    scores = []
    for area, projs in area_groups.items():
        score = compute_community_score(area, projs)
        scores.append(score)

    scores.sort(key=lambda x: -x["communityScore"])
    save_json(COMMUNITY_SCORES_FILE, scores)
    print(f"[Community Engine] Computed {len(scores)} community scores")
    return scores


if __name__ == "__main__":
    run()
