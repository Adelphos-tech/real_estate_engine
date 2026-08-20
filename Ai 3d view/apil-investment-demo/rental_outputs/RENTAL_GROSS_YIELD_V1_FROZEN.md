# RENTAL GROSS YIELD V1 — FROZEN

**Freeze Date**: 2026-08-20
**Status**: **FROZEN — DO NOT MODIFY WITHOUT EXPLICIT RE-APPROVAL**
**Git Tag**: `RENTAL_GROSS_YIELD_V1_FROZEN`
**Preceded By**: `RENTAL_GROSS_YIELD_HTTP_SHADOW_V1_VERIFIED`, `GROSS_RENTAL_YIELD_V1_UI_VERIFIED`

---

## 1. FINAL RUNTIME IDENTITY

| Component | Version |
|-----------|---------|
| Rent estimate | `RENTAL_MARKET_RENT_V1` |
| Gross yield | `GROSS_RENTAL_YIELD_V1` |

These versions are FROZEN. Any methodology change requires a new version marker (V2), full re-audit, and explicit re-approval.

---

## 2. FROZEN METHODOLOGY

### Scope
- **Ready properties only** — Offplan and Unknown are NOT evaluated
- Status resolution uses the SAME production path as `/properties/{id}`: `_build_apil_attributes()` → MASTER `unit_status` > `_resolve_property_status()`

### Tier Hierarchy (deterministic: R1 > R2 > R3 > R4 > NONE)

| Tier | Requirements | Min Comparables |
|------|-------------|-----------------|
| R1 | Exact project + same bedroom + similar size (±25%) | 5 |
| R2 | Exact project + similar size (±25%) | 8 |
| R3 | Same area + same bedroom + similar size (±25%) | 10 |
| R4 | Same area + similar size (±25%) | 20 |
| NONE | Insufficient evidence | — |

### Estimator

| Parameter | Value |
|-----------|-------|
| Estimator | RECENCY_WEIGHTED_MEDIAN_ANNUAL_RENT |
| Half-life | 12 months (365 days) |
| Outlier filter | IQR 1.5 |
| Size band | ±25% |
| Contract strategy | NEW_PLUS_RENEWED |
| Min historical comparables | 5 |
| Calibration | GLOBAL_MULTIPLICATIVE ×0.96 |
| As-of date | 2026-08-09 (latest date in data) |

**No area-specific calibration. No project-specific calibration. No ML.**

---

## 3. GROSS YIELD FORMULA — FROZEN

```
gross_rental_yield_pct = annual_rent_estimate_aed / MASTER_current_price_aed × 100
```

**Denominator**: `MASTER_FINAL.xlsx` → `current_price_aed` ONLY.

NOT used as denominator:
- DLD sales benchmark
- Area benchmark
- Qdrant price
- Fallback property value

---

## 4. RENT RANGE — FROZEN

| Field | Description |
|-------|-------------|
| `annual_rent_p25_aed` | Calibrated weighted 25th percentile |
| `annual_rent_estimate_aed` | Calibrated weighted median |
| `annual_rent_p75_aed` | Calibrated weighted 75th percentile |
| `gross_yield_p25_pct` | P25 rent / MASTER price × 100 |
| `gross_rental_yield_pct` | Median rent / MASTER price × 100 |
| `gross_yield_p75_pct` | P75 rent / MASTER price × 100 |

All use the exact same MASTER asking price.

**Interval guarantee**: P25 ≤ estimate ≤ P75 by construction (weighted percentiles of the same distribution). Verified: 0 violations across 300 estimates.

---

## 5. STATUS RULES — FROZEN

| Status | Action |
|--------|--------|
| Ready | Evaluate rent + yield |
| Offplan | OFFPLAN_RENTAL_NOT_EVALUATED |
| Unknown | NOT_EVALUATED |

Status resolution delegates to `_build_apil_attributes()` — the same function used by `/properties/{id}`. No independent status logic in the rental engine.

---

## 6. INVESTOR UI SEMANTICS — FROZEN

| Tier | Label | Evidence Badge | Support Text |
|------|-------|---------------|-------------|
| R1 | Estimated Project Rent | Strongest Rental Evidence | "Based on recent comparable leases in the same project, same bedroom category, and similar-sized units." |
| R2 | Estimated Project Rent | Strong Rental Evidence | "Based on recent comparable leases in the same project and similar-sized units." |
| R3 | Estimated Area Rent | Broader Rental Evidence | "Based on recent comparable leases in the surrounding area, same bedroom category, and similar-sized units." |
| R4 | Estimated Area Rent | Broader Rental Evidence | "Based on broader comparable leases in the surrounding area and similar-sized units. Individual building rents may differ." |
| NONE | No Reliable Rental Estimate Available | — | "APIL could not find enough comparable rental evidence for this property." |
| Offplan | Gross Rental Yield — Not Evaluated | — | "This property is currently off-plan, so current rental income is not evaluated." |
| Unknown | Rental Yield Not Evaluated | — | "Property status is unknown, so rental income is not evaluated." |

