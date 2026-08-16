"""
Test Harness with Snapshots — D10

Creates automated regression tests with snapshot capability.
Supports snapshot creation, comparison, and reporting.

Usage:
    from verification.test_harness import TestHarness
    harness = TestHarness()
    harness.run_all()
    report = harness.generate_report()
    harness.print_report()
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"


@dataclass
class Snapshot:
    """A snapshot of all deterministic fields for a given input."""
    test_name: str
    input_profile: dict
    expected_fields: dict[str, Any] = field(default_factory=dict)
    actual_fields: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    status: str = "UNKNOWN"  # PASS, FAIL, NEW_SNAPSHOT
    diffs: list[dict] = field(default_factory=list)


# ─── Test profiles ───

TEST_PROFILES = [
    {
        "name": "rental_income_medium_2m",
        "profile": {
            "goal": "rental_income",
            "budget": "2m-5m",
            "property_type": "apartment",
            "bedrooms": "2",
            "ready_offplan": "ready",
            "timeline": "3-5y",
            "financing": "mortgage",
            "risk": "medium",
        },
    },
    {
        "name": "capital_growth_low_5m",
        "profile": {
            "goal": "capital_growth",
            "budget": "5m-10m",
            "property_type": "apartment",
            "bedrooms": "3",
            "ready_offplan": "ready",
            "timeline": "5y+",
            "financing": "cash",
            "risk": "low",
        },
    },
    {
        "name": "flip_handover_high_1m",
        "profile": {
            "goal": "flip_handover",
            "budget": "1m-2m",
            "property_type": "apartment",
            "bedrooms": "1",
            "ready_offplan": "offplan",
            "timeline": "1-2y",
            "financing": "cash",
            "risk": "high",
        },
    },
    {
        "name": "balanced_medium_2m",
        "profile": {
            "goal": "balanced",
            "budget": "2m-5m",
            "property_type": "any",
            "bedrooms": "any",
            "ready_offplan": "either",
            "timeline": "undecided",
            "financing": "mortgage",
            "risk": "medium",
        },
    },
    {
        "name": "end_user_low_5m",
        "profile": {
            "goal": "end_user",
            "budget": "5m-10m",
            "property_type": "villa",
            "bedrooms": "4",
            "ready_offplan": "ready",
            "timeline": "5y+",
            "financing": "mortgage",
            "risk": "low",
        },
    },
]

# ─── Fields to snapshot ───

SNAPSHOT_FIELDS = [
    "goal",
    "budget",
    "property_type",
    "bedrooms",
    "financing",
    "timeline",
    "risk",
    "ready_offplan",
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
    "exit_strategy",
    "holding_period",
    "score_label",
    "rules_flags",
    "pricing_confidence",
    "rental_confidence",
    "has_rental_evidence",
    "has_comparable_sales",
    "report_state",
    "visible_sections",
]


class TestHarness:
    """Snapshot-based regression test harness."""

    def __init__(self, snapshot_dir: Path | None = None):
        self.snapshot_dir = snapshot_dir or SNAPSHOT_DIR
        self.snapshots: list[Snapshot] = []
        self.results: list[Snapshot] = []

    def _extract_fields(self, api_response: dict, profile: dict) -> dict[str, Any]:
        """Extract all deterministic fields from an API response."""
        top_rec = api_response.get("recommendations", [{}])[0] if api_response.get("recommendations") else {}
        rec_conf = api_response.get("recommendationConfidence", {})
        report_contract = api_response.get("reportContract", {})
        report_val = api_response.get("reportValidation", {})
        strategy = api_response.get("investorStrategy", {})

        is_offplan = top_rec.get("propertyType") == "offplan" or top_rec.get("status") == "offplan"
        dq = top_rec.get("dataQuality") or {}

        return {
            # Profile
            "goal": profile.get("goal"),
            "budget": profile.get("budget"),
            "property_type": profile.get("property_type"),
            "bedrooms": profile.get("bedrooms"),
            "financing": profile.get("financing"),
            "timeline": profile.get("timeline"),
            "risk": profile.get("risk"),
            "ready_offplan": profile.get("ready_offplan"),
            # Scores
            "investment_score": top_rec.get("readyScore") or top_rec.get("offplanScore"),
            "investor_fit_score": rec_conf.get("investorFitScore") or (top_rec.get("investorFit", {}) or {}).get("fitScore"),
            "confidence_score": top_rec.get("confidenceScore"),
            "recommendation": top_rec.get("recommendation"),
            "developer_score": (top_rec.get("developerData") or {}).get("developerScore") or top_rec.get("developerScore"),
            "area_score": (top_rec.get("communityData") or {}).get("communityScore") or top_rec.get("communityScore"),
            "liquidity_score": (top_rec.get("liquidity") or {}).get("liquidityScore"),
            "growth_12m": top_rec.get("growth12m"),
            "net_roi": (top_rec.get("roi") or {}).get("netROI") or (top_rec.get("postHandoverROI") or {}).get("netROI"),
            "gross_roi": (top_rec.get("roi") or {}).get("grossROI") or (top_rec.get("postHandoverROI") or {}).get("grossROI"),
            "fair_value": (top_rec.get("marketValuation") or {}).get("fairValueTotal") or (top_rec.get("fairValue") or {}).get("fairValue"),
            "price_vs_market": top_rec.get("priceDifference") or (top_rec.get("priceOpportunity") or {}).get("priceDifferencePct"),
            "risk_level": (top_rec.get("risk") or {}).get("riskLevel"),
            # Report
            "exit_strategy": report_contract.get("exit_strategy") or strategy.get("exit_strategy"),
            "holding_period": profile.get("timeline"),  # Should come from profile, not LLM
            "score_label": top_rec.get("scoreLabel"),
            "rules_flags": top_rec.get("rulesFlags"),
            "pricing_confidence": top_rec.get("pricingConfidence"),
            "rental_confidence": top_rec.get("rentalConfidence"),
            "has_rental_evidence": (dq.get("rentCount", 0) or 0) > 0,
            "has_comparable_sales": (dq.get("salesCount", 0) or dq.get("comparableCount", 0) or 0) > 0,
            "report_state": report_contract.get("report_state"),
            "visible_sections": report_contract.get("visible_sections"),
        }

    def create_snapshot(self, test_name: str, profile: dict, api_response: dict) -> Snapshot:
        """Create a new snapshot from an API response."""
        fields = self._extract_fields(api_response, profile)
        snap = Snapshot(
            test_name=test_name,
            input_profile=profile,
            expected_fields=fields,
            actual_fields=fields,
            created_at=datetime.now().isoformat(),
            status="NEW_SNAPSHOT",
        )
        # Save to disk
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        snap_path = self.snapshot_dir / f"{test_name}.json"
        snap_path.write_text(json.dumps({
            "test_name": snap.test_name,
            "input_profile": snap.input_profile,
            "expected_fields": snap.expected_fields,
            "created_at": snap.created_at,
        }, indent=2))
        return snap

    def compare_snapshot(self, test_name: str, profile: dict, api_response: dict) -> Snapshot:
        """Compare an API response against an existing snapshot."""
        snap_path = self.snapshot_dir / f"{test_name}.json"
        actual_fields = self._extract_fields(api_response, profile)

        if not snap_path.exists():
            # No snapshot exists — create one
            return self.create_snapshot(test_name, profile, api_response)

        saved = json.loads(snap_path.read_text())
        expected = saved.get("expected_fields", {})
        diffs = []

        for field_name in SNAPSHOT_FIELDS:
            exp_val = expected.get(field_name)
            act_val = actual_fields.get(field_name)
            if exp_val != act_val:
                diffs.append({
                    "field": field_name,
                    "expected": exp_val,
                    "actual": act_val,
                })

        snap = Snapshot(
            test_name=test_name,
            input_profile=profile,
            expected_fields=expected,
            actual_fields=actual_fields,
            created_at=saved.get("created_at", ""),
            status="PASS" if not diffs else "FAIL",
            diffs=diffs,
        )
        return snap

    def run_all(self, api_responses: dict[str, dict] | None = None) -> list[Snapshot]:
        """Run all test profiles against provided API responses."""
        self.results = []
        for test in TEST_PROFILES:
            name = test["name"]
            profile = test["profile"]
            if api_responses and name in api_responses:
                snap = self.compare_snapshot(name, profile, api_responses[name])
            else:
                # No API response provided — just validate the profile
                snap = Snapshot(
                    test_name=name,
                    input_profile=profile,
                    status="SKIPPED",
                )
            self.results.append(snap)
        return self.results

    def generate_report(self) -> dict:
        """Generate the test harness report."""
        passes = sum(1 for s in self.results if s.status == "PASS")
        fails = sum(1 for s in self.results if s.status == "FAIL")
        new = sum(1 for s in self.results if s.status == "NEW_SNAPSHOT")
        skipped = sum(1 for s in self.results if s.status == "SKIPPED")

        return {
            "summary": {
                "total_tests": len(self.results),
                "passes": passes,
                "fails": fails,
                "new_snapshots": new,
                "skipped": skipped,
            },
            "test_profiles": [{"name": t["name"], "profile": t["profile"]} for t in TEST_PROFILES],
            "snapshot_fields": SNAPSHOT_FIELDS,
            "results": [
                {
                    "test_name": s.test_name,
                    "status": s.status,
                    "diffs": s.diffs,
                    "input_profile": s.input_profile,
                }
                for s in self.results
            ],
        }

    def print_report(self):
        """Print human-readable test harness report."""
        report = self.generate_report()
        print("=" * 80)
        print("TEST HARNESS — Snapshot Regression Tests")
        print("=" * 80)
        print()
        s = report["summary"]
        print(f"Total tests: {s['total_tests']}")
        print(f"PASS: {s['passes']}")
        print(f"FAIL: {s['fails']}")
        print(f"NEW: {s['new_snapshots']}")
        print(f"SKIPPED: {s['skipped']}")
        print()

        for result in report["results"]:
            marker = "✓" if result["status"] == "PASS" else "✗" if result["status"] == "FAIL" else "+" if result["status"] == "NEW_SNAPSHOT" else "–"
            print(f"  {marker} {result['test_name']}: {result['status']}")
            if result["diffs"]:
                for diff in result["diffs"]:
                    print(f"      {diff['field']}: expected={diff['expected']} → actual={diff['actual']}")
        print()

    def print_test_profiles(self):
        """Print the test profiles that will be used."""
        print("=" * 80)
        print("TEST PROFILES")
        print("=" * 80)
        for test in TEST_PROFILES:
            print(f"\n── {test['name']} ──")
            for k, v in test["profile"].items():
                print(f"  {k}: {v}")
