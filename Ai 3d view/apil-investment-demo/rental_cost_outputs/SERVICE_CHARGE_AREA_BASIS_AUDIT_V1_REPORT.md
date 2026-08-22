# SERVICE CHARGE ADJUSTED INCOME V1 — AREA-BASIS / USAGE PARITY AUDIT

**Date**: 2026-08-20
**Verdict**: **SERVICE_CHARGE_ADJUSTED_INCOME_V1_AREA_BASIS_VERIFIED**
**Phase**: Area-basis verification only — no UI changes, no Net Rental Income

---

## 1. SUMMARY

| Metric | Value |
|--------|-------|
| PRE_AUDIT_CALCULABLE | 8 |
| **POST_AUDIT_CALCULABLE** | **6** |
| APARTMENT_VALID_COUNT | 6 |
| VILLA_VALID_COUNT | 0 |
| UNRESOLVED_AREA_BASIS_COUNT | 1 |
| WRONG_USAGE_COUNT | 0 |
| SERVICE_CHARGE_COMPONENT_MISMATCH | 1 |
| FUTURE_SERVICE_CHARGE_YEAR_USED | 0 |

**Coverage reduced from 8 to 6** after discovering two data-quality issues.

---

## 2. CRITICAL FINDINGS

### Finding 1: Golf Links (6217) — FALSE POSITIVE MATCH

| Field | MASTER (6217) | Mollak (GOLF LINKS) |
|-------|-------------|-------------------|
| Project name | Golf Links | GOLF LINKS |
| Area/Community | **Emaar South** | **Dubai Sports City** |
| Developer | Emaar | (Dubai Sports City project) |
| Qdrant category | **Villa** | — |
| Size | 4,309 sqft | — |

**Determination**:
- `GOLF_LINKS_PROPERTY_TYPE = Villa`
- `GOLF_LINKS_MOLLAK_USAGE = Residential`
- `GOLF_LINKS_MASTER_SIZE_SQFT = 4,309`
- `GOLF_LINKS_CHARGEABLE_AREA_BASIS = UNRESOLVED`
- `GOLF_LINKS_MASTER_SIZE_VALID_FOR_SC = NO`

**Root cause**: The original V1.1 audit matched "Golf Links" (MASTER, Emaar South, by Emaar) to "GOLF LINKS" (Mollak, Dubai Sports City) by exact project name. However, these are **different projects in different locations**:
- MASTER "Golf Links" = Emaar South, developed by Emaar
- Mollak "GOLF LINKS" = Dubai Sports City, different developer

Emaar South has **zero** Mollak service charge entries. The exact name match was coincidental.

**Action**: Property 6217 set to `SERVICE_CHARGE_ADJUSTED_NOT_EVALUATED`. No substitute area used.

### Finding 2: Harbour Views (409) — Component Mismatch

| Component | Value (AED/sqft) |
|-----------|-----------------|
| General Fund | 15.61 |
| Reserve Fund | 1.28 |
| GF + RF sum | **16.89** |
| Grand Total (Mollak) | **16.82** |
| Discrepancy | **0.07** |

The Mollak source data has a 0.07 AED/sqft discrepancy between the sum of components (GF + RF = 16.89) and the stated grand total (16.82). This is a Mollak source data rounding/calculation issue, not an error in our processing.

**Action**: Property 409 excluded from production-eligible calculations until the component discrepancy is resolved. The alias verification (Harbour Views 1 → HARBOUR VIEWS) remains confirmed, but the rate data has a source inconsistency.

---

## 3. PROPERTY TYPE AUDIT (all 8)

| Property ID | Project | Qdrant Category | Resolved Type | Type Source | MASTER Area | Mollak Community | Area Match |
|-------------|---------|----------------|---------------|-------------|-------------|-----------------|-----------|
| 4744 | Ahad Residences | Apartment | Apartment | QDRAST | Business Bay | Business Bay | ✅ |
| 6435 | Pantheon Elysee | Apartment | Apartment | QDRAST | Jumeirah Village Circle | Jumeirah Village Circle | ✅ |
| 7266 | Ahad Residences | Apartment | Apartment | QDRAST | Business Bay | Business Bay | ✅ |
| 1074 | Ahad Residences | Apartment | Apartment | QDRAST | Business Bay | Business Bay | ✅ |
| 6217 | Golf Links | **Villa** | **Villa** | QDRAST | Emaar South | Dubai Sports City | ❌ |
| 4165 | Ahad Residences | Apartment | Apartment | QDRAST | Business Bay | Business Bay | ✅ |
| 7842 | Azizi Feirouz | Apartment | Apartment | QDRAST | Al Furjan | Al Furjan | ✅ |
| 409 | Harbour Views 1 | Apartment | Apartment | QDRAST | Dubai Creek Harbour | Dubai Creek Harbour | ✅ |

