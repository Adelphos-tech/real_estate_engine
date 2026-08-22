# FULL PROPERTY ROI V1.4 — SHADOW CALCULATOR + FORMULA VERIFICATION

**Date**: 2026-08-22
**Phase**: FULL_PROPERTY_ROI_V1_4_SHADOW
**Verdict**: `FULL_PROPERTY_ROI_V1_4_SHADOW_VERIFIED`
**Methodology Version**: `FULL_PROPERTY_ROI_V1`

---

## 1. GOAL

Build the first Full Property ROI calculation engine. SHADOW ONLY. No frontend ROI card. No production freeze.

**Status: VERIFIED.** All 20 test cases pass. All 42 counters zero. Canonical trace produced.

---

## 2. METHODOLOGY

| Field | Value |
|-------|-------|
| Methodology Version | FULL_PROPERTY_ROI_V1 |
| ROI Type | UNLEVERED_TOTAL_ROI |
| Rental Assumption | CONSTANT_ANNUAL_NET_RENTAL |
| Architecture | UNLEVERED, READY_ONLY, TOTAL_ROI_ONLY, DEMO_ONLY_EPHEMERAL |
| ROI Label | "Full Property ROI" |
| ROI Description | "Total unlevered return over the selected holding period." |

---

## 3. CANONICAL INPUTS

| Input | Source | Phase |
|-------|--------|-------|
| A. Purchase Price | MASTER current_price_aed | V1.1 |
| B. Complete Acquisition Costs | V1.2 complete_acquisition_costs_aed | V1.2 |
| C. Total Cash Invested | V1.2 total_cash_invested_aed | V1.2 |
| D. Annual Net Rental Income | Operating-cost context (NET_RENTAL) | Frozen demo |
| E. Holding Period | V1.3 holding_period_months/years | V1.3 |
| F. Exit Sale Price | V1.3 exit_sale_price_aed | V1.3 |
| G. Complete Selling Costs | V1.3 complete_selling_costs_aed | V1.3 |
| H. Net Sale Proceeds | V1.3 net_sale_proceeds_aed | V1.3 |

Does NOT independently recalculate upstream values.

---

## 4. READINESS GATE

Before ROI calculation, ALL must be true:

| Condition | Check |
|-----------|-------|
| Property status | Ready |
| Acquisition level | COMPLETE_ACQUISITION_COSTS |
| Total cash invested | != null, > 0 |
| Operating-cost level | NET_RENTAL |
| Net rental income | != null |
| Holding period months | > 0 |
| Exit sale price | != null |
| Selling cost level | COMPLETE_SELLING_COSTS |
| Net sale proceeds | != null |
| ROI input readiness | READY_FOR_FULL_ROI_CALCULATION |

If any fails: `calculation_status = INCOMPLETE`, all ROI outputs null.

```
FULL_ROI_CALCULATED_WHILE_INPUTS_INCOMPLETE = 0 ✅
```

---

## 5. CONSTANT ANNUAL NET RENTAL MODEL

```
cumulative_net_rental_income_aed =
    net_rental_income_aed * holding_period_months / 12
```

No rent growth. No inflation. No annual escalation. Allows 6, 18, 30 months etc. Does NOT round holding period to whole years.

```
HOLDING_PERIOD_ROUNDED_TO_WHOLE_YEARS = 0 ✅
RENTAL_GROWTH_USED_IN_FULL_ROI_V1 = 0 ✅
```

---

## 6. TOTAL CASH INVESTED (DENOMINATOR)

```
total_cash_invested_aed =
    purchase_price_aed + complete_acquisition_costs_aed
```

Uses V1.2 verified value. Does NOT add service charges, vacancy, management, or maintenance (already deducted in Net Rental Income).

```
OPERATING_COST_DOUBLE_COUNTED_IN_DENOMINATOR = 0 ✅
```

---

## 7. NET SALE PROCEEDS

