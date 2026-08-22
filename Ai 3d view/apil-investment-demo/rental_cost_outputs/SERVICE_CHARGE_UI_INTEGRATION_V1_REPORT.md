# SERVICE CHARGE ADJUSTED INCOME V1 — UI INTEGRATION REPORT

**Date**: 2026-08-20
**Verdict**: **SERVICE_CHARGE_ADJUSTED_INCOME_V1_UI_VERIFIED**
**Status**: UI integration complete. All 19 safety counters at 0.

---

## 1. SUMMARY

| Metric | Value |
|--------|-------|
| Eligible UI properties | 6 |
| Eligible value mismatches | 0 |
| Held/rejected leakage | 0 |
| Non-eligible leakage | 0 |
| Frontend recalculation | 0 |
| Rental regression | 0 |
| Sales/signal regression | 0 |
| Stale Investor Fit message | 0 |
| Performance regression | 0 |

---

## 2. FILES MODIFIED

| File | Change | Lines |
|------|--------|-------|
| `investor_api/rental_costs/service_charge_provider.py` | **New** | Lightweight dict-lookup provider (frozen 6 properties) |
| `investor_api/main_v2.py` | Modified | +3 lines import, +23 lines service_charge_context wiring, +9 lines stale message fix |
| `src/data/api.ts` | Modified | +18 lines (ServiceChargeContext interface + field) |
| `src/components/RentalIncomeCard.tsx` | Modified | +68 lines (adjusted metrics section + disclosure) |
| `src/pages/PropertyDetail.tsx` | Modified | +1 line (pass service_charge_context prop) |

**Total**: 4 modified + 1 new = 5 files. 126 insertions, 3 deletions.

---

## 3. ELIGIBLE PROPERTY VALUES (verified via API)

| PID | Annual Rent | Annual SC | Income After SC | Yield After SC | Match |
|-----|------------|-----------|-----------------|----------------|-------|
| 4744 | 163,200 | 46,760.08 | 116,439.92 | 2.48% | ✅ |
| 6435 | 67,200 | 11,139.80 | 56,060.20 | 6.60% | ✅ |
| 7266 | 110,400 | 18,112.44 | 92,287.56 | 5.13% | ✅ |
| 1074 | 76,800 | 9,177.78 | 67,622.22 | 5.41% | ✅ |
| 4165 | 187,200 | 32,922.50 | 154,277.50 | 4.72% | ✅ |
| 7842 | 70,560 | 12,206.88 | 58,353.12 | 5.72% | ✅ |

**ELIGIBLE_PROPERTY_UI_VALUE_MISMATCH = 0**

---

## 4. NEGATIVE CONTROLS

| PID | Status | SC Exposed? | Adjusted Metrics? |
|-----|--------|-------------|-------------------|
| 409 | VERIFIED_ALIAS / HELD_COMPONENT_MISMATCH | No | No |
| 6217 | REJECTED_IDENTITY / NOT_MATCHED | No | No |
| 6056 | NOT_MATCHED | No | No |
| 8057 | NOT_MATCHED | No | No |
| 3201 | NOT_MATCHED | No | No |

- HELD_PROPERTY_EXPOSED_ADJUSTED_METRICS = 0
- REJECTED_PROPERTY_EXPOSED_ADJUSTED_METRICS = 0
- NON_ELIGIBLE_PROPERTY_EXPOSED_ADJUSTED_METRICS = 0

---

## 5. ALL 19 SAFETY COUNTERS

| Counter | Value | Status |
|---------|-------|--------|
| ELIGIBLE_PROPERTY_UI_VALUE_MISMATCH | 0 | ✅ |
| HELD_PROPERTY_EXPOSED_ADJUSTED_METRICS | 0 | ✅ |
| REJECTED_PROPERTY_EXPOSED_ADJUSTED_METRICS | 0 | ✅ |
| NON_ELIGIBLE_PROPERTY_EXPOSED_ADJUSTED_METRICS | 0 | ✅ |
| UI_CHANGED_ANNUAL_RENT | 0 | ✅ |
| UI_CHANGED_RENT_RANGE | 0 | ✅ |
| UI_CHANGED_RENT_TIER | 0 | ✅ |
| UI_CHANGED_GROSS_YIELD | 0 | ✅ |
| UI_CHANGED_GROSS_YIELD_RANGE | 0 | ✅ |
| UI_INTEGRATION_CHANGED_MARKET_CONTEXT | 0 | ✅ |
| UI_INTEGRATION_CHANGED_PRODUCTION_SIGNAL | 0 | ✅ |
| UI_INTEGRATION_CHANGED_APIL_ADVANTAGE | 0 | ✅ |
| UI_INTEGRATION_CHANGED_CONVENTIONAL_POSITION | 0 | ✅ |
| UI_INTEGRATION_CHANGED_FIT_SCORE | 0 | ✅ |
| STALE_RENTAL_UNKNOWN_MESSAGE_VISIBLE_ON_READY_EVALUATED_PROPERTY | 0 | ✅ |
| FRONTEND_SERVICE_CHARGE_RECALCULATION | 0 | ✅ |
| FRONTEND_ADJUSTED_INCOME_RECALCULATION | 0 | ✅ |
| FRONTEND_ADJUSTED_YIELD_RECALCULATION | 0 | ✅ |
| NORMAL_PROPERTY_API_PERFORMANCE_REGRESSION | 0 | ✅ |

