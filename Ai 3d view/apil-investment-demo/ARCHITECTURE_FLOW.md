# APIL Investment Platform — Architecture & End-to-End Flow

## Overview

APIL (AI Property Investment Layer) is a full-stack platform that analyses Dubai real estate using verified DLD transaction data and live Qdrant property listings. The architecture follows a strict separation of concerns: **backend computes all scores**, **frontend is a pure presentation layer**.

The platform handles **two distinct property types** with separate scoring logic:

- **Ready Properties** — scored on rental income, price fairness, liquidity, and historical growth
- **Off-Plan Properties** — scored on fair market value, future appreciation, developer track record, and post-handover ROI (never compared to launch price)

### 7-Stage Processing Pipeline

Every property goes through 7 stages before reaching the user:

```
Stage 1: VALIDATION     → Reject impossible listings (price/sqft, comparables, rentals, developer)
Stage 2: MARKET VALUATION → Fair value from weighted medians (community + project + building + comparable)
Stage 3: SCORING        → Investment score from price/ROI/growth/liquidity/community/developer
Stage 4: CONFIDENCE     → Evidence-based confidence (sales × rental × developer × project × community)
Stage 5: RECOMMENDATION → Map score → action term (Buy / Watchlist / Avoid)
Stage 6: RULES ENGINE   → Hard overrides (insufficient data → max REVIEW, high premium → max CAUTION)
Stage 7: LLM ADVISOR    → Qwen2.5-VL explains, detects contradictions, advises (ADVISORY ONLY)
```

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              APIL PLATFORM                                    │
│                                                                              │
│  ┌──────┐ ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐ │
│  │ ETL  │▶│STAGE 1  │▶│STAGE 2   │▶│STAGE 3    │▶│STAGE 4   │▶│STAGE 5-6 │ │
│  │Import│ │Validate │ │Fair Value│ │Score It   │ │Confidence│ │Rules+Rec │ │
│  └──────┘ └─────────┘ └──────────┘ └───────────┘ └──────────┘ └──────────┘ │
│                                                              │            │
│                                              ┌───────────────┘            │
│                                              ▼                            │
│                                        STAGE 7: LLM Advisor               │
│                                        (Qwen2.5-VL-7B)                    │
│                                              │                            │
│                                              ▼                            │
│                                        FastAPI + React                    │
│                                        Port 8090                          │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Data Sources

| Source | Type | Data Provided |
|--------|------|---------------|
| DLD (Dubai Land Department) | CSV transactions + rentals | Historical sale prices, rent contracts, project metadata |
| DXBInteract.com | Web scrape | Developer sales volume, project counts, capital gain stats |
| Google Maps | Review data | Developer ratings, review counts |
| Qdrant Vector DB | HTTP API (port 6333) | Live property listings — developer asking prices, images, descriptions, payment plans, amenities, floor plans |

---

## 1. Backend Data Pipeline

### 1.1 ETL Layer (`/backend/etl/`)

Raw data is imported from multiple sources into JSON warehouse files.

| Script | Source | Output | Data Fields Produced |
|--------|--------|--------|---------------------|
| `import_dld.py` | DLD CSV transactions + rentals + project JSON | `dld_warehouse.json` | `price`, `rent`, `area`, `project`, `bedType`, `date`, `transaction_type` — ~50K transactions, ~20K rentals across 150+ communities |
| `import_dxb.py` | DXBInteract developer data | `dxb_warehouse.json` | `developer_name`, `sales_count`, `capital_gain`, `projects_delivered`, `projects_under_construction`, `total_units`, `delayed_projects` — ~33 developers |
| `import_google.py` | Google Maps review data | `google_warehouse.json` | `developer_name`, `google_rating`, `google_review_count` |

**Data flow:**
```
CSV/JSON raw files → ETL scripts → Warehouse JSONs → Engines
Qdrant (live)      → HTTP scroll  → In-memory points → Offplan Engine v2
```

### 1.2 Stage 1 — Validation Engine (`validation_engine_v2.py`)

Rejects impossible listings BEFORE scoring. Never score bad data.

**Input fields:** `asking_price`, `area_sqft`, `community_median_sqft`, `project_median`, `sales_count`, `rent_count`, `developer_data`

**Validation rules:**

| Rule | Threshold | Action |
|------|-----------|--------|
| Price below minimum | < AED 100,000 | Reject |
| Price/sqft outside range | < 200 or > 10,000 AED/sqft | Reject |
| Price deviation from market | > 70% above/below expected | Reject |
| Comparable sales | ≥ 10 = full, ≥ 5 = partial, > 0 = low, 0 = none | Score 100/50/20/0 |
| Rental contracts | ≥ 10 = full, ≥ 5 = partial, > 0 = low, 0 = none | Score 100/50/20/0 |
| Developer track record | ≥ 3 projects = established, ≥ 1 = limited, 0 = unknown | Score 100/50/0 |

**Output fields:** `validationStatus` (VALID/REJECTED), `validationReason`, `expectedPrice`, `deviation`, `evidenceLevels` (comparables/rental/developer with status+label+score)

### 1.3 Stage 2 — Market Valuation Engine (`market_valuation.py`)

Determines fair value BEFORE investment scoring.

**Input fields:** `area_sqft`, `community_median_sqft`, `project_median_sqft`, `building_median_sqft`, `recent_comparable_median`, `asking_price`

**Fair Value Formula:**
```
Fair Value = 40% Community Median + 30% Project Median + 20% Building Median + 10% Recent Comparable Median
(Weights redistributed if some sources unavailable)
```

**Price Classification:**

| Discount % | Classification | Description |
|-----------|---------------|-------------|
| < -15% | Strong Discount | Potential opportunity |
| -5% to -15% | Discount | Below market |
| ±5% | Fair Market Value | At market |
| 5% to 15% | Premium | Above market |
| > 15% | High Premium | Verify justification |

**Output fields:** `fairValueSqft`, `fairValueTotal`, `discountPct`, `classification`, `components` (community/project/building/comparable medians), `evidenceLevel` (full/partial/limited/none), `description`

**Price Score from Discount:**

| Discount % | Score |
|-----------|-------|
| ≤ -20% | 100 |
| -10% to -20% | 90 |
| -5% to -10% | 80 |
| ±5% | 70 |
| 5% to 10% | 50 |
| 10% to 20% | 20 |
| > 20% | 10 |

**Rental Score from Yield:**

| Net Yield % | Score |
|------------|-------|
| ≥ 12% | 100 |
| 10-12% | 90 |
| 8-10% | 75 |
| 6-8% | 60 |
| 4-6% | 40 |
| 2-4% | 20 |
| < 2% | 10 |

### 1.4 Stage 3 — Scoring Engines

#### Community Engine (`community_engine.py`)

**Input:** DLD warehouse (filtered by community)

**Output file:** `community_scores.json` (~154 communities)

**Output fields:**

| Field | Type | Description |
|------|------|-------------|
| `name`, `slug` | string | Community identifier |
| `communityScore` | int 0-100 | Overall area investment score |
| `scoreBreakdown` | object | `{ growth, yield, liquidity, transactions, demandLivabilitySupply }` with score+contribution+max |
| `priceIndex` | float | Price level index |
| `rentalIndex` | float | Rental level index |
| `demandIndex` | int 0-100 | Buyer demand score |
| `supplyIndex` | int 0-100 | Future supply pressure |
| `growthIndex` | int 0-100 | Growth potential |
| `livabilityIndex` | int 0-100 | Area livability |
| `transportIndex` | int 0-100 | Transport connectivity |
| `luxuryIndex` | int 0-100 | Luxury positioning |
| `subScores` | object | Array of {label, value} for 7 sub-scores |
| `medianPriceSqft` | float | Median price per sqft (AED) |
| `medianRent` | float | Median annual rent (AED) |
| `rentalYield` | float | Average rental yield % |
| `growth3m`, `growth6m`, `growth12m` | float | Price growth % (capped ±80%) |
| `salesVolume` | int | Number of recent sales transactions |
| `rentVolume` | int | Number of recent rental contracts |
| `totalProjects` | int | Number of projects in community |
| `totalSupply` | int | Total supply units |
| `riskLevel` | string | Low / Medium / High |
| `confidenceScore` | int 0-100 | Data confidence |

