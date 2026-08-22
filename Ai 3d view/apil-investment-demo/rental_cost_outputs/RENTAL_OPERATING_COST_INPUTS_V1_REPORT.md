# RENTAL OPERATING COST INPUTS V1 — SHADOW REPORT

**Date**: 2026-08-21
**Phase**: CONTROLLED DEVELOPMENT / SHADOW
**Verdict**: **RENTAL_OPERATING_COST_INPUTS_V1_SHADOW_VERIFIED**
**Status**: NOT FROZEN — Shadow verification only

---

## 1. GOAL

Build a safe operating-cost input layer for vacancy, landlord property management, and unit maintenance. This creates the data model, API structure, validation rules, and controlled UI inputs required for future Net Rental Income and Net Rental Yield — without fabricating any values.

---

## 2. INPUT MODEL

### Required Costs

| Cost | Input Modes | Source |
|------|------------|--------|
| Vacancy | VACANCY_PERCENT or VACANCY_LOSS_AED (not both) | USER_INPUT |
| Management | USER_INPUT_FIXED_AED, USER_INPUT_PERCENT, or SELF_MANAGED | USER_INPUT / SELF_MANAGED |
| Maintenance | annual_cost_aed (AED/year) | USER_INPUT |

### Provenance Sources Allowed

| Source | Description |
|--------|-------------|
| OFFICIAL | From official data (e.g., Mollak) |
| VERIFIED_EXTERNAL | From verified external source |
| USER_INPUT | Entered by user |
| SELF_MANAGED | User explicitly selected self-management |
| MISSING | Not yet provided |

### Forbidden Sources

| Source | Reason |
|--------|--------|
| ASSUMED | No assumptions allowed |
| DEFAULT | No defaults allowed |
| MARKET_STANDARD | No market averages |
| ESTIMATED_WITHOUT_EVIDENCE | No estimates without evidence |

---

## 3. VALIDATION RULES

### Vacancy

| Rule | Constraint |
|------|-----------|
| Input mode | VACANCY_PERCENT or VACANCY_LOSS_AED (not both simultaneously) |
| VACANCY_PERCENT | 0 ≤ percent ≤ 100 |
| VACANCY_LOSS_AED | 0 ≤ loss_aed ≤ annual_rent_estimate_aed |
| Source | USER_INPUT |
| Default | None (no default vacancy percentage) |

### Management

| Rule | Constraint |
|------|-----------|
| Input mode | USER_INPUT_FIXED_AED, USER_INPUT_PERCENT, or SELF_MANAGED |
| USER_INPUT_FIXED_AED | annual_cost_aed ≥ 0 |
| USER_INPUT_PERCENT | percent ≥ 0, base = effective_rental_income_after_vacancy |
| SELF_MANAGED | annual_cost_aed = 0, source = SELF_MANAGED (only on explicit user selection) |
| Auto self-managed | Never assumed |

### Maintenance

| Rule | Constraint |
|------|-----------|
| Input | annual_cost_aed ≥ 0 |
| Source | USER_INPUT |
| Default | None (no percentage of price/rent/SC/area) |

---

## 4. CALCULATION LEVELS

| Level | Name | Inputs Required | Outputs |
|-------|------|----------------|---------|
| 1 | GROSS_RENTAL | Annual rent | Gross Rental Yield |
| 2 | SERVICE_CHARGE_ADJUSTED | Annual rent + Service charges | Income After SC, Yield After SC |
| 3 | PARTIAL_OPERATING_COSTS | Some operating costs | Income After Known Operating Costs (NOT Net) |
| 4 | NET_RENTAL | All costs (vacancy + mgmt + maint + SC) | Net Rental Income, Net Rental Yield |

### Level Transitions

- No inputs → Level 2 (SERVICE_CHARGE_ADJUSTED) — existing V2 behavior unchanged
- Some inputs → Level 3 (PARTIAL_OPERATING_COSTS) — shows "Income After Known Operating Costs"
- All inputs + SC eligible → Level 4 (NET_RENTAL) — shows "Net Rental Income" and "Net Rental Yield"
- All inputs but SC NOT eligible → Level 3 (PARTIAL) — Net Rental NOT produced

---

## 5. FORMULAS

### Effective Rental Income

```
effective_rental_income_aed = annual_rent_estimate_aed - vacancy_loss_aed
```

### Known Operating Income (Partial)

```
known_operating_income_aed = effective_rental_income_aed
                            - annual_service_charge_aed (if available)
                            - management_cost_aed (if available)
                            - maintenance_cost_aed (if available)
```

### Net Rental Income (ONLY when ALL costs available)

```
net_rental_income_aed = annual_rent_estimate_aed
                       - vacancy_loss_aed
                       - annual_service_charge_aed
                       - management_cost_aed
                       - maintenance_cost_aed
```

### Net Rental Yield

```
net_rental_yield_pct = net_rental_income_aed / current_price_aed × 100
```

**MASTER current_price remains the authoritative denominator.**

### Management Percent Base

```
management_cost_aed = effective_rental_income_after_vacancy × management_percent / 100
```

---

## 6. TEST CASE RESULTS

