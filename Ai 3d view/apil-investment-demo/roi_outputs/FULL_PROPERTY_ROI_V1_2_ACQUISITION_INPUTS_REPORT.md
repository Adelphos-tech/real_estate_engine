# FULL PROPERTY ROI V1.2 — ACQUISITION USER INPUT COMPLETION LAYER

**Date**: 2026-08-22
**Phase**: FULL_PROPERTY_ROI_V1_2_ACQUISITION_INPUTS
**Verdict**: `FULL_PROPERTY_ROI_V1_2_ACQUISITION_INPUT_LAYER_VERIFIED`
**Methodology Version**: `ACQUISITION_COST_V1_2`

---

## 1. GOAL

Build the controlled user-input layer to move from `OFFICIAL_ACQUISITION_COSTS` to `COMPLETE_ACQUISITION_COSTS` for Ready properties. Purchase-side transaction inputs only.

**Status: VERIFIED.** All 11 test cases pass. All 26 counters zero.

---

## 2. REQUIRED USER INPUTS

| Input | Mode(s) | Required for COMPLETE? |
|-------|---------|------------------------|
| A. DLD buyer-paid share | USE_STATUTORY_DEFAULT / CUSTOM_PERCENT / CUSTOM_AED | YES |
| B. Trustee office fee | USER_INPUT_AED | YES |
| C. Broker purchase commission | BROKER_PERCENT / BROKER_FIXED_AED / NO_BROKER_COST | YES |
| D. Developer/admin fee | USER_INPUT_AED / NO_DEVELOPER_ADMIN_FEE | YES |

---

## 3. DLD BUYER SHARE — CONFIRMATION SEMANTICS

### Official Statute

ECR 30/2013 Article 3(1): "unless agreed otherwise, the Fee for the sale of Real Property will be shared equally by the seller and purchaser."

- Total rate: 4%
- Statutory default: 2% buyer + 2% seller
- Payer allocation: **CONTRACT_DEPENDENT**

### DLD Buyer Share Status

| Status | Meaning |
|--------|---------|
| `OFFICIAL_STATUTORY_DEFAULT` | 2% is the statutory default (reference only, not yet confirmed) |
| `USER_CONFIRMED_DEFAULT` | User explicitly confirmed using the statutory 2% |
| `USER_OVERRIDE` | User entered a custom share (CUSTOM_PERCENT or CUSTOM_AED) |
| `MISSING` | User has not yet provided DLD input |

### DLD Input Modes

| Mode | Description | Buyer Rate | Source |
|------|-------------|-----------|--------|
| `USE_STATUTORY_DEFAULT` | User confirms 2% statutory default | 2.0% | OFFICIAL_DLD_RERA |
| `CUSTOM_PERCENT` | User enters custom buyer share % | user-entered | USER_INPUT |
| `CUSTOM_AED` | User enters fixed AED amount | derived | USER_INPUT |

**Never silently assume 4%. Never silently treat 2% as confirmed without user action.**

```
SELLER_DLD_SHARE_INCLUDED_IN_BUYER_COST = 0 ✅
DLD_4_PERCENT_AUTOMATICALLY_CHARGED_TO_BUYER = 0 ✅
```

### DLD Validation

| Rule | Constraint |
|------|-----------|
| CUSTOM_PERCENT | 0 ≤ pct ≤ 4 |
| CUSTOM_AED | ≥ 0 |
| No clamping | Invalid values rejected (422) |

---

## 4. TRUSTEE OFFICE FEE

| Field | Value |
|-------|-------|
| Status | MISSING (not OFFICIAL_VERIFIED) |
| Input | `trustee_office_fee_aed` |
| Validation | ≥ 0 |
| Default | NONE — never prefill AED 2,000/4,000 |

```
DEFAULT_TRUSTEE_FEE_USED = 0 ✅
```

---

## 5. BROKER PURCHASE COMMISSION

### Input Modes

| Mode | Description | Amount |
|------|-------------|--------|
| `BROKER_PERCENT` | Percentage of purchase price | price * pct / 100 |
| `BROKER_FIXED_AED` | Fixed AED amount | user-entered |
| `NO_BROKER_COST` | Explicit zero — user selects "no broker" | 0.0 |

**NO_BROKER_COST requires explicit user selection.** Never assume broker cost = 0.

```
DEFAULT_BROKER_PURCHASE_COMMISSION_USED = 0 ✅
AUTO_NO_BROKER_ASSUMPTION = 0 ✅
```

### Validation

