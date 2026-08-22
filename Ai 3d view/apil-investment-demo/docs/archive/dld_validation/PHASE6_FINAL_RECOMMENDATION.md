# PHASE 6 — FINAL CANONICAL SALES RECONCILIATION + TRUE LEVEL-2 TRIGGER BACKTEST
**Generated:** 2026-08-19T00:16:00.606279

## PART A — KNOWN PROPERTY RECONCILIATION

### Counters
- KNOWN_PROPERTY_FALSE_UNCHANGED_LABEL: 0
- KNOWN_PROPERTY_MEDIAN_REPORTING_MISMATCH: 1
- KNOWN_PROPERTY_USABLE_FLAG_MISMATCH: 0

### Known Properties Detail
| PID | Name | Live Exists | Shadow Exists | Live Median | Shadow Median | Benchmark Changed | Tx Set Changed | Decision Changed |
|-----|------|-------------|---------------|-------------|---------------|-------------------|----------------|------------------|
| 3201 | Binghatti Nova | False | False | nan | nan | False | False | False |
| 3693 | Elvira | True | True | 2500000.0 | 2500000.0 | False | False | False |
| 3983 | Sapphire 32 | False | False | nan | nan | False | False | False |
| 4434 | Lime Gardens | True | True | 2532500.0 | 2640000.0 | True | True | False |
| 5319 | LIV Residence | True | True | 1921000.0 | 1921000.0 | False | False | False |
| 6956 | Cubix Residences | True | True | 2352806.5 | 2352806.5 | False | False | False |
| 701 | Elvira | True | True | 4000000.0 | 4000000.0 | False | False | False |
| 7061 | azizi mina | True | False | 2197859.995 | nan | True | True | False |
| 7546 | Helvetia Residences | True | True | 1900000.0 | 1900000.0 | False | False | False |
| 8057 | Binghatti Royale | True | True | 2900000.0 | 2900000.0 | False | False | False |
| 8201 | Marquise Square | False | False | nan | nan | False | False | False |

### Property 4434 Root Cause
- Property 4434 (Lime Gardens) live median: 2532500.0
- Property 4434 shadow median: 2640000.0
- Full transaction detail exported to PHASE6_PROPERTY_4434_ROOT_CAUSE.xlsx

### Property 3983 Root Cause
- Property 3983 (Sapphire 32) live usable: False
- Property 3983 live benchmark: None
- Property 3983 live tx count: 0
- Property 3983 evidence level: None
- Property 3983 insufficient reason: No DLD transactions found for project 'Sapphire 32'

### Duplicate Transaction ID Audit
- DUPLICATE_TRANSACTION_ID_COUNT: 15010
- DUPLICATE_TRANSACTION_ID_WITH_DIFFERENT_GROUP_COUNT: 22
- DUPLICATE_ROWS_IN_SALES_BENCHMARK: 1
- TOTAL_UNIQUE_TRANSACTION_IDS: 16151
- TOTAL_COMPOSITE_KEYS: 16173
- DUPLICATE_COMPOSITE_KEYS: 15030
- Composite transaction identity implemented for audit safety.

## PART B — 9 DECISION CHANGE REVIEW

- Property 3618 (Talia Residences): BORDERLINE_THRESHOLD_CHANGE | live=True -> shadow=False | manual_median=1560000.0 engine=1560000.0 match=True | reason: Sales-only reduced tx count from 18 to 1, falling below usable threshold
- Property 1609 (Avelon Boulevard): CORRECT_SALES_ONLY_CHANGE | live=True -> shadow=False | manual_median=nan engine=nan match=True | reason: All transactions were non-sale (mortgage/gifts); sales-only yields no benchmark
- Property 7282 (48 Parkside): BORDERLINE_THRESHOLD_CHANGE | live=True -> shadow=False | manual_median=1700000.0 engine=1700000.0 match=True | reason: Sales-only reduced tx count from 3 to 1, falling below usable threshold
- Property 918 (Sunridge): BORDERLINE_THRESHOLD_CHANGE | live=True -> shadow=False | manual_median=1345944.0 engine=1345944.0 match=True | reason: Sales-only reduced tx count from 33 to 2, falling below usable threshold
- Property 6182 (Chic Tower): CORRECT_SALES_ONLY_CHANGE | live=True -> shadow=False | manual_median=nan engine=nan match=True | reason: All transactions were non-sale (mortgage/gifts); sales-only yields no benchmark
- Property 5646 (Condor Golf Links 18): BORDERLINE_THRESHOLD_CHANGE | live=True -> shadow=False | manual_median=1580120.0 engine=1580120.0 match=True | reason: Sales-only reduced tx count from 14 to 1, falling below usable threshold
- Property 7427 (Cloud Tower): BORDERLINE_THRESHOLD_CHANGE | live=True -> shadow=False | manual_median=2350000.0 engine=2350000.0 match=True | reason: Sales-only reduced tx count from 3 to 1, falling below usable threshold
- Property 7170 (AG Tower): CORRECT_SALES_ONLY_CHANGE | live=True -> shadow=False | manual_median=nan engine=nan match=True | reason: All transactions were non-sale (mortgage/gifts); sales-only yields no benchmark
- Property 546 (Seapoint): CORRECT_SALES_ONLY_CHANGE | live=True -> shadow=False | manual_median=nan engine=nan match=True | reason: All transactions were non-sale (mortgage/gifts); sales-only yields no benchmark

