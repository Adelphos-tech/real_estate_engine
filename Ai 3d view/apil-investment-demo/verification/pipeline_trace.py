"""
Pipeline Trace Tool — D1, D2, D3

Traces every deterministic field from User Input → Recommendation Engine → Rules Engine
→ Report Contract → API Response → Frontend Mapping → LLM Input.

If any immutable field changes between stages, it is reported as FAIL.

Usage:
    from verification.pipeline_trace import PipelineTracer
    tracer = PipelineTracer()
    tracer.trace_profile(profile, api_response, frontend_props)
    report = tracer.generate_report()
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ─── Stages ───

STAGES = [
    "USER_INPUT",
    "RECOMMENDATION_ENGINE",
    "RULES_ENGINE",
    "REPORT_CONTRACT",
    "API_RESPONSE",
    "FRONTEND_MAPPING",
    "FRONTEND_RENDER",
    "LLM_INPUT",
]

# ─── Immutable fields that must never change after user input ───

IMMUTABLE_PROFILE_FIELDS = [
    "goal",
    "budget",
    "property_type",
    "bedrooms",
    "financing",
    "timeline",
    "risk",
    "ready_offplan",
    "location",
]

# ─── Deterministic fields that must be tracked ───

DETERMINISTIC_SCORE_FIELDS = [
    "investment_score",
    "investor_fit_score",
    "confidence_score",
    "recommendation",
    "developer_score",
    "area_score",
    "liquidity_score",
    "growth_12m",
    "net_roi",
    "gross_roi",
    "fair_value",
    "price_vs_market",
    "risk_level",
    "price_sqft",
    "asking_price",
]

DETERMINISTIC_REPORT_FIELDS = [
    "exit_strategy",
    "holding_period",
    "recommendation",
    "confidence_score",
    "score_label",
]

ALL_TRACKED_FIELDS = IMMUTABLE_PROFILE_FIELDS + DETERMINISTIC_SCORE_FIELDS + DETERMINISTIC_REPORT_FIELDS


@dataclass
class FieldTrace:
    """Tracks a single field through all pipeline stages."""
    field_name: str
    values_by_stage: dict[str, Any] = field(default_factory=dict)
    is_immutable: bool = False

    def set_stage_value(self, stage: str, value: Any):
        self.values_by_stage[stage] = value

    def check_consistency(self) -> list[dict]:
        """Check if this field's value changed unexpectedly between stages."""
        issues = []
        if self.is_immutable:
            # Immutable fields must never change after USER_INPUT
            input_val = self.values_by_stage.get("USER_INPUT")
            if input_val is not None:
                for stage in STAGES[1:]:
                    stage_val = self.values_by_stage.get(stage)
                    if stage_val is not None and stage_val != input_val:
                        issues.append({
                            "field": self.field_name,
                            "stage": stage,
                            "expected": input_val,
                            "actual": stage_val,
                            "status": "FAIL",
                            "reason": f"Immutable field changed from '{input_val}' to '{stage_val}' at {stage}",
                        })
        else:
            # Deterministic fields: track all changes, flag if different from engine output
            engine_val = self.values_by_stage.get("RECOMMENDATION_ENGINE")
            if engine_val is not None:
                for stage in STAGES[2:]:
                    stage_val = self.values_by_stage.get(stage)
                    if stage_val is not None and stage_val != engine_val:
                        issues.append({
                            "field": self.field_name,
                            "stage": stage,
                            "expected": engine_val,
                            "actual": stage_val,
                            "status": "WARN",
                            "reason": f"Field changed from '{engine_val}' to '{stage_val}' between ENGINE and {stage}",
                        })
        return issues


@dataclass
class StageComparisonRow:
    """One row in the stage comparison table."""
    field: str
    user_input: Any = "—"
    engine: Any = "—"
    rules: Any = "—"
    report_contract: Any = "—"
    api_response: Any = "—"
    frontend_mapping: Any = "—"
    frontend_render: Any = "—"
    llm_input: Any = "—"
    status: str = "PASS"

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "user_input": str(self.user_input),
            "engine": str(self.engine),
            "rules": str(self.rules),
            "report_contract": str(self.report_contract),
            "api_response": str(self.api_response),
            "frontend_mapping": str(self.frontend_mapping),
            "frontend_render": str(self.frontend_render),
            "llm_input": str(self.llm_input),
            "status": self.status,
        }


