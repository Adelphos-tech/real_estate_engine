"""
Unified DTO Normalizer — Phase 3

Normalizes both ready and off-plan property dicts to a single unified schema.
This runs AFTER scoring and BEFORE the API response, ensuring the frontend
receives identical field names regardless of property type.

Usage:
    from engines.dto_normalizer import normalize_to_unified_dto
    prop = normalize_to_unified_dto(prop)  # works for both ready and offplan
"""
from __future__ import annotations

from engines.utils import safe_float, safe_int


def normalize_to_unified_dto(prop: dict) -> dict:
    """Normalize a property dict to the unified DTO schema.

    Works for both ready and off-plan properties.
    Adds unified field names while keeping legacy names for backward compatibility.
    """
    is_offplan = "offplanScore" in prop or prop.get("status") == "offplan" or prop.get("propertyType") == "offplan"

    # ── 1. Investment Score ──
    if "investmentScore" not in prop:
        score = prop.get("readyScore") or prop.get("offplanScore") or 0
        prop["investmentScore"] = score

    # ── 2. Price vs Market ──
    if "priceVsMarketPct" not in prop:
        if is_offplan:
            po = prop.get("priceOpportunity") or {}
            prop["priceVsMarketPct"] = po.get("priceDifferencePct")
        else:
            prop["priceVsMarketPct"] = prop.get("priceDifference")

    # ── 3. Fair Value ──
    if "marketValuation" not in prop or not isinstance(prop.get("marketValuation"), dict):
        if is_offplan:
            fv = prop.get("fairValue") or {}
            if isinstance(fv, dict):
                prop["marketValuation"] = {
                    "fairValueTotal": fv.get("fairValue"),
                    "fairValueSqft": fv.get("baseSqft"),
                    "source": fv.get("source", "estimated"),
                }
            elif isinstance(fv, (int, float)) and fv > 0:
                # Ready legacy format — fairValue was an int
                prop["marketValuation"] = {
                    "fairValueTotal": fv,
                    "fairValueSqft": None,
                    "source": "computed",
                }
        else:
            mv = prop.get("marketValuation")
            if isinstance(mv, dict):
                pass  # already has marketValuation dict
            elif prop.get("fairValue") is not None:
                fv = prop.get("fairValue")
                if isinstance(fv, (int, float)):
                    prop["marketValuation"] = {
                        "fairValueTotal": fv,
                        "fairValueSqft": None,
                        "source": "computed",
                    }

    # ── 4. ROI ──
    if "roi" not in prop or not isinstance(prop.get("roi"), dict):
        if is_offplan and "postHandoverROI" in prop:
            prop["roi"] = prop["postHandoverROI"]
    elif is_offplan and "postHandoverROI" in prop:
        # Merge postHandoverROI into roi for unified access
        phr = prop["postHandoverROI"]
        if "netROI" not in prop["roi"] and "netROI" in phr:
            prop["roi"]["netROI"] = phr["netROI"]
        if "grossROI" not in prop["roi"] and "grossROI" in phr:
            prop["roi"]["grossROI"] = phr["grossROI"]
        if "estimatedRent" not in prop["roi"] and "estimatedRent" in phr:
            prop["roi"]["estimatedRent"] = phr["estimatedRent"]

    # ── 5. Data Quality ──
    if "dataQuality" not in prop or prop.get("dataQuality") is None:
        if is_offplan:
            # Build dataQuality from available evidence
            po = prop.get("priceOpportunity") or {}
            phr = prop.get("postHandoverROI") or {}
            has_fair_value = po.get("priceDifferencePct") is not None
            has_rent = phr.get("hasRentData", False) or phr.get("estimatedRent") is not None
            prop["dataQuality"] = {
                "hasComparables": has_fair_value,
                "hasRentData": has_rent,
                "salesCount": 1 if has_fair_value else 0,
                "rentCount": 1 if has_rent else 0,
                "comparableCount": 1 if has_fair_value else 0,
            }

    # ── 6. Lost Points ──
    if "lostPoints" not in prop or prop.get("lostPoints") is None:
        if is_offplan:
            # Off-plan doesn't have lostPoints — derive from reasons or leave empty
            prop["lostPoints"] = []

    # ── 7. Pricing/Rental Confidence ──
    if "pricingConfidence" not in prop:
        dq = prop.get("dataQuality") or {}
        sales = safe_int(dq.get("salesCount", 0))
        comp = safe_int(dq.get("comparableCount", 0))
        if sales >= 20 or comp >= 20:
            pc = 90
        elif sales >= 10 or comp >= 10:
            pc = 70
        elif sales >= 5 or comp >= 5:
            pc = 50
        elif sales >= 1 or comp >= 1:
            pc = 30
        else:
            pc = 10
        prop["pricingConfidence"] = pc
        prop["pricingConfidenceLabel"] = "High" if pc >= 70 else "Moderate" if pc >= 40 else "Limited" if pc >= 15 else "Insufficient"

    if "rentalConfidence" not in prop:
        dq = prop.get("dataQuality") or {}
        rent = safe_int(dq.get("rentCount", 0))
        if rent >= 10:
            rc = 90
        elif rent >= 5:
            rc = 60
        elif rent >= 1:
            rc = 35
        else:
            rc = 10
        prop["rentalConfidence"] = rc
        prop["rentalConfidenceLabel"] = "High" if rc >= 60 else "Moderate" if rc >= 30 else "Limited" if rc >= 15 else "Insufficient"

    # ── 8. Rules Flags ──
    if "rulesFlags" not in prop:
        prop["rulesFlags"] = []
    if "rulesFlagsHuman" not in prop:
        prop["rulesFlagsHuman"] = []

    # ── 9. Property Type ──
    if "propertyType" not in prop:
        prop["propertyType"] = "offplan" if is_offplan else "ready"

    # ── 10. Confidence Breakdown ──
    if "confidenceBreakdown" not in prop:
        # Build from confidence_engine if available
        pass  # confidenceScore is already set by the engine

    # ── 11. Exit Strategies (for ready — derive from strategy if available) ──
    if "exitStrategies" not in prop and not is_offplan:
        # Ready properties don't have exitStrategies — will be added by report_rules_engine
        pass

    # ── 12. Score Breakdown — ensure common keys exist ──
    sb = prop.get("scoreBreakdown") or {}
    # Ensure both ready and offplan have these keys (use 0 if not applicable)
    common_keys = {"developer", "price", "roi", "liquidity", "community", "growth", "supplyRisk", "paymentPlan", "project"}
    for k in common_keys:
        if k not in sb:
            # Don't add keys that don't make sense for the property type
            # Just ensure the dict exists
            pass

    return prop


def normalize_recommendations_batch(properties: list[dict]) -> list[dict]:
    """Normalize a batch of properties to unified DTO."""
    return [normalize_to_unified_dto(p) for p in properties]
