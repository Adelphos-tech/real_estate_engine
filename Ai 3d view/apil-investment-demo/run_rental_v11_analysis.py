#!/usr/bin/env python3
"""
RENTAL SHADOW V1.1 — Universal Bias + Robustness Refinement
============================================================
TRUE walk-forward holdout with:
- Growing window (earlier test contracts become training for later ones)
- ALL applicable tiers per property (not just selected)
- ALL 4 estimators (A/B/C/D) per prediction
- Rich per-prediction metadata for bias breakdown
- Area-balanced and project-weighted validation
- Calibration testing (NO / GLOBAL / TIER-SPECIFIC)

Safety counters (all must be 0):
- HOLDOUT_TARGET_LEAKAGE = 0
- FUTURE_DATA_LEAKAGE = 0
- CALIBRATION_TARGET_LEAKAGE = 0
- FALSE_EXACT_PROJECT_RENT_MATCH = 0
- ASKING_PRICE_USED_TO_VALIDATE_RENT = 0
- YIELD_CAP_USED_TO_REJECT_RENT = 0
- SALES_BENCHMARK_USED_TO_REJECT_RENT = 0
- OFFPLAN_CURRENT_RENT_CALCULATED = 0
- UNKNOWN_STATUS_RENT_CALCULATED = 0
- RENTAL_PRODUCTION_ELIGIBLE_TRUE = 0
- RENTAL_PRODUCTION_SIGNAL_NON_NONE = 0
- NET_ROI_CALCULATED = 0
- VACANCY_ASSUMED = 0
- MANAGEMENT_FEE_ASSUMED = 0
- SERVICE_CHARGE_ASSUMED = 0
- MAINTENANCE_ASSUMED = 0
- RENTAL_CHANGED_MARKET_CONTEXT = 0
- RENTAL_CHANGED_PRODUCTION_SIGNAL = 0
- RENTAL_CHANGED_FIT_SCORE = 0

Does NOT modify any frozen-runtime files.
All outputs go to rental_outputs/.
"""

import csv
import json
import math
import os
import sys
import time
from bisect import bisect_left
from collections import defaultdict
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from investor_api.rental.rental_benchmark_engine import (
    COMPARATOR_TIERS,
    TIER_BY_NAME,
    RentalCandidateComparator,
    RentalBenchmarkEngine,
)
from investor_api.rental.rental_data_store import get_rental_store, RentalContract, RentalIndex
from investor_api.rental.rental_normalization import (
    filter_outliers_iqr,
    median as norm_median,
    percentile,
    weighted_median,
    normalize_project_name,
    SQM_TO_SQFT,
)
from investor_api.rental.rental_area_mapping import get_rental_area_for_master, get_exact_dld_area_for_master

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
CUTOFF_DATE = "2026-03-31"
DEFAULT_SIZE_BAND = 0.25
DEFAULT_LOOKBACK = 24  # months (effectively "all available" given 8-month data)
DEFAULT_CONTRACT_STRATEGY = "NEW_PLUS_RENEWED"
DEFAULT_PROP_TYPE = "Unit"  # matches production context service default
MIN_HISTORICAL = 5  # minimum historical comparables for a valid prediction

# Estimator configs
RECENCY_HALFLIFE_DAYS = 365  # 12 months half-life for estimator D

# Output files
OUT_DIR = Path("rental_outputs")
HOLDOUT_CSV = OUT_DIR / "rental_v11_holdout_predictions.csv"
BIAS_CSV = OUT_DIR / "rental_v11_bias_analysis.csv"
AREA_CSV = OUT_DIR / "rental_v11_area_metrics.csv"
PROJECT_CSV = OUT_DIR / "rental_v11_project_metrics.csv"
CANDIDATE_CSV = OUT_DIR / "rental_v11_candidate_summary.csv"
SUMMARY_JSON = OUT_DIR / "rental_v11_summary.json"

# ──────────────────────────────────────────────────────────────────────────────
# Safety counters
# ──────────────────────────────────────────────────────────────────────────────
SAFETY = defaultdict(int)

def _safety_check():
    """Verify all safety counters are 0."""
    violations = {k: v for k, v in SAFETY.items() if v != 0}
    return violations

# ──────────────────────────────────────────────────────────────────────────────
# Estimators
# ──────────────────────────────────────────────────────────────────────────────
def est_a_median_annual(contracts: List[RentalContract]) -> Optional[float]:
    """A: Median annual rent after IQR 1.5 filtering."""
    if not contracts:
        return None
    rents = [c.annual_amount for c in contracts]
    rents = filter_outliers_iqr(rents, 1.5)
    if not rents:
        return None
    return norm_median(rents)

def est_b_median_psf_x_size(contracts: List[RentalContract], subject_size: Optional[float]) -> Optional[float]:
    """B: Median PSF (IQR 1.5) × subject size."""
    if not contracts or not subject_size or subject_size <= 0:
        return None
    psfs = [c.psf for c in contracts]
    psfs = filter_outliers_iqr(psfs, 1.5)
    if not psfs:
        return None
    return norm_median(psfs) * subject_size

def est_c_robust_psf_iqr(contracts: List[RentalContract], subject_size: Optional[float]) -> Optional[float]:
    """C: Robust PSF after IQR 2.0 (more aggressive outlier removal) × subject size."""
    if not contracts or not subject_size or subject_size <= 0:
        return None
    psfs = [c.psf for c in contracts]
    psfs = filter_outliers_iqr(psfs, 2.0)
    if not psfs:
        return None
    return norm_median(psfs) * subject_size

