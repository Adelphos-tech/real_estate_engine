# RENTAL SHADOW ENGINE V1.2 — R4 TAIL ERROR REDUCTION RESEARCH

**Date**: 2026-08-20
**Status**: SHADOW_RESEARCH ONLY (not production)
**Version**: RENTAL_SHADOW_V1_2_RESEARCH
**Predecessor**: RENTAL_SHADOW_V1_1 (integrity verified)
**Goal**: Reduce R4 tail error (P90) without area-specific overfitting

---

## 1. EXECUTIVE SUMMARY

**VERDICT: RENTAL_SHADOW_V1_2_NO_MEANINGFUL_IMPROVEMENT**

14 candidate configurations were tested against the V1.1 baseline (Estimator D + global calibration ×0.96) using the same true walk-forward holdout design. None of the candidates met the universal acceptance requirement. The R4 P90 of ~38-39% is a **structural floor** for area-level comparable analysis in Dubai's heterogeneous rental market.

The V1.1 baseline remains the best configuration. No methodology change is recommended.

---

## 2. RESEARCH METHODOLOGY

### 2.1 Approach
- Used the existing true walk-forward holdout design (growing window, zero leakage)
- Ran ONE walk-forward pass per property (R4, widest pool ±25%)
- Tested 14 candidate configurations post-hoc on the in-memory historical pool
- Applied the verified V1.1 global calibration (×0.96) to all candidates
- Evaluated on the calibration test fold (test ≥ 2026-06-06, N=169,068)

### 2.2 Candidates Tested

| # | Candidate | Description |
|---|-----------|-------------|
| 1 | V1.1_BASELINE | ±25% size, all subtypes, NEW_PLUS_RENEWED, recency-wtd median IQR 1.5 |
| 2 | SUBTYPE_FLAT | ±25% size, Flat only, NEW_PLUS_RENEWED, recency-wtd median IQR 1.5 |
| 3 | SUBTYPE_APT_FAM | ±25% size, Flat+Studio, NEW_PLUS_RENEWED, recency-wtd median IQR 1.5 |
| 4 | SIZE_15 | ±15% size, all subtypes, NEW_PLUS_RENEWED, recency-wtd median IQR 1.5 |
| 5 | SIZE_10 | ±10% size, all subtypes, NEW_PLUS_RENEWED, recency-wtd median IQR 1.5 |
| 6 | SIZE_20 | ±20% size, all subtypes, NEW_PLUS_RENEWED, recency-wtd median IQR 1.5 |
| 7 | NEW_ONLY | ±25% size, all subtypes, NEW_ONLY, recency-wtd median IQR 1.5 |
| 8 | TRIMMED_10 | ±25% size, all subtypes, NEW_PLUS_RENEWED, recency-wtd trimmed median (10%) |
| 9 | IQR_2_0 | ±25% size, all subtypes, NEW_PLUS_RENEWED, recency-wtd median IQR 2.0 |
| 10 | PSF_STRAT_SIZE | ±25% size, all subtypes, size-tertile stratification, recency-wtd median IQR 1.5 |
| 11 | PROJECT_PREF | ±25% size, prefer same project when ≥5, recency-wtd median IQR 1.5 |
| 12 | ABS_SIZE | Absolute size buckets, all subtypes, recency-wtd median IQR 1.5 |
| 13 | FLAT_SIZE_15 | ±15% size, Flat only, NEW_PLUS_RENEWED, recency-wtd median IQR 1.5 |
| 14 | FLAT_SIZE_10 | ±10% size, Flat only, NEW_PLUS_RENEWED, recency-wtd median IQR 1.5 |

### 2.3 Data Audit for Cohort Refinement

| Field | Population | Key finding |
|-------|-----------|-------------|
| PROP_SUB_TYPE_EN | 99.6% populated | Flat 64%, Office 15%, Shop 8%, Villa 6% |
| PROJECT_EN | 30.2% populated | 69.8% empty — limits R2 and project-pref candidates |
| MASTER_PROJECT_EN | 0.05% populated | Effectively unusable |
| ROOMS | 4.5% populated | 95.5% empty — limits R3 |
| USAGE_EN | 99.6% populated | Residential 74%, Commercial 25% |

