"""
Market Context Service — Runtime Orchestration Layer
====================================================
Single entry point for all market-context calculations.

Hierarchy:
    1. Canonical DLD  → CANONICAL_DLD
    2. Level 2        → LEVEL_2_FALLBACK
    3. V4 Area        → AREA_FALLBACK
    4. None           → NONE

Production signal:
    CANONICAL_DLD  or  NONE

No fallback ever drives the production investment signal.
"""
import math
from typing import Any, Dict, Optional

import pandas as pd

from investor_api.fallback.level2_context import compute_level2_exact_project_status_broadened
from investor_api.fallback.dld_fallback_v4 import (
    calculate_fallback_benchmark_v4,
    build_verified_area_mapping_v4,
    build_transaction_index_v4,
    SHADOW_FALLBACK_CONFIG_V4,
)

# ---------------------------------------------------------------------------
# Immutable runtime config for investor-visible Area context
# ---------------------------------------------------------------------------
AREA_CONTEXT_CONFIG_V1 = {
    "version": "AREA_CONTEXT_V4_DLD_OFFICIAL_V1",
    "lookback_months": 24,
    "size_band_pct_default": 0.20,
    "min_transactions_area_fallback": 10,
    "min_unique_projects_area": 3,
    "max_project_concentration": 0.50,
    "ppsf_outlier_iqr_multiplier": 1.5,
    "outlier_method": "iqr_1.5",
    "property_type_filter": False,
    "sale_only": True,
    "sources_allowed": ["DLD_OFFICIAL"],   # investor-visible: DLD official only
}

# ---------------------------------------------------------------------------
# Lazy V4 caches
# ---------------------------------------------------------------------------
_V4_TX_INDEX_CACHE: Optional[Dict] = None
_V4_AREA_MAPPING_CACHE: Optional[Dict] = None
_V4_MASTER_DF_CACHE: Optional[pd.DataFrame] = None

DLD_CSV_PATH = "/Users/apple/Desktop/Ai 3d view/dxb_transactions_all.csv"
MASTER_PATH = "/Users/apple/Desktop/Ai 3d view/MASTER_FINAL.xlsx"


def _get_v4_transaction_index() -> Dict:
    global _V4_TX_INDEX_CACHE
    if _V4_TX_INDEX_CACHE is None:
        _V4_TX_INDEX_CACHE = build_transaction_index_v4(DLD_CSV_PATH)
    return _V4_TX_INDEX_CACHE


def _get_v4_area_mapping() -> Dict:
    global _V4_AREA_MAPPING_CACHE
    if _V4_AREA_MAPPING_CACHE is None:
        master_df = _get_master_df()
        if master_df is not None:
            _V4_AREA_MAPPING_CACHE = build_verified_area_mapping_v4(master_df, None)
    return _V4_AREA_MAPPING_CACHE


def _get_master_df() -> Optional[pd.DataFrame]:
    global _V4_MASTER_DF_CACHE
    if _V4_MASTER_DF_CACHE is None:
        try:
            _V4_MASTER_DF_CACHE = pd.read_excel(MASTER_PATH)
        except Exception:
            _V4_MASTER_DF_CACHE = None
    return _V4_MASTER_DF_CACHE


