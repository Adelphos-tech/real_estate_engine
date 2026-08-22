# PHASE 5 — CANONICAL SALES-ONLY MIGRATION + LEVEL 2 AUDIT
**Generated:** 2026-08-19T00:00:55.964740

## PART A — CANONICAL SALES-ONLY AUDIT

### Summary
- Properties tested: 1169
- Properties changed: 53
- Properties with decision changed: 9
- Median change >5%: 44
- Median change >10%: 35

### Audit Counters
- NON_SALE_PRESENT_IN_RAW_PROJECT_DATA: 508
- NON_SALE_ACTUALLY_USED_IN_SALES_ONLY_TARGET: 0
- SALES_ONLY_MANUAL_MEDIAN_MISMATCH: 0
- UNEXPECTED_SALES_MIGRATION_CHANGE: 0

### Known Property Regression
- Property 701 (Elvira): UNCHANGED | live=True | shadow=True | live_median=4000000.0 | shadow_median=4000000.0
- Property 3983 (Sapphire 32): UNCHANGED | live=False | shadow=False | live_median=None | shadow_median=None
- Property 3693 (Elvira): UNCHANGED | live=True | shadow=True | live_median=2500000.0 | shadow_median=2500000.0
- Property 4434 (Lime Gardens): UNCHANGED | live=True | shadow=True | live_median=2532500.0 | shadow_median=2640000.0
- Property 5319 (LIV Residence): UNCHANGED | live=True | shadow=True | live_median=1921000.0 | shadow_median=1921000.0
- Property 6956 (Cubix Residences): UNCHANGED | live=True | shadow=True | live_median=2352806.5 | shadow_median=2352806.5
- Property 7061 (azizi mina): UNCHANGED | live=False | shadow=False | live_median=2197859.995 | shadow_median=None
- Property 7546 (Helvetia Residences): UNCHANGED | live=True | shadow=True | live_median=1900000.0 | shadow_median=1900000.0
- Property 8057 (Binghatti Royale): UNCHANGED | live=False | shadow=False | live_median=2900000.0 | shadow_median=2900000.0
- Property 8201 (Marquise Square): UNCHANGED | live=False | shadow=False | live_median=None | shadow_median=None
- Property 3201 (Binghatti Nova): UNCHANGED | live=False | shadow=False | live_median=None | shadow_median=None

## PART B — LEVEL 2 VALIDATION

- N tested: 77
- Median abs error: 1.32%
- Mean abs error: 2.72%
- P75: 3.33%
- P90: 5.34%
- Median signed error: 0.0%
- Raw direction accuracy: 87.0%

### Conservative Direction Precision
| Margin | Classified N | Coverage % | Precision | FP Rate |
|--------|-------------:|-----------:|----------:|--------:|
| 5% | 62 | 80.5% | 88.7% | 11.3% |
| 10% | 46 | 59.7% | 97.8% | 2.2% |
| 15% | 34 | 44.2% | 97.1% | 2.9% |
| 20% | 29 | 37.7% | 96.6% | 3.4% |

### Status Pair Analysis
- Ready subject broadened: N=50, med_err=0.88%, P90=5.34%, dir=90.0%
- Offplan subject broadened: N=27, med_err=1.45%, P90=13.87%, dir=81.5%

## PART D — QDRANT COVERAGE AUDIT
- MASTER total properties: 2614
- Qdrant unique records: 4227
- Unique MASTER properties with Qdrant: 1290
- MASTER coverage pct: 49.3%
- QDRANT_PROPERTY_COUNT_OVER_MASTER_COUNT: 0

## PART E — FINAL RECOMMENDATIONS

### A. CANONICAL SALES-ONLY
**RECOMMENDATION: APPROVE with caveats**

Rationale:
- 53 of 1169 properties change (4.5%)
- Only 9 decisions change (0.8%)
- Manual median verification: SALES_ONLY_MANUAL_MEDIAN_MISMATCH = 0
- No unexpected changes in unaffected properties: UNEXPECTED_SALES_MIGRATION_CHANGE = 0
- Sales-only is objectively safer because mortgage/gift transactions do not reflect market prices.
- The 9 decision-changing properties must be manually reviewed before migration.

### B. LEVEL 2 EXACT-PROJECT STATUS-BROADENED
**RECOMMENDATION: CONDITIONAL APPROVAL for ANALYTICAL CONTEXT — NOT production signals**

- Raw direction accuracy: 87.0%
- Best conservative precision (10% margin): 97.8%
- At 5% margin: 88.7% precision with 80.5% coverage
- Level 2 achieves >=80% precision at 5% margin (88.7%) and >=95% at 10% margin (97.8%).
- However, the test set is only 77 properties (both same-status and broadened need >=3 tx).
- Ready properties show stronger reliability (90.0% direction) than Offplan (81.5%).
- RECOMMENDATION: Keep Level 2 as ANALYTICAL CONTEXT ONLY until sample size >200.

### Transaction-Count Thresholds
- min_3: N=77, med_err=1.32%, dir_match=87.0%
- min_5: N=43, med_err=0.74%, dir_match=93.0%
- min_10: N=9, med_err=1.45%, dir_match=88.9%
- min_15: N=4, med_err=1.79%, dir_match=100.0%

### Recency Proxy (Activity Level)
- High activity (broadened_tx >= 10): N=40, med_err=1.08%, dir_match=90.0%
- Low activity (broadened_tx < 10): N=37, med_err=1.32%, dir_match=83.8%

### C. AREA FALLBACK
**RECOMMENDATION: KEEP SHADOW**

- Median error ~11-12% is acceptable for research but not for investor-facing opportunity/avoid signals.
- Raw direction accuracy ~53% is below usable threshold.
- Conservative precision ~66% at 10% margin with 25.8% coverage is insufficient for production.
- DLD_OFFICIAL_ONLY shows promise (10.79% median error) but needs further validation.

## FILES GENERATED

| File | Description |
|------|-------------|
| CANONICAL_SALES_ONLY_FULL_AUDIT.xlsx | Complete audit of all 1,169 properties |
| CANONICAL_SALES_ONLY_53_CHANGED.xlsx | 53 properties with changed medians |
| CANONICAL_SALES_ONLY_9_DECISION_CHANGES.xlsx | 9 properties with decision changes |
| CANONICAL_SALES_ONLY_TRANSACTION_AUDIT.xlsx | Transaction-level detail |
| SALES_SEMANTICS_AUDIT.xlsx | GROUP_EN + PROCEDURE_EN classification |
| LEVEL2_STATUS_BROADENED_BACKTEST.xlsx | Level 2 backtest results |
| LEVEL2_STATUS_PAIR_ANALYSIS.xlsx | Level 2 by status direction |
| LEVEL2_PRECISION_GATING.xlsx | Level 2 conservative precision |
| LEVEL2_TX_COUNT_THRESHOLDS.xlsx | Level 2 transaction-count thresholds |
| LEVEL2_RECENCY_ANALYSIS.xlsx | Level 2 recency proxy analysis |