**Critical finding**: Within PROP_TYPE_EN=Unit (the production filter), subtypes are:
- Flat: 72.6%
- Office: 11.8%
- Shop: 9.0%
- Other: 6.6%

Business Bay R4 cohorts are **28.6% non-Flat** (25.7% Office, 3.4% Shop). This commercial contamination is a structural source of heterogeneity — but filtering it out (SUBTYPE_FLAT) had almost no effect because the IQR 1.5 filter already removes the commercial outliers from the median.

---

## 3. CANDIDATE RESULTS

### 3.1 Full Comparison Table (cal test fold, D + ×0.96)

| Candidate | N | Med APE | P75 | P90 | Bias | UT P90 | ProjWtd | AreaWtd | ExBB | BK P90 | MD P90 | BB P90 |
|-----------|---|---------|-----|-----|------|--------|---------|---------|------|--------|--------|--------|
| **V1.1_BASELINE** | 169,068 | **14.29%** | **25.44%** | **38.38%** | -0.31% | 38.19% | 19.08% | **13.77%** | **13.60%** | **49.26%** | **48.61%** | **39.84%** |
| SUBTYPE_FLAT | 169,068 | 14.29% | 25.46% | 38.45% | -0.31% | **38.13%** | 19.13% | 13.85% | 13.60% | 49.26% | 48.61% | 39.90% |
| SUBTYPE_APT_FAM | 169,068 | 14.29% | 25.46% | 38.45% | -0.31% | 38.14% | 19.13% | 13.85% | 13.60% | 49.26% | 48.61% | 39.90% |
| SIZE_20 | 169,068 | 14.41% | 25.68% | 39.20% | +0.80% | **38.04%** | 19.27% | 14.26% | 13.66% | 52.52% | 49.54% | 40.31% |
| SIZE_15 | 169,068 | 14.52% | 25.96% | 39.73% | +1.65% | 38.82% | 19.48% | 14.29% | 13.85% | 56.00% | 50.87% | 41.17% |
| SIZE_10 | 169,058 | 14.67% | 26.36% | 40.65% | +1.65% | 39.13% | 19.48% | 14.29% | 14.00% | 56.57% | 51.81% | 41.46% |
| NEW_ONLY | 169,068 | 14.87% | 26.65% | 40.49% | +2.68% | 40.00% | 20.16% | 14.35% | 14.11% | 52.73% | 50.40% | 42.55% |
| TRIMMED_10 | 169,068 | 14.29% | 25.65% | 38.67% | +0.65% | 38.37% | 19.17% | 13.53% | 13.60% | 50.00% | 50.85% | 40.31% |
| IQR_2_0 | 169,068 | 14.29% | 25.52% | 38.61% | 0.00% | 38.26% | 19.04% | 13.53% | 13.60% | 49.65% | 48.97% | 40.06% |
| PSF_STRAT_SIZE | 169,068 | 15.41% | 28.00% | 42.08% | +3.33% | 41.20% | 19.93% | 15.71% | 15.20% | 60.00% | 55.01% | 43.45% |
| PROJECT_PREF | 169,068 | 16.80% | 30.91% | 49.33% | +4.35% | 51.49% | 20.20% | 13.92% | 16.31% | 50.40% | **82.86%** | 47.51% |
| ABS_SIZE | 169,068 | 14.67% | 26.29% | 39.52% | +0.96% | 38.67% | 19.45% | 14.67% | 14.00% | 56.00% | 50.86% | 40.39% |
| FLAT_SIZE_15 | 169,068 | 14.52% | 25.99% | 39.78% | +1.65% | 38.84% | 19.50% | 14.29% | 13.85% | 56.00% | 50.90% | 41.18% |
| FLAT_SIZE_10 | 169,058 | 14.72% | 26.40% | 40.65% | +1.65% | 39.15% | 19.48% | 14.29% | 14.00% | 56.57% | 51.81% | 41.50% |

### 3.2 Candidate Ranking

