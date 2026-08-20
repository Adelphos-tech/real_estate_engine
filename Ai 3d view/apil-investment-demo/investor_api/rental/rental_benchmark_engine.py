"""
Rental Benchmark Engine — Comparator Tiers & Rent Estimation
=============================================================
NEW_RENTAL_ENGINE_IMPORTS_LEGACY = 0

Phase 1: Annual market rent estimate → Gross rental yield
Formula: gross_rental_yield = (annual_market_rent / subject_price) * 100

CORRECTED Comparator Tiers (per RENTAL SHADOW V1 CORRECTION Section 7):
- R1: EXACT_PROJECT + SAME_BEDROOM + SIMILAR_SIZE
- R2: EXACT_PROJECT + SIMILAR_SIZE (bedroom not required)
- R3: SAME_AREA + SAME_BEDROOM + SIMILAR_SIZE
- R4: SAME_AREA + SIMILAR_SIZE

Estimation Methods (per handoff section 41):
- Method A: Median annual rent of comparables
- Method B: Median PSF × subject unit size (when size known)

Temporal Holdout Validation (per handoff section 45):
- Train on contracts ending before cutoff, validate on contracts starting after
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from statistics import median
from typing import Any, Dict, List, Optional, Tuple

from investor_api.rental.rental_data_store import RentalContract, get_rental_store, RentalIndex
from investor_api.rental.rental_normalization import (
    filter_outliers_iqr,
    median as norm_median,
    percentile,
    weighted_median,
)

# ──────────────────────────────────────────────────────────────────────────────
# Comparator Tier Definitions (CORRECTED per Section 7)
# ──────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ComparatorTier:
    """Definition of a comparator tier."""
    name: str                    # "R1", "R2", "R3", "R4"
    label: str                   # human-readable
    requires_bedroom: bool       # whether bedroom must be known
    requires_project: bool       # whether project must be known
    same_sub_type: bool          # whether to filter by PROP_SUB_TYPE_EN (deprecated)
    min_comparables: int         # minimum contracts needed
    max_comparables: int         # cap for performance
    weight: float                # confidence weight (higher = more confident)
    # New: size band and recency
    size_band_pct: float         # ± percentage for similar size (e.g., 0.20 = ±20%)
    lookback_months: int         # recency window


COMPARATOR_TIERS = [
    ComparatorTier(
        name="R1",
        label="Exact Project + Same Bedroom + Similar Size",
        requires_bedroom=True,
        requires_project=True,
        same_sub_type=False,
        min_comparables=5,
        max_comparables=2000,
        weight=1.0,
        size_band_pct=0.20,  # ±20%
        lookback_months=24,
    ),
    ComparatorTier(
        name="R2",
        label="Exact Project + Similar Size (Bedroom Not Required)",
        requires_bedroom=False,
        requires_project=True,
        same_sub_type=False,
        min_comparables=8,
        max_comparables=2000,
        weight=0.8,
        size_band_pct=0.20,
        lookback_months=24,
    ),
    ComparatorTier(
        name="R3",
        label="Same Area + Same Bedroom + Similar Size",
        requires_bedroom=True,
        requires_project=False,
        same_sub_type=False,
        min_comparables=10,
        max_comparables=5000,
        weight=0.6,
        size_band_pct=0.20,
        lookback_months=24,
    ),
    ComparatorTier(
        name="R4",
        label="Same Area + Similar Size (Bedroom Aggregated)",
        requires_bedroom=False,
        requires_project=False,
        same_sub_type=False,
        min_comparables=20,
        max_comparables=10000,
        weight=0.4,
        size_band_pct=0.20,
        lookback_months=24,
    ),
]

TIER_BY_NAME = {t.name: t for t in COMPARATOR_TIERS}


# ──────────────────────────────────────────────────────────────────────────────
# Result Data Classes
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class TierResult:
    """Result from a single comparator tier."""
    tier: str
    label: str
    comparables_count: int
    annual_rents: List[float]
    psfs: List[float]
    sizes_sqft: List[float]
    median_annual_rent: Optional[float]
    median_psf: Optional[float]
    p25_annual: Optional[float]
    p75_annual: Optional[float]
    p25_psf: Optional[float]
    p75_psf: Optional[float]
    estimation_method: str          # "median_annual" | "median_psf_times_size"
    estimated_annual_rent: Optional[float]
    confidence: float               # 0-1 based on tier weight * sample size factor
    warnings: List[str] = field(default_factory=list)
    rejected: bool = False
    rejection_reason: Optional[str] = None
    # Match tracking (Section 7)
    project_matched: bool = False
    bedroom_matched: bool = False
    size_matched: bool = False
    area_matched: bool = False
    property_type_matched: bool = False


@dataclass
class RentalBenchmarkResult:
    """Final aggregated rental benchmark."""
    subject_area: str
    subject_project: Optional[str]
    subject_bedrooms: Optional[int]
    subject_size_sqft: Optional[float]
    subject_price_aed: Optional[float]
    subject_prop_type: Optional[str] = None

    tier_results: Dict[str, TierResult] = field(default_factory=dict)
    selected_tier: Optional[str] = None
    selected_method: Optional[str] = None
    final_annual_rent_estimate: Optional[float] = None
    final_annual_rent_p25: Optional[float] = None
    final_annual_rent_p75: Optional[float] = None
    gross_rental_yield: Optional[float] = None
    yield_p25: Optional[float] = None
    yield_p75: Optional[float] = None

    # Metadata
    total_comparables_used: int = 0
    temporal_holdout_passed: bool = False
    temporal_holdout_details: Optional[Dict] = None
    calculation_version: str = "RENTAL_BENCHMARK_V1"
    warnings: List[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Candidate Comparator with Size & Recency Filtering
# ──────────────────────────────────────────────────────────────────────────────
class RentalCandidateComparator:
    """
    Finds and filters comparable rental contracts per tier.
    Enforces size band (±X%) and recency (lookback months).
    """

    def __init__(self, store=None):
        self.store = store or get_rental_store()
        self.contracts = self.store.contracts
        self.index = self.store.index

    def get_candidates(
        self,
        area: str,
        bedrooms: Optional[int],
        project: Optional[str] = None,
        prop_type: Optional[str] = None,  # "Unit" | "Villa"
        tier: ComparatorTier = None,
        as_of_date: str = "2026-03-31",  # Reference date for recency filtering
        apply_recency: bool = True,      # Whether to apply recency filter
        contract_strategy: str = "NEW_PLUS_RENEWED",  # "NEW_ONLY" | "NEW_PLUS_RENEWED"
    ) -> List[RentalContract]:
        """Get comparable contracts for a given tier with size and recency filters."""
        if tier is None:
            tier = COMPARATOR_TIERS[0]

        # Get base candidate indices from index
        indices = []
        if tier.requires_project and project:
            from investor_api.rental.rental_normalization import normalize_project_name
            project_key = normalize_project_name(project)
            if tier.requires_bedroom and bedrooms is not None:
                indices = self.index.get_by_project_bedrooms(project_key, bedrooms)
            else:
                indices = self.index.get_by_project(project_key)
        elif tier.requires_bedroom and bedrooms is not None:
            indices = self.index.get_by_area_bedrooms(area, bedrooms)
        else:
            indices = self.index.get_by_area(area)

        contracts = self.store.get_contracts_by_indices(indices)

        # Filter by property type - CRITICAL: no mixing Unit/Villa (Section 8)
        if prop_type:
            contracts = [c for c in contracts if c.prop_type_en == prop_type]

        # Filter by sub-type if required (legacy, not used in corrected tiers)
        # if tier.same_sub_type and prop_sub_type:
        #     contracts = [c for c in contracts if c.prop_sub_type_en == prop_sub_type]

        # Contract strategy filter (Section 24): NEW_ONLY vs NEW_PLUS_RENEWED
        if contract_strategy == "NEW_ONLY":
            contracts = [c for c in contracts if c.version == "New"]
        elif contract_strategy == "RENEWED_ONLY":
            contracts = [c for c in contracts if c.version == "Renewed"]
        # else: NEW_PLUS_RENEWED (no filter)

        # Filter: must have valid annual rent and PSF
        contracts = [c for c in contracts if c.annual_amount > 0 and c.psf > 0]

        # RECENCY FILTER: Only contracts with registration_date within lookback window
        if apply_recency and tier.lookback_months > 0:
            as_of = datetime.fromisoformat(as_of_date)
            # Calculate cutoff date by subtracting months (use day=1 to avoid day overflow)
            cutoff_year = as_of.year
            cutoff_month = as_of.month - tier.lookback_months
            while cutoff_month <= 0:
                cutoff_year -= 1
                cutoff_month += 12
            cutoff = as_of.replace(year=cutoff_year, month=cutoff_month, day=1)
            contracts = [c for c in contracts if c.registration_date >= cutoff.strftime("%Y-%m-%d")]

        # SIZE FILTER: ±size_band_pct of subject size
        subject_size = None
        # We'll apply size filter after we have subject size - do it in _evaluate_tier

        # Cap by recency (most recent first)
        if len(contracts) > tier.max_comparables:
            contracts.sort(key=lambda c: c.registration_date, reverse=True)
            contracts = contracts[:tier.max_comparables]

        return contracts

    def filter_by_size_band(
        self,
        contracts: List[RentalContract],
        subject_size_sqft: Optional[float],
        band_pct: float
    ) -> List[RentalContract]:
        """Filter contracts to those within ±band_pct of subject size."""
        if not subject_size_sqft or subject_size_sqft <= 0:
            return contracts  # Can't filter without subject size

        low = subject_size_sqft * (1 - band_pct)
        high = subject_size_sqft * (1 + band_pct)
        return [c for c in contracts if low <= c.actual_area_sqft <= high]


# ──────────────────────────────────────────────────────────────────────────────
# Estimation Methods (Section 41)
# ──────────────────────────────────────────────────────────────────────────────
def estimate_median_annual(contracts: List[RentalContract]) -> Optional[float]:
    """Method A: Median of annual rents."""
    if not contracts:
        return None
    rents = [c.annual_amount for c in contracts]
    rents = filter_outliers_iqr(rents, 1.5)
    if not rents:
        return None
    return norm_median(rents)


def estimate_median_psf_times_size(
    contracts: List[RentalContract],
    subject_size_sqft: Optional[float],
) -> Optional[float]:
    """Method B: Median PSF × subject unit size."""
    if not contracts or subject_size_sqft is None or subject_size_sqft <= 0:
        return None
    psfs = [c.psf for c in contracts]
    psfs = filter_outliers_iqr(psfs, 1.5)
    if not psfs:
        return None
    return norm_median(psfs) * subject_size_sqft


def select_estimation_method(
    contracts: List[RentalContract],
    subject_size_sqft: Optional[float],
) -> Tuple[str, Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    Select best estimation method and return:
    (method_name, median_annual, median_psf, p25_annual, p75_annual, p25_psf, p75_psf)
    """
    if not contracts:
        return "none", None, None, None, None, None, None

    rents = [c.annual_amount for c in contracts]
    psfs = [c.psf for c in contracts]
    sizes = [c.actual_area_sqft for c in contracts]

    rents_clean = filter_outliers_iqr(rents, 1.5)
    psfs_clean = filter_outliers_iqr(psfs, 1.5)

    if not rents_clean:
        return "none", None, None, None, None, None, None

    median_annual = norm_median(rents_clean)
    p25_annual = percentile(rents_clean, 25)
    p75_annual = percentile(rents_clean, 75)

    median_psf = norm_median(psfs_clean) if psfs_clean else None
    p25_psf = percentile(psfs_clean, 25) if psfs_clean else None
    p75_psf = percentile(psfs_clean, 75) if psfs_clean else None

    # Method A: median annual rent (always available)
    estimate_a = median_annual

    # Method B: median PSF × size (only if subject size known)
    estimate_b = None
    psf_method_valid = False

    if subject_size_sqft and median_psf and sizes:
        psf_method_valid = True
        estimate_b = median_psf * subject_size_sqft

    # Choose method: prefer B only if valid (subject size known)
    if psf_method_valid:
        return "median_psf_times_size", median_annual, median_psf, p25_annual, p75_annual, p25_psf, p75_psf

    # Default to Method A
    return "median_annual", median_annual, median_psf, p25_annual, p75_annual, p25_psf, p75_psf


