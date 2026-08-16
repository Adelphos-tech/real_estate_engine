# APIL Pipeline Verification Report

Generated: 2026-08-07T11:39:36.896591

---

## Verification Summary

| Module | Key Finding |
|---|---|
| D1-3 Pipeline Trace | 0 FAIL, 0 WARN, 27 fields tracked |
| D4 Duplicate Calculations | 9 fields with duplicates, 106 total sites |
| D5 Mutation Detection | 54 mutations, 6 fields with >2 |
| D6 DTO Verification | 32 only-ready, 13 only-offplan, 3 type mismatches |
| D7 Frontend Verification | 0 values tracked, 0 issues |
| D8 LLM Verification | 7 FAIL, 0 WARN |
| D9 Dependency Graph | 9 issues (2 critical, 3 high) |
| D10 Test Harness | 5 test profiles, 5 skipped |
| Final Report | 29 fields fully mapped |

---

## D4: Duplicate Calculation Detection

| Field | Sites | Files | Status | Source of Truth |
|---|---|---|---|---|
| confidence_score | 11 | report_rules_engine.py, offplan_engine_v2.py, confidence_engine.py | FAIL — DUPLICATE | confidence_engine.py::calculate_confidence (currently UNUSED — should be activated) |
| developer_score | 1 | offplan_engine_v2.py | PASS | Needs analysis |
| exit_strategy | 5 | investor_strategy_engine.py, report_rules_engine.py, offplan_engine_v2.py | FAIL — DUPLICATE | investor_strategy_engine.py::EXIT_PREFERENCES (deterministic, goal-based) |
| fair_value | 3 | offplan_engine_v2.py, market_valuation.py | FAIL — DUPLICATE | market_valuation.py::calculate_fair_value (weighted medians — should be used by both engines) |
| growth | 12 | utils.py, offplan_engine_v2.py | FAIL — DUPLICATE | Needs analysis |
| holding_period | 12 | investor_strategy_engine.py, report_rules_engine.py, offplan_engine_v2.py, llm_engine.py | FAIL — DUPLICATE | User input (profile.timeline) — should never be invented by LLM or fallback |
| investor_fit_score | 1 | investor_fit_engine.py | PASS | Needs analysis |
| liquidity_score | 4 | community_engine.py, project_engine.py, ready_engine.py | FAIL — DUPLICATE | Needs analysis |
| recommendation | 34 | utils.py, offplan_engine_v2.py, rules_engine.py | FAIL — DUPLICATE | utils.py::recommendation_from_score (goal-aware, used by ready engine) |
| risk_level | 16 | utils.py, llm_engine.py, offplan_engine.py, recommendation_engine.py, offplan_engine_v2.py, ready_engine.py | FAIL — DUPLICATE | ready_engine.py inline (≤25/≤50/>50 thresholds — should be extracted to utils.py) |
| roi | 6 | ready_engine.py, offplan_engine_v2.py | FAIL — DUPLICATE | ready_engine.py::calculate_roi (ready) + offplan_engine_v2.py::calculate_post_handover_roi (offplan) — different formulas, should unify |
| score_to_label | 1 | utils.py | PASS | utils.py::score_to_label (single implementation — OK) |

### Duplicate Calculation Sites

#### confidence_score

- `confidence_engine.py:7` in `calculate_confidence()` — `def calculate_confidence(sales_count: int, rent_count: int,`
- `offplan_engine_v2.py:932` in `score_offplan_property()` — `confidence_score = int(sum(w * s for w, s in conf_parts) / total_w)`
- `offplan_engine_v2.py:933` in `score_offplan_property()` — `confidence_score = int(clamp(confidence_score, 0, 100))`
- `report_rules_engine.py:295` in `confidence_from_sales()` — `def confidence_from_sales(sales_count: int) -> tuple[str, int]:`
- `report_rules_engine.py:452` in `build_report_contract()` — `sales_conf_label, sales_conf_score = confidence_from_sales(sales_count)`
- `report_rules_engine.py:307` in `confidence_from_rentals()` — `def confidence_from_rentals(rent_count: int) -> tuple[str, int]:`
- `report_rules_engine.py:453` in `build_report_contract()` — `rent_conf_label, rent_conf_score = confidence_from_rentals(rent_count)`
- `report_rules_engine.py:319` in `confidence_from_growth()` — `def confidence_from_growth(growth_data: dict) -> tuple[str, int]:`
- `report_rules_engine.py:465` in `build_report_contract()` — `growth_conf_label, growth_conf_score = confidence_from_growth(growth_data_obj)`
- `report_rules_engine.py:334` in `confidence_from_pricing()` — `def confidence_from_pricing(sales_count: int, comp_count: int = 0) -> tuple[str, int]:`
- `report_rules_engine.py:468` in `build_report_contract()` — `pricing_conf_label, pricing_conf_score = confidence_from_pricing(sales_count, comp_count)`

#### exit_strategy

- `investor_strategy_engine.py:226` in `<module>()` — `EXIT_PREFERENCES = {`
- `investor_strategy_engine.py:336` in `build_investor_strategy()` — `exit_pref = EXIT_PREFERENCES.get(goal, "sell_handover")`
- `offplan_engine_v2.py:689` in `calculate_exit_strategies()` — `def calculate_exit_strategies(asking_price: float, future_value: float,`
- `report_rules_engine.py:457` in `build_report_contract()` — `exit_strategy = get_exit_strategy(goal, holding_period, pt)`
- `report_rules_engine.py:242` in `get_exit_strategy()` — `def get_exit_strategy(goal: str, holding_period: str = "", property_type: str = "ready") -> str:`

#### fair_value

- `market_valuation.py:18` in `calculate_fair_value()` — `def calculate_fair_value(area_sqft: float,`
- `market_valuation.py:46` in `calculate_fair_value()` — `fair_value_total = fair_value_sqft * area_sqft`
- `offplan_engine_v2.py:159` in `calculate_fair_value()` — `def calculate_fair_value(`

#### growth

- `offplan_engine_v2.py:280` in `calculate_future_appreciation()` — `growth_rate = 0.0`
- `offplan_engine_v2.py:288` in `calculate_future_appreciation()` — `growth_rate = g12 / 100.0`
- `offplan_engine_v2.py:290` in `calculate_future_appreciation()` — `growth_rate = g6 / 100.0`
- `offplan_engine_v2.py:292` in `calculate_future_appreciation()` — `growth_rate = g3 / 100.0`
- `offplan_engine_v2.py:295` in `calculate_future_appreciation()` — `growth_rate = clamp(growth_rate, 0, 0.25)`
- `offplan_engine_v2.py:298` in `calculate_future_appreciation()` — `if growth_rate == 0 and project_data:`
- `offplan_engine_v2.py:301` in `calculate_future_appreciation()` — `growth_rate = clamp(pg / 100.0, 0, 0.25)`
- `offplan_engine_v2.py:304` in `calculate_future_appreciation()` — `if growth_rate == 0:`
- `offplan_engine_v2.py:305` in `calculate_future_appreciation()` — `growth_rate = 0.05`
- `offplan_engine_v2.py:747` in `calculate_exit_strategies()` — `growth_rate = 0.05`
- `utils.py:143` in `calculate_growth()` — `def calculate_growth(sales: list[dict], months: int) -> float:`
- `utils.py:167` in `calculate_growth_with_metadata()` — `def calculate_growth_with_metadata(sales: list[dict], months: int) -> dict:`

