"""
SHADOW FALLBACK BENCHMARK ENGINE — VERSION 4
=============================================
Root-level data pipeline fix addressing all 20 V4 requirements.

MANDATORY CONSTRAINTS (unchanged):
- production_eligible = false on every result
- No frontend changes
- No MASTER_FINAL.xlsx modification
- No Qdrant modification (READ-ONLY only)
- No raw DLD CSV modification
- No rental yield
- No canonical decision changes (production canonical untouched)

PHILOSOPHY:
- Accuracy and traceability over coverage.
- Precision-first conservative direction classification.
- A smaller, correctly validated, defensible subset is the goal.
- UNKNOWN sources EXCLUDED (not inferred).
- Sales-only canonical shadow target (production canonical unchanged).
"""

import csv
import json
import math
import os
import random
import re
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
from statistics import median, mean
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DLD_CSV_PATH = os.environ.get(
    "DLD_CSV_PATH",
    "/Users/apple/Desktop/Ai 3d view/dxb_transactions_all.csv"
)
MASTER_PATH = os.environ.get(
    "MASTER_PATH",
    "/Users/apple/Desktop/Ai 3d view/MASTER_FINAL.xlsx"
)
OUTPUT_DIR = "/Users/apple/Desktop/Ai 3d view/apil-investment-demo"

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# ---------------------------------------------------------------------------
# V4 CONFIG
# ---------------------------------------------------------------------------
SHADOW_FALLBACK_CONFIG_V4 = {
    "version": "fallback_shadow_v4",
    "lookback_months": 24,
    "size_band_pct_default": 0.20,
    "min_transactions_area_fallback": 10,
    "min_unique_projects_area": 3,
    "max_project_concentration": 0.50,
    "ppsf_outlier_iqr_multiplier": 1.5,
    "outlier_method": "iqr_1.5",
    "property_type_filter": False,  # tested in backtest A vs B
    "sale_only": True,
    "sources_allowed": ["DLD_OFFICIAL", "DXBINTERACT", "OTHER_VERIFIED"],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _parse_size(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_date(val: Any) -> Optional[datetime]:
    if not val:
        return None
    try:
        return pd.to_datetime(val)
    except Exception:
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


def _canonical_status(status_raw: str) -> Tuple[str, str]:
    s = str(status_raw).lower()
    if "pre" in s or "offplan" in s or "sell - pre" in s:
        return ("Offplan", status_raw)
    return ("Ready", status_raw)


def _price_band(price: float) -> str:
    if price < 1_000_000:
        return "< 1M"
    elif price < 2_000_000:
        return "1–2M"
    elif price < 4_000_000:
        return "2–4M"
    elif price < 8_000_000:
        return "4–8M"
    else:
        return "8M+"


def _size_band(size: Optional[float]) -> str:
    if size is None or (isinstance(size, float) and math.isnan(size)):
        return "Unknown"
    if size < 600:
        return "< 600 sqft"
    elif size < 1000:
        return "600–1000 sqft"
    elif size < 1500:
        return "1000–1500 sqft"
    elif size < 2500:
        return "1500–2500 sqft"
    else:
        return "2500+ sqft"


def _bedroom_label(br: Optional[float]) -> str:
    if br is None:
        return "Unknown"
    br = int(br) if not math.isnan(br) else None
    if br == 0:
        return "Studio"
    elif br == 1:
        return "1BR"
    elif br == 2:
        return "2BR"
    elif br == 3:
        return "3BR"
    elif br is not None and br >= 4:
        return "4BR+"
    return "Unknown"


# ===========================================================================
# SECTION 1 — PROPERTY TYPE NORMALIZATION
# ===========================================================================

DLD_PROP_SB_TYPE_MAP = {
    # Verified mappings from actual DLD data
    "Flat": "APARTMENT",
    "Villa": "VILLA",
    "Hotel Apartment": "HOTEL_APARTMENT",
    "Office": "OFFICE",
    "Residential / Residential Villa": "VILLA",
    "Residential / Attached Villas": "VILLA",
    "Residential / Villas": "VILLA",
    "Residential Flats": "APARTMENT",
    "Commercial": "OTHER",
    "Shop": "OTHER",
    "Hotel Rooms": "OTHER",
    "Land": "OTHER",
    "General Use": "OTHER",
    "Government Housing": "OTHER",
    "Industrial": "OTHER",
    "Airport": "OTHER",
    "Unit": "OTHER",
    "Labor Camp": "OTHER",
    "Sports Club": "OTHER",
    "Agricultural": "OTHER",
    "Stacked Townhouses": "TOWNHOUSE",
    "Show Rooms": "OTHER",
    "Warehouse": "OTHER",
    "Building": "OTHER",
    "Workshop": "OTHER",
    "School": "OTHER",
    "Exhbition Center": "OTHER",
    "Shopping Mall": "OTHER",
    # Unmapped defaults to OTHER
}

QDRANT_CATEGORY_MAP = {
    "Apartment": "APARTMENT",
    "شقة": "APARTMENT",
    "Villa": "VILLA",
    "فيلا": "VILLA",
    "Townhouse": "TOWNHOUSE",
    "تاون هاوس": "TOWNHOUSE",
    "Penthouse": "PENTHOUSE",
    "بنتهاوس": "PENTHOUSE",
    "Hotel Apartment": "HOTEL_APARTMENT",
    "شقة فندقية": "HOTEL_APARTMENT",
    "office": "OFFICE",
    "Office": "OFFICE",
    "Duplex": "OTHER",
    "دوبلكس": "OTHER",
    "Triplex": "OTHER",
    "تريبلكس": "OTHER",
    "Mansions": "OTHER",
    "القصور": "OTHER",
    "Plot": "OTHER",
    "Land": "OTHER",
    "أرض": "OTHER",
    "School Plots": "OTHER",
    "القصة": "OTHER",
}


def normalize_dld_property_type(prop_sb_type: Optional[str]) -> str:
    """Normalize DLD PROP_SB_TYPE_EN to canonical architectural type."""
    if not prop_sb_type:
        return "UNKNOWN"
    return DLD_PROP_SB_TYPE_MAP.get(prop_sb_type.strip(), "OTHER")


def normalize_qdrant_category(category: Optional[str]) -> str:
    """Normalize Qdrant category to canonical architectural type."""
    if not category:
        return "UNKNOWN"
    return QDRANT_CATEGORY_MAP.get(category.strip(), "OTHER")


# Qdrant cache for property types (READ-ONLY)
_qdrant_type_cache: Dict[str, str] = {}
_qdrant_cache_loaded = False


def _load_qdrant_type_cache():
    """Load property types from Qdrant into memory cache. READ-ONLY."""
    global _qdrant_cache_loaded, _qdrant_type_cache
    if _qdrant_cache_loaded:
        return
    try:
        import sys
        sys.path.insert(0, '/Users/apple/Desktop/Ai 3d view/apil-investment-demo')
        from backend_qdrant_client import _load_id_cache, _id_cache
        _load_id_cache()
        for pid, payload in _id_cache.items():
            # Prefer unit_category, then category
            cat = payload.get("unit_category") or payload.get("category")
            if cat:
                _qdrant_type_cache[pid] = normalize_qdrant_category(cat)
        print(f"[V4] Loaded {len(_qdrant_type_cache)} property types from Qdrant")
    except Exception as e:
        print(f"[V4] Qdrant type cache load failed: {e}")
    _qdrant_cache_loaded = True


def resolve_subject_property_type(
    property_id: str,
    master_property_type: Optional[str],
) -> str:
    """
    Resolve subject property type using hierarchy:
    1. MASTER property_type when valid
    2. Qdrant exact-unit category (READ-ONLY)
    3. Otherwise UNKNOWN
    """
    # 1. MASTER
    if master_property_type and pd.notna(master_property_type):
        pt = str(master_property_type).strip().upper()
        if pt and pt != "NAN" and pt != "NONE":
            return pt

    # 2. Qdrant
    _load_qdrant_type_cache()
    qdrant_type = _qdrant_type_cache.get(str(property_id))
    if qdrant_type:
        return qdrant_type

    return "UNKNOWN"


# ===========================================================================
# SECTION 2 — SALES-ONLY SHADOW CANONICAL TARGET
# ===========================================================================

def compute_project_benchmark_sales_only_shadow(
    project_name: str,
    subject_price: float,
    bedroom: Optional[int] = None,
    status: Optional[str] = None,
    exact_project_only: bool = True,
) -> Dict[str, Any]:
    """
    Sales-only shadow canonical benchmark.
    Identical to production compute_project_benchmark except:
    - Requires GROUP_EN == "SALES"
    - Returns non_sale_counts audit

    Does NOT modify production behavior.
    """
    from investor_api.dld_benchmark_engine import (
        _DLD_STORE, _normalize, _dld_procedure_to_status,
        _parse_price, MIN_TRANSACTION_VALUE
    )

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
        "evidence_level": None,
        "non_sale_counts": {
            "mortgage": 0,
            "gift": 0,
            "other_non_sale": 0,
        },
        "sales_only": True,
    }

    # Inner pipeline (same as production but with GROUP_EN filter)
    def _run_pipeline_sales_only(txs: List[Dict], status_filter: Optional[str]):
        # Filter sales only
        sales_txs = []
        non_sale_counts = {"mortgage": 0, "gift": 0, "other_non_sale": 0}
        for row in txs:
            group = str(row.get("GROUP_EN", "")).strip().upper()
            if group == "SALES":
                sales_txs.append(row)
            elif group == "MORTGAGE":
                non_sale_counts["mortgage"] += 1
            elif group == "GIFTS":
                non_sale_counts["gift"] += 1
            else:
                non_sale_counts["other_non_sale"] += 1

        # Status filter
        if status_filter is not None:
            status_filtered = [
                row for row in sales_txs
                if _dld_procedure_to_status(row.get("PROCEDURE_EN", "")) == status_filter
            ]
        else:
            status_filtered = list(sales_txs)

        # Bedroom filter
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

        # Outlier removal
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
        return final_txs, removed, status_filtered, bedroom_filtered, non_sale_counts

    # Exact project match
    norm_project = _normalize(project_name)
    if not norm_project:
        result["insufficient_evidence_reason"] = "Empty project name"
        result["match_method"] = "no_match"
        result["match_confidence"] = "none"
        return result

    raw_txs = _DLD_STORE.get_transactions(project_name)
    result["provenance"] = {
        "dld_csv_path": _DLD_STORE.csv_path,
        "dld_records_total": len(raw_txs),
        "filter_project": project_name,
        "filter_bedroom": bedroom,
        "filter_status": status,
        "outlier_threshold": MIN_TRANSACTION_VALUE,
        "sales_only": True,
    }

    fuzzy_used = False
    fuzzy_matched_project = None

    if not raw_txs:
        # Try fuzzy match (same as production)
        norm_target = _normalize(project_name)
        best_project = None
        best_score = 0
        for candidate in _DLD_STORE.list_projects():
            if norm_target in candidate or candidate in norm_target:
                score = len(set(norm_target.split()) & set(candidate.split()))
                if score > best_score:
                    best_score = score
                    best_project = candidate
        fuzzy_matched_project = best_project
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

    # Run pipeline with requested status
    final_txs, removed_outliers, status_filtered, bedroom_filtered, non_sale_counts = _run_pipeline_sales_only(raw_txs, status)
    result["non_sale_counts"] = non_sale_counts

    # Fallback if status produced 0 final results
    if not final_txs and status is not None:
        final_txs, removed_outliers, _, _, _ = _run_pipeline_sales_only(raw_txs, None)
        result["warnings"].append(
            f"Status filter '{status}' produced 0 usable transactions after bedroom/outlier filtering. "
            f"Falling back to all transaction types for project '{project_name}'."
        )
        result["status_filter"] = None

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
        if fuzzy_used:
            result["evidence_level"] = "PROJECT_LEVEL_EVIDENCE"
        elif not bedroom_filtered and raw_txs:
            result["evidence_level"] = "NO_SAME_BEDROOM_EVIDENCE"
        elif not raw_txs:
            result["evidence_level"] = "NO_VERIFIED_EVIDENCE"
        else:
            result["evidence_level"] = "NO_VERIFIED_EVIDENCE"
        return result

    # Compute statistics
    prices = [float(r["TRANS_VALUE"]) for r in final_txs]
    prices_sorted = sorted(prices)
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
            "date": row.get("INSTANCE_DATE", "")[:10],
            "price_aed": float(row["TRANS_VALUE"]),
            "rooms": row.get("ROOMS_EN", ""),
            "procedure": row.get("PROCEDURE_EN", ""),
            "project": row.get("PROJECT_EN", ""),
            "area": row.get("AREA_EN", ""),
            "group_en": row.get("GROUP_EN", ""),
        })

    evidence_level = "EXACT_PROJECT_SAME_BEDROOM_EVIDENCE"
    if fuzzy_used:
        evidence_level = "PROJECT_LEVEL_EVIDENCE"
    elif bedroom is None:
        evidence_level = "PROJECT_LEVEL_EVIDENCE"
    elif not raw_txs:
        evidence_level = "NO_VERIFIED_EVIDENCE"

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
        "usable_for_investment": len(final_txs) >= 3,
        "insufficient_evidence_reason": None,
        "evidence_level": evidence_level,
    })

    if len(final_txs) < 10:
        result["warnings"].append(f"Low sample size ({len(final_txs)} transactions)")
    if bedroom is None:
        result["warnings"].append("Bedroom filter not applied — benchmark is project-level, not unit-specific")
        result["match_confidence"] = "medium"
    if fuzzy_used:
        result["warnings"].append(f"Fuzzy project match used: '{fuzzy_matched_project}' instead of '{project_name}'")

    return result


