"""
investor_api/rental_operating_costs/operating_cost_validation.py

Validation rules for rental operating cost inputs.
Returns (is_valid, errors, validated_values).
"""
from typing import Tuple, List, Dict, Any, Optional


def validate_vacancy(
    input_mode: Optional[str],
    percent: Optional[float],
    loss_aed: Optional[float],
    annual_rent_estimate_aed: Optional[float],
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate vacancy input.

    Rules:
      - input_mode must be VACANCY_PERCENT or VACANCY_LOSS_AED (not both)
      - If VACANCY_PERCENT: 0 <= percent <= 100
      - If VACANCY_LOSS_AED: 0 <= loss_aed <= annual_rent_estimate_aed
      - annual_rent_estimate_aed must be > 0
    """
    errors: List[str] = []

    if input_mode is None:
        return True, [], {"input_mode": None, "percent": None, "loss_aed": None}

    if input_mode not in ("VACANCY_PERCENT", "VACANCY_LOSS_AED"):
        errors.append(f"Invalid vacancy input_mode: {input_mode}")
        return False, errors, {}

    # Both modes simultaneously is forbidden
    if input_mode == "VACANCY_PERCENT" and loss_aed is not None:
        errors.append("Cannot provide both VACANCY_PERCENT and VACANCY_LOSS_AED")
        return False, errors, {}

    if input_mode == "VACANCY_LOSS_AED" and percent is not None:
        errors.append("Cannot provide both VACANCY_LOSS_AED and VACANCY_PERCENT")
        return False, errors, {}

    if annual_rent_estimate_aed is None or annual_rent_estimate_aed <= 0:
        errors.append("annual_rent_estimate_aed must be > 0 to calculate vacancy")
        return False, errors, {}

    if input_mode == "VACANCY_PERCENT":
        if percent is None:
            errors.append("VACANCY_PERCENT requires percent value")
            return False, errors, {}
        if not (0 <= percent <= 100):
            errors.append(f"vacancy_percent must be 0-100, got {percent}")
            return False, errors, {}
        return True, [], {"input_mode": "VACANCY_PERCENT", "percent": float(percent), "loss_aed": None}

    if input_mode == "VACANCY_LOSS_AED":
        if loss_aed is None:
            errors.append("VACANCY_LOSS_AED requires loss_aed value")
            return False, errors, {}
        if loss_aed < 0:
            errors.append(f"vacancy_loss_aed must be >= 0, got {loss_aed}")
            return False, errors, {}
        if loss_aed > annual_rent_estimate_aed:
            errors.append(f"vacancy_loss_aed ({loss_aed}) cannot exceed annual rent ({annual_rent_estimate_aed})")
            return False, errors, {}
        return True, [], {"input_mode": "VACANCY_LOSS_AED", "percent": None, "loss_aed": float(loss_aed)}

    return False, ["Unknown vacancy validation error"], {}


def validate_management(
    input_mode: Optional[str],
    annual_cost_aed: Optional[float],
    percent: Optional[float],
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate management input.

    Rules:
      - input_mode must be USER_INPUT_FIXED_AED, USER_INPUT_PERCENT, or SELF_MANAGED
      - If SELF_MANAGED: annual_cost_aed = 0, source = SELF_MANAGED
      - If USER_INPUT_FIXED_AED: annual_cost_aed >= 0
      - If USER_INPUT_PERCENT: percent >= 0
    """
    errors: List[str] = []

    if input_mode is None:
        return True, [], {"input_mode": None, "annual_cost_aed": None, "percent": None}

    if input_mode not in ("USER_INPUT_FIXED_AED", "USER_INPUT_PERCENT", "SELF_MANAGED"):
        errors.append(f"Invalid management input_mode: {input_mode}")
        return False, errors, {}

    if input_mode == "SELF_MANAGED":
        return True, [], {"input_mode": "SELF_MANAGED", "annual_cost_aed": 0, "percent": None}

    if input_mode == "USER_INPUT_FIXED_AED":
        if annual_cost_aed is None:
            errors.append("USER_INPUT_FIXED_AED requires annual_cost_aed")
            return False, errors, {}
        if annual_cost_aed < 0:
            errors.append(f"management annual_cost_aed must be >= 0, got {annual_cost_aed}")
            return False, errors, {}
        return True, [], {"input_mode": "USER_INPUT_FIXED_AED", "annual_cost_aed": float(annual_cost_aed), "percent": None}

    if input_mode == "USER_INPUT_PERCENT":
        if percent is None:
            errors.append("USER_INPUT_PERCENT requires percent value")
            return False, errors, {}
        if percent < 0:
            errors.append(f"management percent must be >= 0, got {percent}")
            return False, errors, {}
        return True, [], {"input_mode": "USER_INPUT_PERCENT", "annual_cost_aed": None, "percent": float(percent)}

    return False, ["Unknown management validation error"], {}


def validate_maintenance(annual_cost_aed: Optional[float]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate maintenance input.

    Rules:
      - annual_cost_aed >= 0
    """
    errors: List[str] = []

    if annual_cost_aed is None:
        return True, [], {"annual_cost_aed": None}

    if annual_cost_aed < 0:
        errors.append(f"maintenance annual_cost_aed must be >= 0, got {annual_cost_aed}")
        return False, errors, {}

    return True, [], {"annual_cost_aed": float(annual_cost_aed)}
