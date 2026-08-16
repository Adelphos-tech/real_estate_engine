# APIL Investment Demo — Data Audit Report

**Date:** August 4, 2026 (Updated 2:30 PM)  
**Audited by:** Cascade (AI Assistant)  
**Data file:** `src/data/dxb_projects.json`  

> **UPDATE:** The data has been re-exported with a full sync script that directly matches all 4,283 admin API property listings to DLD transaction + rent data. See "Updated Data Quality" section below.

---

## Summary

The demo data is a mix of **real synced DLD data** and **simulated/estimated values**. The project-level and community-level data comes from real DLD transactions and rent records fuzzy-matched via the production sync pipeline. However, the individual property listings shown on Report, PropertyAnalysis, and Compare pages are **synthetically generated** using random variance from project medians.

---

## What IS Real (from DLD + Admin API Sync)

| Data Point | Source | Count |
|---|---|---|
| Project names & areas | Admin API (`admin.apilproperties.com`) | 345 projects across 55 areas |
| Sales transaction price/sqft | DLD transactions CSV (fuzzy-matched) | 2,708 sales records |
| Capital appreciation % | DLD transaction matching | 308 of 345 projects (89%) |
| Rental yield % | DLD rent data (fuzzy-matched) | 60 of 345 projects (17%) |
| Service charges | `dxb_project_stats.csv` (dxbinteract.com scrape) | 27 of 345 projects (8%) |
| Median rent | DLD rent data | 41 rent records total |
| Investment scores | `local_sync_calc_UBUNTU.py` scoring algorithm | All 4,283 properties scored |

### Data Pipeline (Real)
1. **DLD Transactions** — `dxb_transactions.csv` (6,874 rows) appended to `transactions-2025-real.csv` on server (total: 16,385 rows)
2. **DLD Rents** — `dxb_rents.csv` (2,235 rows) appended to `rents.csv` on server (total: 32,051 rows)
3. **Sync Script** — `local_sync_calc_UBUNTU.py` fetched 4,283 properties from admin API, fuzzy-matched to DLD data, uploaded to Qdrant
4. **Export** — Qdrant points exported via scroll API, converted to `dxb_projects.json` format
5. **CSV Merge** — `dxb_project_stats.csv` merged for service charges (99 projects matched)

---

## What is NOT Real / Problematic

### 1. Property Listings are SIMULATED

**File:** `src/scoring/engine.ts`, lines 383–465  
**Function:** `generateSampleProperties()`

```typescript
const variance = 0.85 + Math.random() * 0.3; // ±15-30% from median
const askingPrice = Math.round(unit.medianPrice * variance);
```

The `ScoredProperty[]` objects shown on Report, PropertyAnalysis, and Compare pages are **not real listings**. They are synthetically generated from project medians with random ±15-30% variance. The real admin API has 4,283 actual property listings with real asking prices, images, and details — but those are not used in the demo.

### 2. 1,942 Sales Records Have `price: 0`

| Sales Records | Count |
|---|---|
| With real absolute price (from `sold_price_by_year`) | 766 |
| With `price: 0` (only `price_sqft` available from `price_trend`) | 1,942 |
| **Total** | **2,708** |

The Qdrant `price_trend` field only stores price per square foot, not absolute price. This means the scoring engine's `medianPrice` calculation is based on only 766 real prices, with the rest contributing zero.

### 3. Missing Data by Field

| Field | Missing | % Missing |
|---|---|---|
| `avg_price` | 32/345 | 9% |
| `avg_price_sqft` | 16/345 | 4% |
| `price_change_pct` | 37/345 | 10% |
| `avg_rent` | 285/345 | **82%** |
| `rental_yield_pct` | 285/345 | **82%** |
| `service_charge` | 318/345 | **92%** |
| `sales_volume` | 16/345 | 4% |

### 4. Estimated Rent is Guessed

**File:** `src/scoring/engine.ts`, line 410

```typescript
const estimatedRent = unit.medianRent || Math.round(askingPrice * 0.06);
```

When no rent data exists (82% of projects), the engine assumes a flat 6% rental yield to estimate rent. This is a rough heuristic, not real data.

### 5. Rent Data is Very Sparse

- DLD rent file has 32,051 rows on server
- But fuzzy matching only matched **41 rent records** across 345 projects
- Most projects have no rent data at all

---

## Data Flow Diagram

