"""
investor_api/roi/acquisition_cost_models.py

Data models for the acquisition-cost layer.
Defines provenance sources, fee component structures, calculation levels,
and the acquisition_cost_context object.

V1.2 additions:
  - DLD buyer share confirmation semantics (OFFICIAL_STATUTORY_DEFAULT,
    USER_CONFIRMED_DEFAULT, USER_OVERRIDE, MISSING)
  - DLD input modes (USE_STATUTORY_DEFAULT, CUSTOM_PERCENT, CUSTOM_AED)
  - Broker modes (BROKER_PERCENT, BROKER_FIXED_AED, NO_BROKER_COST)
  - Developer/admin modes (USER_INPUT_AED, NO_DEVELOPER_ADMIN_FEE)
  - PARTIAL_ACQUISITION_COSTS level
  - Enhanced provenance (input_mode, confirmed, official_total_rate_pct,
    statutory_buyer_default_pct, actual_buyer_rate_pct)

Every component exposes:
  name, amount_aed, source, status, calculation_basis,
  included_in_total, evidence_date, input_mode

Allowed sources:
  MASTER, OFFICIAL_DLD_RERA, USER_INPUT, DERIVED, NOT_APPLICABLE, MISSING

Allowed statuses:
  OFFICIAL_VERIFIED, USER_INPUT, NOT_APPLICABLE, MISSING
"""
from typing import Dict, Any, Optional, Literal
from enum import Enum


# ── Provenance sources ──
class AcquisitionSource(str, Enum):
    MASTER = "MASTER"
    OFFICIAL_DLD_RERA = "OFFICIAL_DLD_RERA"
    USER_INPUT = "USER_INPUT"
    DERIVED = "DERIVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MISSING = "MISSING"


# ── Fee component statuses ──
class FeeStatus(str, Enum):
    OFFICIAL_VERIFIED = "OFFICIAL_VERIFIED"
    USER_INPUT = "USER_INPUT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    MISSING = "MISSING"


# ── Acquisition calculation levels ──
class AcquisitionLevel(str, Enum):
    PURCHASE_PRICE_ONLY = "PURCHASE_PRICE_ONLY"
    OFFICIAL_ACQUISITION_COSTS = "OFFICIAL_ACQUISITION_COSTS"
    PARTIAL_ACQUISITION_COSTS = "PARTIAL_ACQUISITION_COSTS"
    COMPLETE_ACQUISITION_COSTS = "COMPLETE_ACQUISITION_COSTS"


# ── DLD payer allocation ──
class DldPayerAllocation(str, Enum):
    FIXED_BY_OFFICIAL_RULE = "FIXED_BY_OFFICIAL_RULE"
    CONTRACT_DEPENDENT = "CONTRACT_DEPENDENT"
    UNRESOLVED = "UNRESOLVED"


# ── DLD buyer share confirmation status ──
class DldBuyerShareStatus(str, Enum):
    OFFICIAL_STATUTORY_DEFAULT = "OFFICIAL_STATUTORY_DEFAULT"
    USER_CONFIRMED_DEFAULT = "USER_CONFIRMED_DEFAULT"
    USER_OVERRIDE = "USER_OVERRIDE"
    MISSING = "MISSING"


# ── DLD input modes ──
DldInputMode = Literal["USE_STATUTORY_DEFAULT", "CUSTOM_PERCENT", "CUSTOM_AED"]


# ── Broker input modes ──
BrokerPurchaseMode = Literal["BROKER_PERCENT", "BROKER_FIXED_AED", "NO_BROKER_COST"]


# ── Developer/admin input modes ──
DeveloperAdminMode = Literal["USER_INPUT_AED", "NO_DEVELOPER_ADMIN_FEE"]


# ── Official constants ──
OFFICIAL_DLD_TOTAL_RATE_PCT = 4.0
OFFICIAL_DLD_BUYER_STATUTORY_DEFAULT_PCT = 2.0
OFFICIAL_DLD_SELLER_STATUTORY_DEFAULT_PCT = 2.0


def _missing_component(name: str, reason: str = "") -> Dict[str, Any]:
    """Build a missing fee component."""
    return {
        "name": name,
        "amount_aed": None,
        "source": "MISSING",
        "status": "MISSING",
        "calculation_basis": reason or "Not available",
        "included_in_total": False,
        "evidence_date": None,
        "input_mode": None,
    }


def _not_applicable_component(name: str, reason: str) -> Dict[str, Any]:
    """Build a not-applicable fee component."""
    return {
        "name": name,
        "amount_aed": 0,
        "source": "NOT_APPLICABLE",
        "status": "NOT_APPLICABLE",
        "calculation_basis": reason,
        "included_in_total": False,
        "evidence_date": None,
        "input_mode": None,
    }


def build_empty_acquisition_context() -> Dict[str, Any]:
    """Build the default acquisition_cost_context with all fees MISSING."""
    return {
        "calculation_level": "PURCHASE_PRICE_ONLY",
        "purchase_price": {
            "name": "Property Purchase Price",
            "amount_aed": None,
            "source": "MASTER",
            "status": "MISSING",
            "calculation_basis": "MASTER current_price_aed",
            "included_in_total": False,
            "evidence_date": None,
            "input_mode": None,
        },
        "dld_transfer": {
            "name": "DLD Transfer Fee",
            "amount_aed": None,
            "source": "MISSING",
            "status": "MISSING",
            "calculation_basis": "4% of sale contract value — ECR 30/2013. Buyer share requires user confirmation.",
            "included_in_total": False,
            "evidence_date": None,
            "input_mode": None,
            "official_total_rate_pct": OFFICIAL_DLD_TOTAL_RATE_PCT,
            "statutory_buyer_default_pct": OFFICIAL_DLD_BUYER_STATUTORY_DEFAULT_PCT,
            "actual_buyer_rate_pct": None,
            "buyer_share_status": "MISSING",
            "payer_allocation": "CONTRACT_DEPENDENT",
            "confirmed": False,
        },
        "trustee_office_fee": _missing_component(
            "Trustee Office Fee",
            "Not in DLD statute — trustee offices are private entities; fee varies. USER_INPUT required.",
        ),
        "title_deed_fee": _missing_component(
            "Title Deed Fee",
            "AED 250 — ECR 30/2013 Schedule Item 22",
        ),
        "knowledge_fee": _missing_component(
            "Knowledge Fee",
            "AED 10 — Law No. 1 of 2018",
        ),
        "innovation_fee": _missing_component(
            "Innovation Fee",
            "AED 10 — Law No. 2 of 2018",
        ),
        "broker_purchase": _missing_component(
            "Broker Purchase Commission",
            "No statutory rate — USER_INPUT or NO_BROKER_COST required",
        ),
        "developer_admin": _missing_component(
            "Developer / Admin Fee",
            "Varies by developer — USER_INPUT or NO_DEVELOPER_ADMIN_FEE",
        ),
        "mortgage_registration_fee": _not_applicable_component(
            "Mortgage Registration Fee",
            "NOT_APPLICABLE in unlevered V1",
        ),
        "official_acquisition_fees_aed": None,
        "known_acquisition_costs_aed": None,
        "complete_acquisition_costs_aed": None,
        "total_cash_invested_aed": None,
        "missing_components": [],
        "disclosure": (
            "Acquisition costs are based on official DLD/RERA statutory rates "
            "and user-entered transaction costs. Official fees are derived from "
            "Executive Council Resolution No. 30 of 2013 and Laws No. 1 & 2 of 2018."
        ),
    }
