"""
investor_api/roi/acquisition_cost_calculator.py

V1.2 — Acquisition cost calculation engine with user-input completion layer.

All math happens here (backend only). Frontend never calculates.

Acquisition cost levels:
  PURCHASE_PRICE_ONLY          — no purchase price
  OFFICIAL_ACQUISITION_COSTS   — purchase price + official statutory fees only
  PARTIAL_ACQUISITION_COSTS    — some user inputs provided, but not all required
  COMPLETE_ACQUISITION_COSTS   — all required components resolved

Required for COMPLETE:
  - purchase price (MASTER)
  - confirmed buyer DLD cost (USE_STATUTORY_DEFAULT / CUSTOM_PERCENT / CUSTOM_AED)
  - trustee fee (USER_INPUT)
  - broker purchase cost (BROKER_PERCENT / BROKER_FIXED_AED / NO_BROKER_COST)
  - developer/admin (USER_INPUT_AED / NO_DEVELOPER_ADMIN_FEE)
  - title deed fee (OFFICIAL_VERIFIED — automatic)
  - knowledge fee (OFFICIAL_VERIFIED — automatic)
  - innovation fee (OFFICIAL_VERIFIED — automatic)

Only COMPLETE produces total_cash_invested_aed.

DLD buyer share:
  - USE_STATUTORY_DEFAULT → 2% (OFFICIAL_DLD_RERA, user-confirmed)
  - CUSTOM_PERCENT → user-entered % (USER_INPUT)
  - CUSTOM_AED → user-entered AED (USER_INPUT)
  - Never silently charges 4% to buyer
  - Never charges seller share to buyer
"""
from typing import Dict, Any, Optional
from .acquisition_cost_models import (
    build_empty_acquisition_context,
    OFFICIAL_DLD_TOTAL_RATE_PCT,
    OFFICIAL_DLD_BUYER_STATUTORY_DEFAULT_PCT,
)
from .acquisition_cost_provider import (
    OFFICIAL_FEE_RULES,
    METHODOLOGY_VERSION,
    VALUATION_DATE,
)