```
DLD Transactions CSV (16,385 rows)     DLD Rents CSV (32,051 rows)
         │                                      │
         └──────────────┬───────────────────────┘
                        ▼
         local_sync_calc_UBUNTU.py
         (fuzzy match by area/project name)
                        │
                        ▼
              Qdrant (4,284 points)
         (investment_score, roi, etc.)
                        │
                        ▼
         export_qdrant.py → dxb_projects.json
                        │
                        ▼
         merge_stats.py (add service_charge)
                        │
                        ▼
         dxb_projects.json (345 projects)
                        │
                        ▼
         engine.ts processData()
                        │
                        ▼
         generateSampleProperties() ← SIMULATED HERE
                        │
                        ▼
         ScoredProperty[] (fake asking prices)
```

---

## Server Details

| Item | Value |
|---|---|
| Server | `87.200.15.174` (user: `shivang`) |
| API Path | `/home/amlak/Voicexa/live_apis/investment_api/` |
| Data Path | `/home/amlak/Voicexa/live_apis/investment_api/data/` |
| Transactions File | `data/transactions/transactions-2025-real.csv` (16,385 rows) |
| Rents File | `data/rents/rents.csv` (32,051 rows) |
| Sync Script | `local_sync_calc_UBUNTU.py` |
| Qdrant Collection | `Dubai_real_estate_calculation_data_` (4,284 points) |
| API Endpoint | `localhost:8052/api/search` |
| API Routes | `/health`, `/api/filters`, `/api/search` |
| Last Sync Run | August 4, 2026 |

---

## Files Created/Modified

| File | Action |
|---|---|
| `src/data/dxb_projects.json` | Replaced with synced data (345 projects) |
| `src/data/dxb_projects_scraped_backup.json` | Backup of old scraped data (551 projects) |
| `src/data/dxb_projects_synced.json` | Raw Qdrant export (before CSV merge) |
| `scripts/export_qdrant.py` | Qdrant scroll export script |
| `scripts/export_api_data.py` | API pagination export script (unused, too slow) |
| `scripts/merge_stats.py` | CSV-to-JSON merge script for service charges |

---

## To Make It Fully Real

1. **Replace simulated properties with real admin API listings**
   - Fetch 4,283 properties from admin API with real asking prices, images, sizes
   - Replace `generateSampleProperties()` with real property data
   - Map each property to its matched project's DLD transaction data

2. **Fix the `price: 0` issue**
   - Calculate absolute price as `price_sqft × area_sqft` when only price/sqft is available
   - This would recover 1,942 records that currently contribute zero to median price

3. **Improve rent data coverage**
   - The DLD rent file has 32,051 rows but fuzzy matching only hit 41 records
   - Improve fuzzy matching threshold or add more area/project name normalization
   - Alternatively, use the `dxb_project_stats.csv` rent data (which has rent for more projects)

4. **Get more service charges**
   - Only 28 of 1,314 projects have service charges
   - Source from dxbinteract.com scrape or manual data entry

---

## Updated Data Quality (Full Sync — 2:30 PM)

Re-ran with `export_full_sync.py` which directly matches admin API properties to raw DLD CSVs (bypassing the conservative sync script fuzzy matching).

### Dramatic Improvement

| Metric | Old Scraped | Previous Sync | Full Sync (Current) |
|---|---|---|---|
| **Projects** | 551 | 345 | **1,314** |
| **Areas** | 8 | 55 | **154** |
| **Sales records** | 6,874 | 2,708 | **52,158** |
| **Rent records** | 2,235 | 41 | **7,223** |
| **Real prices (price > 0)** | 6,874 (100%) | 766 (28%) | **52,158 (100%)** |
| **With rental yield** | 309 (56%) | 60 (17%) | **854 (64%)** |
| **With service charge** | 251 (46%) | 27 (8%) | **28 (2%)** |
| **Properties matched to DLD** | N/A | 4,283 | **3,939/4,283 (92%)** |
| **Properties with rent match** | N/A | 41 | **2,756/4,283 (64%)** |

### What's Still Not Real

1. ~~**Property listings on demo pages**~~ — **FIXED**: `generateSampleProperties()` now uses real admin API listings with real asking prices, real sizes, and real property IDs. No more `Math.random()`.
2. **Service charges** — Only 28/1,314 projects have real service charges (from CSV merge).
3. **36% of projects** still have no rent data (DLD rent file has no matching project name).
4. **Estimated rent fallback** — When a project has no DLD rent match, rent is estimated as `askingPrice × 0.06` (6% assumed yield). This affects ~36% of properties.

