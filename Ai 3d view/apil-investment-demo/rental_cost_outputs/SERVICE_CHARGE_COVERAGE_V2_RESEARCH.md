# SERVICE CHARGE COVERAGE V2 — OFFICIAL PROJECT RESOLUTION RESEARCH

**Date**: 2026-08-21
**Verdict**: **SERVICE_CHARGE_COVERAGE_V2_RESEARCH_COMPLETE**
**Status**: RESEARCH ONLY — No production changes made

---

## 1. GOAL

Increase verified official DLD/RERA Mollak service-charge coverage across the 315 Ready properties. This is **research / match resolution only**. No candidates have been promoted to runtime.

---

## 2. DATASET VERIFICATION

| Dataset | Rows | Projects |
|---------|------|----------|
| Mollak total | 4,956 | 284 |
| Mollak Residential | 2,621 | 266 |
| Mollak Villa | 8 | 2 |
| Mollak latest (res+villa, per project+community+usage) | 268 | — |
| MASTER Ready properties | 315 | 125 unique sub_projects |

---

## 3. COVERAGE SUMMARY

| Metric | Value |
|--------|-------|
| READY_TOTAL | 315 |
| CURRENT_PRODUCTION_ELIGIBLE | 6 |
| NEW_VERIFIED_PROJECT_IDENTITIES | 0 |
| NEW_SERVICE_CHARGE_CALCULABLE | 0 |
| NEW_HELD_COMPONENT | 0 |
| NEW_HELD_AREA_BASIS | 0 |
| NEW_HELD_USAGE | 0 |
| NEW_HELD_YEAR | 0 |
| AMBIGUOUS_COUNT | 83 |
| REJECTED_IDENTITY_COUNT | 0 |
| NO_MATCH_COUNT | 224 |
| **TOTAL_PRODUCTION_ELIGIBLE_AFTER_V2** | **6** (unchanged) |

**Accuracy > coverage.** No new auto-verified matches were found. All candidates with phase-family questions or developer-name-only token overlap were correctly sent to the manual review queue.

---

## 4. KEY FALSE POSITIVES PREVENTED

### 4a. "The Pad by Omniyat" → "THE OPUS BY OMNIYAT" (REJECTED)

- **Similarity**: 0.865 (high)
- **Token overlap**: 1 (`omniyat` — developer name only)
- **Non-dev overlap**: 0
- **Reason**: `ONLY_DEVELOPER_TOKEN_OVERLAP: {'omniyat'}`
- **Classification**: AMBIGUOUS → manual review
- **Lesson**: Developer name in project name inflates similarity. Different buildings by same developer must not be auto-verified.

### 4b. "Pantheon Elysee II/III" → "PANTHEON ELYSEE" (HELD — phase family)

- **Similarity**: 0.882–0.909 (high)
- **Token overlap**: 2 (`pantheon`, `elysee`)
- **Non-dev overlap**: 1 (`elysee`)
- **Reason**: `PHASE_FAMILY: MASTER has phase {'ii'}/{'iii'} not in Mollak; cannot assume shared budget`
- **Classification**: AMBIGUOUS → manual review
- **Mollak evidence**: Only ONE "PANTHEON ELYSEE" entry exists. Phases II and III may have separate budgets not in the dataset, or may share the same budget. Cannot auto-verify without official evidence.
- **Frozen 6435** ("Pantheon Elysee" = phase I) remains correctly verified — it has an exact name match.

### 4c. "Canal Residence West" → "Canal Residence West 2" (HELD — multi-phase)

- **Similarity**: 0.952 (very high)
- **Token overlap**: 2 (`canal`, `residence`)
- **Mollak evidence**: TWO separate entries exist with **different budgets**:
  - "CANAL RESIDENCE WEST (PHASE 1)" — 2026 GT = 13.92 AED/sqft
  - "Canal Residence West 2" — 2026 GT = 16.08 AED/sqft
- **Reason**: `AMBIGUOUS: 6 candidates` (both phases are candidates)
- **Classification**: AMBIGUOUS → manual review
- **Lesson**: When multiple Mollak projects share the same base name with different phases, MASTER properties without explicit phase numbers cannot be auto-assigned to either phase.

### 4d. "Golf Links" (Emaar South) → "GOLF LINKS" (Dubai Sports City) (PERMANENTLY REJECTED)

