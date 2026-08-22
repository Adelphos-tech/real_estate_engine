# SERVICE CHARGE ADJUSTED INCOME V1 — FROZEN

**Date**: 2026-08-20
**Verdict**: **SERVICE_CHARGE_ADJUSTED_INCOME_V1_READY_FOR_UI**
**Status**: FROZEN — ready for UI integration pending explicit approval

---

## 1. FROZEN ELIGIBLE PROPERTY SET (6 properties)

| Property ID | Project | Area | Match Method | SC Year | Rate (AED/sqft) | Size (sqft) | Annual SC (AED) | Income After SC (AED) | Yield After SC |
|-------------|---------|------|-------------|---------|-----------------|-------------|-----------------|----------------------|----------------|
| 4744 | Ahad Residences | Business Bay | VERIFIED_EXACT | 2026 | 20.26 | 2,308 | 46,760 | 116,440 | 2.48% |
| 6435 | Pantheon Elysee | JVC | VERIFIED_EXACT | 2025 | 14.60 | 763 | 11,140 | 56,060 | 6.60% |
| 7266 | Ahad Residences | Business Bay | VERIFIED_EXACT | 2026 | 20.26 | 894 | 18,112 | 92,288 | 5.13% |
| 1074 | Ahad Residences | Business Bay | VERIFIED_EXACT | 2026 | 20.26 | 453 | 9,178 | 67,622 | 5.41% |
| 4165 | Ahad Residences | Business Bay | VERIFIED_EXACT | 2026 | 20.26 | 1,625 | 32,923 | 154,278 | 4.72% |
| 7842 | Azizi Feirouz | Al Furjan | VERIFIED_NORMALIZED_EXACT | 2026 | 12.11 | 1,008 | 12,207 | 58,353 | 5.72% |

---

## 2. FROZEN MATCHING METHODOLOGY

### Rule Change (Critical)

**Exact project-name equality is NOT sufficient for verification.**

Every service-charge project match requires:
1. **Project name match** (EXACT, NORMALIZED_EXACT, or VERIFIED_ALIAS)
2. **Location/community parity** (normalized area match)

### Match Types

| Type | Description |
|------|-------------|
| VERIFIED_EXACT | Exact project name match + location parity |
| VERIFIED_NORMALIZED_EXACT | Normalized name match (punctuation/hyphen differences) + location parity |
| VERIFIED_ALIAS | Manually verified alias (phase/variant) + location parity + cross-field support |
| REJECTED_IDENTITY | Name matched but location conflict — permanently rejected |
| NOT_MATCHED | No name match found |

### Normalization Rules (frozen)

1. Lowercase
2. Trim whitespace
3. Collapse repeated whitespace
4. Hyphen → space
5. Slash → space
6. Period removal (`azizi.` → `azizi`)
7. Other punctuation removal
8. Final whitespace collapse + trim

### Location Parity Rule (frozen)

MASTER area must match Mollak community OR Mollak area_name after normalization. Token overlap (≥2 meaningful tokens) is sufficient for longer area names.

---

## 3. FROZEN BLACKLIST

| MASTER Project | MASTER Area | Mollak Project | Mollak Community | Reason |
|---------------|-------------|---------------|-----------------|--------|
| Golf Links | Emaar South | GOLF LINKS | Dubai Sports City | Same name, different projects in different locations. Emaar South has zero Mollak entries. |

**This pair must NEVER be recreated by future exact-name matching logic.**

---

## 4. SEPARATE STATUS FIELDS (frozen)

### project_match_status

| Value | Meaning |
|-------|---------|
| VERIFIED_EXACT | Project identity confirmed via exact name + location |
| VERIFIED_NORMALIZED_EXACT | Project identity confirmed via normalized name + location |
| VERIFIED_ALIAS | Project identity confirmed via alias + location + cross-field |
| REJECTED_IDENTITY | Name matched but location conflict — rejected |
| NOT_MATCHED | No match found |

### service_charge_status

| Value | Meaning |
|-------|---------|
| VERIFIED_CALCULABLE | All checks pass — calculation eligible |
| HELD_COMPONENT_MISMATCH | GF + RF ≠ Grand Total (Mollak source issue) |
| HELD_AREA_BASIS | Property type or area basis unverified |
| HELD_USAGE | Wrong Mollak usage rate |
| HELD_YEAR | Future budget year |
| HELD_NO_RENT | No rent estimate available |
| NOT_MATCHED | No service charge match |

### Example: Harbour Views (409)

- `project_match_status = VERIFIED_ALIAS` (identity confirmed)
- `service_charge_status = HELD_COMPONENT_MISMATCH` (rate held)
- `production_eligible = false`

**The alias is NOT downgraded. Only the rate calculation is held.**

---

## 5. FROZEN VERIFICATION CHECKS

For a property to be `production_eligible = true`, ALL of the following must pass:

| Check | Requirement |
|-------|-------------|
| Project identity | VERIFIED_EXACT / VERIFIED_NORMALIZED_EXACT / VERIFIED_ALIAS |
| Location parity | MASTER area matches Mollak community/area |
| Property type | Apartment (Qdrant category) — villa/townhouse area basis unverified |
| Mollak usage | Residential (not commercial/retail/parking/stores) |
| Component match | General Fund + Reserve Fund = Grand Total (within 0.01) |
| Year valid | Budget year ≤ valuation date (2026) |
| Unit size | MASTER unit_size_sqft present and > 0 |
| Annual rent | Available from existing rental engine |
| Master price | current_price_aed present and > 0 |

---

## 6. FROZEN FORMULAS

### Service Charge
```
annual_service_charge_aed = official_mollak_rate_aed_sqft × verified_chargeable_area_sqft
```

