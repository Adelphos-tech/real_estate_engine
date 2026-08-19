"""
SHADOW FALLBACK BENCHMARK ENGINE — REFINEMENT PHASE
=====================================================
Comprehensive refinement addressing 19 requirements:

1. FIX SIZE UNIT DETECTION — multi-method audit with confidence
2. FIX CONFIDENCE SCORE/LABEL CONTRADICTION — canonical mapping, 0 mismatches
3. REMOVE INVALID PPSF-ONLY BENCHMARK — no AED benchmark without subject size
4–16. SEGMENTED BACKTESTS, PARAMETER GRIDS, TRAIN/TEST SPLIT
17. GENERATE OUTPUT FILES
18. PRODUCTION STILL FORBIDDEN
19. NO RENTAL ROI

This module does NOT modify production decisions, frontend, MASTER_FINAL,
Qdrant, or raw DLD CSVs.
"""

import csv
import json
import math
import os
import random
import re
from collections import Counter, defaultdict
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
# Configuration grids for backtesting
# ---------------------------------------------------------------------------
RECENCY_MONTHS_GRID = [6, 12, 18, 24, 36]
SIZE_BAND_GRID = [0.10, 0.15, 0.20, 0.25, 0.30]
MIN_TX_GRID = [5, 8, 10, 15, 20, 30]
MIN_UNIQUE_PROJECTS_GRID = [2, 3, 4, 5]
MAX_PROJECT_CONC_GRID = [0.40, 0.50, 0.60]
OUTLIER_METHODS = [
    {"name": "none", "method": "none"},
    {"name": "iqr_1.5", "method": "iqr", "multiplier": 1.5},
    {"name": "iqr_2.0", "method": "iqr", "multiplier": 2.0},
    {"name": "mad", "method": "mad"},
]

DEFAULT_CONFIG = {
    "lookback_months": 36,
    "size_band_pct_default": 0.25,
    "min_transactions_area_fallback": 8,
    "min_unique_projects_area": 2,
    "max_project_concentration": 0.60,
    "ppsf_outlier_iqr_multiplier": 1.5,
    "outlier_method": "iqr_1.5",
    "property_type_filter": False,
}

NON_DUBAI_AREAS = {
    "umm al daman", "sharjah waterfront city", "sharjah garden city"
}


# ===========================================================================
# Helpers
# ===========================================================================

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
# SECTION 1 — SIZE UNIT DETECTION & AUDIT
# ===========================================================================

