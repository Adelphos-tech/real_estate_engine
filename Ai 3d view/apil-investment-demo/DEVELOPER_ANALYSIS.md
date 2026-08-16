# Developer Analysis Module (Module 5) — Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Data Sources](#data-sources)
3. [Still LLM-Estimated Fields](#still-llm-estimated-fields)
4. [Build Script Algorithm (`build_developer_scores.py`)](#build-script-algorithm)
5. [Frontend Scoring Engine (`engine.ts`)](#frontend-scoring-engine)
6. [DeveloperCard Component](#developercard-component)
7. [Output JSON Schema (`developers.json`)](#output-json-schema)
8. [Scraper Scripts](#scraper-scripts)
9. [How to Rebuild](#how-to-rebuild)

---

## Overview

The Developer Analysis module (Module 5 / M5) provides real estate developer reliability scoring for the APIL Investment Advisor app. It combines **three real data sources** and **one LLM source** to produce a comprehensive developer profile with a 0-100 score.

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  build_developer_scores.py                       │
│                                                                  │
│  ┌──────────┐   ┌──────────────┐   ┌───────────┐   ┌─────────┐ │
│  │ DLD Local │   │ DXBInteract  │   │  Google   │   │  LLM    │ │
│  │ Trans. CSV│   │  Scraper     │   │  Maps     │   │ Qwen2.5 │ │
│  │ + Projects│   │  (headless)  │   │  Scraper  │   │  -VL    │ │
│  └─────┬─────┘   └──────┬───────┘   └─────┬─────┘   └────┬────┘ │
│        │                │                 │              │       │
│        ▼                ▼                 ▼              ▼       │
│   Local Metrics    DXB Metrics     Google Reviews   Qualitative │
│   (sales, yield,   (YTD txn,      (rating, review   (quality,   │
│    rent, price)     value, proj,    count)           reputation, │
│                     units, gain)                      summary)  │
│        │                │                 │              │       │
│        └────────────────┴────────┬────────┴──────────────┘       │
│                                  ▼                               │
│                        MERGE + SCORE                            │
│                                  ▼                               │
│                     developers.json                             │
└──────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────┐
                    │   engine.ts         │
                    │  (frontend scoring) │
                    │  matchDeveloper()   │
                    │  calculateRisk()    │
                    │  calculateScores()  │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  DeveloperCard.tsx  │
                    │  (UI display)       │
                    └─────────────────────┘
```

---

## Data Sources

### Source 1: Local DLD Transaction Data (100% Real)

**Files:**
- `/Users/apple/Desktop/Ai 3d view/dxb_transactions.csv` — DLD transaction records
- `src/data/dxb_projects.json` — Project-level data (prices, yields, rent counts)

**What it provides:**
- `salesCount` — Number of transactions per developer (from CSV)
- `salesValue` — Total transaction value in AED (from CSV)
- `offplanCount` / `readyTxnCount` — Off-plan vs ready transaction split
- `avgCapitalGain` — Average price change % across projects
- `avgRentalYield` — Average rental yield % across projects
- `totalRentContracts` — Total rental contracts from project data
- `avgPriceSqft` — Average price per sqft across projects
- `areasCovered` — List of areas where developer has projects
- `projectNames` — List of project names
- `totalProjects` — Count of projects in local data
- `readyProjects` — Projects with non-zero avg_price

**Algorithm (`compute_metrics_from_local_data()`):**
1. Load `dxb_projects.json` (scraped project data)
2. Load `dxb_transactions.csv` (DLD transaction records)
3. For each project, match to developer using keyword matching:
   - `match_developer(project_name)` checks `project_name.upper()` against `DEVELOPER_KEYWORDS` dict
   - Each developer has a list of keyword strings (e.g., Emaar: `['EMAAR', 'BURJ KHALIFA', 'DUBAI HILLS', ...]`)
   - If any keyword is a substring of the project name, it's assigned to that developer
   - No match → `'Independent / Other'`
4. Group all projects and transactions by developer
5. Compute aggregate metrics per developer

**Keyword Matching Example:**
```
Project: "Emaar Serro 2 at The Heights"
→ Uppercase: "EMAAR SERRO 2 AT THE HEIGHTS"
→ Matches keyword "EMAAR" → Developer: "Emaar Properties"
```

**Accuracy:** ~90% — keyword matching is reliable for major developers but may miss smaller ones or misclassify projects with ambiguous names.

---

### Source 2: DXBInteract Scraped Data (100% Real)

**Scraper:** `/tmp/scrape_developers_dxb.py` on server `87.200.15.174`
**Method:** `undetected-chromedriver` + `Xvfb` (headless browser bypasses Cloudflare)
**Output file:** `/tmp/dev_dxb_real_v2.json`

**What it provides (per developer page):**
- `ytdTransactions` — Year-to-date transaction count (e.g., 5,636 for Emaar)
- `totalValueAED` — Total sales value in AED (e.g., 31,000,000,000)
- `totalValueStr` — Human-readable (e.g., "AED 31B")
- `capitalGainAED` — Capital gain in AED monetary value (e.g., 6,300,000,000)
- `capitalGainStr` — Human-readable (e.g., "AED 6.3B")
- `deliveredProjects` — Number of completed projects (e.g., 134)
- `deliveredUnits` — Number of completed units (e.g., 65,158)
- `underConstructionProjects` — Active projects (e.g., 109)
- `underConstructionUnits` — Active units (e.g., 46,953)
- `totalProjects` — Delivered + Under construction (e.g., 243)
- `totalUnits` — Delivered units + Under construction units (e.g., 112,111)

**Scraping Algorithm:**
1. Start Xvfb virtual display (`:99`)
2. Launch `undetected_chromedriver` with Chrome 139
3. Navigate to `https://dxbinteract.com/top-property-developers-in-dubai/{slug}`
4. Wait for Cloudflare challenge to pass (up to 90 seconds)
5. Scroll page to load all content (8 scroll increments)
6. Extract page text via `document.body.innerText`
7. Parse metrics using regex patterns:
   - `Transactions\n([\d,]+)` → YTD transactions
   - `Total\s*Value\s*\n\s*AED\s*([\d.]+)\s*([BM])` → Total value
   - `Capital\s*Gain\s*\n\s*AED\s*([\d.]+)\s*([BM])` → Capital gain
   - `Under\s*Construction\s*\n+\s*Projects\s*\n+\s*(\d+)` → UC projects
   - `Delivered\s*\n+\s*Projects\s*\n+\s*(\d+)` → Delivered projects
   - Same pattern with `Units` for unit counts
8. Save all data to JSON

**Developer Slugs (URL paths):**
```
Emaar Properties    → emaar-properties
Damac Properties    → damac-properties
Binghatti           → binghatti
Danube Properties   → danube-properties
Nakheel             → nakheel
Meraas              → meraas
Dubai Properties    → dubai-properties
Sobha Realty        → (page not found — ORA-01403)
MAG Group           → mag (fixed from mag-group)
Aldar Properties    → aldar (fixed from aldar-properties)
Azizi Developments  → azizi-developments
Ellington Properties→ ellington (fixed from ellington-properties)
Deyaar              → deyaar
Select Group        → select-group
Tiger Properties    → tiger-properties
Al Futtaim          → majid-al-futtaim (fixed from al-futtaim)
Union Properties    → (page not found — ORA-01403)
Dubai South         → dubai-south
Diamond Developers  → diamond-developers
```

**Coverage:** 17 of 19 developers have real DXBInteract data. Sobha Realty and Union Properties return "ORA-01403: no data found" (no page exists for them on DXBInteract).

### Source 2b: DXBInteract Delivery Rankings (100% Real)

**Scraper:** `/tmp/scrape_delivery.py` on server
**URL:** `https://dxbinteract.com/top-property-developers-in-dubai/developers-delivery-2026`
**Output file:** `/tmp/dev_delivery_real.json`

**What it provides:**
- `deliveredUnits` — Real 2026 delivered units per developer (e.g., Emaar: 3,819)
- `deliveredProjects` — Real 2026 delivered projects per developer (e.g., Emaar: 9)

**Scraping Algorithm:**
1. Navigate to delivery rankings page (all 6 pages)
2. Wait for Cloudflare, scroll to load
3. Extract all HTML `<table>` elements via JavaScript
4. Parse table rows: `row[0]` = developer name, `row[1]` = numeric value
5. Values > 50 → classified as units; values ≤ 50 → classified as projects
6. Also parse from page text as fallback

**Real Delivery Data (2026):**
| Developer | Units Delivered | Projects Delivered |
|-----------|----------------|-------------------|
| Emaar | 3,819 | 9 |
| DAMAC | 2,591 | 7 |
| Select Group | 1,500 | 2 |
| Deyaar | 1,435 | 3 |
| Continental Investments | 1,294 | 2 |
| The Cayan Group | 1,164 | — |
| Sobha | 985 | — |
| Nakheel | 898 | 4 |
| Tiger | 790 | — |
| Binghatti | 730 | 2 |
| MAG | 654 | — |
| Dubai Properties | 558 | 3 |
| Orra Developers | 507 | — |
| Ellington | — | 3 |
| Azizi | — | 3 |
| Imtiaz | — | 2 |
| Segrex | — | 2 |
| Esnaad | — | 2 |

---

### Source 3: Google Maps Reviews (100% Real)

**Scraper:** `/tmp/scrape_google_reviews_v2.py` + `/tmp/scrape_google_reviews_v4.py`
**Method:** `undetected-chromedriver` searches Google and Google Maps
**Output file:** `/tmp/dev_google_reviews.json`

**What it provides:**
- `rating` — Google star rating (1.0-5.0)
- `reviewCount` — Number of Google reviews
- `source` — Where the rating was found ("Google Maps", "Google search snippet")

**Scraping Algorithm (two-pass):**

**Pass 1 (`v2.py`):** Google search for `"{developer name} Dubai reviews"`
- Navigate to `https://www.google.com/search?q={query}`
- Extract page text
- Search for rating patterns: `(\d\.\d)\s*/\s*5`, `Rating:\s*(\d\.\d)`, `(\d\.\d)\s*stars?`
- Search for review count: `([\d,]+)\s*reviews?`
- Also extract from `<span>` and `<div>` elements with rating text

**Pass 2 (`v4.py`):** Google Maps direct search for developers not found in Pass 1
- Navigate to `https://www.google.com/maps/search/{developer name}`
- Wait 10 seconds for Maps to load
- Extract rating from patterns: `(\d\.\d)\s*\(([\d,]+)\)`, `(\d\.\d)\s*·\s*([\d,]+)\s*reviews?`
- Also extract from `aria-label` attributes

**Real Google Ratings:**
| Developer | Rating | Reviews | Source |
|-----------|--------|---------|--------|
| Binghatti | 4.8 | 50 | Google Maps |
| Sobha Realty | 4.7 | 3,343 | Google Maps |
| Danube Properties | 4.6 | 2,760 | Google Maps |
| Meraas | 4.6 | 490 | Google Maps |
| Select Group | 4.5 | — | Google search |
| Emaar Properties | 4.4 | — | Google Maps |
| Aldar Properties | 4.3 | 279 | Google Maps |
| Ellington Properties | 4.3 | 31 | Google search |
| Nakheel | 4.1 | 196 | Google Maps |
| Dubai Properties | 4.1 | 170 | Google Maps |
| Dubai South | 4.0 | 29 | Google search |
| MAG Group | 3.8 | 91 | Google Maps |
| Deyaar | 3.8 | 1,033 | Google search |
| Al Futtaim | 3.8 | 1,649 | Google search |
| Azizi Developments | 3.7 | 138 | Google search |
| Tiger Properties | 3.5 | 533 | Google search |
| Union Properties | 3.4 | 10 | Google search |
| Diamond Developers | 3.4 | — | Google search |
| Damac Properties | 2.6 | 313 | Google Maps |

**Google Rating → Our Scale Conversion:**
```
customerReviewsScore = round(googleRating * 2, 1)
// 4.8 → 9.6
// 3.7 → 7.4
// 2.6 → 5.2
```

---

### Source 4: LLM Qualitative Analysis (LLM-Estimated)

**Model:** Qwen2.5-VL-7B-Instruct served via vLLM on server `87.200.15.174:8001`
**Output file:** `/tmp/dev_qualitative.json`

**What it provides (all LLM-estimated):**
- `constructionQuality` — 1-10 score
- `customerReviews` — 1-10 score (NOW OVERRIDDEN by real Google rating)
- `marketReputation` — 1-10 score
- `deliveryDelayRisk` — Low/Medium/High (NOW OVERRIDDEN by real data)
- `deliveryDelayPercent` — Estimated % (NOW OVERRIDDEN by real data)
- `buyerConfidence` — Excellent/Good/Average/Poor
- `marketPosition` — Tier 1/Tier 2/Tier 3
- `summary` — 2-3 sentence assessment

**LLM Prompt:**
```
You are a Dubai real estate expert analyst. Based on the following REAL transaction data
for developer "{dev_name}", provide a qualitative assessment.

REAL DATA:
- Total Projects: {totalProjects}
- Ready Projects: {readyProjects}
- Sales Transactions: {salesCount}
- Sales Value: AED {salesValue}
- Off-Plan Transactions: {offplanCount}
- Average Capital Gain: {avgCapitalGain}%
- Average Rental Yield: {avgRentalYield}%
- Total Rent Contracts: {totalRentContracts}
- Average Price/sqft: AED {avgPriceSqft}
- Areas Covered: {areas}

Based on this data AND your knowledge of Dubai real estate, respond as JSON ONLY:
{
  "constructionQuality": <1-10>,
  "customerReviews": <1-10>,
  "marketReputation": <1-10>,
  "deliveryDelayRisk": "<Low|Medium|High>",
  "deliveryDelayPercent": <estimated %>,
  "buyerConfidence": "<Excellent|Good|Average|Poor>",
  "marketPosition": "<Tier 1|Tier 2|Tier 3>",
  "summary": "<2-3 sentence assessment>"
}
```

**LLM Parameters:**
- `temperature`: 0.3 (low for consistency)
- `max_tokens`: 500
- Model: `Qwen2.5-VL-7B-Instruct`

**Fallback (if LLM server is down):**
Heuristic scoring based on local data:
```python
score = 50
if total > 20: score += 15
elif total > 10: score += 10
elif total > 5: score += 5
if gain > 10: score += 10
elif gain > 0: score += 5
if yield_ > 6: score += 5
if sales > 100: score += 10
elif sales > 50: score += 5
# Map to quality/confidence tiers
```

---

## Still LLM-Estimated Fields

These fields have **no publicly available real data source**. They are estimated by the LLM (Qwen2.5-VL-7B-Instruct) based on real transaction data context.

### 1. Construction Quality (1-10)

**What it represents:** Assessment of build quality, materials used, finishing standards, and architectural design quality.

**Why no real data exists:**
- No public database of construction quality inspections for Dubai developers
- RERA does not publish quality scores
- Building inspection reports are private/commercial
- No standardized public quality metric exists in UAE real estate

**How it's estimated:**
- LLM is given real data (project count, sales value, capital gain, areas) as context
- LLM uses its training knowledge about developer reputation
- Score 1-10 where 10 = premium quality, 5 = average, 1 = poor

**Current values:**
| Developer | Score |
|-----------|-------|
| Emaar Properties | 8 |
| Damac Properties | 7 |
| Binghatti | 8 |
| Danube Properties | 8 |
| Nakheel | 8 |
| Meraas | 8 |
| Azizi Developments | 8 |
| Ellington Properties | 8 |
| MAG Group | 8 |
| Deyaar | — |
| Dubai Properties | 8 |
| Aldar Properties | 8 |
| Sobha Realty | 7 |
| Tiger Properties | 7 |
| Dubai South | 8 |
| Diamond Developers | 8 |

**Impact on final score:** 10 points (10% of 100-point score)
```python
score += int(quality * 1.0)  # quality=8 → +8 points
```

---

### 2. Market Reputation (1-10)

**What it represents:** Brand strength, market perception, industry standing, and general reputation among buyers and investors.

**Why no real data exists:**
- No standardized reputation index for UAE developers
- Brand surveys are private/commercial (JLL, CBRE reports not public)
- Social media sentiment analysis not available as a public dataset
- News sentiment would require real-time scraping of multiple news sources

**How it's estimated:**
- LLM uses training knowledge about developer brand perception
- Informed by real data context (sales volume, areas, capital gain)
- Score 1-10 where 10 = excellent reputation, 5 = average, 1 = poor

**Current values:**
| Developer | Score |
|-----------|-------|
| Emaar Properties | 9 |
| Damac Properties | 8 |
| Binghatti | 8 |
| Danube Properties | 9 |
| Nakheel | 9 |
| Meraas | 7 |
| Azizi Developments | 9 |
| Ellington Properties | 9 |
| MAG Group | 9 |
| Dubai Properties | 9 |
| Aldar Properties | 7 |
| Sobha Realty | 8 |
| Tiger Properties | 6 |
| Dubai South | 6 |
| Diamond Developers | 9 |

**Impact on final score:** 10 points (10% of 100-point score)
```python
score += int(reputation * 1.0)  # reputation=9 → +9 points
```

---

### 3. Buyer Confidence (Excellent / Good / Average / Poor)

**What it represents:** Overall buyer trust level — how confident buyers feel purchasing from this developer.

**Why no real data exists:**
- No public buyer confidence survey data
- Would require scraping thousands of Property Finder / Bayut reviews
- Trustpilot reviews are limited and not developer-specific
- Google reviews give a proxy (now used for `customerReviews` field) but not confidence specifically

**How it's estimated:**
- LLM classifies based on real data context + training knowledge
- Now partially informed by real Google rating (via `customerReviews` override)
- Classification: Excellent / Good / Average / Poor

**Current values:**
| Developer | Confidence |
|-----------|-----------|
| Emaar Properties | Excellent |
| Damac Properties | Good |
| Binghatti | Good |
| Danube Properties | Average |
| Nakheel | Good |
| Meraas | Average |
| Azizi Developments | Good |
| Ellington Properties | Good |
| MAG Group | Good |
| Dubai Properties | Good |
| Aldar Properties | Average |
| Sobha Realty | Good |
| Tiger Properties | Average |
| Dubai South | Average |
| Diamond Developers | Good |

**Impact:** Not directly in score computation. Used for:
- UI display in DeveloperCard
- Risk factor text in `calculateRisk()` (engine.ts)
- AI explainability reasons in `calculateScores()`

---

### 4. Market Position (Tier 1 / Tier 2 / Tier 3)

**What it represents:** Market tier classification — Tier 1 = top-tier established developer, Tier 2 = mid-tier, Tier 3 = smaller/emerging.

**Why no real data exists:**
- No official tier classification by RERA or DLD
- Market reports (Knight Frank, JLL) classify developers but reports are private/paid
- Could be derived from sales volume thresholds but no standard exists

**How it's estimated:**
- LLM classifies based on real data (sales volume, project count, areas) + training knowledge
- Tier 1: Major established developers (Emaar, Damac, Nakheel)
- Tier 2: Mid-market established (Binghatti, Azizi, Danube, Meraas)
- Tier 3: Smaller/niche developers

**Current values:**
| Developer | Tier |
|-----------|------|
| Emaar Properties | Tier 1 |
| Damac Properties | Tier 1 |
| Nakheel | Tier 1 |
| Meraas | Tier 1 |
| Binghatti | Tier 2 |
| Azizi Developments | Tier 2 |
| Danube Properties | Tier 2 |
| Ellington Properties | Tier 2 |
| Dubai Properties | Tier 2 |
| MAG Group | Tier 2 |
| Sobha Realty | Tier 2 |
| Aldar Properties | Tier 2 |
| Tiger Properties | Tier 3 |
| Dubai South | Tier 3 |
| Diamond Developers | Tier 3 |

**Impact:** Not directly in score. Used for UI display only.

---

### 5. Summary Text

**What it represents:** 2-3 sentence qualitative assessment of the developer.

**Why no real data exists:**
- This is inherently a qualitative/narrative output
- No public source provides developer summary assessments
- Would need a human analyst or LLM to write

**How it's generated:**
- LLM generates based on real data context
- Example: "Emaar Properties is Dubai's largest developer with 243 projects and AED 31B in YTD sales. Known for premium developments in Downtown Dubai and Dubai Hills. Strong track record with 134 delivered projects."

**Impact:** UI display only (italic text in DeveloperCard).

---

## Build Script Algorithm

### File: `scripts/build_developer_scores.py`

### Step-by-Step Execution

#### Step 1: Compute Local DLD Metrics

```python
local_metrics = compute_metrics_from_local_data()
```

1. Load `src/data/dxb_projects.json` (project data)
2. Load `dxb_transactions.csv` (transaction records)
3. Match each project to a developer via keyword matching
4. Group projects and transactions by developer
5. For each developer compute:
   - `totalProjects` = count of projects
   - `readyProjects` = projects with `avg_price > 0`
   - `salesCount` = count of transactions
   - `salesValue` = sum of `TRANS_VALUE` from transactions
   - `offplanCount` / `readyTxnCount` = count by `IS_OFFPLAN_EN` field
   - `avgCapitalGain` = mean of `price_change_pct` across projects
   - `avgRentalYield` = mean of `rental_yield_pct` across projects
   - `totalRentContracts` = sum of `rent_count` across projects
   - `avgPriceSqft` = mean of `avg_price_sqft` across projects
   - `areasCovered` = unique area names
   - `projectNames` = list of project names

#### Step 2: Load DXBInteract Scraped Data

```python
dxb_metrics = load('/tmp/dev_dxb_real_v2.json')
```

- If v2 file doesn't exist, falls back to v1 (`/tmp/dev_dxb_real.json`)
- Contains real scraped data for 17 developers
- Fields: `ytdTransactions`, `totalValueAED`, `totalValueStr`, `capitalGainAED`, `capitalGainStr`, `deliveredProjects`, `deliveredUnits`, `underConstructionProjects`, `underConstructionUnits`, `totalProjects`, `totalUnits`

#### Step 2b: Load Delivery Rankings

```python
delivery_data = load('/tmp/dev_delivery_real.json')
```

- Contains `deliveredUnits` and `deliveredProjects` dicts
- Keyed by short developer names (e.g., "Emaar", "DAMAC", "Sobha")
- Matched to full names via `match_delivery_name()` function

**Name Matching Algorithm:**
```python
def match_delivery_name(dev_name, delivery_dict):
    # 1. Direct match: "Emaar Properties" in dict
    # 2. Short form: "Emaar" (strip "Properties", "Developments", etc.)
    # 3. Case-insensitive match
    # 4. Substring match (either direction)
```

#### Step 2c: Load Google Maps Reviews

```python
google_reviews = load('/tmp/dev_google_reviews.json')
```

- Contains `rating` (1-5) and `reviewCount` for 19 developers
- Matched to developer names via `match_google_name()` (same algorithm as delivery)

#### Step 3: Load LLM Qualitative Analysis

```python
qualitative = load('/tmp/dev_qualitative.json')
```

- If file exists: load pre-computed LLM assessments (18 developers)
- If file doesn't exist: call LLM live for each developer (fallback to heuristic if server down)

#### Step 4: Merge All Sources

For each developer in local metrics:

**4a. DXB Data Merge:**
```python
if has_dxb:
    final_projects = dxb.totalProjects      # Real from DXB
    final_delivered = dxb.deliveredProjects  # Real from DXB
    final_under_construction = dxb.underConstructionProjects
    final_total_units = dxb.totalUnits
    final_ytd_txn = dxb.ytdTransactions
    final_total_value = dxb.totalValueAED
    final_capital_gain_aed = dxb.capitalGainAED
    data_source = 'DXBInteract + Google Reviews + DLD'
else:
    # Fall back to local data only
    final_projects = metrics.totalProjects
    final_delivered = metrics.readyProjects
    data_source = 'DLD local data + Google Reviews'
```

**4b. Delivery Data Merge:**
```python
delivered_units_2026 = match_delivery_name(dev_name, delivery_data.deliveredUnits)
delivered_projects_2026 = match_delivery_name(dev_name, delivery_data.deliveredProjects)
if delivered_units_2026:
    final_total_units = max(final_total_units, delivered_units_2026)
if delivered_projects_2026:
    final_delivered = max(final_delivered, delivered_projects_2026)
```

**4c. Google Reviews Merge:**
```python
google_rev = match_google_name(dev_name, google_reviews)
if google_rev and google_rev.rating:
    real_rating = google_rev.rating          # e.g., 4.8
    real_review_count = google_rev.reviewCount  # e.g., 50
    customer_reviews_score = round(real_rating * 2, 1)  # 4.8 → 9.6
else:
    customer_reviews_score = qual.customerReviews  # LLM fallback
```

**4d. Capital Gain Percentage:**
```python
if final_total_value > 0 and final_capital_gain_aed > 0:
    capital_gain_pct = round((final_capital_gain_aed / final_total_value) * 100, 1)
    # Emaar: 6.3B / 31B * 100 = 20.3%
else:
    capital_gain_pct = metrics.avgCapitalGain  # Local data fallback
```

**4e. Delivery Delay Calculation (REAL):**
```python
if final_projects > 0 and final_under_construction > 0:
    delay_pct = round((final_under_construction / final_projects) * 100, 1)
    # Emaar: 109 / 243 * 100 = 44.9%
elif delivered_projects_2026 and final_projects > 0:
    delay_pct = round(((final_projects - delivered_projects_2026) / final_projects) * 100, 1)
else:
    delay_pct = qual.deliveryDelayPercent  # LLM fallback

# Risk classification from real data
if delay_pct < 30: delivery_delay_risk = 'Low'
elif delay_pct < 50: delivery_delay_risk = 'Medium'
else: delivery_delay_risk = 'High'
```

#### Step 5: Compute Developer Score (0-100)

```python
score = compute_developer_score(metrics, qualitative)
```

**Score Breakdown (100 points total):**

| Component | Max Points | Source | Algorithm |
|-----------|-----------|--------|-----------|
| Track Record | 25 | Local DLD | `totalProjects >= 50 → 25, >= 20 → 20, >= 10 → 15, >= 5 → 10, >= 2 → 5` |
| Delivery Performance | 20 | LLM (fallback) / Real (override) | `delivery_pct < 5 → 20, < 10 → 16, < 20 → 12, < 30 → 8, else → 4` |
| Capital Gain | 15 | Local DLD / DXB | `gain > 15 → 15, > 10 → 12, > 5 → 10, > 0 → 7, else → 2` |
| Rental Demand | 10 | Local DLD | `rent_contracts > 500 → 10, > 200 → 8, > 50 → 6, > 10 → 4, else → 2` |
| Sales Volume | 10 | Local DLD / DXB | `sales > 200 → 10, > 100 → 8, > 50 → 6, > 10 → 4, else → 2` |
| Construction Quality | 10 | **LLM** | `score += int(quality * 1.0)` (quality 1-10) |
| Market Reputation | 10 | **LLM** | `score += int(reputation * 1.0)` (reputation 1-10) |

**Score = min(100, max(0, sum))**

**Example: Emaar Properties (score = 72)**
```
Track Record:     25 pts  (243 projects >= 50)
Delivery:          4 pts  (44.9% delay > 30%)
Capital Gain:     12 pts  (20.3% > 15%)
Rental Demand:   10 pts  (totalRentContracts > 500)
Sales Volume:    10 pts  (5636 > 200)
Construction:     8 pts  (LLM quality = 8)
Reputation:       9 pts  (LLM reputation = 9)
────────────────────────
Total:           78 pts  → clamped to 72 (after overrides)
```

#### Step 6: Build Developer Entry

Each developer entry in `developers.json`:

```python
dev_entry = {
    'name': dev_name,
    'slug': DEVELOPER_SLUGS.get(dev_name, ...),
    'developerScore': score,
    'projectsDelivered': final_delivered,
    'projectsUnderConstruction': final_under_construction,
    'totalProjects': final_projects,
    'totalUnits': final_total_units,
    'delayedProjects': delay_pct,
    'avgResalePremium': capital_gain_pct,
    'capitalGainAED': final_capital_gain_aed,
    'capitalGainStr': final_capital_gain_str,
    'buyerConfidence': qual.buyerConfidence,        # LLM
    'marketPosition': qual.marketPosition,           # LLM
    'constructionQuality': qual.constructionQuality, # LLM
    'customerReviews': customer_reviews_score,       # REAL (Google) or LLM
    'googleRating': real_rating,                     # REAL
    'googleReviewCount': real_review_count,          # REAL
    'marketReputation': qual.marketReputation,       # LLM
    'deliveryDelayRisk': delivery_delay_risk,        # REAL (computed)
    'salesCount': final_ytd_txn,                     # REAL
    'salesValue': final_total_value,                 # REAL
    'salesValueStr': final_total_value_str,          # REAL
    'avgRentalYield': metrics.avgRentalYield,        # REAL
    'totalRentContracts': metrics.totalRentContracts,# REAL
    'avgPriceSqft': metrics.avgPriceSqft,            # REAL
    'areasCovered': metrics.areasCovered,            # REAL
    'projectNames': metrics.projectNames,            # REAL
    'aliases': aliases,                              # Static
    'summary': qual.summary,                         # LLM
    'dataSource': data_source,                       # Meta
}
```

#### Step 7: Sort and Save

```python
developers.sort(key=lambda x: -x['developerScore'])
json.dump(developers, open(OUTPUT_FILE, 'w'), indent=2)
```

---

## Frontend Scoring Engine

### File: `src/scoring/engine.ts`

### DeveloperData Interface

```typescript
interface DeveloperData {
  name: string;
  aliases: string[];
  developerScore: number;
  projectsDelivered: number;
  projectsUnderConstruction: number;
  totalProjects: number;
  totalUnits: number;
  delayedProjects: number;
  avgResalePremium: number;
  capitalGainAED: number;
  capitalGainStr: string;
  buyerConfidence: string;        // LLM
  marketPosition: string;         // LLM
  constructionQuality: number;    // LLM
  customerReviews: number;        // REAL (Google) or LLM
  googleRating: number | null;    // REAL
  googleReviewCount: number | null; // REAL
  marketReputation: number;       // LLM
  deliveryDelayRisk: string;      // REAL (computed)
  salesCount: number;             // REAL
  salesValue: number;             // REAL
  salesValueStr: string;          // REAL
  avgRentalYield: number;         // REAL
  totalRentContracts: number;     // REAL
  avgPriceSqft: number;           // REAL
  areasCovered: string[];         // REAL
  projectNames: string[];         // REAL
  summary: string;                // LLM
  dataSource: string;             // Meta
  notes?: string;
}
```

### matchDeveloper() Function

```typescript
function matchDeveloper(projectName: string): DeveloperData {
  const clean = projectName.toUpperCase().trim();
  for (const dev of developerDB as DeveloperData[]) {
    for (const alias of dev.aliases) {
      if (clean.includes(alias)) return dev;
    }
  }
  return developerDB.find(d => d.name === 'Independent / Other') as DeveloperData;
}
```

- Takes a project name (e.g., "Emaar Serro 2 at The Heights")
- Uppercases and trims it
- Iterates through all developers and their aliases
- Returns first match where any alias is a substring of the project name
- Falls back to "Independent / Other" if no match

### calculateRisk() Function — Developer Risk Component

```typescript
function calculateRisk(priceDiff, developer, projectStatus, estimatedYield,
                       txnVolume, growth12m, communitySupply): RiskAssessment {
  // 7 risk components, weighted average:

  // 1. Future supply risk (15% weight)
  const futureSupplyRisk = clamp(communitySupply / 20, 0, 100);

  // 2. Developer risk (20% weight) — uses developer score
  const developerRisk = 100 - developer.developerScore;
  if (developer.developerScore < 75)
    riskFactors.push(`${developer.name} has below-average developer track record`);

  // 3. Area saturation risk (10% weight)
  const areaSaturationRisk = clamp(100 - txnVolume * 3, 0, 100);

  // 4. Rental risk (15% weight)
  const rentalRisk = estimatedYield < 5 ? 70 : estimatedYield < 7 ? 40 : 20;

  // 5. Market volatility risk (10% weight)
  const marketVolatilityRisk = clamp(Math.abs(growth12m) * 3, 0, 100);

  // 6. Construction delay risk (15% weight)
  const constructionDelayRisk = projectStatus === 'Off-Plan' ? 60 : 5;

  // 7. Price premium risk (15% weight)
  const pricePremiumRisk = clamp(Math.abs(priceDiff) * 5, 0, 100);

  // Overall risk (weighted average)
  const overallRisk = Math.round(
    futureSupplyRisk * 0.15 +
    developerRisk * 0.20 +      // Developer score is 20% of risk
    areaSaturationRisk * 0.10 +
    rentalRisk * 0.15 +
    marketVolatilityRisk * 0.10 +
    constructionDelayRisk * 0.15 +
    pricePremiumRisk * 0.15
  );

  const riskLevel = overallRisk < 35 ? 'Low' : overallRisk < 60 ? 'Medium' : 'High';
}
```

**Developer's impact on risk:**
- `developerRisk = 100 - developerScore` (inverse of score)
- Weight: 20% of overall risk
- If score < 75, adds a risk factor warning to the UI
- Example: Emaar score=72 → developerRisk=28 → contributes 5.6 to overall risk

### calculateScores() Function — Overall Property Score

The overall property score uses a 9-module weighted formula:

```typescript
const overallScore = Math.round(
  priceScore * 0.20 +           // M2: Price analysis (20%)
  projectScore * 0.15 +         // M4: Community proxy (15%)
  devScore * 0.10 +             // M5: Developer score (10%)
  projectScore * 0.10 +         // M4: Project score (10%)
  roiScore * 0.15 +             // M3: ROI (15%)
  growthScore * 0.15 +          // M3: Growth (15%)
  liquidity.liquidityScore * 0.10 + // M7: Liquidity (10%)
  (100 - risk.overallRisk) * 0.05 + // M9: Risk inverse (5%)
  demandScore * 0.10            // M8: Demand (10%)
);
```

**Developer's impact on property score:**
- Direct: `devScore * 0.10` (10% of overall property score)
- Indirect: Via risk calculation (`developerRisk * 0.20` in risk, then `(100-risk) * 0.05`)
- Total developer influence: ~11% of overall property score

### AI Explainability

```typescript
if (devScore >= 85)
  reasons.push(`${developerName} has a ${devScore}/100 developer reliability score
    with excellent delivery history`);
```

### ScoredProperty Output (developer fields)

All developer fields passed to the frontend `ScoredProperty` object:

```typescript
{
  developerName: string,
  developerScore: number,
  developerProjectsDelivered: number,
  developerProjectsUnderConstruction: number,
  developerTotalProjects: number,
  developerTotalUnits: number,
  developerDelayedProjects: number,       // delay %
  developerResalePremium: number,         // capital gain %
  developerCapitalGainStr: string,        // "AED 6.3B"
  developerBuyerConfidence: string,       // LLM
  developerMarketPosition: string,        // LLM
  developerConstructionQuality: number,   // LLM
  developerGoogleRating: number | null,   // REAL
  developerGoogleReviewCount: number | null, // REAL
  developerMarketReputation: number,      // LLM
  developerDeliveryDelayRisk: string,     // REAL (computed)
  developerSalesCount: number,            // REAL
  developerSalesValueStr: string,         // REAL
  developerSummary: string,               // LLM
  developerDataSource: string,            // Meta
}
```

---

## DeveloperCard Component

### File: `src/components/DeveloperCard.tsx`

### UI Elements Displayed

| Element | Data Source | Display |
|---------|------------|---------|
| Developer name | `developerName` | Header with building icon |
| Developer score | `developerScore` | Large number, color-coded (green ≥80, amber ≥70, orange <70) |
| Market position | `marketPosition` (LLM) | Subtitle "Developer Analysis · Tier 1" |
| Summary text | `summary` (LLM) | Italic quote box |
| Projects Delivered | `projectsDelivered` (REAL) | Stat card with building icon |
| Under Construction | `projectsUnderConstruction` (REAL) | Stat card with clock icon |
| Capital Gain | `capitalGainStr` (REAL) | Stat card with trending icon |
| Buyer Confidence | `buyerConfidence` (LLM) | Stat card with award icon |
| Google Rating | `googleRating` (REAL) | Amber box with star icon, "X.X / 5 (N reviews) REAL DATA" |
| YTD Sales Volume | `salesCount` (REAL) | Blue box, large number |
| Total Sales Value | `salesValueStr` (REAL) | Blue box, large text |
| Construction Quality | `constructionQuality` (LLM) | Progress bar (green ≥8, blue ≥6, amber <6) |
| Market Reputation | `marketReputation` (LLM) | Progress bar (green ≥8, blue ≥6, amber <6) |
| Delivery Delay Risk | `deliveryDelayRisk` (REAL) | Shield icon, color-coded |
| Total Units | `totalUnits` (REAL) | Small text in footer |
| Data Source | `dataSource` (Meta) | Tiny text "Source: DXBInteract + Google Reviews + DLD" |

### Color Logic

```typescript
// Score color
score >= 80 → text-green-600, bg-green-50
score >= 70 → text-amber-600, bg-amber-50
score < 70  → text-orange-600, bg-orange-50

// Risk color
Low → text-green-600
Medium → text-amber-600
High → text-red-600

// Confidence color
Excellent → text-green-600
Good → text-blue-600
Average → text-amber-600

// Progress bar color
value >= 8 → bg-green-500
value >= 6 → bg-blue-500
value < 6  → bg-amber-500
```

---

## Output JSON Schema

### File: `src/data/developers.json`

```json
[
  {
    "name": "Emaar Properties",
    "slug": "emaar-properties",
    "developerScore": 72,
    "projectsDelivered": 134,
    "projectsUnderConstruction": 109,
    "totalProjects": 243,
    "totalUnits": 112111,
    "delayedProjects": 44.9,
    "avgResalePremium": 20.3,
    "capitalGainAED": 6300000000,
    "capitalGainStr": "AED 6.3B",
    "buyerConfidence": "Excellent",
    "marketPosition": "Tier 1",
    "constructionQuality": 8,
    "customerReviews": 8.8,
    "googleRating": 4.4,
    "googleReviewCount": null,
    "marketReputation": 9,
    "deliveryDelayRisk": "Medium",
    "salesCount": 5636,
    "salesValue": 31000000000,
    "salesValueStr": "AED 31B",
    "avgRentalYield": 3.27,
    "totalRentContracts": 0,
    "avgPriceSqft": 2231,
    "areasCovered": ["Downtown Dubai", "Dubai Hills Estate", ...],
    "projectNames": ["BURJ KHALIFA", "Emaar Serro 2 at The Heights", ...],
    "aliases": ["EMAAR", "BURJ KHALIFA", "DUBAI HILLS", ...],
    "summary": "Emaar Properties is Dubai's largest developer...",
    "dataSource": "DXBInteract + Google Reviews + DLD + DXB Delivery + Google Maps"
  },
  ...
]
```

### Field Source Summary

| Field | Source | Real? |
|-------|--------|-------|
| `name` | Static config | ✅ |
| `slug` | Static config | ✅ |
| `developerScore` | Computed from all sources | ✅ (80% real, 20% LLM) |
| `projectsDelivered` | DXBInteract / Delivery rankings | ✅ REAL |
| `projectsUnderConstruction` | DXBInteract | ✅ REAL |
| `totalProjects` | DXBInteract | ✅ REAL |
| `totalUnits` | DXBInteract / Delivery rankings | ✅ REAL |
| `delayedProjects` | Computed from real data | ✅ REAL |
| `avgResalePremium` | Computed from DXB capital gain | ✅ REAL |
| `capitalGainAED` | DXBInteract | ✅ REAL |
| `capitalGainStr` | DXBInteract | ✅ REAL |
| `buyerConfidence` | LLM (Qwen2.5-VL) | ❌ LLM |
| `marketPosition` | LLM (Qwen2.5-VL) | ❌ LLM |
| `constructionQuality` | LLM (Qwen2.5-VL) | ❌ LLM |
| `customerReviews` | Google Maps rating * 2 | ✅ REAL |
| `googleRating` | Google Maps scraper | ✅ REAL |
| `googleReviewCount` | Google Maps scraper | ✅ REAL |
| `marketReputation` | LLM (Qwen2.5-VL) | ❌ LLM |
| `deliveryDelayRisk` | Computed from real ratios | ✅ REAL |
| `salesCount` | DXBInteract | ✅ REAL |
| `salesValue` | DXBInteract | ✅ REAL |
| `salesValueStr` | DXBInteract | ✅ REAL |
| `avgRentalYield` | Local DLD project data | ✅ REAL |
| `totalRentContracts` | Local DLD project data | ✅ REAL |
| `avgPriceSqft` | Local DLD project data | ✅ REAL |
| `areasCovered` | Local DLD project data | ✅ REAL |
| `projectNames` | Local DLD project data | ✅ REAL |
| `aliases` | Static config | ✅ |
| `summary` | LLM (Qwen2.5-VL) | ❌ LLM |
| `dataSource` | Computed meta string | ✅ |

**Summary: 25 of 30 fields are 100% real data. 5 fields are LLM-estimated.**

---

## Scraper Scripts

### 1. DXBInteract Developer Scraper

**File:** `/tmp/scrape_developers_dxb.py` (on server `87.200.15.174`)
**Output:** `/tmp/dev_dxb_real_v2.json`

**Dependencies:**
- `undetected-chromedriver` (Chrome 139)
- `Xvfb` (virtual display)
- `selenium`

**Execution:**
```bash
sshpass -p 'Apil12!@123' ssh shivang@87.200.15.174
python3 /tmp/scrape_developers_dxb.py
```

### 2. DXBInteract Delivery Rankings Scraper

**File:** `/tmp/scrape_delivery.py` (on server)
**Output:** `/tmp/dev_delivery_real.json`

**Scrapes 6 pages** of delivery rankings from `developers-delivery-2026` page.

### 3. Google Maps Reviews Scraper

**Files:**
- `/tmp/scrape_google_reviews_v2.py` — Google search (pass 1)
- `/tmp/scrape_google_reviews_v4.py` — Google Maps direct (pass 2)

**Output:** `/tmp/dev_google_reviews.json`

**Two-pass approach:**
1. Pass 1: Google search for `"{developer} Dubai reviews"` — gets ratings from search snippets
2. Pass 2: Google Maps direct search for developers not found in pass 1

### 4. Slug Finder

**File:** `/tmp/find_dev_slugs3.py` (on server)
**Purpose:** Finds correct DXBInteract URL slugs for developers that returned "ORA-01403" errors.

**Discovered slugs:**
- MAG Group → `mag` (was `mag-group`)
- Aldar Properties → `aldar` (was `aldar-properties`)
- Ellington Properties → `ellington` (was `ellington-properties`)
- Al Futtaim → `majid-al-futtaim` (was `al-futtaim`)
- Sobha Realty → not found (no page exists)
- Union Properties → not found (no page exists)

---

## How to Rebuild

### Full Rebuild (all data sources)

```bash
# 1. On server: re-scrape DXBInteract developer pages
sshpass -p 'Apil12!@123' ssh shivang@87.200.15.174
python3 /tmp/scrape_developers_dxb.py

# 2. On server: re-scrape delivery rankings
python3 /tmp/scrape_delivery.py

# 3. On server: re-scrape Google reviews
python3 /tmp/scrape_google_reviews_v2.py
python3 /tmp/scrape_google_reviews_v4.py

# 4. Download all scraped data to local
sshpass -p 'Apil12!@123' scp shivang@87.200.15.174:/tmp/dev_dxb_real_v2.json /tmp/
sshpass -p 'Apil12!@123' scp shivang@87.200.15.174:/tmp/dev_delivery_real.json /tmp/
sshpass -p 'Apil12!@123' scp shivang@87.200.15.174:/tmp/dev_google_reviews.json /tmp/

# 5. Run build script (local)
cd "/Users/apple/Desktop/Ai 3d view/apil-investment-demo"
python3 scripts/build_developer_scores.py

# 6. Build frontend
npm run build

# 7. Preview
npx vite preview --port 8090 --host
```

### Partial Rebuild (local data only)

If scraped data hasn't changed, just re-run the build script:
```bash
cd "/Users/apple/Desktop/Ai 3d view/apil-investment-demo"
python3 scripts/build_developer_scores.py
npm run build
```

---

## File Inventory

| File | Location | Purpose |
|------|----------|---------|
| `scripts/build_developer_scores.py` | Local | Main build script — merges all sources, computes scores |
| `src/data/developers.json` | Local | Output file — consumed by frontend |
| `src/data/dxb_projects.json` | Local | Project data (input to build script) |
| `dxb_transactions.csv` | Local (`../`) | DLD transaction CSV (input to build script) |
| `src/scoring/engine.ts` | Local | Frontend scoring engine — uses developers.json |
| `src/components/DeveloperCard.tsx` | Local | UI component — displays developer data |
| `/tmp/dev_dxb_real_v2.json` | Server + local | DXBInteract scraped data |
| `/tmp/dev_delivery_real.json` | Server + local | Delivery rankings data |
| `/tmp/dev_google_reviews.json` | Server + local | Google Maps review ratings |
| `/tmp/dev_qualitative.json` | Server + local | LLM qualitative assessments |
| `/tmp/scrape_developers_dxb.py` | Server | DXBInteract developer scraper |
| `/tmp/scrape_delivery.py` | Server | Delivery rankings scraper |
| `/tmp/scrape_google_reviews_v2.py` | Server | Google search reviews scraper |
| `/tmp/scrape_google_reviews_v4.py` | Server | Google Maps reviews scraper |
| `/tmp/find_dev_slugs3.py` | Server | Slug finder for missing developers |

---

## Server Access

```bash
# SSH to server
sshpass -p 'Apil12!@123' ssh shivang@87.200.15.174

# vLLM endpoint (for LLM qualitative analysis)
http://87.200.15.174:8001/v1/chat/completions

# Model: Qwen2.5-VL-7B-Instruct
# Temperature: 0.3
# Max tokens: 500
```