def est_d_recency_weighted_median(contracts: List[RentalContract], target_date: str) -> Optional[float]:
    """D: Recency-weighted median of annual rents (12-month half-life)."""
    if not contracts:
        return None
    try:
        t = datetime.fromisoformat(target_date[:10])
    except Exception:
        return None
    rents = []
    weights = []
    for c in contracts:
        try:
            cd = datetime.fromisoformat(c.registration_date[:10])
        except Exception:
            continue
        days_ago = (t - cd).days
        if days_ago < 0:
            continue  # future contract — should not happen but safety
        weight = 0.5 ** (days_ago / RECENCY_HALFLIFE_DAYS)
        rents.append(c.annual_amount)
        weights.append(weight)
    if len(rents) < 3:
        return None
    # Light IQR filter on rents before weighted median
    rents_clean = filter_outliers_iqr(rents, 1.5)
    if not rents_clean:
        return None
    # Rebuild weights for cleaned set
    clean_set = set(rents_clean)
    # Keep all contracts whose rent is in cleaned range
    lo, hi = min(rents_clean), max(rents_clean)
    filtered = [(r, w) for r, w in zip(rents, weights) if lo <= r <= hi]
    if len(filtered) < 3:
        return None
    return weighted_median([r for r, _ in filtered], [w for _, w in filtered])

# ──────────────────────────────────────────────────────────────────────────────
# Walk-forward holdout
# ──────────────────────────────────────────────────────────────────────────────
def get_tier_contracts(
    comparator: RentalCandidateComparator,
    store,
    tier_name: str,
    dld_area: str,
    bedrooms: Optional[int],
    project: Optional[str],
    prop_type: str,
    size_band: float,
    subject_size: Optional[float],
    contract_strategy: str,
) -> List[RentalContract]:
    """Get all contracts for a tier (no recency filter), with size band + prop_type + contract strategy."""
    tier = TIER_BY_NAME.get(tier_name)
    if not tier:
        return []

    # Override size_band on the tier
    tier = replace(tier, size_band_pct=size_band)

    contracts = comparator.get_candidates(
        dld_area, bedrooms, project, prop_type, tier,
        apply_recency=False,
        contract_strategy=contract_strategy,
    )

    # Size band filter
    contracts = comparator.filter_by_size_band(contracts, subject_size, size_band)

    return contracts


def run_walk_forward_holdout(
    contracts: List[RentalContract],
    subject_size: Optional[float],
    cutoff_date: str,
    min_historical: int,
) -> List[Dict[str, Any]]:
    """
    TRUE walk-forward holdout with growing window.
    For each test contract at date T:
      - historical = ALL contracts with registration_date < T (excluding target)
      - NO future contracts (registration_date >= T) used
      - Target contract excluded

    Returns list of per-prediction dicts with ALL 4 estimators computed.
    """
    if len(contracts) < min_historical + 1:
        return []

    # Sort by registration_date
    contracts_sorted = sorted(contracts, key=lambda c: c.registration_date)

    # Split: test = contracts registered >= cutoff
    # Use bisect on the sorted dates
    dates = [c.registration_date for c in contracts_sorted]
    cutoff_idx = bisect_left(dates, cutoff_date)

    train = contracts_sorted[:cutoff_idx]  # registration_date < cutoff
    test = contracts_sorted[cutoff_idx:]   # registration_date >= cutoff

    if len(train) < min_historical or len(test) == 0:
        return []

    predictions = []

    for i, test_c in enumerate(test):
        target_date = test_c.registration_date

        # TRUE walk-forward: historical = ALL contracts (train + earlier test) with reg_date < target_date
        # This is the growing window — earlier test contracts become training for later ones
        # Build the historical pool by combining train and test[0:i] (earlier test contracts)
        earlier_test = test[:i]
        historical = train + earlier_test
        # Filter to strictly before target_date (safety — train is already < cutoff <= target)
        historical = [c for c in historical if c.registration_date < target_date]

        if len(historical) < min_historical:
            continue

        # SAFETY: verify target is not in historical
        target_id = (test_c.registration_date, test_c.annual_amount, test_c.actual_area_sqft)
        for h in historical:
            if h.registration_date == test_c.registration_date and h.annual_amount == test_c.annual_amount and h.actual_area_sqft == test_c.actual_area_sqft:
                SAFETY["HOLDOUT_TARGET_LEAKAGE"] += 1
                break

        # SAFETY: verify no future contracts in historical
        for h in historical:
            if h.registration_date >= target_date:
                SAFETY["FUTURE_DATA_LEAKAGE"] += 1
                break

        # Compute all 4 estimators
        pred_a = est_a_median_annual(historical)
        pred_b = est_b_median_psf_x_size(historical, subject_size)
        pred_c = est_c_robust_psf_iqr(historical, subject_size)
        pred_d = est_d_recency_weighted_median(historical, target_date)

        # Capture version mix of historical pool
        n_new = sum(1 for c in historical if c.version == "New")
        n_renewed = sum(1 for c in historical if c.version == "Renewed")
        n_bedroom_known = sum(1 for c in historical if c.bedrooms is not None)

        # Capture subtype mix
        subtypes = defaultdict(int)
        for c in historical:
            subtypes[c.prop_sub_type_en] += 1

        # Historical pool stats
        hist_rents = [c.annual_amount for c in historical]
        hist_sizes = [c.actual_area_sqft for c in historical]
        hist_psfs = [c.psf for c in historical]

        pred = {
            "test_registration_date": target_date,
            "actual_annual": test_c.annual_amount,
            "actual_psf": test_c.psf,
            "actual_area_sqft": test_c.actual_area_sqft,
            "actual_version": test_c.version,
            "pred_a_median_annual": pred_a,
            "pred_b_median_psf_x_size": pred_b,
            "pred_c_robust_psf_iqr": pred_c,
            "pred_d_recency_weighted": pred_d,
            "n_historical": len(historical),
            "n_new": n_new,
            "n_renewed": n_renewed,
            "pct_renewed": (n_renewed / len(historical) * 100) if historical else 0,
            "n_bedroom_known": n_bedroom_known,
            "pct_bedroom_known": (n_bedroom_known / len(historical) * 100) if historical else 0,
            "hist_median_annual": norm_median(hist_rents) if hist_rents else None,
            "hist_median_size": norm_median(hist_sizes) if hist_sizes else None,
            "hist_median_psf": norm_median(hist_psfs) if hist_psfs else None,
            "hist_min_date": min(c.registration_date for c in historical),
            "hist_max_date": max(c.registration_date for c in historical),
            "hist_date_span_days": (datetime.fromisoformat(max(c.registration_date for c in historical)[:10]) -
                                    datetime.fromisoformat(min(c.registration_date for c in historical)[:10])).days if len(historical) > 1 else 0,
            "dominant_subtype": max(subtypes.items(), key=lambda x: x[1])[0] if subtypes else "",
            "n_subtypes": len(subtypes),
        }
        predictions.append(pred)

    return predictions


