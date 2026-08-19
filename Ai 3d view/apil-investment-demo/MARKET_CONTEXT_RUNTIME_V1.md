# Market Context Runtime V1

**Date:** 2026-08-12  
**Status:** ACTIVE  
**Tag:** `MARKET_CONTEXT_UI_V1_FROZEN` → `MARKET_CONTEXT_RUNTIME_V1`

---

## 1. Purpose

Single-document reference for the active market-context calculation stack. No legacy engine should be reachable from an investor request.

---

## 2. Active File List

| File | Role |
|---|---|
| `investor_api/dld_benchmark_engine.py` | Canonical DLD benchmark (frozen) |
| `investor_api/fallback/level2_context.py` | Level 2 fallback context (frozen) |
| `investor_api/fallback/dld_fallback_v4.py` | V4 Area fallback calculation (frozen) |
| `investor_api/fallback/market_context_service.py` | Runtime orchestration + response adapters |
| `investor_api/main_v2.py` | API layer only |
| `src/data/api.ts` | Frontend TypeScript contracts |
| `src/pages/PropertyDetail.tsx` | Frontend display |

---

## 3. Runtime Flow

```
MASTER subject facts
       ↓
Canonical DLD  (compute_project_benchmark)
       ↓
Level 2 context  (level2_context.compute_level2_exact_project_status_broadened)
       ↓
V4 Area context  (dld_fallback_v4.calculate_fallback_benchmark_v4)
       ↓
market_context_service.select_market_context()
       ↓
main_v2.py  /properties/{id}
       ↓
PropertyDetail.tsx
```

---

## 4. Hierarchy

```
if canonical usable (≥3 same-project, same-bedroom sales):
    market_context_source = CANONICAL_DLD
    production_signal_source = CANONICAL_DLD
elif Level 2 usable (≥3 same-project, same-bedroom, status-broadened):
    market_context_source = LEVEL_2_FALLBACK
    production_signal_source = NONE
elif V4 Area eligible (≥10 area transactions, ≥3 unique projects, concentration ≤50%):
    market_context_source = AREA_FALLBACK
    production_signal_source = NONE
else:
    market_context_source = NONE
    production_signal_source = NONE
```

---

## 5. Area Context Config

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

## 6. Identity Mapping

| Tier | benchmark_method | benchmark_tier | is_fallback | production_eligible | validation_status |
|---|---|---|---|---|---|
| Canonical | CANONICAL_DLD | LEVEL_1 | false | true | VERIFIED_PRODUCTION |
| Level 2 | DLD_FALLBACK | LEVEL_2 | true | false | VALIDATED_CONTEXT_ONLY |
| Area | DLD_FALLBACK | LEVEL_3/4 | true | false | CONTEXT_ONLY |

---

## 7. Caches

| Cache | Module | Build Trigger |
|---|---|---|
| V4 transaction index | `market_context_service` | First Area context request |
| V4 area mapping | `market_context_service` | First Area context request |
| MASTER df | `market_context_service` | First Area context request |

---

## 8. What Was Archived

| Item | Location |
|---|---|
| Root-level duplicate `main_v2.py` | `../archive/legacy_backend/` |
| Old fallback engines (v1-v3, refined, v5, v6) | `archive/dld_fallback_history/` |
| Audit scripts (`migration_parity_reconciliation.py`, `post_migration_audit.py`, `ui_benchmark_source_validation.py`) | `archive/dld_fallback_history/` |
| One-off diagnostic scripts | `tools/archive/` |
| Historical validation reports | `docs/archive/dld_validation/` |

## 9. Active Debug Endpoint

Only one debug endpoint remains in the active backend:

- `GET /debug/benchmark-sources/{property_id}` — returns canonical, Level 2, and V4 Area calculations using the **same runtime** as production (`market_context_service`).

Removed endpoints (return 404):
- `GET /debug/fallback-benchmark/{property_id}`
- `GET /debug/fallback-benchmark-v3/{property_id}`
- `GET /debug/fallback-benchmark-v4/{property_id}`

---

## 10. Constraints (Frozen)

- Canonical methodology: unchanged
- Sales-only filtering: unchanged
- exact-project / same-bedroom logic: unchanged
- Minimum 3 transaction rule: unchanged
- APIL / conventional formulas: unchanged
- Decision thresholds: unchanged
- MASTER_FINAL.xlsx: read-only
- Qdrant: read-only
- Raw DLD CSVs: read-only
- Rental logic: untouched
