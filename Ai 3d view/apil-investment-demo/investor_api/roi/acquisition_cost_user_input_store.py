"""
investor_api/roi/acquisition_cost_user_input_store.py

In-memory ephemeral store for acquisition cost user inputs.
NOT written to MASTER, Qdrant, Mollak, or any official data store.

V1.2: Keyed by (user_scope, property_id) to prevent cross-user leakage.

PERSISTENCE MODE: EPHEMERAL_USER_SESSION
  - Inputs exist only in process memory for the current session.
  - Inputs disappear on server restart.

If no user_scope is provided, defaults to "anonymous" (demo mode).
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import threading

_lock = threading.Lock()
_store: Dict[Tuple[str, str], Dict[str, Any]] = {}

DEFAULT_USER_SCOPE = "anonymous"


def _make_key(user_scope: str, property_id: str) -> Tuple[str, str]:
    return (user_scope or DEFAULT_USER_SCOPE, str(property_id))


def save_acquisition_input(
    property_id: str,
    user_scope: Optional[str] = None,
    dld_input_mode: Optional[str] = None,
    dld_custom_percent: Optional[float] = None,
    dld_custom_aed: Optional[float] = None,
    trustee_fee_aed: Optional[float] = None,
    broker_purchase_mode: Optional[str] = None,
    broker_purchase_percent: Optional[float] = None,
    broker_purchase_aed: Optional[float] = None,
    developer_admin_mode: Optional[str] = None,
    developer_admin_fee_aed: Optional[float] = None,
) -> Dict[str, Any]:
    """Save acquisition cost user inputs for a (user_scope, property_id)."""
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

        # Preserve existing fields not being updated
        fields = [
            "dld_input_mode", "dld_custom_percent", "dld_custom_aed",
            "trustee_fee_aed",
            "broker_purchase_mode", "broker_purchase_percent", "broker_purchase_aed",
            "developer_admin_mode", "developer_admin_fee_aed",
        ]
        for f in fields:
            val = locals().get(f)
            if val is not None:
                record[f] = val
            elif f in existing:
                record[f] = existing[f]

        _store[key] = record
        return dict(record)


def get_acquisition_input(property_id: str, user_scope: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get stored acquisition inputs for a (user_scope, property_id), or None."""
    key = _make_key(user_scope, property_id)
    with _lock:
        rec = _store.get(key)
        return dict(rec) if rec else None


def clear_acquisition_input(property_id: str, user_scope: Optional[str] = None) -> None:
    """Clear stored acquisition inputs for a (user_scope, property_id) only."""
    key = _make_key(user_scope, property_id)
    with _lock:
        if key in _store:
            del _store[key]


def clear_all() -> None:
    """Clear all stored acquisition inputs (for testing only)."""
    with _lock:
        _store.clear()


def get_store_size() -> int:
    """Return number of stored records (for diagnostics)."""
    with _lock:
        return len(_store)
