# FULL PROPERTY ROI V1.1 — VERIFIED ACQUISITION COST LAYER

**Date**: 2026-08-22
**Phase**: FULL_PROPERTY_ROI_V1_1_ACQUISITION_COST
**Verdict**: `FULL_PROPERTY_ROI_V1_1_ACQUISITION_COST_LAYER_VERIFIED`
**Methodology Version**: `ACQUISITION_COST_V1_1`

---

## 1. GOAL

Build and verify the acquisition-cost layer required for future Full Property ROI. Only include costs that are `OFFICIAL_VERIFIED` or explicit `USER_INPUT`. No invented transaction costs.

**Status: VERIFIED.** The acquisition-cost layer is built, tested, and verified.

---

## 2. PURCHASE PRICE

| Field | Value |
|-------|-------|
| Source | MASTER `current_price_aed` |
| Availability | 2614/2614 (100%) |
| Classification | VERIFIED_PROPERTY_FACT |

DLD benchmark, market estimate, APIL Advantage benchmark, and fallback estimates are NOT used as purchase price.

```
PURCHASE_PRICE_SOURCE_OVERRIDE = 0 ✅
```

---

## 3. ACQUISITION COST COMPONENTS

### A. DLD Transfer / Registration Fee

| Field | Value |
|-------|-------|
| Fee name | DLD Transfer / Registration Fee |
| Source | OFFICIAL_DLD_RERA |
| Legal basis | Executive Council Resolution No. 30 of 2013, Article 2, Schedule Item 1 |
| Effective date | 2013-09-18 |
| Calculation method | Percentage of sale contract value |
| Total rate | 4% |
| Status | OFFICIAL_VERIFIED |

### DLD Payer Responsibility — CRITICAL FINDING

**ECR 30/2013 Article 3(1):**

> "unless agreed otherwise, the Fee for the sale of Real Property will be shared equally by the seller and purchaser"

| Field | Value |
|-------|-------|
| DLD_TRANSFER_FEE_TOTAL_RATE | 4% |
| DLD_BUYER_STATUTORY_SHARE | 2% |
| DLD_SELLER_STATUTORY_SHARE | 2% |
| DLD_PAYER_ALLOCATION_STATUS | **CONTRACT_DEPENDENT** |

**The statute specifies joint/equal liability (2% each) unless the contract says otherwise.** Market practice commonly has the buyer pay the full 4%, but this is contractual, not statutory.

### Buyer ROI Principle

Full Property ROI acquisition cost contains only cash actually attributable to the investor/buyer. Seller costs are NOT counted as buyer acquisition cash.

**V1 Treatment:**
- Default: buyer's statutory share = 2% (OFFICIAL_DLD_RERA)
- User override: `dld_buyer_share_pct` can be set to 4% (USER_INPUT) if contract specifies buyer pays full 4%
- Never silently use 4% as buyer's cost without explicit user selection

```
SELLER_COST_INCLUDED_IN_BUYER_ACQUISITION = 0 ✅
```

### B. Trustee / Registration Office Fee

| Field | Value |
|-------|-------|
| Source | MISSING |
| Status | **MISSING** (not OFFICIAL_VERIFIED) |
| Reason | Trustee offices are private entities authorised by DLD. Their fees are NOT fixed by official government statute. |

**Market sources cite AED 2,000–4,000 but this is NOT verified from official statute.** The ECR 30/2013 fee schedule does not contain a trustee office fee item.

```
TRUSTEE_FEE_RULE_VERIFIED = NO
```

**V1 Treatment:** `USER_INPUT` — the investor must enter this fee if known. It is never defaulted.

### C. Title Deed Fee

| Field | Value |
|-------|-------|
| Fee name | Title Deed Issuance Fee |
| Source | OFFICIAL_DLD_RERA |
| Legal basis | ECR 30/2013, Schedule Item 22 |
| Amount | **AED 250** (not AED 540) |
| Status | OFFICIAL_VERIFIED |

**Previous research cited AED 540.** The official statute (ECR 30/2013 Schedule Item 22) states **AED 250** for title deed issuance. The AED 540 figure from market sources appears to be a bundle of title deed (AED 250) + property map (AED 250) + knowledge (AED 10) + innovation (AED 10) = AED 520–540. These are separate fees.

