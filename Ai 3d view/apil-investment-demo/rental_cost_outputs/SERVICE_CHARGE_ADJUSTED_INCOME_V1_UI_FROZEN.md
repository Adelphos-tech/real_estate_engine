# SERVICE CHARGE ADJUSTED INCOME V1 — UI FROZEN

**Date**: 2026-08-21
**Verdict**: **SERVICE_CHARGE_ADJUSTED_INCOME_V1_UI_FINAL_VERIFIED**
**Milestone**: SERVICE_CHARGE_ADJUSTED_INCOME_V1_UI_FROZEN
**Status**: FROZEN — UI integration complete and verified

---

## 1. FROZEN ELIGIBLE PROPERTY SET (6 properties)

| Property ID | Project | Match Method | SC Year | Rate (AED/sqft) | Annual SC (AED) | Income After SC (AED) | Yield After SC |
|-------------|---------|-------------|---------|-----------------|-----------------|----------------------|----------------|
| 4744 | Ahad Residences | VERIFIED_EXACT | 2026 | 20.26 | 46,760.08 | 116,439.92 | 2.48% |
| 6435 | Pantheon Elysee | VERIFIED_EXACT | 2025 | 14.60 | 11,139.80 | 56,060.20 | 6.60% |
| 7266 | Ahad Residences | VERIFIED_EXACT | 2026 | 20.26 | 18,112.44 | 92,287.56 | 5.13% |
| 1074 | Ahad Residences | VERIFIED_EXACT | 2026 | 20.26 | 9,177.78 | 67,622.22 | 5.41% |
| 4165 | Ahad Residences | VERIFIED_EXACT | 2026 | 20.26 | 32,922.50 | 154,277.50 | 4.72% |
| 7842 | Azizi Feirouz | VERIFIED_NORMALIZED_EXACT | 2026 | 12.11 | 12,206.88 | 58,353.12 | 5.72% |

---

## 2. FROZEN RENTAL MESSAGE LOGIC

### 4-CASE DECISION TREE (frozen)

The Investor Fit `rental_yield` unknown preference message uses the **API-resolved status** (NOT raw MASTER status) and the **actual rental_context output** (NOT duplicated eligibility logic).

| Case | Resolved Status | Rental Evidence | Message |
|------|----------------|-----------------|---------|
| A | Ready | Available (rent + yield non-null) | No warning (yield IS evaluated) |
| B | Ready | Not available | "Rental yield not evaluated — insufficient reliable rental evidence." |
| C | Offplan | N/A | No rental_yield message (handled by RentalIncomeCard) |
| D | Unknown | N/A | Preserve existing safe behavior |

### Key Rules

1. **RAW_MASTER_STATUS_USED_FOR_RENTAL_MESSAGE_LOGIC = 0** — Uses `rental_resolved_status` from the API resolution path
2. **DUPLICATE_RENTAL_ELIGIBILITY_LOGIC_CREATED = 0** — Uses `rental_evidence_available` boolean derived from existing `rental_context`
3. **RENTAL_ENGINE_DOUBLE_EXECUTION_PER_REQUEST = 0** — `compute_rental_context` called exactly once per request

### Flow Restructure

`rental_context` is now computed BEFORE `build_dimension_explanations`. The `rental_evidence_available` boolean and `rental_resolved_status` string are passed as parameters to `build_dimension_explanations`.

---

## 3. FROZEN UI BEHAVIOR

### Eligible Properties (production_eligible = true)

The RentalIncomeCard shows the existing Rental Income section plus:
- Official Service Charges (AED / year)
- Income After Service Charges (AED / year)
- Yield After Service Charges (%)
- Included / Not Included disclosure
- "Income After Service Charges deducts verified official service charges only. It is not Net Rental Income."

### Non-Eligible Properties (production_eligible = false)

Existing Rental Income UI only. No empty placeholders. No adjusted metrics.

### Non-Evaluated Ready Properties (tier = NONE)

RentalIncomeCard shows "Rental Estimate — No Reliable Rental Estimate Available". No service charge metrics.

---

## 4. FROZEN LABELS

| Label | Used |
|-------|------|
| Official Service Charges | ✅ |
| Income After Service Charges | ✅ |
| Yield After Service Charges | ✅ |
| Net Rental Income | ❌ |
| Net Rental Yield | ❌ |
| Net Income | ❌ |
| Net Yield | ❌ |

---

## 5. FROZEN BACKEND RESPONSE

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

For non-eligible: `production_eligible = false`, all numeric values = `null`.

### Performance

O(1) dict lookup — no CSV parsing per request. Average response time: 0.008s.

---

## 6. BASELINE DISCREPANCY CLASSIFICATION

**Classification: PRE_EXISTING_BASELINE_CAPTURE_BUG**

The baseline capture script (`run_cost_baseline.py`) did not capture `gross_yield_p25_pct` or `gross_yield_p75_pct` fields. These fields existed in the committed code at `d22c869` (rental freeze commit, BEFORE service charge work). The service charge work did NOT introduce or change these values.

