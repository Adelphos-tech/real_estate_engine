# APIL Investment Pipeline — Forensic Audit

## Objective

A complete forensic audit of the APIL investment analysis pipeline to identify every place where deterministic data becomes inconsistent before reaching the final report. No fixes applied — understanding first.

---

# Deliverable 1: Architecture Diagram

```
User Questionnaire (9 questions)
    ↓ sessionStorage('investorProfile')
    ↓
Analyzing Page
    ↓ POST /recommendations {goal, budget, property_type, bedrooms, location, ready_offplan, timeline, financing, risk}
    ↓
apil_server.py :: get_recommendations()
    ↓ builds profile dict from body
    ↓
recommendation_engine.py :: generate_recommendations(profile)
    ↓
    ├─ Load cached JSON: ready_property_scores.json, offplan_scores.json
    ├─ _normalize_recommendation() — normalizes CAUTION→WATCHLIST, adds split confidence
    ├─ filter_ready_properties() / filter_offplan_properties() — hard filters
    ├─ sort_by_goal() — goal-specific sorting
    ├─ build_investor_strategy() — strategy weights, thresholds, exit pref
    ├─ calculate_investor_fit() — 7-dimension fit score per property
    ├─ Re-sort by blended: investment_score * 0.6 + fit_score * 0.4
    ├─ recommendation_from_score() — deterministic recommendation for top pick
    ├─ Fit score gates: fit<40 → downgrade to REVIEW, fit<55 → downgrade
    ├─ batch_apply_rules() — rules engine on all recs (DEFAULT goal="balanced"!)
    ├─ build_report_contract() — report rules engine for top pick
    ├─ validate_report() — pre-render validation
    ├─ explain_score(top_prop, profile) — LLM advisory
    └─ generate_advisory_report(top_prop, profile) — LLM full report
    ↓
API Response JSON:
    {
      profile, investorStrategy, recommendations[], topReady[], topOffplan[],
      recommendationConfidence, reportContract, reportValidation
    }
    ↓
Frontend Report.tsx
    ↓ sessionStorage('apiRecommendations') or fresh fetch
    ↓
    ├─ topRec = recommendations[0]
    ├─ mapReadyToLegacy(topRec) → topProperty (legacy shape)
    ├─ buildReportContext(topRec, profile.goal, reportContract)
    ├─ getApplicableSections(ctx) — filters by reportContract.visible_sections
    └─ Renders sections: summary, returns, valuation, risk, market, exit, evidence, advisor
       ↓
       LLMAdvisorySection:
         ├─ If topRec.llmAdvisoryReport exists → use it (from /recommendations)
         └─ Else fetch /properties/{type}/{id}/advisory
              ↓ apil_server.py advisory endpoint
              ↓ profile = {"goal": "balanced", "risk": "medium"} ← HARDCODED
              ↓ explain_score, detect_contradictions, negotiation_strategy, exit_strategy, generate_advisory_report
              ↓ Returns advisory object
```

**Key observation**: There are TWO code paths for LLM advisory. The `/recommendations` path passes the real investor profile. The `/advisory` endpoint hardcodes `{"goal": "balanced", "risk": "medium"}`.

---

# Deliverable 2: Source-of-Truth Table

