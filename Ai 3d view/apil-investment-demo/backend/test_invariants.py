"""
APIL Backend Invariant Tests — pytest
Tests all 12 business logic invariants across the API.
Run: pytest test_invariants.py -v
"""
import pytest
import requests
import json

BASE = "http://localhost:8090"

PROFILES = [
    {"goal": "capital_growth", "budget": "500k-2m", "property_type": "apartment", "bedrooms": "2", "ready_offplan": "offplan", "timeline": "3-5y", "financing": "cash", "risk": "medium"},
    {"goal": "rental_income", "budget": "500k-1m", "property_type": "apartment", "bedrooms": "1", "ready_offplan": "ready", "timeline": "3-5y", "financing": "mortgage", "risk": "low"},
    {"goal": "balanced", "budget": "1m-2m", "property_type": "any", "bedrooms": "2", "ready_offplan": "either", "timeline": "3-5y", "financing": "cash", "risk": "medium"},
    {"goal": "flip_handover", "budget": "500k-1m", "property_type": "apartment", "bedrooms": "1", "ready_offplan": "offplan", "timeline": "1-2y", "financing": "cash", "risk": "high"},
    {"goal": "capital_growth", "budget": "2m-5m", "property_type": "villa", "bedrooms": "3", "ready_offplan": "ready", "timeline": "5y+", "financing": "cash", "risk": "medium"},
    {"goal": "end_user", "budget": "1m-2m", "property_type": "apartment", "bedrooms": "2", "ready_offplan": "ready", "timeline": "5y+", "financing": "mortgage", "risk": "low"},
    {"goal": "rental_income", "budget": "500k-1m", "property_type": "apartment", "bedrooms": "studio", "ready_offplan": "offplan", "timeline": "3-5y", "financing": "cash", "risk": "low"},
    {"goal": "diversification", "budget": "1m-2m", "property_type": "any", "bedrooms": "2", "ready_offplan": "either", "timeline": "5y+", "financing": "cash", "risk": "medium"},
]


@pytest.fixture(scope="module")
def api_health():
    r = requests.get(f"{BASE}/health", timeout=10)
    assert r.status_code == 200
    return r.json()


@pytest.fixture(params=PROFILES)
def recommendation(request):
    profile = dict(request.param)
    r = requests.post(f"{BASE}/recommendations", json=profile, timeout=60)
    assert r.status_code == 200, f"API returned {r.status_code}"
    return {"data": r.json(), "profile": profile}


# ═══════════════════════════════════════════════════════════
# Issue 1: Timeline consistency
# ═══════════════════════════════════════════════════════════
class TestTimelineConsistency:
    def test_holding_period_matches_profile(self, recommendation):
        profile = recommendation["profile"]
        data = recommendation["data"]
        strategy = data.get("investorStrategy", {})
        assert strategy.get("holding_period") == profile["timeline"], \
            f"Timeline mismatch: profile={profile['timeline']}, strategy={strategy.get('holding_period')}"

    def test_holding_description_contains_period(self, recommendation):
        profile = recommendation["profile"]
        data = recommendation["data"]
        strategy = data.get("investorStrategy", {})
        desc = strategy.get("holding_description", "")
        assert profile["timeline"] in desc, \
            f"holding_description '{desc}' doesn't contain timeline '{profile['timeline']}'"

    def test_exit_strategy_accounts_for_timeline(self, recommendation):
        profile = recommendation["profile"]
        data = recommendation["data"]
        contract = data.get("reportContract", {})
        exit_s = contract.get("exit_strategy", "")
        assert len(exit_s) > 10, "Exit strategy is empty or too short"
        # 5y+ should mention hold/long-term, 1-2y should mention sell/assignment
        if profile["timeline"] == "1-2y":
            assert any(w in exit_s.lower() for w in ["sell", "assignment", "handover", "flip"]), \
                f"1-2y exit strategy should mention sell/assignment: {exit_s}"
        elif profile["timeline"] == "5y+":
            assert any(w in exit_s.lower() for w in ["hold", "long", "appreciation", "rent"]), \
                f"5y+ exit strategy should mention hold/long-term: {exit_s}"


