"""
APIL Off-Plan Investment Engine (v2)
Implements fair-value-based recommendation logic for off-plan properties.

Core principle: Never compare to launch price. Always compare current developer
asking price vs current fair market value derived from DLD transactions.

Formula (off-plan specific):
  Developer              25%
  Price vs Market        20%
  Payment Plan           15%
  Future Appreciation    10%
  Supply Risk            10%
  Liquidity               5%
  ROI (post-handover)     5%

Data sources:
  - Qdrant (Dubai_real_estate_calculation_data_): actual developer asking prices, sizes, beds
  - community_scores.json: median price/sqft, growth, demand, supply, liquidity
  - developer_scores.json: track record, delivery, quality, reputation
  - project_scores.json: project-level transaction data, unit types
  - feature_store.json: per-project per-unit-type median prices and rents
"""
from __future__ import annotations

import sys
import json
import re
import urllib.request
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.utils import (
    clamp, median, safe_float, safe_int, normalize_bed_type,
    save_json, load_json, score_to_label
)
from config.settings import (
    OFFPLAN_SCORES_FILE, COMMUNITY_SCORES_FILE,
    DEVELOPER_SCORES_FILE, PROJECT_SCORES_FILE,
    BACKEND_DATA_DIR
)

QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION = "Dubai_real_estate_calculation_data_"


# ─── Qdrant fetch ───

def _scroll_qdrant_offplan(limit: int = 200, offset: str | None = None) -> tuple[list[dict], str | None]:
    """Scroll Qdrant for off-plan properties only."""
    url = f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points/scroll"
    body: dict[str, Any] = {"limit": limit, "with_payload": True, "with_vector": False}
    if offset:
        body["offset"] = offset
    body["filter"] = {"must": [{"key": "is_off_plan", "match": {"value": True}}]}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
    points = resp["result"]["points"]
    next_offset = resp["result"].get("next_page_offset")
    return points, next_offset


def fetch_offplan_from_qdrant() -> list[dict]:
    """Fetch all off-plan listings from Qdrant."""
    all_points = []
    offset = None
    for _ in range(50):
        points, offset = _scroll_qdrant_offplan(limit=200, offset=offset)
        if not points:
            break
        all_points.extend(points)
        if not offset:
            break
    print(f"  [Qdrant] Fetched {len(all_points)} off-plan listings")
    return all_points


# ─── Data loaders ───

def load_community_scores() -> dict[str, dict]:
    if COMMUNITY_SCORES_FILE.exists():
        data = load_json(COMMUNITY_SCORES_FILE)
        return {c["name"].lower(): c for c in data}
    return {}


def load_developer_scores() -> dict[str, dict]:
    if DEVELOPER_SCORES_FILE.exists():
        data = load_json(DEVELOPER_SCORES_FILE)
        return {d["name"].lower(): d for d in data}
    return {}


def load_project_scores() -> dict[str, dict]:
    if PROJECT_SCORES_FILE.exists():
        data = load_json(PROJECT_SCORES_FILE)
        return {p["name"].lower(): p for p in data}
    return {}


def load_feature_store() -> dict[str, dict]:
    fs_path = BACKEND_DATA_DIR / "feature_store.json"
    if fs_path.exists():
        data = load_json(fs_path)
        return {d["projectName"].lower(): d for d in data}
    return {}


# ─── Matching ───

def match_developer(dev_name: str, dev_scores: dict) -> dict | None:
    if not dev_name:
        return None
    clean = dev_name.lower().strip()
    # Direct match
    if clean in dev_scores:
        return dev_scores[clean]
    # Partial match
    for name, data in dev_scores.items():
        if name in clean or clean in name:
            return data
        for alias in data.get("aliases", []):
            if alias and alias.lower() in clean:
                return data
    return None


def match_community(area: str, comm_scores: dict) -> dict | None:
    if not area:
        return None
    clean = area.lower().strip()
    if clean in comm_scores:
        return comm_scores[clean]
    # Partial match
    for name, data in comm_scores.items():
        if name in clean or clean in name:
            return data
    return None


def match_project(project_name: str, proj_scores: dict) -> dict | None:
    if not project_name:
        return None
    clean = project_name.lower().strip()
    if clean in proj_scores:
        return proj_scores[clean]
    for name, data in proj_scores.items():
        if name in clean or clean in name:
            return data
    return None


# ─── Step 1: Fair Launch Price ───

