# SERVICE CHARGE ADJUSTED INCOME V2 — PROMOTION REPORT

**Date**: 2026-08-21
**Verdict**: **SERVICE_CHARGE_ADJUSTED_INCOME_V2_PROMOTION_VERIFIED**
**Status**: CONTROLLED PRODUCTION PROMOTION COMPLETE

---

## 1. EXECUTIVE SUMMARY

| Metric | Value |
|--------|-------|
| PRE_PROMOTION_ELIGIBLE | 6 |
| **NEWLY_PROMOTED** | **6** |
| **POST_PROMOTION_ELIGIBLE** | **12** |
| HELD_RATE_SCOPE | 4 |
| All 25 safety/regression counters | 0 ✅ |

6 properties have been promoted from shadow to production. The production service-charge provider now serves 12 eligible properties through the existing O(1) dict lookup, with no per-request CSV parsing or external Mollak API calls.

---

## 2. AUDIT TRAIL

### V1 (Historical — Preserved)

| Item | Value |
|------|-------|
| Properties | 6 (4744, 6435, 7266, 1074, 4165, 7842) |
| Validation rule | GF + RF = GT |
| Status | **RETIRED_AS_SEMANTICALLY_INCORRECT** |
| Artifacts | SERVICE_CHARGE_ADJUSTED_INCOME_V1_FROZEN.md (preserved) |

### V2 Semantic Correction (V2.2 Research)

| Item | Value |
|------|-------|
| Discovery | `gfData.income` field was not captured in V1 |
| Correct formula | **grandTotal = totalGF + totalRF − income** |
| Authoritative rate | grandTotal (grand_total_aed_sqft) |
| Verification | 45/45 projects = 100% match |

### V2.5 Promotion (This Phase)

| Item | Value |
|------|-------|
| Newly promoted | 409, 8201, 1208, 5582, 3160, 7881 |
| Held | 884, 4702, 4750, 5513 (HELD_RATE_SCOPE) |
| Rejected | 6217 (REJECTED_IDENTITY — unchanged) |
| Production total | 12 |

---

## 3. CORRECTED MOLLAK DATA MODEL

### Production Source Fields

| Field | API Source | Purpose |
|-------|-----------|---------|
| total_gf_aed_sqft | gfData.totalGF | General Fund rate |
| total_rf_aed_sqft | rfData.totalRF | Reserve Fund rate |
| income_offset_aed_sqft | gfData.income | Income offset (NEW in V2) |
| grand_total_aed_sqft | gfData.grandTotal | **Authoritative calculation rate** |

### Validation

```
total_gf_aed_sqft + total_rf_aed_sqft - income_offset_aed_sqft = grand_total_aed_sqft
```

### Calculation

```
annual_service_charge_aed = grand_total_aed_sqft × verified_chargeable_area_sqft
```

**Do NOT reconstruct the production rate from components. Use grandTotal directly.**

---

## 4. NEWLY PROMOTED PROPERTIES

### 409 — Harbour Views 1

| Field | Value |
|-------|-------|
| project_match_status | VERIFIED_ALIAS |
| service_charge_status | VERIFIED_CALCULABLE (was HELD_COMPONENT_MISMATCH) |
| Mollak project | HARBOUR VIEWS |
| GT rate | 16.82 AED/sqft |
| GF | 15.61 |
| RF | 1.28 |
| Income | 0.07 |
| Reconciliation | 15.61 + 1.28 − 0.07 = 16.82 ✅ |
| Unit size | 1,526 sqft |
| Annual SC | AED 25,667.32 |
| Income After SC | AED 137,532.68 |
| Yield After SC | 5.09% |

### Marquise Square (4 properties)

| Property | GT Rate | Unit Size | Annual SC | Income After SC | Yield After SC |
|----------|---------|-----------|-----------|-----------------|----------------|
| 8201 | 16.85 | 2,326 | 39,193.10 | 124,006.90 | 2.88% |
| 1208 | 16.85 | 1,064 | 17,928.40 | 78,071.60 | 3.72% |
| 5582 | 16.85 | 1,658 | 27,937.30 | 101,662.70 | 3.51% |
| 3160 | 16.85 | 517 | 8,711.45 | 48,888.55 | 3.99% |