| Field | Source | Who calculates | Who modifies | Can AI overwrite? | Should AI overwrite? |
|---|---|---|---|---|---|
| Goal | User questionnaire | User | Nobody | No | No |
| Budget | User questionnaire | User | Nobody (relaxation expands search, not budget field) | No | No |
| Timeline | User questionnaire | User | Nobody | No | No |
| Property Type | User questionnaire | User | Nobody | No | No |
| Investment Score (ready) | ready_engine.py | `compute_ready_property_score()` | recommendation_engine (blended sort) | No | No |
| Investment Score (offplan) | offplan_engine_v2.py | `score_offplan_property()` | recommendation_engine (blended sort) | No | No |
| Investor Fit Score | investor_fit_engine.py | `calculate_investor_fit()` | recommendation_engine (gates recommendation) | No | No |
| Confidence Score (ready) | ready_engine.py | Inline calculation (comparables_coverage, rental_coverage, etc.) | _normalize_recommendation (adds split confidence if missing) | No | No |
| Confidence Score (offplan) | offplan_engine_v2.py | Inline (has_developer, has_community, has_fair_value, has_rent weighted) | Nobody | No | No |
| Recommendation (ready) | utils.py | `recommendation_from_score(score, confidence, goal)` | rules_engine.py (downgrades), recommendation_engine (fit gates) | No | No |
| Recommendation (offplan) | offplan_engine_v2.py | Inline `offplan_recommendation()` based on price diff | rules_engine.py (downgrades), recommendation_engine (fit gates) | No | No |
| Fair Value (ready) | market_valuation.py | `calculate_fair_value()` — called by ready_engine (but NOT in current code!) | Nobody | No | No |
| Fair Value (offplan) | offplan_engine_v2.py | `calculate_fair_value()` — inline | Nobody | No | No |
| Price vs Market (ready) | ready_engine.py | `price_diff = ((asking - comparable) / comparable) * 100` | Nobody | No | No |
| Price vs Market (offplan) | offplan_engine_v2.py | `price_diff_pct = ((developer_price - fair_value) / fair_value) * 100` | Nobody | No | No |
| Growth % | ready_engine.py | `calculate_growth_with_metadata()` from sales_history | Nobody | No | No |
| Rental Yield | ready_engine.py | `estimated_yield = (estimated_rent / asking_price) * 100` | Nobody | No | No |
| Net ROI (ready) | ready_engine.py | `calculate_roi()` | Nobody | No | No |
| Net ROI (offplan) | offplan_engine_v2.py | `calculate_post_handover_roi()` | Nobody | No | No |
| Developer Score | developer_engine.py | Pre-computed in developer_scores.json | offplan_engine_v2 re-calculates from breakdown | No | No |
| Risk Level | ready_engine.py / offplan_engine_v2.py | Inline: `"Low" if overall_risk <= 25 else "Medium" if overall_risk <= 50 else "High"` | _normalize_recommendation (re-normalizes) | No | No |
| Holding Period | User questionnaire | User | LLM fallback invents "3-5 years" | YES (fallback) | **NO** |
| Exit Strategy | investor_strategy_engine.py | `EXIT_PREFERENCES[goal]` + holding period override | LLM (fallback invents), offplan_engine_v2 (recommends based on equity_gain/roi) | YES (fallback) | **NO** |
| Negotiation Tips | llm_engine.py | LLM `negotiation_strategy()` | LLM | Yes | Yes (advisory) |
| Executive Summary | llm_engine.py | LLM `generate_advisory_report()` | LLM | Yes | Yes (narrative only) |
| Score Breakdown | ready_engine.py / offplan_engine_v2.py | Inline in score output | Nobody | No | No |
| Lost Points | ready_engine.py | Inline during scoring | Nobody | No | No |
| Rule Flags | rules_engine.py | `apply_rules()` | Nobody | No | No |
| Comparable Sales Count | ready_engine.py | `len(sales_history)` | Nobody | No | No |
| Rental Evidence Count | ready_engine.py | `len(rent_history)` | Nobody | No | No |
| Data Quality (offplan) | **MISSING** | offplan_engine_v2.py does NOT set `dataQuality` field | N/A | No | No |

---

# Deliverable 3: Duplicate Calculation Report

## 3.1 Confidence Score — 5 implementations

| File | Function | Formula |
|---|---|---|
| `confidence_engine.py` | `calculate_confidence()` | Weighted: sales*0.25 + rental*0.20 + dev*0.20 + proj*0.15 + comm*0.20 |
| `ready_engine.py` | Inline (line ~448) | `comparables_coverage * 0.5 + community_coverage * 0.3 + developer_coverage * 0.2` |
| `offplan_engine_v2.py` | Inline (line ~882) | `dev*0.30 + area*0.25 + pricing*0.25 + rental*0.20` |
| `report_rules_engine.py` | `confidence_from_sales()`, `confidence_from_rentals()`, `confidence_from_growth()`, `confidence_from_pricing()` | Separate per-dimension confidence |
| `_normalize_recommendation()` | Inline (line ~226) | Reconstructs pricing/rental confidence from sales/rent counts |

**VERDICT**: 5 different confidence calculations. The `confidence_engine.py` module exists but is **never called** by ready_engine or offplan_engine_v2. Each engine rolls its own.

## 3.2 Recommendation — 3 implementations

| File | Function | Logic |
|---|---|---|
| `utils.py` | `recommendation_from_score()` | Goal-aware: score + confidence thresholds per goal |
| `offplan_engine_v2.py` | `offplan_recommendation()` (line ~565) | Price-diff based: >15%→AVOID, >10%→HOLD, >5%→NEGOTIATE, ≤-5%+score≥70→STRONG BUY |
| `recommendation_engine.py` | Inline (line ~500) | `recommendation_from_score()` + fit score gating |

