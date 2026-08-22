# NET RENTAL INCOME V1 — INPUT DATA AUDIT

**Date**: 2026-08-20
**Verdict**: **NET_RENTAL_INPUT_DATA_AUDIT_V1_COMPLETE**
**Phase**: Data audit only — no calculations, no UI changes, no methodology changes

---

## 1. SUMMARY

| Metric | Value |
|--------|-------|
| READY_TOTAL | 315 |
| SERVICE_CHARGE_VERIFIED_COUNT | 6 |
| SERVICE_CHARGE_MISSING_COUNT | 309 |
| VACANCY_VERIFIED_COUNT | 0 |
| MANAGEMENT_VERIFIED_COUNT | 0 |
| MAINTENANCE_VERIFIED_COUNT | 0 |
| GROSS_ONLY_ELIGIBLE | 294 |
| SERVICE_CHARGE_ADJUSTED_ELIGIBLE | 6 |
| VACANCY_ADJUSTED_ELIGIBLE | 0 |
| FULL_NET_ELIGIBLE | 0 |
| SAME_UNIT_LINKAGE_RELIABLE | NO |

**Bottom line**: Only 6 of 315 Ready properties (1.9%) have verified service charge matches. Vacancy, management, and maintenance data are entirely missing. Full Net Rental Income cannot be calculated for any property at this time.

---

## 2. ISOLATION GUARANTEES

### Existing Runtime Untouched

| Counter | Value | Status |
|---------|-------|--------|
| COST_ENGINE_CHANGED_RENT_ESTIMATE | 0 | ✅ |
| COST_ENGINE_CHANGED_RENT_TIER | 0 | ✅ |
| COST_ENGINE_CHANGED_GROSS_YIELD | 0 | ✅ |
| COST_WORK_CHANGED_MARKET_CONTEXT | 0 | ✅ |
| COST_WORK_CHANGED_PRODUCTION_SIGNAL | 0 | ✅ |
| COST_WORK_CHANGED_APIL_ADVANTAGE | 0 | ✅ |
| COST_WORK_CHANGED_CONVENTIONAL_POSITION | 0 | ✅ |
| COST_WORK_CHANGED_FIT_SCORE | 0 | ✅ |
| NORMAL_PROPERTY_API_PERFORMANCE_CHANGED | 0 | ✅ |
| RENTAL_ENDPOINT_PERFORMANCE_CHANGED | 0 | ✅ |
| NORMAL_REQUEST_IMPORTS_COST_ENGINE | 0 | ✅ |
| NET_RENTAL_INCOME_CALCULATED_WITH_MISSING_COSTS | 0 | ✅ |
| UNVERIFIED_SERVICE_CHARGE_USED | 0 | ✅ |
| UNVERIFIED_VACANCY_USED | 0 | ✅ |
| DEFAULT_MANAGEMENT_ASSUMPTION_USED | 0 | ✅ |
| DEFAULT_MAINTENANCE_ASSUMPTION_USED | 0 | ✅ |

**All 16 safety counters at 0.**

### Post-Audit Regression (6 Ready properties)

| Property | Rent | Yield | Market Context | Production Signal | Fit Score | Status |
|----------|------|-------|---------------|-------------------|-----------|--------|
| 6056 | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| 6277 | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| 8057 | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| 3201 | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| 7061 | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |
| 8201 | ✅ | ✅ | ✅ | ✅ | ✅ | PASS |

**Zero mismatches. Existing runtime completely unchanged.**

---

## 3. NEW MODULE STRUCTURE

```
investor_api/rental_costs/
    __init__.py          — Package docstring, no runtime imports
    cost_data_store.py   — Read-only service charge CSV loader (lru_cache, not imported by normal requests)
```

**Import graph**: `main_v2.py` does NOT import `rental_costs`. The cost package is called only from `run_cost_audit.py` (research script). Normal API requests never load cost data.

---

## 4. SERVICE CHARGE DATA AUDIT (§10, §11)

### Source

