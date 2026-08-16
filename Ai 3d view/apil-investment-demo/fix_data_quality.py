"""
Comprehensive data quality fix script.
Fixes:
1. Missing rent data treated as 0 ROI → Unknown/null
2. Impossible prices not validated → reject listings vs community median
3. Median sold = 0 → null/Insufficient Data
4. Recommendation based on missing data → INSUFFICIENT_DATA when confidence < 40%
5. Price/sqft validation → reject unrealistic values
"""
import re

SERVER = "shivang@87.200.15.174"
PASS = "Apil12!@123"
BASE = "/home/shivang/apil-investment-new/backend"

# ─── 1. Fix utils.py: recommendation_from_score to accept confidence ───

UTILS_PATCH = '''
import re

with open("engines/utils.py", "r") as f:
    content = f.read()

# Replace recommendation_from_score to accept confidence parameter
old_rec = '''def recommendation_from_score(score: float) -> str:
    if score >= 85:
        return "STRONG BUY"
    if score >= 75:
        return "BUY"
    if score >= 65:
        return "HOLD"
    if score >= 55:
        return "CAUTION"
    return "AVOID"'''

new_rec = '''def recommendation_from_score(score: float, confidence: float = 100) -> str:
    # If confidence is too low, return INSUFFICIENT_DATA regardless of score
    if confidence < 40:
        return "INSUFFICIENT_DATA"
    if score >= 85:
        return "STRONG BUY" if confidence >= 80 else "BUY"
    if score >= 75:
        return "BUY" if confidence >= 75 else "HOLD"
    if score >= 65:
        return "HOLD" if confidence >= 70 else "CAUTION"
    if score >= 55:
        return "CAUTION" if confidence >= 60 else "AVOID"
    return "AVOID"'''

content = content.replace(old_rec, new_rec)

with open("engines/utils.py", "w") as f:
    f.write(content)

print("[utils.py] Patched recommendation_from_score with confidence parameter")
'''

# ─── 2. Fix ready_engine.py ───