#### holding_period

- `investor_strategy_engine.py:238` in `<module>()` — `HOLDING_PERIOD_IMPACT = {`
- `investor_strategy_engine.py:308` in `build_investor_strategy()` — `period_config = HOLDING_PERIOD_IMPACT.get(timeline, HOLDING_PERIOD_IMPACT["3-5y"])`
- `investor_strategy_engine.py:399` in `_build_summary()` — `"hold_5yr": "Hold 5+ years",`
- `llm_engine.py:722` in `exit_strategy()` — `timeline = "Hold 5-7 years for rental yield accumulation"`
- `llm_engine.py:724` in `exit_strategy()` — `timeline = "Hold 3-5 years then sell at peak appreciation"`
- `llm_engine.py:726` in `exit_strategy()` — `timeline = "Hold 5 years, monitor market conditions"`
- `llm_engine.py:908` in `generate_advisory_report()` — `"exit_plan": "Hold 3-5 years depending on market conditions",`
- `offplan_engine_v2.py:746` in `calculate_exit_strategies()` — `# Strategy D: Hold 5 years`
- `offplan_engine_v2.py:753` in `calculate_exit_strategies()` — `"name": "Hold 5 Years Post-Handover",`
- `report_rules_engine.py:246` in `get_exit_strategy()` — `if holding_period == "5y+":`
- `report_rules_engine.py:248` in `get_exit_strategy()` — `elif holding_period == "1-2y":`
- `report_rules_engine.py:456` in `build_report_contract()` — `holding_period = (profile.get("timeline", "") or "").lower()`

#### liquidity_score

- `community_engine.py:107` in `compute_community_score()` — `liquidity_score = round(clamp(sales_volume * 0.8 + rent_volume * 0.5, 0, 100))`
- `project_engine.py:99` in `compute_unit_scores()` — `liquidity_score = clamp(txn_count * 7, 0, 100)`
- `project_engine.py:170` in `compute_project_score()` — `liquidity_score = round(clamp(txn_volume * 6 + rent_volume * 4, 0, 100))`
- `ready_engine.py:140` in `calculate_liquidity()` — `liquidity_score = round(volume_score * 0.40 + absorb_score * 0.35 + speed_score * 0.25)`

#### recommendation

- `offplan_engine_v2.py:957` in `score_offplan_property()` — `recommendation = "INSUFFICIENT_DATA"`
- `offplan_engine_v2.py:568` in `get_recommendation()` — `return "AVOID"`
- `offplan_engine_v2.py:570` in `get_recommendation()` — `return "HOLD"`
- `offplan_engine_v2.py:572` in `get_recommendation()` — `return "NEGOTIATE"`
- `offplan_engine_v2.py:574` in `get_recommendation()` — `return "STRONG BUY"`
- `offplan_engine_v2.py:576` in `get_recommendation()` — `return "BUY"`
- `offplan_engine_v2.py:578` in `get_recommendation()` — `return "HOLD"`
- `offplan_engine_v2.py:580` in `get_recommendation()` — `return "AVOID"`
- `rules_engine.py:36` in `apply_rules()` — `recommendation = "REVIEW"`
- `rules_engine.py:58` in `apply_rules()` — `recommendation = "WATCHLIST"`
- `rules_engine.py:65` in `apply_rules()` — `recommendation = "REVIEW"`
- `rules_engine.py:76` in `apply_rules()` — `recommendation = "REVIEW"`
- `rules_engine.py:83` in `apply_rules()` — `recommendation = "REVIEW"`
- `rules_engine.py:90` in `apply_rules()` — `recommendation = "REVIEW"`
- `rules_engine.py:96` in `apply_rules()` — `recommendation = "INSUFFICIENT_DATA"`
- `rules_engine.py:105` in `apply_rules()` — `recommendation = "INSUFFICIENT_DATA"`
- `utils.py:241` in `recommendation_from_score()` — `def recommendation_from_score(score: float, confidence: float = 100, goal: str = "balanced") -> str:`
- `utils.py:244` in `recommendation_from_score()` — `return "INSUFFICIENT_DATA"`
- `utils.py:246` in `recommendation_from_score()` — `return "REVIEW"`
- `utils.py:249` in `recommendation_from_score()` — `return "STRONG BUY"`
- `utils.py:251` in `recommendation_from_score()` — `return "BUY"`
- `utils.py:253` in `recommendation_from_score()` — `return "HOLD"`
- `utils.py:255` in `recommendation_from_score()` — `return "WATCHLIST"`
- `utils.py:256` in `recommendation_from_score()` — `return "REVIEW"`
- `utils.py:259` in `recommendation_from_score()` — `return "STRONG BUY"`
- `utils.py:261` in `recommendation_from_score()` — `return "BUY"`
- `utils.py:263` in `recommendation_from_score()` — `return "HOLD"`
- `utils.py:265` in `recommendation_from_score()` — `return "WATCHLIST"`
- `utils.py:266` in `recommendation_from_score()` — `return "REVIEW"`
- `utils.py:269` in `recommendation_from_score()` — `return "STRONG BUY" if confidence >= 80 else "BUY"`
- `utils.py:271` in `recommendation_from_score()` — `return "BUY" if confidence >= 70 else "HOLD"`
- `utils.py:273` in `recommendation_from_score()` — `return "HOLD" if confidence >= 65 else "WATCHLIST"`
- `utils.py:275` in `recommendation_from_score()` — `return "WATCHLIST"`
- `utils.py:276` in `recommendation_from_score()` — `return "REVIEW"`

#### risk_level

