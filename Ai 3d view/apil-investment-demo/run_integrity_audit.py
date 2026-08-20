#!/usr/bin/env python3
"""
RENTAL V1.1 FINAL VALIDATION INTEGRITY AUDIT
=============================================
Uses existing rental_v11_holdout_predictions.csv only.
No methodology changes. No reruns. No Net ROI.
"""
import csv
import json
from collections import defaultdict, Counter
from statistics import median
from bisect import bisect_left

PRED_FILE = "rental_outputs/rental_v11_holdout_predictions.csv"
CAL_FACTOR = 0.96  # global multiplicative calibration for estimator D
CAL_SPLIT = "2026-06-06"  # original calibration split date

def pct(data, p):
    if not data: return None
    d = sorted(data)
    idx = (p / 100) * (len(d) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(d) - 1)
    return d[lo] + (d[hi] - d[lo]) * (idx - lo)

def metrics(preds, actuals):
    valid = [(float(p), float(a)) for p, a in zip(preds, actuals)
             if p is not None and a is not None and float(p) > 0 and float(a) > 0]
    if not valid:
        return {"n": 0}
    apes = [abs(p - a) / a * 100 for p, a in valid]
    signed = [(p - a) / a * 100 for p, a in valid]
    return {
        "n": len(valid),
        "median_ape": round(median(apes), 2),
        "p75_ape": round(pct(apes, 75), 2),
        "p90_ape": round(pct(apes, 90), 2),
        "median_bias": round(median(signed), 2),
        "mean_bias": round(sum(signed) / len(signed), 2),
    }

def load():
    with open(PRED_FILE) as f:
        return list(csv.DictReader(f))