READY_ENGINE_PATCH = r'''
import re

with open("engines/ready_engine.py", "r") as f:
    content = f.read()

# Fix 1: calculate_roi — return None for ROI when annual_rent is 0
old_roi = '''def calculate_roi(asking_price: float, annual_rent: float, area_sqft: float, service_charge_per_sqft: float | None) -> dict:
    # Cap annual rent at 12% of asking price — prevents impossible ROI
    max_annual_rent = asking_price * 0.12
    if annual_rent > max_annual_rent:
        annual_rent = max_annual_rent

    service_charge = service_charge_per_sqft if service_charge_per_sqft and service_charge_per_sqft > 0 else 15
    service_charge_annual = round(area_sqft * service_charge)
    vacancy_rate = 0.05
    management_fee = round(annual_rent * 0.05)
    vacancy_loss = round(annual_rent * vacancy_rate)
    net_annual_income = annual_rent - service_charge_annual - management_fee - vacancy_loss
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
        "vacancyRate": vacancy_rate,
        "managementFee": management_fee,
        "netAnnualIncome": round(net_annual_income),
    }'''

new_roi = '''def calculate_roi(asking_price: float, annual_rent: float, area_sqft: float, service_charge_per_sqft: float | None) -> dict:
    # If no rent data, return Unknown — never treat missing as 0
    if annual_rent <= 0 or asking_price <= 0:
        return {
            "grossROI": None,
            "netROI": None,
            "annualRent": None,
            "serviceChargeAnnual": None,
            "vacancyRate": 0.05,
            "managementFee": None,
            "netAnnualIncome": None,
            "hasRentData": False,
        }

    # Cap annual rent at 12% of asking price — prevents impossible ROI
    max_annual_rent = asking_price * 0.12
    if annual_rent > max_annual_rent:
        annual_rent = max_annual_rent

    service_charge = service_charge_per_sqft if service_charge_per_sqft and service_charge_per_sqft > 0 else 15
    service_charge_annual = round(area_sqft * service_charge)
    vacancy_rate = 0.05
    management_fee = round(annual_rent * 0.05)
    vacancy_loss = round(annual_rent * vacancy_rate)
    net_annual_income = annual_rent - service_charge_annual - management_fee - vacancy_loss
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
        "vacancyRate": vacancy_rate,
        "managementFee": management_fee,
        "netAnnualIncome": round(net_annual_income),
        "hasRentData": True,
    }'''

content = content.replace(old_roi, new_roi)

# Fix 2: In compute_ready_property_score — add price validation against community median
# Find the section after price_sqft calculation and add validation
old_price_section = '''    bed_type = normalize_bed_type(listing.get("bedrooms", ""))
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
    roi = calculate_roi(asking_price, estimated_rent, area_sqft, project.get("service_charge"))
    roi_score = round(clamp(roi["netROI"] * 8, 0, 100))
    
    # Flag high ROI for verification
    roi_validation = "OK"
    if roi["grossROI"] > 10:
        roi_validation = "HIGH_ROI_VERIFY_RENT"
    elif estimated_rent == 0:
        roi_validation = "NO_RENT_DATA"'''

new_price_section = '''    bed_type = normalize_bed_type(listing.get("bedrooms", ""))
    price_sqft = round(asking_price / area_sqft)

    # ── Price Validation: reject impossible listings ──
    # Check against community median if available
    comm_median_price = 0
    if community_data:
        comm_median_price = safe_float(community_data.get("medianPriceSqft", 0)) * area_sqft
    # Also check project-level median
    proj_median_price = 0
    if project_score_data:
        proj_median_price = safe_float(project_score_data.get("medianPrice", 0))

    # Reject listings where price is more than 70% below community median
    # (e.g., AED 400K for a 4BR villa where median is AED 3.8M)
    reference_median = comm_median_price if comm_median_price > 0 else proj_median_price
    if reference_median > 0 and asking_price < reference_median * 0.30:
        return None  # Skip impossible listing — likely data error

    # Reject listings with unrealistic price/sqft (< AED 200 or > AED 10,000)
    if price_sqft < 200 or price_sqft > 10000:
        return None  # Skip unrealistic price/sqft

    # Comparable price — use unit-level first, then project-level. NULL if insufficient data.
    comparable_price = None
    if unit and unit.get("medianPrice") and unit["medianPrice"] > 0:
        comparable_price = safe_float(unit["medianPrice"])
    elif project_score_data and project_score_data.get("medianPrice") and project_score_data["medianPrice"] > 0:
        comparable_price = safe_float(project_score_data["medianPrice"])

    # If no comparable data, mark as insufficient — don't use 0
    if comparable_price is None or comparable_price <= 0:
        comparable_price = None  # Use None, not 0
        price_diff = None
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
    estimated_rent = None  # Use None instead of 0
    if unit and unit.get("medianRent") and unit["medianRent"] > 0:
        estimated_rent = safe_float(unit["medianRent"])
    elif project_score_data and project_score_data.get("medianRent") and project_score_data["medianRent"] > 0:
        estimated_rent = safe_float(project_score_data["medianRent"])

    # Cap rent at 12% of asking price to prevent impossible yields
    if estimated_rent and estimated_rent > 0 and asking_price > 0:
        max_rent = asking_price * 0.12
        if estimated_rent > max_rent:
            estimated_rent = max_rent

    estimated_yield = round((estimated_rent / asking_price) * 100, 2) if asking_price > 0 and estimated_rent and estimated_rent > 0 else None

    # M1: Price Fairness (25%) — reduced confidence if no comparables
    if comparable_price is None:
        price_score = 50  # Neutral when no comparable data
    else:
        price_score = round(clamp(100 - abs(price_diff) * 3, 0, 100))

    # M2: ROI (25%) — with validation flag for high yields
    roi = calculate_roi(asking_price, estimated_rent or 0, area_sqft, project.get("service_charge"))
    # If no rent data, ROI score is neutral (50), not 0
    if roi.get("hasRentData") is False:
        roi_score = 50  # Neutral — don't penalize for missing data
    else:
        roi_score = round(clamp((roi["netROI"] or 0) * 8, 0, 100))

    # Flag high ROI for verification
    roi_validation = "OK"
    if roi.get("hasRentData") and roi.get("grossROI") and roi["grossROI"] > 10:
        roi_validation = "HIGH_ROI_VERIFY_RENT"
    elif roi.get("hasRentData") is False:
        roi_validation = "NO_RENT_DATA"'''

content = content.replace(old_price_section, new_price_section)

# Fix 3: Fix references to roi["netROI"] that assume it's always a number
# In the risk calculation, estimated_yield could be None
old_risk_call = '''    # Risk
    risk = calculate_risk(
        price_diff, dev_score, estimated_yield, txn_volume,
        growth_12m, safe_int(project.get("sales_volume")), "Ready", rent_volume
    )'''

new_risk_call = '''    # Risk
    risk = calculate_risk(
        price_diff or 0, dev_score, estimated_yield or 0, txn_volume,
        growth_12m, safe_int(project.get("sales_volume")), "Ready", rent_volume
    )'''

content = content.replace(old_risk_call, new_risk_call)

# Fix 4: Fix confidence calculation to use None checks
old_conf = '''    # Confidence score based on data quality
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
    # ROI confidence penalty: if property yield is 2x+ community yield, flag it
    comm_yield = community_data.get("rentalYield", 0) if community_data else 0
    if comm_yield > 0 and estimated_yield > 0 and estimated_yield > comm_yield * 2:
        confidence -= 15
    confidence = int(clamp(confidence, 0, 100))'''

new_conf = '''    # Confidence score based on data quality
    confidence = 100
    if comparable_price is None:
        confidence -= 20
    if estimated_rent is None or estimated_rent <= 0:
        confidence -= 20
    if txn_volume < 10:
        confidence -= 15
    if rent_volume < 5:
        confidence -= 10
    if dev_data is None:
        confidence -= 10
    # ROI confidence penalty: if property yield is 2x+ community yield, flag it
    comm_yield = community_data.get("rentalYield", 0) if community_data else 0
    if comm_yield > 0 and estimated_yield and estimated_yield > 0 and estimated_yield > comm_yield * 2:
        confidence -= 15
    confidence = int(clamp(confidence, 0, 100))

    # If confidence is too low, override recommendation
    final_recommendation = recommendation_from_score(ready_score, confidence)'''

content = content.replace(old_conf, new_conf)

# Fix 5: Update the return dict to use final_recommendation and null-safe values
old_return_rec = '''        "readyScore": ready_score,
        "recommendation": recommendation_from_score(ready_score),
        "scoreLabel": score_to_label(ready_score),'''

new_return_rec = '''        "readyScore": ready_score,
        "recommendation": final_recommendation,
        "scoreLabel": score_to_label(ready_score),'''

content = content.replace(old_return_rec, new_return_rec)

# Fix 6: Update comparablePrice to use None instead of 0
old_comp_return = '''        "comparablePrice": round(comparable_price),'''
new_comp_return = '''        "comparablePrice": round(comparable_price) if comparable_price else None,'''

content = content.replace(old_comp_return, new_comp_return)

# Fix 7: Update estimatedRent and estimatedYield to use None
old_rent_return = '''        "estimatedRent": round(estimated_rent),
        "estimatedYield": estimated_yield,'''

new_rent_return = '''        "estimatedRent": round(estimated_rent) if estimated_rent else None,
        "estimatedYield": estimated_yield if estimated_yield is not None else None,'''

content = content.replace(old_rent_return, new_rent_return)

# Fix 8: Update rent_range to handle None
old_rent_range = '''    # Rent range — show a range with confidence based on sample size
    rent_range = None
    if estimated_rent > 0:'''

new_rent_range = '''    # Rent range — show a range with confidence based on sample size
    rent_range = None
    if estimated_rent and estimated_rent > 0:'''

content = content.replace(old_rent_range, new_rent_range)

# Fix 9: Update dataQuality to use proper checks
old_dq = '''        "dataQuality": {
            "hasComparables": comparable_price > 0,
            "hasRentData": estimated_rent > 0,
            "salesCount": txn_volume,
            "rentCount": rent_volume,
            "comparableCount": txn_volume,
            "roiValidation": roi_validation,
        },'''

new_dq = '''        "dataQuality": {
            "hasComparables": comparable_price is not None and comparable_price > 0,
            "hasRentData": estimated_rent is not None and estimated_rent > 0,
            "salesCount": txn_volume,
            "rentCount": rent_volume,
            "comparableCount": txn_volume,
            "roiValidation": roi_validation,
        },'''

content = content.replace(old_dq, new_dq)

# Fix 10: Update reasons to handle None values
old_reasons_roi = '''    if roi["netROI"] > 6:
        reasons.append(f"Net rental yield of {roi['netROI']}% is above Dubai market average")'''

new_reasons_roi = '''    if roi.get("hasRentData") and roi.get("netROI") and roi["netROI"] > 6:
        reasons.append(f"Net rental yield of {roi['netROI']}% is above Dubai market average")'''

content = content.replace(old_reasons_roi, new_reasons_roi)

# Fix 11: Update lost_points to handle None
old_lost_roi = '''    if roi_score < 80:
        lost_points.append(f"ROI score {roi_score}/100 — net yield of {roi['netROI']}% is {'below average' if roi['netROI'] < 7 else 'moderate'}")'''

new_lost_roi = '''    if roi_score < 80:
        if roi.get("hasRentData") and roi.get("netROI") is not None:
            lost_points.append(f"ROI score {roi_score}/100 — net yield of {roi['netROI']}% is {'below average' if roi['netROI'] < 7 else 'moderate'}")
        else:
            lost_points.append(f"ROI score {roi_score}/100 — no rental data available, ROI not scored")'''

content = content.replace(old_lost_roi, new_lost_roi)

# Fix 12: Update completeness to use None checks
old_completeness_prop = '''    # Property completeness
    prop_fields_ok = sum([
        asking_price > 0,
        area_sqft > 0,
        comparable_price > 0,
        estimated_rent > 0,
        txn_volume > 0,
        rent_volume > 0,
    ])'''

new_completeness_prop = '''    # Property completeness
    prop_fields_ok = sum([
        asking_price > 0,
        area_sqft > 0,
        comparable_price is not None and comparable_price > 0,
        estimated_rent is not None and estimated_rent > 0,
        txn_volume > 0,
        rent_volume > 0,
    ])'''

content = content.replace(old_completeness_prop, new_completeness_prop)

with open("engines/ready_engine.py", "w") as f:
    f.write(content)

print("[ready_engine.py] Patched: ROI null-safe, price validation, confidence-based recommendation")
'''