- `llm_engine.py:954` in `generate_advisory_report()` — `"risk": {"riskLevel": "Low"},`
- `llm_engine.py:972` in `generate_advisory_report()` — `"risk": {"riskLevel": "Low"},`
- `llm_engine.py:993` in `generate_advisory_report()` — `"risk": {"riskLevel": "Low"},`
- `llm_engine.py:1045` in `generate_advisory_report()` — `"risk": {"riskLevel": "Low"},`
- `offplan_engine.py:241` in `compute_offplan_score()` — `risk_level = "Low" if overall_risk < 35 else "Medium" if overall_risk < 60 else "High"`
- `offplan_engine.py:96` in `estimate_future_supply()` — `return {"futureSupplyScore": 50, "totalSupply": 0, "riskLevel": "Medium"}`
- `offplan_engine.py:226` in `compute_offplan_score()` — `if supply["riskLevel"] == "High":`
- `offplan_engine.py:241` in `compute_offplan_score()` — `risk_level = "Low" if overall_risk < 35 else "Medium" if overall_risk < 60 else "High"`
- `offplan_engine_v2.py:897` in `score_offplan_property()` — `risk_level = "Low" if overall_risk <= 25 else "Medium" if overall_risk <= 50 else "High"`
- `offplan_engine_v2.py:897` in `score_offplan_property()` — `risk_level = "Low" if overall_risk <= 25 else "Medium" if overall_risk <= 50 else "High"`
- `ready_engine.py:225` in `calculate_risk()` — `risk_level = "Low" if overall_risk <= 25 else "Medium" if overall_risk <= 50 else "High"`
- `ready_engine.py:544` in `compute_ready_property_score()` — `if risk["riskLevel"] == "Low":`
- `ready_engine.py:225` in `calculate_risk()` — `risk_level = "Low" if overall_risk <= 25 else "Medium" if overall_risk <= 50 else "High"`
- `recommendation_engine.py:127` in `filter_ready_properties()` — `props = [p for p in props if p.get("risk", {}).get("riskLevel") != "High"]`
- `recommendation_engine.py:165` in `filter_offplan_properties()` — `props = [p for p in props if p.get("risk", {}).get("riskLevel") != "High"]`
- `utils.py:223` in `risk_from_score()` — `def risk_from_score(score: float) -> str:`

#### roi

- `offplan_engine_v2.py:409` in `calculate_post_handover_roi()` — `net_roi = (net_income / developer_price) * 100`
- `offplan_engine_v2.py:408` in `calculate_post_handover_roi()` — `gross_roi = (estimated_rent / developer_price) * 100`
- `offplan_engine_v2.py:333` in `calculate_post_handover_roi()` — `def calculate_post_handover_roi(`
- `ready_engine.py:80` in `calculate_roi()` — `def calculate_roi(asking_price: float, annual_rent: float, area_sqft: float, service_charge_per_sqft: float | None) -> d`
- `ready_engine.py:106` in `calculate_roi()` — `net_roi = (net_annual_income / asking_price * 100) if asking_price > 0 else 0`
- `ready_engine.py:105` in `calculate_roi()` — `gross_roi = (annual_rent / asking_price * 100) if asking_price > 0 else 0`

---

## D5: Mutation Detection

| Field | Mutations | Files | Status |
|---|---|---|---|
| confidence | 10 | project_engine.py, community_engine.py, recommendation_engine.py, feature_engine.py, offplan_engine_v2.py, ready_engine.py, validation_engine.py, rules_engine.py | FAIL |
| exit_strategy | 5 | report_rules_engine.py, llm_engine.py | FAIL |
| profile | 5 | recommendation_engine.py, llm_engine.py | FAIL |
| recommendation | 27 | rules_engine.py, offplan_engine_v2.py, recommendation_engine.py | FAIL |
| risk | 4 | ready_engine.py, recommendation_engine.py | FAIL |
| valuation | 3 | offplan_engine.py, market_valuation.py | FAIL |

### Mutation Details

#### confidence — FAIL

- `community_engine.py:140` in `compute_community_score()` [assignment]
  - `confidence = int(clamp(confidence, 0, 100))`
- `feature_engine.py:174` in `compute_project_features()` [assignment]
  - `confidence = int(clamp(confidence, 0, 100))`
- `offplan_engine_v2.py:933` in `score_offplan_property()` [assignment]
  - `confidence_score = int(clamp(confidence_score, 0, 100))`
- `project_engine.py:196` in `compute_project_score()` [assignment]
  - `confidence = int(clamp(confidence, 0, 100))`
- `ready_engine.py:455` in `compute_ready_property_score()` [assignment]
  - `confidence = int(clamp(confidence, 0, 100))`
- `recommendation_engine.py:231` in `_normalize_recommendation()` [dict_update]
  - `prop["pricingConfidence"] = pc`
- `recommendation_engine.py:232` in `_normalize_recommendation()` [dict_update]
  - `prop["rentalConfidence"] = rc`
- `recommendation_engine.py:610` in `_build_match_reasons()` [conditional_override]
  - `conf = prop.get("confidenceScore", 0)`
- `rules_engine.py:23` in `apply_rules()` [conditional_override]
  - `confidence = safe_float(prop.get("confidenceScore", 0))`
- `validation_engine.py:151` in `validate_project()` [assignment]
  - `confidence = int(clamp(confidence, 0, 100))`

#### exit_strategy — FAIL

- `llm_engine.py:722` in `exit_strategy()` [assignment]
  - `timeline = "Hold 5-7 years for rental yield accumulation"`
- `llm_engine.py:724` in `exit_strategy()` [assignment]
  - `timeline = "Hold 3-5 years then sell at peak appreciation"`
- `llm_engine.py:726` in `exit_strategy()` [assignment]
  - `timeline = "Hold 5 years, monitor market conditions"`
- `llm_engine.py:908` in `generate_advisory_report()` [assignment]
  - `"exit_plan": "Hold 3-5 years depending on market conditions",`
- `report_rules_engine.py:457` in `build_report_contract()` [assignment]
  - `exit_strategy = get_exit_strategy(goal, holding_period, pt)`

#### profile — FAIL

- `llm_engine.py:959` in `generate_advisory_report()` [assignment]
  - `investor_profile={"goal": "rental_income", "risk": "medium"},`
- `llm_engine.py:995` in `generate_advisory_report()` [assignment]
  - `investor_profile={"goal": "rental_income", "budget": "1m-2m", "risk": "medium"},`
- `llm_engine.py:1021` in `generate_advisory_report()` [assignment]
  - `investor_profile={"goal": "rental_income", "risk": "medium"},`
- `llm_engine.py:1050` in `generate_advisory_report()` [assignment]
  - `investor_profile={"goal": "rental_income", "risk": "medium"},`
- `recommendation_engine.py:624` in `run()` [assignment]
  - `profile = {}`

#### recommendation — FAIL

- `offplan_engine_v2.py:957` in `score_offplan_property()` [assignment]
  - `recommendation = "INSUFFICIENT_DATA"`
- `recommendation_engine.py:204` in `_normalize_recommendation()` [dict_update]
  - `prop["recommendation"] = "WATCHLIST"`
- `recommendation_engine.py:500` in `get_blended_score()` [dict_update]
  - `top["recommendation"] = recommendation_from_score(top_score, top_conf, goal)`
- `recommendation_engine.py:504` in `get_blended_score()` [dict_update]
  - `top["recommendation"] = "REVIEW"`
- `recommendation_engine.py:506` in `get_blended_score()` [dict_update]
  - `if top["recommendation"] == "STRONG BUY":`
- `recommendation_engine.py:507` in `get_blended_score()` [dict_update]
  - `top["recommendation"] = "BUY"`
- `recommendation_engine.py:508` in `get_blended_score()` [dict_update]
  - `elif top["recommendation"] == "BUY":`
- `recommendation_engine.py:509` in `get_blended_score()` [dict_update]
  - `top["recommendation"] = "BUY IF NEGOTIATED"`
