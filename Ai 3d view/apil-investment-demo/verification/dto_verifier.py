"""
DTO Verification — D6

Compares Ready vs Off-plan DTO schemas.
Detects: missing fields, different names, different types, different nesting,
different calculations, different defaults.

Usage:
    from verification.dto_verifier import DTOVerifier
    verifier = DTOVerifier()
    report = verifier.verify()
    verifier.print_report()
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "apil-investment-new" / "backend" / "data"


class DTOVerifier:
    """Compares Ready vs Off-plan DTO schemas from cached JSON data."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or DATA_DIR
        self.ready_sample: dict = {}
        self.offplan_sample: dict = {}
        self.ready_keys: set[str] = set()
        self.offplan_keys: set[str] = set()

    def _load_samples(self):
        """Load one sample from each cached JSON."""
        ready_path = self.data_dir / "ready_property_scores.json"
        offplan_path = self.data_dir / "offplan_scores.json"

        if ready_path.exists():
            data = json.loads(ready_path.read_text())
            self.ready_sample = data[0] if data else {}
            self.ready_keys = set(self.ready_sample.keys())

        if offplan_path.exists():
            data = json.loads(offplan_path.read_text())
            self.offplan_sample = data[0] if data else {}
            self.offplan_keys = set(self.offplan_sample.keys())

    def _get_type(self, val: Any) -> str:
        if val is None:
            return "null"
        if isinstance(val, bool):
            return "bool"
        if isinstance(val, int):
            return "int"
        if isinstance(val, float):
            return "float"
        if isinstance(val, str):
            return "str"
        if isinstance(val, list):
            return "list"
        if isinstance(val, dict):
            return "dict"
        return type(val).__name__

    def _compare_nested(self, ready_val: Any, offplan_val: Any, path: str = "") -> list[dict]:
        """Recursively compare nested structures."""
        issues = []
        r_type = self._get_type(ready_val)
        o_type = self._get_type(offplan_val)

        if r_type != o_type:
            issues.append({
                "path": path,
                "ready_type": r_type,
                "offplan_type": o_type,
                "issue": "TYPE_MISMATCH",
                "detail": f"Ready has {r_type}, off-plan has {o_type} at {path}",
            })
            return issues

        if r_type == "dict":
            r_keys = set(ready_val.keys())
            o_keys = set(offplan_val.keys())
            only_ready = r_keys - o_keys
            only_offplan = o_keys - r_keys
            for k in only_ready:
                issues.append({
                    "path": f"{path}.{k}" if path else k,
                    "issue": "ONLY_IN_READY",
                    "detail": f"Field '{k}' only exists in ready DTO",
                })
            for k in only_offplan:
                issues.append({
                    "path": f"{path}.{k}" if path else k,
                    "issue": "ONLY_IN_OFFPLAN",
                    "detail": f"Field '{k}' only exists in off-plan DTO",
                })
            common = r_keys & o_keys
            for k in common:
                issues.extend(self._compare_nested(ready_val[k], offplan_val[k], f"{path}.{k}" if path else k))

        return issues

    def verify(self) -> dict:
        """Run full DTO comparison."""
        self._load_samples()

        # Top-level field comparison
        only_ready = self.ready_keys - self.offplan_keys
        only_offplan = self.offplan_keys - self.ready_keys
        common = self.ready_keys & self.offplan_keys

        # Type comparison for common fields
        type_mismatches = []
        for k in sorted(common):
            r_val = self.ready_sample.get(k)
            o_val = self.offplan_sample.get(k)
            r_type = self._get_type(r_val)
            o_type = self._get_type(o_val)
            if r_type != o_type:
                type_mismatches.append({
                    "field": k,
                    "ready_type": r_type,
                    "offplan_type": o_type,
                })

        # Nested comparison for common dict fields
        nested_issues = []
        for k in sorted(common):
            r_val = self.ready_sample.get(k)
            o_val = self.offplan_sample.get(k)
            if isinstance(r_val, dict) and isinstance(o_val, dict):
                nested_issues.extend(self._compare_nested(r_val, o_val, k))

        # Check for semantically equivalent fields with different names
        semantic_equivalents = {
            "investment_score": {
                "ready": "readyScore",
                "offplan": "offplanScore",
                "issue": "Different field names for investment score",
            },
            "fair_value": {
                "ready": "marketValuation.fairValueTotal",
                "offplan": "fairValue.fairValue",
                "issue": "Different paths and names for fair value",
            },
            "price_vs_market": {
                "ready": "priceDifference",
                "offplan": "priceOpportunity.priceDifferencePct",
                "issue": "Different fields for price vs market",
            },
            "comparable_price": {
                "ready": "comparablePrice",
                "offplan": "fairValue.fairValue (used as comparable)",
                "issue": "Ready has explicit comparablePrice, off-plan uses fairValue",
            },
            "roi": {
                "ready": "roi.netROI",
                "offplan": "postHandoverROI.netROI",
                "issue": "Different nesting for ROI",
            },
            "score_breakdown": {
                "ready": "scoreBreakdown.{price,roi,liquidity,community,developer,project}",
                "offplan": "scoreBreakdown.{developer,price,paymentPlan,growth,supplyRisk,liquidity,roi}",
                "issue": "Different keys in scoreBreakdown",
            },
        }

        # Check for missing critical fields
        critical_fields = {
            "dataQuality": {"ready": True, "offplan": False, "impact": "Frontend ReportContext breaks for off-plan"},
            "lostPoints": {"ready": True, "offplan": False, "impact": "Off-plan has no lost points for score explanation"},
            "pricingConfidence": {"ready": True, "offplan": False, "impact": "Off-plan has no split pricing confidence"},
            "rentalConfidence": {"ready": True, "offplan": False, "impact": "Off-plan has no split rental confidence"},
            "rulesFlagsHuman": {"ready": False, "offplan": False, "impact": "Neither has human-readable rule flags in cached data"},
            "marketValuation": {"ready": True, "offplan": False, "impact": "Only ready has marketValuation (from removed code)"},
        }

        missing_critical = []
        for field, info in critical_fields.items():
            in_ready = field in self.ready_keys
            in_offplan = field in self.offplan_keys
            if in_ready != info["ready"] or in_offplan != info["offplan"]:
                missing_critical.append({
                    "field": field,
                    "in_ready": in_ready,
                    "in_offplan": in_offplan,
                    "expected_ready": info["ready"],
                    "expected_offplan": info["offplan"],
                    "impact": info["impact"],
                })

        return {
            "summary": {
                "ready_fields": len(self.ready_keys),
                "offplan_fields": len(self.offplan_keys),
                "common_fields": len(common),
                "only_ready": len(only_ready),
                "only_offplan": len(only_offplan),
                "type_mismatches": len(type_mismatches),
                "nested_issues": len(nested_issues),
                "missing_critical": len(missing_critical),
            },
            "only_in_ready": sorted(only_ready),
            "only_in_offplan": sorted(only_offplan),
            "type_mismatches": type_mismatches,
            "nested_issues": nested_issues,
            "semantic_equivalents": semantic_equivalents,
            "missing_critical_fields": missing_critical,
            "recommended_unified_dto": self._recommend_unified_dto(),
        }

    def _recommend_unified_dto(self) -> list[str]:
        """Recommend a unified DTO schema (without implementing)."""
        return [
            "1. Both ready and off-plan must have: dataQuality, lostPoints, pricingConfidence, rentalConfidence, rulesFlags, rulesFlagsHuman",
            "2. Unify investment score field name: use 'investmentScore' for both (not readyScore/offplanScore)",
            "3. Unify fair value: use 'marketValuation.fairValueTotal' for both (off-plan currently uses 'fairValue.fairValue')",
            "4. Unify price vs market: use 'priceVsMarketPct' for both (not priceDifference / priceOpportunity.priceDifferencePct)",
            "5. Unify ROI nesting: use 'roi.netROI' for both (not postHandoverROI.netROI)",
            "6. Unify scoreBreakdown keys: use common set {developer, price, roi, liquidity, community, growth, supply, paymentPlan}",
            "7. Both must populate dataQuality with: hasComparables, hasRentData, salesCount, rentCount, comparableCount",
            "8. Both must populate rulesFlagsHuman when rules are applied",
        ]

    def print_report(self):
        """Print human-readable DTO comparison."""
        report = self.verify()
        print("=" * 80)
        print("DTO VERIFICATION REPORT — Ready vs Off-plan")
        print("=" * 80)
        print()
        s = report["summary"]
        print(f"Ready fields: {s['ready_fields']}")
        print(f"Off-plan fields: {s['offplan_fields']}")
        print(f"Common: {s['common_fields']}")
        print(f"Only in ready: {s['only_ready']}")
        print(f"Only in off-plan: {s['only_offplan']}")
        print(f"Type mismatches: {s['type_mismatches']}")
        print(f"Nested issues: {s['nested_issues']}")
        print(f"Missing critical: {s['missing_critical']}")
        print()

        if report["only_in_ready"]:
            print("── Fields only in Ready DTO ──")
            for f in report["only_in_ready"]:
                print(f"  {f}")
            print()

        if report["only_in_offplan"]:
            print("── Fields only in Off-plan DTO ──")
            for f in report["only_in_offplan"]:
                print(f"  {f}")
            print()

        if report["type_mismatches"]:
            print("── Type Mismatches ──")
            for tm in report["type_mismatches"]:
                print(f"  {tm['field']}: ready={tm['ready_type']} vs offplan={tm['offplan_type']}")
            print()

        if report["nested_issues"]:
            print("── Nested Structure Issues ──")
            for ni in report["nested_issues"]:
                print(f"  {ni['path']}: {ni['detail']}")
            print()

        print("── Semantic Equivalents (different names, same meaning) ──")
        for name, info in report["semantic_equivalents"].items():
            print(f"  {name}: ready={info['ready']} vs offplan={info['offplan']}")
            print(f"    → {info['issue']}")
        print()

        print("── Missing Critical Fields ──")
        for mc in report["missing_critical_fields"]:
            print(f"  {mc['field']}: ready={mc['in_ready']} offplan={mc['in_offplan']}")
            print(f"    → {mc['impact']}")
        print()

        print("── Recommended Unified DTO ──")
        for rec in report["recommended_unified_dto"]:
            print(f"  {rec}")
        print()
