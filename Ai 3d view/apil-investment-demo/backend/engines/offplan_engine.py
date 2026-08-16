"""
APIL Off-plan Intelligence Engine
Runs daily. Produces offplan_scores.json

Pipeline:
  Project → Launch Price → Nearby Ready Sales → Future Supply →
  Construction → Developer → Growth Forecast → Risk → Off-plan Score

NO ROI Engine. Instead: Growth Prediction Engine.

Formula:
  Developer:              25%
  Location:               20%
  Future Supply:          15%
  Launch Pricing:         15%
  Capital Growth Potential: 15%
  Payment Plan:            5%
  Construction Progress:   5%
"""
from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.utils import (
    clamp, median, safe_float, safe_int, normalize_bed_type,
    calculate_growth, risk_from_score, save_json, load_json,
    score_to_label, recommendation_from_score
)
from config.settings import (
    OFFPLAN_SCORES_FILE, PROJECTS_JSON,
    COMMUNITY_SCORES_FILE, DEVELOPER_SCORES_FILE, PROJECT_SCORES_FILE
)


def load_community_scores() -> dict[str, dict]:
    if COMMUNITY_SCORES_FILE.exists():
        data = load_json(COMMUNITY_SCORES_FILE)
        return {c["name"]: c for c in data}
    return {}


def load_developer_scores() -> dict[str, dict]:
    if DEVELOPER_SCORES_FILE.exists():
        data = load_json(DEVELOPER_SCORES_FILE)
        return {d["name"]: d for d in data}
    return {}


def load_project_scores() -> dict[str, dict]:
    if PROJECT_SCORES_FILE.exists():
        data = load_json(PROJECT_SCORES_FILE)
        return {p["name"]: p for p in data}
    return {}


def match_developer(project_name: str, dev_scores: dict) -> dict | None:
    clean = project_name.upper().strip()
    for dev_name, dev_data in dev_scores.items():
        for alias in dev_data.get("aliases", []):
            if alias in clean:
                return dev_data
    return None


def estimate_launch_pricing(project: dict, nearby_sales: list[dict]) -> dict:
    """Compare project price to nearby ready sales."""
    project_prices_sqft = [safe_float(s.get("price_sqft")) for s in project.get("sales_history", []) if safe_float(s.get("price_sqft")) > 0]
    nearby_prices_sqft = [safe_float(s.get("price_sqft")) for s in nearby_sales if safe_float(s.get("price_sqft")) > 0]

    project_med = median(project_prices_sqft)
    nearby_med = median(nearby_prices_sqft)

    if nearby_med > 0 and project_med > 0:
        discount_pct = round(((nearby_med - project_med) / nearby_med) * 100, 2)
    else:
        discount_pct = 0

    # Launch pricing score: higher discount = better score
    pricing_score = round(clamp(50 + discount_pct * 3, 0, 100))

    return {
        "projectPriceSqft": round(project_med),
        "nearbyPriceSqft": round(nearby_med),
        "discountToMarket": discount_pct,
        "launchPricingScore": pricing_score,
    }


def estimate_future_supply(community_data: dict | None) -> dict:
    if not community_data:
        return {"futureSupplyScore": 50, "totalSupply": 0, "riskLevel": "Medium"}

    total_supply = safe_int(community_data.get("totalSupply"))
    supply_score = round(clamp(100 - total_supply / 10, 0, 100))

    if supply_score >= 70:
        risk = "Low"
    elif supply_score >= 50:
        risk = "Medium"
    else:
        risk = "High"

    return {
        "futureSupplyScore": supply_score,
        "totalSupply": total_supply,
        "riskLevel": risk,
    }


