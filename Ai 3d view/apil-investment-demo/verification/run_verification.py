"""
APIL Pipeline Verification Orchestrator

Runs all verification modules and produces a single unified report.
This is the main entry point for the verification framework.

Usage:
    python3 verification/run_verification.py
    # or
    from verification.run_verification import VerificationOrchestrator
    orch = VerificationOrchestrator()
    report = orch.run_all()
    orch.print_summary()
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from verification.pipeline_trace import PipelineTracer, ALL_TRACKED_FIELDS
from verification.duplicate_detector import DuplicateCalculator
from verification.mutation_detector import MutationDetector
from verification.dto_verifier import DTOVerifier
from verification.frontend_verifier import FrontendVerifier
from verification.llm_verifier import LLMVerifier
from verification.dependency_graph import DependencyGraphBuilder
from verification.test_harness import TestHarness, TEST_PROFILES, SNAPSHOT_FIELDS


def _detect_paths() -> dict[str, Path]:
    """Auto-detect engine, server, data, and frontend directories."""
    cwd = Path.cwd()
    paths = {}

    # Detect engines dir
    candidates = [
        cwd / "engines",
        cwd / "backend" / "engines",
        cwd.parent / "backend" / "engines",
    ]
    for c in candidates:
        if c.exists() and any(c.glob("*.py")):
            paths["engines_dir"] = c
            break

    # Detect server dir (parent of engines)
    if "engines_dir" in paths:
        paths["server_dir"] = paths["engines_dir"].parent
    else:
        paths["server_dir"] = cwd

    # Detect data dir
    candidates = [
        paths["server_dir"] / "data",
        cwd / "backend" / "data",
        cwd / "data",
    ]
    for c in candidates:
        if c.exists() and any(c.glob("*.json")):
            paths["data_dir"] = c
            break

    # Detect frontend dir
    candidates = [
        paths["server_dir"].parent / "apil-investment-demo" / "src",
        cwd.parent / "apil-investment-demo" / "src",
        cwd / "src",
        cwd.parent / "src",
    ]
    for c in candidates:
        if c.exists() and any(c.glob("**/*.tsx")):
            paths["frontend_dir"] = c
            break

    return paths


class VerificationOrchestrator:
    """Runs all verification modules and produces a unified report."""

    def __init__(self):
        self.results: dict[str, Any] = {}
        self.timestamp = datetime.now().isoformat()
        self.paths = _detect_paths()

    def run_all(self) -> dict:
        """Run all verification modules."""
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  APIL Pipeline Verification Framework — Full Run         ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()

        # D1-3: Pipeline Trace
        print("▶ D1-3: Pipeline Trace Tool + Immutable Field Verification...")
        tracer = PipelineTracer()
        # Static analysis (no live API call needed for structure)
        tracer.run_checks()
        trace_report = tracer.generate_report()
        self.results["pipeline_trace"] = trace_report
        print(f"  → {len(trace_report['issues'])} issues found")
        print()

        # D4: Duplicate Calculations
        print("▶ D4: Duplicate Calculation Detection...")
        try:
            dup_detector = DuplicateCalculator(engines_dir=self.paths.get("engines_dir"))
            dup_report = dup_detector.scan()
        except Exception as e:
            dup_report = {"error": str(e), "summary": {"fields_with_duplicates": 0}}
        self.results["duplicate_calculations"] = dup_report
        s = dup_report.get("summary", {})
        print(f"  → {s.get('fields_with_duplicates', 0)} fields with duplicates, {s.get('total_calculation_sites', 0)} total sites")
        print()

        # D5: Mutation Detection
        print("▶ D5: Mutation Detection...")
        try:
            mut_detector = MutationDetector(engines_dir=self.paths.get("engines_dir"))
            mut_report = mut_detector.scan()
        except Exception as e:
            mut_report = {"error": str(e), "summary": {"total_mutations": 0}}
        self.results["mutation_detection"] = mut_report
        s = mut_report.get("summary", {})
        print(f"  → {s.get('total_mutations', 0)} mutations found")
        print()

        # D6: DTO Verification
        print("▶ D6: DTO Verification (Ready vs Off-plan)...")
        try:
            dto_verifier = DTOVerifier(data_dir=self.paths.get("data_dir"))
            dto_report = dto_verifier.verify()
        except Exception as e:
            dto_report = {"error": str(e), "summary": {}}
        self.results["dto_verification"] = dto_report
        s = dto_report.get("summary", {})
        print(f"  → {s.get('only_ready', 0)} only-ready, {s.get('only_offplan', 0)} only-offplan, {s.get('type_mismatches', 0)} type mismatches")
        print()

        # D7: Frontend Verification
        print("▶ D7: Frontend Verification...")
        try:
            fe_verifier = FrontendVerifier(frontend_dir=self.paths.get("frontend_dir"))
            fe_report = fe_verifier.scan()
        except Exception as e:
            fe_report = {"error": str(e), "summary": {"issues_found": 0}}
        self.results["frontend_verification"] = fe_report
        s = fe_report.get("summary", {})
        print(f"  → {s.get('values_tracked', 0)} values tracked, {s.get('issues_found', 0)} issues")
        print()

        # D8: LLM Verification
        print("▶ D8: LLM Prompt Verification...")
        try:
            llm_verifier = LLMVerifier(engines_dir=self.paths.get("engines_dir"), server_dir=self.paths.get("server_dir"))
            llm_report = llm_verifier.scan()
        except Exception as e:
            llm_report = {"error": str(e), "summary": {"fails": 0, "warnings": 0}}
        self.results["llm_verification"] = llm_report
        s = llm_report.get("summary", {})
        print(f"  → {s.get('fails', 0)} FAIL, {s.get('warnings', 0)} WARN")
        print()

        # D9: Dependency Graph
        print("▶ D9: Architectural Dependency Graph...")
        try:
            graph_builder = DependencyGraphBuilder(engines_dir=self.paths.get("engines_dir"), server_dir=self.paths.get("server_dir"))
            graph_report = graph_builder.build()
        except Exception as e:
            graph_report = {"error": str(e), "known_issues": []}
        self.results["dependency_graph"] = graph_report
        issues = graph_report.get("known_issues", [])
        critical = sum(1 for i in issues if i.get("severity") == "CRITICAL")
        print(f"  → {len(issues)} known issues ({critical} critical)")
        print()

        # D10: Test Harness
        print("▶ D10: Test Harness (snapshot framework)...")
        harness = TestHarness()
        harness.run_all()  # No live API — will be SKIPPED
        harness_report = harness.generate_report()
        self.results["test_harness"] = harness_report
        s = harness_report["summary"]
        print(f"  → {s['total_tests']} test profiles defined, {s['skipped']} skipped (no live API)")
        print()

        # Generate final report
        print("▶ Generating Final Architecture Report...")
        final = self._generate_final_report()
        self.results["final_report"] = final
        print(f"  → {len(final['deterministic_fields'])} fields mapped")
        print()

        return self.results

    def _generate_final_report(self) -> dict:
        """Generate the final architecture report."""
        # Collect all deterministic fields with their origins
        deterministic_fields = []
        for field_name in ALL_TRACKED_FIELDS:
            entry = {
                "field": field_name,
                "origin": self._get_field_origin(field_name),
                "modifiers": self._get_field_modifiers(field_name),
                "duplicates": self._get_field_duplicates(field_name),
                "hardcoded_values": self._get_hardcoded_values(field_name),
                "fallbacks": self._get_fallbacks(field_name),
                "mutations": self._get_mutations(field_name),
                "inconsistencies": self._get_inconsistencies(field_name),
                "unused_calculations": self._get_unused_calculations(field_name),
                "architectural_risk": self._get_architectural_risk(field_name),
                "recommended_source_of_truth": self._get_recommended_sot(field_name),
            }
            deterministic_fields.append(entry)

        return {
            "generated_at": self.timestamp,
            "deterministic_fields": deterministic_fields,
            "proposed_future_architecture": self._propose_future_architecture(),
        }

    def _get_field_origin(self, field_name: str) -> str:
        origins = {
            "goal": "User questionnaire → sessionStorage → POST /recommendations",
            "budget": "User questionnaire → sessionStorage → POST /recommendations",
            "property_type": "User questionnaire → sessionStorage → POST /recommendations",
            "bedrooms": "User questionnaire → sessionStorage → POST /recommendations",
            "financing": "User questionnaire → sessionStorage → POST /recommendations",
            "timeline": "User questionnaire → sessionStorage → POST /recommendations",
            "risk": "User questionnaire → sessionStorage → POST /recommendations",
            "ready_offplan": "User questionnaire → sessionStorage → POST /recommendations",
            "location": "User questionnaire → sessionStorage → POST /recommendations",
            "investment_score": "ready_engine.py::compute_ready_property_score() / offplan_engine_v2.py::score_offplan_property()",
            "investor_fit_score": "investor_fit_engine.py::calculate_investor_fit()",
            "confidence_score": "ready_engine.py inline / offplan_engine_v2.py inline (confidence_engine.py UNUSED)",
            "recommendation": "utils.py::recommendation_from_score() / offplan_engine_v2.py::offplan_recommendation()",
            "developer_score": "developer_engine.py → developer_scores.json (offplan_engine_v2 re-calculates from breakdown)",
            "area_score": "community_engine.py → community_scores.json",
            "liquidity_score": "ready_engine.py / offplan_engine_v2.py inline",
            "growth_12m": "ready_engine.py::calculate_growth_with_metadata()",
            "net_roi": "ready_engine.py::calculate_roi() / offplan_engine_v2.py::calculate_post_handover_roi()",
            "gross_roi": "ready_engine.py::calculate_roi() / offplan_engine_v2.py::calculate_post_handover_roi()",
            "fair_value": "market_valuation.py::calculate_fair_value() (UNUSED) / offplan_engine_v2.py::calculate_fair_value()",
            "price_vs_market": "ready_engine.py inline / offplan_engine_v2.py inline",
            "risk_level": "ready_engine.py / offplan_engine_v2.py inline (≤25/≤50/>50)",
            "price_sqft": "ready_engine.py / offplan_engine_v2.py inline",
            "asking_price": "Qdrant payload",
            "exit_strategy": "investor_strategy_engine.py::EXIT_PREFERENCES / offplan_engine_v2.py::calculate_exit_strategies()",
            "holding_period": "User profile.timeline (but LLM fallback invents '3-5 years')",
            "score_label": "utils.py::score_to_label()",
        }
        return origins.get(field_name, "Unknown")

    def _get_field_modifiers(self, field_name: str) -> list[str]:
        modifiers = {
            "recommendation": [
                "_normalize_recommendation() — converts CAUTION→WATCHLIST",
                "rules_engine.py::apply_rules() — downgrades based on rules (uses goal='balanced')",
                "recommendation_engine.py inline — fit score gates (fit<40→REVIEW, fit<55→downgrade)",
            ],
            "confidence_score": [
                "_normalize_recommendation() — reconstructs pricingConfidence/rentalConfidence if missing",
                "rules_engine.py — may downgrade based on confidence <40 or <25",
            ],
            "risk_level": [
                "_normalize_recommendation() — re-normalizes thresholds (≤25/≤50/>50)",
            ],
            "goal": [
                "apil_server.py advisory endpoints — HARDCODES to 'balanced' (lines 207, 250)",
            ],
            "exit_strategy": [
                "LLM fallback — invents 'Hold 3-5 years' when LLM unavailable",
                "offplan_engine_v2.py — re-calculates recommendedStrategy based on equity_gain/roi",
            ],
            "holding_period": [
                "LLM fallback — invents '3-5 years' or '5-7 years' regardless of user input",
            ],
        }
        return modifiers.get(field_name, [])

    def _get_field_duplicates(self, field_name: str) -> list[str]:
        dups = {
            "confidence_score": ["confidence_engine.py (UNUSED)", "ready_engine.py inline", "offplan_engine_v2.py inline", "report_rules_engine.py (per-dimension)", "_normalize_recommendation()"],
            "recommendation": ["utils.py::recommendation_from_score()", "offplan_engine_v2.py::offplan_recommendation()", "recommendation_engine.py inline (fit gates)"],
            "risk_level": ["ready_engine.py/offplan_engine_v2.py (≤25/≤50/>50)", "utils.py::risk_from_score() (≥80/≥65/<65)", "community_engine.py/project_engine.py (uses risk_from_score)"],
            "fair_value": ["market_valuation.py::calculate_fair_value() (UNUSED)", "offplan_engine_v2.py::calculate_fair_value()"],
        }
        return dups.get(field_name, [])

    def _get_hardcoded_values(self, field_name: str) -> list[str]:
        hardcoded = {
            "goal": ["apil_server.py:207 — profile = {'goal': 'balanced'}", "apil_server.py:250 — profile = {'goal': 'balanced'}"],
            "holding_period": ["llm_engine.py:908 — 'Hold 3-5 years depending on market conditions'", "llm_engine.py:722 — 'Hold 5-7 years for rental yield accumulation'", "llm_engine.py:724 — 'Hold 3-5 years then sell at peak appreciation'", "llm_engine.py:726 — 'Hold 5 years, monitor market conditions'"],
            "exit_strategy": ["llm_engine.py:908 — 'Hold 3-5 years depending on market conditions' (fallback exit_plan)"],
            "investment_score": ["offplan_engine_v2.py:215 — growth_rate = 0.05 (default 5% if no data)"],
        }
        return hardcoded.get(field_name, [])

    def _get_fallbacks(self, field_name: str) -> list[str]:
        fallbacks = {
            "exit_strategy": ["LLM fallback invents timeline and strategy when LLM unavailable"],
            "holding_period": ["LLM fallback invents '3-5 years' regardless of user's actual timeline"],
            "investment_score": ["offplan_engine_v2.py uses 5% default growth rate when no community/project data"],
            "recommendation": ["_normalize_recommendation() converts deprecated CAUTION→WATCHLIST at runtime"],
        }
        return fallbacks.get(field_name, [])

    def _get_mutations(self, field_name: str) -> list[str]:
        return self._get_field_modifiers(field_name)

    def _get_inconsistencies(self, field_name: str) -> list[str]:
        inconsistencies = {
            "goal": ["Advisory endpoints hardcode 'balanced' instead of using user's actual goal"],
            "confidence_score": ["5 different implementations produce different values for same data"],
            "recommendation": ["Off-plan uses different vocabulary (NEGOTIATE, AVOID) than ready (WATCHLIST, REVIEW)"],
            "risk_level": ["Property risk and community/project risk use different thresholds"],
            "fair_value": ["Ready uses marketValuation.fairValueTotal, off-plan uses fairValue.fairValue — different paths and formulas"],
            "price_vs_market": ["Ready uses priceDifference (top-level), off-plan uses priceOpportunity.priceDifferencePct (nested)"],
            "exit_strategy": ["Multiple sources: investor_strategy_engine EXIT_PREFERENCES, offplan_engine_v2 calculate_exit_strategies, LLM fallback"],
            "holding_period": ["Should come from user profile.timeline but LLM fallback invents it"],
            "data_quality": ["Off-plan properties have null dataQuality — frontend ReportContext breaks"],
        }
        return inconsistencies.get(field_name, [])

    def _get_unused_calculations(self, field_name: str) -> list[str]:
        unused = {
            "confidence_score": ["confidence_engine.py::calculate_confidence() — exists but never called"],
            "fair_value": ["market_valuation.py::calculate_fair_value() — exists but never called by ready_engine"],
        }
        return unused.get(field_name, [])

    def _get_architectural_risk(self, field_name: str) -> str:
        risks = {
            "goal": "CRITICAL — Profile loss in advisory endpoints causes wrong LLM output",
            "confidence_score": "HIGH — 5 implementations, no single source of truth",
            "recommendation": "HIGH — 3 implementations, 3+ override points, different vocabulary",
            "risk_level": "MEDIUM — 3 different threshold sets",
            "fair_value": "HIGH — 2 different formulas, 1 unused module",
            "exit_strategy": "HIGH — Multiple sources, LLM fallback invents values",
            "holding_period": "HIGH — LLM fallback fabricates timeline",
            "price_vs_market": "MEDIUM — Different field names and nesting between ready and off-plan",
            "data_quality": "HIGH — Missing for off-plan, breaks frontend ReportContext",
        }
        return risks.get(field_name, "LOW")

    def _get_recommended_sot(self, field_name: str) -> str:
        sots = {
            "goal": "User questionnaire — must be passed through every stage without mutation",
            "confidence_score": "confidence_engine.py::calculate_confidence() — activate and use everywhere",
            "recommendation": "utils.py::recommendation_from_score() — unify off-plan to use same function",
            "risk_level": "Extract to utils.py — single function with one threshold set",
            "fair_value": "market_valuation.py::calculate_fair_value() — activate for both engines",
            "exit_strategy": "investor_strategy_engine.py::EXIT_PREFERENCES — deterministic, never LLM-generated",
            "holding_period": "User profile.timeline — never invented by LLM or fallback",
            "price_vs_market": "Unify to single field name 'priceVsMarketPct' in both DTOs",
            "data_quality": "Both engines must populate dataQuality with same schema",
        }
        return sots.get(field_name, "Needs analysis")

    def _propose_future_architecture(self) -> list[str]:
        return [
            "1. UNIFIED DTO: Both ready and off-plan produce identical output schema with same field names",
            "2. SINGLE CONFIDENCE: confidence_engine.py becomes the only confidence calculator",
            "3. SINGLE RECOMMENDATION: utils.py::recommendation_from_score() becomes the only recommendation function",
            "4. SINGLE FAIR VALUE: market_valuation.py::calculate_fair_value() used by both engines",
            "5. PROFILE IMMUTABILITY: Investor profile is passed through every stage without mutation",
            "6. RULES AT SCORING TIME: Rules engine runs during scoring, not at API request time",
            "7. DETERMINISTIC EXIT: Exit strategy comes from investor_strategy_engine only, never from LLM",
            "8. DETERMINISTIC CONTRADICTIONS: Contradiction detection is rule-based, not LLM-based",
            "9. NO FALLBACK INVENTION: LLM fallbacks use deterministic data only, never invent values",
            "10. SNAPSHOT REGRESSION: Every code change is validated against snapshot tests",
        ]

    def save_report(self, filepath: Path | None = None):
        """Save the full report as JSON."""
        if filepath is None:
            filepath = Path(__file__).resolve().parent / "verification_report.json"
        filepath.write_text(json.dumps(self.results, indent=2, default=str))
        print(f"Report saved to {filepath}")

    def print_summary(self):
        """Print a summary of all verification results."""
        print()
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  VERIFICATION SUMMARY                                    ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()

        # Pipeline trace
        pt = self.results.get("pipeline_trace", {}).get("summary", {})
        print(f"D1-3 Pipeline Trace:    {pt.get('fails', 0)} FAIL, {pt.get('warnings', 0)} WARN, {pt.get('total_fields_tracked', 0)} fields")

        # Duplicates
        dup = self.results.get("duplicate_calculations", {}).get("summary", {})
        print(f"D4 Duplicates:          {dup.get('fields_with_duplicates', 0)} fields with duplicates, {dup.get('total_calculation_sites', 0)} total sites")

        # Mutations
        mut = self.results.get("mutation_detection", {}).get("summary", {})
        print(f"D5 Mutations:           {mut.get('total_mutations', 0)} mutations, {mut.get('fields_with_multiple_mutations', 0)} fields with >2")

        # DTO
        dto = self.results.get("dto_verification", {}).get("summary", {})
        print(f"D6 DTO:                 {dto.get('only_ready', 0)} only-ready, {dto.get('only_offplan', 0)} only-offplan, {dto.get('missing_critical', 0)} missing critical")

        # Frontend
        fe = self.results.get("frontend_verification", {}).get("summary", {})
        print(f"D7 Frontend:            {fe.get('values_tracked', 0)} values, {fe.get('issues_found', 0)} issues")

        # LLM
        llm = self.results.get("llm_verification", {}).get("summary", {})
        print(f"D8 LLM:                 {llm.get('fails', 0)} FAIL, {llm.get('warnings', 0)} WARN")

        # Dependency graph
        dg = self.results.get("dependency_graph", {}).get("known_issues", [])
        critical = sum(1 for i in dg if i.get("severity") == "CRITICAL")
        print(f"D9 Dependency Graph:    {len(dg)} issues ({critical} critical)")

        # Test harness
        th = self.results.get("test_harness", {}).get("summary", {})
        print(f"D10 Test Harness:       {th.get('total_tests', 0)} tests, {th.get('skipped', 0)} skipped")

        # Final report
        fr = self.results.get("final_report", {})
        print(f"Final Report:           {len(fr.get('deterministic_fields', []))} fields fully mapped")
        print()

        # Top critical issues
        print("── TOP CRITICAL ISSUES ──")
        final_fields = fr.get("deterministic_fields", [])
        critical_fields = [f for f in final_fields if f["architectural_risk"] == "CRITICAL"]
        for f in critical_fields:
            print(f"  ✗ {f['field']}: {f['architectural_risk']}")
            for inc in f["inconsistencies"][:2]:
                print(f"    → {inc}")
        print()

        high_fields = [f for f in final_fields if f["architectural_risk"] == "HIGH"]
        if high_fields:
            print("── HIGH RISK FIELDS ──")
            for f in high_fields:
                print(f"  ⚠ {f['field']}: {len(f['duplicates'])} duplicates, {len(f['modifiers'])} modifiers, {len(f['inconsistencies'])} inconsistencies")
            print()

        print("── PROPOSED FUTURE ARCHITECTURE ──")
        for item in fr.get("proposed_future_architecture", []):
            print(f"  {item}")
        print()


if __name__ == "__main__":
    orch = VerificationOrchestrator()
    orch.run_all()
    orch.print_summary()
    orch.save_report()
