import json

with open("verification/verification_report.json") as f:
    r = json.load(f)

lines = []
lines.append("# APIL Pipeline Verification Report")
lines.append("")
gen_at = r.get("final_report", {}).get("generated_at", "unknown")
lines.append(f"Generated: {gen_at}")
lines.append("")
lines.append("---")
lines.append("")

# Summary table
lines.append("## Verification Summary")
lines.append("")
lines.append("| Module | Key Finding |")
lines.append("|---|---|")
pt = r.get("pipeline_trace", {}).get("summary", {})
pt_fails = pt.get("fails", 0)
pt_warns = pt.get("warnings", 0)
pt_fields = pt.get("total_fields_tracked", 0)
lines.append(f"| D1-3 Pipeline Trace | {pt_fails} FAIL, {pt_warns} WARN, {pt_fields} fields tracked |")
dup = r.get("duplicate_calculations", {}).get("summary", {})
dup_fields = dup.get("fields_with_duplicates", 0)
dup_sites = dup.get("total_calculation_sites", 0)
lines.append(f"| D4 Duplicate Calculations | {dup_fields} fields with duplicates, {dup_sites} total sites |")
mut = r.get("mutation_detection", {}).get("summary", {})
mut_total = mut.get("total_mutations", 0)
mut_multi = mut.get("fields_with_multiple_mutations", 0)
lines.append(f"| D5 Mutation Detection | {mut_total} mutations, {mut_multi} fields with >2 |")
dto = r.get("dto_verification", {}).get("summary", {})
dto_ready = dto.get("only_ready", 0)
dto_offplan = dto.get("only_offplan", 0)
dto_types = dto.get("type_mismatches", 0)
lines.append(f"| D6 DTO Verification | {dto_ready} only-ready, {dto_offplan} only-offplan, {dto_types} type mismatches |")
fe = r.get("frontend_verification", {}).get("summary", {})
fe_vals = fe.get("values_tracked", 0)
fe_issues = fe.get("issues_found", 0)
lines.append(f"| D7 Frontend Verification | {fe_vals} values tracked, {fe_issues} issues |")
llm = r.get("llm_verification", {}).get("summary", {})
llm_fails = llm.get("fails", 0)
llm_warns = llm.get("warnings", 0)
lines.append(f"| D8 LLM Verification | {llm_fails} FAIL, {llm_warns} WARN |")
dg = r.get("dependency_graph", {}).get("known_issues", [])
critical = sum(1 for i in dg if i.get("severity") == "CRITICAL")
high = sum(1 for i in dg if i.get("severity") == "HIGH")
lines.append(f"| D9 Dependency Graph | {len(dg)} issues ({critical} critical, {high} high) |")
th = r.get("test_harness", {}).get("summary", {})
th_total = th.get("total_tests", 0)
th_skip = th.get("skipped", 0)
lines.append(f"| D10 Test Harness | {th_total} test profiles, {th_skip} skipped |")
fr = r.get("final_report", {})
fr_count = len(fr.get("deterministic_fields", []))
lines.append(f"| Final Report | {fr_count} fields fully mapped |")
lines.append("")
lines.append("---")
lines.append("")

# D4: Duplicate Calculations
lines.append("## D4: Duplicate Calculation Detection")
lines.append("")
dup_fields_data = r.get("duplicate_calculations", {}).get("fields", {})
lines.append("| Field | Sites | Files | Status | Source of Truth |")
lines.append("|---|---|---|---|---|")
for fn, info in sorted(dup_fields_data.items()):
    status = "FAIL — DUPLICATE" if info.get("is_duplicate") else "PASS"
    files = ", ".join(info.get("unique_files", []))
    sot = info.get("recommended_source_of_truth", "")
    cnt = info.get("count", 0)
    lines.append(f"| {fn} | {cnt} | {files} | {status} | {sot} |")
lines.append("")
lines.append("### Duplicate Calculation Sites")
lines.append("")
for fn, info in sorted(dup_fields_data.items()):
    if not info.get("is_duplicate"):
        continue
    lines.append(f"#### {fn}")
    lines.append("")
    for site in info.get("sites", []):
        sf = site.get("file", "")
        sl = site.get("line", "")
        sfunc = site.get("function", "")
        sform = site.get("formula", "")
        lines.append(f"- `{sf}:{sl}` in `{sfunc}()` — `{sform}`")
    lines.append("")
lines.append("---")
lines.append("")

# D5: Mutation Detection
lines.append("## D5: Mutation Detection")
lines.append("")
mut_fields_data = r.get("mutation_detection", {}).get("fields", {})
lines.append("| Field | Mutations | Files | Status |")
lines.append("|---|---|---|---|")
for fn, info in sorted(mut_fields_data.items()):
    files = ", ".join(info.get("unique_files", []))
    status = info.get("status", "?")
    cnt = info.get("total_mutations", 0)
    lines.append(f"| {fn} | {cnt} | {files} | {status} |")
