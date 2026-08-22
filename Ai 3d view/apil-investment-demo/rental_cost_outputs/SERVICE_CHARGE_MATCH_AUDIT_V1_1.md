# SERVICE CHARGE MATCH AUDIT V1.1

**Date**: 2026-08-20
**Verdict**: **SERVICE_CHARGE_COVERAGE_V1_1_VERIFIED**
**Phase**: Verified match expansion only — no calculations, no UI changes

---

## 1. SUMMARY

| Metric | Value |
|--------|-------|
| READY_TOTAL | 315 |
| OLD_VERIFIED_COUNT | 6 |
| NEW_VERIFIED_COUNT | **8** |
| EXACT_COUNT | 6 |
| NORMALIZED_EXACT_COUNT | 1 |
| VERIFIED_ALIAS_COUNT | 1 |
| AMBIGUOUS_COUNT | 23 |
| NO_MATCH_COUNT | 284 |
| ANNUAL_CHARGE_CALCULABLE_COUNT | 8 |

Coverage increased from 6 (1.9%) to 8 (2.5%) of 315 Ready properties.

---

## 2. EXISTING 6 EXACT VERIFIED MATCHES

| Property ID | MASTER Project | MASTER Area | MASTER Developer | Mollak Project | SC Year | Rate (AED/sqft) | Match Method | Status |
|-------------|---------------|-------------|-----------------|---------------|---------|-----------------|-------------|--------|
| 4744 | Ahad Residences | Business Bay | — | Ahad Residences | 2026 | 20.26 | EXACT | VERIFIED |
| 6435 | Pantheon Elysee | JVC | — | PANTHEON ELYSEE | 2025 | 14.60 | EXACT | VERIFIED |
| 7266 | Ahad Residences | Business Bay | — | Ahad Residences | 2026 | 20.26 | EXACT | VERIFIED |
| 1074 | Ahad Residences | Business Bay | — | Ahad Residences | 2026 | 20.26 | EXACT | VERIFIED |
| 6217 | Golf Links | Dubai Hills | — | GOLF LINKS | 2026 | 18.36 | EXACT | VERIFIED |
| 4165 | Ahad Residences | Business Bay | — | Ahad Residences | 2026 | 20.26 | EXACT | VERIFIED |

---

## 3. NORMALIZED EXACT MATCH (1 new)

| Property ID | MASTER Project | Mollak Project | Normalized (both) | SC Year | Rate (AED/sqft) | Match Method | Status |
|-------------|---------------|---------------|-------------------|---------|-----------------|-------------|--------|
| 7842 | Azizi Feirouz | AZIZI. FEIROUZ | `azizi feirouz` | 2026 | *(see CSV)* | EXACT_AFTER_NORMALIZATION | VERIFIED |

**Normalization applied**: Lowercase + period removal (`"AZIZI."` → `"azizi"`). The only difference was a period after "AZIZI" in the Mollak source. After deterministic normalization, both names are identical: `azizi feirouz`.

---

## 4. VERIFIED ALIAS (1 new)

| Property ID | MASTER Project | Mollak Project | Similarity | Area Match | Dev Match | Phase Match | Token Overlap | Status |
|-------------|---------------|---------------|-----------|-----------|-----------|-------------|---------------|--------|
| 409 | Harbour Views 1 | HARBOUR VIEWS | 0.9286 | No | Yes | Yes | {harbour, views} | VERIFIED_ALIAS |

**Verification basis**: "Harbour Views 1" is phase 1 of the "HARBOUR VIEWS" development. After removing the phase number, both normalize to `harbour views`. The meaningful tokens `{harbour, views}` overlap. Developer cross-check confirms the same development entity.

---

## 5. DETERMINISTIC NORMALIZATION RULES

The following normalization steps are applied (in order):