def calculate_fair_value(
    community_data: dict | None,
    project_data: dict | None,
    feature_store: dict | None,
    size_sqft: float,
    bed_type: str,
) -> dict:
    """
    Fair Value = Community Median Price/sqft × Unit Size × Location Factor × Project Premium
    """
    community_median_sqft = 0.0
    if community_data:
        pi = community_data.get("priceIndex", {})
        community_median_sqft = safe_float(pi.get("medianPriceSqft"))

    # Fallback: use project-level median from project_scores
    project_median_sqft = 0.0
    if project_data:
        project_median_sqft = safe_float(project_data.get("priceSqft"))

    # Fallback: use feature_store unit-type median
    fs_unit_sqft = 0.0
    if feature_store:
        uf = feature_store.get("unitFeatures", {})
        norm_bed = normalize_bed_type(bed_type)
        for bed_key, bed_data in uf.items():
            if norm_bed and norm_bed in normalize_bed_type(bed_key):
                fs_unit_sqft = safe_float(bed_data.get("medianPriceSqft"))
                break

    # Pick best available median price/sqft
    base_sqft = community_median_sqft or project_median_sqft or fs_unit_sqft
    source = "community" if community_median_sqft else ("project" if project_median_sqft else ("feature_store" if fs_unit_sqft else "none"))

    # Location factor: adjust based on community score (higher score = premium location)
    location_factor = 1.0
    if community_data:
        cs = safe_int(community_data.get("communityScore"))
        # Score 50 = neutral, 100 = +10% premium, 0 = -10% discount
        location_factor = 1.0 + (cs - 50) * 0.002

    # Project premium: based on project score and developer tier
    project_premium = 1.0
    if project_data:
        ps = safe_int(project_data.get("projectScore"))
        # Score 50 = neutral, 100 = +15% premium, 0 = -15% discount
        project_premium = 1.0 + (ps - 50) * 0.003

    fair_value = base_sqft * size_sqft * location_factor * project_premium

    return {
        "fairValue": round(fair_value),
        "communityMedianSqft": community_median_sqft,
        "projectMedianSqft": project_median_sqft,
        "featureStoreSqft": fs_unit_sqft,
        "baseSqft": base_sqft,
        "source": source,
        "locationFactor": round(location_factor, 4),
        "projectPremium": round(project_premium, 4),
        "sizeSqft": size_sqft,
    }


# ─── Step 2: Price Difference ───

def calculate_price_difference(developer_price: float, fair_value: float) -> dict:
    """
    Price Difference % = (Developer Price - Fair Value) / Fair Value × 100
    """
    if fair_value <= 0:
        return {
            "priceDifferencePct": 0,
            "priceOpportunityScore": 50,
            "label": "Unknown",
        }

    diff_pct = ((developer_price - fair_value) / fair_value) * 100

    # Score: below market = high score, above market = low score
    # -15% → 100, 0% → 60, +15% → 20, >15% → 0
    if diff_pct <= -15:
        score = 100
        label = "Strong Buy — Well below market"
    elif diff_pct <= -5:
        score = round(clamp(100 - (diff_pct + 15) * 2, 0, 100))
        label = "Buy — Below market value"
    elif diff_pct <= 5:
        score = round(clamp(60 - abs(diff_pct) * 2, 0, 100))
        label = "Fair — At market value"
    elif diff_pct <= 10:
        score = round(clamp(40 - (diff_pct - 5) * 4, 0, 100))
        label = "Negotiate — Slight premium"
    elif diff_pct <= 15:
        score = round(clamp(20 - (diff_pct - 10) * 2, 0, 100))
        label = "Hold — Premium over market"
    else:
        score = 0
        label = "Avoid — Significantly overpriced"

    return {
        "developerPrice": round(developer_price),
        "fairValue": round(fair_value),
        "priceDifferencePct": round(diff_pct, 2),
        "priceOpportunityScore": score,
        "label": label,
    }


# ─── Step 3: Future Appreciation ───

def calculate_future_appreciation(
    developer_price: float,
    community_data: dict | None,
    project_data: dict | None,
    completion_years: float,
) -> dict:
    """
    Future Value = Current Community Price × (1 + Expected Growth)^Years
    Potential Gain = Future Value - Purchase Price
    """
    # Expected growth rate from community data
    growth_rate = 0.0
    if community_data:
        gi = community_data.get("growthIndex", {})
        g12 = safe_float(gi.get("growth12m"))
        g6 = safe_float(gi.get("growth6m"))
        g3 = safe_float(gi.get("growth3m"))
        # Use 12m growth as base, blend with 6m and 3m for recency
        if g12 > 0:
            growth_rate = g12 / 100.0
        elif g6 > 0:
            growth_rate = g6 / 100.0
        elif g3 > 0:
            growth_rate = g3 / 100.0

    # Cap growth rate to realistic bounds (0-25%)
    growth_rate = clamp(growth_rate, 0, 0.25)

    # If no community growth, use project growth
    if growth_rate == 0 and project_data:
        pg = safe_float(project_data.get("growth12m"))
        if pg > 0:
            growth_rate = clamp(pg / 100.0, 0, 0.25)

    # Default assumption: 5% if no data
    if growth_rate == 0:
        growth_rate = 0.05

    # Future value of the property (using fair value as current market, not developer price)
    future_value = developer_price * ((1 + growth_rate) ** completion_years)
    potential_gain = future_value - developer_price
    potential_gain_pct = (potential_gain / developer_price) * 100 if developer_price > 0 else 0

    # Score: higher gain = higher score
    # 50%+ gain → 100, 25% → 75, 10% → 50, 0% → 25, negative → 0
    if potential_gain_pct >= 50:
        score = 100
    elif potential_gain_pct >= 0:
        score = round(clamp(25 + potential_gain_pct * 1.5, 0, 100))
    else:
        score = max(0, round(25 + potential_gain_pct * 0.5))

    return {
        "growthRate": round(growth_rate * 100, 2),
        "completionYears": completion_years,
        "futureValue": round(future_value),
        "potentialGain": round(potential_gain),
        "potentialGainPct": round(potential_gain_pct, 2),
        "futureAppreciationScore": score,
    }


