"""
investor_api/roi/roi_scenario_user_input_store.py

In-memory ephemeral store for ROI scenario user inputs.
NOT written to MASTER, Qdrant, Mollak, or any official data store.

V1.3: Keyed by (user_scope, property_id).

PERSISTENCE_MODE: EPHEMERAL_USER_SESSION
  - Inputs exist only in process memory for the current session.
  - Inputs disappear on server restart.
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import threading

_lock = threading.Lock()
_store: Dict[Tuple[str, str], Dict[str, Any]] = {}

DEFAULT_USER_SCOPE = "anonymous"


def _make_key(user_scope: str, property_id: str) -> Tuple[str, str]:
    return (user_scope or DEFAULT_USER_SCOPE, str(property_id))


def save_scenario_input(
    property_id: str,
    user_scope: Optional[str] = None,
    holding_period_months: Optional[float] = None,
    exit_value_mode: Optional[str] = None,
    exit_sale_price_aed: Optional[float] = None,
    annual_appreciation_rate_pct: Optional[float] = None,
    selling_broker_mode: Optional[str] = None,
    selling_broker_percent: Optional[float] = None,
    selling_broker_aed: Optional[float] = None,
    noc_mode: Optional[str] = None,
    noc_fee_aed: Optional[float] = None,
    other_selling_mode: Optional[str] = None,
    other_selling_costs_aed: Optional[float] = None,
) -> Dict[str, Any]:
    """Save ROI scenario user inputs for a (user_scope, property_id)."""
    ts = datetime.now(timezone.utc).isoformat()
    pid = str(property_id)
    scope = user_scope or DEFAULT_USER_SCOPE
    key = _make_key(scope, pid)

    with _lock:
        existing = _store.get(key, {})
        record = {
            "user_scope": scope,
            "property_id": pid,
            "created_at": existing.get("created_at", ts),
            "updated_at": ts,
        }

        fields = [
            "holding_period_months",
            "exit_value_mode", "exit_sale_price_aed", "annual_appreciation_rate_pct",
            "selling_broker_mode", "selling_broker_percent", "selling_broker_aed",
            "noc_mode", "noc_fee_aed",
            "other_selling_mode", "other_selling_costs_aed",
        ]
        for f in fields:
            val = locals().get(f)
            if val is not None:
                record[f] = val
            elif f in existing:
                record[f] = existing[f]

        _store[key] = record
        return dict(record)


def get_scenario_input(property_id: str, user_scope: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get stored scenario inputs, or None."""
    key = _make_key(user_scope, property_id)
    with _lock:
        rec = _store.get(key)
        return dict(rec) if rec else None


def clear_scenario_input(property_id: str, user_scope: Optional[str] = None) -> None:
    """Clear stored scenario inputs for a (user_scope, property_id) only."""
    key = _make_key(user_scope, property_id)
    with _lock:
        if key in _store:
            del _store[key]


def clear_all() -> None:
    """Clear all stored scenario inputs (for testing only)."""
    with _lock:
        _store.clear()


def get_store_size() -> int:
    """Return number of stored records (for diagnostics)."""
    with _lock:
        return len(_store)
