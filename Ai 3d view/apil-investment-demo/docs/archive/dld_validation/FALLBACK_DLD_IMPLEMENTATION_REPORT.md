# Fallback DLD Benchmark Implementation Report
**Generated:** 2026-08-18T18:08:44.557749

## Coverage Summary

| Metric | Count |
|--------|-------|
| Total MASTER properties | 2614 |
| Fallback eligible | 2154 (82.4%) |
| Fallback not eligible | 460 |

## Fallback Level Distribution

- **AREA_SAME_BEDROOM_SIZE_ADJUSTED_EVIDENCE**: 1967 (75.2%)
- **NO_VERIFIED_AREA_MAPPING**: 275 (10.5%)
- **AREA_SAME_BEDROOM_EVIDENCE**: 167 (6.4%)
- **NO_VERIFIED_FALLBACK_EVIDENCE**: 115 (4.4%)
- **AMBIGUOUS_BEDROOM_NO_FALLBACK**: 54 (2.1%)
- **EXACT_PROJECT_STATUS_BROADENED_EVIDENCE**: 20 (0.8%)
- **MISSING_BEDROOM_NO_FALLBACK**: 11 (0.4%)
- **NON_DUBAI_DLD_NOT_APPLICABLE**: 5 (0.2%)

## Exclusion Reasons

- **NO_VERIFIED_AREA_MAPPING**: 275
- **AMBIGUOUS_BEDROOM_NO_FALLBACK**: 54
- **INSUFFICIENT_FINAL_TRANSACTIONS_1_vs_8**: 24
- **INSUFFICIENT_FINAL_TRANSACTIONS_4_vs_8**: 21
- **INSUFFICIENT_FINAL_TRANSACTIONS_2_vs_8**: 18
- **NO_SAME_BEDROOM_TRANSACTIONS_IN_AREA**: 18
- **INSUFFICIENT_FINAL_TRANSACTIONS_7_vs_8**: 12
- **MISSING_BEDROOM**: 11
- **INSUFFICIENT_FINAL_TRANSACTIONS_5_vs_8**: 10
- **INSUFFICIENT_FINAL_TRANSACTIONS_3_vs_8**: 9
- **NON_DUBAI_DLD_NOT_APPLICABLE**: 5
- **INSUFFICIENT_FINAL_TRANSACTIONS_6_vs_8**: 3

## Verified Area Mapping

Total verified mappings: 56

| MASTER Area | DLD Area | Confidence | Supporting Projects |
|-------------|----------|------------|---------------------|
| jumeirah village circle | JUMEIRAH VILLAGE CIRCLE | high | 200 |
| business bay | BUSINESS BAY | high | 88 |
| arjan | ARJAN | high | 69 |
| dubai land residence complex | DUBAI LAND RESIDENCE COMPLEX | high | 68 |
| dubai hills estate | HADAEQ SHEIKH MOHAMMED BIN RASHID | high | 56 |
| dubai creek harbour | DUBAI CREEK HARBOUR | high | 50 |
| dubai islands | PALM DEIRA | high | 39 |
| dubai south | DUBAI SOUTH | high | 35 |
| dubai motor city | MOTOR CITY | high | 32 |
| al furjan | AL FURJAN | high | 28 |
| dubai marina | DUBAI MARINA | high | 27 |
| dubai sports city | DUBAI SPORTS CITY | high | 26 |
| town square dubai | AL YELAYISS 2 | high | 26 |
| jumeirah village triangle | JUMEIRAH VILLAGE TRIANGLE | high | 23 |
| meydan city | HORIZON | high | 21 |
| al jadaf waterfront | SAMA AL JADAF | high | 20 |
| palm jumeirah | PALM JUMEIRAH | high | 19 |
| majan | MAJAN | high | 16 |
| jebel ali | DOWN TOWN JABAL ALI | high | 14 |
| sobha hartland 2 | BUKADRA | high | 14 |
| jumeirah lake towers | JUMEIRAH LAKES TOWERS | high | 13 |
| rashid yachts marina | MADINAT DUBAI ALMELAHEYAH | high | 13 |
| dubai production city | DUBAI PRODUCTION CITY | high | 13 |
| downtown dubai | BURJ KHALIFA | high | 13 |
| dubai science park | DUBAI SCIENCE PARK | high | 12 |
| dubai design district | ZAABEEL SECOND | high | 11 |
| dubai harbour | DUBAI HARBOUR | high | 10 |
| dubai maritime city | DUBAI MARITIME CITY | medium | 9 |
| dubai studio city | DUBAI STUDIO CITY | medium | 8 |
| emaar south | EMAAR SOUTH | medium | 7 |
| sheikh zayed road | TRADE CENTER SECOND | medium | 6 |
| dubai industrial city | DUBAI INDUSTRIAL CITY | medium | 6 |
| expo city | MADINAT AL MATAAR | medium | 6 |
| dubailand | WADI AL SAFA 5 | medium | 6 |
| sobha one | RAS AL KHOR INDUSTRIAL FIRST | medium | 5 |
| dubai water canal | AL WASL | medium | 5 |
| jumeirah garden city | AL SATWA | medium | 5 |
| difc | ZAABEEL FIRST | medium | 4 |
| international city phase 2 | INTERNATIONAL CITY PH 2 & 3 | medium | 4 |
| wasl gate | JABAL ALI FIRST | medium | 3 |
| madinat jumeirah living | UM SUQAIM THIRD | medium | 3 |
| dubai media city | TECOM SITE A | medium | 3 |
| emaar beachfront | DUBAI HARBOUR | medium | 3 |
| مدينة دبي الرياضية | DUBAI SPORTS CITY | medium | 3 |
| liwan square | LIWAN | medium | 3 |
| discovery gardens | JABAL ALI FIRST | medium | 3 |
| al habtoor city | BUSINESS BAY | medium | 3 |
| dubai international city | INTERNATIONAL CITY PH 2 & 3 | medium | 3 |
| ghaf woods | WADI AL SAFA 4 | medium | 3 |
| al satwa | AL SATWA | medium | 3 |
| city walk | DUBAI WATER CANAL | low | 2 |
| jumeirah heights | JUMEIRAH HEIGHTS | low | 2 |
| al barari | AL BARARI | low | 2 |
| dubai investments park | DUBAI INVESTMENT PARK FIRST | low | 2 |
| nad al sheba | NAD AL SHEBA GARDENS | low | 2 |
| the valley | PALM DEIRA | low | 1 |

## Backtest Results (vs Exact-Project Evidence)

Properties backtested: 1057

| Metric | Value |
|--------|-------|
| Median Absolute % Error | 34.00% |
| Mean Absolute % Error | 55.21% |
| P25 | 14.02% |
| P75 | 61.35% |
| P90 | 125.51% |
| Worst | 891.83% |


## Methodology Notes

- All fallback calculations use real DLD transactions only.
- PPSF (price per sqft) is used for area-level comparables.
- Exact-project transactions are EXCLUDED from area fallback during backtest.
- IQR-based outlier removal is applied to PPSF values.
- Area mapping is verified using exact-project matched properties.
- Fallback benchmarks are SHADOW ONLY — not connected to production decisions.

## Configuration

```json
{
  "min_transactions_area_fallback": 8,
  "size_band_pct_default": 0.25,
  "max_project_concentration": 0.6,
  "lookback_months": 36,
  "min_unique_projects_area": 2,
  "ppsf_outlier_iqr_multiplier": 1.5
}
```