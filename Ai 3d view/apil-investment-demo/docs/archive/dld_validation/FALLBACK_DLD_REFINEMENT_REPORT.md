# Fallback DLD Benchmark — REFINEMENT REPORT
**Generated:** 2026-08-18T18:59:54.065623

## Executive Summary

This report documents the refined shadow fallback benchmark methodology.

| Metric | Original | Holdout |
|--------|----------|---------|
| Median abs error | 34.00% | 34.07% |
| Mean abs error | 55.21% | 50.45% |
| P75 | 61.35% | 54.98% |
| P90 | 125.51% | 118.84% |
| Coverage | 1057 | 296 |

## Best Parameters (from sensitivity analysis on tuning sample)

```json
{
  "lookback_months": 12,
  "size_band_pct_default": 0.1,
  "min_transactions_area_fallback": 20,
  "min_unique_projects_area": 2,
  "max_project_concentration": 0.4,
  "ppsf_outlier_iqr_multiplier": 1.5,
  "outlier_method": "iqr_1.5",
  "property_type_filter": false
}
```

## Size Unit Detection

The refined engine uses multi-method size unit detection:

1. **SOURCE_DECLARED_SQM** — raw_size < 20 (physically impossible as sqft)
2. **SOURCE_DECLARED_SQFT** — raw_size > 5000 (impossibly large as sqm)
3. **AREA_DOMINANT_SQM/SQFT** — per-area-bedroom-status statistics
4. **PRICE_CROSS_CHECK** — implied PPSF reasonableness
5. **BEDROOM_RANGE** — typical Dubai unit size ranges
6. **AMBIGUOUS** — if none of the above resolve, transaction is excluded

Ambiguous transactions are EXCLUDED from PPSF fallback calculations.

## Confidence Score/Label Fix

Canonical mapping:

| Score | Label |
|-------|-------|
| ≥ 80 | high |
| 50–79 | medium |
| 20–49 | low |
| < 20 | very_low |

**Mismatches found:** 0 (target: 0)

## Parameter Sensitivity Results (Tuning Sample)

### recency
| Value | N | Median Error | P90 |
|-------|---|--------------|-----|
| 6 | 48 | 39.50% | 244.41% |
| 12 | 48 | 39.28% | 242.33% |
| 18 | 48 | 39.28% | 241.28% |
| 24 | 48 | 39.28% | 240.73% |
| 36 | 48 | 39.28% | 240.73% |

### size_band
| Value | N | Median Error | P90 |
|-------|---|--------------|-----|
| 0.1 | 46 | 35.38% | 248.22% |
| 0.15 | 47 | 37.49% | 247.30% |
| 0.2 | 47 | 39.12% | 243.40% |
| 0.25 | 48 | 39.28% | 240.73% |
| 0.3 | 48 | 38.70% | 239.83% |

### min_tx
| Value | N | Median Error | P90 |
|-------|---|--------------|-----|
| 5 | 49 | 39.28% | 240.73% |
| 8 | 48 | 39.28% | 240.73% |
| 10 | 47 | 39.28% | 240.73% |
| 15 | 43 | 39.28% | 131.12% |
| 20 | 41 | 36.10% | 131.12% |
| 30 | 40 | 36.10% | 197.35% |

### min_unique_projects
| Value | N | Median Error | P90 |
|-------|---|--------------|-----|
| 2 | 48 | 39.28% | 240.73% |
| 3 | 46 | 39.50% | 240.73% |
| 4 | 46 | 39.50% | 240.73% |
| 5 | 44 | 39.50% | 240.73% |

### max_concentration
| Value | N | Median Error | P90 |
|-------|---|--------------|-----|
| 0.4 | 48 | 39.28% | 240.73% |
| 0.5 | 48 | 39.28% | 240.73% |
| 0.6 | 48 | 39.28% | 240.73% |

### outlier
| Value | N | Median Error | P90 |
|-------|---|--------------|-----|
| none | 49 | 39.38% | 240.73% |
| iqr_1.5 | 48 | 39.28% | 240.73% |
| iqr_2.0 | 48 | 39.32% | 240.73% |
| mad | 48 | 39.33% | 240.73% |

## Property Type Filter Backtest

