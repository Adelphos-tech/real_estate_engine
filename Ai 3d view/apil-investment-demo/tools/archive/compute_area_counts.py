#!/usr/bin/env python3
"""
Compute previous vs current raw Area fallback availability
"""
import math
import sys
sys.path.insert(0, '/Users/apple/Desktop/Ai 3d view/apil-investment-demo')

from investor_api.fallback.dld_fallback_engine import (
    calculate_fallback_benchmark,
    build_verified_area_mapping,
    get_fallback_dld_store,
    load_master_df,
)

MASTER_PATH = "/Users/apple/Desktop/Ai 3d view/MASTER_FINAL.xlsx"

def main():
    master_df = load_master_df(MASTER_PATH)
    area_mapping = build_verified_area_mapping(master_df, get_fallback_dld_store())

    # We need to know canonical usability and Level 2 availability for each property
    # We'll use the API for canonical/Level 2 info, but compute Area directly
    import requests
    BASE = "http://127.0.0.1:8000"

    all_props = []
    page = 1
    while True:
        r = requests.get(f"{BASE}/opportunities", params={"limit": 50, "page": page, "include_insufficient": True}, timeout=120)
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

    print(f"Total properties from API: {len(all_props)}")

    previous_definition_available = 0
    current_raw_available = 0
    canonical_rejected = 0
    level2_rejected = 0
    genuine_area_blocked = 0

    for pid in all_props:
        # Get API info for canonical/Level 2
        r = requests.get(f"{BASE}/properties/{pid}", timeout=30)
        api_res = r.json() if r.status_code == 200 else {}
        cc = api_res.get("canonical_calculation")
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
        level2_available = api_res.get("fallback_context", {}).get("level2") is not None

        # Compute Area fallback directly
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

        area_res = calculate_fallback_benchmark(
            property_id=str(int(row.get("property_id", 0))),
            property_name=str(row.get("property_name", "")),
            area=str(row.get("area", "")),
            developer_name=str(row.get("developer_name", "")),
            current_price_aed=float(row.get("current_price_aed", 0)) if not (isinstance(row.get("current_price_aed"), float) and math.isnan(row.get("current_price_aed"))) else 0,
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
        area_eligible = area_res.get("eligible") is True

        # Previous definition: available for ALL properties
        if area_eligible:
            previous_definition_available += 1

        # Current: available only if canonical not usable AND Level 2 not available
        if canonical_usable:
            canonical_rejected += 1
            continue

        if level2_available:
            level2_rejected += 1
            continue

        if area_eligible:
            current_raw_available += 1
        else:
            genuine_area_blocked += 1

    print(f"\n previous_definition_available_count (all properties): {previous_definition_available}")
    print(f" current_raw_available_count (canonical unusable + no Level 2): {current_raw_available}")
    print(f" canonical_rejected: {canonical_rejected}")
    print(f" level2_rejected: {level2_rejected}")
    print(f" genuine_area_blocked: {genuine_area_blocked}")
    print(f" sum check: {canonical_rejected + level2_rejected + current_raw_available + genuine_area_blocked} = {len(all_props)}")


if __name__ == "__main__":
    main()