# ─── Step 4: Rental Yield After Handover ───

def calculate_post_handover_roi(
    developer_price: float,
    community_data: dict | None,
    project_data: dict | None,
    feature_store: dict | None,
    bed_type: str,
    size_sqft: float,
) -> dict:
    """
    Expected Net ROI = (Expected Rent - Expenses) / Purchase Price
    Estimate rent from completed comparable projects, not the off-plan project.
    """
    # Estimate annual rent from community data
    estimated_rent = 0.0
    rent_source = "none"

    if community_data:
        ri = community_data.get("rentalIndex", {})
        community_median_rent = safe_float(ri.get("medianRent"))
        if community_median_rent > 0:
            estimated_rent = community_median_rent
            rent_source = "community"

    # Fallback: project-level rent
    if estimated_rent == 0 and project_data:
        # Check unit types for matching bed type
        for ut in project_data.get("unitTypes", []):
            if normalize_bed_type(bed_type) in normalize_bed_type(ut.get("bedType", "")):
                r = safe_float(ut.get("medianRent"))
                if r > 0:
                    estimated_rent = r
                    rent_source = "project_unit"
                    break

    # Fallback: feature store
    if estimated_rent == 0 and feature_store:
        uf = feature_store.get("unitFeatures", {})
        norm_bed = normalize_bed_type(bed_type)
        for bed_key, bed_data in uf.items():
            if norm_bed and norm_bed in normalize_bed_type(bed_key):
                r = safe_float(bed_data.get("medianRent"))
                if r > 0:
                    estimated_rent = r
                    rent_source = "feature_store"
                    break

    # Fallback: estimate from price/sqft × size × typical yield
    if estimated_rent == 0 and community_data:
        pi = community_data.get("priceIndex", {})
        med_sqft = safe_float(pi.get("medianPriceSqft"))
        ry = safe_float(community_data.get("rentalYield", 0))
        if med_sqft > 0 and size_sqft > 0 and ry > 0:
            estimated_rent = med_sqft * size_sqft * (ry / 100.0)
            rent_source = "estimated"

    if estimated_rent == 0 or developer_price <= 0:
        return {
            "estimatedRent": None,
            "rentSource": rent_source,
            "serviceChargeAnnual": None,
            "managementFee": None,
            "vacancyCost": None,
            "netAnnualIncome": None,
            "grossROI": None,
            "netROI": None,
            "roiScore": 50,  # Neutral — don't penalize for missing data
            "hasRentData": False,
        }

    # Expenses: service charge (~AED 15/sqft), management fee (5%), vacancy (5%)
    service_charge = size_sqft * 15
    management_fee = estimated_rent * 0.05
    vacancy = estimated_rent * 0.05
    net_income = estimated_rent - service_charge - management_fee - vacancy

    gross_roi = (estimated_rent / developer_price) * 100
    net_roi = (net_income / developer_price) * 100

    # Score: 8%+ net ROI → 100, 6% → 75, 4% → 50, 2% → 25, 0% → 0
    if net_roi >= 8:
        score = 100
    elif net_roi >= 0:
        score = round(clamp(net_roi * 12.5, 0, 100))
    else:
        score = 0

    return {
        "estimatedRent": round(estimated_rent),
        "rentSource": rent_source,
        "serviceChargeAnnual": round(service_charge),
        "managementFee": round(management_fee),
        "vacancyCost": round(vacancy),
        "netAnnualIncome": round(net_income),
        "grossROI": round(gross_roi, 2),
        "netROI": round(net_roi, 2),
        "roiScore": score,
        "hasRentData": True,
    }


# ─── Step 5: Developer Score ───

def calculate_developer_score(dev_data: dict | None) -> dict:
    """
    Developer Score = Track Record 30% + Delivery History 25% + Construction Quality 20%
                      + Capital Appreciation 15% + Market Reputation 10%
    """
    if not dev_data:
        return {
            "developerScore": 50,
            "developerName": "Independent / Other",
            "trackRecord": 50,
            "deliveryHistory": 50,
            "constructionQuality": 50,
            "capitalAppreciation": 50,
            "marketReputation": 50,
            "delayRisk": "Medium",
            "marketPosition": "Tier 3",
        }

    sb = dev_data.get("scoreBreakdown", {})
    track_record = safe_int(sb.get("trackRecord"), 50)
    delivery_history = safe_int(sb.get("deliveryPerformance"), 50)
    construction_quality = safe_int(sb.get("constructionQuality"), 50) * 10  # scale 0-10 to 0-100
    capital_appreciation = safe_int(sb.get("capitalGain"), 50)
    market_reputation = safe_int(sb.get("marketReputation"), 50) * 10  # scale 0-10 to 0-100

    score = round(
        track_record * 0.30 +
        delivery_history * 0.25 +
        construction_quality * 0.20 +
        capital_appreciation * 0.15 +
        market_reputation * 0.10
    )

    return {
        "developerScore": score,
        "developerName": dev_data.get("name", "Independent / Other"),
        "trackRecord": track_record,
        "deliveryHistory": delivery_history,
        "constructionQuality": construction_quality,
        "capitalAppreciation": capital_appreciation,
        "marketReputation": market_reputation,
        "delayRisk": "Low" if score >= 75 else "Medium" if score >= 50 else "High",
        "delayedProjectsPct": safe_float(dev_data.get("delayedProjects")),
        "marketPosition": "Tier 1" if score >= 80 else "Tier 2" if score >= 60 else "Tier 3",
        "avgResalePremium": safe_float(dev_data.get("avgResalePremium")),
    }