class PipelineTracer:
    """Main tracer that tracks all fields through all stages."""

    def __init__(self):
        self.traces: dict[str, FieldTrace] = {}
        self.issues: list[dict] = []
        self.comparison_rows: list[StageComparisonRow] = []

        # Initialize traces for all tracked fields
        for f in IMMUTABLE_PROFILE_FIELDS:
            self.traces[f] = FieldTrace(field_name=f, is_immutable=True)
        for f in DETERMINISTIC_SCORE_FIELDS + DETERMINISTIC_REPORT_FIELDS:
            self.traces[f] = FieldTrace(field_name=f, is_immutable=False)

    # ─── Stage capture methods ───

    def capture_user_input(self, profile: dict):
        """Capture fields from the user questionnaire."""
        for f in IMMUTABLE_PROFILE_FIELDS:
            val = profile.get(f)
            if val is not None:
                self.traces[f].set_stage_value("USER_INPUT", val)

    def capture_engine_output(self, property_data: dict, strategy: dict | None = None):
        """Capture fields from the recommendation engine output."""
        # Map engine field names to tracked field names
        field_map = {
            "investment_score": property_data.get("readyScore") or property_data.get("offplanScore"),
            "investor_fit_score": property_data.get("investorFit", {}).get("fitScore") if isinstance(property_data.get("investorFit"), dict) else None,
            "confidence_score": property_data.get("confidenceScore"),
            "recommendation": property_data.get("recommendation"),
            "developer_score": property_data.get("developerData", {}).get("developerScore") if isinstance(property_data.get("developerData"), dict) else property_data.get("developerScore"),
            "area_score": property_data.get("communityData", {}).get("communityScore") if isinstance(property_data.get("communityData"), dict) else property_data.get("communityScore"),
            "liquidity_score": property_data.get("liquidity", {}).get("liquidityScore") if isinstance(property_data.get("liquidity"), dict) else None,
            "growth_12m": property_data.get("growth12m"),
            "net_roi": property_data.get("roi", {}).get("netROI") if isinstance(property_data.get("roi"), dict) else property_data.get("postHandoverROI", {}).get("netROI") if isinstance(property_data.get("postHandoverROI"), dict) else None,
            "gross_roi": property_data.get("roi", {}).get("grossROI") if isinstance(property_data.get("roi"), dict) else property_data.get("postHandoverROI", {}).get("grossROI") if isinstance(property_data.get("postHandoverROI"), dict) else None,
            "fair_value": property_data.get("marketValuation", {}).get("fairValueTotal") if isinstance(property_data.get("marketValuation"), dict) else property_data.get("fairValue", {}).get("fairValue") if isinstance(property_data.get("fairValue"), dict) else None,
            "price_vs_market": property_data.get("priceDifference") or property_data.get("priceOpportunity", {}).get("priceDifferencePct") if isinstance(property_data.get("priceOpportunity"), dict) else property_data.get("priceDifference"),
            "risk_level": property_data.get("risk", {}).get("riskLevel") if isinstance(property_data.get("risk"), dict) else None,
            "price_sqft": property_data.get("priceSqft"),
            "asking_price": property_data.get("askingPrice"),
        }
        for tracked_name, value in field_map.items():
            if value is not None:
                self.traces[tracked_name].set_stage_value("RECOMMENDATION_ENGINE", value)

        # Capture profile fields from strategy
        if strategy:
            goal = strategy.get("goal")
            if goal:
                self.traces["goal"].set_stage_value("RECOMMENDATION_ENGINE", goal)

        # Exit strategy
        exit_strat = None
        if strategy and isinstance(strategy.get("exit_strategy"), str):
            exit_strat = strategy["exit_strategy"]
        elif isinstance(property_data.get("exitStrategies"), dict):
            exit_strat = property_data["exitStrategies"].get("recommendedStrategy")
        if exit_strat:
            self.traces["exit_strategy"].set_stage_value("RECOMMENDATION_ENGINE", exit_strat)

    def capture_rules_output(self, property_data: dict, goal: str | None = None):
        """Capture fields after rules engine has run."""
        rec = property_data.get("recommendation")
        if rec:
            self.traces["recommendation"].set_stage_value("RULES_ENGINE", rec)
        if goal:
            self.traces["goal"].set_stage_value("RULES_ENGINE", goal)
        flags = property_data.get("rulesFlags", [])
        if flags:
            self.traces["recommendation"].set_stage_value("RULES_ENGINE_FLAGS", flags)

    def capture_report_contract(self, report_contract: dict | None):
        """Capture fields from the report contract."""
        if not report_contract:
            return
        if report_contract.get("exit_strategy"):
            self.traces["exit_strategy"].set_stage_value("REPORT_CONTRACT", report_contract["exit_strategy"])
        if report_contract.get("goal"):
            self.traces["goal"].set_stage_value("REPORT_CONTRACT", report_contract["goal"])
        if report_contract.get("recommendation", {}).get("value"):
            self.traces["recommendation"].set_stage_value("REPORT_CONTRACT", report_contract["recommendation"]["value"])

    def capture_api_response(self, top_rec: dict, profile: dict | None = None):
        """Capture fields from the API response."""
        # Profile fields
        if profile:
            for f in IMMUTABLE_PROFILE_FIELDS:
                val = profile.get(f)
                if val is not None:
                    self.traces[f].set_stage_value("API_RESPONSE", val)

        # Property fields
        field_map = {
            "investment_score": top_rec.get("readyScore") or top_rec.get("offplanScore"),
            "confidence_score": top_rec.get("confidenceScore"),
            "recommendation": top_rec.get("recommendation"),
            "asking_price": top_rec.get("askingPrice"),
            "price_sqft": top_rec.get("priceSqft"),
        }
        for tracked_name, value in field_map.items():
            if value is not None:
                self.traces[tracked_name].set_stage_value("API_RESPONSE", value)

        # Exit strategy from investorFit or exitStrategies
        if isinstance(top_rec.get("exitStrategies"), dict):
            es = top_rec["exitStrategies"].get("recommendedStrategy")
            if es:
                self.traces["exit_strategy"].set_stage_value("API_RESPONSE", es)

    def capture_frontend_mapping(self, mapped_property: dict, ctx: dict | None = None):
        """Capture fields after frontend legacy mapping."""
        field_map = {
            "investment_score": mapped_property.get("overallScore") or mapped_property.get("propertyScore"),
            "recommendation": mapped_property.get("recommendation"),
            "developer_score": mapped_property.get("developerScore"),
            "liquidity_score": mapped_property.get("liquidityScore"),
            "risk_level": mapped_property.get("riskLevel"),
            "growth_12m": mapped_property.get("growth12m"),
            "net_roi": mapped_property.get("netROI"),
            "gross_roi": mapped_property.get("grossROI"),
            "asking_price": mapped_property.get("askingPrice"),
        }
        for tracked_name, value in field_map.items():
            if value is not None:
                self.traces[tracked_name].set_stage_value("FRONTEND_MAPPING", value)

        if ctx:
            goal = ctx.get("investorGoal")
            if goal:
                self.traces["goal"].set_stage_value("FRONTEND_MAPPING", goal.lower())
            conf = ctx.get("confidenceScore")
            if conf is not None:
                self.traces["confidence_score"].set_stage_value("FRONTEND_MAPPING", conf)

    def capture_frontend_render(self, rendered_values: dict):
        """Capture fields as actually rendered in the UI."""
        for k, v in rendered_values.items():
            if k in self.traces:
                self.traces[k].set_stage_value("FRONTEND_RENDER", v)

    def capture_llm_input(self, llm_profile: dict, llm_property_data: dict):
        """Capture fields as passed to the LLM."""
        if llm_profile:
            goal = llm_profile.get("goal")
            if goal:
                self.traces["goal"].set_stage_value("LLM_INPUT", goal)
            risk = llm_profile.get("risk")
            if risk:
                self.traces["risk"].set_stage_value("LLM_INPUT", risk)

        if llm_property_data:
            rec = llm_property_data.get("recommendation")
            if rec:
                self.traces["recommendation"].set_stage_value("LLM_INPUT", rec)
            score = llm_property_data.get("readyScore") or llm_property_data.get("offplanScore")
            if score:
                self.traces["investment_score"].set_stage_value("LLM_INPUT", score)
            conf = llm_property_data.get("confidenceScore")
            if conf is not None:
                self.traces["confidence_score"].set_stage_value("LLM_INPUT", conf)

    # ─── Reporting ───

    def run_checks(self):
        """Run all consistency checks and populate issues."""
        self.issues = []
        for trace in self.traces.values():
            self.issues.extend(trace.check_consistency())

    def generate_comparison_table(self) -> list[dict]:
        """Generate the stage comparison table."""
        self.comparison_rows = []
        for field_name in ALL_TRACKED_FIELDS:
            trace = self.traces.get(field_name)
            if not trace:
                continue
            row = StageComparisonRow(field=field_name)
            row.user_input = trace.values_by_stage.get("USER_INPUT", "—")
            row.engine = trace.values_by_stage.get("RECOMMENDATION_ENGINE", "—")
            row.rules = trace.values_by_stage.get("RULES_ENGINE", "—")
            row.report_contract = trace.values_by_stage.get("REPORT_CONTRACT", "—")
            row.api_response = trace.values_by_stage.get("API_RESPONSE", "—")
            row.frontend_mapping = trace.values_by_stage.get("FRONTEND_MAPPING", "—")
            row.frontend_render = trace.values_by_stage.get("FRONTEND_RENDER", "—")
            row.llm_input = trace.values_by_stage.get("LLM_INPUT", "—")

            # Determine status
            field_issues = [i for i in self.issues if i["field"] == field_name]
            if any(i["status"] == "FAIL" for i in field_issues):
                row.status = "FAIL"
            elif any(i["status"] == "WARN" for i in field_issues):
                row.status = "WARN"
            else:
                row.status = "PASS"

            self.comparison_rows.append(row.to_dict())
        return self.comparison_rows

    def generate_report(self) -> dict:
        """Generate the full trace report."""
        self.run_checks()
        comparison = self.generate_comparison_table()
        fails = [i for i in self.issues if i["status"] == "FAIL"]
        warns = [i for i in self.issues if i["status"] == "WARN"]
        return {
            "summary": {
                "total_fields_tracked": len(self.traces),
                "total_issues": len(self.issues),
                "fails": len(fails),
                "warnings": len(warns),
                "stages_traced": STAGES,
            },
            "issues": self.issues,
            "stage_comparison": comparison,
            "field_traces": {
                name: trace.values_by_stage
                for name, trace in self.traces.items()
                if trace.values_by_stage
            },
        }

    def print_trace(self):
        """Print a human-readable trace for each field."""
        self.run_checks()
        print("=" * 80)
        print("PIPELINE TRACE — Field Consistency Report")
        print("=" * 80)
        print()
        for field_name in ALL_TRACKED_FIELDS:
            trace = self.traces.get(field_name)
            if not trace or not trace.values_by_stage:
                continue
            print(f"── {field_name} {'(IMMUTABLE)' if trace.is_immutable else ''} ──")
            for stage in STAGES:
                val = trace.values_by_stage.get(stage)
                if val is not None:
                    print(f"  {stage:25s} → {val}")
            field_issues = [i for i in self.issues if i["field"] == field_name]
            if field_issues:
                for issue in field_issues:
                    print(f"  ⚠ {issue['status']}: {issue['reason']}")
            else:
                print("  ✓ PASS")
            print()

        # Summary
        fails = [i for i in self.issues if i["status"] == "FAIL"]
        warns = [i for i in self.issues if i["status"] == "WARN"]
        print("=" * 80)
        print(f"SUMMARY: {len(fails)} FAIL, {len(warns)} WARN, {len(self.traces)} fields tracked")
        print("=" * 80)