#### Developer Engine (`developer_engine.py`)

**Input:** DXB + Google + delivery data

**Output file:** `developer_scores.json` (~33 developers)

**Output fields:**

| Field | Type | Description |
|------|------|-------------|
| `name` | string | Developer name |
| `developerScore` | int 0-100 | Overall developer score |
| `scoreBreakdown` | object | `{ trackRecord, deliveryPerformance, capitalGain, rentalDemand, salesVolume, constructionQuality, marketReputation }` |
| `projectsDelivered` | int | Completed projects count |
| `projectsUnderConstruction` | int | Active projects |
| `totalProjects` | int | Total projects |
| `totalUnits` | int | Total units delivered |
| `delayedProjects` | int | Projects with delays |
| `deliveryDelayRisk` | string | Low / Medium / High |
| `deliveryDelayPercent` | float | % of projects delayed |
| `avgResalePremium` | float | Average resale premium % |
| `capitalGainAED`, `capitalGainStr` | float/string | Capital gain value |
| `buyerConfidence` | string | Good / Moderate / Low |
| `marketPosition` | string | Tier 1 / Tier 2 / Tier 3 |
| `constructionQuality` | int 0-10 | Build quality rating |
| `customerReviews` | int | Review count |
| `googleRating` | float | Google Maps rating |
| `googleReviewCount` | int | Google review count |
| `marketReputation` | int 0-10 | Market reputation score |
| `salesCount` | int | Total sales volume |
| `salesValue`, `salesValueStr` | float/string | Total sales value (AED) |
| `avgRentalYield` | float | Average rental yield % |
| `totalRentContracts` | int | Total rental contracts |
| `areasCovered` | array | Areas where developer has projects |
| `projectNames` | array | Project names |
| `aliases` | array | Name aliases for matching |
| `summary` | string | Text summary |

#### Project Engine (`project_engine.py`)

**Input:** DLD warehouse + developer scores

**Output file:** `project_scores.json` (~1,312 projects)

**Output fields:**

| Field | Type | Description |
|------|------|-------------|
| `name`, `slug`, `area` | string | Project identifier + location |
| `projectScore` | int 0-100 | Overall project score |
| `priceSqft` | float | Median price per sqft (AED) |
| `medianPrice` | float | Median total price (AED) |
| `priceChangePct` | float | Price change % (capped ±40%) |
| `rentalYield` | float | Average rental yield % |
| `transactionVolume` | int | Number of recent transactions |
| `rentVolume` | int | Number of recent rentals |
| `demandScore` | int 0-100 | Demand score |
| `liquidityScore` | int 0-100 | Liquidity score |
| `growthScore` | int 0-100 | Growth score |
| `yieldScore` | int 0-100 | Yield score |
| `growth3m`, `growth6m`, `growth12m` | float | Price growth % |
| `riskLevel` | string | Low / Medium / High |
| `status` | string | Ready / Under Construction |
| `developerName` | string | Developer name |
| `developerScore` | int 0-100 | Developer score |
| `unitTypes` | array | Unit types with per-type prices/yields |
| `confidenceScore` | int 0-100 | Data confidence |
| `scoreBreakdown` | object | Component scores |

#### Ready Property Engine (`ready_engine.py`)

**Input:** DLD listings + community + developer + project scores

**Output file:** `ready_property_scores.json` (~600+ ready properties)

**Output fields (complete):**

| Field | Type | Description |
|------|------|-------------|
| `id`, `title`, `category` | string | Property identifier |
| `project`, `projectSlug`, `area` | string | Location info |
| `bedType` | string | Studio / 1 B/R / 2 B/R / 3 B/R |
| `askingPrice` | float | Current asking price (AED) |
| `priceSqft` | float | Price per sqft (AED) |
| `areaSqft` | float | Unit area (sqft) |
| `comparablePrice` | float | Recent comparable sold price |
| `priceDifference` | float | % difference from comparables |
| `marketPosition` | string | Fair / Premium / Discount / High Premium |
| `estimatedRent` | float | Estimated annual rent (AED) |
| `estimatedYield` | float | Estimated gross yield % |
| `readyScore` | int 0-100 | Overall investment score |
| `recommendation` | string | STRONG BUY / BUY / HOLD / CAUTION / REVIEW / AVOID / INSUFFICIENT_DATA |
| `scoreLabel` | string | Human-readable score label |
| `priceScore` | int 0-100 | Price fairness score |
| `roi` | object | `{ grossROI, netROI, annualRent, serviceChargeAnnual, vacancyRate, managementFee, netAnnualIncome, hasRentData }` |
| `roiScore` | int 0-100 | Rental ROI score |
| `liquidity` | object | `{ liquidityScore, liquidityLabel, absorptionRate, avgDaysOnMarket }` |
| `communityScore` | int 0-100 | Community score |
| `developerScore` | int 0-100 | Developer score |
| `projectScore` | int 0-100 | Project score |
| `developerName` | string | Developer name |
| `growth3m`, `growth6m`, `growth12m` | float | Price growth % (0 = insufficient data) |
| `growthMetadata` | object | `{ 3m/6m/12m: { growth, recentSamples, olderSamples, totalSamples, confidence } }` |
| `rentRange` | object | `{ low, high, mid, confidence, sampleSize }` |
| `scoreBreakdown` | object | `{ price, roi, liquidity, community, developer, project }` — each 0-100 |
| `risk` | object | `{ overallRisk, riskLevel, riskFactors[], components: { futureSupplyRisk, developerRisk, areaSaturationRisk, rentalRisk, marketVolatilityRisk, constructionDelayRisk, pricePremiumRisk } }` |
| `reasons` | array | Top reasons for the score (strings) |
| `lostPoints` | array | Where points were lost (strings) |
| `confidenceScore` | int 0-100 | Evidence-based confidence |
| `demandScore` | int 0-100 | Demand score |
| `communityData` | object | Full community data snapshot |
| `projectData` | object | Full project data snapshot |
| `developerData` | object | Full developer data snapshot |
| `dataQuality` | object | `{ hasComparables, hasRentData, salesCount, rentCount, comparableCount, roiValidation }` |
| `dataCompleteness` | object | `{ community, project, developer, property, overall }` — each 0-100 |
| `confidenceBreakdown` | object | `{ sales, rental, developer, project, community }` — each 0-100 |
| `validationStatus` | string | VALID / REJECTED |
| `evidenceLevels` | object | `{ comparables: {status, label, score}, rental: {...}, developer: {...} }` |
| `marketValuation` | object | `{ fairValueSqft, fairValueTotal, discountPct, classification, components, evidenceLevel, description }` |
| `fairValue` | float | Fair market value total (AED) |
| `confidenceLevel` | string | High / Moderate / Low / Very Low / Insufficient |
| `propertyType` | string | "ready" |
| `rulesFlags` | array | Rules engine flags applied (e.g. RULE_2_HIGH_PREMIUM) |
| `computedAt` | string | ISO timestamp |

#### Off-Plan Engine v2 (`offplan_engine_v2.py`)

**Core principle: Never compare to launch price. Always compare current developer asking price vs current fair market value derived from DLD transactions.**

**Input:** Qdrant off-plan listings (3,610 fetched) + community_scores.json + developer_scores.json + project_scores.json + feature_store.json

**Output file:** `offplan_scores.json` (~3,441 scored properties)

**Output fields (complete):**