| Item | Value |
|------|-------|
| Path | `/Users/apple/Desktop/Ai 3d view/dld_service_charges.csv` |
| Schema | project_name, community, area_name, property_group_name, property_group_id, management_company, budget_year, usage, usage_id, total_gf_aed_sqft, total_rf_aed_sqft, grand_total_aed_sqft, budget_start, budget_end, charge_categories, additional_charges_total, properties_count, latitude, longitude |
| Row count | 4,956 |
| Date/year coverage | 2012–2026 |
| Property/project identifiers | project_name, area_name, property_group_name, property_group_id |
| Unique project_name | 284 |
| Unique property_group_id | 684 |
| Data quality | Official DLD/Mollak service charge data |
| Official/verified | YES (DLD official) |

### Residential Filter

| Metric | Count |
|--------|-------|
| Residential rows | 2,621 |
| Residential with valid rate (>0) | 2,606 |
| Unique residential projects (latest year) | 266 |

### Matching to 315 Ready Properties

| Match Type | Count |
|------------|-------|
| Exact match (project name) | 6 |
| Fuzzy match (≥0.85 similarity) | 22 |
| No match | 287 |

**Only exact matches are counted as verified.** Fuzzy matches are NOT used (per §9: do not invent missing data).

### Verified Service Charge Matches (6 properties)

| Property ID | MASTER Project | Matched SC Project | Rate (AED/sqft) | Year | Annual SC (AED) |
|-------------|---------------|-------------------|-----------------|------|-----------------|
| 4744 | Ahad Residences | Ahad Residences | 20.26 | 2026 | 46,760 |
| 6435 | Pantheon Elysee | PANTHEON ELYSEE | 14.60 | 2026 | 11,140 |
| 7266 | Ahad Residences | Ahad Residences | 20.26 | 2026 | 18,112 |
| 1074 | Ahad Residences | Ahad Residences | 20.26 | 2026 | 9,178 |
| 6217 | Golf Links | GOLF LINKS | 18.36 | 2026 | 79,113 |
| *(+1 more)* | | | | | |

### Charge Basis

- **Rate unit**: AED per sqft per year
- **Calculation**: `annual_service_charge_aed = rate_aed_sqft × unit_size_sqft`
- **Calculation is fully verified** when:
  - Service charge rate is from official DLD/Mollak source
  - Unit size is from MASTER_FINAL.xlsx (verified)
  - Both are non-null and positive

### Why Only 6 Matched

The DLD service charges dataset has 266 unique residential project names. The MASTER_FINAL.xlsx has 315 Ready properties across many projects. The exact-name match rate is low because:
1. Project name formatting differs (e.g., "Imperial Avenue" vs "IMPERIAL AVENUE")
2. Many MASTER projects are not in the DLD service charges dataset
3. Some projects have service charges under different names (developer name vs OA name)

Fuzzy matching (22 additional matches at ≥0.85) could increase coverage but is NOT used for verified calculations per §9.

---

## 5. VACANCY COVERAGE AUDIT (§12)

### Source

| Item | Value |
|------|-------|
| Path | `/Users/apple/Desktop/Ai 3d view/dxb_rents_all.csv` |
| Row count | 573,001 |
| Key columns | PROPERTY_ID, PARCEL_ID, LAND_PROPERTY_ID, CONTRACT_NUMBER, VERSION_NUMBER, START_DATE, END_DATE |

### Stable Unit Identifier Check

| Field | Non-null | Unique Values | Sample | Reliable? |
|-------|----------|---------------|--------|-----------|
| PROPERTY_ID | 573,001 (100%) | 1 | [0, 0, 0, ...] | NO — all zeros |
| PARCEL_ID | 2,193 (0.4%) | 1 | [0] | NO — nearly all null |
| LAND_PROPERTY_ID | 573,001 (100%) | 1 | [0, 0, 0, ...] | NO — all zeros |
| CONTRACT_NUMBER | 0 (0%) | 0 | [] | NO — completely null |

### Verdict

**SAME_UNIT_LINKAGE_RELIABLE = NO**

All stable unit identifiers (PROPERTY_ID, PARCEL_ID, LAND_PROPERTY_ID, CONTRACT_NUMBER) are either all zeros or completely null. It is impossible to link the same physical unit across multiple lease contracts.

Without same-unit linkage, the gap-between-leases method for vacancy estimation cannot be applied. There is no way to determine when a unit was vacant between tenants.

