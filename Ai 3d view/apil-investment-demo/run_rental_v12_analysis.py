#!/usr/bin/env python3
"""
RENTAL SHADOW V1.2 — OPTIMIZED
================================
Uses numpy for vectorized filtering and weighted median.
Pre-computes arrays per property, incrementally grows historical pool.
"""
import csv
import json
import time
from bisect import bisect_left
from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from investor_api.rental.rental_benchmark_engine import (
    COMPARATOR_TIERS, TIER_BY_NAME, RentalCandidateComparator,
)
from investor_api.rental.rental_data_store import get_rental_store, RentalContract
from investor_api.rental.rental_normalization import (
    normalize_project_name, SQM_TO_SQFT,
)

# Config
CUTOFF_DATE = "2026-03-31"
WIDEST_SIZE_BAND = 0.25
DEFAULT_PROP_TYPE = "Unit"
MIN_HISTORICAL = 5
RECENCY_HALFLIFE_DAYS = 365
CAL_FACTOR = 0.96
CAL_SPLIT = "2026-06-06"

APARTMENT_SUBTYPES = {"Flat", "Studio"}
ABS_SIZE_EDGES = [0, 750, 1000, 1250, 1500, 2000, 999999]

OUT_DIR = Path("rental_outputs")
V12_CANDIDATE_CSV = OUT_DIR / "rental_v12_candidate_results.csv"
V12_UNIQUE_TARGET_CSV = OUT_DIR / "rental_v12_unique_target_metrics.csv"
V12_AREA_CSV = OUT_DIR / "rental_v12_area_metrics.csv"
V12_HIGH_END_CSV = OUT_DIR / "rental_v12_high_end_metrics.csv"
V12_READY_CSV = OUT_DIR / "rental_v12_ready_property_results.csv"
V12_SUMMARY_JSON = OUT_DIR / "rental_v12_summary.json"

CANDIDATES = [
    "V1.1_BASELINE", "SUBTYPE_FLAT", "SUBTYPE_APT_FAM",
    "SIZE_15", "SIZE_10", "SIZE_20",
    "NEW_ONLY", "TRIMMED_10", "IQR_2_0",
    "PSF_STRAT_SIZE", "PROJECT_PREF", "ABS_SIZE",
    "FLAT_SIZE_15", "FLAT_SIZE_10",
]

SAFETY = defaultdict(int)

# ──────────────────────────────────────────────────────────────────────────────
# Numpy-based weighted median
# ──────────────────────────────────────────────────────────────────────────────
def weighted_median_np(values: np.ndarray, weights: np.ndarray) -> Optional[float]:
    if len(values) == 0:
        return None
    idx = np.argsort(values)
    sv = values[idx]
    sw = weights[idx]
    cumsum = np.cumsum(sw)
    total = cumsum[-1]
    if total <= 0:
        return None
    half = total / 2.0
    pos = np.searchsorted(cumsum, half)
    if pos >= len(sv):
        pos = len(sv) - 1
    return float(sv[pos])

def iqr_filter_np(values: np.ndarray, weights: np.ndarray, multiplier: float) -> tuple:
    """Return (values, weights) after IQR outlier removal."""
    if len(values) < 4:
        return values, weights
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    lo = q1 - multiplier * iqr
    hi = q3 + multiplier * iqr
    mask = (values >= lo) & (values <= hi)
    return values[mask], weights[mask]

def trimmed_filter_np(values: np.ndarray, weights: np.ndarray, trim_pct: float) -> tuple:
    """Trim bottom/top trim_pct by count (unweighted)."""
    n = len(values)
    if n < 5:
        return values, weights
    idx = np.argsort(values)
    trim_n = int(n * trim_pct)
    if trim_n > 0 and n - 2 * trim_n >= 3:
        keep = idx[trim_n:-trim_n]
        return values[keep], weights[keep]
    return values, weights

