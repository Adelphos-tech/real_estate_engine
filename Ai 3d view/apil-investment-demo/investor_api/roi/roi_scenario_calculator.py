"""
investor_api/roi/roi_scenario_calculator.py

V1.3 — ROI scenario calculation engine.
Covers: holding period, exit value, selling costs, net sale proceeds,
ROI input readiness.

All math happens here (backend only). Frontend never calculates.

NOT calculated in this phase:
  - Full Property ROI
  - Capital return
  - Total return
  - Annualized return
  - IRR
  - Cumulative net rental income

Exit value:
  - USER_EXIT_PRICE: user enters exit_sale_price_aed directly
  - USER_APPRECIATION_RATE: backend derives exit price from appreciation
  - Never uses DLD benchmark, APIL Advantage, or market context as exit price

Appreciation formula:
  exit_sale_price_aed = purchase_price_aed * (1 + rate/100) ^ holding_period_years

Selling costs:
  - COMPLETE requires: broker + NOC + other (each resolved)
  - net_sale_proceeds = exit_price - complete_selling_costs
  - Negative net sale proceeds allowed (not clamped)

ROI input readiness:
  - READY_FOR_FULL_ROI_CALCULATION requires:
    COMPLETE_ACQUISITION_COSTS + NET_RENTAL + holding_period + exit_value + COMPLETE_SELLING_COSTS
  - Offplan → NOT_EVALUATED_OFFPLAN
  - Does NOT calculate Full ROI even when READY
"""
from typing import Dict, Any, Optional
from .roi_scenario_models import build_empty_scenario_context, SellingCostLevel, RoiInputReadiness
from .acquisition_cost_provider import METHODOLOGY_VERSION, VALUATION_DATE


