# FULL PROPERTY ROI V1.3 — HOLDING PERIOD + EXIT VALUE + SELLING COST INPUT LAYER

**Date**: 2026-08-22
**Phase**: FULL_PROPERTY_ROI_V1_3_SCENARIO_INPUTS
**Verdict**: `FULL_PROPERTY_ROI_V1_3_SCENARIO_INPUT_LAYER_VERIFIED`
**Methodology Version**: `ROI_SCENARIO_V1_3`

---

## 1. GOAL

Build and verify the remaining scenario/input layer required for future Full Property ROI: holding period, exit sale value, and selling costs. INPUT + VALIDATION + COMPLETENESS only.

**Status: VERIFIED.** All 18 test cases pass. All 35 counters zero.

---

## 2. REQUIRED FUTURE ROI INPUTS

| Input | Phase Built | Status |
|-------|-------------|--------|
| A. COMPLETE_ACQUISITION_COSTS | V1.2 | VERIFIED |
| B. NET_RENTAL | Frozen demo layer | VERIFIED (dependency only) |
| C. HOLDING_PERIOD | V1.3 | VERIFIED |
| D. EXIT_VALUE | V1.3 | VERIFIED |
| E. COMPLETE_SELLING_COSTS | V1.3 | VERIFIED |

---

## 3. HOLDING PERIOD MODEL

| Field | Value |
|-------|-------|
| Input | `holding_period_months` |
| Source | USER_INPUT |
| Default | NONE |
| Validation | months > 0, <= 1200 (100 years technical max) |

### Derived Years

```
holding_period_years = holding_period_months / 12
```

This is DERIVED — not a separate user input.

```
DEFAULT_HOLDING_PERIOD_USED = 0 ✅
INVALID_HOLDING_PERIOD_ACCEPTED = 0 ✅
```

### Why Months

- Avoids year/month ambiguity
- Allows 18 months, 30 months, etc.
- Deterministic for future annualization

---

## 4. EXIT VALUE — NO AUTOMATIC FORECAST

**Never uses as future exit price:**
- DLD benchmark
- APIL Advantage
- Area benchmark
- Canonical benchmark
- Current market context
- Current asking price
- Historical appreciation

```
MARKET_BENCHMARK_USED_AS_FUTURE_EXIT_PRICE = 0 ✅
```

### Exit Value Input Modes

| Mode | Description | Source |
|------|-------------|--------|
| `USER_EXIT_PRICE` | User enters `exit_sale_price_aed` directly | USER_INPUT |
| `USER_APPRECIATION_RATE` | User enters `annual_appreciation_rate_pct`, backend derives | USER_INPUT (rate) / DERIVED (price) |

**Both modes cannot be submitted simultaneously → 422.**

---

## 5. USER EXIT PRICE

| Field | Value |
|-------|-------|
| Input | `exit_sale_price_aed` |
| Validation | >= 0 |
| Source | USER_INPUT |
| No comparison against DLD benchmark | Yes |
| No silent modification | Yes |

---

## 6. USER APPRECIATION RATE

| Field | Value |
|-------|-------|
| Input | `annual_appreciation_rate_pct` |
| Source | USER_INPUT |
| Never ASSUMED / DEFAULT / MARKET_STANDARD | Verified |

```
DEFAULT_APPRECIATION_USED = 0 ✅
```

### Appreciation Formula

```
exit_sale_price_aed =
    purchase_price_aed
    * (1 + annual_appreciation_rate_pct / 100)
    ^ holding_period_years
```

Uses MASTER `current_price_aed` as purchase-price basis. This is scenario math, not a market forecast.

Label: "Based on your appreciation assumption."

---

## 7. NEGATIVE APPRECIATION

Negative appreciation rates are allowed. Property prices can decline. Not clamped to zero.

```
NEGATIVE_APPRECIATION_CLAMPED = 0 ✅
```

### Test E Verification

- Rate: -10% over 5 years
- Expected: 2,700,000 * 0.90^5 = AED 1,594,323
- Result: AED 1,594,323 ✅ (decreased, not clamped)

---

## 8. EXTREME APPRECIATION