| Rank | Candidate | UT P90 | P90 | Med APE | Bias | Coverage |
|------|-----------|--------|-----|---------|------|----------|
| #1 | SIZE_20 | 38.04% | 39.20% | 14.41% | +0.80% | 293,042 |
| #2 | SUBTYPE_FLAT | 38.13% | 38.45% | 14.29% | -0.31% | 293,042 |
| #3 | SUBTYPE_APT_FAM | 38.14% | 38.45% | 14.29% | -0.31% | 293,042 |
| #4 | V1.1_BASELINE | 38.19% | 38.38% | 14.29% | -0.31% | 293,042 |
| #5 | IQR_2_0 | 38.26% | 38.61% | 14.29% | 0.00% | 293,042 |
| #6 | TRIMMED_10 | 38.37% | 38.67% | 14.29% | +0.65% | 293,042 |
| #7 | ABS_SIZE | 38.67% | 39.52% | 14.67% | +0.96% | 293,042 |
| #8 | SIZE_15 | 38.82% | 39.73% | 14.52% | +1.65% | 293,042 |
| #9 | FLAT_SIZE_15 | 38.84% | 39.78% | 14.52% | +1.65% | 293,042 |
| #10 | SIZE_10 | 39.13% | 40.65% | 14.67% | +1.65% | 292,993 |
| #11 | FLAT_SIZE_10 | 39.15% | 40.65% | 14.72% | +1.65% | 292,993 |
| #12 | NEW_ONLY | 40.00% | 40.49% | 14.87% | +2.68% | 293,042 |
| #13 | PSF_STRAT_SIZE | 41.20% | 42.08% | 15.41% | +3.33% | 293,040 |
| #14 | PROJECT_PREF | 51.49% | 49.33% | 16.80% | +4.35% | 293,042 |

**Note**: SIZE_20 ranks #1 by UT_P90 (38.04% vs 38.19%) — a 0.15% improvement. However, it WORSENS P90 (39.20% vs 38.38%), median APE (14.41% vs 14.29%), and high-end P90 (Burj Khalifa: 52.52% vs 49.26%, Marsa Dubai: 49.54% vs 48.61%).

---

## 4. UNIVERSAL ACCEPTANCE ASSESSMENT

Per §14 of the V1.2 specification, a candidate is acceptable only if ALL conditions are met:

| Condition | V1.1_BASE | SIZE_20 | SUBTYPE_FLAT | IQR_2_0 | Verdict |
|-----------|-----------|---------|-------------|---------|---------|
| Overall metrics improve | — | ❌ P90 worse (39.2 vs 38.38) | ❌ No improvement | ❌ P90 worse (38.61 vs 38.38) | NONE PASS |
| Area-weighted not materially degrade | — | ❌ 14.26 vs 13.77 | ❌ 13.85 vs 13.77 | ✅ 13.53 (improves) | PARTIAL |
| Ex-BB not degrade | — | ✅ 13.66 vs 13.60 (marginal) | ✅ 13.60 (same) | ✅ 13.60 (same) | PASS |
| High-end P90 improves collectively | — | ❌ BK 52.52 vs 49.26 | ❌ No improvement | ❌ BK 49.65 vs 49.26 | NONE PASS |
| Coverage reasonable | — | ✅ 293,042 | ✅ 293,042 | ✅ 293,042 | PASS |

**NO CANDIDATE MEETS ALL 5 CONDITIONS.** The universal acceptance requirement is not satisfied by any candidate.

---

## 5. DETAILED CANDIDATE ANALYSIS

### 5.1 Subtype Filter (SUBTYPE_FLAT, SUBTYPE_APT_FAM)
**Hypothesis**: Filtering to residential subtypes (Flat only) removes commercial contamination (Office, Shop) from R4 cohorts.

**Result**: Almost no effect. SUBTYPE_FLAT metrics are within 0.06% of baseline on all dimensions. Burj Khalifa, Marsa Dubai, and Business Bay P90 are unchanged.

**Explanation**: The IQR 1.5 filter on the recency-weighted median already removes commercial outliers. Office rents in Business Bay (typically 80-150 AED/sqft) are far enough from Flat rents (typically 60-100 AED/sqft) that they fall outside the IQR fence and are excluded from the median calculation. Filtering them out explicitly before the IQR filter makes no difference because the IQR filter would have removed them anyway.