| Field | Type | Description |
|------|------|-------------|
| `id`, `title`, `slug` | string | Property identifier |
| `project`, `area`, `developer` | string | Location + developer info |
| `bedType`, `category` | string | Unit type (studio/1br/2br/3br) + property type |
| `sizeSqft` | float | Unit size (sqft) |
| `askingPrice` | float | Developer asking price (AED) |
| `priceSqft` | float | Price per sqft (AED) |
| `status` | string | Off-plan status |
| `offplanScore` | int 0-100 | Overall investment score |
| `recommendation` | string | STRONG BUY / BUY / NEGOTIATE / HOLD / AVOID |
| `scoreLabel` | string | Human-readable score label |
| `fairValue` | object | `{ fairValue, source, locationFactor }` |
| `priceOpportunity` | object | `{ priceDifferencePct, priceOpportunityScore, label }` |
| `futureAppreciation` | object | `{ growthRate, futureValue, potentialGainPct, completionYears }` |
| `postHandoverROI` | object | `{ netROI, estimatedRent, rentSource, serviceCharge, managementFee, vacancyCost }` |
| `developerData` | object | `{ developerScore, developerName, delayRisk, trackRecord, deliveryHistory, constructionQuality, ... }` |
| `communityData` | object | `{ communityScore, demandIndex, growth12m, ... }` |
| `liquidity` | object | `{ liquidityScore, liquidityLabel, absorptionRate }` |
| `risk` | object | `{ overallRisk, riskLevel, riskFactors[], components: {...} }` |
| `reasons` | array | Top reasons for the score |
| `listingData` | object | `{ images[], description, paymentPlans[], amenities[], highlights[], canonicalUrl }` |
| `confidenceScore` | int 0-100 | Evidence-based confidence |
| `confidenceBreakdown` | object | `{ sales, rental, developer, project, community }` |
| `confidenceLevel` | string | High / Moderate / Low / Very Low / Insufficient |
| `validationStatus` | string | VALID / REJECTED |
| `validationReason` | string | Reason if rejected |
| `marketValuation` | object | `{ fairValueSqft, fairValueTotal, discountPct, classification, components, evidenceLevel, description }` |
| `rulesFlags` | array | Rules engine flags |
| `evidenceLevels` | object | Evidence status per category |
| `priceScore` | int 0-100 | Price opportunity score |
| `roiScore` | int 0-100 | Post-handover ROI score |
| `projectScore` | int 0-100 | Project score |
| `readyScore` | int 0-100 | Ready equivalent score |
| `priceDifference` | float | % difference from fair value |
| `marketPosition` | string | Market position classification |
| `roi` | object | ROI breakdown (for frontend compat) |
| `estimatedRent` | float | Estimated rent |
| `estimatedYield` | float | Estimated yield % |
| `scoreBreakdown` | object | Component scores |
| `propertyType` | string | "offplan" |
| `computedAt` | string | ISO timestamp |

**Off-Plan Scoring Formula:**

```
Step 1: Fair Value = Community Median Price/sqft × Unit Size × Location Factor × Project Premium
        - Location Factor: 1.0 + (communityScore - 50) × 0.002
        - Project Premium: 1.0 + (projectScore - 50) × 0.003
        - Fallback chain: community median → project median → feature store unit-type median

Step 2: Price Difference % = (Developer Price − Fair Value) / Fair Value × 100

Step 3: Future Value = Developer Price × (1 + Growth Rate)^Completion Years
        - Growth rate from community growth12m (capped 0-25%), default 5%

Step 4: Post-Handover ROI = (Est. Rent - Service Charge - Mgmt Fee - Vacancy) / Purchase Price

Step 5: Developer Score = 30% Track Record + 25% Delivery History + 20% Construction Quality + 15% Capital Appreciation + 10% Market Reputation

Step 6: Final Investment Score = 25% Price Opportunity + 25% Future Appreciation + 20% Developer + 15% Community + 10% Liquidity + 5% ROI

Step 7: Recommendation Matrix:
        - Price Diff ≤ -5% + Score ≥ 80 → STRONG BUY
        - Price Diff ≤ 5% + Score ≥ 75 → BUY
        - Price Diff 5-10% + Score ≥ 65 → NEGOTIATE
        - Price Diff 10-15% → HOLD
        - Price Diff > 15% → AVOID
```

### 1.5 Stage 4 — Confidence Engine (`confidence_engine.py`)

Evidence-based confidence: NOT a score quality metric, but a **data evidence** metric.

**Input fields:** `sales_count`, `rent_count`, `developer_delivered`, `project_txn_volume`, `community_data`

**Scoring:**

| Component | Weight | Full (100) | Partial (50-80) | Low (20-40) | None (0) |
|-----------|--------|------------|-----------------|-------------|----------|
| Sales evidence | 25% | ≥ 50 sales | 20-49 sales | 5-19 sales | 0 sales |
| Rental evidence | 20% | ≥ 50 rentals | 20-49 rentals | 5-19 rentals | 0 rentals |
| Developer evidence | 20% | ≥ 10 delivered | 5-9 delivered | 1-4 delivered | 0 delivered |
| Project evidence | 15% | ≥ 50 txns | 20-49 txns | 5-19 txns | 0 txns |
| Community evidence | 20% | All 10 fields present | 7-9 fields | 4-6 fields | < 4 fields |

**Critical rule:** If sales=0 AND rental=0, confidence capped at 20.

**Output fields:** `score` (0-100), `level` (High ≥80 / Moderate ≥60 / Low ≥40 / Very Low ≥25 / Insufficient <25), `breakdown` ({ sales, rental, developer, project, community })

### 1.6 Stage 5 — Recommendation Mapping

Maps numeric score → actionable recommendation term:

| Score | Recommendation | Frontend Label |
|-------|---------------|----------------|
| ≥ 85 | STRONG BUY | Buy 🟢 |
| 75-84 | BUY | Buy 🟢 |
| 65-74 | HOLD | Buy if Negotiated 🟡 |
| 55-64 | CAUTION | Watchlist 🟠 |
| 40-54 | REVIEW | Needs Review ⚪ |
| < 40 | INSUFFICIENT_DATA | Insufficient Data 🔴 |
| Price > 15% above market | AVOID | Avoid 🔴 |

### 1.7 Stage 6 — Rules Engine (`rules_engine.py`)

Hard business rules that override recommendations. NON-NEGOTIABLE.

**Input:** Scored property + investor goal

| Rule | Condition | Override |
|------|-----------|----------|
| 1 | Comparable sales < 5 | Never BUY, max REVIEW |
| 2 | Price > 20% above market | Max CAUTION |
| 3 | No rental evidence + rental investor | Never BUY |
| 4 | Unknown developer + off-plan | Max REVIEW |
| 5 | Confidence < 40% | Max REVIEW |
| 6 | Confidence < 25% | INSUFFICIENT_DATA |
| 7 | Price/sqft outside 200-10,000 | Reject entirely |

**Output fields:** `rulesFlags` (array of flag strings like `RULE_2_HIGH_PREMIUM`), updated `recommendation`

### 1.8 Stage 7 — LLM Advisor (`llm_engine.py`)

The LLM (Qwen2.5-VL-7B-Instruct) is an **ADVISOR ONLY**. It NEVER calculates scores, estimates rent, or determines confidence. All calculations are deterministic.

**Input:** Scored property JSON (all fields from Stage 1-6) + investor profile

**LLM Advisory Functions:**

| Function | Input | Output |
|----------|-------|--------|
| `validate_listing` | Listing data | Advisory flags (not hard validation) |
| `explain_score` | Property + score breakdown | Plain-English explanation of why score is what it is |
| `detect_contradictions` | Property metrics | Flags contradicting metrics (e.g. high ROI + low rent data) |
| `investor_recommendation` | Property + investor profile | Buy/Wait/Avoid advice with reasoning |
| `compare_alternatives` | Top 3-5 properties | Side-by-side comparison with trade-offs |
| `negotiation_strategy` | Property + market data | Suggested offer price + negotiation leverage points |
| `exit_strategy` | Property + growth data | Recommended holding period + exit timing |
| `generate_advisory_report` | All property data | Full report: summary, thesis, strengths, risks, negotiation, exit, data reliability |