# ──────────────────────────────────────────────────────────────────────────────
# Temporal Holdout Validation (Section 45) - TRUE OUT-OF-SAMPLE
# ──────────────────────────────────────────────────────────────────────────────
def temporal_holdout_validation(
    contracts: List[RentalContract],
    subject_size_sqft: Optional[float],
    cutoff_date: str = "2026-03-31",
    tier_name: str = "R1",
) -> Dict[str, Any]:
    """
    TRUE out-of-sample validation using registration_date as time axis:
    For each eligible held-out lease (registered after cutoff):
    1. Build comparator cohort using ONLY contracts registered before the target lease
    2. Exclude the target lease itself
    3. Predict target annual rent using historical cohort only
    4. Compare prediction to actual annual rent
    """
    cutoff = cutoff_date

    # Split by registration_date: train = before cutoff, test = at/after cutoff
    train = []
    test = []

    for c in contracts:
        if c.registration_date < cutoff:
            train.append(c)
        elif c.registration_date >= cutoff:
            test.append(c)

    if len(train) < 10 or len(test) < 10:
        return {
            "passed": False,
            "reason": f"Insufficient train ({len(train)}) or test ({len(test)}) samples for temporal holdout",
            "train_count": len(train),
            "test_count": len(test),
        }

    # For each test contract, predict using only train data registered before it
    predictions = []
    actuals = []

    for test_contract in test:
        # Build historical comparator pool: train contracts registered strictly before this test lease
        historical = [c for c in train if c.registration_date < test_contract.registration_date]

        if len(historical) < 3:  # Need minimum for estimation
            continue

        # Apply size filter if subject size known
        if subject_size_sqft:
            tier = TIER_BY_NAME.get(tier_name, COMPARATOR_TIERS[0])
            historical = [c for c in historical
                         if subject_size_sqft * (1 - tier.size_band_pct) <= c.actual_area_sqft <= subject_size_sqft * (1 + tier.size_band_pct)]

        if len(historical) < 3:
            continue

        # Estimate using historical data only
        method, est_annual, _, _, _, _, _ = select_estimation_method(historical, subject_size_sqft)
        if est_annual is None:
            continue

        predictions.append(est_annual)
        actuals.append(test_contract.annual_amount)

    if not predictions:
        return {
            "passed": False,
            "reason": "No valid predictions generated (all test leases lacked sufficient history)",
            "train_count": len(train),
            "test_count": len(test),
        }

    # Calculate error metrics
    mape_list = [abs(p - a) / a * 100 for p, a in zip(predictions, actuals) if a > 0]
    mape = norm_median(mape_list) if mape_list else None
    p75_ape = percentile(mape_list, 75) if mape_list else None
    p90_ape = percentile(mape_list, 90) if mape_list else None
    median_aed_error = norm_median([abs(p - a) for p, a in zip(predictions, actuals)]) if predictions else None
    median_bias = norm_median([(p - a) / a * 100 for p, a in zip(predictions, actuals) if a > 0]) if predictions else None

    passed = mape is not None and mape <= 20  # 20% MAPE threshold

    return {
        "passed": passed,
        "mape": mape,
        "p75_ape": p75_ape,
        "p90_ape": p90_ape,
        "median_aed_error": median_aed_error,
        "median_bias_pct": median_bias,
        "n_predictions": len(predictions),
        "n_test": len(test),
        "n_train": len(train),
        "method_used": method,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Main Benchmark Engine
# ──────────────────────────────────────────────────────────────────────────────
class RentalBenchmarkEngine:
    """
    Orchestrates tiered rental benchmark computation.
    """

    def __init__(self, comparator=None):
        self.comparator = comparator or RentalCandidateComparator()

    def compute_benchmark(
        self,
        area: str,
        bedrooms: Optional[int],
        project: Optional[str] = None,
        prop_type: Optional[str] = None,  # "Unit" | "Villa"
        subject_size_sqft: Optional[float] = None,
        subject_price_aed: Optional[float] = None,
        run_temporal_holdout: bool = True,
        contract_strategy: str = "NEW_PLUS_RENEWED",  # "NEW_ONLY" | "NEW_PLUS_RENEWED"
    ) -> RentalBenchmarkResult:
        """
        Compute rental benchmark across all applicable tiers.
        Returns the best available estimate.
        """
        result = RentalBenchmarkResult(
            subject_area=area,
            subject_project=project,
            subject_bedrooms=bedrooms,
            subject_size_sqft=subject_size_sqft,
            subject_price_aed=subject_price_aed,
            subject_prop_type=prop_type,
        )

        applicable_tiers = []
        for tier in COMPARATOR_TIERS:
            if tier.requires_bedroom and bedrooms is None:
                continue
            if tier.requires_project and not project:
                continue
            applicable_tiers.append(tier)

        if not applicable_tiers:
            result.warnings.append("No applicable tiers (missing bedroom/project)")
            return result

        # Evaluate each tier
        tier_results = {}
        for tier in applicable_tiers:
            tier_result = self._evaluate_tier(
                tier, area, bedrooms, project, prop_type, subject_size_sqft, contract_strategy
            )
            tier_results[tier.name] = tier_result

        result.tier_results = tier_results

        # Select best tier (highest weight * confidence, with min comparables met)
        best_tier = None
        best_score = -1
        for tier in applicable_tiers:
            tr = tier_results[tier.name]
            if tr.rejected:
                continue
            if tr.comparables_count < tier.min_comparables:
                continue
            # Score = tier weight * log(sample_size_factor)
            sample_factor = min(tr.comparables_count / tier.min_comparables, 5.0)
            score = tier.weight * sample_factor
            if score > best_score:
                best_score = score
                best_tier = tier

        if best_tier is None:
            result.warnings.append("No tier met minimum comparables requirement")
            return result

        best_result = tier_results[best_tier.name]
        result.selected_tier = best_tier.name
        result.selected_method = best_result.estimation_method
        result.final_annual_rent_estimate = best_result.estimated_annual_rent
        result.final_annual_rent_p25 = best_result.p25_annual
        result.final_annual_rent_p75 = best_result.p75_annual
        result.total_comparables_used = best_result.comparables_count

        # Gross rental yield
        if subject_price_aed and subject_price_aed > 0 and result.final_annual_rent_estimate:
            result.gross_rental_yield = (result.final_annual_rent_estimate / subject_price_aed) * 100
            if result.final_annual_rent_p25:
                result.yield_p25 = (result.final_annual_rent_p25 / subject_price_aed) * 100
            if result.final_annual_rent_p75:
                result.yield_p75 = (result.final_annual_rent_p75 / subject_price_aed) * 100

        # Temporal holdout on selected tier's contracts
        if run_temporal_holdout and best_result.comparables_count >= 10:
            # Get ALL candidates WITHOUT recency filter (temporal holdout handles time split internally)
            contracts = self.comparator.get_candidates(
                area, bedrooms, project, prop_type, best_tier, apply_recency=False,
                contract_strategy=contract_strategy
            )
            holdout = temporal_holdout_validation(contracts, subject_size_sqft, tier_name=best_tier.name)
            result.temporal_holdout_passed = holdout.get("passed", False)
            result.temporal_holdout_details = holdout
            if not holdout.get("passed"):
                result.warnings.append(f"Temporal holdout failed: {holdout.get('reason')}")

        return result

    def _evaluate_tier(
        self,
        tier: ComparatorTier,
        area: str,
        bedrooms: Optional[int],
        project: Optional[str],
        prop_type: Optional[str],
        subject_size_sqft: Optional[float],
        contract_strategy: str = "NEW_PLUS_RENEWED",
    ) -> TierResult:
        """Evaluate a single comparator tier."""
        warnings = []

        # Get candidates (with recency filter)
        contracts = self.comparator.get_candidates(
            area, bedrooms, project, prop_type, tier,
            contract_strategy=contract_strategy
        )

        # Apply size band filter
        contracts = self.comparator.filter_by_size_band(contracts, subject_size_sqft, tier.size_band_pct)

        if len(contracts) < tier.min_comparables:
            return TierResult(
                tier=tier.name,
                label=tier.label,
                comparables_count=len(contracts),
                annual_rents=[],
                psfs=[],
                sizes_sqft=[],
                median_annual_rent=None,
                median_psf=None,
                p25_annual=None,
                p75_annual=None,
                p25_psf=None,
                p75_psf=None,
                estimation_method="insufficient_data",
                estimated_annual_rent=None,
                confidence=0.0,
                rejected=True,
                rejection_reason=f"Only {len(contracts)} comparables (need {tier.min_comparables})",
                project_matched=tier.requires_project and project is not None,
                bedroom_matched=tier.requires_bedroom and bedrooms is not None,
                size_matched=subject_size_sqft is not None,
                area_matched=True,
                property_type_matched=prop_type is not None,
            )

        # Extract values
        annual_rents = [c.annual_amount for c in contracts]
        psfs = [c.psf for c in contracts]
        sizes = [c.actual_area_sqft for c in contracts]

        # Clean outliers
        annual_rents_clean = filter_outliers_iqr(annual_rents, 1.5)
        psfs_clean = filter_outliers_iqr(psfs, 1.5)

        if not annual_rents_clean:
            return TierResult(
                tier=tier.name,
                label=tier.label,
                comparables_count=len(contracts),
                annual_rents=annual_rents,
                psfs=psfs,
                sizes_sqft=sizes,
                median_annual_rent=None,
                median_psf=None,
                p25_annual=None,
                p75_annual=None,
                p25_psf=None,
                p75_psf=None,
                estimation_method="outlier_removal_eliminated_all",
                estimated_annual_rent=None,
                confidence=0.0,
                rejected=True,
                rejection_reason="All contracts removed as outliers",
                project_matched=tier.requires_project and project is not None,
                bedroom_matched=tier.requires_bedroom and bedrooms is not None,
                size_matched=subject_size_sqft is not None,
                area_matched=True,
                property_type_matched=prop_type is not None,
            )

        # Percentiles
        p25_annual = percentile(annual_rents_clean, 25)
        p75_annual = percentile(annual_rents_clean, 75)
        p25_psf = percentile(psfs_clean, 25) if psfs_clean else None
        p75_psf = percentile(psfs_clean, 75) if psfs_clean else None

        # Select estimation method
        method, median_annual, median_psf, _, _, _, _ = select_estimation_method(
            contracts, subject_size_sqft
        )

        if method == "median_psf_times_size":
            estimated = median_psf * subject_size_sqft if median_psf and subject_size_sqft else None
        else:
            estimated = median_annual

        # Confidence: tier weight * sample adequacy
        sample_adequacy = min(len(contracts) / tier.min_comparables, 2.0)
        confidence = tier.weight * (sample_adequacy / 2.0)

        return TierResult(
            tier=tier.name,
            label=tier.label,
            comparables_count=len(contracts),
            annual_rents=annual_rents,
            psfs=psfs,
            sizes_sqft=sizes,
            median_annual_rent=norm_median(annual_rents_clean),
            median_psf=norm_median(psfs_clean) if psfs_clean else None,
            p25_annual=p25_annual,
            p75_annual=p75_annual,
            p25_psf=p25_psf,
            p75_psf=p75_psf,
            estimation_method=method,
            estimated_annual_rent=estimated,
            confidence=confidence,
            warnings=warnings,
            project_matched=tier.requires_project and project is not None,
            bedroom_matched=tier.requires_bedroom and bedrooms is not None,
            size_matched=subject_size_sqft is not None,
            area_matched=True,
            property_type_matched=prop_type is not None,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Module-level convenience function
# ──────────────────────────────────────────────────────────────────────────────
def compute_rental_benchmark(
    area: str,
    bedrooms: Optional[int],
    project: Optional[str] = None,
    prop_type: Optional[str] = None,
    subject_size_sqft: Optional[float] = None,
    subject_price_aed: Optional[float] = None,
) -> RentalBenchmarkResult:
    """Convenience function for single-call benchmark."""
    engine = RentalBenchmarkEngine()
    return engine.compute_benchmark(
        area=area,
        bedrooms=bedrooms,
        project=project,
        prop_type=prop_type,
        subject_size_sqft=subject_size_sqft,
        subject_price_aed=subject_price_aed,
    )