```
net_sale_proceeds_aed =
    exit_sale_price_aed - complete_selling_costs_aed
```

Uses V1.3 value. Selling costs not deducted again downstream.

```
SELLING_COST_DOUBLE_COUNTED = 0 ✅
```

---

## 8. CAPITAL RETURN

```
capital_return_aed =
    net_sale_proceeds_aed - total_cash_invested_aed
```

Can be positive, zero, or negative. NOT clamped.

---

## 9. TOTAL RETURN

```
total_return_aed =
    cumulative_net_rental_income_aed + capital_return_aed
```

### Identity Verification

Both formulations produce the same result:

```
Form 1: cumulative_rental + capital_return
Form 2: cumulative_rental + net_sale_proceeds - total_cash_invested
```

```
TOTAL_RETURN_IDENTITY_MISMATCH = 0 ✅
```

---

## 10. FULL PROPERTY ROI

```
full_property_roi_pct =
    total_return_aed / total_cash_invested_aed * 100
```

Only if `total_cash_invested_aed > 0`. Does NOT use purchase price alone as denominator.

```
PURCHASE_PRICE_ONLY_USED_AS_ROI_DENOMINATOR = 0 ✅
```

---

## 11. TOTAL ROI ONLY

This is **TOTAL ROI over the user-selected holding period**. NOT annualized ROI, CAGR, IRR, cash-on-cash, or leveraged return.

```
TOTAL_ROI_MISLABELED_AS_ANNUALIZED = 0 ✅
IRR_CALCULATED_IN_V1 = 0 ✅
```

---

## 12. NO LEVERAGE

V1 remains UNLEVERED. No mortgage, down payment, interest, loan principal, loan fees, mortgage registration, balloon payment, or loan payoff.

```
FINANCING_INCLUDED_IN_UNLEVERED_ROI = 0 ✅
```

---

## 13. EXIT APPRECIATION PROVENANCE

If exit price was derived from appreciation:
- `annual_appreciation_rate_pct` = USER_INPUT
- `exit_sale_price_aed` = DERIVED

NOT relabeled as forecast, predicted value, APIL estimate, or market expectation.

```
USER_APPRECIATION_PRESENTED_AS_MARKET_FORECAST = 0 ✅
```

---

## 14. NEGATIVE ROI

Negative `capital_return_aed`, `total_return_aed`, and `full_property_roi_pct` are allowed. NOT clamped.

```
NEGATIVE_FULL_ROI_CLAMPED = 0 ✅
```

---

## 15. ROI ABOVE 100%

ROI >100% is allowed if valid inputs mathematically produce it. NOT clamped.

```
FULL_ROI_ABOVE_100_CLAMPED = 0 ✅
```

---

## 16. OFFPLAN

Offplan → `NOT_EVALUATED_OFFPLAN`. All ROI numeric outputs null. No future rental, project benchmark, or offplan projected appreciation substituted.

```
OFFPLAN_FULL_ROI_CALCULATED = 0 ✅
```

---

## 17. PARTIAL INPUTS

| Condition | Result |
|-----------|--------|
| SERVICE_CHARGE_ADJUSTED | INCOMPLETE |
| PARTIAL_OPERATING_COSTS | INCOMPLETE |
| GROSS_RENTAL | INCOMPLETE |
| PARTIAL_ACQUISITION_COSTS | INCOMPLETE |
| PARTIAL_SELLING_COSTS | INCOMPLETE |

```
NON_NET_RENTAL_USED_IN_FULL_ROI = 0 ✅
INCOMPLETE_ACQUISITION_USED_IN_FULL_ROI = 0 ✅
INCOMPLETE_SELLING_COSTS_USED_IN_FULL_ROI = 0 ✅
```

---

## 18. ROUNDING

- Internal calculations use unrounded source values
- Display/output: AED values at 2 decimal places, ROI at 2 decimal places
- No stepwise rounding that changes ROI

