"""
investor_api/roi/full_roi_models.py

Data models for the Full Property ROI V1 shadow calculator.
Defines the full_roi_context output object with provenance.

V1 architecture:
  UNLEVERED
  READY_ONLY
  TOTAL_ROI_ONLY
  CONSTANT_ANNUAL_NET_RENTAL
  DEMO_ONLY_EPHEMERAL

ROI type: UNLEVERED_TOTAL_ROI
Rental assumption: CONSTANT_ANNUAL_NET_RENTAL
"""
from typing import Dict, Any, Optional, List
from enum import Enum


# ── Full ROI calculation status ──
class FullRoiStatus(str, Enum):
    CALCULATED = "CALCULATED"
    INCOMPLETE = "INCOMPLETE"
    NOT_EVALUATED_OFFPLAN = "NOT_EVALUATED_OFFPLAN"


# ── Methodology constants ──
METHODOLOGY_VERSION = "FULL_PROPERTY_ROI_V1"
ROI_TYPE = "UNLEVERED_TOTAL_ROI"
RENTAL_ASSUMPTION = "CONSTANT_ANNUAL_NET_RENTAL"


# ── Included components ──
INCLUDED_COMPONENTS = [
    "purchase_price",
    "verified_user_confirmed_acquisition_costs",
    "net_rental_income",
    "holding_period",
    "exit_sale_price",
    "selling_costs",
]

# ── Excluded components ──
EXCLUDED_COMPONENTS = [
    "financing_leverage",
    "mortgage_interest",
    "rental_growth",
    "tax_assumptions",
    "income_tax",
    "capital_gains_tax",
    "discounted_cash_flow",
    "IRR",
    "time_value_of_money_adjustment",
]


def build_empty_full_roi_context() -> Dict[str, Any]:
    """Build the default full_roi_context with all ROI values null."""
    return {
        "calculation_status": "INCOMPLETE",
        "methodology_version": METHODOLOGY_VERSION,
        "roi_type": ROI_TYPE,
        "rental_assumption": RENTAL_ASSUMPTION,

        # Canonical inputs (echoed for provenance)
        "purchase_price_aed": None,
        "complete_acquisition_costs_aed": None,
        "total_cash_invested_aed": None,
        "annual_net_rental_income_aed": None,
        "holding_period_months": None,
        "holding_period_years": None,
        "exit_sale_price_aed": None,
        "complete_selling_costs_aed": None,
        "net_sale_proceeds_aed": None,

        # Calculated outputs
        "cumulative_net_rental_income_aed": None,
        "capital_return_aed": None,
        "total_return_aed": None,
        "full_property_roi_pct": None,

        # Provenance
        "included_components": list(INCLUDED_COMPONENTS),
        "excluded_components": list(EXCLUDED_COMPONENTS),
        "missing_inputs": [],

        # Description
        "roi_label": "Full Property ROI",
        "roi_description": "Total unlevered return over the selected holding period.",
        "disclosure": (
            "This ROI is TOTAL ROI over the user-selected holding period. "
            "It is NOT annualized ROI, CAGR, or IRR. "
            "Rental income is assumed constant (no growth). "
            "No financing, taxes, or time-value-of-money adjustments."
        ),
    }


def build_offplan_full_roi_context() -> Dict[str, Any]:
    """Build the offplan full_roi_context — NOT_EVALUATED_OFFPLAN."""
    ctx = build_empty_full_roi_context()
    ctx["calculation_status"] = "NOT_EVALUATED_OFFPLAN"
    ctx["missing_inputs"] = []
    ctx["disclosure"] = (
        "Offplan properties are not evaluated for Full Property ROI in V1. "
        "A separate offplan cash-flow model is required."
    )
    return ctx