# ═══════════════════════════════════════════════════════════
# Issue 2: Bedroom consistency
# ═══════════════════════════════════════════════════════════
class TestBedroomConsistency:
    def test_top_property_bedroom_matches_or_adjacent(self, recommendation):
        profile = recommendation["profile"]
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if not recs:
            pytest.skip("No recommendations")
        
        bed = profile["bedrooms"]
        bt = recs[0].get("bedType", "").lower()
        
        if bed == "studio":
            assert "studio" in bt or "1" in bt, \
                f"Profile studio but got {bt}"
        elif bed == "1":
            assert "studio" in bt or "1" in bt, \
                f"Profile 1BR but got {bt}"
        elif bed == "2":
            assert "1" in bt or "2" in bt or "3" in bt, \
                f"Profile 2BR but got {bt} (should be 1-3BR)"
        elif bed == "3":
            assert "2" in bt or "3" in bt or "4" in bt or "5" in bt, \
                f"Profile 3BR but got {bt}"

    def test_no_studio_for_2br_request(self, recommendation):
        profile = recommendation["profile"]
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if not recs or profile["bedrooms"] != "2":
            pytest.skip("Not a 2BR profile")
        
        for rec in recs:
            bt = rec.get("bedType", "").lower()
            assert "studio" not in bt, \
                f"Studio returned for 2BR request: {bt}"


# ═══════════════════════════════════════════════════════════
# Issue 3/11: Alternative ranking consistency
# ═══════════════════════════════════════════════════════════
class TestAlternativeRanking:
    def test_all_alternatives_have_scores(self, recommendation):
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if len(recs) < 2:
            pytest.skip("Not enough recommendations")
        
        for i, rec in enumerate(recs):
            score = rec.get("offplanScore", 0) or rec.get("readyScore", 0)
            assert score > 0, \
                f"Recommendation #{i+1} has score 0: offplanScore={rec.get('offplanScore')}, readyScore={rec.get('readyScore')}"

    def test_alternatives_have_developer_scores(self, recommendation):
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if len(recs) < 2:
            pytest.skip("Not enough recommendations")
        
        for i, rec in enumerate(recs):
            if rec.get("propertyType") == "offplan":
                dev = rec.get("developerData", {})
                ds = dev.get("developerScore")
                assert ds is not None and ds > 0, \
                    f"Recommendation #{i+1} offplan has developerScore={ds}"

    def test_top_score_is_highest(self, recommendation):
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if len(recs) < 2:
            pytest.skip("Not enough recommendations")
        
        top_score = recs[0].get("offplanScore", 0) or recs[0].get("readyScore", 0)
        for i, rec in enumerate(recs[1:], 2):
            score = rec.get("offplanScore", 0) or rec.get("readyScore", 0)
            assert score <= top_score, \
                f"Alternative #{i} score {score} > top score {top_score}"


# ═══════════════════════════════════════════════════════════
# Issue 4-7: AI grounding / Rule flags
# ═══════════════════════════════════════════════════════════
class TestRuleFlags:
    def test_rules_flags_are_human_readable(self, recommendation):
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if not recs:
            pytest.skip("No recommendations")
        
        flags = recs[0].get("rulesFlags", [])
        human = recs[0].get("rulesFlagsHuman", [])
        
        # If flags exist, human-readable versions must exist
        if flags:
            assert len(human) == len(flags), \
                f"rulesFlags has {len(flags)} items but rulesFlagsHuman has {len(human)}"
            for h in human:
                assert not h.startswith("RULE_"), \
                    f"Human-readable flag still contains internal code: {h}"

    def test_no_raw_rule_codes_in_human_flags(self, recommendation):
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if not recs:
            pytest.skip("No recommendations")
        
        human = recs[0].get("rulesFlagsHuman", [])
        for h in human:
            assert "RULE_" not in h, \
                f"Human flag contains RULE_ prefix: {h}"


# ═══════════════════════════════════════════════════════════
# Issue 8: Recommendation vocabulary
# ═══════════════════════════════════════════════════════════
class TestRecommendationVocab:
    def test_no_caution_in_recommendation(self, recommendation):
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if not recs:
            pytest.skip("No recommendations")
        
        for rec in recs:
            rec_label = rec.get("recommendation", "")
            assert "CAUTION" not in rec_label, \
                f"Recommendation contains deprecated 'CAUTION': {rec_label}"

    def test_recommendation_is_valid_vocab(self, recommendation):
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if not recs:
            pytest.skip("No recommendations")
        
        VALID = {"STRONG BUY", "BUY", "BUY IF NEGOTIATED", "HOLD", "WATCHLIST", "REVIEW", "INSUFFICIENT_DATA", "AVOID"}
        for rec in recs:
            label = rec.get("recommendation", "")
            assert label in VALID, \
                f"Invalid recommendation vocab: '{label}' not in {VALID}"


