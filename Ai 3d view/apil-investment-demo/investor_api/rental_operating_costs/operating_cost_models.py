"""
investor_api/rental_operating_costs/operating_cost_models.py

Data models for rental operating cost inputs.
Defines provenance sources, input modes, cost field structures, and
the rental_operating_cost_context object.
"""
from typing import Dict, Any, Optional, Literal
from enum import Enum
from datetime import datetime, timezone


# ── Provenance sources ──
class CostSource(str, Enum):
    OFFICIAL = "OFFICIAL"
    VERIFIED_EXTERNAL = "VERIFIED_EXTERNAL"
    USER_INPUT = "USER_INPUT"
    SELF_MANAGED = "SELF_MANAGED"
    MISSING = "MISSING"


# Forbidden sources (never allowed)
FORBIDDEN_SOURCES = {"ASSUMED", "DEFAULT", "MARKET_STANDARD", "ESTIMATED_WITHOUT_EVIDENCE"}


# ── Input modes ──
VacancyInputMode = Literal["VACANCY_PERCENT", "VACANCY_LOSS_AED"]
ManagementInputMode = Literal["USER_INPUT_FIXED_AED", "USER_INPUT_PERCENT", "SELF_MANAGED"]


# ── Calculation levels ──
class CalculationLevel(str, Enum):
    GROSS_RENTAL = "GROSS_RENTAL"
    SERVICE_CHARGE_ADJUSTED = "SERVICE_CHARGE_ADJUSTED"
    PARTIAL_OPERATING_COSTS = "PARTIAL_OPERATING_COSTS"
    NET_RENTAL = "NET_RENTAL"


def _empty_vacancy() -> Dict[str, Any]:
    return {
        "status": "MISSING",
        "source": "MISSING",
        "input_mode": None,
        "percent": None,
        "loss_aed": None,
    }


def _empty_management() -> Dict[str, Any]:
    return {
        "status": "MISSING",
        "source": "MISSING",
        "input_mode": None,
        "percent": None,
        "annual_cost_aed": None,
    }


def _empty_maintenance() -> Dict[str, Any]:
    return {
        "status": "MISSING",
        "source": "MISSING",
        "annual_cost_aed": None,
    }


def build_empty_context() -> Dict[str, Any]:
    """Build the default rental_operating_cost_context with all costs MISSING."""
    return {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "vacancy": _empty_vacancy(),
        "management": _empty_management(),
        "maintenance": _empty_maintenance(),
        "effective_rental_income_aed": None,
        "known_operating_income_aed": None,
        "net_rental_income_aed": None,
        "net_rental_yield_pct": None,
        "included_costs": [],
        "missing_costs": ["Vacancy", "Property management", "Unit maintenance"],
        "disclosure": "Vacancy, management, and maintenance values shown here are based on your inputs unless identified as verified data.",
        "partial_disclosure": None,
    }


def build_vacancy_from_input(
    input_mode: VacancyInputMode,
    percent: Optional[float] = None,
    loss_aed: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a vacancy cost field from user input."""
    if input_mode == "VACANCY_PERCENT":
        return {
            "status": "AVAILABLE",
            "source": "USER_INPUT",
            "input_mode": "VACANCY_PERCENT",
            "percent": percent,
            "loss_aed": None,  # calculated by calculator
        }
    elif input_mode == "VACANCY_LOSS_AED":
        return {
            "status": "AVAILABLE",
            "source": "USER_INPUT",
            "input_mode": "VACANCY_LOSS_AED",
            "percent": None,
            "loss_aed": loss_aed,
        }
    return _empty_vacancy()


def build_management_from_input(
    input_mode: ManagementInputMode,
    annual_cost_aed: Optional[float] = None,
    percent: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a management cost field from user input."""
    if input_mode == "SELF_MANAGED":
        return {
            "status": "AVAILABLE",
            "source": "SELF_MANAGED",
            "input_mode": "SELF_MANAGED",
            "percent": None,
            "annual_cost_aed": 0,
        }
    elif input_mode == "USER_INPUT_FIXED_AED":
        return {
            "status": "AVAILABLE",
            "source": "USER_INPUT",
            "input_mode": "USER_INPUT_FIXED_AED",
            "percent": None,
            "annual_cost_aed": annual_cost_aed,
        }
    elif input_mode == "USER_INPUT_PERCENT":
        return {
            "status": "AVAILABLE",
            "source": "USER_INPUT",
            "input_mode": "USER_INPUT_PERCENT",
            "percent": percent,
            "annual_cost_aed": None,  # calculated by calculator
        }
    return _empty_management()


def build_maintenance_from_input(annual_cost_aed: float) -> Dict[str, Any]:
    """Build a maintenance cost field from user input."""
    return {
        "status": "AVAILABLE",
        "source": "USER_INPUT",
        "annual_cost_aed": annual_cost_aed,
    }
