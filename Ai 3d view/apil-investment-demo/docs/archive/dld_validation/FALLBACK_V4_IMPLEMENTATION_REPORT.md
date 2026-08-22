# Fallback DLD Benchmark — V4 IMPLEMENTATION REPORT
**Generated:** 2026-08-18T23:20:31.816941

## 1. Canonical Sales Contamination Audit

- Properties tested: 1169
- Properties with non-sale transactions: 508
- Properties with median change: 53
- Properties with median change >5%: 44
- Properties with median change >10%: 35
- Properties whose decision changes: 9

## 2. V4 Configuration

```json
{
  "lookback_months": 24,
  "size_band_pct_default": 0.2,
  "min_transactions_area_fallback": 10,
  "min_unique_projects_area": 3,
  "max_project_concentration": 0.5,
  "outlier_method": "iqr_1.5",
  "property_type_filter": false,
  "sources_allowed": [
    "DLD_OFFICIAL",
    "DXBINTERACT",
    "OTHER_VERIFIED"
  ]
}
```

## 3. Holdout Accuracy Results

| Metric | Without Type Filter | With Type Filter | DLD_OFFICIAL_ONLY | Multi-Verified |
|--------|--------------------:|-----------------:|------------------:|---------------:|
| N | 182 | 182 | 125 | 182 |
| Median abs error | 11.46% | 11.62% | 10.79% | 11.46% |
| Mean abs error | 18.78% | 18.92% | 16.99% | 18.78% |
| P75 | 22.85% | 22.85% | 20.00% | 22.85% |
| P90 | 39.54% | 39.27% | 35.98% | 39.54% |
| Direction match | 52.7% | 52.7% | 53.6% | 52.7% |

## 4. Conservative Direction Precision

| Safety Margin | Classified N | Coverage % | Precision | FP Rate |
|---------------|-------------:|-----------:|----------:|--------:|
| 0% | 97 | 53.3% | 62.9% | 37.1% |
| 5% | 77 | 42.3% | 62.3% | 37.7% |
| 10% | 47 | 25.8% | 66.0% | 34.0% |
| 15% | 32 | 17.6% | 62.5% | 37.5% |

## 5. High-End Safety Gates

| Gate | Excluded N | Remaining Median Error | Remaining P90 |
|------|-----------:|----------------------:|--------------:|
| price_4M+ | 15 | 10.82% | 35.98% |
| price_6M+ | 8 | 11.11% | 37.84% |
| price_8M+ | 7 | 11.2% | 37.84% |
| size_2000+ | 7 | 11.2% | 37.84% |
| size_2500+ | 2 | 11.29% | 38.65% |
| 3BR+ | 13 | 10.82% | 38.65% |
| 4BR+ | 0 | 11.46% | 39.54% |

## 6. Level 2 Exact-Project Status-Broadened

- N: 225
- Median abs error: 10.00%
- P90: 33.85%

## 7. Audit Counters

| Counter | Value | Target |
|---------|-------|--------|
| NON_SALE_FALLBACK_TRANSACTION_USED | 0 | 0 |
| NON_SALE_CANONICAL_TARGET_TRANSACTION_USED | 108 | 0 |
| UNKNOWN_SOURCE_USED_IN_BENCHMARK | 0 | 0 |
| TARGET_PROJECT_LEAKAGE | 0 | 0 |
| TRAIN_TEST_PROJECT_LEAKAGE | 0 | 0 |
| AMBIGUOUS_SIZE_USED | 0 | 0 |
| AMBIGUOUS_AREA_MAPPING_USED | 0 | 0 |
| PROPERTY_TYPE_SOURCE_CONFLICT | 0 | 0 |
| STATUS_BROADENED_WITHOUT_LABEL | 0 | 0 |
| MISSING_SIZE_BENCHMARK_GENERATED | 0 | 0 |

## 8. Area Reliability