### Income After Service Charges
```
income_after_service_charges_aed = annual_rent_estimate_aed - annual_service_charge_aed
```

### Yield After Service Charges
```
yield_after_service_charges_pct = (income_after_service_charges_aed / MASTER current_price_aed) × 100
```

---

## 7. FROZEN LABELS

| Metric | Label (UI) | NOT Label |
|--------|-----------|-----------|
| income_after_service_charges_aed | **Income After Service Charges** | ~~Net Rental Income~~ |
| yield_after_service_charges_pct | **Yield After Service Charges** | ~~Net Rental Yield~~ |

---

## 8. FROZEN YEAR SELECTION RULE

**Rule**: Latest officially approved Mollak budget year available for the verified project, where year ≤ valuation date.

No mixing of years. Each property uses exactly one year's rate.

---

## 9. FROZEN COMPONENT AUDIT

Mollak `grand_total_aed_sqft` includes:
- General Fund (total_gf_aed_sqft)
- Reserve Fund (total_rf_aed_sqft)
- Sub-components: Services, Maintenance, Utilities Services, Management Services, Insurance, Master Community, Improvement

**ALL components are OA/Building-level costs.** None are landlord-level costs.

The "Management Services" and "Maintenance" components are OA building-level, NOT landlord property management fees or unit maintenance costs.

---

## 10. HELD PROPERTIES (not frozen for calculation)

### Property 409 — Harbour Views 1

| Field | Value |
|-------|-------|
| project_match_status | VERIFIED_ALIAS |
| service_charge_status | HELD_COMPONENT_MISMATCH |
| production_eligible | false |
| Reason | GF (15.61) + RF (1.28) = 16.89 ≠ Grand Total (16.82) |
| Discrepancy | 0.07 AED/sqft (Mollak source rounding) |
| Action | Held until Mollak source semantics/precision resolved |

**The Harbour Views alias IS frozen as verified. The rate is NOT frozen.**

---

## 11. REJECTED PROPERTIES (permanently blacklisted)

### Property 6217 — Golf Links

| Field | Value |
|-------|-------|
| project_match_status | REJECTED_IDENTITY |
| service_charge_status | NOT_MATCHED |
| production_eligible | false |
| Reason | MASTER "Golf Links" (Emaar South) ≠ Mollak "GOLF LINKS" (Dubai Sports City) |
| Action | Permanently blacklisted. Do not recreate. |

---

## 12. FULL 315 COVERAGE SUMMARY

| Category | Count |
|----------|-------|
| PROJECT_IDENTITY_VERIFIED_COUNT | 7 |
| SERVICE_CHARGE_CALCULABLE_COUNT | 6 |
| SERVICE_CHARGE_HELD_COUNT | 1 |
| SERVICE_CHARGE_NO_MATCH_COUNT | 308 |
| REJECTED_IDENTITY_COUNT | 1 |
| EXACT_NAME_WITH_LOCATION_CONFLICT_USED | 0 |

---

## 13. SAFETY COUNTERS — ALL ZERO

| Counter | Value |
|---------|-------|
| MATCH_HARDENING_CHANGED_RENT_ESTIMATE | 0 |
| MATCH_HARDENING_CHANGED_RENT_TIER | 0 |
| MATCH_HARDENING_CHANGED_GROSS_YIELD | 0 |
| MATCH_HARDENING_CHANGED_MARKET_CONTEXT | 0 |
| MATCH_HARDENING_CHANGED_PRODUCTION_SIGNAL | 0 |
| MATCH_HARDENING_CHANGED_APIL_ADVANTAGE | 0 |
| MATCH_HARDENING_CHANGED_CONVENTIONAL_POSITION | 0 |
| MATCH_HARDENING_CHANGED_FIT_SCORE | 0 |
| NORMAL_RUNTIME_IMPORTS_COST_ENGINE | 0 |
| SERVICE_CHARGE_ARITHMETIC_MISMATCH | 0 |
| ADJUSTED_INCOME_ARITHMETIC_MISMATCH | 0 |
| ADJUSTED_YIELD_ARITHMETIC_MISMATCH | 0 |

---

## 14. CALCULATION LEVEL DISCLOSURE

```
calculation_level = SERVICE_CHARGE_ADJUSTED
cost_coverage = {
    annual_rent: AVAILABLE,
    service_charge: VERIFIED,
    vacancy: MISSING,
    management: MISSING,
    maintenance: MISSING
}
NOT_INCLUDED = [vacancy, landlord_management, unit_maintenance]
```

**This is NOT Net Rental Income. Only one verified operating cost (service charge) has been deducted.**

---

## 15. OUTPUT FILES

| File | Description |
|------|-------------|
| `rental_cost_outputs/service_charge_full_315_coverage_v1_final.csv` | All 315 Ready properties with match/eligibility status |
| `rental_cost_outputs/service_charge_v1_final_freeze_verdict.json` | Final verdict data |
| `rental_cost_outputs/SERVICE_CHARGE_ADJUSTED_INCOME_V1_FROZEN.md` | This freeze document |

---

## 16. VERDICT

### **SERVICE_CHARGE_ADJUSTED_INCOME_V1_READY_FOR_UI**

| Check | Result |
|-------|--------|
| Eligible properties | 6 (independently verified) |
| Arithmetic failures | 0 |
| Location conflict used | 0 |
| All safety counters | 0 |
| Engine isolation | ✅ |
| Blacklist enforced | ✅ |
| Harbour Views held | ✅ (alias verified, rate held) |

**FROZEN. Ready for UI integration pending explicit approval.**

**STOP. Do NOT wire UI yet. Do NOT calculate vacancy. Do NOT calculate Net Rental Income. Do NOT start Full Property ROI.**