1. **Lowercase**: `str.lower()`
2. **Trim**: `str.strip()`
3. **Collapse whitespace**: `\s+` → single space
4. **Hyphen → space**: `binghatti-royale` → `binghatti royale`
5. **Slash → space**: `a/b` → `a b`
6. **Period removal**: `azizi. feirouz` → `azizi feirouz`
7. **Other punctuation removal**: `[^\w\s]` removed
8. **Final whitespace collapse + trim**

**Suffix removal** was tested but **rejected** for V1.1 because it caused false matches:
- "Vera Residences" → "vera" (after stripping "residences")
- "Vera Tower" → "vera" (after stripping "tower")
- These are DIFFERENT projects but would falsely match

The suffix removal rule requires the remaining core to be ≥8 characters, which prevents most false matches but also prevents most legitimate matches. It was not used for any verified matches in V1.1.

---

## 6. SAFE ALIAS RULES

A fuzzy candidate is classified as VERIFIED_ALIAS only when ALL of the following are true:

1. **Similarity score ≥ 0.85**
2. **Meaningful token overlap**: At least 1 non-generic, non-developer-name token shared
3. **Cross-field support**: At least one of:
   - Area match (normalized area names identical)
   - Developer match (developer name cross-references)
   - Phase match (core name matches after removing trailing phase numbers)

**Generic tokens excluded**: the, by, residences, residence, tower, towers, apartments, apartment, building, buildings, properties, property, real, estate, dubai

**Developer name tokens excluded**: omniyat, emaar, damac, azizi, nakheel, etc. — these are NOT project identity tokens.

### Rejected False Matches

| Candidate | Why Rejected |
|-----------|-------------|
| Vera Residences → REVA RESIDENCES | No meaningful token overlap (vera ≠ reva) |
| The Pad by Omniyat → THE OPUS BY OMNIYAT | Only shared token is "omniyat" (developer name, excluded). Different buildings. |
| Mama Residences → Ahad Residences | No meaningful token overlap (mama ≠ ahad). Different projects. |
| Aura Residences → Ahad Residences | No meaningful token overlap (aura ≠ ahad). Different projects. |
| AG Tower → G-TOWER | No meaningful token overlap (ag ≠ g). Different buildings. |
| Empire Residences → DEZIRE RESIDENCES | No meaningful token overlap (empire ≠ dezire). Different projects. |
| Canal Residence West → Canal Residence West 2 | Ambiguous: "West" and "West 2" may be different phases. No area/dev cross-check. |
| Pantheon Elysee II/III → PANTHEON ELYSEE | Ambiguous: II/III are different phases. No area/dev cross-check to confirm same budget. |

---

## 7. CHARGE BASIS VERIFICATION

### Mollak Data Structure

| Field | Description |
|-------|-------------|
| `grand_total_aed_sqft` | Total service charge rate (AED per sqft per year) |
| `total_gf_aed_sqft` | General Fund component |
| `total_rf_aed_sqft` | Reserve Fund component |
| `grand_total = total_gf + total_rf` | Verified: sum is correct |
| `budget_start` / `budget_end` | Annual budget period |
| `properties_count` | Number of units under this budget |

### Area Basis

- **Mollak rate basis**: AED per sqft of built-up area (BUA) per year
- **MASTER field**: `unit_size_sqft` (unit built-up area)
- **For apartments**: `unit_size_sqft ≈ chargeable BUA` → **CORRECT**
- **For villas/penthouses**: May differ (plot area vs BUA) → **NEEDS VERIFICATION**

### Annual Charge Calculation

```
annual_service_charge_aed = rate_aed_sqft × unit_size_sqft
```

This calculation is performed only when:
1. Service charge rate is from official DLD/Mollak source (verified match)
2. `unit_size_sqft` is present in MASTER_FINAL and > 0
3. Property type is apartment (not villa/penthouse — area basis unconfirmed)

**AMBIGUOUS_AREA_BASIS_USED = 0** — All 8 verified matches have confirmed unit sizes and are apartments.

**ANNUAL_CHARGE_CALCULABLE_COUNT = 8** (all 8 verified matches have calculable annual charges)

---

## 8. COMPONENT AUDIT

### Components Found in Verified Projects