- **Arjan**: VALIDATED_CANDIDATE | N=8 | med_err=4.94% | P90=16.66% | dir=50.0%
- **Dubai Land Residence Complex**: VALIDATED_CANDIDATE | N=10 | med_err=5.35% | P90=29.62% | dir=60.0%
- **Dubai Hills Estate**: VALIDATED_CANDIDATE | N=8 | med_err=5.6% | P90=19.09% | dir=75.0%
- **Al Furjan**: VALIDATED_CANDIDATE | N=9 | med_err=6.12% | P90=17.89% | dir=44.4%
- **Jumeirah village circle**: VALIDATED_CANDIDATE | N=34 | med_err=9.94% | P90=26.1% | dir=52.9%
- **Dubai Sports City**: VALIDATED_CANDIDATE | N=12 | med_err=13.76% | P90=42.61% | dir=75.0%
- **Business Bay**: VALIDATED_CANDIDATE | N=26 | med_err=15.72% | P90=36.03% | dir=50.0%
- **Meydan City**: UNSAFE_DIRECTION_ACCURACY | N=8 | med_err=17.96% | P90=50.09% | dir=25.0%
- **Dubai Islands**: VALIDATED_CANDIDATE | N=9 | med_err=19.88% | P90=50.6% | dir=55.6%
- **Dubai Marina**: MARGINAL | N=9 | med_err=37.84% | P90=66.74% | dir=44.4%
- **Dubai Creek Harbour**: INSUFFICIENT_VALIDATION | N=4 | med_err=None% | P90=None% | dir=None%
- **Dubailand**: INSUFFICIENT_VALIDATION | N=1 | med_err=None% | P90=None% | dir=None%
- **Palm Jumeirah**: INSUFFICIENT_VALIDATION | N=4 | med_err=None% | P90=None% | dir=None%
- **Dubai Science Park**: INSUFFICIENT_VALIDATION | N=2 | med_err=None% | P90=None% | dir=None%
- **Rashid Yachts & Marina**: INSUFFICIENT_VALIDATION | N=4 | med_err=None% | P90=None% | dir=None%
- **Jumeirah Village Triangle**: INSUFFICIENT_VALIDATION | N=4 | med_err=None% | P90=None% | dir=None%
- **Al Satwa**: INSUFFICIENT_VALIDATION | N=2 | med_err=None% | P90=None% | dir=None%
- **Dubai Maritime City**: INSUFFICIENT_VALIDATION | N=1 | med_err=None% | P90=None% | dir=None%
- **Dubai Studio City**: INSUFFICIENT_VALIDATION | N=1 | med_err=None% | P90=None% | dir=None%
- **Jumeirah Lake Towers**: INSUFFICIENT_VALIDATION | N=2 | med_err=None% | P90=None% | dir=None%
- **Town Square Dubai**: INSUFFICIENT_VALIDATION | N=2 | med_err=None% | P90=None% | dir=None%
- **Sobha Hartland 2**: INSUFFICIENT_VALIDATION | N=1 | med_err=None% | P90=None% | dir=None%
- **Dubai Production City**: INSUFFICIENT_VALIDATION | N=3 | med_err=None% | P90=None% | dir=None%
- **International City Phase 2**: INSUFFICIENT_VALIDATION | N=1 | med_err=None% | P90=None% | dir=None%
- **Al Habtoor City**: INSUFFICIENT_VALIDATION | N=3 | med_err=None% | P90=None% | dir=None%
- **Dubai South**: INSUFFICIENT_VALIDATION | N=4 | med_err=None% | P90=None% | dir=None%
- **Dubai Water Canal**: INSUFFICIENT_VALIDATION | N=1 | med_err=None% | P90=None% | dir=None%
- **Downtown Dubai**: INSUFFICIENT_VALIDATION | N=1 | med_err=None% | P90=None% | dir=None%
- **Majan**: INSUFFICIENT_VALIDATION | N=3 | med_err=None% | P90=None% | dir=None%
- **Dubai International City**: INSUFFICIENT_VALIDATION | N=2 | med_err=None% | P90=None% | dir=None%
- **Ghaf Woods**: INSUFFICIENT_VALIDATION | N=1 | med_err=None% | P90=None% | dir=None%
- **Wasl Gate**: INSUFFICIENT_VALIDATION | N=2 | med_err=None% | P90=None% | dir=None%

## 9. Segment Analysis