**Qwen Server:**
- Model: Qwen2.5-VL-7B-Instruct at `/home/shivang/models/Qwen2.5-VL-7B-Instruct`
- Server: `/tmp/qwen_advisor_server.py` (FastAPI on port 8001)
- OpenAI-compatible `/v1/chat/completions` endpoint
- Falls back gracefully if LLM unavailable (deterministic fallback)

### 1.9 Recommendation Engine (`recommendation_engine.py`)

**Input:** Ready + offplan scores + investor profile

**Output:** Dynamic API response with filtered + sorted recommendations

**Filtering pipeline (strict order):**

| Step | Filter | Type | Field Used |
|------|--------|------|------------|
| 1 | Property type | HARD | `category` matched against `PROPERTY_TYPE_MAP` |
| 2 | Bedrooms | HARD | `normalize_bedtype()` maps studio/1br/2br/3br/4br+ across formats |
| 3 | Budget | HARD | `askingPrice` within parsed budget range |
| 4 | Location | SOFT | `area` or `project` contains location string |
| 5 | Risk | SOFT | Exclude High risk + AVOID for low-risk investors |
| 6 | Goal sort | — | capital_growth → `futureAppreciation.potentialGainPct` or `growth12m`; rental_income → `postHandoverROI.netROI` or `roi.netROI` |

**Progressive relaxation:** If no results after all hard filters → relax budget (±20%) → relax bedrooms → relax property type. Each step logged and reported to user. NEVER silently violate a hard constraint.

**Engine execution order:**
```
ETL → validation_engine_v2 → feature_engine →
  community_engine → developer_engine → project_engine → ready_engine
  (Stage 1: Validation → Stage 2: Market Valuation → Stage 3: Scoring → Stage 4: Confidence)
                                                                    ↓
  Qdrant fetch (3,610 off-plan listings) → offplan_engine_v2 (3,441 scored)
  (Stage 1-4 same pipeline)
                                                                    ↓
  Stage 5: Recommendation mapping → Stage 6: Rules engine → Stage 7: LLM advisor
                                                                    ↓
                                                        recommendation_engine (on-demand via API)
```

### Key Data Quality Fixes Applied

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| ROI 20%+ | Monthly rent stored as annual | Cap rent at 12% of asking price |
| Price/sqft = 207 | Plot/land area mixed with unit area | Filter sales with area > 5000 sqft; recalculate |
| Growth 1494% | No outlier filtering in `calculate_growth()` | IQR outlier removal + min 3 data points + ±80% cap |
| Comparable = 0 | No comparable data silently set to 0 | Use `None`, set `marketPosition = "Insufficient Comparables"` |
| Demand = 0, Liquidity = 100 | Demand score never computed | `demand_score = clamp(txn_volume * 5 + rent_volume * 3, 0, 100)` |
| Absorption 1900% | No cap on absorption rate | `min(absorption_rate, 300)` |
| Developer = Independent | Dar Al Arkan not in keyword list | Added with aliases: MISSONI, URBAN OASIS, OCTA ISLE |
| Price change -79% | Corrupted price_sqft in growth calc | ±40% cap + filtered sales data |
| Villa returns studio | Title keyword matching (false positives) | Strict `category` field filtering from listing data |
| Future supply = 0 | Supply index only used total_supply field | Added project count factor |
| Offplan bedType mismatch | v2 uses `1br`, filter expected `1 B/R` | `normalize_bedtype()` function maps all formats |
| Offplan 0 matches | Server mapped `propertyType` not `property_type` | Fixed `apil_server.py` profile field mapping |
| Offplan launch price = 0 | Old engine used `projectPriceSqft` (always 0) | v2 engine fetches actual `askingPrice` from Qdrant |
| 0% growth displayed | No data available, growth=0 | Frontend shows "Insufficient Data" not 0% |
| Undefined toFixed crash | `discountPct` undefined when no market valuation | Frontend uses `!= null` (catches both null and undefined) |

### 1.10 Scheduler (`/backend/scheduler/scheduler.py`)

| Mode | Frequency | Tasks |
|------|-----------|-------|
| **Daily** | Every day | ETL import + Community + Project + Ready + Off-plan v2 engines |
| **Weekly** | Every week | Developer engine + full re-import of DXB data |
| **Monthly** | Every month | Full rebuild — all ETL + all engines + Qdrant re-fetch |

### 1.11 Pipeline Runner (`/backend/run_pipeline.py`)

```bash
cd backend
python3 run_pipeline.py              # Run all ETL + validation + feature + engines
python3 run_pipeline.py --engines     # Run engines only (no API)
python3 run_pipeline.py --api         # Start API only
python3 run_pipeline.py --serve       # Run pipeline + start API server (default)
```

**Pipeline steps in order:**
1. ETL: Import DLD → `dld_warehouse.json`
2. ETL: Import DXBInteract → `dxb_warehouse.json`
3. ETL: Import Google Reviews → `google_warehouse.json`
4. **Stage 1**: Validation Engine v2 → `validation_results.json` (reject impossible listings)
5. Feature Engineering Engine → `feature_store.json` (normalize, clean, cap)
6. **Stage 2**: Market Valuation → fair value per property (weighted medians)
7. **Stage 3**: Community Engine → `community_scores.json` (~154 communities)
8. **Stage 3**: Developer Engine → `developer_scores.json` (~33 developers)
9. **Stage 3**: Project Engine → `project_scores.json` (~1,312 projects)
10. **Stage 3**: Ready Property Engine → `ready_property_scores.json` (~600+ properties)
11. **Stage 3**: Off-Plan Engine v2 → `offplan_scores.json` (~3,441 properties from Qdrant)
12. **Stage 4**: Confidence Engine → confidence scores attached to each property
13. **Stage 5**: Recommendation mapping → action terms (Buy/Watchlist/Avoid)
14. **Stage 6**: Rules Engine → hard overrides applied
15. **Stage 7**: LLM Advisor → advisory reports (on-demand via API)
16. Recommendation Engine → Dynamic filtering + sorting (on-demand via API)

---

## 2. Backend API

### 2.1 Combined Server (`apil_server.py`)

The production server runs on **port 8090** and serves both the FastAPI backend and the static React frontend.

```bash
cd /home/shivang/apil-investment-new
python3 apil_server.py    # Starts on 0.0.0.0:8090
```

### 2.2 Endpoints

| Method | Path | Description | Expected Response |
|--------|------|-------------|-------------------|
| `GET` | `/health` | Health check + data file status | `{ status: "ok", data_files: { communities: true, ... } }` |
| `GET` | `/communities` | All community scores | Array of ~154 community objects |
| `GET` | `/communities/{slug}` | Single community by slug | Community with priceIndex, rentalIndex, subScores |
| `GET` | `/developers` | All developer scores | Array of ~33 developer objects |
| `GET` | `/developers/{name}` | Single developer by name | Developer with scoreBreakdown, aliases |
| `GET` | `/projects?limit=N` | Project scores (paginated) | Array of project objects (default 100) |
| `GET` | `/projects/{slug}` | Single project by slug | Project with unitTypes, priceSqft, rentalYield |
| `GET` | `/properties/ready?limit=N` | Ready property scores | Array of ~600+ ready property objects |
| `GET` | `/properties/ready/{id}` | Single ready property | Property with roi, liquidity, risk, marketValuation, confidenceScore, rulesFlags |
| `GET` | `/properties/offplan?limit=N` | Off-plan property scores | Array of ~3,441 offplan v2 objects |
| `GET` | `/properties/offplan/{slug}` | Single off-plan property | Property with fairValue, priceOpportunity, futureAppreciation, listingData |
| `GET` | `/properties/ready/{id}/advisory` | LLM advisory for ready property | Advisory report (summary, thesis, strengths, risks, negotiation, exit) |
| `GET` | `/properties/offplan/{slug}/advisory` | LLM advisory for offplan | Advisory report |
| `GET` | `/properties/compare?ids=...&slugs=...` | LLM comparison | Side-by-side comparison with trade-offs |
| `POST` | `/recommendations` | Dynamic recommendations | `{ totalReadyMatches, totalOffplanMatches, recommendations[], topReady[], topOffplan[] }` — includes rulesFlags + confidenceScore per property |
| `POST` | `/report` | Full report data | Report with top property + enriched listing data |