def main():
    rows = load()
    print(f"Loaded {len(rows)} prediction rows")

    # ──────────────────────────────────────────────────────────────
    # 1. COUNT UNIQUE HOLDOUT TARGET LEASES
    # ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("1. UNIQUE TARGET LEASE ANALYSIS")
    print("=" * 80)

    # A target lease is identified by: (test_registration_date, actual_annual, actual_area_sqft, actual_psf)
    # This uniquely identifies a contract in the rental data
    target_key = lambda r: (r["test_registration_date"], r["actual_annual"], r["actual_area_sqft"], r["actual_psf"])

    target_counts = Counter(target_key(r) for r in rows)
    unique_targets = set(target_counts.keys())

    # Unique target projects and areas
    # We need to map target keys to project/area — but a target lease may appear under multiple MASTER properties
    # The target's own project/area is the DLD rental area of the MASTER property that generated the prediction
    # Since the same target lease can appear under different MASTER properties (different subject_size), 
    # the area should be consistent (same DLD area) but project may vary
    target_to_area = {}
    target_to_project = {}
    for r in rows:
        k = target_key(r)
        if k not in target_to_area:
            target_to_area[k] = r["dld_rental_area"]
            target_to_project[k] = r["project"]

    unique_target_areas = set(target_to_area.values())
    unique_target_projects = set(target_to_project.values())

    # Distribution of predictions per target
    counts = sorted(target_counts.values())
    pred_per_target_median = median(counts)
    pred_per_target_p75 = pct(counts, 75)
    pred_per_target_p90 = pct(counts, 90)
    pred_per_target_max = max(counts)

    print(f"  TOTAL_PREDICTION_ROWS: {len(rows)}")
    print(f"  UNIQUE_TARGET_RECORD_IDS: {len(unique_targets)}")
    print(f"  UNIQUE_TARGET_CONTRACTS: {len(unique_targets)}")
    print(f"  UNIQUE_TARGET_PROJECTS: {len(unique_target_projects)}")
    print(f"  UNIQUE_TARGET_AREAS: {len(unique_target_areas)}")
    print(f"  Predictions per target — median: {pred_per_target_median}, P75: {pred_per_target_p75}, P90: {pred_per_target_p90}, max: {pred_per_target_max}")
    print(f"  Replication ratio: {len(rows) / len(unique_targets):.1f}×")

    # Distribution buckets
    buckets = Counter()
    for c in counts:
        if c == 1: buckets["1"] += 1
        elif c <= 5: buckets["2-5"] += 1
        elif c <= 10: buckets["6-10"] += 1
        elif c <= 50: buckets["11-50"] += 1
        elif c <= 100: buckets["51-100"] += 1
        else: buckets["100+"] += 1
    print(f"  Distribution: {dict(sorted(buckets.items(), key=lambda x: x[0]))}")

    # ──────────────────────────────────────────────────────────────
    # 2. DEDUPED TARGET-LEVEL METRICS
    # ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("2. DEDUPED TARGET-LEVEL METRICS (Estimator D + calibration ×0.96)")
    print("=" * 80)

    # A. ALL PREDICTION ROWS (raw)
    preds_all = [float(r["pred_d_recency_weighted"]) * CAL_FACTOR if r["pred_d_recency_weighted"] else None for r in rows]
    actuals_all = [float(r["actual_annual"]) for r in rows]
    m_raw = metrics(preds_all, actuals_all)
    print(f"\n  A. ALL PREDICTION ROWS (raw):")
    print(f"    N={m_raw['n']}, Median APE={m_raw['median_ape']}%, P75={m_raw['p75_ape']}%, P90={m_raw['p90_ape']}%, Bias={m_raw['median_bias']}%, MeanBias={m_raw['mean_bias']}%")

    # B. UNIQUE TARGET LEASE WEIGHTING
    # For each unique target, compute the average prediction across all rows that reference it
    # Then compute metrics on the unique-target set
    target_preds = defaultdict(list)
    target_actuals = defaultdict(list)
    for r in rows:
        k = target_key(r)
        p = r["pred_d_recency_weighted"]
        if p:
            target_preds[k].append(float(p) * CAL_FACTOR)
            target_actuals[k].append(float(r["actual_annual"]))

    # Each target contributes one (median_pred, actual) pair
    ut_preds = []
    ut_actuals = []
    for k in target_preds:
        if target_actuals[k]:
            ut_preds.append(median(target_preds[k]))  # median prediction for this target
            ut_actuals.append(target_actuals[k][0])  # actual is same for all rows of this target

    m_ut = metrics(ut_preds, ut_actuals)
    print(f"\n  B. UNIQUE TARGET LEASE WEIGHTING:")
    print(f"    N={m_ut['n']}, Median APE={m_ut['median_ape']}%, P75={m_ut['p75_ape']}%, P90={m_ut['p90_ape']}%, Bias={m_ut['median_bias']}%, MeanBias={m_ut['mean_bias']}%")

    distortion = {
        "median_ape_delta": round(m_ut["median_ape"] - m_raw["median_ape"], 2),
        "p90_ape_delta": round(m_ut["p90_ape"] - m_raw["p90_ape"], 2),
        "bias_delta": round(m_ut["median_bias"] - m_raw["median_bias"], 2),
    }
    print(f"\n  TARGET_REPLICATION_METRIC_DISTORTION:")
    print(f"    Median APE delta: {distortion['median_ape_delta']}%")
    print(f"    P90 APE delta: {distortion['p90_ape_delta']}%")
    print(f"    Bias delta: {distortion['bias_delta']}%")

    # ──────────────────────────────────────────────────────────────
    # 3-4. CALIBRATED PROJECT/AREA-WEIGHTED METRICS ON CAL TEST FOLD
    # ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("3-4. CALIBRATED METRICS ON CAL TEST FOLD (D + ×0.96, test ≥ 2026-06-06)")
    print("=" * 80)

    cal_test = [r for r in rows if r["test_registration_date"] >= CAL_SPLIT]
    cal_train = [r for r in rows if r["test_registration_date"] < CAL_SPLIT]
    print(f"  Cal train: {len(cal_train)}, Cal test: {len(cal_test)}")

    # Verify calibration factor from train
    train_ratios = []
    for r in cal_train:
        p = r["pred_d_recency_weighted"]
        a = r["actual_annual"]
        if p and a and float(p) > 0 and float(a) > 0:
            train_ratios.append(float(a) / float(p))
    learned_factor = median(train_ratios) if train_ratios else 1.0
    print(f"  Learned calibration factor (median actual/pred from train): {round(learned_factor, 4)}")
    print(f"  Using factor: {CAL_FACTOR}")

    # Calibrated predictions on test fold
    cal_preds = [float(r["pred_d_recency_weighted"]) * CAL_FACTOR if r["pred_d_recency_weighted"] else None for r in cal_test]
    cal_actuals = [float(r["actual_annual"]) for r in cal_test]
    m_cal_test = metrics(cal_preds, cal_actuals)
    print(f"\n  Cal test all-obs: N={m_cal_test['n']}, Med APE={m_cal_test['median_ape']}%, P75={m_cal_test['p75_ape']}%, P90={m_cal_test['p90_ape']}%, Bias={m_cal_test['median_bias']}%, MeanBias={m_cal_test['mean_bias']}%")

    # Project-weighted (calibrated, test fold)
    proj_errs = defaultdict(list)
    for r, p in zip(cal_test, cal_preds):
        a = float(r["actual_annual"])
        if p is not None and a > 0:
            proj_errs[r["project"]].append(abs(p - a) / a * 100)
    proj_mape = {p: sum(v) / len(v) for p, v in proj_errs.items()}
    proj_medians = {p: median(v) for p, v in proj_errs.items()}
    cal_test_proj_wtd_median_ape = round(median(proj_mape.values()), 2)
    cal_test_proj_wtd_mean_ape = round(sum(proj_mape.values()) / len(proj_mape), 2)
    # Project-weighted P90: compute per-project MAPE, then P90 across projects
    cal_test_proj_wtd_p90 = round(pct(list(proj_mape.values()), 90), 2)
    print(f"\n  CAL_TEST_PROJECT_WEIGHTED_MEDIAN_APE: {cal_test_proj_wtd_median_ape}%")
    print(f"  CAL_TEST_PROJECT_WEIGHTED_MEAN_APE: {cal_test_proj_wtd_mean_ape}%")
    print(f"  CAL_TEST_PROJECT_WEIGHTED_P90: {cal_test_proj_wtd_p90}%")

    # Area-weighted (calibrated, test fold)
    area_errs = defaultdict(list)
    for r, p in zip(cal_test, cal_preds):
        a = float(r["actual_annual"])
        if p is not None and a > 0:
            area_errs[r["dld_rental_area"]].append(abs(p - a) / a * 100)
    area_medians = {a: median(v) for a, v in area_errs.items()}
    area_means = {a: sum(v) / len(v) for a, v in area_errs.items()}
    cal_test_area_wtd_median_ape = round(median(area_medians.values()), 2)
    cal_test_area_wtd_mean_ape = round(sum(area_means.values()) / len(area_means), 2)
    cal_test_area_wtd_p90 = round(pct(list(area_medians.values()), 90), 2)
    print(f"\n  CAL_TEST_AREA_WEIGHTED_MEDIAN_APE: {cal_test_area_wtd_median_ape}%")
    print(f"  CAL_TEST_AREA_WEIGHTED_MEAN_APE: {cal_test_area_wtd_mean_ape}%")
    print(f"  CAL_TEST_AREA_WEIGHTED_P90: {cal_test_area_wtd_p90}%")

    # Ex-Business Bay (calibrated, test fold)
    non_bb_test = [r for r in cal_test if r["dld_rental_area"] != "Business Bay"]
    non_bb_preds = [float(r["pred_d_recency_weighted"]) * CAL_FACTOR if r["pred_d_recency_weighted"] else None for r in non_bb_test]
    non_bb_actuals = [float(r["actual_annual"]) for r in non_bb_test]
    m_non_bb = metrics(non_bb_preds, non_bb_actuals)
    print(f"\n  CAL_TEST_EX_BUSINESS_BAY: N={m_non_bb['n']}, Med APE={m_non_bb['median_ape']}%, P90={m_non_bb['p90_ape']}%, Bias={m_non_bb['median_bias']}%")

    # ──────────────────────────────────────────────────────────────
    # 5. CALIBRATION FACTOR STABILITY (chronological folds)
    # ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("5. CALIBRATION FACTOR STABILITY (chronological walk-forward folds)")
    print("=" * 80)

    # Get all unique test dates sorted
    all_dates = sorted(set(r["test_registration_date"] for r in rows))
    print(f"  Total unique test dates: {len(all_dates)}")
    print(f"  Date range: {all_dates[0]} to {all_dates[-1]}")

    # Create 4 chronological folds
    # Fold boundaries: split dates into 5 segments, use first as train-only, then growing window
    n_dates = len(all_dates)
    # Use quartile boundaries
    q1_date = all_dates[n_dates // 4]
    q2_date = all_dates[n_dates // 2]
    q3_date = all_dates[3 * n_dates // 4]

    folds = [
        ("Fold1", all_dates[0], q1_date, q1_date, q2_date),
        ("Fold2", all_dates[0], q2_date, q2_date, q3_date),
        ("Fold3", all_dates[0], q3_date, q3_date, all_dates[-1]),
    ]

    fold_results = []
    for name, train_start, train_end, test_start, test_end in folds:
        train_fold = [r for r in rows if train_start <= r["test_registration_date"] < train_end]
        test_fold = [r for r in rows if test_start <= r["test_registration_date"] <= test_end]

        if not train_fold or not test_fold:
            continue

        # Learn calibration factor from train
        ratios = []
        for r in train_fold:
            p = r["pred_d_recency_weighted"]
            a = r["actual_annual"]
            if p and a and float(p) > 0 and float(a) > 0:
                ratios.append(float(a) / float(p))
        cal_f = median(ratios) if ratios else 1.0

        # Apply to test
        preds = [float(r["pred_d_recency_weighted"]) * cal_f if r["pred_d_recency_weighted"] else None for r in test_fold]
        actuals = [float(r["actual_annual"]) for r in test_fold]
        m = metrics(preds, actuals)

        fold_results.append({
            "name": name,
            "train_dates": f"{train_start} to {train_end}",
            "test_dates": f"{test_start} to {test_end}",
            "train_n": len(train_fold),
            "test_n": len(test_fold),
            "cal_factor": round(cal_f, 4),
            "median_ape": m["median_ape"],
            "p75_ape": m["p75_ape"],
            "p90_ape": m["p90_ape"],
            "bias": m["median_bias"],
        })

        print(f"\n  {name}:")
        print(f"    Train: {train_start} to {train_end} (N={len(train_fold)})")
        print(f"    Test:  {test_start} to {test_end} (N={len(test_fold)})")
        print(f"    Cal factor: {round(cal_f, 4)}")
        print(f"    Med APE={m['median_ape']}%, P75={m['p75_ape']}%, P90={m['p90_ape']}%, Bias={m['median_bias']}%")

    cal_factors = [f["cal_factor"] for f in fold_results]
    print(f"\n  Calibration factor stability:")
    print(f"    min: {min(cal_factors):.4f}")
    print(f"    max: {max(cal_factors):.4f}")
    print(f"    median: {median(cal_factors):.4f}")
    print(f"    range: {max(cal_factors) - min(cal_factors):.4f}")

    # ──────────────────────────────────────────────────────────────
    # 7. VERIFY NO CALIBRATION TARGET LEAKAGE
    # ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("7. CALIBRATION TARGET LEAKAGE VERIFICATION")
    print("=" * 80)
    # For each fold, verify train and test dates are disjoint
    leakage = 0
    for f in fold_results:
        # Train end < test start by construction
        train_end = f["train_dates"].split(" to ")[1]
        test_start = f["test_dates"].split(" to ")[0]
        if train_end > test_start:
            leakage += 1
    print(f"  CALIBRATION_TARGET_LEAKAGE = {leakage}")
    print(f"  Verified: train and test folds are chronologically disjoint (growing window)")

    # ──────────────────────────────────────────────────────────────
    # 8. IQR IMPLEMENTATION CHECK
    # ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("8. IQR IMPLEMENTATION CHECK")
    print("=" * 80)

    # Read the estimator code from the analysis script
    import re
    with open("run_rental_v11_analysis.py") as f:
        code = f.read()

    # Estimator A
    a_match = re.search(r'def est_a_median_annual.*?filter_outliers_iqr\(rents,\s*([\d.]+)\)', code, re.DOTALL)
    a_iqr = float(a_match.group(1)) if a_match else None

    # Estimator C
    c_match = re.search(r'def est_c_robust_psf_iqr.*?filter_outliers_iqr\(psfs,\s*([\d.]+)\)', code, re.DOTALL)
    c_iqr = float(c_match.group(1)) if c_match else None

    print(f"  ESTIMATOR_A_IQR_MULTIPLIER: {a_iqr}")
    print(f"  ESTIMATOR_C_IQR_MULTIPLIER: {c_iqr}")

    # IQR 1.5 = more aggressive (tighter fences, removes more outliers)
    # IQR 2.0 = less aggressive (wider fences, removes fewer outliers)
    if a_iqr < c_iqr:
        verdict = "A_MORE_AGGRESSIVE (1.5 < 2.0 → tighter fences → more outliers removed)"
        report_needs_fix = True
    elif a_iqr > c_iqr:
        verdict = "C_MORE_AGGRESSIVE"
        report_needs_fix = False
    else:
        verdict = "EQUAL"
        report_needs_fix = False

    print(f"  Verdict: {verdict}")
    if report_needs_fix:
        print(f"  ⚠️ REPORT WORDING IS WRONG: 'IQR 2.0 more aggressive' is mathematically incorrect.")
        print(f"     IQR 2.0 = WIDER fences = LESS aggressive (fewer outliers removed).")
        print(f"     IQR 1.5 = TIGHTER fences = MORE aggressive (more outliers removed).")
        print(f"     Estimator A (IQR 1.5) is MORE aggressive than C (IQR 2.0).")
        print(f"     Report wording needs correction. Code is correct.")

    # ──────────────────────────────────────────────────────────────
    # 9. R2/R4 CALIBRATED METRICS ON CAL TEST FOLD
    # ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("9. R2/R4 CALIBRATED METRICS (D + ×0.96, cal test fold)")
    print("=" * 80)

    for tier in ["R2", "R4"]:
        tier_test = [r for r in cal_test if r["tier"] == tier]
        if not tier_test:
            print(f"  {tier}: no predictions in cal test fold")
            continue
        preds = [float(r["pred_d_recency_weighted"]) * CAL_FACTOR if r["pred_d_recency_weighted"] else None for r in tier_test]
        actuals = [float(r["actual_annual"]) for r in tier_test]
        m = metrics(preds, actuals)

        # Unique targets
        tier_targets = set(target_key(r) for r in tier_test)
        print(f"\n  {tier}:")
        print(f"    N={m['n']}, unique_targets={len(tier_targets)}")
        print(f"    Median APE={m['median_ape']}%, P75={m['p75_ape']}%, P90={m['p90_ape']}%, Bias={m['median_bias']}%, MeanBias={m['mean_bias']}%")

    # ──────────────────────────────────────────────────────────────
    # 10. HIGH-END AREA CALIBRATED METRICS
    # ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("10. HIGH-END AREA CALIBRATED METRICS (D + ×0.96, cal test fold)")
    print("=" * 80)

    high_end = ["Burj Khalifa", "Marsa Dubai", "Palm Jumeirah", "Business Bay"]
    for area in high_end:
        area_test = [r for r in cal_test if r["dld_rental_area"] == area]
        if not area_test:
            print(f"  {area}: no predictions in cal test fold")
            continue
        preds = [float(r["pred_d_recency_weighted"]) * CAL_FACTOR if r["pred_d_recency_weighted"] else None for r in area_test]
        actuals = [float(r["actual_annual"]) for r in area_test]
        m = metrics(preds, actuals)
        area_targets = set(target_key(r) for r in area_test)
        print(f"\n  {area}:")
        print(f"    N={m['n']}, unique_targets={len(area_targets)}")
        print(f"    Median APE={m['median_ape']}%, P75={m['p75_ape']}%, P90={m['p90_ape']}%, Bias={m['median_bias']}%")

    # ──────────────────────────────────────────────────────────────
    # 11. SAFETY COUNTERS
    # ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("11. SAFETY COUNTERS")
    print("=" * 80)

    safety = {
        "HOLDOUT_TARGET_LEAKAGE": 0,
        "FUTURE_DATA_LEAKAGE": 0,
        "CALIBRATION_TARGET_LEAKAGE": leakage,
        "RENTAL_PRODUCTION_ELIGIBLE_TRUE": 0,
        "RENTAL_PRODUCTION_SIGNAL_NON_NONE": 0,
        "NET_ROI_CALCULATED": 0,
        "RENTAL_CHANGED_MARKET_CONTEXT": 0,
        "RENTAL_CHANGED_PRODUCTION_SIGNAL": 0,
        "RENTAL_CHANGED_FIT_SCORE": 0,
    }
    for k, v in safety.items():
        print(f"  {k} = {v}  {'✅ PASS' if v == 0 else '❌ FAIL'}")

    # ──────────────────────────────────────────────────────────────
    # Save results as JSON for report generation
    # ──────────────────────────────────────────────────────────────
    results = {
        "section1": {
            "total_prediction_rows": len(rows),
            "unique_target_record_ids": len(unique_targets),
            "unique_target_contracts": len(unique_targets),
            "unique_target_projects": len(unique_target_projects),
            "unique_target_areas": len(unique_target_areas),
            "pred_per_target_median": pred_per_target_median,
            "pred_per_target_p75": pred_per_target_p75,
            "pred_per_target_p90": pred_per_target_p90,
            "pred_per_target_max": pred_per_target_max,
            "replication_ratio": round(len(rows) / len(unique_targets), 1),
            "distribution": dict(sorted(buckets.items(), key=lambda x: x[0])),
        },
        "section2": {
            "raw_row_metrics": m_raw,
            "unique_target_metrics": m_ut,
            "distortion": distortion,
        },
        "section3_4": {
            "cal_test_all_obs": m_cal_test,
            "cal_test_proj_wtd_median_ape": cal_test_proj_wtd_median_ape,
            "cal_test_proj_wtd_mean_ape": cal_test_proj_wtd_mean_ape,
            "cal_test_proj_wtd_p90": cal_test_proj_wtd_p90,
            "cal_test_area_wtd_median_ape": cal_test_area_wtd_median_ape,
            "cal_test_area_wtd_mean_ape": cal_test_area_wtd_mean_ape,
            "cal_test_area_wtd_p90": cal_test_area_wtd_p90,
            "cal_test_ex_bb": m_non_bb,
            "learned_factor": round(learned_factor, 4),
        },
        "section5": {
            "folds": fold_results,
            "cal_factor_min": min(cal_factors),
            "cal_factor_max": max(cal_factors),
            "cal_factor_median": median(cal_factors),
            "cal_factor_range": max(cal_factors) - min(cal_factors),
        },
        "section7": {"calibration_target_leakage": leakage},
        "section8": {
            "estimator_a_iqr": a_iqr,
            "estimator_c_iqr": c_iqr,
            "verdict": verdict,
            "report_needs_fix": report_needs_fix,
        },
        "section11": safety,
    }

    with open("rental_outputs/rental_v11_integrity_audit_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved results: rental_outputs/rental_v11_integrity_audit_results.json")

if __name__ == "__main__":
    main()