NaN, Infinity, and non-numeric values are rejected. Numeric bounds:

| Bound | Value | Reason |
|-------|-------|--------|
| Minimum | -100 | Complete loss (property worth zero) |
| Maximum | 1000 | Technical max to reject absurd inputs |

Entered values are NOT silently capped.

```
APPRECIATION_SILENTLY_CLAMPED = 0 ✅
```

---

## 9. EXIT VALUE PROVENANCE

| Field | USER_EXIT_PRICE | USER_APPRECIATION_RATE |
|-------|-----------------|----------------------|
| `exit_value_mode` | USER_EXIT_PRICE | USER_APPRECIATION_RATE |
| `exit_sale_price_aed` | user-entered | derived |
| `annual_appreciation_rate_pct` | null | user-entered |
| `source` | USER_INPUT | DERIVED |
| `rate_source` | null | USER_INPUT |
| `exit_price_source` | USER_INPUT | DERIVED |
| `calculation_basis` | "User-entered exit sale price" | "purchase_price * (1 + rate%) ^ years" |

---

## 10. SELLING COST COMPONENTS

| Component | Modes | Required for COMPLETE? |
|-----------|-------|------------------------|
| A. Selling broker commission | SELLING_BROKER_PERCENT / SELLING_BROKER_FIXED_AED / NO_SELLING_BROKER_COST | YES |
| B. Developer / NOC fee | NOC_FIXED_AED / NO_NOC_FEE | YES |
| C. Other selling costs | OTHER_SELLING_COSTS_AED / NO_OTHER_SELLING_COSTS | YES |

**No mortgage payoff — UNLEVERED V1.**

---

## 11. SELLING BROKER COMMISSION

| Mode | Calculation |
|------|-------------|
| SELLING_BROKER_PERCENT | `exit_sale_price_aed * percent / 100` |
| SELLING_BROKER_FIXED_AED | user-entered fixed amount |
| NO_SELLING_BROKER_COST | explicit 0.0 |

**NO_SELLING_BROKER_COST requires explicit user selection.** Never assume broker cost = 0.

```
DEFAULT_SELLING_BROKER_COMMISSION_USED = 0 ✅
AUTO_NO_SELLING_BROKER_ASSUMPTION = 0 ✅
```

---

## 12. DEVELOPER / NOC FEE

| Mode | Amount |
|------|--------|
| NOC_FIXED_AED | user-entered |
| NO_NOC_FEE | explicit 0.0 |

No universal NOC fee invented.

```
DEFAULT_NOC_FEE_USED = 0 ✅
```

---

## 13. OTHER SELLING COSTS

| Mode | Amount |
|------|--------|
| OTHER_SELLING_COSTS_AED | user-entered |
| NO_OTHER_SELLING_COSTS | explicit 0.0 |

Does NOT automatically add government fee, admin fee, trustee fee, or marketing fee.

---

## 14. ZERO MUST BE EXPLICIT

Missing is NOT zero. For variable selling costs, 0 is valid only when:
- User enters 0 explicitly, OR
- Selects NO_SELLING_BROKER_COST / NO_NOC_FEE / NO_OTHER_SELLING_COSTS

```
MISSING_SELLING_COST_COERCED_TO_ZERO = 0 ✅
```

---

## 15. SELLING COST COMPLETENESS

### Levels

| Level | Condition |
|-------|-----------|
| `NO_SELLING_COSTS` | No selling cost inputs |
| `PARTIAL_SELLING_COSTS` | Some inputs provided, but not all |
| `COMPLETE_SELLING_COSTS` | All 3 components resolved |

### COMPLETE requires resolution of:
- Selling broker (value or explicit zero)
- NOC/developer fee (value or explicit zero)
- Other selling costs (value or explicit zero)

---

## 16. SELLING COST FORMULA

```
complete_selling_costs_aed =
    selling_broker_cost_aed
    + noc_fee_aed
    + other_selling_costs_aed

net_sale_proceeds_aed =
    exit_sale_price_aed
    - complete_selling_costs_aed
```

`net_sale_proceeds_aed` is calculated as an intermediate validated output. Full ROI is NOT calculated.

---

## 17. NEGATIVE NET SALE PROCEEDS

