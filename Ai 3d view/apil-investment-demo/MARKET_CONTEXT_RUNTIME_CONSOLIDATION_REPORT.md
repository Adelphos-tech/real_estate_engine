# Market Context Runtime Consolidation Report

**Date:** 2026-08-12  
**Scope:** Wire latest validated runtime methods (V4 Area, extracted Level 2), then safely remove old runtime paths.  
**Status:** `FALLBACK_MARKET_CONTEXT_UI_VERIFIED` → `MARKET_CONTEXT_RUNTIME_V1`

---

## 1. Old Area Runtime Function

**Function:** `calculate_fallback_benchmark()`  
**File:** `investor_api/fallback/dld_fallback_engine.py`  
**Status:** **ARCHIVED** — no longer called by investor-visible API

Default config:
- lookback = 36 months
- size band = ±25%
- min transactions = 8
- max project concentration = 60%

---

## 2. New Area Runtime Function

**Function:** `calculate_fallback_benchmark_v4()`  
**File:** `investor_api/fallback/dld_fallback_v4.py`  
**Status:** **ACTIVE** — called exclusively via `market_context_service.get_area_context()`

---

## 3. Exact Area Runtime Config

```python
AREA_CONTEXT_CONFIG_V1 = {
    "version": "AREA_CONTEXT_V4_DLD_OFFICIAL_V1",
    "lookback_months": 24,
    "size_band_pct_default": 0.20,
    "min_transactions_area_fallback": 10,
    "min_unique_projects_area": 3,
    "max_project_concentration": 0.50,
    "ppsf_outlier_iqr_multiplier": 1.5,
    "outlier_method": "iqr_1.5",
    "property_type_filter": False,
    "sale_only": True,
    "sources_allowed": ["DLD_OFFICIAL"],
}
```

---

## 4. DLD_OFFICIAL_ONLY Is Used

**Yes.** `sources_allowed = ["DLD_OFFICIAL"]` in `AREA_CONTEXT_CONFIG_V1`.  
UNKNOWN and DXBINTERACT sources are excluded from investor-visible Area fallback.  
Multi-source V4 remains available for research/debug via direct module call.

---

## 5. Property 6277 — Binghatti Emerald (Old vs New)

| Metric | Old Engine | New V4 Runtime |
|---|---|---|
| **eligible** | True | **False** |
| **benchmark** | AED 2.40M | **N/A** |
| **tx count** | 40 | **N/A** |
| **rejection reason** | — | `EXCESSIVE_PROJECT_CONCENTRATION:55.6%` |

**Explanation:** V4 correctly rejects 6277 because more than 50% of comparables come from a single project (Luma Park Views). The old engine allowed up to 60%. Latest validated safeguards have priority over coverage.

**Final selection:** `market_context_source = NONE`, `production_signal_source = NONE`

---

## 6. Property 8057 — Binghatti Royale (Old vs New)

| Metric | Old Engine | New V4 Runtime |
|---|---|---|
| **Level 2 eligible** | False (1 tx) | False (1 tx) |
| **Area eligible** | True | True |
| **Area benchmark** | AED 3.55M | **AED 3.29M** |
| **Area tx count** | 27 | **18** |
| **Area unique projects** | 19 | **16** |

**Explanation:** V4 uses 24-month lookback (vs 36 months) and stricter size band (±20% vs ±25%), yielding fewer but more comparable transactions. The estimate is slightly lower but more defensible.

**Final selection:** `market_context_source = AREA_FALLBACK`, `production_signal_source = NONE`

---

## 7. Full Before vs After Coverage (2,614 Properties)

| Context Tier | Before (Old Engine) | After (V4 Runtime) | Δ |
|---|---|---|---|
| **Canonical DLD** | 785 | **785** | 0 |
| **Level 2 Fallback** | 361 | **40** | **−321** |
| **Area Fallback** | 1,082 | **1,171** | **+89** |
| **No Context** | 386 | **618** | **+232** |
| **Total** | **2,614** | **2,614** | 0 |

**Key insight:**
- Level 2 dropped from 361 → 40 because the old code was displaying **invalid** Level 2 results with 1–2 transactions. The new runtime enforces `usable_for_investment == True` (≥3 transactions).
- The 321 properties that lost invalid Level 2 mostly gained valid Area fallback or fell to No Context.
- No Context increased by 232 because V4's stricter safeguards (50% concentration limit, 24-month lookback, ±20% size band) reject some properties that the old engine accepted.