- `recommendation_engine.py:204` in `_normalize_recommendation()` [dict_update]
  - `prop["recommendation"] = "WATCHLIST"`
- `recommendation_engine.py:500` in `get_blended_score()` [dict_update]
  - `top["recommendation"] = recommendation_from_score(top_score, top_conf, goal)`
- `recommendation_engine.py:504` in `get_blended_score()` [dict_update]
  - `top["recommendation"] = "REVIEW"`
- `recommendation_engine.py:506` in `get_blended_score()` [dict_update]
  - `if top["recommendation"] == "STRONG BUY":`
- `recommendation_engine.py:507` in `get_blended_score()` [dict_update]
  - `top["recommendation"] = "BUY"`
- `recommendation_engine.py:508` in `get_blended_score()` [dict_update]
  - `elif top["recommendation"] == "BUY":`
- `recommendation_engine.py:509` in `get_blended_score()` [dict_update]
  - `top["recommendation"] = "BUY IF NEGOTIATED"`
- `recommendation_engine.py:203` in `_normalize_recommendation()` [normalization]
  - `if rec == "CAUTION":`
- `recommendation_engine.py:204` in `_normalize_recommendation()` [normalization]
  - `prop["recommendation"] = "WATCHLIST"`
- `rules_engine.py:107` in `apply_rules()` [dict_update]
  - `prop["recommendation"] = recommendation`
- `rules_engine.py:36` in `apply_rules()` [assignment]
  - `recommendation = "REVIEW"`
- `rules_engine.py:58` in `apply_rules()` [assignment]
  - `recommendation = "WATCHLIST"`
- `rules_engine.py:65` in `apply_rules()` [assignment]
  - `recommendation = "REVIEW"`
- `rules_engine.py:76` in `apply_rules()` [assignment]
  - `recommendation = "REVIEW"`
- `rules_engine.py:83` in `apply_rules()` [assignment]
  - `recommendation = "REVIEW"`
- `rules_engine.py:90` in `apply_rules()` [assignment]
  - `recommendation = "REVIEW"`
- `rules_engine.py:96` in `apply_rules()` [assignment]
  - `recommendation = "INSUFFICIENT_DATA"`
- `rules_engine.py:105` in `apply_rules()` [assignment]
  - `recommendation = "INSUFFICIENT_DATA"`
- `rules_engine.py:107` in `apply_rules()` [dict_update]
  - `prop["recommendation"] = recommendation`

#### risk — FAIL

- `ready_engine.py:544` in `compute_ready_property_score()` [dict_update]
  - `if risk["riskLevel"] == "Low":`
- `recommendation_engine.py:242` in `_normalize_recommendation()` [dict_update]
  - `risk["riskLevel"] = new_level`
- `recommendation_engine.py:243` in `_normalize_recommendation()` [dict_update]
  - `prop["risk"] = risk`
- `recommendation_engine.py:240` in `_normalize_recommendation()` [normalization]
  - `new_level = "Low" if overall <= 25 else "Medium" if overall <= 50 else "High"`

#### valuation — FAIL

- `market_valuation.py:70` in `classify_price()` [assignment]
  - `discount_pct = ((asking_price - fair_value_total) / fair_value_total) * 100`
- `offplan_engine.py:79` in `estimate_launch_pricing()` [assignment]
  - `discount_pct = round(((nearby_med - project_med) / nearby_med) * 100, 2)`
- `offplan_engine.py:81` in `estimate_launch_pricing()` [assignment]
  - `discount_pct = 0`

---

## D6: DTO Verification — Ready vs Off-plan

- Ready fields: 51
- Off-plan fields: 32
- Common: 19
- Only in ready: 32
- Only in off-plan: 13
- Type mismatches: 3
- Nested issues: 41
- Missing critical: 2

### Fields Only in Ready DTO

- `areaSqft`
- `communityScore`
- `comparablePrice`
- `confidenceBreakdown`
- `confidenceLevel`
- `dataCompleteness`
- `dataQuality`
- `demandScore`
- `developerName`
- `developerScore`
- `estimatedRent`
- `estimatedYield`
- `evidenceLevels`
- `growth12m`
- `growth3m`
- `growth6m`
- `growthMetadata`
- `lostPoints`
- `marketPosition`
- `marketValuation`
- `priceDifference`
- `priceScore`
- `projectData`
- `projectScore`
- `projectSlug`
- `propertyType`
- `readyScore`
- `rentRange`
- `roi`
- `roiScore`
- `rulesFlags`
- `validationStatus`

### Fields Only in Off-plan DTO

- `confidenceExplanation`
- `developer`
- `exitStrategies`
- `futureAppreciation`
- `hasSize`
- `listingData`
- `offplanScore`
- `paymentPlanAnalysis`
- `postHandoverROI`
- `priceOpportunity`
- `sizeSqft`
- `slug`
- `status`

### Type Mismatches

| Field | Ready Type | Off-plan Type |
|---|---|---|
| fairValue | int | dict |
| id | str | int |
| priceSqft | int | float |

### Nested Structure Issues

- `communityData.rentalYield`: Field 'rentalYield' only exists in ready DTO
- `communityData.growth3m`: Field 'growth3m' only exists in ready DTO
- `communityData.rentVolume`: Field 'rentVolume' only exists in ready DTO
- `communityData.medianPriceSqft`: Field 'medianPriceSqft' only exists in ready DTO
- `communityData.name`: Field 'name' only exists in ready DTO
- `communityData.totalProjects`: Field 'totalProjects' only exists in ready DTO
- `communityData.subScores`: Field 'subScores' only exists in ready DTO
- `communityData.salesVolume`: Field 'salesVolume' only exists in ready DTO
- `communityData.medianRent`: Field 'medianRent' only exists in ready DTO
- `communityData.transactionScore`: Field 'transactionScore' only exists in ready DTO
- `communityData.scoreBreakdown`: Field 'scoreBreakdown' only exists in ready DTO
- `communityData.riskLevel`: Field 'riskLevel' only exists in ready DTO
- `communityData.totalSupply`: Field 'totalSupply' only exists in ready DTO
- `communityData.growth6m`: Field 'growth6m' only exists in ready DTO
- `communityData.rentalDemand`: Field 'rentalDemand' only exists in off-plan DTO
- `communityData.liquidityScore`: Field 'liquidityScore' only exists in off-plan DTO
- `communityData.futureSupplyScore`: Field 'futureSupplyScore' only exists in off-plan DTO
- `communityData.growthIndex`: Field 'growthIndex' only exists in off-plan DTO
- `developerData.name`: Field 'name' only exists in ready DTO
- `developerData.googleRating`: Field 'googleRating' only exists in ready DTO
- `developerData.deliveryDelayRisk`: Field 'deliveryDelayRisk' only exists in ready DTO
- `developerData.buyerConfidence`: Field 'buyerConfidence' only exists in ready DTO
- `developerData.scoreBreakdown`: Field 'scoreBreakdown' only exists in ready DTO
- `developerData.projectsDelivered`: Field 'projectsDelivered' only exists in ready DTO
- `developerData.deliveryDelayPercent`: Field 'deliveryDelayPercent' only exists in ready DTO
- `developerData.developerName`: Field 'developerName' only exists in off-plan DTO
- `developerData.trackRecord`: Field 'trackRecord' only exists in off-plan DTO
- `developerData.deliveryHistory`: Field 'deliveryHistory' only exists in off-plan DTO
- `developerData.delayRisk`: Field 'delayRisk' only exists in off-plan DTO
- `developerData.capitalAppreciation`: Field 'capitalAppreciation' only exists in off-plan DTO
- `liquidity.liquidityLabel`: Field 'liquidityLabel' only exists in ready DTO
- `liquidity.avgDaysOnMarket`: Field 'avgDaysOnMarket' only exists in ready DTO
- `liquidity.absorptionRate`: Field 'absorptionRate' only exists in ready DTO
- `liquidity.communityLiquidity`: Field 'communityLiquidity' only exists in off-plan DTO
- `liquidity.transactionVolume`: Field 'transactionVolume' only exists in off-plan DTO
- `liquidity.projectLiquidity`: Field 'projectLiquidity' only exists in off-plan DTO
- `scoreBreakdown.community`: Field 'community' only exists in ready DTO
- `scoreBreakdown.project`: Field 'project' only exists in ready DTO
- `scoreBreakdown.paymentPlan`: Field 'paymentPlan' only exists in off-plan DTO
- `scoreBreakdown.growth`: Field 'growth' only exists in off-plan DTO
- `scoreBreakdown.supplyRisk`: Field 'supplyRisk' only exists in off-plan DTO

