# APIL Investment Engine — Step 11 Production Readiness Report
**Audit Date:** 2026-08-16 18:25 UTC
**Version:** 2.0.0

## Executive Summary

| Metric | Value |
|---|---|
| Total Tests | 46 |
| Passed | 44 |
| Failed | 0 |
| Warnings | 2 |
| **Final Status** | **PASS** |
| **Launch Recommendation** | **READY_WITH_REVIEW** |

## Performance Measurements

| Endpoint | Time (s) | Status | Items |
|---|---|---|---|
| GET /opportunities | 0.011 | 200 | 20 |
| GET /properties/6749 | 0.003 | 200 | 1 |
| POST /compare | 0.003 | 200 | 3 |
| POST /investors | 0.005 | 200 | 1 |

## Personas Tested

**conservative**, **moderate_balanced**, **aggressive**, **short_term**, **luxury**, **low_budget**, **income_oriented**

## Detailed Results

### WARNING (2)

- **L_Questionnaire.tsx** — Frontend on `Questionnaire.tsx`
  - Description: Page may not reference objective/fit data
  - Observed: `missing refs`
  - Expected: `should reference api types`

- **L_Profile.tsx** — Frontend on `Profile.tsx`
  - Description: Page may not reference objective/fit data
  - Observed: `missing refs`
  - Expected: `should reference api types`

### PASS (44)

- **A1** — API Health on `GET /`
  - Description: Root endpoint returns correct version and stats
  - Observed: `PASSED`
  - Expected: `PASSED`

- **B_conservative** — Profile Creation on `POST /investors`
  - Description: Created conservative investor
  - Observed: `PASSED`
  - Expected: `PASSED`

- **B_moderate_balanced** — Profile Creation on `POST /investors`
  - Description: Created moderate_balanced investor
  - Observed: `PASSED`
  - Expected: `PASSED`

- **B_aggressive** — Profile Creation on `POST /investors`
  - Description: Created aggressive investor
  - Observed: `PASSED`
  - Expected: `PASSED`

- **B_short_term** — Profile Creation on `POST /investors`
  - Description: Created short_term investor
  - Observed: `PASSED`
  - Expected: `PASSED`

- **B_luxury** — Profile Creation on `POST /investors`
  - Description: Created luxury investor
  - Observed: `PASSED`
  - Expected: `PASSED`

- **B_low_budget** — Profile Creation on `POST /investors`
  - Description: Created low_budget investor
  - Observed: `PASSED`
  - Expected: `PASSED`

- **B_income_oriented** — Profile Creation on `POST /investors`
  - Description: Created income_oriented investor
  - Observed: `PASSED`
  - Expected: `PASSED`

- **C2** — Decision Safety on `GET /properties/6749`
  - Description: Objective decision identical across 7 personas: STRONG_OPPORTUNITY
  - Observed: `PASSED`
  - Expected: `PASSED`

- **C3** — Decision Safety on `GET /properties/6749`
  - Description: Confidence identical across personas
  - Observed: `PASSED`
  - Expected: `PASSED`

- **C4** — Decision Safety on `GET /properties/6749`
  - Description: Developer grade identical across personas
  - Observed: `PASSED`
  - Expected: `PASSED`

- **C5** — Decision Safety on `GET /properties/6749`
  - Description: Benchmarks identical across personas
  - Observed: `PASSED`
  - Expected: `PASSED`

- **C6** — Decision Safety on `GET /properties/6749`
  - Description: Fit scores vary appropriately: {'conservative': 70, 'moderate_balanced': 57, 'aggressive': 53, 'short_term': 57, 'luxury': 51, 'low_budget': 70, 'income_oriented': 57}
  - Observed: `PASSED`
  - Expected: `PASSED`

- **D3** — Evidence Display on `GET /properties/6749`
  - Description: All 2 benchmarks checked for advantage safety
  - Observed: `PASSED`
  - Expected: `PASSED`

- **E1** — Language Audit on `All frontend files`
  - Description: No forbidden wording detected
  - Observed: `PASSED`
  - Expected: `PASSED`

- **E_sep_api.ts** — Language Audit on `api.ts`
  - Description: Page shows both objective_signal and combined_explanation
  - Observed: `PASSED`
  - Expected: `PASSED`

- **E_sep_PropertyDetail.tsx** — Language Audit on `PropertyDetail.tsx`
  - Description: Page shows both objective_signal and combined_explanation
  - Observed: `PASSED`
  - Expected: `PASSED`

- **F1** — Unknown Data on `GET /properties/6749`
  - Description: Unsupported preferences correctly UNKNOWN: ['rental_yield', 'financing_compatibility']
  - Observed: `PASSED`
  - Expected: `PASSED`

- **G1** — API Contract on `GET /properties/NONEXISTENT`
  - Description: 404 for nonexistent property
  - Observed: `PASSED`
  - Expected: `PASSED`