---

## Scoring Algorithm — Full Documentation

**File:** `src/scoring/engine.ts` (499 lines)  
**Entry point:** `processData(rawProjects: ProjectData[])` → `{ communities, projects, properties }`

### Scoring Hierarchy

```
Community Score (area-level)
  └── Project Score (project-level)
        └── Unit Score (bedroom-type-level)
              └── Property Score (individual listing — SIMULATED)
```

Each level aggregates data from the level below.

---

### 1. Helper Functions

| Function | What it does |
|---|---|
| `median(arr)` | Standard median: sorts array, takes middle (or avg of two middle) |
| `clamp(val, min, max)` | Constrains value to range [min, max] |
| `normalizeBedType(beds)` | Maps "Studio", "1 B/R", "2 B/R" etc. from raw strings |
| `parseDate(dateStr)` | Parses ISO dates (`2026-01-01`) or space-separated dates |
| `monthsBetween(d1, d2)` | Calculates month difference between two dates |
| `scoreToLabel(score)` | ≥90 → "Excellent Investment", ≥80 → "Strong Opportunity", ≥70 → "Fair Investment", <70 → "Review Carefully" |
| `riskFromScore(score)` | ≥80 → "Low", ≥65 → "Medium", <65 → "High" |

---

### 2. Growth Calculation (`calculateGrowth`)

**Lines 164–184**

```
Growth = ((Recent Median Price/SqFt - Older Median Price/SqFt) / Older Median Price/SqFt) × 100
```

- Splits sales records into "recent" (within last N months) and "older" (before cutoff)
- Calculates median price/sqft for each group
- Returns percentage change
- Returns 0 if either group is empty or older median is 0
- Used for 3-month, 6-month, and 12-month growth

---

### 3. Unit-Level Scoring (`calculateUnitScores`)

**Lines 188–248**

Groups sales and rent records by bedroom type (Studio, 1 B/R, 2 B/R, etc.), then for each unit type:

**Calculated values:**
- `medianPrice` = median of all sale prices > 0
- `medianPriceSqft` = median of all price/sqft values > 0
- `medianRent` = median of all annual rents > 0
- `avgAreaSqft` = median of all area_sqft values > 0
- `rentalYield` = `(medianRent / medianPrice) × 100` (if both > 0, else 0)
- `transactionCount` = total number of sales records
- `demandScore` = `clamp(transactionCount × 8, 0, 100)` — caps at 100 (12+ transactions = max)

**Unit Score Formula (weighted):**
```
unitScore = yieldScore × 0.35 + demandScore × 0.25 + stabilityScore × 0.20 + liquidityScore × 0.20
```

| Component | Calculation | Weight | Max |
|---|---|---|---|
| `yieldScore` | `clamp(rentalYield × 6, 0, 100)` — 6% yield = 36, 10% = 60, 16.7% = 100 | 35% | 100 |
| `demandScore` | `clamp(transactionCount × 8, 0, 100)` | 25% | 100 |
| `stabilityScore` | `70 if medianPriceSqft > 0 else 40` — has real price data = more stable | 20% | 70 |
| `liquidityScore` | `clamp(transactionCount × 7, 0, 100)` | 20% | 100 |

**Example:** A 1 B/R unit with 10 transactions, 8% yield, and real price/sqft data:
- yieldScore = 8 × 6 = 48
- demandScore = 10 × 8 = 80
- stabilityScore = 70
- liquidityScore = 10 × 7 = 70
- **unitScore** = 48×0.35 + 80×0.25 + 70×0.20 + 70×0.20 = 16.8 + 20 + 14 + 14 = **65**

---

### 4. Project-Level Scoring (`calculateProjectScore`)

**Lines 252–303**

**Calculated values:**
- `medianPrice` = median of all sale prices in project
- `medianPriceSqft` = median of all price/sqft values
- `transactionVolume` = total sales records
- `rentVolume` = total rent records
- `rentalYield` = `project.rental_yield_pct` (from JSON) OR max unit-level yield
- `growth3m/6m/12m` = from `calculateGrowth()` on project's sales history
- `demandScore` = `clamp(transactionVolume × 7, 0, 100)`
- `liquidityScore` = `clamp(transactionVolume × 6 + rentVolume × 4, 0, 100)`
- `yieldScore` = `clamp(rentalYield × 6, 0, 100)`
- `growthScore` = `clamp(50 + growth12m × 2, 0, 100)` — baseline 50, +2 per 1% growth
- `status` = "Off-Plan" if any sale has `area_sqft === null` or date includes "Offplan", else "Ready"

