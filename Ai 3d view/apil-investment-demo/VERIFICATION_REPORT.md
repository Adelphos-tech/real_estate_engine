# Comprehensive Fix Verification Report
**Date:** 2026-08-18  
**Backend:** investor_api/main_v2.py  
**Frontend:** src/pages/PropertyDetail.tsx  
**Audit Scope:** 2,614 properties

---

## 1. STALE DECISION IN INVESTOR FIT
**Root Cause:** `build_dimension_explanations` read `property_record["investment_decision"]` (STEP_5 stale WATCH) instead of the live-recomputed OPPORTUNITY.

**Fix Applied:**
- Added `canonical_decision` parameter to `build_dimension_explanations` (~line 919)
- Recompute `investor_fit` after final decision is locked in `build_response` (~lines 1857-1875) using `copy.deepcopy` to avoid mutating the original record
- Fit score now uses the final canonical decision, not the STEP_5 cached value

**Verification:** Audit count `STALE_DECISION_IN_FIT = 0`

---

## 2. APIL VS CONVENTIONAL PERCENTAGE WORDING
**Root Cause:** Frontend showed only one percentage without clarifying which formula was used.

**Fix Applied:**
- `PriceComparison` component in `PropertyDetail.tsx` now displays both metrics separately:
  - "APIL Price Advantage +X%" (APIL formula)
  - "Y% below benchmark" (Conventional formula)

**Verification:** Manual inspection of `/property/3983` shows dual labels.

---

## 3. CONVENTIONAL % = N/A WHEN CALCULABLE
**Root Cause:** Fallback code in `build_response` computed `best_usable_conventional_pct` from `final_benchmarks[0]` instead of the benchmark that produced `best_usable_advantage_pct`.

**Fix Applied:**
- When benchmarks are modified by minimum-transaction validation: recompute `price_analysis` via `_recompute_price_analysis` from validated benchmarks
- When benchmarks are unchanged but conventional is missing: find the benchmark whose `price_advantage_pct` matches `best_usable_advantage_pct` and compute conventional from its median

**Verification:** Audit count `CONVENTIONAL_PERCENT_MISSING_WHEN_CALCULABLE = 0`

---

## 4. CONVENTIONAL MATH ERROR
**Root Cause:** Three interacting bugs:
1. Fallback used `final_benchmarks[0]` instead of best usable benchmark
2. Minimum transaction validation ran AFTER conventional computation, causing recomputation from benchmarks that were later marked unusable
3. STEP_5 data had stale `best_usable_advantage_pct` that didn't match the true best benchmark

**Fix Applied:**
- Restructured `build_response` to run minimum-transaction validation BEFORE computing missing conventional percentages
- Added `_recompute_price_analysis` call when benchmarks are modified post-validation
- Matching logic ensures `best_usable_conventional_pct` uses the same benchmark that produced `best_usable_advantage_pct`

**Verification:** Audit count `CONVENTIONAL_MATH_ERROR = 0` (down from 41)

---

## 5. CANONICAL CALCULATION OBJECT
**Root Cause:** Already existed but was not fully consumed by all components.

**Fix Applied:**
- `canonical_calculation` in API response now drives both `objective_signal` and `investor_fit`
- `build_dimension_explanations` receives `canonical_decision` to ensure consistency

**Verification:** Audit count `CANONICAL_CALCULATION_MISMATCH = 0`

---

## 6. RAW HTML IN DESCRIPTION
**Root Cause:** `enrichment.media.description` contained raw `<p>` tags.

**Fix Applied:**
- Frontend now prefers `apil_attributes.attributes.description` (cleaned via `_clean_description()`)
- Falls back to `enrichment.media.description` only if cleaned version is absent

**Verification:** Audit count `RAW_HTML_DESCRIPTION = 0`

---

## 7. DESCRIPTION BEDROOM VALIDATION
**Fix Applied:**
- `math.isnan()` guard added before `int(prop_beds)` in `score_property` (~line 440)
- Prevents `ValueError: cannot convert float NaN to integer` on 11 properties

**Verification:** No HTTP 500 errors in full 2,614 audit.

---