lines.append("")
lines.append("### Mutation Details")
lines.append("")
for fn, info in sorted(mut_fields_data.items()):
    status = info.get("status", "?")
    lines.append(f"#### {fn} — {status}")
    lines.append("")
    for mut in info.get("mutations", []):
        mf = mut.get("file", "")
        ml = mut.get("line", "")
        mfunc = mut.get("function", "")
        mtype = mut.get("type", "")
        mcode = mut.get("code", "")
        lines.append(f"- `{mf}:{ml}` in `{mfunc}()` [{mtype}]")
        lines.append(f"  - `{mcode}`")
    lines.append("")
lines.append("---")
lines.append("")

# D6: DTO Verification
lines.append("## D6: DTO Verification — Ready vs Off-plan")
lines.append("")
dto_data = r.get("dto_verification", {})
ds = dto_data.get("summary", {})
lines.append(f"- Ready fields: {ds.get('ready_fields', 0)}")
lines.append(f"- Off-plan fields: {ds.get('offplan_fields', 0)}")
lines.append(f"- Common: {ds.get('common_fields', 0)}")
lines.append(f"- Only in ready: {ds.get('only_ready', 0)}")
lines.append(f"- Only in off-plan: {ds.get('only_offplan', 0)}")
lines.append(f"- Type mismatches: {ds.get('type_mismatches', 0)}")
lines.append(f"- Nested issues: {ds.get('nested_issues', 0)}")
lines.append(f"- Missing critical: {ds.get('missing_critical', 0)}")
lines.append("")
oir = dto_data.get("only_in_ready", [])
if oir:
    lines.append("### Fields Only in Ready DTO")
    lines.append("")
    for f in oir:
        lines.append(f"- `{f}`")
    lines.append("")
oio = dto_data.get("only_in_offplan", [])
if oio:
    lines.append("### Fields Only in Off-plan DTO")
    lines.append("")
    for f in oio:
        lines.append(f"- `{f}`")
    lines.append("")
tms = dto_data.get("type_mismatches", [])
if tms:
    lines.append("### Type Mismatches")
    lines.append("")
    lines.append("| Field | Ready Type | Off-plan Type |")
    lines.append("|---|---|---|")
    for tm in tms:
        lines.append(f"| {tm['field']} | {tm['ready_type']} | {tm['offplan_type']} |")
    lines.append("")
nis = dto_data.get("nested_issues", [])
if nis:
    lines.append("### Nested Structure Issues")
    lines.append("")
    for ni in nis:
        np_ = ni.get("path", "")
        nd = ni.get("detail", "")
        lines.append(f"- `{np_}`: {nd}")
    lines.append("")
seqs = dto_data.get("semantic_equivalents", {})
if seqs:
    lines.append("### Semantic Equivalents (different names, same meaning)")
    lines.append("")
    lines.append("| Concept | Ready | Off-plan | Issue |")
    lines.append("|---|---|---|---|")
    for name, info in seqs.items():
        r_val = info.get("ready", "")
        o_val = info.get("offplan", "")
        issue = info.get("issue", "")
        lines.append(f"| {name} | `{r_val}` | `{o_val}` | {issue} |")
    lines.append("")
mcf = dto_data.get("missing_critical_fields", [])
if mcf:
    lines.append("### Missing Critical Fields")
    lines.append("")
    lines.append("| Field | In Ready | In Off-plan | Impact |")
    lines.append("|---|---|---|---|")
    for mc in mcf:
        lines.append(f"| {mc['field']} | {mc['in_ready']} | {mc['in_offplan']} | {mc['impact']} |")
    lines.append("")
rud = dto_data.get("recommended_unified_dto", [])
if rud:
    lines.append("### Recommended Unified DTO")
    lines.append("")
    for rec in rud:
        lines.append(f"- {rec}")
    lines.append("")
lines.append("---")
lines.append("")

# D8: LLM Verification
lines.append("## D8: LLM Prompt Verification")
lines.append("")
llm_data = r.get("llm_verification", {})
llm_checks = llm_data.get("checks", [])
lines.append("| Status | Type | Function | Line | Field | Detail |")
lines.append("|---|---|---|---|---|---|")
for c in llm_checks:
    cs = c.get("status", "")
    ct = c.get("check_type", "")
    cf = c.get("function", "")
    cl = c.get("line", "")
    cfield = c.get("field", "")
    cd = c.get("detail", "")
    lines.append(f"| {cs} | {ct} | {cf} | {cl} | {cfield} | {cd} |")
lines.append("")
llm_fails_list = llm_data.get("fails", [])
if llm_fails_list:
    lines.append("### Failures")
    lines.append("")
    for c in llm_fails_list:
        ct = c.get("check_type", "")
        cf = c.get("function", "")
        cl = c.get("line", "")
        cfield = c.get("field", "")
        cd = c.get("detail", "")
        lines.append(f"- **[{ct}]** `{cf}:{cl}` — **{cfield}**")
        lines.append(f"  - {cd}")
    lines.append("")
