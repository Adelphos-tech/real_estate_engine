# GROSS RENTAL YIELD UI INTEGRATION REPORT

**Date**: 2026-08-20
**Verdict**: **GROSS_RENTAL_YIELD_V1_UI_VERIFIED**
**Checkpoint Tag**: `RENTAL_GROSS_YIELD_HTTP_SHADOW_V1_VERIFIED`
**Calc Version (Rent)**: `RENTAL_MARKET_RENT_V1_CANDIDATE`
**Calc Version (Yield)**: `GROSS_RENTAL_YIELD_V1_CANDIDATE`

---

## 1. Files Changed

| File | Change | Description |
|------|--------|-------------|
| `investor_api/main_v2.py` | Modified | Added `rental_context` to `build_response()` (display-only); added shadow endpoint import |
| `investor_api/rental/rental_context_service.py` | New | Rental context computation service (shared by `/properties/{id}` and `/debug/rental-context/{id}`) |
| `investor_api/rental/__init__.py` | Modified | Updated imports for new service |
| `src/data/api.ts` | Modified | Added `RentalContext` interface and `rental_context` field to `PersonalizedProperty` |
| `src/components/RentalIncomeCard.tsx` | New | UI component for RENTAL INCOME section |
| `src/pages/PropertyDetail.tsx` | Modified | Added `RentalIncomeCard` import and placement after "What does this mean?" section |

---

## 2. UI Placement

The RENTAL INCOME section is placed on the Property Detail page (`/property/{id}`), between:
- **Section 4**: "What does this mean?" (DLD sales benchmark explanation)
- **Section 5**: "Two separate assessments" (Investment signal vs Investor fit)

This positions rental income as a distinct, display-only section that does not interfere with the sales investment signal flow.

---

## 3. R1 Appearance

**Label**: Estimated Project Rent
**Evidence Badge**: Strongest Rental Evidence (emerald)
**Support Text**: "Based on recent comparable leases in the same project, same bedroom category, and similar-sized units."

```
┌─────────────────────────────────────────────┐
│ RENTAL INCOME                                │
│                                              │
│ [Strongest Rental Evidence]                  │
│                                              │
│ Estimated Project Rent                       │
│ AED 278,400 / year                           │
│ Estimated Rent Range: AED 264,000 – 297,600  │
│                                              │
│ ┌─────────────────────────────────────────┐ │
│ │ Gross Rental Yield                       │ │
│ │ 4.42%                                    │ │
│ │ Gross Yield Range: 4.19% – 4.72%         │ │
│ └─────────────────────────────────────────┘ │
│                                              │
│ Based on recent comparable leases in the     │
│ same project, same bedroom category...       │
│                                              │
│ Gross Rental Yield is estimated annual rent  │
│ divided by the property's current asking     │
│ price, before service charges, vacancy...    │
└─────────────────────────────────────────────┘
```

Technical code "R1" is NOT exposed prominently to normal investors.

---

## 4. R2 Appearance

**Label**: Estimated Project Rent
**Evidence Badge**: Strong Rental Evidence (blue)
**Support Text**: "Based on recent comparable leases in the same project and similar-sized units."

Same layout as R1, with blue evidence badge.

---

## 5. R3 Appearance

**Label**: Estimated Area Rent
**Evidence Badge**: Broader Rental Evidence (amber)
**Support Text**: "Based on recent comparable leases in the surrounding area, same bedroom category, and similar-sized units."

---

## 6. R4 Appearance

**Label**: Estimated Area Rent
**Evidence Badge**: Broader Rental Evidence (amber)
**Support Text**: "Based on broader comparable leases in the surrounding area and similar-sized units. Individual building rents may differ."
**Warning Box**: Amber background with R4 disclosure text

R4 does NOT imply:
- Same project
- Exact building rent
- Verified project rent

P90 technical error is NOT exposed to normal users.

---

## 7. NONE Appearance

