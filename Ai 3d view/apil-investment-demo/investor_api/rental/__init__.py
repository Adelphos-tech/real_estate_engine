"""
APIL Rental Engine — Phase 1: Annual Market Rent Estimate → Gross Rental Yield
==============================================================================
NEW_RENTAL_ENGINE_IMPORTS_LEGACY = 0

This package implements a NEW rental engine from scratch with ZERO legacy dependencies.
All rental calculations are SHADOW_RESEARCH only - no production signal.

Components:
- rental_normalization: Pure normalization functions (sqm→sqft, bedrooms, PSF)
- rental_data_store: Safe normalized access layer (dxb_rents_all.csv, 573K rows)
- rental_benchmark_engine: Comparator tiers R1-R4, dual estimation, temporal holdout
- rental_area_mapping: MASTER→DLD rental area mapping (auditable, versioned)
- rental_context_service: Runtime orchestration (shadow only, no production signal)
- rental_validation: Quality gates (NO yield caps, NO sales cross-check rejection)

Tier Definitions (Corrected per RENTAL SHADOW V1 CORRECTION Section 7):
- R1: EXACT_PROJECT + SAME_BEDROOM + SIMILAR_SIZE
- R2: EXACT_PROJECT + SIMILAR_SIZE (bedroom not required)
- R3: SAME_AREA + SAME_BEDROOM + SIMILAR_SIZE
- R4: SAME_AREA + SIMILAR_SIZE

All tiers require:
- TOTAL_PROPERTIES == 1 (no assumption for missing)
- READY status only (Offplan/Unknown → NOT_EVALUATED)
- Property type matching (no Villa in Unit estimates)
- Size band filtering (±15%/±20%/±25%)
- Recency filtering (12/18/24/36 months)
- True temporal holdout (no future data leakage)

Phase 1 Output: Gross Rental Yield ONLY (annual_market_rent / price * 100)
NO net ROI, NO vacancy/management/service charge assumptions.
"""

from investor_api.rental.rental_normalization import (
    parse_date_yyyymmdd,
    parse_float,
    parse_int,
    infer_bedrooms_from_rooms,
    infer_property_class,
    convert_sqm_to_sqft,
    compute_psf,
    normalize_rent_to_annual,
    normalize_rental_row,
    median,
    percentile,
    iqr_bounds,
    filter_outliers_iqr,
    weighted_median,
    SQM_TO_SQFT,
)

from investor_api.rental.rental_data_store import (
    RentalContract,
    RentalIndex,
    RentalDataStore,
    get_rental_store,
)

from investor_api.rental.rental_benchmark_engine import (
    ComparatorTier,
    COMPARATOR_TIERS,
    TIER_BY_NAME,
    TierResult,
    RentalBenchmarkResult,
    RentalCandidateComparator,
    estimate_median_annual,
    estimate_median_psf_times_size,
    select_estimation_method,
    temporal_holdout_validation,
    RentalBenchmarkEngine,
    compute_rental_benchmark,
)

from investor_api.rental.rental_area_mapping import (
    AreaMappingEntry,
    get_rental_area_mapping,
    get_rental_area_for_master,
    get_mapping_audit,
    get_unmapped_areas,
    export_mapping_audit,
)

from investor_api.rental.rental_context_service import (
    compute_rental_context,
    get_rental_csv_sha256,
    get_rental_csv_rows,
    EXPECTED_RENTAL_SHA256,
    RENTAL_CSV_PATH,
    CALC_VERSION_RENT,
    CALC_VERSION_YIELD,
)

from investor_api.rental.rental_validation import (
    DEFAULT_VALIDATION_CONFIG,
    validate_rental_estimate,
    validate_rental_benchmark_result,
    validate_tier_consistency,
    run_full_validation,
)

__all__ = [
    # Normalization
    "parse_date_yyyymmdd",
    "parse_float",
    "parse_int",
    "infer_bedrooms_from_rooms",
    "infer_property_class",
    "convert_sqm_to_sqft",
    "compute_psf",
    "normalize_rent_to_annual",
    "normalize_rental_row",
    "median",
    "percentile",
    "iqr_bounds",
    "filter_outliers_iqr",
    "weighted_median",
    "SQM_TO_SQFT",
    # Data Store
    "RentalContract",
    "RentalIndex",
    "RentalDataStore",
    "get_rental_store",
    # Benchmark Engine
    "ComparatorTier",
    "COMPARATOR_TIERS",
    "TIER_BY_NAME",
    "TierResult",
    "RentalBenchmarkResult",
    "RentalCandidateComparator",
    "estimate_median_annual",
    "estimate_median_psf_times_size",
    "select_estimation_method",
    "temporal_holdout_validation",
    "RentalBenchmarkEngine",
    "compute_rental_benchmark",
    # Area Mapping
    "AreaMappingEntry",
    "get_rental_area_mapping",
    "get_rental_area_for_master",
    "get_mapping_audit",
    "get_unmapped_areas",
    "export_mapping_audit",
    # Context Service
    "compute_rental_context",
    "get_rental_csv_sha256",
    "get_rental_csv_rows",
    "EXPECTED_RENTAL_SHA256",
    "RENTAL_CSV_PATH",
    "CALC_VERSION_RENT",
    "CALC_VERSION_YIELD",
    # Validation
    "DEFAULT_VALIDATION_CONFIG",
    "validate_rental_estimate",
    "validate_rental_benchmark_result",
    "validate_tier_consistency",
    "run_full_validation",
]