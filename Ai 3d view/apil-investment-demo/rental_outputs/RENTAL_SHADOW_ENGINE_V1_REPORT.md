# RENTAL SHADOW ENGINE V1 — FINAL VALIDATION REPORT

**Date**: 2026-08-20
**Status**: SHADOW_RESEARCH ONLY (not production)
**Version**: RENTAL_SHADOW_RESEARCH_CONFIG + CANONICAL_DLD_SALES_ONLY_V1 (frozen)

---

## 1. EXECUTIVE SUMMARY

| Metric | Value |
|--------|-------|
| **VERDICT** | **PROMISING — NEEDS REFINEMENT** |
| Ready properties evaluated | 315 |
| Tier hits (R1-R4) | 301 (95.6% coverage) |
| Tier hits with temporal holdout | 13 (4.3% of tier hits) |
| Individual out-of-sample predictions | 306 |
| Median Absolute Percentage Error (MAPE) | **13.6%** |
| P75 APE | 24.0% |
| P90 APE | 39.0% |
| Signed Bias (Median) | +12.5% (over-estimation) |
| Signed Bias (Mean) | +16.9% |
| Project-Weighted MAPE | 20.6% |

**Interpretation**: The engine achieves strong tier coverage (95.6% of Ready properties hit at least one comparator tier) and out-of-sample prediction accuracy (median 13.6% APE) that is **promising** for a research shadow. However, the positive signed bias (+12.5% median, +16.9% mean) indicates systematic over-estimation in the temporal holdout, and only 13/301 tier-hit properties had sufficient temporal data for holdout validation (4.3%). This warrants **refinement** before any production consideration.

---

## 2. METHODOLOGY (FROZEN PER SPEC)

### 2.1 Comparator Tiers (CORRECTED per Section 7)
- **R1**: EXACT_PROJECT + SAME_BEDROOM + SIMILAR_SIZE → min 5 comps
- **R2**: EXACT_PROJECT + SIMILAR_SIZE (bedroom not required) → min 8 comps
- **R3**: SAME_AREA + SAME_BEDROOM + SIMILAR_SIZE → min 10 comps
- **R4**: SAME_AREA + SIMILAR_SIZE → min 20 comps

### 2.2 Best Configuration (from grid search)
- **Size band**: ±25% (0.25)
- **Lookback**: 24 months
- **Contract strategy**: NEW_PLUS_RENEWED
- **Cutoff date**: 2026-03-31

### 2.3 Estimation Methods
- **Method A**: Median annual rent of comparables
- **Method B**: Median PSF × subject unit size (preferred when subject size known)
- Selection: B used if subject size available, else A

### 2.4 Temporal Holdout (TRUE OUT-OF-SAMPLE)
- For each test lease (registered after cutoff):
  1. Build comparator cohort using ONLY contracts registered before the target lease
  2. Exclude the target lease itself
  3. Predict target annual rent using historical cohort only
  4. Compare prediction to actual annual rent
- Metrics: MEDIAN_ERROR, P75_ERROR, P90_ERROR, SIGNED_BIAS, PROJECT_WEIGHTED_ERROR

### 2.5 Critical Constraints (ALL ENFORCED)
- ✅ READY status only (Offplan → OFFPLAN_RENTAL_NOT_EVALUATED, Unknown → STATUS_NOT_ELIGIBLE)
- ✅ TOTAL_PROPERTIES == 1 filter (single-property contracts only)
- ✅ ACTUAL_AREA unit: SQM → SQFT conversion (×10.7639104167)
- ✅ Property type isolation (Unit/Apartment separate from Villa)
- ✅ NO circular validation (no yield caps, no sales benchmark rejection)
- ✅ NO production eligibility (production_eligible=False, production_signal_source=NONE for all tiers)
- ✅ NO net ROI calculation
- ✅ NO production UI wiring

---

## 3. DATA SOURCES & LINEAGE

| Source | Path | Records | Usage |
|--------|------|---------|-------|
| MASTER_FINAL.xlsx | project root | 2,614 properties | Subject properties (authoritative) |
| dxb_rents_all.csv | project root (DLD_RENTS_PATH) | 384,161 contracts | Rental comparables (SHA256 verified) |
| Manual area mapping | MANUAL_RENTAL_AREA_MAPPING_V1 | 99 mappings | MASTER area → DLD rental area |
| Auto area mapping | rental_area_mapping.py | generated | Project-overlap based, auditable |

