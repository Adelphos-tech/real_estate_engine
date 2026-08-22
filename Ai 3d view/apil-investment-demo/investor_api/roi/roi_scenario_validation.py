"""
investor_api/roi/roi_scenario_validation.py

Validation rules for ROI scenario user inputs (V1.3).
Returns (is_valid, errors, validated_values).

Holding period:
  - months > 0
  - months <= 1200 (100 years technical max)
  - No default

Exit value:
  - mode must be USER_EXIT_PRICE or USER_APPRECIATION_RATE (not both)
  - USER_EXIT_PRICE: exit_sale_price_aed >= 0
  - USER_APPRECIATION_RATE: rate must be finite, -100 <= rate <= 1000
  - Reject NaN, Infinity

Selling broker:
  - SELLING_BROKER_PERCENT: percent >= 0, <= 100
  - SELLING_BROKER_FIXED_AED: amount >= 0
  - NO_SELLING_BROKER_COST: explicit zero

NOC:
  - NOC_FIXED_AED: amount >= 0
  - NO_NOC_FEE: explicit zero

Other selling:
  - OTHER_SELLING_COSTS_AED: amount >= 0
  - NO_OTHER_SELLING_COSTS: explicit zero
"""
from typing import Tuple, List, Dict, Any, Optional
import math