- **Status**: FROZEN as REJECTED_IDENTITY from V1
- **Reason**: Cross-community match (Emaar South ≠ Dubai Sports City)
- **CROSS_COMMUNITY_MATCH_PROMOTED = 0** ✅

---

## 5. HARBOUR VIEWS 409 — COMPONENT MISMATCH RESEARCH

**HARBOUR_VIEWS_COMPONENT_MISMATCH_RESOLVED = PARTIAL**

### Findings

| Year | GF | RF | GF+RF | GT | Diff | Additional Charges |
|------|-----|-----|-------|-----|------|-------------------|
| 2026 | 15.61 | 1.28 | 16.89 | 16.82 | 0.07 | — |
| 2025 | 15.41 | 1.23 | 16.64 | 16.43 | 0.21 | 4.44 |
| 2024 | 15.34 | 1.16 | 16.50 | 16.40 | 0.10 | 4.35 |
| 2023 | 14.25 | 1.22 | 15.47 | 15.37 | 0.10 | 4.21 |
| 2022 | 12.90 | 1.13 | 14.03 | 13.97 | 0.06 | 4.07 |
| 2021 | 12.76 | 1.47 | 14.23 | 14.23 | 0.00 | 6.17 |

### Analysis

- **5 of 6 years** have a component mismatch (GF+RF ≠ GT)
- **Only 2021** has matching components (GF+RF = GT = 14.23)
- The mismatch is **consistent and small** (0.06–0.21 AED/sqft)
- The `charge_categories` field shows 7 categories that sum to the GF value
- The `additional_charges_total` field exists for some years but is separate from GF+RF
- The grand_total may come from a separate official total that includes/excludes items differently from the component extraction

### Conclusion

The mismatch is not a data error — it appears to be a **semantic difference** between how components are extracted vs how the grand total is officially reported. The component rows may have hidden decimal precision, or the grand total may include/exclude certain categories differently.

**Decision**: Keep 409 as HELD_COMPONENT_MISMATCH. Do NOT choose 16.82 or 16.89 arbitrarily. The 2021 year with matching components is too old (5 years stale) to use as the current rate.

---

## 6. MANUAL REVIEW QUEUE

| Classification | Count |
|----------------|-------|
| HIGH_CONFIDENCE_REVIEW | 25 |
| MEDIUM_CONFIDENCE_REVIEW | 58 |
| REJECT (low confidence) | 0 |
| **Total** | **83** |

### Top HIGH_CONFIDENCE_REVIEW Candidates

| Property ID | MASTER Project | MASTER Area | Mollak Candidate | Mollak Community | Sim | Tokens | Dev | Qdrant | Reason |
|-------------|---------------|-------------|-----------------|-----------------|-----|--------|-----|--------|--------|
| 884, 4702, 4750, 5513 | Canal Residence West | Dubai Sports City | Canal Residence West 2 | Dubai Sports City | 0.952 | 2 | ✅ | ✅ | AMBIGUOUS: 6 candidates (Phase 1 vs Phase 2) |
| 7881 | Dubai Creek Residence Tower 2 North | Dubai Creek Harbour | THE DUBAI CREEK RESIDENCES | Dubai Creek Harbour | 0.689 | 2 | ✅ | ✅ | PHASE_FAMILY: phase {'2'} not in Mollak |
| 8201, 1208, 5582, 3160 | Marquise Square | Business Bay | MARQUISE SQUARE TOWER | Business Bay | 0.833 | 2 | ❌ | ✅ | AMBIGUOUS (no failure reason — needs manual check) |
| 655, 7669 | Pantheon Elysee III | JVC | PANTHEON ELYSEE | JVC | 0.882 | 2 | ❌ | ✅ | PHASE_FAMILY: phase {'iii'} not in Mollak |
| 3599, 5431 | Pantheon Elysee II | JVC | PANTHEON ELYSEE | JVC | 0.909 | 2 | ❌ | ✅ | PHASE_FAMILY: phase {'ii'} not in Mollak |
| 432, 1913, 6594 | Creek Beach Orchid | Dubai Creek Harbour | CREEK HORIZON | Dubai Creek Harbour | 0.645 | 1 | ✅ | ✅ | AMBIGUOUS (different project names) |
| 735, 3231, 4263 | Harbour Gate | Dubai Creek Harbour | HARBOUR VIEWS | Dubai Creek Harbour | 0.720 | 1 | ✅ | ✅ | AMBIGUOUS (different project names) |
| 5402, 7622 | The Pad by Omniyat | Business Bay | THE OPUS BY OMNIYAT | Business Bay | 0.865 | 1 | ❌ | ✅ | ONLY_DEVELOPER_TOKEN_OVERLAP |
| 5528, 5579, 7449, 1298 | Creek Rise Tower 1 | Dubai Creek Harbour | CREEKSIDE 18 | Dubai Creek Harbour | 0.600 | 0 | ✅ | ✅ | PHASE_FAMILY: phase {'1'} not in Mollak |

