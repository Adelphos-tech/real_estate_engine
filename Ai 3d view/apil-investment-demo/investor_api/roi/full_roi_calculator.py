"""
investor_api/roi/full_roi_calculator.py

Full Property ROI V1 shadow calculator engine.
All math happens here (backend only).

Formula:
  cumulative_net_rental_income_aed =
      net_rental_income_aed * holding_period_months / 12

  capital_return_aed =
      net_sale_proceeds_aed - total_cash_invested_aed

  total_return_aed =
      cumulative_net_rental_income_aed + capital_return_aed

  full_property_roi_pct =
      total_return_aed / total_cash_invested_aed * 100

Rules:
  - Only calculates when ALL inputs are READY
  - No rental growth (CONSTANT_ANNUAL_NET_RENTAL)
  - No leverage (UNLEVERED)
  - No IRR
  - Negative results allowed (not clamped)
  - ROI >100% allowed (not clamped)
  - Uses unrounded source values for calculation, rounds only for display
  - Offplan → NOT_EVALUATED_OFFPLAN
"""
from typing import Dict, Any, Optional
from .full_roi_models import (
    build_empty_full_roi_context,
    build_offplan_full_roi_context,
    METHODOLOGY_VERSION,
    ROI_TYPE,
    RENTAL_ASSUMPTION,
    INCLUDED_COMPONENTS,
    EXCLUDED_COMPONENTS,
)
from .full_roi_validation import check_full_roi_readiness