def validate_holding_period(months: Optional[float]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate holding period in months."""
    errors: List[str] = []
    if months is None:
        return True, [], {"months": None}
    if not isinstance(months, (int, float)) or math.isnan(months) or math.isinf(months):
        errors.append(f"holding_period_months must be a finite number, got {months}")
        return False, errors, {}
    if months <= 0:
        errors.append(f"holding_period_months must be > 0, got {months}")
        return False, errors, {}
    if months > 1200:
        errors.append(f"holding_period_months must be <= 1200 (100 years), got {months}")
        return False, errors, {}
    return True, [], {"months": float(months)}


def validate_exit_value(
    mode: Optional[str],
    exit_sale_price_aed: Optional[float] = None,
    annual_appreciation_rate_pct: Optional[float] = None,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate exit value input. Only one mode allowed."""
    errors: List[str] = []
    if mode is None:
        return True, [], {"mode": None, "exit_sale_price_aed": None, "annual_appreciation_rate_pct": None}

    if mode not in ("USER_EXIT_PRICE", "USER_APPRECIATION_RATE"):
        errors.append(f"Invalid exit value mode: {mode}")
        return False, errors, {}

    # Both modes simultaneously is forbidden
    if mode == "USER_EXIT_PRICE" and annual_appreciation_rate_pct is not None:
        errors.append("Cannot provide both USER_EXIT_PRICE and USER_APPRECIATION_RATE")
        return False, errors, {}
    if mode == "USER_APPRECIATION_RATE" and exit_sale_price_aed is not None:
        errors.append("Cannot provide both USER_APPRECIATION_RATE and USER_EXIT_PRICE")
        return False, errors, {}

    if mode == "USER_EXIT_PRICE":
        if exit_sale_price_aed is None:
            errors.append("USER_EXIT_PRICE requires exit_sale_price_aed value")
            return False, errors, {}
        if not isinstance(exit_sale_price_aed, (int, float)) or math.isnan(exit_sale_price_aed) or math.isinf(exit_sale_price_aed):
            errors.append(f"exit_sale_price_aed must be a finite number, got {exit_sale_price_aed}")
            return False, errors, {}
        if exit_sale_price_aed < 0:
            errors.append(f"exit_sale_price_aed must be >= 0, got {exit_sale_price_aed}")
            return False, errors, {}
        return True, [], {"mode": "USER_EXIT_PRICE", "exit_sale_price_aed": float(exit_sale_price_aed), "annual_appreciation_rate_pct": None}

    if mode == "USER_APPRECIATION_RATE":
        if annual_appreciation_rate_pct is None:
            errors.append("USER_APPRECIATION_RATE requires annual_appreciation_rate_pct value")
            return False, errors, {}
        if not isinstance(annual_appreciation_rate_pct, (int, float)) or math.isnan(annual_appreciation_rate_pct) or math.isinf(annual_appreciation_rate_pct):
            errors.append(f"annual_appreciation_rate_pct must be a finite number, got {annual_appreciation_rate_pct}")
            return False, errors, {}
        # Allow negative (prices can decline). Technical bounds to reject non-finite / absurd.
        if annual_appreciation_rate_pct < -100:
            errors.append(f"annual_appreciation_rate_pct must be >= -100 (complete loss), got {annual_appreciation_rate_pct}")
            return False, errors, {}
        if annual_appreciation_rate_pct > 1000:
            errors.append(f"annual_appreciation_rate_pct must be <= 1000 (technical max), got {annual_appreciation_rate_pct}")
            return False, errors, {}
        return True, [], {"mode": "USER_APPRECIATION_RATE", "exit_sale_price_aed": None, "annual_appreciation_rate_pct": float(annual_appreciation_rate_pct)}

    return False, ["Unknown exit value validation error"], {}


def validate_selling_broker(
    mode: Optional[str],
    percent: Optional[float] = None,
    amount_aed: Optional[float] = None,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate selling broker commission input."""
    errors: List[str] = []
    if mode is None:
        return True, [], {"mode": None, "percent": None, "amount_aed": None}

    if mode not in ("SELLING_BROKER_PERCENT", "SELLING_BROKER_FIXED_AED", "NO_SELLING_BROKER_COST"):
        errors.append(f"Invalid selling broker mode: {mode}")
        return False, errors, {}

    if mode == "NO_SELLING_BROKER_COST":
        return True, [], {"mode": "NO_SELLING_BROKER_COST", "percent": None, "amount_aed": 0.0}

    if mode == "SELLING_BROKER_PERCENT":
        if percent is None:
            errors.append("SELLING_BROKER_PERCENT requires percent value")
            return False, errors, {}
        if percent < 0:
            errors.append(f"selling broker percent must be >= 0, got {percent}")
            return False, errors, {}
        if percent > 100:
            errors.append(f"selling broker percent must be <= 100, got {percent}")
            return False, errors, {}
        return True, [], {"mode": "SELLING_BROKER_PERCENT", "percent": float(percent), "amount_aed": None}

    if mode == "SELLING_BROKER_FIXED_AED":
        if amount_aed is None:
            errors.append("SELLING_BROKER_FIXED_AED requires amount_aed value")
            return False, errors, {}
        if amount_aed < 0:
            errors.append(f"selling broker amount_aed must be >= 0, got {amount_aed}")
            return False, errors, {}
        return True, [], {"mode": "SELLING_BROKER_FIXED_AED", "percent": None, "amount_aed": float(amount_aed)}

    return False, ["Unknown selling broker validation error"], {}


def validate_noc(
    mode: Optional[str],
    amount_aed: Optional[float] = None,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate NOC/developer fee input."""
    errors: List[str] = []
    if mode is None:
        return True, [], {"mode": None, "amount_aed": None}

    if mode not in ("NOC_FIXED_AED", "NO_NOC_FEE"):
        errors.append(f"Invalid NOC mode: {mode}")
        return False, errors, {}

    if mode == "NO_NOC_FEE":
        return True, [], {"mode": "NO_NOC_FEE", "amount_aed": 0.0}

    if mode == "NOC_FIXED_AED":
        if amount_aed is None:
            errors.append("NOC_FIXED_AED requires amount_aed value")
            return False, errors, {}
        if amount_aed < 0:
            errors.append(f"NOC fee must be >= 0, got {amount_aed}")
            return False, errors, {}
        return True, [], {"mode": "NOC_FIXED_AED", "amount_aed": float(amount_aed)}

    return False, ["Unknown NOC validation error"], {}


def validate_other_selling(
    mode: Optional[str],
    amount_aed: Optional[float] = None,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """Validate other selling costs input."""
    errors: List[str] = []
    if mode is None:
        return True, [], {"mode": None, "amount_aed": None}

    if mode not in ("OTHER_SELLING_COSTS_AED", "NO_OTHER_SELLING_COSTS"):
        errors.append(f"Invalid other selling cost mode: {mode}")
        return False, errors, {}

    if mode == "NO_OTHER_SELLING_COSTS":
        return True, [], {"mode": "NO_OTHER_SELLING_COSTS", "amount_aed": 0.0}

    if mode == "OTHER_SELLING_COSTS_AED":
        if amount_aed is None:
            errors.append("OTHER_SELLING_COSTS_AED requires amount_aed value")
            return False, errors, {}
        if amount_aed < 0:
            errors.append(f"other selling costs must be >= 0, got {amount_aed}")
            return False, errors, {}
        return True, [], {"mode": "OTHER_SELLING_COSTS_AED", "amount_aed": float(amount_aed)}

    return False, ["Unknown other selling cost validation error"], {}
