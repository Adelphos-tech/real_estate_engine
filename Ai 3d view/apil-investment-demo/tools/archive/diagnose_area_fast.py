#!/usr/bin/env python3
"""
Fast Area Fallback Diagnosis — no API calls, direct function only
"""
import json
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

    test_ids = [6277, 3201, 3983, 7061, 8057, 8201]

    print("=" * 80)
    print("PER-PROPERTY DIAGNOSIS (Direct Function)")
    print("=" * 80)
    for pid in test_ids:
        row = master_df[master_df["property_id"] == pid]
        if row.empty:
            print(f"{pid}: NOT IN MASTER")
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

        print(f"\n--- Property {pid} | {row.get('property_name')} ---")
        print(f"eligible: {area_res.get('eligible')}")
        print(f"level: {area_res.get('level')}")
        bm = area_res.get("benchmark", {})
        print(f"estimated_benchmark_aed: {bm.get('estimated_benchmark_aed')}")
        print(f"final_transaction_count: {bm.get('final_transaction_count')}")
        print(f"raw_transaction_count: {bm.get('raw_transaction_count')}")
        print(f"unique_project_count: {bm.get('unique_project_count')}")
        print(f"mapped_dld_area: {bm.get('mapped_dld_area')}")
        print(f"excluded_reasons: {area_res.get('validation', {}).get('excluded_reasons', [])}")
        print(f"quality_flags: {area_res.get('validation', {}).get('quality_flags', [])}")
        print(f"main_v2.py looks for 'benchmark_median': {area_res.get('benchmark_median')}")
        print(f"main_v2.py looks for 'transaction_count': {area_res.get('transaction_count')}")

    # Aggregate across ALL MASTER properties
    print("\n" + "=" * 80)
    print("AGGREGATE ACROSS ALL 2,614 MASTER PROPERTIES")
    print("=" * 80)

    area_called = 0
    area_returned_object = 0
    area_eligible = 0
    area_valid_median = 0
    area_valid_tx = 0
    area_identity_valid = 0
    area_blocked = 0
    area_available = 0
    area_level_counts = {}
    area_block_reasons = {}

    for _, row in master_df.iterrows():
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
        area_returned_object += 1

        level = area_res.get("level", "UNKNOWN")
        area_level_counts[level] = area_level_counts.get(level, 0) + 1

        if area_res.get("eligible"):
            area_eligible += 1
            bm = area_res.get("benchmark", {})
            if bm.get("estimated_benchmark_aed") is not None and bm["estimated_benchmark_aed"] > 0:
                area_valid_median += 1
            if bm.get("final_transaction_count", 0) > 0:
                area_valid_tx += 1
            if level in ("AREA_SAME_BEDROOM_SIZE_ADJUSTED_EVIDENCE", "AREA_SAME_BEDROOM_EVIDENCE"):
                area_identity_valid += 1
            area_available += 1
        else:
            area_blocked += 1
            reasons = area_res.get("validation", {}).get("excluded_reasons", [])
            for r in reasons:
                area_block_reasons[r] = area_block_reasons.get(r, 0) + 1

    print(f"area_function_called_count: {area_called}")
    print(f"area_function_returned_object_count: {area_returned_object}")
    print(f"area_function_eligible_count: {area_eligible}")
    print(f"area_function_valid_median_count: {area_valid_median}")
    print(f"area_function_valid_tx_count: {area_valid_tx}")
    print(f"area_function_identity_valid_count: {area_identity_valid}")
    print(f"area_function_blocked_count: {area_blocked}")
    print(f"area_function_available_count: {area_available}")
    print(f"\nLevel distribution:")
    for lvl, cnt in sorted(area_level_counts.items(), key=lambda x: -x[1]):
        print(f"  {lvl}: {cnt}")
    print(f"\nBlock reason distribution:")
    for reason, cnt in sorted(area_block_reasons.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {cnt}")

    # What main_v2.py would see vs what function provides
    print("\n" + "=" * 80)
    print("WIRING BUG CONFIRMATION")
    print("=" * 80)
    print("main_v2.py looks for 'benchmark_median' at top level")
    print("calculate_fallback_benchmark stores it at result['benchmark']['estimated_benchmark_aed']")
    print("main_v2.py looks for 'transaction_count' at top level")
    print("calculate_fallback_benchmark stores it at result['benchmark']['final_transaction_count']")
    print("main_v2.py looks for 'evidence_level' at top level")
    print("calculate_fallback_benchmark stores it at result['level']")
    print("main_v2.py does NOT check result['eligible']")
    print("Therefore: area_fallback_raw.get('benchmark_median') is ALWAYS None")
    print("Therefore: area_fallback is NEVER selected even when function produces valid results")


if __name__ == "__main__":
    main()