**Project Score Formula (weighted):**
```
projectScore = yieldScore × 0.25 + growthScore × 0.25 + demandScore × 0.20 + liquidityScore × 0.15 + priceStability × 0.15
```

| Component | Calculation | Weight | Max |
|---|---|---|---|
| `yieldScore` | `clamp(rentalYield × 6, 0, 100)` | 25% | 100 |
| `growthScore` | `clamp(50 + growth12m × 2, 0, 100)` | 25% | 100 |
| `demandScore` | `clamp(transactionVolume × 7, 0, 100)` | 20% | 100 |
| `liquidityScore` | `clamp(txnVolume × 6 + rentVolume × 4, 0, 100)` | 15% | 100 |
| `priceStability` | `65 if medianPriceSqft > 0 else 30` | 15% | 65 |

**Example:** A project with 50 sales, 10 rents, 7% yield, 15% 12-month growth:
- yieldScore = 7 × 6 = 42
- growthScore = 50 + 15×2 = 80
- demandScore = 50 × 7 = 350 → clamped to 100
- liquidityScore = 50×6 + 10×4 = 340 → clamped to 100
- priceStability = 65
- **projectScore** = 42×0.25 + 80×0.25 + 100×0.20 + 100×0.15 + 65×0.15 = 10.5 + 20 + 20 + 15 + 9.75 = **75**

**Risk level:** ≥80 → "Low", ≥65 → "Medium", <65 → "High"

---

### 5. Community-Level Scoring (`calculateCommunityScore`)

**Lines 307–379**

Aggregates all projects in an area, then:

**Calculated values:**
- `medianPriceSqft` = median of ALL sales price/sqft across all projects in area
- `medianRent` = median of ALL rents across all projects
- `salesVolume` = total sales records across all projects
- `rentVolume` = total rent records
- `avgYield` = average of all project-level rental yields
- `growth3m/6m/12m` = from `calculateGrowth()` on ALL sales in area
- `growthScore` = `clamp(50 + growth12m × 2, 0, 100)`
- `yieldScore` = `clamp(avgYield × 6, 0, 100)`
- `liquidityScore` = `clamp(salesVolume × 0.8 + rentVolume × 0.5, 0, 100)`
- `transactionScore` = `clamp(salesVolume × 0.7, 0, 100)`
- `avgProjectScore` = average of all project scores in area

**Community Investment Score Formula (weighted):**
```
investmentScore = growthScore × 0.25 + yieldScore × 0.25 + liquidityScore × 0.20 + transactionScore × 0.15 + avgProjectScore × 0.15
```

| Component | Calculation | Weight | Max |
|---|---|---|---|
| `growthScore` | `clamp(50 + growth12m × 2, 0, 100)` | 25% | 100 |
| `yieldScore` | `clamp(avgYield × 6, 0, 100)` | 25% | 100 |
| `liquidityScore` | `clamp(salesVolume × 0.8 + rentVolume × 0.5, 0, 100)` | 20% | 100 |
| `transactionScore` | `clamp(salesVolume × 0.7, 0, 100)` | 15% | 100 |
| `avgProjectScore` | mean of all project scores | 15% | 100 |

**Risk level:** ≥80 → "Low", ≥65 → "Medium", <65 → "High"

---

### 6. Property-Level Scoring (`generateSampleProperties`) — REAL LISTINGS

**Lines 395–485**

Uses real property listings from the admin API (stored in `project.listings`).

**Process:**
1. For each project, get up to 6 real listings from `project.listings[]`
2. For each listing, use the real `listing.price` as `askingPrice` and `listing.size_sqft` as `areaSqft`
3. Match listing bedroom type to unit score via `unitMap`
4. `comparablePrice` = unit median price (from DLD transactions) or project median
5. `priceDifference` = `((askingPrice - comparablePrice) / comparablePrice) × 100`

**Market Position Classification:**
| Price Difference | Label |
|---|---|
| < -5% | Value Opportunity |
| -5% to +5% | Fair Market Value |
| +5% to +15% | Premium Pricing |
| > +15% | High Premium |

