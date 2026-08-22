# SERVICE CHARGE V2.4 — RATE-SCOPE RESOLUTION + PRODUCTION PROMOTION READINESS

**Date**: 2026-08-21
**Verdict**: **SERVICE_CHARGE_V2_4_READY_FOR_CONTROLLED_PROMOTION**
**Status**: SHADOW AUDIT ONLY — No production changes made

---

## 1. EXECUTIVE SUMMARY

| Metric | Value |
|--------|-------|
| CURRENT_PRODUCTION_ELIGIBLE | 6 |
| CANDIDATES_AUDITED | 10 |
| **READY_FOR_PRODUCTION_PROMOTION_COUNT** | **6** |
| HELD_RATE_SCOPE_COUNT | 4 |
| HELD_OTHER_COUNT | 0 |
| **POTENTIAL_PRODUCTION_TOTAL** | **12** |
| REPRESENTATIVE_RATE_USED_IN_PRODUCTION | 0 ✅ |
| DUBAI_CREEK_6_TOWER_SHARED_RATE_CONFIRMED | YES ✅ |

**6 properties are ready for controlled promotion. 4 properties are held due to unresolved rate scope.**

---

## 2. GROUP A — READY FOR PRODUCTION PROMOTION (6 properties)

### 2a. Harbour Views 1 (409)

| Field | Value |
|-------|-------|
| Mollak project | Harbour Views |
| Mollak property groups | 1 (single group: "Harbour Views", id=310544607) |
| Budget scope | Single Mollak property group covers both Harbour Views 1 and 2 (twin towers) |
| Tower scope | Harbour Views = twin towers (HV1 + HV2) on shared podium; single OA budget |
| GT rate | 16.82 AED/sqft |
| rate_scope_verified | **YES** |
| Evidence | Emaar official: "tallest twin towers on Creek Island". Bayut: "two 51-storey towers". Single jointly owned property. |
| Official source | Emaar Properties, ECM, Bayut, Mollak API |

**Shadow calculation:**
| Field | Value |
|-------|-------|
| Unit size | 1,526 sqft |
| Annual rent | AED 163,200 |
| Current price | AED 2,700,000 |
| Annual SC | AED 25,667.32 |
| Income After SC | AED 137,532.68 |
| Yield After SC | 5.09% |

### 2b. Marquise Square (4 properties: 8201, 1208, 5582, 3160)

| Field | Value |
|-------|-------|
| Mollak project | MARQUISE SQUARE TOWER |
| Mollak property groups | 1 residential (other 2 are "Developer Extra Parking", not residential) |
| Budget scope | Single residential Mollak property group |
| Tower scope | Marquise Square = single 29-storey tower, 384 units |
| GT rate | 16.85 AED/sqft |
| rate_scope_verified | **YES** |
| Evidence | JRE: "single tower, 29 storeys". Bayut: "29-storey residential building". FazWaz: "384 units across 29 floors". RERA escrow #1011221899533019. |
| Official source | JRE Dubai, Bayut, FazWaz, Mollak API |

**Shadow calculations:**
| Property | Size (sqft) | Price (AED) | Annual Rent (AED) | Annual SC (AED) | Income After SC (AED) | Yield After SC |
|----------|-------------|-------------|-------------------|-----------------|----------------------|----------------|
| 8201 | 2,326 | 4,300,000 | 163,200 | 39,193.10 | 124,006.90 | 2.88% |
| 1208 | 1,064 | 2,100,000 | 96,000 | 17,928.40 | 78,071.60 | 3.72% |
| 5582 | 1,658 | 2,900,000 | 129,600 | 27,937.30 | 101,662.70 | 3.51% |
| 3160 | 517 | 1,225,000 | 57,600 | 8,711.45 | 48,888.55 | 3.99% |

### 2c. Dubai Creek Residence Tower 2 North (7881)

| Field | Value |
|-------|-------|
| Mollak project | THE DUBAI CREEK RESIDENCES |
| Mollak property groups | 1 (single group: "The Dubai Creek Residences", id=106778868) |
| Budget scope | Single Mollak property group covers all 6 towers |
| Tower scope | Dubai Creek Residences = 6 waterfront towers, single OA budget |
| GT rate | 16.50 AED/sqft |
| rate_scope_verified | **YES** |
| DUBAI_CREEK_6_TOWER_SHARED_RATE_CONFIRMED | **YES** |
| Evidence | ECM official: "comprises six waterfront towers". Dubai Holding: "six-tower residential development". Christie's: "collection of six residential towers". |
| Official source | ECM (Emaar Community Management), Dubai Holding, Christie's, Mollak API |

**Shadow calculation:**
| Field | Value |
|-------|-------|
| Unit size | 1,020 sqft |
| Annual rent | AED 120,000 |
| Current price | AED 1,399,990 |
| Annual SC | AED 16,830.00 |
| Income After SC | AED 103,170.00 |
| Yield After SC | 7.37% |

---

## 3. GROUP B — HELD RATE SCOPE (4 properties)