```
TITLE_DEED_RULE_VERIFIED = YES
TITLE_DEED_FEE_DOUBLE_COUNT = 0 ✅
```

### D. Knowledge Fee

| Field | Value |
|-------|-------|
| Fee name | Knowledge Dirham Fee |
| Source | OFFICIAL_DLD_RERA |
| Legal basis | Law No. 1 of 2018 |
| Amount | AED 10 |
| Status | OFFICIAL_VERIFIED |
| Applies to | All government service transactions |
| Threshold | Not charged for transactions < AED 50 |

**Separate from title deed fee.** Not embedded in any other fee.

```
KNOWLEDGE_FEE_DOUBLE_COUNT = 0 ✅
```

### E. Innovation Fee

| Field | Value |
|-------|-------|
| Fee name | Innovation Dirham Fee |
| Source | OFFICIAL_DLD_RERA |
| Legal basis | Law No. 2 of 2018 |
| Amount | AED 10 |
| Status | OFFICIAL_VERIFIED |
| Applies to | All government service transactions |
| Threshold | Not charged for transactions < AED 50 |

**Separate from title deed fee.** Not embedded in any other fee.

```
INNOVATION_FEE_DOUBLE_COUNT = 0 ✅
```

### F. Broker Purchase Commission

| Field | Value |
|-------|-------|
| Source | USER_INPUT |
| Legal basis | No statutory rate — regulated contractually (RERA Form B) |
| Market standard | 2% of sale price + 5% VAT (commonly cited, not statutory) |
| Status | USER_INPUT |

**No default is ever applied.** The investor must explicitly enter the broker commission (percent or AED).

```
DEFAULT_BROKER_PURCHASE_COMMISSION_USED = 0 ✅
```

### G. Developer / Admin Fee

| Field | Value |
|-------|-------|
| Source | USER_INPUT |
| Status | USER_INPUT or MISSING |

Not universally applicable. Does NOT block `COMPLETE_ACQUISITION_COSTS` level — some properties have no developer fee.

### H. Mortgage Registration Fee

| Field | Value |
|-------|-------|
| Status | NOT_APPLICABLE |

Not applicable in unlevered V1.

---

## 4. ACQUISITION COST LEVELS

### LEVEL A: PURCHASE_PRICE_ONLY

No acquisition costs available. Purchase price may be available but no fees calculated.

### LEVEL B: OFFICIAL_ACQUISITION_COSTS

Purchase price + all verified applicable statutory/government costs (DLD transfer, title deed, knowledge, innovation).

Broker/admin/trustee costs may still be missing. This is **NOT** Total Cash Invested.

### LEVEL C: COMPLETE_ACQUISITION_COSTS

Purchase price + official costs + all required investor-paid transaction costs (trustee fee + broker commission).

Only LEVEL C produces `total_cash_invested_aed`.

Developer/admin fee is optional — its absence does not block COMPLETE.

---

## 5. DO NOT CALL PARTIAL COST TOTAL CASH INVESTED

If broker or trustee costs are missing, the label is **"Purchase Price + Verified Acquisition Fees"** or **"Known Acquisition Cost"**, NOT "Total Cash Invested".

```
TOTAL_CASH_INVESTED_SHOWN_WITH_MISSING_ACQUISITION_COST = 0 ✅
INCOMPLETE_ACQUISITION_USED_AS_COMPLETE = 0 ✅
```

---

## 6. BACKEND PACKAGE

### Files Created

| File | Role |
|------|------|
| `investor_api/roi/__init__.py` | Package init |
| `investor_api/roi/acquisition_cost_models.py` | Data models, provenance, calculation levels |
| `investor_api/roi/acquisition_cost_provider.py` | Official DLD/RERA fee rules (versioned config) |
| `investor_api/roi/acquisition_cost_calculator.py` | Calculation engine (all math on backend) |
| `investor_api/roi/acquisition_cost_validation.py` | Input validation |

### Isolation

The ROI package is completely isolated. It does NOT modify:
- Rental engine
- Service charge provider
- Sales benchmark engine
- Operating cost layer
- Investor Fit

---

## 7. OFFICIAL COST PROVIDER

