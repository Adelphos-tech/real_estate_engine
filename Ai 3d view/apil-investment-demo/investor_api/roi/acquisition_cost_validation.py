"""
investor_api/roi/acquisition_cost_validation.py

Validation rules for acquisition cost user inputs (V1.2).
Returns (is_valid, errors, validated_values).

DLD buyer share:
  - USE_STATUTORY_DEFAULT: uses 2% (official statutory default, user-confirmed)
  - CUSTOM_PERCENT: 0 <= pct <= 4
  - CUSTOM_AED: >= 0
  - Never silently charge seller share to buyer

Broker:
  - BROKER_PERCENT: percent >= 0
  - BROKER_FIXED_AED: amount >= 0
  - NO_BROKER_COST: explicit zero, requires user selection

Developer/admin:
  - USER_INPUT_AED: amount >= 0
  - NO_DEVELOPER_ADMIN_FEE: explicit zero

Trustee:
  - amount >= 0, no default
"""
from typing import Tuple, List, Dict, Any, Optional


def validate_dld_buyer_share(
    input_mode: Optional[str],
    custom_percent: Optional[float] = None,
    custom_aed: Optional[float] = None,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate DLD buyer share input.

    Modes:
      USE_STATUTORY_DEFAULT — uses 2% (official, user-confirmed)
      CUSTOM_PERCENT — user enters buyer share % (0-4)
      CUSTOM_AED — user enters fixed AED amount (>=0)
    """
    errors: List[str] = []

    if input_mode is None:
        return True, [], {"input_mode": None, "custom_percent": None, "custom_aed": None}

    if input_mode not in ("USE_STATUTORY_DEFAULT", "CUSTOM_PERCENT", "CUSTOM_AED"):
        errors.append(f"Invalid DLD input_mode: {input_mode}")
        return False, errors, {}

    if input_mode == "USE_STATUTORY_DEFAULT":
        return True, [], {
            "input_mode": "USE_STATUTORY_DEFAULT",
            "custom_percent": None,
            "custom_aed": None,
        }

    if input_mode == "CUSTOM_PERCENT":
        if custom_percent is None:
            errors.append("CUSTOM_PERCENT requires custom_percent value")
            return False, errors, {}
        if custom_percent < 0:
            errors.append(f"DLD buyer share must be >= 0, got {custom_percent}")
            return False, errors, {}
        if custom_percent > 4:
            errors.append(f"DLD buyer share cannot exceed 4% (total fee), got {custom_percent}")
            return False, errors, {}
        return True, [], {
            "input_mode": "CUSTOM_PERCENT",
            "custom_percent": float(custom_percent),
            "custom_aed": None,
        }

    if input_mode == "CUSTOM_AED":
        if custom_aed is None:
            errors.append("CUSTOM_AED requires custom_aed value")
            return False, errors, {}
        if custom_aed < 0:
            errors.append(f"DLD buyer custom AED must be >= 0, got {custom_aed}")
            return False, errors, {}
        return True, [], {
            "input_mode": "CUSTOM_AED",
            "custom_percent": None,
            "custom_aed": float(custom_aed),
        }

    return False, ["Unknown DLD validation error"], {}


def validate_trustee_fee(amount_aed: Optional[float]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate trustee office fee input.
    No default — never prefill AED 2000/4000.
    """
    errors: List[str] = []
    if amount_aed is None:
        return True, [], {"amount_aed": None}
    if amount_aed < 0:
        errors.append(f"trustee_fee must be >= 0, got {amount_aed}")
        return False, errors, {}
    return True, [], {"amount_aed": float(amount_aed)}


def validate_broker_purchase(
    mode: Optional[str],
    percent: Optional[float] = None,
    amount_aed: Optional[float] = None,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate broker purchase commission input.

    Modes:
      BROKER_PERCENT — percent of purchase price
      BROKER_FIXED_AED — fixed AED
      NO_BROKER_COST — explicit zero (user selects "no broker")
    """
    errors: List[str] = []

    if mode is None:
        return True, [], {"mode": None, "percent": None, "amount_aed": None}

    if mode not in ("BROKER_PERCENT", "BROKER_FIXED_AED", "NO_BROKER_COST"):
        errors.append(f"Invalid broker purchase mode: {mode}")
        return False, errors, {}

    if mode == "NO_BROKER_COST":
        return True, [], {"mode": "NO_BROKER_COST", "percent": None, "amount_aed": 0.0}

    if mode == "BROKER_PERCENT":
        if percent is None:
            errors.append("BROKER_PERCENT requires percent value")
            return False, errors, {}
        if percent < 0:
            errors.append(f"broker percent must be >= 0, got {percent}")
            return False, errors, {}
        if percent > 100:
            errors.append(f"broker percent must be <= 100, got {percent}")
            return False, errors, {}
        return True, [], {"mode": "BROKER_PERCENT", "percent": float(percent), "amount_aed": None}

    if mode == "BROKER_FIXED_AED":
        if amount_aed is None:
            errors.append("BROKER_FIXED_AED requires amount_aed value")
            return False, errors, {}
        if amount_aed < 0:
            errors.append(f"broker amount_aed must be >= 0, got {amount_aed}")
            return False, errors, {}
        return True, [], {"mode": "BROKER_FIXED_AED", "percent": None, "amount_aed": float(amount_aed)}

    return False, ["Unknown broker validation error"], {}


def validate_developer_admin(
    mode: Optional[str],
    amount_aed: Optional[float] = None,
) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate developer/admin fee input.

    Modes:
      USER_INPUT_AED — user enters amount
      NO_DEVELOPER_ADMIN_FEE — explicit zero
    """
    errors: List[str] = []

    if mode is None:
        return True, [], {"mode": None, "amount_aed": None}

    if mode not in ("USER_INPUT_AED", "NO_DEVELOPER_ADMIN_FEE"):
        errors.append(f"Invalid developer/admin mode: {mode}")
        return False, errors, {}

    if mode == "NO_DEVELOPER_ADMIN_FEE":
        return True, [], {"mode": "NO_DEVELOPER_ADMIN_FEE", "amount_aed": 0.0}

    if mode == "USER_INPUT_AED":
        if amount_aed is None:
            errors.append("USER_INPUT_AED requires amount_aed value")
            return False, errors, {}
        if amount_aed < 0:
            errors.append(f"developer_admin_fee must be >= 0, got {amount_aed}")
            return False, errors, {}
        return True, [], {"mode": "USER_INPUT_AED", "amount_aed": float(amount_aed)}

    return False, ["Unknown developer/admin validation error"], {}
