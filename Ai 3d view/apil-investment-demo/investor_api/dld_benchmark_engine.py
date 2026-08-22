"""
DLD Benchmark Engine — Defensive Benchmark Calculator
=======================================================
FROZEN METHODOLOGY — DLD_CANONICAL_UI_V1_FROZEN
DO NOT MODIFY WITHOUT EXPLICIT RE-APPROVAL
This engine powers the canonical DLD calculation for investor-facing benchmarks.
Any change requires: new version marker, full 2,614-property re-audit, regression re-verification.
=======================================================

Computes property benchmarks directly from DLD transaction data.
Rules (defensive — never assume where data conflicts):

1. PROJECT MATCHING
   - Normalize project names (strip, lower, collapse whitespace)
   - Require EXACT normalized match; fuzzy substitution is forbidden
   - If no exact match → return "insufficient_comparable_evidence"

2. BEDROOM MATCHING
   - Use the selected unit's bedroom count when known
   - If APIL/Qdrant conflict, prefer the specific unit record
   - If only a project-level range exists, mark benchmark as "project_level_range"

3. STATUS RESOLUTION
   - Preserve all source values (APIL, Qdrant, DLD)
   - Precedence: confirmed Qdrant > DLD majority > APIL classification
   - Return canonical status + provenance + confidence

4. OUTLIER REMOVAL
   - Remove transactions < AED 100,000 (likely deposits or partial payments)
   - Document every removal

5. PROVENANCE
   - Every benchmark must expose:
     matched_project, match_method, matched_transaction_ids,
     transaction_count, bedroom_filter, status_filter,
     benchmark_median, subject_price, price_difference_percentage
"""

import csv
import os
import re
from statistics import median
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MIN_TRANSACTION_VALUE = 100_000  # AED — filter out deposits / partial payments
DLD_CSV_PATH = os.environ.get(
    "DLD_CSV_PATH",
    "/Users/apple/Desktop/Ai 3d view/dxb_transactions_all.csv"
)