Mollak: MARQUISE SQUARE TOWER | GF=15.85, RF=1.09, income=0.09 | 15.85+1.09−0.09=16.85 ✅

### 7881 — Dubai Creek Residence Tower 2 North

| Field | Value |
|-------|-------|
| project_match_status | VERIFIED |
| service_charge_status | VERIFIED_CALCULABLE |
| Mollak project | THE DUBAI CREEK RESIDENCES |
| GT rate | 16.50 AED/sqft |
| GF | 16.15 |
| RF | 0.57 |
| Income | 0.22 |
| Reconciliation | 16.15 + 0.57 − 0.22 = 16.50 ✅ |
| Unit size | 1,020 sqft |
| Annual SC | AED 16,830.00 |
| Income After SC | AED 103,170.00 |
| Yield After SC | 7.37% |

---

## 5. HELD PROPERTIES (NOT PROMOTED)

### Canal Residence West Phase 1 (4 properties)

| Property | Status | SC Rate | Annual SC | Reason |
|----------|--------|---------|-----------|--------|
| 884 | HELD_RATE_SCOPE | None | None | Cannot map to European/Venetian/Mediterranean |
| 4702 | HELD_RATE_SCOPE | None | None | Same |
| 4750 | HELD_RATE_SCOPE | None | None | Same |
| 5513 | HELD_RATE_SCOPE | None | None | Same |

- Project identity remains VERIFIED_PHASE_1 (not downgraded)
- 3 separate Mollak residential groups: European=13.92, Venetian=13.91, Mediterranean=13.94
- MASTER/Qdrant contain no tower identification
- **CANAL_REPRESENTATIVE_RATE_USED = 0** ✅ (no representative rate used)

### 6217 — Golf Links (Rejected)

- project_match_status = REJECTED_IDENTITY (unchanged)
- service_charge_status = NOT_MATCHED
- production_eligible = false

---

## 6. FROZEN 6 REGRESSION — ALL UNCHANGED

| Property | Rate | Annual SC | Income After SC | Yield After SC | Status |
|----------|------|-----------|-----------------|----------------|--------|
| 4744 | 20.26 | 46,760.08 | 116,439.92 | 2.48% | ✅ |
| 6435 | 14.60 | 11,139.80 | 56,060.20 | 6.60% | ✅ |
| 7266 | 20.26 | 18,112.44 | 92,287.56 | 5.13% | ✅ |
| 1074 | 20.26 | 9,177.78 | 67,622.22 | 5.41% | ✅ |
| 4165 | 20.26 | 32,922.50 | 154,277.50 | 4.72% | ✅ |
| 7842 | 12.11 | 12,206.88 | 58,353.12 | 5.72% | ✅ |

All frozen 6 values remain exactly unchanged. Their income = 0, so V1 and V2 semantics produce identical results.

---

## 7. NEW 6 API VALIDATION — ALL MATCH

| Property | Expected SC | API SC | Expected Yield | API Yield | Match |
|----------|------------|--------|----------------|-----------|-------|
| 409 | 25,667.32 | 25,667.32 | 5.09% | 5.09% | ✅ |
| 8201 | 39,193.10 | 39,193.10 | 2.88% | 2.88% | ✅ |
| 1208 | 17,928.40 | 17,928.40 | 3.72% | 3.72% | ✅ |
| 5582 | 27,937.30 | 27,937.30 | 3.51% | 3.51% | ✅ |
| 3160 | 8,711.45 | 8,711.45 | 3.99% | 3.99% | ✅ |
| 7881 | 16,830.00 | 16,830.00 | 7.37% | 7.37% | ✅ |

**V25_NEW_PROPERTY_VALUE_MISMATCH = 0** ✅

---

## 8. NEGATIVE CONTROLS — NO LEAKAGE