If valid user inputs produce selling costs > exit price: `net_sale_proceeds_aed < 0` is allowed. Not clamped.

```
NEGATIVE_NET_SALE_PROCEEDS_CLAMPED = 0 ✅
```

### Verification

- Exit: AED 100,000
- Selling costs: AED 150,000 (broker 50k + NOC 100k)
- Net sale proceeds: AED -50,000 ✅ (allowed)

---

## 18. MULTI-YEAR RENTAL INPUT

V1.3 uses `CONSTANT_ANNUAL` design. Rental escalation is NOT implemented.

```
RENTAL_GROWTH_ASSUMPTION_INTRODUCED = 0 ✅
```

Future cumulative rental concept (NOT calculated yet):
```
cumulative_net_rental_income = annual_net_rental_income * holding_period_years
```

---

## 19. NET RENTAL INPUT DEPENDENCY

The frozen operating-cost demo layer is NOT modified. Future Full ROI eligibility requires `calculation_level = NET_RENTAL`.

If property has `SERVICE_CHARGE_ADJUSTED` or `PARTIAL_OPERATING_COSTS`, Full ROI remains incomplete. No substitution with Gross Yield.

```
GROSS_RENTAL_USED_AS_NET_RENTAL_INPUT = 0 ✅
SERVICE_CHARGE_INCOME_USED_AS_NET_RENTAL_INPUT = 0 ✅
```

---

## 20. SCENARIO CONTEXT

Isolated package — does NOT modify acquisition cost formulas.

### Files Created

| File | Role |
|------|------|
| `investor_api/roi/roi_scenario_models.py` | Holding period, exit value, selling costs, readiness models |
| `investor_api/roi/roi_scenario_validation.py` | All input validations |
| `investor_api/roi/roi_scenario_calculator.py` | Exit price derivation, selling costs, net sale proceeds, readiness |
| `investor_api/roi/roi_scenario_user_input_store.py` | Ephemeral in-memory store |

---

## 21. EPHEMERAL STORAGE

```
PERSISTENCE_MODE = EPHEMERAL_USER_SESSION
```

- Keyed by `(user_scope, property_id)`
- NOT written to MASTER, Qdrant, Mollak, rental evidence, SC provider, or acquisition rules
- No authentication

---

## 22. SHADOW API CONTEXT

```json
{
  "holding_period": {
    "status": "AVAILABLE|MISSING",
    "months": null,
    "years": null,
    "source": "USER_INPUT|MISSING"
  },
  "exit_value": {
    "status": "AVAILABLE|MISSING",
    "mode": "USER_EXIT_PRICE|USER_APPRECIATION_RATE|null",
    "exit_sale_price_aed": null,
    "annual_appreciation_rate_pct": null,
    "source": "USER_INPUT|DERIVED|MISSING",
    "rate_source": "USER_INPUT|null",
    "exit_price_source": "USER_INPUT|DERIVED|null"
  },
  "selling_costs": {
    "calculation_level": "NO_SELLING_COSTS|PARTIAL_SELLING_COSTS|COMPLETE_SELLING_COSTS",
    "broker": {...},
    "noc": {...},
    "other": {...},
    "complete_selling_costs_aed": null
  },
  "net_sale_proceeds_aed": null,
  "roi_input_readiness": "INCOMPLETE|READY_FOR_FULL_ROI_CALCULATION|NOT_EVALUATED_OFFPLAN",
  "missing_roi_inputs": [...]
}
```

---

## 23. ROI INPUT READINESS

| State | Condition |
|-------|-----------|
| `INCOMPLETE` | Any required input missing |
| `READY_FOR_FULL_ROI_CALCULATION` | All inputs available |
| `NOT_EVALUATED_OFFPLAN` | Offplan property |

### READY requires ALL of:
1. COMPLETE_ACQUISITION_COSTS
2. NET_RENTAL (not GROSS_RENTAL, not SERVICE_CHARGE_ADJUSTED)
3. Holding period
4. Exit sale price
5. COMPLETE_SELLING_COSTS

**Full ROI is NOT calculated even when READY.**

---

## 24. READINESS USES ACTUAL CONTEXT

