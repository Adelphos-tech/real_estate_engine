# FULL PROPERTY ROI V1 — INPUT DATA AUDIT + METHODOLOGY DESIGN

**Date**: 2026-08-22
**Phase**: FULL_PROPERTY_ROI_V1_INPUT_AUDIT
**Verdict**: `FULL_PROPERTY_ROI_V1_INPUT_AUDIT_COMPLETE`
**Status**: RESEARCH / INPUT AUDIT ONLY — No implementation

---

## 1. GOAL

Determine whether APIL has enough verified data to calculate a defensible Full Property ROI.

**Answer: NO.** Full ROI is not calculable for any property with current data. This is not a failure — it identifies what input layer must be built next.

---

## 2. ROI MODEL — UNLEVERED

This audit covers **UNLEVERED** property ROI only. No mortgage/leverage.

### Canonical Formula

```
total_cash_invested_aed = purchase_price_aed + acquisition_costs_aed

cumulative_net_rental_income_aed = net_rental_income_aed * holding_period_years
  (V1: constant annual — no rental escalation)

net_sale_proceeds_aed = exit_sale_price_aed - selling_costs_aed

total_return_aed = cumulative_net_rental_income_aed + net_sale_proceeds_aed - total_cash_invested_aed

full_property_roi_pct = total_return_aed / total_cash_invested_aed * 100
```

### Decomposition (mathematically identical)

```
capital_return_aed = net_sale_proceeds_aed - purchase_price_aed - acquisition_costs_aed
rental_return_aed = cumulative_net_rental_income_aed
total_return_aed = capital_return_aed + rental_return_aed
```

### Double-Counting Check

- Acquisition costs appear in denominator (total_cash_invested) — NOT subtracted from net rental income
- Recurring operating costs (vacancy, management, maintenance, SC) are already inside net_rental_income — NOT subtracted again
- No double counting

### Sign Convention

- Positive return = profit
- Negative return = loss
- No clamping to zero

---

## 3. REQUIRED INPUT CATEGORIES — AUDIT RESULTS

### A. PROPERTY PURCHASE PRICE

| Field | Value |
|-------|-------|
| Source | MASTER `current_price_aed` |
| Availability | 2614/2614 (100%) |
| Nulls | 0 |
| Zeros | 0 |
| Range | AED 90,000 – AED 299,500,000 |
| Classification | VERIFIED_PROPERTY_FACT |

**DLD benchmark is NOT substituted for subject purchase price.** ✅

### B. ACQUISITION COSTS

| Cost | Source | Classification | In System? |
|------|--------|---------------|------------|
| DLD transfer fee (4%) | OFFICIAL_DLD_RERA — Executive Council Resolution No. 30 of 2013 | OFFICIAL_VERIFIED | NO — not stored/calculated |
| Title deed fee (AED 540) | OFFICIAL_DLD_RERA | OFFICIAL_VERIFIED | NO |
| Trustee office fee (AED 2,000/4,000) | OFFICIAL_DLD_RERA | OFFICIAL_VERIFIED | NO |
| Knowledge fee (AED 10) | OFFICIAL_DLD_RERA | OFFICIAL_VERIFIED | NO |
| Innovation fee (AED 10) | OFFICIAL_DLD_RERA | OFFICIAL_VERIFIED | NO |
| Broker purchase commission | Contractual — no statutory rate | USER_INPUT | NO |
| Mortgage registration | N/A for unlevered | NOT_APPLICABLE | N/A |

**DLD 4% is a statutory rate** (not an assumption). It can be DERIVED from `purchase_price_aed * 0.04`.

**Broker commission has no legal maximum/minimum** — it is regulated contractually. Market standard is 2% but must NOT be defaulted.

```
DEFAULT_BROKER_COMMISSION_USED = 0 ✅
```

### C. HOLDING PERIOD

| Field | Value |
|-------|-------|
| Source | USER_INPUT |
| Availability | 0/2614 — no field exists |
| Classification | USER_INPUT |

Full ROI requires an explicit holding period. Do NOT assume 1/3/5 years.

### D. NET RENTAL INCOME DURING HOLD

| Condition | Count |
|-----------|-------|
| Annual rent available | 300/2614 (283/321 Ready) |
| SC production eligible | 12/2614 (12/321 Ready) |
| Both prerequisites met | 12/2614 |
| Net rental income available (with user inputs) | 0/2614 |

Net Rental Income is available ONLY when `calculation_level == NET_RENTAL`, which requires:
- annual rent (frozen) ✅ for 300 properties
- verified official SC (frozen V2) ✅ for 12 properties
- vacancy (user input, ephemeral) — not persisted
- management (user input, ephemeral) — not persisted
- maintenance (user input, ephemeral) — not persisted