def get_level2_context(
    project_name: str,
    subject_price: float,
    bedroom: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Compute Level 2 fallback context.
    Returns None if not usable_for_investment.
    """
    raw = compute_level2_exact_project_status_broadened(
        project_name=project_name,
        subject_price=subject_price,
        bedroom=bedroom,
    )
    if raw.get("usable_for_investment") is not True:
        return None

    # Enrich with source labeling
    tx_count = raw.get("transaction_count", 0)
    source_dist = {"DLD_OFFICIAL": tx_count}
    raw["source_distribution"] = source_dist
    raw["transaction_source_label"] = "verified DLD sales"
    return raw


def get_area_context(
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
) -> Optional[Dict[str, Any]]:
    """
    Compute V4 Area fallback context with DLD_OFFICIAL_ONLY config.
    Returns normalized result dict or None if rejected by V4 safeguards.
    """
    tx_index = _get_v4_transaction_index()
    area_mapping = _get_v4_area_mapping()

    if tx_index is None or area_mapping is None:
        return None

    v4_result = calculate_fallback_benchmark_v4(
        property_id=property_id,
        property_name=property_name,
        area=area,
        developer_name=developer_name,
        current_price_aed=current_price_aed,
        unit_bedrooms=unit_bedrooms,
        unit_bathrooms=unit_bathrooms,
        unit_size_sqft=unit_size_sqft,
        unit_size_sqm=unit_size_sqm,
        unit_status=unit_status,
        property_type=property_type,
        bedroom_value_status=bedroom_value_status,
        dld_evidence_status=dld_evidence_status,
        tx_index=tx_index,
        area_mapping=area_mapping,
        config=AREA_CONTEXT_CONFIG_V1,
        subject_project_name=property_name,
    )

    if v4_result.get("eligible") is not True:
        return None

    bm = v4_result.get("benchmark", {})
    if not bm or bm.get("estimated_benchmark_aed") is None or bm["estimated_benchmark_aed"] <= 0:
        return None

    if bm.get("final_transaction_count", 0) < AREA_CONTEXT_CONFIG_V1["min_transactions_area_fallback"]:
        return None

    if bm.get("unique_project_count", 0) < AREA_CONTEXT_CONFIG_V1["min_unique_projects_area"]:
        return None

    # Map V4 level to tier
    level = v4_result.get("level", "AREA_SAME_BEDROOM_STATUS_BROADENED")
    if "SAME_STATUS" in level and "SIZE_ADJUSTED" in level:
        tier = "LEVEL_3"
        fb_type = "AREA_SAME_BEDROOM_SAME_STATUS_SIZE_ADJUSTED"
    elif "STATUS_BROADENED" in level and "SIZE_ADJUSTED" in level:
        tier = "LEVEL_3"
        fb_type = "AREA_SAME_BEDROOM_STATUS_BROADENED_SIZE_ADJUSTED"
    elif "SAME_STATUS" in level:
        tier = "LEVEL_4"
        fb_type = "AREA_SAME_BEDROOM_SAME_STATUS"
    else:
        tier = "LEVEL_4"
        fb_type = "AREA_SAME_BEDROOM_STATUS_BROADENED"

    source_dist = bm.get("source_distribution", {})
    tx_label = "verified DLD sales" if source_dist.get("DLD_OFFICIAL", 0) == bm.get("final_transaction_count", 0) else "comparable sales evidence"

    return {
        "benchmark_median": bm.get("estimated_benchmark_aed"),
        "transaction_count": bm.get("final_transaction_count", 0),
        "raw_transaction_count": bm.get("raw_transaction_count", 0),
        "unique_projects": bm.get("unique_project_count", 0),
        "largest_project_share": bm.get("largest_project_share"),
        "matched_area": bm.get("mapped_dld_area"),
        "bedroom_filter": unit_bedrooms,
        "status_filter": "status_broadened" if bm.get("status_broadened") else "same_status",
        "status_broadened": bm.get("status_broadened", False),
        "size_band_applied": bm.get("size_band_applied", False),
        "size_band_pct": bm.get("size_band_pct"),
        "median_ppsf": bm.get("median_ppsf"),
        "benchmark_p25": bm.get("estimated_benchmark_p25"),
        "benchmark_p75": bm.get("estimated_benchmark_p75"),
        "bootstrap_lower": bm.get("estimated_benchmark_bootstrap_lower"),
        "bootstrap_upper": bm.get("estimated_benchmark_bootstrap_upper"),
        "source_distribution": source_dist,
        "transaction_source_label": tx_label,
        "quality_score": v4_result.get("quality", {}).get("quality_score"),
        "quality_label": v4_result.get("quality", {}).get("quality_label"),
        "evidence_level": level,
        "validation_flags": v4_result.get("validation", {}).get("quality_flags", []),
        # Identity
        "benchmark_method": "DLD_FALLBACK",
        "benchmark_tier": tier,
        "is_fallback": True,
        "fallback_type": fb_type,
        "production_eligible": False,
        "validation_status": "CONTEXT_ONLY",
        "calculation_version": "AREA_CONTEXT_V4_DLD_OFFICIAL_V1",
    }


def select_market_context(
    canonical_usable: bool,
    level2_result: Optional[Dict],
    area_result: Optional[Dict],
) -> tuple:
    """
    Return (market_context_source, production_signal_source, fallback_context_dict).
    """
    if canonical_usable:
        return "CANONICAL_DLD", "CANONICAL_DLD", {"level2": None, "area_fallback": None}

    if level2_result is not None:
        return "LEVEL_2_FALLBACK", "NONE", {"level2": level2_result, "area_fallback": None}

    if area_result is not None:
        return "AREA_FALLBACK", "NONE", {"level2": None, "area_fallback": area_result}

    return "NONE", "NONE", {"level2": None, "area_fallback": None}