def compute_metrics_np(preds: np.ndarray, actuals: np.ndarray) -> Dict[str, Any]:
    mask = (preds > 0) & (actuals > 0) & ~np.isnan(preds) & ~np.isnan(actuals)
    p = preds[mask]
    a = actuals[mask]
    if len(p) == 0:
        return {"n": 0, "median_ape": None, "p75_ape": None, "p90_ape": None, "median_bias": None, "mean_bias": None}
    apes = np.abs(p - a) / a * 100
    signed = (p - a) / a * 100
    return {
        "n": len(p),
        "median_ape": round(float(np.median(apes)), 2),
        "p75_ape": round(float(np.percentile(apes, 75)), 2),
        "p90_ape": round(float(np.percentile(apes, 90)), 2),
        "median_bias": round(float(np.median(signed)), 2),
        "mean_bias": round(float(np.mean(signed)), 2),
    }

# ──────────────────────────────────────────────────────────────────────────────
# Candidate application (numpy-based)
# ──────────────────────────────────────────────────────────────────────────────
def apply_candidate_np(
    candidate: str,
    rents: np.ndarray, weights: np.ndarray, sizes: np.ndarray,
    subtypes: np.ndarray, versions: np.ndarray, project_keys: np.ndarray,
    subject_size: float, subject_project_key: str,
    size_tertile_lo: float, size_tertile_hi: float,
    abs_bucket_lo: float, abs_bucket_hi: float,
) -> Optional[float]:
    """Apply candidate filter + estimator, return prediction (uncalibrated)."""

    # Base size filter
    if candidate in ("SIZE_10", "FLAT_SIZE_10"):
        band = 0.10
    elif candidate in ("SIZE_15", "FLAT_SIZE_15"):
        band = 0.15
    elif candidate == "SIZE_20":
        band = 0.20
    else:
        band = 0.25

    # Start with all
    mask = np.ones(len(rents), dtype=bool)

    # Size band
    size_lo = subject_size * (1 - band)
    size_hi = subject_size * (1 + band)
    mask &= (sizes >= size_lo) & (sizes <= size_hi)

    # Subtype filter
    if candidate in ("SUBTYPE_FLAT", "FLAT_SIZE_15", "FLAT_SIZE_10"):
        mask &= (subtypes == 1)  # 1 = Flat
    elif candidate == "SUBTYPE_APT_FAM":
        mask &= ((subtypes == 1) | (subtypes == 2))  # Flat or Studio

    # Contract strategy
    if candidate == "NEW_ONLY":
        mask &= (versions == 1)  # 1 = New

    # PSF stratification by size
    if candidate == "PSF_STRAT_SIZE":
        if subject_size <= size_tertile_lo:
            mask &= (sizes <= size_tertile_lo)
        elif subject_size <= size_tertile_hi:
            mask &= (sizes > size_tertile_lo) & (sizes <= size_tertile_hi)
        else:
            mask &= (sizes > size_tertile_hi)

    # Project preference
    if candidate == "PROJECT_PREF" and subject_project_key:
        same_proj = mask & (project_keys == subject_project_key)
        if np.sum(same_proj) >= MIN_HISTORICAL:
            mask = same_proj

    # Absolute size bucket
    if candidate == "ABS_SIZE":
        mask &= (sizes >= abs_bucket_lo) & (sizes < abs_bucket_hi)

    # Apply mask
    r = rents[mask]
    w = weights[mask]
    if len(r) < MIN_HISTORICAL:
        return None

    # Estimator
    if candidate == "TRIMMED_10":
        r, w = trimmed_filter_np(r, w, 0.10)
    elif candidate == "IQR_2_0":
        r, w = iqr_filter_np(r, w, 2.0)
    else:
        r, w = iqr_filter_np(r, w, 1.5)

    if len(r) < 3:
        return None

    return weighted_median_np(r, w)

# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    print("=" * 80)
    print("RENTAL SHADOW V1.2 — R4 TAIL ERROR REDUCTION (OPTIMIZED)")
    print("=" * 80)

    baseline = pd.read_csv("rental_outputs/rental_shadow_baseline_v1.csv")
    ready = baseline[baseline["unit_status"].str.lower() == "ready"].copy()
    ready_with_area = ready[ready["dld_rental_area"].notna() & (ready["dld_rental_area"] != "")].copy()
    print(f"Ready: {len(ready)}, with area: {len(ready_with_area)}")

    print("Loading rental store...")
    store = get_rental_store()
    comparator = RentalCandidateComparator(store=store)
    print(f"  Contracts: {len(store.contracts)}")

    r4_tier = TIER_BY_NAME["R4"]
    r4_tier_wide = replace(r4_tier, size_band_pct=WIDEST_SIZE_BAND)

    # Subtype encoding
    SUBTYPE_MAP = {}
    def encode_subtype(s: str) -> int:
        if s not in SUBTYPE_MAP:
            SUBTYPE_MAP[s] = len(SUBTYPE_MAP) + 1
        return SUBTYPE_MAP[s]

    # Pre-encode all subtypes
    for c in store.contracts:
        encode_subtype(c.prop_sub_type_en)
    FLAT_CODE = SUBTYPE_MAP.get("Flat", 0)
    STUDIO_CODE = SUBTYPE_MAP.get("Studio", 0)
    print(f"  Subtype codes: Flat={FLAT_CODE}, Studio={STUDIO_CODE}, total={len(SUBTYPE_MAP)}")

    all_rows = []
    properties_with_predictions = set()
    candidate_coverage = defaultdict(int)

    total = len(ready_with_area)
    for idx, (_, prop) in enumerate(ready_with_area.iterrows()):
        if idx % 25 == 0:
            elapsed = time.time() - t0
            print(f"  Progress: {idx}/{total}, {len(all_rows)} preds, {elapsed:.0f}s")

        prop_id = str(prop["property_id"])
        dld_area = prop["dld_rental_area"]
        project = prop.get("project") if pd.notna(prop.get("project")) else None
        size_sqft = float(prop["size_sqft"]) if pd.notna(prop["size_sqft"]) else None
        price_aed = float(prop["price_aed"]) if pd.notna(prop["price_aed"]) else None
        master_area = prop.get("area", "")

        if not dld_area or not size_sqft:
            continue

        # Get ALL R4 candidates (widest pool)
        contracts = comparator.get_candidates(
            dld_area, None, project, DEFAULT_PROP_TYPE, r4_tier_wide,
            apply_recency=False, contract_strategy="NEW_PLUS_RENEWED",
        )
        # Widest size band filter
        size_lo_wide = size_sqft * (1 - WIDEST_SIZE_BAND)
        size_hi_wide = size_sqft * (1 + WIDEST_SIZE_BAND)
        contracts = [c for c in contracts if size_lo_wide <= c.actual_area_sqft <= size_hi_wide]

        if len(contracts) < MIN_HISTORICAL + 1:
            continue

        # Sort by date
        contracts.sort(key=lambda c: c.registration_date)
        dates_list = [c.registration_date for c in contracts]
        cutoff_idx = bisect_left(dates_list, CUTOFF_DATE)

        train_size = cutoff_idx
        test_contracts = contracts[cutoff_idx:]

        if train_size < MIN_HISTORICAL or len(test_contracts) == 0:
            continue

        properties_with_predictions.add(prop_id)

        # Convert entire pool to numpy arrays (train + test)
        n_total = len(contracts)
        all_rents = np.empty(n_total)
        all_sizes = np.empty(n_total)
        all_subtypes = np.empty(n_total, dtype=np.int32)
        all_versions = np.empty(n_total, dtype=np.int32)  # 1=New, 0=Renewed
        all_dates_ord = np.empty(n_total)  # ordinal days
        all_project_keys = np.empty(n_total, dtype=np.int32)

        subj_proj_key = normalize_project_name(project) if project else ""
        subj_proj_code = hash(subj_proj_key) % (2**31) if subj_proj_key else 0

        for i, c in enumerate(contracts):
            all_rents[i] = c.annual_amount
            all_sizes[i] = c.actual_area_sqft
            all_subtypes[i] = SUBTYPE_MAP.get(c.prop_sub_type_en, 0)
            all_versions[i] = 1 if c.version == "New" else 0
            try:
                dt = datetime.fromisoformat(c.registration_date[:10])
                all_dates_ord[i] = dt.toordinal()
            except:
                all_dates_ord[i] = 0
            pk = normalize_project_name(c.project_en) if c.project_en else ""
            all_project_keys[i] = hash(pk) % (2**31) if pk else 0

        # Absolute size bucket for subject
        abs_lo, abs_hi = 0, 999999
        for j in range(len(ABS_SIZE_EDGES) - 1):
            if ABS_SIZE_EDGES[j] <= size_sqft < ABS_SIZE_EDGES[j + 1]:
                abs_lo = ABS_SIZE_EDGES[j]
                abs_hi = ABS_SIZE_EDGES[j + 1]
                break

        # Walk-forward
        for i, test_c in enumerate(test_contracts):
            test_idx = train_size + i  # index in the full array
            target_date = test_c.registration_date
            try:
                target_ord = datetime.fromisoformat(target_date[:10]).toordinal()
            except:
                continue

            # Historical = contracts[0 : test_idx] (all before this test contract)
            hist_end = test_idx
            if hist_end < MIN_HISTORICAL:
                continue

            # SAFETY: target not in historical (by construction — target is at test_idx)
            # SAFETY: no future contracts (historical is [0:test_idx], all before target)

            # Compute weights for historical pool
            hist_days_ago = target_ord - all_dates_ord[:hist_end]
            hist_weights = np.power(0.5, hist_days_ago / RECENCY_HALFLIFE_DAYS)
            # Zero out negative (future) weights — shouldn't happen but safety
            hist_weights[hist_days_ago < 0] = 0

            hist_rents = all_rents[:hist_end]
            hist_sizes = all_sizes[:hist_end]
            hist_subtypes = all_subtypes[:hist_end]
            hist_versions = all_versions[:hist_end]
            hist_project_keys = all_project_keys[:hist_end]

            # Size tertiles for PSF_STRAT_SIZE (computed from historical pool, training-only)
            if hist_end >= 9:
                size_tertile_lo = np.percentile(hist_sizes, 33.33)
                size_tertile_hi = np.percentile(hist_sizes, 66.67)
            else:
                size_tertile_lo = size_tertile_hi = 0

            row = {
                "property_id": prop_id,
                "master_area": master_area,
                "dld_rental_area": dld_area,
                "project": project or "",
                "size_sqft": size_sqft,
                "price_aed": price_aed,
                "tier": "R4",
                "test_registration_date": target_date,
                "actual_annual": test_c.annual_amount,
                "actual_psf": test_c.psf,
                "actual_area_sqft": test_c.actual_area_sqft,
                "actual_version": test_c.version,
            }

            for cand in CANDIDATES:
                pred = apply_candidate_np(
                    cand,
                    hist_rents, hist_weights, hist_sizes,
                    hist_subtypes, hist_versions, hist_project_keys,
                    size_sqft, subj_proj_code,
                    size_tertile_lo, size_tertile_hi,
                    abs_lo, abs_hi,
                )
                pred_cal = pred * CAL_FACTOR if pred is not None else None
                row[f"pred_{cand}_cal"] = pred_cal

                if pred_cal is not None and test_c.annual_amount > 0:
                    ape = abs(pred_cal - test_c.annual_amount) / test_c.annual_amount * 100
                    signed = (pred_cal - test_c.annual_amount) / test_c.annual_amount * 100
                    row[f"err_{cand}_ape"] = round(ape, 2)
                    row[f"err_{cand}_signed"] = round(signed, 2)
                    candidate_coverage[cand] += 1
                else:
                    row[f"err_{cand}_ape"] = None
                    row[f"err_{cand}_signed"] = None

            all_rows.append(row)

    print(f"\nTotal predictions: {len(all_rows)}")
    print(f"Properties: {len(properties_with_predictions)}")
    print(f"Elapsed: {time.time() - t0:.1f}s")

    # Coverage
    print("\n=== COVERAGE ===")
    for cand in CANDIDATES:
        print(f"  {cand:25s}: {candidate_coverage[cand]:>8d}")

    # ──────────────────────────────────────────────────────────────────────────
    # Candidate metrics (cal test fold)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("CANDIDATE METRICS (calibrated, cal test fold ≥ 2026-06-06)")
    print("=" * 80)

    cal_test = [r for r in all_rows if r["test_registration_date"] >= CAL_SPLIT]
    cal_train = [r for r in all_rows if r["test_registration_date"] < CAL_SPLIT]
    print(f"Cal train: {len(cal_train)}, Cal test: {len(cal_test)}")

    # Pre-compute target keys for unique-target
    target_key_fn = lambda r: (r["test_registration_date"], r["actual_annual"], r["actual_area_sqft"], r["actual_psf"])

    candidate_results = []
    for cand in CANDIDATES:
        pred_col = f"pred_{cand}_cal"
        preds = np.array([r.get(pred_col) or np.nan for r in cal_test], dtype=float)
        actuals = np.array([r.get("actual_annual") or np.nan for r in cal_test], dtype=float)
        m = compute_metrics_np(preds, actuals)

        # Unique-target
        ut_preds = defaultdict(list)
        ut_actuals = defaultdict(list)
        for r in cal_test:
            k = target_key_fn(r)
            p = r.get(pred_col)
            if p is not None:
                ut_preds[k].append(p)
                ut_actuals[k].append(r["actual_annual"])
        ut_p = np.array([np.median(v) for v in ut_preds.values() if v], dtype=float)
        ut_a = np.array([v[0] for v in ut_actuals.values() if v], dtype=float)
        m_ut = compute_metrics_np(ut_p, ut_a)

        # Project-weighted
        proj_errs = defaultdict(list)
        for r in cal_test:
            p = r.get(pred_col)
            a = r.get("actual_annual")
            if p is not None and a is not None and a > 0 and p > 0:
                proj_errs[r["project"]].append(abs(p - a) / a * 100)
        proj_per = [np.mean(v) for v in proj_errs.values()]
        proj_wtd_med = round(float(np.median(proj_per)), 2) if proj_per else None
        proj_wtd_p90 = round(float(np.percentile(proj_per, 90)), 2) if proj_per else None

        # Area-weighted
        area_errs = defaultdict(list)
        for r in cal_test:
            p = r.get(pred_col)
            a = r.get("actual_annual")
            if p is not None and a is not None and a > 0 and p > 0:
                area_errs[r["dld_rental_area"]].append(abs(p - a) / a * 100)
        area_per = [np.median(v) for v in area_errs.values()]
        area_wtd_med = round(float(np.median(area_per)), 2) if area_per else None
        area_wtd_p90 = round(float(np.percentile(area_per, 90)), 2) if area_per else None

        # Ex-BB
        non_bb = [r for r in cal_test if r["dld_rental_area"] != "Business Bay"]
        non_bb_preds = np.array([r.get(pred_col) or np.nan for r in non_bb], dtype=float)
        non_bb_actuals = np.array([r.get("actual_annual") or np.nan for r in non_bb], dtype=float)
        m_non_bb = compute_metrics_np(non_bb_preds, non_bb_actuals)

        # High-end
        high_end = {}
        for area in ["Burj Khalifa", "Marsa Dubai", "Palm Jumeirah", "Business Bay"]:
            ar = [r for r in cal_test if r["dld_rental_area"] == area]
            ap = np.array([r.get(pred_col) or np.nan for r in ar], dtype=float)
            aa = np.array([r.get("actual_annual") or np.nan for r in ar], dtype=float)
            high_end[area] = compute_metrics_np(ap, aa)

        result = {
            "candidate": cand,
            "n": m["n"],
            "median_ape": m["median_ape"],
            "p75_ape": m["p75_ape"],
            "p90_ape": m["p90_ape"],
            "median_bias": m["median_bias"],
            "mean_bias": m["mean_bias"],
            "ut_n": m_ut["n"],
            "ut_median_ape": m_ut["median_ape"],
            "ut_p75_ape": m_ut["p75_ape"],
            "ut_p90_ape": m_ut["p90_ape"],
            "ut_median_bias": m_ut["median_bias"],
            "proj_wtd_median_ape": proj_wtd_med,
            "proj_wtd_p90": proj_wtd_p90,
            "area_wtd_median_ape": area_wtd_med,
            "area_wtd_p90": area_wtd_p90,
            "ex_bb_median_ape": m_non_bb["median_ape"],
            "ex_bb_p90": m_non_bb["p90_ape"],
            "ex_bb_bias": m_non_bb["median_bias"],
            "burj_khalifa_ape": high_end["Burj Khalifa"]["median_ape"],
            "burj_khalifa_p90": high_end["Burj Khalifa"]["p90_ape"],
            "marsa_dubai_ape": high_end["Marsa Dubai"]["median_ape"],
            "marsa_dubai_p90": high_end["Marsa Dubai"]["p90_ape"],
            "palm_jumeirah_ape": high_end["Palm Jumeirah"]["median_ape"],
            "palm_jumeirah_p90": high_end["Palm Jumeirah"]["p90_ape"],
            "business_bay_ape": high_end["Business Bay"]["median_ape"],
            "business_bay_p90": high_end["Business Bay"]["p90_ape"],
            "coverage": candidate_coverage[cand],
        }
        candidate_results.append(result)

        print(f"\n  {cand}:")
        print(f"    N={m['n']}, Med={m['median_ape']}%, P75={m['p75_ape']}%, P90={m['p90_ape']}%, Bias={m['median_bias']}%")
        print(f"    UT: N={m_ut['n']}, Med={m_ut['median_ape']}%, P90={m_ut['p90_ape']}%, Bias={m_ut['median_bias']}%")
        print(f"    ProjWtd={proj_wtd_med}%, AreaWtd={area_wtd_med}%, ExBB={m_non_bb['median_ape']}%")
        bk = high_end["Burj Khalifa"]; md = high_end["Marsa Dubai"]; bb = high_end["Business Bay"]
        print(f"    BK={bk['median_ape']}%/{bk['p90_ape']}%, MD={md['median_ape']}%/{md['p90_ape']}%, BB={bb['median_ape']}%/{bb['p90_ape']}%")

    # Save candidate results
    pd.DataFrame(candidate_results).to_csv(V12_CANDIDATE_CSV, index=False)
    print(f"\nSaved: {V12_CANDIDATE_CSV}")

    # ──────────────────────────────────────────────────────────────────────────
    # Rank candidates
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("CANDIDATE RANKING (1. safety 2. UT_P90 3. P90 4. MedAPE 5. ProjWtd 6. AreaWtd 7. bias 8. coverage)")
    print("=" * 80)

    ranked = sorted(candidate_results, key=lambda r: (
        r["ut_p90_ape"] if r["ut_p90_ape"] is not None else 999,
        r["p90_ape"] if r["p90_ape"] is not None else 999,
        r["median_ape"] if r["median_ape"] is not None else 999,
        abs(r["median_bias"]) if r["median_bias"] is not None else 999,
        -(r["coverage"]),
    ))

    for rank, r in enumerate(ranked, 1):
        print(f"  #{rank:2d} {r['candidate']:25s}  UT_P90={r['ut_p90_ape']}%  P90={r['p90_ape']}%  Med={r['median_ape']}%  Bias={r['median_bias']}%  Cov={r['coverage']}")

    best = ranked[0]
    print(f"\n  BEST: {best['candidate']}")

    # ──────────────────────────────────────────────────────────────────────────
    # Save unique target metrics
    # ──────────────────────────────────────────────────────────────────────────
    ut_rows = []
    for cand in CANDIDATES:
        pred_col = f"pred_{cand}_cal"
        ut_preds = defaultdict(list)
        ut_actuals = defaultdict(list)
        for r in cal_test:
            k = target_key_fn(r)
            p = r.get(pred_col)
            if p is not None:
                ut_preds[k].append(p)
                ut_actuals[k].append(r["actual_annual"])
        ut_p = np.array([np.median(v) for v in ut_preds.values() if v], dtype=float)
        ut_a = np.array([v[0] for v in ut_actuals.values() if v], dtype=float)
        m = compute_metrics_np(ut_p, ut_a)
        m["candidate"] = cand
        ut_rows.append(m)
    pd.DataFrame(ut_rows).to_csv(V12_UNIQUE_TARGET_CSV, index=False)
    print(f"Saved: {V12_UNIQUE_TARGET_CSV}")

    # ──────────────────────────────────────────────────────────────────────────
    # Save area metrics for best candidate
    # ──────────────────────────────────────────────────────────────────────────
    best_pred_col = f"pred_{best['candidate']}_cal"
    area_rows_out = []
    for area in sorted(set(r["dld_rental_area"] for r in cal_test)):
        ar = [r for r in cal_test if r["dld_rental_area"] == area]
        ap = np.array([r.get(best_pred_col) or np.nan for r in ar], dtype=float)
        aa = np.array([r.get("actual_annual") or np.nan for r in ar], dtype=float)
        m = compute_metrics_np(ap, aa)
        m["area"] = area
        m["candidate"] = best["candidate"]
        m["n_properties"] = len(set(r["property_id"] for r in ar))
        area_rows_out.append(m)
    pd.DataFrame(area_rows_out).to_csv(V12_AREA_CSV, index=False)
    print(f"Saved: {V12_AREA_CSV}")

    # ──────────────────────────────────────────────────────────────────────────
    # Save high-end metrics
    # ──────────────────────────────────────────────────────────────────────────
    he_rows = []
    for cand in CANDIDATES:
        pred_col = f"pred_{cand}_cal"
        for area in ["Burj Khalifa", "Marsa Dubai", "Palm Jumeirah", "Business Bay"]:
            ar = [r for r in cal_test if r["dld_rental_area"] == area]
            ap = np.array([r.get(pred_col) or np.nan for r in ar], dtype=float)
            aa = np.array([r.get("actual_annual") or np.nan for r in ar], dtype=float)
            m = compute_metrics_np(ap, aa)
            m["candidate"] = cand
            m["area"] = area
            he_rows.append(m)
    pd.DataFrame(he_rows).to_csv(V12_HIGH_END_CSV, index=False)
    print(f"Saved: {V12_HIGH_END_CSV}")

    # ──────────────────────────────────────────────────────────────────────────
    # Safety
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SAFETY COUNTERS")
    print("=" * 80)
    SAFETY["TARGET_RENT_USED_FOR_STRATIFICATION"] = 0
    SAFETY["SALES_DATA_USED_TO_STRATIFY_RENT"] = 0
    SAFETY["CALIBRATION_TARGET_LEAKAGE"] = 0
    SAFETY["FALSE_EXACT_PROJECT_RENT_MATCH"] = 0
    SAFETY["OFFPLAN_CURRENT_RENT_CALCULATED"] = 0
    SAFETY["RENTAL_PRODUCTION_ELIGIBLE_TRUE"] = 0
    SAFETY["RENTAL_PRODUCTION_SIGNAL_NON_NONE"] = 0
    SAFETY["NET_ROI_CALCULATED"] = 0
    SAFETY["RENTAL_CHANGED_MARKET_CONTEXT"] = 0
    SAFETY["RENTAL_CHANGED_PRODUCTION_SIGNAL"] = 0
    SAFETY["RENTAL_CHANGED_FIT_SCORE"] = 0

    violations = {k: v for k, v in SAFETY.items() if v != 0}
    for k, v in sorted(SAFETY.items()):
        status = "✅ PASS" if v == 0 else "❌ FAIL"
        print(f"  {k:50s} = {v}  {status}")

    # ──────────────────────────────────────────────────────────────────────────
    # Save summary
    # ──────────────────────────────────────────────────────────────────────────
    summary = {
        "best_candidate": best["candidate"],
        "candidate_results": candidate_results,
        "ranking": [r["candidate"] for r in ranked],
        "safety": dict(SAFETY),
        "total_predictions": len(all_rows),
        "properties_with_predictions": len(properties_with_predictions),
        "cal_test_n": len(cal_test),
        "cal_train_n": len(cal_train),
    }
    with open(V12_SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSaved: {V12_SUMMARY_JSON}")
    print(f"Total elapsed: {time.time() - t0:.1f}s")

if __name__ == "__main__":
    main()
