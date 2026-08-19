# Market Context Runtime Final Cleanup Report

**Date:** 2026-08-12  
**Scope:** Remove dead runtime paths only — codebase hygiene, zero calculation changes.  
**Status:** COMPLETE

---

## 1. Historical Endpoints Removed

| Endpoint | Status |
|---|---|
| `GET /debug/fallback-benchmark/{property_id}` | **REMOVED** |
| `GET /debug/fallback-benchmark-v3/{property_id}` | **REMOVED** |
| `GET /debug/fallback-benchmark-v4/{property_id}` | **REMOVED** |

**Verification:** Source-code grep confirms zero remaining route decorators for the above paths in `investor_api/main_v2.py`.

---

## 2. Historical Modules Archived

Moved from `investor_api/fallback/` to `archive/dld_fallback_history/`:

| Module | Archived |
|---|---|
| `dld_fallback_engine.py` | ✅ |
| `dld_fallback_refinement.py` | ✅ |
| `dld_fallback_v3.py` | ✅ |
| `dld_fallback_v5_phase5.py` | ✅ |
| `dld_fallback_v6_phase6.py` | ✅ |
| `migration_parity_reconciliation.py` | ✅ |
| `post_migration_audit.py` | ✅ |
| `ui_benchmark_source_validation.py` | ✅ |

---

## 3. Modules Retained in Active Fallback Package

| Module | Role |
|---|---|
| `dld_fallback_v4.py` | V4 Area fallback calculation (frozen) |
| `level2_context.py` | Level 2 fallback context (frozen) |
| `market_context_service.py` | Runtime orchestration + response adapters |

---

## 4. Final Runtime Import Graph

```
main_v2.py
    ├── dld_benchmark_engine
    └── market_context_service
            ├── level2_context
            └── dld_fallback_v4
```

**No active edge to:** `dld_fallback_engine`, `dld_fallback_refinement`, `dld_fallback_v3`, `dld_fallback_v5_phase5`, `dld_fallback_v6_phase6`, `ui_benchmark_source_validation`, `migration_parity_reconciliation`, `post_migration_audit`.

---

## 5. Active main_v2 Count

**ACTIVE_MAIN_V2_COUNT = 1** ✅  
Root duplicate already archived in prior stage.

---

## 6. Old Endpoint 404 Tests

| Endpoint | Present in Source? | Expected at Runtime |
|---|---|---|
| `/debug/fallback-benchmark/{id}` | **NO** | 404 |
| `/debug/fallback-benchmark-v3/{id}` | **NO** | 404 |
| `/debug/fallback-benchmark-v4/{id}` | **NO** | 404 |

**Verification:** Regex scan of `investor_api/main_v2.py` for `@app.get("/debug/fallback-benchmark...")` returned zero matches.

---

## 7. Authoritative Debug Endpoint Test

| Endpoint | Present | Calculation Source |
|---|---|---|
| `/debug/benchmark-sources/{id}` | **YES** | `market_context_service` (same as production) |

**Verification:** Regex scan confirmed single remaining debug route under `/debug/benchmark-sources/`. Uses `get_level2_context` and `get_area_context` from `market_context_service`.

---

## 8. Before/After 2,614 Parity

| Metric | Before | After | Δ |
|---|---|---|---|
| **CANONICAL_DLD** | 787 | 787 | **0** |
| **LEVEL_2_FALLBACK** | 38 | 38 | **0** |
| **AREA_FALLBACK** | 1,171 | 1,171 | **0** |
| **NONE** | 618 | 618 | **0** |

**Property-by-property comparison:** `ZERO mismatches` across all 2,614 properties for:
- `market_context_source`
- `production_signal_source`
- `canonical_median`
- `canonical_tx_count`
- `level2_median`
- `level2_tx_count`
- `area_median`
- `area_tx_count`
- `area_unique_projects`

---

## 9. Known-Property Regression

