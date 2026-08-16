"""
Frontend Verification — D7

Inspects every React component that displays investment data.
For each displayed value identifies: source field, API field, transformation,
fallback, default value, hardcoded value.

Usage:
    from verification.frontend_verifier import FrontendVerifier
    verifier = FrontendVerifier()
    report = verifier.scan()
    verifier.print_report()
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "src"


@dataclass
class DisplayedValue:
    """A value displayed in the frontend with its source tracking."""
    component: str
    displayed_field: str
    source_field: str  # where it reads from in code
    api_field: str  # the API response field
    transformation: str  # any transformation applied
    fallback: str  # fallback value if source is null
    hardcoded: bool = False
    issue: str = ""


class FrontendVerifier:
    """Scans frontend React components for data display patterns."""

    def __init__(self, frontend_dir: Path | None = None):
        self.frontend_dir = frontend_dir or FRONTEND_DIR
        self.values: list[DisplayedValue] = []
        self.issues: list[dict] = []

    def scan(self) -> dict:
        """Scan all report section components."""
        self.values = []
        self.issues = []

        sections_dir = self.frontend_dir / "report" / "sections"
        components_dir = self.frontend_dir / "components"

        files_to_scan = []
        if sections_dir.exists():
            files_to_scan.extend(sorted(sections_dir.glob("*.tsx")))
        if components_dir.exists():
            files_to_scan.extend(sorted(components_dir.glob("*.tsx")))
        # Also scan Report.tsx
        report_file = self.frontend_dir / "pages" / "Report.tsx"
        if report_file.exists():
            files_to_scan.append(report_file)

        for f in files_to_scan:
            self._scan_file(f)

        # Check for issues
        for v in self.values:
            if v.hardcoded:
                self.issues.append({
                    "component": v.component,
                    "field": v.displayed_field,
                    "issue": "HARDCODED",
                    "detail": f"Value is hardcoded: '{v.fallback}' instead of from API",
                })
            if v.fallback and v.fallback not in ("", "—", "N/A", "0", "null", "undefined"):
                if v.fallback in ("Hold 3-5 years depending on market conditions",
                                  "Hold 5-7 years for rental yield accumulation",
                                  "Hold 3-5 years then sell at peak appreciation",
                                  "Hold 5 years, monitor market conditions"):
                    self.issues.append({
                        "component": v.component,
                        "field": v.displayed_field,
                        "issue": "FABRICATED_FALLBACK",
                        "detail": f"Fallback invents value: '{v.fallback}' — should come from user profile",
                    })

        return {
            "summary": {
                "components_scanned": len(set(v.component for v in self.values)),
                "values_tracked": len(self.values),
                "issues_found": len(self.issues),
            },
            "values": [self._value_to_dict(v) for v in self.values],
            "issues": self.issues,
        }

    def _scan_file(self, filepath: Path):
        """Scan a single TSX file for data display patterns."""
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return

        component_name = filepath.stem
        lines = text.splitlines()

        # Patterns to find data access
        patterns = [
            # topRec?.field or topRec.field
            (r"topRec\??\.(\w+)", "topRec"),
            # property.field
            (r"property\.(\w+)", "property"),
            # ctx.field
            (r"ctx\.(\w+)", "ctx"),
            # safeVal(property, 'field')
            (r"safeVal\(\s*[\w.]+,\s*['\"](\w+)['\"]", "safeVal"),
            # Hardcoded strings
            (r"'(Hold \d[^']*)'", "hardcoded_string"),
            (r'"(Hold \d[^"]*)"', "hardcoded_string"),
            # Fallback values
            (r"\|\|\s*['\"]([^'\"]+)['\"]", "fallback"),
            (r"\?\?\s*['\"]([^'\"]+)['\"]", "fallback"),
            # reportContract
            (r"reportContract\??\.(\w+)", "reportContract"),
            # strategy
            (r"strat\.(\w+)|strategy\.(\w+)", "strategy"),
        ]

        for i, line in enumerate(lines):
            for pat, source_type in patterns:
                for m in re.finditer(pat, line):
                    field_name = m.group(1) if m.group(1) else (m.group(2) if len(m.groups()) > 1 and m.group(2) else "")
                    if not field_name:
                        continue
                    is_hardcoded = source_type == "hardcoded_string"
                    is_fallback = source_type == "fallback"

                    val = DisplayedValue(
                        component=component_name,
                        displayed_field=field_name,
                        source_field=f"{source_type}.{field_name}" if not is_hardcoded else "literal",
                        api_field=self._map_to_api_field(field_name),
                        transformation="",
                        fallback=m.group(0).split("||")[-1].split("??")[-1].strip().strip("'\"") if is_fallback else "",
                        hardcoded=is_hardcoded,
                    )
                    if is_hardcoded:
                        val.fallback = field_name
                        val.issue = "HARDCODED_VALUE"
                    self.values.append(val)

    def _map_to_api_field(self, frontend_field: str) -> str:
        """Map frontend field names to API response field names."""
        mapping = {
            "overallScore": "readyScore / offplanScore",
            "propertyScore": "readyScore / offplanScore",
            "offplanScore": "offplanScore",
            "readyScore": "readyScore",
            "recommendation": "recommendation",
            "confidenceScore": "confidenceScore",
            "askingPrice": "askingPrice",
            "priceSqft": "priceSqft",
            "developerScore": "developerData.developerScore",
            "developerName": "developerData.developerName",
            "liquidityScore": "liquidity.liquidityScore",
            "riskLevel": "risk.riskLevel",
            "growth12m": "growth12m",
            "netROI": "roi.netROI / postHandoverROI.netROI",
            "grossROI": "roi.grossROI / postHandoverROI.grossROI",
            "estimatedRent": "estimatedRent / postHandoverROI.estimatedRent",
            "estimatedYield": "estimatedYield",
            "comparablePrice": "comparablePrice",
            "priceDifference": "priceDifference / priceOpportunity.priceDifferencePct",
            "marketPosition": "marketPosition",
            "investorGoal": "profile.goal",
            "confidence": "confidenceScore",
            "fitScore": "investorFit.fitScore",
            "fitLabel": "investorFit.fitLabel",
            "exitStrategy": "reportContract.exit_strategy / strategy.exit_strategy",
            "holdingPeriod": "profile.timeline (should be)",
            "scoreBreakdown": "scoreBreakdown",
            "lostPoints": "lostPoints",
            "rulesFlags": "rulesFlags",
            "dataQuality": "dataQuality",
            "marketValuation": "marketValuation",
            "fairValue": "fairValue.fairValue",
            "priceOpportunity": "priceOpportunity",
            "futureAppreciation": "futureAppreciation",
            "paymentPlanAnalysis": "paymentPlanAnalysis",
            "exitStrategies": "exitStrategies",
        }
        return mapping.get(frontend_field, f"unknown:{frontend_field}")

    def _value_to_dict(self, v: DisplayedValue) -> dict:
        return {
            "component": v.component,
            "displayed_field": v.displayed_field,
            "source_field": v.source_field,
            "api_field": v.api_field,
            "fallback": v.fallback,
            "hardcoded": v.hardcoded,
            "issue": v.issue,
        }

    def print_report(self):
        """Print human-readable frontend verification report."""
        report = self.scan()
        print("=" * 80)
        print("FRONTEND VERIFICATION REPORT")
        print("=" * 80)
        print()
        s = report["summary"]
        print(f"Components scanned: {s['components_scanned']}")
        print(f"Values tracked: {s['values_tracked']}")
        print(f"Issues found: {s['issues_found']}")
        print()

        # Group by component
        by_component: dict[str, list] = {}
        for v in report["values"]:
            by_component.setdefault(v["component"], []).append(v)

        for comp, vals in sorted(by_component.items()):
            print(f"── {comp} ──")
            for v in vals:
                marker = "⚠" if v["hardcoded"] or v["issue"] else " "
                print(f"  {marker} {v['displayed_field']:25s} ← {v['source_field']:30s} (API: {v['api_field']})")
                if v["fallback"]:
                    print(f"      fallback: {v['fallback']}")
            print()

        if report["issues"]:
            print("── Issues ──")
            for issue in report["issues"]:
                print(f"  [{issue['issue']}] {issue['component']}.{issue['field']}: {issue['detail']}")
            print()
