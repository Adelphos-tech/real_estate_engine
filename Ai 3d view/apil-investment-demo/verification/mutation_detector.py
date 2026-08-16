"""
Mutation Detection — D5

Detects every place where a deterministic field is modified after its initial creation.
Tracks the chain of mutations for: recommendation, confidence, risk, valuation, exit_strategy, profile.

Usage:
    from verification.mutation_detector import MutationDetector
    detector = MutationDetector()
    report = detector.scan()
    detector.print_report()
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ENGINES_DIR = Path(__file__).resolve().parent.parent.parent / "apil-investment-new" / "backend" / "engines"


@dataclass
class Mutation:
    """A single mutation of a field after creation."""
    field_name: str
    file: str
    function: str
    line: int
    code: str
    mutation_type: str  # "assignment", "dict_update", "conditional_override", "normalization"


# ─── Mutation patterns to search for ───

MUTATION_PATTERNS: dict[str, list[dict]] = {
    "recommendation": [
        {"pattern": r'prop\["recommendation"\]\s*=', "type": "dict_update", "desc": "prop dict update"},
        {"pattern": r'prop\.get\("recommendation"\).*=', "type": "conditional_override", "desc": "conditional override"},
        {"pattern": r'top\["recommendation"\]\s*=', "type": "dict_update", "desc": "top dict update"},
        {"pattern": r'recommendation\s*=\s*"(STRONG BUY|BUY|HOLD|WATCHLIST|REVIEW|CAUTION|AVOID|NEGOTIATE|INSUFFICIENT_DATA)"', "type": "assignment", "desc": "literal assignment"},
        {"pattern": r'p\["recommendation"\]\s*=', "type": "dict_update", "desc": "p dict update"},
        {"pattern": r'\.recommendation\s*=\s*', "type": "assignment", "desc": "attribute assignment"},
        {"pattern": r'if\s+rec\s*==\s*"CAUTION"', "type": "normalization", "desc": "CAUTION normalization check"},
        {"pattern": r'prop\["recommendation"\]\s*=\s*"WATCHLIST"', "type": "normalization", "desc": "CAUTION→WATCHLIST normalization"},
    ],
    "confidence": [
        {"pattern": r'prop\["confidenceScore"\]\s*=', "type": "dict_update", "desc": "confidenceScore dict update"},
        {"pattern": r'prop\["pricingConfidence"\]\s*=', "type": "dict_update", "desc": "pricingConfidence added"},
        {"pattern": r'prop\["rentalConfidence"\]\s*=', "type": "dict_update", "desc": "rentalConfidence added"},
        {"pattern": r'confidence\s*=\s*int\(clamp', "type": "assignment", "desc": "confidence clamp assignment"},
        {"pattern": r'confidence_score\s*=\s*int\(clamp', "type": "assignment", "desc": "confidence_score clamp"},
        {"pattern": r'prop\.get\("confidenceScore".*\)', "type": "conditional_override", "desc": "confidence read+conditional"},
    ],
    "risk": [
        {"pattern": r'risk\["riskLevel"\]\s*=', "type": "dict_update", "desc": "riskLevel dict update"},
        {"pattern": r'risk\["overallRisk"\]\s*=', "type": "dict_update", "desc": "overallRisk dict update"},
        {"pattern": r'prop\["risk"\]\s*=\s*risk', "type": "dict_update", "desc": "risk dict replacement"},
        {"pattern": r'new_level\s*=\s*"Low"\s*if\s+overall', "type": "normalization", "desc": "risk level re-normalization"},
    ],
    "valuation": [
        {"pattern": r'marketValuation.*=', "type": "dict_update", "desc": "marketValuation assignment"},
        {"pattern": r'fairValue.*=', "type": "dict_update", "desc": "fairValue assignment"},
        {"pattern": r'priceDifference\s*=', "type": "assignment", "desc": "priceDifference assignment"},
        {"pattern": r'discount_pct\s*=', "type": "assignment", "desc": "discount_pct assignment"},
    ],
    "exit_strategy": [
        {"pattern": r'exit_strategy\s*=', "type": "assignment", "desc": "exit_strategy assignment"},
        {"pattern": r'recommendedStrategy\s*=', "type": "assignment", "desc": "recommendedStrategy assignment"},
        {"pattern": r'timeline\s*=\s*"Hold', "type": "assignment", "desc": "hardcoded timeline fallback"},
        {"pattern": r'"exit_plan":\s*"Hold', "type": "assignment", "desc": "hardcoded exit_plan fallback"},
    ],
    "profile": [
        {"pattern": r'profile\s*=\s*\{', "type": "assignment", "desc": "profile dict creation"},
        {"pattern": r'profile\s*=\s*\{"goal":\s*"balanced"', "type": "assignment", "desc": "HARDCODED profile override"},
        {"pattern": r'profile\["goal"\]\s*=', "type": "dict_update", "desc": "profile goal mutation"},
    ],
}


class MutationDetector:
    """Detects mutations of deterministic fields across the codebase."""

    def __init__(self, engines_dir: Path | None = None):
        self.engines_dir = engines_dir or ENGINES_DIR
        self.mutations: list[Mutation] = []

    def scan_file(self, filepath: Path) -> list[Mutation]:
        """Scan a single file for mutation patterns."""
        found = []
        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return found

        lines = text.splitlines()

        # Find function context
        current_func = "<module>"
        func_at_line: dict[int, str] = {}
        for i, line in enumerate(lines):
            m = re.match(r"\s*def\s+(\w+)", line)
            if m:
                current_func = m.group(1)
            func_at_line[i + 1] = current_func

        for field_name, patterns in MUTATION_PATTERNS.items():
            for pat_info in patterns:
                pat = pat_info["pattern"]
                mtype = pat_info["type"]
                for i, line in enumerate(lines):
                    if re.search(pat, line, re.IGNORECASE):
                        found.append(Mutation(
                            field_name=field_name,
                            file=str(filepath.name),
                            function=func_at_line.get(i + 1, "<module>"),
                            line=i + 1,
                            code=line.strip()[:120],
                            mutation_type=mtype,
                        ))
        return found

    def scan(self) -> dict:
        """Scan all engine files and the server file."""
        self.mutations = []

        py_files = sorted(self.engines_dir.glob("*.py"))
        server_file = self.engines_dir.parent / "apil_server.py"
        if server_file.exists():
            py_files.append(server_file)

        for f in py_files:
            if "__pycache__" in str(f) or "__init__" in f.name:
                continue
            self.mutations.extend(self.scan_file(f))

        # Group by field
        by_field: dict[str, list[dict]] = {}
        for mut in self.mutations:
            entry = {
                "file": mut.file,
                "function": mut.function,
                "line": mut.line,
                "code": mut.code,
                "type": mut.mutation_type,
            }
            by_field.setdefault(mut.field_name, []).append(entry)

        # Build mutation chains
        chains = {}
        for field_name, muts in by_field.items():
            chains[field_name] = {
                "total_mutations": len(muts),
                "unique_files": list(set(m["file"] for m in muts)),
                "unique_functions": list(set(m["function"] for m in muts)),
                "mutations": muts,
                "status": "FAIL" if len(muts) > 2 else "WARN" if len(muts) > 1 else "PASS",
            }

        return {
            "summary": {
                "total_fields_tracked": len(MUTATION_PATTERNS),
                "total_mutations": len(self.mutations),
                "fields_with_multiple_mutations": sum(1 for v in chains.values() if v["status"] == "FAIL"),
            },
            "fields": chains,
        }

    def print_report(self):
        """Print human-readable mutation report."""
        report = self.scan()
        print("=" * 80)
        print("MUTATION DETECTION REPORT")
        print("=" * 80)
        print()
        print(f"Fields tracked: {report['summary']['total_fields_tracked']}")
        print(f"Total mutations found: {report['summary']['total_mutations']}")
        print(f"Fields with >2 mutations (FAIL): {report['summary']['fields_with_multiple_mutations']}")
        print()

        for field_name, info in sorted(report["fields"].items()):
            print(f"── {field_name} ── {info['status']}")
            print(f"  Mutations: {info['total_mutations']} in {len(info['unique_files'])} files")
            print(f"  Files: {', '.join(info['unique_files'])}")
            print(f"  Functions: {', '.join(info['unique_functions'])}")
            for mut in info["mutations"]:
                print(f"    {mut['file']}:{mut['line']} in {mut['function']}() [{mut['type']}]")
                print(f"      → {mut['code']}")
            print()