# ─── 3. Fix offplan_engine_v2.py ───

OFFPLAN_PATCH = r'''
import re

with open("engines/offplan_engine_v2.py", "r") as f:
    content = f.read()

# Fix 1: calculate_post_handover_roi — return null values when no rent data
old_no_rent = '''    if estimated_rent == 0 or developer_price <= 0:
        return {
            "estimatedRent": 0,
            "rentSource": rent_source,
            "grossROI": 0,
            "netROI": 0,
            "roiScore": 50,
        }'''

new_no_rent = '''    if estimated_rent == 0 or developer_price <= 0:
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
        }'''

content = content.replace(old_no_rent, new_no_rent)

# Add hasRentData: True to the normal return
old_roi_return = '''        "grossROI": round(gross_roi, 2),
        "netROI": round(net_roi, 2),
        "roiScore": score,
    }'''

new_roi_return = '''        "grossROI": round(gross_roi, 2),
        "netROI": round(net_roi, 2),
        "roiScore": score,
        "hasRentData": True,
    }'''

content = content.replace(old_roi_return, new_roi_return)

# Fix 2: Add price validation in score_offplan_property
# Find the section where price and size are extracted
old_price_extract = '''    # Estimate completion time (default 2.5 years for off-plan)
    completion_years = 2.5'''

new_price_extract = '''    # ── Price Validation: reject impossible listings ──
    # Check against community median if available
    comm_data = match_community(area, comm_scores)
    if comm_data:
        comm_median_sqft = safe_float(comm_data.get("priceIndex", {}).get("medianPriceSqft", 0))
        if comm_median_sqft > 0 and size_sqft > 0:
            comm_median_total = comm_median_sqft * size_sqft
            # Reject if price is more than 70% below community median
            if price < comm_median_total * 0.30:
                return None  # Skip impossible listing
            # Reject if price/sqft is unrealistic
            price_per_sqft = price / size_sqft
            if price_per_sqft < 200 or price_per_sqft > 10000:
                return None  # Skip unrealistic price/sqft

    # Estimate completion time (default 2.5 years for off-plan)
    completion_years = 2.5'''

content = content.replace(old_price_extract, new_price_extract)

# Fix 3: Add confidence score to offplan properties
# Find the return dict and add confidence + override recommendation
old_offplan_return_rec = '''        "offplanScore": investment_score,
        "recommendation": recommendation,
        "scoreLabel": score_to_label(investment_score),'''

new_offplan_return_rec = '''        "offplanScore": investment_score,
        "recommendation": recommendation,
        "scoreLabel": score_to_label(investment_score),
        "confidenceScore": confidence_score,'''

content = content.replace(old_offplan_return_rec, new_offplan_return_rec)

# Add confidence calculation before the return dict
old_before_return = '''    # Enrichment data from Qdrant
    images = []'''

new_before_return = '''    # ── Confidence Score ──
    confidence_score = 100
    if not community_data:
        confidence_score -= 25
    if not dev_data or dev_data.get("developerName", "Independent / Other") == "Independent / Other":
        confidence_score -= 15
    if roi.get("hasRentData") is False:
        confidence_score -= 20
    if fair_value.get("source") == "estimated":
        confidence_score -= 10
    if fair_value.get("source") == "none":
        confidence_score -= 25
    confidence_score = int(clamp(confidence_score, 0, 100))

    # Override recommendation if confidence is too low
    if confidence_score < 40:
        recommendation = "INSUFFICIENT_DATA"

    # Enrichment data from Qdrant
    images = []'''

content = content.replace(old_before_return, new_before_return)

# Fix 4: Update risk factors to handle None ROI
old_risk_roi = '''    if roi["netROI"] < 4:
        risk_factors.append(f"Low post-handover net ROI ({roi['netROI']:.1f}%)")'''

new_risk_roi = '''    if roi.get("hasRentData") and roi.get("netROI") is not None and roi["netROI"] < 4:
        risk_factors.append(f"Low post-handover net ROI ({roi['netROI']:.1f}%)")
    elif roi.get("hasRentData") is False:
        risk_factors.append("No rental data available — post-handover ROI estimate is uncertain")'''

content = content.replace(old_risk_roi, new_risk_roi)

# Fix 5: Update reasons to handle None ROI
old_reason_roi = '''    if roi["netROI"] >= 7:
        reasons.append(f"Healthy post-handover net ROI of {roi['netROI']:.1f}%")'''

new_reason_roi = '''    if roi.get("hasRentData") and roi.get("netROI") is not None and roi["netROI"] >= 7:
        reasons.append(f"Healthy post-handover net ROI of {roi['netROI']:.1f}%")'''

content = content.replace(old_reason_roi, new_reason_roi)

with open("engines/offplan_engine_v2.py", "w") as f:
    f.write(content)

print("[offplan_engine_v2.py] Patched: ROI null-safe, price validation, confidence score, INSUFFICIENT_DATA")
'''