### 2.3 Investor Profile (POST body)

```json
{
  "goal": "rental_income | capital_growth | holiday_home | balanced",
  "budget": "500k-1m | 1m-2m | 2m-5m | 5m+ | custom:1500000",
  "property_type": "apartment | villa | townhouse | penthouse",
  "bedrooms": "studio | 1 | 2 | 3",
  "location": "any | dubai_marina | business_bay | ...",
  "ready_offplan": "ready | offplan | either",
  "timeline": "1y | 3y | 5y | 10y",
  "financing": "cash | mortgage",
  "risk": "low | medium | high"
}
```

### 2.4 Qdrant Integration

The off-plan engine fetches live property data from Qdrant vector database.

| Setting | Value |
|---------|-------|
| Qdrant URL | `http://localhost:6333` |
| Collection | `Dubai_real_estate_calculation_data_` |
| Filter | `is_off_plan: True` |
| Fetch method | Scroll API (200 per batch, up to 50 batches) |
| Expected fetch | ~3,610 off-plan listings |
| Skipped (no price/size) | ~169 |
| Final scored | ~3,441 properties |

**Qdrant payload fields used:**
- `askingPrice` — developer's current asking price
- `sizeSqft` — unit size
- `bedType` — studio, 1br, 2br, 3br, 4br, 5br, 6br, 7br+
- `category` — Apartment, Villa, Townhouse, Penthouse, Duplex, Mansions
- `projectName` — project name for matching
- `area` — community/area name
- `developer` — developer name
- `images` — array of { url, alt } objects
- `description` — marketing description text
- `paymentPlans` — installment schedule
- `amenities` — facility features
- `highlights` — key selling points
- `canonicalUrl` — listing URL

---

## 3. Frontend Architecture

### 3.1 API Client (`/src/data/api.ts`)

Typed HTTP client with interfaces for all backend data types. **No scoring logic exists in the frontend.**

Key TypeScript interfaces:
- `CommunityScore`, `DeveloperScore`, `ProjectScore`, `ReadyPropertyScore`
- `OffplanScoreV2` — full v2 off-plan type with fairValue, priceOpportunity, futureAppreciation, postHandoverROI, developerData, communityData, liquidity, listingData
- `RecommendationItem` — union type for ready | offplan recommendations
- `RecommendationResponse` — includes totalReadyMatches, totalOffplanMatches, recommendations[]

### 3.2 Data Loader (`/src/data/loader.ts`)

Async wrapper around `api.ts` with caching and legacy mapping functions.

- **Caches** all API responses in memory
- **Maps** API response types → legacy UI shapes via `mapReadyToLegacy()`, `mapCommunityToLegacy()`, `mapProjectToLegacy()`
- Exports: `OffplanScoreV2`, `RecommendationItem` types for offplan-aware components

### 3.3 Pages

| Page | Route | Data Source | Description |
|------|-------|-------------|------------|
| `Landing.tsx` | `/` | API: communities + properties | Hero, stats, top communities, sample reports |
| `Questionnaire.tsx` | `/investment-advisor` | sessionStorage (user input) | 6-step investor profile questionnaire |
| `Analyzing.tsx` | `/investment-advisor/analyzing` | API: POST /recommendations | Animation + pre-fetches recommendations |
| `Report.tsx` | `/investment-report/:reportId` | API: recommendations + communities + projects | Full investment report — **7 decision-focused sections** for ready properties, offplan sections for offplan |
| `CommunityAnalysis.tsx` | `/investment-advisor/community/:slug` | API: community + projects | Community deep-dive |
| `ProjectAnalysis.tsx` | `/investment-advisor/project/:slug` | API: project + community + properties | Project deep-dive |
| `UnitAnalysis.tsx` | `/investment-advisor/unit/:slug/:bedType` | API: project + properties | Unit type analysis |
| `PropertyAnalysis.tsx` | `/investment-property/:propertyId` | API: property + project + community | Single property detail |
| `Compare.tsx` | `/investment-compare` | API: properties | Side-by-side property comparison |
| `DebugXRay.tsx` | `/x-ray-debug-9281` | API: all endpoints | Debug tool for inspecting raw engine data |

### 3.4 Components

#### Shared Components

| Component | Purpose |
|-----------|---------|
| `ScoreRing` | Circular score gauge (0-100) |
| `ScoreBadge` | Compact score pill |
| `RiskBadge` | Risk level indicator |
| `MarketPositionBadge` | Fair/Premium/Discount badge |
| `GrowthIndicator` | Up/down growth arrow |
| `StatCard` | Label + value stat display |
| `formatAED` | Format AED currency |
| `formatNumber` | Format numbers with commas |

#### Report Components

| Component | Purpose |
|-----------|--------|
| `ROIBreakdownCard` | Gross/net ROI breakdown (ready properties) |
| `ComparableTransactionsCard` | Sold comparables table |
| `RiskMatrixCard` | 7-dimension risk matrix |
| `LLMAdvisorySection` | AI advisory display (summary, thesis, strengths, risks, negotiation, exit, data reliability) |
| `OffplanReportSections.tsx` | Off-plan report sections (v2): OffplanOverviewSection, OffplanDeveloperSection, OffplanCommunitySection, OffplanLiquiditySection, OffplanFinalVerdict, OffplanAlternativesSection |
| `ErrorBoundary` | Catches render errors gracefully |
| `Layout` | Page layout wrapper with navigation |

### 3.5 Report.tsx — Decision-Focused Report Structure

The report uses **7 decision-focused sections** (replacing the old 11 data-focused sections) for ready properties:

| Section ID | Label | Icon | Component | What It Shows |
|-----------|-------|------|-----------|---------------|
| `verdict` | Verdict | LayoutDashboard | `VerdictSection` | Hero card: recommendation + score, top 3 reasons to buy, top 3 risks, actionable advice, goal alignment, score breakdown bars |
| `returns` | Returns | TrendingUp | `ReturnsSection` | Net income/year, net yield, price growth (12m), total return estimate, ROI breakdown, scenario analysis (rent drop 10%, price negotiation), market valuation (asking vs fair value), comparable transactions |
| `market` | Market | MapPin | `MarketSection` | Area profile: community score, demand/supply/growth indices, median price/sqft, rental yield, sales/rent volume, price trends (3/6/12m) |
| `property` | Property | Building2 | `PropertySection` | Building profile (project name, price/sqft, rental yield, price change), developer score + breakdown (track record, delivery, quality, delay risk), resale liquidity (score, est. time to sell, market position), risk matrix (7 dimensions) |
| `evidence` | Evidence | FileText | `EvidenceSection` | Evidence counts (comparable sales, rental contracts, project transactions, area sales volume), recommendation confidence (level + description), validation rules applied (rulesFlags), investment risk vs data confidence (separate cards), data sources (community, building, property) |
| `advisor` | AI Advisor | Sparkles | `LLMAdvisorySection` | LLM advisory: executive summary, thesis, strengths, risks, negotiation tips, exit strategy, data reliability, contradictions, score explanation |
| `alternatives` | Alternatives | GitCompare | `AlternativesSection` | Alternative properties with trade-off comparison (rental yield, liquidity, growth, overall score vs top pick) |