# Status canonical mapping
STATUS_ALIASES = {
    "ready": "Ready",
    "off-plan": "Offplan",
    "offplan": "Offplan",
    "off plan": "Offplan",
    "mixed": "Mixed",
    "pre-registration": "Offplan",
    "sell - pre registration": "Offplan",
    "sale": "Ready",
    "sell": "Ready",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(text: Optional[str]) -> str:
    """Strip, lower, collapse whitespace, remove punctuation except alphanumeric."""
    if not text:
        return ""
    text = str(text).strip().lower()
    text = re.sub(r"[^\w\s]", "", text)  # remove punctuation
    text = re.sub(r"\s+", " ", text)   # collapse whitespace
    return text.strip()


def _canonical_status(raw: Optional[str]) -> Tuple[str, str]:
    """Return (canonical_status, source_value)."""
    if not raw:
        return ("Unknown", "")
    key = _normalize(raw)
    for alias, canonical in STATUS_ALIASES.items():
        if alias in key or key == _normalize(alias):
            return (canonical, raw.strip())
    # Fallback: if it contains "off" treat as Offplan
    if "off" in key:
        return ("Offplan", raw.strip())
    if "ready" in key:
        return ("Ready", raw.strip())
    return ("Unknown", raw.strip())


def _dld_procedure_to_status(procedure: str) -> str:
    """Map DLD PROCEDURE_EN to canonical status."""
    p = _normalize(procedure)
    if "pre registration" in p or "pre-registration" in p:
        return "Offplan"
    if p == "sale" or p == "sell":
        return "Ready"
    return "Unknown"


def _parse_price(val: Any) -> Optional[float]:
    """Safely parse a transaction value."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _is_sale_transaction(row: Dict) -> Tuple[bool, str]:
    """
    Definitive sale classification.
    Returns (is_sale, classification).
    """
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


def _build_composite_transaction_key(row: Dict) -> str:
    """
    Stable transaction-row identity that handles duplicate IDs with different GROUP_EN.
    Never deduplicate Sales vs Mortgage rows simply because transaction IDs match.
    """
    parts = [
        str(row.get("TRANSACTION_NUMBER", "")),
        str(row.get("GROUP_EN", "")).strip().upper(),
        str(row.get("PROCEDURE_EN", "")).strip().lower(),
        str(row.get("INSTANCE_DATE", ""))[:10],
        _normalize(str(row.get("PROJECT_EN", ""))),
        str(_parse_price(row.get("TRANS_VALUE"))),
    ]
    return "|".join(parts)


# ---------------------------------------------------------------------------
# DLD Loader
# ---------------------------------------------------------------------------

class DLDTransactionStore:
    """In-memory index of DLD transactions keyed by normalized project name."""

    def __init__(self, csv_path: str = DLD_CSV_PATH):
        self.csv_path = csv_path
        self._projects: Dict[str, List[Dict]] = {}
        self._loaded = False
        self._load()

    def _load(self):
        if self._loaded:
            return
        if not os.path.exists(self.csv_path):
            print(f"[DLDStore] WARNING: DLD CSV not found at {self.csv_path}")
            self._loaded = True
            return

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                project_raw = row.get("PROJECT_EN", "")
                if not project_raw:
                    continue
                project_norm = _normalize(project_raw)
                if project_norm not in self._projects:
                    self._projects[project_norm] = []
                self._projects[project_norm].append(row)

        self._loaded = True
        print(f"[DLDStore] Loaded {sum(len(v) for v in self._projects.values())} transactions across {len(self._projects)} projects")

    def get_transactions(self, project_name: str) -> List[Dict]:
        """Return raw DLD transactions for an exact normalized project name."""
        return self._projects.get(_normalize(project_name), [])

    def list_projects(self) -> List[str]:
        return sorted(self._projects.keys())


# Global singleton (loaded once on import)
_DLD_STORE = DLDTransactionStore()


def reload_dld_store(csv_path: str = DLD_CSV_PATH) -> DLDTransactionStore:
    global _DLD_STORE
    _DLD_STORE = DLDTransactionStore(csv_path)
    return _DLD_STORE


# ---------------------------------------------------------------------------
# Benchmark Calculator
# ---------------------------------------------------------------------------

def compute_project_benchmark(
    project_name: str,
    subject_price: float,
    bedroom: Optional[int] = None,
    status: Optional[str] = None,
    exact_project_only: bool = True,
) -> Dict[str, Any]:
    """
    Compute a defensive benchmark for a property.

    Parameters
    ----------
    project_name : str
        The project name from APIL / Qdrant.
    subject_price : float
        The asking price of the subject property.
    bedroom : int | None
        Specific bedroom count to filter by. If None, all unit types are included
        and the result is marked as project-level/less precise.
    status : str | None
        Canonical status filter ("Ready" or "Offplan"). If None, uses all.
    exact_project_only : bool
        If True (default), only exact project matches are allowed.

    Returns
    -------
    dict with keys:
        - benchmark_median
        - benchmark_mean
        - transaction_count
        - matched_project
        - match_method
        - match_confidence
        - bedroom_filter
        - status_filter
        - matched_transaction_ids  (list of TRANSACTION_NUMBER)
        - transactions               (list of {id, date, price, rooms, procedure})
        - subject_price
        - price_difference_aed
        - price_difference_percentage
        - usable_for_investment
        - insufficient_evidence_reason
        - warnings
        - provenance
    """

    result = {
        "benchmark_median": None,
        "benchmark_mean": None,
        "transaction_count": 0,
        "matched_project": None,
        "match_method": None,
        "match_confidence": None,
        "bedroom_filter": bedroom,
        "status_filter": status,
        "matched_transaction_ids": [],
        "transactions": [],
        "subject_price": subject_price,
        "price_difference_aed": None,
        "price_difference_percentage": None,
        "usable_for_investment": False,
        "insufficient_evidence_reason": None,
        "warnings": [],
        # ── Explicit calculation identity (§25–36) ──
        "benchmark_method": "CANONICAL_DLD",
        "benchmark_tier": "LEVEL_1",
        "is_fallback": False,
        "fallback_type": None,
        "production_eligible": False,
        "validation_status": "VERIFIED_PRODUCTION",
        "calculation_version": "CANONICAL_DLD_SALES_ONLY_V1",
        "evidence_level": None,
        "provenance": {
            "dld_csv_path": _DLD_STORE.csv_path,
            "dld_records_total": 0,
            "filter_project": project_name,
            "filter_bedroom": bedroom,
            "filter_status": status,
            "outlier_threshold": MIN_TRANSACTION_VALUE,
        },
    }

    # -----------------------------------------------------------------
    # Helper: run full filter pipeline (status → bedroom → outlier)
    # -----------------------------------------------------------------
    def _run_pipeline(txs: List[Dict], status_filter: Optional[str]) -> Tuple[List[Dict], List[Dict]]:
        """Return (final_transactions, outlier_records)."""
        # status filter
        if status_filter is not None:
            status_filtered = [
                row for row in txs
                if _dld_procedure_to_status(row.get("PROCEDURE_EN", "")) == status_filter
            ]
        else:
            status_filtered = list(txs)

        # bedroom filter
        bedroom_filtered = []
        for row in status_filtered:
            rooms_raw = row.get("ROOMS_EN", "")
            rooms_norm = _normalize(rooms_raw)
            parsed_br = None
            if "studio" in rooms_norm:
                parsed_br = 0
            elif "b/r" in rooms_raw.lower() or "br" in rooms_norm:
                m = re.search(r"(\d+)", rooms_norm)
                if m:
                    parsed_br = int(m.group(1))

            if bedroom is None:
                bedroom_filtered.append(row)
            elif parsed_br is not None and parsed_br == bedroom:
                bedroom_filtered.append(row)

        # outlier removal
        final_txs = []
        removed = []
        for row in bedroom_filtered:
            price = _parse_price(row.get("TRANS_VALUE"))
            if price is None:
                continue
            if price >= MIN_TRANSACTION_VALUE:
                final_txs.append(row)
            else:
                removed.append({
                    "id": row.get("TRANSACTION_NUMBER"),
                    "price": price,
                    "reason": f"Below outlier threshold AED {MIN_TRANSACTION_VALUE:,}",
                })
        return final_txs, removed, status_filtered, bedroom_filtered

    # -----------------------------------------------------------------
    # Helper: fuzzy project search
    # -----------------------------------------------------------------
    def _find_fuzzy_match(project_name: str, original_txs: List[Dict]) -> Optional[str]:
        """If exact project has no transactions after filtering, find best fuzzy match."""
        if original_txs:
            # Project exists but filtering removed all — keep exact project
            return None
        # Project not found at all — search for similar names
        norm_target = _normalize(project_name)
        if not norm_target:
            return None
        best_project = None
        best_score = 0
        for candidate in _DLD_STORE.list_projects():
            # Simple containment scoring
            if norm_target in candidate or candidate in norm_target:
                score = len(set(norm_target.split()) & set(candidate.split()))
                if score > best_score:
                    best_score = score
                    best_project = candidate
        return best_project

    # Step 1: exact project match
    norm_project = _normalize(project_name)
    if not norm_project:
        result["insufficient_evidence_reason"] = "Empty project name"
        result["match_method"] = "no_match"
        result["match_confidence"] = "none"
        return result

    raw_txs = _DLD_STORE.get_transactions(project_name)
    result["provenance"]["dld_records_total"] = len(raw_txs)

    fuzzy_used = False
    fuzzy_matched_project = None

    if not raw_txs:
        # Try fuzzy match
        fuzzy_matched_project = _find_fuzzy_match(project_name, raw_txs)
        if fuzzy_matched_project and not exact_project_only:
            raw_txs = _DLD_STORE.get_transactions(fuzzy_matched_project)
            result["provenance"]["dld_records_total"] = len(raw_txs)
            fuzzy_used = True
            result["warnings"].append(
                f"Exact project '{project_name}' not found in DLD. Using fuzzy match '{fuzzy_matched_project}'."
            )
        else:
            result["insufficient_evidence_reason"] = f"No DLD transactions found for project '{project_name}'"
            result["match_method"] = "no_match"
            result["match_confidence"] = "none"
            return result

    # =====================================================================
    # SALES-ONLY FILTER (production migration — validated in Phase 6)
    # =====================================================================
    sales_only_txs = []
    removed_non_sale = []
    seen_composite_keys = set()
    duplicate_identical_sale_rows = 0

    for row in raw_txs:
        is_sale, classification = _is_sale_transaction(row)
        if not is_sale:
            removed_non_sale.append({
                "id": row.get("TRANSACTION_NUMBER"),
                "group_en": row.get("GROUP_EN", ""),
                "procedure_en": row.get("PROCEDURE_EN", ""),
                "reason": classification,
            })
            continue

        # Deduplicate truly identical sale observations using composite key
        key = _build_composite_transaction_key(row)
        if key in seen_composite_keys:
            duplicate_identical_sale_rows += 1
            continue
        seen_composite_keys.add(key)
        sales_only_txs.append(row)

    if removed_non_sale:
        result["warnings"].append(
            f"Removed {len(removed_non_sale)} non-sale transaction(s) from benchmark cohort"
        )
    if duplicate_identical_sale_rows:
        result["warnings"].append(
            f"Removed {duplicate_identical_sale_rows} duplicate identical sale row(s)"
        )

    # Replace raw_txs with sales-only deduplicated set for pipeline
    pipeline_txs = sales_only_txs

    # Step 2: run pipeline with requested status
    final_txs, removed_outliers, status_filtered, bedroom_filtered = _run_pipeline(pipeline_txs, status)

    # Step 3: fallback if status produced 0 final results but project has data
    if not final_txs and status is not None:
        # Retry with no status filter (still sales-only)
        final_txs, removed_outliers, _, _ = _run_pipeline(pipeline_txs, None)
        result["warnings"].append(
            f"Status filter '{status}' produced 0 usable transactions after bedroom/outlier filtering. "
            f"Falling back to all transaction types for project '{project_name}'."
        )
        result["status_filter"] = None  # record that we dropped the filter

    if removed_outliers:
        result["warnings"].append(
            f"Removed {len(removed_outliers)} outlier transaction(s) below AED {MIN_TRANSACTION_VALUE:,}"
        )

    if not final_txs:
        reason_parts = []
        if not status_filtered and status is not None:
            reason_parts.append(f"no transactions matching status '{status}'")
        if not bedroom_filtered:
            reason_parts.append(f"no transactions matching bedroom={bedroom}")
        if removed_outliers and not final_txs:
            reason_parts.append("all matching transactions were outliers")
        reason = "; ".join(reason_parts) if reason_parts else "unknown filter mismatch"
        result["insufficient_evidence_reason"] = (
            f"No usable DLD transactions for '{project_name}' ({reason})"
        )
        result["match_method"] = "project_exact" if not fuzzy_used else "project_fuzzy"
        result["match_confidence"] = "none"
        result["matched_project"] = fuzzy_matched_project if fuzzy_used else project_name

        # Determine evidence level for zero-transaction result
        if fuzzy_used:
            result["evidence_level"] = "PROJECT_LEVEL_EVIDENCE"
        elif not bedroom_filtered and pipeline_txs:
            result["evidence_level"] = "NO_SAME_BEDROOM_EVIDENCE"
        elif not pipeline_txs:
            result["evidence_level"] = "NO_VERIFIED_EVIDENCE"
        else:
            result["evidence_level"] = "NO_VERIFIED_EVIDENCE"
        result["provenance"]["sales_only"] = True
        result["provenance"]["calculation_version"] = "CANONICAL_DLD_SALES_ONLY_V1"
        result["provenance"]["non_sale_removed_count"] = len(removed_non_sale)
        result["provenance"]["duplicate_identical_sale_rows_removed"] = duplicate_identical_sale_rows
        result["non_sale_removed"] = removed_non_sale
        result["duplicate_identical_sale_rows_removed"] = duplicate_identical_sale_rows
        result["production_eligible"] = False  # insufficient evidence
        return result

    # Step 4: compute statistics
    prices = [float(r["TRANS_VALUE"]) for r in final_txs]
    prices_sorted = sorted(prices)
    med = median(prices)
    mean_val = sum(prices) / len(prices)

    # Step 6: compute price advantage
    diff_aed = med - subject_price
    diff_pct = (diff_aed / subject_price) * 100 if subject_price else None

    # Step 7: build provenance transaction list
    tx_provenance = []
    tx_ids = []
    for row in final_txs:
        tx_ids.append(row.get("TRANSACTION_NUMBER", ""))
        tx_provenance.append({
            "transaction_id": row.get("TRANSACTION_NUMBER"),
            "date": row.get("INSTANCE_DATE", "")[:10],
            "price_aed": float(row["TRANS_VALUE"]),
            "rooms": row.get("ROOMS_EN", ""),
            "procedure": row.get("PROCEDURE_EN", ""),
            "group_en": row.get("GROUP_EN", ""),
            "project": row.get("PROJECT_EN", ""),
            "area": row.get("AREA_EN", ""),
        })

    # Determine evidence level
    evidence_level = "EXACT_PROJECT_SAME_BEDROOM_EVIDENCE"
    if fuzzy_used:
        evidence_level = "PROJECT_LEVEL_EVIDENCE"
    elif bedroom is None:
        evidence_level = "PROJECT_LEVEL_EVIDENCE"
    elif not pipeline_txs:
        evidence_level = "NO_VERIFIED_EVIDENCE"

    usable = len(final_txs) >= 3  # require at least 3 tx for reliability
    result.update({
        "benchmark_median": med,
        "benchmark_mean": mean_val,
        "transaction_count": len(final_txs),
        "matched_project": fuzzy_matched_project if fuzzy_used else project_name,
        "match_method": "project_exact" if not fuzzy_used else "project_fuzzy",
        "match_confidence": "high" if len(final_txs) >= 10 else ("medium" if len(final_txs) >= 5 else "low"),
        "matched_transaction_ids": tx_ids,
        "transactions": tx_provenance,
        "price_difference_aed": diff_aed,
        "price_difference_percentage": diff_pct,
        "usable_for_investment": usable,
        "insufficient_evidence_reason": None,
        "evidence_level": evidence_level,
        "calculation_version": "CANONICAL_DLD_SALES_ONLY_V1",
        "non_sale_removed": removed_non_sale,
        "duplicate_identical_sale_rows_removed": duplicate_identical_sale_rows,
        # ── Explicit calculation identity (§25–36) ──
        "production_eligible": usable,
    })

    # Update provenance with sales-only metadata
    result["provenance"]["sales_only"] = True
    result["provenance"]["calculation_version"] = "CANONICAL_DLD_SALES_ONLY_V1"
    result["provenance"]["non_sale_removed_count"] = len(removed_non_sale)
    result["provenance"]["duplicate_identical_sale_rows_removed"] = duplicate_identical_sale_rows

    if len(final_txs) < 10:
        result["warnings"].append(f"Low sample size ({len(final_txs)} transactions)")

    if bedroom is None:
        result["warnings"].append("Bedroom filter not applied — benchmark is project-level, not unit-specific")
        result["match_confidence"] = "medium"  # downgrade because it's project-level

    if fuzzy_used:
        result["warnings"].append(f"Fuzzy project match used: '{fuzzy_matched_project}' instead of '{project_name}'")

    return result


# ---------------------------------------------------------------------------
# Status Resolver
# ---------------------------------------------------------------------------

def resolve_canonical_status(
    apil_status: Optional[str] = None,
    qdrant_status: Optional[str] = None,
    dld_statuses: Optional[List[str]] = None,
    enrichment_confirmed: bool = False,
) -> Dict[str, Any]:
    """
    Resolve a single canonical status from multiple sources.

    Precedence (when enrichment_confirmed is True):
        1. Qdrant (confirmed enrichment)
        2. DLD majority (if available)
        3. APIL classification

    Precedence (when enrichment_confirmed is False):
        1. DLD majority (if available)
        2. APIL classification
        3. Qdrant (unconfirmed)

    Returns dict with:
        - canonical_status
        - source_precedence
        - confidence
        - source_values  {apil, qdrant, dld_majority}
        - conflict_detected
        - conflict_details
    """
    sources = {
        "apil": _canonical_status(apil_status),
        "qdrant": _canonical_status(qdrant_status),
        "dld_majority": (None, None),
    }

    # Compute DLD majority
    if dld_statuses:
        canon_counts = {}
        for s in dld_statuses:
            c = _canonical_status(s)[0]
            canon_counts[c] = canon_counts.get(c, 0) + 1
        if canon_counts:
            dld_majority = max(canon_counts, key=canon_counts.get)
            sources["dld_majority"] = (dld_majority, f"majority of {len(dld_statuses)} DLD transactions")

    # Determine precedence
    if enrichment_confirmed:
        precedence = ["qdrant", "dld_majority", "apil"]
    else:
        precedence = ["dld_majority", "apil", "qdrant"]

    chosen = None
    chosen_source = None
    for src in precedence:
        val, raw = sources[src]
        if val and val != "Unknown":
            chosen = val
            chosen_source = src
            break

    if chosen is None:
        chosen = "Unknown"
        chosen_source = "none"

    # Detect conflicts
    unique_values = set()
    for src, (val, _) in sources.items():
        if val and val != "Unknown":
            unique_values.add(val)
    conflict_detected = len(unique_values) > 1

    conflict_details = []
    if conflict_detected:
        for src, (val, raw) in sources.items():
            if val and val != "Unknown":
                conflict_details.append(f"{src}='{raw}' -> {val}")

    confidence = "high"
    if conflict_detected:
        confidence = "medium"
    if chosen_source == "none":
        confidence = "none"
    elif chosen_source == "qdrant" and enrichment_confirmed:
        confidence = "high"
    elif chosen_source == "dld_majority":
        confidence = "high" if len(dld_statuses) >= 10 else "medium"

    return {
        "canonical_status": chosen,
        "source_precedence": precedence,
        "chosen_source": chosen_source,
        "confidence": confidence,
        "source_values": {
            "apil": {"raw": apil_status, "canonical": sources["apil"][0]},
            "qdrant": {"raw": qdrant_status, "canonical": sources["qdrant"][0]},
            "dld_majority": {"raw": sources["dld_majority"][1], "canonical": sources["dld_majority"][0]},
        },
        "conflict_detected": conflict_detected,
        "conflict_details": conflict_details,
    }


# ---------------------------------------------------------------------------
# Validation Helpers
# ---------------------------------------------------------------------------

def validate_step5_benchmark(
    property_record: Dict[str, Any],
    dld_store: Optional[DLDTransactionStore] = None,
) -> Dict[str, Any]:
    """
    Validate a STEP_5 benchmark against live DLD data.
    Returns a validation report with old vs new values.
    """
    if dld_store is None:
        dld_store = _DLD_STORE

    prop = property_record.get("property", {})
    project_name = prop.get("name", "")
    subject_price = prop.get("current_price_aed", 0)

    # Determine bedroom from enrichment if available
    bedroom = None
    enrichment = property_record.get("enrichment", {})
    if enrichment.get("enrichment_status") == "CONFIRMED":
        attrs = enrichment.get("property_attributes", {})
        bedroom = attrs.get("bedrooms")

    # Determine status
    apil_status = property_record.get("apil_attributes", {}).get("attributes", {}).get("status")
    qdrant_status = enrichment.get("property_attributes", {}).get("status") if enrichment else None
    status = None
    if qdrant_status:
        status = _canonical_status(qdrant_status)[0]
    elif apil_status:
        status = _canonical_status(apil_status)[0]

    # Compute live benchmark
    live = compute_project_benchmark(
        project_name=project_name,
        subject_price=subject_price,
        bedroom=bedroom,
        status=status,
    )

    # Compare with STEP_5
    step5_bench = property_record.get("benchmarks", [{}])[0]
    step5_median = step5_bench.get("median_price_aed")
    step5_count = step5_bench.get("transaction_count")
    step5_match = step5_bench.get("match_level")

    report = {
        "property_id": prop.get("id"),
        "project_name": project_name,
        "old_benchmark": {
            "median": step5_median,
            "count": step5_count,
            "match_level": step5_match,
        },
        "new_benchmark": {
            "median": live.get("benchmark_median"),
            "count": live.get("transaction_count"),
            "match_level": live.get("match_method"),
            "matched_project": live.get("matched_project"),
            "bedroom_filter": live.get("bedroom_filter"),
            "status_filter": live.get("status_filter"),
            "transaction_ids": live.get("matched_transaction_ids"),
            "price_difference_percentage": live.get("price_difference_percentage"),
        },
        "median_discrepancy": None,
        "count_discrepancy": None,
        "match_level_changed": False,
        "recommendation": "keep_old",
    }

    if step5_median is not None and live.get("benchmark_median") is not None:
        report["median_discrepancy"] = live["benchmark_median"] - step5_median
    if step5_count is not None and live.get("transaction_count") is not None:
        report["count_discrepancy"] = live["transaction_count"] - step5_count
    if step5_match != live.get("match_method"):
        report["match_level_changed"] = True

    # Recommendation logic
    if live.get("insufficient_evidence_reason"):
        report["recommendation"] = "replace_with_insufficient_evidence"
    elif report.get("median_discrepancy") and abs(report["median_discrepancy"]) > 50000:
        report["recommendation"] = "review_median_discrepancy"
    elif report.get("match_level_changed"):
        report["recommendation"] = "review_match_method"
    else:
        report["recommendation"] = "keep_old"

    return report
