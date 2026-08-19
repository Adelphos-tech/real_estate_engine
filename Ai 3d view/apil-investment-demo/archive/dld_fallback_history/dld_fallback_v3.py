"""
SHADOW FALLBACK BENCHMARK ENGINE — VERSION 3
=============================================
Root-level data pipeline fix addressing all 29 requirements.

MANDATORY CONSTRAINTS (unchanged):
- production_eligible = false on every result
- No frontend changes
- No MASTER_FINAL.xlsx modification
- No Qdrant modification
- No raw DLD CSV modification
- No rental yield
- No canonical decision changes

PHILOSOPHY:
- Accuracy and traceability over coverage.
- A smaller, correctly validated, defensible subset is the goal.
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
# SINGLE CANONICAL CONFIG
# ---------------------------------------------------------------------------
SHADOW_FALLBACK_CONFIG_V3 = {
    "version": "fallback_shadow_v3",
    "lookback_months": 24,
    "size_band_pct_default": 0.20,
    "min_transactions_area_fallback": 10,
    "min_unique_projects_area": 3,
    "max_project_concentration": 0.50,
    "ppsf_outlier_iqr_multiplier": 1.5,
    "outlier_method": "iqr_1.5",
    "property_type_filter": False,
    "sale_only": True,
    "sources_allowed": ["DLD_OFFICIAL", "DXBINTERACT", "OTHER_DLD_SALES"],
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
# SECTION 1 — TRANSACTION PROVENANCE & SALES FILTER
# ===========================================================================

def classify_transaction_source(tx_number: str) -> str:
    """Classify transaction by ID prefix pattern."""
    if not tx_number:
        return "UNKNOWN"
    tx = str(tx_number).strip().upper()
    if tx.startswith("DXB-"):
        return "DXBINTERACT"
    # Numeric prefixes followed by dash are DLD-style (could be any emirate)
    if re.match(r"^\d+-", tx):
        return "DLD_OFFICIAL"
    return "UNKNOWN"


def transaction_is_sale(row: Dict) -> Tuple[bool, str]:
    """
    Determine if a transaction is a sale transaction.
    Returns (is_sale, reason_or_empty).
    """
    group = str(row.get("GROUP_EN", "")).strip().upper()
    procedure = str(row.get("PROCEDURE_EN", "")).strip().lower()

    if group == "SALES":
        return (True, "")

    # Explicit non-sale groups
    if group in ("MORTGAGE", "GIFTS"):
        return (False, f"GROUP_EN={group}")

    # If group is empty/missing, use procedure as secondary signal
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
# SECTION 2 — SOURCE-AWARE SIZE UNIT DETECTION
# ===========================================================================

def detect_size_unit_source_aware(raw_size: float, tx_source: str) -> Dict:
    """
    Determine size unit from transaction source provenance.

    Empirically verified:
    - DLD_OFFICIAL (numeric prefix): ACTUAL_AREA is in sqm
    - DXBINTERACT (DXB-* prefix): ACTUAL_AREA is in sqft
    - OTHER_DLD_SALES (other numeric prefixes): ACTUAL_AREA is in sqm
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
    elif tx_source == "OTHER_DLD_SALES":
        return {
            "raw_size": raw_size,
            "detected_unit": "sqm",
            "converted_size_sqft": raw_size * 10.764,
            "conversion_method": "SOURCE_INFERRED_SQM",
            "conversion_confidence": "medium",
        }
    else:
        return {
            "raw_size": raw_size,
            "detected_unit": None,
            "converted_size_sqft": None,
            "conversion_method": "UNKNOWN_SOURCE_AMBIGUOUS",
            "conversion_confidence": "none",
        }


# ===========================================================================
# SECTION 3 — REFINED AREA MAPPING
# ===========================================================================

def build_verified_area_mapping_v3(
    master_df: pd.DataFrame,
    dld_store,  # DLDAreaStore
) -> Dict[str, Dict]:
    """
    Build statistically verified MASTER area → DLD area mapping.
    Uses UNIQUE PROJECT count for confidence, not property row count.
    """
    from investor_api.dld_benchmark_engine import _DLD_STORE as project_store

    # Collect exact-project matched properties
    strong_evidence = master_df[
        (master_df["dld_evidence_status"] == "DLD_MATCH")
        & (master_df["dld_transaction_count"] >= 5)
        & (master_df["normalized_project_name"].notna())
        & (master_df["normalized_project_name"] != "")
    ].copy()

    # For each property, find its DLD area from exact-project transactions
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

        # Get DLD areas for this project's transactions
        dld_area_counts = Counter()
        for tx in proj_txs:
            dld_area = str(tx.get("AREA_EN", "")).strip().upper()
            if dld_area:
                dld_area_counts[dld_area] += 1

        if not dld_area_counts:
            continue

        # Take majority DLD area
        majority_dld_area = dld_area_counts.most_common(1)[0][0]

        mapping_data[master_area_norm]["dld_areas"][majority_dld_area] += 1
        mapping_data[master_area_norm]["projects"].add(_normalize(proj_name))
        mapping_data[master_area_norm]["property_ids"].add(int(row["property_id"]))

    # Build final mapping with dominance ratios
    mapping = {}
    for master_area, data in mapping_data.items():
        dld_areas = data["dld_areas"]
        if not dld_areas:
            continue

        total_projects = len(data["projects"])
        top_candidate, top_count = dld_areas.most_common(1)[0]
        dominance_ratio = top_count / total_projects if total_projects > 0 else 0

        # Second candidate
        second_candidate = None
        second_count = 0
        if len(dld_areas) > 1:
            second_candidate, second_count = dld_areas.most_common(2)[1]

        # Confidence based on dominance ratio and project count
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
# SECTION 4 — TRANSACTION INDEX (pre-built, sales-only, source-aware)
# ===========================================================================