**Gross Rental Yield and Income After Service Charges are NOT substitutes for Net Rental Income.**

### E. EXIT / SALE VALUE

| Field | Value |
|-------|-------|
| Source | USER_INPUT |
| Availability | 0/2614 — no field exists |
| Classification | USER_INPUT |

**DLD benchmark, APIL Advantage, current asking price, and market-context estimates are NOT used as future sale value.**

```
MARKET_BENCHMARK_USED_AS_FUTURE_EXIT_PRICE = 0 ✅
```

### V1 Exit Value Modes

| Mode | Description |
|------|-------------|
| `USER_ENTERED_EXIT_PRICE` | User enters expected sale price |
| `USER_ENTERED_ANNUAL_APPRECIATION_RATE` | User enters annual appreciation % |
| `NO_EXIT_VALUE_AVAILABLE` | Cannot calculate capital return |

### F. SELLING COSTS

| Cost | Source | Classification | In System? |
|------|--------|---------------|------------|
| Broker selling commission (2% + VAT) | Contractual | USER_INPUT | NO |
| Developer NOC fee (AED 500–5,000) | Varies by developer | USER_INPUT | NO |
| DLD transfer fee on sale | Typically buyer pays | NOT_APPLICABLE_FOR_SELLER | N/A |

No universal selling-cost percentage is assumed.

### G. CAPITAL RETURN

```
capital_return_aed = net_sale_proceeds_aed - purchase_price_aed - acquisition_costs_aed
```

Classification: DERIVED

### H. TOTAL RETURN

```
total_return_aed = cumulative_net_rental_income_aed + net_sale_proceeds_aed - total_cash_invested_aed
```

Classification: DERIVED

---

## 4. DLD / GOVERNMENT FEES — RESEARCH

### DLD Transfer Fee

| Field | Value |
|-------|-------|
| Fee name | DLD Registration Fee (property sale transfer) |
| Rate | 4% of sale contract value |
| Legal basis | Executive Council Resolution No. 30 of 2013, Article 2 |
| Effective date | September 2013 (increased from previous 2%) |
| Payer | Legally 2% buyer + 2% seller; market practice: buyer pays full 4% |
| Source | Dubai Land Department official |

### Fixed Administrative Fees

| Fee | Amount | Source |
|-----|--------|--------|
| Title deed issuance | AED 540 (apartments AED 580, land AED 430) | DLD official schedule |
| Trustee office fee | AED 2,000 (<AED 500k) or AED 4,000 (≥AED 500k) + VAT | DLD trustee offices |
| Knowledge fee | AED 10 | DLD official |
| Innovation fee | AED 10 | DLD official |

### Broker Commission

| Field | Value |
|-------|-------|
| Legal limit | No statutory maximum or minimum |
| Regulation | Regulated contractually (RERA Form A/B) |
| Market standard (sales) | 2% of sale price (buyer) + 2% (seller) + 5% VAT |
| Source | RERA Real Estate Brokerage Practice Guide 2024 |
| V1 treatment | USER_INPUT — must not default |

---

## 5. MULTI-YEAR RENTAL INCOME

### Current Engine

The rental engine estimates **one annual rental level**. It does NOT project multi-year rent.

### V1 Recommendation: CONSTANT_ANNUAL_NET_RENTAL_INCOME

```
cumulative_net_rental_income_aed = net_rental_income_aed * holding_period_years
```

No rental escalation without explicit evidence/input.

### Future Options

| Option | Description | V1? |
|--------|-------------|-----|
| A. Constant annual | No growth | **RECOMMENDED** |
| B. User-entered growth | User provides annual growth rate | Future |
| C. Verified market model | Requires validated rental growth data | Future |

---

## 6. APPRECIATION

No default appreciation (5%, 8%, 10%) is invented.

```
DEFAULT_APPRECIATION_USED = 0 ✅
```

If appreciation mode exists, source must be explicit: `USER_INPUT` or `VERIFIED_FORECAST_MODEL`.

---

## 7. ANNUALIZED RETURN

### V1 Recommendation: TOTAL_ROI_ONLY

| Metric | V1? | Reason |
|--------|-----|--------|
| Total ROI | YES | Simple, no timing required |
| Annualized return (CAGR) | FUTURE | Requires holding period (user input) |
| IRR | FUTURE | Requires per-period cash-flow timing |

### IRR Requirement

IRR requires timing for: purchase, annual rent, service charges, operating costs, sale.

Current system has **no cash-flow timing**. Therefore:

```
IRR_WITHOUT_CASHFLOW_TIMING = 0 ✅
```

---

## 8. OFFPLAN TREATMENT