lines.append("---")
lines.append("")

# D9: Dependency Graph
lines.append("## D9: Architectural Dependency Graph")
lines.append("")
dg_data = r.get("dependency_graph", {})
gt = dg_data.get("graph_text", "")
if gt:
    lines.append("```")
    lines.append(gt)
    lines.append("```")
    lines.append("")
ki = dg_data.get("known_issues", [])
lines.append("### Known Issues")
lines.append("")
lines.append("| Severity | Title | Detail |")
lines.append("|---|---|---|")
for issue in ki:
    sev = issue.get("severity", "")
    title = issue.get("title", "")
    detail = issue.get("detail", "")
    lines.append(f"| {sev} | {title} | {detail} |")
lines.append("")
mods = dg_data.get("modules", {})
lines.append("### Module Details")
lines.append("")
lines.append("| Module | Dead Code | Imports | Imported By | Notes |")
lines.append("|---|---|---|---|---|")
for name, info in sorted(mods.items()):
    if name.startswith("._"):
        continue
    dead = "YES" if info.get("is_dead_code") else "no"
    imports = ", ".join(info.get("imports", [])) or "—"
    imported_by = ", ".join(info.get("imported_by", [])) or "—"
    notes = "; ".join(info.get("notes", [])) or "—"
    lines.append(f"| {name} | {dead} | {imports} | {imported_by} | {notes} |")
lines.append("")
lines.append("---")
lines.append("")

# D10: Test Harness
lines.append("## D10: Test Harness — Snapshot Framework")
lines.append("")
th_data = r.get("test_harness", {})
ts = th_data.get("summary", {})
lines.append(f"- Total test profiles: {ts.get('total_tests', 0)}")
sf = th_data.get("snapshot_fields", [])
lines.append(f"- Snapshot fields per test: {len(sf)}")
lines.append("")
lines.append("### Test Profiles")
lines.append("")
lines.append("| Name | Goal | Budget | Type | Beds | Timeline | Risk |")
lines.append("|---|---|---|---|---|---|---|")
for tp in th_data.get("test_profiles", []):
    p = tp.get("profile", {})
    name = tp.get("name", "")
    goal = p.get("goal", "—")
    budget = p.get("budget", "—")
    ptype = p.get("property_type", "—")
    beds = p.get("bedrooms", "—")
    timeline = p.get("timeline", "—")
    risk = p.get("risk", "—")
    lines.append(f"| {name} | {goal} | {budget} | {ptype} | {beds} | {timeline} | {risk} |")
lines.append("")
lines.append("### Snapshot Fields Tracked")
lines.append("")
for f in sf:
    lines.append(f"- `{f}`")
lines.append("")
lines.append("---")
lines.append("")

# Final Report
lines.append("## Final Architecture Report — Deterministic Field Map")
lines.append("")
final = r.get("final_report", {})
for f in final.get("deterministic_fields", []):
    risk = f.get("architectural_risk", "LOW")
    field_name = f.get("field", "")
    lines.append(f"### `{field_name}` — Risk: {risk}")
    lines.append("")
    origin = f.get("origin", "Unknown")
    lines.append(f"- **Origin**: {origin}")
    mods_list = f.get("modifiers", [])
    if mods_list:
        lines.append("- **Modifiers**:")
        for m in mods_list:
            lines.append(f"  - {m}")
    dups_list = f.get("duplicates", [])
    if dups_list:
        lines.append("- **Duplicate calculations**:")
        for d in dups_list:
            lines.append(f"  - {d}")
    hv_list = f.get("hardcoded_values", [])
    if hv_list:
        lines.append("- **Hardcoded values**:")
        for h in hv_list:
            lines.append(f"  - {h}")
    fb_list = f.get("fallbacks", [])
    if fb_list:
        lines.append("- **Fallbacks**:")
        for fb in fb_list:
            lines.append(f"  - {fb}")
    inc_list = f.get("inconsistencies", [])
    if inc_list:
        lines.append("- **Inconsistencies**:")
        for inc in inc_list:
            lines.append(f"  - {inc}")
    uc_list = f.get("unused_calculations", [])
    if uc_list:
        lines.append("- **Unused calculations**:")
        for u in uc_list:
            lines.append(f"  - {u}")
    sot = f.get("recommended_source_of_truth", "Needs analysis")
    lines.append(f"- **Recommended source of truth**: {sot}")
    lines.append("")
lines.append("---")
lines.append("")

# Proposed architecture
lines.append("## Proposed Future Architecture")
lines.append("")
for item in final.get("proposed_future_architecture", []):
    lines.append(f"- {item}")
lines.append("")

with open("verification/VERIFICATION_REPORT.md", "w") as f:
    f.write("\n".join(lines))

print("Written VERIFICATION_REPORT.md")
print(f"Lines: {len(lines)}")