---

## 6. BACKEND RESPONSE DESIGN

### service_charge_context block

```json
{
  "calculation_level": "SERVICE_CHARGE_ADJUSTED",
  "production_eligible": true,
  "project_match_status": "VERIFIED_EXACT",
  "service_charge_status": "VERIFIED_CALCULABLE",
  "service_charge_source": "DLD/RERA Mollak",
  "service_charge_year": 2026,
  "service_charge_rate_aed_sqft": 20.26,
  "mollak_project_name": "Ahad Residences",
  "annual_service_charge_aed": 46760.08,
  "income_after_service_charges_aed": 116439.92,
  "yield_after_service_charges_pct": 2.48,
  "included_costs": ["Estimated annual market rent", "Official DLD/RERA Mollak service charges"],
  "excluded_costs": ["Vacancy", "Landlord property management", "Unit maintenance"]
}
```

For non-eligible properties: `production_eligible = false`, all numeric values = `null`.

---

## 7. PERFORMANCE

| Property | Response Time |
|----------|--------------|
| 6056 | 0.008s |
| 8057 | 0.052s |
| 3201 | 0.017s |
| **Average** | **0.026s** |

No performance regression. The service_charge_context uses O(1) dict lookup — no CSV parsing per request.

---

## 8. STALE INVESTOR FIT RENTAL MESSAGE FIX

**Before**: All Ready properties showed "Rental Yield cannot be evaluated — required data is not currently linked to properties." in the Investor Fit / Unknown Information section.

**After**: For Ready properties, the stale `rental_yield` unknown preference message is suppressed. The rental_yield dimension remains in `unknown_preferences` for scoring purposes (it does not affect the fit score), but the misleading "cannot be evaluated" text is no longer shown.

**Investor Fit score logic**: UNCHANGED. The fix only affects the displayed explanation text, not the scoring algorithm.

---

## 9. UI LAYOUT

### Eligible Property

```
Rental Income

  [Evidence Badge]

  Estimated Annual Rent
  AED 163,200 / year
  Estimated Rent Range: AED 147,000 – AED 179,400 / year

  Gross Rental Yield
  3.47%
  Gross Yield Range: 3.13% – 3.82%

  [Support text]

  ─────────────────────

  Official Service Charges
  AED 46,760 / year
  Source: DLD/RERA Mollak · Budget year: 2026

  Income After Service Charges
  AED 116,440 / year

  Yield After Service Charges
  2.48%

  Included in this calculation:
  ✓ Estimated annual market rent
  ✓ Official DLD/RERA Mollak service charges

  Not included:
  — Vacancy
  — Landlord property management
  — Unit maintenance

  Income After Service Charges deducts verified official service charges only.
  It is not Net Rental Income.
```

### Non-Eligible Property

Existing Rental Income UI only. No empty placeholders. No adjusted metrics.

---

## 10. LABELS USED

| Label | Used |
|-------|------|
| Official Service Charges | ✅ |
| Income After Service Charges | ✅ |
| Yield After Service Charges | ✅ |
| Net Rental Income | ❌ (not used) |
| Net Rental Yield | ❌ (not used) |
| Net Income | ❌ (not used) |
| Net Yield | ❌ (not used) |

---

## 11. FRONTEND RECALCULATION

The frontend (`RentalIncomeCard.tsx`) only formats and displays values from the backend. No service charge, income, or yield formula is implemented in frontend code.

- FRONTEND_SERVICE_CHARGE_RECALCULATION = 0
- FRONTEND_ADJUSTED_INCOME_RECALCULATION = 0
- FRONTEND_ADJUSTED_YIELD_RECALCULATION = 0

---

## 12. WHAT WAS NOT MODIFIED

- Annual rent methodology
- Rental tier logic
- Rental calibration
- Gross Rental Yield formula
- DLD canonical engine
- Level 2 fallback
- Area V4 fallback
- APIL Advantage
- Conventional Price Position
- Production Signal
- Investor Fit score logic
- Property status resolution

---

## 13. VERDICT

### **SERVICE_CHARGE_ADJUSTED_INCOME_V1_UI_VERIFIED**

| Check | Result |
|-------|--------|
| Eligible UI properties | 6 |
| All 19 safety counters | 0 |
| Frontend builds | ✅ |
| TypeScript compiles | ✅ |
| Performance | 0.026s avg |

**STOP. UI integration verified. Do NOT calculate vacancy. Do NOT calculate Net Rental Income. Do NOT start Full Property ROI.**
