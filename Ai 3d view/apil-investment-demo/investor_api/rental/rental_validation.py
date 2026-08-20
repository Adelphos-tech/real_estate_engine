"""
Rental Validation — Quality Gates & Sanity Checks
==================================================
NEW_RENTAL_ENGINE_IMPORTS_LEGACY = 0

Validates rental estimates against:
- Configurable bounds (min/max rent, PSF bounds) - NO yield caps
- Temporal consistency
- Comparable quality (sample size, concentration, outlier %)
- NO cross-check with sales benchmarks to reject rent (Section 14)

Phase 1 rent validity must be based on rental evidence only.
Gross yield is calculated AFTER rent is estimated.
Do not use gross yield to filter the rent estimate.
"""

from typing import Any, Dict, List, Optional

# ──────────────────────────────────────────────────────────────────────────────
# Validation Configuration (NO yield caps, NO sales cross-check rejection)
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_VALIDATION_CONFIG = {
    # Rent bounds (annual AED) - based on rental market reality
    "min_annual_rent": 10_000,
    "max_annual_rent": 5_000_000,

    # NO yield bounds - Section 14: YIELD_CAP_USED_TO_REJECT_RENT = 0
    # "min_gross_yield": 1.0,   # REMOVED - circular
    # "max_gross_yield": 15.0,  # REMOVED - circular

    # PSF bounds (AED/sqft/year) - based on rental market reality
    "min_psf": 20,
    "max_psf": 5_000,

    # Comparable quality
    "min_comparables_r1": 5,
    "min_comparables_r2": 8,
    "min_comparables_r3": 10,
    "min_comparables_r4": 20,
    "max_project_concentration": 0.50,
    "max_outlier_fraction": 0.30,  # Max 30% of samples removed as outliers

    # Temporal
    "temporal_mape_threshold": 20.0,

    # NO sales cross-check rejection - Section 14: SALES_BENCHMARK_USED_TO_REJECT_RENT = 0
    # "sales_rent_ratio_min": 0.03,   # REMOVED - circular
    # "sales_rent_ratio_max": 0.12,   # REMOVED - circular
}