| Component | Projects | Classification |
|-----------|---------|---------------|
| Services | 6 | OA service charge (in grand_total) |
| Maintenance | 6 | OA building maintenance (NOT landlord unit maintenance) |
| Utilities Services | 6 | OA utilities (in grand_total) |
| Management Services | 6 | OA management (NOT landlord property management fee) |
| Insurance | 6 | OA building insurance (in grand_total) |
| Master Community | 6 | Master community charge (in grand_total) |
| Improvement | 5 | OA improvement fund (in grand_total) |

### Key Distinction

| OA Component (in grand_total) | NOT the same as |
|------------------------------|-----------------|
| Management Services | Landlord property management fee |
| Maintenance | Landlord unit interior maintenance |
| Insurance | Landlord contents insurance |

**ALL components are OA/Building-level costs.** `grand_total_aed_sqft` = sum of all components = official service charge obligation.

---

## 9. YEAR SELECTION RULE

**Rule**: Latest officially approved year available.

| Project | Available Years | Year Used |
|---------|----------------|-----------|
| Ahad Residences | 2023, 2024, 2025, 2026 | 2026 |
| PANTHEON ELYSEE | 2021, 2022, 2023, 2024, 2025 | 2025 |
| GOLF LINKS | 2026 | 2026 |
| HARBOUR VIEWS | 2021, 2022, 2023, 2024, 2025, 2026 | 2026 |
| AZIZI. FEIROUZ | 2019–2026 | 2026 |

No years are mixed. Each project uses exactly one year (the latest available).

---

## 10. COVERAGE SUMMARY

| Category | Count | % of 315 Ready |
|----------|-------|----------------|
| EXACT_VERIFIED | 6 | 1.9% |
| NORMALIZED_EXACT_VERIFIED | 1 | 0.3% |
| VERIFIED_ALIAS | 1 | 0.3% |
| **TOTAL VERIFIED** | **8** | **2.5%** |
| AMBIGUOUS | 23 | 7.3% |
| NO_MATCH | 284 | 90.2% |
| **TOTAL** | **315** | **100%** |

---

## 11. AMBIGUOUS CANDIDATES (23)

These candidates have similarity ≥ 0.85 but lack sufficient cross-field support (area match, developer match, or meaningful token overlap). They are NOT promoted to verified.

| Property ID | MASTER Project | Mollak Project | Score | Reason |
|-------------|---------------|---------------|-------|--------|
| 7608 | Vera Residences | REVA RESIDENCES | 0.867 | No token overlap (vera ≠ reva) |
| 601 | Aura Residences | Ahad Residences | 0.867 | No token overlap |
| 8369 | Aura Residences | Ahad Residences | 0.867 | No token overlap |
| 5497 | Aura Residences | Ahad Residences | 0.867 | No token overlap |
| 7464 | Plaza Residences 1 | TOPAZ RESIDENCES 1 | 0.889 | Only shared token is "1" (phase number) |
| 6530 | Empire Residences | DEZIRE RESIDENCES | 0.882 | No token overlap |
| 5801 | Empire Residences | DEZIRE RESIDENCES | 0.882 | No token overlap |
| 6473 | Empire Residences | DEZIRE RESIDENCES | 0.882 | No token overlap |
| 884 | Canal Residence West | Canal Residence West 2 | 0.952 | Phase ambiguity, no cross-field |
| 4702 | Canal Residence West | Canal Residence West 2 | 0.952 | Phase ambiguity, no cross-field |
| 4750 | Canal Residence West | Canal Residence West 2 | 0.952 | Phase ambiguity, no cross-field |
| 5513 | Canal Residence West | Canal Residence West 2 | 0.952 | Phase ambiguity, no cross-field |
| 5402 | The Pad by Omniyat | THE OPUS BY OMNIYAT | 0.865 | Only shared token is "omniyat" (developer) |
| 7622 | The Pad by Omniyat | THE OPUS BY OMNIYAT | 0.865 | Only shared token is "omniyat" (developer) |
| 7669 | Pantheon Elysee III | PANTHEON ELYSEE | 0.882 | Phase ambiguity, no cross-field |
| 5431 | Pantheon Elysee II | PANTHEON ELYSEE | 0.909 | Phase ambiguity, no cross-field |
| 3599 | Pantheon Elysee II | PANTHEON ELYSEE | 0.909 | Phase ambiguity, no cross-field |
| 655 | Pantheon Elysee III | PANTHEON ELYSEE | 0.882 | Phase ambiguity, no cross-field |
| 1656 | AG Tower | G-TOWER | 0.933 | No token overlap (ag ≠ g) |
| 5793 | AG Tower | G-TOWER | 0.933 | No token overlap |
| 7170 | AG Tower | G-TOWER | 0.933 | No token overlap |
| 5961 | Vera Residences | REVA RESIDENCES | 0.867 | No token overlap |
| 2381 | Mama Residences | Ahad Residences | 0.867 | No token overlap |