**VERDICT**: Off-plan uses a completely different recommendation logic than ready. The `utils.py` function is goal-aware; the offplan function is price-diff only. The offplan recommendation vocabulary includes `NEGOTIATE` and `AVOID` which are NOT in `ALLOWED_RECOMMENDATIONS` in report_rules_engine.

## 3.3 Risk Level — 3 implementations

| File | Threshold |
|---|---|
| `ready_engine.py` / `offplan_engine_v2.py` | `≤25 Low, ≤50 Medium, >50 High` |
| `utils.py` `risk_from_score()` | `≥80 Low, ≥65 Medium, <65 High` |
| `community_engine.py` / `project_engine.py` | Uses `risk_from_score()` — different thresholds |

**VERDICT**: Community/project risk levels use different thresholds than property risk levels. A community can be "High" risk at score 64 while a property is "Medium" at overall_risk 50.

## 3.4 Fair Value — 2 implementations

| File | Function |
|---|---|
| `market_valuation.py` | `calculate_fair_value()` — 40% community + 30% project + 20% building + 10% comparable |
| `offplan_engine_v2.py` | `calculate_fair_value()` — community median × location factor × project premium |

**VERDICT**: Completely different formulas. `market_valuation.py` is imported by ready_engine but **never called** in the current ready_engine code. The `marketValuation` field in `ready_property_scores.json` was computed by a previous version of the code that has since been removed.

## 3.5 Split Confidence — 2 implementations

| File | Location |
|---|---|
| `ready_engine.py` | Inline: `pricingConfidence = clamp(comparables_coverage * 0.5 + community_coverage * 0.3 + developer_coverage * 0.2)` |
| `_normalize_recommendation()` | Inline: reconstructs from sales/rent counts with different thresholds |

**VERDICT**: If the ready_engine runs, it sets split confidence one way. If the data is cached and _normalize_recommendation runs, it may overwrite with different values.

---

# Deliverable 4: Hardcoded Values & Fallback Text

## 4.1 Hardcoded Profile in Advisory Endpoints

```python
# apil_server.py line 207, 250
profile = {"goal": "balanced", "risk": "medium"}
```

**IMPACT**: When the frontend calls `/properties/ready/{id}/advisory` or `/properties/offplan/{slug}/advisory`, the LLM receives `goal=balanced` regardless of the user's actual goal. The LLM then generates an advisory report for a "balanced" investor even if the user selected "Capital Growth" or "Rental Income".

## 4.2 LLM Fallback Text

```python
# llm_engine.py line 908
"exit_plan": "Hold 3-5 years depending on market conditions",
```
**IMPACT**: When LLM is unavailable, exit plan always says "3-5 years" regardless of user's timeline (could be "1-2y" or "5y+").

```python
# llm_engine.py line 722-726
if goal == "rental_income":
    timeline = "Hold 5-7 years for rental yield accumulation"
elif goal == "capital_growth":
    timeline = "Hold 3-5 years then sell at peak appreciation"
else:
    timeline = "Hold 5 years, monitor market conditions"
```
**IMPACT**: Fallback exit strategy invents holding periods not derived from user's timeline input.

## 4.3 Off-plan Default Growth Rate

```python
# offplan_engine_v2.py line ~215
if growth_rate == 0:
    growth_rate = 0.05  # Default assumption: 5% if no data
```
**IMPACT**: When no growth data exists, off-plan future appreciation is calculated using a fabricated 5% growth rate. The report then shows projected values as if they're data-driven.

## 4.4 Off-plan Exit Strategy Hardcoded Growth

```python
# offplan_engine_v2.py line ~680
growth_rate = 0.05  # Strategy D: Hold 5 years
value_5yr = future_value * (1 + growth_rate) ** 5
```
**IMPACT**: The "Hold 5 Years" exit strategy always uses 5% growth, ignoring actual market data.

## 4.5 Deprecated Recommendation Vocabulary in Cached Data

```
ready_property_scores.json: 1363 properties with "CAUTION" (not in ALLOWED_RECOMMENDATIONS)
offplan_scores.json: 195 properties with "NEGOTIATE" (not in ALLOWED_RECOMMENDATIONS)
```
**IMPACT**: `_normalize_recommendation()` converts CAUTION→WATCHLIST at runtime, but the cached JSON still contains the old values. If any code reads the JSON directly (e.g., advisory endpoint), it gets the old vocabulary.

