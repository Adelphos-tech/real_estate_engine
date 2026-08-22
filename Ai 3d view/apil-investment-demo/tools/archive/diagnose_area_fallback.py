#!/usr/bin/env python3
"""
Diagnose Area Fallback Wiring — Trace availability → selection
"""
import json
import math
import random
import sys
sys.path.insert(0, '/Users/apple/Desktop/Ai 3d view/apil-investment-demo')

from investor_api.fallback.dld_fallback_engine import (
    calculate_fallback_benchmark,
    build_verified_area_mapping,
    get_fallback_dld_store,
    load_master_df,
)
from investor_api.dld_benchmark_engine import (
    compute_project_benchmark,
    resolve_canonical_status,
    _canonical_status,
)

MASTER_PATH = "/Users/apple/Desktop/Ai 3d view/MASTER_FINAL.xlsx"
BASE_URL = "http://127.0.0.1:8000"

def get_api_property(pid):
    import requests
    try:
        r = requests.get(f"{BASE_URL}/properties/{pid}", timeout=30)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def diagnose_property(pid, master_df, area_mapping):
    row = master_df[master_df["property_id"] == int(pid)]
    if row.empty:
        return {"error": "not in MASTER"}
    row = row.iloc[0]

    bedrooms = row.get("unit_bedrooms")
    size_sqft = row.get("unit_size_sqft")
    if isinstance(bedrooms, float) and math.isnan(bedrooms):
        bedrooms = None
    if isinstance(size_sqft, float) and math.isnan(size_sqft):
        size_sqft = None

    api_res = get_api_property(pid)
    canonical = api_res.get("canonical_calculation") if api_res else None
    canonical_usable = False
    if canonical:
        canonical_usable = (
            canonical.get("benchmark_method") == "CANONICAL_DLD" and
            canonical.get("benchmark_tier") == "LEVEL_1" and
            canonical.get("is_fallback") == False and
            canonical.get("production_eligible") == True and
            canonical.get("validation_status") == "VERIFIED_PRODUCTION" and
            canonical.get("evidence", {}).get("median") is not None and
            canonical.get("evidence", {}).get("transaction_count", 0) >= 3
        )

    level2 = api_res.get("fallback_context", {}).get("level2") if api_res else None

    area_res = calculate_fallback_benchmark(
        property_id=str(int(row.get("property_id", 0))),
        property_name=str(row.get("property_name", "")),
        area=str(row.get("area", "")),
        developer_name=str(row.get("developer_name", "")),
        current_price_aed=float(row.get("current_price_aed", 0)) if hasattr(row.get("current_price_aed"), '__float__') else 0,
        unit_bedrooms=int(bedrooms) if bedrooms is not None else None,
        unit_bathrooms=row.get("unit_bathrooms"),
        unit_size_sqft=float(size_sqft) if size_sqft is not None else None,
        unit_size_sqm=float(row.get("unit_size_sqm")) if row.get("unit_size_sqm") is not None and not (isinstance(row.get("unit_size_sqm"), float) and math.isnan(row.get("unit_size_sqm"))) else None,
        unit_status=str(row.get("unit_status", "")),
        property_type=str(row.get("property_type", "")) if row.get("property_type") is not None else None,
        bedroom_value_status=str(row.get("bedroom_value_status", "")),
        dld_evidence_status=str(row.get("dld_evidence_status", "")),
        area_mapping=area_mapping,
    )

    # Check what keys main_v2.py is looking for vs what area_res provides
    main_looks_for = {
        "benchmark_median": area_res.get("benchmark_median"),
        "transaction_count": area_res.get("transaction_count"),
        "evidence_level": area_res.get("evidence_level"),
        "benchmark_method": area_res.get("benchmark_method"),
        "benchmark_tier": area_res.get("benchmark_tier"),
        "matched_area": area_res.get("matched_area"),
        "bedroom_filter": area_res.get("bedroom_filter"),
        "status_filter": area_res.get("status_filter"),
    }

    actual_provides = {
        "eligible": area_res.get("eligible"),
        "level": area_res.get("level"),
        "estimated_benchmark_aed": area_res.get("benchmark", {}).get("estimated_benchmark_aed"),
        "final_transaction_count": area_res.get("benchmark", {}).get("final_transaction_count"),
        "raw_transaction_count": area_res.get("benchmark", {}).get("raw_transaction_count"),
        "unique_project_count": area_res.get("benchmark", {}).get("unique_project_count"),
        "mapped_dld_area": area_res.get("benchmark", {}).get("mapped_dld_area"),
        "size_band_applied": area_res.get("benchmark", {}).get("size_band_applied"),
        "status_broadened": area_res.get("benchmark", {}).get("status_broadened"),
    }

    return {
        "pid": pid,
        "name": str(row.get("property_name", "")),
        "area": str(row.get("area", "")),
        "bedrooms": bedrooms,
        "size_sqft": size_sqft,
        "canonical_usable": canonical_usable,
        "level2_available": level2 is not None,
        "api_market_context_source": api_res.get("market_context_source") if api_res else None,
        "api_production_signal_source": api_res.get("production_signal_source") if api_res else None,
        "area_eligible": area_res.get("eligible"),
        "area_level": area_res.get("level"),
        "area_excluded_reasons": area_res.get("validation", {}).get("excluded_reasons", []),
        "area_quality_flags": area_res.get("validation", {}).get("quality_flags", []),
        "main_looks_for": main_looks_for,
        "actual_provides": actual_provides,
    }