**Data Filtering Applied**:
- Rental contracts: TOTAL_PROPERTIES == 1 ONLY (excludes building-level leases)
- Temporal span: 2026-01-01 to 2026-08-09 (214 unique registration dates)
- Property type isolation: Unit/Apartment ≠ Villa

---

## 4. COVERAGE ANALYSIS

### 4.1 Full MASTER (2,614 properties)
| Status | Count | % |
|--------|-------|---|
| Offplan | 2,249 | 86.0% |
| Ready | 315 | 12.1% |
| Unknown | 50 | 1.9% |

### 4.2 Ready Properties (315) — Tier Assignment
| Tier | Count | % of Ready | Evidence Level |
|------|-------|-----------|----------------|
| R4 (Area + Size) | 203 | 64.4% | AREA_LEVEL |
| R2 (Project + Size) | 67 | 21.3% | PROJECT_LEVEL |
| R3 (Area + Bedroom + Size) | 31 | 9.8% | AREA_BEDROOM_LEVEL |
| R1 (Project + Bedroom + Size) | 0 | 0.0% | PROJECT_LEVEL |
| NO_RENTAL_EVIDENCE_IN_AREA | 7 | 2.2% | NONE |
| NO_TIER_MET_MINIMUM | 7 | 2.2% | NONE |
| **Tier hits (R1-R4)** | **301** | **95.6%** | — |

### 4.3 R1 Diagnostic (0 hits)
R1 requires EXACT_PROJECT + SAME_BEDROOM + SIMILAR_SIZE with min 5 contracts.
- Root cause: 63.6% of rental contracts have missing PROJECT_EN (cannot match exact project)
- R2 (project + size, bedroom not required) captures 67 properties where project is available
- R1 would require both project AND bedroom match simultaneously — too restrictive given data sparsity

---

## 5. TEMPORAL HOLDOUT VALIDATION RESULTS

### 5.1 Aggregate Metrics (306 individual predictions)
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Median APE | 13.64% | ≤20% | ✅ PASS |
| P75 APE | 23.96% | ≤30% | ✅ PASS |
| P90 APE | 39.01% | ≤40% | ✅ PASS (marginal) |
| Median Bias | +12.50% | ±10% | ⚠️ OVER-ESTIMATE |
| Mean Bias | +16.91% | ±10% | ⚠️ OVER-ESTIMATE |
| Project-Weighted MAPE | 20.60% | ≤20% | ⚠️ MARGINAL |

### 5.2 Per-Property Holdout (13 properties with sufficient temporal data)
| Property ID | Tier | MAPE | P75 | P90 | Bias | N_pred | Pass |
|-----------|------|------|-----|-----|------|--------|------|
| 2459 | R2 | 28.0% | 40.7% | 60.0% | +28.0% | 50 | ❌ |
| 507 | R2 | 32.9% | 40.0% | 50.7% | +32.9% | 18 | ❌ |
| 6556 | R2 | 7.6% | 12.5% | 14.0% | +2.3% | 20 | ✅ |
| 983 | R2 | 17.1% | 36.6% | 42.3% | +17.1% | 14 | ✅ |
| 8220 | R2 | 16.5% | 26.3% | 42.5% | +13.7% | 16 | ✅ |
| 6235 | R2 | 16.9% | 22.7% | 35.0% | +16.9% | 26 | ✅ |
| 2645 | R2 | 10.2% | 12.9% | 38.0% | +8.0% | 29 | ✅ |
| 4872 | R2 | 18.7% | 22.7% | 28.1% | +17.0% | 16 | ✅ |
| 3522 | R2 | 10.7% | 11.7% | 15.5% | +9.4% | 13 | ✅ |
| 1656 | R2 | 10.2% | 18.2% | 18.2% | +8.3% | 34 | ✅ |
| 7266 | R2 | 8.7% | 13.6% | 21.5% | +8.7% | 34 | ✅ |
| 7170 | R2 | 19.6% | 20.4% | 25.4% | +19.6% | 20 | ✅ |
| 6246 | R2 | 16.5% | 26.3% | 42.5% | +13.7% | 16 | ✅ |

**Pass rate**: 11/13 (84.6%) at MAPE ≤20% threshold

### 5.3 Geographic Distribution
- **Business Bay**: 248 predictions (81% of total) — median APE 13.3%
- **Palm Jumeirah**: 58 predictions (19% of total) — median APE 16.9%

**Concentration risk**: 81% of holdout predictions are from Business Bay, limiting generalization confidence.

---