- Without filter: median=35.24%, coverage=40
- With filter: median=35.24%, coverage=40
- Decision: DO NOT APPLY

## Holdout Segmented Backtest Results

### area_Arjan
- N: 19
- Median abs error: 23.81%
- Mean abs error: 58.07%
- P75: 133.91%
- P90: 172.84%
- Median signed error: 13.16%

### area_Business Bay
- N: 25
- Median abs error: 42.52%
- Mean abs error: 64.21%
- P75: 63.23%
- P90: 192.07%
- Median signed error: 13.31%

### area_Dubai Creek Harbour
- N: 10
- Median abs error: 43.77%
- Mean abs error: 32.14%
- P75: 53.78%
- P90: 55.99%
- Median signed error: -11.77%

### area_Dubai Hills Estate
- N: 18
- Median abs error: 36.33%
- Mean abs error: 58.53%
- P75: 60.46%
- P90: 158.97%
- Median signed error: 25.80%

### area_Dubai Islands
- N: 14
- Median abs error: 66.60%
- Mean abs error: 74.03%
- P75: 97.23%
- P90: 132.42%
- Median signed error: 66.60%

### area_Dubai Land Residence Complex
- N: 23
- Median abs error: 48.03%
- Mean abs error: 56.51%
- P75: 76.52%
- P90: 121.83%
- Median signed error: 48.03%

### area_Dubai South
- N: 13
- Median abs error: 30.08%
- Mean abs error: 31.75%
- P75: 45.31%
- P90: 53.56%
- Median signed error: 7.87%

### area_Jumeirah village circle
- N: 53
- Median abs error: 24.98%
- Mean abs error: 38.06%
- P75: 45.04%
- P90: 85.18%
- Median signed error: 1.47%

### area_Meydan City
- N: 10
- Median abs error: 40.08%
- Mean abs error: 42.87%
- P75: 60.18%
- P90: 102.96%
- Median signed error: 23.54%

### bedroom_1BR
- N: 101
- Median abs error: 22.96%
- Mean abs error: 29.86%
- P75: 43.64%
- P90: 53.20%
- Median signed error: -6.61%

### bedroom_2BR
- N: 106
- Median abs error: 40.08%
- Mean abs error: 53.81%
- P75: 79.68%
- P90: 123.96%
- Median signed error: 36.82%

### bedroom_3BR
- N: 38
- Median abs error: 77.75%
- Mean abs error: 100.42%
- P75: 134.96%
- P90: 286.78%
- Median signed error: 77.75%

### bedroom_Studio
- N: 49
- Median abs error: 27.48%
- Mean abs error: 28.57%
- P75: 40.57%
- P90: 54.23%
- Median signed error: -27.48%

### price_1–2M
- N: 134
- Median abs error: 33.85%
- Mean abs error: 40.62%
- P75: 53.56%
- P90: 87.89%
- Median signed error: 16.60%

### price_2–4M
- N: 67
- Median abs error: 42.37%
- Mean abs error: 58.22%
- P75: 79.68%
- P90: 135.94%
- Median signed error: 29.03%

### price_4–8M
- N: 23
- Median abs error: 40.97%
- Mean abs error: 81.16%
- P75: 121.69%
- P90: 192.07%
- Median signed error: 30.99%

### price_8M+
- N: 10
- Median abs error: 225.92%
- Mean abs error: 213.05%
- P75: 302.24%
- P90: 647.73%
- Median signed error: 225.92%

### price_< 1M
- N: 62
- Median abs error: 25.59%
- Mean abs error: 25.66%
- P75: 38.20%
- P90: 45.31%
- Median signed error: -21.79%

### size_1000–1500 sqft
- N: 87
- Median abs error: 40.08%
- Mean abs error: 51.09%
- P75: 78.91%
- P90: 118.84%
- Median signed error: 37.85%

### size_1500–2500 sqft
- N: 43
- Median abs error: 60.91%
- Mean abs error: 80.73%
- P75: 133.91%
- P90: 150.75%
- Median signed error: 60.91%

### size_2500+ sqft
- N: 10
- Median abs error: 302.24%
- Mean abs error: 278.08%
- P75: 349.39%
- P90: 647.73%
- Median signed error: 302.24%

