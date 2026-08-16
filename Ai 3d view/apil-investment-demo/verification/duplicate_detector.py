"""
Duplicate Calculation Detection — D4

Scans all engine files for functions that calculate the same field.
Produces a report listing: Field, File, Function, Formula, Usage, Source of Truth.

Usage:
    from verification.duplicate_detector import DuplicateCalculator
    detector = DuplicateCalculator()
    report = detector.scan()
    detector.print_report()
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ENGINES_DIR = Path(__file__).resolve().parent.parent.parent / "apil-investment-new" / "backend" / "engines"
SERVER_DIR = Path(__file__).resolve().parent.parent.parent / "apil-investment-new"

# If not found locally, use remote path
if not ENGINES_DIR.exists():
    ENGINES_DIR = Path("/dev/null")  # Will be populated from remote scan


@dataclass
class CalculationSite:
    """A single place where a field is calculated."""
    field_name: str
    file: str
    function: str
    line: int
    formula: str
    usage: str  # "primary", "duplicate", "fallback", "normalization"
    is_source_of_truth: bool = False


# ─── Known field calculation patterns ───

FIELD_PATTERNS: dict[str, list[dict]] = {
    "confidence_score": [
        {"pattern": r"confidence_score\s*=\s*(.+)", "label": "confidence_score assignment"},
        {"pattern": r"confidenceScore\s*[:=]\s*(.+)", "label": "confidenceScore assignment"},
        {"pattern": r"def\s+calculate_confidence", "label": "calculate_confidence function"},
        {"pattern": r"confidence_from_sales", "label": "confidence_from_sales"},
        {"pattern": r"confidence_from_rentals", "label": "confidence_from_rentals"},
        {"pattern": r"confidence_from_growth", "label": "confidence_from_growth"},
        {"pattern": r"confidence_from_pricing", "label": "confidence_from_pricing"},
        {"pattern": r"pricingConfidence\s*=\s*(.+)", "label": "pricingConfidence assignment"},
        {"pattern": r"rentalConfidence\s*=\s*(.+)", "label": "rentalConfidence assignment"},
    ],
    "recommendation": [
        {"pattern": r"def\s+recommendation_from_score", "label": "recommendation_from_score"},
        {"pattern": r"def\s+offplan_recommendation", "label": "offplan_recommendation"},
        {"pattern": r"recommendation\s*=\s*\"(STRONG BUY|BUY|HOLD|WATCHLIST|REVIEW|CAUTION|AVOID|NEGOTIATE|INSUFFICIENT_DATA)\"", "label": "recommendation literal assignment"},
        {"pattern": r"return\s+\"(STRONG BUY|BUY|HOLD|WATCHLIST|REVIEW|CAUTION|AVOID|NEGOTIATE|INSUFFICIENT_DATA)\"", "label": "recommendation return"},
    ],
    "risk_level": [
        {"pattern": r"risk_level\s*=\s*\"(Low|Medium|High)\"", "label": "risk_level literal"},
        {"pattern": r"riskLevel.*\"(Low|Medium|High)\"", "label": "riskLevel literal"},
        {"pattern": r"def\s+risk_from_score", "label": "risk_from_score function"},
        {"pattern": r"overall_risk\s*(<=|<|>=|>)\s*\d+", "label": "risk threshold comparison"},
    ],
    "fair_value": [
        {"pattern": r"def\s+calculate_fair_value", "label": "calculate_fair_value function"},
        {"pattern": r"fair_value_total\s*=", "label": "fair_value_total assignment"},
        {"pattern": r"fairValue\s*[:=]\s*", "label": "fairValue assignment"},
    ],
    "roi": [
        {"pattern": r"def\s+calculate_roi", "label": "calculate_roi function"},
        {"pattern": r"net_roi\s*=\s*\(", "label": "net_roi calculation"},
        {"pattern": r"gross_roi\s*=\s*\(", "label": "gross_roi calculation"},
        {"pattern": r"def\s+calculate_post_handover_roi", "label": "calculate_post_handover_roi"},
    ],
    "growth": [
        {"pattern": r"def\s+calculate_growth", "label": "calculate_growth function"},
        {"pattern": r"growth_rate\s*=\s*(?!0\b)(.+)", "label": "growth_rate assignment"},
        {"pattern": r"growth12m\s*[:=]", "label": "growth12m assignment"},
    ],
    "developer_score": [
        {"pattern": r"def\s+calculate_developer_score", "label": "calculate_developer_score"},
        {"pattern": r"developerScore\s*=\s*round", "label": "developerScore calculation"},
    ],
    "liquidity_score": [
        {"pattern": r"liquidity_score\s*=", "label": "liquidity_score assignment"},
        {"pattern": r"liquidityScore\s*[:=]\s*round", "label": "liquidityScore calculation"},
    ],
    "investor_fit_score": [
        {"pattern": r"def\s+calculate_investor_fit", "label": "calculate_investor_fit"},
        {"pattern": r"fit_score\s*=\s*round", "label": "fit_score calculation"},
        {"pattern": r"fitScore\s*[:=]\s*round", "label": "fitScore calculation"},
    ],
    "exit_strategy": [
        {"pattern": r"EXIT_PREFERENCES", "label": "EXIT_PREFERENCES reference"},
        {"pattern": r"recommendedStrategy\s*=", "label": "recommendedStrategy assignment"},
        {"pattern": r"exit_strategy\s*=", "label": "exit_strategy assignment"},
        {"pattern": r"def\s+get_exit_strategy", "label": "get_exit_strategy function"},
        {"pattern": r"def\s+calculate_exit_strategies", "label": "calculate_exit_strategies"},
    ],
    "holding_period": [
        {"pattern": r"holding_period\s*=", "label": "holding_period assignment"},
        {"pattern": r"HOLDING_PERIOD", "label": "HOLDING_PERIOD reference"},
        {"pattern": r"Hold\s+\d", "label": "Hardcoded Hold period text"},
    ],
    "score_to_label": [
        {"pattern": r"def\s+score_to_label", "label": "score_to_label function"},
        {"pattern": r"scoreLabel\s*[:=]\s*score_to_label", "label": "scoreLabel via score_to_label"},
    ],
}


class DuplicateCalculator:
    """Scans engine source files for duplicate calculations."""

    def __init__(self, engines_dir: Path | None = None):
        self.engines_dir = engines_dir or ENGINES_DIR
        self.sites: list[CalculationSite] = []
        self._function_context: dict[str, str] = {}  # line_range -> function name

    def _find_functions(self, lines: list[str]) -> dict[int, str]:
        """Map line numbers to enclosing function names."""
        func_at_line: dict[int, str] = {}
        current_func = "<module>"
        for i, line in enumerate(lines):
            m = re.match(r"\s*def\s+(\w+)", line)
            if m:
                current_func = m.group(1)
            func_at_line[i + 1] = current_func
        return func_at_line

    def scan_file(self, filepath: Path) -> list[CalculationSite]:
        """Scan a single Python file for calculation patterns."""
        sites = []
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return sites

        lines = text.splitlines()
        func_at_line = self._find_functions(lines)

        for field_name, patterns in FIELD_PATTERNS.items():
            for pat_info in patterns:
                pat = pat_info["pattern"]
                label = pat_info["label"]
                for i, line in enumerate(lines):
                    if re.search(pat, line):
                        func_name = func_at_line.get(i + 1, "<module>")
                        # Extract a snippet as the formula
                        formula = line.strip()[:120]
                        sites.append(CalculationSite(
                            field_name=field_name,
                            file=str(filepath.name),
                            function=func_name,
                            line=i + 1,
                            formula=formula,
                            usage=label,
                            is_source_of_truth=False,
                        ))
        return sites

    def scan(self) -> dict:
        """Scan all engine files and return a report."""
        self.sites = []

        py_files = sorted(self.engines_dir.glob("*.py"))
        # Also scan apil_server.py
        server_file = self.engines_dir.parent / "apil_server.py"
        if server_file.exists():
            py_files.append(server_file)

        for f in py_files:
            if "__pycache__" in str(f) or "__init__" in f.name:
                continue
            self.sites.extend(self.scan_file(f))

        # Group by field
        by_field: dict[str, list[dict]] = {}
        for site in self.sites:
            entry = {
                "file": site.file,
                "function": site.function,
                "line": site.line,
                "formula": site.formula,
                "usage": site.usage,
            }
            by_field.setdefault(site.field_name, []).append(entry)

        # Determine duplicates and source of truth
        duplicates = {}
        for field_name, sites_list in by_field.items():
            # Count unique files
            unique_files = set(s["file"] for s in sites_list)
            unique_functions = set(s["function"] for s in sites_list)
            is_duplicate = len(unique_files) > 1 or len(unique_functions) > 1
            duplicates[field_name] = {
                "count": len(sites_list),
                "unique_files": list(unique_files),
                "unique_functions": list(unique_functions),
                "is_duplicate": is_duplicate,
                "sites": sites_list,
                "recommended_source_of_truth": self._recommend_source_of_truth(field_name, sites_list),
            }

        return {
            "summary": {
                "total_fields_scanned": len(FIELD_PATTERNS),
                "fields_with_duplicates": sum(1 for v in duplicates.values() if v["is_duplicate"]),
                "total_calculation_sites": len(self.sites),
            },
            "fields": duplicates,
        }

    def _recommend_source_of_truth(self, field_name: str, sites: list[dict]) -> str:
        """Recommend which implementation should be the source of truth."""
        recommendations = {
            "confidence_score": "confidence_engine.py::calculate_confidence (currently UNUSED — should be activated)",
            "recommendation": "utils.py::recommendation_from_score (goal-aware, used by ready engine)",
            "risk_level": "ready_engine.py inline (≤25/≤50/>50 thresholds — should be extracted to utils.py)",
            "fair_value": "market_valuation.py::calculate_fair_value (weighted medians — should be used by both engines)",
            "roi": "ready_engine.py::calculate_roi (ready) + offplan_engine_v2.py::calculate_post_handover_roi (offplan) — different formulas, should unify",
            "exit_strategy": "investor_strategy_engine.py::EXIT_PREFERENCES (deterministic, goal-based)",
            "holding_period": "User input (profile.timeline) — should never be invented by LLM or fallback",
            "score_to_label": "utils.py::score_to_label (single implementation — OK)",
        }
        return recommendations.get(field_name, "Needs analysis")

    def print_report(self):
        """Print human-readable duplicate calculation report."""
        report = self.scan()
        print("=" * 80)
        print("DUPLICATE CALCULATION DETECTION REPORT")
        print("=" * 80)
        print()
        print(f"Fields scanned: {report['summary']['total_fields_scanned']}")
        print(f"Fields with duplicates: {report['summary']['fields_with_duplicates']}")
        print(f"Total calculation sites: {report['summary']['total_calculation_sites']}")
        print()

        for field_name, info in sorted(report["fields"].items()):
            status = "FAIL — DUPLICATE" if info["is_duplicate"] else "PASS"
            print(f"── {field_name} ── {status}")
            print(f"  Implementations: {info['count']} in {len(info['unique_files'])} files")
            print(f"  Files: {', '.join(info['unique_files'])}")
            print(f"  Functions: {', '.join(info['unique_functions'])}")
            print(f"  Source of truth: {info['recommended_source_of_truth']}")
            for site in info["sites"]:
                print(f"    {site['file']}:{site['line']} in {site['function']}() — {site['formula']}")
            print()
