"""
APIL Recommendation Engine
Runs on-demand or daily. Produces recommendations.json

Filter pipeline (strict order — each step is a hard constraint):
  1. Ready / Off-plan
  2. Property Type (category)
  3. Bedrooms
  4. Budget
  5. Location
  6. Risk
  7. Goal-based sorting

If no results after all hard filters:
  → Progressive relaxation (budget → bedrooms → property type alternatives)
  → Each relaxation step is logged and reported to user
  → NEVER silently violate a hard constraint
"""
from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.utils import clamp, safe_float, safe_int, save_json, load_json, recommendation_from_score
from config.settings import (
    RECOMMENDATIONS_FILE,
    READY_PROPERTY_SCORES_FILE, OFFPLAN_SCORES_FILE,
    COMMUNITY_SCORES_FILE, DEVELOPER_SCORES_FILE, PROJECT_SCORES_FILE
)
from engines.investor_strategy_engine import build_investor_strategy
from engines.investor_fit_engine import calculate_investor_fit
from engines.report_rules_engine import build_report_contract, validate_report

BUDGET_RANGES = {
    "500k-1m": (500_000, 1_000_000),
    "1m-2m": (1_000_000, 2_000_000),
    "2m-5m": (2_000_000, 5_000_000),
    "5m+": (5_000_000, float("inf")),
}

BEDROOM_MAP = {
    "studio": ["Studio"],
    "1": ["1 B/R"],
    "2": ["2 B/R"],
    "3": ["3 B/R", "4 B/R", "5 B/R", "6 B/R"],
}


def normalize_bedtype(bed_type: str) -> str:
    """Normalize bed type strings to a common format for matching."""
    if not bed_type:
        return ""
    b = bed_type.lower().strip()
    if "studio" in b:
        return "studio"
    if b.startswith("1") or b == "1br":
        return "1br"
    if b.startswith("2") or b == "2br":
        return "2br"
    if b.startswith("3") or b == "3br":
        return "3br"
    if any(b.startswith(x) for x in ["4", "5", "6", "7"]) or "br+" in b:
        return "4br+"
    return b

PROPERTY_TYPE_MAP = {
    "apartment": ["Apartment", "Flat", "Studio", "Hotel Apartment"],
    "villa": ["Villa", "Mansions", "Mansion"],
    "townhouse": ["Townhouse"],
    "penthouse": ["Penthouse", "Duplex", "Triplex"],
}

# Fallback mapping when no exact matches found
PROPERTY_TYPE_FALLBACK = {
    "villa": ["Townhouse", "Penthouse", "Duplex"],
    "townhouse": ["Villa", "Apartment"],
    "penthouse": ["Apartment", "Duplex"],
    "apartment": ["Townhouse", "Penthouse"],
}


def parse_budget(budget: str) -> tuple[float, float]:
    if not budget:
        return 0, float("inf")
    if budget.startswith("custom:"):
        amount = safe_float(budget.split(":")[1])
        if amount > 0:
            tolerance = amount * 0.2
            return max(0, amount - tolerance), amount + tolerance
        return 0, float("inf")
    if budget.lower().strip() in BUDGET_RANGES:
        return BUDGET_RANGES[budget.lower().strip()]
    return 0, float("inf")


def filter_ready_properties(profile: dict, ready_props: list[dict]) -> list[dict]:
    """Hard filter pipeline — each filter is a strict constraint."""
    props = ready_props

    # Step 1: Property type (HARD)
    prop_type = profile.get("property_type")
    if prop_type and prop_type in PROPERTY_TYPE_MAP:
        categories = PROPERTY_TYPE_MAP[prop_type]
        props = [p for p in props if p.get("category", "") in categories]

    # Step 2: Bedrooms (HARD)
    bedrooms = profile.get("bedrooms")
    if bedrooms and bedrooms in BEDROOM_MAP:
        bed_types = BEDROOM_MAP[bedrooms]
        props = [p for p in props if p.get("bedType") in bed_types]

    # Step 3: Budget (HARD) — skip properties without valid price
    min_price, max_price = parse_budget(profile.get("budget", ""))
    if min_price > 0 or max_price < float("inf"):
        props = [p for p in props if p.get("askingPrice", 0) > 0 and min_price <= p.get("askingPrice", 0) <= max_price]

    # Step 4: Location
    location = profile.get("location")
    if location and location != "any":
        props = [p for p in props if location.lower() in p.get("area", "").lower() or location.lower() in p.get("project", "").lower()]

    # Step 5: Risk
    if profile.get("risk") == "low":
        props = [p for p in props if p.get("risk", {}).get("riskLevel") != "High"]

    return props