## 4.6 Off-plan Missing dataQuality

```
offplan_scores.json: 0/3420 properties have dataQuality field
```
**IMPACT**: The frontend's `ReportContext.buildReportContext()` reads `topRec.dataQuality` to determine `hasRentalEvidence` and `hasComparableSales`. For off-plan properties, `dataQuality` is `null`, so both flags default to `false`. This means the ReportContext thinks there's no rental evidence even when `postHandoverROI.hasRentData` is `true`.

## 4.7 Rules Engine Default Goal

```python
# apil_server.py line 163-165
recs["recommendations"] = batch_apply_rules(recs["recommendations"])
# batch_apply_rules uses goal="balanced" by default
```
**IMPACT**: `rules_engine.apply_rules()` checks Rule 3 (no rental + rental goal → downgrade). But `batch_apply_rules` is called without the user's goal, so it defaults to "balanced". Rule 3 never fires for rental investors in the batch path. It only fires if `apply_rules` is called individually with the correct goal (which happens in the advisory endpoint — but that uses hardcoded "balanced" too).

---

# Deliverable 5: Prompt Audit

## 5.1 Prompt: `generate_advisory_report()`

**System prompt** (`REPORT_SYSTEM`): 26 rules. Comprehensive. Includes:
- Goal constraint injection
- Price vs market rules
- Forbidden words list
- Confidence-based precision rules
- Rental evidence rules

**User prompt**: Injects all metrics + goal constraint + profile.

**Issues found**:

1. **Goal injection works correctly** — the `goal_constraint` block is well-constructed and includes the deterministic recommendation.

2. **Missing data not marked as NULL** — The prompt sends `roi.get('netROI', 'N/A')` but when the LLM sees "N/A", it may still reference it. The prompt says "If data is insufficient, say 'insufficient data'" but doesn't explicitly mark which fields are N/A due to missing data vs. genuinely not applicable.

3. **Off-plan dataQuality is null** — The prompt includes `sales_count` from `dataQuality.salesCount`, but for off-plan this is always `'N/A'`. The LLM may interpret this as "no sales evidence" when it actually means "field not populated".

4. **Fair value injection** — For ready properties, `fair_value` is not injected at all (only off-plan). The ready property prompt doesn't mention fair value, yet the frontend ValuationSection reads `marketValuation` from the property data. The LLM and the frontend are looking at different data.

5. **Rule flags human** — `flags_human` is injected, but `rulesFlagsHuman` is never populated in the cached data (0/3575 properties have it). The prompt receives an empty list.

## 5.2 Prompt: `explain_score()`

**Issues**:

1. **No goal constraint** — Unlike `generate_advisory_report()`, the explain_score prompt does NOT include a goal constraint block. The LLM may discuss rental yield for a capital growth investor.

2. **No price vs market rule** — The explain_score prompt doesn't include the critical rule about overpriced vs. discounted properties.

## 5.3 Prompt: `exit_strategy()`

**Issues**:

1. **Fallback invents timeline** — When LLM fails, the fallback hardcodes "3-5 years" or "5-7 years" regardless of user's actual timeline input.

2. **LLM prompt asks for timeline** — The prompt asks the LLM to suggest a hold period. This is a deterministic value (user already specified it). The LLM should not be generating holding periods.

## 5.4 Prompt: `detect_contradictions()`

**Issues**:

1. **LLM-based contradiction detection** — This should be deterministic, not LLM-based. The LLM may miss contradictions or invent false ones. The fallback does have simple deterministic checks, but they're minimal.

## 5.5 Advisory Endpoint Profile Loss

**CRITICAL**: The `/properties/ready/{id}/advisory` and `/properties/offplan/{slug}/advisory` endpoints hardcode `profile = {"goal": "balanced", "risk": "medium"}`. This means:

- LLM receives wrong goal → may discuss rental income for a capital growth investor
- Rules engine receives wrong goal → Rule 3 (no rental + rental goal) never fires
- Exit strategy receives wrong goal → may recommend "hold and rent" for a flip investor

**When does this path activate?**: When `topRec.llmAdvisoryReport` is NOT present (line 59-66 of LLMAdvisorySection.tsx). The `/recommendations` endpoint does attach `llmAdvisoryReport` to the top pick, so this path only activates for non-top recommendations or when the LLM was unavailable during the `/recommendations` call.