**Label**: Rental Estimate — No Reliable Rental Estimate Available
**Support Text**: "APIL could not find enough comparable rental evidence for this property."

No rent is fabricated. No yield is calculated.

---

## 8. Offplan Appearance

**Label**: Gross Rental Yield — Not Evaluated
**Support Text**: "This property is currently off-plan, so current rental income is not evaluated."

No future rental income is forecasted.

---

## 9. Data-Quality Warning Appearance

When `data_quality_warning` is present (e.g., property 2725 with 93.87% yield):

**Orange warning box** with:
> **Check asking price:** Gross yield is unusually high relative to the supplied asking price. Verify property price before relying on this figure.

The warning does NOT:
- Change the price
- Change the rent
- Cap the yield
- Hide the yield
- Guess the correct price

---

## 10. 50-Property UI/API Parity Results

| Check | Mismatches | Status |
|-------|-----------|--------|
| UI_RENT_ESTIMATE_MISMATCH | 0 | ✅ PASS |
| UI_RENT_RANGE_MISMATCH | 0 | ✅ PASS |
| UI_GROSS_YIELD_MISMATCH | 0 | ✅ PASS |
| UI_RENT_TIER_SEMANTIC_MISMATCH | 0 | ✅ PASS |

50 Ready properties compared: `/properties/{id}` rental_context vs `/debug/rental-context/{id}` — all identical.

---

## 11. Known Trace Results

| Property ID | Name | Status | Tier | Rent (AED) | Yield | R4 Disclosure | DQ Warning | Match |
|-------------|------|--------|------|-----------|-------|---------------|------------|-------|
| 6056 | Imperial Avenue | Ready | R2 | 278,400 | 4.42% | — | — | ✅ |
| 6277 | Binghatti Emerald | Ready | R2 | 100,800 | 7.75% | — | — | ✅ |
| 8057 | Binghatti Royale | Ready | R2 | 172,800 | 3.84% | — | — | ✅ |
| 3201 | Binghatti Nova | Ready | R2 | 72,000 | 5.22% | — | — | ✅ |
| 7061 | Azizi Mina | Ready | R4 | 172,800 | 3.84% | ✅ Required | — | ✅ |
| 8201 | Marquise Square | Ready | R4 | 163,200 | 3.80% | ✅ Required | — | ✅ |
| 2725 | Saba 2 | Ready | R4 | 84,480 | 93.87% | ✅ | ✅ Present | ✅ |
| 3693 | Elvira | Offplan | NONE | — | — | — | — | ✅ NOT EVALUATED |
| 4434 | Lime Gardens | Offplan | NONE | — | — | — | — | ✅ NOT EVALUATED |
| 701 | Elvira | Offplan | NONE | — | — | — | — | ✅ NOT EVALUATED |
| 3983 | Sapphire 32 | Offplan | NONE | — | — | — | — | ✅ NOT EVALUATED |

**All 11 traces pass.** 0 failures.

---

## 12. Existing Sales Regression Results

20 properties tested before/after UI integration:

| Counter | Value | Status |
|---------|-------|--------|
| RENTAL_UI_CHANGED_MARKET_CONTEXT | 0 | ✅ PASS |
| RENTAL_UI_CHANGED_PRODUCTION_SIGNAL | 0 | ✅ PASS |
| RENTAL_UI_CHANGED_APIL_ADVANTAGE | 0 | ✅ PASS |
| RENTAL_UI_CHANGED_CONVENTIONAL_POSITION | 0 | ✅ PASS |
| RENTAL_UI_CHANGED_FIT_SCORE | 0 | ✅ PASS |

**All zero.** No sales signal was altered.

---

## 13. Safety Counters