### Manual Review Notes

1. **Canal Residence West** (4 properties): Mollak has separate Phase 1 and Phase 2 budgets. Need to determine which phase the MASTER properties belong to.
2. **Dubai Creek Residence Tower 2 North** (1 property): Likely matches "THE DUBAI CREEK RESIDENCES" but tower number and "North" designation need confirmation.
3. **Marquise Square** (4 properties): "Marquise Square" vs "MARQUISE SQUARE TOWER" — likely same project, but "TOWER" suffix and lack of developer match requires manual confirmation.
4. **Pantheon Elysee II/III** (4 properties): Need to confirm whether phases II and III share the same Mollak budget as phase I.
5. **Creek Beach Orchid** (3 properties): "Creek Beach Orchid" vs "CREEK HORIZON" — different names, same community. Need official confirmation.
6. **Harbour Gate** (3 properties): "Harbour Gate" vs "HARBOUR VIEWS" — different buildings in same community. Need official confirmation.
7. **The Pad by Omniyat** (2 properties): Different building from "THE OPUS BY OMNIYAT". Should be REJECTED in manual review.
8. **Creek Rise Tower 1** (4 properties): "Creek Rise Tower 1" vs "CREEKSIDE 18" — different names, need confirmation.

---

## 7. MATCH METHODOLOGY

### 7a. Candidate Generation

1. **Normalized exact match**: `normalize_name(MASTER) == normalize_name(Mollak)`
2. **Community-restricted fuzzy**: Same community + similarity ≥ 0.6
3. **Token overlap**: ≥ 2 meaningful overlapping tokens + similarity ≥ 0.5

### 7b. Verification Gates (all must pass)

1. **Location parity**: MASTER area must be compatible with Mollak community
2. **Non-developer token overlap**: At least 1 overlapping token must NOT be a developer name
3. **Phase check**: No unresolved phase mismatch (MASTER phase not in Mollak, or vice versa)
4. **Multi-candidate check**: If multiple candidates share the same base name with different phases, auto-reject
5. **Component integrity**: |GF + RF - GT| ≤ 0.01 AED/sqft
6. **Usage**: Must be Residential or Villa
7. **Year**: ≤ 2026 (current valuation year)
8. **Area basis**: Qdrant category must be Apartment (or independently proven)

### 7c. Normalization (frozen from V1)

lowercase → trim → collapse whitespace → hyphen→space → slash→space → period removal → punctuation removal → final whitespace cleanup

### 7d. Phase Indicators

`{'1', '2', '3', '4', 'i', 'ii', 'iii', 'iv'}`

---

## 8. YEAR VALIDITY

Latest officially approved Mollak budget year where budget year ≤ 2026. All verified candidates use the latest available year per project+community+usage.

---

## 9. PROPERTY TYPE / AREA BASIS

Current V1 production rule: **Apartment only**. Properties with Qdrant category ≠ Apartment are held as `HELD_AREA_BASIS` unless a different chargeable-area basis is independently proven.

---

## 10. REGRESSION CHECKS — ALL ZERO

### Engine Regression

| Counter | Value |
|---------|-------|
| V2_CHANGED_ANNUAL_RENT | 0 ✅ |
| V2_CHANGED_RENT_RANGE | 0 ✅ |
| V2_CHANGED_RENT_TIER | 0 ✅ |
| V2_CHANGED_GROSS_YIELD | 0 ✅ |
| V2_CHANGED_MARKET_CONTEXT | 0 ✅ |
| V2_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| V2_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| V2_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| V2_CHANGED_FIT_SCORE | 0 ✅ |

### Service Charge Regression (Frozen 6)