| Test | Description | Property | Level | Net Income | Result |
|------|-------------|----------|-------|------------|--------|
| A | No user inputs | 409 | SERVICE_CHARGE_ADJUSTED | None | PASS ✅ |
| B | Vacancy only (5%) | 409 | PARTIAL_OPERATING_COSTS | None | PASS ✅ |
| C | Vacancy + management | 409 | PARTIAL_OPERATING_COSTS | None | PASS ✅ |
| D | All costs + SC eligible | 409 | NET_RENTAL | 112,372.68 | PASS ✅ |
| E | Self-managed | 409 | NET_RENTAL | 124,372.68 | PASS ✅ |
| F | No SC available | 3201 | PARTIAL_OPERATING_COSTS | None | PASS ✅ |

### Test D Detail (409 — all costs)

| Field | Value |
|-------|-------|
| Annual rent | AED 163,200 |
| Vacancy (5%) | -AED 8,160 |
| Service charges | -AED 25,667.32 |
| Management (fixed) | -AED 12,000 |
| Maintenance | -AED 5,000 |
| **Net Rental Income** | **AED 112,372.68** |
| **Net Rental Yield** | **4.16%** |

### Test E Detail (409 — self-managed)

| Field | Value |
|-------|-------|
| Management source | SELF_MANAGED |
| Management cost | AED 0 |
| **Net Rental Income** | **AED 124,372.68** |

### Test F Detail (3201 — no SC)

| Field | Value |
|-------|-------|
| SC eligible | False |
| All operating costs entered | Yes |
| Net Rental Income | None (not produced) |
| Level | PARTIAL_OPERATING_COSTS |

---

## 7. BACKEND DATA MODEL

### Package Structure

```
investor_api/rental_operating_costs/
├── __init__.py                    # Package docstring
├── operating_cost_models.py       # Data models, provenance, calculation levels
├── operating_cost_validation.py   # Validation rules
├── operating_cost_calculator.py   # Calculation engine
└── user_input_store.py            # In-memory user input persistence
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/properties/{id}/operating-costs` | Submit user inputs |
| DELETE | `/properties/{id}/operating-costs` | Clear user inputs |
| GET | `/properties/{id}` | Returns `rental_operating_cost_context` in response |

### Response Object

```json
{
  "rental_operating_cost_context": {
    "calculation_level": "NET_RENTAL",
    "vacancy": { "status": "AVAILABLE", "source": "USER_INPUT", ... },
    "management": { "status": "AVAILABLE", "source": "USER_INPUT", ... },
    "maintenance": { "status": "AVAILABLE", "source": "USER_INPUT", ... },
    "effective_rental_income_aed": 155040.0,
    "known_operating_income_aed": 112372.68,
    "net_rental_income_aed": 112372.68,
    "net_rental_yield_pct": 4.16,
    "included_costs": [...],
    "missing_costs": [],
    "disclosure": "...",
    "partial_disclosure": null
  }
}
```

---

## 8. USER INPUT PERSISTENCE

| Storage | Used | Reason |
|---------|------|--------|
| In-memory (session) | YES | User preferences only |
| MASTER_FINAL.xlsx | NO | User input never overwrites official data |
| Qdrant | NO | User input never written to vector store |
| Mollak | NO | User input never overwrites official SC data |

Each stored field tracks: value, input_mode, source, timestamp, property_id.

---

## 9. UI DESIGN

### Component

`src/components/OperatingCostsCard.tsx` — placed beneath the existing RentalIncomeCard.

### Progressive Display

| State | Shows |
|-------|-------|
| No inputs | Input fields only, hint text |
| Some inputs | "Income After Known Operating Costs" + partial disclosure |
| All inputs + SC | "Net Rental Income" + "Net Rental Yield" + full included list |

### Labels Used

| Label | Correct |
|-------|---------|
| Official Service Charges | YES |
| Income After Service Charges | YES |
| Yield After Service Charges | YES |
| Income After Known Operating Costs | YES |
| Net Rental Income | YES (only at Level 4) |
| Net Rental Yield | YES (only at Level 4) |

### Labels NEVER Used (Forbidden)

| Label | Used |
|-------|------|
| Net Rental Income (at partial level) | NO ✅ |
| Net Rental Yield (at partial level) | NO ✅ |
| Net Income | NO ✅ |
| Net Yield | NO ✅ |

### Disclosure

- "Vacancy, management, and maintenance values shown here are based on your inputs unless identified as verified data."
- Partial: "This is not Net Rental Income because one or more operating cost inputs are still missing."

### Frontend No-Recalculation

The frontend sends validated input values to the backend. Backend performs all financial calculations. Frontend only formats backend results.

---

## 10. ALL REGRESSION COUNTERS

### Service Charge V2 Frozen Regression

| Counter | Value |
|---------|-------|
| OPERATING_COST_V1_CHANGED_SC_ELIGIBILITY | 0 ✅ |
| OPERATING_COST_V1_CHANGED_SC_RATE | 0 ✅ |
| OPERATING_COST_V1_CHANGED_SC_ANNUAL | 0 ✅ |
| OPERATING_COST_V1_CHANGED_INCOME_AFTER_SC | 0 ✅ |
| OPERATING_COST_V1_CHANGED_YIELD_AFTER_SC | 0 ✅ |

