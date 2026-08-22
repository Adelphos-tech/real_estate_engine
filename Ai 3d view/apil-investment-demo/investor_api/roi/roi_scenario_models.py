"""
investor_api/roi/roi_scenario_models.py

Data models for the ROI scenario input layer (V1.3).
Covers: holding period, exit value, selling costs, ROI input readiness.

Every component exposes:
  name, amount_aed, source, status, calculation_basis,
  included_in_total, input_mode

Allowed sources:
  MASTER, OFFICIAL_DLD_RERA, USER_INPUT, DERIVED, NOT_APPLICABLE, MISSING

Allowed statuses:
  OFFICIAL_VERIFIED, USER_INPUT, NOT_APPLICABLE, MISSING
"""
from typing import Dict, Any, Optional, Literal
from enum import Enum


# ── Holding period ──
HoldingPeriodStatus = Literal["AVAILABLE", "MISSING"]


# ── Exit value modes ──
ExitValueMode = Literal["USER_EXIT_PRICE", "USER_APPRECIATION_RATE"]


# ── Selling broker modes ──
SellingBrokerMode = Literal["SELLING_BROKER_PERCENT", "SELLING_BROKER_FIXED_AED", "NO_SELLING_BROKER_COST"]


# ── NOC modes ──
NocMode = Literal["NOC_FIXED_AED", "NO_NOC_FEE"]


# ── Other selling cost modes ──
OtherSellingMode = Literal["OTHER_SELLING_COSTS_AED", "NO_OTHER_SELLING_COSTS"]


# ── Selling cost calculation levels ──
class SellingCostLevel(str, Enum):
    NO_SELLING_COSTS = "NO_SELLING_COSTS"
    PARTIAL_SELLING_COSTS = "PARTIAL_SELLING_COSTS"
    COMPLETE_SELLING_COSTS = "COMPLETE_SELLING_COSTS"


# ── ROI input readiness ──
class RoiInputReadiness(str, Enum):
    INCOMPLETE = "INCOMPLETE"
    READY_FOR_FULL_ROI_CALCULATION = "READY_FOR_FULL_ROI_CALCULATION"
    NOT_EVALUATED_OFFPLAN = "NOT_EVALUATED_OFFPLAN"


def _missing_component(name: str, reason: str = "") -> Dict[str, Any]:
    return {
        "name": name,
        "amount_aed": None,
        "source": "MISSING",
        "status": "MISSING",
        "calculation_basis": reason or "Not available",
        "included_in_total": False,
        "input_mode": None,
    }


def build_empty_scenario_context() -> Dict[str, Any]:
    """Build the default roi_scenario_context with all inputs MISSING."""
    return {
        "holding_period": {
            "status": "MISSING",
            "months": None,
            "years": None,
            "source": "MISSING",
            "input_mode": None,
        },
        "exit_value": {
            "status": "MISSING",
            "mode": None,
            "exit_sale_price_aed": None,
            "annual_appreciation_rate_pct": None,
            "source": "MISSING",
            "rate_source": None,
            "exit_price_source": None,
            "calculation_basis": None,
            "input_mode": None,
        },
        "selling_costs": {
            "calculation_level": "NO_SELLING_COSTS",
            "broker": _missing_component(
                "Selling Broker Commission",
                "No statutory rate — USER_INPUT or NO_SELLING_BROKER_COST required",
            ),
            "noc": _missing_component(
                "Developer / NOC Fee",
                "Varies by developer — USER_INPUT or NO_NOC_FEE required",
            ),
            "other": _missing_component(
                "Other Selling Costs",
                "USER_INPUT or NO_OTHER_SELLING_COSTS required",
            ),
            "complete_selling_costs_aed": None,
        },
        "net_sale_proceeds_aed": None,
        "roi_input_readiness": "INCOMPLETE",
        "missing_roi_inputs": [
            "holding_period",
            "exit_value",
            "selling_costs",
        ],
        "disclosure": (
            "ROI scenario inputs are based on user assumptions only. "
            "Exit value is not a market forecast. Appreciation rate is "
            "user-entered, not a verified model."
        ),
    }