---

# Deliverable 6: AI Responsibilities Audit

| Responsibility | Deterministic | AI | Issue |
|---|---|---|---|
| Investment Score | ✅ | ❌ | OK |
| Developer Score | ✅ | ❌ | OK |
| Confidence Score | ✅ | ❌ | OK |
| Recommendation | ✅ | ❌ | OK |
| Investor Goal | ✅ | ❌ | OK |
| Budget | ✅ | ❌ | OK |
| Growth % | ✅ | ❌ | OK |
| Fair Value | ✅ | ❌ | OK |
| Price vs Market | ✅ | ❌ | OK |
| Holding Period | ✅ (user input) | ⚠️ (fallback invents) | **VIOLATION** |
| Exit Strategy | ✅ (deterministic) | ⚠️ (fallback invents) | **VIOLATION** |
| Negotiation Tips | ❌ | ✅ | OK |
| Executive Summary | ❌ | ✅ | OK (narrative) |
| Thesis | ❌ | ✅ | OK (narrative) |
| Contradiction Detection | Should be ✅ | ⚠️ (LLM-based) | **SHOULD BE DETERMINISTIC** |
| Projected Value at Handover | ✅ | ❌ | OK, but uses hardcoded 5% growth fallback |

---

# Deliverable 7: DTO Consistency Audit

## 7.1 Ready vs Off-plan Schema Differences

| Field | Ready | Off-plan | Issue |
|---|---|---|---|
| `dataQuality` | ✅ Populated | ❌ **NULL** | Frontend ReportContext breaks for off-plan |
| `marketValuation` | ✅ Populated (by old code) | ❌ Not present | Different fair value fields |
| `fairValue` | ❌ Not present | ✅ Populated | Different fair value fields |
| `priceOpportunity` | ❌ Not present | ✅ Populated | Different price diff fields |
| `priceDifference` | ✅ Populated | ❌ Not present | Different price diff fields |
| `comparablePrice` | ✅ Populated | ❌ Not present | Different comp fields |
| `scoreBreakdown` | ✅ {price, roi, liquidity, community, developer, project} | ✅ {developer, price, paymentPlan, growth, supplyRisk, liquidity, roi} | Different keys, different labels |
| `rulesFlagsHuman` | ❌ **Empty** | ❌ **Not present** | Human-readable flags never populated |
| `lostPoints` | ✅ Populated | ❌ **Not present** | Off-plan has no lost points |
| `rentRange` | ✅ Populated | ❌ Not present | Off-plan has no rent range |
| `pricingConfidence` | ✅ (if _normalize adds it) | ❌ Not present | Off-plan has no split confidence |
| `rentalConfidence` | ✅ (if _normalize adds it) | ❌ Not present | Off-plan has no split confidence |

**IMPACT**: The frontend must handle two completely different DTO shapes. `ReportContext.buildReportContext()` reads `topRec.dataQuality` — which is null for off-plan. This means `hasRentalEvidence` and `hasComparableSales` are always `false` for off-plan properties, even when rental data exists in `postHandoverROI.hasRentData`.

## 7.2 Legacy Mapping Loss

`mapReadyToLegacy()` in `loader.ts` maps API fields to legacy UI shape. It drops:
- `scoreBreakdown` (not mapped)
- `lostPoints` (not mapped)
- `dataQuality` (not mapped)
- `pricingConfidence` / `rentalConfidence` (not mapped)
- `rulesFlags` / `rulesFlagsHuman` (not mapped)
- `marketValuation` (not mapped)
- `rentRange` (not mapped)
- `confidenceBreakdown` (not mapped)

**However**: The report sections receive `topRec` directly (not the mapped `topProperty`), so most sections have access to the full DTO. The `property` prop is the legacy-mapped version.

## 7.3 Recommendation Override Chain

A single property's recommendation can be overridden in **4 places**:

1. **Engine**: `recommendation_from_score()` or `offplan_recommendation()` — initial value
2. **_normalize_recommendation()**: Converts CAUTION→WATCHLIST
3. **batch_apply_rules()**: Downgrades based on rules (but uses default goal="balanced")
4. **recommendation_engine inline**: Fit score gates (fit<40 → REVIEW, fit<55 → downgrade)

**IMPACT**: The final recommendation depends on the order of these overrides. If rules engine runs with wrong goal, it may not downgrade when it should. If fit gates run after rules, they may re-downgrade a property that rules already downgraded.

