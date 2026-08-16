"""
APIL Investor Fit Engine
Scores how well a property matches the investor's strategy.

This is SEPARATE from the investment score:
  - Investment Score: "Is this a good property?" (property quality)
  - Investor Fit Score: "Is this property right for THIS investor?" (strategy match)

Architecture:
  Property Score (78) → Investor Fit Score (95%) → Recommendation (BUY)

A property can have a high investment score but low investor fit
(e.g., great growth property but investor wants rental income).
"""
from __future__ import annotations

from engines.utils import safe_float, safe_int


def calculate_investor_fit(property_data: dict, strategy: dict, property_type: str = "ready") -> dict:
    """
    Calculate how well a property matches the investor's strategy.

    Args:
        property_data: Scored property dict (ready or offplan)
        strategy: Output from build_investor_strategy()
        property_type: "ready" or "offplan"

    Returns:
        {
            "fitScore": int (0-100),
            "fitLabel": str,
            "matchReasons": list[str],
            "mismatchReasons": list[str],
            "dimensionScores": dict,  # per-dimension fit
        }
    """
    if property_data is None:
        property_data = {}
    if strategy is None:
        strategy = {}
    thresholds = strategy.get("thresholds", {}) or {}
    goal = strategy.get("goal", "balanced")
    risk = strategy.get("risk_level", "medium")
    exit_pref = strategy.get("exit_strategy", "sell_handover")

    match_reasons = []
    mismatch_reasons = []
    dimension_scores = {}

    # ─── Developer Fit ───
    if property_type == "offplan":
        dd = property_data.get("developerData") or {}
        dev_score = safe_int(dd.get("developerScore", 0))
    else:
        dev_score = safe_int(property_data.get("developerScore", 0))
    min_dev = thresholds.get("min_developer_score", 50)
    if dev_score >= min_dev:
        dev_fit = min(100, int(100 - (min_dev - dev_score) * 0.5)) if dev_score >= min_dev else int(dev_score / min_dev * 100)
        dev_fit = min(100, max(0, dev_fit))
        dimension_scores["developer"] = dev_fit
        if dev_score >= 75:
            match_reasons.append(f"Strong developer track record ({dev_score}/100)")
    else:
        dev_fit = int(dev_score / max(min_dev, 1) * 100)
        dimension_scores["developer"] = dev_fit
        if risk == "low":
            mismatch_reasons.append(f"Developer score {dev_score}/100 below your conservative minimum ({min_dev})")
        else:
            mismatch_reasons.append(f"Developer score {dev_score}/100 — below recommended ({min_dev})")

    # ─── Pricing Fit ───
    # Convention in fit engine: price_diff_pct > 0 = above market (premium), < 0 = below market (discount)
    if property_type == "offplan":
        price_opp = property_data.get("priceOpportunity") or {}
        price_diff_pct = safe_float(price_opp.get("priceDifferencePct", 0))
    else:
        mv = property_data.get("marketValuation") or {}
        # Real data: discountPct negative = below market (discount), positive = above market (premium)
        # This matches our engine convention already — positive = above market
        price_diff_pct = safe_float(mv.get("discountPct", 0))

    max_premium = thresholds.get("max_premium_pct", 15)
    if price_diff_pct <= 0:
        price_fit = 100
        # Price discount is quality, not fit — do not add to match reasons
    elif price_diff_pct <= max_premium:
        price_fit = int(100 - (price_diff_pct / max_premium) * 30)
        match_reasons.append(f"Price {price_diff_pct:.1f}% above market — within your threshold")
    else:
        price_fit = max(0, int(50 - (price_diff_pct - max_premium) * 3))
        mismatch_reasons.append(f"Price {price_diff_pct:.1f}% above market — exceeds your {max_premium}% threshold")
    dimension_scores["pricing"] = price_fit

    # ─── Growth Fit ───
    if property_type == "offplan":
        fa = property_data.get("futureAppreciation") or {}
        growth_score = safe_int(fa.get("futureAppreciationScore", 0))
        potential_gain = safe_float(fa.get("potentialGainPct", 0))
    else:
        growth_score = safe_int(property_data.get("growthScore", 0))
        potential_gain = safe_float(property_data.get("growth12m", 0))

    min_growth = thresholds.get("min_area_growth", 5)
    if potential_gain >= min_growth:
        growth_fit = min(100, int(60 + (potential_gain / max(min_growth, 1)) * 40))
        if potential_gain >= 15:
            match_reasons.append(f"Strong growth potential ({potential_gain:.1f}%)")
        dimension_scores["growth"] = growth_fit
    else:
        growth_fit = int(potential_gain / max(min_growth, 1) * 60)
        dimension_scores["growth"] = growth_fit
        if goal in ("capital_growth", "flip_handover"):
            gap = min_growth - potential_gain
            mismatch_reasons.append(f"Growth {potential_gain:.1f}% — {gap:.1f}% below your {min_growth}% target")

    # ─── ROI Fit (goal-dependent) ───
    min_roi = thresholds.get("min_net_roi", 0)
    if property_type == "offplan":
        phr = property_data.get("postHandoverROI") or {}
        net_roi = safe_float(phr.get("netROI", 0))
    else:
        roi_data = property_data.get("roi") or {}
        net_roi = safe_float(roi_data.get("netROI", 0))

    if min_roi > 0:
        if net_roi >= min_roi:
            roi_fit = min(100, int(60 + (net_roi / min_roi) * 40))
            match_reasons.append(f"Net ROI {net_roi:.1f}% meets your {min_roi}% target")
        else:
            roi_fit = int(net_roi / max(min_roi, 1) * 60)
            mismatch_reasons.append(f"Net ROI {net_roi:.1f}% below your {min_roi}% target")
    else:
        # ROI not a priority for this goal
        roi_fit = 70 if net_roi > 0 else 50
    dimension_scores["roi"] = roi_fit

    # ─── Supply Risk Fit ───
    if property_type == "offplan":
        sb = property_data.get("scoreBreakdown") or {}
        supply_score = safe_int(sb.get("supplyRisk", 50))
    else:
        risk_data = property_data.get("risk") or {}
        risk_components = risk_data.get("components") or {}
        supply_score = 100 - safe_int(risk_components.get("futureSupplyRisk", 50))

    min_supply = thresholds.get("min_supply_score", 50)
    if supply_score >= min_supply:
        supply_fit = min(100, int(70 + (supply_score - min_supply) * 0.5))
        dimension_scores["supply"] = supply_fit
    else:
        supply_fit = int(supply_score / max(min_supply, 1) * 70)
        dimension_scores["supply"] = supply_fit
        if goal in ("capital_growth", "rental_income"):
            mismatch_reasons.append(f"Area supply risk score {supply_score}/100 — above your threshold")

    # ─── Liquidity Fit ───
    if property_type == "offplan":
        liq_data = property_data.get("liquidity") or {}
        liq_score = safe_int(liq_data.get("liquidityScore", 0))
    else:
        liq_data = property_data.get("liquidity") or {}
        liq_score = safe_int(liq_data.get("liquidityScore", 0))

    # Liquidity importance varies by goal + holding period
    if goal == "flip_handover" or strategy.get("holding_period") == "1-2y":
        liq_weight = 1.5  # Critical for short-term
    elif goal in ("rental_income", "end_user"):
        liq_weight = 0.7  # Less important
    else:
        liq_weight = 1.0

    if liq_score >= 70:
        liq_fit = min(100, liq_score)
        if liq_score >= 80 and liq_weight > 1.0:
            match_reasons.append(f"High liquidity ({liq_score}/100) — suits your short-term strategy")
    elif liq_score >= 50:
        liq_fit = liq_score
    else:
        liq_fit = max(0, liq_score)
        if liq_weight > 1.0:
            mismatch_reasons.append(f"Low liquidity ({liq_score}/100) — concern for your exit strategy")
    dimension_scores["liquidity"] = liq_fit

    # ─── Payment Plan Fit (off-plan only) ───
    if property_type == "offplan":
        pp_data = property_data.get("paymentPlanAnalysis") or {}
        pp_score = safe_int(pp_data.get("paymentPlanScore", 0))
        if goal == "flip_handover":
            # Low down payment is critical for flipping
            down_pct = safe_float(pp_data.get("downPaymentPct", 100))
            if down_pct <= 20:
                pp_fit = min(100, pp_score + 10)
                match_reasons.append(f"Low down payment ({down_pct}%) — ideal for flip strategy")
            elif down_pct >= 50:
                pp_fit = max(20, pp_score - 30)
                mismatch_reasons.append(f"High down payment ({down_pct}%) — reduces flip leverage")
            else:
                pp_fit = pp_score
        else:
            pp_fit = pp_score
        dimension_scores["payment_plan"] = pp_fit

    # ─── Exit Strategy Fit ───
    exit_strats = property_data.get("exitStrategies") or {}
    recommended_exit = exit_strats.get("recommendedStrategy", "")
    if recommended_exit and exit_pref:
        if recommended_exit == exit_pref:
            exit_fit = 100
            match_reasons.append(f"Recommended exit ({recommended_exit}) matches your strategy")
        else:
            exit_fit = 60
            # Not a hard mismatch, just not optimal
    else:
        exit_fit = 70  # Neutral if no exit data
    dimension_scores["exit_strategy"] = exit_fit

    # ─── Calculate Overall Fit Score ───
    # Weight dimensions by goal-specific importance
    goal_dim_weights = _get_dimension_weights(goal, property_type)

    total_weight = 0
    weighted_sum = 0
    for dim, score in dimension_scores.items():
        w = goal_dim_weights.get(dim, 1.0)
        weighted_sum += score * w
        total_weight += w

    fit_score = int(weighted_sum / max(total_weight, 1)) if total_weight > 0 else 50
    fit_score = max(0, min(100, fit_score))

    # ─── Critical Dimension Penalty ───
    # If a critical dimension is very low, the overall fit should suffer
    # even if other dimensions are high. A property with a terrible developer
    # and 25% premium should never be a "Good Match" regardless of growth.
    critical_penalties = 0
    critical_dims = {
        "developer": (40, 20),   # (threshold, penalty per dim below threshold)
        "pricing": (25, 20),     # Pricing is critical — bad price = bad investment
    }
    if goal == "flip_handover":
        critical_dims["payment_plan"] = (30, 15)
    if goal == "rental_income":
        critical_dims["roi"] = (30, 15)

    for dim, (threshold, penalty) in critical_dims.items():
        dim_score = dimension_scores.get(dim, 100)
        if dim_score < threshold:
            critical_penalties += penalty

    if critical_penalties > 0:
        fit_score = max(0, fit_score - critical_penalties)

    # Determine label
    if fit_score >= 85:
        fit_label = "Excellent Match"
    elif fit_score >= 70:
        fit_label = "Good Match"
    elif fit_score >= 50:
        fit_label = "Partial Match"
    elif fit_score >= 30:
        fit_label = "Weak Match"
    else:
        fit_label = "Poor Match"

    # Issue 17: If fit is weak, swap match/mismatch priority
    is_good_fit = fit_score >= 50
    primary_reasons = match_reasons[:5] if is_good_fit else mismatch_reasons[:5]
    secondary_reasons = mismatch_reasons[:5] if is_good_fit else match_reasons[:5]

    return {
        "fitScore": fit_score,
        "fitLabel": fit_label,
        "matchReasons": primary_reasons,
        "mismatchReasons": secondary_reasons,
        "isGoodFit": is_good_fit,
        "dimensionScores": dimension_scores,
    }


def _get_dimension_weights(goal: str, property_type: str) -> dict:
    """Get dimension importance weights for fit calculation."""
    if property_type == "offplan":
        base = {
            "developer": 1.5,
            "pricing": 1.2,
            "growth": 1.0,
            "roi": 0.8,
            "supply": 1.0,
            "liquidity": 0.8,
            "payment_plan": 1.0,
            "exit_strategy": 1.0,
        }
    else:
        base = {
            "developer": 1.0,
            "pricing": 1.2,
            "growth": 1.0,
            "roi": 1.0,
            "supply": 0.8,
            "liquidity": 1.0,
            "exit_strategy": 0.5,
        }

    # Adjust by goal
    if goal == "rental_income":
        base["roi"] = 2.0
        base["growth"] = 0.5
        base["liquidity"] = 1.2
    elif goal == "capital_growth":
        base["growth"] = 2.0
        base["roi"] = 0.5
        base["developer"] = 1.8
    elif goal == "flip_handover":
        base["payment_plan"] = 2.0
        base["liquidity"] = 1.8
        base["roi"] = 0.0
        base["growth"] = 1.3
    elif goal == "holiday_home":
        base["roi"] = 1.3
        base["growth"] = 1.0
        base["developer"] = 1.3

    return base
