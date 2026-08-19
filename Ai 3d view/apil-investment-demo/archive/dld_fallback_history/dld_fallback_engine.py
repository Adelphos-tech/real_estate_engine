"""
Shadow Fallback Benchmark Engine — Backend-Only
================================================
Calculates INDICATIVE fallback benchmarks for properties with insufficient
exact-project DLD evidence.  Runs in SHADOW MODE — does NOT affect
production investment signals or frontend UI.

Hierarchy:
    LEVEL 1 — EXACT_PROJECT_SAME_BEDROOM_EVIDENCE (existing, unchanged)
    LEVEL 2 — EXACT_PROJECT_STATUS_BROADENED_EVIDENCE
    LEVEL 3 — AREA_SAME_BEDROOM_SIZE_ADJUSTED_EVIDENCE
    LEVEL 4 — AREA_SAME_BEDROOM_EVIDENCE
    LEVEL 5 — NO_VERIFIED_FALLBACK_EVIDENCE

Rules:
    * Never fabricate transactions
    * All calculations based on traceable real DLD records
    * production_eligible = false until explicit user approval
    * Does not modify MASTER_FINAL.xlsx, Qdrant, or raw DLD CSVs
"""

import csv
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from statistics import median
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

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

# ---------------------------------------------------------------------------
# Configuration — AUDITABLE, not hard-coded blindly
# ---------------------------------------------------------------------------
MIN_TRANSACTION_VALUE = 100_000
FALLBACK_CONFIG = {
    "min_transactions_area_fallback": 8,          # will be backtested
    "size_band_pct_default": 0.25,              # ±25% — will be backtested
    "max_project_concentration": 0.60,         # single project ≤ 60% of tx
    "lookback_months": 36,                     # 36 months — will be backtested
    "min_unique_projects_area": 2,             # will be backtested
    "ppsf_outlier_iqr_multiplier": 1.5,        # IQR-based outlier removal
}

