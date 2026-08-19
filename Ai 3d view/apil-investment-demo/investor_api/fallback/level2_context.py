"""
Level 2 Fallback Context — Runtime Module
=========================================
Exact project + same bedroom + ALL statuses (sales only).
Does NOT filter by Ready/Offplan status.
production_eligible = False by design.

Extracted from ui_benchmark_source_validation.py for clean runtime separation.
"""
import re
from collections import Counter
from datetime import datetime
from statistics import median
from typing import Any, Dict, List, Optional, Tuple

from investor_api.dld_benchmark_engine import _DLD_STORE

MIN_TRANSACTION_VALUE = 100_000


def _normalize(text: Optional[str]) -> str:
    if not text:
        return ""
    text = str(text).strip().lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_price(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_bedrooms(rooms_raw: Optional[str]) -> Optional[int]:
    if not rooms_raw:
        return None
    rooms_norm = _normalize(rooms_raw)
    if "studio" in rooms_norm:
        return 0
    if "b/r" in rooms_raw.lower() or "br" in rooms_norm:
        m = re.search(r"(\d+)", rooms_norm)
        if m:
            return int(m.group(1))
    return None


def _is_sale_transaction(row: Dict) -> Tuple[bool, str]:
    group = str(row.get("GROUP_EN", "")).strip().upper()
    procedure = str(row.get("PROCEDURE_EN", "")).strip().lower()
    if group == "SALES":
        return True, "SALE"
    if group in ("MORTGAGE", "GIFTS"):
        return False, "NON_SALE"
    if not group:
        sale_procedures = {
            "sale", "sell", "sell - pre registration", "delayed sell",
            "sell development", "lease to own registration",
        }
        if procedure in sale_procedures:
            return True, "SALE_INFERRED_FROM_PROCEDURE"
        non_sale = {
            "mortgage registration", "portfolio mortgage registration",
            "delayed mortgage", "modify mortgage", "portfolio mortgage modification",
            "grant", "grant pre-registration", "development registration pre-registration",
            "lease finance registration", "development mortgage",
        }
        if procedure in non_sale:
            return False, "NON_SALE_INFERRED_FROM_PROCEDURE"
    return False, "UNKNOWN"


def compute_level2_exact_project_status_broadened(
    project_name: str,
    subject_price: float,
    bedroom: Optional[int] = None,
    exact_project_only: bool = True,
) -> Dict[str, Any]:
    """
    Level 2 fallback: exact project + same bedroom + ALL statuses (sales only).
    Does NOT filter by Ready/Offplan status.
    production_eligible = False by design.
    """
    result = {
        "benchmark_median": None,
        "benchmark_mean": None,
        "transaction_count": 0,
        "matched_project": None,
        "match_method": None,
        "match_confidence": None,
        "bedroom_filter": bedroom,
        "status_filter": None,  # deliberately broadened
        "matched_transaction_ids": [],
        "transactions": [],
        "subject_price": subject_price,
        "price_difference_aed": None,
        "price_difference_percentage": None,
        "usable_for_investment": False,
        "insufficient_evidence_reason": None,
        "warnings": [],
        # ── Explicit calculation identity ──
        "benchmark_method": "DLD_FALLBACK",
        "benchmark_tier": "LEVEL_2",
        "is_fallback": True,
        "fallback_type": "EXACT_PROJECT_STATUS_BROADENED",
        "production_eligible": False,
        "validation_status": "VALIDATED_CONTEXT_ONLY",
        "calculation_version": "LEVEL2_EXACT_PROJECT_STATUS_BROADENED_V1",
        "evidence_level": None,
    }

    norm_project = _normalize(project_name)
    if not norm_project:
        result["insufficient_evidence_reason"] = "Empty project name"
        result["match_method"] = "no_match"
        result["match_confidence"] = "none"
        result["evidence_level"] = "NO_VERIFIED_EVIDENCE"
        return result

    raw_txs = _DLD_STORE.get_transactions(project_name)
    if not raw_txs:
        result["insufficient_evidence_reason"] = f"No DLD transactions found for project '{project_name}'"
        result["match_method"] = "no_match"
        result["match_confidence"] = "none"
        result["evidence_level"] = "NO_VERIFIED_EVIDENCE"
        return result

    # Sales-only filter (NO status filter)
    sales_txs = []
    for row in raw_txs:
        is_sale, _ = _is_sale_transaction(row)
        if is_sale:
            sales_txs.append(row)

    # Bedroom filter
    bedroom_filtered = []
    for row in sales_txs:
        rooms_raw = row.get("ROOMS_EN", "")
        parsed_br = _parse_bedrooms(rooms_raw)
        if bedroom is None:
            bedroom_filtered.append(row)
        elif parsed_br is not None and parsed_br == bedroom:
            bedroom_filtered.append(row)

    # Outlier removal
    final_txs = []
    for row in bedroom_filtered:
        price = _parse_price(row.get("TRANS_VALUE"))
        if price is not None and price >= MIN_TRANSACTION_VALUE:
            final_txs.append(row)

    if not final_txs:
        reason_parts = []
        if not bedroom_filtered:
            reason_parts.append(f"no transactions matching bedroom={bedroom}")
        else:
            reason_parts.append("all matching transactions were outliers")
        reason = "; ".join(reason_parts) if reason_parts else "unknown filter mismatch"
        result["insufficient_evidence_reason"] = (
            f"No usable DLD transactions for '{project_name}' ({reason})"
        )
        result["match_method"] = "project_exact"
        result["match_confidence"] = "none"
        result["matched_project"] = project_name
        if not bedroom_filtered and sales_txs:
            result["evidence_level"] = "NO_SAME_BEDROOM_EVIDENCE"
        else:
            result["evidence_level"] = "NO_VERIFIED_EVIDENCE"
        return result

    prices = [float(r["TRANS_VALUE"]) for r in final_txs]
    med = median(prices)
    mean_val = sum(prices) / len(prices)
    diff_aed = med - subject_price
    diff_pct = (diff_aed / subject_price) * 100 if subject_price else None

    tx_ids = []
    tx_provenance = []
    for row in final_txs:
        tx_ids.append(row.get("TRANSACTION_NUMBER", ""))
        tx_provenance.append({
            "transaction_id": row.get("TRANSACTION_NUMBER"),
            "date": str(row.get("INSTANCE_DATE", ""))[:10],
            "price_aed": float(row["TRANS_VALUE"]),
            "rooms": row.get("ROOMS_EN", ""),
            "procedure": row.get("PROCEDURE_EN", ""),
            "project": row.get("PROJECT_EN", ""),
            "area": row.get("AREA_EN", ""),
            "group_en": row.get("GROUP_EN", ""),
        })

    evidence_level = "EXACT_PROJECT_SAME_BEDROOM_STATUS_BROADENED"
    if bedroom is None:
        evidence_level = "PROJECT_LEVEL_EVIDENCE"

    usable = len(final_txs) >= 3

    result.update({
        "benchmark_median": med,
        "benchmark_mean": mean_val,
        "transaction_count": len(final_txs),
        "matched_project": project_name,
        "match_method": "project_exact",
        "match_confidence": "high" if len(final_txs) >= 10 else ("medium" if len(final_txs) >= 5 else "low"),
        "matched_transaction_ids": tx_ids,
        "transactions": tx_provenance,
        "price_difference_aed": diff_aed,
        "price_difference_percentage": diff_pct,
        "usable_for_investment": usable,
        "insufficient_evidence_reason": None,
        "evidence_level": evidence_level,
    })

    if len(final_txs) < 10:
        result["warnings"].append(f"Low sample size ({len(final_txs)} transactions)")
    if bedroom is None:
        result["warnings"].append("Bedroom filter not applied — benchmark is project-level, not unit-specific")
        result["match_confidence"] = "medium"

    return result