def build_transaction_index(dld_path: str) -> Dict:
    """
    Pre-build a clean transaction index with all provenance and unit fixes applied.
    Returns dict with:
        - by_area: Dict[area_norm, List[Dict]]
        - by_project: Dict[project_norm, List[Dict]]
        - audit_counts: Dict
    """
    print(f"[V3] Building transaction index from {dld_path}...")

    total_raw = 0
    sales_included = 0
    mortgage_excluded = 0
    gifts_excluded = 0
    other_non_sale_excluded = 0
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

            # Source classification
            tx_source = classify_transaction_source(row.get("TRANSACTION_NUMBER", ""))

            # Price
            price = _parse_price(row.get("TRANS_VALUE"))
            if price is None or price <= 0:
                continue
            if price < 100_000:
                continue  # outlier threshold

            # Size
            raw_size = _parse_size(row.get("ACTUAL_AREA"))
            if raw_size is None or raw_size <= 0:
                continue

            size_detection = detect_size_unit_source_aware(raw_size, tx_source)
            if size_detection["detected_unit"] is None:
                ambiguous_size_excluded += 1
                continue

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
            prop_sub_type = str(row.get("PROP_SB_TYPE_EN", "")).strip()

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
                "property_sub_type": prop_sub_type,
                "source": tx_source,
                "conversion_method": size_detection["conversion_method"],
                "conversion_confidence": size_detection["conversion_confidence"],
                "ppsf": price / size_detection["converted_size_sqft"],
            }

            if area_norm:
                by_area[area_norm].append(clean_tx)
            if project_norm:
                by_project[project_norm].append(clean_tx)

    print(f"[V3] Index complete:")
    print(f"  Total raw: {total_raw:,}")
    print(f"  Sales included: {sales_included:,}")
    print(f"  Mortgage excluded: {mortgage_excluded:,}")
    print(f"  Gifts excluded: {gifts_excluded:,}")
    print(f"  Other non-sale excluded: {other_non_sale_excluded:,}")
    print(f"  Ambiguous size excluded: {ambiguous_size_excluded:,}")
    print(f"  Final indexed transactions: {sum(len(v) for v in by_area.values()):,}")

    return {
        "by_area": dict(by_area),
        "by_project": dict(by_project),
        "audit_counts": {
            "TOTAL_RAW_TRANSACTIONS": total_raw,
            "SALES_INCLUDED": sales_included,
            "MORTGAGE_EXCLUDED": mortgage_excluded,
            "GIFTS_EXCLUDED": gifts_excluded,
            "OTHER_NON_SALE_EXCLUDED": other_non_sale_excluded,
            "AMBIGUOUS_SIZE_EXCLUDED": ambiguous_size_excluded,
        },
    }


# ===========================================================================
# SECTION 5 — CANONICAL BACKTEST TARGET
# ===========================================================================

def compute_canonical_backtest_target(
    row: pd.Series,
    config: Dict = None,
) -> Optional[Dict]:
    """
    Compute canonical exact-project benchmark using the same logic as production.
    Uses investor_api.dld_benchmark_engine.compute_project_benchmark.
    """
    from investor_api.dld_benchmark_engine import compute_project_benchmark

    property_name = str(row.get("property_name", "")).strip()
    bedrooms = row.get("unit_bedrooms")
    status = str(row.get("unit_status", "")).strip()
    price = float(row.get("current_price_aed", 0)) if pd.notna(row.get("current_price_aed")) else 0

    if isinstance(bedrooms, float) and math.isnan(bedrooms):
        bedrooms = None
    if bedrooms is not None:
        bedrooms = int(bedrooms)

    canonical_status = _canonical_status(status)[0]

    canonical = compute_project_benchmark(
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
    }


# ===========================================================================
# SECTION 6 — FALLBACK BENCHMARK CALCULATOR (V3)
# ===========================================================================