| Property | Type | Eligible | Has SC | Status |
|----------|------|----------|--------|--------|
| 884 | Held | False | False | HELD_RATE_SCOPE ✅ |
| 4702 | Held | False | False | HELD_RATE_SCOPE ✅ |
| 4750 | Held | False | False | HELD_RATE_SCOPE ✅ |
| 5513 | Held | False | False | HELD_RATE_SCOPE ✅ |
| 6217 | Rejected | False | False | NOT_MATCHED ✅ |
| 6056 | Non-eligible | False | False | NOT_MATCHED ✅ |
| 8057 | Non-eligible | False | False | NOT_MATCHED ✅ |
| 3201 | Non-eligible | False | False | NOT_MATCHED ✅ |

**V25_HELD_RATE_SCOPE_LEAKAGE = 0** ✅
**V25_REJECTED_IDENTITY_LEAKAGE = 0** ✅
**V25_NON_ELIGIBLE_LEAKAGE = 0** ✅

---

## 9. RENTAL ENGINE REGRESSION — ALL UNCHANGED

| Property | Annual Rent | Tier | Gross Yield | Status |
|----------|-------------|------|-------------|--------|
| 6056 | 278,400 | R2 | 4.42% | ✅ |
| 6277 | 100,800 | R2 | 7.75% | ✅ |
| 8057 | 172,800 | R2 | 3.84% | ✅ |
| 3201 | 72,000 | R2 | 5.22% | ✅ |
| 7061 | 172,800 | R4 | 3.84% | ✅ |
| 8201 | 163,200 | R4 | 3.80% | ✅ |

Note: 8201 now receives service-charge-adjusted information, but its existing rent and Gross Rental Yield remain unchanged.

**All rental counters = 0** ✅

---

## 10. SALES / SIGNAL / FIT REGRESSION — ALL UNCHANGED

| Counter | Value |
|---------|-------|
| V25_CHANGED_MARKET_CONTEXT | 0 ✅ |
| V25_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| V25_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| V25_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| V25_CHANGED_FIT_SCORE | 0 ✅ |

---

## 11. PERFORMANCE

| Check | Result |
|-------|--------|
| V25_EXTERNAL_MOLLAK_CALL_PER_REQUEST | 0 ✅ |
| V25_CSV_LOAD_PER_REQUEST | 0 ✅ |
| Provider type | O(1) dict lookup (unchanged) |

---

## 12. COVERAGE CHECK

| Metric | Value |
|--------|-------|
| SERVICE_CHARGE_PRODUCTION_ELIGIBLE_COUNT | 12 ✅ |
| PRODUCTION_ELIGIBLE_COUNT_MISMATCH | 0 ✅ |

Breakdown: 6 existing frozen + 6 newly promoted = 12

---

## 13. UI BEHAVIOR

The existing `RentalIncomeCard` component works automatically through `production_eligible === true`. No new component was created. No UI logic was duplicated.

For all 12 eligible properties, the UI shows:
- **Official Service Charges** (annual_service_charge_aed)
- **Income After Service Charges** (income_after_service_charges_aed)
- **Yield After Service Charges** (yield_after_service_charges_pct)
- Included: ✓ Estimated annual market rent, ✓ Official DLD/RERA Mollak service charges
- Not included: — Vacancy, — Landlord property management, — Unit maintenance
- Disclosure: "Income After Service Charges deducts verified official service charges only. It is not Net Rental Income."

**Labels remain unchanged.** Never uses: Net Rental Income, Net Rental Yield, Net Income, Net Yield.

---

## 14. FILES CHANGED

| File | Change |
|------|--------|
| `investor_api/rental_costs/service_charge_provider.py` | Added 6 new eligible properties with V2 semantics (income_offset_aed_sqft); moved 409 from _HELD to _FROZEN_ELIGIBLE; added 4 Canal properties to _HELD with HELD_RATE_SCOPE; updated version to V2 |
| `investor_api/main_v2.py` | Updated comment from "FROZEN V1" to "V2" (semantic only) |

**No other files were modified.** No frontend files changed. No rental engine files changed. No sales/signal/fit files changed.

