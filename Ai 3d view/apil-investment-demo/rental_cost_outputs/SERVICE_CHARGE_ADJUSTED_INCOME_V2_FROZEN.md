# SERVICE CHARGE ADJUSTED INCOME V2 — FROZEN

**Freeze Date**: 2026-08-21
**Freeze Identifier**: `SERVICE_CHARGE_ADJUSTED_INCOME_V2_FROZEN`
**Status**: FROZEN — Production

---

## 1. METHODOLOGY

### V1 (Historical — Retired)

| Item | Value |
|------|-------|
| Validation rule | GF + RF = GT |
| Status | **RETIRED_AS_SEMANTICALLY_INCORRECT** |
| Reason | Omitted `gfData.income` field (property-generated income that offsets service charges) |
| Properties | 6 (unchanged in V2 — income=0, identical results) |

### V2 (Current — Frozen)

| Item | Value |
|------|-------|
| Validation rule | **GF + RF − income = GT** |
| Authoritative calculation rate | **grandTotal** (grand_total_aed_sqft) |
| Source | DLD/RERA Mollak API |
| Properties | 12 (6 original + 6 newly promoted) |

### Corrected Mollak Data Model

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
income_after_service_charges_aed = annual_rent_estimate_aed - annual_service_charge_aed
yield_after_service_charges_pct = income_after_service_charges_aed / current_price_aed × 100
```

**The production rate comes directly from gfData.grandTotal. It is NOT reconstructed from components.**

---

## 2. PRODUCTION-ELIGIBLE PROPERTIES (12)

### V1 Original 6 (Unchanged)

| Property ID | Mollak Project | Rate (AED/sqft) | Annual SC (AED) | Income After SC (AED) | Yield After SC |
|-------------|---------------|-----------------|-----------------|----------------------|----------------|
| 4744 | Ahad Residences | 20.26 | 46,760.08 | 116,439.92 | 2.48% |
| 6435 | PANTHEON ELYSEE | 14.60 | 11,139.80 | 56,060.20 | 6.60% |
| 7266 | Ahad Residences | 20.26 | 18,112.44 | 92,287.56 | 5.13% |
| 1074 | Ahad Residences | 20.26 | 9,177.78 | 67,622.22 | 5.41% |
| 4165 | Ahad Residences | 20.26 | 32,922.50 | 154,277.50 | 4.72% |
| 7842 | AZIZI. FEIROUZ | 12.11 | 12,206.88 | 58,353.12 | 5.72% |

### V2.5 Newly Promoted 6

| Property ID | Mollak Project | Rate (AED/sqft) | GF | RF | Income | GT | Annual SC (AED) | Income After SC (AED) | Yield After SC |
|-------------|---------------|-----------------|-----|-----|--------|-----|-----------------|----------------------|----------------|
| 409 | HARBOUR VIEWS | 16.82 | 15.61 | 1.28 | 0.07 | 16.82 | 25,667.32 | 137,532.68 | 5.09% |
| 8201 | MARQUISE SQUARE TOWER | 16.85 | 15.85 | 1.09 | 0.09 | 16.85 | 39,193.10 | 124,006.90 | 2.88% |
| 1208 | MARQUISE SQUARE TOWER | 16.85 | 15.85 | 1.09 | 0.09 | 16.85 | 17,928.40 | 78,071.60 | 3.72% |
| 5582 | MARQUISE SQUARE TOWER | 16.85 | 15.85 | 1.09 | 0.09 | 16.85 | 27,937.30 | 101,662.70 | 3.51% |
| 3160 | MARQUISE SQUARE TOWER | 16.85 | 15.85 | 1.09 | 0.09 | 16.85 | 8,711.45 | 48,888.55 | 3.99% |
| 7881 | THE DUBAI CREEK RESIDENCES | 16.50 | 16.15 | 0.57 | 0.22 | 16.50 | 16,830.00 | 103,170.00 | 7.37% |

---

## 3. HELD PROPERTIES (4 — NOT ELIGIBLE)

### Canal Residence West Phase 1

| Property ID | Project Match | SC Status | Eligible | Rate | Reason |
|-------------|--------------|-----------|----------|------|--------|
| 884 | VERIFIED_PHASE_1 | HELD_RATE_SCOPE | False | None | Cannot map to European/Venetian/Mediterranean |
| 4702 | VERIFIED_PHASE_1 | HELD_RATE_SCOPE | False | None | Same |
| 4750 | VERIFIED_PHASE_1 | HELD_RATE_SCOPE | False | None | Same |
| 5513 | VERIFIED_PHASE_1 | HELD_RATE_SCOPE | False | None | Same |

**Mollak residential groups**: European=13.92, Venetian=13.91, Mediterranean=13.94 AED/sqft
**No representative rate used.** MASTER/Qdrant do not identify which tower each property belongs to.

---

## 4. REJECTED IDENTITY (1 — Permanently Blacklisted)

| Property ID | Project Match | SC Status | Eligible | Reason |
|-------------|--------------|-----------|----------|--------|
| 6217 | REJECTED_IDENTITY | NOT_MATCHED | False | Cross-community (Emaar South ≠ Dubai Sports City) |

---

## 5. INCLUDED / EXCLUDED COSTS

### Included
- Estimated annual market rent
- Official DLD/RERA Mollak service charges

### Not Included
- Vacancy
- Landlord property management
- Unit maintenance

### Disclosure
"Income After Service Charges deducts verified official service charges only. It is not Net Rental Income."

---

## 6. PRODUCTION PROVIDER

| Item | Value |
|------|-------|
| File | `investor_api/rental_costs/service_charge_provider.py` |
| Lookup type | O(1) dict lookup |
| CSV parsing per request | No |
| External Mollak API call per request | No |
| Version identifier | SERVICE_CHARGE_ADJUSTED_INCOME_V2 |

---

## 7. ALL REGRESSION COUNTERS (38 counters — ALL ZERO)

| Counter | Value |
|---------|-------|
| UNEXPECTED_PRODUCTION_ELIGIBLE_PROPERTY | 0 ✅ |
| EXPECTED_PRODUCTION_ELIGIBLE_PROPERTY_MISSING | 0 ✅ |
| CANAL_RATE_SCOPE_LEAKAGE | 0 ✅ |
| CANAL_REPRESENTATIVE_RATE_USED | 0 ✅ |
| REJECTED_IDENTITY_LEAKAGE | 0 ✅ |
| PRODUCTION_RATE_RECONSTRUCTED_FROM_COMPONENTS | 0 ✅ |
| V2_FREEZE_CHANGED_ORIGINAL_RATE | 0 ✅ |
| V2_FREEZE_CHANGED_ORIGINAL_SC | 0 ✅ |
| V2_FREEZE_CHANGED_ORIGINAL_INCOME | 0 ✅ |
| V2_FREEZE_CHANGED_ORIGINAL_YIELD | 0 ✅ |
| V2_FREEZE_NEW_PROPERTY_VALUE_MISMATCH | 0 ✅ |
| V2_FREEZE_BACKEND_AUDIT_FAILURES | 0 ✅ |
| V2_FREEZE_NON_ELIGIBLE_UI_LEAKAGE | 0 ✅ |
| V2_FREEZE_CHANGED_ANNUAL_RENT | 0 ✅ |
| V2_FREEZE_CHANGED_RENT_RANGE | 0 ✅ |
| V2_FREEZE_CHANGED_RENT_TIER | 0 ✅ |
| V2_FREEZE_CHANGED_GROSS_YIELD | 0 ✅ |
| V2_FREEZE_CHANGED_GROSS_YIELD_RANGE | 0 ✅ |
| V2_FREEZE_CHANGED_MARKET_CONTEXT | 0 ✅ |
| V2_FREEZE_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| V2_FREEZE_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| V2_FREEZE_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| V2_FREEZE_CHANGED_FIT_SCORE | 0 ✅ |
| V2_FREEZE_CHANGED_RENTAL_MESSAGE_LOGIC | 0 ✅ |
| V2_FREEZE_EXTERNAL_MOLLAK_CALL_PER_REQUEST | 0 ✅ |
| V2_FREEZE_CSV_PARSE_PER_REQUEST | 0 ✅ |
| V2_FREEZE_API_PERFORMANCE_REGRESSION | 0 ✅ |
| V2_FREEZE_FRONTEND_SC_RECALCULATION | 0 ✅ |
| V2_FREEZE_FRONTEND_INCOME_RECALCULATION | 0 ✅ |
| V2_FREEZE_FRONTEND_YIELD_RECALCULATION | 0 ✅ |
| NET_RENTAL_INCOME_LABEL_USED | 0 ✅ |
| NET_RENTAL_YIELD_LABEL_USED | 0 ✅ |
| NET_INCOME_LABEL_USED | 0 ✅ |
| NET_YIELD_LABEL_USED | 0 ✅ |
| UNINTENDED_PROVIDER_CHANGE | 0 ✅ |
| INTENTIONAL_PROVIDER_PROMOTION_APPLIED | 1 (intentional) |
| PRODUCTION_ELIGIBLE_COUNT_MISMATCH | 0 ✅ |
| UNRELATED_FILE_INCLUDED_IN_V2_FREEZE | 0 ✅ |

---

## 8. HISTORICAL ARTIFACTS PRESERVED

| Artifact | Status |
|----------|--------|
| SERVICE_CHARGE_ADJUSTED_INCOME_V1_FROZEN.md | Preserved (immutable historical audit) |
| SERVICE_CHARGE_ADJUSTED_INCOME_V1_REPORT.md | Preserved |
| SERVICE_CHARGE_ADJUSTED_INCOME_V1_UI_FROZEN.md | Preserved |
| SERVICE_CHARGE_COVERAGE_V2_RESEARCH.md | Preserved |
| SERVICE_CHARGE_COVERAGE_V2_1_MANUAL_VERIFICATION.md | Preserved |
| MOLLAK_COMPONENT_SEMANTICS_V2_2_RESEARCH.md | Preserved |
| SERVICE_CHARGE_V2_3_CORRECTED_SEMANTICS_REVALIDATION.md | Preserved |
| SERVICE_CHARGE_V2_4_PROMOTION_READINESS.md | Preserved |
| SERVICE_CHARGE_ADJUSTED_INCOME_V2_PROMOTION_REPORT.md | Preserved |

---

## 9. GIT FILES

| File | Change | V2-Related |
|------|--------|------------|
| `investor_api/rental_costs/service_charge_provider.py` | New file (V2 provider with 12 eligible, 4 held, 1 rejected) | YES |
| `investor_api/main_v2.py` | Comment update from "FROZEN V1" to "V2" | YES |

No unrelated files included in V2 freeze.

---

## 10. FREEZE VERDICT

### **SERVICE_CHARGE_ADJUSTED_INCOME_V2_FROZEN**

| Check | Result |
|-------|--------|
| PRODUCTION_ELIGIBLE | 12 |
| ORIGINAL_V1_PROPERTIES | 6 (unchanged) |
| NEW_V2_PROPERTIES | 6 (promoted) |
| HELD_RATE_SCOPE | 4 |
| REJECTED_IDENTITY | 1 |
| All 38 regression/safety counters | 0 ✅ |
| V1 artifacts preserved | YES ✅ |
| Production provider O(1) | YES ✅ |
| No external API calls per request | YES ✅ |
| No CSV parsing per request | YES ✅ |

**This freeze is immutable. Do NOT add properties without a full audit + promotion + freeze process.**