## PART C — TRUE LEVEL 2 TRIGGER-FAITHFUL VALIDATION

- Temporal validation observations: 44
- Simulated holdout observations: 409
- Total observations: 453
- Unique projects: 234
- Median abs error: 4.83%
- P75: 10.29%
- P90: 19.33%
- Direction match rate: 69.8%

### Conservative Precision with 95% Binomial CI
| Margin | Classified N | Coverage | Precision | 95% CI | FP Rate | Opp FP Rate |
|--------|-------------:|---------:|----------:|-------:|--------:|------------:|
| 0% | 444 | 98.0% | 61.0% | [56.4%, 65.5%] | 39.0% | 24.3% |
| 5% | 302 | 66.7% | 78.5% | [73.5%, 82.7%] | 21.5% | 11.9% |
| 10% | 203 | 44.8% | 86.7% | [81.3%, 90.7%] | 13.3% | 6.4% |
| 15% | 129 | 28.5% | 89.1% | [82.6%, 93.4%] | 10.9% | 4.7% |

### Status Pair Analysis (True Trigger)
- Ready broadened: N=66, projects=33, med_err=6.74%, P90=19.67%, dir=74.2% [62.6-83.3]
- Offplan broadened: N=387, projects=201, med_err=4.33%, P90=19.16%, dir=69.0% [64.2-73.4]

### Transaction Count Thresholds
- min_3: N=453, projects=234, med_err=4.83%, P90=19.33%, dir=69.8%
- min_5: N=409, projects=226, med_err=4.46%, P90=19.33%, dir=69.2%
- min_8: N=306, projects=187, med_err=4.95%, P90=19.46%, dir=68.0%
- min_10: N=259, projects=163, med_err=4.84%, P90=19.16%, dir=70.3%

## PART D — CANONICAL SALES MIGRATION RECOMMENDATION

**APPROVE_SALES_ONLY_MIGRATION**

- All 9 manual medians match engine: True
- No false UNCHANGED labels: True
- No usable flag mismatches: True
- Property 4434 reconciled (status fallback): True
- Duplicate TIDs handled safely with composite keys: True
- All 9 decision changes explained: 9 reviewed

## PART E — LEVEL 2 RECOMMENDATION

**LEVEL2_CONTEXT_ONLY**

- True-trigger observations: 453
- True-trigger unique projects: 234
- Best precision: 89.1%
- Best opportunity FP rate: 4.7%

## PART F — AREA FALLBACK
**SHADOW ONLY — production_eligible = false**

## PART G — RENTAL ROI
**NOT IMPLEMENTED**

## CONFIRMATIONS
- Frontend: UNCHANGED
- MASTER_FINAL.xlsx: UNCHANGED
- Qdrant records/schema: UNCHANGED
- Raw DLD files: UNCHANGED
- Production canonical calculations: UNCHANGED (shadow analysis only)
- Rental yield: NOT IMPLEMENTED

## FILES GENERATED

| File | Description |
|------|-------------|
| PHASE6_KNOWN_PROPERTY_RECONCILIATION.xlsx | Explicit-field reconciliation of 11 known properties |
| PHASE6_PROPERTY_4434_ROOT_CAUSE.xlsx | Every transaction for property 4434 with inclusion flags |
| PHASE6_9_DECISION_CHANGE_REVIEW.xlsx | Deep review of all decision-changing properties |
| PHASE6_9_DECISION_CHANGE_TRANSACTIONS.xlsx | Transaction-level detail for 9 properties |
| PHASE6_DUPLICATE_TRANSACTION_ID_AUDIT.xlsx | Duplicate TID audit with composite keys |
| LEVEL2_TRUE_TRIGGER_TEMPORAL_BACKTEST.xlsx | Temporal validation results |
| LEVEL2_TRUE_TRIGGER_SIMULATED_HOLDOUT.xlsx | Simulated holdout results |
| LEVEL2_TRUE_TRIGGER_PRECISION.xlsx | Conservative precision with binomial CIs |
| LEVEL2_TRUE_TRIGGER_STATUS_PAIR.xlsx | Ready vs Offplan analysis |
| LEVEL2_TRUE_TRIGGER_THRESHOLD_ANALYSIS.xlsx | Tx count threshold analysis |