### Semantic Equivalents (different names, same meaning)

| Concept | Ready | Off-plan | Issue |
|---|---|---|---|
| investment_score | `readyScore` | `offplanScore` | Different field names for investment score |
| fair_value | `marketValuation.fairValueTotal` | `fairValue.fairValue` | Different paths and names for fair value |
| price_vs_market | `priceDifference` | `priceOpportunity.priceDifferencePct` | Different fields for price vs market |
| comparable_price | `comparablePrice` | `fairValue.fairValue (used as comparable)` | Ready has explicit comparablePrice, off-plan uses fairValue |
| roi | `roi.netROI` | `postHandoverROI.netROI` | Different nesting for ROI |
| score_breakdown | `scoreBreakdown.{price,roi,liquidity,community,developer,project}` | `scoreBreakdown.{developer,price,paymentPlan,growth,supplyRisk,liquidity,roi}` | Different keys in scoreBreakdown |

### Missing Critical Fields

| Field | In Ready | In Off-plan | Impact |
|---|---|---|---|
| pricingConfidence | False | False | Off-plan has no split pricing confidence |
| rentalConfidence | False | False | Off-plan has no split rental confidence |

### Recommended Unified DTO

- 1. Both ready and off-plan must have: dataQuality, lostPoints, pricingConfidence, rentalConfidence, rulesFlags, rulesFlagsHuman
- 2. Unify investment score field name: use 'investmentScore' for both (not readyScore/offplanScore)
- 3. Unify fair value: use 'marketValuation.fairValueTotal' for both (off-plan currently uses 'fairValue.fairValue')
- 4. Unify price vs market: use 'priceVsMarketPct' for both (not priceDifference / priceOpportunity.priceDifferencePct)
- 5. Unify ROI nesting: use 'roi.netROI' for both (not postHandoverROI.netROI)
- 6. Unify scoreBreakdown keys: use common set {developer, price, roi, liquidity, community, growth, supply, paymentPlan}
- 7. Both must populate dataQuality with: hasComparables, hasRentData, salesCount, rentCount, comparableCount
- 8. Both must populate rulesFlagsHuman when rules are applied

---

## D8: LLM Prompt Verification

| Status | Type | Function | Line | Field | Detail |
|---|---|---|---|---|---|
| PASS | field_injection | validate_listing | 107 | confidence | Function injects confidence score |
| PASS | profile_injection | explain_score | 179 | goal | Function receives investor_profile and extracts goal |
| PASS | goal_constraint | explain_score | 179 | goal | Function injects goal constraint into prompt |
| PASS | field_injection | explain_score | 179 | recommendation | Function injects deterministic recommendation |
| PASS | field_injection | explain_score | 179 | confidence | Function injects confidence score |
| PASS | field_injection | explain_score | 179 | price_vs_market | Function injects price vs market data |
| PASS | field_injection | detect_contradictions | 313 | recommendation | Function injects deterministic recommendation |
| PASS | field_injection | detect_contradictions | 313 | confidence | Function injects confidence score |
| PASS | profile_injection | investor_recommendation | 391 | goal | Function receives investor_profile and extracts goal |
| FAIL | goal_constraint | investor_recommendation | 391 | goal | Function receives profile but does NOT inject goal constraint into prompt |
| PASS | field_injection | investor_recommendation | 391 | recommendation | Function injects deterministic recommendation |
| PASS | field_injection | investor_recommendation | 391 | confidence | Function injects confidence score |
| PASS | profile_injection | compare_alternatives | 480 | goal | Function receives investor_profile and extracts goal |
| FAIL | goal_constraint | compare_alternatives | 480 | goal | Function receives profile but does NOT inject goal constraint into prompt |
| PASS | field_injection | compare_alternatives | 480 | confidence | Function injects confidence score |
| PASS | field_injection | negotiation_strategy | 559 | price_vs_market | Function injects price vs market data |
| PASS | profile_injection | exit_strategy | 668 | goal | Function receives investor_profile and extracts goal |
| PASS | goal_constraint | exit_strategy | 668 | goal | Function injects goal constraint into prompt |
| FAIL | fallback_invention | exit_strategy | 668 | holding_period/exit_strategy | Invents holding period '3-5 years' in fallback |
| FAIL | fallback_invention | exit_strategy | 668 | holding_period/exit_strategy | Invents holding period '5-7 years' in fallback |
| FAIL | fallback_invention | exit_strategy | 668 | holding_period/exit_strategy | Invents holding period '5 years' in fallback |
| PASS | field_injection | exit_strategy | 668 | confidence | Function injects confidence score |
| PASS | profile_injection | generate_advisory_report | 776 | goal | Function receives investor_profile and extracts goal |
| PASS | goal_constraint | generate_advisory_report | 776 | goal | Function injects goal constraint into prompt |
| FAIL | fallback_invention | generate_advisory_report | 776 | holding_period/exit_strategy | Invents holding period '3-5 years' in fallback |
| FAIL | fallback_invention | generate_advisory_report | 776 | holding_period/exit_strategy | Invents exit plan in fallback |
| PASS | field_injection | generate_advisory_report | 776 | recommendation | Function injects deterministic recommendation |
| PASS | field_injection | generate_advisory_report | 776 | confidence | Function injects confidence score |
| PASS | field_injection | generate_advisory_report | 776 | price_vs_market | Function injects price vs market data |