Readiness is determined by checking actual backend contexts, not inferred from property ID or status alone.

```
ROI_INPUT_READINESS_FALSE_POSITIVE = 0 ✅
ROI_INPUT_READINESS_FALSE_NEGATIVE = 0 ✅
```

---

## 25. READY ONLY

Full ROI V1 remains READY_ONLY. Offplan → `NOT_EVALUATED_OFFPLAN`.

```
OFFPLAN_FULL_ROI_SCENARIO_CALCULATED = 0 ✅
```

---

## 26. TEST CASES (A-R)

All 18 tests pass:

| Test | Description | Result |
|------|-------------|--------|
| A | No scenario inputs → INCOMPLETE | PASS ✅ |
| B | Holding period only → INCOMPLETE | PASS ✅ |
| C | Holding + user exit price → INCOMPLETE (selling missing) | PASS ✅ |
| D | Holding + appreciation rate → exit price derived correctly | PASS ✅ |
| E | Negative appreciation → price decreases, not clamped | PASS ✅ |
| F | Both exit price and appreciation → 422 | PASS ✅ |
| G | Selling broker only → PARTIAL_SELLING_COSTS | PASS ✅ |
| H | NO_SELLING_BROKER_COST → broker = 0, explicit | PASS ✅ |
| I | All selling costs complete → COMPLETE + net_sale_proceeds | PASS ✅ |
| J | Missing NOC → remain incomplete | PASS ✅ |
| K | NO_NOC_FEE explicit → 0 accepted | PASS ✅ |
| L | Missing other selling cost → remain incomplete | PASS ✅ |
| M | NO_OTHER_SELLING_COSTS explicit → 0 accepted | PASS ✅ |
| N | Negative selling cost → 422 | PASS ✅ |
| O | Offplan property → NOT_EVALUATED_OFFPLAN | PASS ✅ |
| P | Scenario complete, acquisition incomplete → INCOMPLETE | PASS ✅ |
| Q | Acquisition + scenario complete, NET_RENTAL missing → INCOMPLETE | PASS ✅ |
| R | All complete → READY_FOR_FULL_ROI_CALCULATION (no ROI value) | PASS ✅ |

```
ALL_TESTS_PASS = 1 ✅
```

### Test D Details (Appreciation Derivation)

- Price: AED 2,700,000
- Rate: 5% over 5 years
- Expected: 2,700,000 * 1.05^5 = AED 3,445,960.22
- Result: AED 3,445,960.22 ✅
- rate_source: USER_INPUT
- exit_price_source: DERIVED

### Test I Details (Complete Selling Costs)

- Exit: AED 3,500,000
- Broker (2%): AED 70,000
- NOC: AED 5,000
- Other: AED 0 (NO_OTHER_SELLING_COSTS)
- Complete selling costs: AED 75,000
- Net sale proceeds: AED 3,425,000 ✅

---

## 27. NO FRONTEND ROI UI

No Full ROI card built. Shadow/backend testing only. No calculated Full ROI displayed.

---

## 28. FRONTEND MATH SAFETY

Backend calculates all derived values. Frontend sends raw inputs only.

```
FRONTEND_EXIT_VALUE_CALCULATION = 0 ✅
FRONTEND_SELLING_BROKER_CALCULATION = 0 ✅
FRONTEND_SELLING_COST_TOTAL_CALCULATION = 0 ✅
FRONTEND_NET_SALE_PROCEEDS_CALCULATION = 0 ✅
```

---

## 29. ACQUISITION V1.2 REGRESSION

| Counter | Value |
|---------|-------|
| V13_CHANGED_DLD_RULE | 0 ✅ |
| V13_CHANGED_TITLE_DEED_FEE | 0 ✅ |
| V13_CHANGED_KNOWLEDGE_FEE | 0 ✅ |
| V13_CHANGED_INNOVATION_FEE | 0 ✅ |
| V13_CHANGED_ACQUISITION_COMPLETENESS | 0 ✅ |
| V13_CHANGED_TOTAL_CASH_INVESTED_FORMULA | 0 ✅ |

---

## 30. RENTAL / SC REGRESSION