Lightweight local versioned configuration. No external DLD API call per property.

### Configuration

```json
{
  "methodology_version": "ACQUISITION_COST_V1_1",
  "valuation_date": "2026-08-22",
  "dld_transfer": { "total_rate_pct": 4.0, "buyer_statutory_share_pct": 2.0, ... },
  "title_deed": { "fixed_amount_aed": 250.0, ... },
  "knowledge_fee": { "fixed_amount_aed": 10.0, ... },
  "innovation_fee": { "fixed_amount_aed": 10.0, ... },
  "trustee_office_fee": { "status": "MISSING", ... }
}
```

---

## 8. ACQUISITION SUBTOTALS

### Official Acquisition Fees

```
official_acquisition_fees_aed =
    dld_transfer_fee_aed (buyer share)
    + title_deed_fee_aed (250)
    + knowledge_fee_aed (10)
    + innovation_fee_aed (10)
```

### Known Acquisition Costs

```
known_acquisition_costs_aed =
    official_acquisition_fees_aed
    + trustee_office_fee_aed (if user-entered)
    + broker_purchase_commission_aed (if user-entered)
    + developer_admin_fee_aed (if user-entered)
```

### Total Cash Invested (only when COMPLETE)

```
total_cash_invested_aed =
    purchase_price_aed
    + complete_acquisition_costs_aed
```

Only exposed when `calculation_level == COMPLETE_ACQUISITION_COSTS`.

---

## 9. PROVENANCE

Every component exposes:

| Field | Purpose |
|-------|---------|
| `name` | Fee name |
| `amount_aed` | Calculated amount |
| `source` | MASTER / OFFICIAL_DLD_RERA / USER_INPUT / DERIVED / NOT_APPLICABLE / MISSING |
| `status` | OFFICIAL_VERIFIED / USER_INPUT / NOT_APPLICABLE / MISSING |
| `calculation_basis` | How the amount was derived |
| `included_in_total` | Whether included in subtotal |
| `evidence_date` | When the data was verified |

---

## 10. PROPERTY COVERAGE AUDIT

### Ready Properties (321)

| Metric | Count |
|--------|-------|
| READY_PROPERTY_COUNT | 321 |
| Purchase price available | 321 (100%) |
| Official acquisition fee calculable | **321 (100%)** |
| Complete acquisition cost calculable | 0 (0%) |
| Total cash invested calculable | 0 (0%) |

### Level Distribution

| Level | Count |
|-------|-------|
| PURCHASE_PRICE_ONLY | 0 |
| OFFICIAL_ACQUISITION_COSTS | 321 |
| COMPLETE_ACQUISITION_COSTS | 0 |

### Missing Components

| Component | Missing | Required for COMPLETE? |
|-----------|---------|------------------------|
| trustee_office_fee | 321/321 | YES |
| broker_purchase_commission | 321/321 | YES |
| developer_admin_fee | 321/321 | NO (optional) |

### Official Fee Consistency

| Fee | Value | Consistent across all 321? |
|-----|-------|---------------------------|
| Title deed | AED 250 | YES ✅ |
| Knowledge | AED 10 | YES ✅ |
| Innovation | AED 10 | YES ✅ |
| DLD transfer (2% buyer) | price * 2% | YES ✅ |

---

## 11. READY ONLY

This acquisition cost audit covers Ready properties only. Offplan requires a separate cash-flow model (payment plans, future handover, etc.).

---

## 12. FRONTEND

No ROI UI implemented. No Full ROI card. No capital-return display. Backend/shadow only.

---

## 13. FROZEN RENTAL STACK REGRESSION

All counters zero — no frozen layer modified.

| Counter | Value |
|---------|-------|
| ACQ_V1_CHANGED_ANNUAL_RENT | 0 ✅ |
| ACQ_V1_CHANGED_GROSS_YIELD | 0 ✅ |
| ACQ_V1_CHANGED_SC_ELIGIBILITY | 0 ✅ |
| ACQ_V1_CHANGED_SC_RATE | 0 ✅ |
| ACQ_V1_CHANGED_SC_ANNUAL | 0 ✅ |
| ACQ_V1_CHANGED_INCOME_AFTER_SC | 0 ✅ |
| ACQ_V1_CHANGED_YIELD_AFTER_SC | 0 ✅ |
| ACQ_V1_CHANGED_NET_RENTAL_FORMULA | 0 ✅ |