**VACANCY_VERIFIED_COUNT = 0**

No vacancy approximation from area averages is used (per §12: do not approximate vacancy from area averages).

---

## 6. MANAGEMENT COVERAGE AUDIT (§13)

### Source

The `charge_categories` field in `dld_service_charges.csv` contains a breakdown like:
```
Services=3.5; Maintenance=3.3; Management Services=1.33; Insurance=0.32
```

266 projects have a "Management Services" component in their charge categories.

### Key Finding

This Management Services component is **already included** in `grand_total_aed_sqft`. It is a sub-component of the service charge, NOT a separate management fee paid by the landlord to a property management company.

For Net Rental Income purposes, "management cost" refers to the cost of managing the rental (tenant placement, rent collection, property oversight) — which is separate from the OA/Building management service charge.

**No separate verified management fee data source exists.**

**MANAGEMENT_VERIFIED_COUNT = 0**

Management status: **MISSING** (no verified source, no user input)

---

## 7. MAINTENANCE COVERAGE AUDIT (§14)

### Source

Same `charge_categories` field. 266 projects have a "Maintenance" component.

### Key Finding

Similar to management, this Maintenance component is a sub-component of the service charge (building-level maintenance by the Owners Association), NOT the landlord's individual maintenance costs for their specific unit.

For Net Rental Income, "maintenance cost" refers to the landlord's recurring maintenance expenses (AC servicing, plumbing, painting, etc.) — which is separate from the OA maintenance budget.

**No separate verified maintenance cost data source exists.**

**MAINTENANCE_VERIFIED_COUNT = 0**

Maintenance status: **MISSING** (no verified source, no user input)

---

## 8. CALCULATION ELIGIBILITY ESTIMATE (§15)

Across 315 Ready properties:

| Level | Eligible | Description |
|-------|----------|-------------|
| GROSS_ONLY | 294 | Has rent estimate, no verified service charge |
| SERVICE_CHARGE_ADJUSTED | 6 | Has rent estimate + verified service charge |
| VACANCY_ADJUSTED | 0 | Has rent + service charge + verified vacancy |
| FULL_NET | 0 | Has rent + service charge + vacancy + management + maintenance |

### Eligibility Flow

```
315 Ready properties
    ↓
300 have rent estimates (15 are NONE tier)
    ↓
6 have verified service charges (294 do not)
    ↓
0 have verified vacancy (unit linkage impossible)
    ↓
0 have verified management fees
    ↓
0 have verified maintenance costs
    ↓
FULL_NET_ELIGIBLE = 0
```

### What This Means

- **LEVEL 1 (Gross Rental Yield)**: Already implemented and frozen as `GROSS_RENTAL_YIELD_V1`. Available for 300 properties.
- **LEVEL 2 (Service Charge Adjusted)**: Possible for only 6 properties (1.9% of Ready).
- **LEVEL 3 (Vacancy Adjusted)**: Not possible for any property.
- **LEVEL 4 (Full Net)**: Not possible for any property.

---

## 9. PROGRESSIVE METRIC DESIGN (§8)

| Level | Formula | Eligible | Status |
|-------|---------|----------|--------|
| LEVEL 1 | `gross_rental_yield_pct = annual_rent / price × 100` | 300 | ✅ FROZEN (V1) |
| LEVEL 2 | `income_after_service_charges = annual_rent - annual_service_charge` | 6 | NOT IMPLEMENTED |
| LEVEL 3 | `adjusted_rental_income = annual_rent - service_charge - vacancy_loss` | 0 | NOT POSSIBLE |
| LEVEL 4 | `net_rental_income = annual_rent - service_charge - vacancy - management - maintenance` | 0 | NOT POSSIBLE |

No calculations were performed for Levels 2–4. This is data audit only.

---

## 10. DATA SOURCES SEARCHED