**Note**: The "Pantheon Elysee II/III" candidates share meaningful tokens `{pantheon, elysee}` with "PANTHEON ELYSEE" but are classified as AMBIGUOUS because phase II/III may have different service charge budgets than the base project. A manual review could potentially promote these if the Mollak data covers all phases under one budget.

---

## 12. SAFETY COUNTERS — ALL ZERO

### Engine Isolation

| Counter | Value | Status |
|---------|-------|--------|
| SERVICE_CHARGE_WORK_CHANGED_RENT_ESTIMATE | 0 | ✅ |
| SERVICE_CHARGE_WORK_CHANGED_RENT_TIER | 0 | ✅ |
| SERVICE_CHARGE_WORK_CHANGED_GROSS_YIELD | 0 | ✅ |
| SERVICE_CHARGE_WORK_CHANGED_MARKET_CONTEXT | 0 | ✅ |
| SERVICE_CHARGE_WORK_CHANGED_PRODUCTION_SIGNAL | 0 | ✅ |
| SERVICE_CHARGE_WORK_CHANGED_APIL_ADVANTAGE | 0 | ✅ |
| SERVICE_CHARGE_WORK_CHANGED_CONVENTIONAL_POSITION | 0 | ✅ |
| SERVICE_CHARGE_WORK_CHANGED_FIT_SCORE | 0 | ✅ |

### Matching Safety

| Counter | Value | Status |
|---------|-------|--------|
| FUZZY_ONLY_MATCH_PROMOTED_TO_VERIFIED | 0 | ✅ |
| RUNTIME_FUZZY_SERVICE_CHARGE_MATCH | 0 | ✅ |
| AMBIGUOUS_AREA_BASIS_USED | 0 | ✅ |
| NORMAL_REQUEST_IMPORTS_SERVICE_CHARGE_ENGINE | 0 | ✅ |

**All 12 safety counters at 0.**

---

## 13. OUTPUT FILES

| File | Description | Rows |
|------|-------------|------|
| `rental_cost_outputs/service_charge_verified_matches_v1_1.csv` | All 8 verified matches | 8 |
| `rental_cost_outputs/service_charge_project_aliases_v1.csv` | VERIFIED_ALIAS entries | 1 |
| `rental_cost_outputs/service_charge_ambiguous_matches_v1_1.csv` | Ambiguous candidates | 23 |
| `rental_cost_outputs/service_charge_audit_v1_1_verdict.json` | Verdict data | — |
| `rental_cost_outputs/SERVICE_CHARGE_MATCH_AUDIT_V1_1.md` | This report | — |

---

## 14. VERDICT

### **SERVICE_CHARGE_COVERAGE_V1_1_VERIFIED**

Coverage expanded from 6 to 8 verified matches (2 new: 1 normalized exact + 1 verified alias). All safety counters at 0. No existing runtime modified. No calculations performed beyond annual service charge estimation (rate × size). No UI changed.

**STOP. No Net Rental Income calculated. No UI changed. Waiting for explicit approval.**
