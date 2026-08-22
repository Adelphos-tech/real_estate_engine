#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/apple/Desktop/Ai 3d view/apil-investment-demo')

import math
from investor_api.fallback.dld_fallback_v4 import (
    calculate_fallback_benchmark_v4,
    build_verified_area_mapping_v4,
    build_transaction_index_v4,
    SHADOW_FALLBACK_CONFIG_V4,
)
from investor_api.fallback.market_context_service import AREA_CONTEXT_CONFIG_V1, _get_master_df

MASTER_PATH = "/Users/apple/Desktop/Ai 3d view/MASTER_FINAL.xlsx"
DLD_CSV_PATH = "/Users/apple/Desktop/Ai 3d view/dxb_transactions_all.csv"

master_df = _get_master_df()
tx_index = build_transaction_index_v4(DLD_CSV_PATH)
area_mapping = build_verified_area_mapping_v4(master_df, None)

for pid in ["6277", "8057", "3201", "3983", "7061", "8201"]:
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

    print(f"\n=== Property {pid} | {row.get('property_name')} ===")

    # OLD engine (V4 with all sources)
    old_res = calculate_fallback_benchmark_v4(
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
        tx_index=tx_index,
        area_mapping=area_mapping,
        config=SHADOW_FALLBACK_CONFIG_V4,
        subject_project_name=str(row.get("property_name", "")),
    )

    # NEW runtime (DLD_OFFICIAL_ONLY)
    new_res = calculate_fallback_benchmark_v4(
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
        tx_index=tx_index,
        area_mapping=area_mapping,
        config=AREA_CONTEXT_CONFIG_V1,
        subject_project_name=str(row.get("property_name", "")),
    )

    print(f"OLD (all sources): eligible={old_res.get('eligible')}, level={old_res.get('level')}, tx={old_res.get('benchmark', {}).get('final_transaction_count')}, median={old_res.get('benchmark', {}).get('estimated_benchmark_aed')}")
    if not old_res.get('eligible'):
        print(f"  excluded: {old_res.get('validation', {}).get('excluded_reasons')}")

    print(f"NEW (DLD_ONLY):  eligible={new_res.get('eligible')}, level={new_res.get('level')}, tx={new_res.get('benchmark', {}).get('final_transaction_count')}, median={new_res.get('benchmark', {}).get('estimated_benchmark_aed')}")
    if not new_res.get('eligible'):
        print(f"  excluded: {new_res.get('validation', {}).get('excluded_reasons')}")
        print(f"  quality_flags: {new_res.get('validation', {}).get('quality_flags')}")