- **area_Al Furjan**: N=9 | med_err=6.12% | P90=17.89% | dir=44.4%
- **area_Arjan**: N=8 | med_err=4.94% | P90=16.66% | dir=50.0%
- **area_Business Bay**: N=26 | med_err=15.72% | P90=36.03% | dir=50.0%
- **area_Dubai Hills Estate**: N=8 | med_err=5.6% | P90=19.09% | dir=75.0%
- **area_Dubai Islands**: N=9 | med_err=19.88% | P90=50.6% | dir=55.6%
- **area_Dubai Land Residence Complex**: N=10 | med_err=5.35% | P90=29.62% | dir=60.0%
- **area_Dubai Marina**: N=9 | med_err=37.84% | P90=66.74% | dir=44.4%
- **area_Dubai Sports City**: N=12 | med_err=13.76% | P90=42.61% | dir=75.0%
- **area_Jumeirah village circle**: N=34 | med_err=9.94% | P90=26.1% | dir=52.9%
- **area_Meydan City**: N=8 | med_err=17.96% | P90=50.09% | dir=25.0%
- **bedroom_1BR**: N=72 | med_err=11.2% | P90=39.54% | dir=50.0%
- **bedroom_2BR**: N=62 | med_err=10.28% | P90=44.23% | dir=59.7%
- **bedroom_3BR**: N=13 | med_err=22.29% | P90=42.61% | dir=46.2%
- **bedroom_Studio**: N=35 | med_err=10.82% | P90=29.62% | dir=48.6%
- **price_1–2M**: N=89 | med_err=8.62% | P90=31.54% | dir=55.1%
- **price_2–4M**: N=39 | med_err=19.09% | P90=44.23% | dir=48.7%
- **price_4–8M**: N=8 | med_err=33.61% | P90=123.01% | dir=25.0%
- **price_8M+**: N=7 | med_err=34.98% | P90=207.45% | dir=71.4%
- **price_< 1M**: N=39 | med_err=10.13% | P90=28.76% | dir=53.8%
- **size_1000–1500 sqft**: N=51 | med_err=8.61% | P90=42.56% | dir=52.9%
- **size_1500–2500 sqft**: N=17 | med_err=22.85% | P90=55.81% | dir=47.1%
- **size_600–1000 sqft**: N=72 | med_err=11.29% | P90=36.45% | dir=58.3%
- **size_< 600 sqft**: N=40 | med_err=10.78% | P90=29.62% | dir=47.5%
- **status_Offplan**: N=151 | med_err=11.53% | P90=38.65% | dir=51.0%
- **status_Ready**: N=31 | med_err=10.88% | P90=39.54% | dir=61.3%
- **type_APARTMENT**: N=82 | med_err=12.0% | P90=36.45% | dir=52.4%
- **type_UNKNOWN**: N=82 | med_err=10.77% | P90=41.47% | dir=54.9%
- **type_VILLA**: N=8 | med_err=20.2% | P90=44.23% | dir=0.0%

## 10. Production Status

**production_eligible: FALSE**

No production decisions, frontend, MASTER_FINAL, Qdrant, or raw DLD CSVs modified.

## 11. Files Generated

| File | Description |
|------|-------------|
| DLD_CANONICAL_SALES_CONTAMINATION_AUDIT.xlsx | Current vs sales-only canonical comparison |
| FALLBACK_V4_PROPERTY_TYPE_MAPPING.xlsx | DLD PROP_SB_TYPE_EN → normalized type mapping |
| FALLBACK_V4_TUNING_RESULTS.xlsx | Tuning set backtest results |
| FALLBACK_V4_HOLDOUT_RESULTS.xlsx | Holdout set backtest results |
| FALLBACK_V4_PRECISION_GATING.xlsx | Conservative direction precision by safety margin |
| FALLBACK_V4_SEGMENT_ELIGIBILITY.xlsx | Segment reliability classifications |
| FALLBACK_V4_AREA_RELIABILITY.xlsx | Area reliability classifications |
| FALLBACK_V4_LEVEL2_RESULTS.xlsx | Level 2 exact-project status-broadened results |
| FALLBACK_V4_IMPLEMENTATION_REPORT.md | This report |