def calculate_full_roi(
    unit_status: Optional[str] = None,
    # Acquisition (V1.2)
    purchase_price_aed: Optional[float] = None,
    complete_acquisition_costs_aed: Optional[float] = None,
    total_cash_invested_aed: Optional[float] = None,
    acquisition_calculation_level: Optional[str] = None,
    # Net rental (frozen demo layer)
    net_rental_income_aed: Optional[float] = None,
    net_rental_calculation_level: Optional[str] = None,
    # Scenario (V1.3)
    holding_period_months: Optional[float] = None,
    holding_period_years: Optional[float] = None,
    exit_sale_price_aed: Optional[float] = None,
    exit_value_mode: Optional[str] = None,
    annual_appreciation_rate_pct: Optional[float] = None,
    complete_selling_costs_aed: Optional[float] = None,
    net_sale_proceeds_aed: Optional[float] = None,
    selling_calculation_level: Optional[str] = None,
    # Overall readiness from V1.3
    roi_input_readiness: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate Full Property ROI.

    Returns the full_roi_context dict.
    All ROI outputs are null if inputs are incomplete.
    """
    # ── Offplan check ──
    if unit_status and "offplan" in unit_status.lower():
        return build_offplan_full_roi_context()

    # ── Readiness gate ──
    is_ready, missing, details = check_full_roi_readiness(
        unit_status=unit_status,
        acquisition_calculation_level=acquisition_calculation_level,
        total_cash_invested_aed=total_cash_invested_aed,
        net_rental_calculation_level=net_rental_calculation_level,
        net_rental_income_aed=net_rental_income_aed,
        holding_period_months=holding_period_months,
        exit_sale_price_aed=exit_sale_price_aed,
        selling_calculation_level=selling_calculation_level,
        net_sale_proceeds_aed=net_sale_proceeds_aed,
        roi_input_readiness=roi_input_readiness,
    )

    if not is_ready:
        ctx = build_empty_full_roi_context()
        ctx["calculation_status"] = "INCOMPLETE"
        ctx["missing_inputs"] = missing
        # Echo available inputs for provenance
        ctx["purchase_price_aed"] = purchase_price_aed
        ctx["complete_acquisition_costs_aed"] = complete_acquisition_costs_aed
        ctx["total_cash_invested_aed"] = total_cash_invested_aed
        ctx["annual_net_rental_income_aed"] = net_rental_income_aed
        ctx["holding_period_months"] = holding_period_months
        ctx["holding_period_years"] = holding_period_years
        ctx["exit_sale_price_aed"] = exit_sale_price_aed
        ctx["complete_selling_costs_aed"] = complete_selling_costs_aed
        ctx["net_sale_proceeds_aed"] = net_sale_proceeds_aed
        return ctx

    # ── All inputs ready — calculate ──
    # Use unrounded source values for calculation
    price = float(purchase_price_aed)
    acq_costs = float(complete_acquisition_costs_aed)
    tci = float(total_cash_invested_aed)
    annual_net_rental = float(net_rental_income_aed)
    months = float(holding_period_months)
    # Use provided years if available, otherwise derive (do NOT round to whole years)
    if holding_period_years is not None:
        years = float(holding_period_years)
    else:
        years = months / 12.0
    exit_price = float(exit_sale_price_aed)
    selling_costs = float(complete_selling_costs_aed)
    nsp = float(net_sale_proceeds_aed)

    # ── Cumulative Net Rental Income (CONSTANT_ANNUAL) ──
    # No rounding of holding period to whole years
    cumulative_rental = annual_net_rental * months / 12.0

    # ── Capital Return ──
    capital_return = nsp - tci

    # ── Total Return ──
    total_return = cumulative_rental + capital_return

    # ── Full Property ROI % ──
    if tci > 0:
        roi_pct = (total_return / tci) * 100.0
    else:
        roi_pct = None

    # ── Build context ──
    ctx = build_empty_full_roi_context()
    ctx["calculation_status"] = "CALCULATED"
    ctx["methodology_version"] = METHODOLOGY_VERSION
    ctx["roi_type"] = ROI_TYPE
    ctx["rental_assumption"] = RENTAL_ASSUMPTION

    # Echo canonical inputs
    ctx["purchase_price_aed"] = round(price, 2)
    ctx["complete_acquisition_costs_aed"] = round(acq_costs, 2)
    ctx["total_cash_invested_aed"] = round(tci, 2)
    ctx["annual_net_rental_income_aed"] = round(annual_net_rental, 2)
    ctx["holding_period_months"] = months
    ctx["holding_period_years"] = round(years, 6)
    ctx["exit_sale_price_aed"] = round(exit_price, 2)
    ctx["complete_selling_costs_aed"] = round(selling_costs, 2)
    ctx["net_sale_proceeds_aed"] = round(nsp, 2)

    # Calculated outputs (rounded for display)
    ctx["cumulative_net_rental_income_aed"] = round(cumulative_rental, 2)
    ctx["capital_return_aed"] = round(capital_return, 2)
    ctx["total_return_aed"] = round(total_return, 2)
    ctx["full_property_roi_pct"] = round(roi_pct, 2) if roi_pct is not None else None

    # Provenance
    ctx["included_components"] = list(INCLUDED_COMPONENTS)
    ctx["excluded_components"] = list(EXCLUDED_COMPONENTS)
    ctx["missing_inputs"] = []

    # Exit value provenance
    if exit_value_mode:
        ctx["exit_value_mode"] = exit_value_mode
        if exit_value_mode == "USER_APPRECIATION_RATE":
            ctx["annual_appreciation_rate_pct"] = annual_appreciation_rate_pct
            ctx["exit_price_source"] = "DERIVED"
            ctx["appreciation_rate_source"] = "USER_INPUT"
        elif exit_value_mode == "USER_EXIT_PRICE":
            ctx["exit_price_source"] = "USER_INPUT"

    return ctx


def verify_total_return_identity(ctx: Dict[str, Any]) -> bool:
    """
    Verify that:
      cumulative_rental + capital_return
    equals
      cumulative_rental + net_sale_proceeds - total_cash_invested

    Returns True if identity holds within rounding tolerance.
    """
    if ctx.get("calculation_status") != "CALCULATED":
        return True  # Nothing to verify

    cr = ctx["cumulative_net_rental_income_aed"]
    cap = ctx["capital_return_aed"]
    nsp = ctx["net_sale_proceeds_aed"]
    tci = ctx["total_cash_invested_aed"]
    tr = ctx["total_return_aed"]

    # Formulation 1: cr + cap
    form1 = cr + cap
    # Formulation 2: cr + nsp - tci
    form2 = cr + nsp - tci

    # Check both equal total_return and each other
    tolerance = 0.02  # 2 fils tolerance for rounding
    return (
        abs(form1 - tr) < tolerance
        and abs(form2 - tr) < tolerance
        and abs(form1 - form2) < tolerance
    )