### Failures

- **[goal_constraint]** `investor_recommendation:391` — **goal**
  - Function receives profile but does NOT inject goal constraint into prompt
- **[goal_constraint]** `compare_alternatives:480` — **goal**
  - Function receives profile but does NOT inject goal constraint into prompt
- **[fallback_invention]** `exit_strategy:668` — **holding_period/exit_strategy**
  - Invents holding period '3-5 years' in fallback
- **[fallback_invention]** `exit_strategy:668` — **holding_period/exit_strategy**
  - Invents holding period '5-7 years' in fallback
- **[fallback_invention]** `exit_strategy:668` — **holding_period/exit_strategy**
  - Invents holding period '5 years' in fallback
- **[fallback_invention]** `generate_advisory_report:776` — **holding_period/exit_strategy**
  - Invents holding period '3-5 years' in fallback
- **[fallback_invention]** `generate_advisory_report:776` — **holding_period/exit_strategy**
  - Invents exit plan in fallback

---

## D9: Architectural Dependency Graph

```
PIPELINE DEPENDENCY GRAPH

Questionnaire (frontend)
  ↓ profile
apil_server.py :: /recommendations
  ↓ profile dict
recommendation_engine.py :: generate_recommendations()
  ├─→ investor_strategy_engine.py :: build_investor_strategy()
  ├─→ investor_fit_engine.py :: calculate_investor_fit()
  ├─→ ready_engine.py (cached JSON) ← market_valuation.py [DEAD]
  ├─→ offplan_engine_v2.py (cached JSON)
  ├─→ _normalize_recommendation() [MUTATES: rec, confidence, risk]
  ├─→ rules_engine.py :: batch_apply_rules() [MUTATES: rec] (goal=balanced!)
  ├─→ report_rules_engine.py :: build_report_contract()
  ├─→ report_rules_engine.py :: validate_report()
  ├─→ llm_engine.py :: explain_score() [profile=real ✓]
  └─→ llm_engine.py :: generate_advisory_report() [profile=real ✓]
  ↓ JSON response
Frontend Report.tsx
  ├─→ loader.ts :: mapReadyToLegacy() [DROPS: scoreBreakdown, lostPoints, dataQuality]
  ├─→ ReportContext.ts :: buildReportContext() [READS: dataQuality=NULL for offplan]
  ├─→ SectionRegistry.tsx :: getApplicableSections()
  ├─→ report/sections/*.tsx [READ: topRec directly]
  └─→ LLMAdvisorySection.tsx
       ├─→ if topRec.llmAdvisoryReport → use it [profile=real ✓]
       └─→ else fetch /advisory endpoint [profile=HARDCODED balanced ✗]

DEAD CODE:
  confidence_engine.py — never called
  market_valuation.py — never called by ready_engine
  offplan_engine.py (v1) — superseded by v2

DUPLICATE PATHS:
  Confidence: 5 implementations (confidence_engine, ready_engine, offplan_engine_v2, report_rules_engine, _normalize)
  Recommendation: 3 implementations (utils, offplan_engine_v2, recommendation_engine inline)
  Risk level: 3 threshold sets (ready/offplan, utils.risk_from_score, community/project)
  Fair value: 2 implementations (market_valuation.py, offplan_engine_v2.py)
```

### Known Issues

| Severity | Title | Detail |
|---|---|---|
| CRITICAL | Two scoring paths with different DTOs | ready_engine.py and offplan_engine_v2.py produce completely different output schemas. Ready has marketValuation, priceDifference, dataQuality, lostPoints. Off-plan has fairValue, priceOpportunity, no dataQuality, no lostPoints. |
| HIGH | Confidence calculated in 5 places | confidence_engine.py (unused), ready_engine.py inline, offplan_engine_v2.py inline, report_rules_engine.py (per-dimension), _normalize_recommendation() (reconstruction). |
| HIGH | Recommendation calculated in 3 places | utils.py::recommendation_from_score (goal-aware), offplan_engine_v2.py::offplan_recommendation (price-diff based), recommendation_engine.py inline (fit gates). |
| HIGH | Recommendation overwritten 3+ times | 1) Engine creates it, 2) _normalize_recommendation converts CAUTION→WATCHLIST, 3) rules_engine downgrades, 4) fit gates downgrade again. |
| CRITICAL | Profile overwritten in advisory endpoints | apil_server.py lines 207, 250 hardcode profile={'goal':'balanced'} for advisory endpoints, losing the user's actual goal. |
| MEDIUM | confidence_engine.py is never called | Module exists with calculate_confidence() function but ready_engine and offplan_engine_v2 have their own inline calculations. |
| MEDIUM | market_valuation.py is never called by ready_engine | Module exists with calculate_fair_value() but ready_engine.py does not import or call it. marketValuation in cached JSON was computed by removed code. |
| LOW | offplan_engine.py (v1) still exists alongside v2 | offplan_engine.py is the old version. offplan_engine_v2.py is the current version. v1 is dead code. |
| INFO | No cycles detected | Pipeline is linear: questionnaire → engine → rules → contract → API → frontend. No circular dependencies. |

### Module Details

| Module | Dead Code | Imports | Imported By | Notes |
|---|---|---|---|---|
| apil_server | no | — | — | — |
| community_engine | YES | utils | — | Module is never imported by any other module |
| confidence_engine | YES | — | — | Module is never imported by any other module; calculate_confidence() exists but is never called by ready_engine or offplan_engine_v2 |
| developer_engine | YES | utils | — | Module is never imported by any other module |
| feature_engine | YES | utils | — | Module is never imported by any other module |
| investor_fit_engine | no | utils | recommendation_engine | — |
| investor_strategy_engine | no | — | recommendation_engine | — |
| llm_engine | YES | — | — | Module is never imported by any other module |
| market_valuation | YES | utils | — | Module is never imported by any other module; calculate_fair_value() exists but ready_engine does not call it |
| offplan_engine | YES | utils | — | Module is never imported by any other module; v1 engine — superseded by offplan_engine_v2 |
| offplan_engine_v2 | YES | utils | — | Module is never imported by any other module |
| project_engine | YES | utils | — | Module is never imported by any other module |
| qdrant_enrichment | YES | — | — | Module is never imported by any other module |
| ready_engine | YES | utils | — | Module is never imported by any other module |
| recommendation_engine | YES | utils, investor_strategy_engine, investor_fit_engine, report_rules_engine | — | Module is never imported by any other module |
| report_rules_engine | no | utils | recommendation_engine | — |
| rules_engine | YES | utils | — | Module is never imported by any other module |
| utils | no | — | community_engine, offplan_engine, validation_engine_v2, validation_engine, project_engine, ready_engine, recommendation_engine, rules_engine, offplan_engine_v2, investor_fit_engine, market_valuation, developer_engine, report_rules_engine, feature_engine | — |
| validation_engine | YES | utils | — | Module is never imported by any other module |
| validation_engine_v2 | YES | utils | — | Module is never imported by any other module |

---

## D10: Test Harness — Snapshot Framework