**Key frontend behaviors:**
- **Goal-aware personalization**: Verdict section shows goal-specific alignment text ("This property aligns with your X goal because...")
- **Terminology mapping**: Backend recommendations mapped to user-friendly labels (STRONG BUY → "Buy", HOLD → "Buy if Negotiated", CAUTION → "Watchlist", REVIEW → "Needs Review")
- **0% growth handling**: Shows "Insufficient Data" instead of 0% when growth data is unavailable
- **Safe null handling**: Uses `!= null` (not `!== null`) to catch both `null` and `undefined` for optional fields like `discountPct`
- **Score context helper**: Maps 0-100 scores to labels (Excellent ≥80, Good ≥65, Fair ≥50, Weak ≥35, Poor <35)
- **ROI breakdown hidden for capital growth investors**: `ROIBreakdownCard` only shown for non-capital-growth goals

---

## 4. User Flow (End-to-End)

### 4.1 Ready Property Flow

```
Step 1: User visits Landing page (/)
        → Sees top communities + sample investment reports
        → Clicks "Start Investment Analysis"
        → Expected: Landing page loads with community stats, total sales count

Step 2: Questionnaire (/investment-advisor)
        → 6 questions: Goal, Budget, Property Type, Bedrooms, Timeline, Risk
        → User selects ready_offplan: "ready" (or "either")
        → Answers saved to sessionStorage as 'investorProfile'
        → Navigates to /investment-advisor/analyzing?reportId=RPT-XXX

Step 3: Analyzing (/investment-advisor/analyzing)
        → 8-step animation (~6.4 seconds)
        → Simultaneously: POST /recommendations with investor profile
        → API filters ready properties by type, bedrooms, budget, location, risk
        → Sorts by goal (rental_income → netROI, capital_growth → growth12m)
        → API response cached in sessionStorage as 'apiRecommendations'
        → Expected: { totalReadyMatches: 600+, totalOffplanMatches: 0, recommendations: 10 }
        → Navigates to /investment-report/RPT-XXX

Step 4: Report (/investment-report/:reportId) — READY property
        → isOffplanV2(topRec) = false → renders ready property sections
        → Fetches communities + projects from API in parallel
        → Maps API data to legacy UI format
        → Renders 7 decision-focused sections:
            1. Verdict — recommendation hero, top 3 reasons to buy, top 3 risks,
               actionable advice, goal alignment, score breakdown bars
            2. Returns — net income/year, net yield, price growth, total return,
               ROI breakdown, scenario analysis, market valuation, comparables
            3. Market — area profile: community score, demand/supply/growth,
               median price/sqft, rental yield, price trends
            4. Property — building profile, developer score, resale liquidity,
               risk matrix (7 dimensions)
            5. Evidence — evidence counts, confidence level, validation rules,
               data sources, investment risk vs data confidence
            6. AI Advisor — LLM advisory (summary, thesis, strengths, risks,
               negotiation, exit strategy, data reliability)
            7. Alternatives — 4 alternative properties with trade-off comparison
        → Sidebar navigation with 7 sections + icons
        → Goal-aware: verdict section personalized based on investor goal

Step 5: Deep-dive navigation
        → User clicks through to Community, Project, or Property detail pages
```

### 4.2 Off-Plan Property Flow

```
Step 1: User visits Landing page (/)
        → Clicks "Start Investment Analysis"

Step 2: Questionnaire (/investment-advisor)
        → User selects ready_offplan: "offplan"
        → Answers saved to sessionStorage as 'investorProfile'
        → Navigates to /investment-advisor/analyzing?reportId=RPT-XXX

Step 3: Analyzing (/investment-advisor/analyzing)
        → POST /recommendations with investor profile
        → API fetches offplan_scores.json (3,441 properties)
        → filter_offplan_properties():
            - Property type: category in PROPERTY_TYPE_MAP[prop_type]
            - Bedrooms: normalize_bedtype(bedType) in target_set
            - Budget: askingPrice within range
            - Location: area or project contains location
            - Risk: exclude AVOID for low-risk investors
        → sort_by_goal(): capital_growth → futureAppreciation.potentialGainPct
        → Expected: { totalReadyMatches: 300+, totalOffplanMatches: 280+, recommendations: 10 }
        → Navigates to /investment-report/RPT-XXX

Step 4: Report (/investment-report/:reportId) — OFF-PLAN property
        → isOffplanV2(topRec) = true → renders off-plan sections
        → OffplanOverviewSection:
            - Recommendation banner: STRONG BUY / BUY / NEGOTIATE / HOLD / AVOID
            - Quick stats: Price vs Market %, Future Gain %, Post-Handover ROI %, Risk
            - Buy reasons + Watch items
            - Property images gallery (from Qdrant listingData.images)
            - Property description + highlights (from Qdrant)
            - Property details: developer price, fair market value, size, price/sqft, developer, completion timeline
            - Fair Value Analysis: developer price vs fair market value, community median/sqft, location factor, project premium
            - Future Appreciation: purchase price, projected future value, potential gain, growth rate, completion timeline
            - Post-Handover ROI: est. rent, gross/net ROI, service charge, management fee, vacancy cost, rent source
            - Score Breakdown: 6 factors (Price Opportunity 25%, Future Appreciation 25%, Developer 20%, Community 15%, Liquidity 10%, ROI 5%)
            - Things to Keep in Mind: deductions per component
            - Payment Plans: installment schedule from Qdrant
            - Amenities: facility features from Qdrant
            - Risk Factors: developer score, delay risk, price above market, future supply
        → OffplanCommunitySection: 8 sub-scores, 12M growth, supply index, rental demand
        → OffplanDeveloperSection: 5-component score breakdown, delay risk, market position
        → OffplanLiquiditySection: liquidity score, time to sell, transaction volume
        → RiskMatrixCard: 7-dimension risk matrix
        → LLMAdvisorySection: AI advisory (if available)
        → OffplanAlternativesSection: alternative off-plan properties with images
        → OffplanFinalVerdict: recommendation, key metrics, main risks, benchmark comparison, overall opinion

Step 5: Deep-dive navigation
        → User can explore alternatives or start a new search
```

### 4.3 Sample API Response (Off-Plan)

```json
{
  "totalReadyMatches": 314,
  "totalOffplanMatches": 280,
  "recommendations": [
    {
      "id": 4467,
      "title": "Sera Gardens | Studio Apartment",
      "propertyType": "offplan",
      "askingPrice": 594000,
      "offplanScore": 87,
      "recommendation": "STRONG BUY",
      "fairValue": { "fairValue": 943278, "source": "community" },
      "priceOpportunity": { "priceDifferencePct": -37.03, "label": "Strong Buy — Well below market" },
      "futureAppreciation": { "futureValue": 1037675, "potentialGainPct": 74.69, "growthRate": 25.0 },
      "postHandoverROI": { "netROI": 11.83, "estimatedRent": 85000 },
      "developerData": { "developerScore": 50, "developerName": "Independent / Other" },
      "communityData": { "communityScore": 80, "demandIndex": 100 },
      "listingData": { "images": [{"url": "..."}], "description": "...", "paymentPlans": [...] }
    }
  ]
}
```

---

## 5. Data Flow Diagram