**Estimated Rent:** `unit.medianRent` (real) OR `askingPrice × 0.06` (assumed 6% yield if no rent data)  
**Estimated Yield:** `(estimatedRent / askingPrice) × 100`

**Property Score Formula (weighted):**
```
propertyScore = unitScore × 0.40 + priceScore × 0.30 + yieldScore × 0.20 + projectScore × 0.10
```

| Component | Calculation | Weight | Max |
|---|---|---|---|
| `unitScore` | From unit-level scoring (above) | 40% | 100 |
| `priceScore` | `clamp(100 - abs(priceDifference) × 3, 0, 100)` — closer to market = better | 30% | 100 |
| `yieldScore` | `clamp(estimatedYield × 6, 0, 100)` | 20% | 100 |
| `projectScore` | From project-level scoring (above) | 10% | 100 |

**Risk Factors (auto-generated):**
- `priceDifference > 10` → "Premium pricing above comparable transactions"
- `transactionCount < 5` → "Limited transaction history"
- `status === 'Off-Plan'` → "Off-plan project — delivery risk"
- `estimatedYield < 5` → "Below-average rental yield"
- If none: "No significant risk factors identified"

**Investment Reasons (auto-generated):**
- `priceDifference < -5` → "Asking price is below comparable sold prices — potential value opportunity"
- `estimatedYield > 7` → "Estimated rental yield is above Dubai market average"
- `transactionCount > 8` → "Strong transaction volume indicates good resale liquidity"
- `priceChangePct > 10` → "Strong price growth of X% in recent transactions"
- `marketPosition === 'Fair Market Value'` → "Asking price is aligned with verified transactions"
- If none: "Property meets baseline investment criteria"

---

### 7. Main Processing (`processData`)

**Lines 475–496**

```
1. Group all projects by area → areaGroups
2. For each area: calculateCommunityScore(area, projects) → communities[]
3. Sort communities by investmentScore (descending)
4. For each project: calculateProjectScore(project) → projects[]
5. Sort projects by projectScore (descending)
6. generateSampleProperties(projects) → properties[] (SIMULATED)
7. Sort properties by propertyScore (descending)
8. Return { communities, projects, properties }
```

---

### 8. Data Source → Algorithm Mapping

| JSON Field | Used In | Purpose |
|---|---|---|
| `sales_history[].price` | Unit, Project, Community | Median price calculation |
| `sales_history[].price_sqft` | Unit, Project, Community, Growth | Median price/sqft, growth calculation |
| `sales_history[].beds` | Unit | Grouping by bedroom type |
| `sales_history[].area_sqft` | Unit | Average area, off-plan detection |
| `sales_history[].date` | Growth, Project status | 3/6/12-month growth, off-plan detection |
| `rent_history[].annual_rent` | Unit, Project, Community | Median rent, yield calculation |
| `rent_history[].beds` | Unit | Grouping by bedroom type |
| `avg_price` | (Not directly used — calculated from sales_history) | — |
| `avg_price_sqft` | (Not directly used — calculated from sales_history) | — |
| `price_change_pct` | Project | Fallback if growth12m calculation returns 0 |
| `rental_yield_pct` | Project | Primary yield source, fallback to unit-level max |
| `avg_rent` | (Not directly used — calculated from rent_history) | — |
| `sales_volume` | Community | totalSupply calculation |
| `service_charge` | (Not used in scoring engine) | Displayed on PropertyAnalysis page |

---

### 9. Key Observations

1. **Yield multiplier is 6** — `yieldScore = clamp(yield × 6, 0, 100)`. This means:
   - 0% yield → 0 score
   - 6% yield → 36 score
   - 10% yield → 60 score
   - 16.7% yield → 100 score (maxed out)

2. **Growth baseline is 50** — `growthScore = clamp(50 + growth12m × 2, 0, 100)`. This means:
   - 0% growth → 50 score (neutral)
   - 10% growth → 70 score
   - 25% growth → 100 score (maxed out)
   - -25% growth → 0 score (mined out)

3. **Demand multiplier varies by level:**
   - Unit: `txnCount × 8` (12+ transactions = max)
   - Project: `txnCount × 7` (14+ transactions = max)
   - Community: `salesVolume × 0.7` (143+ transactions = max)

4. **Property scores now use REAL listings** — 4,283 real admin API property listings with real asking prices, real sizes, and real property IDs. No more `Math.random()` simulation. Each property is scored against DLD transaction medians for its project + bedroom type.