### Canal Residence West Phase 1 (884, 4702, 4750, 5513)

| Field | Value |
|-------|-------|
| Mollak project | CANAL RESIDENCE WEST (PHASE 1) |
| Mollak property groups | **3 residential** (European, Venetian, Mediterranean) |
| Budget scope | 3 separate residential Mollak property groups with **different rates** |
| Tower scope | Canal Residence West Phase 1 = 3 completed towers with separate OA budgets |
| GT rates | European=13.92, Venetian=13.91, Mediterranean=13.94 AED/sqft |
| rate_scope_verified | **NO** |
| resolved_property_group | UNRESOLVED |
| confidence | NONE |
| promotion_status | **HELD_RATE_SCOPE** |
| project_match_status | VERIFIED_PHASE_1 (not downgraded) |

**Why unresolved:**

MASTER data contains no tower identification:
- `sub_project`: "Canal Residence West" (generic)
- No building/tower field

Qdrant data contains no tower identification:
- `building_name`: "Canal Residence West" (generic for all 4)
- `project_name`: "Canal Residence West" (generic)
- `district`: "Al Hebiah Fourth" (same for all)
- No unit number, floor, or tower reference in any metadata field
- All 4 properties share the same `video_id` and `latitude/longitude`

**The 0.03 AED/sqft max difference does NOT authorize substitution.** Per the V2.4 requirements, the small difference is not a basis for using a representative rate.

| Property | Status | SC Rate | Annual SC | Income After SC | Yield After SC |
|----------|--------|---------|-----------|-----------------|----------------|
| 884 | HELD_RATE_SCOPE | UNRESOLVED | N/A | N/A | N/A |
| 4702 | HELD_RATE_SCOPE | UNRESOLVED | N/A | N/A | N/A |
| 4750 | HELD_RATE_SCOPE | UNRESOLVED | N/A | N/A | N/A |
| 5513 | HELD_RATE_SCOPE | UNRESOLVED | N/A | N/A | N/A |

**Resolution path (future):** These properties can only be promoted if:
1. MASTER is enriched with tower identification (European/Venetian/Mediterranean), OR
2. Qdrant metadata is enriched with tower-specific building names, OR
3. DLD transaction data links the unit to a specific tower

---

## 4. HISTORICAL AUDIT TRACE

| Item | Value |
|------|-------|
| OLD RULE | GF + RF = GT |
| OLD RULE STATUS | **RETIRED_AS_SEMANTICALLY_INCORRECT** |
| NEW VALIDATION RULE | GF + RF − income = GT |
| CALCULATION RATE | grandTotal (grand_total_aed_sqft) |

---

## 5. CORRECTED MOLLAK DATA MODEL

Future production source records must preserve:

| Field | Source | Purpose |
|-------|--------|---------|
| total_gf_aed_sqft | gfData.totalGF | General Fund rate |
| total_rf_aed_sqft | rfData.totalRF | Reserve Fund rate |
| income_offset_aed_sqft | gfData.income | Income offset (NEW FIELD) |
| grand_total_aed_sqft | gfData.grandTotal | **Authoritative calculation rate** |

**Validation:** total_gf + total_rf − income = grand_total

**Calculation:** annual_service_charge = grand_total × verified_chargeable_area

**Do NOT calculate the production rate from components.**

---

## 6. FINAL CALCULATION RECHECK

For all 6 promotion-ready candidates:

| Check | Result |
|-------|--------|
| V24_SC_ARITHMETIC_MISMATCH | 0 ✅ |
| V24_ADJUSTED_INCOME_MISMATCH | 0 ✅ |
| V24_ADJUSTED_YIELD_MISMATCH | 0 ✅ |

All shadow calculations verified:
- annual_sc = grand_total × unit_size_sqft ✅
- income_after_sc = annual_rent − annual_sc ✅
- yield_after_sc = income_after_sc / current_price × 100 ✅

---

## 7. FROZEN SIX MUST REMAIN UNCHANGED

| Counter | Value |
|---------|-------|
| V24_CHANGED_FROZEN_RATE | 0 ✅ |
| V24_CHANGED_FROZEN_SC | 0 ✅ |
| V24_CHANGED_FROZEN_INCOME_AFTER_SC | 0 ✅ |
| V24_CHANGED_FROZEN_YIELD_AFTER_SC | 0 ✅ |

The frozen 6 all have income = 0, so their rates and calculations are unchanged under both old and new rules.

---

## 8. ALL 20 REGRESSION/SAFETY COUNTERS — ALL ZERO