```
                    ┌──────────────────────────────────────────────────────┐
                    │                    DATA SOURCES                       │
                    │  DLD CSV  │  DXBInteract  │  Google Maps  │ Qdrant  │
                    └─────┬──────────┬──────────────┬────────────┴────┬────┘
                          │          │              │                  │
                    ┌─────▼──────────▼──────────────▼──────────┐      │
                    │              ETL LAYER                    │      │
                    │  import_dld  │  import_dxb  │ import_google│      │
                    └─────┬────────────────────────────────────┘      │
                          │                                           │
                    ┌─────▼────────────────────────────────────┐      │
                    │         WAREHOUSE JSONS                  │      │
                    │  dld_warehouse │ dxb_warehouse │ google_wh│      │
                    └─────┬────────────────────────────────────┘      │
                          │                                           │
                    ┌─────▼────────────────────────────────────┐      │
                    │  STAGE 1: VALIDATION ENGINE v2           │      │
                    │  Reject impossible listings              │      │
                    │  → validationStatus, evidenceLevels      │      │
                    └─────┬────────────────────────────────────┘      │
                          │                                           │
                    ┌─────▼────────────────────────────────────┐      │
                    │  FEATURE ENGINE + STAGE 2: MARKET VAL.   │      │
                    │  Fair value from weighted medians         │      │
                    │  → fairValueSqft, discountPct, class     │      │
                    └─────┬────────────────────────────────────┘      │
                          │                                           │
                    ┌─────▼────────────────────────────────────┐      │
                    │  STAGE 3: SCORING ENGINES                │      │
                    │  community_engine → community_scores.json │      │
                    │  developer_engine → developer_scores.json│      │
                    │  project_engine ──→ project_scores.json  │      │
                    │  ready_engine ────→ ready_scores.json    │      │
                    │                                          │      │
                    │  offplan_engine_v2 ←─────────────────────┼──────┘
                    │    (fetches Qdrant off-plan listings)    │
                    │    → offplan_scores.json (3,441 props)   │
                    └─────┬────────────────────────────────────┘
                          │
                    ┌─────▼────────────────────────────────────┐
                    │  STAGE 4: CONFIDENCE ENGINE              │
                    │  Evidence-based: sales×rental×dev×proj×comm│
                    │  → confidenceScore, confidenceLevel       │
                    └─────┬────────────────────────────────────┘
                          │
                    ┌─────▼────────────────────────────────────┐
                    │  STAGE 5: RECOMMENDATION MAPPING         │
                    │  Score → action term (Buy/Watchlist/Avoid)│
                    └─────┬────────────────────────────────────┘
                          │
                    ┌─────▼────────────────────────────────────┐
                    │  STAGE 6: RULES ENGINE                   │
                    │  Hard overrides (insufficient → REVIEW)  │
                    │  → rulesFlags[]                          │
                    └─────┬────────────────────────────────────┘
                          │
                    ┌─────▼────────────────────────────────────┐
                    │  STAGE 7: LLM ADVISOR (on-demand)        │
                    │  Qwen2.5-VL-7B: explains, advises        │
                    │  (ADVISORY ONLY — never scores)          │
                    └─────┬────────────────────────────────────┘
                          │
                    ┌─────────────────▼────────────────────────┐
                    │        COMBINED SERVER (:8090)            │
                    │  apil_server.py = FastAPI + static serve  │
                    │                                          │
                    │  GET  /communities                       │
                    │  GET  /developers                        │
                    │  GET  /projects                          │
                    │  GET  /properties/ready                  │
                    │  GET  /properties/offplan                │
                    │  GET  /properties/{id}/advisory          │
                    │  POST /recommendations (dynamic filter)  │
                    │  + serves React build from /dist         │
                    └─────────────────┬────────────────────────┘
                                      │ HTTP (JSON)
                    ┌─────────────────▼────────────────────────┐
                    │         REACT FRONTEND (:5173 dev)       │
                    │         (served by :8090 in prod)        │
                    │                                          │
                    │  api.ts ──▶ loader.ts ──▶ Pages          │
                    │                                          │
                    │  Report.tsx (7 decision-focused sections):│
                    │    Verdict │ Returns │ Market │ Property │
                    │    Evidence │ AI Advisor │ Alternatives  │
                    │                                          │
                    │  if isOffplanV2(topRec):                 │
                    │    OffplanReportSections.tsx             │
                    │    (fair value, future value, images,    │
                    │     payment plans, developer breakdown)  │
                    │                                          │
                    │  NO SCORING LOGIC                        │
                    │  PURE PRESENTATION LAYER                 │
                    └──────────────────────────────────────────┘
```

---

## 6. Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI, Uvicorn, Pydantic |
| Engines | Python 3.9+, JSON I/O, urllib (Qdrant HTTP) |
| Vector DB | Qdrant (port 6333, collection `Dubai_real_estate_calculation_data_`) |
| LLM Advisor | Qwen2.5-VL-7B-Instruct (port 8001, OpenAI-compatible API) |
| Scheduler | Python `schedule` library |
| Frontend | React 18, TypeScript, Vite |
| UI | TailwindCSS, Lucide Icons, Recharts |
| Data | DLD transactions, DXBInteract, Google Maps, Qdrant listings |
| Production Server | `apil_server.py` on port 8090 (FastAPI + static frontend) |
| Python compat | 3.9+ (uses `from __future__ import annotations` + `Optional[]`) |

---

## 7. Key Rules

1. **Frontend NEVER computes scores** — all scoring is backend-only
2. **No JSON score files in frontend** — all data fetched from API at runtime
3. **Backend engines are idempotent** — re-running produces the same output
4. **API is stateless** — all filtering happens via POST body, no server-side sessions
5. **All scores include confidence** — every output has `confidenceScore` (0–100) + `confidenceLevel`
6. **Recommendation engine never violates property type** — progressive relaxation with notification
7. **Plot-area sales are filtered** — sales with `area_sqft > 5000` are excluded
8. **All monetary values are capped** — ROI ≤12%, growth ±80%, absorption ≤300%, price change ±40%
9. **Off-plan never compares to launch price** — always compares current developer asking price vs current fair market value
10. **Off-plan fair value uses DLD transactions** — community median price/sqft × size × location factor × project premium
11. **Off-plan future value uses community growth** — not developer projections; growth rate capped at 0-25%
12. **Qdrant data is live** — off-plan engine fetches current listings at pipeline run time, not static files
13. **LLM is ADVISORY ONLY** — Qwen2.5-VL never calculates scores, estimates rent, or determines confidence
14. **Rules engine overrides are NON-NEGOTIABLE** — insufficient data → max REVIEW, high premium → max CAUTION
15. **Confidence ≠ Score quality** — confidence measures data evidence, not investment quality
16. **Frontend uses `!= null`** — catches both `null` and `undefined` for optional backend fields

---

## 8. Development Commands

```bash
# Backend
cd backend
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload   # Start API (dev)
python3 run_pipeline.py                                                 # Run all engines
python3 run_pipeline.py --serve                                         # Engines + API
python3 scheduler/scheduler.py                                          # Start scheduler

# Off-plan engine v2 (standalone)
cd backend
python3 -c 'from engines.offplan_engine_v2 import run; run()'           # Fetch Qdrant + score

# Production server (combined API + frontend)
cd /home/shivang/apil-investment-new
python3 apil_server.py                                                  # Port 8090

# Frontend
cd apil-investment-demo
npm run dev          # Vite dev server (port 5173)
npm run build        # Production build → dist/
npx tsc --noEmit     # Type check

# Deploy frontend to server
rsync -az --delete dist/ shivang@87.200.15.174:/home/shivang/apil-investment-new/dist/

# Environment
VITE_API_BASE=http://localhost:8000   # Frontend API base URL (optional)
```

---

## 9. File Structure