| Rule | Constraint |
|------|-----------|
| BROKER_PERCENT | 0 ≤ pct ≤ 100 |
| BROKER_FIXED_AED | ≥ 0 |
| NO_BROKER_COST | Always valid (explicit zero) |

---

## 6. DEVELOPER / ADMIN FEE

### Input Modes

| Mode | Description | Amount |
|------|-------------|--------|
| `USER_INPUT_AED` | User enters amount | user-entered |
| `NO_DEVELOPER_ADMIN_FEE` | Explicit zero | 0.0 |

**Never default to zero unless explicitly selected.**

---

## 7. VERIFIED OFFICIAL COMPONENTS (unchanged)

| Fee | Amount | Source | Legal Basis |
|-----|--------|--------|-------------|
| Title deed | AED 250 | OFFICIAL_DLD_RERA | ECR 30/2013 Item 22 |
| Knowledge | AED 10 | OFFICIAL_DLD_RERA | Law No. 1 of 2018 |
| Innovation | AED 10 | OFFICIAL_DLD_RERA | Law No. 2 of 2018 |

**Property map fee is NOT automatically included** — it's optional and only applies when a new map is required.

```
OPTIONAL_PROPERTY_MAP_FEE_AUTOMATICALLY_INCLUDED = 0 ✅
OLD_AED_540_TITLE_DEED_BUNDLE_USED = 0 ✅
TITLE_DEED_DOUBLE_COUNT = 0 ✅
KNOWLEDGE_DOUBLE_COUNT = 0 ✅
INNOVATION_DOUBLE_COUNT = 0 ✅
```

---

## 8. ACQUISITION COMPLETENESS

### Required Components for COMPLETE

1. Purchase price (MASTER)
2. Confirmed buyer DLD cost (USE_STATUTORY_DEFAULT / CUSTOM_PERCENT / CUSTOM_AED)
3. Trustee fee (USER_INPUT)
4. Broker purchase cost (BROKER_PERCENT / BROKER_FIXED_AED / NO_BROKER_COST)
5. Developer/admin (USER_INPUT_AED / NO_DEVELOPER_ADMIN_FEE)
6. Title deed fee (OFFICIAL_VERIFIED — automatic)
7. Knowledge fee (OFFICIAL_VERIFIED — automatic)
8. Innovation fee (OFFICIAL_VERIFIED — automatic)

### Calculation Levels

| Level | Condition |
|-------|-----------|
| `PURCHASE_PRICE_ONLY` | No purchase price |
| `OFFICIAL_ACQUISITION_COSTS` | Price + official fixed fees only (DLD not confirmed) |
| `PARTIAL_ACQUISITION_COSTS` | DLD confirmed but some user inputs missing |
| `COMPLETE_ACQUISITION_COSTS` | All required components resolved |

If any required component is unresolved: `total_cash_invested_aed = None`.

```
TOTAL_CASH_INVESTED_SHOWN_WHILE_INCOMPLETE = 0 ✅
```

---

## 9. COMPLETE ACQUISITION FORMULA

```
complete_acquisition_costs_aed =
    buyer_dld_fee_aed
    + trustee_office_fee_aed
    + title_deed_fee_aed (250)
    + knowledge_fee_aed (10)
    + innovation_fee_aed (10)
    + broker_purchase_cost_aed
    + developer_admin_fee_aed

total_cash_invested_aed =
    MASTER current_price_aed
    + complete_acquisition_costs_aed
```

Only produced when `calculation_level == COMPLETE_ACQUISITION_COSTS`.

---

## 10. ZERO MUST BE EXPLICIT

For user-variable costs, 0 is valid only when explicitly supplied or explicitly selected.

| Mode | Zero is explicit? |
|------|-------------------|
| NO_BROKER_COST | YES — user selected |
| NO_DEVELOPER_ADMIN_FEE | YES — user selected |
| Missing (no input) | NO — treated as MISSING, not 0 |

```
MISSING_ACQUISITION_COST_COERCED_TO_ZERO = 0 ✅
```

---

## 11. PROVENANCE

Every component exposes:

| Field | Purpose |
|-------|---------|
| `amount_aed` | Calculated amount |
| `status` | OFFICIAL_VERIFIED / USER_INPUT / NOT_APPLICABLE / MISSING |
| `source` | MASTER / OFFICIAL_DLD_RERA / USER_INPUT / DERIVED / NOT_APPLICABLE / MISSING |
| `input_mode` | USE_STATUTORY_DEFAULT / CUSTOM_PERCENT / etc. |
| `calculation_basis` | How the amount was derived |
| `included_in_total` | Whether in subtotal |
| `evidence_date` | When verified |