| Counter | Value |
|---------|-------|
| V24_CHANGED_ANNUAL_RENT | 0 ✅ |
| V24_CHANGED_RENT_RANGE | 0 ✅ |
| V24_CHANGED_RENT_TIER | 0 ✅ |
| V24_CHANGED_GROSS_YIELD | 0 ✅ |
| V24_CHANGED_GROSS_YIELD_RANGE | 0 ✅ |
| V24_CHANGED_MARKET_CONTEXT | 0 ✅ |
| V24_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| V24_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| V24_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| V24_CHANGED_FIT_SCORE | 0 ✅ |
| V24_CHANGED_PRODUCTION_PROVIDER | 0 ✅ |
| V24_CHANGED_UI | 0 ✅ |
| V24_CHANGED_FRONTEND | 0 ✅ |
| V24_SC_ARITHMETIC_MISMATCH | 0 ✅ |
| V24_ADJUSTED_INCOME_MISMATCH | 0 ✅ |
| V24_ADJUSTED_YIELD_MISMATCH | 0 ✅ |
| V24_CHANGED_FROZEN_RATE | 0 ✅ |
| V24_CHANGED_FROZEN_SC | 0 ✅ |
| V24_CHANGED_FROZEN_INCOME_AFTER_SC | 0 ✅ |
| V24_CHANGED_FROZEN_YIELD_AFTER_SC | 0 ✅ |

- 409 still held in runtime: YES ✅
- 6217 still rejected: YES ✅
- REPRESENTATIVE_RATE_USED_IN_PRODUCTION: 0 ✅

---

## 9. REJECTED IDENTITIES — NOT REOPENED

| Project | Status | Reason |
|---------|--------|--------|
| Golf Links 6217 | REJECTED_IDENTITY | Cross-community (Emaar South ≠ Dubai Sports City) |
| Pantheon Elysee II (3599, 5431) | REJECTED | Separate project (District 12 ≠ District 13) |
| Pantheon Elysee III (655, 7669) | REJECTED | Separate project (District 15 ≠ District 13) |
| The Pad by Omniyat (5402, 7622) | REJECTED | Different buildings; only developer token overlaps |
| Creek Beach Orchid → Creek Horizon (432, 1913, 6594) | REJECTED | Different projects on DCH master plan |
| Harbour Gate → Harbour Views (735, 3231, 4263) | REJECTED | Different projects on DCH master plan |
| Creek Rise → Creekside 18 (5528, 5579, 7449, 1298) | REJECTED | Different projects on DCH master plan |

Corrected component semantics do NOT repair identity mismatch.

---

## 10. PRODUCTION READINESS CLASSIFICATION

| Property | Status | GT Rate | Annual SC (AED) | Yield After SC |
|----------|--------|---------|-----------------|----------------|
| 409 | READY_FOR_PRODUCTION_PROMOTION | 16.82 | 25,667 | 5.09% |
| 8201 | READY_FOR_PRODUCTION_PROMOTION | 16.85 | 39,193 | 2.88% |
| 1208 | READY_FOR_PRODUCTION_PROMOTION | 16.85 | 17,928 | 3.72% |
| 5582 | READY_FOR_PRODUCTION_PROMOTION | 16.85 | 27,937 | 3.51% |
| 3160 | READY_FOR_PRODUCTION_PROMOTION | 16.85 | 8,711 | 3.99% |
| 7881 | READY_FOR_PRODUCTION_PROMOTION | 16.50 | 16,830 | 7.37% |
| 884 | HELD_RATE_SCOPE | UNRESOLVED | N/A | N/A |
| 4702 | HELD_RATE_SCOPE | UNRESOLVED | N/A | N/A |
| 4750 | HELD_RATE_SCOPE | UNRESOLVED | N/A | N/A |
| 5513 | HELD_RATE_SCOPE | UNRESOLVED | N/A | N/A |

---

## 11. OUTPUT FILES

| File | Description |
|------|-------------|
| `SERVICE_CHARGE_V2_4_PROMOTION_READINESS.md` | This report |
| `service_charge_v2_4_rate_scope_audit.csv` | All 10 candidates with rate scope verification |
| `service_charge_v2_4_promotion_candidates.csv` | 6 promotion-ready candidates with shadow calcs |
| `service_charge_v2_4_held_candidates.csv` | 4 held candidates (rate scope unresolved) |
| `service_charge_v2_4_verdict.json` | Machine-readable verdict + all counters |

---

## 12. VERDICT

### **SERVICE_CHARGE_V2_4_READY_FOR_CONTROLLED_PROMOTION**

| Check | Result |
|-------|--------|
| Ready for promotion | 6 properties |
| Held rate scope | 4 properties |
| Held other | 0 |
| Potential production total | 12 (6 existing + 6 new) |
| Representative rate used | 0 ✅ |
| All 20 regression/safety counters | 0 ✅ |
| Frozen 6 unchanged | YES ✅ |
| 409 still held in runtime | YES ✅ |
| 6217 still rejected | YES ✅ |
| Production provider changed | NO ✅ |
| Normal UI changed | NO ✅ |
| Frontend changed | NO ✅ |

**STOP. Do NOT modify service_charge_provider.py. Do NOT modify normal API behavior. Do NOT modify UI. Do NOT promote candidates. Do NOT calculate vacancy. Do NOT calculate management. Do NOT calculate maintenance. Do NOT calculate Net Rental Income. Do NOT calculate Net Rental Yield. Do NOT start Full Property ROI.**
