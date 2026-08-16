"""
APIL Rules Engine — Hard Business Rules

Sits between the Investment Engine and the LLM Advisor.
Enforces non-negotiable business rules before the LLM ever sees the data.

Rules:
  1. comparable_sales < 5  → confidence = LOW, price_score = UNKNOWN
  2. median_price == 0     → price_score = UNKNOWN
  3. rental_contracts == 0 → roi_score = UNKNOWN
  4. asking_price < 50% or > 200% of market median → flag as outlier
  5. critical metrics missing → recommendation cannot be BUY/STRONG BUY
  6. confidence < 40 → recommendation = INSUFFICIENT_DATA
  7. price/sqft outside 200-10,000 → reject listing entirely
"""
from __future__ import annotations

from typing import Any


def apply_rules(scored_property: dict) -> dict:
    """
    Apply hard business rules to a scored property.
    Returns the property with:
      - rule_flags: list of triggered rules
      - recommendation: possibly overridden
      - confidence: possibly reduced
      - *_score: possibly set to None (UNKNOWN)
    """
    flags: list[str] = []
    p = dict(scored_property)  # shallow copy

    is_offplan = "offplanScore" in p
    confidence = p.get("confidenceScore", 50)
    recommendation = p.get("recommendation", "HOLD")

    # ── Rule 7: Price/sqft validation (reject entirely) ──
    price = p.get("askingPrice", 0)
    size = p.get("sizeSqft") or p.get("areaSqft", 0)
    if price > 0 and size > 0:
        price_sqft = price / size
        if price_sqft < 200 or price_sqft > 10000:
            flags.append("RULE_7_REJECT_PRICE_SQFT")
            p["_rejected"] = True
            p["ruleFlags"] = flags
            return p

    # ── Rule 4: Price outlier vs market median ──
    if is_offplan:
        fair_value = p.get("fairValue", {}).get("fairValue", 0)
        if fair_value > 0 and price > 0:
            ratio = price / fair_value
            if ratio < 0.50 or ratio > 2.00:
                flags.append("RULE_4_PRICE_OUTLIER")
                confidence = min(confidence, 30)
    else:
        comp_price = p.get("comparablePrice")
        if comp_price and comp_price > 0 and price > 0:
            ratio = price / comp_price
            if ratio < 0.50 or ratio > 2.00:
                flags.append("RULE_4_PRICE_OUTLIER")
                confidence = min(confidence, 30)

    # ── Rule 1: Insufficient comparable sales ──
    sales_count = p.get("dataQuality", {}).get("salesCount", 0) if not is_offplan else 0
    if sales_count < 5:
        flags.append("RULE_1_INSUFFICIENT_SALES")
        confidence = min(confidence, 50)
        if not is_offplan:
            p["priceScore"] = None  # UNKNOWN

    # ── Rule 2: No comparable price ──
    if not is_offplan:
        comp = p.get("comparablePrice")
        if comp is None or comp == 0:
            flags.append("RULE_2_NO_COMPARABLE_PRICE")
            p["priceScore"] = None
            p["comparablePrice"] = None
            p["priceDifference"] = None
            confidence = min(confidence, 50)

    # ── Rule 3: No rental data ──
    has_rent = p.get("dataQuality", {}).get("hasRentData", False) if not is_offplan else p.get("postHandoverROI", {}).get("hasRentData", False)
    rent_count = p.get("dataQuality", {}).get("rentCount", 0) if not is_offplan else 0
    if not has_rent or rent_count < 5:
        flags.append("RULE_3_NO_RENT_DATA")
        if not is_offplan:
            p["roiScore"] = None  # UNKNOWN
            roi = p.get("roi", {})
            roi["grossROI"] = None
            roi["netROI"] = None
            roi["annualRent"] = None
            p["roi"] = roi
        else:
            roi = p.get("postHandoverROI", {})
            roi["netROI"] = None
            roi["grossROI"] = None
            roi["estimatedRent"] = None
            p["postHandoverROI"] = roi
        confidence = min(confidence, 50)

    # ── Rule 5: Critical metrics missing → cannot be BUY ──
    critical_missing = any(f in flags for f in [
        "RULE_1_INSUFFICIENT_SALES",
        "RULE_2_NO_COMPARABLE_PRICE",
        "RULE_3_NO_RENT_DATA",
    ])
    if critical_missing and recommendation in ("STRONG BUY", "BUY"):
        recommendation = "HOLD"
        flags.append("RULE_5_DOWNGRADED_TO_HOLD")

    # ── Rule 6: Confidence < 40 → INSUFFICIENT_DATA ──
    if confidence < 40:
        recommendation = "INSUFFICIENT_DATA"
        flags.append("RULE_6_INSUFFICIENT_DATA")

    p["confidenceScore"] = confidence
    p["recommendation"] = recommendation
    p["ruleFlags"] = flags
    return p


def batch_apply_rules(properties: list[dict]) -> list[dict]:
    """Apply rules to a list of scored properties. Rejected ones are filtered out."""
    results = []
    for p in properties:
        ruled = apply_rules(p)
        if not ruled.get("_rejected"):
            results.append(ruled)
        else:
            print(f"  [Rules] Rejected property {p.get('id', '?')}: {ruled['ruleFlags']}")
    return results
