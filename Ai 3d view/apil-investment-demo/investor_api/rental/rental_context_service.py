"""
Rental Context Service — Shadow endpoint logic for gross rental yield.

LOCKED METHODOLOGY: RENTAL_MARKET_RENT_V1 / GROSS_RENTAL_YIELD_V1
  - Estimator: RECENCY_WEIGHTED_MEDIAN_ANNUAL_RENT
  - Half-life: 12 months
  - Outlier filter: IQR 1.5
  - Size band: ±25%
  - Contract strategy: NEW_PLUS_RENEWED
  - Calibration: GLOBAL_MULTIPLICATIVE ×0.96

This module is SHADOW ONLY. It does NOT modify any production signal.
Status resolution delegates to the SAME production path:
  _build_apil_attributes() → MASTER unit_status > _resolve_property_status()
"""
import hashlib
import math
from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from investor_api.rental.rental_benchmark_engine import (
    COMPARATOR_TIERS, TIER_BY_NAME, RentalCandidateComparator,
)
from investor_api.rental.rental_data_store import get_rental_store, RentalContract
from investor_api.rental.rental_normalization import (
    filter_outliers_iqr, weighted_median,
)
from investor_api.rental.rental_area_mapping import (
    get_rental_area_for_master, get_exact_dld_area_for_master,
)

# ──────────────────────────────────────────────────────────────────────────────
# LOCKED CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────
CALC_VERSION_RENT = "RENTAL_MARKET_RENT_V1"
CALC_VERSION_YIELD = "GROSS_RENTAL_YIELD_V1"
DEFAULT_PROP_TYPE = "Unit"
SIZE_BAND = 0.25
MIN_HISTORICAL = 5
RECENCY_HALFLIFE_DAYS = 365
CAL_FACTOR = 0.96
AS_OF_DATE = "2026-08-09"

RENTAL_CSV_PATH = "/Users/apple/Desktop/Ai 3d view/dxb_rents_all.csv"
EXPECTED_RENTAL_SHA256 = "92546471b4326a89ca5980381b918cd5077d277eae396edf0374d9448d91129d"

# Yield threshold for data-quality warning (disclosure only, no capping)
YIELD_WARNING_THRESHOLD = 15.0  # %

# ──────────────────────────────────────────────────────────────────────────────
# Singleton comparator (loaded once)
# ──────────────────────────────────────────────────────────────────────────────
_comparator: Optional[RentalCandidateComparator] = None
_rental_store = None
_rental_csv_sha256: Optional[str] = None
_rental_csv_rows: Optional[int] = None


def _get_comparator() -> RentalCandidateComparator:
    global _comparator, _rental_store
    if _comparator is None:
        _rental_store = get_rental_store()
        _comparator = RentalCandidateComparator(store=_rental_store)
    return _comparator


def _get_rental_store():
    global _rental_store
    if _rental_store is None:
        _rental_store = get_rental_store()
    return _rental_store