### DLD-Specific Provenance

| Field | Purpose |
|-------|---------|
| `official_total_rate_pct` | 4.0 (statutory total) |
| `statutory_buyer_default_pct` | 2.0 (statutory buyer share) |
| `actual_buyer_rate_pct` | What's actually used (2.0, 4.0, or derived) |
| `buyer_share_status` | OFFICIAL_STATUTORY_DEFAULT / USER_CONFIRMED_DEFAULT / USER_OVERRIDE / MISSING |
| `confirmed` | Boolean — has user confirmed? |

---

## 12. DEMO INPUT STORAGE

```
PERSISTENCE_MODE = EPHEMERAL_USER_SESSION
```

- In-memory dict keyed by `(user_scope, property_id)`
- Disappears on server restart
- NOT written to MASTER, Qdrant, Mollak, rental evidence, or service charge provider
- No authentication

---

## 13. BACKEND ONLY CALCULATIONS

All calculations happen on the backend. Frontend sends raw inputs only.

```
FRONTEND_DLD_FEE_CALCULATION = 0 ✅
FRONTEND_BROKER_COST_CALCULATION = 0 ✅
FRONTEND_ACQUISITION_TOTAL_CALCULATION = 0 ✅
FRONTEND_TOTAL_CASH_INVESTED_CALCULATION = 0 ✅
```

---

## 14. SHADOW API CONTEXT

The `acquisition_cost_context` response includes:

```
calculation_level
purchase_price_aed
dld_transfer: {
    total_official_rate_pct,
    statutory_buyer_default_pct,
    actual_buyer_rate_pct,
    buyer_cost_aed,
    source,
    confirmed,
    buyer_share_status,
    input_mode
}
trustee_office_fee
title_deed_fee
knowledge_fee
innovation_fee
broker_purchase
developer_admin
official_acquisition_fees_aed
known_acquisition_costs_aed
complete_acquisition_costs_aed
total_cash_invested_aed
missing_components
```

---

## 15. TEST CASES (A-K)

All 11 tests pass:

| Test | Description | Result |
|------|-------------|--------|
| A | No user inputs → not COMPLETE, tci=null | PASS ✅ |
| B | Statutory DLD 2% only → PARTIAL, still incomplete | PASS ✅ |
| C | DLD + trustee only → PARTIAL, still incomplete | PASS ✅ |
| D | DLD + trustee + broker, dev unresolved → PARTIAL | PASS ✅ |
| E | All inputs complete → COMPLETE, tci available | PASS ✅ |
| F | Custom DLD 4% → uses 4% (USER_OVERRIDE) | PASS ✅ |
| G | NO_BROKER_COST → 0 accepted with explicit provenance | PASS ✅ |
| H | NO_DEVELOPER_ADMIN_FEE → 0 accepted explicitly | PASS ✅ |
| I | Missing trustee → remain incomplete (not coerced to 0) | PASS ✅ |
| J | Negative trustee → 422 rejected | PASS ✅ |
| K | DLD >4% → 422 rejected | PASS ✅ |

```
ALL_TESTS_PASS = 1 ✅
```

### Test E Details (Complete Acquisition)

Property 409 (price = AED 2,700,000):
- DLD (2% statutory, confirmed): AED 54,000
- Title deed: AED 250
- Knowledge: AED 10
- Innovation: AED 10
- Trustee: AED 4,000
- Broker (2%): AED 54,000
- Developer: AED 0 (NO_DEVELOPER_ADMIN_FEE)
- **Complete acquisition costs**: AED 112,270
- **Total cash invested**: AED 2,812,270

### Test F Details (Custom 4% DLD)

- DLD (4% user override): AED 108,000
- Buyer share status: USER_OVERRIDE
- Source: USER_INPUT

---

## 16. READY PROPERTY COVERAGE

With NO user inputs (default state):

| Metric | Count |
|--------|-------|
| READY_PROPERTY_COUNT | 321 |
| Official acquisition fee calculable | 321 (100%) |
| Complete acquisition cost calculable | 0 (0%) |
| Total cash invested calculable | 0 (0%) |

No batch-populated assumptions. Complete requires explicit user inputs.

---

## 17. FROZEN RENTAL REGRESSION