- Total test profiles: 5
- Snapshot fields per test: 31

### Test Profiles

| Name | Goal | Budget | Type | Beds | Timeline | Risk |
|---|---|---|---|---|---|---|
| rental_income_medium_2m | rental_income | 2m-5m | apartment | 2 | 3-5y | medium |
| capital_growth_low_5m | capital_growth | 5m-10m | apartment | 3 | 5y+ | low |
| flip_handover_high_1m | flip_handover | 1m-2m | apartment | 1 | 1-2y | high |
| balanced_medium_2m | balanced | 2m-5m | any | any | undecided | medium |
| end_user_low_5m | end_user | 5m-10m | villa | 4 | 5y+ | low |

### Snapshot Fields Tracked

- `goal`
- `budget`
- `property_type`
- `bedrooms`
- `financing`
- `timeline`
- `risk`
- `ready_offplan`
- `investment_score`
- `investor_fit_score`
- `confidence_score`
- `recommendation`
- `developer_score`
- `area_score`
- `liquidity_score`
- `growth_12m`
- `net_roi`
- `gross_roi`
- `fair_value`
- `price_vs_market`
- `risk_level`
- `exit_strategy`
- `holding_period`
- `score_label`
- `rules_flags`
- `pricing_confidence`
- `rental_confidence`
- `has_rental_evidence`
- `has_comparable_sales`
- `report_state`
- `visible_sections`

---

## Final Architecture Report — Deterministic Field Map

### `goal` — Risk: CRITICAL — Profile loss in advisory endpoints causes wrong LLM output

- **Origin**: User questionnaire → sessionStorage → POST /recommendations
- **Modifiers**:
  - apil_server.py advisory endpoints — HARDCODES to 'balanced' (lines 207, 250)
- **Hardcoded values**:
  - apil_server.py:207 — profile = {'goal': 'balanced'}
  - apil_server.py:250 — profile = {'goal': 'balanced'}
- **Inconsistencies**:
  - Advisory endpoints hardcode 'balanced' instead of using user's actual goal
- **Recommended source of truth**: User questionnaire — must be passed through every stage without mutation

### `budget` — Risk: LOW

- **Origin**: User questionnaire → sessionStorage → POST /recommendations
- **Recommended source of truth**: Needs analysis

### `property_type` — Risk: LOW

- **Origin**: User questionnaire → sessionStorage → POST /recommendations
- **Recommended source of truth**: Needs analysis

### `bedrooms` — Risk: LOW

- **Origin**: User questionnaire → sessionStorage → POST /recommendations
- **Recommended source of truth**: Needs analysis

### `financing` — Risk: LOW

- **Origin**: User questionnaire → sessionStorage → POST /recommendations
- **Recommended source of truth**: Needs analysis

### `timeline` — Risk: LOW

- **Origin**: User questionnaire → sessionStorage → POST /recommendations
- **Recommended source of truth**: Needs analysis

### `risk` — Risk: LOW

- **Origin**: User questionnaire → sessionStorage → POST /recommendations
- **Recommended source of truth**: Needs analysis

### `ready_offplan` — Risk: LOW

- **Origin**: User questionnaire → sessionStorage → POST /recommendations
- **Recommended source of truth**: Needs analysis

### `location` — Risk: LOW

- **Origin**: User questionnaire → sessionStorage → POST /recommendations
- **Recommended source of truth**: Needs analysis

### `investment_score` — Risk: LOW

- **Origin**: ready_engine.py::compute_ready_property_score() / offplan_engine_v2.py::score_offplan_property()
- **Hardcoded values**:
  - offplan_engine_v2.py:215 — growth_rate = 0.05 (default 5% if no data)
- **Fallbacks**:
  - offplan_engine_v2.py uses 5% default growth rate when no community/project data
- **Recommended source of truth**: Needs analysis

### `investor_fit_score` — Risk: LOW

- **Origin**: investor_fit_engine.py::calculate_investor_fit()
- **Recommended source of truth**: Needs analysis

### `confidence_score` — Risk: HIGH — 5 implementations, no single source of truth

- **Origin**: ready_engine.py inline / offplan_engine_v2.py inline (confidence_engine.py UNUSED)
- **Modifiers**:
  - _normalize_recommendation() — reconstructs pricingConfidence/rentalConfidence if missing
  - rules_engine.py — may downgrade based on confidence <40 or <25
- **Duplicate calculations**:
  - confidence_engine.py (UNUSED)
  - ready_engine.py inline
  - offplan_engine_v2.py inline
  - report_rules_engine.py (per-dimension)
  - _normalize_recommendation()
- **Inconsistencies**:
  - 5 different implementations produce different values for same data
- **Unused calculations**:
  - confidence_engine.py::calculate_confidence() — exists but never called
- **Recommended source of truth**: confidence_engine.py::calculate_confidence() — activate and use everywhere

### `recommendation` — Risk: HIGH — 3 implementations, 3+ override points, different vocabulary

- **Origin**: utils.py::recommendation_from_score() / offplan_engine_v2.py::offplan_recommendation()
- **Modifiers**:
  - _normalize_recommendation() — converts CAUTION→WATCHLIST
  - rules_engine.py::apply_rules() — downgrades based on rules (uses goal='balanced')
  - recommendation_engine.py inline — fit score gates (fit<40→REVIEW, fit<55→downgrade)
- **Duplicate calculations**:
  - utils.py::recommendation_from_score()
  - offplan_engine_v2.py::offplan_recommendation()
  - recommendation_engine.py inline (fit gates)
- **Fallbacks**:
  - _normalize_recommendation() converts deprecated CAUTION→WATCHLIST at runtime
- **Inconsistencies**:
  - Off-plan uses different vocabulary (NEGOTIATE, AVOID) than ready (WATCHLIST, REVIEW)
- **Recommended source of truth**: utils.py::recommendation_from_score() — unify off-plan to use same function

### `developer_score` — Risk: LOW

- **Origin**: developer_engine.py → developer_scores.json (offplan_engine_v2 re-calculates from breakdown)
- **Recommended source of truth**: Needs analysis

### `area_score` — Risk: LOW

- **Origin**: community_engine.py → community_scores.json
- **Recommended source of truth**: Needs analysis

### `liquidity_score` — Risk: LOW

- **Origin**: ready_engine.py / offplan_engine_v2.py inline
- **Recommended source of truth**: Needs analysis

### `growth_12m` — Risk: LOW

- **Origin**: ready_engine.py::calculate_growth_with_metadata()
- **Recommended source of truth**: Needs analysis

### `net_roi` — Risk: LOW

- **Origin**: ready_engine.py::calculate_roi() / offplan_engine_v2.py::calculate_post_handover_roi()
- **Recommended source of truth**: Needs analysis

### `gross_roi` — Risk: LOW

- **Origin**: ready_engine.py::calculate_roi() / offplan_engine_v2.py::calculate_post_handover_roi()
- **Recommended source of truth**: Needs analysis