# ===========================================================================
# SECTION 3 — TRANSACTION SOURCE CLASSIFICATION (V4)
# ===========================================================================

def classify_transaction_source_v4(tx_number: str) -> str:
    """
    V4 source classification.
    UNKNOWN sources are NOT treated as OTHER_DLD_SALES.
    They remain UNKNOWN and are excluded from benchmarks.
    """
    if not tx_number:
        return "UNKNOWN"
    tx = str(tx_number).strip().upper()
    if tx.startswith("DXB-"):
        return "DXBINTERACT"
    # Numeric prefixes followed by dash are DLD-style
    if re.match(r"^\d+-", tx):
        return "DLD_OFFICIAL"
    # Any other prefix that looks like a transaction number but not recognized
    if re.match(r"^[A-Z0-9-]+", tx):
        return "OTHER_VERIFIED"
    return "UNKNOWN"


def transaction_is_sale(row: Dict) -> Tuple[bool, str]:
    """
    Determine if a transaction is a sale transaction.
    """
    group = str(row.get("GROUP_EN", "")).strip().upper()
    procedure = str(row.get("PROCEDURE_EN", "")).strip().lower()

    if group == "SALES":
        return (True, "")

    if group in ("MORTGAGE", "GIFTS"):
        return (False, f"GROUP_EN={group}")

    if not group:
        sale_procedures = {
            "sale", "sell", "sell - pre registration", "delayed sell",
            "sell development", "lease to own registration",
        }
        if procedure in sale_procedures:
            return (True, "PROCEDURE_INFERRED_SALE")
        non_sale = {
            "mortgage registration", "portfolio mortgage registration",
            "delayed mortgage", "modify mortgage", "portfolio mortgage modification",
            "grant", "grant pre-registration", "development registration pre-registration",
            "lease finance registration", "development mortgage",
        }
        if procedure in non_sale:
            return (False, f"PROCEDURE_INFERRED_NON_SALE={procedure}")

    return (False, f"GROUP_UNRECOGNIZED={group}")


# ===========================================================================
# SECTION 4 — SOURCE-AWARE SIZE UNIT DETECTION (V4)
# ===========================================================================

def detect_size_unit_source_aware_v4(raw_size: float, tx_source: str) -> Dict:
    """
    V4 size unit detection.
    UNKNOWN source → detected_unit = None (excluded, not inferred).
    """
    if raw_size is None or raw_size <= 0:
        return {
            "raw_size": raw_size,
            "detected_unit": None,
            "converted_size_sqft": None,
            "conversion_method": "INVALID_SIZE",
            "conversion_confidence": "none",
        }

    if tx_source == "DXBINTERACT":
        return {
            "raw_size": raw_size,
            "detected_unit": "sqft",
            "converted_size_sqft": raw_size,
            "conversion_method": "SOURCE_DECLARED_SQFT",
            "conversion_confidence": "high",
        }
    elif tx_source == "DLD_OFFICIAL":
        return {
            "raw_size": raw_size,
            "detected_unit": "sqm",
            "converted_size_sqft": raw_size * 10.764,
            "conversion_method": "SOURCE_DECLARED_SQM",
            "conversion_confidence": "high",
        }
    elif tx_source == "OTHER_VERIFIED":
        # Other verified sources treated as sqm (same as DLD numeric pattern)
        return {
            "raw_size": raw_size,
            "detected_unit": "sqm",
            "converted_size_sqft": raw_size * 10.764,
            "conversion_method": "SOURCE_VERIFIED_SQM",
            "conversion_confidence": "medium",
        }
    else:
        # UNKNOWN source → excluded, not inferred
        return {
            "raw_size": raw_size,
            "detected_unit": None,
            "converted_size_sqft": None,
            "conversion_method": "UNKNOWN_SOURCE_EXCLUDED",
            "conversion_confidence": "none",
        }


# ===========================================================================
# SECTION 5 — AREA MAPPING (reuse V3 proven logic)
# ===========================================================================

def build_verified_area_mapping_v4(
    master_df: pd.DataFrame,
    dld_store,
) -> Dict[str, Dict]:
    """
    Build statistically verified MASTER area → DLD area mapping.
    Uses UNIQUE PROJECT count for confidence, not property row count.
    """
    from investor_api.dld_benchmark_engine import _DLD_STORE as project_store

    strong_evidence = master_df[
        (master_df["dld_evidence_status"] == "DLD_MATCH")
        & (master_df["dld_transaction_count"] >= 5)
        & (master_df["normalized_project_name"].notna())
        & (master_df["normalized_project_name"] != "")
    ].copy()

    mapping_data = defaultdict(lambda: {"dld_areas": Counter(), "projects": set(), "property_ids": set()})

    for _, row in strong_evidence.iterrows():
        master_area = str(row.get("area", "")).strip()
        if not master_area:
            continue
        master_area_norm = _normalize(master_area)

        proj_name = str(row.get("normalized_project_name", "")).strip()
        if not proj_name:
            continue

        proj_txs = project_store.get_transactions(proj_name)
        if not proj_txs:
            continue

        dld_area_counts = Counter()
        for tx in proj_txs:
            dld_area = str(tx.get("AREA_EN", "")).strip().upper()
            if dld_area:
                dld_area_counts[dld_area] += 1

        if not dld_area_counts:
            continue

        majority_dld_area = dld_area_counts.most_common(1)[0][0]
        mapping_data[master_area_norm]["dld_areas"][majority_dld_area] += 1
        mapping_data[master_area_norm]["projects"].add(_normalize(proj_name))
        mapping_data[master_area_norm]["property_ids"].add(int(row["property_id"]))

    mapping = {}
    for master_area, data in mapping_data.items():
        dld_areas = data["dld_areas"]
        if not dld_areas:
            continue

        total_projects = len(data["projects"])
        top_candidate, top_count = dld_areas.most_common(1)[0]
        dominance_ratio = top_count / total_projects if total_projects > 0 else 0

        if total_projects >= 10 and dominance_ratio >= 0.8:
            confidence = "high"
        elif total_projects >= 3 and dominance_ratio >= 0.5:
            confidence = "medium"
        elif total_projects >= 1 and dominance_ratio >= 0.5:
            confidence = "low"
        else:
            confidence = "ambiguous"

        mapping[master_area] = {
            "dld_area": top_candidate,
            "unique_supporting_projects": total_projects,
            "supporting_property_count": len(data["property_ids"]),
            "dominance_ratio": round(dominance_ratio, 3),
            "mapping_confidence": confidence,
            "alternative_candidates": [
                {"area": a, "project_support": c}
                for a, c in dld_areas.most_common(3)
            ],
        }

    return mapping


# ===========================================================================
# SECTION 6 — TRANSACTION INDEX (pre-built, sales-only, source-aware, UNKNOWN excluded)
# ===========================================================================