def main():
    master_df = load_master_df(MASTER_PATH)
    area_mapping = build_verified_area_mapping(master_df, get_fallback_dld_store())

    test_ids = ["6277", "3201", "3983", "7061", "8057", "8201"]

    print("=" * 80)
    print("PER-PROPERTY DIAGNOSIS")
    print("=" * 80)
    for pid in test_ids:
        d = diagnose_property(pid, master_df, area_mapping)
        print(json.dumps(d, indent=2, default=str))
        print("-" * 80)

    # Sample 25 NO_CONTEXT properties
    print("\n" + "=" * 80)
    print("SAMPLING 25 NO-CONTEXT PROPERTIES")
    print("=" * 80)

    all_props = []
    import requests
    page = 1
    while True:
        r = requests.get(f"{BASE_URL}/opportunities", params={"limit": 50, "page": page, "include_insufficient": True}, timeout=120)
        data = r.json()
        results = data.get("results", [])
        if not results:
            break
        for res in results:
            pid = res.get("property", {}).get("id")
            if pid:
                all_props.append(pid)
        if len(all_props) >= data.get("total", 0):
            break
        page += 1
        if page > 100:
            break

    # Get those with market_context_source = NONE
    no_context_ids = []
    for pid in all_props:
        api_res = get_api_property(pid)
        if api_res and api_res.get("market_context_source") == "NONE":
            no_context_ids.append(pid)

    print(f"Total properties: {len(all_props)}")
    print(f"NO_CONTEXT properties: {len(no_context_ids)}")

    sample = random.sample(no_context_ids, min(25, len(no_context_ids)))

    for pid in sample:
        d = diagnose_property(pid, master_df, area_mapping)
        print(json.dumps({
            "pid": d["pid"],
            "name": d["name"],
            "area": d["area"],
            "bedrooms": d["bedrooms"],
            "size_sqft": d["size_sqft"],
            "canonical_usable": d["canonical_usable"],
            "level2_available": d["level2_available"],
            "area_eligible": d["area_eligible"],
            "area_level": d["area_level"],
            "area_excluded_reasons": d["area_excluded_reasons"],
            "actual_estimated_benchmark_aed": d["actual_provides"]["estimated_benchmark_aed"],
            "actual_final_tx_count": d["actual_provides"]["final_transaction_count"],
            "main_would_see_benchmark_median": d["main_looks_for"]["benchmark_median"],
            "api_market_context_source": d["api_market_context_source"],
        }, indent=2, default=str))
        print("-" * 40)

    # Aggregate counters
    print("\n" + "=" * 80)
    print("AGGREGATE COUNTERS")
    print("=" * 80)

    area_called = 0
    area_returned_object = 0
    area_eligible = 0
    area_valid_median = 0
    area_valid_tx = 0
    area_identity_valid = 0
    area_blocked = 0
    area_available = 0
    area_selected = 0

    for pid in all_props:
        row = master_df[master_df["property_id"] == int(pid)]
        if row.empty:
            continue
        row = row.iloc[0]
        bedrooms = row.get("unit_bedrooms")
        size_sqft = row.get("unit_size_sqft")
        if isinstance(bedrooms, float) and math.isnan(bedrooms):
            bedrooms = None
        if isinstance(size_sqft, float) and math.isnan(size_sqft):
            size_sqft = None

        area_called += 1
        area_res = calculate_fallback_benchmark(
            property_id=str(int(row.get("property_id", 0))),
            property_name=str(row.get("property_name", "")),
            area=str(row.get("area", "")),
            developer_name=str(row.get("developer_name", "")),
            current_price_aed=float(row.get("current_price_aed", 0)) if hasattr(row.get("current_price_aed"), '__float__') else 0,
            unit_bedrooms=int(bedrooms) if bedrooms is not None else None,
            unit_bathrooms=row.get("unit_bathrooms"),
            unit_size_sqft=float(size_sqft) if size_sqft is not None else None,
            unit_size_sqm=float(row.get("unit_size_sqm")) if row.get("unit_size_sqm") is not None and not (isinstance(row.get("unit_size_sqm"), float) and math.isnan(row.get("unit_size_sqm"))) else None,
            unit_status=str(row.get("unit_status", "")),
            property_type=str(row.get("property_type", "")) if row.get("property_type") is not None else None,
            bedroom_value_status=str(row.get("bedroom_value_status", "")),
            dld_evidence_status=str(row.get("dld_evidence_status", "")),
            area_mapping=area_mapping,
        )
        area_returned_object += 1
        if area_res.get("eligible"):
            area_eligible += 1
            bm = area_res.get("benchmark", {})
            if bm.get("estimated_benchmark_aed") is not None and bm["estimated_benchmark_aed"] > 0:
                area_valid_median += 1
            if bm.get("final_transaction_count", 0) > 0:
                area_valid_tx += 1
            level = area_res.get("level", "")
            if level in ("AREA_SAME_BEDROOM_SIZE_ADJUSTED_EVIDENCE", "AREA_SAME_BEDROOM_EVIDENCE"):
                area_identity_valid += 1
            area_available += 1
        else:
            area_blocked += 1

        api_res = get_api_property(pid)
        if api_res and api_res.get("market_context_source") == "AREA_FALLBACK":
            area_selected += 1

    print(f"area_function_called_count: {area_called}")
    print(f"area_function_returned_object_count: {area_returned_object}")
    print(f"area_function_valid_median_count: {area_valid_median}")
    print(f"area_function_valid_tx_count: {area_valid_tx}")
    print(f"area_function_identity_valid_count: {area_identity_valid}")
    print(f"area_function_blocked_count: {area_blocked}")
    print(f"area_function_available_count: {area_available}")
    print(f"area_context_selected_count: {area_selected}")


if __name__ == "__main__":
    main()