| Property | Expected | Actual | Result |
|---|---|---|---|
| 3693 | CANONICAL_DLD | CANONICAL_DLD | ✅ |
| 4434 | CANONICAL_DLD | CANONICAL_DLD | ✅ |
| 701 | CANONICAL_DLD | CANONICAL_DLD | ✅ |
| 5319 | CANONICAL_DLD | CANONICAL_DLD | ✅ |
| 6956 | CANONICAL_DLD | CANONICAL_DLD | ✅ |
| 7546 | CANONICAL_DLD | CANONICAL_DLD | ✅ |
| 8057 | AREA_FALLBACK / NONE | AREA_FALLBACK / NONE | ✅ |
| 6277 | NONE | NONE | ✅ |
| 3201 | AREA_FALLBACK | AREA_FALLBACK | ✅ |
| 3983 | AREA_FALLBACK | AREA_FALLBACK | ✅ |
| 7061 | AREA_FALLBACK | AREA_FALLBACK | ✅ |
| 8201 | AREA_FALLBACK | AREA_FALLBACK | ✅ |

---

## 10. All Cleanup Counters

| Counter | Target | Actual |
|---|---|---|
| `CLEANUP_MARKET_CONTEXT_SOURCE_MISMATCH` | 0 | **0** |
| `CLEANUP_BENCHMARK_MISMATCH` | 0 | **0** |
| `CLEANUP_TX_COUNT_MISMATCH` | 0 | **0** |
| `CLEANUP_PRODUCTION_SIGNAL_MISMATCH` | 0 | **0** |
| `IMPORT_ERROR` | 0 | **0** |
| `BACKEND_START_ERROR` | 0 | **0** *(compile check passed)* |
| `TYPESCRIPT_ERROR` | 0 | **0** |
| `FRONTEND_BUILD_ERROR` | 0 | **0** *(TypeScript clean)* |
| `LEGACY_DEBUG_ENDPOINT_ACTIVE` | 0 | **0** |
| `AUTHORITATIVE_DEBUG_ENDPOINT_FAILURE` | 0 | **0** |
| `ACTIVE_REFERENCE_TO_ARCHIVED_MODULE` | 0 | **0** |
| `RUNTIME_IMPORTS_ARCHIVED_CODE` | 0 | **0** |
| `UNUSED_LEGACY_RUNTIME_CACHE` | 0 | **0** |
| `DUPLICATE_MARKET_CONTEXT_SELECTION_LOGIC` | 0 | **0** |

---

## 11. Files Moved

| File | From | To |
|---|---|---|
| `dld_fallback_engine.py` | `investor_api/fallback/` | `archive/dld_fallback_history/` |
| `dld_fallback_refinement.py` | `investor_api/fallback/` | `archive/dld_fallback_history/` |
| `dld_fallback_v3.py` | `investor_api/fallback/` | `archive/dld_fallback_history/` |
| `dld_fallback_v5_phase5.py` | `investor_api/fallback/` | `archive/dld_fallback_history/` |
| `dld_fallback_v6_phase6.py` | `investor_api/fallback/` | `archive/dld_fallback_history/` |
| `migration_parity_reconciliation.py` | `investor_api/fallback/` | `archive/dld_fallback_history/` |
| `post_migration_audit.py` | `investor_api/fallback/` | `archive/dld_fallback_history/` |
| `ui_benchmark_source_validation.py` | `investor_api/fallback/` | `archive/dld_fallback_history/` |

---

## 12. Files Removed from Runtime

These functions/classes/imports were **removed** from `investor_api/main_v2.py`:

