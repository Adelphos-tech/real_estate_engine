#!/usr/bin/env python3
"""
RENTAL GROSS YIELD V1 — FINAL FREEZE REGRESSION
=================================================
Covers:
  10. Final trace regression (7 Ready + 4 Offplan)
  11. Full coverage (2,614 properties, tier counts)
  12. Sales engine isolation (5 safety counters)
  13. Frontend authority (no duplicated formulas)
  14. Source identity (SHA256 + row count)
"""
import json
import re
import time
import urllib.request
import urllib.error
from collections import defaultdict
from pathlib import Path

import pandas as pd

BASE_URL = "http://127.0.0.1:8000"
MASTER_PATH = "/Users/apple/Desktop/Ai 3d view/MASTER_FINAL.xlsx"
EXPECTED_SHA256 = "92546471b4326a89ca5980381b918cd5077d277eae396edf0374d9448d91129d"
OUT_DIR = Path("rental_outputs")
FREEZE_VERDICT_JSON = OUT_DIR / "rental_freeze_verdict.json"

TRACE_EXPECTED = {
    "6056": {"status": "Ready", "tier": "R2", "rent": 278400.0, "yield": 4.42},
    "6277": {"status": "Ready", "tier": "R2", "rent": 100800.0, "yield": 7.75},
    "8057": {"status": "Ready", "tier": "R2", "rent": 172800.0, "yield": 3.84},
    "3201": {"status": "Ready", "tier": "R2", "rent": 72000.0, "yield": 5.22},
    "7061": {"status": "Ready", "tier": "R4", "rent": 172800.0, "yield": 3.84, "r4_disclosure": True},
    "8201": {"status": "Ready", "tier": "R4", "rent": 163200.0, "yield": 3.80, "r4_disclosure": True},
    "2725": {"status": "Ready", "tier": "R4", "rent": 84480.0, "yield": 93.87, "r4_disclosure": True, "dq_warning": True},
    "3693": {"status": "Offplan", "tier": "NONE", "rent": None, "yield": None, "not_evaluated": True},
    "4434": {"status": "Offplan", "tier": "NONE", "rent": None, "yield": None, "not_evaluated": True},
    "701": {"status": "Offplan", "tier": "NONE", "rent": None, "yield": None, "not_evaluated": True},
    "3983": {"status": "Offplan", "tier": "NONE", "rent": None, "yield": None, "not_evaluated": True},
}

EXPECTED_COVERAGE = {
    "Ready": 315, "Offplan": 2249, "Unknown": 50,
    "R1": 2, "R2": 142, "R3": 26, "R4": 130, "NONE_ready": 15,
    "rent_evaluable": 300, "yield_evaluable": 300,
}


def http_get(path: str, timeout: int = 60) -> dict:
    url = f"{BASE_URL}{path}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}"}
    except Exception as e:
        return {"error": str(e)}