**Property type source**: Qdrant `category` field (verified via `qdrant_matched_canonical_id` from MASTER). Arabic categories translated: شقة = Apartment, فيلا = Villa.

---

## 4. MOLLAK USAGE VERIFICATION

| Property ID | Mollak Usage Used | Non-Residential Usages in Project | Usage Match |
|-------------|------------------|----------------------------------|-------------|
| 4744 | Residential | Retail, Parking | YES |
| 6435 | Residential | Parking, Retail | YES |
| 7266 | Residential | Retail, Parking | YES |
| 1074 | Residential | Retail, Parking | YES |
| 6217 | Residential | Stores | YES |
| 4165 | Residential | Retail, Parking | YES |
| 7842 | Residential | Parking | YES |
| 409 | Residential | Retail | YES |

**WRONG_MOLLAK_USAGE_RATE_USED = 0** — All rates are from Residential usage. No commercial/retail/parking rates were used.

---

## 5. RATE COMPONENT VERIFICATION

| Property ID | Project | General Fund | Reserve Fund | GF + RF | Grand Total | Match |
|-------------|---------|-------------|-------------|---------|-------------|-------|
| 4744 | Ahad Residences | 18.15 | 2.11 | 20.26 | 20.26 | ✅ |
| 6435 | Pantheon Elysee | 13.07 | 1.53 | 14.60 | 14.60 | ✅ |
| 7266 | Ahad Residences | 18.15 | 2.11 | 20.26 | 20.26 | ✅ |
| 1074 | Ahad Residences | 18.15 | 2.11 | 20.26 | 20.26 | ✅ |
| 6217 | GOLF LINKS | 17.09 | 1.27 | 18.36 | 18.36 | ✅ |
| 4165 | Ahad Residences | 18.15 | 2.11 | 20.26 | 20.26 | ✅ |
| 7842 | AZIZI. FEIROUZ | 11.37 | 0.74 | 12.11 | 12.11 | ✅ |
| 409 | HARBOUR VIEWS | 15.61 | 1.28 | **16.89** | **16.82** | ❌ |

**SERVICE_CHARGE_COMPONENT_MISMATCH = 1** (Harbour Views only)

---

## 6. YEAR VERIFICATION

| Property ID | Year Used | Budget Start | Budget End | Year Valid |
|-------------|-----------|-------------|-----------|-----------|
| 4744 | 2026 | 01/01/2026 | 31/12/2026 | ✅ |
| 6435 | 2025 | 01/01/2025 | 31/12/2025 | ✅ |
| 7266 | 2026 | 01/01/2026 | 31/12/2026 | ✅ |
| 1074 | 2026 | 01/01/2026 | 31/12/2026 | ✅ |
| 6217 | 2026 | 01/03/2026 | 31/12/2026 | ✅ |
| 4165 | 2026 | 01/01/2026 | 31/12/2026 | ✅ |
| 7842 | 2026 | 01/01/2026 | 31/12/2026 | ✅ |
| 409 | 2026 | 01/01/2026 | 31/12/2026 | ✅ |

**FUTURE_SERVICE_CHARGE_YEAR_USED = 0** — All years ≤ 2026 (valuation date).

Note: Golf Links (6217) has a partial-year budget (01/03/2026–31/12/2026 = 10 months), but this is excluded anyway due to the area mismatch.

---

## 7. FINAL TABLE — ALL 8 PROPERTIES

| PID | Property | Type | Mollak Usage | Rate (AED/sqft) | Chargeable Area (sqft) | Area Basis Verified | Annual SC (AED) | Income After SC (AED) | Yield After SC | Production Eligible |
|-----|---------|------|-------------|-----------------|----------------------|-------------------|----------------|----------------------|---------------|-------------------|
| 4744 | Ahad Residences | Apartment | Residential | 20.26 | 2,308 | YES | 46,760 | 116,440 | 2.48% | **YES** |
| 6435 | Pantheon Elysee | Apartment | Residential | 14.60 | 763 | YES | 11,140 | 56,060 | 6.60% | **YES** |
| 7266 | Ahad Residences | Apartment | Residential | 20.26 | 894 | YES | 18,112 | 92,288 | 5.13% | **YES** |
| 1074 | Ahad Residences | Apartment | Residential | 20.26 | 453 | YES | 9,178 | 67,622 | 5.41% | **YES** |
| 6217 | Golf Links | Villa | Residential | 18.36 | 4,309 | **NO** | — | — | — | **NO** |
| 4165 | Ahad Residences | Apartment | Residential | 20.26 | 1,625 | YES | 32,923 | 154,278 | 4.72% | **YES** |
| 7842 | Azizi Feirouz | Apartment | Residential | 12.11 | 1,008 | YES | 12,207 | 58,353 | 5.72% | **YES** |
| 409 | Harbour Views 1 | Apartment | Residential | 16.82 | 1,526 | **NO** | — | — | — | **NO** |

