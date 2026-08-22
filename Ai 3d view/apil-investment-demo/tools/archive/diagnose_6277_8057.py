#!/usr/bin/env python3
"""
Deep diagnosis of 6277 and 8057 - trace exact values from both functions
"""
import math
import sys
sys.path.insert(0, '/Users/apple/Desktop/Ai 3d view/apil-investment-demo')

import requests
from investor_api.fallback.ui_benchmark_source_validation import compute_level2_exact_project_status_broadened
from investor_api.fallback.dld_fallback_engine import (
    calculate_fallback_benchmark,
    build_verified_area_mapping,
    get_fallback_dld_store,
    load_master_df,
)

MASTER_PATH = "/Users/apple/Desktop/Ai 3d view/MASTER_FINAL.xlsx"
BASE = "http://127.0.0.1:8000"

def get_api(pid):
    r = requests.get(f"{BASE}/properties/{pid}", timeout=30)
    return r.json() if r.status_code == 200 else {}

def main():
    master_df = load_master_df(MASTER_PATH)
    area_mapping = build_verified_area_mapping(master_df, get_fallback_dld_store())

    for pid in ["6277", "8057"]:
        print(f"\n{'='*80}")
        print(f"PROPERTY {pid}")
        print(f"{'='*80}")

        # API result
        api = get_api(pid)
        cc = api.get("canonical_calculation")
        fb = api.get("fallback_context", {})
        mcs = api.get("market_context_source", "NONE")
        pss = api.get("production_signal_source", "NONE")

        print(f"\n--- API RESPONSE ---")
        print(f"canonical benchmark_method: {cc.get('benchmark_method') if cc else 'None'}")
        print(f"canonical benchmark_tier: {cc.get('benchmark_tier') if cc else 'None'}")
        print(f"canonical is_fallback: {cc.get('is_fallback') if cc else 'None'}")
        print(f"canonical production_eligible: {cc.get('production_eligible') if cc else 'None'}")
        print(f"canonical validation_status: {cc.get('validation_status') if cc else 'None'}")
        print(f"canonical transaction_count: {cc.get('evidence', {}).get('transaction_count') if cc else 'None'}")
        print(f"canonical median: {cc.get('evidence', {}).get('median') if cc else 'None'}")
        print(f"market_context_source: {mcs}")
        print(f"production_signal_source: {pss}")
        print(f"level2 from API: {'YES' if fb.get('level2') else 'NO'}")
        if fb.get('level2'):
            l2 = fb['level2']
            print(f"  level2 benchmark_median: {l2.get('benchmark_median')}")
            print(f"  level2 transaction_count: {l2.get('transaction_count')}")
            print(f"  level2 benchmark_tier: {l2.get('benchmark_tier')}")
            print(f"  level2 production_eligible: {l2.get('production_eligible')}")
        print(f"area_fallback from API: {'YES' if fb.get('area_fallback') else 'NO'}")
        if fb.get('area_fallback'):
            a = fb['area_fallback']
            print(f"  area benchmark_median: {a.get('benchmark_median')}")
            print(f"  area transaction_count: {a.get('transaction_count')}")
            print(f"  area benchmark_tier: {a.get('benchmark_tier')}")
            print(f"  area production_eligible: {a.get('production_eligible')}")

        # Direct Level 2 call
        print(f"\n--- DIRECT LEVEL 2 CALL ---")
        row = master_df[master_df["property_id"] == int(pid)]
        if not row.empty:
            row = row.iloc[0]
            project_name = str(row.get("property_name", ""))
            subject_price = float(row.get("current_price_aed", 0)) if not (isinstance(row.get("current_price_aed"), float) and math.isnan(row.get("current_price_aed"))) else 0
            bedrooms = row.get("unit_bedrooms")
            if isinstance(bedrooms, float) and math.isnan(bedrooms):
                bedrooms = None

            l2_raw = compute_level2_exact_project_status_broadened(
                project_name=project_name,
                subject_price=subject_price,
                bedroom=int(bedrooms) if bedrooms is not None else None,
            )
            print(f"level2 benchmark_median: {l2_raw.get('benchmark_median')}")
            print(f"level2 transaction_count: {l2_raw.get('transaction_count')}")
            print(f"level2 usable_for_investment: {l2_raw.get('usable_for_investment')}")
            print(f"level2 evidence_level: {l2_raw.get('evidence_level')}")
            print(f"level2 match_confidence: {l2_raw.get('match_confidence')}")
            print(f"level2 insufficient_evidence_reason: {l2_raw.get('insufficient_evidence_reason')}")
            print(f"level2 warnings: {l2_raw.get('warnings', [])}")
            # Source provenance
            txs = l2_raw.get("transactions", [])
            print(f"level2 total transactions: {len(txs)}")
            if txs:
                # Show a sample
                for i, t in enumerate(txs[:3]):
                    print(f"  tx[{i}]: price={t.get('price_aed')}, area={t.get('area')}, procedure={t.get('procedure')}")

        # Direct Area call
        print(f"\n--- DIRECT AREA CALL ---")
        if not row.empty:
            size_sqft = row.get("unit_size_sqft")
            if isinstance(size_sqft, float) and math.isnan(size_sqft):
                size_sqft = None
            area_raw = calculate_fallback_benchmark(
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
            print(f"area eligible: {area_raw.get('eligible')}")
            print(f"area level: {area_raw.get('level')}")
            bm = area_raw.get("benchmark", {})
            print(f"area estimated_benchmark_aed: {bm.get('estimated_benchmark_aed')}")
            print(f"area final_transaction_count: {bm.get('final_transaction_count')}")
            print(f"area raw_transaction_count: {bm.get('raw_transaction_count')}")
            print(f"area unique_project_count: {bm.get('unique_project_count')}")
            print(f"area mapped_dld_area: {bm.get('mapped_dld_area')}")
            print(f"area excluded_reasons: {area_raw.get('validation', {}).get('excluded_reasons', [])}")
            # Source provenance
            txs = area_raw.get("comparables", [])
            print(f"area total comparables: {len(txs)}")
            if txs:
                for i, t in enumerate(txs[:3]):
                    print(f"  comp[{i}]: price={t.get('price_aed')}, area={t.get('area')}, project={t.get('project')}, status={t.get('status')}")


if __name__ == "__main__":
    main()
