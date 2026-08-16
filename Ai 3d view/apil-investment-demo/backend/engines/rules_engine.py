"""
APIL Stage 6 — Hard Rules Engine
Overrides impossible recommendations. These rules are NON-NEGOTIABLE.

Rules:
  1. Comparable sales < 5 → Never BUY, max REVIEW
  2. Price >20% above market → Max CAUTION
  3. No rental evidence + rental investor → Never BUY
  4. Unknown developer + off-plan → Max REVIEW
  5. Confidence < 40% → Max REVIEW
  6. Confidence < 25% → INSUFFICIENT_DATA
  7. Impossible price → Reject entirely
  8. Low developer score (<40) + off-plan → Max REVIEW
"""
from __future__ import annotations
from engines.utils import safe_float, safe_int


def apply_rules(prop: dict, goal: str = "balanced") -> dict:
    """Apply hard business rules to a scored property."""
    flags = []
    recommendation = prop.get("recommendation", "REVIEW")
    confidence = safe_float(prop.get("confidenceScore", 0))

    # Extract data quality metrics
    dq = prop.get("dataQuality", {}) or {}
    sales_count = safe_int(dq.get("salesCount", 0))
    rent_count = safe_int(dq.get("rentCount", 0))
    has_rent = dq.get("hasRentData", False)
    has_comparables = dq.get("hasComparables", False)

    # ── Rule 1: Comparable sales < 5 → Never BUY ──
    if sales_count < 5:
        flags.append("RULE_1_INSUFFICIENT_SALES")
        if recommendation in ("STRONG BUY", "BUY"):
            recommendation = "REVIEW"
            flags.append("RULE_1_DOWNGRADED_TO_REVIEW")

    # ── Rule 2: Price >20% above market → Max CAUTION ──
    # Check all possible price difference sources
    price_diff = None
    pd_val = prop.get("priceDifference")
    if pd_val is not None and safe_float(pd_val) != 0:
        price_diff = pd_val
    if price_diff is None:
        price_opp = prop.get("priceOpportunity") or {}
        po_val = price_opp.get("priceDifferencePct")
        if po_val is not None and safe_float(po_val) != 0:
            price_diff = po_val
    if price_diff is None:
        mv = prop.get("marketValuation") or {}
        mv_val = mv.get("discountPct")
        if mv_val is not None:
            price_diff = mv_val
    if price_diff is not None and safe_float(price_diff) > 20:
        flags.append("RULE_2_HIGH_PREMIUM")
        if recommendation in ("STRONG BUY", "BUY", "HOLD"):
            recommendation = "CAUTION"
            flags.append("RULE_2_DOWNGRADED_TO_CAUTION")

    # ── Rule 3: No rental evidence + rental investor → Never BUY ──
    if not has_rent and goal == "rental_income":
        flags.append("RULE_3_NO_RENT_FOR_RENTAL_INVESTOR")
        if recommendation in ("STRONG BUY", "BUY"):
            recommendation = "REVIEW"
            flags.append("RULE_3_DOWNGRADED_TO_REVIEW")

    # ── Rule 4: Unknown developer + off-plan → Max REVIEW ──
    dev_data = prop.get("developerData") or {}
    dev_name = dev_data.get("name", "")
    dev_score = safe_int(dev_data.get("developerScore", 0))
    is_offplan = prop.get("propertyType") == "offplan" or "offplan" in str(prop.get("offplanScore", ""))
    if (not dev_name or dev_name == "Independent / Other") and is_offplan:
        flags.append("RULE_4_UNKNOWN_DEV_OFFPLAN")
        if recommendation in ("STRONG BUY", "BUY", "HOLD"):
            recommendation = "REVIEW"
            flags.append("RULE_4_DOWNGRADED_TO_REVIEW")

    # ── Rule 8: Low developer score (<40) → Max REVIEW ──
    if dev_score > 0 and dev_score < 40:
        flags.append("RULE_8_LOW_DEVELOPER_SCORE")
        if recommendation in ("STRONG BUY", "BUY"):
            recommendation = "REVIEW"
            flags.append("RULE_8_DOWNGRADED_TO_REVIEW")

    # ── Rule 5: Confidence < 40% → Max REVIEW ──
    if confidence < 40 and confidence >= 25:
        flags.append("RULE_5_LOW_CONFIDENCE")
        if recommendation not in ("INSUFFICIENT_DATA",):
            recommendation = "REVIEW"
            flags.append("RULE_5_DOWNGRADED_TO_REVIEW")

    # ── Rule 6: Confidence < 25% → INSUFFICIENT_DATA ──
    if confidence < 25:
        flags.append("RULE_6_INSUFFICIENT_DATA")
        recommendation = "INSUFFICIENT_DATA"

    # ── Rule 7: Impossible price → reject (should never reach here) ──
    asking = safe_float(prop.get("askingPrice", 0))
    area = safe_float(prop.get("areaSqft", 0))
    if asking > 0 and area > 0:
        psqft = asking / area
        if psqft < 200 or psqft > 10000:
            flags.append("RULE_7_IMPOSSIBLE_PRICE")
            recommendation = "INSUFFICIENT_DATA"

    prop["recommendation"] = recommendation
    # Issue 3: Translate internal rule IDs to human-readable text
    RULE_FLAG_LABELS = {
        "RULE_1_LOW_SALES": "Limited comparable sales — pricing confidence reduced",
        "RULE_1_INSUFFICIENT_SALES": "Limited comparable sales — pricing confidence reduced",
        "RULE_1_DOWNGRADED_TO_REVIEW": "Insufficient data — recommendation downgraded to Review",
        "RULE_2_NO_MEDIAN": "No median price data — fair value estimate is uncertain",
        "RULE_3_NO_RENT_DATA": "No rental contracts found — ROI estimate is unavailable",
        "RULE_4_UNKNOWN_DEV_OFFPLAN": "Developer history is limited — delivery risk is higher than average",
        "RULE_4_UNKNOWN_DEV": "Developer history is limited — delivery risk is higher than average",
        "RULE_5_MISSING_METRICS": "Some critical metrics are missing — recommendation confidence reduced",
        "RULE_6_INSUFFICIENT_DATA": "Insufficient data — recommendation based on limited evidence",
        "RULE_7_PRICE_OUTLIER": "Asking price is significantly different from market — verify listing",
        "RULE_7_PRICE_PER_SQFT_OUTLIER": "Price per sqft is outside normal range — verify listing",
    }
    prop["rulesFlags"] = flags
    prop["rulesFlagsHuman"] = [RULE_FLAG_LABELS.get(f, f) for f in flags]
    return prop


def batch_apply_rules(properties: list[dict], goal: str = "balanced") -> list[dict]:
    """Apply rules to a list of properties."""
    return [apply_rules(p, goal) for p in properties]
