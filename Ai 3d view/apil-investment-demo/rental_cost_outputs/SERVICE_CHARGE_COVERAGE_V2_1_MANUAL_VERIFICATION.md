# SERVICE CHARGE COVERAGE V2.1 — MANUAL OFFICIAL VERIFICATION

**Date**: 2026-08-21
**Verdict**: **SERVICE_CHARGE_COVERAGE_V2_1_MANUAL_REVIEW_COMPLETE**
**Status**: RESEARCH ONLY — No production changes made

---

## 1. SUMMARY

| Metric | Value |
|--------|-------|
| PROPERTIES_MANUALLY_REVIEWED | 25 |
| NEW_PROJECT_IDENTITIES_VERIFIED | 9 |
| NEW_IDENTITIES_REJECTED | 16 |
| NEW_IDENTITIES_UNRESOLVED | 0 |
| NEW_CALCULABLE_CANDIDATES | 0 |
| NEW_HELD_CANDIDATES | 9 |
| CURRENT_PRODUCTION_ELIGIBLE | 6 |
| **POTENTIAL_PRODUCTION_ELIGIBLE_AFTER_APPROVAL** | **6** (unchanged) |

**No new calculable candidates found.** 9 project identities were VERIFIED but all fail component integrity (GF+RF ≠ GT). 16 candidates were REJECTED with official evidence.

---

## 2. VERDICT BY PROJECT FAMILY

### PRIORITY A — MARQUISE SQUARE

**MARQUISE_SQUARE_IDENTITY = VERIFIED**

| Property ID | Identity | SC Status | Rate (2026) | Component Diff |
|-------------|----------|-----------|-------------|----------------|
| 8201 | VERIFIED | HELD_COMPONENT_MISMATCH | 16.85 | 0.09 |
| 1208 | VERIFIED | HELD_COMPONENT_MISMATCH | 16.85 | 0.09 |
| 5582 | VERIFIED | HELD_COMPONENT_MISMATCH | 16.85 | 0.09 |
| 3160 | VERIFIED | HELD_COMPONENT_MISMATCH | 16.85 | 0.09 |

**Evidence basis:**
- Cushman & Wakefield Core lists "Marquise Square Tower" as the official name
- Bayut lists "Marquise Square" — same building, 29 floors, 384 units
- JRE confirms RERA escrow registration (1011221899533019)
- Developer: Seven Tides (MASTER = Qdrant = Mollak)
- "TOWER" is a descriptive suffix, not a phase indicator
- Component integrity FAILS: GF+RF=16.94 vs GT=16.85, diff=0.09 > 0.01 tolerance

---

### PRIORITY B — DUBAI CREEK RESIDENCE TOWER 2 NORTH

**DUBAI_CREEK_TOWER_2_NORTH_IDENTITY = VERIFIED**

| Property ID | Identity | SC Status | Rate (2026) | Component Diff |
|-------------|----------|-----------|-------------|----------------|
| 7881 | VERIFIED | HELD_COMPONENT_MISMATCH | 16.50 | 0.22 |

**Evidence basis:**
- ECM (Emaar Community Management) official page: "Dubai Creek Residences comprises six waterfront towers"
- Skyscraper Center: "Dubai Creek Residences North Tower 2" is one of the six towers
- Zeus Capital confirms Tower 2 North is part of Dubai Creek Residences complex
- Single Mollak entry "THE DUBAI CREEK RESIDENCES" covers all 6 towers (no separate per-tower entries)
- Developer: Emaar Properties (MASTER = Qdrant = Mollak mgmt = EMAAR COMMUNITY MANAGEMENT)
- Component integrity FAILS: GF+RF=16.72 vs GT=16.50, diff=0.22 > 0.01 tolerance

---

### PRIORITY C — PANTHEON ELYSEE PHASES

**PANTHEON_ELYSEE_II = SEPARATE_PROJECT**
**PANTHEON_ELYSEE_III = SEPARATE_PROJECT**

| Property ID | Identity | SC Status | Reason |
|-------------|----------|-----------|--------|
| 3599 | REJECTED | NOT_MATCHED | Phase II in District 12, Phase I in District 13 |
| 5431 | REJECTED | NOT_MATCHED | Phase II in District 12, Phase I in District 13 |
| 655 | REJECTED | NOT_MATCHED | Phase III in District 15, Phase I in District 13 |
| 7669 | REJECTED | NOT_MATCHED | Phase III in District 15, Phase I in District 13 |

**Evidence basis:**
- Official developer website (pantheon.ae): "Pantheon Elysée I" in District 13
- Property Finder: "Pantheon Elysee II" in District 12
- Property Finder: "Pantheon Elysee Phase 3" in District 15
- Only ONE "PANTHEON ELYSEE" entry in Mollak — likely covers Phase I only (District 13)
- No separate Mollak entries for Phase II or Phase III
- Official factsheet: "ANTICIPATED SERVICE CHARGE AED 15 per sq.ft." for Phase II, vs Mollak PANTHEON ELYSEE GT=14.6 — different rates suggest separate budgets
- Different districts = different buildings with separate OA registrations
- Frozen 6435 (Pantheon Elysee Phase I) remains correctly verified — exact name match