def filter_offplan_properties(profile: dict, offplan_props: list[dict]) -> list[dict]:
    props = offplan_props

    # Step 1: Property type (HARD) — new v2 fields
    prop_type = profile.get("property_type")
    if prop_type and prop_type in PROPERTY_TYPE_MAP:
        categories = PROPERTY_TYPE_MAP[prop_type]
        props = [p for p in props if p.get("category", "") in categories]

    # Step 2: Bedrooms (HARD) — normalize bed types for matching
    bedrooms = profile.get("bedrooms")
    if bedrooms and bedrooms in BEDROOM_MAP:
        target_norm = normalize_bedtype(bedrooms)
        if target_norm == "3br":
            target_set = {"3br", "4br+"}
        else:
            target_set = {target_norm}
        props = [p for p in props if normalize_bedtype(p.get("bedType", "")) in target_set]

    # Step 3: Budget (HARD) — new v2 uses askingPrice
    min_price, max_price = parse_budget(profile.get("budget", ""))
    if min_price > 0 or max_price < float("inf"):
        props = [p for p in props if p.get("askingPrice", 0) > 0 and
                 min_price <= p.get("askingPrice", 0) <= max_price]

    # Step 4: Location
    location = profile.get("location")
    if location and location != "any":
        props = [p for p in props if location.lower() in p.get("area", "").lower() or
                 location.lower() in p.get("project", "").lower()]

    # Step 5: Risk filter
    if profile.get("risk") == "low":
        props = [p for p in props if p.get("risk", {}).get("riskLevel") != "High"]
        # Also filter by developer score for conservative investors
        props = [p for p in props if p.get("developerData", {}).get("developerScore", 0) >= 70 or
                 p.get("developerScore", 0) >= 70]

    # Step 6: Exclude AVOID recommendations for low-risk investors
    if profile.get("risk") == "low":
        props = [p for p in props if p.get("recommendation", "") != "AVOID"]

    return props


def sort_by_goal(props: list[dict], goal: str, score_field: str) -> list[dict]:
    if goal == "rental_income":
        # For offplan v2: sort by post-handover ROI; for ready: sort by netROI
        return sorted(props, key=lambda p: -(
            safe_float(p.get("postHandoverROI", {}).get("netROI", 0)) or
            safe_float(p.get("roi", {}).get("netROI", 0))
        ))
    elif goal == "capital_growth":
        # For offplan v2: sort by future appreciation; for ready: sort by growth12m
        return sorted(props, key=lambda p: -(
            safe_float(p.get("futureAppreciation", {}).get("potentialGainPct", 0)) or
            safe_float(p.get("growth12m", 0))
        ))
    elif goal == "holiday_home":
        return sorted(props, key=lambda p: -(
            safe_float(p.get(score_field, 0)) +
            (safe_float(p.get("futureAppreciation", {}).get("potentialGainPct", 0)) or
             safe_float(p.get("growth12m", 0)))
        ))
    else:
        return sorted(props, key=lambda p: -safe_float(p.get(score_field, 0)))