```
STEPWISE_ROUNDING_CHANGED_ROI = 0 ✅
```

---

## 19. CANONICAL TRACE — PROPERTY 409

### Step 1: Acquisition (V1.2)

| Component | Amount (AED) | Source |
|-----------|-------------|--------|
| Purchase Price | 2,700,000.00 | MASTER |
| DLD Buyer Cost (2%) | 54,000.00 | OFFICIAL_DLD_RERA (USER_CONFIRMED_DEFAULT) |
| Trustee Fee | 4,000.00 | USER_INPUT |
| Title Deed Fee | 250.00 | OFFICIAL_DLD_RERA |
| Knowledge Fee | 10.00 | OFFICIAL_DLD_RERA |
| Innovation Fee | 10.00 | OFFICIAL_DLD_RERA |
| Broker Purchase (2%) | 54,000.00 | USER_INPUT |
| Developer/Admin | 0.00 | USER_INPUT (NO_DEVELOPER_ADMIN_FEE) |
| **Complete Acquisition Costs** | **112,270.00** | |
| **Total Cash Invested** | **2,812,270.00** | |

### Step 2: Scenario (V1.3)

| Component | Value | Source |
|-----------|-------|--------|
| Annual Net Rental Income | 130,000.00 | OPERATING_COST_CONTEXT (NET_RENTAL) |
| Holding Period | 60 months (5.0 years) | USER_INPUT |
| Exit Sale Price | 3,500,000.00 | USER_INPUT (USER_EXIT_PRICE) |
| Selling Broker (2%) | 70,000.00 | USER_INPUT |
| NOC Fee | 5,000.00 | USER_INPUT |
| Other Selling | 0.00 | USER_INPUT (NO_OTHER_SELLING_COSTS) |
| **Complete Selling Costs** | **75,000.00** | |
| **Net Sale Proceeds** | **3,425,000.00** | |
| ROI Input Readiness | READY_FOR_FULL_ROI_CALCULATION | |

### Step 3: Full ROI (V1.4)

| Output | Value | Formula |
|--------|-------|---------|
| Cumulative Net Rental | 650,000.00 | 130,000 * 60/12 |
| Capital Return | 612,730.00 | 3,425,000 - 2,812,270 |
| Total Return | 1,262,730.00 | 650,000 + 612,730 |
| **Full Property ROI** | **44.90%** | 1,262,730 / 2,812,270 * 100 |

### Identity Verification

- Form 1: 650,000 + 612,730 = 1,262,730 ✅
- Form 2: 650,000 + 3,425,000 - 2,812,270 = 1,262,730 ✅
- Match: YES ✅

---

## 20. INCLUDED COMPONENTS

- Purchase price
- Verified/user-confirmed acquisition costs
- Net Rental Income
- Holding period
- Exit sale price
- Selling costs

---

## 21. EXCLUDED COMPONENTS

- Financing/leverage
- Mortgage interest
- Rental growth
- Tax assumptions (income tax, capital gains tax)
- Discounted cash flow
- IRR
- Time-value-of-money adjustment

---

## 22. TEST CASES (A-T)

All 20 tests pass:

| Test | Description | Result |
|------|-------------|--------|
| A | No inputs → INCOMPLETE, all null | PASS ✅ |
| B | Acquisition complete only → INCOMPLETE | PASS ✅ |
| C | Acquisition + NET_RENTAL only → INCOMPLETE | PASS ✅ |
| D | Everything except selling costs → INCOMPLETE | PASS ✅ |
| E | Everything complete → CALCULATED (ROI=44.90%) | PASS ✅ |
| F | 6-month holding → cumulative = annual * 0.5 | PASS ✅ |
| G | 18-month holding → cumulative = annual * 1.5 | PASS ✅ |
| H | Negative capital return, positive rental → actual total | PASS ✅ |
| I | Overall negative ROI → preserved (-49.15%) | PASS ✅ |
| J | ROI >100% → not clamped (133.80%) | PASS ✅ |
| K | Exit = purchase price → capital return = -187,270 (not 0) | PASS ✅ |
| L | Zero selling costs → valid calculation | PASS ✅ |
| M | Custom DLD 4% → uses V1.2 TCI exactly | PASS ✅ |
| N | USER_APPRECIATION_RATE → uses V1.3 derived exit | PASS ✅ |
| O | Direct USER_EXIT_PRICE → uses user price exactly | PASS ✅ |
| P | No verified SC → INCOMPLETE | PASS ✅ |
| Q | Offplan → NOT_EVALUATED_OFFPLAN | PASS ✅ |
| R | Negative net rental → cumulative negative, not clamped | PASS ✅ |
| S | Repeated calls → deterministic | PASS ✅ |
| T | Formula identity → both forms match | PASS ✅ |

```
ALL_TESTS_PASS = 1 ✅
```

---

## 23. FULL ROI COVERAGE

Across 321 Ready properties with NO demo user inputs:

| Metric | Count |
|--------|-------|
| FULL_ROI_CALCULABLE_COUNT (no user inputs) | 0 |
| FULL_ROI_CALCULABLE_COUNT (with explicit test scenario) | 1 (property 409) |

No batch-populated assumptions.

---

## 24. ACQUISITION REGRESSION

| Counter | Value |
|---------|-------|
| ROI_V1_CHANGED_DLD_RULE | 0 ✅ |
| ROI_V1_CHANGED_TITLE_DEED_FEE | 0 ✅ |
| ROI_V1_CHANGED_KNOWLEDGE_FEE | 0 ✅ |
| ROI_V1_CHANGED_INNOVATION_FEE | 0 ✅ |
| ROI_V1_CHANGED_ACQUISITION_COMPLETENESS | 0 ✅ |
| ROI_V1_CHANGED_TOTAL_CASH_INVESTED | 0 ✅ |

---

## 25. SC / RENTAL / NET REGRESSION

| Counter | Value |
|---------|-------|
| ROI_V1_CHANGED_ANNUAL_RENT | 0 ✅ |
| ROI_V1_CHANGED_GROSS_YIELD | 0 ✅ |
| ROI_V1_CHANGED_SC_ELIGIBILITY | 0 ✅ |
| ROI_V1_CHANGED_SC_RATE | 0 ✅ |
| ROI_V1_CHANGED_INCOME_AFTER_SC | 0 ✅ |
| ROI_V1_CHANGED_YIELD_AFTER_SC | 0 ✅ |
| ROI_V1_CHANGED_NET_RENTAL_FORMULA | 0 ✅ |

---

## 26. SCENARIO REGRESSION

| Counter | Value |
|---------|-------|
| ROI_V1_CHANGED_HOLDING_PERIOD_RULE | 0 ✅ |
| ROI_V1_CHANGED_EXIT_VALUE_RULE | 0 ✅ |
| ROI_V1_CHANGED_APPRECIATION_FORMULA | 0 ✅ |
| ROI_V1_CHANGED_SELLING_COST_COMPLETENESS | 0 ✅ |
| ROI_V1_CHANGED_NET_SALE_PROCEEDS | 0 ✅ |

---

## 27. SALES / SIGNAL / FIT REGRESSION

| Counter | Value |
|---------|-------|
| ROI_V1_CHANGED_MARKET_CONTEXT | 0 ✅ |
| ROI_V1_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| ROI_V1_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| ROI_V1_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| ROI_V1_CHANGED_FIT_SCORE | 0 ✅ |

Full Property ROI does NOT affect Investor Fit.

---

## 28. SAFETY COUNTERS

