"""
investor_api/rental_operating_costs/user_input_store.py

In-memory store for user-entered operating cost inputs.
NOT written to MASTER, Qdrant, Mollak, or any official data store.

V1.1: Keyed by (user_scope, property_id) to prevent cross-user leakage.
Each entry tracks: user_scope, property_id, vacancy, management, maintenance,
provenance, created_at, updated_at.

PERSISTENCE MODE: EPHEMERAL_USER_SESSION
  - Inputs exist only in process memory for the current session.
  - Inputs disappear on server restart.
  - UI must disclose: "Your operating-cost inputs are temporary and may
    not be available after the session ends."

If no user_scope is provided, defaults to "anonymous" (demo mode).
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import threading

_lock = threading.Lock()
# Key: (user_scope, property_id) → record dict
_store: Dict[Tuple[str, str], Dict[str, Any]] = {}

DEFAULT_USER_SCOPE = "anonymous"


def _make_key(user_scope: str, property_id: str) -> Tuple[str, str]:
    return (user_scope or DEFAULT_USER_SCOPE, str(property_id))


def save_user_input(
    property_id: str,
    user_scope: Optional[str] = None,
    vacancy: Optional[Dict[str, Any]] = None,
    management: Optional[Dict[str, Any]] = None,
    maintenance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Save user-entered operating cost inputs for a (user_scope, property_id).
    Returns the stored record with timestamps.
    """
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
        if vacancy is not None:
            record["vacancy"] = vacancy
        elif "vacancy" in existing:
            record["vacancy"] = existing["vacancy"]

        if management is not None:
            record["management"] = management
        elif "management" in existing:
            record["management"] = existing["management"]

        if maintenance is not None:
            record["maintenance"] = maintenance
        elif "maintenance" in existing:
            record["maintenance"] = existing["maintenance"]

        _store[key] = record
        return dict(record)


def get_user_input(property_id: str, user_scope: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get stored user inputs for a (user_scope, property_id), or None."""
    key = _make_key(user_scope, property_id)
    with _lock:
        rec = _store.get(key)
        return dict(rec) if rec else None


def clear_user_input(property_id: str, user_scope: Optional[str] = None) -> None:
    """Clear stored user inputs for a (user_scope, property_id) only."""
    key = _make_key(user_scope, property_id)
    with _lock:
        if key in _store:
            del _store[key]


def clear_all() -> None:
    """Clear all stored user inputs (for testing only)."""
    with _lock:
        _store.clear()


def get_store_size() -> int:
    """Return number of stored records (for diagnostics)."""
    with _lock:
        return len(_store)