---

## 8. All Stage A Safety Counters

| Counter | Target | Actual |
|---|---|---|
| `CANONICAL_CHANGED` | 0 | **0** |
| `LEVEL2_METHODOLOGY_CHANGED` | 0 | **0** |
| `AREA_V4_INELIGIBLE_DISPLAYED` | 0 | **0** |
| `OLD_AREA_ENGINE_USED_IN_RUNTIME` | 0 | **0** |
| `REFINED_AREA_ENGINE_USED_IN_RUNTIME` | 0 | **0** |
| `V3_AREA_ENGINE_USED_IN_RUNTIME` | 0 | **0** |
| `FALLBACK_USED_FOR_PRODUCTION_SIGNAL` | 0 | **0** |
| `FALLBACK_USED_FOR_CANONICAL_APIL` | 0 | **0** |
| `FALLBACK_USED_FOR_CANONICAL_CONVENTIONAL` | 0 | **0** |
| `UNKNOWN_SOURCE_USED_IN_AREA_CONTEXT` | 0 | **0** |
| `NON_SALE_USED_IN_AREA_CONTEXT` | 0 | **0** |
| `AREA_PROJECT_CONCENTRATION_VIOLATION` | 0 | **0** |
| `AREA_MIN_PROJECT_VIOLATION` | 0 | **0** |
| `AREA_MIN_TX_VIOLATION` | 0 | **0** |
| `AREA_LOOKBACK_VIOLATION` | 0 | **0** |
| `DEBUG_RUNTIME_AREA_MISMATCH` | 0 | **0** |
| `DEBUG_RUNTIME_LEVEL2_MISMATCH` | 0 | **0** |

---

## 9. New Runtime Files

| File | Role |
|---|---|
| `investor_api/fallback/market_context_service.py` | Single orchestration layer for all market context |
| `investor_api/fallback/level2_context.py` | Extracted Level 2 runtime (frozen methodology) |

---

## 10. Legacy Modules Archived

| File | Action | Reason |
|---|---|---|
| `../investor_api/main_v2.py` (root duplicate) | Moved to `../archive/legacy_backend/` | Duplicate, inactive since Aug 16 |
| One-off diagnostic scripts (`diagnose_*.py`, `test_area_api*.py`, `compute_area_counts.py`) | Moved to `tools/archive/` | One-off diagnostics |
| Generated output files (`diagnose_*.txt`, `area_counts_output.txt`, etc.) | Moved to `tools/archive/` | Generated artifacts |
| Historical reports (`FALLBACK_*_REPORT.md`, `PHASE*_FINAL_RECOMMENDATION.md`, etc.) | Moved to `docs/archive/dld_validation/` | Historical validation artifacts |

---

## 11. Legacy Modules Retained (Not Deleted)

| File | Classification | Why Retained |
|---|---|---|
| `dld_fallback_engine.py` | HISTORICAL_AUDIT_ONLY | Used by debug endpoints `/debug/fallback-benchmark/*` (Stage B later) |
| `dld_fallback_refinement.py` | HISTORICAL_AUDIT_ONLY | Same — debug endpoint references |
| `dld_fallback_v3.py` | HISTORICAL_AUDIT_ONLY | Same — debug endpoint references |
| `dld_fallback_v5_phase5.py` | HISTORICAL_AUDIT_ONLY | Same |
| `dld_fallback_v6_phase6.py` | HISTORICAL_AUDIT_ONLY | Same |
| `ui_benchmark_source_validation.py` | HISTORICAL_AUDIT_ONLY | Same — debug endpoint + audit runner references |
| `migration_parity_reconciliation.py` | HISTORICAL_AUDIT_ONLY | Audit script references |
| `post_migration_audit.py` | HISTORICAL_AUDIT_ONLY | Audit script references |

**Note:** These modules remain on disk but are no longer imported by the investor-visible runtime path. Only `market_context_service`, `level2_context`, and `dld_fallback_v4` are in the active runtime chain.

---

## 12. Old Debug Endpoints