---

# Deliverable 8: End-to-End Trace — One Report

**Scenario**: User selects Goal=Capital Growth, Budget=2M-5M, Property Type=Apartment, Bedrooms=2, Timeline=3-5y

| Stage | Field | Value | Notes |
|---|---|---|---|
| User Input | goal | "capital_growth" | Stored in sessionStorage |
| User Input | budget | "2m-5m" | |
| API Request | profile.goal | "capital_growth" | Sent to /recommendations |
| recommendation_engine | filter_ready_properties | Filters by type, beds, budget | OK |
| recommendation_engine | sort_by_goal | Sorts by `futureAppreciation.potentialGainPct` or `growth12m` | OK for capital_growth |
| recommendation_engine | build_investor_strategy | `exit_strategy = "sell_handover"` | Correct for capital_growth |
| recommendation_engine | calculate_investor_fit | 7-dimension fit score | OK |
| recommendation_engine | blended sort | `score * 0.6 + fit * 0.4` | OK |
| recommendation_engine | recommendation_from_score | Uses goal="capital_growth" thresholds | OK |
| recommendation_engine | fit gates | May downgrade | OK |
| **batch_apply_rules** | **apply_rules(prop, goal="balanced")** | **WRONG — uses "balanced" not "capital_growth"** | **Rule 3 won't fire for rental, but more importantly, the rules don't have goal-specific logic except Rule 3** |
| recommendation_engine | build_report_contract | Uses profile goal | OK |
| recommendation_engine | generate_advisory_report | Uses profile goal | OK — LLM gets correct goal |
| API Response | topRec.recommendation | e.g., "BUY" | |
| API Response | topRec.llmAdvisoryReport | LLM narrative | Goal-aware |
| Frontend | buildReportContext | Reads profile.goal from sessionStorage | OK |
| Frontend | getApplicableSections | Filters by reportContract.visible_sections | OK |
| **Frontend** | **LLMAdvisorySection** | **If topRec.llmAdvisoryReport exists → OK. If not → fetches /advisory with hardcoded goal="balanced"** | **PROFILE LOST** |
| Frontend | ExitStrategySection | Reads ctx.investorGoal | OK (uses ctx, not LLM) |
| Frontend | ValuationSection | Reads topRec.marketValuation or topRec.fairValue | Depends on property type |
| Frontend | EvidenceSection | Reads topRec.dataQuality | **BREAKS for off-plan (null)** |

---

# Deliverable 9: Contradiction Rule Set

## Identified Contradictions in Current System

| # | Rule | Current Status | Root Cause |
|---|---|---|---|
| C1 | If Goal == Capital Growth, AI cannot mention Rental Income strategy | **PARTIALLY ENFORCED** | LLM prompt has goal constraint, but advisory endpoint hardcodes "balanced" |
| C2 | If Budget < Property Price, Recommendation cannot be Buy | **NOT ENFORCED** | Budget filter exists but relaxation can expand budget by 80%. No post-relaxation check. |
| C3 | If Fair Value == null, AI cannot reference Fair Value | **NOT ENFORCED** | LLM prompt says "do not invent" but doesn't explicitly tell LLM when fair value is null |
| C4 | If Comparable Sales == 0, AI cannot claim historical sales evidence | **PARTIALLY ENFORCED** | LLM prompt includes sales count, but off-plan has null dataQuality so sales_count = 'N/A' |
| C5 | If Rental Evidence == 0, AI cannot discuss rental confidence | **PARTIALLY ENFORCED** | LLM prompt has Rule 25, but off-plan dataQuality is null so rent_count is unknown |
| C6 | If Recommendation == REVIEW, AI cannot recommend BUY | **ENFORCED** in prompt | LLM prompt includes deterministic rec and says "never contradict" |
| C7 | If Confidence < 70, AI cannot say High Confidence | **PARTIALLY ENFORCED** | LLM prompt Rule 24 says use ranges, but confidence label is not explicitly injected |
| C8 | Price >20% above market cannot be "attractive" | **ENFORCED** in prompt | Rule 21 in REPORT_SYSTEM |
| C9 | Timeline = undecided → AI cannot say "3-5 years" | **NOT ENFORCED** | LLM fallback hardcodes "3-5 years" |
| C10 | Off-plan with no rental evidence → cannot recommend "Rent after handover" | **NOT ENFORCED in engine** | `calculate_exit_strategies()` always includes "rent_hold" option regardless of rental data |
| C11 | Off-plan NEGOTIATE recommendation not in allowed vocabulary | **NOT ENFORCED** | `_normalize_recommendation()` doesn't convert NEGOTIATE |
| C12 | Off-plan AVOID recommendation not in allowed vocabulary for ready | **INCONSISTENT** | AVOID is in ALLOWED_RECOMMENDATIONS but ready_engine never produces it |
| C13 | rulesFlagsHuman never populated | **BUG** | ready_engine doesn't call apply_rules, so rulesFlagsHuman is never set. Only set at runtime in /recommendations |
| C14 | Off-plan properties have no lostPoints | **MISSING DATA** | offplan_engine_v2 doesn't generate lostPoints |
| C15 | Off-plan properties have no split confidence | **MISSING DATA** | offplan_engine_v2 doesn't generate pricingConfidence/rentalConfidence |