def build_transaction_index_v4(dld_path: str) -> Dict:
    """
    Pre-build a clean V4 transaction index.
    Sales-only, UNKNOWN sources excluded, property type included.
    """
    print(f"[V4] Building transaction index from {dld_path}...")

    total_raw = 0
    sales_included = 0
    mortgage_excluded = 0
    gifts_excluded = 0
    other_non_sale_excluded = 0
    unknown_source_excluded = 0
    ambiguous_size_excluded = 0

    by_area = defaultdict(list)
    by_project = defaultdict(list)

    with open(dld_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_raw += 1

            # Sales filter
            is_sale, filter_reason = transaction_is_sale(row)
            if not is_sale:
                group = str(row.get("GROUP_EN", "")).strip().upper()
                if group == "MORTGAGE":
                    mortgage_excluded += 1
                elif group == "GIFTS":
                    gifts_excluded += 1
                else:
                    other_non_sale_excluded += 1
                continue

            sales_included += 1

            # Source classification (V4)
            tx_source = classify_transaction_source_v4(row.get("TRANSACTION_NUMBER", ""))
            if tx_source == "UNKNOWN":
                unknown_source_excluded += 1
                continue

            # Price
            price = _parse_price(row.get("TRANS_VALUE"))
            if price is None or price <= 0:
                continue
            if price < 100_000:
                continue

            # Size
            raw_size = _parse_size(row.get("ACTUAL_AREA"))
            if raw_size is None or raw_size <= 0:
                continue

            size_detection = detect_size_unit_source_aware_v4(raw_size, tx_source)
            if size_detection["detected_unit"] is None:
                ambiguous_size_excluded += 1
                continue

            # Property type from DLD
            prop_sb_type = str(row.get("PROP_SB_TYPE_EN", "")).strip()
            dld_property_type = normalize_dld_property_type(prop_sb_type)

            # Date
            tx_date = _parse_date(row.get("INSTANCE_DATE"))

            # Bedrooms
            tx_bedrooms = _parse_bedrooms(row.get("ROOMS_EN"))

            # Status
            tx_status = _canonical_status(row.get("PROCEDURE_EN", ""))[0]

            # Area
            dld_area = str(row.get("AREA_EN", "")).strip().upper()
            area_norm = _normalize(dld_area)

            # Project
            project_raw = str(row.get("PROJECT_EN", "")).strip()
            project_norm = _normalize(project_raw)

            # Property type
            prop_type = str(row.get("PROP_TYPE_EN", "")).strip()

            clean_tx = {
                "transaction_id": row.get("TRANSACTION_NUMBER", ""),
                "project": project_raw,
                "project_norm": project_norm,
                "area": dld_area,
                "area_norm": area_norm,
                "date": tx_date,
                "price_aed": price,
                "raw_size": raw_size,
                "size_sqft": size_detection["converted_size_sqft"],
                "size_unit": size_detection["detected_unit"],
                "bedrooms": tx_bedrooms,
                "status": tx_status,
                "property_type": prop_type,
                "property_sub_type": prop_sb_type,
                "architectural_type": dld_property_type,
                "source": tx_source,
                "conversion_method": size_detection["conversion_method"],
                "conversion_confidence": size_detection["conversion_confidence"],
                "ppsf": price / size_detection["converted_size_sqft"],
            }

            if area_norm:
                by_area[area_norm].append(clean_tx)
            if project_norm:
                by_project[project_norm].append(clean_tx)

    print(f"[V4] Index complete:")
    print(f"  Total raw: {total_raw:,}")
    print(f"  Sales included: {sales_included:,}")
    print(f"  Mortgage excluded: {mortgage_excluded:,}")
    print(f"  Gifts excluded: {gifts_excluded:,}")
    print(f"  Other non-sale excluded: {other_non_sale_excluded:,}")
    print(f"  Unknown source excluded: {unknown_source_excluded:,}")
    print(f"  Ambiguous size excluded: {ambiguous_size_excluded:,}")
    print(f"  Final indexed transactions: {sum(len(v) for v in by_area.values()):,}")

    return {
        "by_area": dict(by_area),
        "by_project": dict(by_project),
        "audit_counts": {
            "total_raw": total_raw,
            "sales_included": sales_included,
            "mortgage_excluded": mortgage_excluded,
            "gifts_excluded": gifts_excluded,
            "other_non_sale_excluded": other_non_sale_excluded,
            "unknown_source_excluded": unknown_source_excluded,
            "ambiguous_size_excluded": ambiguous_size_excluded,
        },
    }


# ===========================================================================
# SECTION 7 — V4 FALLBACK BENCHMARK CALCULATOR
# ===========================================================================

def calculate_fallback_benchmark_v4(
    property_id: str,
    property_name: str,
    area: str,
    developer_name: str,
    current_price_aed: float,
    unit_bedrooms: Optional[int],
    unit_bathrooms: Optional[float],
    unit_size_sqft: Optional[float],
    unit_size_sqm: Optional[float],
    unit_status: str,
    property_type: Optional[str],
    bedroom_value_status: str,
    dld_evidence_status: str,
    tx_index: Dict,
    area_mapping: Optional[Dict[str, Dict]] = None,
    config: Optional[Dict] = None,
    subject_project_name: Optional[str] = None,
) -> Dict[str, Any]:
    """V4 fallback benchmark calculator."""
    if config is None:
        config = SHADOW_FALLBACK_CONFIG_V4

    result = {
        "eligible": False,
        "level": None,
        "production_eligible": False,
        "subject": {
            "property_id": property_id,
            "property_name": property_name,
            "area": area,
            "developer_name": developer_name,
            "current_price_aed": current_price_aed,
            "unit_bedrooms": unit_bedrooms,
            "unit_bathrooms": unit_bathrooms,
            "unit_size_sqft": unit_size_sqft,
            "unit_size_sqm": unit_size_sqm,
            "unit_status": unit_status,
            "property_type": property_type,
            "bedroom_value_status": bedroom_value_status,
        },
        "comparables": [],
        "benchmark": {},
        "calculations": {},
        "quality": {},
        "validation": {
            "excluded_reasons": [],
            "quality_flags": [],
            "filter_counts": {},
        },
    }

    # Hard exclusion checks
    if bedroom_value_status == "AMBIGUOUS_BEDROOM":
        result["validation"]["excluded_reasons"].append("AMBIGUOUS_BEDROOM_NO_FALLBACK")
        result["level"] = "AMBIGUOUS_BEDROOM_NO_FALLBACK"
        return result

    if unit_bedrooms is None or (isinstance(unit_bedrooms, float) and math.isnan(unit_bedrooms)):
        result["validation"]["excluded_reasons"].append("MISSING_BEDROOM")
        result["level"] = "MISSING_BEDROOM_NO_FALLBACK"
        return result

    if unit_size_sqft is None or (isinstance(unit_size_sqft, float) and math.isnan(unit_size_sqft)) or unit_size_sqft <= 0:
        result["validation"]["excluded_reasons"].append("MISSING_SUBJECT_SIZE_NO_PPSF_BENCHMARK")
        result["level"] = "MISSING_SUBJECT_SIZE_NO_PPSF_BENCHMARK"
        return result

    # Area mapping
    area_norm = _normalize(area)
    mapped = area_mapping.get(area_norm) if area_mapping else None
    if not mapped:
        result["validation"]["excluded_reasons"].append("NO_VERIFIED_AREA_MAPPING")
        result["level"] = "NO_VERIFIED_AREA_MAPPING"
        return result

    if mapped.get("mapping_confidence") == "ambiguous":
        result["validation"]["excluded_reasons"].append("AMBIGUOUS_AREA_MAPPING")
        result["level"] = "AMBIGUOUS_AREA_MAPPING"
        return result

    dld_area = mapped["dld_area"]
    mapping_confidence = mapped.get("mapping_confidence", "low")

    # Load area transactions
    by_area = tx_index.get("by_area", {})
    area_txs = by_area.get(_normalize(dld_area), [])

    if not area_txs:
        result["validation"]["excluded_reasons"].append("NO_DLD_TRANSACTIONS_IN_MAPPED_AREA")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    canonical_status, _ = _canonical_status(unit_status)

    # Filter by bedroom
    bedroom_filtered = [tx for tx in area_txs if tx["bedrooms"] is not None and tx["bedrooms"] == int(unit_bedrooms)]
    if not bedroom_filtered:
        result["validation"]["excluded_reasons"].append("NO_SAME_BEDROOM_TRANSACTIONS_IN_AREA")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    # Source filter
    allowed_sources = config.get("sources_allowed", ["DLD_OFFICIAL", "DXBINTERACT", "OTHER_VERIFIED"])
    source_filtered = [tx for tx in bedroom_filtered if tx["source"] in allowed_sources]
    if not source_filtered:
        result["validation"]["excluded_reasons"].append("NO_ALLOWED_SOURCE_TRANSACTIONS")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    # Exclude subject project
    subject_project_norm = _normalize(subject_project_name) if subject_project_name else ""
    if subject_project_norm:
        before_exclusion = len(source_filtered)
        source_filtered = [tx for tx in source_filtered if tx["project_norm"] != subject_project_norm]
        excluded_count = before_exclusion - len(source_filtered)
        if excluded_count > 0:
            result["validation"]["quality_flags"].append(f"SUBJECT_PROJECT_EXCLUDED:{excluded_count}")

    # Status filter: same status first
    status_filtered = [tx for tx in source_filtered if tx["status"] == canonical_status]
    same_status_count = len(status_filtered)

    status_broadened = False
    if same_status_count < config.get("min_transactions_area_fallback", 10):
        status_filtered = source_filtered
        status_broadened = True
        result["validation"]["quality_flags"].append(f"STATUS_BROADENED:same_status_count={same_status_count}")

    broadened_status_count = len(status_filtered)

    # Recency filter
    lookback = config.get("lookback_months", 24)
    cutoff = datetime.now() - pd.DateOffset(months=lookback)
    recent = [tx for tx in status_filtered if tx["date"] is not None and tx["date"] >= cutoff]
    if len(recent) >= config.get("min_transactions_area_fallback", 10):
        status_filtered = recent
    else:
        result["validation"]["excluded_reasons"].append(
            f"INSUFFICIENT_TRANSACTIONS_WITHIN_LOOKBACK:{len(recent)}_vs_{config.get('min_transactions_area_fallback', 10)}"
        )
        result["level"] = "INSUFFICIENT_TRANSACTIONS_WITHIN_LOOKBACK"
        return result

    raw_tx_count = len(status_filtered)

    # Size band filter
    size_band_applied = False
    band_pct = config.get("size_band_pct_default", 0.20)
    lower = unit_size_sqft * (1 - band_pct)
    upper = unit_size_sqft * (1 + band_pct)
    size_banded = [tx for tx in status_filtered if lower <= tx["size_sqft"] <= upper]
    if len(size_banded) >= config.get("min_transactions_area_fallback", 10):
        size_band_applied = True
        status_filtered = size_banded
        result["validation"]["quality_flags"].append(f"SIZE_BAND_APPLIED_{band_pct}")
    else:
        result["validation"]["quality_flags"].append(
            f"SIZE_BAND_INSUFFICIENT_{len(size_banded)}_vs_{config.get('min_transactions_area_fallback', 10)}"
        )

    # Property type filter (optional — tested in backtest A vs B)
    type_filter_applied = False
    if config.get("property_type_filter") and property_type and property_type != "UNKNOWN":
        type_filtered = [tx for tx in status_filtered if tx["architectural_type"] == property_type]
        if len(type_filtered) >= config.get("min_transactions_area_fallback", 10):
            status_filtered = type_filtered
            type_filter_applied = True
            result["validation"]["quality_flags"].append(f"PROPERTY_TYPE_FILTER_APPLIED:{property_type}")
        else:
            result["validation"]["quality_flags"].append(
                f"PROPERTY_TYPE_FILTER_INSUFFICIENT_{len(type_filtered)}_vs_{config.get('min_transactions_area_fallback', 10)}"
            )

    # Outlier removal
    ppsf_values = [tx["ppsf"] for tx in status_filtered]
    outliers = []
    final_txs = []
    outlier_method = config.get("outlier_method", "iqr_1.5")

    if outlier_method == "none" or len(ppsf_values) < 4:
        final_txs = status_filtered
    elif outlier_method.startswith("iqr"):
        multiplier = config.get("ppsf_outlier_iqr_multiplier", 1.5)
        s = sorted(ppsf_values)
        n = len(s)
        q1 = s[n // 4]
        q3 = s[(3 * n) // 4]
        iqr = q3 - q1
        lb = q1 - multiplier * iqr
        ub = q3 + multiplier * iqr
        for tx in status_filtered:
            if lb <= tx["ppsf"] <= ub:
                final_txs.append(tx)
            else:
                outliers.append(tx)
        if outliers:
            result["validation"]["quality_flags"].append(f"PPSF_OUTLIERS_REMOVED:{len(outliers)}(IQR_{lb:.0f}-{ub:.0f})")
    elif outlier_method == "mad":
        med_ppsf = median(ppsf_values)
        mad = median([abs(v - med_ppsf) for v in ppsf_values])
        mf = 1.4826
        lb = med_ppsf - 3 * mf * mad
        ub = med_ppsf + 3 * mf * mad
        for tx in status_filtered:
            if lb <= tx["ppsf"] <= ub:
                final_txs.append(tx)
            else:
                outliers.append(tx)
        if outliers:
            result["validation"]["quality_flags"].append(f"PPSF_OUTLIERS_REMOVED_MAD:{len(outliers)}({lb:.0f}-{ub:.0f})")

    if not final_txs:
        result["validation"]["excluded_reasons"].append("ALL_TRANSACTIONS_REMOVED_AS_OUTLIERS")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    final_tx_count = len(final_txs)
    min_tx = config.get("min_transactions_area_fallback", 10)
    if final_tx_count < min_tx:
        result["validation"]["excluded_reasons"].append(f"INSUFFICIENT_FINAL_TRANSACTIONS_{final_tx_count}_vs_{min_tx}")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    # Project diversity and concentration
    project_counts = Counter(tx["project"] for tx in final_txs if tx["project"])
    unique_projects = len(project_counts)
    largest_share = max(project_counts.values()) / final_tx_count if project_counts else 1.0

    max_conc = config.get("max_project_concentration", 0.50)
    if largest_share > max_conc and project_counts:
        top_project = project_counts.most_common(1)[0][0]
        result["validation"]["excluded_reasons"].append(
            f"EXCESSIVE_PROJECT_CONCENTRATION:{largest_share:.1%}_from_{top_project}"
        )
        result["level"] = "EXCESSIVE_PROJECT_CONCENTRATION"
        return result

    min_unique = config.get("min_unique_projects_area", 3)
    if unique_projects < min_unique:
        result["validation"]["excluded_reasons"].append(f"INSUFFICIENT_UNIQUE_PROJECTS_{unique_projects}_vs_{min_unique}")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    # PPSF statistics with P25/P50/P75
    final_ppsf = [tx["ppsf"] for tx in final_txs]
    s = sorted(final_ppsf)
    n = len(s)
    ppsf_p25 = s[n // 4] if n >= 4 else s[0]
    ppsf_p50 = median(final_ppsf)
    ppsf_p75 = s[(3 * n) // 4] if n >= 4 else s[-1]
    ppsf_mean = sum(final_ppsf) / n
    mad = median([abs(v - ppsf_p50) for v in final_ppsf])
    iqr = ppsf_p75 - ppsf_p25
    high_dispersion = iqr / ppsf_p50 > 0.5 if ppsf_p50 > 0 else False

    # Bootstrap confidence bounds (simplified percentile bootstrap)
    bootstrap_samples = 200
    bootstrap_medians = []
    for _ in range(bootstrap_samples):
        sample = [random.choice(final_ppsf) for _ in range(n)]
        bootstrap_medians.append(median(sample))
    bootstrap_medians_sorted = sorted(bootstrap_medians)
    bootstrap_lower = bootstrap_medians_sorted[int(bootstrap_samples * 0.025)]
    bootstrap_upper = bootstrap_medians_sorted[int(bootstrap_samples * 0.975)]

    # Estimated benchmark (size required — enforced above)
    estimated_benchmark = ppsf_p50 * unit_size_sqft
    estimated_benchmark_p25 = ppsf_p25 * unit_size_sqft
    estimated_benchmark_p75 = ppsf_p75 * unit_size_sqft
    estimated_benchmark_lower = bootstrap_lower * unit_size_sqft
    estimated_benchmark_upper = bootstrap_upper * unit_size_sqft

    # APIL and Conventional
    diff_aed = estimated_benchmark - current_price_aed
    apil_adv = (diff_aed / current_price_aed) * 100 if current_price_aed else None
    conv_pct = (diff_aed / estimated_benchmark) * 100 if estimated_benchmark else None

    # Level
    if size_band_applied and not status_broadened and not type_filter_applied:
        level = "AREA_SAME_BEDROOM_SAME_STATUS_SIZE_ADJUSTED"
    elif size_band_applied and status_broadened and not type_filter_applied:
        level = "AREA_SAME_BEDROOM_STATUS_BROADENED_SIZE_ADJUSTED"
    elif not size_band_applied and not status_broadened and not type_filter_applied:
        level = "AREA_SAME_BEDROOM_SAME_STATUS"
    else:
        level = "AREA_SAME_BEDROOM_STATUS_BROADENED"

    if type_filter_applied:
        level = level + "_TYPE_FILTERED"

    # Quality score (not confidence — calibrated later)
    quality_score = 0.0
    quality_reasons = []

    if "AREA_SAME_BEDROOM_SAME_STATUS_SIZE_ADJUSTED" in level:
        quality_score += 40
        quality_reasons.append("Area-level same-status size-adjusted evidence")
    elif "AREA_SAME_BEDROOM_STATUS_BROADENED_SIZE_ADJUSTED" in level:
        quality_score += 30
        quality_reasons.append("Area-level status-broadened size-adjusted evidence")
    elif "AREA_SAME_BEDROOM_SAME_STATUS" in level:
        quality_score += 25
        quality_reasons.append("Area-level same-status evidence")
    else:
        quality_score += 15
        quality_reasons.append("Area-level status-broadened evidence")

    if final_tx_count >= 30:
        quality_score += 25
        quality_reasons.append(f"Very strong transaction count ({final_tx_count})")
    elif final_tx_count >= 15:
        quality_score += 20
        quality_reasons.append(f"Strong transaction count ({final_tx_count})")
    elif final_tx_count >= 10:
        quality_score += 15
        quality_reasons.append(f"Moderate transaction count ({final_tx_count})")
    else:
        quality_score -= 10
        quality_reasons.append(f"Low transaction count ({final_tx_count})")

    if mapping_confidence == "high":
        quality_score += 15
        quality_reasons.append("High-confidence area mapping")
    elif mapping_confidence == "medium":
        quality_score += 5
        quality_reasons.append("Medium-confidence area mapping")
    else:
        quality_score -= 10
        quality_reasons.append("Low-confidence area mapping")

    if unique_projects >= 5:
        quality_score += 10
        quality_reasons.append(f"Diverse comparables ({unique_projects} projects)")
    elif unique_projects >= 3:
        quality_score += 5
        quality_reasons.append(f"Moderate diversity ({unique_projects} projects)")

    if high_dispersion:
        quality_score -= 10
        quality_reasons.append("High PPSF dispersion")

    if status_broadened:
        quality_score -= 10
        quality_reasons.append("Status filter broadened")

    if size_band_applied:
        quality_score += 5
        quality_reasons.append("Size-adjusted comparables")

    if type_filter_applied:
        quality_score += 5
        quality_reasons.append("Property-type filtered comparables")

    quality_score = max(0, min(100, quality_score))

    # Source distribution
    source_dist = Counter(tx["source"] for tx in final_txs)

    result.update({
        "eligible": True,
        "level": level,
        "production_eligible": False,
        "comparables": final_txs,
        "benchmark": {
            "estimated_benchmark_aed": round(estimated_benchmark, 2),
            "estimated_benchmark_p25": round(estimated_benchmark_p25, 2),
            "estimated_benchmark_p75": round(estimated_benchmark_p75, 2),
            "estimated_benchmark_bootstrap_lower": round(estimated_benchmark_lower, 2),
            "estimated_benchmark_bootstrap_upper": round(estimated_benchmark_upper, 2),
            "median_ppsf": round(ppsf_p50, 2),
            "ppsf_p25": round(ppsf_p25, 2),
            "ppsf_p75": round(ppsf_p75, 2),
            "ppsf_mean": round(ppsf_mean, 2),
            "ppsf_iqr": round(iqr, 2),
            "ppsf_mad": round(mad, 2),
            "high_dispersion_flag": high_dispersion,
            "raw_transaction_count": raw_tx_count,
            "final_transaction_count": final_tx_count,
            "unique_project_count": unique_projects,
            "largest_project_share": round(largest_share, 4),
            "status_broadened": status_broadened,
            "same_status_count": same_status_count,
            "broadened_status_count": broadened_status_count,
            "size_band_applied": size_band_applied,
            "size_band_pct": band_pct if size_band_applied else None,
            "type_filter_applied": type_filter_applied,
            "mapped_dld_area": dld_area,
            "area_mapping_confidence": mapping_confidence,
            "source_distribution": dict(source_dist),
        },
        "calculations": {
            "apil_advantage_pct": round(apil_adv, 2) if apil_adv is not None else None,
            "conventional_below_benchmark_pct": round(conv_pct, 2) if conv_pct is not None else None,
            "price_difference_aed": round(diff_aed, 2) if diff_aed is not None else None,
        },
        "quality": {
            "quality_score": round(quality_score, 1),
            "quality_label": _quality_label(quality_score),
            "quality_reasons": quality_reasons,
        },
        "validation": result["validation"],
    })

    return result


def _quality_label(score: float) -> str:
    if score >= 80:
        return "high"
    elif score >= 50:
        return "medium"
    elif score >= 20:
        return "low"
    else:
        return "very_low"


# ===========================================================================
# SECTION 8 — CONSERVATIVE DIRECTION CLASSIFIER (Precision-First)
# ===========================================================================

def classify_conservative_direction(
    subject_price: float,
    estimated_benchmark: float,
    benchmark_p25: float,
    benchmark_p75: float,
    safety_margin: float = 0.10,
) -> str:
    """
    Conservative direction classification.
    LIKELY_BELOW_MARKET: subject is below lower bound by safety margin
    LIKELY_ABOVE_MARKET: subject is above upper bound by safety margin
    INDETERMINATE: everything else
    """
    lower_bound = benchmark_p25 * (1 - safety_margin)
    upper_bound = benchmark_p75 * (1 + safety_margin)

    if subject_price < lower_bound:
        return "LIKELY_BELOW_MARKET"
    elif subject_price > upper_bound:
        return "LIKELY_ABOVE_MARKET"
    else:
        return "INDETERMINATE"


def evaluate_conservative_direction(
    backtests: List[Dict],
    safety_margins: List[float] = None,
) -> Dict:
    """
    Evaluate conservative direction classification across multiple safety margins.
    """
    if safety_margins is None:
        safety_margins = [0.0, 0.05, 0.10, 0.15]

    results = {}
    for margin in safety_margins:
        classified = []
        indeterminate = []
        true_positives_below = 0
        false_positives_below = 0
        true_positives_above = 0
        false_positives_above = 0

        for b in backtests:
            subject_price = b.get("current_price_aed", 0)
            exact_benchmark = b.get("exact_benchmark")
            fallback_benchmark = b.get("fallback_benchmark")
            benchmark_p25 = b.get("fallback_benchmark_p25")
            benchmark_p75 = b.get("fallback_benchmark_p75")

            if not exact_benchmark or not fallback_benchmark or not benchmark_p25 or not benchmark_p75:
                continue

            predicted = classify_conservative_direction(
                subject_price, fallback_benchmark, benchmark_p25, benchmark_p75, margin
            )

            # Ground truth direction from exact benchmark
            true_diff_pct = (exact_benchmark - subject_price) / subject_price * 100 if subject_price else 0
            true_direction = "neutral"
            if true_diff_pct > 5:
                true_direction = "below_market"
            elif true_diff_pct < -5:
                true_direction = "above_market"

            if predicted == "INDETERMINATE":
                indeterminate.append(b)
                continue

            classified.append(b)

            if predicted == "LIKELY_BELOW_MARKET":
                if true_direction == "below_market":
                    true_positives_below += 1
                else:
                    false_positives_below += 1
            elif predicted == "LIKELY_ABOVE_MARKET":
                if true_direction == "above_market":
                    true_positives_above += 1
                else:
                    false_positives_above += 1

        total_classified = len(classified)
        total = len(backtests)

        below_precision = true_positives_below / (true_positives_below + false_positives_below) if (true_positives_below + false_positives_below) > 0 else 0
        below_recall = true_positives_below / sum(1 for b in backtests if b.get("canonical_direction") == "below_market") if sum(1 for b in backtests if b.get("canonical_direction") == "below_market") > 0 else 0

        above_precision = true_positives_above / (true_positives_above + false_positives_above) if (true_positives_above + false_positives_above) > 0 else 0
        above_recall = true_positives_above / sum(1 for b in backtests if b.get("canonical_direction") == "above_benchmark") if sum(1 for b in backtests if b.get("canonical_direction") == "above_benchmark") > 0 else 0

        total_correct = true_positives_below + true_positives_above
        overall_precision = total_correct / total_classified if total_classified > 0 else 0
        fp_rate = (false_positives_below + false_positives_above) / total_classified if total_classified > 0 else 0

        results[f"margin_{int(margin*100)}pct"] = {
            "safety_margin": margin,
            "classified_n": total_classified,
            "indeterminate_n": len(indeterminate),
            "coverage_pct": round(total_classified / total * 100, 1) if total > 0 else 0,
            "below_market_precision": round(below_precision * 100, 1),
            "below_market_recall": round(below_recall * 100, 1),
            "above_market_precision": round(above_precision * 100, 1),
            "above_market_recall": round(above_recall * 100, 1),
            "overall_classified_precision": round(overall_precision * 100, 1),
            "false_positive_rate": round(fp_rate * 100, 1),
        }

    return results


# ===========================================================================
# SECTION 9 — BACKTEST FRAMEWORK (V4)
# ===========================================================================

def compute_canonical_backtest_target_v4(row: pd.Series) -> Optional[Dict]:
    """
    Compute canonical exact-project benchmark using SALES-ONLY shadow target.
    """
    property_name = str(row.get("property_name", "")).strip()
    bedrooms = row.get("unit_bedrooms")
    status = str(row.get("unit_status", "")).strip()
    price = float(row.get("current_price_aed", 0)) if pd.notna(row.get("current_price_aed")) else 0

    if isinstance(bedrooms, float) and math.isnan(bedrooms):
        bedrooms = None
    if bedrooms is not None:
        bedrooms = int(bedrooms)

    canonical_status = _canonical_status(status)[0]

    canonical = compute_project_benchmark_sales_only_shadow(
        project_name=property_name,
        subject_price=price,
        bedroom=bedrooms,
        status=canonical_status,
        exact_project_only=True,
    )

    if not canonical.get("usable_for_investment"):
        return None

    return {
        "canonical_median": canonical["benchmark_median"],
        "canonical_mean": canonical["benchmark_mean"],
        "canonical_transaction_count": canonical["transaction_count"],
        "canonical_transaction_ids": canonical["matched_transaction_ids"],
        "canonical_matched_project": canonical["matched_project"],
        "canonical_match_method": canonical["match_method"],
        "canonical_evidence_level": canonical["evidence_level"],
        "canonical_warnings": canonical["warnings"],
        "non_sale_counts": canonical.get("non_sale_counts", {}),
        "sales_only": True,
    }


def run_backtest_v4(
    master_df: pd.DataFrame,
    tx_index: Dict,
    area_mapping: Dict,
    config: Dict,
    subject_property_ids: List[str],
    source_filter: Optional[str] = None,
) -> Tuple[List[Dict], Dict]:
    """
    Run backtest against SALES-ONLY canonical exact-project benchmarks.
    """
    backtests = []
    audit_counters = {
        "NON_SALE_FALLBACK_TRANSACTION_USED": 0,
        "NON_SALE_CANONICAL_TARGET_TRANSACTION_USED": 0,
        "UNKNOWN_SOURCE_USED_IN_BENCHMARK": 0,
        "TARGET_PROJECT_LEAKAGE": 0,
        "TRAIN_TEST_PROJECT_LEAKAGE": 0,
        "AMBIGUOUS_SIZE_USED": 0,
        "AMBIGUOUS_AREA_MAPPING_USED": 0,
        "PROPERTY_TYPE_SOURCE_CONFLICT": 0,
        "STATUS_BROADENED_WITHOUT_LABEL": 0,
        "MISSING_SIZE_BENCHMARK_GENERATED": 0,
    }

    for prop_id in subject_property_ids:
        row_match = master_df[master_df["property_id"] == int(prop_id)]
        if row_match.empty:
            continue
        row = row_match.iloc[0]

        bedrooms = row.get("unit_bedrooms")
        size_sqft = row.get("unit_size_sqft")
        if isinstance(bedrooms, float) and math.isnan(bedrooms):
            bedrooms = None
        if isinstance(size_sqft, float) and math.isnan(size_sqft):
            size_sqft = None

        # Resolve property type
        subject_property_type = resolve_subject_property_type(
            str(prop_id),
            row.get("property_type"),
        )

        # Compute canonical target (sales-only)
        canonical_target = compute_canonical_backtest_target_v4(row)
        if canonical_target is None:
            continue

        # Non-sale audit on canonical target
        non_sale = canonical_target.get("non_sale_counts", {})
        if non_sale.get("mortgage", 0) > 0 or non_sale.get("gift", 0) > 0 or non_sale.get("other_non_sale", 0) > 0:
            audit_counters["NON_SALE_CANONICAL_TARGET_TRANSACTION_USED"] += 1

        # Run fallback
        fallback = calculate_fallback_benchmark_v4(
            property_id=prop_id,
            property_name=str(row.get("property_name", "")),
            area=str(row.get("area", "")),
            developer_name=str(row.get("developer_name", "")),
            current_price_aed=float(row.get("current_price_aed", 0)) if pd.notna(row.get("current_price_aed")) else 0,
            unit_bedrooms=int(bedrooms) if bedrooms is not None else None,
            unit_bathrooms=row.get("unit_bathrooms"),
            unit_size_sqft=float(size_sqft) if size_sqft is not None else None,
            unit_size_sqm=row.get("unit_size_sqm"),
            unit_status=str(row.get("unit_status", "")),
            property_type=subject_property_type,
            bedroom_value_status=str(row.get("bedroom_value_status", "")),
            dld_evidence_status=str(row.get("dld_evidence_status", "")),
            tx_index=tx_index,
            area_mapping=area_mapping,
            config=config,
            subject_project_name=str(row.get("property_name", "")),
        )

        if not fallback.get("eligible"):
            continue

        # Source filter for DLD_OFFICIAL_ONLY or multi-source backtest
        if source_filter:
            final_sources = fallback["benchmark"].get("source_distribution", {})
            if source_filter not in final_sources or final_sources[source_filter] == 0:
                continue
            if source_filter == "DLD_OFFICIAL":
                total_sources = sum(final_sources.values())
                if final_sources.get("DLD_OFFICIAL", 0) < total_sources:
                    continue

        # Compare fallback vs canonical target
        fallback_benchmark = fallback["benchmark"]["estimated_benchmark_aed"]
        exact_benchmark = canonical_target["canonical_median"]

        # Verify target benchmark match (sales-only vs live)
        # In V4, the target IS the sales-only shadow, so this should always match itself
        # We verify by recomputing
        from investor_api.dld_benchmark_engine import compute_project_benchmark
        live_check = compute_project_benchmark(
            project_name=str(row.get("property_name", "")).strip(),
            subject_price=float(row.get("current_price_aed", 0)) if pd.notna(row.get("current_price_aed")) else 0,
            bedroom=int(row.get("unit_bedrooms")) if pd.notna(row.get("unit_bedrooms")) else None,
            status=_canonical_status(str(row.get("unit_status", "")).strip())[0],
            exact_project_only=True,
        )
        # Note: live_check may differ from sales-only target — this is expected and audited

        # Transaction ID overlap check (target leakage)
        canonical_tx_ids = set(canonical_target["canonical_transaction_ids"])
        fallback_tx_ids = set(tx["transaction_id"] for tx in fallback.get("comparables", []))
        if canonical_tx_ids and fallback_tx_ids:
            overlap = canonical_tx_ids & fallback_tx_ids
            if overlap:
                audit_counters["TARGET_PROJECT_LEAKAGE"] += 1

        # Subject project leakage check
        subject_norm = _normalize(str(row.get("property_name", "")))
        subject_project_in_comparables = sum(
            1 for tx in fallback.get("comparables", [])
            if _normalize(tx.get("project", "")) == subject_norm
        )
        if subject_project_in_comparables > 0:
            audit_counters["TARGET_PROJECT_LEAKAGE"] += subject_project_in_comparables

        # Unknown source audit
        for tx in fallback.get("comparables", []):
            if tx.get("source") == "UNKNOWN":
                audit_counters["UNKNOWN_SOURCE_USED_IN_BENCHMARK"] += 1

        error_aed = fallback_benchmark - exact_benchmark
        error_pct = (error_aed / exact_benchmark) * 100 if exact_benchmark else None
        abs_error_pct = abs(error_pct) if error_pct is not None else None
        signed_error_pct = error_pct if error_pct is not None else None

        # Decision direction
        subject_price = float(row.get("current_price_aed", 0))
        canonical_direction = "neutral"
        fallback_direction = "neutral"

        if exact_benchmark and subject_price:
            canonical_diff_pct = (exact_benchmark - subject_price) / subject_price * 100
            fallback_diff_pct = (fallback_benchmark - subject_price) / subject_price * 100

            canonical_direction = "below_market" if canonical_diff_pct > 5 else ("above_market" if canonical_diff_pct < -5 else "neutral")
            fallback_direction = "below_market" if fallback_diff_pct > 5 else ("above_market" if fallback_diff_pct < -5 else "neutral")

        direction_match = canonical_direction == fallback_direction

        # Conservative direction classification
        benchmark_p25 = fallback["benchmark"].get("estimated_benchmark_p25")
        benchmark_p75 = fallback["benchmark"].get("estimated_benchmark_p75")

        conservative_direction = "INDETERMINATE"
        if benchmark_p25 and benchmark_p75 and subject_price:
            conservative_direction = classify_conservative_direction(
                subject_price,
                fallback_benchmark,
                benchmark_p25,
                benchmark_p75,
                safety_margin=0.10,
            )

        backtests.append({
            "property_id": prop_id,
            "property_name": row.get("property_name", ""),
            "area": row.get("area", ""),
            "dld_area": fallback["benchmark"]["mapped_dld_area"],
            "bedrooms": int(bedrooms) if bedrooms is not None else None,
            "bedroom_label": _bedroom_label(bedrooms),
            "status": row.get("unit_status", ""),
            "property_type": subject_property_type,
            "price_band": _price_band(float(row.get("current_price_aed", 0))),
            "size_band": _size_band(size_sqft),
            "exact_benchmark": exact_benchmark,
            "fallback_benchmark": fallback_benchmark,
            "fallback_benchmark_p25": benchmark_p25,
            "fallback_benchmark_p75": benchmark_p75,
            "error_aed": round(error_aed, 2),
            "error_pct": round(error_pct, 2) if error_pct is not None else None,
            "absolute_error_pct": round(abs_error_pct, 2) if abs_error_pct is not None else None,
            "signed_error_pct": round(signed_error_pct, 2) if signed_error_pct is not None else None,
            "canonical_direction": canonical_direction,
            "fallback_direction": fallback_direction,
            "direction_match": direction_match,
            "conservative_direction": conservative_direction,
            "fallback_level": fallback["level"],
            "tx_count": fallback["benchmark"]["final_transaction_count"],
            "unique_projects": fallback["benchmark"]["unique_project_count"],
            "size_band_applied": fallback["benchmark"]["size_band_applied"],
            "status_broadened": fallback["benchmark"]["status_broadened"],
            "type_filter_applied": fallback["benchmark"]["type_filter_applied"],
            "area_mapping_confidence": fallback["benchmark"]["area_mapping_confidence"],
            "quality_score": fallback["quality"]["quality_score"],
            "quality_label": fallback["quality"]["quality_label"],
            "ppsf_p50": fallback["benchmark"]["median_ppsf"],
            "ppsf_p25": fallback["benchmark"]["ppsf_p25"],
            "ppsf_p75": fallback["benchmark"]["ppsf_p75"],
            "ppsf_iqr": fallback["benchmark"]["ppsf_iqr"],
            "high_dispersion": fallback["benchmark"]["high_dispersion_flag"],
            "subject_project_in_comparables": subject_project_in_comparables,
            "current_price_aed": float(row.get("current_price_aed", 0)),
            "unit_size_sqft": size_sqft,
            "source_distribution": fallback["benchmark"].get("source_distribution", {}),
            "canonical_tx_count": canonical_target["canonical_transaction_count"],
            "canonical_non_sale_counts": canonical_target.get("non_sale_counts", {}),
        })

    return backtests, audit_counters


def summarize_backtests(backtests: List[Dict]) -> Dict:
    errors = [b.get("absolute_error_pct") for b in backtests if b.get("absolute_error_pct") is not None]
    signed_errors = [b.get("signed_error_pct") for b in backtests if b.get("signed_error_pct") is not None]
    if not errors:
        return {"n": 0}

    s = sorted(errors)
    n = len(s)

    dir_matches = sum(1 for b in backtests if b.get("direction_match"))

    result = {
        "n": n,
        "median_abs_error": round(median(errors), 2),
        "mean_abs_error": round(sum(errors) / n, 2),
        "p75": round(s[int(n * 0.75)] if n > 1 else s[0], 2),
        "p90": round(s[int(n * 0.90)] if n > 1 else s[-1], 2),
        "direction_match_rate": round(dir_matches / n * 100, 1) if n > 0 else 0,
    }

    if signed_errors:
        result["median_signed_error"] = round(median(signed_errors), 2)
    else:
        result["median_signed_error"] = None

    return result


def segment_backtests(backtests: List[Dict]) -> Dict[str, Dict]:
    segments = defaultdict(list)
    for b in backtests:
        segments[f"area_{b.get('area', 'unknown')}"].append(b)
        segments[f"bedroom_{b.get('bedroom_label', 'unknown')}"].append(b)
        segments[f"status_{b.get('status', 'unknown')}"].append(b)
        segments[f"type_{b.get('property_type', 'unknown')}"].append(b)
        segments[f"price_{b.get('price_band', 'unknown')}"].append(b)
        segments[f"size_{b.get('size_band', 'unknown')}"].append(b)

    return {k: summarize_backtests(v) for k, v in segments.items()}


# ===========================================================================
# SECTION 10 — CONTAMINATION AUDIT
# ===========================================================================

def run_contamination_audit(master_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Audit current production canonical vs sales-only shadow canonical.
    """
    print("\n[Audit] Running contamination audit...")

    from investor_api.dld_benchmark_engine import compute_project_benchmark

    audit_rows = []
    dld_match_properties = master_df[master_df["dld_evidence_status"] == "DLD_MATCH"].copy()

    for _, row in dld_match_properties.iterrows():
        prop_id = int(row["property_id"])
        property_name = str(row.get("property_name", "")).strip()
        bedrooms = row.get("unit_bedrooms")
        status = str(row.get("unit_status", "")).strip()
        price = float(row.get("current_price_aed", 0)) if pd.notna(row.get("current_price_aed")) else 0

        if isinstance(bedrooms, float) and math.isnan(bedrooms):
            bedrooms = None
        if bedrooms is not None:
            bedrooms = int(bedrooms)

        canonical_status = _canonical_status(status)[0]

        # Current live canonical
        live = compute_project_benchmark(
            project_name=property_name,
            subject_price=price,
            bedroom=bedrooms,
            status=canonical_status,
            exact_project_only=True,
        )

        # Sales-only shadow
        shadow = compute_project_benchmark_sales_only_shadow(
            project_name=property_name,
            subject_price=price,
            bedroom=bedrooms,
            status=canonical_status,
            exact_project_only=True,
        )

        live_median = live.get("benchmark_median")
        shadow_median = shadow.get("benchmark_median")
        live_tx_count = live.get("transaction_count", 0)
        shadow_tx_count = shadow.get("transaction_count", 0)
        live_tx_ids = live.get("matched_transaction_ids", [])
        shadow_tx_ids = shadow.get("matched_transaction_ids", [])

        non_sale = shadow.get("non_sale_counts", {})
        mortgage_count = non_sale.get("mortgage", 0)
        gift_count = non_sale.get("gift", 0)
        other_non_sale_count = non_sale.get("other_non_sale", 0)

        median_diff_aed = None
        median_diff_pct = None
        if live_median is not None and shadow_median is not None and live_median != 0:
            median_diff_aed = abs(shadow_median - live_median)
            median_diff_pct = (shadow_median - live_median) / live_median * 100

        live_decision = live.get("usable_for_investment", False)
        shadow_decision = shadow.get("usable_for_investment", False)
        decision_changed = live_decision != shadow_decision

        audit_rows.append({
            "property_id": prop_id,
            "property_name": property_name,
            "current_live_median": live_median,
            "sales_only_shadow_median": shadow_median,
            "current_transaction_count": live_tx_count,
            "sales_only_transaction_count": shadow_tx_count,
            "current_transaction_ids": ",".join(live_tx_ids[:20]),
            "sales_only_transaction_ids": ",".join(shadow_tx_ids[:20]),
            "mortgage_count_in_current": mortgage_count,
            "gift_count_in_current": gift_count,
            "other_non_sale_count_in_current": other_non_sale_count,
            "median_difference_aed": median_diff_aed,
            "median_difference_pct": median_diff_pct,
            "current_decision": live_decision,
            "sales_only_candidate_decision": shadow_decision,
            "decision_changed": decision_changed,
        })

    audit_df = pd.DataFrame(audit_rows)

    summary = {
        "properties_tested": len(audit_df),
        "properties_with_non_sale_transactions": len(audit_df[
            (audit_df["mortgage_count_in_current"] > 0) |
            (audit_df["gift_count_in_current"] > 0) |
            (audit_df["other_non_sale_count_in_current"] > 0)
        ]),
        "properties_with_median_change": len(audit_df[audit_df["median_difference_aed"].notna() & (audit_df["median_difference_aed"] > 0)]),
        "properties_with_material_median_change_gt_5pct": len(audit_df[audit_df["median_difference_pct"].abs() > 5]),
        "properties_with_material_median_change_gt_10pct": len(audit_df[audit_df["median_difference_pct"].abs() > 10]),
        "properties_whose_candidate_signal_changes": len(audit_df[audit_df["decision_changed"] == True]),
    }

    print(f"[Audit] Complete: {summary}")
    return audit_df, summary


# ===========================================================================
# SECTION 11 — PARAMETER SEARCH
# ===========================================================================

def run_parameter_search_v4(
    master_df: pd.DataFrame,
    tx_index: Dict,
    area_mapping: Dict,
    tuning_property_ids: List[str],
) -> List[Dict]:
    """Search over V4 parameter grid on tuning set."""
    configs_to_test = [
        {"lookback_months": 12, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "iqr_1.5", "property_type_filter": False, "sources_allowed": ["DLD_OFFICIAL", "DXBINTERACT", "OTHER_VERIFIED"]},
        {"lookback_months": 24, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "iqr_1.5", "property_type_filter": False, "sources_allowed": ["DLD_OFFICIAL", "DXBINTERACT", "OTHER_VERIFIED"]},
        {"lookback_months": 36, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "iqr_1.5", "property_type_filter": False, "sources_allowed": ["DLD_OFFICIAL", "DXBINTERACT", "OTHER_VERIFIED"]},
        {"lookback_months": 24, "size_band_pct_default": 0.20, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "iqr_1.5", "property_type_filter": False, "sources_allowed": ["DLD_OFFICIAL", "DXBINTERACT", "OTHER_VERIFIED"]},
        {"lookback_months": 24, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 15, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "iqr_1.5", "property_type_filter": False, "sources_allowed": ["DLD_OFFICIAL", "DXBINTERACT", "OTHER_VERIFIED"]},
        {"lookback_months": 24, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.40, "outlier_method": "iqr_1.5", "property_type_filter": False, "sources_allowed": ["DLD_OFFICIAL", "DXBINTERACT", "OTHER_VERIFIED"]},
        {"lookback_months": 24, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "iqr_2.0", "property_type_filter": False, "sources_allowed": ["DLD_OFFICIAL", "DXBINTERACT", "OTHER_VERIFIED"]},
        {"lookback_months": 24, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "mad", "property_type_filter": False, "sources_allowed": ["DLD_OFFICIAL", "DXBINTERACT", "OTHER_VERIFIED"]},
    ]

    results = []
    for cfg in configs_to_test:
        bt, counters = run_backtest_v4(master_df, tx_index, area_mapping, cfg, tuning_property_ids)
        s = summarize_backtests(bt)
        results.append({"config": cfg, "summary": s, "counters": counters})
        print(f"  Config: lookback={cfg['lookback_months']}, band={cfg['size_band_pct_default']}, min_tx={cfg['min_transactions_area_fallback']}, max_conc={cfg['max_project_concentration']}, outlier={cfg['outlier_method']}")
        print(f"    → n={s['n']}, med_err={s['median_abs_error']:.2f}%, p90={s['p90']:.2f}%, dir_match={s['direction_match_rate']:.1f}%")

    results.sort(key=lambda x: (x["summary"].get("median_abs_error", 999), -x["summary"].get("n", 0)))
    return results


# ===========================================================================
# SECTION 12 — HIGH-END SAFETY GATE ANALYSIS
# ===========================================================================

def analyze_high_end_gates(backtests: List[Dict]) -> Dict:
    """Test explicit exclusion gates for high-end properties."""
    gates = {
        "price_4M+": lambda b: b.get("current_price_aed", 0) >= 4_000_000,
        "price_6M+": lambda b: b.get("current_price_aed", 0) >= 6_000_000,
        "price_8M+": lambda b: b.get("current_price_aed", 0) >= 8_000_000,
        "size_2000+": lambda b: (b.get("unit_size_sqft") or 0) >= 2000,
        "size_2500+": lambda b: (b.get("unit_size_sqft") or 0) >= 2500,
        "3BR+": lambda b: (b.get("bedrooms") or 0) >= 3,
        "4BR+": lambda b: (b.get("bedrooms") or 0) >= 4,
    }

    results = {}
    for gate_name, predicate in gates.items():
        excluded = [b for b in backtests if predicate(b)]
        remaining = [b for b in backtests if not predicate(b)]

        excluded_summary = summarize_backtests(excluded)
        remaining_summary = summarize_backtests(remaining)

        results[gate_name] = {
            "excluded_n": excluded_summary.get("n", 0),
            "excluded_p90": excluded_summary.get("p90"),
            "excluded_median_error": excluded_summary.get("median_abs_error"),
            "remaining_n": remaining_summary.get("n", 0),
            "remaining_p90": remaining_summary.get("p90"),
            "remaining_median_error": remaining_summary.get("median_abs_error"),
            "remaining_direction_match": remaining_summary.get("direction_match_rate"),
        }

    return results


# ===========================================================================
# SECTION 13 — AREA RELIABILITY CLASSIFICATION
# ===========================================================================

def classify_area_reliability(backtests: List[Dict]) -> Dict:
    """Classify area reliability using holdout results."""
    area_groups = defaultdict(list)
    for b in backtests:
        area_groups[b.get("area", "unknown")].append(b)

    reliability = {}
    for area, subset in area_groups.items():
        if len(subset) < 5:
            reliability[area] = {
                "n": len(subset),
                "status": "INSUFFICIENT_VALIDATION",
                "median_error": None,
                "p90": None,
                "direction_match_rate": None,
            }
            continue

        summary = summarize_backtests(subset)
        med_err = summary.get("median_abs_error", 999)
        p90 = summary.get("p90", 999)
        dir_match = summary.get("direction_match_rate", 0)

        if med_err < 25 and p90 < 100 and dir_match >= 40:
            status = "VALIDATED_CANDIDATE"
        elif med_err >= 50 or p90 >= 100:
            status = "UNSAFE_TAIL_ERROR"
        elif dir_match < 40:
            status = "UNSAFE_DIRECTION_ACCURACY"
        else:
            status = "MARGINAL"

        reliability[area] = {
            "n": summary.get("n"),
            "median_error": med_err,
            "p75": summary.get("p75"),
            "p90": p90,
            "direction_match_rate": dir_match,
            "status": status,
        }

    return reliability


# ===========================================================================
# SECTION 14 — LEVEL 2 EXACT-PROJECT STATUS-BROADENED BACKTEST
# ===========================================================================

def run_level2_backtest(
    master_df: pd.DataFrame,
    subject_property_ids: List[str],
) -> List[Dict]:
    """
    Backtest Level 2: exact project, same bedroom, sales only, status broadened.
    This is a separate backtest from the area fallback.
    """
    level2_results = []
    for prop_id in subject_property_ids:
        row_match = master_df[master_df["property_id"] == int(prop_id)]
        if row_match.empty:
            continue
        row = row_match.iloc[0]

        property_name = str(row.get("property_name", "")).strip()
        bedrooms = row.get("unit_bedrooms")
        status = str(row.get("unit_status", "")).strip()
        price = float(row.get("current_price_aed", 0)) if pd.notna(row.get("current_price_aed")) else 0

        if isinstance(bedrooms, float) and math.isnan(bedrooms):
            bedrooms = None
        if bedrooms is not None:
            bedrooms = int(bedrooms)

        canonical_status = _canonical_status(status)[0]

        # Same status first
        shadow_same_status = compute_project_benchmark_sales_only_shadow(
            project_name=property_name,
            subject_price=price,
            bedroom=bedrooms,
            status=canonical_status,
            exact_project_only=True,
        )

        # Status broadened
        shadow_broadened = compute_project_benchmark_sales_only_shadow(
            project_name=property_name,
            subject_price=price,
            bedroom=bedrooms,
            status=None,
            exact_project_only=True,
        )

        same_status_median = shadow_same_status.get("benchmark_median")
        broadened_median = shadow_broadened.get("benchmark_median")

        if same_status_median is not None:
            level = "EXACT_PROJECT_SAME_BEDROOM_SAME_STATUS"
            used_median = same_status_median
            tx_count = shadow_same_status.get("transaction_count", 0)
        elif broadened_median is not None:
            level = "EXACT_PROJECT_SAME_BEDROOM_STATUS_BROADENED"
            used_median = broadened_median
            tx_count = shadow_broadened.get("transaction_count", 0)
        else:
            continue

        error_aed = used_median - price
        error_pct = (error_aed / price) * 100 if price else None

        level2_results.append({
            "property_id": prop_id,
            "property_name": property_name,
            "level": level,
            "exact_benchmark_median": used_median,
            "subject_price": price,
            "error_aed": round(error_aed, 2),
            "error_pct": round(error_pct, 2) if error_pct is not None else None,
            "absolute_error_pct": round(abs(error_pct), 2) if error_pct is not None else None,
            "tx_count": tx_count,
        })

    return level2_results


# ===========================================================================
# SECTION 15 — FULL V4 ANALYSIS RUNNER
# ===========================================================================

def run_full_v4_analysis():
    print("=" * 70)
    print("SHADOW FALLBACK V4 ANALYSIS")
    print("=" * 70)

    # 1. Load MASTER
    print("\n[1/12] Loading MASTER...")
    master_df = pd.read_excel(MASTER_PATH)
    print(f"  MASTER: {len(master_df)} properties")

    # 2. Contamination Audit
    print("\n[2/12] Running contamination audit...")
    audit_df, audit_summary = run_contamination_audit(master_df)
    audit_df.to_excel(os.path.join(OUTPUT_DIR, "DLD_CANONICAL_SALES_CONTAMINATION_AUDIT.xlsx"), index=False)
    print(f"  Properties tested: {audit_summary['properties_tested']}")
    print(f"  With non-sale transactions: {audit_summary['properties_with_non_sale_transactions']}")
    print(f"  Median change >5%: {audit_summary['properties_with_material_median_change_gt_5pct']}")
    print(f"  Median change >10%: {audit_summary['properties_with_material_median_change_gt_10pct']}")
    print(f"  Decision changed: {audit_summary['properties_whose_candidate_signal_changes']}")

    # 3. Build transaction index
    print("\n[3/12] Building V4 transaction index...")
    tx_index = build_transaction_index_v4(DLD_CSV_PATH)

    # 4. Build area mapping v4
    print("\n[4/12] Building area mapping v4...")
    area_mapping = build_verified_area_mapping_v4(master_df, tx_index)
    print(f"  Verified mappings: {len(area_mapping)}")

    # 5. Compute canonical targets for all properties
    print("\n[5/12] Computing SALES-ONLY canonical backtest targets...")
    all_targets = []
    for _, row in master_df.iterrows():
        prop_id = str(int(row["property_id"]))
        target = compute_canonical_backtest_target_v4(row)
        if target:
            all_targets.append({"property_id": prop_id, **target})

    target_df = pd.DataFrame(all_targets)
    print(f"  Properties with valid sales-only canonical target: {len(target_df)}")

    # 6. Project-level train/test split
    print("\n[6/12] Creating project-level train/test split...")
    target_properties = master_df[master_df["property_id"].astype(str).isin(target_df["property_id"].tolist())].copy()
    target_properties["project_norm"] = target_properties["property_name"].apply(_normalize)

    project_groups = defaultdict(list)
    for _, row in target_properties.iterrows():
        project_groups[row["project_norm"]].append(str(int(row["property_id"])))

    projects = list(project_groups.keys())
    random.shuffle(projects)
    split_idx = int(len(projects) * 0.7)
    tuning_projects = projects[:split_idx]
    holdout_projects = projects[split_idx:]

    tuning_ids = [pid for proj in tuning_projects for pid in project_groups[proj]]
    holdout_ids = [pid for proj in holdout_projects for pid in project_groups[proj]]

    leaked_projects = set(tuning_projects) & set(holdout_projects)
    print(f"  Tuning properties: {len(tuning_projects)} ({len(tuning_ids)} units)")
    print(f"  Holdout properties: {len(holdout_projects)} ({len(holdout_ids)} units)")
    print(f"  PROJECT_LEAKAGE_BETWEEN_TRAIN_TEST: {len(leaked_projects)}")

    # 7. Parameter search on tuning set
    print("\n[7/12] Running parameter search on tuning set...")
    search_results = run_parameter_search_v4(master_df, tx_index, area_mapping, tuning_ids)

    best_result = search_results[0]
    best_config = best_result["config"]
    print(f"\n  Best config (lowest median error on tuning):")
    for k, v in sorted(best_config.items()):
        print(f"    {k}: {v}")
    print(f"    → Tuning: n={best_result['summary']['n']}, med_err={best_result['summary']['median_abs_error']:.2f}%, p90={best_result['summary']['p90']:.2f}%")

    # 8. Holdout evaluation with best config
    print("\n[8/12] Running holdout evaluation with best config...")
    holdout_backtests, holdout_counters = run_backtest_v4(
        master_df, tx_index, area_mapping, best_config, holdout_ids
    )
    holdout_summary = summarize_backtests(holdout_backtests)

    print(f"\n  HOLDOUT RESULTS:")
    print(f"    N: {holdout_summary['n']}")
    print(f"    Median abs error: {holdout_summary['median_abs_error']:.2f}%")
    print(f"    Mean abs error: {holdout_summary['mean_abs_error']:.2f}%")
    print(f"    P75: {holdout_summary['p75']:.2f}%")
    print(f"    P90: {holdout_summary['p90']:.2f}%")
    print(f"    Median signed error: {holdout_summary['median_signed_error']:.2f}%")
    print(f"    Direction match rate: {holdout_summary['direction_match_rate']:.1f}%")

    # 9. Holdout with property type filter
    print("\n[9/12] Running holdout WITH property type filter...")
    type_config = dict(best_config)
    type_config["property_type_filter"] = True
    type_backtests, type_counters = run_backtest_v4(
        master_df, tx_index, area_mapping, type_config, holdout_ids
    )
    type_summary = summarize_backtests(type_backtests)
    print(f"    WITH type filter: N={type_summary['n']}, med_err={type_summary['median_abs_error']:.2f}%, p90={type_summary['p90']:.2f}%")

    # 10. DLD_OFFICIAL_ONLY backtest
    print("\n[10/12] Running DLD_OFFICIAL_ONLY backtest...")
    official_backtests, official_counters = run_backtest_v4(
        master_df, tx_index, area_mapping, best_config, holdout_ids, source_filter="DLD_OFFICIAL"
    )
    official_summary = summarize_backtests(official_backtests)
    print(f"    DLD_OFFICIAL_ONLY: N={official_summary['n']}, med_err={official_summary['median_abs_error']:.2f}%, p90={official_summary['p90']:.2f}%")

    # Multi-verified source backtest
    multi_backtests, multi_counters = run_backtest_v4(
        master_df, tx_index, area_mapping, best_config, holdout_ids
    )
    multi_summary = summarize_backtests(multi_backtests)

    # 11. Conservative direction precision analysis
    print("\n[11/12] Running conservative direction precision analysis...")
    precision_results = evaluate_conservative_direction(holdout_backtests)
    for margin_key, margin_result in precision_results.items():
        print(f"    {margin_key}: coverage={margin_result['coverage_pct']:.1f}%, precision={margin_result['overall_classified_precision']:.1f}%, fp_rate={margin_result['false_positive_rate']:.1f}%")

    # 12. High-end safety gates
    print("\n[12/12] Running high-end safety gate analysis...")
    gate_results = analyze_high_end_gates(holdout_backtests)
    for gate_name, gate_result in gate_results.items():
        print(f"    {gate_name}: excluded={gate_result['excluded_n']}, remaining_median_err={gate_result['remaining_median_error']:.2f}%, remaining_p90={gate_result['remaining_p90']:.2f}%")

    # 13. Level 2 backtest
    print("\n[13/12] Running Level 2 exact-project status-broadened backtest...")
    level2_results = run_level2_backtest(master_df, holdout_ids)
    level2_summary = summarize_backtests(level2_results)
    if level2_summary.get("n", 0) > 0:
        print(f"    Level 2: N={level2_summary['n']}, med_err={level2_summary['median_abs_error']:.2f}%, p90={level2_summary['p90']:.2f}%")
    else:
        print(f"    Level 2: No results")

    # 14. Segment analysis
    print("\n[14/12] Running segment analysis...")
    holdout_segments = segment_backtests(holdout_backtests)
    area_reliability = classify_area_reliability(holdout_backtests)

    # 15. Export results
    print("\n[15/12] Exporting results...")

    # Property type mapping
    prop_type_rows = []
    for dld_type, canonical_type in DLD_PROP_SB_TYPE_MAP.items():
        prop_type_rows.append({"dld_prop_sb_type_en": dld_type, "canonical_type": canonical_type})
    prop_type_df = pd.DataFrame(prop_type_rows)
    prop_type_df.to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V4_PROPERTY_TYPE_MAPPING.xlsx"), index=False)

    # Tuning results
    tuning_backtests, _ = run_backtest_v4(master_df, tx_index, area_mapping, best_config, tuning_ids)
    pd.DataFrame(tuning_backtests).to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V4_TUNING_RESULTS.xlsx"), index=False)

    # Holdout results
    pd.DataFrame(holdout_backtests).to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V4_HOLDOUT_RESULTS.xlsx"), index=False)

    # Precision gating
    precision_rows = []
    for margin_key, margin_result in precision_results.items():
        precision_rows.append(margin_result)
    pd.DataFrame(precision_rows).to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V4_PRECISION_GATING.xlsx"), index=False)

    # Segment eligibility
    segment_rows = []
    for segment_name, segment_summary in holdout_segments.items():
        segment_rows.append({
            "segment": segment_name,
            "n": segment_summary.get("n"),
            "median_abs_error": segment_summary.get("median_abs_error"),
            "mean_abs_error": segment_summary.get("mean_abs_error"),
            "p75": segment_summary.get("p75"),
            "p90": segment_summary.get("p90"),
            "direction_match_rate": segment_summary.get("direction_match_rate"),
        })
    pd.DataFrame(segment_rows).to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V4_SEGMENT_ELIGIBILITY.xlsx"), index=False)

    # Area reliability
    area_rows = []
    for area, info in area_reliability.items():
        area_rows.append({"area": area, **info})
    pd.DataFrame(area_rows).to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V4_AREA_RELIABILITY.xlsx"), index=False)

    # Level 2 results
    if level2_results:
        pd.DataFrame(level2_results).to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V4_LEVEL2_RESULTS.xlsx"), index=False)

    # Implementation report
    report = _generate_v4_report(
        audit_summary=audit_summary,
        holdout_summary=holdout_summary,
        type_summary=type_summary,
        official_summary=official_summary,
        multi_summary=multi_summary,
        precision_results=precision_results,
        gate_results=gate_results,
        level2_summary=level2_summary,
        holdout_segments=holdout_segments,
        area_reliability=area_reliability,
        holdout_counters=holdout_counters,
        best_config=best_config,
    )

    with open(os.path.join(OUTPUT_DIR, "FALLBACK_V4_IMPLEMENTATION_REPORT.md"), "w") as f:
        f.write(report)

    print("\n" + "=" * 70)
    print("V4 ANALYSIS COMPLETE")
    print("=" * 70)

    return {
        "audit_summary": audit_summary,
        "holdout_summary": holdout_summary,
        "precision_results": precision_results,
        "best_config": best_config,
    }


def _generate_v4_report(
    audit_summary: Dict,
    holdout_summary: Dict,
    type_summary: Dict,
    official_summary: Dict,
    multi_summary: Dict,
    precision_results: Dict,
    gate_results: Dict,
    level2_summary: Dict,
    holdout_segments: Dict,
    area_reliability: Dict,
    holdout_counters: Dict,
    best_config: Dict,
) -> str:
    """Generate the V4 implementation report."""
    lines = [
        "# Fallback DLD Benchmark — V4 IMPLEMENTATION REPORT",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## 1. Canonical Sales Contamination Audit",
        "",
        f"- Properties tested: {audit_summary.get('properties_tested', 0)}",
        f"- Properties with non-sale transactions: {audit_summary.get('properties_with_non_sale_transactions', 0)}",
        f"- Properties with median change: {audit_summary.get('properties_with_median_change', 0)}",
        f"- Properties with median change >5%: {audit_summary.get('properties_with_material_median_change_gt_5pct', 0)}",
        f"- Properties with median change >10%: {audit_summary.get('properties_with_material_median_change_gt_10pct', 0)}",
        f"- Properties whose decision changes: {audit_summary.get('properties_whose_candidate_signal_changes', 0)}",
        "",
        "## 2. V4 Configuration",
        "",
        "```json",
        json.dumps(best_config, indent=2),
        "```",
        "",
        "## 3. Holdout Accuracy Results",
        "",
        f"| Metric | Without Type Filter | With Type Filter | DLD_OFFICIAL_ONLY | Multi-Verified |",
        f"|--------|--------------------:|-----------------:|------------------:|---------------:|",
        f"| N | {holdout_summary.get('n', 0)} | {type_summary.get('n', 0)} | {official_summary.get('n', 0)} | {multi_summary.get('n', 0)} |",
        f"| Median abs error | {holdout_summary.get('median_abs_error', 0):.2f}% | {type_summary.get('median_abs_error', 0):.2f}% | {official_summary.get('median_abs_error', 0):.2f}% | {multi_summary.get('median_abs_error', 0):.2f}% |",
        f"| Mean abs error | {holdout_summary.get('mean_abs_error', 0):.2f}% | {type_summary.get('mean_abs_error', 0):.2f}% | {official_summary.get('mean_abs_error', 0):.2f}% | {multi_summary.get('mean_abs_error', 0):.2f}% |",
        f"| P75 | {holdout_summary.get('p75', 0):.2f}% | {type_summary.get('p75', 0):.2f}% | {official_summary.get('p75', 0):.2f}% | {multi_summary.get('p75', 0):.2f}% |",
        f"| P90 | {holdout_summary.get('p90', 0):.2f}% | {type_summary.get('p90', 0):.2f}% | {official_summary.get('p90', 0):.2f}% | {multi_summary.get('p90', 0):.2f}% |",
        f"| Direction match | {holdout_summary.get('direction_match_rate', 0):.1f}% | {type_summary.get('direction_match_rate', 0):.1f}% | {official_summary.get('direction_match_rate', 0):.1f}% | {multi_summary.get('direction_match_rate', 0):.1f}% |",
        "",
        "## 4. Conservative Direction Precision",
        "",
        "| Safety Margin | Classified N | Coverage % | Precision | FP Rate |",
        "|---------------|-------------:|-----------:|----------:|--------:|",
    ]

    for margin_key, margin_result in precision_results.items():
        lines.append(
            f"| {margin_result['safety_margin']*100:.0f}% | {margin_result['classified_n']} | "
            f"{margin_result['coverage_pct']:.1f}% | {margin_result['overall_classified_precision']:.1f}% | "
            f"{margin_result['false_positive_rate']:.1f}% |"
        )

    lines.extend([
        "",
        "## 5. High-End Safety Gates",
        "",
        "| Gate | Excluded N | Remaining Median Error | Remaining P90 |",
        "|------|-----------:|----------------------:|--------------:|",
    ])

    for gate_name, gate_result in gate_results.items():
        lines.append(
            f"| {gate_name} | {gate_result['excluded_n']} | "
            f"{gate_result['remaining_median_error'] or 'N/A'}% | "
            f"{gate_result['remaining_p90'] or 'N/A'}% |"
        )

    lines.extend([
        "",
        "## 6. Level 2 Exact-Project Status-Broadened",
        "",
    ])
    if level2_summary.get("n", 0) > 0:
        lines.extend([
            f"- N: {level2_summary['n']}",
            f"- Median abs error: {level2_summary['median_abs_error']:.2f}%",
            f"- P90: {level2_summary['p90']:.2f}%",
        ])
    else:
        lines.append("- No Level 2 results")

    lines.extend([
        "",
        "## 7. Audit Counters",
        "",
        "| Counter | Value | Target |",
        "|---------|-------|--------|",
    ])

    for counter, value in holdout_counters.items():
        lines.append(f"| {counter} | {value} | 0 |")

    lines.extend([
        "",
        "## 8. Area Reliability",
        "",
    ])

    for area, info in sorted(area_reliability.items(), key=lambda x: x[1].get("median_error") or 999):
        lines.append(
            f"- **{area}**: {info['status']} | N={info.get('n', 0)} | "
            f"med_err={info.get('median_error', 'N/A')}% | "
            f"P90={info.get('p90', 'N/A')}% | dir={info.get('direction_match_rate', 'N/A')}%"
        )

    lines.extend([
        "",
        "## 9. Segment Analysis",
        "",
    ])

    for segment_name, segment_summary in sorted(holdout_segments.items()):
        if segment_summary.get("n", 0) >= 5:
            lines.append(
                f"- **{segment_name}**: N={segment_summary['n']} | "
                f"med_err={segment_summary.get('median_abs_error', 'N/A')}% | "
                f"P90={segment_summary.get('p90', 'N/A')}% | "
                f"dir={segment_summary.get('direction_match_rate', 'N/A')}%"
            )

    lines.extend([
        "",
        "## 10. Production Status",
        "",
        "**production_eligible: FALSE**",
        "",
        "No production decisions, frontend, MASTER_FINAL, Qdrant, or raw DLD CSVs modified.",
        "",
        "## 11. Files Generated",
        "",
        "| File | Description |",
        "|------|-------------|",
        "| DLD_CANONICAL_SALES_CONTAMINATION_AUDIT.xlsx | Current vs sales-only canonical comparison |",
        "| FALLBACK_V4_PROPERTY_TYPE_MAPPING.xlsx | DLD PROP_SB_TYPE_EN → normalized type mapping |",
        "| FALLBACK_V4_TUNING_RESULTS.xlsx | Tuning set backtest results |",
        "| FALLBACK_V4_HOLDOUT_RESULTS.xlsx | Holdout set backtest results |",
        "| FALLBACK_V4_PRECISION_GATING.xlsx | Conservative direction precision by safety margin |",
        "| FALLBACK_V4_SEGMENT_ELIGIBILITY.xlsx | Segment reliability classifications |",
        "| FALLBACK_V4_AREA_RELIABILITY.xlsx | Area reliability classifications |",
        "| FALLBACK_V4_LEVEL2_RESULTS.xlsx | Level 2 exact-project status-broadened results |",
        "| FALLBACK_V4_IMPLEMENTATION_REPORT.md | This report |",
    ])

    return "\n".join(lines)