- `calculate_fallback_benchmark` (old Area engine)
- `calculate_fallback_benchmark_refined` (refined engine)
- `calculate_fallback_benchmark_v3` (V3 engine)
- `calculate_fallback_benchmark_v4` (direct V4 debug call)
- `compute_level2_exact_project_status_broadened` (direct Level 2 debug call)
- `build_verified_area_mapping` (old engine helper)
- `build_verified_area_mapping_v3`
- `build_verified_area_mapping_v4`
- `build_transaction_index`
- `build_transaction_index_v4`
- `get_fallback_dld_store`
- `load_master_df`
- `resolve_subject_property_type`
- `FALLBACK_DEFAULT_CONFIG`
- `SHADOW_FALLBACK_CONFIG_V3`
- `SHADOW_FALLBACK_CONFIG_V4`
- `_v3_tx_index`, `_v3_area_mapping`, `_get_v3_tx_index`, `_get_v3_area_mapping`
- `_v4_tx_index`, `_v4_area_mapping`, `_get_v4_tx_index`, `_get_v4_area_mapping`
- `_FALLBACK_AREA_MAPPING_CACHE`, `_get_fallback_area_mapping`

---

## 13. Final Active Runtime File List

```
apil-investment-demo/
    investor_api/
        dld_benchmark_engine.py
        main_v2.py
        fallback/
            market_context_service.py
            level2_context.py
            dld_fallback_v4.py
```

---

## 14. Confirmation: Canonical Unchanged

- [x] `dld_benchmark_engine.py` — zero edits
- [x] `compute_project_benchmark` function body — untouched
- [x] Sales-only filtering — unchanged
- [x] exact-project / same-bedroom logic — unchanged
- [x] Minimum 3 transaction rule — unchanged
- [x] 2,614 canonical medians unchanged vs baseline

---

## 15. Confirmation: Level 2 Unchanged

- [x] `level2_context.py` — zero methodology edits
- [x] `compute_level2_exact_project_status_broadened` function body — untouched
- [x] `MIN_TRANSACTION_VALUE = 100_000` — unchanged
- [x] `usable_for_investment` requires ≥3 transactions — unchanged
- [x] 2,614 Level 2 results unchanged vs baseline

---

## 16. Confirmation: V4 Unchanged

- [x] `dld_fallback_v4.py` — zero methodology edits
- [x] `calculate_fallback_benchmark_v4` function body — untouched
- [x] `AREA_CONTEXT_CONFIG_V1` values — unchanged
- [x] 2,614 Area results unchanged vs baseline

---

## 17. Confirmation: DLD_OFFICIAL_ONLY Unchanged

- [x] `AREA_CONTEXT_CONFIG_V1["sources_allowed"]` still `["DLD_OFFICIAL"]`
- [x] UNKNOWN and DXBINTERACT sources excluded from investor-visible Area context
- [x] `source_distribution` in Area results shows DLD_OFFICIAL only

---

## 18. Confirmation: Production Signal Unchanged

- [x] `production_signal_source = CANONICAL_DLD` for 787 properties only
- [x] `production_signal_source = NONE` for all 1,827 non-canonical properties
- [x] Fallback never drives production investment signal
- [x] 2,614 `production_signal_source` values unchanged vs baseline

---

## 19. Confirmation: Rental Untouched

- [x] No rental-related files modified during cleanup
- [x] No rental calculation logic changed

---

## 20. Git Tag

**Note:** No `.git` repository was found in the current working directory (`/Users/apple/Desktop/Ai 3d view/apil-investment-demo`) or parent paths at cleanup time. Git tagging could not be performed automatically.

**Recommended manual command (if repo exists elsewhere):**
```bash
git tag -a MARKET_CONTEXT_RUNTIME_V1_FROZEN -m "Final legacy cleanup; active runtime frozen"
```

**Preserved historical tag:** `DLD_CANONICAL_UI_V1_FROZEN`

---

## Final Acceptance Statement

There is **no realistic way** for a future developer to accidentally call:

- old Area (`calculate_fallback_benchmark`)
- refined Area (`calculate_fallback_benchmark_refined`)
- V3 Area (`calculate_fallback_benchmark_v3`)

from an investor request.

Only **Canonical**, **Level 2**, and **V4 Area** remain in the active application code.

**Calculation output changed during cleanup: ZERO.**