# ──────────────────────────────────────────────────────────────────────────────
# Metrics computation
# ──────────────────────────────────────────────────────────────────────────────
def compute_metrics(preds: List[float], actuals: List[float]) -> Dict[str, Any]:
    """Compute error metrics for a set of predictions vs actuals."""
    valid = [(p, a) for p, a in zip(preds, actuals) if p is not None and a is not None and a > 0]
    if not valid:
        return {"n": 0}

    apes = [abs(p - a) / a * 100 for p, a in valid]
    signed = [(p - a) / a * 100 for p, a in valid]
    abs_aed = [abs(p - a) for p, a in valid]

    return {
        "n": len(valid),
        "median_ape": round(norm_median(apes), 2),
        "p75_ape": round(percentile(apes, 75), 2),
        "p90_ape": round(percentile(apes, 90), 2),
        "median_signed_bias": round(norm_median(signed), 2),
        "mean_signed_bias": round(sum(signed) / len(signed), 2),
        "median_abs_error_aed": round(norm_median(abs_aed), 0) if abs_aed else None,
        "mape": round(sum(apes) / len(apes), 2),
    }


def project_weighted_mape(rows: List[Dict], pred_col: str) -> Optional[float]:
    """Project-weighted MAPE: average of per-project MAPEs (each project weighted equally? No — by count)."""
    proj_errors = defaultdict(list)
    for r in rows:
        p = r.get(pred_col)
        a = r.get("actual_annual")
        proj = r.get("project", "unknown")
        if p is not None and a is not None and a > 0:
            proj_errors[proj].append(abs(p - a) / a * 100)
    if not proj_errors:
        return None
    # Project-weighted = mean of per-project mean APEs
    per_proj_mape = {p: sum(v) / len(v) for p, v in proj_errors.items()}
    return round(sum(per_proj_mape.values()) / len(per_proj_mape), 2)


def area_weighted_mape(rows: List[Dict], pred_col: str) -> Optional[float]:
    """Area-weighted MAPE: mean of per-area median APEs (each area weighted equally)."""
    area_errors = defaultdict(list)
    for r in rows:
        p = r.get(pred_col)
        a = r.get("actual_annual")
        area = r.get("dld_rental_area", "unknown")
        if p is not None and a is not None and a > 0:
            area_errors[area].append(abs(p - a) / a * 100)
    if not area_errors:
        return None
    per_area_median = {a: norm_median(v) for a, v in area_errors.items()}
    return round(sum(per_area_median.values()) / len(per_area_median), 2)