- **G2** — API Contract on `GET /properties/6749?investor_id=bad`
  - Description: Invalid investor_id returns property with null fit
  - Observed: `PASSED`
  - Expected: `PASSED`

- **G3** — API Contract on `GET /opportunities`
  - Description: Empty result handled correctly
  - Observed: `PASSED`
  - Expected: `PASSED`

- **G4** — API Contract on `POST /compare`
  - Description: 1 property rejected with 400
  - Observed: `PASSED`
  - Expected: `PASSED`

- **G5** — API Contract on `POST /compare`
  - Description: 4 properties rejected with 400
  - Observed: `PASSED`
  - Expected: `PASSED`

- **G6** — API Contract on `POST /compare`
  - Description: Duplicate IDs deduplicated to 2 unique
  - Observed: `PASSED`
  - Expected: `PASSED`

- **G6b** — API Contract on `POST /compare`
  - Description: Comparing same property with itself returns 400
  - Observed: `PASSED`
  - Expected: `PASSED`

- **G7** — API Contract on `POST /investors`
  - Description: Invalid questionnaire value rejected
  - Observed: `PASSED`
  - Expected: `PASSED`

- **G8** — API Contract on `POST /investors`
  - Description: Missing required fields rejected
  - Observed: `PASSED`
  - Expected: `PASSED`

- **G9** — API Contract on `GET /opportunities`
  - Description: Pagination beyond range returns empty results
  - Observed: `PASSED`
  - Expected: `PASSED`

- **G10** — API Contract on `GET /properties/6749`
  - Description: No internal fields leaked
  - Observed: `PASSED`
  - Expected: `PASSED`

- **H1** — Security on `GET /properties/INVALID<>PATH`
  - Description: Error response clean
  - Observed: `PASSED`
  - Expected: `PASSED`

- **H2** — Security on `GET /investors/ca0f6bb8-fabd-4348-b832-3716ea717095`
  - Description: Random investor_id returns 404
  - Observed: `PASSED`
  - Expected: `PASSED`

- **H3** — Security on `GET /opportunities`
  - Description: No cross-investor data leakage
  - Observed: `PASSED`
  - Expected: `PASSED`

- **I1** — Performance on `GET /opportunities`
  - Description: Response time: 0.01s
  - Observed: `PASSED`
  - Expected: `PASSED`

- **I2** — Performance on `GET /properties/6749`
  - Description: Response time: 0.00s
  - Observed: `PASSED`
  - Expected: `PASSED`

- **I3** — Performance on `POST /compare`
  - Description: Response time: 0.00s
  - Observed: `PASSED`
  - Expected: `PASSED`

- **I4** — Performance on `POST /investors`
  - Description: Response time: 0.00s
  - Observed: `PASSED`
  - Expected: `PASSED`

- **J1** — Marketplace on `GET /opportunities`
  - Description: INSUFFICIENT_EVIDENCE excluded from default view
  - Observed: `PASSED`
  - Expected: `PASSED`

- **J2** — Marketplace on `GET /opportunities`
  - Description: Results sorted by decision tier descending
  - Observed: `PASSED`
  - Expected: `PASSED`

- **K1** — Session on `GET /investors/d69c180f-96b2-4eb3-b669-0ce1d961cb71`
  - Description: Consistent profile across repeated fetches
  - Observed: `PASSED`
  - Expected: `PASSED`

- **L_Landing.tsx** — Frontend on `Landing.tsx`
  - Description: Page exists and references locked data structures
  - Observed: `PASSED`
  - Expected: `PASSED`

- **L_Marketplace.tsx** — Frontend on `Marketplace.tsx`
  - Description: Page exists and references locked data structures
  - Observed: `PASSED`
  - Expected: `PASSED`

- **L_PropertyDetail.tsx** — Frontend on `PropertyDetail.tsx`
  - Description: Page exists and references locked data structures
  - Observed: `PASSED`
  - Expected: `PASSED`

- **L_Compare.tsx** — Frontend on `Compare.tsx`
  - Description: Page exists and references locked data structures
  - Observed: `PASSED`
  - Expected: `PASSED`

- **L_viewport** — Frontend on `index.html`
  - Description: Viewport meta tag present for responsive design
  - Observed: `PASSED`
  - Expected: `PASSED`


## Safety Verification

- Objective decisions verified identical across 7 personas for Property 6749: **STRONG_OPPORTUNITY**
- Fit scores varied appropriately: **4 unique values**
- INSUFFICIENT_EVIDENCE excluded from default marketplace: **PASS**
- No internal fields leaked in API responses: **PASS**

## Launch Recommendation

**READY_WITH_REVIEW**

The system passes all automated safety and API contract tests. A visual/manual review of responsive UX and browser-level edge cases is recommended before production deployment.