"""
investor_api/roi/full_roi_validation.py

Readiness gate for Full Property ROI V1 calculation.
Validates ALL required inputs before allowing ROI calculation.

Readiness requires:
  - property status = Ready
  - acquisition calculation level = COMPLETE_ACQUISITION_COSTS
  - total_cash_invested_aed != null
  - operating-cost calculation level = NET_RENTAL
  - net_rental_income_aed != null
  - holding_period_months > 0
  - exit_sale_price_aed != null
  - selling calculation level = COMPLETE_SELLING_COSTS
  - net_sale_proceeds_aed != null
  - roi_input_readiness = READY_FOR_FULL_ROI_CALCULATION

If any condition fails → INCOMPLETE, all ROI outputs null.
"""
from typing import Tuple, List, Dict, Any, Optional


def check_full_roi_readiness(
    unit_status: Optional[str],
    acquisition_calculation_level: Optional[str],
    total_cash_invested_aed: Optional[float],
    net_rental_calculation_level: Optional[str],
    net_rental_income_aed: Optional[float],
    holding_period_months: Optional[float],
    exit_sale_price_aed: Optional[float],
    selling_calculation_level: Optional[str],
    net_sale_proceeds_aed: Optional[float],
    roi_input_readiness: Optional[str],
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Check if all inputs are ready for Full ROI calculation.

    Returns (is_ready, missing_inputs, details).
    """
    missing: List[str] = []

    # Offplan check first
    if unit_status and "offplan" in unit_status.lower():
        return False, [], {"reason": "NOT_EVALUATED_OFFPLAN", "offplan": True}

    # Property status
    if not unit_status or "ready" not in unit_status.lower():
        missing.append("property_status_ready")

    # Acquisition
    if acquisition_calculation_level != "COMPLETE_ACQUISITION_COSTS":
        missing.append("complete_acquisition_costs")
    if total_cash_invested_aed is None or total_cash_invested_aed <= 0:
        missing.append("total_cash_invested_aed")

    # Net rental
    if net_rental_calculation_level != "NET_RENTAL":
        missing.append("net_rental_calculation_level")
    if net_rental_income_aed is None:
        missing.append("net_rental_income_aed")

    # Holding period
    if holding_period_months is None or holding_period_months <= 0:
        missing.append("holding_period_months")

    # Exit value
    if exit_sale_price_aed is None:
        missing.append("exit_sale_price_aed")

    # Selling costs
    if selling_calculation_level != "COMPLETE_SELLING_COSTS":
        missing.append("complete_selling_costs")
    if net_sale_proceeds_aed is None:
        missing.append("net_sale_proceeds_aed")

    # Overall readiness from V1.3
    if roi_input_readiness != "READY_FOR_FULL_ROI_CALCULATION":
        if len(missing) == 0:
            missing.append("roi_input_readiness")

    is_ready = len(missing) == 0
    return is_ready, missing, {"offplan": False}