## 6. SAFETY COUNTER VERIFICATION

| Counter | Expected | Actual | Status |
|---------|----------|--------|--------|
| Production-eligible tiers | 0 | 0 | ✅ PASS |
| Production signal source != NONE | 0 | 0 | ✅ PASS |
| Circular validation pathways | 0 | 0 | ✅ PASS |
| Net ROI calculations | 0 | 0 | ✅ PASS |
| UI production wiring | 0 | 0 | ✅ PASS |

**All safety counters at zero. Engine is confirmed SHADOW_RESEARCH ONLY.**

---

## 7. KNOWN LIMITATIONS

1. **Temporal data sparsity**: Only 13/301 tier-hit properties (4.3%) had ≥10 train and ≥10 test leases for holdout. The rental dataset spans only 8 months (2026-01 to 2026-08), limiting temporal validation depth.

2. **Geographic concentration**: 81% of holdout predictions from Business Bay. Generalization to other areas (JVC, Arjan, Marina) is unvalidated.

3. **Systematic over-estimation**: +12.5% median / +16.9% mean bias suggests the historical cohort median is higher than subsequent leases. Possible causes:
   - Rent decline in 2026 H1 (market softening)
   - Survivorship: older leases registered at higher rates
   - Method B (PSF × size) over-estimates when subject size differs from cohort median

4. **R1 tier unused**: No properties hit R1 due to missing PROJECT_EN in 63.6% of contracts. R2 (project + size) is the de-facto highest tier.

5. **Offplan dominance**: 86% of MASTER is Offplan — rental shadow only applies to 12% (Ready). Net ROI integration (when built) will be limited to Ready segment.

---

## 8. RECOMMENDATIONS

### Immediate (Pre-Production Gate)
1. **Bias correction**: Apply -12.5% median / -16.9% mean bias adjustment to R2/R4 estimates, or investigate rent trend decomposition.
2. **Expand temporal window**: Collect rental data with ≥12 months history per area before re-running holdout.
3. **Geographic diversification**: Prioritize holdout validation in JVC, Arjan, Dubai Marina (currently 0 holdout predictions).

### Medium-Term
4. **R1 activation**: Improve PROJECT_EN fill rate (currently 36.4%) via developer-name normalization to unlock R1.
5. **Method B refinement**: Cap PSF × size estimate when subject size > 2× cohort median to reduce over-estimation.
6. **Renewal vs New separation**: Re-run grid with NEW_ONLY strategy to test if renewal leases bias estimates.

### Long-Term
7. **Production readiness**: Only after holdout MAPE ≤15% AND bias ≤±5% AND ≥50 properties validated across ≥5 areas.
8. **Net ROI integration**: Build separately per handoff Section 45 — NOT in this shadow phase.

---

## 9. VERDICT

**PROMISING — NEEDS REFINEMENT**

The Rental Shadow V1 engine demonstrates:
- ✅ Strong tier coverage (95.6% of Ready properties)
- ✅ Reasonable out-of-sample accuracy (median 13.6% APE)
- ✅ Clean safety posture (all shadow-only counters at zero)
- ✅ Corrected methodology fully implemented per spec

But requires refinement on:
- ⚠️ Systematic over-estimation bias (+12.5% median)
- ⚠️ Limited temporal validation depth (4.3% of tier hits)
- ⚠️ Geographic concentration (81% Business Bay)

**Recommendation**: Continue as SHADOW_RESEARCH. Do NOT promote to production. Address bias correction and temporal expansion before re-evaluation.

---

## 10. ARTIFACTS

| File | Description |
|------|-------------|
| `rental_outputs/rental_shadow_baseline_v1.csv` | 2,614 property baseline with tier assignments |
| `rental_outputs/rental_shadow_baseline_v1.json` | Same, JSON format |
| `rental_outputs/rental_grid_results_v1.csv` | 12/12 parameter grid search results |
| `rental_outputs/rental_grid_results_v1.json` | Same, JSON format |
| `rental_outputs/holdout_predictions_v1.csv` | 306 individual temporal holdout predictions |
| `rental_outputs/holdout_predictions_v1.json` | Same, JSON format |
| `rental_outputs/temporal_holdout_summary_v1.json` | Aggregate metrics + per-property details |
| `rental_outputs/RENTAL_RAW_DATA_AUDIT_V1.md` | Raw data audit (16 sections) |
| `rental_outputs/RENTAL_SHADOW_ENGINE_V1_REPORT.md` | This report |

---

**END OF REPORT**