| Counter | Value |
|---------|-------|
| ACQ_INPUT_V1_CHANGED_ANNUAL_RENT | 0 ✅ |
| ACQ_INPUT_V1_CHANGED_GROSS_YIELD | 0 ✅ |
| ACQ_INPUT_V1_CHANGED_SC_ELIGIBILITY | 0 ✅ |
| ACQ_INPUT_V1_CHANGED_SC_RATE | 0 ✅ |
| ACQ_INPUT_V1_CHANGED_SC_ANNUAL | 0 ✅ |
| ACQ_INPUT_V1_CHANGED_INCOME_AFTER_SC | 0 ✅ |
| ACQ_INPUT_V1_CHANGED_YIELD_AFTER_SC | 0 ✅ |
| ACQ_INPUT_V1_CHANGED_NET_RENTAL_FORMULA | 0 ✅ |

---

## 18. SALES / SIGNAL / FIT REGRESSION

| Counter | Value |
|---------|-------|
| ACQ_INPUT_V1_CHANGED_MARKET_CONTEXT | 0 ✅ |
| ACQ_INPUT_V1_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| ACQ_INPUT_V1_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| ACQ_INPUT_V1_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| ACQ_INPUT_V1_CHANGED_FIT_SCORE | 0 ✅ |

---

## 19. SAFETY COUNTERS

| Counter | Value |
|---------|-------|
| SELLER_DLD_SHARE_INCLUDED_IN_BUYER_COST | 0 ✅ |
| DLD_4_PERCENT_AUTOMATICALLY_CHARGED_TO_BUYER | 0 ✅ |
| DEFAULT_TRUSTEE_FEE_USED | 0 ✅ |
| DEFAULT_BROKER_PURCHASE_COMMISSION_USED | 0 ✅ |
| AUTO_NO_BROKER_ASSUMPTION | 0 ✅ |
| OPTIONAL_PROPERTY_MAP_FEE_AUTOMATICALLY_INCLUDED | 0 ✅ |
| MISSING_ACQUISITION_COST_COERCED_TO_ZERO | 0 ✅ |
| OLD_AED_540_TITLE_DEED_BUNDLE_USED | 0 ✅ |
| TITLE_DEED_DOUBLE_COUNT | 0 ✅ |
| KNOWLEDGE_DOUBLE_COUNT | 0 ✅ |
| INNOVATION_DOUBLE_COUNT | 0 ✅ |
| TOTAL_CASH_INVESTED_SHOWN_WHILE_INCOMPLETE | 0 ✅ |
| ACQ_INPUT_V1_AUTH_CHANGES | 0 ✅ |

**All 26 counters (13 regression + 13 safety) = 0.**

---

## 20. BACKEND PACKAGE

### Files (V1.2 updated)

| File | Role |
|------|------|
| `investor_api/roi/__init__.py` | Package init |
| `investor_api/roi/acquisition_cost_models.py` | Data models with DLD confirmation semantics, broker/developer modes |
| `investor_api/roi/acquisition_cost_provider.py` | Official DLD/RERA fee rules (unchanged from V1.1) |
| `investor_api/roi/acquisition_cost_calculator.py` | Calculation engine with 4 levels, enhanced provenance |
| `investor_api/roi/acquisition_cost_validation.py` | Input validation for all modes |
| `investor_api/roi/acquisition_cost_user_input_store.py` | Ephemeral in-memory store (NEW) |

---

## 21. OUTPUT FILES

| File | Description |
|------|-------------|
| `roi_outputs/FULL_PROPERTY_ROI_V1_2_ACQUISITION_INPUTS_REPORT.md` | This report |
| `roi_outputs/full_property_roi_v1_2_acquisition_test_cases.json` | Test case results (A-K) |
| `roi_outputs/full_property_roi_v1_2_acquisition_verdict.json` | Verdict + summary |

---

## 22. FINAL VERDICT

### **FULL_PROPERTY_ROI_V1_2_ACQUISITION_INPUT_LAYER_VERIFIED**

| Metric | Value |
|--------|-------|
| ALL_TESTS_PASS | 1 ✅ |
| All regression counters | 0 ✅ |
| All safety counters | 0 ✅ |
| DLD confirmation semantics | VERIFIED ✅ |
| Zero-is-explicit rule | VERIFIED ✅ |
| No double counting | VERIFIED ✅ |
| No defaults | VERIFIED ✅ |
| Backend-only calculations | VERIFIED ✅ |
| Ephemeral storage | VERIFIED ✅ |

### NOT DONE

- No holding period
- No exit value
- No selling costs
- No appreciation
- No Full Property ROI calculation
- No mortgage/leverage
- No rental stack modification
- No Service Charge V2 modification
- No Investor Fit modification
- No authentication
- No frontend UI