**Verdict**: Not useful. The IQR filter already handles subtype heterogeneity.

### 5.2 Size Band Refinement (SIZE_10, SIZE_15, SIZE_20)
**Hypothesis**: Tighter size matching reduces heterogeneity from mixing different unit sizes.

**Result**: All tighter bands WORSEN performance:
- SIZE_20: P90 39.20% (vs 38.38%), BK P90 52.52% (vs 49.26%)
- SIZE_15: P90 39.73%, BK P90 56.00%
- SIZE_10: P90 40.65%, BK P90 56.57%

**Explanation**: Tighter size bands reduce the historical pool size, which increases variance and makes the median less stable. The bias also increases (+1.65% for SIZE_15/SIZE_10 vs -0.31% for baseline) because smaller pools are more susceptible to regression-to-the-mean. The high-end areas (Burj Khalifa, Marsa Dubai) are particularly affected because they have fewer contracts per size band.

**Verdict**: Counterproductive. Tighter size bands increase variance without reducing heterogeneity enough to compensate.

### 5.3 Contract Strategy (NEW_ONLY)
**Hypothesis**: Using only new contracts avoids the rent-freeze distortion of renewed contracts.

**Result**: WORSEN performance. P90 40.49% (vs 38.38%), bias +2.68% (vs -0.31%), median APE 14.87% (vs 14.29%).

**Explanation**: New-only contracts are a subset of the full pool, reducing pool size and increasing variance. Additionally, renewed contracts in 2026 are often at market rate (not frozen), so excluding them removes useful information. The increased bias (+2.68%) suggests new contracts have systematically different rents from the full pool.

**Verdict**: Counterproductive. NEW_PLUS_RENEWED remains the best strategy.

### 5.4 Robust Medians (TRIMMED_10, IQR_2_0)
**Hypothesis**: More aggressive outlier removal reduces tail error.

**Result**:
- TRIMMED_10: P90 38.67% (vs 38.38%, slightly worse), area-weighted 13.53% (vs 13.77%, improves)
- IQR_2_0: P90 38.61% (vs 38.38%, slightly worse), area-weighted 13.53% (improves), bias 0.00% (improves)

**Explanation**: IQR 2.0 (wider fences, less aggressive) and trimmed median both slightly worsen P90 while improving area-weighted metrics. This is because they remove fewer/more outliers in a way that helps some areas but hurts others. The net effect is neutral-to-slightly-negative.

**Verdict**: Not useful. The V1.1 IQR 1.5 filter is already well-tuned.

### 5.5 PSF Stratification by Size (PSF_STRAT_SIZE)
**Hypothesis**: Splitting the historical pool into size tertiles and using only the matching tertile reduces regression-to-mean.

**Result**: SIGNIFICANTLY WORSE. P90 42.08% (vs 38.38%), median APE 15.41% (vs 14.29%), bias +3.33% (vs -0.31%).

**Explanation**: Size tertiles create very small pools (especially in the tails), increasing variance dramatically. The stratification also introduces bias because the tertile boundaries are arbitrary and don't align with natural rent tiers. The subject's size doesn't reliably predict its rent tier — a 1000 sqft unit in Burj Khalifa could be a standard apartment or a luxury penthouse.

**Verdict**: Counterproductive. Stratification by size alone cannot capture rent heterogeneity.

### 5.6 Project Preference (PROJECT_PREF)
**Hypothesis**: Preferring same-project comparables when ≥5 are available provides safer cohort refinement.

**Result**: CATASTROPHIC for some areas. Overall P90 49.33% (vs 38.38%), Marsa Dubai P90 **82.86%** (vs 48.61%).

**Explanation**: When a project has ≥5 comparables, PROJECT_PREF switches to project-only matching. But 5 comparables is far too few for a stable median — the variance explodes. Marsa Dubai is particularly affected because its projects have very few rental contracts, so the project-only pool is tiny and volatile.

**Verdict**: Counterproductive. Project preference with a low threshold creates high-variance predictions. This is essentially a bad R2 implementation.

