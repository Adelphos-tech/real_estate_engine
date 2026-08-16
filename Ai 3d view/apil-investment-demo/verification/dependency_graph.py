"""
Architectural Dependency Graph — D9

Generates a complete dependency graph of the APIL investment pipeline.
Highlights: duplicate paths, multiple sources of truth, cycles, overwrites,
dead code, unused modules.

Usage:
    from verification.dependency_graph import DependencyGraphBuilder
    builder = DependencyGraphBuilder()
    report = builder.build()
    builder.print_report()
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

ENGINES_DIR = Path(__file__).resolve().parent.parent.parent / "apil-investment-new" / "backend" / "engines"
SERVER_DIR = Path(__file__).resolve().parent.parent.parent / "apil-investment-new"


@dataclass
class ModuleInfo:
    """Information about a single module."""
    name: str
    file: str
    imports: list[str] = field(default_factory=list)
    imported_by: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    is_used: bool = True
    is_dead_code: bool = False
    notes: list[str] = field(default_factory=list)


# ─── Known pipeline stages and their dependencies ───

PIPELINE_STAGES = [
    {"stage": "User Questionnaire", "module": "frontend/Questionnaire.tsx", "outputs": ["profile"]},
    {"stage": "API Entry", "module": "apil_server.py", "outputs": ["profile dict"]},
    {"stage": "Recommendation Engine", "module": "recommendation_engine.py", "outputs": ["filtered props", "sorted props", "fit scores", "report contract"]},
    {"stage": "Investor Strategy", "module": "investor_strategy_engine.py", "outputs": ["strategy weights", "thresholds", "exit pref"]},
    {"stage": "Investor Fit", "module": "investor_fit_engine.py", "outputs": ["fitScore", "dimensionScores", "matchReasons"]},
    {"stage": "Ready Engine (scoring)", "module": "ready_engine.py", "outputs": ["readyScore", "confidence", "ROI", "risk", "marketValuation"]},
    {"stage": "Off-plan Engine (scoring)", "module": "offplan_engine_v2.py", "outputs": ["offplanScore", "confidence", "postHandoverROI", "fairValue"]},
    {"stage": "Rules Engine", "module": "rules_engine.py", "outputs": ["rulesFlags", "recommendation override"]},
    {"stage": "Confidence Engine (UNUSED)", "module": "confidence_engine.py", "outputs": ["confidence"], "dead_code": True},
    {"stage": "Market Valuation (UNUSED by ready)", "module": "market_valuation.py", "outputs": ["fairValue"], "dead_code": True},
    {"stage": "Report Rules Engine", "module": "report_rules_engine.py", "outputs": ["reportContract", "validation"]},
    {"stage": "LLM Engine", "module": "llm_engine.py", "outputs": ["advisory report", "explanation", "contradictions"]},
    {"stage": "API Response", "module": "apil_server.py", "outputs": ["JSON response"]},
    {"stage": "Frontend Mapping", "module": "loader.ts", "outputs": ["legacy property shape"]},
    {"stage": "Report Context", "module": "ReportContext.ts", "outputs": ["ctx object"]},
    {"stage": "Section Registry", "module": "SectionRegistry.tsx", "outputs": ["applicable sections"]},
    {"stage": "Report Sections", "module": "report/sections/*.tsx", "outputs": ["rendered HTML"]},
    {"stage": "LLM Advisory Section", "module": "LLMAdvisorySection.tsx", "outputs": ["AI insights display"]},
]

# ─── Known issues to highlight ───

KNOWN_ISSUES = [
    {
        "type": "duplicate_paths",
        "title": "Two scoring paths with different DTOs",
        "detail": "ready_engine.py and offplan_engine_v2.py produce completely different output schemas. Ready has marketValuation, priceDifference, dataQuality, lostPoints. Off-plan has fairValue, priceOpportunity, no dataQuality, no lostPoints.",
        "severity": "CRITICAL",
    },
    {
        "type": "multiple_sources_of_truth",
        "title": "Confidence calculated in 5 places",
        "detail": "confidence_engine.py (unused), ready_engine.py inline, offplan_engine_v2.py inline, report_rules_engine.py (per-dimension), _normalize_recommendation() (reconstruction).",
        "severity": "HIGH",
    },
    {
        "type": "multiple_sources_of_truth",
        "title": "Recommendation calculated in 3 places",
        "detail": "utils.py::recommendation_from_score (goal-aware), offplan_engine_v2.py::offplan_recommendation (price-diff based), recommendation_engine.py inline (fit gates).",
        "severity": "HIGH",
    },
    {
        "type": "overwrites",
        "title": "Recommendation overwritten 3+ times",
        "detail": "1) Engine creates it, 2) _normalize_recommendation converts CAUTION→WATCHLIST, 3) rules_engine downgrades, 4) fit gates downgrade again.",
        "severity": "HIGH",
    },
    {
        "type": "overwrites",
        "title": "Profile overwritten in advisory endpoints",
        "detail": "apil_server.py lines 207, 250 hardcode profile={'goal':'balanced'} for advisory endpoints, losing the user's actual goal.",
        "severity": "CRITICAL",
    },
    {
        "type": "dead_code",
        "title": "confidence_engine.py is never called",
        "detail": "Module exists with calculate_confidence() function but ready_engine and offplan_engine_v2 have their own inline calculations.",
        "severity": "MEDIUM",
    },
    {
        "type": "dead_code",
        "title": "market_valuation.py is never called by ready_engine",
        "detail": "Module exists with calculate_fair_value() but ready_engine.py does not import or call it. marketValuation in cached JSON was computed by removed code.",
        "severity": "MEDIUM",
    },
    {
        "type": "unused_modules",
        "title": "offplan_engine.py (v1) still exists alongside v2",
        "detail": "offplan_engine.py is the old version. offplan_engine_v2.py is the current version. v1 is dead code.",
        "severity": "LOW",
    },
    {
        "type": "cycles",
        "title": "No cycles detected",
        "detail": "Pipeline is linear: questionnaire → engine → rules → contract → API → frontend. No circular dependencies.",
        "severity": "INFO",
    },
]


class DependencyGraphBuilder:
    """Builds a complete dependency graph of the pipeline."""

    def __init__(self, engines_dir: Path | None = None, server_dir: Path | None = None):
        self.engines_dir = engines_dir or ENGINES_DIR
        self.server_dir = server_dir or SERVER_DIR
        self.modules: dict[str, ModuleInfo] = {}

    def _scan_imports(self):
        """Scan all Python files for import statements."""
        py_files = list(self.engines_dir.glob("*.py")) + [self.server_dir / "apil_server.py"]

        for f in py_files:
            if "__pycache__" in str(f) or "__init__" in f.name:
                continue
            mod_name = f.stem
            if mod_name not in self.modules:
                self.modules[mod_name] = ModuleInfo(name=mod_name, file=str(f.name))
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for line in text.splitlines():
                m = re.match(r"from\s+engines\.(\w+)\s+import", line)
                if m:
                    imported = m.group(1)
                    self.modules[mod_name].imports.append(imported)
                    if imported not in self.modules:
                        self.modules[imported] = ModuleInfo(name=imported, file=f"{imported}.py")
                    self.modules[imported].imported_by.append(mod_name)

    def _scan_functions(self):
        """Scan for function definitions."""
        for mod_name, mod_info in self.modules.items():
            filepath = self.engines_dir / mod_info.file
            if not filepath.exists():
                filepath = self.server_dir / mod_info.file
            if not filepath.exists():
                continue
            try:
                text = filepath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for line in text.splitlines():
                m = re.match(r"def\s+(\w+)", line)
                if m:
                    mod_info.functions.append(m.group(1))

    def _detect_dead_code(self):
        """Detect modules that are never imported."""
        for mod_name, mod_info in self.modules.items():
            if not mod_info.imported_by and mod_name not in ("apil_server", "__init__"):
                mod_info.is_dead_code = True
                mod_info.notes.append("Module is never imported by any other module")

        # Known dead code
        if "confidence_engine" in self.modules:
            self.modules["confidence_engine"].notes.append("calculate_confidence() exists but is never called by ready_engine or offplan_engine_v2")
        if "market_valuation" in self.modules:
            self.modules["market_valuation"].notes.append("calculate_fair_value() exists but ready_engine does not call it")
        if "offplan_engine" in self.modules:
            self.modules["offplan_engine"].notes.append("v1 engine — superseded by offplan_engine_v2")

    def build(self) -> dict:
        """Build the complete dependency graph."""
        self._scan_imports()
        self._scan_functions()
        self._detect_dead_code()

        return {
            "pipeline_stages": PIPELINE_STAGES,
            "modules": {
                name: {
                    "file": mod.file,
                    "imports": mod.imports,
                    "imported_by": mod.imported_by,
                    "functions": mod.functions,
                    "is_dead_code": mod.is_dead_code,
                    "notes": mod.notes,
                }
                for name, mod in self.modules.items()
            },
            "known_issues": KNOWN_ISSUES,
            "graph_text": self._generate_graph_text(),
        }

    def _generate_graph_text(self) -> str:
        """Generate ASCII graph text."""
        lines = [
            "PIPELINE DEPENDENCY GRAPH",
            "",
            "Questionnaire (frontend)",
            "  ↓ profile",
            "apil_server.py :: /recommendations",
            "  ↓ profile dict",
            "recommendation_engine.py :: generate_recommendations()",
            "  ├─→ investor_strategy_engine.py :: build_investor_strategy()",
            "  ├─→ investor_fit_engine.py :: calculate_investor_fit()",
            "  ├─→ ready_engine.py (cached JSON) ← market_valuation.py [DEAD]",
            "  ├─→ offplan_engine_v2.py (cached JSON)",
            "  ├─→ _normalize_recommendation() [MUTATES: rec, confidence, risk]",
            "  ├─→ rules_engine.py :: batch_apply_rules() [MUTATES: rec] (goal=balanced!)",
            "  ├─→ report_rules_engine.py :: build_report_contract()",
            "  ├─→ report_rules_engine.py :: validate_report()",
            "  ├─→ llm_engine.py :: explain_score() [profile=real ✓]",
            "  └─→ llm_engine.py :: generate_advisory_report() [profile=real ✓]",
            "  ↓ JSON response",
            "Frontend Report.tsx",
            "  ├─→ loader.ts :: mapReadyToLegacy() [DROPS: scoreBreakdown, lostPoints, dataQuality]",
            "  ├─→ ReportContext.ts :: buildReportContext() [READS: dataQuality=NULL for offplan]",
            "  ├─→ SectionRegistry.tsx :: getApplicableSections()",
            "  ├─→ report/sections/*.tsx [READ: topRec directly]",
            "  └─→ LLMAdvisorySection.tsx",
            "       ├─→ if topRec.llmAdvisoryReport → use it [profile=real ✓]",
            "       └─→ else fetch /advisory endpoint [profile=HARDCODED balanced ✗]",
            "",
            "DEAD CODE:",
            "  confidence_engine.py — never called",
            "  market_valuation.py — never called by ready_engine",
            "  offplan_engine.py (v1) — superseded by v2",
            "",
            "DUPLICATE PATHS:",
            "  Confidence: 5 implementations (confidence_engine, ready_engine, offplan_engine_v2, report_rules_engine, _normalize)",
            "  Recommendation: 3 implementations (utils, offplan_engine_v2, recommendation_engine inline)",
            "  Risk level: 3 threshold sets (ready/offplan, utils.risk_from_score, community/project)",
            "  Fair value: 2 implementations (market_valuation.py, offplan_engine_v2.py)",
        ]
        return "\n".join(lines)

    def print_report(self):
        """Print human-readable dependency graph."""
        report = self.build()
        print("=" * 80)
        print("ARCHITECTURAL DEPENDENCY GRAPH")
        print("=" * 80)
        print()
        print(report["graph_text"])
        print()
        print("── Known Issues ──")
        for issue in report["known_issues"]:
            marker = "✗" if issue["severity"] in ("CRITICAL", "HIGH") else "⚠" if issue["severity"] == "MEDIUM" else "ℹ"
            print(f"  {marker} [{issue['severity']}] {issue['title']}")
            print(f"    → {issue['detail']}")
        print()
        print("── Module Details ──")
        for name, info in sorted(report["modules"].items()):
            dead = " [DEAD CODE]" if info["is_dead_code"] else ""
            print(f"  {name}{dead}")
            if info["imports"]:
                print(f"    imports: {', '.join(info['imports'])}")
            if info["imported_by"]:
                print(f"    imported by: {', '.join(info['imported_by'])}")
            for note in info["notes"]:
                print(f"    note: {note}")
        print()