def get_rental_csv_sha256() -> str:
    """Return SHA256 of the rental CSV (computed once, cached)."""
    global _rental_csv_sha256
    if _rental_csv_sha256 is None:
        sha = hashlib.sha256()
        with open(RENTAL_CSV_PATH, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        _rental_csv_sha256 = sha.hexdigest()
    return _rental_csv_sha256


def get_rental_csv_rows() -> int:
    """Return row count of the rental CSV (computed once, cached)."""
    global _rental_csv_rows
    if _rental_csv_rows is None:
        with open(RENTAL_CSV_PATH) as f:
            _rental_csv_rows = sum(1 for _ in f) - 1
    return _rental_csv_rows


# ──────────────────────────────────────────────────────────────────────────────
# Estimator D: Recency-weighted median (LOCKED V1.1)
# ──────────────────────────────────────────────────────────────────────────────
def _compute_weighted_percentiles(
    contracts: List[RentalContract], target_date: str
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Return (weighted_median, weighted_p25, weighted_p75) after IQR 1.5 filter."""
    if not contracts:
        return None, None, None
    try:
        t = datetime.fromisoformat(target_date[:10])
    except Exception:
        return None, None, None

    rents = []
    weights = []
    for c in contracts:
        try:
            cd = datetime.fromisoformat(c.registration_date[:10])
        except Exception:
            continue
        days_ago = (t - cd).days
        if days_ago < 0:
            continue
        weight = 0.5 ** (days_ago / RECENCY_HALFLIFE_DAYS)
        rents.append(c.annual_amount)
        weights.append(weight)

    if len(rents) < 3:
        return None, None, None

    rents_clean = filter_outliers_iqr(rents, 1.5)
    if not rents_clean:
        return None, None, None

    lo, hi = min(rents_clean), max(rents_clean)
    filtered = [(r, w) for r, w in zip(rents, weights) if lo <= r <= hi]
    if len(filtered) < 3:
        return None, None, None

    est = weighted_median([r for r, _ in filtered], [w for _, w in filtered])

    paired = sorted(filtered)
    total_w = sum(w for _, w in paired)
    if total_w <= 0:
        return est, None, None

    p25_target = total_w * 0.25
    p75_target = total_w * 0.75
    cumsum = 0
    p25 = None
    p75 = None
    for r, w in paired:
        cumsum += w
        if p25 is None and cumsum >= p25_target:
            p25 = r
        if p75 is None and cumsum >= p75_target:
            p75 = r
            break

    return est, p25, p75


# ──────────────────────────────────────────────────────────────────────────────
# Tier contract retrieval
# ──────────────────────────────────────────────────────────────────────────────
def _get_tier_contracts(
    comparator: RentalCandidateComparator,
    tier_name: str,
    dld_area: str,
    bedrooms: Optional[int],
    project: Optional[str],
    prop_type: str,
    size_band: float,
    subject_size: float,
    contract_strategy: str,
) -> List[RentalContract]:
    tier = TIER_BY_NAME.get(tier_name)
    if not tier:
        return []
    tier = replace(tier, size_band_pct=size_band)
    contracts = comparator.get_candidates(
        dld_area, bedrooms, project, prop_type, tier,
        apply_recency=False, contract_strategy=contract_strategy,
    )
    lo = subject_size * (1 - size_band)
    hi = subject_size * (1 + size_band)
    contracts = [c for c in contracts if lo <= c.actual_area_sqft <= hi]
    return contracts


# ──────────────────────────────────────────────────────────────────────────────
# Deterministic tier selection: R1 > R2 > R3 > R4 > NONE
# ──────────────────────────────────────────────────────────────────────────────
def _select_tier_deterministic(
    comparator: RentalCandidateComparator,
    dld_area: str,
    bedrooms: Optional[int],
    project: Optional[str],
    prop_type: str,
    size_sqft: float,
) -> Tuple[str, List[RentalContract]]:
    for tier_name in ["R1", "R2", "R3", "R4"]:
        tier = TIER_BY_NAME[tier_name]
        if tier.requires_bedroom and bedrooms is None:
            continue
        if tier.requires_project and not project:
            continue
        contracts = _get_tier_contracts(
            comparator, tier_name, dld_area, bedrooms, project,
            prop_type, SIZE_BAND, size_sqft, "NEW_PLUS_RENEWED",
        )
        historical = [c for c in contracts if c.registration_date < AS_OF_DATE]
        if len(historical) >= MIN_HISTORICAL:
            return tier_name, historical
    return "NONE", []


# ──────────────────────────────────────────────────────────────────────────────
# Evidence quality + investor label
# ──────────────────────────────────────────────────────────────────────────────
_TIER_META = {
    "R1": {"evidence_quality": "STRONGEST", "investor_label": "Estimated Project Rent (Exact Bedroom Match)"},
    "R2": {"evidence_quality": "STRONGER", "investor_label": "Estimated Project Rent"},
    "R3": {"evidence_quality": "STRONG", "investor_label": "Estimated Area Rent (Bedroom Match)"},
    "R4": {"evidence_quality": "BROADER", "investor_label": "Estimated Area Rent"},
    "NONE": {"evidence_quality": "NONE", "investor_label": ""},
}

_R4_WARNING = "Based on broader area rental comparables. Individual building rents may differ materially."


# ──────────────────────────────────────────────────────────────────────────────
# Data-quality warning (disclosure only — does NOT change rent, yield, or price)
# ──────────────────────────────────────────────────────────────────────────────
def _data_quality_warning(gross_yield_pct: Optional[float]) -> Optional[str]:
    if gross_yield_pct is None:
        return None
    if gross_yield_pct > YIELD_WARNING_THRESHOLD:
        return (
            "Gross yield is unusually high relative to the supplied asking price. "
            "Verify property price before relying on this figure."
        )
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Main: compute rental context for a property
# ──────────────────────────────────────────────────────────────────────────────
def compute_rental_context(
    property_id: str,
    resolved_status: str,
    master_area: Optional[str],
    master_project: Optional[str],
    master_bedrooms: Optional[int],
    master_size_sqft: Optional[float],
    master_price_aed: Optional[float],
) -> Dict[str, Any]:
    """
    Compute the shadow rental context for a single property.

    `resolved_status` MUST come from the SAME production status-resolution path
    (i.e. _build_apil_attributes → MASTER unit_status > _resolve_property_status).
    This function does NOT independently resolve status.
    """
    result: Dict[str, Any] = {
        "shadow": True,
        "property_id": property_id,
        "resolved_status": resolved_status,
        "selected_rental_tier": "NONE",
        "investor_label": "",
        "evidence_quality": "NONE",
        "annual_rent_estimate_aed": None,
        "annual_rent_p25_aed": None,
        "annual_rent_p75_aed": None,
        "comparable_count": 0,
        "projects_in_pool": 0,
        "gross_rental_yield_pct": None,
        "gross_yield_p25_pct": None,
        "gross_yield_p75_pct": None,
        "warnings": "",
        "data_quality_warning": None,
        "calc_version_rent": CALC_VERSION_RENT,
        "calc_version_yield": CALC_VERSION_YIELD,
    }

    # Offplan and Unknown: do NOT evaluate rent
    if resolved_status.lower() not in ("ready",):
        if resolved_status.lower() == "offplan":
            result["warnings"] = "Offplan properties not evaluated for current rent"
        elif resolved_status.lower() == "unknown":
            result["warnings"] = "Unknown status properties not evaluated for current rent"
        return result

    # Ready — estimate rent
    if not master_area or not master_size_sqft:
        result["warnings"] = "No DLD rental area or size"
        return result

    store = _get_rental_store()
    comparator = _get_comparator()

    dld_area = get_exact_dld_area_for_master(master_area, store)
    if not dld_area:
        dld_area = get_rental_area_for_master(master_area)
    if not dld_area:
        result["warnings"] = "No DLD rental area mapping"
        return result

    tier_name, historical = _select_tier_deterministic(
        comparator, dld_area, master_bedrooms, master_project,
        DEFAULT_PROP_TYPE, master_size_sqft,
    )

    result["selected_rental_tier"] = tier_name

    if tier_name == "NONE" or not historical:
        result["warnings"] = "Insufficient comparable rental data"
        return result

    est, p25, p75 = _compute_weighted_percentiles(historical, AS_OF_DATE)
    if est is None:
        result["warnings"] = "Estimator returned no valid estimate"
        return result

    est_cal = est * CAL_FACTOR
    p25_cal = p25 * CAL_FACTOR if p25 is not None else None
    p75_cal = p75 * CAL_FACTOR if p75 is not None else None

    meta = _TIER_META.get(tier_name, _TIER_META["NONE"])
    result["investor_label"] = meta["investor_label"]
    result["evidence_quality"] = meta["evidence_quality"]
    result["annual_rent_estimate_aed"] = round(est_cal, 0)
    result["annual_rent_p25_aed"] = round(p25_cal, 0) if p25_cal is not None else None
    result["annual_rent_p75_aed"] = round(p75_cal, 0) if p75_cal is not None else None
    result["comparable_count"] = len(historical)
    result["projects_in_pool"] = len(set(c.project_en for c in historical if c.project_en))

    if tier_name == "R4":
        result["warnings"] = _R4_WARNING
    else:
        result["warnings"] = ""

    # Gross yield
    if master_price_aed and master_price_aed > 0:
        gy = est_cal / master_price_aed * 100
        result["gross_rental_yield_pct"] = round(gy, 2)
        if p25_cal is not None:
            result["gross_yield_p25_pct"] = round(p25_cal / master_price_aed * 100, 2)
        if p75_cal is not None:
            result["gross_yield_p75_pct"] = round(p75_cal / master_price_aed * 100, 2)
        # Data-quality warning (disclosure only)
        result["data_quality_warning"] = _data_quality_warning(gy)

    return result