def generate_recommendations(profile: dict) -> dict:
    ready_props = load_json(READY_PROPERTY_SCORES_FILE) if READY_PROPERTY_SCORES_FILE.exists() else []
    offplan_props = load_json(OFFPLAN_SCORES_FILE) if OFFPLAN_SCORES_FILE.exists() else []

    # Filter — respect user's ready/offplan preference
    ready_offplan = profile.get("ready_offplan", "ready")
    if ready_offplan in ("ready", "either", "", None):
        filtered_ready = filter_ready_properties(profile, ready_props)
    else:
        filtered_ready = []
    if ready_offplan in ("offplan", "either", "", None):
        filtered_offplan = filter_offplan_properties(profile, offplan_props)
    else:
        filtered_offplan = []

    # Progressive relaxation — each step logs what was relaxed
    relaxed = False
    relaxation_note = ""
    relaxation_steps = []

    if not filtered_ready and ready_props and ready_offplan in ("ready", "either", "", None):
        prop_type = profile.get("property_type", "")
        categories = PROPERTY_TYPE_MAP.get(prop_type, [])
        bed_types = BEDROOM_MAP.get(profile.get("bedrooms", ""), [])
        min_price, max_price = parse_budget(profile.get("budget", ""))

        # Step 1: Relax budget by 20% (keep type + bedrooms strict)
        if not filtered_ready and min_price > 0:
            wider_min = max(0, min_price * 0.9)
            wider_max = max_price * 1.3 if max_price < float("inf") else max_price
            filtered_ready = [p for p in ready_props
                            if (not categories or p.get("category", "") in categories)
                            and (not bed_types or p.get("bedType") in bed_types)
                            and p.get("askingPrice", 0) > 0
                            and wider_min <= p.get("askingPrice", 0) <= wider_max]
            if filtered_ready:
                relaxed = True
                relaxation_steps.append(f"Budget expanded to AED {wider_min:,.0f}–{wider_max:,.0f}")

        # Step 2: Relax bedrooms (keep type + budget strict)
        if not filtered_ready:
            filtered_ready = [p for p in ready_props
                            if (not categories or p.get("category", "") in categories)
                            and p.get("askingPrice", 0) > 0
                            and min_price <= p.get("askingPrice", 0) <= max_price]
            if filtered_ready:
                relaxed = True
                relaxation_steps.append(f"Bedroom filter relaxed (was: {profile.get('bedrooms', 'any')})")

        # Step 3: Relax both budget + bedrooms (keep type strict)
        if not filtered_ready and min_price > 0:
            wider_min = max(0, min_price * 0.8)
            wider_max = max_price * 1.8 if max_price < float("inf") else max_price
            filtered_ready = [p for p in ready_props
                            if (not categories or p.get("category", "") in categories)
                            and p.get("askingPrice", 0) > 0
                            and wider_min <= p.get("askingPrice", 0) <= wider_max]
            if filtered_ready:
                relaxed = True
                relaxation_steps.append(f"Budget + bedrooms relaxed to find {prop_type} matches")

        # Step 4: Fallback to alternative property types (keep budget + bedrooms strict)
        # Only relax type if user explicitly asked for a specific type
        if not filtered_ready:
            fallback_cats = PROPERTY_TYPE_FALLBACK.get(prop_type, [])
            if fallback_cats:
                filtered_ready = [p for p in ready_props
                                if p.get("category", "") in fallback_cats
                                and (not bed_types or p.get("bedType") in bed_types)
                                and p.get("askingPrice", 0) > 0
                                and min_price <= p.get("askingPrice", 0) <= max_price]
                if filtered_ready:
                    relaxed = True
                    relaxation_steps.append(f"No {prop_type}s found in budget. Showing similar: {', '.join(fallback_cats)}")
            # If still nothing, don't force it — return empty
            if not filtered_ready:
                relaxation_steps.append(f"No properties found matching your criteria. Try expanding budget or bedrooms.")

        # Step 5: DO NOT relax all filters — return empty with helpful message
        if not filtered_ready:
            relaxation_steps.append(f"No {prop_type or 'properties'} found matching your criteria. Try adjusting budget or bedrooms.")
            filtered_ready = []

        relaxation_note = ". ".join(relaxation_steps)

    # Off-plan relaxation (only if user asked for offplan and nothing was found)
    if not filtered_offplan and offplan_props and ready_offplan in ("offplan", "either", "", None):
        prop_type = profile.get("property_type", "")
        categories = PROPERTY_TYPE_MAP.get(prop_type, [])
        bed_types = BEDROOM_MAP.get(profile.get("bedrooms", ""))
        min_price, max_price = parse_budget(profile.get("budget", ""))

        # Step 1: Relax budget by 20%
        if not filtered_offplan and min_price > 0:
            wider_min = max(0, min_price * 0.9)
            wider_max = max_price * 1.3 if max_price < float("inf") else max_price
            filtered_offplan = [p for p in offplan_props
                            if (not categories or p.get("category", "") in categories)
                            and (not bed_types or p.get("bedType") in bed_types)
                            and p.get("askingPrice", 0) > 0
                            and wider_min <= p.get("askingPrice", 0) <= wider_max]
            if filtered_offplan:
                relaxed = True
                relaxation_steps.append(f"Off-plan budget expanded to AED {wider_min:,.0f}–{wider_max:,.0f}")

        # Step 2: Relax bedrooms
        if not filtered_offplan:
            filtered_offplan = [p for p in offplan_props
                            if (not categories or p.get("category", "") in categories)
                            and p.get("askingPrice", 0) > 0
                            and min_price <= p.get("askingPrice", 0) <= max_price]
            if filtered_offplan:
                relaxed = True
                relaxation_steps.append(f"Off-plan bedroom filter relaxed")

        # Step 3: Relax both budget + bedrooms
        if not filtered_offplan and min_price > 0:
            wider_min = max(0, min_price * 0.8)
            wider_max = max_price * 1.8 if max_price < float("inf") else max_price
            filtered_offplan = [p for p in offplan_props
                            if (not categories or p.get("category", "") in categories)
                            and p.get("askingPrice", 0) > 0
                            and wider_min <= p.get("askingPrice", 0) <= wider_max]
            if filtered_offplan:
                relaxed = True
                relaxation_steps.append(f"Off-plan budget + bedrooms relaxed")

        # Step 4: Fallback to alternative property types
        if not filtered_offplan:
            fallback_cats = PROPERTY_TYPE_FALLBACK.get(prop_type, [])
            if fallback_cats:
                filtered_offplan = [p for p in offplan_props
                                if p.get("category", "") in fallback_cats
                                and (not bed_types or p.get("bedType") in bed_types)
                                and p.get("askingPrice", 0) > 0
                                and min_price <= p.get("askingPrice", 0) <= max_price]
                if filtered_offplan:
                    relaxed = True
                    relaxation_steps.append(f"No off-plan {prop_type}s found. Showing similar: {', '.join(fallback_cats)}")

        if not filtered_offplan:
            relaxation_steps.append(f"No off-plan {prop_type or 'properties'} found. Try adjusting budget or bedrooms.")

        relaxation_note = ". ".join(relaxation_steps) if relaxation_steps else relaxation_note

    # Sort by goal
    goal = profile.get("goal", "balanced")
    filtered_ready = sort_by_goal(filtered_ready, goal, "readyScore")
    filtered_offplan = sort_by_goal(filtered_offplan, goal, "offplanScore")

    # ─── Investor Strategy Engine ───
    strategy = build_investor_strategy(profile)

    # ─── Investor Fit Engine ───
    # Calculate fit score for each property
    for p in filtered_ready:
        fit = calculate_investor_fit(p, strategy, "ready")
        p["investorFit"] = fit
    for p in filtered_offplan:
        fit = calculate_investor_fit(p, strategy, "offplan")
        p["investorFit"] = fit

    # Re-sort by blended score: investment_score * 0.6 + fit_score * 0.4
    filtered_ready.sort(key=lambda p: -(safe_float(p.get("readyScore", 0)) * 0.6 + safe_float(p.get("investorFit", {}).get("fitScore", 0)) * 0.4))
    filtered_offplan.sort(key=lambda p: -(safe_float(p.get("offplanScore", 0)) * 0.6 + safe_float(p.get("investorFit", {}).get("fitScore", 0)) * 0.4))

    # Top 10 combined
    top_ready = filtered_ready[:7]
    top_offplan = filtered_offplan[:3]

    # Combined ranking
    combined = []
    for p in top_ready:
        combined.append({**p, "propertyType": "ready"})
    for p in top_offplan:
        combined.append({**p, "propertyType": "offplan"})

    # Sort combined by blended score: investment_score * 0.6 + investor_fit * 0.4
    def get_score(p):
        if "readyScore" in p:
            return p["readyScore"]
        if "offplanScore" in p:
            return p["offplanScore"]
        return 0

    def get_blended_score(p):
        inv_score = safe_float(p.get("readyScore", 0)) if p.get("propertyType") == "ready" else safe_float(p.get("offplanScore", 0))
        fit_score = safe_float(p.get("investorFit", {}).get("fitScore", 0))
        return -(inv_score * 0.6 + fit_score * 0.4)
    combined.sort(key=get_blended_score)

    # Build recommendation confidence for top property
    goal = profile.get("goal", "balanced")
    rec_confidence = {}
    if combined:
        top = combined[0]
        top_conf = top.get("confidenceScore", 50)
        # Apply goal-aware recommendation
        from engines.utils import recommendation_from_score
        top_score = get_score(top)
        top_fit = top.get("investorFit", {})
        top_fit_score = top_fit.get("fitScore", 0)
        top["recommendation"] = recommendation_from_score(top_score, top_conf, goal)
        # Issue 3: Fit score gates recommendation — low fit = downgrade
        if top_fit_score < 40:
            if top["recommendation"] in ("STRONG BUY", "BUY", "BUY IF NEGOTIATED"):
                top["recommendation"] = "REVIEW"
        elif top_fit_score < 55:
            if top["recommendation"] == "STRONG BUY":
                top["recommendation"] = "BUY"
            elif top["recommendation"] == "BUY":
                top["recommendation"] = "BUY IF NEGOTIATED"
        rec_confidence = {
            "score": top_score,
            "investorFitScore": top_fit_score,
            "investorFitLabel": top_fit.get("fitLabel", ""),
            "confidence": top_conf,
            "goal": goal,
            "matchReasons": _build_match_reasons(top, profile),
            "fitMatchReasons": top_fit.get("matchReasons", []),
            "fitMismatchReasons": top_fit.get("mismatchReasons", []),
            "strategySummary": strategy.get("strategy_summary", ""),
            "exitStrategy": strategy.get("exit_strategy", ""),
        }
        if top_conf < 40:
            rec_confidence["warning"] = "Insufficient data — recommendation based on limited evidence"
        if top_conf < 25:
            rec_confidence["warning"] = "INSUFFICIENT DATA — evidence too weak for investment recommendation"
    # Build report contract for top recommendation (Rule Book)
    report_contract = None
    report_validation = None
    if combined:
        top_prop = combined[0]
        report_contract = build_report_contract(top_prop, profile, strategy)
        report_validation = validate_report(top_prop, report_contract)


    return {
        "profile": profile,
        "investorStrategy": strategy,
        "totalReadyMatches": len(filtered_ready),
        "totalOffplanMatches": len(filtered_offplan),
        "recommendations": combined[:10],
        "topReady": top_ready,
        "topOffplan": top_offplan,
        "relaxed": relaxed,
        "relaxationNote": relaxation_note,
        "relaxationSteps": relaxation_steps if relaxed else [],
        "recommendationConfidence": rec_confidence,
        "noResults": len(combined) == 0,
        "reportContract": report_contract if combined else None,
        "reportValidation": report_validation if combined else None,
        "noResultsReason": relaxation_steps[-1] if relaxation_steps and not combined else None,
        "generatedAt": datetime.now().isoformat(),
    }