---

## 14. SALES / SIGNAL / FIT REGRESSION

| Counter | Value |
|---------|-------|
| ACQ_V1_CHANGED_MARKET_CONTEXT | 0 ✅ |
| ACQ_V1_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| ACQ_V1_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| ACQ_V1_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| ACQ_V1_CHANGED_FIT_SCORE | 0 ✅ |

---

## 15. AUTH

No authentication, login, signup, or account persistence added.

```
ACQ_V1_AUTH_CHANGES = 0 ✅
```

---

## 16. SAFETY COUNTERS

| Counter | Value |
|---------|-------|
| DEFAULT_BROKER_PURCHASE_COMMISSION_USED | 0 ✅ |
| SELLER_COST_INCLUDED_IN_BUYER_ACQUISITION | 0 ✅ |
| TITLE_DEED_FEE_DOUBLE_COUNT | 0 ✅ |
| KNOWLEDGE_FEE_DOUBLE_COUNT | 0 ✅ |
| INNOVATION_FEE_DOUBLE_COUNT | 0 ✅ |
| TOTAL_CASH_INVESTED_SHOWN_WITH_MISSING_ACQUISITION_COST | 0 ✅ |
| INCOMPLETE_ACQUISITION_USED_AS_COMPLETE | 0 ✅ |
| OFFICIAL_FEE_WITHOUT_AUTHORITATIVE_SOURCE | 0 ✅ |
| PURCHASE_PRICE_SOURCE_OVERRIDE | 0 ✅ |
| ACQ_V1_AUTH_CHANGES | 0 ✅ |

**All 23 counters (13 regression + 10 safety) = 0.**

---

## 17. OUTPUT FILES

| File | Description |
|------|-------------|
| `roi_outputs/FULL_PROPERTY_ROI_V1_1_ACQUISITION_COST_AUDIT.md` | This report |
| `roi_outputs/full_property_roi_v1_1_acquisition_cost_matrix.csv` | Per-property acquisition cost matrix (321 rows) |
| `roi_outputs/full_property_roi_v1_1_official_fee_rules.json` | Official fee rules configuration |
| `roi_outputs/full_property_roi_v1_1_verdict.json` | Verdict + summary statistics |

---

## 18. FINAL VERDICT

### **FULL_PROPERTY_ROI_V1_1_ACQUISITION_COST_LAYER_VERIFIED**

| Metric | Value |
|--------|-------|
| READY_PROPERTY_COUNT | 321 |
| DLD_TRANSFER_RULE_VERIFIED | YES (ECR 30/2013) |
| DLD_BUYER_PAYER_RULE | CONTRACT_DEPENDENT (statutory default 2%, market practice up to 4%) |
| TRUSTEE_FEE_RULE_VERIFIED | NO (not in DLD statute — private entity fee, USER_INPUT) |
| TITLE_DEED_RULE_VERIFIED | YES (AED 250, ECR 30/2013 Item 22) |
| OFFICIAL_ACQUISITION_FEE_CALCULABLE_COUNT | 321/321 |
| COMPLETE_ACQUISITION_COST_CALCULABLE_COUNT | 0/321 (requires trustee + broker user input) |
| TOTAL_CASH_INVESTED_CALCULABLE_COUNT | 0/321 |
| All frozen-layer regressions | 0 ✅ |
| All safety counters | 0 ✅ |

### Missing Acquisition Components

1. **Trustee office fee** — not in DLD statute, requires USER_INPUT
2. **Broker purchase commission** — no statutory rate, requires USER_INPUT

### What Was Built

- Isolated `investor_api/roi/` backend package
- Official DLD/RERA fee rules (versioned, from statute)
- Acquisition cost calculator with 3 calculation levels
- Input validation for all user-entered fields
- Provenance tracking for every component

### What Was NOT Done

- No Full Property ROI calculation
- No exit value logic
- No appreciation forecasting
- No broker commission default
- No developer fee invention
- No mortgage/leverage ROI
- No rental stack modification
- No Service Charge V2 modification
- No Investor Fit modification
- No authentication
- No frontend UI