**POST_HOC_BASELINE_RESET_USED_TO_HIDE_REGRESSION = 0**

---

## 7. READY POPULATION AUDIT

| Metric | Value |
|--------|-------|
| READY_TOTAL | 315 |
| READY_RENTAL_EVALUATED_COUNT | 300 |
| READY_RENTAL_NOT_EVALUATED_COUNT | 15 |
| READY_EVALUATED_WITH_WARNING_COUNT | 0 |
| READY_NOT_EVALUATED_WITHOUT_WARNING_COUNT | 0 |
| READY_NOT_EVALUATED_NO_FIT_COUNT | 15 (no investor_fit — UI handles via RentalIncomeCard) |
| READY_NOT_EVALUATED_CORRECT_WARNING_COUNT | 0 |

The 15 non-evaluated Ready properties don't match any investor's eligibility criteria. They have no `investor_fit` and therefore no `dimension_explanations`. The RentalIncomeCard handles them by showing "No Reliable Rental Estimate Available".

---

## 8. ALL 22 SAFETY COUNTERS — ALL ZERO

| Counter | Value |
|---------|-------|
| RAW_MASTER_STATUS_USED_FOR_RENTAL_MESSAGE_LOGIC | 0 |
| DUPLICATE_RENTAL_ELIGIBILITY_LOGIC_CREATED | 0 |
| RENTAL_ENGINE_DOUBLE_EXECUTION_PER_REQUEST | 0 |
| READY_EVALUATED_WITH_WARNING_COUNT | 0 |
| READY_NOT_EVALUATED_WITHOUT_WARNING_COUNT | 0 |
| TRACE_TEST_MISMATCHES | 0 |
| NON_EVALUATED_TRACE_MISMATCHES | 0 |
| POST_HOC_BASELINE_RESET_USED_TO_HIDE_REGRESSION | 0 |
| FINAL_ANNUAL_RENT_MISMATCH | 0 |
| FINAL_RENT_RANGE_MISMATCH | 0 |
| FINAL_RENT_TIER_MISMATCH | 0 |
| FINAL_GROSS_YIELD_MISMATCH | 0 |
| FINAL_GROSS_YIELD_RANGE_MISMATCH | 0 |
| SERVICE_CHARGE_UI_FINAL_MISMATCH | 0 |
| HELD_SC_LEAKAGE | 0 |
| REJECTED_SC_LEAKAGE | 0 |
| FINAL_CHANGED_MARKET_CONTEXT | 0 |
| FINAL_CHANGED_PRODUCTION_SIGNAL | 0 |
| FINAL_CHANGED_APIL_ADVANTAGE | 0 |
| FINAL_CHANGED_CONVENTIONAL_POSITION | 0 |
| FINAL_CHANGED_FIT_SCORE | 0 |
| FINAL_API_PERFORMANCE_REGRESSION | 0 |

---

## 9. HELD / REJECTED PROPERTIES

| Property ID | Project | project_match_status | service_charge_status | production_eligible |
|-------------|---------|---------------------|----------------------|-------------------|
| 409 | Harbour Views 1 | VERIFIED_ALIAS | HELD_COMPONENT_MISMATCH | false |
| 6217 | Golf Links | REJECTED_IDENTITY | NOT_MATCHED | false |

Both have null adjusted values. No leakage.

---

## 10. FILES MODIFIED

| File | Change |
|------|--------|
| `investor_api/rental_costs/service_charge_provider.py` | New — O(1) dict lookup provider |
| `investor_api/main_v2.py` | Import + service_charge_context wiring + rental_context restructure + message logic fix |
| `src/data/api.ts` | ServiceChargeContext interface |
| `src/components/RentalIncomeCard.tsx` | Adjusted metrics section + disclosure |
| `src/pages/PropertyDetail.tsx` | Pass serviceCharge prop |

---

## 11. PREVIOUS FROZEN TAGS PRESERVED

- GROSS_RENTAL_YIELD_V1_FROZEN
- RENTAL_GROSS_YIELD_V1_FROZEN
- SERVICE_CHARGE_ADJUSTED_INCOME_V1_FROZEN (backend)
- DLD_CANONICAL_UI_V1_FROZEN
- MARKET_CONTEXT_RUNTIME_V1_FROZEN

---

## 12. VERDICT

### **SERVICE_CHARGE_ADJUSTED_INCOME_V1_UI_FINAL_VERIFIED**

| Check | Result |
|-------|--------|
| Eligible UI properties | 6 |
| All 22 safety counters | 0 |
| Frontend builds | ✅ |
| TypeScript compiles | ✅ |
| Performance | 0.008s avg |
| Baseline classification | PRE_EXISTING_BASELINE_CAPTURE_BUG |
| Ready population audited | 315 (300 evaluated, 15 not evaluated) |

**FROZEN. UI integration complete and verified.**

**STOP. Do NOT calculate vacancy. Do NOT calculate Net Rental Income. Do NOT start Full Property ROI.**