| Counter | Value |
|---------|-------|
| V2_CHANGED_FROZEN_SC_RATE | 0 ✅ |
| V2_CHANGED_FROZEN_ANNUAL_SC | 0 ✅ |
| V2_CHANGED_FROZEN_ADJUSTED_INCOME | 0 ✅ |
| V2_CHANGED_FROZEN_ADJUSTED_YIELD | 0 ✅ |

### Safety Counters

| Counter | Value |
|---------|-------|
| V2_RESEARCH_CHANGED_PRODUCTION_PROVIDER | 0 ✅ |
| V2_RESEARCH_CHANGED_UI | 0 ✅ |
| CROSS_COMMUNITY_MATCH_PROMOTED | 0 ✅ |
| WRONG_MOLLAK_USAGE_PROMOTED | 0 ✅ |

### Held/Rejected Status

| Property | Status | OK |
|----------|--------|-----|
| 409 (Harbour Views 1) | HELD_COMPONENT_MISMATCH | ✅ |
| 6217 (Golf Links) | REJECTED_IDENTITY | ✅ |

---

## 11. OUTPUT FILES

| File | Description |
|------|-------------|
| `service_charge_v2_full_315_candidates.csv` | Full 315 Ready properties coverage table |
| `service_charge_v2_new_verified_candidates.csv` | New auto-verified candidates (empty — 0 found) |
| `service_charge_v2_manual_review_queue.csv` | 83 manual review candidates with confidence ranking |
| `service_charge_v2_rejected_candidates.csv` | Rejected candidates (empty — 0 rejected) |
| `service_charge_v2_research_verdict.json` | Machine-readable verdict + all counters |

---

## 12. RECOMMENDATIONS FOR MANUAL REVIEW

The following candidates are the most likely to be verifiable with manual research:

### Priority 1: Phase Family Confirmation

| Properties | MASTER Project | Mollak Project | Action Needed |
|-----------|---------------|----------------|---------------|
| 3599, 5431 | Pantheon Elysee II | PANTHEON ELYSEE | Confirm whether II shares the same OA budget as I |
| 655, 7669 | Pantheon Elysee III | PANTHEON ELYSEE | Confirm whether III shares the same OA budget as I |
| 884, 4702, 4750, 5513 | Canal Residence West | Canal Residence West 2 / Phase 1 | Determine which phase the MASTER properties belong to |

### Priority 2: Name Variant Confirmation

| Properties | MASTER Project | Mollak Project | Action Needed |
|-----------|---------------|----------------|---------------|
| 8201, 1208, 5582, 3160 | Marquise Square | MARQUISE SQUARE TOWER | Confirm same project (TOWER suffix) |
| 7881 | Dubai Creek Residence Tower 2 North | THE DUBAI CREEK RESIDENCES | Confirm tower 2 north is part of the development |

### Priority 3: Different Name, Same Community

| Properties | MASTER Project | Mollak Project | Action Needed |
|-----------|---------------|----------------|---------------|
| 432, 1913, 6594 | Creek Beach Orchid | CREEK HORIZON | Confirm these are the same project |
| 735, 3231, 4263 | Harbour Gate | HARBOUR VIEWS | Confirm these are the same project |

### Should Be Rejected

| Properties | MASTER Project | Mollak Project | Reason |
|-----------|---------------|----------------|--------|
| 5402, 7622 | The Pad by Omniyat | THE OPUS BY OMNIYAT | Different buildings, only developer name overlaps |

---

## 13. VERDICT

### **SERVICE_CHARGE_COVERAGE_V2_RESEARCH_COMPLETE**

| Check | Result |
|-------|--------|
| Current eligible | 6 |
| New verified identities | 0 |
| New calculable candidates | 0 |
| Held candidates | 0 |
| Manual review candidates | 83 (25 HIGH + 58 MEDIUM) |
| Rejected candidates | 0 |
| Total potential eligible after approval | 6 (unchanged) |
| All 17 regression/safety counters | 0 ✅ |
| Harbour Views 409 | PARTIAL (kept held) |
| Production provider changed | NO ✅ |
| UI changed | NO ✅ |

**STOP. Do NOT promote candidates to runtime. Do NOT modify normal UI. Do NOT calculate vacancy. Do NOT calculate Net Rental Income. Do NOT start Full Property ROI.**