def estimate_growth_potential(project: dict, community_data: dict | None) -> dict:
    """Predict capital growth for off-plan based on area trends + developer track record."""
    sales = project.get("sales_history", [])
    historical_growth = calculate_growth(sales, 12)

    community_growth = 0
    if community_data:
        community_growth = safe_float(community_data.get("growth12m"))

    # Blend: 60% community trend + 40% project historical
    predicted_growth = round(community_growth * 0.6 + historical_growth * 0.4, 2)

    growth_score = round(clamp(50 + predicted_growth * 2, 0, 100))

    return {
        "historicalGrowth12m": historical_growth,
        "communityGrowth12m": community_growth,
        "predictedGrowth": predicted_growth,
        "growthPotentialScore": growth_score,
    }


def estimate_construction_progress(project: dict, dev_data: dict | None) -> dict:
    """Estimate construction progress from delivery delay data."""
    if not dev_data:
        return {"constructionProgressScore": 50, "delayRisk": "Medium"}

    delay_pct = safe_float(dev_data.get("delayedProjects"), 50)
    _dev_s = dev_data.get("developerScore", 0)
    delay_risk = "Low" if _dev_s >= 75 else "Medium" if _dev_s >= 50 else "High"

    # Lower delay = higher progress score
    progress_score = round(clamp(100 - delay_pct, 0, 100))

    return {
        "constructionProgressScore": progress_score,
        "delayRisk": delay_risk,
        "delayPct": delay_pct,
    }


def estimate_payment_plan_score(dev_data: dict | None) -> dict:
    """Score payment plan flexibility. Most Dubai developers offer 50/50 or 60/40 plans."""
    if not dev_data:
        return {"paymentPlanScore": 50, "planType": "Unknown"}

    # Heuristic: Tier 1 developers tend to offer better payment plans
    dev_score_val = dev_data.get("developerScore", 0)
    if dev_score_val >= 80:
        tier = "Tier 1"
    elif dev_score_val >= 60:
        tier = "Tier 2"
    else:
        tier = "Tier 3"
    if "Tier 1" in tier:
        score = 80
        plan = "Flexible (post-handover 40-50%)"
    elif "Tier 2" in tier:
        score = 65
        plan = "Standard (50/50)"
    else:
        score = 50
        plan = "Basic (60/40)"

    return {"paymentPlanScore": score, "planType": plan}