# Dubai-only areas (non-Dubai areas excluded from Dubai DLD fallback)
NON_DUBAI_AREAS = {
    "umm al daman", "sharjah waterfront city", "sharjah garden city"
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(text: Optional[str]) -> str:
    """Strip, lower, collapse whitespace, remove punctuation except alphanumeric."""
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
    """Parse bedroom count from DLD ROOMS_EN field."""
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


def _iqr_outlier_bounds(values: List[float], multiplier: float = 1.5) -> Tuple[float, float]:
    """Return (lower_bound, upper_bound) using IQR outlier detection."""
    if len(values) < 4:
        return (float("-inf"), float("inf"))
    s = sorted(values)
    n = len(s)
    q1 = s[n // 4] if n >= 4 else s[0]
    q3 = s[(3 * n) // 4] if n >= 4 else s[-1]
    iqr = q3 - q1
    return (q1 - multiplier * iqr, q3 + multiplier * iqr)


def _median_abs_deviation(values: List[float]) -> float:
    """Calculate MAD (Median Absolute Deviation)."""
    if not values:
        return 0.0
    med = median(values)
    abs_devs = [abs(v - med) for v in values]
    return median(abs_devs) if abs_devs else 0.0


def _detect_size_unit_and_convert(size: float, bedrooms: Optional[int]) -> float:
    """
    Detect whether ACTUAL_AREA is in sqft or sqm and convert to sqft.

    Heuristic based on Dubai real estate norms:
    - Studios: ~400–600 sqft (~40–60 sqm)
    - 1BR: ~700–1,000 sqft (~70–100 sqm)
    - 2BR: ~1,000–1,500 sqft (~100–140 sqm)
    - 3BR: ~1,500–2,500 sqft (~140–230 sqm)
    """
    if size is None or size <= 0:
        return size

    # If already large, assume sqft
    if size >= 1000:
        return size

    # If very small, assume sqm
    if size < 200:
        return size * 10.764

    # Middle range: use bedroom count as additional signal
    threshold_sqm = {
        0: 300,   # studio: < 300 → sqm
        1: 400,   # 1BR: < 400 → sqm
        2: 600,   # 2BR: < 600 → sqm
        3: 800,   # 3BR: < 800 → sqm
    }
    thresh = threshold_sqm.get(bedrooms, 800)
    if size < thresh:
        return size * 10.764

    return size


# ---------------------------------------------------------------------------
# DLD Area Store — indexed by area (complement to existing project-level store)
# ---------------------------------------------------------------------------

class DLDAreaStore:
    """In-memory index of DLD transactions keyed by normalized AREA_EN."""

    def __init__(self, csv_path: str = DLD_CSV_PATH):
        self.csv_path = csv_path
        self._areas: Dict[str, List[Dict]] = defaultdict(list)
        self._loaded = False
        self._load()

    def _load(self):
        if self._loaded:
            return
        if not os.path.exists(self.csv_path):
            print(f"[FallbackDLD] WARNING: DLD CSV not found at {self.csv_path}")
            self._loaded = True
            return

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                area_raw = row.get("AREA_EN", "")
                if not area_raw:
                    continue
                area_norm = _normalize(area_raw)
                if not area_norm:
                    continue
                self._areas[area_norm].append(row)

        self._loaded = True
        total = sum(len(v) for v in self._areas.values())
        print(f"[FallbackDLD] Loaded {total} transactions across {len(self._areas)} areas")

    def get_area_transactions(self, area_name: str) -> List[Dict]:
        return self._areas.get(_normalize(area_name), [])

    def list_areas(self) -> List[str]:
        return sorted(self._areas.keys())

    def get_transaction(self, tx_number: str) -> Optional[Dict]:
        for area_txs in self._areas.values():
            for tx in area_txs:
                if tx.get("TRANSACTION_NUMBER") == tx_number:
                    return tx
        return None


# Global singleton
_FALLBACK_DLD_STORE: Optional[DLDAreaStore] = None


def get_fallback_dld_store() -> DLDAreaStore:
    global _FALLBACK_DLD_STORE
    if _FALLBACK_DLD_STORE is None:
        _FALLBACK_DLD_STORE = DLDAreaStore()
    return _FALLBACK_DLD_STORE


def reload_fallback_dld_store(csv_path: str = DLD_CSV_PATH) -> DLDAreaStore:
    global _FALLBACK_DLD_STORE
    _FALLBACK_DLD_STORE = DLDAreaStore(csv_path)
    return _FALLBACK_DLD_STORE


# ---------------------------------------------------------------------------
# MASTER Loader
# ---------------------------------------------------------------------------

def load_master_df(path: str = MASTER_PATH) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"MASTER_FINAL not found: {path}")
    df = pd.read_excel(path)
    return df


# ---------------------------------------------------------------------------
# Verified Area Mapping Builder
# ---------------------------------------------------------------------------

def build_verified_area_mapping(
    master_df: pd.DataFrame,
    dld_store: DLDAreaStore,
) -> Dict[str, Dict]:
    """
    Build a verified MASTER area → DLD area mapping using properties
    that have strong exact-project DLD matches.

    Returns:
        {
            master_area: {
                "dld_area": str,
                "supporting_exact_project_count": int,
                "supporting_property_ids": List[int],
                "confidence": str,  # "high" | "medium" | "low"
            }
        }
    """
    mapping: Dict[str, Dict] = {}

    # Reuse existing DLD project store
    from investor_api.dld_benchmark_engine import _DLD_STORE as project_store

    # Filter to properties with strong exact-project DLD evidence
    strong_evidence = master_df[
        (master_df["dld_evidence_status"] == "DLD_MATCH")
        & (master_df["dld_transaction_count"] >= 5)
        & (master_df["normalized_project_name"].notna())
        & (master_df["normalized_project_name"] != "")
    ].copy()

    for _, row in strong_evidence.iterrows():
        master_area = str(row.get("area", "")).strip()
        if not master_area:
            continue
        master_area_norm = _normalize(master_area)

        # Look up the project's DLD transactions to infer DLD area
        proj_name = str(row.get("normalized_project_name", "")).strip()
        if not proj_name:
            continue

        proj_txs = project_store.get_transactions(proj_name)

        if not proj_txs:
            continue

        # Count DLD areas for this project's transactions
        dld_area_counts = Counter()
        for tx in proj_txs:
            dld_area = str(tx.get("AREA_EN", "")).strip().upper()
            if dld_area:
                dld_area_counts[dld_area] += 1

        if not dld_area_counts:
            continue

        # Take the majority DLD area
        majority_dld_area, count = dld_area_counts.most_common(1)[0]
        total_proj_tx = len(proj_txs)
        confidence = "high" if count / total_proj_tx >= 0.8 else ("medium" if count / total_proj_tx >= 0.5 else "low")

        # Normalize master area key
        if master_area_norm not in mapping:
            mapping[master_area_norm] = {
                "dld_area": majority_dld_area,
                "supporting_exact_project_count": 0,
                "supporting_property_ids": [],
                "confidence": confidence,
            }
        mapping[master_area_norm]["supporting_exact_project_count"] += 1
        mapping[master_area_norm]["supporting_property_ids"].append(int(row["property_id"]))

    # Upgrade confidence based on supporting count
    for master_area, data in mapping.items():
        if data["supporting_exact_project_count"] >= 10:
            data["confidence"] = "high"
        elif data["supporting_exact_project_count"] >= 3:
            data["confidence"] = "medium"
        else:
            data["confidence"] = "low"
        data["supporting_property_ids"] = list(set(data["supporting_property_ids"]))

    return mapping


# ---------------------------------------------------------------------------
# Fallback Benchmark Calculator
# ---------------------------------------------------------------------------

def calculate_fallback_benchmark(
    property_id: str,
    property_name: str,
    area: str,
    developer_name: str,
    current_price_aed: float,
    unit_bedrooms: Optional[int],
    unit_bathrooms: Optional[int],
    unit_size_sqft: Optional[float],
    unit_size_sqm: Optional[float],
    unit_status: str,
    property_type: Optional[str],
    bedroom_value_status: str,
    dld_evidence_status: str,
    area_mapping: Optional[Dict[str, Dict]] = None,
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Calculate a SHADOW fallback benchmark for a property with insufficient
    exact-project evidence.

    Returns a structured dict that is NOT connected to production decisions.
    """
    if config is None:
        config = FALLBACK_CONFIG

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

    # ── Hard exclusion checks ──
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

    # ── Area mapping ──
    if area_mapping is None:
        # Build on-the-fly (slow but defensive)
        master_df = load_master_df()
        area_mapping = build_verified_area_mapping(master_df, get_fallback_dld_store())

    mapped = area_mapping.get(area_norm)
    if not mapped:
        result["validation"]["excluded_reasons"].append("NO_VERIFIED_AREA_MAPPING")
        result["level"] = "NO_VERIFIED_AREA_MAPPING"
        return result

    dld_area = mapped["dld_area"]
    mapping_confidence = mapped.get("confidence", "low")

    # ── Load comparable transactions ──
    dld_store = get_fallback_dld_store()
    area_txs = dld_store.get_area_transactions(dld_area)

    if not area_txs:
        result["validation"]["excluded_reasons"].append("NO_DLD_TRANSACTIONS_IN_MAPPED_AREA")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    # ── Canonical status ──
    from investor_api.dld_benchmark_engine import _canonical_status
    canonical_status, _ = _canonical_status(unit_status)

    # ── Filter by bedroom ──
    bedroom_filtered = []
    for tx in area_txs:
        tx_br = _parse_bedrooms(tx.get("ROOMS_EN"))
        if tx_br is not None and tx_br == int(unit_bedrooms):
            bedroom_filtered.append(tx)

    if not bedroom_filtered:
        result["validation"]["excluded_reasons"].append("NO_SAME_BEDROOM_TRANSACTIONS_IN_AREA")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    # ── Filter by status ──
    status_filtered = []
    status_broadened = False
    for tx in bedroom_filtered:
        tx_status = _canonical_status(tx.get("PROCEDURE_EN", ""))[0]
        if tx_status == canonical_status:
            status_filtered.append(tx)

    if not status_filtered:
        # Try status-broadened fallback
        for tx in bedroom_filtered:
            status_filtered.append(tx)
        status_broadened = True

    if not status_filtered:
        result["validation"]["excluded_reasons"].append("NO_STATUS_MATCHING_TRANSACTIONS")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    # ── Parse transactions with PPSF ──
    parsed = []
    sqm_converted_count = 0
    for tx in status_filtered:
        price = _parse_price(tx.get("TRANS_VALUE"))
        raw_size = _parse_size(tx.get("ACTUAL_AREA"))
        tx_date = _parse_date(tx.get("INSTANCE_DATE"))
        tx_bedrooms = _parse_bedrooms(tx.get("ROOMS_EN"))

        if price is None or price <= 0:
            result["validation"]["quality_flags"].append(f"invalid_price:{tx.get('TRANSACTION_NUMBER')}")
            continue
        if raw_size is None or raw_size <= 0:
            result["validation"]["quality_flags"].append(f"invalid_size:{tx.get('TRANSACTION_NUMBER')}")
            continue

        size = _detect_size_unit_and_convert(raw_size, tx_bedrooms)
        if size != raw_size:
            sqm_converted_count += 1

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
        })

    if sqm_converted_count > 0:
        result["validation"]["quality_flags"].append(f"SQM_CONVERTED_TO_SQFT:{sqm_converted_count}")

    if not parsed:
        result["validation"]["excluded_reasons"].append("ALL_TRANSACTIONS_INVALID_AFTER_PARSING")
        result["level"] = "NO_VERIFIED_FALLBACK_EVIDENCE"
        return result

    # ── Recency filter ──
    lookback_months = config.get("lookback_months", 36)
    cutoff_date = datetime.now() - pd.DateOffset(months=lookback_months)
    recent = [tx for tx in parsed if tx["date"] is not None and tx["date"] >= cutoff_date]
    if len(recent) >= config.get("min_transactions_area_fallback", 8):
        parsed = recent
    else:
        result["validation"]["quality_flags"].append(f"INSUFFICIENT_RECENT_TX_USING_ALL_{len(parsed)}")

    raw_tx_count = len(parsed)

    # ── Size band filter (if subject size known) ──
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

    # ── Outlier removal on PPSF ──
    ppsf_values = [tx["ppsf"] for tx in parsed]
    lower_bound, upper_bound = _iqr_outlier_bounds(
        ppsf_values, config.get("ppsf_outlier_iqr_multiplier", 1.5)
    )
    final_txs = []
    outliers = []
    for tx in parsed:
        if lower_bound <= tx["ppsf"] <= upper_bound:
            final_txs.append(tx)
        else:
            outliers.append(tx)

    if outliers:
        result["validation"]["quality_flags"].append(
            f"PPSF_OUTLIERS_REMOVED:{len(outliers)}(IQR_{lower_bound:.0f}-{upper_bound:.0f})"
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

    # ── Project diversity ──
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

    # ── Calculate PPSF statistics ──
    final_ppsf = [tx["ppsf"] for tx in final_txs]
    final_ppsf_sorted = sorted(final_ppsf)
    n = len(final_ppsf_sorted)

    ppsf_p25 = final_ppsf_sorted[n // 4] if n >= 4 else final_ppsf_sorted[0]
    ppsf_p50 = median(final_ppsf)
    ppsf_p75 = final_ppsf_sorted[(3 * n) // 4] if n >= 4 else final_ppsf_sorted[-1]
    ppsf_mean = sum(final_ppsf) / n
    mad = _median_abs_deviation(final_ppsf)
    iqr = ppsf_p75 - ppsf_p25

    high_dispersion = iqr / ppsf_p50 > 0.5 if ppsf_p50 > 0 else False

    # ── Estimated benchmark ──
    if unit_size_sqft is not None and unit_size_sqft > 0:
        estimated_benchmark = ppsf_p50 * unit_size_sqft
    else:
        estimated_benchmark = ppsf_p50 * 1000  # rough fallback if size missing
        result["validation"]["quality_flags"].append("MISSING_SIZE_USED_DEFAULT_1000SQFT")

    # ── APIL and Conventional percentages ──
    diff_aed = estimated_benchmark - current_price_aed
    apil_advantage_pct = (diff_aed / current_price_aed) * 100 if current_price_aed else None
    conventional_pct = (diff_aed / estimated_benchmark) * 100 if estimated_benchmark else None

    # ── Determine fallback level ──
    if size_band_applied and status_broadened:
        level = "EXACT_PROJECT_STATUS_BROADENED_EVIDENCE"
    elif size_band_applied and not status_broadened:
        level = "AREA_SAME_BEDROOM_SIZE_ADJUSTED_EVIDENCE"
    elif not size_band_applied and not status_broadened:
        level = "AREA_SAME_BEDROOM_EVIDENCE"
    else:
        level = "AREA_SAME_BEDROOM_EVIDENCE"

    # ── Fallback confidence model ──
    confidence_score = 0.0
    confidence_reasons = []

    # Base by level
    if level == "AREA_SAME_BEDROOM_SIZE_ADJUSTED_EVIDENCE":
        confidence_score += 40
        confidence_reasons.append("Area-level size-adjusted evidence")
    elif level == "AREA_SAME_BEDROOM_EVIDENCE":
        confidence_score += 30
        confidence_reasons.append("Area-level bedroom-matched evidence")
    elif level == "EXACT_PROJECT_STATUS_BROADENED_EVIDENCE":
        confidence_score += 50
        confidence_reasons.append("Exact project status-broadened evidence")
    else:
        confidence_score += 20
        confidence_reasons.append("Lower hierarchy fallback")

    # Transaction count
    if final_tx_count >= 15:
        confidence_score += 25
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

    # Area mapping confidence
    if mapping_confidence == "high":
        confidence_score += 15
        confidence_reasons.append("High-confidence area mapping")
    elif mapping_confidence == "medium":
        confidence_score += 5
        confidence_reasons.append("Medium-confidence area mapping")
    else:
        confidence_score -= 10
        confidence_reasons.append("Low-confidence area mapping")

    # Project diversity
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
        confidence_reasons.append(f"Single-project concentration")

    # Concentration penalty
    if largest_share > max_conc:
        confidence_score -= 15
        confidence_reasons.append(f"High project concentration ({largest_share:.1%})")

    # Dispersion penalty
    if high_dispersion:
        confidence_score -= 10
        confidence_reasons.append("High PPSF dispersion among comparables")

    # Status broadening penalty
    if status_broadened:
        confidence_score -= 10
        confidence_reasons.append("Status filter broadened")

    # Size band bonus
    if size_band_applied:
        confidence_score += 5
        confidence_reasons.append("Size-adjusted comparables")

    confidence_score = max(0, min(100, confidence_score))

    if confidence_score >= 70:
        confidence_label = "medium"
    elif confidence_score >= 40:
        confidence_label = "low"
    else:
        confidence_label = "very_low"

    # ── Shadow direction ──
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
            "size_band_applied": size_band_applied,
            "size_band_pct": config.get("size_band_pct_default") if size_band_applied else None,
            "mapped_dld_area": dld_area,
            "area_mapping_confidence": mapping_confidence,
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


# ---------------------------------------------------------------------------
# Batch runner — run fallback across all properties
# ---------------------------------------------------------------------------

def run_fallback_for_all_properties(
    master_df: Optional[pd.DataFrame] = None,
    area_mapping: Optional[Dict[str, Dict]] = None,
    config: Optional[Dict] = None,
) -> List[Dict]:
    """Run fallback calculation for all MASTER properties."""
    if master_df is None:
        master_df = load_master_df()
    if area_mapping is None:
        area_mapping = build_verified_area_mapping(master_df, get_fallback_dld_store())
    if config is None:
        config = FALLBACK_CONFIG

    results = []
    for _, row in master_df.iterrows():
        prop_id = str(int(row["property_id"]))
        bedrooms = row.get("unit_bedrooms")
        size_sqft = row.get("unit_size_sqft")

        # Convert NaN to None
        if isinstance(bedrooms, float) and math.isnan(bedrooms):
            bedrooms = None
        if isinstance(size_sqft, float) and math.isnan(size_sqft):
            size_sqft = None

        res = calculate_fallback_benchmark(
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
            area_mapping=area_mapping,
            config=config,
        )
        results.append(res)

    return results


# ---------------------------------------------------------------------------
# Backtest against exact-evidence properties
# ---------------------------------------------------------------------------

def backtest_fallback_against_exact_evidence(
    master_df: Optional[pd.DataFrame] = None,
    area_mapping: Optional[Dict[str, Dict]] = None,
    config: Optional[Dict] = None,
) -> List[Dict]:
    """
    For properties with exact-project evidence, hide their exact-project
    transactions and calculate what the area fallback would predict.
    Compare fallback vs actual exact-project benchmark.
    """
    if master_df is None:
        master_df = load_master_df()
    if area_mapping is None:
        area_mapping = build_verified_area_mapping(master_df, get_fallback_dld_store())
    if config is None:
        config = FALLBACK_CONFIG

    # Filter to properties with exact-project evidence
    exact_evidence = master_df[
        (master_df["dld_evidence_status"] == "DLD_MATCH")
        & (master_df["dld_transaction_count"] >= 3)
        & (master_df["dld_median_price_aed"].notna())
        & (master_df["unit_bedrooms"].notna())
    ].copy()

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

        # Run fallback
        fallback = calculate_fallback_benchmark(
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
            area_mapping=area_mapping,
            config=config,
        )

        if not fallback.get("eligible"):
            continue

        fallback_benchmark = fallback["benchmark"]["estimated_benchmark_aed"]
        error_aed = fallback_benchmark - exact_benchmark
        error_pct = (error_aed / exact_benchmark) * 100 if exact_benchmark else None
        abs_error_pct = abs(error_pct) if error_pct is not None else None

        backtests.append({
            "property_id": prop_id,
            "property_name": row.get("property_name", ""),
            "area": row.get("area", ""),
            "bedrooms": bedrooms,
            "status": row.get("unit_status", ""),
            "property_type": row.get("property_type", ""),
            "exact_benchmark": exact_benchmark,
            "fallback_benchmark": fallback_benchmark,
            "error_aed": round(error_aed, 2),
            "error_pct": round(error_pct, 2) if error_pct is not None else None,
            "absolute_error_pct": round(abs_error_pct, 2) if abs_error_pct is not None else None,
            "fallback_level": fallback["level"],
            "tx_count": fallback["benchmark"]["final_transaction_count"],
            "unique_projects": fallback["benchmark"]["unique_project_count"],
            "size_band_applied": fallback["benchmark"]["size_band_applied"],
            "size_band_pct": fallback["benchmark"]["size_band_pct"],
            "status_broadened": fallback["benchmark"]["status_broadened"],
            "area_mapping_confidence": fallback["benchmark"]["area_mapping_confidence"],
            "subject_project_excluded": True,
            "confidence_score": fallback["confidence"]["fallback_confidence_score"],
            "confidence_label": fallback["confidence"]["fallback_confidence_label"],
            "ppsf_p50": fallback["benchmark"]["median_ppsf"],
            "ppsf_iqr": fallback["benchmark"]["ppsf_iqr"],
            "high_dispersion": fallback["benchmark"]["high_dispersion_flag"],
        })

    return backtests


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def export_fallback_coverage(results: List[Dict], output_path: str):
    """Export fallback coverage audit to Excel."""
    rows = []
    for r in results:
        subject = r.get("subject", {})
        benchmark = r.get("benchmark", {})
        calc = r.get("calculations", {})
        conf = r.get("confidence", {})
        val = r.get("validation", {})

        rows.append({
            "property_id": subject.get("property_id"),
            "property_name": subject.get("property_name"),
            "area": subject.get("area"),
            "bedrooms": subject.get("unit_bedrooms"),
            "status": subject.get("unit_status"),
            "size_sqft": subject.get("unit_size_sqft"),
            "price": subject.get("current_price_aed"),
            "current_evidence_status": subject.get("dld_evidence_status"),
            "fallback_candidate": r.get("eligible", False),
            "fallback_level": r.get("level"),
            "verified_dld_area": benchmark.get("mapped_dld_area"),
            "raw_tx_count": benchmark.get("raw_transaction_count"),
            "final_tx_count": benchmark.get("final_transaction_count"),
            "unique_project_count": benchmark.get("unique_project_count"),
            "median_ppsf": benchmark.get("median_ppsf"),
            "estimated_benchmark": benchmark.get("estimated_benchmark_aed"),
            "apil_advantage_pct": calc.get("apil_advantage_pct"),
            "conventional_pct": calc.get("conventional_below_benchmark_pct"),
            "fallback_confidence_score": conf.get("fallback_confidence_score"),
            "fallback_confidence_label": conf.get("fallback_confidence_label"),
            "production_eligible": False,
            "shadow_direction": r.get("shadow_direction"),
            "excluded_reasons": "; ".join(val.get("excluded_reasons", [])),
            "quality_flags": "; ".join(val.get("quality_flags", [])),
        })

    df = pd.DataFrame(rows)
    df.to_excel(output_path, index=False)
    print(f"[Fallback] Coverage audit exported: {output_path} ({len(df)} rows)")


def export_backtest(backtests: List[Dict], output_path: str):
    """Export backtest results to Excel."""
    if not backtests:
        print(f"[Fallback] No backtests to export")
        return
    df = pd.DataFrame(backtests)
    df.to_excel(output_path, index=False)
    print(f"[Fallback] Backtest exported: {output_path} ({len(df)} rows)")


def generate_implementation_report(
    results: List[Dict],
    backtests: List[Dict],
    area_mapping: Dict[str, Dict],
    output_path: str,
):
    """Generate markdown implementation report."""
    total = len(results)
    eligible = [r for r in results if r.get("eligible")]
    by_level = Counter(r.get("level") for r in results)
    by_reason = Counter()
    for r in results:
        for reason in r.get("validation", {}).get("excluded_reasons", []):
            by_reason[reason] += 1

    lines = [
        "# Fallback DLD Benchmark Implementation Report",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## Coverage Summary",
        f"",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total MASTER properties | {total} |",
        f"| Fallback eligible | {len(eligible)} ({len(eligible)/total*100:.1f}%) |",
        f"| Fallback not eligible | {total - len(eligible)} |",
        "",
        "## Fallback Level Distribution",
        "",
    ]
    for level, count in sorted(by_level.items(), key=lambda x: -x[1]):
        lines.append(f"- **{level}**: {count} ({count/total*100:.1f}%)")

    lines.extend([
        "",
        "## Exclusion Reasons",
        "",
    ])
    for reason, count in sorted(by_reason.items(), key=lambda x: -x[1]):
        lines.append(f"- **{reason}**: {count}")

    # Area mapping summary
    lines.extend([
        "",
        "## Verified Area Mapping",
        f"",
        f"Total verified mappings: {len(area_mapping)}",
        "",
        "| MASTER Area | DLD Area | Confidence | Supporting Projects |",
        "|-------------|----------|------------|---------------------|",
    ])
    for master_area, data in sorted(area_mapping.items(), key=lambda x: -x[1]["supporting_exact_project_count"]):
        lines.append(
            f"| {master_area} | {data['dld_area']} | {data['confidence']} | {data['supporting_exact_project_count']} |"
        )

    # Backtest summary
    if backtests:
        errors = [b["absolute_error_pct"] for b in backtests if b["absolute_error_pct"] is not None]
        if errors:
            errors_sorted = sorted(errors)
            n = len(errors_sorted)
            lines.extend([
                "",
                "## Backtest Results (vs Exact-Project Evidence)",
                f"",
                f"Properties backtested: {len(backtests)}",
                f"",
                f"| Metric | Value |",
                f"|--------|-------|",
                f"| Median Absolute % Error | {errors_sorted[n//2]:.2f}% |",
                f"| Mean Absolute % Error | {sum(errors)/len(errors):.2f}% |",
                f"| P25 | {errors_sorted[n//4]:.2f}% |",
                f"| P75 | {errors_sorted[(3*n)//4]:.2f}% |",
                f"| P90 | {errors_sorted[int(n*0.9)]:.2f}% |",
                f"| Worst | {errors_sorted[-1]:.2f}% |",
                "",
            ])

    lines.extend([
        "",
        "## Methodology Notes",
        "",
        "- All fallback calculations use real DLD transactions only.",
        "- PPSF (price per sqft) is used for area-level comparables.",
        "- Exact-project transactions are EXCLUDED from area fallback during backtest.",
        "- IQR-based outlier removal is applied to PPSF values.",
        "- Area mapping is verified using exact-project matched properties.",
        "- Fallback benchmarks are SHADOW ONLY — not connected to production decisions.",
        "",
        "## Configuration",
        "",
        "```json",
        json.dumps(FALLBACK_CONFIG, indent=2),
        "```",
    ])

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    print(f"[Fallback] Implementation report: {output_path}")


# ---------------------------------------------------------------------------
# Main entry point for backend shadow calculation
# ---------------------------------------------------------------------------

def run_full_fallback_analysis(
    output_dir: str = "/Users/apple/Desktop/Ai 3d view/apil-investment-demo",
    config: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Run the complete fallback analysis pipeline.
    Returns results for backend consumption only.
    """
    print("[Fallback] Starting full fallback analysis...")
    master_df = load_master_df()
    print(f"[Fallback] Loaded {len(master_df)} MASTER properties")

    area_mapping = build_verified_area_mapping(master_df, get_fallback_dld_store())
    print(f"[Fallback] Built {len(area_mapping)} verified area mappings")

    print("[Fallback] Running fallback calculations...")
    results = run_fallback_for_all_properties(master_df, area_mapping, config)

    print("[Fallback] Running backtest against exact-evidence properties...")
    backtests = backtest_fallback_against_exact_evidence(master_df, area_mapping, config)

    # Export
    coverage_path = os.path.join(output_dir, "FALLBACK_DLD_COVERAGE_AUDIT.xlsx")
    backtest_path = os.path.join(output_dir, "FALLBACK_DLD_BACKTEST.xlsx")
    report_path = os.path.join(output_dir, "FALLBACK_DLD_IMPLEMENTATION_REPORT.md")

    export_fallback_coverage(results, coverage_path)
    export_backtest(backtests, report_path.replace(".md", "_BACKTEST.xlsx"))
    export_backtest(backtests, backtest_path)
    generate_implementation_report(results, backtests, area_mapping, report_path)

    return {
        "results": results,
        "backtests": backtests,
        "area_mapping": area_mapping,
        "coverage_path": coverage_path,
        "backtest_path": backtest_path,
        "report_path": report_path,
    }


if __name__ == "__main__":
    run_full_fallback_analysis()