# ═══════════════════════════════════════════════════════════
# Issue 9: Risk consistency
# ═══════════════════════════════════════════════════════════
class TestRiskConsistency:
    def test_risk_components_present_for_offplan(self, recommendation):
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if not recs or recs[0].get("propertyType") != "offplan":
            pytest.skip("Not an offplan recommendation")
        
        risk = recs[0].get("risk", {})
        comps = risk.get("components", {})
        assert len(comps) >= 5, \
            f"Offplan risk should have >=5 components, got {len(comps)}: {list(comps.keys())}"

    def test_risk_level_matches_overall(self, recommendation):
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if not recs:
            pytest.skip("No recommendations")
        
        risk = recs[0].get("risk", {})
        overall = risk.get("overallRisk", 0)
        level = risk.get("riskLevel", "")
        
        if overall <= 25:
            assert level == "Low", f"overallRisk={overall} but riskLevel={level}"
        elif overall <= 50:
            assert level == "Medium", f"overallRisk={overall} but riskLevel={level}"
        elif overall > 50:
            assert level == "High", f"overallRisk={overall} but riskLevel={level}"

    def test_developer_tier_not_none(self, recommendation):
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if not recs:
            pytest.skip("No recommendations")
        
        for rec in recs:
            if rec.get("propertyType") == "offplan":
                dev = rec.get("developerData", {})
                tier = dev.get("marketPosition")
                assert tier is not None, \
                    f"marketPosition is None for developer {dev.get('developerName')}"
                assert "Tier" in str(tier), \
                    f"marketPosition should contain 'Tier': {tier}"


# ═══════════════════════════════════════════════════════════
# Issue 10/12: Confidence consistency
# ═══════════════════════════════════════════════════════════
class TestConfidenceConsistency:
    def test_confidence_explanation_present(self, recommendation):
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if not recs:
            pytest.skip("No recommendations")
        
        if recs[0].get("propertyType") == "offplan":
            ce = recs[0].get("confidenceExplanation")
            assert ce is not None and len(ce) > 10, \
                f"confidenceExplanation missing or too short: {ce}"

    def test_confidence_score_in_valid_range(self, recommendation):
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        if not recs:
            pytest.skip("No recommendations")
        
        score = recs[0].get("confidenceScore", 0)
        assert 0 <= score <= 100, \
            f"confidenceScore out of range: {score}"


# ═══════════════════════════════════════════════════════════
# Issue 11: Property type consistency
# ═══════════════════════════════════════════════════════════
class TestPropertyTypeConsistency:
    def test_offplan_profile_gets_offplan_properties(self, recommendation):
        profile = recommendation["profile"]
        data = recommendation["data"]
        if profile["ready_offplan"] != "offplan":
            pytest.skip("Not an offplan-only profile")
        
        recs = data.get("recommendations", [])
        for rec in recs:
            assert rec.get("propertyType") == "offplan", \
                f"Profile requested offplan-only but got propertyType={rec.get('propertyType')}"

    def test_ready_profile_gets_ready_properties(self, recommendation):
        profile = recommendation["profile"]
        data = recommendation["data"]
        if profile["ready_offplan"] != "ready":
            pytest.skip("Not a ready-only profile")
        
        recs = data.get("recommendations", [])
        for rec in recs:
            assert rec.get("propertyType") == "ready", \
                f"Profile requested ready-only but got propertyType={rec.get('propertyType')}"


# ═══════════════════════════════════════════════════════════
# Structural tests
# ═══════════════════════════════════════════════════════════
class TestResponseStructure:
    def test_has_investor_strategy(self, recommendation):
        data = recommendation["data"]
        assert "investorStrategy" in data, "Missing investorStrategy"
        s = data["investorStrategy"]
        for field in ["goal", "holding_period", "exit_strategy", "strategy_summary"]:
            assert field in s, f"investorStrategy missing field: {field}"

    def test_has_report_contract(self, recommendation):
        data = recommendation["data"]
        c = data.get("reportContract")
        assert c is not None, "Missing reportContract"
        assert "exit_strategy" in c, "reportContract missing exit_strategy"

    def test_has_report_validation(self, recommendation):
        data = recommendation["data"]
        v = data.get("reportValidation")
        assert v is not None, "Missing reportValidation"
        assert "valid" in v, "reportValidation missing 'valid' field"
        assert "total_assertions" in v, "reportValidation missing 'total_assertions'"

    def test_has_recommendation_confidence(self, recommendation):
        data = recommendation["data"]
        rc = data.get("recommendationConfidence")
        assert rc is not None, "Missing recommendationConfidence"

    def test_recommendations_not_empty(self, recommendation):
        data = recommendation["data"]
        recs = data.get("recommendations", [])
        assert len(recs) > 0, "No recommendations returned"
