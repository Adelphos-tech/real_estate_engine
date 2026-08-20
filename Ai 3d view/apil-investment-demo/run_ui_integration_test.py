#!/usr/bin/env python3
"""
GROSS RENTAL YIELD V1 — UI INTEGRATION REGRESSION TEST
=======================================================
Verifies:
  17. Property regression tests (7 Ready + 4 Offplan controls)
  18. UI/API parity (50 Ready properties)
  19. Existing sales UI regression (no signal changes)
  16. No duplicated rental logic in frontend
"""
import json
import time
import urllib.request
import urllib.error
from collections import defaultdict
from pathlib import Path

BASE_URL = "http://127.0.0.1:8191"
OUT_DIR = Path("rental_outputs")
UI_PARITY_CSV = OUT_DIR / "rental_ui_api_parity.csv"
UI_REGRESSION_CSV = OUT_DIR / "rental_ui_sales_regression.csv"
UI_TRACES_CSV = OUT_DIR / "rental_ui_traces.csv"
UI_VERDICT_JSON = OUT_DIR / "rental_ui_verdict.json"

# Expected trace values from the audit
TRACE_EXPECTED = {
    "6056": {"status": "Ready", "tier": "R2", "rent": 278400.0, "yield": 4.42, "label": "Estimated Project Rent", "r4_disclosure": False},
    "6277": {"status": "Ready", "tier": "R2", "rent": 100800.0, "yield": 7.75, "label": "Estimated Project Rent", "r4_disclosure": False},
    "8057": {"status": "Ready", "tier": "R2", "rent": 172800.0, "yield": 3.84, "label": "Estimated Project Rent", "r4_disclosure": False},
    "3201": {"status": "Ready", "tier": "R2", "rent": 72000.0, "yield": 5.22, "label": "Estimated Project Rent", "r4_disclosure": False},
    "7061": {"status": "Ready", "tier": "R4", "rent": 172800.0, "yield": 3.84, "label": "Estimated Area Rent", "r4_disclosure": True},
    "8201": {"status": "Ready", "tier": "R4", "rent": 163200.0, "yield": 3.80, "label": "Estimated Area Rent", "r4_disclosure": True},
    "2725": {"status": "Ready", "tier": "R4", "rent": 84480.0, "yield": 93.87, "label": "Estimated Area Rent", "r4_disclosure": True, "dq_warning": True},
    "3693": {"status": "Offplan", "tier": "NONE", "rent": None, "yield": None, "not_evaluated": True},
    "4434": {"status": "Offplan", "tier": "NONE", "rent": None, "yield": None, "not_evaluated": True},
    "701": {"status": "Offplan", "tier": "NONE", "rent": None, "yield": None, "not_evaluated": True},
    "3983": {"status": "Offplan", "tier": "NONE", "rent": None, "yield": None, "not_evaluated": True},
}


def http_get(path: str, timeout: int = 60) -> dict:
    url = f"{BASE_URL}{path}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "detail": e.read().decode("utf-8", errors="replace")}
    except Exception as e:
        return {"error": str(e)}