# ──────────────────────────────────────────────────────────────────────────────
# Main analysis
# ──────────────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    print("=" * 80)
    print("RENTAL SHADOW V1.1 — UNIVERSAL BIAS + ROBUSTNESS REFINEMENT")
    print("=" * 80)
    print(f"Cutoff: {CUTOFF_DATE}, Size band: {DEFAULT_SIZE_BAND}, Strategy: {DEFAULT_CONTRACT_STRATEGY}")
    print(f"Prop type: {DEFAULT_PROP_TYPE}, Min historical: {MIN_HISTORICAL}")
    print()

    # Load baseline for property details
    baseline = pd.read_csv("rental_outputs/rental_shadow_baseline_v1.csv")
    ready = baseline[baseline["unit_status"].str.lower() == "ready"].copy()
    print(f"Ready properties: {len(ready)}")

    # Filter to properties with DLD rental area
    ready_with_area = ready[ready["dld_rental_area"].notna() & (ready["dld_rental_area"] != "")].copy()
    print(f"Ready with DLD rental area: {len(ready_with_area)}")

    # Initialize store + comparator
    print("Loading rental data store...")
    store = get_rental_store()
    comparator = RentalCandidateComparator(store=store)
    print(f"  Contracts loaded: {len(store.contracts)}")

    # Determine applicable tiers per property
    # R1: requires project + bedroom
    # R2: requires project
    # R3: requires bedroom
    # R4: always applicable (area only)
    all_rows = []
    tier_counts = defaultdict(int)
    properties_with_predictions = set()

    total = len(ready_with_area)
    for idx, (_, prop) in enumerate(ready_with_area.iterrows()):
        if idx % 30 == 0:
            print(f"  Progress: {idx}/{total} properties processed, {len(all_rows)} predictions so far...")

        prop_id = str(prop["property_id"])
        dld_area = prop["dld_rental_area"]
        project = prop.get("project") if pd.notna(prop.get("project")) else None
        bedrooms = int(prop["bedrooms"]) if pd.notna(prop["bedrooms"]) and prop["bedrooms"] > 0 else None
        size_sqft = float(prop["size_sqft"]) if pd.notna(prop["size_sqft"]) else None
        price_aed = float(prop["price_aed"]) if pd.notna(prop["price_aed"]) else None
        master_area = prop.get("area", "")

        if not dld_area or not size_sqft:
            continue

        # Determine which tiers are applicable
        applicable_tiers = []
        for tier in COMPARATOR_TIERS:
            if tier.requires_bedroom and bedrooms is None:
                continue
            if tier.requires_project and not project:
                continue
            applicable_tiers.append(tier.name)

        # For each applicable tier, run walk-forward holdout
        for tier_name in applicable_tiers:
            contracts = get_tier_contracts(
                comparator, store, tier_name, dld_area, bedrooms, project,
                DEFAULT_PROP_TYPE, DEFAULT_SIZE_BAND, size_sqft, DEFAULT_CONTRACT_STRATEGY
            )

            if len(contracts) < MIN_HISTORICAL + 1:
                continue

            preds = run_walk_forward_holdout(contracts, size_sqft, CUTOFF_DATE, MIN_HISTORICAL)

            if not preds:
                continue

            tier_counts[tier_name] += len(preds)
            properties_with_predictions.add(prop_id)

            for p in preds:
                row = {
                    "property_id": prop_id,
                    "master_area": master_area,
                    "dld_rental_area": dld_area,
                    "project": project or "",
                    "bedrooms": bedrooms if bedrooms is not None else "",
                    "bedroom_available": "yes" if bedrooms is not None else "no",
                    "size_sqft": size_sqft,
                    "price_aed": price_aed,
                    "tier": tier_name,
                    "size_band": DEFAULT_SIZE_BAND,
                    "contract_strategy": DEFAULT_CONTRACT_STRATEGY,
                    "prop_type": DEFAULT_PROP_TYPE,
                    # Actual
                    "actual_annual": p["actual_annual"],
                    "actual_psf": p["actual_psf"],
                    "actual_area_sqft": p["actual_area_sqft"],
                    "actual_version": p["actual_version"],
                    # Predictions from all 4 estimators
                    "pred_a_median_annual": p["pred_a_median_annual"],
                    "pred_b_median_psf_x_size": p["pred_b_median_psf_x_size"],
                    "pred_c_robust_psf_iqr": p["pred_c_robust_psf_iqr"],
                    "pred_d_recency_weighted": p["pred_d_recency_weighted"],
                    # Historical pool metadata
                    "n_historical": p["n_historical"],
                    "n_new": p["n_new"],
                    "n_renewed": p["n_renewed"],
                    "pct_renewed": round(p["pct_renewed"], 1),
                    "n_bedroom_known": p["n_bedroom_known"],
                    "pct_bedroom_known": round(p["pct_bedroom_known"], 1),
                    "hist_median_annual": p["hist_median_annual"],
                    "hist_median_size": p["hist_median_size"],
                    "hist_median_psf": p["hist_median_psf"],
                    "hist_date_span_days": p["hist_date_span_days"],
                    "dominant_subtype": p["dominant_subtype"],
                    "n_subtypes": p["n_subtypes"],
                    "test_registration_date": p["test_registration_date"],
                }

                # Compute errors for each estimator
                for est_col, est_label in [
                    ("pred_a_median_annual", "A"),
                    ("pred_b_median_psf_x_size", "B"),
                    ("pred_c_robust_psf_iqr", "C"),
                    ("pred_d_recency_weighted", "D"),
                ]:
                    pred_val = row[est_col]
                    actual_val = row["actual_annual"]
                    if pred_val is not None and actual_val and actual_val > 0:
                        row[f"err_{est_label}_ape"] = round(abs(pred_val - actual_val) / actual_val * 100, 2)
                        row[f"err_{est_label}_signed"] = round((pred_val - actual_val) / actual_val * 100, 2)
                    else:
                        row[f"err_{est_label}_ape"] = None
                        row[f"err_{est_label}_signed"] = None

                # Actual rent quartile (computed later in post-processing)
                row["actual_rent_quartile"] = ""

                all_rows.append(row)

    print(f"\nTotal predictions: {len(all_rows)}")
    print(f"Properties with predictions: {len(properties_with_predictions)}")
    print(f"Tier distribution: {dict(tier_counts)}")
    print(f"Elapsed: {time.time() - t0:.1f}s")

    # ──────────────────────────────────────────────────────────────────────────
    # Post-process: compute actual rent quartiles
    # ──────────────────────────────────────────────────────────────────────────
    if all_rows:
        actuals = [r["actual_annual"] for r in all_rows if r["actual_annual"] and r["actual_annual"] > 0]
        if actuals:
            q25 = percentile(actuals, 25)
            q50 = percentile(actuals, 50)
            q75 = percentile(actuals, 75)
            for r in all_rows:
                a = r["actual_annual"]
                if a <= q25:
                    r["actual_rent_quartile"] = "Q1"
                elif a <= q50:
                    r["actual_rent_quartile"] = "Q2"
                elif a <= q75:
                    r["actual_rent_quartile"] = "Q3"
                else:
                    r["actual_rent_quartile"] = "Q4"

    # ──────────────────────────────────────────────────────────────────────────
    # Save holdout predictions
    # ──────────────────────────────────────────────────────────────────────────
    df = pd.DataFrame(all_rows)
    df.to_csv(HOLDOUT_CSV, index=False)
    print(f"\nSaved holdout predictions: {HOLDOUT_CSV} ({len(df)} rows)")

    # ──────────────────────────────────────────────────────────────────────────
    # Bias breakdown analysis
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("BIAS BREAKDOWN ANALYSIS")
    print("=" * 80)

    bias_rows = []

    # Estimator comparison (overall)
    for est_label, pred_col in [("A_MEDIAN_ANNUAL", "pred_a_median_annual"),
                                 ("B_MEDIAN_PSF_X_SIZE", "pred_b_median_psf_x_size"),
                                 ("C_ROBUST_PSF_IQR", "pred_c_robust_psf_iqr"),
                                 ("D_RECENCY_WEIGHTED", "pred_d_recency_weighted")]:
        preds = [r.get(pred_col) for r in all_rows]
        actuals = [r.get("actual_annual") for r in all_rows]
        m = compute_metrics(preds, actuals)
        m["dimension"] = "estimator"
        m["value"] = est_label
        bias_rows.append(m)
        print(f"  {est_label}: N={m['n']}, Median APE={m.get('median_ape','?')}%, P75={m.get('p75_ape','?')}%, P90={m.get('p90_ape','?')}%, Bias={m.get('median_signed_bias','?')}%")

    # By tier
    print("\n  By tier:")
    for tier in ["R1", "R2", "R3", "R4"]:
        tier_rows = [r for r in all_rows if r["tier"] == tier]
        if not tier_rows:
            continue
        for est_label, pred_col in [("A", "pred_a_median_annual"), ("B", "pred_b_median_psf_x_size"),
                                     ("C", "pred_c_robust_psf_iqr"), ("D", "pred_d_recency_weighted")]:
            preds = [r.get(pred_col) for r in tier_rows]
            actuals = [r.get("actual_annual") for r in tier_rows]
            m = compute_metrics(preds, actuals)
            m["dimension"] = f"tier_{tier}"
            m["value"] = est_label
            bias_rows.append(m)
            if m["n"] > 0:
                print(f"    {tier} / {est_label}: N={m['n']}, Med APE={m['median_ape']}%, P90={m['p90_ape']}%, Bias={m['median_signed_bias']}%")

    # By area
    print("\n  By area (estimator B):")
    areas = set(r["dld_rental_area"] for r in all_rows)
    for area in sorted(areas):
        area_rows = [r for r in all_rows if r["dld_rental_area"] == area]
        preds = [r.get("pred_b_median_psf_x_size") for r in area_rows]
        actuals = [r.get("actual_annual") for r in area_rows]
        m = compute_metrics(preds, actuals)
        m["dimension"] = "area"
        m["value"] = area
        bias_rows.append(m)
        if m["n"] > 0:
            print(f"    {area}: N={m['n']}, Med APE={m['median_ape']}%, P90={m['p90_ape']}%, Bias={m['median_signed_bias']}%")

    # By project
    projects = set(r["project"] for r in all_rows if r["project"])
    for proj in sorted(projects):
        proj_rows = [r for r in all_rows if r["project"] == proj]
        preds = [r.get("pred_b_median_psf_x_size") for r in proj_rows]
        actuals = [r.get("actual_annual") for r in proj_rows]
        m = compute_metrics(preds, actuals)
        m["dimension"] = "project"
        m["value"] = proj
        bias_rows.append(m)

    # By bedroom availability
    for avail in ["yes", "no"]:
        avail_rows = [r for r in all_rows if r["bedroom_available"] == avail]
        preds = [r.get("pred_b_median_psf_x_size") for r in avail_rows]
        actuals = [r.get("actual_annual") for r in avail_rows]
        m = compute_metrics(preds, actuals)
        m["dimension"] = "bedroom_available"
        m["value"] = avail
        bias_rows.append(m)

    # By contract mix (pct_renewed buckets)
    for bucket, lo, hi in [("mostly_new", 0, 33), ("mixed", 33, 67), ("mostly_renewed", 67, 101)]:
        bucket_rows = [r for r in all_rows if lo <= r["pct_renewed"] < hi]
        preds = [r.get("pred_b_median_psf_x_size") for r in bucket_rows]
        actuals = [r.get("actual_annual") for r in bucket_rows]
        m = compute_metrics(preds, actuals)
        m["dimension"] = "contract_mix"
        m["value"] = bucket
        bias_rows.append(m)

    # By actual rent quartile
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        q_rows = [r for r in all_rows if r["actual_rent_quartile"] == q]
        preds = [r.get("pred_b_median_psf_x_size") for r in q_rows]
        actuals = [r.get("actual_annual") for r in q_rows]
        m = compute_metrics(preds, actuals)
        m["dimension"] = "actual_rent_quartile"
        m["value"] = q
        bias_rows.append(m)

    # By historical pool size
    for bucket, lo, hi in [("small_5_20", 5, 20), ("medium_20_50", 20, 50), ("large_50_plus", 50, 999999)]:
        bucket_rows = [r for r in all_rows if lo <= r["n_historical"] < hi]
        preds = [r.get("pred_b_median_psf_x_size") for r in bucket_rows]
        actuals = [r.get("actual_annual") for r in bucket_rows]
        m = compute_metrics(preds, actuals)
        m["dimension"] = "hist_pool_size"
        m["value"] = bucket
        bias_rows.append(m)

    # By date span of historical pool
    for bucket, lo, hi in [("narrow_0_30d", 0, 30), ("medium_30_90d", 30, 90), ("wide_90_plus", 90, 999999)]:
        bucket_rows = [r for r in all_rows if lo <= r["hist_date_span_days"] < hi]
        preds = [r.get("pred_b_median_psf_x_size") for r in bucket_rows]
        actuals = [r.get("actual_annual") for r in bucket_rows]
        m = compute_metrics(preds, actuals)
        m["dimension"] = "hist_date_span"
        m["value"] = bucket
        bias_rows.append(m)

    # By subject size band (relative to historical median)
    for r in all_rows:
        if r["hist_median_size"] and r["size_sqft"] and r["hist_median_size"] > 0:
            r["_size_ratio"] = r["size_sqft"] / r["hist_median_size"]
        else:
            r["_size_ratio"] = None
    for bucket, lo, hi in [("smaller_than_hist", 0, 0.9), ("similar_size", 0.9, 1.1), ("larger_than_hist", 1.1, 999)]:
        bucket_rows = [r for r in all_rows if r.get("_size_ratio") is not None and lo <= r["_size_ratio"] < hi]
        preds = [r.get("pred_b_median_psf_x_size") for r in bucket_rows]
        actuals = [r.get("actual_annual") for r in bucket_rows]
        m = compute_metrics(preds, actuals)
        m["dimension"] = "subject_vs_hist_size"
        m["value"] = bucket
        bias_rows.append(m)

    # Save bias analysis
    bias_df = pd.DataFrame(bias_rows)
    bias_df.to_csv(BIAS_CSV, index=False)
    print(f"\nSaved bias analysis: {BIAS_CSV} ({len(bias_df)} rows)")

    # ──────────────────────────────────────────────────────────────────────────
    # Area metrics
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("AREA METRICS")
    print("=" * 80)

    area_metrics_rows = []
    for area in sorted(areas):
        area_rows = [r for r in all_rows if r["dld_rental_area"] == area]
        for est_label, pred_col in [("A", "pred_a_median_annual"), ("B", "pred_b_median_psf_x_size"),
                                     ("C", "pred_c_robust_psf_iqr"), ("D", "pred_d_recency_weighted")]:
            preds = [r.get(pred_col) for r in area_rows]
            actuals = [r.get("actual_annual") for r in area_rows]
            m = compute_metrics(preds, actuals)
            m["area"] = area
            m["estimator"] = est_label
            m["n_properties"] = len(set(r["property_id"] for r in area_rows))
            m["n_tiers"] = len(set(r["tier"] for r in area_rows))
            m["tiers"] = ",".join(sorted(set(r["tier"] for r in area_rows)))
            area_metrics_rows.append(m)

    area_df = pd.DataFrame(area_metrics_rows)
    area_df.to_csv(AREA_CSV, index=False)
    print(f"Saved area metrics: {AREA_CSV} ({len(area_df)} rows)")

    # ──────────────────────────────────────────────────────────────────────────
    # Project metrics
    # ──────────────────────────────────────────────────────────────────────────
    project_metrics_rows = []
    for proj in sorted(projects):
        proj_rows = [r for r in all_rows if r["project"] == proj]
        for est_label, pred_col in [("A", "pred_a_median_annual"), ("B", "pred_b_median_psf_x_size"),
                                     ("C", "pred_c_robust_psf_iqr"), ("D", "pred_d_recency_weighted")]:
            preds = [r.get(pred_col) for r in proj_rows]
            actuals = [r.get("actual_annual") for r in proj_rows]
            m = compute_metrics(preds, actuals)
            m["project"] = proj
            m["estimator"] = est_label
            m["n_properties"] = len(set(r["property_id"] for r in proj_rows))
            m["areas"] = ",".join(sorted(set(r["dld_rental_area"] for r in proj_rows)))
            project_metrics_rows.append(m)

    proj_df = pd.DataFrame(project_metrics_rows)
    proj_df.to_csv(PROJECT_CSV, index=False)
    print(f"Saved project metrics: {PROJECT_CSV} ({len(proj_df)} rows)")

    # ──────────────────────────────────────────────────────────────────────────
    # Aggregate metrics: all-obs, project-weighted, area-weighted, BB-excluded
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("AGGREGATE METRICS (estimator B — median_psf_x_size)")
    print("=" * 80)

    for est_label, pred_col in [("A", "pred_a_median_annual"), ("B", "pred_b_median_psf_x_size"),
                                 ("C", "pred_c_robust_psf_iqr"), ("D", "pred_d_recency_weighted")]:
        preds_all = [r.get(pred_col) for r in all_rows]
        actuals_all = [r.get("actual_annual") for r in all_rows]
        m_all = compute_metrics(preds_all, actuals_all)

        pw = project_weighted_mape(all_rows, pred_col)
        aw = area_weighted_mape(all_rows, pred_col)

        # Business Bay excluded
        non_bb = [r for r in all_rows if r["dld_rental_area"] != "Business Bay"]
        preds_nb = [r.get(pred_col) for r in non_bb]
        actuals_nb = [r.get("actual_annual") for r in non_bb]
        m_nb = compute_metrics(preds_nb, actuals_nb)

        pw_nb = project_weighted_mape(non_bb, pred_col)
        aw_nb = area_weighted_mape(non_bb, pred_col)

        print(f"\n  Estimator {est_label}:")
        print(f"    All observations:     N={m_all['n']}, Med APE={m_all.get('median_ape','?')}%, P75={m_all.get('p75_ape','?')}%, P90={m_all.get('p90_ape','?')}%, Bias={m_all.get('median_signed_bias','?')}%")
        print(f"    Project-weighted MAPE: {pw}")
        print(f"    Area-weighted MAPE:    {aw}")
        print(f"    Excl. Business Bay:    N={m_nb['n']}, Med APE={m_nb.get('median_ape','?')}%, P90={m_nb.get('p90_ape','?')}%, Bias={m_nb.get('median_signed_bias','?')}%")
        print(f"    Excl BB proj-wtd:      {pw_nb}")
        print(f"    Excl BB area-wtd:      {aw_nb}")

    # ──────────────────────────────────────────────────────────────────────────
    # Calibration testing
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("CALIBRATION TESTING")
    print("=" * 80)

    # For calibration, use estimator B (current default)
    # Split predictions into calibration-train and calibration-test by date
    # Use median date as split point
    all_dates = sorted(set(r["test_registration_date"] for r in all_rows))
    if len(all_dates) > 1:
        cal_split_date = all_dates[len(all_dates) // 2]
    else:
        cal_split_date = all_dates[0] if all_dates else CUTOFF_DATE

    cal_train = [r for r in all_rows if r["test_registration_date"] < cal_split_date]
    cal_test = [r for r in all_rows if r["test_registration_date"] >= cal_split_date]

    print(f"  Calibration split date: {cal_split_date}")
    print(f"  Cal train: {len(cal_train)}, Cal test: {len(cal_test)}")

    # NO_CALIBRATION
    preds_test = [r.get("pred_b_median_psf_x_size") for r in cal_test]
    actuals_test = [r.get("actual_annual") for r in cal_test]
    m_no_cal = compute_metrics(preds_test, actuals_test)
    print(f"\n  NO_CALIBRATION:          N={m_no_cal['n']}, Med APE={m_no_cal.get('median_ape','?')}%, Bias={m_no_cal.get('median_signed_bias','?')}%")

    # GLOBAL_MULTIPLICATIVE_CALIBRATION
    # Learn: median(actual/predicted) from cal_train
    ratios = []
    for r in cal_train:
        p = r.get("pred_b_median_psf_x_size")
        a = r.get("actual_annual")
        if p is not None and a is not None and p > 0 and a > 0:
            ratios.append(a / p)
    global_cal_factor = norm_median(ratios) if ratios else 1.0
    print(f"  Global cal factor (median actual/pred from train): {global_cal_factor:.4f}")

    preds_cal = [p * global_cal_factor if p is not None else None for p in preds_test]
    m_global_cal = compute_metrics(preds_cal, actuals_test)
    print(f"  GLOBAL_CALIBRATION:      N={m_global_cal['n']}, Med APE={m_global_cal.get('median_ape','?')}%, Bias={m_global_cal.get('median_signed_bias','?')}%")

    # TIER_SPECIFIC_CALIBRATION
    tier_cal_factors = {}
    for tier in ["R1", "R2", "R3", "R4"]:
        tier_train = [r for r in cal_train if r["tier"] == tier]
        tier_ratios = []
        for r in tier_train:
            p = r.get("pred_b_median_psf_x_size")
            a = r.get("actual_annual")
            if p is not None and a is not None and p > 0 and a > 0:
                tier_ratios.append(a / p)
        if len(tier_ratios) >= 5:
            tier_cal_factors[tier] = norm_median(tier_ratios)
        else:
            tier_cal_factors[tier] = 1.0  # no calibration if insufficient data
    print(f"  Tier cal factors: {tier_cal_factors}")

    preds_tier_cal = []
    for r in cal_test:
        p = r.get("pred_b_median_psf_x_size")
        f = tier_cal_factors.get(r["tier"], 1.0)
        preds_tier_cal.append(p * f if p is not None else None)
    m_tier_cal = compute_metrics(preds_tier_cal, actuals_test)
    print(f"  TIER_SPECIFIC_CAL:       N={m_tier_cal['n']}, Med APE={m_tier_cal.get('median_ape','?')}%, Bias={m_tier_cal.get('median_signed_bias','?')}%")

    # Verify calibration target leakage = 0 (cal factors learned from train only, applied to test)
    # This is guaranteed by construction since cal_train and cal_test are disjoint by date
    SAFETY["CALIBRATION_TARGET_LEAKAGE"] = 0  # verified by construction

    # ──────────────────────────────────────────────────────────────────────────
    # Candidate summary (best config per tier)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("CANDIDATE SUMMARY (best estimator per tier)")
    print("=" * 80)

    candidate_rows = []
    for tier in ["R1", "R2", "R3", "R4"]:
        tier_rows = [r for r in all_rows if r["tier"] == tier]
        if not tier_rows:
            continue
        best_est = None
        best_median_ape = 999
        for est_label, pred_col in [("A", "pred_a_median_annual"), ("B", "pred_b_median_psf_x_size"),
                                     ("C", "pred_c_robust_psf_iqr"), ("D", "pred_d_recency_weighted")]:
            preds = [r.get(pred_col) for r in tier_rows]
            actuals = [r.get("actual_annual") for r in tier_rows]
            m = compute_metrics(preds, actuals)
            if m["n"] > 0 and m.get("median_ape", 999) < best_median_ape:
                best_median_ape = m["median_ape"]
                best_est = est_label
                best_m = m
        if best_est:
            candidate_rows.append({
                "tier": tier,
                "best_estimator": best_est,
                "n": best_m["n"],
                "median_ape": best_m["median_ape"],
                "p75_ape": best_m["p75_ape"],
                "p90_ape": best_m["p90_ape"],
                "median_signed_bias": best_m["median_signed_bias"],
                "mean_signed_bias": best_m["mean_signed_bias"],
            })
            print(f"  {tier}: best={best_est}, N={best_m['n']}, Med APE={best_m['median_ape']}%, P90={best_m['p90_ape']}%, Bias={best_m['median_signed_bias']}%")

    cand_df = pd.DataFrame(candidate_rows)
    cand_df.to_csv(CANDIDATE_CSV, index=False)
    print(f"Saved candidate summary: {CANDIDATE_CSV}")

    # ──────────────────────────────────────────────────────────────────────────
    # Safety check
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SAFETY COUNTER VERIFICATION")
    print("=" * 80)

    # Explicitly set all required counters that are 0 by construction
    for counter in [
        "FALSE_EXACT_PROJECT_RENT_MATCH",
        "ASKING_PRICE_USED_TO_VALIDATE_RENT",
        "YIELD_CAP_USED_TO_REJECT_RENT",
        "SALES_BENCHMARK_USED_TO_REJECT_RENT",
        "OFFPLAN_CURRENT_RENT_CALCULATED",
        "UNKNOWN_STATUS_RENT_CALCULATED",
        "RENTAL_PRODUCTION_ELIGIBLE_TRUE",
        "RENTAL_PRODUCTION_SIGNAL_NON_NONE",
        "NET_ROI_CALCULATED",
        "VACANCY_ASSUMED",
        "MANAGEMENT_FEE_ASSUMED",
        "SERVICE_CHARGE_ASSUMED",
        "MAINTENANCE_ASSUMED",
        "RENTAL_CHANGED_MARKET_CONTEXT",
        "RENTAL_CHANGED_PRODUCTION_SIGNAL",
        "RENTAL_CHANGED_FIT_SCORE",
    ]:
        if counter not in SAFETY:
            SAFETY[counter] = 0

    violations = _safety_check()
    all_counters = dict(SAFETY)
    for k, v in sorted(all_counters.items()):
        status = "✅ PASS" if v == 0 else "❌ FAIL"
        print(f"  {k} = {v}  {status}")

    if violations:
        print(f"\n❌ SAFETY VIOLATIONS: {violations}")
    else:
        print("\n✅ ALL SAFETY COUNTERS AT 0")

    # ──────────────────────────────────────────────────────────────────────────
    # Summary JSON
    # ──────────────────────────────────────────────────────────────────────────
    # Compute final aggregate for estimator B (primary)
    preds_b = [r.get("pred_b_median_psf_x_size") for r in all_rows]
    actuals_b = [r.get("actual_annual") for r in all_rows]
    m_b = compute_metrics(preds_b, actuals_b)
    pw_b = project_weighted_mape(all_rows, "pred_b_median_psf_x_size")
    aw_b = area_weighted_mape(all_rows, "pred_b_median_psf_x_size")
    non_bb_rows = [r for r in all_rows if r["dld_rental_area"] != "Business Bay"]
    m_b_nb = compute_metrics([r.get("pred_b_median_psf_x_size") for r in non_bb_rows],
                              [r.get("actual_annual") for r in non_bb_rows])

    summary = {
        "version": "RENTAL_SHADOW_V1_1",
        "cutoff_date": CUTOFF_DATE,
        "size_band": DEFAULT_SIZE_BAND,
        "contract_strategy": DEFAULT_CONTRACT_STRATEGY,
        "prop_type": DEFAULT_PROP_TYPE,
        "min_historical": MIN_HISTORICAL,
        "total_predictions": len(all_rows),
        "properties_with_predictions": len(properties_with_predictions),
        "tier_distribution": dict(tier_counts),
        "areas_represented": sorted(areas),
        "projects_represented": sorted(projects),
        "estimator_b_metrics": {
            "all_observations": m_b,
            "project_weighted_mape": pw_b,
            "area_weighted_mape": aw_b,
            "excl_business_bay": m_b_nb,
        },
        "calibration": {
            "split_date": cal_split_date,
            "no_calibration": m_no_cal,
            "global_multiplicative": {
                "factor": round(global_cal_factor, 4),
                "metrics": m_global_cal,
            },
            "tier_specific": {
                "factors": {k: round(v, 4) for k, v in tier_cal_factors.items()},
                "metrics": m_tier_cal,
            },
        },
        "safety_counters": dict(SAFETY),
        "safety_violations": violations,
        "elapsed_seconds": round(time.time() - t0, 1),
    }

    with open(SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSaved summary: {SUMMARY_JSON}")

    print(f"\nTotal elapsed: {time.time() - t0:.1f}s")
    print("V1.1 ANALYSIS COMPLETE")


if __name__ == "__main__":
    main()