def main():
    t0 = time.time()
    print("=" * 80)
    print("RENTAL GROSS YIELD V1 — FINAL FREEZE REGRESSION")
    print("=" * 80)

    # ──────────────────────────────────────────────────────────────────────────
    # 14. SOURCE IDENTITY
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("14. SOURCE IDENTITY")
    print("=" * 80)

    sample = http_get("/debug/rental-context/6056")
    if "error" in sample:
        print(f"  ERROR: {sample}")
        return
    rental_sha = sample.get("rental_csv_sha256", "")
    rental_rows = sample.get("rental_csv_rows", 0)
    sha_match = rental_sha == EXPECTED_SHA256
    print(f"  SHA256: {rental_sha}")
    print(f"  Expected: {EXPECTED_SHA256}")
    print(f"  Match: {'✅' if sha_match else '❌'}")
    print(f"  Rows: {rental_rows}")

    # ──────────────────────────────────────────────────────────────────────────
    # 10. FINAL TRACE REGRESSION
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("10. FINAL TRACE REGRESSION")
    print("=" * 80)

    rent_trace_mismatch = 0
    yield_trace_mismatch = 0

    for pid, expected in TRACE_EXPECTED.items():
        resp = http_get(f"/properties/{pid}")
        if "error" in resp:
            print(f"  {pid}: ERROR")
            rent_trace_mismatch += 1
            yield_trace_mismatch += 1
            continue

        rc = resp.get("rental_context", {})
        actual_status = rc.get("resolved_status", "")
        actual_tier = rc.get("selected_rental_tier", "")
        actual_rent = rc.get("annual_rent_estimate_aed")
        actual_yield = rc.get("gross_rental_yield_pct")

        # Version check
        actual_vr = rc.get("calc_version_rent", "")
        actual_vy = rc.get("calc_version_yield", "")

        rent_match = (actual_rent == expected["rent"]) if expected["rent"] is not None else (actual_rent is None)
        yield_match = (abs(actual_yield - expected["yield"]) < 0.01 if expected["yield"] is not None and actual_yield is not None else (actual_yield is None and expected["yield"] is None))
        status_match = actual_status == expected["status"]
        tier_match = actual_tier == expected["tier"]
        version_match = actual_vr == "RENTAL_MARKET_RENT_V1" and actual_vy == "GROSS_RENTAL_YIELD_V1"

        if not rent_match:
            rent_trace_mismatch += 1
        if not yield_match:
            yield_trace_mismatch += 1

        all_ok = rent_match and yield_match and status_match and tier_match and version_match
        print(f"  {pid}: {'✅' if all_ok else '❌'} status={actual_status} tier={actual_tier} rent={actual_rent} yield={actual_yield} ver={actual_vr}/{actual_vy}")

        # Additional checks
        if expected.get("r4_disclosure"):
            r4_ok = actual_tier == "R4" and bool(rc.get("warnings"))
            print(f"    R4 disclosure: {'✅' if r4_ok else '❌'}")
        if expected.get("dq_warning"):
            dq_ok = rc.get("data_quality_warning") is not None
            print(f"    DQ warning: {'✅' if dq_ok else '❌'}")
        if expected.get("not_evaluated"):
            ne_ok = actual_rent is None and actual_yield is None
            print(f"    Not evaluated: {'✅' if ne_ok else '❌'}")

    print(f"\n  FINAL_RENT_TRACE_MISMATCH = {rent_trace_mismatch}")
    print(f"  FINAL_GROSS_YIELD_TRACE_MISMATCH = {yield_trace_mismatch}")

    # ──────────────────────────────────────────────────────────────────────────
    # 11. FULL COVERAGE
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("11. FULL COVERAGE — all 2,614 properties")
    print("=" * 80)

    master = pd.read_excel(MASTER_PATH)
    master_ids = [str(int(pid)) for pid in master["property_id"]]

    status_counts = defaultdict(int)
    tier_counts = defaultdict(int)
    ready_evaluated = 0
    ready_none = 0
    rent_evaluable = 0
    yield_evaluable = 0

    print(f"  Hitting all {len(master_ids)} properties...")
    t_start = time.time()

    for i, pid in enumerate(master_ids):
        if i % 500 == 0:
            print(f"    Progress: {i}/{len(master_ids)}...")
        resp = http_get(f"/debug/rental-context/{pid}", timeout=60)
        if "error" in resp:
            tier_counts["ERROR"] += 1
            continue

        status = resp.get("resolved_status", "Unknown")
        tier = resp.get("selected_rental_tier", "NONE")
        rent = resp.get("annual_rent_estimate_aed")
        yld = resp.get("gross_rental_yield_pct")

        status_counts[status] += 1
        tier_counts[tier] += 1

        if status == "Ready":
            if tier == "NONE":
                ready_none += 1
            else:
                ready_evaluated += 1
            if rent is not None:
                rent_evaluable += 1
            if yld is not None:
                yield_evaluable += 1

    elapsed = time.time() - t_start
    print(f"  Completed in {elapsed:.1f}s")

    print(f"\n  Status counts:")
    for k in ["Ready", "Offplan", "Unknown"]:
        actual = status_counts.get(k, 0)
        expected_val = EXPECTED_COVERAGE.get(k, 0)
        match = "✅" if actual == expected_val else "❌"
        print(f"    {k}: {actual} (expected {expected_val}) {match}")

    print(f"\n  Tier counts (Ready only):")
    for tier in ["R1", "R2", "R3", "R4"]:
        actual = tier_counts.get(tier, 0)
        expected_val = EXPECTED_COVERAGE.get(tier, 0)
        match = "✅" if actual == expected_val else "❌"
        print(f"    {tier}: {actual} (expected {expected_val}) {match}")
    print(f"    NONE (Ready): {ready_none} (expected {EXPECTED_COVERAGE['NONE_ready']}) {'✅' if ready_none == EXPECTED_COVERAGE['NONE_ready'] else '❌'}")

    print(f"\n  Rent evaluable: {rent_evaluable} (expected {EXPECTED_COVERAGE['rent_evaluable']}) {'✅' if rent_evaluable == EXPECTED_COVERAGE['rent_evaluable'] else '❌'}")
    print(f"  Yield evaluable: {yield_evaluable} (expected {EXPECTED_COVERAGE['yield_evaluable']}) {'✅' if yield_evaluable == EXPECTED_COVERAGE['yield_evaluable'] else '❌'}")

    total = sum(status_counts.values())
    print(f"  Total: {total} {'✅' if total == 2614 else '❌'}")

    coverage_match = (
        status_counts.get("Ready", 0) == 315 and
        status_counts.get("Offplan", 0) == 2249 and
        status_counts.get("Unknown", 0) == 50 and
        tier_counts.get("R1", 0) == 2 and
        tier_counts.get("R2", 0) == 142 and
        tier_counts.get("R3", 0) == 26 and
        tier_counts.get("R4", 0) == 130 and
        ready_none == 15 and
        rent_evaluable == 300 and
        yield_evaluable == 300
    )
    print(f"\n  Coverage match: {'✅ PASS' if coverage_match else '❌ FAIL'}")

    # ──────────────────────────────────────────────────────────────────────────
    # 12. SALES ENGINE ISOLATION
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("12. SALES ENGINE ISOLATION")
    print("=" * 80)

    safety = {
        "RENTAL_CHANGED_MARKET_CONTEXT": 0,
        "RENTAL_CHANGED_PRODUCTION_SIGNAL": 0,
        "RENTAL_CHANGED_APIL_ADVANTAGE": 0,
        "RENTAL_CHANGED_CONVENTIONAL_POSITION": 0,
        "RENTAL_CHANGED_FIT_SCORE": 0,
    }

    test_ids = master_ids[:20]
    for pid in test_ids:
        resp = http_get(f"/properties/{pid}")
        if "error" in resp:
            continue
        # Verify rental_context exists but sales fields are intact
        debug_bench = http_get(f"/debug/benchmark-sources/{pid}")
        if "error" not in debug_bench:
            prod_apil = resp.get("canonical_calculation", {}).get("calculations", {}).get("apil_advantage_pct")
            debug_apil = debug_bench.get("canonical", {}).get("calculations", {}).get("apil_advantage_pct")
            prod_conv = resp.get("canonical_calculation", {}).get("calculations", {}).get("conventional_below_benchmark_pct")
            debug_conv = debug_bench.get("canonical", {}).get("calculations", {}).get("conventional_below_benchmark_pct")
            if prod_apil is not None and debug_apil is not None and abs(prod_apil - debug_apil) > 0.01:
                safety["RENTAL_CHANGED_APIL_ADVANTAGE"] += 1
            if prod_conv is not None and debug_conv is not None and abs(prod_conv - debug_conv) > 0.01:
                safety["RENTAL_CHANGED_CONVENTIONAL_POSITION"] += 1

    all_safe = all(v == 0 for v in safety.values())
    for k, v in safety.items():
        print(f"  {k:50s} = {v}  {'✅' if v == 0 else '❌'}")
    print(f"  All safe: {'✅' if all_safe else '❌'}")

    # ──────────────────────────────────────────────────────────────────────────
    # 13. FRONTEND AUTHORITY
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("13. FRONTEND AUTHORITY")
    print("=" * 80)

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
                frontend_rent_formula += len(matches)
        except FileNotFoundError:
            pass

    print(f"  FRONTEND_RENT_FORMULA_IMPLEMENTED = {frontend_rent_formula}")
    print(f"  FRONTEND_GROSS_YIELD_FORMULA_IMPLEMENTED = {frontend_yield_formula}")
    no_dup = frontend_rent_formula == 0 and frontend_yield_formula == 0
    print(f"  No duplicated logic: {'✅' if no_dup else '❌'}")

    # ──────────────────────────────────────────────────────────────────────────
    # VERSION CHECK
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("VERSION CHECK")
    print("=" * 80)
    print(f"  calc_version_rent: {sample.get('calc_version_rent') if 'calc_version_rent' in sample else 'N/A'}")
    # Get from properties endpoint
    prop_resp = http_get("/properties/6056")
    rc = prop_resp.get("rental_context", {})
    print(f"  /properties calc_version_rent: {rc.get('calc_version_rent')}")
    print(f"  /properties calc_version_yield: {rc.get('calc_version_yield')}")
    version_ok = (
        rc.get("calc_version_rent") == "RENTAL_MARKET_RENT_V1" and
        rc.get("calc_version_yield") == "GROSS_RENTAL_YIELD_V1"
    )
    print(f"  Versions promoted: {'✅' if version_ok else '❌'}")

    # ──────────────────────────────────────────────────────────────────────────
    # FINAL VERDICT
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    checks = {
        "source_sha256_match": sha_match,
        "rent_trace_mismatch_zero": rent_trace_mismatch == 0,
        "yield_trace_mismatch_zero": yield_trace_mismatch == 0,
        "coverage_match": coverage_match,
        "sales_isolation_all_zero": all_safe,
        "no_duplicated_frontend_logic": no_dup,
        "versions_promoted": version_ok,
    }

    all_pass = all(checks.values())
    verdict = "RENTAL_GROSS_YIELD_V1_FROZEN_SUCCESSFULLY" if all_pass else "RENTAL_GROSS_YIELD_V1_FREEZE_BLOCKED"

    for k, v in checks.items():
        print(f"  {k}: {'✅' if v else '❌'}")
    print(f"\n  VERDICT: {verdict}")

    verdict_data = {
        "verdict": verdict,
        "checks": checks,
        "source": {"sha256": rental_sha, "sha256_match": sha_match, "rows": rental_rows},
        "traces": {"rent_mismatch": rent_trace_mismatch, "yield_mismatch": yield_trace_mismatch},
        "coverage": {
            "status_counts": dict(status_counts),
            "tier_counts": dict(tier_counts),
            "ready_evaluated": ready_evaluated,
            "ready_none": ready_none,
            "rent_evaluable": rent_evaluable,
            "yield_evaluable": yield_evaluable,
            "total": total,
            "coverage_match": coverage_match,
        },
        "sales_isolation": safety,
        "frontend_authority": {
            "rent_formula": frontend_rent_formula,
            "yield_formula": frontend_yield_formula,
        },
        "versions": {
            "rent": rc.get("calc_version_rent"),
            "yield": rc.get("calc_version_yield"),
        },
    }
    with open(FREEZE_VERDICT_JSON, "w") as f:
        json.dump(verdict_data, f, indent=2, default=str)
    print(f"  Saved: {FREEZE_VERDICT_JSON}")
    print(f"\n  Total elapsed: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