### size_600–1000 sqft
- N: 100
- Median abs error: 20.77%
- Mean abs error: 26.72%
- P75: 41.48%
- P90: 53.20%
- Median signed error: -2.38%

### size_< 600 sqft
- N: 56
- Median abs error: 27.48%
- Mean abs error: 27.93%
- P75: 40.87%
- P90: 54.23%
- Median signed error: -26.56%

### status_Offplan
- N: 243
- Median abs error: 34.07%
- Mean abs error: 48.15%
- P75: 55.99%
- P90: 109.68%
- Median signed error: 7.69%

### status_Ready
- N: 53
- Median abs error: 33.85%
- Mean abs error: 61.00%
- P75: 54.25%
- P90: 133.91%
- Median signed error: 17.52%

### type_nan
- N: 296
- Median abs error: 34.07%
- Mean abs error: 50.45%
- P75: 54.98%
- P90: 118.84%
- Median signed error: 9.51%

## Area Reliability Classification

- **Al Furjan**: RELIABLE_AREA | N=7 | med_err=18.0% | P90=43.2%
- **Town Square Dubai**: RELIABLE_AREA | N=9 | med_err=21.4% | P90=55.0%
- **Arjan**: RELIABLE_AREA | N=19 | med_err=23.8% | P90=172.8%
- **Jumeirah village circle**: RELIABLE_AREA | N=53 | med_err=25.0% | P90=85.2%
- **Dubai Marina**: MARGINAL_AREA | N=7 | med_err=25.4% | P90=56.4%
- **Dubai South**: MARGINAL_AREA | N=13 | med_err=30.1% | P90=53.6%
- **Dubai Hills Estate**: MARGINAL_AREA | N=18 | med_err=36.3% | P90=159.0%
- **Jumeirah Village Triangle**: MARGINAL_AREA | N=6 | med_err=36.6% | P90=177.3%
- **Rashid Yachts & Marina**: MARGINAL_AREA | N=7 | med_err=36.8% | P90=84.5%
- **Dubai Motor City**: MARGINAL_AREA | N=9 | med_err=39.0% | P90=66.0%
- **Meydan City**: MARGINAL_AREA | N=10 | med_err=40.1% | P90=103.0%
- **Business Bay**: MARGINAL_AREA | N=25 | med_err=42.5% | P90=192.1%
- **Dubai Creek Harbour**: MARGINAL_AREA | N=10 | med_err=43.8% | P90=56.0%
- **Downtown Dubai**: MARGINAL_AREA | N=5 | med_err=46.3% | P90=647.7%
- **Dubai Sports City**: MARGINAL_AREA | N=8 | med_err=47.8% | P90=118.8%
- **Dubai Land Residence Complex**: MARGINAL_AREA | N=23 | med_err=48.0% | P90=121.8%
- **Palm Jumeirah**: MARGINAL_AREA | N=5 | med_err=49.3% | P90=302.2%
- **Dubai Islands**: UNRELIABLE_AREA | N=14 | med_err=66.6% | P90=132.4%

## Worst-Case Root Cause Analysis (Top 100)

- **OTHER**: 83
- **AREA_TOO_HETEROGENEOUS**: 10
- **LUXURY_MIX**: 5
- **SIZE_UNIT_ERROR**: 1
- **PROJECT_CONCENTRATION**: 1

## Production Status

**production_eligible: FALSE**

The fallback engine remains in SHADOW MODE. No production decisions, frontend, MASTER_FINAL, Qdrant, or raw DLD CSVs have been modified.

## Files Generated

| File | Description |
|------|-------------|
| FALLBACK_DLD_REFINED_BACKTEST.xlsx | Per-property holdout backtest results |
| FALLBACK_DLD_SIZE_UNIT_AUDIT.xlsx | Transaction-level size unit detection |
| FALLBACK_DLD_AREA_RELIABILITY.xlsx | Per-area reliability classification |
| FALLBACK_DLD_GRID_SEARCH.xlsx | Parameter sensitivity on tuning sample |
| FALLBACK_DLD_WORST_CASES.xlsx | Top 100 worst errors with root causes |
| FALLBACK_DLD_REFINEMENT_REPORT.md | This report |