```
OFFPLAN_RENTAL_NOT_EVALUATED
```

Current rental engine does not project future rent for Offplan properties.

### V1 Recommendation: READY_ONLY

Full Property ROI V1 should be calculated for Ready properties only. Offplan requires a separate model.

| Status | Count | ROI V1? |
|--------|-------|---------|
| Ready | 321 | YES (if all inputs available) |
| Offplan | 2293 | NO — separate model needed |

---

## 9. INPUT MATRIX SUMMARY

### Across All 2614 Properties

| Input | Available | Missing |
|-------|-----------|---------|
| Purchase price | 2614 (100%) | 0 |
| Annual rent | 300 (11.5%) | 2314 |
| Verified service charge | 12 (0.5%) | 2602 |
| Net rental income | 0 (0%) | 2614 |
| Acquisition costs | 0 (0%) | 2614 |
| Broker purchase cost | 0 (0%) | 2614 |
| Holding period | 0 (0%) | 2614 |
| Exit value | 0 (0%) | 2614 |
| Selling costs | 0 (0%) | 2614 |
| **Full ROI calculable** | **0 (0%)** | **2614** |

### Ready Properties Only (321)

| Input | Available | Missing |
|-------|-----------|---------|
| Purchase price | 321 (100%) | 0 |
| Annual rent | 283 (88.2%) | 38 |
| Verified service charge | 12 (3.7%) | 309 |
| All prerequisites (price + rent + SC) | 12 (3.7%) | 309 |
| Net rental income (with user inputs) | 0 (0%) | 321 |
| Acquisition costs | 0 (0%) | 321 |
| Holding period | 0 (0%) | 321 |
| Exit value | 0 (0%) | 321 |
| Selling costs | 0 (0%) | 321 |
| **Full ROI calculable** | **0 (0%)** | **321** |

---

## 10. TOP MISSING INPUTS

| Missing Input | Properties Affected | Classification |
|---------------|---------------------|---------------|
| Net rental income | 2614/2614 | Requires user inputs (ephemeral) + SC (12 have it) |
| Acquisition costs | 2614/2614 | Not in system (DLD 4% is derivable but not stored) |
| Broker purchase cost | 2614/2614 | Not in system (USER_INPUT) |
| Holding period | 2614/2614 | Not in system (USER_INPUT) |
| Exit value | 2614/2614 | Not in system (USER_INPUT) |
| Selling costs | 2614/2614 | Not in system (USER_INPUT) |
| Verified service charge | 2602/2614 | Only 12 properties have SC V2 eligibility |
| Annual rent | 2314/2614 | 300 have rental estimates |

---

## 11. RECOMMENDED V1 ARCHITECTURE

### User-Input Fields (must not default)

| Field | Type | Required for ROI? |
|-------|------|-------------------|
| `holding_period_years` | number | YES |
| `vacancy_input` | already exists | YES (for net rental) |
| `management_input` | already exists | YES (for net rental) |
| `maintenance_input` | already exists | YES (for net rental) |
| `broker_purchase_commission_aed` or `_pct` | number | YES |
| `exit_value_mode` | enum | YES |
| `exit_sale_price_aed` | number | If USER_ENTERED_EXIT_PRICE |
| `annual_appreciation_rate_pct` | number | If USER_ENTERED_ANNUAL_APPRECIATION_RATE |
| `broker_selling_commission_aed` or `_pct` | number | YES |
| `developer_noc_fee_aed` | number | YES |

### Verified-Cost Fields (DERIVED from official rates)

| Field | Formula | Source |
|-------|---------|--------|
| `dld_transfer_fee_aed` | `purchase_price_aed * 0.04` | OFFICIAL_VERIFIED (statutory) |
| `title_deed_fee_aed` | `AED 540` (or AED 580 apartments) | OFFICIAL_VERIFIED |
| `trustee_office_fee_aed` | `AED 2000` if price < 500k, else `AED 4000` | OFFICIAL_VERIFIED |
| `knowledge_fee_aed` | `AED 10` | OFFICIAL_VERIFIED |
| `innovation_fee_aed` | `AED 10` | OFFICIAL_VERIFIED |

### ROI Formula (V1 Unlevered)

```
acquisition_costs_aed = dld_transfer_fee + title_deed_fee + trustee_office_fee
    + knowledge_fee + innovation_fee + broker_purchase_commission

total_cash_invested_aed = purchase_price_aed + acquisition_costs_aed

cumulative_net_rental_income_aed = net_rental_income_aed * holding_period_years

exit_sale_price_aed = user_entered_value OR
    purchase_price_aed * (1 + annual_appreciation_rate/100)^holding_period_years

selling_costs_aed = broker_selling_commission + developer_noc_fee

net_sale_proceeds_aed = exit_sale_price_aed - selling_costs_aed

total_return_aed = cumulative_net_rental_income_aed + net_sale_proceeds_aed
    - total_cash_invested_aed

full_property_roi_pct = total_return_aed / total_cash_invested_aed * 100
```