---

### PRIORITY D — CANAL RESIDENCE WEST

**Phase resolution: VERIFIED_PHASE_1** (all 4 properties)

| Property ID | Resolved Phase | Mollak Project | SC Status | Rate (2026) | Component Diff |
|-------------|---------------|----------------|-----------|-------------|----------------|
| 884 | Phase 1 | CANAL RESIDENCE WEST (PHASE 1) | HELD_COMPONENT_MISMATCH | 13.92 | 0.18 |
| 4702 | Phase 1 | CANAL RESIDENCE WEST (PHASE 1) | HELD_COMPONENT_MISMATCH | 13.92 | 0.18 |
| 4750 | Phase 1 | CANAL RESIDENCE WEST (PHASE 1) | HELD_COMPONENT_MISMATCH | 13.92 | 0.18 |
| 5513 | Phase 1 | CANAL RESIDENCE WEST (PHASE 1) | HELD_COMPONENT_MISMATCH | 13.92 | 0.18 |

**Evidence basis:**
- MASTER label "Canal Residence West" matches Mollak Phase 1 name
- Phase 2 is called "Canal Residence West 2" — different name
- No "Canal Residence West 2" properties exist in MASTER
- PropertyStellar (DLD data): Phase 1 (Mediterranean/European/Venetian) = 13.9 AED/sqft; Phase 2 (Arabic/Spanish) = 15.9-16.1 AED/sqft
- Diar Consult (lead consultant): Canal Residence West = 5 buildings, 987 apartments
- Phase 1 completed 2013/2015 (3 towers); Phase 2 completed 2020 (2 towers)
- All Phase 1 towers share the same rate (13.9) — specific tower identification not needed
- Component integrity FAILS: GF+RF=14.10 vs GT=13.92, diff=0.18 > 0.01 tolerance

---

### KNOWN FALSE POSITIVE — THE PAD

**project_match_status = REJECTED_IDENTITY_RESEARCH**

| Property ID | Identity | Reason |
|-------------|----------|--------|
| 5402 | REJECTED | Different buildings; only developer token overlaps |
| 7622 | REJECTED | Different buildings; only developer token overlaps |

**Evidence basis:**
- Qdrant: project_name = "The Pad by Omniyat", building_name = "The Pad by Omniyat"
- Mollak: "THE OPUS BY OMNIYAT" — different project name
- Only shared token: "omniyat" (developer name)
- Different buildings by same developer — developer match alone is NOT evidence
- This research rejection does NOT modify production runtime

---

### LOWER PRIORITY — CREEK BEACH ORCHID → CREEK HORIZON

**REJECTED**

| Property ID | Identity | Reason |
|-------------|----------|--------|
| 432 | REJECTED | Different projects on DCH master plan |
| 1913 | REJECTED | Different projects on DCH master plan |
| 6594 | REJECTED | Different projects on DCH master plan |

**Evidence basis:**
- Emaar DCH master plan shows ORCHID and CREEK HORIZON as separate projects in different locations
- Orchid is part of Creek Beach district; Creek Horizon is in the Island District
- Different project names, different buildings
- Same community/developer is NOT sufficient evidence

---

### LOWER PRIORITY — HARBOUR GATE → HARBOUR VIEWS

**REJECTED**

| Property ID | Identity | Reason |
|-------------|----------|--------|
| 735 | REJECTED | Different projects on DCH master plan |
| 3231 | REJECTED | Different projects on DCH master plan |
| 4263 | REJECTED | Different projects on DCH master plan |

**Evidence basis:**
- Emaar DCH master plan shows HARBOUR GATE and HARBOUR VIEWS as separate projects
- ECM page lists them separately
- Harbour Gate = two stepped towers; Harbour Views = 51-floor twin towers
- Different buildings with different names

---

### CREEK RISE TOWER 1 → CREEKSIDE 18

**REJECTED**

| Property ID | Identity | Reason |
|-------------|----------|--------|
| 5528 | REJECTED | Different projects on DCH master plan |
| 5579 | REJECTED | Different projects on DCH master plan |
| 7449 | REJECTED | Different projects on DCH master plan |
| 1298 | REJECTED | Different projects; also Townhouse (area basis issue) |

**Evidence basis:**
- Emaar DCH master plan shows CREEK RISE and CREEKSIDE 18 as separate projects
- Qdrant: project_name = "Creek Rise Tower 1" (not Creekside 18)
- Different project names, different buildings
- Property 1298 is a 4BR Townhouse (category=Townhouse in Qdrant) — would also fail area basis check

---

## 3. COMPONENT INTEGRITY ANALYSIS

A systematic analysis of all 266 Mollak residential projects reveals:

| Metric | Value |
|--------|-------|
| Total residential projects (latest year) | 266 |
| Component PASS (diff ≤ 0.01) | 132 (49.6%) |
| Component FAIL (diff > 0.01) | 134 (50.4%) |

