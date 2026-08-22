# Fallback DLD Benchmark — V3 IMPLEMENTATION REPORT
**Generated:** 2026-08-18T20:32:39.045107

## Transaction Provenance & Sales Filter

| Counter | Value |
|---------|-------|
| TOTAL_RAW_TRANSACTIONS | 112,749 |
| SALES_INCLUDED | 86,141 |
| MORTGAGE_EXCLUDED | 22,239 |
| GIFTS_EXCLUDED | 4,369 |
| OTHER_NON_SALE_EXCLUDED | 0 |
| AMBIGUOUS_SIZE_EXCLUDED | 0 |

## Size Unit Detection (Source-Aware)

Empirically verified:
- DLD_OFFICIAL (numeric prefix): ACTUAL_AREA is in **sqm**
- DXBINTERACT (DXB-* prefix): ACTUAL_AREA is in **sqft**
- OTHER_DLD_SALES: ACTUAL_AREA is in **sqm**

## Area Mapping (Dominance Ratio)

Total mappings: 56
Ambiguous mappings excluded: 0

## Backtest Target

Properties with valid canonical exact-project target: 796

Target uses `investor_api.dld_benchmark_engine.compute_project_benchmark` with:
- exact_project_only=True
- same bedroom filter
- same status filter (with fallback to all if insufficient)
- MIN_TRANSACTION_VALUE = 100,000 AED

## Train/Test Split

| Dimension | Count |
|-----------|-------|
| Tuning projects | 257 |
| Holdout projects | 111 |
| PROJECT_LEAKAGE_BETWEEN_TRAIN_TEST | 0 |

## Best Configuration (from tuning set)

```json
{
  "lookback_months": 24,
  "size_band_pct_default": 0.2,
  "min_transactions_area_fallback": 10,
  "min_unique_projects_area": 3,
  "max_project_concentration": 0.5,
  "outlier_method": "iqr_1.5"
}
```

## Accuracy Results

| Metric | Tuning | Holdout | DLD_OFFICIAL_ONLY |
|--------|--------|---------|-------------------|
| N | 448 | 188 | 129 |
| Median abs error | 11.30% | 12.99% | 13.44% |
| Mean abs error | 18.05% | 19.37% | 19.97% |
| P75 | 22.89% | 25.33% | 23.81% |
| P90 | 36.25% | 42.61% | 42.61% |
| Direction match | 45.8% | 52.1% | 51.9% |

## Audit Counters

| Counter | Value | Target |
|---------|-------|--------|
| TARGET_BENCHMARK_MISMATCH | 0 | 0 |
| TARGET_TRANSACTION_ID_MISMATCH | 0 | 0 |
| TARGET_LEAKAGE_COUNT | 0 | 0 |
| NON_SALE_TRANSACTION_USED_IN_BENCHMARK | 0 | 0 |
| AMBIGUOUS_SIZE_USED | 0 | 0 |
| AMBIGUOUS_AREA_MAPPING_USED | 0 | 0 |
| MISSING_SIZE_BENCHMARK_GENERATED | 0 | 0 |
| STATUS_BROADENED_WITHOUT_LABEL | 0 | 0 |
| PROJECT_CONCENTRATION_RULE_NOT_ENFORCED | 0 | 0 |

## Holdout Segmented Results

### area_Al Furjan
- N: 10
- Median abs error: 8.61%
- P90: 46.90%
- Direction match: 30.0%

### area_Arjan
- N: 17
- Median abs error: 12.36%
- P90: 35.05%
- Direction match: 47.1%

### area_Business Bay
- N: 21
- Median abs error: 17.06%
- P90: 35.14%
- Direction match: 47.6%

### area_Dubai Creek Harbour
- N: 6
- Median abs error: 28.36%
- P90: 275.82%
- Direction match: 66.7%

### area_Dubai Islands
- N: 6
- Median abs error: 17.37%
- P90: 50.60%
- Direction match: 66.7%

### area_Dubai Land Residence Complex
- N: 7
- Median abs error: 13.59%
- P90: 29.62%
- Direction match: 42.9%

### area_Dubai Marina
- N: 9
- Median abs error: 37.84%
- P90: 66.74%
- Direction match: 44.4%

### area_Dubai South
- N: 5
- Median abs error: 11.95%
- P90: 26.67%
- Direction match: 40.0%

### area_Dubai Sports City
- N: 14
- Median abs error: 16.63%
- P90: 56.77%
- Direction match: 71.4%

### area_Jumeirah Village Triangle
- N: 5
- Median abs error: 20.00%
- P90: 27.41%
- Direction match: 40.0%

### area_Jumeirah village circle
- N: 45
- Median abs error: 9.85%
- P90: 27.16%
- Direction match: 64.4%

### bedroom_1BR
- N: 78
- Median abs error: 12.23%
- P90: 45.69%
- Direction match: 51.3%

### bedroom_2BR
- N: 61
- Median abs error: 13.44%
- P90: 44.23%
- Direction match: 55.7%

### bedroom_3BR
- N: 9
- Median abs error: 20.00%
- P90: 48.64%
- Direction match: 55.6%