**Mandatory R4 wording**: "Based on broader comparable leases in the surrounding area and similar-sized units. Individual building rents may differ."

Technical tier codes (R1/R2/R3/R4) are NOT exposed prominently to normal investors. They remain available in debug/details.

---

## 7. GROSS YIELD DISCLOSURE — FROZEN

**Mandatory footer on all rental cards**:

> "Gross Rental Yield is estimated annual rent divided by the property's current asking price, before service charges, vacancy, management fees, maintenance, financing and other ownership costs."

**NOT labeled as**:
- Net ROI
- Property ROI
- Total ROI
- ROI

This is GROSS RENTAL YIELD only. Full Property ROI is a separate future engine.

---

## 8. DATA QUALITY WARNING — FROZEN

When `gross_rental_yield_pct > 15%`, the response includes:

> "Gross yield is unusually high relative to the supplied asking price. Verify property price before relying on this figure."

**The warning does NOT**:
- Cap yield
- Alter MASTER price
- Alter rent estimate
- Guess corrected prices
- Change any APIL signal

It is disclosure only.

**Known example**: Property 2725 (Saba 2, JLT) — MASTER price 90,000 AED, rent 84,480 AED, yield 93.87%. Warning is displayed. No values are changed.

---

## 9. DEBUG ENDPOINT — FROZEN

`GET /debug/rental-context/{property_id}`

Remains available for auditability. Normal UI and debug endpoint use the same backend rental service (`compute_rental_context()`).

---

## 10. FROZEN REGRESSION PROPERTIES

### Ready Properties

| Property ID | Name | Tier | Rent (AED) | Yield | R4 Disclosure | DQ Warning |
|-------------|------|------|-----------|-------|---------------|------------|
| 6056 | Imperial Avenue | R2 | 278,400 | 4.42% | — | — |
| 6277 | Binghatti Emerald | R2 | 100,800 | 7.75% | — | — |
| 8057 | Binghatti Royale | R2 | 172,800 | 3.84% | — | — |
| 3201 | Binghatti Nova | R2 | 72,000 | 5.22% | — | — |
| 7061 | Azizi Mina | R4 | 172,800 | 3.84% | ✅ | — |
| 8201 | Marquise Square | R4 | 163,200 | 3.80% | ✅ | — |
| 2725 | Saba 2 | R4 | 84,480 | 93.87% | ✅ | ✅ |

### Offplan Controls

| Property ID | Name | Status | Rent | Yield |
|-------------|------|--------|------|-------|
| 3693 | Elvira | Offplan | NOT EVALUATED | NOT EVALUATED |
| 4434 | Lime Gardens | Offplan | NOT EVALUATED | NOT EVALUATED |
| 701 | Elvira | Offplan | NOT EVALUATED | NOT EVALUATED |
| 3983 | Sapphire 32 | Offplan | NOT EVALUATED | NOT EVALUATED |

**FINAL_RENT_TRACE_MISMATCH = 0** ✅
**FINAL_GROSS_YIELD_TRACE_MISMATCH = 0** ✅

---

## 11. PRODUCTION COVERAGE — FROZEN

### Status Distribution (2,614 properties)

| Status | Count |
|--------|-------|
| Ready | 315 |
| Offplan | 2,249 |
| Unknown | 50 |
| **Total** | **2,614** |

### Tier Distribution (Ready only)

| Tier | Count |
|------|-------|
| R1 | 2 |
| R2 | 142 |
| R3 | 26 |
| R4 | 130 |
| NONE | 15 |
| **Sum** | **315** |

### Evaluable

| Metric | Count |
|--------|-------|
| Rent evaluable | 300 / 315 (95.2%) |
| Gross yield evaluable | 300 / 315 (95.2%) |

---

## 12. SOURCE IDENTITY — FROZEN

| Item | Value |
|------|-------|
| Rental CSV path | `/Users/apple/Desktop/Ai 3d view/dxb_rents_all.csv` |
| Rental CSV SHA256 | `92546471b4326a89ca5980381b918cd5077d277eae396edf0374d9448d91129d` |
| Rental CSV rows | 573,097 |
| MASTER path | `/Users/apple/Desktop/Ai 3d view/MASTER_FINAL.xlsx` |
| MASTER rows | 2,614 |

**SHA256 is the authoritative identity.** Stale/duplicate rental CSVs are archived in `archive/stale_rental_data/` and must NOT be resurrected.

---

## 13. SAFETY RULES — FROZEN

### Sales Engine Isolation