def calculate_acquisition_costs(
    purchase_price_aed: Optional[float],
    dld_input_mode: Optional[str] = None,
    dld_custom_percent: Optional[float] = None,
    dld_custom_aed: Optional[float] = None,
    trustee_fee_aed: Optional[float] = None,
    broker_purchase_mode: Optional[str] = None,
    broker_purchase_percent: Optional[float] = None,
    broker_purchase_aed: Optional[float] = None,
    developer_admin_mode: Optional[str] = None,
    developer_admin_fee_aed: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calculate acquisition costs for a property.

    Returns the acquisition_cost_context dict.
    """
    ctx = build_empty_acquisition_context()

    # ── Purchase price ──
    if purchase_price_aed is not None and purchase_price_aed > 0:
        ctx["purchase_price"] = {
            "name": "Property Purchase Price",
            "amount_aed": float(purchase_price_aed),
            "source": "MASTER",
            "status": "OFFICIAL_VERIFIED",
            "calculation_basis": "MASTER current_price_aed",
            "included_in_total": True,
            "evidence_date": VALUATION_DATE,
            "input_mode": None,
        }
    else:
        ctx["purchase_price"] = {
            "name": "Property Purchase Price",
            "amount_aed": None,
            "source": "MASTER",
            "status": "MISSING",
            "calculation_basis": "MASTER current_price_aed — not available",
            "included_in_total": False,
            "evidence_date": None,
            "input_mode": None,
        }
        ctx["calculation_level"] = "PURCHASE_PRICE_ONLY"
        ctx["missing_components"] = ["purchase_price"]
        return ctx

    price = float(purchase_price_aed)
    missing = []

    # ── DLD Transfer Fee ──
    dld_rules = OFFICIAL_FEE_RULES["dld_transfer"]
    dld_ctx = {
        "name": "DLD Transfer Fee",
        "source": "MISSING",
        "status": "MISSING",
        "calculation_basis": "",
        "included_in_total": False,
        "evidence_date": dld_rules["source_date"],
        "input_mode": None,
        "official_total_rate_pct": OFFICIAL_DLD_TOTAL_RATE_PCT,
        "statutory_buyer_default_pct": OFFICIAL_DLD_BUYER_STATUTORY_DEFAULT_PCT,
        "actual_buyer_rate_pct": None,
        "buyer_share_status": "MISSING",
        "payer_allocation": "CONTRACT_DEPENDENT",
        "confirmed": False,
    }

    if dld_input_mode == "USE_STATUTORY_DEFAULT":
        buyer_pct = OFFICIAL_DLD_BUYER_STATUTORY_DEFAULT_PCT
        dld_amount = round(price * buyer_pct / 100.0, 2)
        dld_ctx.update({
            "amount_aed": dld_amount,
            "source": "OFFICIAL_DLD_RERA",
            "status": "OFFICIAL_VERIFIED",
            "calculation_basis": f"purchase_price * {buyer_pct}% (statutory default, user-confirmed). Total rate 4%, shared equally per ECR 30/2013 Art 3(1).",
            "included_in_total": True,
            "input_mode": "USE_STATUTORY_DEFAULT",
            "actual_buyer_rate_pct": buyer_pct,
            "buyer_share_status": "USER_CONFIRMED_DEFAULT",
            "confirmed": True,
        })
    elif dld_input_mode == "CUSTOM_PERCENT":
        buyer_pct = float(dld_custom_percent)
        dld_amount = round(price * buyer_pct / 100.0, 2)
        dld_ctx.update({
            "amount_aed": dld_amount,
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": f"purchase_price * {buyer_pct}% (user-entered custom buyer share). Total statutory rate 4%.",
            "included_in_total": True,
            "input_mode": "CUSTOM_PERCENT",
            "actual_buyer_rate_pct": buyer_pct,
            "buyer_share_status": "USER_OVERRIDE",
            "confirmed": True,
        })
    elif dld_input_mode == "CUSTOM_AED":
        dld_amount = float(dld_custom_aed)
        implied_pct = round(dld_amount / price * 100, 4) if price > 0 else None
        dld_ctx.update({
            "amount_aed": dld_amount,
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": f"User-entered fixed AED amount. Implied rate: {implied_pct}% of purchase price.",
            "included_in_total": True,
            "input_mode": "CUSTOM_AED",
            "actual_buyer_rate_pct": implied_pct,
            "buyer_share_status": "USER_OVERRIDE",
            "confirmed": True,
        })
    else:
        # DLD not confirmed — MISSING
        dld_ctx.update({
            "amount_aed": None,
            "calculation_basis": "4% total statutory rate. Buyer share requires user confirmation (USE_STATUTORY_DEFAULT, CUSTOM_PERCENT, or CUSTOM_AED).",
        })
        missing.append("dld_transfer")

    ctx["dld_transfer"] = dld_ctx

    # ── Title Deed Fee (OFFICIAL_VERIFIED — automatic) ──
    td_rules = OFFICIAL_FEE_RULES["title_deed"]
    ctx["title_deed_fee"] = {
        "name": "Title Deed Issuance Fee",
        "amount_aed": td_rules["fixed_amount_aed"],
        "source": "OFFICIAL_DLD_RERA",
        "status": "OFFICIAL_VERIFIED",
        "calculation_basis": f"Fixed AED {td_rules['fixed_amount_aed']:.0f} — ECR 30/2013 Schedule Item 22. Does NOT include knowledge/innovation.",
        "included_in_total": True,
        "evidence_date": td_rules["source_date"],
        "input_mode": None,
    }

    # ── Knowledge Fee (OFFICIAL_VERIFIED — automatic) ──
    kf_rules = OFFICIAL_FEE_RULES["knowledge_fee"]
    ctx["knowledge_fee"] = {
        "name": "Knowledge Dirham Fee",
        "amount_aed": kf_rules["fixed_amount_aed"],
        "source": "OFFICIAL_DLD_RERA",
        "status": "OFFICIAL_VERIFIED",
        "calculation_basis": f"Fixed AED {kf_rules['fixed_amount_aed']:.0f} — Law No. 1 of 2018. Separate from title deed.",
        "included_in_total": True,
        "evidence_date": kf_rules["source_date"],
        "input_mode": None,
    }

    # ── Innovation Fee (OFFICIAL_VERIFIED — automatic) ──
    if_rules = OFFICIAL_FEE_RULES["innovation_fee"]
    ctx["innovation_fee"] = {
        "name": "Innovation Dirham Fee",
        "amount_aed": if_rules["fixed_amount_aed"],
        "source": "OFFICIAL_DLD_RERA",
        "status": "OFFICIAL_VERIFIED",
        "calculation_basis": f"Fixed AED {if_rules['fixed_amount_aed']:.0f} — Law No. 2 of 2018. Separate from title deed.",
        "included_in_total": True,
        "evidence_date": if_rules["source_date"],
        "input_mode": None,
    }

    # ── Trustee Office Fee (USER_INPUT only) ──
    if trustee_fee_aed is not None:
        ctx["trustee_office_fee"] = {
            "name": "Trustee Office Fee",
            "amount_aed": float(trustee_fee_aed),
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": "User-entered — trustee offices are private entities, fees not fixed by statute.",
            "included_in_total": True,
            "evidence_date": VALUATION_DATE,
            "input_mode": "USER_INPUT_AED",
        }
    else:
        ctx["trustee_office_fee"] = {
            "name": "Trustee Office Fee",
            "amount_aed": None,
            "source": "MISSING",
            "status": "MISSING",
            "calculation_basis": "Not in DLD statute — USER_INPUT required. Never defaulted.",
            "included_in_total": False,
            "evidence_date": None,
            "input_mode": None,
        }
        missing.append("trustee_office_fee")

    # ── Broker Purchase Commission ──
    broker_ctx = {
        "name": "Broker Purchase Commission",
        "source": "MISSING",
        "status": "MISSING",
        "calculation_basis": "",
        "included_in_total": False,
        "evidence_date": None,
        "input_mode": None,
    }

    if broker_purchase_mode == "BROKER_PERCENT" and broker_purchase_percent is not None:
        broker_amount = round(price * float(broker_purchase_percent) / 100.0, 2)
        broker_ctx.update({
            "amount_aed": broker_amount,
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": f"purchase_price * {broker_purchase_percent}% (user-entered percent)",
            "included_in_total": True,
            "evidence_date": VALUATION_DATE,
            "input_mode": "BROKER_PERCENT",
        })
    elif broker_purchase_mode == "BROKER_FIXED_AED" and broker_purchase_aed is not None:
        broker_ctx.update({
            "amount_aed": float(broker_purchase_aed),
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": "User-entered fixed amount",
            "included_in_total": True,
            "evidence_date": VALUATION_DATE,
            "input_mode": "BROKER_FIXED_AED",
        })
    elif broker_purchase_mode == "NO_BROKER_COST":
        broker_ctx.update({
            "amount_aed": 0.0,
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": "User explicitly selected NO_BROKER_COST. Zero is explicit, not assumed.",
            "included_in_total": True,
            "evidence_date": VALUATION_DATE,
            "input_mode": "NO_BROKER_COST",
        })
    else:
        broker_ctx.update({
            "amount_aed": None,
            "calculation_basis": "No statutory rate — USER_INPUT (BROKER_PERCENT, BROKER_FIXED_AED, or NO_BROKER_COST) required. Never defaulted.",
        })
        missing.append("broker_purchase")

    ctx["broker_purchase"] = broker_ctx

    # ── Developer / Admin Fee ──
    dev_ctx = {
        "name": "Developer / Admin Fee",
        "source": "MISSING",
        "status": "MISSING",
        "calculation_basis": "",
        "included_in_total": False,
        "evidence_date": None,
        "input_mode": None,
    }

    if developer_admin_mode == "USER_INPUT_AED" and developer_admin_fee_aed is not None:
        dev_ctx.update({
            "amount_aed": float(developer_admin_fee_aed),
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": "User-entered — varies by developer",
            "included_in_total": True,
            "evidence_date": VALUATION_DATE,
            "input_mode": "USER_INPUT_AED",
        })
    elif developer_admin_mode == "NO_DEVELOPER_ADMIN_FEE":
        dev_ctx.update({
            "amount_aed": 0.0,
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": "User explicitly selected NO_DEVELOPER_ADMIN_FEE. Zero is explicit, not assumed.",
            "included_in_total": True,
            "evidence_date": VALUATION_DATE,
            "input_mode": "NO_DEVELOPER_ADMIN_FEE",
        })
    else:
        dev_ctx.update({
            "amount_aed": None,
            "calculation_basis": "Varies by developer — USER_INPUT_AED or NO_DEVELOPER_ADMIN_FEE required.",
        })
        missing.append("developer_admin")

    ctx["developer_admin"] = dev_ctx

    # ── Mortgage Registration Fee (NOT_APPLICABLE) ──
    ctx["mortgage_registration_fee"] = {
        "name": "Mortgage Registration Fee",
        "amount_aed": 0,
        "source": "NOT_APPLICABLE",
        "status": "NOT_APPLICABLE",
        "calculation_basis": "NOT_APPLICABLE in unlevered V1",
        "included_in_total": False,
        "evidence_date": None,
        "input_mode": None,
    }

    # ── Calculate subtotals ──
    # Official acquisition fees = DLD (if confirmed) + title deed + knowledge + innovation
    official_fees = 0.0
    if ctx["dld_transfer"]["included_in_total"]:
        official_fees += ctx["dld_transfer"]["amount_aed"]
    official_fees += ctx["title_deed_fee"]["amount_aed"]
    official_fees += ctx["knowledge_fee"]["amount_aed"]
    official_fees += ctx["innovation_fee"]["amount_aed"]
    ctx["official_acquisition_fees_aed"] = round(official_fees, 2)

    # Known acquisition costs = official + available user-entered costs
    known_costs = official_fees
    if ctx["trustee_office_fee"]["included_in_total"]:
        known_costs += ctx["trustee_office_fee"]["amount_aed"]
    if ctx["broker_purchase"]["included_in_total"]:
        known_costs += ctx["broker_purchase"]["amount_aed"]
    if ctx["developer_admin"]["included_in_total"]:
        known_costs += ctx["developer_admin"]["amount_aed"]
    ctx["known_acquisition_costs_aed"] = round(known_costs, 2)

    # ── Determine calculation level ──
    # REQUIRED for COMPLETE:
    #   dld_transfer (confirmed), trustee_fee, broker_purchase, developer_admin
    if len(missing) == 0:
        ctx["calculation_level"] = "COMPLETE_ACQUISITION_COSTS"
        ctx["complete_acquisition_costs_aed"] = round(known_costs, 2)
        ctx["total_cash_invested_aed"] = round(price + known_costs, 2)
    elif ctx["dld_transfer"]["included_in_total"]:
        # DLD confirmed but other inputs missing
        ctx["calculation_level"] = "PARTIAL_ACQUISITION_COSTS"
        ctx["complete_acquisition_costs_aed"] = None
        ctx["total_cash_invested_aed"] = None
    else:
        # DLD not even confirmed — only official fixed fees
        ctx["calculation_level"] = "OFFICIAL_ACQUISITION_COSTS"
        ctx["complete_acquisition_costs_aed"] = None
        ctx["total_cash_invested_aed"] = None

    ctx["missing_components"] = missing
    ctx["methodology_version"] = METHODOLOGY_VERSION
    ctx["valuation_date"] = VALUATION_DATE

    return ctx