**50% of Mollak residential projects have a component mismatch.** This is a systematic data issue in the Mollak dataset, not specific to our candidates. The frozen 6 all pass (diff = 0.0).

All 9 newly verified identities fail component integrity:
- Marquise Square Tower: diff = 0.09
- The Dubai Creek Residences: diff = 0.22
- Canal Residence West Phase 1: diff = 0.18

---

## 4. HARBOUR VIEWS 409

**Identity**: VERIFIED_ALIAS (unchanged)
**SC Status**: HELD_COMPONENT_MISMATCH (unchanged)

The component mismatch (GF+RF=16.89 vs GT=16.82, diff=0.07) is consistent with the systematic Mollak data issue. Not resolved — kept held.

---

## 5. GOLF LINKS 6217

**REJECTED_IDENTITY** (unchanged). MASTER Emaar South ≠ Mollak Dubai Sports City. Never recreate this candidate.

---

## 6. ALL 17 REGRESSION/SAFETY COUNTERS — ALL ZERO

| Counter | Value |
|---------|-------|
| V21_CHANGED_FROZEN_MATCH | 0 ✅ |
| V21_CHANGED_FROZEN_RATE | 0 ✅ |
| V21_CHANGED_FROZEN_ANNUAL_SC | 0 ✅ |
| V21_CHANGED_FROZEN_ADJUSTED_INCOME | 0 ✅ |
| V21_CHANGED_FROZEN_ADJUSTED_YIELD | 0 ✅ |
| V21_CHANGED_ANNUAL_RENT | 0 ✅ |
| V21_CHANGED_RENT_RANGE | 0 ✅ |
| V21_CHANGED_RENT_TIER | 0 ✅ |
| V21_CHANGED_GROSS_YIELD | 0 ✅ |
| V21_CHANGED_GROSS_YIELD_RANGE | 0 ✅ |
| V21_CHANGED_MARKET_CONTEXT | 0 ✅ |
| V21_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| V21_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| V21_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| V21_CHANGED_FIT_SCORE | 0 ✅ |
| V21_CHANGED_SERVICE_CHARGE_PROVIDER | 0 ✅ |
| V21_CHANGED_UI | 0 ✅ |

---

## 7. NEWLY VERIFIED IDENTITIES (DETAILED EVIDENCE)

### 1. Marquise Square (4 properties: 8201, 1208, 5582, 3160)

**Evidence basis:**
- Cushman & Wakefield Core official guide: "Marquise Square Tower, Business Bay, Dubai"
- Bayut building guide: "Marquise Square is a 29-storey residential building in Business Bay"
- JRE: RERA escrow #1011221899533019 confirms regulatory standing
- Developer: Seven Tides (all sources agree)
- "TOWER" is a descriptive suffix — same building
- **SC Status: HELD_COMPONENT_MISMATCH** (diff=0.09)

### 2. Dubai Creek Residence Tower 2 North (1 property: 7881)

**Evidence basis:**
- ECM official page: "Dubai Creek Residences comprises six waterfront towers"
- Skyscraper Center: "Dubai Creek Residences North Tower 2" — one of the six
- Single Mollak entry covers all 6 towers (no separate per-tower budgets)
- **SC Status: HELD_COMPONENT_MISMATCH** (diff=0.22)

### 3. Canal Residence West Phase 1 (4 properties: 884, 4702, 4750, 5513)

**Evidence basis:**
- MASTER label "Canal Residence West" = Phase 1 name (not Phase 2 = "Canal Residence West 2")
- No Phase 2 properties in MASTER
- PropertyStellar (DLD data): Phase 1 = 13.9 AED/sqft, Phase 2 = 15.9-16.1 AED/sqft
- All Phase 1 towers share same rate
- **SC Status: HELD_COMPONENT_MISMATCH** (diff=0.18)

---

## 8. OUTPUT FILES

| File | Description |
|------|-------------|
| `service_charge_v2_1_manual_verification.csv` | One row per investigated property (25 rows) |
| `service_charge_v2_1_verdict.json` | Machine-readable verdict + all counters |
| `SERVICE_CHARGE_COVERAGE_V2_1_MANUAL_VERIFICATION.md` | This report |

---

## 9. VERDICT

### **SERVICE_CHARGE_COVERAGE_V2_1_MANUAL_REVIEW_COMPLETE**

| Check | Result |
|-------|--------|
| Properties manually reviewed | 25 |
| New verified identities | 9 (all HELD_COMPONENT_MISMATCH) |
| New rejected identities | 16 |
| New calculable candidates | 0 |
| Total potential eligible after approval | 6 (unchanged) |
| All 17 regression/safety counters | 0 ✅ |
| Production provider changed | NO ✅ |
| UI changed | NO ✅ |
| 409 held | YES ✅ |
| 6217 rejected | YES ✅ |
| Frozen 6 unchanged | YES ✅ |

**STOP. Do NOT modify runtime provider. Do NOT modify normal UI. Do NOT calculate vacancy. Do NOT calculate Net Rental Income. Do NOT calculate Net Rental Yield. Do NOT start Full Property ROI.**