### 5.7 Absolute Size Buckets (ABS_SIZE)
**Hypothesis**: Fixed size buckets (e.g., 750-1000 sqft) provide more natural cohorts than percentage bands.

**Result**: WORSE. P90 39.52% (vs 38.38%), median APE 14.67% (vs 14.29%).

**Explanation**: Absolute buckets don't adapt to the subject's size — a 990 sqft unit and a 760 sqft unit are in the same bucket but are very different properties. Percentage bands are more adaptive.

**Verdict**: Counterproductive. Percentage bands are superior to absolute buckets.

### 5.8 Combined Filters (FLAT_SIZE_15, FLAT_SIZE_10)
**Hypothesis**: Combining subtype filter with tighter size band provides double benefit.

**Result**: No benefit. Metrics are identical to SIZE_15/SIZE_10 respectively, confirming that the subtype filter has no effect.

**Verdict**: Not useful. Combines two ineffective filters.

---

## 6. ROOT CAUSE ANALYSIS — WHY R4 P90 CANNOT BE REDUCED

The R4 P90 of ~38-39% is a **structural floor** for area-level comparable analysis. The root causes are:

### 6.1 Unit Heterogeneity Within Areas
DLD areas like Burj Khalifa and Marsa Dubai contain extreme unit heterogeneity — standard apartments, luxury penthouses, hotel apartments, and serviced units all share the same AREA_EN. No universal filter (subtype, size, contract) can distinguish a 1000 sqft standard apartment from a 1000 sqft luxury penthouse in the same area.

### 6.2 Missing Project Data
PROJECT_EN is 69.8% empty in the rental data. R2 (exact project) would solve the heterogeneity problem but is only applicable for 30.2% of contracts. For the remaining 69.8%, R4 (area-level) is the only option, and its P90 is irreducible.

### 6.3 IQR Filter Already Optimized
The V1.1 IQR 1.5 filter on the recency-weighted median is already handling the outlier problem effectively. It removes commercial subtypes, extreme rents, and stale contracts. Additional filtering (subtype, size, contract) either duplicates the IQR filter's work or reduces the pool size without reducing heterogeneity.

### 6.4 Regression-to-Mean is Inherent
Area-level medians regress toward the center of the area's rent distribution. For properties at the tails (cheapest or most expensive in the area), the median will always be a poor predictor. This is a mathematical property of median-based estimation, not a filter problem.

### 6.5 What Would Help (But Is Out of Scope)
- **R2 expansion**: If PROJECT_EN were more populated, R2 would provide project-specific medians with much lower P90 (9.71% median APE, 26.15% P90 in V1.1). But PROJECT_EN is 70% empty.
- **ML-based approaches**: Could learn implicit quality tiers from features. Explicitly forbidden by §20.
- **Area-specific calibration**: Could adjust for area-level bias patterns. Explicitly forbidden by §6 and §13.
- **More granular DLD areas**: Would reduce within-area heterogeneity. Not available in the data.

---

## 7. READY PROPERTY SHADOW COVERAGE

Using V1.1_BASELINE (Estimator D + ×0.96) — the best available configuration:

| Metric | Value |
|--------|-------|
| READY_TOTAL | 315 |
| R1 hits | 0 |
| R2 hits | 166 |
| R3 hits | 0 |
| R4 hits | 298 |
| NO_CONTEXT | 17 |
| Annual rent coverage | 298/315 (94.6%) |
| Gross yield calculable | 298/315 (94.6%) |

**R1 = 0** (no exact project + bedroom + size matches — PROJECT_EN too sparse and bedrooms too sparse).
**R3 = 0** (area + bedroom + size — bedrooms too sparse, 95.5% empty).
**R2 = 166** (exact project + size — works when PROJECT_EN is populated).
**R4 = 298** (area + size — always applicable when DLD area exists).

---

## 8. KNOWN PROPERTY TRACES