# ─── Step 6: Community Score ───

def calculate_community_score(community_data: dict | None) -> dict:
    """
    Community Score from: Demand, Growth, Future Supply, Infrastructure, Liquidity, Rental Demand
    """
    if not community_data:
        return {
            "communityScore": 50,
            "demandIndex": 50,
            "growthIndex": 50,
            "futureSupplyScore": 50,
            "liquidityScore": 50,
            "rentalDemand": 50,
            "livabilityIndex": 50,
        }

    cs = safe_int(community_data.get("communityScore"), 50)
    demand = safe_int(community_data.get("demandIndex"), 50)
    supply = safe_int(community_data.get("supplyIndex"), 50)
    # Future supply: high supply = lower score
    future_supply_score = round(clamp(100 - (supply - 50) * 1.5, 0, 100))
    liquidity = safe_int(community_data.get("subScores", {}).get("liquidity"), 50)
    rental_demand = safe_int(community_data.get("subScores", {}).get("yield"), 50)
    livability = safe_int(community_data.get("livabilityIndex"), 50)

    gi = community_data.get("growthIndex", {})
    growth_12m = safe_float(gi.get("growth12m"))
    growth_score = round(clamp(50 + growth_12m * 2, 0, 100))

    return {
        "communityScore": cs,
        "demandIndex": demand,
        "growthIndex": growth_score,
        "growth12m": growth_12m,
        "futureSupplyScore": future_supply_score,
        "supplyIndex": supply,
        "liquidityScore": liquidity,
        "rentalDemand": rental_demand,
        "livabilityIndex": livability,
        "luxuryIndex": safe_int(community_data.get("luxuryIndex"), 50),
        "transportIndex": safe_int(community_data.get("transportIndex"), 50),
    }


# ─── Liquidity Score ───

def calculate_liquidity_score(community_data: dict | None, project_data: dict | None) -> dict:
    """How easily the property can be resold."""
    comm_liquidity = 50
    if community_data:
        comm_liquidity = safe_int(community_data.get("subScores", {}).get("liquidity"), 50)

    proj_liquidity = 50
    if project_data:
        proj_liquidity = safe_int(project_data.get("liquidityScore"), 50)

    tx_volume = 0
    if project_data:
        tx_volume = safe_int(project_data.get("transactionVolume"), 0)

    # Blend: 60% community + 40% project
    score = round(comm_liquidity * 0.6 + proj_liquidity * 0.4)

    return {
        "liquidityScore": score,
        "communityLiquidity": comm_liquidity,
        "projectLiquidity": proj_liquidity,
        "transactionVolume": tx_volume,
    }


# ─── Recommendation Logic ───

def get_recommendation(price_diff_pct: float, investment_score: int) -> str:
    """
    Recommendation based on price difference vs market AND overall investment score.

    Premium vs Market → Recommendation:
      Under 5%     → BUY (if score >= 65) or HOLD
      5-10%        → NEGOTIATE
      10-15%       → HOLD
      >15%         → AVOID
    """
    if price_diff_pct > 15:
        return "AVOID"
    elif price_diff_pct > 10:
        return "HOLD"
    elif price_diff_pct > 5:
        return "NEGOTIATE"
    elif price_diff_pct <= -5 and investment_score >= 70:
        return "STRONG BUY"
    elif price_diff_pct <= 5 and investment_score >= 65:
        return "BUY"
    elif investment_score >= 55:
        return "HOLD"
    else:
        return "AVOID"



# ─── Payment Plan Analysis ───