### `fair_value` — Risk: HIGH — 2 different formulas, 1 unused module

- **Origin**: market_valuation.py::calculate_fair_value() (UNUSED) / offplan_engine_v2.py::calculate_fair_value()
- **Duplicate calculations**:
  - market_valuation.py::calculate_fair_value() (UNUSED)
  - offplan_engine_v2.py::calculate_fair_value()
- **Inconsistencies**:
  - Ready uses marketValuation.fairValueTotal, off-plan uses fairValue.fairValue — different paths and formulas
- **Unused calculations**:
  - market_valuation.py::calculate_fair_value() — exists but never called by ready_engine
- **Recommended source of truth**: market_valuation.py::calculate_fair_value() — activate for both engines

### `price_vs_market` — Risk: MEDIUM — Different field names and nesting between ready and off-plan

- **Origin**: ready_engine.py inline / offplan_engine_v2.py inline
- **Inconsistencies**:
  - Ready uses priceDifference (top-level), off-plan uses priceOpportunity.priceDifferencePct (nested)
- **Recommended source of truth**: Unify to single field name 'priceVsMarketPct' in both DTOs

### `risk_level` — Risk: MEDIUM — 3 different threshold sets

- **Origin**: ready_engine.py / offplan_engine_v2.py inline (≤25/≤50/>50)
- **Modifiers**:
  - _normalize_recommendation() — re-normalizes thresholds (≤25/≤50/>50)
- **Duplicate calculations**:
  - ready_engine.py/offplan_engine_v2.py (≤25/≤50/>50)
  - utils.py::risk_from_score() (≥80/≥65/<65)
  - community_engine.py/project_engine.py (uses risk_from_score)
- **Inconsistencies**:
  - Property risk and community/project risk use different thresholds
- **Recommended source of truth**: Extract to utils.py — single function with one threshold set

### `price_sqft` — Risk: LOW

- **Origin**: ready_engine.py / offplan_engine_v2.py inline
- **Recommended source of truth**: Needs analysis

### `asking_price` — Risk: LOW

- **Origin**: Qdrant payload
- **Recommended source of truth**: Needs analysis

### `exit_strategy` — Risk: HIGH — Multiple sources, LLM fallback invents values

- **Origin**: investor_strategy_engine.py::EXIT_PREFERENCES / offplan_engine_v2.py::calculate_exit_strategies()
- **Modifiers**:
  - LLM fallback — invents 'Hold 3-5 years' when LLM unavailable
  - offplan_engine_v2.py — re-calculates recommendedStrategy based on equity_gain/roi
- **Hardcoded values**:
  - llm_engine.py:908 — 'Hold 3-5 years depending on market conditions' (fallback exit_plan)
- **Fallbacks**:
  - LLM fallback invents timeline and strategy when LLM unavailable
- **Inconsistencies**:
  - Multiple sources: investor_strategy_engine EXIT_PREFERENCES, offplan_engine_v2 calculate_exit_strategies, LLM fallback
- **Recommended source of truth**: investor_strategy_engine.py::EXIT_PREFERENCES — deterministic, never LLM-generated

### `holding_period` — Risk: HIGH — LLM fallback fabricates timeline

- **Origin**: User profile.timeline (but LLM fallback invents '3-5 years')
- **Modifiers**:
  - LLM fallback — invents '3-5 years' or '5-7 years' regardless of user input
- **Hardcoded values**:
  - llm_engine.py:908 — 'Hold 3-5 years depending on market conditions'
  - llm_engine.py:722 — 'Hold 5-7 years for rental yield accumulation'
  - llm_engine.py:724 — 'Hold 3-5 years then sell at peak appreciation'
  - llm_engine.py:726 — 'Hold 5 years, monitor market conditions'
- **Fallbacks**:
  - LLM fallback invents '3-5 years' regardless of user's actual timeline
- **Inconsistencies**:
  - Should come from user profile.timeline but LLM fallback invents it
- **Recommended source of truth**: User profile.timeline — never invented by LLM or fallback

### `recommendation` — Risk: HIGH — 3 implementations, 3+ override points, different vocabulary

- **Origin**: utils.py::recommendation_from_score() / offplan_engine_v2.py::offplan_recommendation()
- **Modifiers**:
  - _normalize_recommendation() — converts CAUTION→WATCHLIST
  - rules_engine.py::apply_rules() — downgrades based on rules (uses goal='balanced')
  - recommendation_engine.py inline — fit score gates (fit<40→REVIEW, fit<55→downgrade)
- **Duplicate calculations**:
  - utils.py::recommendation_from_score()
  - offplan_engine_v2.py::offplan_recommendation()
  - recommendation_engine.py inline (fit gates)
- **Fallbacks**:
  - _normalize_recommendation() converts deprecated CAUTION→WATCHLIST at runtime
- **Inconsistencies**:
  - Off-plan uses different vocabulary (NEGOTIATE, AVOID) than ready (WATCHLIST, REVIEW)
- **Recommended source of truth**: utils.py::recommendation_from_score() — unify off-plan to use same function

### `confidence_score` — Risk: HIGH — 5 implementations, no single source of truth

- **Origin**: ready_engine.py inline / offplan_engine_v2.py inline (confidence_engine.py UNUSED)
- **Modifiers**:
  - _normalize_recommendation() — reconstructs pricingConfidence/rentalConfidence if missing
  - rules_engine.py — may downgrade based on confidence <40 or <25
- **Duplicate calculations**:
  - confidence_engine.py (UNUSED)
  - ready_engine.py inline
  - offplan_engine_v2.py inline
  - report_rules_engine.py (per-dimension)
  - _normalize_recommendation()
- **Inconsistencies**:
  - 5 different implementations produce different values for same data
- **Unused calculations**:
  - confidence_engine.py::calculate_confidence() — exists but never called
- **Recommended source of truth**: confidence_engine.py::calculate_confidence() — activate and use everywhere

### `score_label` — Risk: LOW

- **Origin**: utils.py::score_to_label()
- **Recommended source of truth**: Needs analysis

---

## Proposed Future Architecture

- 1. UNIFIED DTO: Both ready and off-plan produce identical output schema with same field names
- 2. SINGLE CONFIDENCE: confidence_engine.py becomes the only confidence calculator
- 3. SINGLE RECOMMENDATION: utils.py::recommendation_from_score() becomes the only recommendation function
- 4. SINGLE FAIR VALUE: market_valuation.py::calculate_fair_value() used by both engines
- 5. PROFILE IMMUTABILITY: Investor profile is passed through every stage without mutation
- 6. RULES AT SCORING TIME: Rules engine runs during scoring, not at API request time
- 7. DETERMINISTIC EXIT: Exit strategy comes from investor_strategy_engine only, never from LLM
- 8. DETERMINISTIC CONTRADICTIONS: Contradiction detection is rule-based, not LLM-based
- 9. NO FALLBACK INVENTION: LLM fallbacks use deterministic data only, never invent values
- 10. SNAPSHOT REGRESSION: Every code change is validated against snapshot tests