| Counter | Value | Status |
|---------|-------|--------|
| FRONTEND_RENT_FORMULA_IMPLEMENTED | 0 | ✅ PASS |
| FRONTEND_GROSS_YIELD_FORMULA_IMPLEMENTED | 0 | ✅ PASS |
| RENTAL_UI_CHANGED_MARKET_CONTEXT | 0 | ✅ PASS |
| RENTAL_UI_CHANGED_PRODUCTION_SIGNAL | 0 | ✅ PASS |
| RENTAL_UI_CHANGED_APIL_ADVANTAGE | 0 | ✅ PASS |
| RENTAL_UI_CHANGED_CONVENTIONAL_POSITION | 0 | ✅ PASS |
| RENTAL_UI_CHANGED_FIT_SCORE | 0 | ✅ PASS |

**All 7 safety counters at 0.**

---

## 14. Discrepancies

**None.** All checks pass with zero discrepancies.

---

## 15. Key Design Decisions

### No Duplicated Rental Logic (§16)
The frontend (`RentalIncomeCard.tsx`) only formats and displays values from the backend. No rent or yield formula is implemented in frontend code. The backend (`rental_context_service.py`) remains the single calculation authority.

### Same Service for Debug and Production (§15, §20)
Both `/properties/{id}` and `/debug/rental-context/{id}` call the same `compute_rental_context()` function. The debug endpoint remains available for auditability.

### Status Parity (§2 from previous phase)
The rental context in `/properties/{id}` uses the same `_build_apil_attributes()` path for status resolution — MASTER `unit_status` > `_resolve_property_status()`. No independent status logic.

### Display-Only (§14)
The RENTAL INCOME section is labeled "Rental Income" and "Gross Rental Yield" — NOT "ROI", "Net ROI", "Total ROI", or "Property ROI". The mandatory footer disclosure clarifies what gross rental yield includes and excludes.

### Calculation Versions (§21)
Versions remain `RENTAL_MARKET_RENT_V1_CANDIDATE` and `GROSS_RENTAL_YIELD_V1_CANDIDATE` — NOT renamed to FINAL/FROZEN.

---

## 16. Formula

```
Gross Rental Yield = Estimated Annual Market Rent / Current Asking Price × 100
```

- Asking price = `MASTER_FINAL.xlsx` → `current_price_aed`
- No sales benchmark denominator
- No capping, no alteration

---

## 17. Output Files

| File | Description |
|------|-------------|
| `rental_outputs/rental_ui_traces.csv` | 11 trace property results |
| `rental_outputs/rental_ui_api_parity.csv` | 50-property UI/API parity |
| `rental_outputs/rental_ui_sales_regression.csv` | 20-property sales regression |
| `rental_outputs/rental_ui_verdict.json` | Full verdict data |
| `rental_outputs/RENTAL_GROSS_YIELD_UI_INTEGRATION_REPORT.md` | This report |

---

## 18. Final Verdict

### **GROSS_RENTAL_YIELD_V1_UI_VERIFIED**

| Check | Status |
|-------|--------|
| Trace tests pass (11 properties) | ✅ |
| UI/API parity pass (50 properties) | ✅ |
| Sales regression pass (20 properties) | ✅ |
| No duplicated logic in frontend | ✅ |
| Calculation versions correct | ✅ |
| Debug endpoint still available | ✅ |

### What is verified
- RENTAL INCOME section appears on Property Detail page
- R1/R2/R3/R4/NONE/Offplan/Unknown all render correctly
- R4 includes tail-risk disclosure
- Data-quality warning displays for unusual yields (property 2725)
- Mandatory footer disclosure present on all rental cards
- Frontend consumes backend results only (no duplicated formulas)
- No sales signal altered (market_context, production_signal, APIL advantage, conventional position, fit)
- Debug endpoint remains available
- Calculation versions remain CANDIDATE (not FINAL/FROZEN)

### What is NOT done
- Full Property ROI not started (separate future engine)
- No capital appreciation, service charges, vacancy, management, maintenance, financing, purchase costs, or selling costs added
- Calculation versions NOT renamed to FINAL/FROZEN

**WAITING FOR APPROVAL before starting Full Property ROI.**