### Excluded Properties

| PID | Property | Reason |
|-----|---------|--------|
| 6217 | Golf Links | AREA_MISMATCH: Mollak project is in Dubai Sports City, MASTER property is in Emaar South. Different projects. False positive name match. |
| 409 | Harbour Views 1 | COMPONENT_MISMATCH: GF+RF (16.89) ≠ Grand Total (16.82). Mollak source data rounding inconsistency. |

---

## 8. ARITHMETIC VALIDATION (6 valid properties)

| Check | Mismatches | Status |
|-------|-----------|--------|
| SERVICE_CHARGE_ARITHMETIC_MISMATCH | 0 | ✅ |
| ADJUSTED_INCOME_ARITHMETIC_MISMATCH | 0 | ✅ |
| ADJUSTED_YIELD_ARITHMETIC_MISMATCH | 0 | ✅ |

All 6 valid properties pass independent arithmetic verification.

---

## 9. ENGINE ISOLATION — ALL SAFETY COUNTERS AT 0

| Counter | Value | Status |
|---------|-------|--------|
| AREA_BASIS_AUDIT_CHANGED_RENT_ESTIMATE | 0 | ✅ |
| AREA_BASIS_AUDIT_CHANGED_GROSS_YIELD | 0 | ✅ |
| AREA_BASIS_AUDIT_CHANGED_MARKET_CONTEXT | 0 | ✅ |
| AREA_BASIS_AUDIT_CHANGED_PRODUCTION_SIGNAL | 0 | ✅ |
| AREA_BASIS_AUDIT_CHANGED_FIT_SCORE | 0 | ✅ |

**All 5 safety counters at 0.** No existing runtime modified.

---

## 10. CORRECTIONS TO PREVIOUS AUDIT

### V1.1 Audit Correction: Golf Links False Positive

The V1.1 audit classified "Golf Links" → "GOLF LINKS" as an EXACT match. This was a **false positive**:
- Same project name, but different locations (Emaar South vs Dubai Sports City)
- Different developers (Emaar vs Dubai Sports City developer)
- Qdrant confirms property 6217 is a Villa, not an apartment

**The V1.1 EXACT match count should be revised from 6 to 5.** The total verified count should be revised from 8 to 6 (after also excluding Harbour Views for component mismatch).

### V1 Shadow Calculation Correction

The V1 shadow calculation included property 6217 (Golf Links) with:
- Annual SC: AED 79,113
- Income After SC: AED 43,767
- Yield After SC: 1.07%

**These figures are INVALID and must be discarded.** The Mollak rate does not apply to this property.

Similarly, property 409 (Harbour Views) figures are held pending Mollak source data resolution:
- Annual SC: AED 25,667
- Income After SC: AED 137,533
- Yield After SC: 5.09%

**These figures are HELD pending component mismatch resolution.**

---

## 11. REVISED VERIFIED COVERAGE

| Category | V1.1 Count | Post-Area-Basis Audit | Change |
|----------|-----------|----------------------|--------|
| EXACT_VERIFIED | 6 | **5** | -1 (Golf Links false positive) |
| NORMALIZED_EXACT_VERIFIED | 1 | 1 | 0 |
| VERIFIED_ALIAS | 1 | **0** | -1 (Harbour Views component mismatch) |
| **TOTAL PRODUCTION-ELIGIBLE** | **8** | **6** | **-2** |
| AMBIGUOUS | 23 | 23 | 0 |
| NO_MATCH | 284 | 284 | 0 |

---

## 12. OUTPUT FILES

| File | Description |
|------|-------------|
| `rental_cost_outputs/service_charge_area_basis_audit_v1.csv` | All 8 properties with area-basis verification |
| `rental_cost_outputs/service_charge_area_basis_audit_v1_verdict.json` | Verdict data |

---

## 13. VERDICT

### **SERVICE_CHARGE_ADJUSTED_INCOME_V1_AREA_BASIS_VERIFIED**

The area-basis audit successfully identified and excluded 2 invalid properties:
1. Golf Links (6217) — false positive name match (different locations)
2. Harbour Views (409) — Mollak source component mismatch

**6 properties remain production-eligible**, all apartments with verified area basis, correct Mollak residential usage, valid years, and zero arithmetic mismatches.

| Check | Result |
|-------|--------|
| PRE_AUDIT_CALCULABLE | 8 |
| POST_AUDIT_CALCULABLE | 6 |
| Arithmetic failures | 0 |
| All safety counters | 0 |
| Engine isolation | ✅ |

**STOP. No UI wired. No vacancy calculated. No Net Rental Income. Waiting for explicit approval.**