```
apil-investment-demo/
├── backend/
│   ├── api/
│   │   └── main.py                    # FastAPI application (dev)
│   ├── config/
│   │   └── settings.py                # Paths, data sources, API config
│   ├── engines/
│   │   ├── validation_engine.py       # Legacy validation (anomalies, outliers)
│   │   ├── validation_engine_v2.py    # Stage 1: Validation v2 (price/sqft, comparables, rentals, developer)
│   │   ├── market_valuation.py        # Stage 2: Fair value from weighted medians + price classification
│   │   ├── feature_engine.py          # Feature engineering (normalization, cleaning, capping)
│   │   ├── confidence_engine.py       # Stage 4: Evidence-based confidence (sales×rental×dev×proj×comm)
│   │   ├── community_engine.py        # Stage 3: Community scoring
│   │   ├── developer_engine.py        # Stage 3: Developer scoring
│   │   ├── project_engine.py          # Stage 3: Project scoring
│   │   ├── ready_engine.py            # Stage 3: Ready property scoring
│   │   ├── offplan_engine.py          # Legacy off-plan scoring (v1)
│   │   ├── offplan_engine_v2.py       # Stage 3: Off-plan scoring v2 (Qdrant + fair value + future appreciation)
│   │   ├── rules_engine.py            # Stage 6: Hard business rules (7 non-negotiable overrides)
│   │   ├── recommendation_engine.py   # Dynamic recommendations (ready + offplan filtering + goal sort)
│   │   ├── llm_engine.py              # Stage 7: LLM Advisor (8 advisory functions, Qwen2.5-VL)
│   │   ├── qdrant_enrichment.py       # Qdrant client for property enrichment
│   │   └── utils.py                   # Shared helpers (IQR, growth, median, clamp, normalize_bedtype)
│   ├── etl/
│   │   ├── import_dld.py              # DLD transaction import
│   │   ├── import_dxb.py              # DXBInteract developer import
│   │   └── import_google.py           # Google Maps review import
│   ├── scheduler/
│   │   └── scheduler.py               # Daily/weekly/monthly scheduler
│   ├── data/                          # Generated score files (gitignored)
│   │   ├── community_scores.json      # ~154 communities
│   │   ├── developer_scores.json      # ~33 developers
│   │   ├── project_scores.json        # ~1,312 projects
│   │   ├── ready_property_scores.json # ~600+ ready properties
│   │   ├── offplan_scores.json        # ~3,441 off-plan properties (v2)
│   │   ├── feature_store.json         # Normalized per-unit features
│   │   └── validation_results.json    # Data quality flags
│   ├── run_pipeline.py                # Manual pipeline runner
│   └── requirements.txt               # Python dependencies
├── apil_server.py                     # Combined server (FastAPI + static frontend, port 8090)
├── src/
│   ├── data/
│   │   ├── api.ts                     # API client (typed) — includes OffplanScoreV2, RecommendationItem
│   │   └── loader.ts                  # Async data loader (cached, mapped) — exports offplan types
│   ├── pages/
│   │   ├── Landing.tsx                # Home page
│   │   ├── Questionnaire.tsx          # Investor profile questionnaire
│   │   ├── Analyzing.tsx              # Loading animation + API pre-fetch
│   │   ├── Report.tsx                 # Full investment report (7 decision-focused sections for ready, offplan sections for offplan)
│   │   ├── CommunityAnalysis.tsx      # Community detail
│   │   ├── ProjectAnalysis.tsx        # Project detail
│   │   ├── UnitAnalysis.tsx           # Unit type detail
│   │   ├── PropertyAnalysis.tsx       # Property detail
│   │   ├── Compare.tsx                # Property comparison
│   │   └── DebugXRay.tsx              # Debug tool for raw engine data inspection
│   ├── components/
│   │   ├── Shared.tsx                 # ScoreRing, ScoreBadge, RiskBadge, MarketPositionBadge, GrowthIndicator, StatCard, formatAED, formatNumber
│   │   ├── ErrorBoundary.tsx          # Catches render errors gracefully
│   │   ├── ROIBreakdownCard.tsx       # ROI breakdown (ready properties)
│   │   ├── ComparableTransactionsCard.tsx # Sold comparables table
│   │   ├── RiskMatrixCard.tsx         # 7-dimension risk matrix
│   │   ├── LLMAdvisorySection.tsx     # AI advisory display (summary, thesis, strengths, risks, negotiation, exit)
│   │   ├── OffplanReportSections.tsx  # Off-plan report sections (v2):
│   │   │                              #   OffplanOverviewSection, OffplanDeveloperSection,
│   │   │                              #   OffplanCommunitySection, OffplanLiquiditySection,
│   │   │                              #   OffplanFinalVerdict, OffplanAlternativesSection
│   │   └── Layout.tsx                 # Page layout wrapper with navigation
│   ├── test/                          # Unit tests (vitest) — not part of production build
│   │   ├── components/                # Component tests
│   │   ├── unit/                      # Unit tests (Shared.test.tsx)
│   │   ├── fixtures/mockData.ts       # Test mock data
│   │   └── setup.ts                   # Test setup
│   └── main.tsx                       # Router + app entry (wrapped in ErrorBoundary)
├── dist/                              # Production build (deployed to server)
└── ARCHITECTURE_FLOW.md               # This file
```

---

## 10. Pipeline Expected Results Summary

| Pipeline Step | Stage | Input | Output File | Expected Count | Key Fields |
|---------------|-------|-------|-------------|----------------|------------|
| ETL: DLD Import | — | DLD CSVs | `dld_warehouse.json` | ~50K transactions | price, rent, area, project, bedType |
| ETL: DXB Import | — | DXBInteract scrape | `dxb_warehouse.json` | ~33 developers | salesCount, capitalGain, projectsDelivered |
| Validation v2 | Stage 1 | Listing + community + project + dev | `validation_results.json` | ~1,312 projects | validationStatus, evidenceLevels, expectedPrice |
| Feature Engineering | — | Project + validation | `feature_store.json` | ~1,312 projects | unitFeatures (medianPriceSqft, medianRent per bed type) |
| Market Valuation | Stage 2 | Area + community/project/building medians | (embedded in property scores) | per property | fairValueSqft, fairValueTotal, discountPct, classification |
| Community Engine | Stage 3 | DLD warehouse | `community_scores.json` | ~154 communities | communityScore, priceIndex, rentalIndex, growth12m, demandIndex |
| Developer Engine | Stage 3 | DXB + Google | `developer_scores.json` | ~33 developers | developerScore, trackRecord, deliveryHistory, marketPosition |
| Project Engine | Stage 3 | DLD + dev scores | `project_scores.json` | ~1,312 projects | projectScore, priceSqft, unitTypes, rentalYield |
| Ready Engine | Stage 3 | Listings + all scores | `ready_property_scores.json` | ~600+ properties | readyScore, roi, liquidity, risk, marketValuation, recommendation |
| **Off-Plan Engine v2** | **Stage 3** | **Qdrant (3,610) + all scores** | **`offplan_scores.json`** | **~3,441 properties** | **offplanScore, fairValue, priceOpportunity, futureAppreciation, postHandoverROI, listingData** |
| Confidence Engine | Stage 4 | Sales/rent/dev/project/comm counts | (embedded in property scores) | per property | confidenceScore, confidenceLevel, confidenceBreakdown |
| Recommendation Mapping | Stage 5 | Score + price difference | (embedded) | per property | recommendation (STRONG BUY/BUY/HOLD/CAUTION/REVIEW/AVOID) |
| Rules Engine | Stage 6 | Scored property + investor goal | (embedded) | per property | rulesFlags[] (RULE_1_INSUFFICIENT_SALES, etc.) |
| LLM Advisor | Stage 7 | Scored property + profile | Dynamic (API) | on-demand | advisory report (summary, thesis, strengths, risks, negotiation, exit) |
| Recommendation Engine | — | Ready + offplan + profile | Dynamic (API) | 10 recommendations | totalReadyMatches, totalOffplanMatches, sorted by goal |

### Server Deployment

| Component | Address | Port |
|-----------|---------|------|
| Qdrant Vector DB | localhost | 6333 |
| Qwen LLM Advisor | localhost | 8001 |
| Combined Server (API + Frontend) | 87.200.15.174 | 8090 |
| Frontend Dev Server | localhost | 5173 |