---

# Deliverable 10: Architecture Recommendations

## Root Cause Analysis

The contradictions continue appearing because of **5 architectural issues**, not individual bugs:

### Issue 1: Two Different DTO Schemas (Critical)

Ready and off-plan properties have completely different field names, different score breakdown keys, different confidence calculations, and different recommendation logic. The frontend must handle both shapes, leading to missing data and broken conditionals.

**Fix**: Unify the DTO. Both ready and off-plan should produce the same output schema with the same field names. Missing fields should be explicitly `null`, not absent.

### Issue 2: Advisory Endpoint Loses Investor Profile (Critical)

The `/advisory` endpoints hardcode `goal="balanced"`. When the frontend falls back to these endpoints (non-top recommendations, or when LLM was unavailable during /recommendations), the LLM generates advice for the wrong investor profile.

**Fix**: Pass the investor profile from the frontend to the advisory endpoint, or always attach LLM advisory to all recommendations in the `/recommendations` response.

### Issue 3: Rules Engine Runs Without Goal (High)

`batch_apply_rules()` is called without the user's goal, defaulting to "balanced". This means goal-specific rules (like Rule 3: no rental + rental goal → downgrade) never fire in the main pipeline.

**Fix**: Pass `profile["goal"]` to `batch_apply_rules()`.

### Issue 4: Confidence Calculated Differently Everywhere (High)

5 different confidence implementations produce different scores for the same data. The `confidence_engine.py` module exists but is never used. Ready and off-plan engines have different formulas.

**Fix**: Use `confidence_engine.py` as the single source. Both engines should call it. Remove inline confidence calculations.

### Issue 5: Cached Data is Stale and Inconsistent (Medium)

`ready_property_scores.json` contains `marketValuation` computed by old code that no longer exists. It contains `CAUTION` recommendations that are normalized at runtime. `rulesFlagsHuman` is empty because rules are applied at runtime, not at scoring time. Off-plan data lacks `dataQuality`, `lostPoints`, and split confidence.

**Fix**: Re-run both scoring engines to regenerate cached JSON. Apply rules during scoring, not at runtime. Add missing fields to off-plan engine output.

---

# Pipeline Risk Report

## High-Risk Files

| File | Risk | Reason |
|---|---|---|
| `apil_server.py` | **CRITICAL** | Hardcodes profile for advisory endpoints (lines 207, 250) |
| `recommendation_engine.py` | **CRITICAL** | Calls batch_apply_rules without goal (line 163) |
| `offplan_engine_v2.py` | **HIGH** | Missing dataQuality, lostPoints, split confidence; uses different recommendation logic; hardcoded 5% growth fallback |
| `llm_engine.py` | **HIGH** | Fallback text invents holding periods; explain_score lacks goal constraint; contradiction detection is LLM-based |
| `ready_engine.py` | **HIGH** | marketValuation field exists in output but calculation code is missing (was removed); confidence calculated inline instead of using confidence_engine |

## Medium-Risk Files

| File | Risk | Reason |
|---|---|---|
| `rules_engine.py` | **MEDIUM** | Rule 2 comment says "Max CAUTION" but code downgrades to WATCHLIST; Rule 3 depends on goal which is often wrong |
| `report_rules_engine.py` | **MEDIUM** | Has comprehensive validation rules but they're only checked, not enforced — validation results are returned but not acted upon |
| `ReportContext.ts` | **MEDIUM** | Reads dataQuality which is null for off-plan; hasRentalEvidence and hasComparableSales are wrong for off-plan |
| `LLMAdvisorySection.tsx` | **MEDIUM** | Falls back to advisory endpoint which loses investor profile |