def analyze_payment_plan(payment_plans: list, asking_price: float, future_value: float) -> dict:
    """Analyze payment plan structure and compute equity gain metrics."""
    if not payment_plans or asking_price <= 0:
        return {
            "downPaymentPct": 0,
            "duringConstructionPct": 0,
            "onHandoverPct": 0,
            "downPaymentAmount": 0,
            "cashInvestedToday": 0,
            "projectedValueAtHandover": round(future_value) if future_value else 0,
            "equityGain": 0,
            "equityGainPct": 0,
            "leverageRatio": 0,
            "paymentPlanScore": 50,
            "structure": "Unknown",
            "installments": [],
        }

    # Parse payment plan percentages
    down_pct = 0
    during_pct = 0
    handover_pct = 0
    installments = []

    for plan in payment_plans:
        pct = safe_float(plan.get("percentage", 0))
        heading = (plan.get("heading") or "").lower()
        sub = (plan.get("sub_heading") or "").lower()

        installments.append({
            "percentage": pct,
            "label": plan.get("heading", ""),
            "timing": plan.get("sub_heading", ""),
        })

        if "down" in heading or "booking" in heading or "booking" in sub:
            down_pct += pct
        elif "handover" in heading or "completion" in heading or "handover" in sub or "completion" in sub:
            handover_pct += pct
        elif "construction" in heading or "construction" in sub or "installment" in heading:
            during_pct += pct
        else:
            if down_pct == 0:
                down_pct += pct
            else:
                handover_pct += pct

    down_amount = asking_price * (down_pct / 100)
    cash_invested = down_amount

    # Equity gain: if property value rises, investor equity grows disproportionately
    equity_gain = future_value - asking_price
    equity_gain_pct = round((equity_gain / cash_invested * 100), 1) if cash_invested > 0 else 0
    leverage_ratio = round(asking_price / cash_invested, 1) if cash_invested > 0 else 0

    # Score: lower down payment + spread out = better score
    if down_pct <= 10:
        pp_score = 100
    elif down_pct <= 20:
        pp_score = 85
    elif down_pct <= 30:
        pp_score = 70
    elif down_pct <= 50:
        pp_score = 50
    elif down_pct < 100:
        pp_score = 30
    else:
        pp_score = 15

    # Bonus for spreading during construction
    if during_pct > 0 and down_pct <= 20:
        pp_score = min(100, pp_score + 10)

    # Determine structure label
    if down_pct <= 20 and handover_pct >= 50:
        structure = "Low down, bulk at handover"
    elif down_pct <= 20 and during_pct >= 40:
        structure = "Low down, spread during construction"
    elif down_pct <= 10:
        structure = "Minimal down payment"
    elif down_pct >= 50:
        structure = "High upfront payment"
    else:
        structure = "Standard payment plan"

    return {
        "downPaymentPct": down_pct,
        "duringConstructionPct": during_pct,
        "onHandoverPct": handover_pct,
        "downPaymentAmount": round(down_amount),
        "cashInvestedToday": round(cash_invested),
        "projectedValueAtHandover": round(future_value),
        "equityGain": round(equity_gain),
        "equityGainPct": equity_gain_pct,
        "leverageRatio": leverage_ratio,
        "paymentPlanScore": pp_score,
        "structure": structure,
        "installments": installments,
    }


# ─── Exit Strategy Analysis ───

def calculate_exit_strategies(asking_price: float, future_value: float,
                               completion_years: float, post_handover_roi: dict,
                               payment_plan: dict, developer_score: int) -> dict:
    """Calculate multiple exit strategies for off-plan investment."""
    strategies = []
    down_payment = payment_plan.get("downPaymentAmount", asking_price * 0.20)
    equity_gain = future_value - asking_price

    # Strategy A: Assignment before completion
    assignment_premium_pct = 5 if developer_score >= 70 else 3
    assignment_value = asking_price * (1 + assignment_premium_pct / 100)
    assignment_profit = assignment_value - asking_price
    assignment_roi = round((assignment_profit / down_payment * 100), 1) if down_payment > 0 else 0
    strategies.append({
        "id": "assignment",
        "name": "Assignment Before Completion",
        "description": f"Sell the contract before handover. Typical premium: {assignment_premium_pct}% over purchase price.",
        "projectedValue": round(assignment_value),
        "profit": round(assignment_profit),
        "roiOnDownPayment": assignment_roi,
        "timeline": f"Before handover (~{completion_years} years)",
        "difficulty": "Medium" if developer_score >= 70 else "Hard",
        "requirements": "Developer approval + NOC + buyer found",
    })

    # Strategy B: Sell at handover
    sell_at_handover_profit = equity_gain
    sell_at_handover_roi = round((sell_at_handover_profit / down_payment * 100), 1) if down_payment > 0 else 0
    strategies.append({
        "id": "sell_handover",
        "name": "Sell at Handover",
        "description": "Complete payment, take possession, sell immediately at projected market value.",
        "projectedValue": round(future_value),
        "profit": round(sell_at_handover_profit),
        "roiOnDownPayment": sell_at_handover_roi,
        "timeline": f"At handover (~{completion_years} years)",
        "difficulty": "Medium",
        "requirements": "Full payment + DLD transfer fees (4%) + agent fees",
    })

    # Strategy C: Rent after handover
    est_rent = post_handover_roi.get("estimatedRent")
    net_roi = post_handover_roi.get("netROI")
    annual_income = post_handover_roi.get("netAnnualIncome")
    strategies.append({
        "id": "rent_hold",
        "name": "Rent After Handover",
        "description": "Complete payment, rent out for passive income.",
        "projectedValue": round(future_value),
        "annualRent": est_rent,
        "netROI": net_roi,
        "netAnnualIncome": annual_income,
        "timeline": "Handover + ongoing",
        "difficulty": "Easy",
        "requirements": "Full payment + furnishing + tenant onboarding",
    })

    # Strategy D: Hold 5 years
    growth_rate = 0.05
    value_5yr = future_value * (1 + growth_rate) ** 5
    hold_profit = value_5yr - asking_price
    hold_roi = round((hold_profit / down_payment * 100), 1) if down_payment > 0 else 0
    strategies.append({
        "id": "hold_5yr",
        "name": "Hold 5 Years Post-Handover",
        "description": f"Rent out for 5 years, then sell. Assumes {growth_rate*100:.0f}% annual growth post-completion.",
        "projectedValue": round(value_5yr),
        "profit": round(hold_profit),
        "roiOnDownPayment": hold_roi,
        "timeline": f"{completion_years + 5} years",
        "difficulty": "Easy",
        "requirements": "Full payment + tenant management + market monitoring",
    })

    recommended = "sell_handover" if equity_gain > 0 and developer_score >= 70 else "rent_hold" if net_roi and net_roi >= 6 else "assignment"

    return {
        "strategies": strategies,
        "recommendedStrategy": recommended,
    }