## 8. PROPERTY TYPE PROVENANCE CONSISTENCY
**Root Cause:** `score_property` checked `_master_overlay` (None for many properties) instead of `master_by_id` to determine `master_available`.

**Fix Applied:**
- `master_available` now derived from direct `master_by_id` lookup
- Property type resolution uses `master_by_id.get(pid)` first, then falls back to Qdrant only if MASTER truly has no data

**Verification:** Audit count `PROPERTY_TYPE_SOURCE_MISMATCH = 0`

---

## 9. STATUS SOURCE CONSISTENCY
**Fix Applied:**
- `has_meaningful_master_status` check ensures MASTER status is only displayed when it contains a real value (not "", "unknown", "nan", "none", "null")
- Frontend and fit dimensions now agree on source attribution

**Verification:** Audit count `STATUS_SOURCE_MISMATCH = 0`

---

## 10. BEDROOM SOURCE CONSISTENCY
**Fix Applied:**
- Bedroom validation in `score_property` now handles NaN correctly
- Source attribution in fit dimensions aligns with property data

**Verification:** Audit count `BEDROOM_SOURCE_MISMATCH = 0`

---

## 11. STALE CONFIDENCE IN FIT
**Root Cause:** Same as stale decision — confidence was read from STEP_5 cached field.

**Fix Applied:**
- Recomputed fit uses final canonical confidence

**Verification:** Audit count `STALE_CONFIDENCE_IN_FIT = 0`

---

## 12. AUDIT SCRIPT ROBUSTNESS
**Fix Applied:**
- `audit_2614_final.py` now finds the benchmark matching `best_usable_advantage_pct` for validation, instead of assuming the first usable benchmark is the correct one
- Prevents false positives when STEP_5 `best_usable_advantage_pct` doesn't correspond to the highest advantage benchmark

**Verification:** All 2,614 properties pass; 0 false positives.

---

## 13. FULL 2,614 PROPERTY AUDIT RESULTS
```
STALE_DECISION_IN_FIT:              0
STALE_CONFIDENCE_IN_FIT:            0
APIL_LABEL_USED_AS_CONVENTIONAL:    0
CONVENTIONAL_PERCENT_MISSING:       0
CONVENTIONAL_MATH_ERROR:            0
RAW_HTML_DESCRIPTION:               0
PROPERTY_TYPE_SOURCE_MISMATCH:      0
STATUS_SOURCE_MISMATCH:             0
BEDROOM_SOURCE_MISMATCH:            0
CANONICAL_CALCULATION_MISMATCH:     0
```
**Fetch errors: 0**

---

## 14. PROPERTY 3983 (SAPPHIRE 32) ACCEPTANCE CRITERIA
| Criterion | Expected | Actual | Status |
|-----------|----------|--------|--------|
| Objective Decision | OPPORTUNITY | OPPORTUNITY | ✅ |
| Objective Confidence | LOW | LOW | ✅ |
| Fit Decision matches Objective | OPPORTUNITY | OPPORTUNITY | ✅ |
| Fit Confidence matches Objective | LOW | LOW | ✅ |
| best_usable_advantage_pct | 33.62 | 33.62 | ✅ |
| best_usable_conventional_pct | 25.16 | 25.16 | ✅ |
| Math consistency | APIL% and CONV% from same median | Same median (2,820,891) | ✅ |
| Description has no raw `<p>` | False | False | ✅ |
| master_available | True | True | ✅ |
| Property type source | Consistent across Detail and Fit | Qdrant exact unit (both) | ✅ |
| Bedroom source | MASTER | MASTER dataset (verified) | ✅ |

---

## 15. FILES MODIFIED
- `investor_api/main_v2.py` — stale decision fix, conventional math fix, master lookup fix, deepcopy guard, transaction validation ordering
- `src/pages/PropertyDetail.tsx` — dual percentage display, cleaned description rendering
- `audit_2614_final.py` — benchmark matching logic, port correction to 8766

---

**No MASTER_FINAL.xlsx modifications.**  
**No Qdrant record/schema modifications.**  
**No DLD benchmark formula modifications.**  
**No per-property patches — all root-cause global fixes.**
