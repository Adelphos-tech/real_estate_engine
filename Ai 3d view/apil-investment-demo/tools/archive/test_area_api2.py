#!/usr/bin/env python3
import requests

BASE = "http://127.0.0.1:8000"
TEST_IDS = ["3693", "4434"]

for pid in TEST_IDS:
    r = requests.get(f"{BASE}/properties/{pid}", timeout=30)
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

    print(f"Property {pid}: canonical={canonical_usable}, level2={'YES' if fb.get('level2') else 'NO'}, area={'YES' if fb.get('area_fallback') else 'NO'}, mcs={mcs}, pss={pss}")