def compute_offplan_score(
    project: dict,
    community_data: dict | None,
    dev_data: dict | None,
    proj_score_data: dict | None,
    nearby_sales: list[dict],
) -> dict:
    # Developer (25%)
    dev_score = safe_int(dev_data.get("developerScore")) if dev_data else 50
    dev_name = dev_data.get("name", "Independent / Other") if dev_data else "Independent / Other"

    # Location (20%)
    location_score = safe_int(community_data.get("communityScore")) if community_data else 50

    # Future Supply (15%)
    supply = estimate_future_supply(community_data)

    # Launch Pricing (15%)
    pricing = estimate_launch_pricing(project, nearby_sales)

    # Capital Growth Potential (15%)
    growth = estimate_growth_potential(project, community_data)

    # Payment Plan (5%)
    payment = estimate_payment_plan_score(dev_data)

    # Construction Progress (5%)
    construction = estimate_construction_progress(project, dev_data)

    # Off-plan Score
    offplan_score = round(
        dev_score * 0.25 +
        location_score * 0.20 +
        supply["futureSupplyScore"] * 0.15 +
        pricing["launchPricingScore"] * 0.15 +
        growth["growthPotentialScore"] * 0.15 +
        payment["paymentPlanScore"] * 0.05 +
        construction["constructionProgressScore"] * 0.05
    )

    # Risk assessment (off-plan specific)
    risk_factors: list[str] = []
    if dev_score < 75:
        risk_factors.append(f"Developer {dev_name} has below-average track record (score: {dev_score})")
    if supply["riskLevel"] == "High":
        risk_factors.append("High future supply in area may pressure prices on completion")
    if construction["delayRisk"] == "High":
        risk_factors.append(f"High delivery delay risk ({construction['delayPct']}% historical delay)")
    if pricing["discountToMarket"] < 0:
        risk_factors.append(f"Launch price is {abs(pricing['discountToMarket'])}% above nearby ready prices")
    if growth["predictedGrowth"] < 3:
        risk_factors.append("Low predicted capital growth based on area trends")

    overall_risk = round(
        (100 - dev_score) * 0.30 +
        (100 - supply["futureSupplyScore"]) * 0.25 +
        (100 - construction["constructionProgressScore"]) * 0.25 +
        (100 - growth["growthPotentialScore"]) * 0.20
    )
    risk_level = "Low" if overall_risk < 35 else "Medium" if overall_risk < 60 else "High"
    if not risk_factors:
        risk_factors.append("No significant risk factors identified")

    # AI Explainability
    reasons: list[str] = []
    if pricing["discountToMarket"] > 5:
        reasons.append(f"Launch price is {pricing['discountToMarket']}% below nearby ready prices — potential upside on completion")
    if dev_score >= 85:
        reasons.append(f"Top-tier developer with {dev_score}/100 score and strong delivery history")
    if growth["predictedGrowth"] > 10:
        reasons.append(f"Predicted capital growth of {growth['predictedGrowth']}% based on area trends")
    if supply["futureSupplyScore"] >= 70:
        reasons.append("Low future supply in area — favorable for price appreciation")
    if payment["paymentPlanScore"] >= 75:
        reasons.append(f"Flexible payment plan: {payment['planType']}")
    if not reasons:
        reasons.append("Off-plan project meets baseline investment criteria")

    # Unit types
    unit_types = []
    if proj_score_data and proj_score_data.get("unitTypes"):
        unit_types = proj_score_data["unitTypes"]

    return {
        "projectName": project["name"],
        "slug": project.get("slug", project["name"].lower().replace(" ", "-")),
        "area": project.get("area", "Unknown"),
        "offplanScore": offplan_score,
        "recommendation": recommendation_from_score(offplan_score),
        "scoreLabel": score_to_label(offplan_score),
        "developerName": dev_name,
        "developerScore": dev_score,
        "locationScore": location_score,
        "futureSupply": supply,
        "launchPricing": pricing,
        "growthForecast": growth,
        "paymentPlan": payment,
        "constructionProgress": construction,
        "risk": {
            "overallRisk": overall_risk,
            "riskLevel": risk_level,
            "riskFactors": risk_factors,
        },
        "reasons": reasons,
        "unitTypes": unit_types,
        "computedAt": datetime.now().isoformat(),
    }


def run():
    print("[Off-plan Engine] Starting...")
    projects = load_json(PROJECTS_JSON)
    communities = load_community_scores()
    developers = load_developer_scores()
    project_scores = load_project_scores()

    # Group all sales by area for nearby comparisons
    area_sales: dict[str, list[dict]] = defaultdict(list)
    for p in projects:
        area = p.get("area", "Unknown")
        for s in p.get("sales_history", []):
            if s.get("area_sqft"):
                area_sales[area].append(s)

    results = []
    for project in projects:
        sales = project.get("sales_history", [])
        # Identify off-plan projects: no area_sqft in sales or very recent
        is_offplan = any(s.get("area_sqft") is None for s in sales[:5])
        if not is_offplan and not sales:
            is_offplan = True
        if not is_offplan:
            continue

        dev_data = match_developer(project["name"], developers)
        community_data = communities.get(project.get("area", ""))
        proj_score_data = project_scores.get(project["name"])
        nearby = area_sales.get(project.get("area", ""), [])

        score = compute_offplan_score(project, community_data, dev_data, proj_score_data, nearby)
        results.append(score)

    results.sort(key=lambda x: -x["offplanScore"])
    save_json(OFFPLAN_SCORES_FILE, results)
    print(f"[Off-plan Engine] Computed {len(results)} off-plan scores")
    return results


if __name__ == "__main__":
    run()