# ─── Main scoring function ───

def score_offplan_property(
    qdrant_payload: dict,
    comm_scores: dict[str, dict],
    dev_scores: dict[str, dict],
    proj_scores: dict[str, dict],
    feature_store: dict[str, dict],
) -> dict | None:
    """Score a single off-plan property from Qdrant."""

    pl = qdrant_payload
    name = pl.get("name", "")
    project_name = pl.get("project_name", "")
    area = pl.get("community_area", "")
    developer_name = pl.get("developer", "")
    price = safe_float(pl.get("price"))
    size_sqft = safe_float(pl.get("size_sq_ft") or pl.get("size_sqft"))
    bed_type = pl.get("bedroom_norm") or pl.get("bedroom", "")
    slug = pl.get("slug", "")

    # Skip if no price or size
    if price <= 0 or size_sqft <= 0:
        return None

    # Match data
    community_data = match_community(area, comm_scores)
    dev_data = match_developer(developer_name, dev_scores)
    project_data = match_project(project_name, proj_scores)
    fs_data = feature_store.get(project_name.lower().strip()) if project_name else None

    # ── Price Validation: reject impossible listings ──
    comm_data_for_validation = match_community(area, comm_scores)
    if comm_data_for_validation:
        comm_median_sqft = safe_float(comm_data_for_validation.get("priceIndex", {}).get("medianPriceSqft", 0))
        if comm_median_sqft > 0 and size_sqft > 0:
            comm_median_total = comm_median_sqft * size_sqft
            if price < comm_median_total * 0.30:
                return None  # Skip impossible listing
            price_per_sqft = price / size_sqft
            if price_per_sqft < 200 or price_per_sqft > 10000:
                return None  # Skip unrealistic price/sqft

    # Estimate completion time (default 2.5 years for off-plan)
    completion_years = 2.5

    # Step 1: Fair Value
    fair_value = calculate_fair_value(community_data, project_data, fs_data, size_sqft, bed_type)

    # Step 2: Price Difference
    price_diff = calculate_price_difference(price, fair_value["fairValue"])

    # Step 3: Future Appreciation
    future_apprec = calculate_future_appreciation(price, community_data, project_data, completion_years)

    # Step 4: Post-handover ROI
    roi = calculate_post_handover_roi(price, community_data, project_data, fs_data, bed_type, size_sqft)

    # Step 5: Developer Score
    dev_score = calculate_developer_score(dev_data)

    # Step 6: Community Score
    comm_score = calculate_community_score(community_data)

    # Liquidity
    liquidity = calculate_liquidity_score(community_data, project_data)

    # ─── Payment Plan Analysis ───
    payment_plans_raw = pl.get("payment_plans", [])
    if isinstance(payment_plans_raw, str):
        try:
            import json as _json
            payment_plans_raw = _json.loads(payment_plans_raw)
        except Exception:
            payment_plans_raw = []
    payment_plan = analyze_payment_plan(
        payment_plans_raw, price, future_apprec["futureValue"]
    )

    # ─── Exit Strategies ───
    exit_strategies = calculate_exit_strategies(
        price, future_apprec["futureValue"], completion_years,
        roi, payment_plan, dev_score["developerScore"]
    )

    # ─── Supply Risk Score ───
    supply_risk_score = comm_score.get("futureSupplyScore", 50)

    # ─── Final Investment Score (off-plan specific weights) ───
    investment_score = round(
        dev_score["developerScore"] * 0.25 +
        price_diff["priceOpportunityScore"] * 0.20 +
        payment_plan["paymentPlanScore"] * 0.15 +
        future_apprec["futureAppreciationScore"] * 0.10 +
        supply_risk_score * 0.10 +
        liquidity["liquidityScore"] * 0.05 +
        roi["roiScore"] * 0.05
    )

    # Recommendation
    recommendation = get_recommendation(price_diff["priceDifferencePct"], investment_score)

    # Risk assessment
    risk_factors = []
    if price_diff["priceDifferencePct"] > 10:
        risk_factors.append(f"Developer price is {price_diff['priceDifferencePct']:.1f}% above fair market value")
    if dev_score["developerScore"] < 70:
        risk_factors.append(f"Developer score {dev_score['developerScore']}/100 — below average track record")
    if dev_score.get("delayRisk") == "High":
        risk_factors.append("High delivery delay risk")
    if comm_score.get("futureSupplyScore", 50) < 40:
        risk_factors.append("High future supply in area may pressure prices on completion")
    if future_apprec["growthRate"] < 3:
        risk_factors.append("Low predicted capital growth based on area trends")
    if roi.get("hasRentData") and roi.get("netROI") is not None and roi["netROI"] < 4:
        risk_factors.append(f"Low post-handover net ROI ({roi['netROI']:.1f}%)")
    elif roi.get("hasRentData") is False:
        risk_factors.append("No rental data available — post-handover ROI estimate is uncertain")

    overall_risk = round(
        (100 - dev_score["developerScore"]) * 0.30 +
        (100 - comm_score.get("futureSupplyScore", 50)) * 0.25 +
        max(0, price_diff["priceDifferencePct"]) * 2 * 0.20 +
        (100 - future_apprec["futureAppreciationScore"]) * 0.15 +
        (100 - payment_plan["paymentPlanScore"]) * 0.10
    )
    risk_level = "Low" if overall_risk < 35 else "Medium" if overall_risk < 60 else "High"
    if not risk_factors:
        risk_factors.append("No significant risk factors identified")

    # AI Explainability
    reasons = []
    if price_diff["priceDifferencePct"] <= -5:
        reasons.append(f"Developer price is {abs(price_diff['priceDifferencePct']):.1f}% below fair market value — strong price opportunity")
    elif price_diff["priceDifferencePct"] > 10:
        reasons.append(f"Developer price is {price_diff['priceDifferencePct']:.1f}% above fair market value — overpriced")
    if dev_score["developerScore"] >= 80:
        reasons.append(f"Top-tier developer ({dev_score['developerName']}) with score {dev_score['developerScore']}/100")
    if future_apprec["potentialGainPct"] > 20:
        reasons.append(f"Projected {future_apprec['potentialGainPct']:.1f}% capital gain over {completion_years} years")
    if comm_score["communityScore"] >= 75:
        reasons.append(f"Strong community score ({comm_score['communityScore']}/100) in {area}")
    if roi.get("hasRentData") and roi.get("netROI") is not None and roi["netROI"] >= 7:
        reasons.append(f"Healthy post-handover net ROI of {roi['netROI']:.1f}%")
    if not reasons:
        reasons.append("Off-plan property meets baseline investment criteria")

    # ── Confidence Score ── (Issue 2,12: Build from evidence, not deduct from 100)
    # Separate confidence dimensions
    has_community = community_data is not None
    has_developer = dev_data is not None and dev_data.get("developerName", "Independent / Other") != "Independent / Other"
    has_rent = roi.get("hasRentData") is True
    has_fair_value = fair_value.get("source") not in ("none", "estimated")

    # Weight: developer 30%, area 25%, pricing 25%, rental 20%
    conf_parts = []
    conf_parts.append((30, 90 if has_developer else 30))
    conf_parts.append((25, 85 if has_community else 30))
    conf_parts.append((25, 85 if has_fair_value else 40))
    conf_parts.append((20, 80 if has_rent else 25))
    total_w = sum(w for w, _ in conf_parts)
    confidence_score = int(sum(w * s for w, s in conf_parts) / total_w)
    confidence_score = int(clamp(confidence_score, 0, 100))

    # Build confidence explanation
    conf_explanation_parts = []
    if has_developer:
        conf_explanation_parts.append("developer data available")
    else:
        conf_explanation_parts.append("limited developer data")
    if has_community:
        conf_explanation_parts.append("area market data available")
    else:
        conf_explanation_parts.append("limited area data")
    if has_fair_value:
        conf_explanation_parts.append("pricing evidence available")
    else:
        conf_explanation_parts.append("limited pricing evidence")
    if has_rent:
        conf_explanation_parts.append("rental data available")
    else:
        conf_explanation_parts.append("no rental data")
    confidence_explanation = "Confidence driven by: " + ", ".join(conf_explanation_parts) + "."

    # Override recommendation if confidence is too low
    if confidence_score < 40:
        recommendation = "INSUFFICIENT_DATA"

    # Enrichment data from Qdrant
    images = []
    for img in pl.get("images", [])[:10]:
        if isinstance(img, dict) and img.get("url"):
            images.append({"url": f"https://www.apilproperties.com/storage/{img['url']}", "alt": img.get("alt", "")})
        elif isinstance(img, str):
            images.append({"url": f"https://www.apilproperties.com/storage/{img}", "alt": ""})

    payment_plans = pl.get("payment_plans", [])
    if isinstance(payment_plans, str):
        try:
            payment_plans = json.loads(payment_plans)
        except Exception:
            payment_plans = []

    highlights = pl.get("highlights", [])
    if isinstance(highlights, str):
        try:
            highlights = json.loads(highlights)
        except Exception:
            highlights = []

    amenities = pl.get("feature_and_amenities") or pl.get("features_and_amenities", {})
    if isinstance(amenities, str):
        try:
            amenities = json.loads(amenities)
        except Exception:
            amenities = {}

    description = pl.get("description", "")
    if description:
        description = re.sub(r"<[^>]+>", "", description).strip()

    return {
        # Identity
        "id": pl.get("id"),
        "title": name,
        "slug": slug,
        "project": project_name,
        "area": area,
        "developer": developer_name,
        "bedType": bed_type,
        "category": pl.get("category", "Apartment"),
        "sizeSqft": size_sqft,
        "askingPrice": price,
        "priceSqft": round(price / size_sqft, 2) if size_sqft > 0 else None,
        "hasSize": size_sqft > 0,
        "status": "offplan",

        # Scores
        "offplanScore": investment_score,
        "recommendation": recommendation,
        "scoreLabel": score_to_label(investment_score),
        "confidenceScore": confidence_score,
        "confidenceExplanation": confidence_explanation,

        # Step 1: Fair Value
        "fairValue": fair_value,

        # Step 2: Price Difference
        "priceOpportunity": price_diff,

        # Step 3: Future Appreciation
        "futureAppreciation": future_apprec,

        # Step 4: Post-handover ROI
        "postHandoverROI": roi,

        # Step 5: Developer
        "developerData": dev_score,

        # Step 6: Community
        "communityData": comm_score,

        # Liquidity
        "liquidity": liquidity,

        # Risk
        "risk": {
            "overallRisk": overall_risk,
            "riskLevel": risk_level,
            "riskFactors": risk_factors,
            # Issue 6: Add components so frontend RiskMatrixCard works
            "components": {
                "futureSupplyRisk": 100 - comm_score.get("futureSupplyScore", 50),
                "developerRisk": 100 - dev_score.get("developerScore", 50),
                "areaSaturationRisk": 100 - comm_score.get("demandIndex", 50),
                "rentalRisk": 100 - (50 if roi.get("hasRentData") else 0),
                "marketVolatilityRisk": max(0, min(100, abs(price_diff.get("priceDifferencePct", 0)) * 5)),
                "constructionDelayRisk": 100 - dev_score.get("developerScore", 50),
                "pricePremiumRisk": max(0, min(100, price_diff.get("priceDifferencePct", 0) * 3 if price_diff.get("priceDifferencePct", 0) > 0 else 0)),
            },
        },

        # Score Breakdown (off-plan specific)
        "scoreBreakdown": {
            "developer": dev_score["developerScore"],
            "price": price_diff["priceOpportunityScore"],
            "paymentPlan": payment_plan["paymentPlanScore"],
            "growth": future_apprec["futureAppreciationScore"],
            "supplyRisk": supply_risk_score,
            "liquidity": liquidity["liquidityScore"],
            "roi": roi["roiScore"],
        },

        # Explainability
        "reasons": reasons,

        # Payment Plan Analysis
        "paymentPlanAnalysis": payment_plan,

        # Exit Strategies
        "exitStrategies": exit_strategies,

        # Enrichment from Qdrant
        "listingData": {
            "name": name,
            "slug": slug,
            "description": description,
            "images": images,
            "paymentPlans": payment_plans,
            "highlights": highlights,
            "amenities": amenities,
            "developer": developer_name,
            "latitude": pl.get("latitude"),
            "longitude": pl.get("longitude"),
            "floorPlanImage": pl.get("floor_plan_image"),
            "virtualTourUrl": pl.get("virtual_tour_url"),
            "videoId": pl.get("video_id"),
            "canonicalUrl": pl.get("canonical_url", ""),
            "sizeSqft": size_sqft,
            "noOfParking": pl.get("no_of_parking"),
            "noOfBathroom": pl.get("no_of_bathroom"),
        },

        "computedAt": datetime.now().isoformat(),
    }