# ─── 4. Fix recommendation_engine.py ───

REC_ENGINE_PATCH = r'''
import re

with open("engines/recommendation_engine.py", "r") as f:
    content = f.read()

# Fix 1: Add confidence-based filtering in generate_recommendations
# After building combined list, filter out INSUFFICIENT_DATA recommendations
old_combined_sort = '''    # Sort combined by goal-aware metric
    def get_score(p):
        if "readyScore" in p:
            return p["readyScore"]
        if "offplanScore" in p:
            return p["offplanScore"]
        return 0

    def get_sort_key(p):
        if goal == "rental_income":
            return -safe_float(p.get("roi", {}).get("netROI", 0)) if p.get("propertyType") == "ready" else -safe_float(p.
get("offplanScore", 0))                                                                                                          elif goal == "capital_growth":
            return -safe_float(p.get("growth12m", 0)) if p.get("propertyType") == "ready" else -safe_float(p.get("growthF
orecast", {}).get("predictedGrowth", 0))                                                                                         else:
            return -get_score(p)
    combined.sort(key=get_sort_key)'''

new_combined_sort = '''    # Filter out INSUFFICIENT_DATA recommendations — don't recommend based on missing data
    combined = [p for p in combined if p.get("recommendation", "") != "INSUFFICIENT_DATA"]

    # Sort combined by goal-aware metric
    def get_score(p):
        if "readyScore" in p:
            return p["readyScore"]
        if "offplanScore" in p:
            return p["offplanScore"]
        return 0

    def get_sort_key(p):
        if goal == "rental_income":
            roi_val = p.get("roi", {}).get("netROI")
            if roi_val is None:
                roi_val = 0
            post_roi_val = p.get("postHandoverROI", {}).get("netROI")
            if post_roi_val is None:
                post_roi_val = 0
            return -safe_float(roi_val) if p.get("propertyType") == "ready" else -safe_float(post_roi_val if post_roi_val else p.get("offplanScore", 0))
        elif goal == "capital_growth":
            growth_val = p.get("growth12m", 0)
            future_growth = p.get("futureAppreciation", {}).get("potentialGainPct", 0)
            return -safe_float(growth_val) if p.get("propertyType") == "ready" else -safe_float(future_growth)
        else:
            return -get_score(p)
    combined.sort(key=get_sort_key)'''

content = content.replace(old_combined_sort, new_combined_sort)

# Fix 2: Update rec_confidence to handle INSUFFICIENT_DATA
old_rec_conf = '''    # Build recommendation confidence for top property
    rec_confidence = {}
    if combined:
        top = combined[0]
        rec_confidence = {
            "score": get_score(top),
            "confidence": top.get("confidenceScore", 50),
            "matchReasons": _build_match_reasons(top, profile),
        }'''

new_rec_conf = '''    # Build recommendation confidence for top property
    rec_confidence = {}
    if combined:
        top = combined[0]
        top_conf = top.get("confidenceScore", 50)
        rec_confidence = {
            "score": get_score(top),
            "confidence": top_conf,
            "matchReasons": _build_match_reasons(top, profile),
        }
        # If top property has low confidence, note it
        if top_conf < 40:
            rec_confidence["warning"] = "Insufficient data — recommendation based on limited evidence"'''

content = content.replace(old_rec_conf, new_rec_conf)

with open("engines/recommendation_engine.py", "w") as f:
    f.write(content)

print("[recommendation_engine.py] Patched: INSUFFICIENT_DATA filtering, null-safe sorting, confidence warning")
'''

# Write all patches to a single script
with open("fix_data_quality.py", "w") as f:
    f.write("import subprocess, sys\n")
    f.write("patches = [\n")
    f.write(f"    {repr(UTILS_PATCH)},\n")
    f.write(f"    {repr(READY_ENGINE_PATCH)},\n")
    f.write(f"    {repr(OFFPLAN_PATCH)},\n")
    f.write(f"    {repr(REC_ENGINE_PATCH)},\n")
    f.write("]\n")
    f.write("for i, patch in enumerate(patches):\n")
    f.write("    with open(f'/tmp/patch_{i}.py', 'w') as pf:\n")
    f.write("        pf.write(patch)\n")
    f.write("    result = subprocess.run([sys.executable, f'/tmp/patch_{i}.py'], capture_output=True, text=True, cwd='/home/shivang/apil-investment-new/backend')\n")
    f.write("    print(result.stdout)\n")
    f.write("    if result.returncode != 0:\n")
    f.write("        print(f'ERROR in patch {i}:', result.stderr)\n")
    f.write("    else:\n")
    f.write("        print(f'Patch {i} applied successfully')\n")

print("fix_data_quality.py created")