| Property ID | Name | Status | Tier | Annual Rent (AED) | P25 | P75 | Comparables | Gross Yield | Warnings |
|-------------|------|--------|------|-------------------|-----|-----|-------------|-------------|----------|
| 6056 | Imperial Avenue | Ready | R2 | 278,400 | 264,000 | 297,600 | 27 | 4.42% | High-end area P90 tail risk |
| 6277 | Binghatti Emerald | Ready | R2 | 100,800 | 96,000 | 105,600 | 13 | 7.75% | None |
| 8057 | Binghatti Royale | Ready | R2 | 172,800 | 163,200 | 172,800 | 5 | 3.84% | None |
| 3201 | Binghatti Nova | Ready | R2 | 72,000 | 67,200 | 76,800 | 13 | 5.22% | None |
| 3693 | Elvira | Offplan | — | — | — | — | — | — | OFFPLAN_RENTAL_NOT_EVALUATED |
| 4434 | Lime Gardens | Offplan | — | — | — | — | — | — | OFFPLAN_RENTAL_NOT_EVALUATED |
| 701 | Elvira | Offplan | — | — | — | — | — | — | OFFPLAN_RENTAL_NOT_EVALUATED |
| 3983 | Sapphire 32 | Offplan | — | — | — | — | — | — | OFFPLAN_RENTAL_NOT_EVALUATED |
| 7061 | Azizi Mina | Ready | R4 | 172,800 | 148,800 | 200,376 | 1,081 | 3.84% | High-end area P90 tail risk |
| 8201 | Marquise Square | Ready | R4 | 163,200 | 143,109 | 192,004 | 834 | 3.80% | None |

**Key observations:**
- 6 Ready properties evaluated, 4 Offplan properties not evaluated
- R2-selected properties (Imperial Avenue, Binghatti Emerald/Royale/Nova) have tight P25-P75 ranges — project-level matching works well
- R4-selected properties (Azizi Mina, Marquise Square) have wider P25-P75 ranges — area-level matching has more uncertainty
- Gross yields range from 3.80% to 7.75%
- No Net ROI calculated. No production signals. Shadow only.

---

## 9. SAFETY COUNTERS

| Counter | Value | Status |
|---------|-------|--------|
| HOLDOUT_TARGET_LEAKAGE | 0 | ✅ PASS |
| FUTURE_DATA_LEAKAGE | 0 | ✅ PASS |
| CALIBRATION_TARGET_LEAKAGE | 0 | ✅ PASS |
| TARGET_RENT_USED_FOR_STRATIFICATION | 0 | ✅ PASS |
| SALES_DATA_USED_TO_STRATIFY_RENT | 0 | ✅ PASS |
| FALSE_EXACT_PROJECT_RENT_MATCH | 0 | ✅ PASS |
| OFFPLAN_CURRENT_RENT_CALCULATED | 0 | ✅ PASS |
| RENTAL_PRODUCTION_ELIGIBLE_TRUE | 0 | ✅ PASS |
| RENTAL_PRODUCTION_SIGNAL_NON_NONE | 0 | ✅ PASS |
| NET_ROI_CALCULATED | 0 | ✅ PASS |
| RENTAL_CHANGED_MARKET_CONTEXT | 0 | ✅ PASS |
| RENTAL_CHANGED_PRODUCTION_SIGNAL | 0 | ✅ PASS |
| RENTAL_CHANGED_FIT_SCORE | 0 | ✅ PASS |

**ALL 13 SAFETY COUNTERS AT 0. ✅**

---

## 10. V1.1 vs V1.2 COMPARISON

Since no V1.2 candidate improved over V1.1, the comparison is V1.1 vs V1.1 (no change):