# ─── Pipeline runner ───

def run():
    print("[Off-plan Engine v2] Starting...")

    # Load scoring data
    comm_scores = load_community_scores()
    dev_scores = load_developer_scores()
    proj_scores = load_project_scores()
    feature_store = load_feature_store()
    print(f"  Loaded {len(comm_scores)} communities, {len(dev_scores)} developers, {len(proj_scores)} projects, {len(feature_store)} feature records")

    # Fetch off-plan listings from Qdrant
    qdrant_points = fetch_offplan_from_qdrant()
    if not qdrant_points:
        print("  No off-plan listings found in Qdrant — falling back to existing scores")
        return

    # Score each property
    results = []
    skipped = 0
    for point in qdrant_points:
        pl = point.get("payload", {})
        scored = score_offplan_property(pl, comm_scores, dev_scores, proj_scores, feature_store)
        if scored:
            results.append(scored)
        else:
            skipped += 1

    print(f"  Scored {len(results)} properties, skipped {skipped} (missing price/size)")

    # Sort by investment score
    results.sort(key=lambda x: -x["offplanScore"])

    # Save
    save_json(OFFPLAN_SCORES_FILE, results)
    print(f"[Off-plan Engine v2] Saved {len(results)} off-plan scores to {OFFPLAN_SCORES_FILE}")
    return results


if __name__ == "__main__":
    run()