| Endpoint | Status |
|---|---|
| `/debug/fallback-benchmark/{id}` | **Retained** (uses old engine, but not investor-visible) |
| `/debug/fallback-benchmark-v3/{id}` | **Retained** |
| `/debug/fallback-benchmark-v4/{id}` | **Retained** |
| `/debug/benchmark-sources/{id}` | **Retained** (uses same runtime as normal API) |

---

## 13. Authoritative main_v2.py

**File:** `/Users/apple/Desktop/Ai 3d view/apil-investment-demo/investor_api/main_v2.py`  
**Verification:** Frontend calls `127.0.0.1:8000` which is served by this file. Root-level duplicate moved to `../archive/legacy_backend/`.

---

## 14. Confirmation: Only One Active main_v2.py

**ACTIVE_MAIN_V2_COUNT = 1** ✅  
Root duplicate archived.

---

## 15. Root Scripts Archived

One-off diagnostic scripts and generated outputs moved to `tools/archive/`:
- `diagnose_area_fallback.py`
- `diagnose_area_fast.py`
- `diagnose_6277_8057.py`
- `compute_area_counts.py`
- `test_area_api.py`
- `test_area_api2.py`
- `test_v4_6277.py`
- All `.txt` output files

---

## 16. Historical Reports Archived

Historical validation reports moved to `docs/archive/dld_validation/`:
- `FALLBACK_DLD_IMPLEMENTATION_REPORT.md`
- `FALLBACK_DLD_REFINEMENT_REPORT.md`
- `FALLBACK_V3_IMPLEMENTATION_REPORT.md`
- `FALLBACK_V4_IMPLEMENTATION_REPORT.md`
- `PHASE5_FINAL_RECOMMENDATION.md`
- `PHASE6_FINAL_RECOMMENDATION.md`
- `MIGRATION_PARITY_REPORT.md`
- `POST_MIGRATION_FINAL_REPORT.md`
- `SHADOW_FALLBACK_COMPLETE_REPORT.md`

---

## 17. Runtime Import Graph

```
main_v2.py
    └── market_context_service
            ├── level2_context
            │       └── dld_benchmark_engine._DLD_STORE
            └── dld_fallback_v4
                    └── build_transaction_index_v4
                    └── build_verified_area_mapping_v4
```

**No imports from:** `dld_fallback_engine`, `dld_fallback_refinement`, `dld_fallback_v3`, `ui_benchmark_source_validation` in the investor-visible runtime path.

---

## 18. Cleanup Regression Counters

| Counter | Target | Actual |
|---|---|---|
| `IMPORT_ERROR` | 0 | **0** |
| `BACKEND_START_ERROR` | 0 | **0** |
| `FRONTEND_BUILD_ERROR` | 0 | **0** |
| `KNOWN_PROPERTY_REGRESSION_ERROR` | 0 | **0** |
| `CLEANUP_CONTEXT_RESULT_MISMATCH` | 0 | **0** |

Verification: `npx tsc --noEmit` passed with zero errors.

---

## 19. Confirmation: Canonical Unchanged

- [x] `dld_benchmark_engine.py` — zero edits
- [x] Sales-only filtering — unchanged
- [x] exact-project / same-bedroom logic — unchanged
- [x] Minimum 3 transaction rule — unchanged
- [x] APIL / conventional formulas — unchanged
- [x] Decision thresholds — unchanged

---

## 20. Confirmation: Fallback Does Not Drive Production Signal

- [x] `production_signal_source = CANONICAL_DLD` for 785 properties only
- [x] `production_signal_source = NONE` for all 1,829 non-canonical properties
- [x] Fallback (Level 2 or Area) never drives investment signal

---

## 21. Confirmation: Rental Untouched

- [x] No rental-related files modified

---

## Summary

The production runtime now has **ONE obvious path**:

```
dld_benchmark_engine (canonical)
        ↓
market_context_service (orchestration)
        ├── level2_context (Level 2)
        └── dld_fallback_v4 (Area)
        ↓
main_v2.py (API)
        ↓
PropertyDetail.tsx (UI)
```

No old/refined/V3 fallback engine remains reachable from an investor request.  
All 17 Stage A safety counters are **0**.  
All 5 Stage B regression counters are **0**.

**Freeze authorized: `MARKET_CONTEXT_RUNTIME_V1`**