---

## 12. EVIDENCE / INPUT HIERARCHY

Every ROI field must track:

| Field | Purpose |
|-------|---------|
| `value` | The numeric value |
| `source` | MASTER / OFFICIAL_DLD_RERA / VERIFIED_EXTERNAL / USER_INPUT / DERIVED / MISSING |
| `status` | AVAILABLE / MISSING / NOT_APPLICABLE |
| `evidence_date` | When the data was verified |

**Never mix user assumptions with verified official facts.**

---

## 13. FROZEN LAYER REGRESSION

All counters zero — no frozen layer was modified.

| Counter | Value |
|---------|-------|
| ROI_AUDIT_CHANGED_ANNUAL_RENT | 0 ✅ |
| ROI_AUDIT_CHANGED_GROSS_YIELD | 0 ✅ |
| ROI_AUDIT_CHANGED_SC_ELIGIBILITY | 0 ✅ |
| ROI_AUDIT_CHANGED_SC_RATE | 0 ✅ |
| ROI_AUDIT_CHANGED_SC_ANNUAL | 0 ✅ |
| ROI_AUDIT_CHANGED_INCOME_AFTER_SC | 0 ✅ |
| ROI_AUDIT_CHANGED_YIELD_AFTER_SC | 0 ✅ |
| ROI_AUDIT_CHANGED_NET_RENTAL_FORMULA | 0 ✅ |
| ROI_AUDIT_CHANGED_MARKET_CONTEXT | 0 ✅ |
| ROI_AUDIT_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| ROI_AUDIT_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| ROI_AUDIT_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| ROI_AUDIT_CHANGED_FIT_SCORE | 0 ✅ |

### Safety Counters

| Counter | Value |
|---------|-------|
| ROI_AUDIT_AUTH_CHANGES | 0 ✅ |
| DEFAULT_BROKER_COMMISSION_USED | 0 ✅ |
| DEFAULT_APPRECIATION_USED | 0 ✅ |
| MARKET_BENCHMARK_USED_AS_FUTURE_EXIT_PRICE | 0 ✅ |
| IRR_WITHOUT_CASHFLOW_TIMING | 0 ✅ |

---

## 14. NO AUTH WORK

No authentication, login, signup, account database, or user persistence was added.

```
ROI_AUDIT_AUTH_CHANGES = 0 ✅
```

---

## 15. INVESTOR FIT

Full Property ROI must NOT affect Investor Fit in this phase.

```
ROI_AUDIT_CHANGED_FIT_SCORE = 0 ✅
```

---

## 16. OUTPUT FILES

| File | Description |
|------|-------------|
| `roi_outputs/FULL_PROPERTY_ROI_V1_INPUT_AUDIT.md` | This report |
| `roi_outputs/full_property_roi_v1_input_matrix.csv` | Per-property input availability matrix |
| `roi_outputs/full_property_roi_v1_methodology.json` | Methodology design (formula, fields, classifications) |
| `roi_outputs/full_property_roi_v1_verdict.json` | Verdict + summary statistics |

---

## 17. FINAL VERDICT

### **FULL_PROPERTY_ROI_V1_INPUT_AUDIT_COMPLETE**

| Metric | Value |
|--------|-------|
| READY_PROPERTY_COUNT | 321 |
| NET_RENTAL_INPUT_AVAILABLE_COUNT | 0 |
| PURCHASE_PRICE_AVAILABLE_COUNT | 2614 |
| ACQUISITION_COST_VERIFIED_COUNT | 0 |
| EXIT_VALUE_AVAILABLE_COUNT | 0 |
| SELLING_COST_AVAILABLE_COUNT | 0 |
| FULL_ROI_CALCULABLE_COUNT | 0 |

**FULL_ROI_CALCULABLE_COUNT = 0 is expected.** The audit identifies the input layers that must be built next:

1. **Acquisition cost layer** — DLD fees are derivable from statutory rates; broker commission needs user input
2. **Holding period input** — user-entered field
3. **Exit value input** — user-entered exit price or appreciation rate
4. **Selling cost layer** — broker commission + NOC fee need user input
5. **SC V2 coverage expansion** — only 12/321 Ready properties have verified SC
6. **Operating cost persistence** — currently ephemeral; needs to persist for ROI calculation

**NOT IMPLEMENTED. No ROI UI, no production ROI calculation, no frozen changes.**