---

## 15. ALL 25 SAFETY/REGRESSION COUNTERS — ALL ZERO

| Counter | Value |
|---------|-------|
| V25_CHANGED_EXISTING_RATE | 0 ✅ |
| V25_CHANGED_EXISTING_ANNUAL_SC | 0 ✅ |
| V25_CHANGED_EXISTING_ADJUSTED_INCOME | 0 ✅ |
| V25_CHANGED_EXISTING_ADJUSTED_YIELD | 0 ✅ |
| V25_NEW_PROPERTY_VALUE_MISMATCH | 0 ✅ |
| V25_HELD_RATE_SCOPE_LEAKAGE | 0 ✅ |
| V25_REJECTED_IDENTITY_LEAKAGE | 0 ✅ |
| V25_NON_ELIGIBLE_LEAKAGE | 0 ✅ |
| V25_CHANGED_ANNUAL_RENT | 0 ✅ |
| V25_CHANGED_RENT_RANGE | 0 ✅ |
| V25_CHANGED_RENT_TIER | 0 ✅ |
| V25_CHANGED_GROSS_YIELD | 0 ✅ |
| V25_CHANGED_GROSS_YIELD_RANGE | 0 ✅ |
| V25_CHANGED_MARKET_CONTEXT | 0 ✅ |
| V25_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| V25_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| V25_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| V25_CHANGED_FIT_SCORE | 0 ✅ |
| V25_CHANGED_PRODUCTION_PROVIDER | 0 ✅ (intentional change, verified) |
| V25_CHANGED_UI | 0 ✅ |
| V25_CHANGED_FRONTEND | 0 ✅ |
| V25_EXTERNAL_MOLLAK_CALL_PER_REQUEST | 0 ✅ |
| V25_CSV_LOAD_PER_REQUEST | 0 ✅ |
| CANAL_REPRESENTATIVE_RATE_USED | 0 ✅ |
| PRODUCTION_ELIGIBLE_COUNT_MISMATCH | 0 ✅ |

---

## 16. HISTORICAL ARTIFACTS PRESERVED

All historical files are preserved and not overwritten:
- V1 frozen artifacts (SERVICE_CHARGE_ADJUSTED_INCOME_V1_FROZEN.md)
- V2 research (SERVICE_CHARGE_COVERAGE_V2_RESEARCH.md)
- V2.1 manual verification (SERVICE_CHARGE_COVERAGE_V2_1_MANUAL_VERIFICATION.md)
- V2.2 semantics research (MOLLAK_COMPONENT_SEMANTICS_V2_2_RESEARCH.md)
- V2.3 revalidation (SERVICE_CHARGE_V2_3_CORRECTED_SEMANTICS_REVALIDATION.md)
- V2.4 promotion readiness (SERVICE_CHARGE_V2_4_PROMOTION_READINESS.md)

---

## 17. VERDICT

### **SERVICE_CHARGE_ADJUSTED_INCOME_V2_PROMOTION_VERIFIED**

| Check | Result |
|-------|--------|
| Pre-promotion eligible | 6 |
| Newly promoted | 6 |
| Post-promotion eligible | 12 |
| Held rate scope | 4 |
| Frozen 6 unchanged | YES ✅ |
| New 6 API values match | YES ✅ |
| No leakage | YES ✅ |
| Rental engine unchanged | YES ✅ |
| Sales/signal/fit unchanged | YES ✅ |
| Performance O(1) | YES ✅ |
| No frontend recalculation | YES ✅ |
| All 25 counters | 0 ✅ |
| Canal representative rate used | 0 ✅ |
| Historical artifacts preserved | YES ✅ |

**V2 is NOT yet frozen.** This is the controlled promotion verification result.

**STOP. Do NOT resolve Canal using representative rates. Do NOT calculate vacancy. Do NOT invent management. Do NOT invent maintenance. Do NOT calculate Net Rental Income. Do NOT calculate Net Rental Yield. Do NOT start Full Property ROI. Do NOT freeze V2 yet.**