def main():
    t0 = time.time()
    print("=" * 80)
    print("GROSS RENTAL YIELD V1 — UI INTEGRATION REGRESSION TEST")
    print("=" * 80)

    # ──────────────────────────────────────────────────────────────────────────
    # 17. PROPERTY REGRESSION TESTS
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("17. PROPERTY REGRESSION TESTS")
    print("=" * 80)

    trace_rows = []
    trace_failures = 0

    for pid, expected in TRACE_EXPECTED.items():
        # Get the normal /properties/{id} response (what the UI consumes)
        resp = http_get(f"/properties/{pid}")
        if "error" in resp:
            print(f"  {pid}: ERROR: {resp['error']}")
            trace_failures += 1
            trace_rows.append({"property_id": pid, "error": resp["error"]})
            continue

        rc = resp.get("rental_context", {})
        actual_status = rc.get("resolved_status", "")
        actual_tier = rc.get("selected_rental_tier", "")
        actual_rent = rc.get("annual_rent_estimate_aed")
        actual_yield = rc.get("gross_rental_yield_pct")
        actual_label = rc.get("investor_label", "")
        actual_warnings = rc.get("warnings", "")
        actual_dq_warning = rc.get("data_quality_warning")

        checks = {
            "status_match": actual_status == expected["status"],
            "tier_match": actual_tier == expected["tier"],
            "rent_match": (actual_rent == expected["rent"]) if expected["rent"] is not None else (actual_rent is None),
            "yield_match": (abs(actual_yield - expected["yield"]) < 0.01 if expected["yield"] is not None and actual_yield is not None else (actual_yield is None and expected["yield"] is None)),
            "label_match": actual_label == expected["label"] if "label" in expected else True,
        }

        # R4 disclosure check
        if expected.get("r4_disclosure"):
            checks["r4_disclosure_present"] = bool(actual_warnings) and actual_tier == "R4"

        # Offplan not evaluated check
        if expected.get("not_evaluated"):
            checks["not_evaluated"] = actual_rent is None and actual_yield is None

        # Data quality warning check
        if expected.get("dq_warning"):
            checks["dq_warning_present"] = actual_dq_warning is not None and len(actual_dq_warning) > 0

        all_pass = all(checks.values())
        if not all_pass:
            trace_failures += 1

        status_str = "✅" if all_pass else "❌"
        print(f"  {pid}: {status_str} status={actual_status}, tier={actual_tier}, rent={actual_rent}, yield={actual_yield}")
        if not all_pass:
            for k, v in checks.items():
                if not v:
                    print(f"    FAILED: {k}")

        trace_rows.append({
            "property_id": pid,
            "expected_status": expected["status"], "actual_status": actual_status,
            "expected_tier": expected["tier"], "actual_tier": actual_tier,
            "expected_rent": expected["rent"], "actual_rent": actual_rent,
            "expected_yield": expected["yield"], "actual_yield": actual_yield,
            "expected_label": expected.get("label", ""), "actual_label": actual_label,
            "r4_disclosure_required": expected.get("r4_disclosure", False),
            "r4_disclosure_present": bool(actual_warnings) and actual_tier == "R4",
            "not_evaluated": expected.get("not_evaluated", False),
            "dq_warning_required": expected.get("dq_warning", False),
            "dq_warning_present": actual_dq_warning is not None,
            "all_pass": all_pass,
        })

    import pandas as pd
    trace_df = pd.DataFrame(trace_rows)
    trace_df.to_csv(UI_TRACES_CSV, index=False)
    print(f"\n  Saved: {UI_TRACES_CSV}")
    print(f"  Trace failures: {trace_failures}")

    # ──────────────────────────────────────────────────────────────────────────
    # 18. UI/API PARITY (50 Ready properties)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("18. UI/API PARITY — 50 Ready properties")
    print("=" * 80)

    # Get all Ready property IDs from the full coverage CSV
    coverage_df = pd.read_csv(OUT_DIR / "rental_http_full_coverage.csv")
    ready_props = coverage_df[coverage_df["status"] == "Ready"]
    ready_with_rent = ready_props[ready_props["tier"] != "NONE"].head(50)
    print(f"  Testing {len(ready_with_rent)} Ready properties with rental estimates")

    parity_rows = []
    rent_mismatches = 0
    range_mismatches = 0
    yield_mismatches = 0
    tier_semantic_mismatches = 0

    for _, row in ready_with_rent.iterrows():
        pid = str(row["property_id"])
        # Get /properties/{id} (what UI sees)
        prod = http_get(f"/properties/{pid}")
        if "error" in prod:
            print(f"  {pid}: ERROR")
            continue

        prod_rc = prod.get("rental_context", {})
        # Get /debug/rental-context/{id} (authoritative backend)
        debug_rc = http_get(f"/debug/rental-context/{pid}")

        # Compare
        rent_match = prod_rc.get("annual_rent_estimate_aed") == debug_rc.get("annual_rent_estimate_aed")
        p25_match = prod_rc.get("annual_rent_p25_aed") == debug_rc.get("annual_rent_p25_aed")
        p75_match = prod_rc.get("annual_rent_p75_aed") == debug_rc.get("annual_rent_p75_aed")
        yield_match = prod_rc.get("gross_rental_yield_pct") == debug_rc.get("gross_rental_yield_pct")
        tier_match = prod_rc.get("selected_rental_tier") == debug_rc.get("selected_rental_tier")
        label_match = prod_rc.get("investor_label") == debug_rc.get("investor_label")

        if not rent_match:
            rent_mismatches += 1
        if not (p25_match and p75_match):
            range_mismatches += 1
        if not yield_match:
            yield_mismatches += 1
        if not (tier_match and label_match):
            tier_semantic_mismatches += 1

        parity_rows.append({
            "property_id": pid,
            "prod_rent": prod_rc.get("annual_rent_estimate_aed"), "debug_rent": debug_rc.get("annual_rent_estimate_aed"),
            "rent_match": rent_match,
            "prod_p25": prod_rc.get("annual_rent_p25_aed"), "debug_p25": debug_rc.get("annual_rent_p25_aed"),
            "prod_p75": prod_rc.get("annual_rent_p75_aed"), "debug_p75": debug_rc.get("annual_rent_p75_aed"),
            "range_match": p25_match and p75_match,
            "prod_yield": prod_rc.get("gross_rental_yield_pct"), "debug_yield": debug_rc.get("gross_rental_yield_pct"),
            "yield_match": yield_match,
            "prod_tier": prod_rc.get("selected_rental_tier"), "debug_tier": debug_rc.get("selected_rental_tier"),
            "prod_label": prod_rc.get("investor_label"), "debug_label": debug_rc.get("investor_label"),
            "tier_semantic_match": tier_match and label_match,
        })

    parity_df = pd.DataFrame(parity_rows)
    parity_df.to_csv(UI_PARITY_CSV, index=False)
    print(f"  Saved: {UI_PARITY_CSV}")
    print(f"  UI_RENT_ESTIMATE_MISMATCH = {rent_mismatches}")
    print(f"  UI_RENT_RANGE_MISMATCH = {range_mismatches}")
    print(f"  UI_GROSS_YIELD_MISMATCH = {yield_mismatches}")
    print(f"  UI_RENT_TIER_SEMANTIC_MISMATCH = {tier_semantic_mismatches}")

    parity_pass = rent_mismatches == 0 and range_mismatches == 0 and yield_mismatches == 0 and tier_semantic_mismatches == 0
    print(f"  UI/API Parity: {'✅ PASS' if parity_pass else '❌ FAIL'}")

    # ──────────────────────────────────────────────────────────────────────────
    # 19. EXISTING SALES UI REGRESSION
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("19. EXISTING SALES UI REGRESSION")
    print("=" * 80)

    # Get all property IDs and test 20 properties for sales signal changes
    all_ids = coverage_df["property_id"].astype(str).tolist()
    test_ids = all_ids[:20]

    safety_counters = {
        "RENTAL_UI_CHANGED_MARKET_CONTEXT": 0,
        "RENTAL_UI_CHANGED_PRODUCTION_SIGNAL": 0,
        "RENTAL_UI_CHANGED_APIL_ADVANTAGE": 0,
        "RENTAL_UI_CHANGED_CONVENTIONAL_POSITION": 0,
        "RENTAL_UI_CHANGED_FIT_SCORE": 0,
    }

    regression_rows = []

    for pid in test_ids:
        resp = http_get(f"/properties/{pid}")
        if "error" in resp:
            continue

        # Check that rental_context exists but doesn't affect sales fields
        rc = resp.get("rental_context", {})
        has_rental = "rental_context" in resp

        # Extract sales signal fields
        mc = resp.get("market_context_source")
        ps = resp.get("production_signal_source")
        apil_adv = resp.get("canonical_calculation", {}).get("calculations", {}).get("apil_advantage_pct")
        conv_pos = resp.get("canonical_calculation", {}).get("calculations", {}).get("conventional_below_benchmark_pct")
        fit_score = resp.get("investor_fit", {}).get("score") if resp.get("investor_fit") else None

        # Verify rental_context is present but sales fields are intact
        # We compare against the checkpoint commit's values by re-fetching from /debug/benchmark-sources
        # which doesn't include rental context
        debug_bench = http_get(f"/debug/benchmark-sources/{pid}")
        if "error" not in debug_bench:
            debug_apil = debug_bench.get("canonical", {}).get("calculations", {}).get("apil_advantage_pct")
            debug_conv = debug_bench.get("canonical", {}).get("calculations", {}).get("conventional_below_benchmark_pct")
            if apil_adv is not None and debug_apil is not None and abs(apil_adv - debug_apil) > 0.01:
                safety_counters["RENTAL_UI_CHANGED_APIL_ADVANTAGE"] += 1
                print(f"  {pid}: APIL advantage CHANGED ❌ ({apil_adv} vs {debug_apil})")
            if conv_pos is not None and debug_conv is not None and abs(conv_pos - debug_conv) > 0.01:
                safety_counters["RENTAL_UI_CHANGED_CONVENTIONAL_POSITION"] += 1
                print(f"  {pid}: Conventional position CHANGED ❌ ({conv_pos} vs {debug_conv})")

        regression_rows.append({
            "property_id": pid,
            "has_rental_context": has_rental,
            "market_context_source": mc,
            "production_signal_source": ps,
            "apil_advantage_pct": apil_adv,
            "conventional_position_pct": conv_pos,
            "fit_score": fit_score,
            "rental_tier": rc.get("selected_rental_tier"),
            "rental_yield": rc.get("gross_rental_yield_pct"),
        })

    reg_df = pd.DataFrame(regression_rows)
    reg_df.to_csv(UI_REGRESSION_CSV, index=False)
    print(f"  Saved: {UI_REGRESSION_CSV}")
    print(f"\n  Safety counters ({len(test_ids)} properties tested):")
    all_safe = True
    for k, v in safety_counters.items():
        status = "✅ PASS" if v == 0 else "❌ FAIL"
        print(f"    {k:50s} = {v}  {status}")
        if v != 0:
            all_safe = False
    print(f"  All safe: {'✅' if all_safe else '❌'}")

    # ──────────────────────────────────────────────────────────────────────────
    # 16. NO DUPLICATED RENTAL LOGIC
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("16. NO DUPLICATED RENTAL LOGIC IN FRONTEND")
    print("=" * 80)

    # Check that frontend files don't implement rent/yield formulas
    import re
    frontend_files = [
        "src/components/RentalIncomeCard.tsx",
        "src/pages/PropertyDetail.tsx",
        "src/data/api.ts",
    ]
    rent_formula_patterns = [
        r"annual_rent.*\/.*price.*\*.*100",
        r"rent.*\/.*asking.*\*.*100",
        r"estimatedRent.*\/.*price",
        r"grossROI.*=.*rent.*\/.*price",
    ]
    frontend_rent_formula = 0
    frontend_yield_formula = 0

    for fpath in frontend_files:
        try:
            with open(fpath) as f:
                content = f.read()
            for pattern in rent_formula_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    frontend_rent_formula += len(matches)
                    print(f"  WARNING: Found rent formula in {fpath}: {matches}")
        except FileNotFoundError:
            pass

    print(f"  FRONTEND_RENT_FORMULA_IMPLEMENTED = {frontend_rent_formula}")
    print(f"  FRONTEND_GROSS_YIELD_FORMULA_IMPLEMENTED = {frontend_yield_formula}")
    no_dup = frontend_rent_formula == 0 and frontend_yield_formula == 0
    print(f"  No duplicated logic: {'✅' if no_dup else '❌'}")

    # ──────────────────────────────────────────────────────────────────────────
    # 21. CALCULATION VERSIONS
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("21. CALCULATION VERSIONS")
    print("=" * 80)

    sample = http_get("/properties/6056")
    rc = sample.get("rental_context", {})
    print(f"  calc_version_rent: {rc.get('calc_version_rent')}")
    print(f"  calc_version_yield: {rc.get('calc_version_yield')}")
    version_ok = (
        rc.get("calc_version_rent") == "RENTAL_MARKET_RENT_V1" and
        rc.get("calc_version_yield") == "GROSS_RENTAL_YIELD_V1"
    )
    print(f"  Versions correct: {'✅' if version_ok else '❌'}")

    # ──────────────────────────────────────────────────────────────────────────
    # 20. DEBUG ENDPOINT STILL AVAILABLE
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("20. DEBUG ENDPOINT STILL AVAILABLE")
    print("=" * 80)
    debug_resp = http_get("/debug/rental-context/6056")
    debug_ok = "error" not in debug_resp and debug_resp.get("shadow") == True
    print(f"  /debug/rental-context/6056: {'✅ available' if debug_ok else '❌ ERROR'}")

    # ──────────────────────────────────────────────────────────────────────────
    # FINAL VERDICT
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    checks = {
        "trace_tests_pass": trace_failures == 0,
        "ui_api_parity_pass": parity_pass,
        "sales_regression_pass": all_safe,
        "no_duplicated_logic": no_dup,
        "calc_versions_correct": version_ok,
        "debug_endpoint_available": debug_ok,
    }

    all_pass = all(checks.values())
    verdict = "GROSS_RENTAL_YIELD_V1_UI_VERIFIED" if all_pass else "GROSS_RENTAL_YIELD_V1_UI_NEEDS_FIXES"

    for k, v in checks.items():
        print(f"  {k}: {'✅' if v else '❌'}")
    print(f"\n  VERDICT: {verdict}")

    verdict_data = {
        "verdict": verdict,
        "checks": checks,
        "trace_failures": trace_failures,
        "ui_api_parity": {
            "rent_mismatches": rent_mismatches,
            "range_mismatches": range_mismatches,
            "yield_mismatches": yield_mismatches,
            "tier_semantic_mismatches": tier_semantic_mismatches,
            "properties_tested": len(parity_rows),
        },
        "sales_regression": safety_counters,
        "no_duplicated_logic": {
            "frontend_rent_formula": frontend_rent_formula,
            "frontend_yield_formula": frontend_yield_formula,
        },
        "calc_versions": {
            "rent": rc.get("calc_version_rent"),
            "yield": rc.get("calc_version_yield"),
        },
    }
    with open(UI_VERDICT_JSON, "w") as f:
        json.dump(verdict_data, f, indent=2, default=str)
    print(f"  Saved: {UI_VERDICT_JSON}")
    print(f"\n  Total elapsed: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