| Counter | Value |
|---------|-------|
| V13_CHANGED_ANNUAL_RENT | 0 ✅ |
| V13_CHANGED_GROSS_YIELD | 0 ✅ |
| V13_CHANGED_SC_ELIGIBILITY | 0 ✅ |
| V13_CHANGED_SC_RATE | 0 ✅ |
| V13_CHANGED_INCOME_AFTER_SC | 0 ✅ |
| V13_CHANGED_YIELD_AFTER_SC | 0 ✅ |
| V13_CHANGED_NET_RENTAL_FORMULA | 0 ✅ |

---

## 31. SALES / SIGNAL / FIT REGRESSION

| Counter | Value |
|---------|-------|
| V13_CHANGED_MARKET_CONTEXT | 0 ✅ |
| V13_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| V13_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| V13_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| V13_CHANGED_FIT_SCORE | 0 ✅ |

---

## 32. SAFETY COUNTERS

| Counter | Value |
|---------|-------|
| DEFAULT_HOLDING_PERIOD_USED | 0 ✅ |
| DEFAULT_APPRECIATION_USED | 0 ✅ |
| MARKET_BENCHMARK_USED_AS_FUTURE_EXIT_PRICE | 0 ✅ |
| NEGATIVE_APPRECIATION_CLAMPED | 0 ✅ |
| APPRECIATION_SILENTLY_CLAMPED | 0 ✅ |
| DEFAULT_SELLING_BROKER_COMMISSION_USED | 0 ✅ |
| AUTO_NO_SELLING_BROKER_ASSUMPTION | 0 ✅ |
| DEFAULT_NOC_FEE_USED | 0 ✅ |
| MISSING_SELLING_COST_COERCED_TO_ZERO | 0 ✅ |
| NEGATIVE_NET_SALE_PROCEEDS_CLAMPED | 0 ✅ |
| RENTAL_GROWTH_ASSUMPTION_INTRODUCED | 0 ✅ |
| GROSS_RENTAL_USED_AS_NET_RENTAL_INPUT | 0 ✅ |
| SERVICE_CHARGE_INCOME_USED_AS_NET_RENTAL_INPUT | 0 ✅ |
| ROI_INPUT_READINESS_FALSE_POSITIVE | 0 ✅ |
| ROI_INPUT_READINESS_FALSE_NEGATIVE | 0 ✅ |
| OFFPLAN_FULL_ROI_SCENARIO_CALCULATED | 0 ✅ |
| V13_AUTH_CHANGES | 0 ✅ |

**All 35 counters (18 regression + 17 safety) = 0.**

---

## 33. OUTPUT FILES

| File | Description |
|------|-------------|
| `roi_outputs/FULL_PROPERTY_ROI_V1_3_SCENARIO_INPUTS_REPORT.md` | This report |
| `roi_outputs/full_property_roi_v1_3_scenario_test_cases.json` | Test case results (A-R) |
| `roi_outputs/full_property_roi_v1_3_scenario_verdict.json` | Verdict + summary |

---

## 34. FINAL VERDICT

### **FULL_PROPERTY_ROI_V1_3_SCENARIO_INPUT_LAYER_VERIFIED**

| Metric | Value |
|--------|-------|
| ALL_TESTS_PASS | 1 ✅ (18/18) |
| All regression counters | 0 ✅ (18) |
| All safety counters | 0 ✅ (17) |
| Holding period model | VERIFIED ✅ |
| Exit value modes | VERIFIED ✅ |
| Appreciation semantics | VERIFIED ✅ |
| Selling cost model | VERIFIED ✅ |
| Completion rules | VERIFIED ✅ |
| Net sale proceeds calculation | VERIFIED ✅ |
| ROI input readiness logic | VERIFIED ✅ |
| No Full ROI calculated | VERIFIED ✅ |

### NOT DONE

- No Full Property ROI calculation
- No capital return
- No total return
- No annualized return
- No IRR
- No default appreciation
- No DLD benchmark as future price
- No rental growth
- No mortgage ROI
- No acquisition V1.2 formula modification
- No rental stack modification
- No Service Charge V2 modification
- No Investor Fit modification
- No authentication
- No frontend UI