| Counter | Value |
|---------|-------|
| FULL_ROI_CALCULATED_WHILE_INPUTS_INCOMPLETE | 0 ✅ |
| HOLDING_PERIOD_ROUNDED_TO_WHOLE_YEARS | 0 ✅ |
| RENTAL_GROWTH_USED_IN_FULL_ROI_V1 | 0 ✅ |
| OPERATING_COST_DOUBLE_COUNTED_IN_DENOMINATOR | 0 ✅ |
| SELLING_COST_DOUBLE_COUNTED | 0 ✅ |
| TOTAL_RETURN_IDENTITY_MISMATCH | 0 ✅ |
| PURCHASE_PRICE_ONLY_USED_AS_ROI_DENOMINATOR | 0 ✅ |
| TOTAL_ROI_MISLABELED_AS_ANNUALIZED | 0 ✅ |
| IRR_CALCULATED_IN_V1 | 0 ✅ |
| FINANCING_INCLUDED_IN_UNLEVERED_ROI | 0 ✅ |
| USER_APPRECIATION_PRESENTED_AS_MARKET_FORECAST | 0 ✅ |
| NEGATIVE_FULL_ROI_CLAMPED | 0 ✅ |
| FULL_ROI_ABOVE_100_CLAMPED | 0 ✅ |
| OFFPLAN_FULL_ROI_CALCULATED | 0 ✅ |
| NON_NET_RENTAL_USED_IN_FULL_ROI | 0 ✅ |
| INCOMPLETE_ACQUISITION_USED_IN_FULL_ROI | 0 ✅ |
| INCOMPLETE_SELLING_COSTS_USED_IN_FULL_ROI | 0 ✅ |
| STEPWISE_ROUNDING_CHANGED_ROI | 0 ✅ |
| ROI_V1_AUTH_CHANGES | 0 ✅ |

**All 42 counters (23 regression + 19 safety) = 0.**

---

## 29. BACKEND PACKAGE

### New Files (V1.4)

| File | Role |
|------|------|
| `investor_api/roi/full_roi_models.py` | ROI output models, provenance, included/excluded |
| `investor_api/roi/full_roi_validation.py` | Readiness gate |
| `investor_api/roi/full_roi_calculator.py` | Calculation engine + identity verification |

### Isolation

Does NOT modify:
- Rental engine
- Service-charge provider
- Operating-cost calculator
- Acquisition calculator (V1.2)
- Scenario calculator (V1.3)
- Investor Fit

---

## 30. NO FRONTEND

No FullROICard, ROI chart, ROI badge, ROI ranking, or Investor Fit integration. Backend/shadow only.

---

## 31. OUTPUT FILES

| File | Description |
|------|-------------|
| `roi_outputs/FULL_PROPERTY_ROI_V1_4_SHADOW_REPORT.md` | This report |
| `roi_outputs/full_property_roi_v1_4_test_cases.json` | Test case results (A-T) |
| `roi_outputs/full_property_roi_v1_4_canonical_trace.json` | Property 409 canonical trace |
| `roi_outputs/full_property_roi_v1_4_verdict.json` | Verdict + summary |

---

## 32. FINAL VERDICT

### **FULL_PROPERTY_ROI_V1_4_SHADOW_VERIFIED**

| Metric | Value |
|--------|-------|
| ALL_TESTS_PASS | 1 ✅ (20/20) |
| All regression counters | 0 ✅ (23) |
| All safety counters | 0 ✅ (19) |
| Total counters | 42/42 zero ✅ |
| Canonical trace | Produced ✅ |
| Formula identity | Verified ✅ |
| Readiness gate | Enforced ✅ |
| No frontend | Verified ✅ |
| No auth | Verified ✅ |

### NOT DONE

- No Full ROI frontend UI
- No Full ROI production freeze
- No annualized ROI / CAGR / IRR
- No mortgage/leverage
- No rental growth
- No Investor Fit changes
- No acquisition V1.2 modification
- No scenario V1.3 modification
- No rental methodology modification
- No Service Charge V2 modification
- No authentication