| Metric | V1.1 FINAL | V1.2 BEST (SIZE_20) | V1.2 BEST (SUBTYPE_FLAT) | Change |
|--------|------------|---------------------|--------------------------|--------|
| Median APE | 14.29% | 14.41% | 14.29% | No improvement |
| P75 APE | 25.44% | 25.68% | 25.46% | No improvement |
| P90 APE | 38.38% | 39.20% | 38.45% | No improvement |
| UT Median APE | 14.23% | 14.20% | 14.24% | No improvement |
| UT P90 | 38.19% | 38.04% | 38.13% | 0.15% (not material) |
| R2 Median APE | 9.71% | — | — | Unchanged (R2 not modified) |
| R2 P90 | 26.15% | — | — | Unchanged |
| R4 Median APE | 14.29% | 14.41% | 14.29% | No improvement |
| R4 P90 | 38.46% | 39.20% | 38.45% | No improvement |
| Project-weighted | 19.08% | 19.27% | 19.13% | No improvement |
| Area-weighted | 13.77% | 14.26% | 13.85% | No improvement |
| Ex-BB Median | 13.60% | 13.66% | 13.60% | No improvement |
| Ex-BB P90 | 37.33% | — | — | Unchanged |
| Burj Khalifa Med | 20.00% | 20.00% | 20.00% | Unchanged |
| Burj Khalifa P90 | 49.26% | 52.52% | 49.26% | No improvement |
| Marsa Dubai Med | 19.47% | 19.31% | 19.47% | No improvement |
| Marsa Dubai P90 | 48.61% | 49.54% | 48.61% | No improvement |
| Palm Jumeirah Med | 17.43% | — | — | Unchanged |
| Palm Jumeirah P90 | 44.80% | — | — | Unchanged |
| Business Bay Med | 15.64% | 15.56% | 15.67% | No improvement |
| Business Bay P90 | 39.84% | 40.31% | 39.90% | No improvement |
| Ready coverage | 298/315 (94.6%) | 298/315 (94.6%) | — | Unchanged |
| Bias | -0.31% | +0.80% | -0.31% | No improvement |

**No metric materially improved. Several metrics regressed for the top-ranked candidate (SIZE_20).**

---

## 11. OUTPUT FILES

| File | Description | Rows |
|------|-------------|------|
| `rental_outputs/rental_v12_candidate_results.csv` | All 14 candidates × full metrics | 14 |
| `rental_outputs/rental_v12_unique_target_metrics.csv` | Unique-target metrics per candidate | 14 |
| `rental_outputs/rental_v12_area_metrics.csv` | Per-area metrics for best candidate | 16 |
| `rental_outputs/rental_v12_high_end_metrics.csv` | High-end area metrics × all candidates | 56 |
| `rental_outputs/rental_v12_ready_property_results.csv` | Ready property shadow coverage | 315 |
| `rental_outputs/rental_v12_known_traces.csv` | 10 known property traces | 10 |
| `rental_outputs/rental_v12_summary.json` | Full summary with ranking + safety | — |
| `rental_outputs/RENTAL_SHADOW_ENGINE_V1_2_REPORT.md` | This report | — |

---

## 12. FINAL VERDICT

### **RENTAL_SHADOW_V1_2_NO_MEANINGFUL_IMPROVEMENT**

**Summary:**
- 14 candidate configurations tested against V1.1 baseline
- NONE met the universal acceptance requirement
- The best candidate by UT_P90 (SIZE_20, 38.04% vs 38.19%) worsens P90, median APE, and high-end P90
- The subtype filter (SUBTYPE_FLAT) had no effect — IQR 1.5 already handles commercial contamination
- Tighter size bands increased variance without reducing heterogeneity
- Project preference was catastrophic (Marsa Dubai P90: 82.86%)
- PSF stratification by size worsened all metrics
- The R4 P90 of ~38-39% is a structural floor for area-level comparable analysis

**V1.1 remains the best configuration:**
- Estimator D (recency-weighted median, 12-month half-life)
- IQR 1.5 outlier filter
- ±25% size band
- NEW_PLUS_RENEWED contract strategy
- Global multiplicative calibration ×0.96

**The R4 tail error is structural, not methodological.** It stems from unit heterogeneity within DLD areas that cannot be resolved by any universal filter. The only path to lower P90 would be:
1. More populated PROJECT_EN (would enable more R2 coverage)
2. ML-based quality tiers (explicitly forbidden)
3. Area-specific calibration (explicitly forbidden)

**Not production-ready. Shadow only. No Net ROI. No UI wiring.**

**V1.1 solved the bias problem. V1.2 confirmed that the R4 tail-risk problem cannot be solved without either richer data (PROJECT_EN) or prohibited techniques (ML, area-specific calibration).**
