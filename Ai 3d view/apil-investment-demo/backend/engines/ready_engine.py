"""
APIL Ready Property Intelligence Engine
Runs daily. Produces ready_property_scores.json

Pipeline:
  Property → Comparable Sales → Rental Transactions → Community Score →
  Project Score → Developer Score → Liquidity → Price Fairness → ROI →
  Ready Score

Formula:
  Price Fairness: 25%
  ROI:            25%
  Liquidity:      20%
  Community:      15%
  Developer:      10%
  Project:         5%
"""
from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.utils import (
    clamp, median, safe_float, safe_int, normalize_bed_type,
    parse_date, calculate_growth, calculate_growth_with_metadata, risk_from_score, save_json, load_json,
    score_to_label, recommendation_from_score
)
from config.settings import (
    READY_PROPERTY_SCORES_FILE, PROJECTS_JSON,
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
    # First try aliases from dev_scores
    for dev_name, dev_data in dev_scores.items():
        for alias in dev_data.get("aliases", []):
            if alias and alias in clean:
                return dev_data
        # Also check if developer name itself is in project name
        if dev_name.upper() in clean:
            return dev_data
    # Fallback: use keyword matching from developer_engine
    try:
        from engines.developer_engine import DEVELOPER_KEYWORDS, match_developer as dev_match
        matched_name = dev_match(project_name)
        if matched_name != "Independent / Other" and matched_name in dev_scores:
            return dev_scores[matched_name]
    except Exception:
        pass
    return None


def calculate_roi(asking_price: float, annual_rent: float, area_sqft: float, service_charge_per_sqft: float | None) -> dict:
    # Cap annual rent at 12% of asking price — prevents impossible ROI
    max_annual_rent = asking_price * 0.12
    if annual_rent > max_annual_rent:
        annual_rent = max_annual_rent

    has_service_charge = service_charge_per_sqft is not None and service_charge_per_sqft > 0
    if has_service_charge:
        service_charge_annual = round(area_sqft * service_charge_per_sqft)
    else:
        service_charge_annual = None
    vacancy_rate = 0.05
    management_fee = round(annual_rent * 0.05)
    vacancy_loss = round(annual_rent * vacancy_rate)
    if has_service_charge:
        net_annual_income = annual_rent - service_charge_annual - management_fee - vacancy_loss
    else:
        net_annual_income = annual_rent - management_fee - vacancy_loss
    gross_roi = (annual_rent / asking_price * 100) if asking_price > 0 else 0
    net_roi = (net_annual_income / asking_price * 100) if asking_price > 0 else 0

    # Cap ROI at realistic maximums
    gross_roi = min(gross_roi, 15.0)
    net_roi = min(net_roi, 12.0)

    return {
        "grossROI": round(gross_roi, 2),
        "netROI": round(net_roi, 2),
        "annualRent": round(annual_rent),
        "serviceChargeAnnual": service_charge_annual,
        "serviceChargePerSqft": round(service_charge_per_sqft, 2) if has_service_charge else None,
        "vacancyRate": vacancy_rate,
        "managementFee": management_fee,
        "netAnnualIncome": round(net_annual_income),
        "hasServiceChargeData": has_service_charge,
    }


def calculate_liquidity(txn_volume: int, listings_count: int, sales_history: list[dict]) -> dict:
    absorption_rate = round((txn_volume / listings_count) * 100) if listings_count > 0 else 0
    absorption_rate = min(absorption_rate, 300)  # Cap at 300%

    avg_days_on_market = 90
    if txn_volume > 0 and len(sales_history) > 1:
        dates = [parse_date(s.get("date", "")) for s in sales_history]
        dates = [d for d in dates if d]
        if len(dates) > 1:
            dates.sort()
            span_days = (dates[-1] - dates[0]).days
            avg_days_on_market = round(span_days / max(len(dates) - 1, 1))

    volume_score = clamp(txn_volume * 5, 0, 100)
    absorb_score = clamp(absorption_rate * 2, 0, 100)
    speed_score = clamp(100 - avg_days_on_market / 3, 0, 100)
    liquidity_score = round(volume_score * 0.40 + absorb_score * 0.35 + speed_score * 0.25)

    if liquidity_score >= 80:
        label = "Excellent"
    elif liquidity_score >= 65:
        label = "Good"
    elif liquidity_score >= 45:
        label = "Average"
    else:
        label = "Low"

    return {
        "liquidityScore": liquidity_score,
        "liquidityLabel": label,
        "absorptionRate": absorption_rate,
        "avgDaysOnMarket": avg_days_on_market,
    }


def calculate_risk(price_diff: float, dev_score: int, estimated_yield: float,
                   txn_volume: int, growth_12m: float, community_supply: int,
                   project_status: str, rent_count: int = 0) -> dict:
    risk_factors: list[str] = []

    # Future supply
    future_supply_risk = clamp(community_supply / 20, 0, 100)
    if future_supply_risk > 50:
        risk_factors.append(f"High future supply in community ({community_supply} upcoming units)")
    elif future_supply_risk > 25:
        risk_factors.append(f"Medium future supply in community ({community_supply} upcoming units)")
    elif future_supply_risk > 10:
        risk_factors.append(f"Moderate future supply ({community_supply} units)")

    # Developer
    developer_risk = 100 - dev_score
    if dev_score < 50:
        risk_factors.append("Weak developer track record with limited delivery history")
    elif dev_score < 65:
        risk_factors.append("Developer has average track record — some projects experienced delays")
    elif dev_score < 80:
        risk_factors.append("Moderate developer reputation — room for improvement")

    # Transaction volume
    area_saturation_risk = clamp(100 - txn_volume * 3, 0, 100)
    if txn_volume < 5:
        risk_factors.append("Low transaction volume indicates limited market activity")

    # Rental yield
    rental_risk = 70 if estimated_yield < 5 else 40 if estimated_yield < 7 else 20
    if estimated_yield < 5:
        risk_factors.append("Below-average rental yield increases vacancy risk")

    # Limited rental data
    if rent_count > 0 and rent_count < 10:
        risk_factors.append(f"Limited rental evidence ({rent_count} contracts)")
    elif rent_count == 0:
        risk_factors.append("No rental data available — rent estimate is uncertain")

    # Growth history
    market_volatility_risk = clamp(abs(growth_12m) * 3, 0, 100)
    if abs(growth_12m) > 20:
        risk_factors.append("High price volatility in recent transactions")
    elif growth_12m == 0:
        risk_factors.append("Growth history limited — insufficient data for appreciation estimate")

    # Construction delay
    construction_delay_risk = 60 if project_status == "Off-Plan" else 5
    if project_status == "Off-Plan":
        risk_factors.append("Off-plan project carries delivery timeline risk")

    # Price premium
    price_premium_risk = clamp(abs(price_diff) * 5, 0, 100)
    if price_diff > 10:
        risk_factors.append("Asking price is significantly above comparable sold prices")

    overall_risk = round(
        future_supply_risk * 0.15 +
        developer_risk * 0.20 +
        area_saturation_risk * 0.10 +
        rental_risk * 0.15 +
        market_volatility_risk * 0.10 +
        construction_delay_risk * 0.15 +
        price_premium_risk * 0.15
    )

    risk_level = "Low" if overall_risk < 35 else "Medium" if overall_risk < 60 else "High"
    if not risk_factors:
        risk_factors.append("No significant risk factors identified")

    return {
        "overallRisk": overall_risk,
        "riskLevel": risk_level,
        "riskFactors": risk_factors,
        "components": {
            "futureSupplyRisk": round(future_supply_risk),
            "developerRisk": round(developer_risk),
            "areaSaturationRisk": round(area_saturation_risk),
            "rentalRisk": rental_risk,
            "marketVolatilityRisk": round(market_volatility_risk),
            "constructionDelayRisk": construction_delay_risk,
            "pricePremiumRisk": round(price_premium_risk),
        }
    }


def compute_ready_property_score(
    listing: dict,
    project: dict,
    unit: dict | None,
    project_score_data: dict | None,
    community_data: dict | None,
    dev_data: dict | None,
) -> dict:
    asking_price = safe_float(listing.get("price"))
    area_sqft = safe_float(listing.get("size_sqft"))
    if asking_price <= 0 or area_sqft <= 0:
        return None

    bed_type = normalize_bed_type(listing.get("bedrooms", ""))
    price_sqft = round(asking_price / area_sqft)
    # Comparable price — use unit-level first, then project-level. NULL if insufficient data.
    comparable_price = None
    if unit and unit.get("medianPrice") and unit["medianPrice"] > 0:
        comparable_price = safe_float(unit["medianPrice"])
    elif project_score_data and project_score_data.get("medianPrice") and project_score_data["medianPrice"] > 0:
        comparable_price = safe_float(project_score_data["medianPrice"])

    # If no comparable data, mark as insufficient — don't use 0
    if comparable_price is None or comparable_price <= 0:
        comparable_price = 0
        price_diff = 0
        market_position = "Insufficient Comparables"
    else:
        price_diff = round(((asking_price - comparable_price) / comparable_price) * 100, 2)
        if price_diff < -5:
            market_position = "Value Opportunity"
        elif price_diff < 5:
            market_position = "Fair Market Value"
        elif price_diff < 15:
            market_position = "Premium Pricing"
        else:
            market_position = "High Premium"

    # Estimated rent — use unit-level median rent, with validation
    estimated_rent = 0
    if unit and unit.get("medianRent") and unit["medianRent"] > 0:
        estimated_rent = safe_float(unit["medianRent"])
    elif project_score_data and project_score_data.get("medianRent") and project_score_data["medianRent"] > 0:
        estimated_rent = safe_float(project_score_data["medianRent"])
    
    # Cap rent at 12% of asking price to prevent impossible yields
    if estimated_rent > 0 and asking_price > 0:
        max_rent = asking_price * 0.12
        if estimated_rent > max_rent:
            estimated_rent = max_rent
    
    estimated_yield = round((estimated_rent / asking_price) * 100, 2) if asking_price > 0 and estimated_rent > 0 else 0

    # M1: Price Fairness (25%) — reduced confidence if no comparables
    if comparable_price == 0:
        price_score = 50  # Neutral when no comparable data
    else:
        price_score = round(clamp(100 - abs(price_diff) * 3, 0, 100))

    # M2: ROI (25%) — with validation flag for high yields
    # Service charge: prefer project-level, fallback to project_score_data (DLD Mollak)
    service_charge_per_sqft = project.get("service_charge")
    if (service_charge_per_sqft is None or float(service_charge_per_sqft or 0) <= 0) and project_score_data:
        sc = project_score_data.get("serviceCharge")
        if sc is not None and float(sc) > 0:
            service_charge_per_sqft = float(sc)
    roi = calculate_roi(asking_price, estimated_rent, area_sqft, service_charge_per_sqft)
    roi_score = round(clamp(roi["netROI"] * 8, 0, 100))
    
    # Flag high ROI for verification
    roi_validation = "OK"
    if roi["grossROI"] > 10:
        roi_validation = "HIGH_ROI_VERIFY_RENT"
    elif estimated_rent == 0:
        roi_validation = "NO_RENT_DATA"
    elif not roi.get("hasServiceChargeData"):
        roi_validation = "NO_SERVICE_CHARGE_DATA"

    # M7: Liquidity (20%) — use project transaction volume
    sales_history = project.get("sales_history", [])
    rent_history = project.get("rent_history", [])
    txn_volume = len(sales_history)
    rent_volume = len(rent_history)
    listings_count = max(len(project.get("listings", [])), 1)
    liquidity = calculate_liquidity(txn_volume, listings_count, sales_history)

    # Rent range — show a range with confidence based on sample size
    rent_range = None
    if estimated_rent > 0:
        if rent_volume >= 20:
            rent_low = round(estimated_rent * 0.92)
            rent_high = round(estimated_rent * 1.08)
            rent_confidence = "High"
        elif rent_volume >= 5:
            rent_low = round(estimated_rent * 0.85)
            rent_high = round(estimated_rent * 1.15)
            rent_confidence = "Medium"
        else:
            rent_low = round(estimated_rent * 0.80)
            rent_high = round(estimated_rent * 1.20)
            rent_confidence = "Low"
        rent_range = {
            "low": rent_low,
            "high": rent_high,
            "mid": round(estimated_rent),
            "confidence": rent_confidence,
            "sampleSize": rent_volume,
        }

    # Demand score — derived from transaction + rental volume (not zero)
    demand_score = round(clamp(txn_volume * 5 + rent_volume * 3, 0, 100))

    # Community (15%)
    community_score = safe_int(community_data.get("communityScore")) if community_data else 50

    # Developer (10%)
    dev_score = safe_int(dev_data.get("developerScore")) if dev_data else 50

    # Project (5%)
    proj_score = safe_int(project_score_data.get("projectScore")) if project_score_data else 50

    # Growth
    # Growth — using valid sales only (with price AND unit area)
    valid_sales = []
    for s in sales_history:
        price = safe_float(s.get("price"))
        area = safe_float(s.get("area_sqft"))
        if price > 0 and area > 0:
            # Skip sales with area > 5000 sqft — plot/land area, not unit area
            if area > 5000:
                continue
            valid_sales.append({**s, "price_sqft": price / area})
    growth_12m_meta = calculate_growth_with_metadata(valid_sales, 12)
    growth_3m_meta = calculate_growth_with_metadata(valid_sales, 3)
    growth_6m_meta = calculate_growth_with_metadata(valid_sales, 6)
    growth_12m = growth_12m_meta["growth"]
    growth_3m = growth_3m_meta["growth"]
    growth_6m = growth_6m_meta["growth"]

    # Risk
    risk = calculate_risk(
        price_diff, dev_score, estimated_yield, txn_volume,
        growth_12m, safe_int(project.get("sales_volume")), "Ready", rent_volume
    )

    # Confidence score based on data quality
    confidence = 100
    if comparable_price == 0:
        confidence -= 20
    if estimated_rent == 0:
        confidence -= 20
    if txn_volume < 10:
        confidence -= 15
    if rent_volume < 5:
        confidence -= 10
    if dev_data is None:
        confidence -= 10
    if not roi.get("hasServiceChargeData"):
        confidence -= 10
    # ROI confidence penalty: if property yield is 2x+ community yield, flag it
    comm_yield = community_data.get("rentalYield", 0) if community_data else 0
    if comm_yield > 0 and estimated_yield > 0 and estimated_yield > comm_yield * 2:
        confidence -= 15
    confidence = int(clamp(confidence, 0, 100))

    # Data Completeness — tracks which data sources are available
    completeness = {
        "community": 0,
        "project": 0,
        "developer": 0,
        "property": 0,
        "overall": 0,
    }
    # Community completeness
    comm_fields = ["demandIndex", "supplyIndex", "growth12m", "medianPriceSqft", "medianRent", "rentalYield", "livabilityIndex", "transportIndex", "salesVolume", "rentVolume"]
    if community_data:
        comm_present = sum(1 for f in comm_fields if community_data.get(f) is not None and community_data.get(f) != 0)
        completeness["community"] = round(comm_present / len(comm_fields) * 100)
    # Project completeness
    proj_fields = ["priceSqft", "medianPrice", "rentalYield", "transactionVolume", "status", "unitTypes", "demandScore", "priceChangePct"]
    if project_score_data:
        proj_present = sum(1 for f in proj_fields if project_score_data.get(f) is not None)
        completeness["project"] = round(proj_present / len(proj_fields) * 100)
    # Developer completeness
    if dev_data and dev_data.get("name", "Independent / Other") != "Independent / Other":
        completeness["developer"] = 100
    elif dev_data:
        completeness["developer"] = 30
    else:
        completeness["developer"] = 0
    # Property completeness
    prop_fields_ok = sum([
        asking_price > 0,
        area_sqft > 0,
        comparable_price > 0,
        estimated_rent > 0,
        txn_volume > 0,
        rent_volume > 0,
    ])
    completeness["property"] = round(prop_fields_ok / 6 * 100)
    # Overall
    completeness["overall"] = round(
        completeness["community"] * 0.25 +
        completeness["project"] * 0.25 +
        completeness["developer"] * 0.20 +
        completeness["property"] * 0.30
    )

    # Ready Property Score: Price(25) + ROI(25) + Liquidity(20) + Community(15) + Developer(10) + Project(5)
    ready_score = round(
        price_score * 0.25 +
        roi_score * 0.25 +
        liquidity["liquidityScore"] * 0.20 +
        community_score * 0.15 +
        dev_score * 0.10 +
        proj_score * 0.05
    )

    # AI Explainability
    reasons: list[str] = []
    if price_diff < -5:
        reasons.append(f"Asking price is {abs(price_diff)}% below comparable sold prices — potential value opportunity")
    if roi["netROI"] > 6:
        reasons.append(f"Net rental yield of {roi['netROI']}% is above Dubai market average")
    if liquidity["liquidityLabel"] == "Excellent":
        reasons.append(f"Excellent resale liquidity — {liquidity['avgDaysOnMarket']} day average selling period")
    if dev_score >= 85:
        reasons.append(f"Developer has a {dev_score}/100 reliability score with excellent delivery history")
    if growth_12m > 10:
        reasons.append(f"Strong capital appreciation of {round(growth_12m)}% over the last 12 months")
    if market_position == "Fair Market Value":
        reasons.append("Asking price is aligned with verified DLD transactions")
    if risk["riskLevel"] == "Low":
        reasons.append("Low overall risk profile with balanced supply and sustained demand")
    if not reasons:
        reasons.append("Property meets baseline investment criteria")

    # Lost points analysis — explain what prevents a higher score
    lost_points: list[str] = []
    if price_score < 80:
        lost_points.append(f"Price score {price_score}/100 — asking price is {'above' if price_diff > 0 else 'near'} comparable sold prices")
    if roi_score < 80:
        lost_points.append(f"ROI score {roi_score}/100 — net yield of {roi['netROI']}% is {'below average' if roi['netROI'] < 7 else 'moderate'}")
    if liquidity["liquidityScore"] < 80:
        lost_points.append(f"Liquidity score {liquidity['liquidityScore']}/100 — resale may take longer than average")
    if community_score < 80:
        lost_points.append(f"Community score {community_score}/100 — area fundamentals have room for improvement")
    if dev_score < 75:
        lost_points.append(f"Developer score {dev_score}/100 — {'limited delivery history' if dev_score < 60 else 'some projects experienced delays'}")
    if proj_score < 75:
        lost_points.append(f"Project score {proj_score}/100 — project-level metrics are moderate")
    if rent_volume < 10:
        lost_points.append(f"Limited rental data ({rent_volume} contracts) — rent estimate has lower confidence")
    if not lost_points:
        lost_points.append("No significant weaknesses identified — this is a strong investment opportunity")

    return {
        "id": listing.get("id"),
        "title": listing.get("title"),
        "category": listing.get("category", "Apartment"),
        "project": project["name"],
        "projectSlug": project.get("slug", ""),
        "area": project.get("area", "Unknown"),
        "bedType": bed_type,
        "askingPrice": asking_price,
        "priceSqft": price_sqft,
        "areaSqft": area_sqft,
        "comparablePrice": round(comparable_price),
        "priceDifference": price_diff,
        "marketPosition": market_position,
        "estimatedRent": round(estimated_rent),
        "estimatedYield": estimated_yield,
        "readyScore": ready_score,
        "recommendation": recommendation_from_score(ready_score),
        "scoreLabel": score_to_label(ready_score),
        "priceScore": price_score,
        "roi": roi,
        "roiScore": roi_score,
        "liquidity": liquidity,
        "communityScore": community_score,
        "developerScore": dev_score,
        "projectScore": proj_score,
        "developerName": dev_data.get("name", "Independent / Other") if dev_data else "Independent / Other",
        "growth3m": growth_3m,
        "growth6m": growth_6m,
        "growth12m": growth_12m,
        "growthMetadata": {
            "3m": growth_3m_meta,
            "6m": growth_6m_meta,
            "12m": growth_12m_meta,
        },
        "rentRange": rent_range,
        "scoreBreakdown": {
            "price": price_score,
            "roi": roi_score,
            "liquidity": liquidity["liquidityScore"],
            "community": community_score,
            "developer": dev_score,
            "project": proj_score,
        },
        "risk": risk,
        "reasons": reasons,
        "lostPoints": lost_points,
        "confidenceScore": confidence,
        "demandScore": demand_score,
        # Embedded entity data — prevents frontend mismatch
        "communityData": {
            "name": project.get("area", "Unknown"),
            "communityScore": community_score,
            "demandIndex": community_data.get("demandIndex") if community_data else None,
            "supplyIndex": community_data.get("supplyIndex") if community_data else None,
            "growth12m": community_data.get("growth12m") if community_data else None,
            "growth6m": community_data.get("growth6m") if community_data else None,
            "growth3m": community_data.get("growth3m") if community_data else None,
            "medianPriceSqft": community_data.get("medianPriceSqft") if community_data else None,
            "medianRent": community_data.get("medianRent") if community_data else None,
            "rentalYield": community_data.get("rentalYield") if community_data else None,
            "luxuryIndex": community_data.get("luxuryIndex") if community_data else None,
            "livabilityIndex": community_data.get("livabilityIndex") if community_data else None,
            "transportIndex": community_data.get("transportIndex") if community_data else None,
            "transactionScore": community_data.get("transactionScore") if community_data else None,
            "salesVolume": community_data.get("salesVolume") if community_data else None,
            "rentVolume": community_data.get("rentVolume") if community_data else None,
            "totalProjects": community_data.get("totalProjects") if community_data else None,
            "totalSupply": community_data.get("totalSupply") if community_data else None,
            "riskLevel": community_data.get("riskLevel") if community_data else None,
            "subScores": community_data.get("subScores") if community_data else None,
            "scoreBreakdown": community_data.get("scoreBreakdown") if community_data else None,
        } if community_data else None,
        "projectData": {
            "name": project["name"],
            "slug": project.get("slug", ""),
            "area": project.get("area", "Unknown"),
            "projectScore": proj_score,
            "status": project_score_data.get("status", "Ready") if project_score_data else "Ready",
            "priceSqft": project_score_data.get("priceSqft") if project_score_data else None,
            "priceChangePct": project_score_data.get("priceChangePct") if project_score_data else None,
            "growth12m": project_score_data.get("growth12m") if project_score_data else None,
            "demandScore": project_score_data.get("demandScore") if project_score_data else None,
            "liquidityScore": project_score_data.get("liquidityScore") if project_score_data else None,
            "medianPrice": project_score_data.get("medianPrice") if project_score_data else None,
            "medianRent": project_score_data.get("medianRent") if project_score_data else None,
            "rentalYield": project_score_data.get("rentalYield") if project_score_data else None,
            "transactionVolume": project_score_data.get("transactionVolume") if project_score_data else None,
            "riskLevel": project_score_data.get("riskLevel") if project_score_data else None,
            "unitTypes": project_score_data.get("unitTypes") if project_score_data else None,
            "confidenceScore": project_score_data.get("confidenceScore") if project_score_data else None,
            "scoreBreakdown": project_score_data.get("scoreBreakdown") if project_score_data else None,
        } if project_score_data else None,
        "developerData": {
            "name": dev_data.get("name", "Independent / Other") if dev_data else "Independent / Other",
            "developerScore": dev_score,
            "scoreBreakdown": dev_data.get("scoreBreakdown") if dev_data else None,
            "projectsDelivered": dev_data.get("projectsDelivered") if dev_data else 0,
            "marketPosition": dev_data.get("marketPosition") if dev_data else "Unknown",
            "buyerConfidence": dev_data.get("buyerConfidence") if dev_data else "Unknown",
            "deliveryDelayRisk": dev_data.get("deliveryDelayRisk") if dev_data else "Unknown",
            "deliveryDelayPercent": dev_data.get("delayedProjects") if dev_data else None,
            "constructionQuality": dev_data.get("constructionQuality") if dev_data else None,
            "marketReputation": dev_data.get("marketReputation", round(dev_score / 10)) if dev_data else round(dev_score / 10),
            "googleRating": dev_data.get("googleRating") if dev_data else None,
        } if dev_data else None,
        "dataQuality": {
            "hasComparables": comparable_price > 0,
            "hasRentData": estimated_rent > 0,
            "hasServiceChargeData": roi.get("hasServiceChargeData", False),
            "salesCount": txn_volume,
            "rentCount": rent_volume,
            "comparableCount": txn_volume,
            "roiValidation": roi_validation,
        },
        "dataCompleteness": completeness,
        "computedAt": datetime.now().isoformat(),
    }


def run():
    print("[Ready Property Engine] Starting...")
    projects = load_json(PROJECTS_JSON)
    communities = load_community_scores()
    developers = load_developer_scores()
    project_scores = load_project_scores()

    results = []
    for project in projects:
        listings = project.get("listings", [])
        if not listings:
            continue

        # Only Ready properties
        sales = project.get("sales_history", [])
        is_ready = any(s.get("area_sqft") for s in sales[:3])
        if not is_ready:
            continue

        dev_data = match_developer(project["name"], developers)
        community_data = communities.get(project.get("area", ""))
        proj_score_data = project_scores.get(project["name"])

        # Build unit map
        unit_map: dict[str, dict] = {}
        if proj_score_data and proj_score_data.get("unitTypes"):
            for u in proj_score_data["unitTypes"]:
                unit_map[u["bedType"]] = u

        for listing in listings[:6]:
            bed_type = normalize_bed_type(listing.get("bedrooms", ""))
            unit = unit_map.get(bed_type)
            score = compute_ready_property_score(
                listing, project, unit, proj_score_data, community_data, dev_data
            )
            if score:
                results.append(score)

    results.sort(key=lambda x: -x["readyScore"])
    save_json(READY_PROPERTY_SCORES_FILE, results)
    print(f"[Ready Property Engine] Computed {len(results)} ready property scores")
    return results


if __name__ == "__main__":
    run()