def _build_match_reasons(prop: dict, profile: dict) -> list[str]:
    """Build human-readable match reasons for recommendation confidence.
    Fit reasons = budget, timeline, goal, financing — NOT price discount.
    """
    reasons = []

    # Budget match
    min_p, max_p = parse_budget(profile.get("budget", ""))
    price = safe_float(prop.get("askingPrice", 0))
    if min_p <= price <= max_p:
        reasons.append(f"Property price AED {price:,.0f} - within your budget")
    elif price > 0:
        reasons.append(f"Property price AED {price:,.0f} — outside original budget")

    # Property type match
    prop_type = profile.get("property_type", "")
    categories = PROPERTY_TYPE_MAP.get(prop_type, [])
    if categories and prop.get("category", "") in categories:
        reasons.append(f"Property type matches: {prop.get('category', '?')}")

    # Goal match (FIT)
    goal = (profile.get("goal", "balanced") or "balanced").lower()
    goal_labels = {
        "rental_income": "Rental Income",
        "capital_growth": "Capital Growth",
        "flip_handover": "Flip Before Handover",
        "end_user": "End User",
        "holiday_home": "Holiday Home",
        "balanced": "Balanced",
    }
    reasons.append(f"Goal: {goal_labels.get(goal, goal or 'N/A')}")

    # Timeline match (FIT)
    timeline = profile.get("timeline", "3-5y")
    timeline_labels = {"1-2y": "1-2 years", "3-5y": "3-5 years", "5y+": "5+ years", "undecided": "Flexible"}
    reasons.append(f"Timeline: {timeline_labels.get(timeline, timeline or 'N/A')}")

    # Financing match (FIT)
    financing = profile.get("financing", "cash")
    reasons.append(f"Financing: {(financing or 'N/A').capitalize()}")

    # Bedroom match
    bed_types = BEDROOM_MAP.get(profile.get("bedrooms", ""), [])
    if bed_types and prop.get("bedType") in bed_types:
        reasons.append(f"Bedrooms match: {prop.get('bedType', '?')}")

    # Data quality
    sales_count = prop.get("dataQuality", {}).get("salesCount", 0)
    rent_count = prop.get("dataQuality", {}).get("rentCount", 0)
    if sales_count > 0:
        reasons.append(f"{sales_count} sales analysed")
    if rent_count > 0:
        reasons.append(f"{rent_count} rentals analysed")

    # Confidence
    conf = prop.get("confidenceScore", 0)
    if conf >= 70:
        reasons.append("High data confidence")
    elif conf >= 50:
        reasons.append("Moderate data confidence")
    else:
        reasons.append("Low data confidence — verify estimates")

    return reasons


def run():
    print("[Recommendation Engine] Starting...")
    # Generate default recommendations (no profile filter)
    profile = {}
    recs = generate_recommendations(profile)
    save_json(RECOMMENDATIONS_FILE, recs)
    print(f"[Recommendation Engine] Generated {len(recs['recommendations'])} recommendations")
    return recs


if __name__ == "__main__":
    run()