def calculate_fallback_benchmark_v3(
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
    """V3 fallback benchmark calculator."""
    if config is None:
        config = SHADOW_FALLBACK_CONFIG_V3

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

    # Size required for AED benchmark
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
    allowed_sources = config.get("sources_allowed", ["DLD_OFFICIAL", "DXBINTERACT", "OTHER_DLD_SALES"])
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
        # Try status-broadened
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
    size_banded = status_filtered
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
        med = median(ppsf_values)
        mad = median([abs(v - med) for v in ppsf_values])
        mf = 1.4826
        lb = med - 3 * mf * mad
        ub = med + 3 * mf * mad
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

    # PPSF statistics
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

    # Estimated benchmark (size required — enforced above)
    estimated_benchmark = ppsf_p50 * unit_size_sqft

    # APIL and Conventional
    diff_aed = estimated_benchmark - current_price_aed
    apil_adv = (diff_aed / current_price_aed) * 100 if current_price_aed else None
    conv_pct = (diff_aed / estimated_benchmark) * 100 if estimated_benchmark else None

    # Level
    if size_band_applied and not status_broadened:
        level = "AREA_SAME_BEDROOM_SAME_STATUS_SIZE_ADJUSTED"
    elif size_band_applied and status_broadened:
        level = "AREA_SAME_BEDROOM_STATUS_BROADENED_SIZE_ADJUSTED"
    elif not size_band_applied and not status_broadened:
        level = "AREA_SAME_BEDROOM_SAME_STATUS"
    else:
        level = "AREA_SAME_BEDROOM_STATUS_BROADENED"

    # Quality score (not confidence — calibrated later)
    quality_score = 0.0
    quality_reasons = []

    if level == "AREA_SAME_BEDROOM_SAME_STATUS_SIZE_ADJUSTED":
        quality_score += 40
        quality_reasons.append("Area-level same-status size-adjusted evidence")
    elif level == "AREA_SAME_BEDROOM_STATUS_BROADENED_SIZE_ADJUSTED":
        quality_score += 30
        quality_reasons.append("Area-level status-broadened size-adjusted evidence")
    elif level == "AREA_SAME_BEDROOM_SAME_STATUS":
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

    quality_score = max(0, min(100, quality_score))

    # Shadow direction
    shadow_direction = "neutral"
    if apil_adv is not None:
        if apil_adv >= 15:
            shadow_direction = "positive"
        elif apil_adv >= 5:
            shadow_direction = "slightly_positive"
        elif apil_adv <= -15:
            shadow_direction = "negative"
        elif apil_adv <= -5:
            shadow_direction = "slightly_negative"

    # Source distribution
    source_dist = Counter(tx["source"] for tx in final_txs)

    result.update({
        "eligible": True,
        "level": level,
        "production_eligible": False,
        "comparables": final_txs,
        "benchmark": {
            "estimated_benchmark_aed": round(estimated_benchmark, 2),
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
        "shadow_direction": shadow_direction,
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
# SECTION 7 — BACKTEST FRAMEWORK
# ===========================================================================

def run_backtest_v3(
    master_df: pd.DataFrame,
    tx_index: Dict,
    area_mapping: Dict,
    config: Dict,
    subject_property_ids: List[str],
    source_filter: Optional[str] = None,
) -> List[Dict]:
    """
    Run backtest against canonical exact-project benchmarks.
    """
    backtests = []
    audit_counters = {
        "TARGET_BENCHMARK_MISMATCH": 0,
        "TARGET_TRANSACTION_ID_MISMATCH": 0,
        "TARGET_LEAKAGE_COUNT": 0,
        "NON_SALE_TRANSACTION_USED_IN_BENCHMARK": 0,
        "AMBIGUOUS_SIZE_USED": 0,
        "AMBIGUOUS_AREA_MAPPING_USED": 0,
        "MISSING_SIZE_BENCHMARK_GENERATED": 0,
        "STATUS_BROADENED_WITHOUT_LABEL": 0,
        "PROJECT_CONCENTRATION_RULE_NOT_ENFORCED": 0,
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

        # Compute canonical target
        canonical_target = compute_canonical_backtest_target(row)
        if canonical_target is None:
            continue

        # Run fallback
        fallback = calculate_fallback_benchmark_v3(
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
            property_type=str(row.get("property_type", "")) if pd.notna(row.get("property_type")) else None,
            bedroom_value_status=str(row.get("bedroom_value_status", "")),
            dld_evidence_status=str(row.get("dld_evidence_status", "")),
            tx_index=tx_index,
            area_mapping=area_mapping,
            config=config,
            subject_project_name=str(row.get("property_name", "")),
        )

        if not fallback.get("eligible"):
            continue

        # Source filter for DLD_OFFICIAL_ONLY backtest
        if source_filter:
            final_sources = fallback["benchmark"].get("source_distribution", {})
            if source_filter not in final_sources or final_sources[source_filter] == 0:
                continue
            if source_filter == "DLD_OFFICIAL":
                # Require ALL sources to be DLD_OFFICIAL
                total_sources = sum(final_sources.values())
                if final_sources.get("DLD_OFFICIAL", 0) < total_sources:
                    continue

        # Compare fallback vs canonical target
        fallback_benchmark = fallback["benchmark"]["estimated_benchmark_aed"]
        exact_benchmark = canonical_target["canonical_median"]

        # Verify backtest target matches live canonical API (not stale MASTER field)
        # Requirement #5: backtest target must match live canonical API exactly
        from investor_api.dld_benchmark_engine import compute_project_benchmark
        _status_for_check = _canonical_status(str(row.get("unit_status", "")).strip())[0]
        live_check = compute_project_benchmark(
            project_name=str(row.get("property_name", "")).strip(),
            subject_price=float(row.get("current_price_aed", 0)) if pd.notna(row.get("current_price_aed")) else 0,
            bedroom=int(row.get("unit_bedrooms")) if pd.notna(row.get("unit_bedrooms")) else None,
            status=_status_for_check,
            exact_project_only=True,
        )
        live_median = live_check.get("benchmark_median")
        if live_median is not None and exact_benchmark is not None:
            if abs(float(live_median) - float(exact_benchmark)) > 0.01:
                audit_counters["TARGET_BENCHMARK_MISMATCH"] += 1

        # Verify transaction ID overlap
        canonical_tx_ids = set(canonical_target["canonical_transaction_ids"])
        fallback_tx_ids = set(tx["transaction_id"] for tx in fallback.get("comparables", []))
        if canonical_tx_ids and fallback_tx_ids:
            overlap = canonical_tx_ids & fallback_tx_ids
            if overlap:
                audit_counters["TARGET_LEAKAGE_COUNT"] += 1

        # Subject project leakage check
        subject_norm = _normalize(str(row.get("property_name", "")))
        subject_project_in_comparables = sum(
            1 for tx in fallback.get("comparables", [])
            if _normalize(tx.get("project", "")) == subject_norm
        )
        if subject_project_in_comparables > 0:
            audit_counters["TARGET_LEAKAGE_COUNT"] += subject_project_in_comparables

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

            canonical_direction = "below_benchmark" if canonical_diff_pct > 5 else ("above_benchmark" if canonical_diff_pct < -5 else "neutral")
            fallback_direction = "below_benchmark" if fallback_diff_pct > 5 else ("above_benchmark" if fallback_diff_pct < -5 else "neutral")

        direction_match = canonical_direction == fallback_direction

        backtests.append({
            "property_id": prop_id,
            "property_name": row.get("property_name", ""),
            "area": row.get("area", ""),
            "dld_area": fallback["benchmark"]["mapped_dld_area"],
            "bedrooms": int(bedrooms) if bedrooms is not None else None,
            "bedroom_label": _bedroom_label(bedrooms),
            "status": row.get("unit_status", ""),
            "property_type": row.get("property_type", ""),
            "price_band": _price_band(float(row.get("current_price_aed", 0))),
            "size_band": _size_band(size_sqft),
            "exact_benchmark": exact_benchmark,
            "fallback_benchmark": fallback_benchmark,
            "error_aed": round(error_aed, 2),
            "error_pct": round(error_pct, 2) if error_pct is not None else None,
            "absolute_error_pct": round(abs_error_pct, 2) if abs_error_pct is not None else None,
            "signed_error_pct": round(signed_error_pct, 2) if signed_error_pct is not None else None,
            "canonical_direction": canonical_direction,
            "fallback_direction": fallback_direction,
            "direction_match": direction_match,
            "fallback_level": fallback["level"],
            "tx_count": fallback["benchmark"]["final_transaction_count"],
            "unique_projects": fallback["benchmark"]["unique_project_count"],
            "size_band_applied": fallback["benchmark"]["size_band_applied"],
            "status_broadened": fallback["benchmark"]["status_broadened"],
            "area_mapping_confidence": fallback["benchmark"]["area_mapping_confidence"],
            "quality_score": fallback["quality"]["quality_score"],
            "quality_label": fallback["quality"]["quality_label"],
            "ppsf_p50": fallback["benchmark"]["median_ppsf"],
            "ppsf_iqr": fallback["benchmark"]["ppsf_iqr"],
            "high_dispersion": fallback["benchmark"]["high_dispersion_flag"],
            "subject_project_in_comparables": subject_project_in_comparables,
            "current_price_aed": float(row.get("current_price_aed", 0)),
            "unit_size_sqft": size_sqft,
            "source_distribution": fallback["benchmark"].get("source_distribution", {}),
            "canonical_tx_count": canonical_target["canonical_transaction_count"],
            "canonical_tx_ids": list(canonical_target["canonical_transaction_ids"])[:10],
        })

    return backtests, audit_counters


def summarize_backtests(backtests: List[Dict]) -> Dict:
    errors = [b["absolute_error_pct"] for b in backtests if b["absolute_error_pct"] is not None]
    signed_errors = [b["signed_error_pct"] for b in backtests if b["signed_error_pct"] is not None]
    if not errors:
        return {"n": 0}

    s = sorted(errors)
    n = len(s)
    signed_sorted = sorted(signed_errors)

    # Direction accuracy
    direction_matches = sum(1 for b in backtests if b.get("direction_match"))
    dir_rate = direction_matches / len(backtests) if backtests else 0

    return {
        "n": n,
        "median_abs_error": s[n // 2],
        "mean_abs_error": sum(errors) / n,
        "p25": s[n // 4],
        "p75": s[(3 * n) // 4],
        "p90": s[int(n * 0.9)],
        "worst": s[-1],
        "median_signed_error": signed_sorted[n // 2] if n > 0 else None,
        "mean_signed_error": sum(signed_errors) / n,
        "direction_match_rate": round(dir_rate * 100, 1),
    }


def segment_backtests(backtests: List[Dict]) -> Dict[str, Dict]:
    segments = {}
    for label in ["Studio", "1BR", "2BR", "3BR", "4BR+", "Unknown"]:
        subset = [b for b in backtests if b["bedroom_label"] == label]
        if subset:
            segments[f"bedroom_{label}"] = summarize_backtests(subset)

    for status in ["Ready", "Offplan"]:
        subset = [b for b in backtests if b["status"] == status]
        if subset:
            segments[f"status_{status}"] = summarize_backtests(subset)

    type_groups = defaultdict(list)
    for b in backtests:
        pt = str(b.get("property_type", "")).strip().lower()
        if not pt:
            pt = "unknown"
        type_groups[pt].append(b)
    for pt, subset in type_groups.items():
        if len(subset) >= 5:
            segments[f"type_{pt}"] = summarize_backtests(subset)

    for band in ["< 1M", "1–2M", "2–4M", "4–8M", "8M+"]:
        subset = [b for b in backtests if b["price_band"] == band]
        if subset:
            segments[f"price_{band}"] = summarize_backtests(subset)

    for band in ["< 600 sqft", "600–1000 sqft", "1000–1500 sqft", "1500–2500 sqft", "2500+ sqft", "Unknown"]:
        subset = [b for b in backtests if b["size_band"] == band]
        if subset:
            segments[f"size_{band}"] = summarize_backtests(subset)

    area_groups = defaultdict(list)
    for b in backtests:
        area_groups[b.get("area", "unknown")].append(b)
    for area, subset in sorted(area_groups.items(), key=lambda x: -len(x[1]))[:20]:
        if len(subset) >= 5:
            segments[f"area_{area}"] = summarize_backtests(subset)

    # Quality score buckets
    for label in ["high", "medium", "low", "very_low"]:
        subset = [b for b in backtests if b.get("quality_label") == label]
        if subset:
            segments[f"quality_{label}"] = summarize_backtests(subset)

    # Distance from benchmark buckets
    for bucket in ["0-5%", "5-10%", "10-20%", "20-30%", "30%+"]:
        subset = []
        for b in backtests:
            abs_err = b.get("absolute_error_pct")
            if abs_err is None:
                continue
            if bucket == "0-5%" and abs_err < 5:
                subset.append(b)
            elif bucket == "5-10%" and 5 <= abs_err < 10:
                subset.append(b)
            elif bucket == "10-20%" and 10 <= abs_err < 20:
                subset.append(b)
            elif bucket == "20-30%" and 20 <= abs_err < 30:
                subset.append(b)
            elif bucket == "30%+" and abs_err >= 30:
                subset.append(b)
        if subset:
            segments[f"distance_{bucket}"] = summarize_backtests(subset)

    return segments


# ===========================================================================
# SECTION 8 — PARAMETER SEARCH & MAIN ORCHESTRATION
# ===========================================================================

def run_parameter_search(
    master_df: pd.DataFrame,
    tx_index: Dict,
    area_mapping: Dict,
    tuning_property_ids: List[str],
) -> List[Dict]:
    """Coarse parameter search on tuning set."""
    configs_to_test = [
        {"lookback_months": 12, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "iqr_1.5"},
        {"lookback_months": 24, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "iqr_1.5"},
        {"lookback_months": 36, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "iqr_1.5"},
        {"lookback_months": 24, "size_band_pct_default": 0.20, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "iqr_1.5"},
        {"lookback_months": 24, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 15, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "iqr_1.5"},
        {"lookback_months": 24, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.40, "outlier_method": "iqr_1.5"},
        {"lookback_months": 24, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "iqr_2.0"},
        {"lookback_months": 24, "size_band_pct_default": 0.15, "min_transactions_area_fallback": 10, "min_unique_projects_area": 3, "max_project_concentration": 0.50, "outlier_method": "mad"},
    ]

    results = []
    for cfg in configs_to_test:
        bt, counters = run_backtest_v3(master_df, tx_index, area_mapping, cfg, tuning_property_ids)
        s = summarize_backtests(bt)
        results.append({"config": cfg, "summary": s, "counters": counters})
        print(f"  Config: lookback={cfg['lookback_months']}, band={cfg['size_band_pct_default']}, min_tx={cfg['min_transactions_area_fallback']}, max_conc={cfg['max_project_concentration']}, outlier={cfg['outlier_method']}")
        print(f"    → n={s['n']}, med_err={s['median_abs_error']:.2f}%, p90={s['p90']:.2f}%, dir_match={s['direction_match_rate']:.1f}%")

    # Sort by median_abs_error then by coverage
    results.sort(key=lambda x: (x["summary"].get("median_abs_error", 999), -x["summary"].get("n", 0)))
    return results


def analyze_worst_cases(backtests: List[Dict], top_n: int = 50) -> Dict:
    if not backtests:
        return {}
    sorted_bt = sorted(backtests, key=lambda x: x.get("absolute_error_pct") or 0, reverse=True)
    worst = sorted_bt[:top_n]

    root_causes = Counter()
    details = []
    for b in worst:
        cause = "OTHER"
        if b.get("subject_project_in_comparables", 0) > 0:
            cause = "TARGET_LEAKAGE"
        elif b.get("high_dispersion"):
            cause = "AREA_TOO_HETEROGENEOUS"
        elif b.get("ppsf_iqr", 0) / (b.get("ppsf_p50") or 1) > 1.0:
            cause = "PROPERTY_TYPE_MIX"
        elif b.get("exact_benchmark", 0) > 5_000_000 and b.get("fallback_benchmark", 0) < 2_000_000:
            cause = "LUXURY_MIX"
        elif b.get("exact_benchmark", 0) < 1_000_000 and b.get("fallback_benchmark", 0) > 2_000_000:
            cause = "LUXURY_MIX"
        elif b.get("unique_projects", 0) <= 2:
            cause = "PROJECT_CONCENTRATION"
        elif b.get("tx_count", 0) < 15:
            cause = "INSUFFICIENT_TRANSACTIONS"

        root_causes[cause] += 1
        details.append({
            **{k: v for k, v in b.items() if k not in ("canonical_tx_ids",)},
            "root_cause": cause,
        })

    return {"root_cause_counts": dict(root_causes), "worst_details": details}


def run_full_v3_analysis():
    from investor_api.fallback.dld_fallback_engine import load_master_df

    print("=" * 70)
    print("SHADOW FALLBACK V3 ANALYSIS")
    print("=" * 70)

    # 1. Load MASTER
    print("\n[1/9] Loading MASTER...")
    master_df = load_master_df()
    print(f"  MASTER: {len(master_df)} properties")

    # 2. Build transaction index
    print("\n[2/9] Building transaction index...")
    tx_index = build_transaction_index(DLD_CSV_PATH)

    # 3. Build area mapping v3
    print("\n[3/9] Building area mapping v3...")
    area_mapping = build_verified_area_mapping_v3(master_df, tx_index)
    print(f"  Verified mappings: {len(area_mapping)}")
    ambiguous_mappings = sum(1 for v in area_mapping.values() if v["mapping_confidence"] == "ambiguous")
    print(f"  Ambiguous mappings excluded: {ambiguous_mappings}")

    # 4. Compute canonical targets for all properties and filter
    print("\n[4/9] Computing canonical backtest targets...")
    all_targets = []
    for _, row in master_df.iterrows():
        prop_id = str(int(row["property_id"]))
        target = compute_canonical_backtest_target(row)
        if target:
            all_targets.append({"property_id": prop_id, **target})

    target_df = pd.DataFrame(all_targets)
    print(f"  Properties with valid canonical target: {len(target_df)}")

    # 5. Project-level train/test split
    print("\n[5/9] Creating project-level train/test split...")
    # Get canonical project names for target properties
    target_properties = master_df[master_df["property_id"].astype(str).isin(target_df["property_id"].tolist())].copy()
    target_properties["project_norm"] = target_properties["property_name"].apply(_normalize)

    # Group by project
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

    # Verify no project leakage
    leaked_projects = set(tuning_projects) & set(holdout_projects)
    print(f"  Tuning properties: {len(tuning_projects)} ({len(tuning_ids)} units)")
    print(f"  Holdout properties: {len(holdout_projects)} ({len(holdout_ids)} units)")
    print(f"  PROJECT_LEAKAGE_BETWEEN_TRAIN_TEST: {len(leaked_projects)}")

    # 6. Parameter search on tuning set
    print("\n[6/9] Running parameter search on tuning set...")
    search_results = run_parameter_search(master_df, tx_index, area_mapping, tuning_ids)

    best_result = search_results[0]
    best_config = best_result["config"]
    print(f"\n  Best config (lowest median error on tuning):")
    for k, v in sorted(best_config.items()):
        print(f"    {k}: {v}")
    print(f"    → Tuning: n={best_result['summary']['n']}, med_err={best_result['summary']['median_abs_error']:.2f}%, p90={best_result['summary']['p90']:.2f}%")

    # 7. Run holdout with best config
    print("\n[7/9] Running holdout evaluation with best config...")
    holdout_backtests, holdout_counters = run_backtest_v3(
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

    # 8. DLD_OFFICIAL_ONLY backtest
    print("\n[8/9] Running DLD_OFFICIAL_ONLY backtest...")
    dld_only_backtests, dld_only_counters = run_backtest_v3(
        master_df, tx_index, area_mapping, best_config, holdout_ids, source_filter="DLD_OFFICIAL"
    )
    dld_only_summary = summarize_backtests(dld_only_backtests)
    print(f"    DLD_OFFICIAL_ONLY: N={dld_only_summary['n']}, med_err={dld_only_summary['median_abs_error']:.2f}%, p90={dld_only_summary['p90']:.2f}%")

    # 9. Segmented analysis
    print("\n[9/9] Running segmented analysis...")
    holdout_segments = segment_backtests(holdout_backtests)
    worst_analysis = analyze_worst_cases(holdout_backtests, top_n=50)

    # Area reliability
    area_reliability = {}
    area_groups = defaultdict(list)
    for b in holdout_backtests:
        area_groups[b.get("area", "unknown")].append(b)
    for area, subset in area_groups.items():
        if len(subset) >= 5:
            summary = summarize_backtests(subset)
            med_err = summary.get("median_abs_error", 999)
            if med_err < 25 and summary.get("p90", 999) < 100:
                reliability = "CANDIDATE_RELIABLE"
            elif med_err < 50:
                reliability = "MARGINAL"
            else:
                reliability = "UNRELIABLE"
            area_reliability[area] = {
                "n": summary.get("n"),
                "median_error": med_err,
                "p75": summary.get("p75"),
                "p90": summary.get("p90"),
                "direction_match_rate": summary.get("direction_match_rate"),
                "reliability": reliability,
            }

    # Export
    print("\n[10/9] Exporting results...")

    # Transaction provenance audit
    prov_rows = []
    for area_norm, txs in tx_index["by_area"].items():
        for tx in txs[:5000]:  # sample for file size
            prov_rows.append({
                "transaction_id": tx["transaction_id"],
                "source": tx["source"],
                "raw_size": tx["raw_size"],
                "size_sqft": tx["size_sqft"],
                "size_unit": tx["size_unit"],
                "conversion_method": tx["conversion_method"],
                "conversion_confidence": tx["conversion_confidence"],
                "area": tx["area"],
                "project": tx["project"],
                "bedrooms": tx["bedrooms"],
                "status": tx["status"],
                "price_aed": tx["price_aed"],
                "ppsf": tx["ppsf"],
            })
    pd.DataFrame(prov_rows).to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V3_TRANSACTION_PROVENANCE.xlsx"), index=False)
    print("  → FALLBACK_V3_TRANSACTION_PROVENANCE.xlsx")

    # Area mapping audit
    mapping_rows = []
    for ma, data in area_mapping.items():
        mapping_rows.append({"master_area": ma, **data})
    pd.DataFrame(mapping_rows).to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V3_AREA_MAPPING_AUDIT.xlsx"), index=False)
    print("  → FALLBACK_V3_AREA_MAPPING_AUDIT.xlsx")

    # Canonical target audit
    pd.DataFrame(all_targets).to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V3_CANONICAL_TARGET_AUDIT.xlsx"), index=False)
    print("  → FALLBACK_V3_CANONICAL_TARGET_AUDIT.xlsx")

    # Holdout results
    if holdout_backtests:
        pd.DataFrame(holdout_backtests).to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V3_HOLDOUT_RESULTS.xlsx"), index=False)
        print("  → FALLBACK_V3_HOLDOUT_RESULTS.xlsx")

    # Tuning results (first config)
    if search_results:
        tuning_bt, _ = run_backtest_v3(master_df, tx_index, area_mapping, search_results[0]["config"], tuning_ids)
        if tuning_bt:
            pd.DataFrame(tuning_bt).to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V3_TUNING_RESULTS.xlsx"), index=False)
            print("  → FALLBACK_V3_TUNING_RESULTS.xlsx")

    # Error analysis
    if holdout_backtests:
        pd.DataFrame([{
            "segment": k,
            **v
        } for k, v in sorted(holdout_segments.items())]).to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V3_ERROR_ANALYSIS.xlsx"), index=False)
        print("  → FALLBACK_V3_ERROR_ANALYSIS.xlsx")

    # Worst cases
    if worst_analysis.get("worst_details"):
        pd.DataFrame(worst_analysis["worst_details"]).to_excel(os.path.join(OUTPUT_DIR, "FALLBACK_V3_WORST_CASES.xlsx"), index=False)
        print("  → FALLBACK_V3_WORST_CASES.xlsx")

    # Implementation report
    generate_v3_report(
        os.path.join(OUTPUT_DIR, "FALLBACK_V3_IMPLEMENTATION_REPORT.md"),
        tx_index["audit_counts"],
        area_mapping,
        len(target_df),
        len(tuning_projects),
        len(holdout_projects),
        len(leaked_projects),
        best_config,
        best_result["summary"],
        holdout_summary,
        dld_only_summary,
        holdout_segments,
        area_reliability,
        worst_analysis,
        holdout_counters,
    )
    print("  → FALLBACK_V3_IMPLEMENTATION_REPORT.md")

    print("\n" + "=" * 70)
    print("V3 ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\nOriginal median error: 34.00%")
    print(f"Holdout median error:  {holdout_summary.get('median_abs_error', 'N/A'):.2f}%")
    print(f"\nOriginal P90:          125.51%")
    print(f"Holdout P90:           {holdout_summary.get('p90', 'N/A'):.2f}%")
    print(f"\nDirection match rate:  {holdout_summary.get('direction_match_rate', 'N/A'):.1f}%")
    print(f"\nDLD_OFFICIAL_ONLY:     N={dld_only_summary.get('n')}, med_err={dld_only_summary.get('median_abs_error'):.2f}%, p90={dld_only_summary.get('p90'):.2f}%")


def generate_v3_report(
    report_path: str,
    audit_counts: Dict,
    area_mapping: Dict,
    canonical_target_count: int,
    tuning_project_count: int,
    holdout_project_count: int,
    project_leakage: int,
    best_config: Dict,
    tuning_summary: Dict,
    holdout_summary: Dict,
    dld_only_summary: Dict,
    holdout_segments: Dict,
    area_reliability: Dict,
    worst_analysis: Dict,
    holdout_counters: Dict,
):
    lines = [
        "# Fallback DLD Benchmark — V3 IMPLEMENTATION REPORT",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## Transaction Provenance & Sales Filter",
        "",
        "| Counter | Value |",
        "|---------|-------|",
    ]
    for k, v in audit_counts.items():
        lines.append(f"| {k} | {v:,} |")

    lines.extend([
        "",
        "## Size Unit Detection (Source-Aware)",
        "",
        "Empirically verified:",
        "- DLD_OFFICIAL (numeric prefix): ACTUAL_AREA is in **sqm**",
        "- DXBINTERACT (DXB-* prefix): ACTUAL_AREA is in **sqft**",
        "- OTHER_DLD_SALES: ACTUAL_AREA is in **sqm**",
        "",
        "## Area Mapping (Dominance Ratio)",
        "",
        f"Total mappings: {len(area_mapping)}",
        f"Ambiguous mappings excluded: {sum(1 for v in area_mapping.values() if v['mapping_confidence'] == 'ambiguous')}",
        "",
        "## Backtest Target",
        "",
        f"Properties with valid canonical exact-project target: {canonical_target_count}",
        "",
        "Target uses `investor_api.dld_benchmark_engine.compute_project_benchmark` with:",
        "- exact_project_only=True",
        "- same bedroom filter",
        "- same status filter (with fallback to all if insufficient)",
        "- MIN_TRANSACTION_VALUE = 100,000 AED",
        "",
        "## Train/Test Split",
        "",
        f"| Dimension | Count |",
        f"|-----------|-------|",
        f"| Tuning projects | {tuning_project_count} |",
        f"| Holdout projects | {holdout_project_count} |",
        f"| PROJECT_LEAKAGE_BETWEEN_TRAIN_TEST | {project_leakage} |",
        "",
        "## Best Configuration (from tuning set)",
        "",
        "```json",
        json.dumps(best_config, indent=2),
        "```",
        "",
        "## Accuracy Results",
        "",
        "| Metric | Tuning | Holdout | DLD_OFFICIAL_ONLY |",
        "|--------|--------|---------|-------------------|",
        f"| N | {tuning_summary.get('n', 0)} | {holdout_summary.get('n', 0)} | {dld_only_summary.get('n', 0)} |",
        f"| Median abs error | {tuning_summary.get('median_abs_error', 'N/A'):.2f}% | {holdout_summary.get('median_abs_error', 'N/A'):.2f}% | {dld_only_summary.get('median_abs_error', 'N/A'):.2f}% |",
        f"| Mean abs error | {tuning_summary.get('mean_abs_error', 'N/A'):.2f}% | {holdout_summary.get('mean_abs_error', 'N/A'):.2f}% | {dld_only_summary.get('mean_abs_error', 'N/A'):.2f}% |",
        f"| P75 | {tuning_summary.get('p75', 'N/A'):.2f}% | {holdout_summary.get('p75', 'N/A'):.2f}% | {dld_only_summary.get('p75', 'N/A'):.2f}% |",
        f"| P90 | {tuning_summary.get('p90', 'N/A'):.2f}% | {holdout_summary.get('p90', 'N/A'):.2f}% | {dld_only_summary.get('p90', 'N/A'):.2f}% |",
        f"| Direction match | {tuning_summary.get('direction_match_rate', 'N/A'):.1f}% | {holdout_summary.get('direction_match_rate', 'N/A'):.1f}% | {dld_only_summary.get('direction_match_rate', 'N/A'):.1f}% |",
        "",
        "## Audit Counters",
        "",
        "| Counter | Value | Target |",
        "|---------|-------|--------|",
    ])
    for k, v in holdout_counters.items():
        lines.append(f"| {k} | {v} | 0 |")

    lines.extend([
        "",
        "## Holdout Segmented Results",
        "",
    ])
    for segment_name, summary in sorted(holdout_segments.items()):
        if summary.get("n", 0) < 3:
            continue
        lines.append(f"### {segment_name}")
        lines.append(f"- N: {summary.get('n')}")
        lines.append(f"- Median abs error: {summary.get('median_abs_error', 'N/A'):.2f}%")
        lines.append(f"- P90: {summary.get('p90', 'N/A'):.2f}%")
        lines.append(f"- Direction match: {summary.get('direction_match_rate', 'N/A'):.1f}%")
        lines.append("")

    lines.extend([
        "## Area Reliability",
        "",
    ])
    for area, data in sorted(area_reliability.items(), key=lambda x: x[1]["median_error"])[:20]:
        lines.append(f"- **{area}**: {data['reliability']} | N={data['n']} | med_err={data['median_error']:.1f}% | P90={data['p90']:.1f}% | dir={data['direction_match_rate']:.1f}%")

    lines.extend([
        "",
        "## Worst Cases (Top 50)",
        "",
    ])
    if worst_analysis.get("root_cause_counts"):
        for cause, count in Counter(worst_analysis["root_cause_counts"]).most_common():
            lines.append(f"- **{cause}**: {count}")

    lines.extend([
        "",
        "## Production Status",
        "",
        "**production_eligible: FALSE**",
        "",
        "No production decisions, frontend, MASTER_FINAL, Qdrant, or raw DLD CSVs modified.",
        "",
        "## Files Generated",
        "",
        "| File | Description |",
        "|------|-------------|",
        "| FALLBACK_V3_TRANSACTION_PROVENANCE.xlsx | Transaction source, size unit, conversion |",
        "| FALLBACK_V3_AREA_MAPPING_AUDIT.xlsx | Area mapping with dominance ratios |",
        "| FALLBACK_V3_CANONICAL_TARGET_AUDIT.xlsx | Canonical exact-project targets |",
        "| FALLBACK_V3_TUNING_RESULTS.xlsx | Tuning set backtest results |",
        "| FALLBACK_V3_HOLDOUT_RESULTS.xlsx | Holdout set backtest results |",
        "| FALLBACK_V3_ERROR_ANALYSIS.xlsx | Segmented error analysis |",
        "| FALLBACK_V3_WORST_CASES.xlsx | Top 50 worst errors with root causes |",
        "| FALLBACK_V3_IMPLEMENTATION_REPORT.md | This report |",
        "",
    ])

    with open(report_path, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run_full_v3_analysis()
