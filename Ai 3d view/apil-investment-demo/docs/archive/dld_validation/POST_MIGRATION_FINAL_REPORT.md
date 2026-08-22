# CANONICAL DLD SALES-ONLY POST-MIGRATION AUDIT
**Generated:** 2026-08-19T00:25:01.917654

## SUMMARY
- Total properties recalculated: 2614
- Usable canonical evidence before migration: 1169
- Usable canonical evidence after migration: 787
- Properties that lost usable evidence: 382
- Properties that gained usable evidence: 0
- Properties with changed median: 485
- Properties with changed decision: 382

## AUDIT COUNTERS
- NON_SALE_TRANSACTION_USED_IN_CANONICAL: 0
- DUPLICATE_IDENTICAL_SALE_ROW_USED: 0
- UNKNOWN_TRANSACTION_TYPE_USED: 0
- BEDROOM_MISMATCH_USED: 0
- FUZZY_PROJECT_USED_AS_EXACT: 0
- MIN_TX_RULE_VIOLATION: 0
- STALE_BENCHMARK_AFTER_SALES_RECALCULATION: 0
- STALE_DECISION_AFTER_SALES_RECALCULATION: 0
- STALE_CONFIDENCE_AFTER_SALES_RECALCULATION: 0
- OBJECTIVE_SIGNAL_CANONICAL_MISMATCH: 0
- FIT_DECISION_CANONICAL_MISMATCH: 0
- MEDIAN_MATH_ERROR: 0
- APIL_MATH_ERROR: 0
- CONVENTIONAL_MATH_ERROR: 0

## 9 DECISION-CHANGE PROPERTIES
- Property 3618 (Talia Residences): tx_count=1, median=1560000.0, usable=False, evidence=EXACT_PROJECT_SAME_BEDROOM_EVIDENCE, version=CANONICAL_DLD_SALES_ONLY_V1, non_sale_removed=48
- Property 1609 (Avelon Boulevard): tx_count=0, median=nan, usable=False, evidence=NO_SAME_BEDROOM_EVIDENCE, version=None, non_sale_removed=30
- Property 7282 (48 Parkside): tx_count=1, median=1700000.0, usable=False, evidence=EXACT_PROJECT_SAME_BEDROOM_EVIDENCE, version=CANONICAL_DLD_SALES_ONLY_V1, non_sale_removed=20
- Property 918 (Sunridge): tx_count=2, median=1345944.0, usable=False, evidence=EXACT_PROJECT_SAME_BEDROOM_EVIDENCE, version=CANONICAL_DLD_SALES_ONLY_V1, non_sale_removed=49
- Property 6182 (Chic Tower): tx_count=0, median=nan, usable=False, evidence=NO_SAME_BEDROOM_EVIDENCE, version=None, non_sale_removed=5
- Property 5646 (Condor Golf Links 18): tx_count=1, median=1580120.0, usable=False, evidence=EXACT_PROJECT_SAME_BEDROOM_EVIDENCE, version=CANONICAL_DLD_SALES_ONLY_V1, non_sale_removed=131
- Property 7427 (Cloud Tower): tx_count=1, median=2350000.0, usable=False, evidence=EXACT_PROJECT_SAME_BEDROOM_EVIDENCE, version=CANONICAL_DLD_SALES_ONLY_V1, non_sale_removed=77
- Property 7170 (AG Tower): tx_count=0, median=nan, usable=False, evidence=NO_SAME_BEDROOM_EVIDENCE, version=None, non_sale_removed=120
- Property 546 (Seapoint): tx_count=0, median=nan, usable=False, evidence=NO_SAME_BEDROOM_EVIDENCE, version=None, non_sale_removed=47

## 11 KNOWN REGRESSION PROPERTIES
- Property 3201 (Binghatti Nova): tx_count=0, median=nan, usable=False, evidence=NO_SAME_BEDROOM_EVIDENCE, version=None, non_sale_removed=2
- Property 3693 (Elvira): tx_count=9, median=2500000.0, usable=True, evidence=EXACT_PROJECT_SAME_BEDROOM_EVIDENCE, version=CANONICAL_DLD_SALES_ONLY_V1, non_sale_removed=6
- Property 3983 (Sapphire 32): tx_count=0, median=nan, usable=False, evidence=None, version=None, non_sale_removed=0
- Property 4434 (Lime Gardens): tx_count=9, median=2640000.0, usable=True, evidence=EXACT_PROJECT_SAME_BEDROOM_EVIDENCE, version=CANONICAL_DLD_SALES_ONLY_V1, non_sale_removed=17
- Property 5319 (LIV Residence): tx_count=3, median=1921000.0, usable=True, evidence=EXACT_PROJECT_SAME_BEDROOM_EVIDENCE, version=CANONICAL_DLD_SALES_ONLY_V1, non_sale_removed=0
- Property 6956 (Cubix Residences): tx_count=6, median=2352806.5, usable=True, evidence=EXACT_PROJECT_SAME_BEDROOM_EVIDENCE, version=CANONICAL_DLD_SALES_ONLY_V1, non_sale_removed=0
- Property 701 (Elvira): tx_count=8, median=4000000.0, usable=True, evidence=EXACT_PROJECT_SAME_BEDROOM_EVIDENCE, version=CANONICAL_DLD_SALES_ONLY_V1, non_sale_removed=6
- Property 7061 (azizi mina): tx_count=0, median=nan, usable=False, evidence=NO_SAME_BEDROOM_EVIDENCE, version=None, non_sale_removed=4
- Property 7546 (Helvetia Residences): tx_count=27, median=1900000.0, usable=True, evidence=EXACT_PROJECT_SAME_BEDROOM_EVIDENCE, version=CANONICAL_DLD_SALES_ONLY_V1, non_sale_removed=0
- Property 8057 (Binghatti Royale): tx_count=1, median=2900000.0, usable=False, evidence=EXACT_PROJECT_SAME_BEDROOM_EVIDENCE, version=CANONICAL_DLD_SALES_ONLY_V1, non_sale_removed=43
- Property 8201 (Marquise Square): tx_count=0, median=nan, usable=False, evidence=None, version=None, non_sale_removed=0

## CONFIRMATIONS
- Raw DLD files: UNCHANGED
- MASTER_FINAL.xlsx: UNCHANGED
- Qdrant records/schema: UNCHANGED
- Frontend: UNCHANGED
- Level 2: context-only (production_eligible = false)
- Area fallback: shadow-only (production_eligible = false)
- Rental yield: NOT IMPLEMENTED

## FILES GENERATED

| File | Description |
|------|-------------|
| POST_MIGRATION_FULL_AUDIT.xlsx | Full 2,614 property audit |
| POST_MIGRATION_9_DECISION_CHANGES.xlsx | 9 decision-change properties |
| POST_MIGRATION_11_REGRESSION.xlsx | 11 known regression properties |