def calculate_roi_scenario(
    purchase_price_aed: Optional[float] = None,
    unit_status: Optional[str] = None,
    holding_period_months: Optional[float] = None,
    exit_value_mode: Optional[str] = None,
    exit_sale_price_aed: Optional[float] = None,
    annual_appreciation_rate_pct: Optional[float] = None,
    selling_broker_mode: Optional[str] = None,
    selling_broker_percent: Optional[float] = None,
    selling_broker_aed: Optional[float] = None,
    noc_mode: Optional[str] = None,
    noc_fee_aed: Optional[float] = None,
    other_selling_mode: Optional[str] = None,
    other_selling_costs_aed: Optional[float] = None,
    # External context for readiness check
    acquisition_calculation_level: Optional[str] = None,
    net_rental_calculation_level: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate ROI scenario context.

    Returns the roi_scenario_context dict.
    Does NOT calculate Full Property ROI.
    """
    ctx = build_empty_scenario_context()

    # ── Offplan check ──
    if unit_status and "offplan" in unit_status.lower():
        ctx["roi_input_readiness"] = "NOT_EVALUATED_OFFPLAN"
        ctx["missing_roi_inputs"] = []
        ctx["disclosure"] = (
            "Offplan properties are not evaluated for Full Property ROI in V1. "
            "A separate offplan cash-flow model is required."
        )
        return ctx

    missing = []

    # ── Holding Period ──
    if holding_period_months is not None and holding_period_months > 0:
        months = float(holding_period_months)
        years = round(months / 12.0, 6)
        ctx["holding_period"] = {
            "status": "AVAILABLE",
            "months": months,
            "years": years,
            "source": "USER_INPUT",
            "input_mode": "USER_INPUT_MONTHS",
        }
    else:
        missing.append("holding_period")

    # ── Exit Value ──
    exit_price = None
    exit_ctx = {
        "status": "MISSING",
        "mode": None,
        "exit_sale_price_aed": None,
        "annual_appreciation_rate_pct": None,
        "source": "MISSING",
        "rate_source": None,
        "exit_price_source": None,
        "calculation_basis": None,
        "input_mode": None,
    }

    if exit_value_mode == "USER_EXIT_PRICE" and exit_sale_price_aed is not None:
        exit_price = float(exit_sale_price_aed)
        exit_ctx.update({
            "status": "AVAILABLE",
            "mode": "USER_EXIT_PRICE",
            "exit_sale_price_aed": exit_price,
            "source": "USER_INPUT",
            "exit_price_source": "USER_INPUT",
            "calculation_basis": "User-entered exit sale price. Not a market forecast.",
            "input_mode": "USER_EXIT_PRICE",
        })
    elif exit_value_mode == "USER_APPRECIATION_RATE" and annual_appreciation_rate_pct is not None:
        rate = float(annual_appreciation_rate_pct)
        # Need holding period and purchase price to derive
        if holding_period_months and holding_period_months > 0 and purchase_price_aed and purchase_price_aed > 0:
            years = float(holding_period_months) / 12.0
            exit_price = round(float(purchase_price_aed) * ((1 + rate / 100.0) ** years), 2)
            exit_ctx.update({
                "status": "AVAILABLE",
                "mode": "USER_APPRECIATION_RATE",
                "exit_sale_price_aed": exit_price,
                "annual_appreciation_rate_pct": rate,
                "source": "DERIVED",
                "rate_source": "USER_INPUT",
                "exit_price_source": "DERIVED",
                "calculation_basis": (
                    f"purchase_price * (1 + {rate}%) ^ {round(years, 2)} years. "
                    "Based on user appreciation assumption. Not a market forecast."
                ),
                "input_mode": "USER_APPRECIATION_RATE",
            })
        else:
            # Have rate but missing holding period or price — still incomplete
            exit_ctx.update({
                "mode": "USER_APPRECIATION_RATE",
                "annual_appreciation_rate_pct": rate,
                "rate_source": "USER_INPUT",
                "calculation_basis": "Appreciation rate provided but cannot derive exit price without holding period and purchase price.",
            })
            missing.append("exit_value")
    else:
        missing.append("exit_value")

    ctx["exit_value"] = exit_ctx

    # ── Selling Costs ──
    selling_missing = []
    selling_level = "NO_SELLING_COSTS"

    # Broker
    broker_ctx = {
        "name": "Selling Broker Commission",
        "source": "MISSING",
        "status": "MISSING",
        "calculation_basis": "",
        "included_in_total": False,
        "input_mode": None,
    }
    if selling_broker_mode == "SELLING_BROKER_PERCENT" and selling_broker_percent is not None:
        if exit_price is not None:
            broker_amount = round(exit_price * float(selling_broker_percent) / 100.0, 2)
        else:
            broker_amount = None  # Can't calculate without exit price
        broker_ctx.update({
            "amount_aed": broker_amount,
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": f"exit_sale_price * {selling_broker_percent}% (user-entered percent)",
            "included_in_total": True,
            "input_mode": "SELLING_BROKER_PERCENT",
        })
    elif selling_broker_mode == "SELLING_BROKER_FIXED_AED" and selling_broker_aed is not None:
        broker_ctx.update({
            "amount_aed": float(selling_broker_aed),
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": "User-entered fixed amount",
            "included_in_total": True,
            "input_mode": "SELLING_BROKER_FIXED_AED",
        })
    elif selling_broker_mode == "NO_SELLING_BROKER_COST":
        broker_ctx.update({
            "amount_aed": 0.0,
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": "User explicitly selected NO_SELLING_BROKER_COST. Zero is explicit.",
            "included_in_total": True,
            "input_mode": "NO_SELLING_BROKER_COST",
        })
    else:
        broker_ctx.update({
            "amount_aed": None,
            "calculation_basis": "No statutory rate — USER_INPUT or NO_SELLING_BROKER_COST required. Never defaulted.",
        })
        selling_missing.append("selling_broker")

    # NOC
    noc_ctx = {
        "name": "Developer / NOC Fee",
        "source": "MISSING",
        "status": "MISSING",
        "calculation_basis": "",
        "included_in_total": False,
        "input_mode": None,
    }
    if noc_mode == "NOC_FIXED_AED" and noc_fee_aed is not None:
        noc_ctx.update({
            "amount_aed": float(noc_fee_aed),
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": "User-entered — varies by developer",
            "included_in_total": True,
            "input_mode": "NOC_FIXED_AED",
        })
    elif noc_mode == "NO_NOC_FEE":
        noc_ctx.update({
            "amount_aed": 0.0,
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": "User explicitly selected NO_NOC_FEE. Zero is explicit.",
            "included_in_total": True,
            "input_mode": "NO_NOC_FEE",
        })
    else:
        noc_ctx.update({
            "amount_aed": None,
            "calculation_basis": "Varies by developer — NOC_FIXED_AED or NO_NOC_FEE required.",
        })
        selling_missing.append("noc")

    # Other selling costs
    other_ctx = {
        "name": "Other Selling Costs",
        "source": "MISSING",
        "status": "MISSING",
        "calculation_basis": "",
        "included_in_total": False,
        "input_mode": None,
    }
    if other_selling_mode == "OTHER_SELLING_COSTS_AED" and other_selling_costs_aed is not None:
        other_ctx.update({
            "amount_aed": float(other_selling_costs_aed),
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": "User-entered other selling costs",
            "included_in_total": True,
            "input_mode": "OTHER_SELLING_COSTS_AED",
        })
    elif other_selling_mode == "NO_OTHER_SELLING_COSTS":
        other_ctx.update({
            "amount_aed": 0.0,
            "source": "USER_INPUT",
            "status": "USER_INPUT",
            "calculation_basis": "User explicitly selected NO_OTHER_SELLING_COSTS. Zero is explicit.",
            "included_in_total": True,
            "input_mode": "NO_OTHER_SELLING_COSTS",
        })
    else:
        other_ctx.update({
            "amount_aed": None,
            "calculation_basis": "OTHER_SELLING_COSTS_AED or NO_OTHER_SELLING_COSTS required.",
        })
        selling_missing.append("other_selling")

    # Selling cost level
    if len(selling_missing) == 0:
        selling_level = "COMPLETE_SELLING_COSTS"
    elif len(selling_missing) < 3:
        selling_level = "PARTIAL_SELLING_COSTS"
    else:
        selling_level = "NO_SELLING_COSTS"

    # Calculate selling costs total
    complete_selling = None
    if selling_level == "COMPLETE_SELLING_COSTS":
        total = 0.0
        for c in [broker_ctx, noc_ctx, other_ctx]:
            if c["included_in_total"] and c["amount_aed"] is not None:
                total += c["amount_aed"]
        complete_selling = round(total, 2)

    ctx["selling_costs"] = {
        "calculation_level": selling_level,
        "broker": broker_ctx,
        "noc": noc_ctx,
        "other": other_ctx,
        "complete_selling_costs_aed": complete_selling,
    }

    # ── Net Sale Proceeds ──
    if exit_price is not None and complete_selling is not None:
        ctx["net_sale_proceeds_aed"] = round(exit_price - complete_selling, 2)
    # Negative is allowed — no clamping

    # ── ROI Input Readiness ──
    if "holding_period" in missing or "exit_value" in missing or selling_level != "COMPLETE_SELLING_COSTS":
        ctx["roi_input_readiness"] = "INCOMPLETE"
    else:
        # Check external contexts
        acq_complete = acquisition_calculation_level == "COMPLETE_ACQUISITION_COSTS"
        net_rental = net_rental_calculation_level == "NET_RENTAL"
        if acq_complete and net_rental:
            ctx["roi_input_readiness"] = "READY_FOR_FULL_ROI_CALCULATION"
        else:
            ctx["roi_input_readiness"] = "INCOMPLETE"

    # Build missing list
    full_missing = list(missing) + list(selling_missing)
    if acquisition_calculation_level is not None and acquisition_calculation_level != "COMPLETE_ACQUISITION_COSTS":
        full_missing.append("complete_acquisition_costs")
    if net_rental_calculation_level is not None and net_rental_calculation_level != "NET_RENTAL":
        full_missing.append("net_rental_income")
    ctx["missing_roi_inputs"] = full_missing

    ctx["methodology_version"] = METHODOLOGY_VERSION
    ctx["valuation_date"] = VALUATION_DATE

    return ctx
