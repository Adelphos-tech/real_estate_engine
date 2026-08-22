#!/usr/bin/env python3
import requests
import json

BASE = "http://127.0.0.1:8000"

TEST_IDS = ["6277", "3201", "3983", "7061", "8057", "8201"]

for pid in TEST_IDS:
    r = requests.get(f"{BASE}/properties/{pid}", timeout=30)
    if r.status_code != 200:
        print(f"{pid}: API error {r.status_code}")
        continue
    d = r.json()
    cc = d.get("canonical_calculation")
    fb = d.get("fallback_context", {})
    mcs = d.get("market_context_source", "NONE")
    pss = d.get("production_signal_source", "NONE")

    canonical_usable = False
    if cc:
        canonical_usable = (
            cc.get("benchmark_method") == "CANONICAL_DLD" and
            cc.get("benchmark_tier") == "LEVEL_1" and
            cc.get("is_fallback") == False and
            cc.get("production_eligible") == True and
            cc.get("validation_status") == "VERIFIED_PRODUCTION" and
            cc.get("evidence", {}).get("median") is not None and
            cc.get("evidence", {}).get("transaction_count", 0) >= 3
        )

    print(f"\n=== Property {pid} ===")
    print(f"canonical_usable: {canonical_usable}")
    print(f"level2: {'YES' if fb.get('level2') else 'NO'}")
    print(f"area_fallback: {'YES' if fb.get('area_fallback') else 'NO'}")
    if fb.get('area_fallback'):
        a = fb['area_fallback']
        print(f"  benchmark_median: {a.get('benchmark_median')}")
        print(f"  transaction_count: {a.get('transaction_count')}")
        print(f"  benchmark_tier: {a.get('benchmark_tier')}")
        print(f"  evidence_level: {a.get('evidence_level')}")
        print(f"  validation_status: {a.get('validation_status')}")
        print(f"  matched_area: {a.get('matched_area')}")
        print(f"  unique_projects: {a.get('unique_projects')}")
    print(f"market_context_source: {mcs}")
    print(f"production_signal_source: {pss}")