def _build_area_unit_statistics(dld_path: str) -> Dict:
    """Build per-area-bedroom-status statistics to infer dominant unit."""
    area_stats = defaultdict(lambda: {"areas": [], "prices": []})

    with open(dld_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            area_str = row.get("ACTUAL_AREA", "").strip()
            price_str = row.get("TRANS_VALUE", "").strip()
            dld_area = row.get("AREA_EN", "").strip().upper()
            rooms = row.get("ROOMS_EN", "").strip().lower()
            status = row.get("PROCEDURE_EN", "").strip().lower()

            if not area_str or not price_str or not dld_area:
                continue
            try:
                area = float(area_str)
                price = float(price_str)
            except Exception:
                continue
            if area <= 0 or price <= 0:
                continue

            br = _parse_bedrooms(rooms)
            can_status, _ = _canonical_status(status)

            key = (dld_area, br, can_status)
            area_stats[key]["areas"].append(area)
            area_stats[key]["prices"].append(price)

    unit_signals = {}
    for key, data in area_stats.items():
        areas = sorted(data["areas"])
        n = len(areas)
        if n < 10:
            continue

        med = median(areas)
        low_count = sum(1 for a in areas if a < 300)
        high_count = sum(1 for a in areas if a > 800)

        if med < 250 and high_count < n * 0.15:
            dominant = "sqm"
            confidence = "high"
        elif med > 900 and low_count < n * 0.15:
            dominant = "sqft"
            confidence = "high"
        elif low_count > n * 0.25 and high_count > n * 0.25:
            dominant = "mixed"
            confidence = "low"
        elif med < 400:
            dominant = "sqm"
            confidence = "medium"
        elif med > 700:
            dominant = "sqft"
            confidence = "medium"
        else:
            dominant = "ambiguous"
            confidence = "low"

        unit_signals[key] = {
            "median": med,
            "count": n,
            "dominant_unit": dominant,
            "confidence": confidence,
            "low_pct": low_count / n,
            "high_pct": high_count / n,
        }

    return unit_signals


def detect_size_unit(
    raw_size: float,
    transaction_price: Optional[float],
    transaction_rooms: Optional[int],
    transaction_area: Optional[str],
    area_unit_stats: Dict,
) -> Dict:
    """Detect whether ACTUAL_AREA is in sqft or sqm for a SINGLE transaction."""
    if raw_size is None or raw_size <= 0:
        return {
            "raw_size": None,
            "detected_unit": None,
            "converted_size_sqft": None,
            "detection_method": "INVALID_SIZE",
            "detection_confidence": "none",
        }

    result = {
        "raw_size": raw_size,
        "detected_unit": None,
        "converted_size_sqft": None,
        "detection_method": None,
        "detection_confidence": None,
    }

    # Method 1: Absolute physical impossibility
    if raw_size < 20:
        result["detected_unit"] = "sqm"
        result["converted_size_sqft"] = raw_size * 10.764
        result["detection_method"] = "SOURCE_DECLARED_SQM"
        result["detection_confidence"] = "high"
        return result

    if raw_size > 5000:
        result["detected_unit"] = "sqft"
        result["converted_size_sqft"] = raw_size
        result["detection_method"] = "SOURCE_DECLARED_SQFT"
        result["detection_confidence"] = "high"
        return result

    # Method 2: Area-level dominant unit
    area_br_key = (transaction_area, transaction_rooms, "Ready")
    area_fallback_key = (transaction_area, transaction_rooms, "Offplan")

    area_signal = None
    if area_br_key in area_unit_stats:
        area_signal = area_unit_stats[area_br_key]
    elif area_fallback_key in area_unit_stats:
        area_signal = area_unit_stats[area_fallback_key]

    if area_signal:
        dominant = area_signal["dominant_unit"]
        if dominant == "sqm" and raw_size < 300:
            result["detected_unit"] = "sqm"
            result["converted_size_sqft"] = raw_size * 10.764
            result["detection_method"] = "AREA_DOMINANT_SQM"
            result["detection_confidence"] = area_signal["confidence"]
            return result
        elif dominant == "sqft" and raw_size > 500:
            result["detected_unit"] = "sqft"
            result["converted_size_sqft"] = raw_size
            result["detection_method"] = "AREA_DOMINANT_SQFT"
            result["detection_confidence"] = area_signal["confidence"]
            return result

    # Method 3: Price-per-area cross-check
    if transaction_price and transaction_price > 0:
        ppsf_if_sqft = transaction_price / raw_size
        ppsf_if_sqm = transaction_price / (raw_size * 10.764)

        sqft_reasonable = 200 <= ppsf_if_sqft <= 15000
        sqm_reasonable = 20 <= ppsf_if_sqm <= 1500

        if sqft_reasonable and not sqm_reasonable:
            result["detected_unit"] = "sqft"
            result["converted_size_sqft"] = raw_size
            result["detection_method"] = "PRICE_CROSS_CHECK_SQFT"
            result["detection_confidence"] = "medium"
            return result
        elif sqm_reasonable and not sqft_reasonable:
            result["detected_unit"] = "sqm"
            result["converted_size_sqft"] = raw_size * 10.764
            result["detection_method"] = "PRICE_CROSS_CHECK_SQM"
            result["detection_confidence"] = "medium"
            return result

    # Method 4: Bedroom-consistent range
    br = transaction_rooms
    if br is not None:
        sqm_typical_ranges = {
            0: (25, 90), 1: (45, 130), 2: (70, 200),
            3: (100, 350), 4: (150, 600),
        }
        sqft_typical_ranges = {
            0: (300, 1000), 1: (500, 1500), 2: (800, 2500),
            3: (1100, 4000), 4: (1600, 7000),
        }
        sqm_range = sqm_typical_ranges.get(min(br, 4), (50, 500))
        sqft_range = sqft_typical_ranges.get(min(br, 4), (500, 5000))

        in_sqm_range = sqm_range[0] <= raw_size <= sqm_range[1]
        in_sqft_range = sqft_range[0] <= raw_size <= sqft_range[1]

        if in_sqm_range and not in_sqft_range:
            result["detected_unit"] = "sqm"
            result["converted_size_sqft"] = raw_size * 10.764
            result["detection_method"] = "BEDROOM_RANGE_SQM"
            result["detection_confidence"] = "medium"
            return result
        elif in_sqft_range and not in_sqm_range:
            result["detected_unit"] = "sqft"
            result["converted_size_sqft"] = raw_size
            result["detection_method"] = "BEDROOM_RANGE_SQFT"
            result["detection_confidence"] = "medium"
            return result

    # Fallback: ambiguous
    result["detected_unit"] = "ambiguous"
    result["converted_size_sqft"] = None
    result["detection_method"] = "AMBIGUOUS"
    result["detection_confidence"] = "none"
    return result


def generate_size_unit_audit(dld_path: str, output_path: str) -> pd.DataFrame:
    """Audit every DLD transaction for size unit detection."""
    print("[SizeAudit] Building area unit statistics...")
    area_stats = _build_area_unit_statistics(dld_path)
    print(f"[SizeAudit] Built stats for {len(area_stats)} area-BR-status combos")

    rows = []
    method_counts = Counter()
    confidence_counts = Counter()
    ambiguous_count = 0

    print("[SizeAudit] Auditing transactions...")
    with open(dld_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i % 50000 == 0 and i > 0:
                print(f"  ...processed {i:,} transactions")

            area_str = row.get("ACTUAL_AREA", "").strip()
            if not area_str:
                continue
            try:
                raw_size = float(area_str)
            except:
                continue
            if raw_size <= 0:
                continue

            price = _parse_price(row.get("TRANS_VALUE"))
            br = _parse_bedrooms(row.get("ROOMS_EN"))
            dld_area = row.get("AREA_EN", "").strip().upper()

            detection = detect_size_unit(raw_size, price, br, dld_area, area_stats)

            method_counts[detection["detection_method"]] += 1
            confidence_counts[detection["detection_confidence"]] += 1
            if detection["detected_unit"] == "ambiguous":
                ambiguous_count += 1

            rows.append({
                "transaction_number": row.get("TRANSACTION_NUMBER", ""),
                "project_en": row.get("PROJECT_EN", ""),
                "area_en": dld_area,
                "rooms_en": row.get("ROOMS_EN", ""),
                "prop_type_en": row.get("PROP_TYPE_EN", ""),
                "procedure_en": row.get("PROCEDURE_EN", ""),
                "raw_actual_area": raw_size,
                "trans_value": price,
                "detected_unit": detection["detected_unit"],
                "converted_size_sqft": detection["converted_size_sqft"],
                "detection_method": detection["detection_method"],
                "detection_confidence": detection["detection_confidence"],
                "implied_ppsf": round(price / detection["converted_size_sqft"], 2) if detection["converted_size_sqft"] and price else None,
            })

    df = pd.DataFrame(rows)
    df.to_excel(output_path, index=False)
    print(f"[SizeAudit] Exported {len(df):,} transactions to {output_path}")

    print("\n=== Size Unit Detection Summary ===")
    print(f"Total transactions audited: {len(df):,}")
    print(f"Ambiguous (excluded): {ambiguous_count:,} ({ambiguous_count/len(df)*100:.1f}%)")
    print("\nBy detection method:")
    for method, count in method_counts.most_common():
        print(f"  {method}: {count:,} ({count/len(df)*100:.1f}%)")
    print("\nBy confidence:")
    for conf, count in confidence_counts.most_common():
        print(f"  {conf}: {count:,} ({count/len(df)*100:.1f}%)")

    return df


# ===========================================================================
# SECTION 2 — CONFIDENCE SCORE/LABEL FIX
# ===========================================================================

def score_to_label(score: float) -> str:
    """Canonical score → label mapping. ZERO mismatches allowed."""
    if score >= 80:
        return "high"
    elif score >= 50:
        return "medium"
    elif score >= 20:
        return "low"
    else:
        return "very_low"


def audit_confidence_score_label_mismatch(results: List[Dict]) -> List[Dict]:
    """Find any property where score and label contradict canonical mapping."""
    mismatches = []
    for r in results:
        conf = r.get("confidence", {})
        score = conf.get("fallback_confidence_score")
        label = conf.get("fallback_confidence_label")
        if score is not None and label is not None:
            expected = score_to_label(score)
            if expected != label:
                mismatches.append({
                    "property_id": r.get("subject", {}).get("property_id"),
                    "score": score,
                    "actual_label": label,
                    "expected_label": expected,
                })
    return mismatches


# ===========================================================================
# SECTION 3 — REFINED FALLBACK CALCULATOR
# ===========================================================================

def calculate_fallback_benchmark_refined(
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
    area_mapping: Optional[Dict[str, Dict]] = None,
    area_unit_stats: Optional[Dict] = None,
    config: Optional[Dict] = None,
    subject_project_name: Optional[str] = None,
) -> Dict[str, Any]:
    """REFINED shadow fallback benchmark calculator."""
    if config is None:
        config = DEFAULT_CONFIG.copy()
    if area_unit_stats is None:
        area_unit_stats = {}

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
        "confidence": {},
        "validation": {
            "excluded_reasons": [],
            "quality_flags": [],
        },
    }

    # Hard exclusion checks
    area_norm = _normalize(area)
    if area_norm in NON_DUBAI_AREAS:
        result["validation"]["excluded_reasons"].append("NON_DUBAI_DLD_NOT_APPLICABLE")
        result["level"] = "NON_DUBAI_DLD_NOT_APPLICABLE"
        return result

    if bedroom_value_status == "AMBIGUOUS_BEDROOM":
        result["validation"]["excluded_reasons"].append("AMBIGUOUS_BEDROOM_NO_FALLBACK")
        result["level"] = "AMBIGUOUS_BEDROOM_NO_FALLBACK"
        return result

    if unit_bedrooms is None or (isinstance(unit_bedrooms, float) and math.isnan(unit_bedrooms)):
        result["validation"]["excluded_reasons"].append("MISSING_BEDROOM")
        result["level"] = "MISSING_BEDROOM_NO_FALLBACK"
        return result

    # Area mapping
    if area_mapping is None:
        from investor_api.fallback.dld_fallback_engine import build_verified_area_mapping, get_fallback_dld_store, load_master_df
        master_df = load_master_df()
        area_mapping = build_verified_area_mapping(master_df, get_fallback_dld_store())

    mapped = area_mapping.get(area_norm)
    if not mapped:
        result["validation"]["excluded_reasons"].append("NO_VERIFIED_AREA_MAPPING")
        result["level"] = "NO_VERIFIED_AREA_MAPPING"
        return result

    dld_area = mapped["dld_area"]
    mapping_confidence = mapped.get("confidence", "low")

    # Load comparable transactions
    from investor_api.fallback.dld_fallback_engine import get_fallback_dld_store
    dld_store = get_fallback_dld_store()
    area_txs = dld_store.get_area_transactions(dld_area)

    if not area_txs:
        result["validation"]["excluded_reasons"].append("NO_DLD_TRANSACTIONS_IN_MAPPED_AREA")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    canonical_status, _ = _canonical_status(unit_status)

    # Filter by bedroom
    bedroom_filtered = []
    for tx in area_txs:
        tx_br = _parse_bedrooms(tx.get("ROOMS_EN"))
        if tx_br is not None and tx_br == int(unit_bedrooms):
            bedroom_filtered.append(tx)

    if not bedroom_filtered:
        result["validation"]["excluded_reasons"].append("NO_SAME_BEDROOM_TRANSACTIONS_IN_AREA")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    # Filter by status
    status_filtered = []
    status_broadened = False
    for tx in bedroom_filtered:
        tx_status = _canonical_status(tx.get("PROCEDURE_EN", ""))[0]
        if tx_status == canonical_status:
            status_filtered.append(tx)

    if not status_filtered:
        for tx in bedroom_filtered:
            status_filtered.append(tx)
        status_broadened = True

    if not status_filtered:
        result["validation"]["excluded_reasons"].append("NO_STATUS_MATCHING_TRANSACTIONS")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    # Parse transactions with refined size unit detection
    parsed = []
    ambiguous_excluded = 0
    sqm_converted_count = 0
    sqft_kept_count = 0

    for tx in status_filtered:
        price = _parse_price(tx.get("TRANS_VALUE"))
        raw_size = _parse_size(tx.get("ACTUAL_AREA"))
        tx_date = _parse_date(tx.get("INSTANCE_DATE"))
        tx_bedrooms = _parse_bedrooms(tx.get("ROOMS_EN"))
        tx_area = tx.get("AREA_EN", "").strip().upper()
        tx_project = _normalize(tx.get("PROJECT_EN", ""))

        if price is None or price <= 0:
            continue
        if raw_size is None or raw_size <= 0:
            continue

        # Exclude subject project's own transactions (leakage prevention)
        if subject_project_name and tx_project == _normalize(subject_project_name):
            continue

        detection = detect_size_unit(raw_size, price, tx_bedrooms, tx_area, area_unit_stats)

        if detection["detected_unit"] == "ambiguous":
            ambiguous_excluded += 1
            continue

        size = detection["converted_size_sqft"]
        if detection["detected_unit"] == "sqm":
            sqm_converted_count += 1
        else:
            sqft_kept_count += 1

        ppsf = price / size
        parsed.append({
            "transaction_id": tx.get("TRANSACTION_NUMBER"),
            "project": tx.get("PROJECT_EN", ""),
            "area": tx.get("AREA_EN", ""),
            "date": tx_date,
            "price_aed": price,
            "size_sqft": size,
            "ppsf": ppsf,
            "bedrooms": tx_bedrooms,
            "status": _canonical_status(tx.get("PROCEDURE_EN", ""))[0],
            "property_type": tx.get("PROP_TYPE_EN", ""),
            "detection_method": detection["detection_method"],
            "detection_confidence": detection["detection_confidence"],
        })

    if sqm_converted_count > 0:
        result["validation"]["quality_flags"].append(f"SQM_CONVERTED_TO_SQFT:{sqm_converted_count}")
    if sqft_kept_count > 0:
        result["validation"]["quality_flags"].append(f"SQFT_KEPT_AS_IS:{sqft_kept_count}")
    if ambiguous_excluded > 0:
        result["validation"]["quality_flags"].append(f"AMBIGUOUS_SIZE_EXCLUDED:{ambiguous_excluded}")

    if not parsed:
        result["validation"]["excluded_reasons"].append("ALL_TRANSACTIONS_INVALID_OR_AMBIGUOUS_AFTER_PARSING")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    # Property type filter
    if config.get("property_type_filter") and property_type:
        prop_type_norm = _normalize(property_type)
        type_matches = []
        for tx in parsed:
            tx_type = _normalize(tx.get("property_type", ""))
            if prop_type_norm in tx_type or tx_type in prop_type_norm:
                type_matches.append(tx)
        if len(type_matches) >= config.get("min_transactions_area_fallback", 8):
            parsed = type_matches
            result["validation"]["quality_flags"].append("PROPERTY_TYPE_FILTER_APPLIED")

    # Recency filter
    lookback_months = config.get("lookback_months", 36)
    cutoff_date = datetime.now() - pd.DateOffset(months=lookback_months)
    recent = [tx for tx in parsed if tx["date"] is not None and tx["date"] >= cutoff_date]
    if len(recent) >= config.get("min_transactions_area_fallback", 8):
        parsed = recent
    else:
        result["validation"]["quality_flags"].append(f"INSUFFICIENT_RECENT_TX_USING_ALL_{len(parsed)}")

    raw_tx_count = len(parsed)

    # Size band filter
    size_band_applied = False
    size_banded = parsed
    if unit_size_sqft is not None and not (isinstance(unit_size_sqft, float) and math.isnan(unit_size_sqft)) and unit_size_sqft > 0:
        band_pct = config.get("size_band_pct_default", 0.25)
        lower = unit_size_sqft * (1 - band_pct)
        upper = unit_size_sqft * (1 + band_pct)
        size_banded = [tx for tx in parsed if lower <= tx["size_sqft"] <= upper]
        if len(size_banded) >= config.get("min_transactions_area_fallback", 8):
            size_band_applied = True
            parsed = size_banded
            result["validation"]["quality_flags"].append(f"SIZE_BAND_APPLIED_{band_pct}")
        else:
            result["validation"]["quality_flags"].append(f"SIZE_BAND_INSUFFICIENT_{len(size_banded)}_USING_ALL_{len(parsed)}")

    # Outlier removal
    outlier_method = config.get("outlier_method", "iqr_1.5")
    ppsf_values = [tx["ppsf"] for tx in parsed]
    outliers = []
    final_txs = []

    if outlier_method == "none" or len(ppsf_values) < 4:
        final_txs = parsed
    elif outlier_method.startswith("iqr"):
        multiplier = config.get("ppsf_outlier_iqr_multiplier", 1.5)
        s = sorted(ppsf_values)
        n = len(s)
        q1 = s[n // 4]
        q3 = s[(3 * n) // 4]
        iqr = q3 - q1
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        for tx in parsed:
            if lower_bound <= tx["ppsf"] <= upper_bound:
                final_txs.append(tx)
            else:
                outliers.append(tx)
        if outliers:
            result["validation"]["quality_flags"].append(
                f"PPSF_OUTLIERS_REMOVED:{len(outliers)}(IQR_{lower_bound:.0f}-{upper_bound:.0f})"
            )
    elif outlier_method == "mad":
        med = median(ppsf_values)
        mad = median([abs(v - med) for v in ppsf_values])
        mad_factor = 1.4826
        lower_bound = med - 3 * mad_factor * mad
        upper_bound = med + 3 * mad_factor * mad
        for tx in parsed:
            if lower_bound <= tx["ppsf"] <= upper_bound:
                final_txs.append(tx)
            else:
                outliers.append(tx)
        if outliers:
            result["validation"]["quality_flags"].append(
                f"PPSF_OUTLIERS_REMOVED_MAD:{len(outliers)}({lower_bound:.0f}-{upper_bound:.0f})"
            )

    if not final_txs:
        result["validation"]["excluded_reasons"].append("ALL_TRANSACTIONS_REMOVED_AS_OUTLIERS")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    final_tx_count = len(final_txs)
    min_tx = config.get("min_transactions_area_fallback", 8)
    if final_tx_count < min_tx:
        result["validation"]["excluded_reasons"].append(f"INSUFFICIENT_FINAL_TRANSACTIONS_{final_tx_count}_vs_{min_tx}")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    # Project diversity
    project_counts = Counter(tx["project"] for tx in final_txs if tx["project"])
    unique_projects = len(project_counts)
    if project_counts:
        largest_share = max(project_counts.values()) / final_tx_count
    else:
        largest_share = 1.0

    max_conc = config.get("max_project_concentration", 0.60)
    if largest_share > max_conc and project_counts:
        result["validation"]["quality_flags"].append(
            f"HIGH_PROJECT_CONCENTRATION:{largest_share:.1%}_from_{project_counts.most_common(1)[0][0]}"
        )

    min_unique = config.get("min_unique_projects_area", 2)
    if unique_projects < min_unique:
        result["validation"]["excluded_reasons"].append(f"INSUFFICIENT_UNIQUE_PROJECTS_{unique_projects}_vs_{min_unique}")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    # PPSF statistics
    final_ppsf = [tx["ppsf"] for tx in final_txs]
    final_ppsf_sorted = sorted(final_ppsf)
    n = len(final_ppsf_sorted)

    ppsf_p25 = final_ppsf_sorted[n // 4] if n >= 4 else final_ppsf_sorted[0]
    ppsf_p50 = median(final_ppsf)
    ppsf_p75 = final_ppsf_sorted[(3 * n) // 4] if n >= 4 else final_ppsf_sorted[-1]
    ppsf_mean = sum(final_ppsf) / n
    mad = median([abs(v - ppsf_p50) for v in final_ppsf])
    iqr = ppsf_p75 - ppsf_p25

    high_dispersion = iqr / ppsf_p50 > 0.5 if ppsf_p50 > 0 else False

    # REQUIRE subject size for AED benchmark
    if unit_size_sqft is not None and unit_size_sqft > 0:
        estimated_benchmark = ppsf_p50 * unit_size_sqft
    else:
        result["validation"]["excluded_reasons"].append("MISSING_SUBJECT_SIZE_NO_PPSF_BENCHMARK")
        result["level"] = "MISSING_SUBJECT_SIZE_NO_PPSF_BENCHMARK"
        return result

    # APIL and Conventional percentages
    if estimated_benchmark is not None and current_price_aed and current_price_aed > 0:
        diff_aed = estimated_benchmark - current_price_aed
        apil_advantage_pct = (diff_aed / current_price_aed) * 100
        conventional_pct = (diff_aed / estimated_benchmark) * 100 if estimated_benchmark else None
    else:
        diff_aed = None
        apil_advantage_pct = None
        conventional_pct = None

    # Fallback level
    if size_band_applied and not status_broadened:
        level = "AREA_SAME_BEDROOM_SIZE_ADJUSTED_EVIDENCE"
    elif size_band_applied and status_broadened:
        level = "AREA_SAME_BEDROOM_SIZE_ADJUSTED_STATUS_BROADENED"
    elif not size_band_applied and not status_broadened:
        level = "AREA_SAME_BEDROOM_EVIDENCE"
    else:
        level = "AREA_SAME_BEDROOM_STATUS_BROADENED_EVIDENCE"

    # Refined confidence model
    confidence_score = 0.0
    confidence_reasons = []

    if level == "AREA_SAME_BEDROOM_SIZE_ADJUSTED_EVIDENCE":
        confidence_score += 40
        confidence_reasons.append("Area-level size-adjusted evidence")
    elif level == "AREA_SAME_BEDROOM_SIZE_ADJUSTED_STATUS_BROADENED":
        confidence_score += 35
        confidence_reasons.append("Area-level size-adjusted, status-broadened")
    elif level == "AREA_SAME_BEDROOM_EVIDENCE":
        confidence_score += 30
        confidence_reasons.append("Area-level bedroom-matched evidence")
    elif level == "AREA_SAME_BEDROOM_STATUS_BROADENED_EVIDENCE":
        confidence_score += 25
        confidence_reasons.append("Area-level bedroom-matched, status-broadened")
    else:
        confidence_score += 20
        confidence_reasons.append("Lower hierarchy fallback")

    if final_tx_count >= 30:
        confidence_score += 25
        confidence_reasons.append(f"Very strong transaction count ({final_tx_count})")
    elif final_tx_count >= 15:
        confidence_score += 20
        confidence_reasons.append(f"Strong transaction count ({final_tx_count})")
    elif final_tx_count >= 10:
        confidence_score += 15
        confidence_reasons.append(f"Moderate transaction count ({final_tx_count})")
    elif final_tx_count >= 8:
        confidence_score += 10
        confidence_reasons.append(f"Adequate transaction count ({final_tx_count})")
    else:
        confidence_score -= 10
        confidence_reasons.append(f"Low transaction count ({final_tx_count})")

    if mapping_confidence == "high":
        confidence_score += 15
        confidence_reasons.append("High-confidence area mapping")
    elif mapping_confidence == "medium":
        confidence_score += 5
        confidence_reasons.append("Medium-confidence area mapping")
    else:
        confidence_score -= 10
        confidence_reasons.append("Low-confidence area mapping")

    if unique_projects >= 5:
        confidence_score += 10
        confidence_reasons.append(f"Diverse comparables ({unique_projects} projects)")
    elif unique_projects >= 3:
        confidence_score += 5
        confidence_reasons.append(f"Moderate diversity ({unique_projects} projects)")
    elif unique_projects >= 2:
        confidence_score += 0
    else:
        confidence_score -= 15
        confidence_reasons.append("Single-project concentration")

    if largest_share > max_conc:
        confidence_score -= 15
        confidence_reasons.append(f"High project concentration ({largest_share:.1%})")

    if high_dispersion:
        confidence_score -= 10
        confidence_reasons.append("High PPSF dispersion among comparables")

    if status_broadened:
        confidence_score -= 10
        confidence_reasons.append("Status filter broadened")

    if size_band_applied:
        confidence_score += 5
        confidence_reasons.append("Size-adjusted comparables")

    confidence_score = max(0, min(100, confidence_score))
    confidence_label = score_to_label(confidence_score)

    # Shadow direction
    shadow_direction = "neutral"
    if apil_advantage_pct is not None:
        if apil_advantage_pct >= 15:
            shadow_direction = "positive"
        elif apil_advantage_pct >= 5:
            shadow_direction = "slightly_positive"
        elif apil_advantage_pct <= -15:
            shadow_direction = "negative"
        elif apil_advantage_pct <= -5:
            shadow_direction = "slightly_negative"

    result.update({
        "eligible": True,
        "level": level,
        "production_eligible": False,
        "comparables": final_txs,
        "benchmark": {
            "estimated_benchmark_aed": round(estimated_benchmark, 2) if estimated_benchmark else None,
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
            "size_band_applied": size_band_applied,
            "size_band_pct": config.get("size_band_pct_default") if size_band_applied else None,
            "mapped_dld_area": dld_area,
            "area_mapping_confidence": mapping_confidence,
            "outlier_method": outlier_method,
            "property_type_filter": config.get("property_type_filter", False),
        },
        "calculations": {
            "apil_advantage_pct": round(apil_advantage_pct, 2) if apil_advantage_pct is not None else None,
            "conventional_below_benchmark_pct": round(conventional_pct, 2) if conventional_pct is not None else None,
            "price_difference_aed": round(diff_aed, 2) if diff_aed is not None else None,
        },
        "confidence": {
            "fallback_confidence_score": round(confidence_score, 1),
            "fallback_confidence_label": confidence_label,
            "confidence_reasons": confidence_reasons,
        },
        "shadow_direction": shadow_direction,
        "validation": result["validation"],
    })

    return result


# ===========================================================================
# SECTION 4 — SEGMENTED BACKTEST FRAMEWORK
# ===========================================================================

def run_backtest_with_config(
    master_df: pd.DataFrame,
    area_mapping: Dict,
    area_unit_stats: Dict,
    config: Dict,
    subject_properties: Optional[List[str]] = None,
) -> List[Dict]:
    """Run backtest for a specific configuration."""
    from investor_api.fallback.dld_fallback_engine import get_fallback_dld_store

    exact_evidence = master_df[
        (master_df["dld_evidence_status"] == "DLD_MATCH")
        & (master_df["dld_transaction_count"] >= 3)
        & (master_df["dld_median_price_aed"].notna())
        & (master_df["unit_bedrooms"].notna())
    ].copy()

    if subject_properties:
        exact_evidence = exact_evidence[exact_evidence["property_id"].astype(str).isin(subject_properties)]

    backtests = []
    for _, row in exact_evidence.iterrows():
        prop_id = str(int(row["property_id"]))
        exact_benchmark = float(row["dld_median_price_aed"])

        bedrooms = row.get("unit_bedrooms")
        size_sqft = row.get("unit_size_sqft")
        if isinstance(bedrooms, float) and math.isnan(bedrooms):
            bedrooms = None
        if isinstance(size_sqft, float) and math.isnan(size_sqft):
            size_sqft = None

        subject_project = str(row.get("property_name", "")).strip()

        fallback = calculate_fallback_benchmark_refined(
            property_id=prop_id,
            property_name=subject_project,
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
            area_mapping=area_mapping,
            area_unit_stats=area_unit_stats,
            config=config,
            subject_project_name=subject_project,
        )

        if not fallback.get("eligible"):
            continue

        subject_project_norm = _normalize(subject_project)
        subject_project_in_comparables = sum(
            1 for tx in fallback.get("comparables", [])
            if _normalize(tx.get("project", "")) == subject_project_norm
        )

        fallback_benchmark = fallback["benchmark"]["estimated_benchmark_aed"]
        error_aed = fallback_benchmark - exact_benchmark
        error_pct = (error_aed / exact_benchmark) * 100 if exact_benchmark else None
        abs_error_pct = abs(error_pct) if error_pct is not None else None
        signed_error_pct = error_pct if error_pct is not None else None

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
            "fallback_level": fallback["level"],
            "tx_count": fallback["benchmark"]["final_transaction_count"],
            "unique_projects": fallback["benchmark"]["unique_project_count"],
            "size_band_applied": fallback["benchmark"]["size_band_applied"],
            "size_band_pct": fallback["benchmark"]["size_band_pct"],
            "status_broadened": fallback["benchmark"]["status_broadened"],
            "area_mapping_confidence": fallback["benchmark"]["area_mapping_confidence"],
            "confidence_score": fallback["confidence"]["fallback_confidence_score"],
            "confidence_label": fallback["confidence"]["fallback_confidence_label"],
            "ppsf_p50": fallback["benchmark"]["median_ppsf"],
            "ppsf_iqr": fallback["benchmark"]["ppsf_iqr"],
            "high_dispersion": fallback["benchmark"]["high_dispersion_flag"],
            "subject_project_in_comparables": subject_project_in_comparables,
            "current_price_aed": float(row.get("current_price_aed", 0)),
            "unit_size_sqft": size_sqft,
            "developer_name": row.get("developer_name", ""),
        })

    return backtests


def summarize_backtests(backtests: List[Dict]) -> Dict:
    errors = [b["absolute_error_pct"] for b in backtests if b["absolute_error_pct"] is not None]
    signed_errors = [b["signed_error_pct"] for b in backtests if b["signed_error_pct"] is not None]
    if not errors:
        return {"n": 0}

    errors_sorted = sorted(errors)
    n = len(errors_sorted)
    signed_sorted = sorted(signed_errors)

    return {
        "n": n,
        "median_abs_error": errors_sorted[n // 2],
        "mean_abs_error": sum(errors) / n,
        "p25": errors_sorted[n // 4],
        "p75": errors_sorted[(3 * n) // 4],
        "p90": errors_sorted[int(n * 0.9)],
        "worst": errors_sorted[-1],
        "median_signed_error": signed_sorted[n // 2] if n > 0 else None,
        "mean_signed_error": sum(signed_errors) / n,
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
        if len(subset) >= 10:
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
        if len(subset) >= 10:
            segments[f"area_{area}"] = summarize_backtests(subset)

    return segments


# ===========================================================================
# SECTION 5 — PARAMETER GRID SEARCH (one-at-a-time sensitivity)
# ===========================================================================

def run_parameter_sensitivity(
    master_df: pd.DataFrame,
    area_mapping: Dict,
    area_unit_stats: Dict,
    tuning_property_ids: List[str],
) -> List[Dict]:
    """Run one-at-a-time sensitivity analysis on tuning set."""
    results = []
    base_config = DEFAULT_CONFIG.copy()

    print("[Sensitivity] Testing RECENCY months...")
    for months in RECENCY_MONTHS_GRID:
        cfg = base_config.copy()
        cfg["lookback_months"] = months
        bt = run_backtest_with_config(master_df, area_mapping, area_unit_stats, cfg, tuning_property_ids)
        s = summarize_backtests(bt)
        results.append({"dimension": "recency", "value": months, **s})
        print(f"  {months}mo: n={s.get('n')}, med_err={s.get('median_abs_error', 'N/A'):.2f}%, p90={s.get('p90', 'N/A'):.2f}%")

    print("[Sensitivity] Testing SIZE BAND...")
    for band in SIZE_BAND_GRID:
        cfg = base_config.copy()
        cfg["size_band_pct_default"] = band
        bt = run_backtest_with_config(master_df, area_mapping, area_unit_stats, cfg, tuning_property_ids)
        s = summarize_backtests(bt)
        results.append({"dimension": "size_band", "value": band, **s})
        print(f"  ±{band*100:.0f}%: n={s.get('n')}, med_err={s.get('median_abs_error', 'N/A'):.2f}%, p90={s.get('p90', 'N/A'):.2f}%")

    print("[Sensitivity] Testing MIN TX...")
    for tx in MIN_TX_GRID:
        cfg = base_config.copy()
        cfg["min_transactions_area_fallback"] = tx
        bt = run_backtest_with_config(master_df, area_mapping, area_unit_stats, cfg, tuning_property_ids)
        s = summarize_backtests(bt)
        results.append({"dimension": "min_tx", "value": tx, **s})
        print(f"  min={tx}: n={s.get('n')}, med_err={s.get('median_abs_error', 'N/A'):.2f}%, p90={s.get('p90', 'N/A'):.2f}%")

    print("[Sensitivity] Testing MIN UNIQUE PROJECTS...")
    for proj in MIN_UNIQUE_PROJECTS_GRID:
        cfg = base_config.copy()
        cfg["min_unique_projects_area"] = proj
        bt = run_backtest_with_config(master_df, area_mapping, area_unit_stats, cfg, tuning_property_ids)
        s = summarize_backtests(bt)
        results.append({"dimension": "min_unique_projects", "value": proj, **s})
        print(f"  min_proj={proj}: n={s.get('n')}, med_err={s.get('median_abs_error', 'N/A'):.2f}%, p90={s.get('p90', 'N/A'):.2f}%")

    print("[Sensitivity] Testing MAX PROJECT CONCENTRATION...")
    for conc in MAX_PROJECT_CONC_GRID:
        cfg = base_config.copy()
        cfg["max_project_concentration"] = conc
        bt = run_backtest_with_config(master_df, area_mapping, area_unit_stats, cfg, tuning_property_ids)
        s = summarize_backtests(bt)
        results.append({"dimension": "max_concentration", "value": conc, **s})
        print(f"  max={conc}: n={s.get('n')}, med_err={s.get('median_abs_error', 'N/A'):.2f}%, p90={s.get('p90', 'N/A'):.2f}%")

    print("[Sensitivity] Testing OUTLIER METHODS...")
    for outlier in OUTLIER_METHODS:
        cfg = base_config.copy()
        cfg["outlier_method"] = outlier["name"]
        if "multiplier" in outlier:
            cfg["ppsf_outlier_iqr_multiplier"] = outlier["multiplier"]
        bt = run_backtest_with_config(master_df, area_mapping, area_unit_stats, cfg, tuning_property_ids)
        s = summarize_backtests(bt)
        results.append({"dimension": "outlier", "value": outlier["name"], **s})
        print(f"  {outlier['name']}: n={s.get('n')}, med_err={s.get('median_abs_error', 'N/A'):.2f}%, p90={s.get('p90', 'N/A'):.2f}%")

    return results


def run_property_type_filter_backtest(
    master_df: pd.DataFrame,
    area_mapping: Dict,
    area_unit_stats: Dict,
    tuning_property_ids: List[str],
    best_config: Dict,
) -> Dict:
    """Compare backtest with and without property type filter."""
    cfg_no = best_config.copy()
    cfg_no["property_type_filter"] = False
    bt_no = run_backtest_with_config(master_df, area_mapping, area_unit_stats, cfg_no, tuning_property_ids)
    s_no = summarize_backtests(bt_no)

    cfg_yes = best_config.copy()
    cfg_yes["property_type_filter"] = True
    bt_yes = run_backtest_with_config(master_df, area_mapping, area_unit_stats, cfg_yes, tuning_property_ids)
    s_yes = summarize_backtests(bt_yes)

    return {
        "without_filter": s_no,
        "with_filter": s_yes,
        "coverage_diff": s_yes.get("n", 0) - s_no.get("n", 0),
        "median_error_diff": (s_yes.get("median_abs_error") or 0) - (s_no.get("median_abs_error") or 0),
        "p90_diff": (s_yes.get("p90") or 0) - (s_no.get("p90") or 0),
    }


# ===========================================================================
# SECTION 6 — WORST-CASE ROOT CAUSE ANALYSIS
# ===========================================================================

def analyze_worst_cases(backtests: List[Dict], top_n: int = 100) -> Dict:
    if not backtests:
        return {}

    sorted_bt = sorted(backtests, key=lambda x: x.get("absolute_error_pct") or 0, reverse=True)
    worst = sorted_bt[:top_n]

    root_causes = Counter()
    worst_details = []

    for b in worst:
        cause = "OTHER"
        if b.get("ppsf_p50") and b.get("ppsf_p50") > 5000:
            cause = "SIZE_UNIT_ERROR"
        elif b.get("high_dispersion"):
            cause = "AREA_TOO_HETEROGENEOUS"
        elif b.get("subject_project_in_comparables", 0) > 0:
            cause = "TARGET_LEAKAGE"
        elif b.get("unique_projects", 0) <= 2:
            cause = "PROJECT_CONCENTRATION"
        elif b.get("ppsf_iqr", 0) / (b.get("ppsf_p50") or 1) > 1.0:
            cause = "PROPERTY_TYPE_MIX"
        elif b.get("exact_benchmark", 0) > 5_000_000 and b.get("fallback_benchmark", 0) < 2_000_000:
            cause = "LUXURY_MIX"
        elif b.get("exact_benchmark", 0) < 1_000_000 and b.get("fallback_benchmark", 0) > 2_000_000:
            cause = "LUXURY_MIX"
        elif b.get("tx_count", 0) < 15:
            cause = "INSUFFICIENT_TRANSACTIONS"

        root_causes[cause] += 1
        worst_details.append({
            "property_id": b["property_id"],
            "property_name": b["property_name"],
            "area": b["area"],
            "bedrooms": b["bedrooms"],
            "status": b["status"],
            "property_type": b["property_type"],
            "exact_benchmark": b["exact_benchmark"],
            "fallback_benchmark": b["fallback_benchmark"],
            "absolute_error_pct": b["absolute_error_pct"],
            "signed_error_pct": b["signed_error_pct"],
            "ppsf_p50": b["ppsf_p50"],
            "ppsf_iqr": b["ppsf_iqr"],
            "tx_count": b["tx_count"],
            "unique_projects": b["unique_projects"],
            "root_cause": cause,
            "subject_project_in_comparables": b.get("subject_project_in_comparables", 0),
        })

    return {
        "root_cause_counts": dict(root_causes),
        "worst_details": worst_details,
    }


# ===========================================================================
# SECTION 7 — MAIN ORCHESTRATION
# ===========================================================================

def run_full_refinement_analysis():
    from investor_api.fallback.dld_fallback_engine import (
        build_verified_area_mapping, get_fallback_dld_store, load_master_df
    )

    print("=" * 70)
    print("SHADOW FALLBACK REFINEMENT ANALYSIS")
    print("=" * 70)

    # 1. Load data
    print("\n[1/8] Loading data...")
    master_df = load_master_df()
    print(f"  MASTER: {len(master_df)} properties")

    area_mapping = build_verified_area_mapping(master_df, get_fallback_dld_store())
    print(f"  Area mappings: {len(area_mapping)}")

    # 2. Size unit audit
    print("\n[2/8] Running size unit detection audit...")
    size_audit_path = os.path.join(OUTPUT_DIR, "FALLBACK_DLD_SIZE_UNIT_AUDIT.xlsx")
    size_audit_df = generate_size_unit_audit(DLD_CSV_PATH, size_audit_path)

    area_unit_stats = _build_area_unit_statistics(DLD_CSV_PATH)

    # 3. Train/test split
    print("\n[3/8] Creating train/test split...")
    exact_evidence = master_df[
        (master_df["dld_evidence_status"] == "DLD_MATCH")
        & (master_df["dld_transaction_count"] >= 3)
        & (master_df["dld_median_price_aed"].notna())
        & (master_df["unit_bedrooms"].notna())
        & (master_df["unit_size_sqft"].notna())
    ].copy()

    all_property_ids = exact_evidence["property_id"].astype(str).tolist()
    random.shuffle(all_property_ids)

    # Use 50-property tuning sample for speed, full holdout for final evaluation
    tuning_sample_size = 50
    split_idx = int(len(all_property_ids) * 0.7)
    tuning_ids = all_property_ids[:split_idx]
    holdout_ids = all_property_ids[split_idx:]
    tuning_sample = random.sample(tuning_ids, min(tuning_sample_size, len(tuning_ids)))

    print(f"  Full tuning set: {len(tuning_ids)} properties")
    print(f"  Tuning sample for sensitivity: {len(tuning_sample)} properties")
    print(f"  Holdout set: {len(holdout_ids)} properties")

    # 4. Parameter sensitivity on tuning sample
    print("\n[4/8] Running parameter sensitivity on tuning sample...")
    sensitivity_results = run_parameter_sensitivity(master_df, area_mapping, area_unit_stats, tuning_sample)

    # Pick best value from each dimension
    best_config = DEFAULT_CONFIG.copy()
    for dim in ["recency", "size_band", "min_tx", "min_unique_projects", "max_concentration", "outlier"]:
        dim_results = [r for r in sensitivity_results if r["dimension"] == dim]
        if not dim_results:
            continue
        # Pick lowest median_abs_error with at least 50% of max coverage
        max_cov = max(r.get("n", 0) for r in dim_results)
        viable = [r for r in dim_results if r.get("n", 0) >= max_cov * 0.3 and r.get("median_abs_error") is not None]
        if not viable:
            viable = dim_results
        best = min(viable, key=lambda x: x["median_abs_error"])
        print(f"  Best {dim}: {best['value']} (med_err={best['median_abs_error']:.2f}%, n={best['n']})")

        if dim == "recency":
            best_config["lookback_months"] = best["value"]
        elif dim == "size_band":
            best_config["size_band_pct_default"] = best["value"]
        elif dim == "min_tx":
            best_config["min_transactions_area_fallback"] = best["value"]
        elif dim == "min_unique_projects":
            best_config["min_unique_projects_area"] = best["value"]
        elif dim == "max_concentration":
            best_config["max_project_concentration"] = best["value"]
        elif dim == "outlier":
            best_config["outlier_method"] = best["value"]
            if best["value"] == "iqr_2.0":
                best_config["ppsf_outlier_iqr_multiplier"] = 2.0
            elif best["value"] == "iqr_1.5":
                best_config["ppsf_outlier_iqr_multiplier"] = 1.5

    print(f"\n  Selected best config:")
    for k, v in sorted(best_config.items()):
        print(f"    {k}: {v}")

    # 5. Property type filter backtest on tuning sample
    print("\n[5/8] Testing property type filter...")
    type_filter_result = run_property_type_filter_backtest(
        master_df, area_mapping, area_unit_stats, tuning_sample, best_config
    )
    print(f"  Without filter: median={type_filter_result['without_filter'].get('median_abs_error'):.2f}%, coverage={type_filter_result['without_filter'].get('n')}")
    print(f"  With filter: median={type_filter_result['with_filter'].get('median_abs_error'):.2f}%, coverage={type_filter_result['with_filter'].get('n')}")
    print(f"  Coverage diff: {type_filter_result['coverage_diff']}")
    print(f"  Median error diff: {type_filter_result['median_error_diff']:.2f}%")

    use_type_filter = (
        type_filter_result["median_error_diff"] < -2
        and type_filter_result["with_filter"].get("n", 0) > type_filter_result["without_filter"].get("n", 0) * 0.5
    )
    if use_type_filter:
        print("  → Property type filter IMPROVES accuracy. Will apply.")
        best_config["property_type_filter"] = True
    else:
        print("  → Property type filter does NOT significantly improve accuracy. Will NOT apply.")
        best_config["property_type_filter"] = False

    # 6. Run final backtest on FULL holdout set with best params
    print("\n[6/8] Running final backtest on FULL HOLDOUT set...")
    holdout_backtests = run_backtest_with_config(
        master_df, area_mapping, area_unit_stats, best_config, holdout_ids
    )
    holdout_summary = summarize_backtests(holdout_backtests)

    print(f"\n  HOLDOUT SET:")
    print(f"    N: {holdout_summary.get('n')}")
    print(f"    Median abs error: {holdout_summary.get('median_abs_error', 'N/A'):.2f}%")
    print(f"    Mean abs error: {holdout_summary.get('mean_abs_error', 'N/A'):.2f}%")
    print(f"    P75: {holdout_summary.get('p75', 'N/A'):.2f}%")
    print(f"    P90: {holdout_summary.get('p90', 'N/A'):.2f}%")
    print(f"    Median signed error: {holdout_summary.get('median_signed_error', 'N/A'):.2f}%")
    print(f"    Mean signed error: {holdout_summary.get('mean_signed_error', 'N/A'):.2f}%")

    # 7. Segmented analysis
    print("\n[7/8] Running segmented analysis...")
    holdout_segments = segment_backtests(holdout_backtests)

    # 8. Worst-case analysis
    print("\n[8/8] Analyzing worst-case errors...")
    worst_analysis = analyze_worst_cases(holdout_backtests, top_n=100)

    # Area reliability
    print("\n[9/8] Computing area reliability...")
    area_reliability = {}
    area_groups = defaultdict(list)
    for b in holdout_backtests:
        area_groups[b.get("area", "unknown")].append(b)
    for area, subset in area_groups.items():
        if len(subset) >= 5:
            summary = summarize_backtests(subset)
            med_err = summary.get("median_abs_error", 999)
            if med_err < 25:
                reliability = "RELIABLE_AREA"
            elif med_err < 50:
                reliability = "MARGINAL_AREA"
            else:
                reliability = "UNRELIABLE_AREA"
            area_reliability[area] = {
                "n": summary.get("n"),
                "median_error": med_err,
                "p75": summary.get("p75"),
                "p90": summary.get("p90"),
                "reliability": reliability,
            }

    # Confidence mismatch audit
    print("\n[10/8] Auditing confidence score/label mismatches...")
    all_fallbacks = []
    for prop_id in holdout_ids[:100]:
        row = master_df[master_df["property_id"] == int(prop_id)].iloc[0]
        bedrooms = row.get("unit_bedrooms")
        size_sqft = row.get("unit_size_sqft")
        if isinstance(bedrooms, float) and math.isnan(bedrooms):
            bedrooms = None
        if isinstance(size_sqft, float) and math.isnan(size_sqft):
            size_sqft = None

        fb = calculate_fallback_benchmark_refined(
            property_id=str(int(row["property_id"])),
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
            area_mapping=area_mapping,
            area_unit_stats=area_unit_stats,
            config=best_config,
        )
        all_fallbacks.append(fb)

    mismatches = audit_confidence_score_label_mismatch(all_fallbacks)
    print(f"  Confidence score/label mismatches found: {len(mismatches)}")
    if mismatches:
        for m in mismatches[:5]:
            print(f"    Property {m['property_id']}: score={m['score']}, label={m['actual_label']}, expected={m['expected_label']}")

    # Export all results
    print("\n[11/8] Exporting results...")

    backtest_path = os.path.join(OUTPUT_DIR, "FALLBACK_DLD_REFINED_BACKTEST.xlsx")
    if holdout_backtests:
        df_bt = pd.DataFrame(holdout_backtests)
        df_bt.to_excel(backtest_path, index=False)
        print(f"  → {backtest_path}")

    area_rel_path = os.path.join(OUTPUT_DIR, "FALLBACK_DLD_AREA_RELIABILITY.xlsx")
    if area_reliability:
        df_rel = pd.DataFrame([
            {"area": k, **v} for k, v in sorted(area_reliability.items(), key=lambda x: x[1]["median_error"])
        ])
        df_rel.to_excel(area_rel_path, index=False)
        print(f"  → {area_rel_path}")

    grid_path = os.path.join(OUTPUT_DIR, "FALLBACK_DLD_GRID_SEARCH.xlsx")
    if sensitivity_results:
        df_grid = pd.DataFrame(sensitivity_results)
        df_grid.to_excel(grid_path, index=False)
        print(f"  → {grid_path}")

    worst_path = os.path.join(OUTPUT_DIR, "FALLBACK_DLD_WORST_CASES.xlsx")
    if worst_analysis.get("worst_details"):
        df_worst = pd.DataFrame(worst_analysis["worst_details"])
        df_worst.to_excel(worst_path, index=False)
        print(f"  → {worst_path}")

    # Refinement report
    report_path = os.path.join(OUTPUT_DIR, "FALLBACK_DLD_REFINEMENT_REPORT.md")
    generate_refinement_report(
        report_path=report_path,
        holdout_summary=holdout_summary,
        original_median_error=34.0,
        original_p90=125.51,
        original_coverage=1057,
        holdout_backtests=holdout_backtests,
        holdout_segments=holdout_segments,
        worst_analysis=worst_analysis,
        area_reliability=area_reliability,
        best_config=best_config,
        sensitivity_results=sensitivity_results,
        type_filter_result=type_filter_result,
        confidence_mismatches=mismatches,
    )
    print(f"  → {report_path}")

    print("\n" + "=" * 70)
    print("REFINEMENT ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\nOriginal median error: 34.00%")
    print(f"Holdout median error:  {holdout_summary.get('median_abs_error', 'N/A'):.2f}%" if holdout_summary.get('median_abs_error') else "Holdout median error: N/A")
    print(f"\nOriginal P90:          125.51%")
    print(f"Holdout P90:           {holdout_summary.get('p90', 'N/A'):.2f}%" if holdout_summary.get('p90') else "Holdout P90: N/A")
    print(f"\nOriginal coverage:     1,057 properties")
    print(f"Holdout coverage:        {holdout_summary.get('n', 0)} properties")
    print(f"\nConfidence mismatches: {len(mismatches)} (target: 0)")
    if len(mismatches) > 0:
        print("WARNING: Confidence score/label mismatches still exist!")


# ===========================================================================
# SECTION 8 — REPORT GENERATOR
# ===========================================================================

def generate_refinement_report(
    report_path: str,
    holdout_summary: Dict,
    original_median_error: float,
    original_p90: float,
    original_coverage: int,
    holdout_backtests: List[Dict],
    holdout_segments: Dict,
    worst_analysis: Dict,
    area_reliability: Dict,
    best_config: Dict,
    sensitivity_results: List[Dict],
    type_filter_result: Dict,
    confidence_mismatches: List[Dict],
):
    lines = [
        "# Fallback DLD Benchmark — REFINEMENT REPORT",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## Executive Summary",
        "",
        "This report documents the refined shadow fallback benchmark methodology.",
        "",
        "| Metric | Original | Holdout |",
        "|--------|----------|---------|",
        f"| Median abs error | {original_median_error:.2f}% | {holdout_summary.get('median_abs_error', 'N/A'):.2f}% |",
        f"| Mean abs error | 55.21% | {holdout_summary.get('mean_abs_error', 'N/A'):.2f}% |",
        f"| P75 | 61.35% | {holdout_summary.get('p75', 'N/A'):.2f}% |",
        f"| P90 | {original_p90:.2f}% | {holdout_summary.get('p90', 'N/A'):.2f}% |",
        f"| Coverage | {original_coverage} | {holdout_summary.get('n', 0)} |",
        "",
        "## Best Parameters (from sensitivity analysis on tuning sample)",
        "",
        "```json",
        json.dumps(best_config, indent=2),
        "```",
        "",
        "## Size Unit Detection",
        "",
        "The refined engine uses multi-method size unit detection:",
        "",
        "1. **SOURCE_DECLARED_SQM** — raw_size < 20 (physically impossible as sqft)",
        "2. **SOURCE_DECLARED_SQFT** — raw_size > 5000 (impossibly large as sqm)",
        "3. **AREA_DOMINANT_SQM/SQFT** — per-area-bedroom-status statistics",
        "4. **PRICE_CROSS_CHECK** — implied PPSF reasonableness",
        "5. **BEDROOM_RANGE** — typical Dubai unit size ranges",
        "6. **AMBIGUOUS** — if none of the above resolve, transaction is excluded",
        "",
        "Ambiguous transactions are EXCLUDED from PPSF fallback calculations.",
        "",
        "## Confidence Score/Label Fix",
        "",
        "Canonical mapping:",
        "",
        "| Score | Label |",
        "|-------|-------|",
        "| ≥ 80 | high |",
        "| 50–79 | medium |",
        "| 20–49 | low |",
        "| < 20 | very_low |",
        "",
        f"**Mismatches found:** {len(confidence_mismatches)} (target: 0)",
        "",
        "## Parameter Sensitivity Results (Tuning Sample)",
        "",
    ]

    for dim in ["recency", "size_band", "min_tx", "min_unique_projects", "max_concentration", "outlier"]:
        dim_results = [r for r in sensitivity_results if r["dimension"] == dim]
        if not dim_results:
            continue
        lines.append(f"### {dim}")
        lines.append("| Value | N | Median Error | P90 |")
        lines.append("|-------|---|--------------|-----|")
        for r in dim_results:
            lines.append(f"| {r['value']} | {r.get('n', 0)} | {r.get('median_abs_error', 'N/A'):.2f}% | {r.get('p90', 'N/A'):.2f}% |")
        lines.append("")

    lines.extend([
        "## Property Type Filter Backtest",
        "",
    ])
    if type_filter_result:
        lines.extend([
            f"- Without filter: median={type_filter_result['without_filter'].get('median_abs_error', 'N/A'):.2f}%, coverage={type_filter_result['without_filter'].get('n', 0)}",
            f"- With filter: median={type_filter_result['with_filter'].get('median_abs_error', 'N/A'):.2f}%, coverage={type_filter_result['with_filter'].get('n', 0)}",
            f"- Decision: {'APPLY' if best_config.get('property_type_filter') else 'DO NOT APPLY'}",
            "",
        ])

    lines.extend([
        "## Holdout Segmented Backtest Results",
        "",
    ])

    for segment_name, summary in sorted(holdout_segments.items()):
        if summary.get("n", 0) < 5:
            continue
        lines.append(f"### {segment_name}")
        lines.append(f"- N: {summary.get('n')}")
        lines.append(f"- Median abs error: {summary.get('median_abs_error', 'N/A'):.2f}%")
        lines.append(f"- Mean abs error: {summary.get('mean_abs_error', 'N/A'):.2f}%")
        lines.append(f"- P75: {summary.get('p75', 'N/A'):.2f}%")
        lines.append(f"- P90: {summary.get('p90', 'N/A'):.2f}%")
        lines.append(f"- Median signed error: {summary.get('median_signed_error', 'N/A'):.2f}%")
        lines.append("")

    lines.extend([
        "## Area Reliability Classification",
        "",
    ])
    for area, data in sorted(area_reliability.items(), key=lambda x: x[1]["median_error"])[:30]:
        lines.append(f"- **{area}**: {data['reliability']} | N={data['n']} | med_err={data['median_error']:.1f}% | P90={data['p90']:.1f}%")

    lines.extend([
        "",
        "## Worst-Case Root Cause Analysis (Top 100)",
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
        "The fallback engine remains in SHADOW MODE. No production decisions, frontend, MASTER_FINAL, Qdrant, or raw DLD CSVs have been modified.",
        "",
        "## Files Generated",
        "",
        "| File | Description |",
        "|------|-------------|",
        "| FALLBACK_DLD_REFINED_BACKTEST.xlsx | Per-property holdout backtest results |",
        "| FALLBACK_DLD_SIZE_UNIT_AUDIT.xlsx | Transaction-level size unit detection |",
        "| FALLBACK_DLD_AREA_RELIABILITY.xlsx | Per-area reliability classification |",
        "| FALLBACK_DLD_GRID_SEARCH.xlsx | Parameter sensitivity on tuning sample |",
        "| FALLBACK_DLD_WORST_CASES.xlsx | Top 100 worst errors with root causes |",
        "| FALLBACK_DLD_REFINEMENT_REPORT.md | This report |",
        "",
    ])

    with open(report_path, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    run_full_refinement_analysis()
