"""
investor_api/rental_operating_costs/operating_cost_calculator.py

Calculator for rental operating costs.
Determines calculation level, computes vacancy loss, management cost,
effective rental income, known operating income, and (only when all
required costs are available) Net Rental Income and Net Rental Yield.

All calculations happen on the backend. Frontend never recalculates.
"""
from typing import Dict, Any, Optional
from .operating_cost_models import (
    build_empty_context,
    build_vacancy_from_input,
    build_management_from_input,
    build_maintenance_from_input,
    CalculationLevel,
)


def _round2(v: Optional[float]) -> Optional[float]:
    if v is None:
        return None
    return round(v, 2)


def calculate_operating_cost_context(
    annual_rent_estimate_aed: Optional[float],
    annual_service_charge_aed: Optional[float],
    service_charge_production_eligible: bool,
    current_price_aed: Optional[float],
    vacancy_input: Optional[Dict[str, Any]] = None,
    management_input: Optional[Dict[str, Any]] = None,
    maintenance_input: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build the rental_operating_cost_context from rental + service charge + user inputs.

    Args:
        annual_rent_estimate_aed: From rental_context (frozen V1)
        annual_service_charge_aed: From service_charge_context (frozen V2)
        service_charge_production_eligible: Whether SC is eligible
        current_price_aed: From MASTER (authoritative denominator)
        vacancy_input: {input_mode, percent, loss_aed} or None
        management_input: {input_mode, annual_cost_aed, percent} or None
        maintenance_input: {annual_cost_aed} or None

    Returns:
        rental_operating_cost_context dict with calculation_level, all cost
        fields, effective_rental_income, known_operating_income, and
        net_rental_income/yield (only if ALL costs available).
    """
    ctx = build_empty_context()

    # ── Build cost fields from inputs ──
    vacancy = build_empty_vacancy_field(vacancy_input)
    management = build_empty_management_field(management_input)
    maintenance = build_empty_maintenance_field(maintenance_input)

    # ── Calculate vacancy_loss_aed ──
    vacancy_loss_aed = None
    if vacancy["status"] == "AVAILABLE":
        if vacancy["input_mode"] == "VACANCY_PERCENT":
            if annual_rent_estimate_aed and annual_rent_estimate_aed > 0:
                vacancy_loss_aed = round(annual_rent_estimate_aed * vacancy["percent"] / 100, 2)
                vacancy["loss_aed"] = vacancy_loss_aed
        elif vacancy["input_mode"] == "VACANCY_LOSS_AED":
            vacancy_loss_aed = vacancy["loss_aed"]

    # ── Calculate effective_rental_income_aed ──
    effective_rental_income_aed = None
    if vacancy_loss_aed is not None and annual_rent_estimate_aed is not None:
        effective_rental_income_aed = round(annual_rent_estimate_aed - vacancy_loss_aed, 2)

    # ── Calculate management_cost_aed ──
    management_cost_aed = None
    if management["status"] == "AVAILABLE":
        if management["input_mode"] == "SELF_MANAGED":
            management_cost_aed = 0
            management["annual_cost_aed"] = 0
        elif management["input_mode"] == "USER_INPUT_FIXED_AED":
            management_cost_aed = management["annual_cost_aed"]
        elif management["input_mode"] == "USER_INPUT_PERCENT":
            # Base: effective_rental_income_after_vacancy
            if effective_rental_income_aed is not None:
                management_cost_aed = round(effective_rental_income_aed * management["percent"] / 100, 2)
                management["annual_cost_aed"] = management_cost_aed
            elif annual_rent_estimate_aed is not None:
                # Vacancy not provided — use annual rent as base
                management_cost_aed = round(annual_rent_estimate_aed * management["percent"] / 100, 2)
                management["annual_cost_aed"] = management_cost_aed

    # ── Calculate maintenance_cost_aed ──
    maintenance_cost_aed = None
    if maintenance["status"] == "AVAILABLE":
        maintenance_cost_aed = maintenance["annual_cost_aed"]

    # ── Determine which costs are available ──
    has_vacancy = vacancy["status"] == "AVAILABLE"
    has_management = management["status"] == "AVAILABLE"
    has_maintenance = maintenance["status"] == "AVAILABLE"
    has_service_charge = service_charge_production_eligible and annual_service_charge_aed is not None

    available_count = sum([has_vacancy, has_management, has_maintenance])
    all_operating_available = has_vacancy and has_management and has_maintenance

    # ── Determine calculation level ──
    if all_operating_available and has_service_charge:
        level = CalculationLevel.NET_RENTAL
    elif available_count > 0:
        level = CalculationLevel.PARTIAL_OPERATING_COSTS
    else:
        level = CalculationLevel.SERVICE_CHARGE_ADJUSTED

    # ── Calculate known_operating_income_aed (partial) ──
    known_operating_income_aed = None
    if available_count > 0 and annual_rent_estimate_aed is not None:
        base = effective_rental_income_aed if effective_rental_income_aed is not None else annual_rent_estimate_aed
        known_operating_income_aed = base
        deductions = []

        if has_service_charge and annual_service_charge_aed is not None:
            known_operating_income_aed -= annual_service_charge_aed
            deductions.append("Official service charges")

        if has_vacancy:
            # Already deducted via effective_rental_income
            pass

        if has_management and management_cost_aed is not None:
            known_operating_income_aed -= management_cost_aed
            deductions.append("Property management")

        if has_maintenance and maintenance_cost_aed is not None:
            known_operating_income_aed -= maintenance_cost_aed
            deductions.append("Unit maintenance")

        known_operating_income_aed = round(known_operating_income_aed, 2)

    # ── Calculate Net Rental Income (ONLY if ALL costs available) ──
    net_rental_income_aed = None
    net_rental_yield_pct = None

    if level == CalculationLevel.NET_RENTAL:
        # All required costs are available
        net_rental_income_aed = annual_rent_estimate_aed
        net_rental_income_aed -= vacancy_loss_aed
        net_rental_income_aed -= annual_service_charge_aed
        net_rental_income_aed -= management_cost_aed
        net_rental_income_aed -= maintenance_cost_aed
        net_rental_income_aed = round(net_rental_income_aed, 2)

        if current_price_aed and current_price_aed > 0:
            net_rental_yield_pct = round(net_rental_income_aed / current_price_aed * 100, 2)

    # ── Calculate Adjusted Rental Income (Level 3: rent - SC - vacancy only) ──
    # This is shown when vacancy is available but management or maintenance is missing.
    # It does NOT include management or maintenance even if they are available.
    adjusted_rental_income_aed = None
    adjusted_rental_yield_pct = None
    if has_vacancy and has_service_charge and annual_rent_estimate_aed is not None:
        adjusted_rental_income_aed = round(
            annual_rent_estimate_aed - vacancy_loss_aed - annual_service_charge_aed, 2
        )
        if current_price_aed and current_price_aed > 0:
            adjusted_rental_yield_pct = round(adjusted_rental_income_aed / current_price_aed * 100, 2)

    # ── Build included/missing cost lists ──
    included_costs = ["Estimated annual market rent"]
    if has_service_charge:
        included_costs.append("Official DLD/RERA Mollak service charges")
    if has_vacancy:
        included_costs.append("Your vacancy allowance")
    if has_management:
        if management["input_mode"] == "SELF_MANAGED":
            included_costs.append("Property management (self-managed)")
        else:
            included_costs.append("Your property management cost")
    if has_maintenance:
        included_costs.append("Your unit maintenance cost")

    missing_costs = []
    if not has_vacancy:
        missing_costs.append("Vacancy")
    if not has_management:
        missing_costs.append("Property management")
    if not has_maintenance:
        missing_costs.append("Unit maintenance")

    # ── Partial disclosure ──
    partial_disclosure = None
    if level == CalculationLevel.PARTIAL_OPERATING_COSTS:
        partial_disclosure = "This is not Net Rental Income because one or more operating cost inputs are still missing."
    elif level == CalculationLevel.NET_RENTAL:
        partial_disclosure = None

    # ── Assemble context ──
    ctx = {
        "calculation_level": level.value,
        "vacancy": vacancy,
        "management": management,
        "maintenance": maintenance,
        "effective_rental_income_aed": _round2(effective_rental_income_aed),
        "known_operating_income_aed": _round2(known_operating_income_aed),
        "adjusted_rental_income_aed": _round2(adjusted_rental_income_aed),
        "adjusted_rental_yield_pct": adjusted_rental_yield_pct,
        "net_rental_income_aed": _round2(net_rental_income_aed),
        "net_rental_yield_pct": net_rental_yield_pct,
        "included_costs": included_costs,
        "missing_costs": missing_costs,
        "disclosure": "Vacancy, management, and maintenance values shown here are based on your inputs unless identified as verified data.",
        "partial_disclosure": partial_disclosure,
    }

    return ctx


def build_empty_vacancy_field(vacancy_input: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build vacancy field from input or empty."""
    if vacancy_input is None or vacancy_input.get("input_mode") is None:
        return {
            "status": "MISSING",
            "source": "MISSING",
            "input_mode": None,
            "percent": None,
            "loss_aed": None,
        }
    return build_vacancy_from_input(
        vacancy_input["input_mode"],
        vacancy_input.get("percent"),
        vacancy_input.get("loss_aed"),
    )


def build_empty_management_field(management_input: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build management field from input or empty."""
    if management_input is None or management_input.get("input_mode") is None:
        return {
            "status": "MISSING",
            "source": "MISSING",
            "input_mode": None,
            "percent": None,
            "annual_cost_aed": None,
        }
    return build_management_from_input(
        management_input["input_mode"],
        management_input.get("annual_cost_aed"),
        management_input.get("percent"),
    )


def build_empty_maintenance_field(maintenance_input: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Build maintenance field from input or empty."""
    if maintenance_input is None or maintenance_input.get("annual_cost_aed") is None:
        return {
            "status": "MISSING",
            "source": "MISSING",
            "annual_cost_aed": None,
        }
    return build_maintenance_from_input(maintenance_input["annual_cost_aed"])