| Counter | Value | Status |
|---------|-------|--------|
| RENTAL_CHANGED_MARKET_CONTEXT | 0 | ✅ |
| RENTAL_CHANGED_PRODUCTION_SIGNAL | 0 | ✅ |
| RENTAL_CHANGED_APIL_ADVANTAGE | 0 | ✅ |
| RENTAL_CHANGED_CONVENTIONAL_POSITION | 0 | ✅ |
| RENTAL_CHANGED_FIT_SCORE | 0 | ✅ |

### Frontend Authority

| Counter | Value | Status |
|---------|-------|--------|
| FRONTEND_RENT_FORMULA_IMPLEMENTED | 0 | ✅ |
| FRONTEND_GROSS_YIELD_FORMULA_IMPLEMENTED | 0 | ✅ |

### Other Safety Counters

| Counter | Value | Status |
|---------|-------|--------|
| OFFPLAN_CURRENT_RENT_CALCULATED | 0 | ✅ |
| UNKNOWN_STATUS_RENT_CALCULATED | 0 | ✅ |
| ASKING_PRICE_USED_TO_ESTIMATE_RENT | 0 | ✅ |
| ASKING_PRICE_USED_TO_VALIDATE_RENT | 0 | ✅ |
| YIELD_USED_TO_REJECT_RENT | 0 | ✅ |
| DLD_SALES_PRICE_USED_FOR_GROSS_YIELD | 0 | ✅ |
| AREA_BENCHMARK_USED_FOR_GROSS_YIELD | 0 | ✅ |
| QDRANT_PRICE_USED_FOR_GROSS_YIELD | 0 | ✅ |
| NET_ROI_CALCULATED | 0 | ✅ |

**ALL SAFETY COUNTERS AT 0.**

---

## 14. KNOWN LIMITATIONS

1. **R4 tail error**: P90 APE is ~38-39% due to unit heterogeneity within DLD areas. This is structural and cannot be improved without area-specific overfitting (rejected in V1.2 research).

2. **15 Ready properties have NONE**: No DLD rental area mapping or insufficient comparables. No rent is fabricated.

3. **Property 2725**: MASTER price of 90,000 AED produces 93.87% yield. This is a MASTER data quality issue, not a rental engine issue. Yield is NOT capped. Data-quality warning is displayed.

4. **PROJECT_EN is 70% empty**: Limits project-based refinements. R1/R2 coverage depends on project name availability.

5. **No Net ROI**: Gross Rental Yield does not include service charges, vacancy, management fees, maintenance, financing, or other ownership costs. Full Property ROI is a separate future engine.

6. **No future rent forecasting**: Offplan properties are NOT evaluated for current or future rental income.

---

## 15. R4 TAIL-RISK WARNING — FROZEN

All R4 responses include:

> "Based on broader comparable leases in the surrounding area and similar-sized units. Individual building rents may differ."

R4 is labeled "Estimated Area Rent" with "Broader Rental Evidence" badge. It is NOT called "verified project rent" or "exact building rent." P90 technical error is NOT exposed to normal users.

---

## 16. FILES — FROZEN

### Runtime Code

| File | Role |
|------|------|
| `investor_api/rental/rental_context_service.py` | Rental context computation (shared by UI and debug endpoint) |
| `investor_api/main_v2.py` | Shadow endpoint + `rental_context` in `build_response()` |
| `investor_api/rental/rental_benchmark_engine.py` | Comparator tiers R1-R4 |
| `investor_api/rental/rental_data_store.py` | Rental CSV singleton loader |
| `investor_api/rental/rental_area_mapping.py` | MASTER → DLD area mapping |
| `investor_api/rental/rental_normalization.py` | IQR filter, weighted median |

### Frontend

| File | Role |
|------|------|
| `src/components/RentalIncomeCard.tsx` | UI component (display only, no formulas) |
| `src/pages/PropertyDetail.tsx` | Page integration |
| `src/data/api.ts` | TypeScript types |

### Test/Audit

| File | Role |
|------|------|
| `run_freeze_regression.py` | Final freeze regression |
| `run_ui_integration_test.py` | UI integration regression |
| `run_http_shadow_verification.py` | HTTP shadow verification |
| `run_gross_yield_audit.py` | Production readiness audit |

---

## 17. DO NOT

- Do NOT change methodology without a new version marker (V2)
- Do NOT cap yield
- Do NOT alter MASTER price
- Do NOT use DLD sales benchmark as yield denominator
- Do NOT calculate Net ROI
- Do NOT forecast future rental income for Offplan
- Do NOT independently recreate status logic
- Do NOT implement rent/yield formulas in frontend code
- Do NOT remove the debug endpoint
- Do NOT start Full Property ROI without explicit approval

---

**FROZEN. Any change requires: new version marker, full 2,614-property re-audit, regression re-verification, and explicit re-approval.**