### Rental Regression

| Counter | Value |
|---------|-------|
| OPERATING_COST_V1_CHANGED_ANNUAL_RENT | 0 ✅ |
| OPERATING_COST_V1_CHANGED_RENT_RANGE | 0 ✅ |
| OPERATING_COST_V1_CHANGED_RENT_TIER | 0 ✅ |
| OPERATING_COST_V1_CHANGED_GROSS_YIELD | 0 ✅ |
| OPERATING_COST_V1_CHANGED_GROSS_YIELD_RANGE | 0 ✅ |

### Sales / Signal / Fit Regression

| Counter | Value |
|---------|-------|
| OPERATING_COST_V1_CHANGED_MARKET_CONTEXT | 0 ✅ |
| OPERATING_COST_V1_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| OPERATING_COST_V1_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| OPERATING_COST_V1_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| OPERATING_COST_V1_CHANGED_FIT_SCORE | 0 ✅ |

### Safety Counters

| Counter | Value |
|---------|-------|
| ASSUMED_OPERATING_COST_USED | 0 ✅ |
| DEFAULT_VACANCY_ASSUMPTION_USED | 0 ✅ |
| AUTO_SELF_MANAGED_ASSUMPTION | 0 ✅ |
| DEFAULT_MAINTENANCE_ASSUMPTION_USED | 0 ✅ |
| NET_INCOME_SHOWN_WITH_MISSING_COST | 0 ✅ |
| NET_YIELD_SHOWN_WITH_MISSING_COST | 0 ✅ |
| USER_INPUT_OVERWROTE_MASTER | 0 ✅ |
| USER_INPUT_OVERWROTE_MOLLAK | 0 ✅ |
| USER_INPUT_WRITTEN_TO_QDRANT | 0 ✅ |
| FRONTEND_VACANCY_CALCULATION | 0 ✅ |
| FRONTEND_MANAGEMENT_CALCULATION | 0 ✅ |
| FRONTEND_MAINTENANCE_CALCULATION | 0 ✅ |
| FRONTEND_NET_INCOME_CALCULATION | 0 ✅ |
| FRONTEND_NET_YIELD_CALCULATION | 0 ✅ |
| OPERATING_COST_V1_CHANGED_RENTAL_MESSAGE_LOGIC | 0 ✅ |

---

## 11. FILES CREATED/MODIFIED

### New Files

| File | Description |
|------|-------------|
| `investor_api/rental_operating_costs/__init__.py` | Package init |
| `investor_api/rental_operating_costs/operating_cost_models.py` | Data models |
| `investor_api/rental_operating_costs/operating_cost_validation.py` | Validation rules |
| `investor_api/rental_operating_costs/operating_cost_calculator.py` | Calculation engine |
| `investor_api/rental_operating_costs/user_input_store.py` | In-memory store |
| `src/components/OperatingCostsCard.tsx` | UI component |

### Modified Files

| File | Change |
|------|--------|
| `investor_api/main_v2.py` | Added imports, rental_operating_cost_context in response, POST/DELETE endpoints |
| `src/data/api.ts` | Added RentalOperatingCostContext and OperatingCostInputRequest types |
| `src/pages/PropertyDetail.tsx` | Added OperatingCostsCard beneath RentalIncomeCard |

### Output Files

| File | Description |
|------|-------------|
| `rental_cost_outputs/RENTAL_OPERATING_COST_INPUTS_V1_REPORT.md` | This report |
| `rental_cost_outputs/rental_operating_cost_inputs_v1_test_cases.json` | Test case results |
| `rental_cost_outputs/rental_operating_cost_inputs_v1_verdict.json` | Verdict + all counters |

---

## 12. ACQUISITION COSTS EXCLUDED

This rental operating-income layer does NOT include:

- DLD purchase fee
- Broker purchase fee
- Mortgage registration
- Loan interest
- Down payment
- Selling fee
- Capital appreciation
- Exit value
- Capital gains
- Holding-period return

Those belong to future FULL PROPERTY ROI, not Net Rental Income.

---

## 13. VERDICT

### **RENTAL_OPERATING_COST_INPUTS_V1_SHADOW_VERIFIED**

| Check | Result |
|-------|--------|
| Input model | Complete ✅ |
| Validation rules | Complete ✅ |
| Calculation levels (1-4) | Complete ✅ |
| Test cases A-F | All PASS ✅ |
| SC V2 frozen regression | 0 ✅ |
| Rental regression | 0 ✅ |
| Sales/signal/fit regression | 0 ✅ |
| Safety counters | 0 ✅ |
| No fabricated values | YES ✅ |
| No defaults | YES ✅ |
| No frontend recalculation | YES ✅ |
| User input not in MASTER/Qdrant | YES ✅ |
| Net Rental only at Level 4 | YES ✅ |
| Partial disclosure correct | YES ✅ |

**This is a SHADOW phase. NOT FROZEN. Do NOT start Full Property ROI.**
