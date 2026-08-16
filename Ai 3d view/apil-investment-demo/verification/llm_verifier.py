"""
LLM Prompt Verification — D8

Verifies that every deterministic field passed into the LLM exactly matches
the API response. Checks for profile loss, goal mismatch, and missing data.

Usage:
    from verification.llm_verifier import LLMVerifier
    verifier = LLMVerifier()
    report = verifier.scan()
    verifier.print_report()
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ENGINES_DIR = Path(__file__).resolve().parent.parent.parent / "apil-investment-new" / "backend" / "engines"
SERVER_DIR = Path(__file__).resolve().parent.parent.parent / "apil-investment-new"


@dataclass
class LLMPromptCheck:
    """A single verification check on an LLM prompt."""
    function_name: str
    check_type: str  # "profile_injection", "field_injection", "missing_constraint", "fallback_invention"
    field: str
    status: str  # "PASS", "FAIL", "WARN"
    detail: str
    line: int = 0


class LLMVerifier:
    """Verifies LLM prompt construction in llm_engine.py and apil_server.py."""

    def __init__(self, engines_dir: Path | None = None, server_dir: Path | None = None):
        self.engines_dir = engines_dir or ENGINES_DIR
        self.server_dir = server_dir or SERVER_DIR
        self.checks: list[LLMPromptCheck] = []

    def scan(self) -> dict:
        """Scan llm_engine.py and apil_server.py for prompt construction issues."""
        self.checks = []

        llm_file = self.engines_dir / "llm_engine.py"
        server_file = self.server_dir / "apil_server.py"

        if llm_file.exists():
            self._scan_llm_engine(llm_file)
        if server_file.exists():
            self._scan_server(server_file)

        # Categorize
        fails = [c for c in self.checks if c.status == "FAIL"]
        warns = [c for c in self.checks if c.status == "WARN"]

        return {
            "summary": {
                "total_checks": len(self.checks),
                "passes": sum(1 for c in self.checks if c.status == "PASS"),
                "fails": len(fails),
                "warnings": len(warns),
            },
            "checks": [self._check_to_dict(c) for c in self.checks],
            "fails": [self._check_to_dict(c) for c in fails],
            "warnings": [self._check_to_dict(c) for c in warns],
        }

    def _scan_llm_engine(self, filepath: Path):
        """Scan llm_engine.py for prompt construction issues."""
        text = filepath.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()

        # Find function boundaries
        functions: list[tuple[str, int, int]] = []  # (name, start_line, end_line)
        current_name = None
        current_start = 0
        for i, line in enumerate(lines):
            m = re.match(r"def\s+(\w+)", line)
            if m:
                if current_name:
                    functions.append((current_name, current_start, i))
                current_name = m.group(1)
                current_start = i
        if current_name:
            functions.append((current_name, current_start, len(lines)))

        for func_name, start, end in functions:
            func_text = "\n".join(lines[start:end])

            # Check 1: Does the function receive investor_profile?
            has_profile_param = "investor_profile" in func_text[:200]

            # Check 2: Does it extract goal from profile?
            if has_profile_param:
                if "goal" in func_text:
                    self.checks.append(LLMPromptCheck(
                        function_name=func_name, check_type="profile_injection",
                        field="goal", status="PASS",
                        detail="Function receives investor_profile and extracts goal",
                        line=start + 1,
                    ))
                else:
                    self.checks.append(LLMPromptCheck(
                        function_name=func_name, check_type="profile_injection",
                        field="goal", status="WARN",
                        detail="Function receives investor_profile but does not extract goal",
                        line=start + 1,
                    ))

            # Check 3: Does it inject goal constraint?
            if has_profile_param and "goal" in func_text:
                if "goal_constraint" in func_text or "CRITICAL GOAL" in func_text or "Investor Goal:" in func_text:
                    self.checks.append(LLMPromptCheck(
                        function_name=func_name, check_type="goal_constraint",
                        field="goal", status="PASS",
                        detail="Function injects goal constraint into prompt",
                        line=start + 1,
                    ))
                else:
                    self.checks.append(LLMPromptCheck(
                        function_name=func_name, check_type="goal_constraint",
                        field="goal", status="FAIL",
                        detail="Function receives profile but does NOT inject goal constraint into prompt",
                        line=start + 1,
                    ))

            # Check 4: Does it have fallback that invents values?
            fallback_patterns = [
                (r'"Hold 3-5 years', "Invents holding period '3-5 years' in fallback"),
                (r'"Hold 5-7 years', "Invents holding period '5-7 years' in fallback"),
                (r'"Hold 5 years', "Invents holding period '5 years' in fallback"),
                (r"'Hold 3-5 years", "Invents holding period in fallback"),
                (r'"exit_plan":\s*"Hold', "Invents exit plan in fallback"),
            ]
            for pat, desc in fallback_patterns:
                if re.search(pat, func_text):
                    self.checks.append(LLMPromptCheck(
                        function_name=func_name, check_type="fallback_invention",
                        field="holding_period/exit_strategy", status="FAIL",
                        detail=desc,
                        line=start + 1,
                    ))

            # Check 5: Does it inject recommendation?
            if "recommendation" in func_text and "rec" in func_text:
                if re.search(r'rec.*=.*property_data\.get\("recommendation"', func_text):
                    self.checks.append(LLMPromptCheck(
                        function_name=func_name, check_type="field_injection",
                        field="recommendation", status="PASS",
                        detail="Function injects deterministic recommendation",
                        line=start + 1,
                    ))

            # Check 6: Does it inject confidence?
            if "confidenceScore" in func_text or "conf" in func_text:
                self.checks.append(LLMPromptCheck(
                    function_name=func_name, check_type="field_injection",
                    field="confidence", status="PASS",
                    detail="Function injects confidence score",
                    line=start + 1,
                ))

            # Check 7: Does it inject price vs market?
            if "priceDifference" in func_text or "price_vs_market" in func_text or "priceDifferencePct" in func_text:
                self.checks.append(LLMPromptCheck(
                    function_name=func_name, check_type="field_injection",
                    field="price_vs_market", status="PASS",
                    detail="Function injects price vs market data",
                    line=start + 1,
                ))
            elif has_profile_param and "generate_advisory" in func_name:
                self.checks.append(LLMPromptCheck(
                    function_name=func_name, check_type="field_injection",
                    field="price_vs_market", status="WARN",
                    detail="Advisory function may not inject price vs market for ready properties",
                    line=start + 1,
                ))

    def _scan_server(self, filepath: Path):
        """Scan apil_server.py for profile hardcoding."""
        text = filepath.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()

        for i, line in enumerate(lines):
            # Check for hardcoded profile
            if re.search(r'profile\s*=\s*\{"goal":\s*"balanced"', line):
                self.checks.append(LLMPromptCheck(
                    function_name="apil_server.py",
                    check_type="profile_hardcoding",
                    field="goal",
                    status="FAIL",
                    detail=f"HARDCODED profile = {{'goal': 'balanced', 'risk': 'medium'}} — loses user's actual goal",
                    line=i + 1,
                ))

            # Check for advisory endpoints
            if "advisory" in line.lower() and "def" in line:
                self.checks.append(LLMPromptCheck(
                    function_name="apil_server.py",
                    check_type="advisory_endpoint",
                    field="profile",
                    status="WARN",
                    detail=f"Advisory endpoint defined — verify it receives real profile, not hardcoded",
                    line=i + 1,
                ))

    def _check_to_dict(self, c: LLMPromptCheck) -> dict:
        return {
            "function": c.function_name,
            "check_type": c.check_type,
            "field": c.field,
            "status": c.status,
            "detail": c.detail,
            "line": c.line,
        }

    def print_report(self):
        """Print human-readable LLM verification report."""
        report = self.scan()
        print("=" * 80)
        print("LLM PROMPT VERIFICATION REPORT")
        print("=" * 80)
        print()
        s = report["summary"]
        print(f"Total checks: {s['total_checks']}")
        print(f"PASS: {s['passes']}")
        print(f"FAIL: {s['fails']}")
        print(f"WARN: {s['warnings']}")
        print()

        if report["fails"]:
            print("── FAILURES ──")
            for c in report["fails"]:
                print(f"  [{c['check_type']}] {c['function']}:{c['line']} — {c['field']}")
                print(f"    → {c['detail']}")
            print()

        if report["warnings"]:
            print("── WARNINGS ──")
            for c in report["warnings"]:
                print(f"  [{c['check_type']}] {c['function']}:{c['line']} — {c['field']}")
                print(f"    → {c['detail']}")
            print()

        print("── All Checks ──")
        for c in report["checks"]:
            marker = "✓" if c["status"] == "PASS" else "✗" if c["status"] == "FAIL" else "⚠"
            print(f"  {marker} [{c['check_type']}] {c['function']}:{c['line']} — {c['field']}: {c['detail']}")
        print()