## Low-Risk Files

| File | Risk | Reason |
|---|---|---|
| `investor_strategy_engine.py` | **LOW** | Clean, deterministic, well-structured |
| `investor_fit_engine.py` | **LOW** | Clean, deterministic |
| `confidence_engine.py` | **LOW** | Correct but unused |
| `market_valuation.py` | **LOW** | Correct but unused (ready_engine doesn't call it) |

---

# Recommended Refactor Order

Ranked by impact (highest first):

1. **Fix advisory endpoint profile** — Pass real investor profile to `/advisory` endpoints. This is a 2-line fix in `apil_server.py` with massive impact on LLM output consistency.

2. **Fix batch_apply_rules goal** — Pass `profile["goal"]` to `batch_apply_rules()`. Another 1-line fix that makes Rule 3 actually work.

3. **Add dataQuality to off-plan engine** — offplan_engine_v2.py should populate `dataQuality` with `hasComparables`, `hasRentData`, `salesCount`, `rentCount`. This fixes ReportContext for off-plan.

4. **Unify recommendation vocabulary** — Add `NEGOTIATE` to `_normalize_recommendation()` (convert to `BUY IF NEGOTIATED`). Ensure all engines only produce values from `ALLOWED_RECOMMENDATIONS`.

5. **Use confidence_engine.py everywhere** — Replace inline confidence calculations in ready_engine and offplan_engine_v2 with calls to `confidence_engine.calculate_confidence()`.

6. **Add lostPoints and split confidence to off-plan** — offplan_engine_v2 should generate `lostPoints`, `pricingConfidence`, `rentalConfidence` like ready_engine does.

7. **Fix off-plan exit strategy rental check** — `calculate_exit_strategies()` should only include "rent_hold" if `post_handover_roi.hasRentData` is true.

8. **Remove LLM fallback invented timelines** — Replace hardcoded "3-5 years" fallback with deterministic value from investor profile.

9. **Make contradiction detection deterministic** — Replace LLM-based `detect_contradictions()` with rule-based checks in `report_rules_engine.py`.

10. **Re-run scoring engines** — Regenerate cached JSON with all fixes applied. This eliminates stale `CAUTION` values, empty `rulesFlagsHuman`, and missing fields.

11. **Unify DTO schema** — Make ready and off-plan produce identical field names for score breakdown, fair value, price difference, and confidence.

12. **Apply rules during scoring, not at runtime** — Move `apply_rules()` call into `ready_engine.run()` and `offplan_engine_v2.run()` so cached JSON includes rules flags.

---

# Implementation Plan (Post-Audit)

**Phase 1 — Quick Wins (1-2 hours)**
- Fix `apil_server.py`: Accept profile as query param in advisory endpoints
- Fix `recommendation_engine.py`: Pass goal to `batch_apply_rules()`
- Fix `offplan_engine_v2.py`: Add `dataQuality` field to output
- Fix `_normalize_recommendation()`: Convert `NEGOTIATE` → `BUY IF NEGOTIATED`

**Phase 2 — Consistency (3-4 hours)**
- Add `lostPoints`, `pricingConfidence`, `rentalConfidence` to off-plan output
- Fix `calculate_exit_strategies()`: Gate "rent_hold" on rental evidence
- Replace LLM fallback timelines with deterministic values
- Make `detect_contradictions()` deterministic

**Phase 3 — Architecture (1-2 days)**
- Unify confidence calculation using `confidence_engine.py`
- Unify DTO schema between ready and off-plan
- Move rules application into scoring engines
- Re-run both scoring engines to regenerate cached JSON

**Phase 4 — Frontend (4-6 hours)**
- Update `ReportContext.ts` to handle off-plan dataQuality correctly
- Update `LLMAdvisorySection.tsx` to pass profile to advisory endpoint
- Update ValuationSection to handle unified DTO
- Test all 8 report sections with both ready and off-plan properties

---

# Critical Rule Adherence

This audit was conducted without:
- Patching any individual bugs
- Modifying any prompts
- Changing any UI
- Adjusting any wording

Every recommendation is backed by evidence from the codebase. The root cause of recurring contradictions is architectural: two different DTO schemas, profile loss in advisory endpoints, rules engine running without goal context, and 5 different confidence calculations.