### bedroom_Studio
- N: 40
- Median abs error: 13.08%
- P90: 34.52%
- Direction match: 47.5%

### distance_0-5%
- N: 38
- Median abs error: 1.81%
- P90: 4.53%
- Direction match: 94.7%

### distance_10-20%
- N: 55
- Median abs error: 13.34%
- P90: 17.52%
- Direction match: 38.2%

### distance_20-30%
- N: 30
- Median abs error: 24.72%
- P90: 28.76%
- Direction match: 40.0%

### distance_30%+
- N: 33
- Median abs error: 45.69%
- P90: 62.41%
- Direction match: 33.3%

### distance_5-10%
- N: 32
- Median abs error: 6.86%
- P90: 9.19%
- Direction match: 56.2%

### price_1–2M
- N: 104
- Median abs error: 11.38%
- P90: 35.14%
- Direction match: 52.9%

### price_2–4M
- N: 32
- Median abs error: 22.07%
- P90: 45.88%
- Direction match: 46.9%

### price_4–8M
- N: 5
- Median abs error: 47.34%
- P90: 55.81%
- Direction match: 40.0%

### price_8M+
- N: 3
- Median abs error: 34.98%
- P90: 48.64%
- Direction match: 100.0%

### price_< 1M
- N: 44
- Median abs error: 11.77%
- P90: 28.76%
- Direction match: 52.3%

### quality_high
- N: 159
- Median abs error: 11.95%
- P90: 35.67%
- Direction match: 53.5%

### quality_medium
- N: 28
- Median abs error: 26.48%
- P90: 62.41%
- Direction match: 46.4%

### size_1000–1500 sqft
- N: 51
- Median abs error: 13.03%
- P90: 46.90%
- Direction match: 49.0%

### size_1500–2500 sqft
- N: 16
- Median abs error: 21.77%
- P90: 55.81%
- Direction match: 56.2%

### size_600–1000 sqft
- N: 77
- Median abs error: 11.95%
- P90: 37.84%
- Direction match: 57.1%

### size_< 600 sqft
- N: 44
- Median abs error: 12.51%
- P90: 29.62%
- Direction match: 45.5%

### status_Offplan
- N: 151
- Median abs error: 12.61%
- P90: 42.61%
- Direction match: 49.0%

### status_Ready
- N: 37
- Median abs error: 17.09%
- P90: 42.56%
- Direction match: 64.9%

### type_nan
- N: 188
- Median abs error: 12.99%
- P90: 42.61%
- Direction match: 52.1%

## Area Reliability

- **Al Furjan**: CANDIDATE_RELIABLE | N=10 | med_err=8.6% | P90=46.9% | dir=30.0%
- **Jumeirah village circle**: CANDIDATE_RELIABLE | N=45 | med_err=9.8% | P90=27.2% | dir=64.4%
- **Dubai South**: CANDIDATE_RELIABLE | N=5 | med_err=11.9% | P90=26.7% | dir=40.0%
- **Arjan**: CANDIDATE_RELIABLE | N=17 | med_err=12.4% | P90=35.0% | dir=47.1%
- **Dubai Land Residence Complex**: CANDIDATE_RELIABLE | N=7 | med_err=13.6% | P90=29.6% | dir=42.9%
- **Dubai Sports City**: CANDIDATE_RELIABLE | N=14 | med_err=16.6% | P90=56.8% | dir=71.4%
- **Business Bay**: CANDIDATE_RELIABLE | N=21 | med_err=17.1% | P90=35.1% | dir=47.6%
- **Dubai Islands**: CANDIDATE_RELIABLE | N=6 | med_err=17.4% | P90=50.6% | dir=66.7%
- **Jumeirah Village Triangle**: CANDIDATE_RELIABLE | N=5 | med_err=20.0% | P90=27.4% | dir=40.0%
- **Dubai Creek Harbour**: MARGINAL | N=6 | med_err=28.4% | P90=275.8% | dir=66.7%
- **Dubai Marina**: MARGINAL | N=9 | med_err=37.8% | P90=66.7% | dir=44.4%

## Worst Cases (Top 50)

- **OTHER**: 42
- **AREA_TOO_HETEROGENEOUS**: 8

## Production Status

**production_eligible: FALSE**

No production decisions, frontend, MASTER_FINAL, Qdrant, or raw DLD CSVs modified.

## Files Generated

| File | Description |
|------|-------------|
| FALLBACK_V3_TRANSACTION_PROVENANCE.xlsx | Transaction source, size unit, conversion |
| FALLBACK_V3_AREA_MAPPING_AUDIT.xlsx | Area mapping with dominance ratios |
| FALLBACK_V3_CANONICAL_TARGET_AUDIT.xlsx | Canonical exact-project targets |
| FALLBACK_V3_TUNING_RESULTS.xlsx | Tuning set backtest results |
| FALLBACK_V3_HOLDOUT_RESULTS.xlsx | Holdout set backtest results |
| FALLBACK_V3_ERROR_ANALYSIS.xlsx | Segmented error analysis |
| FALLBACK_V3_WORST_CASES.xlsx | Top 50 worst errors with root causes |
| FALLBACK_V3_IMPLEMENTATION_REPORT.md | This report |