| Source | Path | Found? | Relevant? |
|--------|------|--------|-----------|
| DLD Service Charges | `dld_service_charges.csv` | ✅ | Service charges only |
| DLD Rental Data | `dxb_rents_all.csv` | ✅ | Vacancy linkage: NO (all IDs are zero) |
| MASTER_FINAL | `MASTER_FINAL.xlsx` | ✅ | No cost columns |
| MASTER_CLEANED | `MASTER_CLEANED.xlsx` | ✅ | No cost columns |
| STEP_5 data | `STEP_5_RANKED_OPPORTUNITIES.jsonl` | ✅ | No cost columns |
| Developer grading | `developer_grading_*.csv` | ✅ | Not relevant |
| Project stats | `dxb_project_stats.csv` | ✅ | Not relevant |
| Service charge scripts | `match_service_charges.py`, `fetch_service_charges.py`, `update_service_charges*.py` | ✅ | Matching logic reference |
| RERA/Mollak | — | ❌ | Not found as separate source |
| Vacancy data | — | ❌ | Not found |
| Management fee data | — | ❌ | Not found |
| Maintenance cost data | — | ❌ | Not found |

---

## 11. FILES CREATED

| File | Description |
|------|-------------|
| `investor_api/rental_costs/__init__.py` | Package init (no runtime imports) |
| `investor_api/rental_costs/cost_data_store.py` | Read-only service charge loader |
| `run_cost_audit.py` | Audit script (research only) |
| `run_cost_baseline.py` | Baseline capture script |
| `rental_cost_outputs/baseline_before.json` | Baseline values for 6 properties |
| `rental_cost_outputs/service_charge_matches.csv` | 6 verified service charge matches |
| `rental_cost_outputs/net_rental_input_coverage_v1.csv` | Full 315-property coverage table |
| `rental_cost_outputs/audit_verdict.json` | Verdict data |
| `rental_cost_outputs/NET_RENTAL_INPUT_DATA_AUDIT_V1.md` | This report |

---

## 12. EXISTING FILES NOT MODIFIED

| File | Status |
|------|--------|
| `investor_api/main_v2.py` | NOT MODIFIED (only StaticFiles mount from previous task) |
| `investor_api/rental/rental_context_service.py` | NOT MODIFIED |
| `investor_api/rental/rental_benchmark_engine.py` | NOT MODIFIED |
| `investor_api/dld_benchmark_engine.py` | NOT MODIFIED |
| `investor_api/fallback/market_context_service.py` | NOT MODIFIED |
| `investor_api/fallback/level2_context.py` | NOT MODIFIED |
| `investor_api/fallback/dld_fallback_v4.py` | NOT MODIFIED |
| `src/components/RentalIncomeCard.tsx` | NOT MODIFIED |
| `src/pages/PropertyDetail.tsx` | NOT MODIFIED |
| `src/data/api.ts` | NOT MODIFIED |

---

## 13. KNOWN LIMITATIONS

1. **Service charge matching is name-based only**: No property_group_id linkage to MASTER property_id. Fuzzy matching could increase coverage but is not used for verified calculations.

2. **Vacancy estimation is impossible** with current data: All unit-level identifiers in the rental CSV are zero/null. A new data source with actual unit IDs would be required.

3. **Management and maintenance are conflated with OA service charges**: The DLD service charge breakdown includes "Management Services" and "Maintenance" components, but these are building-level OA costs, not landlord-level costs. They cannot be used as standalone management/maintenance fees.

4. **No user-input mechanism exists**: The spec mentions USER_INPUT as a possible status for management/maintenance, but no UI or API for user-entered costs has been built.

5. **Only 6 properties (1.9%) can reach LEVEL 2**: Even if service charge adjustment were implemented, the coverage is too low for a meaningful feature.

---

## 14. RECOMMENDATIONS (FOR FUTURE APPROVAL)

1. **Improve service charge matching**: Investigate fuzzy matching with manual verification, or use property_group_id + area + developer for better linkage.
2. **Acquire vacancy data**: Find or purchase a data source with actual unit-level lease histories (Ejari IDs, unit numbers).
3. **User-input costs**: Build a UI for investors to enter their own management/maintenance costs.
4. **Do NOT implement Net Rental Income automatically**: Coverage is too low (6/315 = 1.9%) for a production feature.

---

## 15. VERDICT

### **NET_RENTAL_INPUT_DATA_AUDIT_V1_COMPLETE**

All safety counters at 0. No existing runtime modified. No calculations performed. No UI changed.

**STOP. Waiting for explicit approval before any further work.**