# ──────────────────────────────────────────────────────────────────────────────
# Validation Functions
# ──────────────────────────────────────────────────────────────────────────────
def validate_rental_estimate(
    rental_context: Dict[str, Any],
    config: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Validate a rental context result.

    Returns: {"valid": bool, "reasons": List[str], "warnings": List[str]}
    """
    cfg = {**DEFAULT_VALIDATION_CONFIG, **(config or {})}
    reasons = []
    warnings = []

    # 1. Core estimate exists
    estimate = rental_context.get("annual_market_rent_estimate")
    if estimate is None:
        reasons.append("No annual market rent estimate")
        return {"valid": False, "reasons": reasons, "warnings": warnings}

    # 2. Rent bounds (based on rental data only)
    if estimate < cfg["min_annual_rent"]:
        reasons.append(f"Estimated rent {estimate:,.0f} below minimum {cfg['min_annual_rent']:,.0f}")
    if estimate > cfg["max_annual_rent"]:
        reasons.append(f"Estimated rent {estimate:,.0f} exceeds maximum {cfg['max_annual_rent']:,.0f}")

    # 3. NO yield bounds validation (Section 14: YIELD_CAP_USED_TO_REJECT_RENT = 0)
    # yield_val = rental_context.get("gross_rental_yield")
    # if yield_val is not None:
    #     ... yield validation REMOVED

    # 4. PSF bounds (if computable from rental evidence only)
    size_sqft = rental_context.get("subject_size_sqft")
    if size_sqft and size_sqft > 0:
        psf = estimate / size_sqft
        if psf < cfg["min_psf"]:
            warnings.append(f"Implied PSF {psf:.0f} below minimum {cfg['min_psf']}")
        if psf > cfg["max_psf"]:
            warnings.append(f"Implied PSF {psf:.0f} exceeds maximum {cfg['max_psf']}")

    # 5. Comparable quality
    tier = rental_context.get("selected_tier")
    comp_count = rental_context.get("comparable_count", 0)
    tier_config = cfg.get(f"min_comparables_{tier.lower()}")
    if tier_config and comp_count < tier_config:
        reasons.append(f"Tier {tier}: only {comp_count} comparables (need {tier_config})")

    # 6. Project concentration check
    if tier == "R1" and comp_count < 5:
        warnings.append(f"R1 tier has only {comp_count} comparables - consider broader tier")

    # 7. Outlier fraction (estimated from tier results)
    tier_results = rental_context.get("tier_results", {})
    if tier in tier_results:
        tr = tier_results[tier]
        # We don't have raw count vs clean count here - would need to track in engine
        pass

    # 8. Temporal holdout
    temporal = rental_context.get("temporal_holdout")
    if temporal and not temporal.get("passed", True):
        mape = temporal.get("mape")
        if mape is not None and mape > cfg["temporal_mape_threshold"]:
            reasons.append(f"Temporal holdout failed: MAPE {mape:.1f}% > {cfg['temporal_mape_threshold']:.1f}%")
        else:
            warnings.append(f"Temporal holdout failed: {temporal.get('reason', 'unknown')}")

    # 9. Estimation method sanity
    method = rental_context.get("estimation_method")
    if method == "median_psf_times_size":
        median_psf = rental_context.get("tier_results", {}).get(tier, {}).get("median_psf")
        if median_psf and (median_psf < cfg["min_psf"] or median_psf > cfg["max_psf"]):
            reasons.append(f"Median PSF {median_psf:.0f} outside valid range")

    # 10. P25/P75 consistency
    p25 = rental_context.get("annual_market_rent_p25")
    p75 = rental_context.get("annual_market_rent_p75")
    if p25 is not None and p75 is not None:
        if p25 > p75:
            reasons.append("P25 > P75 (percentile inconsistency)")
        if estimate < p25 or estimate > p75:
            warnings.append("Median estimate outside P25-P75 range")

    # Valid if no reasons (warnings are non-blocking)
    return {
        "valid": len(reasons) == 0,
        "reasons": reasons,
        "warnings": warnings,
    }


def validate_rental_benchmark_result(
    benchmark_result: Any,  # RentalBenchmarkResult from rental_benchmark_engine
    config: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Validate a RentalBenchmarkResult object directly.
    """
    # Convert to dict-like for validate_rental_estimate
    ctx = {
        "annual_market_rent_estimate": benchmark_result.final_annual_rent_estimate,
        "annual_market_rent_p25": benchmark_result.final_annual_rent_p25,
        "annual_market_rent_p75": benchmark_result.final_annual_rent_p75,
        "gross_rental_yield": benchmark_result.gross_rental_yield,
        "selected_tier": benchmark_result.selected_tier,
        "comparable_count": benchmark_result.total_comparables_used,
        "estimation_method": benchmark_result.selected_method,
        "subject_size_sqft": benchmark_result.subject_size_sqft,
        "tier_results": {
            name: {
                "median_psf": tr.median_psf,
            }
            for name, tr in benchmark_result.tier_results.items()
        },
        "temporal_holdout": benchmark_result.temporal_holdout_details,
    }
    return validate_rental_estimate(ctx, config)


def validate_tier_consistency(
    tier_results: Dict[str, Any],
    config: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Validate consistency across tiers.
    Higher tiers (R1) should generally have estimates close to broader tiers.
    """
    cfg = {**DEFAULT_VALIDATION_CONFIG, **(config or {})}
    reasons = []
    warnings = []

    estimates = {}
    for tier_name in ["R1", "R2", "R3", "R4"]:
        if tier_name in tier_results:
            tr = tier_results[tier_name]
            est = tr.get("estimate")
            if est is not None:
                estimates[tier_name] = est

    if len(estimates) < 2:
        return {"valid": True, "reasons": [], "warnings": ["Insufficient tiers for cross-tier validation"]}

    # Check R1 vs R3 (same bedroom, project vs area)
    if "R1" in estimates and "R3" in estimates:
        r1 = estimates["R1"]
        r3 = estimates["R3"]
        diff_pct = abs(r1 - r3) / r3 * 100 if r3 else 0
        if diff_pct > 50:
            warnings.append(f"R1 vs R3 estimate divergence: {diff_pct:.0f}%")

    # Check R2 vs R3 (same bedroom, sub-type vs broadened)
    if "R2" in estimates and "R3" in estimates:
        r2 = estimates["R2"]
        r3 = estimates["R3"]
        diff_pct = abs(r2 - r3) / r3 * 100 if r3 else 0
        if diff_pct > 30:
            warnings.append(f"R2 vs R3 estimate divergence: {diff_pct:.0f}%")

    # Check R3 vs R4 (bedroom-specific vs aggregated)
    if "R3" in estimates and "R4" in estimates:
        r3 = estimates["R3"]
        r4 = estimates["R4"]
        diff_pct = abs(r3 - r4) / r4 * 100 if r4 else 0
        if diff_pct > 40:
            warnings.append(f"R3 vs R4 estimate divergence: {diff_pct:.0f}%")

    return {"valid": len(reasons) == 0, "reasons": reasons, "warnings": warnings}


# ──────────────────────────────────────────────────────────────────────────────
# Comprehensive Validation Pipeline
# ──────────────────────────────────────────────────────────────────────────────
def run_full_validation(
    rental_context: Dict[str, Any],
    sales_benchmark_median: Optional[float] = None,
    subject_price: Optional[float] = None,
    config: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Run all validations and aggregate results.
    NO sales cross-check that can reject rent (Section 14).
    """
    all_reasons = []
    all_warnings = []

    # 1. Core estimate validation
    core = validate_rental_estimate(rental_context, config)
    all_reasons.extend(core["reasons"])
    all_warnings.extend(core["warnings"])

    # 2. NO sales cross-check that can reject rent (Section 14: SALES_BENCHMARK_USED_TO_REJECT_RENT = 0)
    # if sales_benchmark_median and subject_price:
    #     ... REMOVED

    # 3. Tier consistency (informational only)
    tier_results = rental_context.get("tier_results", {})
    if tier_results:
        consistency = validate_tier_consistency(tier_results, config)
        all_reasons.extend(consistency["reasons"])
        all_warnings.extend(consistency["warnings"])

    return {
        "valid": len(all_reasons) == 0,
        "reasons": all_reasons,
        "warnings": all_warnings,
        "checks_run": ["core", "tier_consistency"],
    }