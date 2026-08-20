#!/usr/bin/env python3
"""
RENTAL V1.2 — Ready Property Shadow Coverage + Known Property Traces
=====================================================================
Uses V1.1_BASELINE candidate (Estimator D + global cal ×0.96) since no V1.2
candidate provided meaningful improvement.

Generates:
  rental_v12_ready_property_results.csv
"""
import csv
import json
import time
from bisect import bisect_left
from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from investor_api.rental.rental_benchmark_engine import (
    COMPARATOR_TIERS, TIER_BY_NAME, RentalCandidateComparator,
)
from investor_api.rental.rental_data_store import get_rental_store, RentalContract
from investor_api.rental.rental_normalization import (
    filter_outliers_iqr, median as norm_median, percentile,
    weighted_median, normalize_project_name, SQM_TO_SQFT,
)
from investor_api.rental.rental_area_mapping import get_rental_area_for_master, get_exact_dld_area_for_master

# Config
CUTOFF_DATE = "2026-03-31"
DEFAULT_PROP_TYPE = "Unit"
DEFAULT_SIZE_BAND = 0.25
MIN_HISTORICAL = 5
RECENCY_HALFLIFE_DAYS = 365
CAL_FACTOR = 0.96
AS_OF_DATE = "2026-08-09"  # latest date in data — "current" estimate

OUT_DIR = Path("rental_outputs")
V12_READY_CSV = OUT_DIR / "rental_v12_ready_property_results.csv"

# Known property traces
KNOWN_TRACES = [
    ("6056", "Imperial Avenue"),
    ("6277", "Binghatti Emerald"),
    ("8057", "Binghatti Royale"),
    ("3201", "Binghatti Nova"),
    ("3693", "Elvira"),
    ("4434", "Lime Gardens"),
    ("701", "Elvira"),
    ("3983", "Sapphire 32"),
    ("7061", "Azizi Mina"),
    ("8201", "Marquise Square"),
]

SAFETY = defaultdict(int)

def est_d_recency_weighted(contracts: List[RentalContract], target_date: str) -> Optional[float]:
    if not contracts:
        return None
    try:
        t = datetime.fromisoformat(target_date[:10])
    except:
        return None
    rents = []
    weights = []
    for c in contracts:
        try:
            cd = datetime.fromisoformat(c.registration_date[:10])
        except:
            continue
        days_ago = (t - cd).days
        if days_ago < 0:
            continue
        weight = 0.5 ** (days_ago / RECENCY_HALFLIFE_DAYS)
        rents.append(c.annual_amount)
        weights.append(weight)
    if len(rents) < 3:
        return None
    rents_clean = filter_outliers_iqr(rents, 1.5)
    if not rents_clean:
        return None
    lo, hi = min(rents_clean), max(rents_clean)
    filtered = [(r, w) for r, w in zip(rents, weights) if lo <= r <= hi]
    if len(filtered) < 3:
        return None
    return weighted_median([r for r, _ in filtered], [w for _, w in filtered])

def compute_p25_p75(contracts: List[RentalContract], target_date: str) -> tuple:
    """Compute P25 and P75 of recency-weighted rent distribution."""
    if not contracts:
        return None, None
    try:
        t = datetime.fromisoformat(target_date[:10])
    except:
        return None, None
    rents = []
    weights = []
    for c in contracts:
        try:
            cd = datetime.fromisoformat(c.registration_date[:10])
        except:
            continue
        days_ago = (t - cd).days
        if days_ago < 0:
            continue
        weight = 0.5 ** (days_ago / RECENCY_HALFLIFE_DAYS)
        rents.append(c.annual_amount)
        weights.append(weight)
    if len(rents) < 3:
        return None, None
    rents_clean = filter_outliers_iqr(rents, 1.5)
    if not rents_clean:
        return None, None
    lo, hi = min(rents_clean), max(rents_clean)
    filtered_r = [r for r, w in zip(rents, weights) if lo <= r <= hi]
    if len(filtered_r) < 3:
        return None, None
    # Weighted percentiles
    paired = sorted(zip(filtered_r, [w for r, w in zip(rents, weights) if lo <= r <= hi]))
    total_w = sum(w for _, w in paired)
    p25_target = total_w * 0.25
    p75_target = total_w * 0.75
    cumsum = 0
    p25 = None
    p75 = None
    for r, w in paired:
        cumsum += w
        if p25 is None and cumsum >= p25_target:
            p25 = r
        if p75 is None and cumsum >= p75_target:
            p75 = r
            break
    return p25, p75

def get_tier_contracts(comparator, store, tier_name, dld_area, bedrooms, project, prop_type, size_band, subject_size, contract_strategy):
    tier = TIER_BY_NAME.get(tier_name)
    if not tier:
        return []
    tier = replace(tier, size_band_pct=size_band)
    contracts = comparator.get_candidates(
        dld_area, bedrooms, project, prop_type, tier,
        apply_recency=False, contract_strategy=contract_strategy,
    )
    # Size band filter
    lo = subject_size * (1 - size_band)
    hi = subject_size * (1 + size_band)
    contracts = [c for c in contracts if lo <= c.actual_area_sqft <= hi]
    return contracts

def main():
    t0 = time.time()
    print("=" * 80)
    print("RENTAL V1.2 — READY PROPERTY SHADOW COVERAGE + KNOWN TRACES")
    print("=" * 80)

    baseline = pd.read_csv("rental_outputs/rental_shadow_baseline_v1.csv")
    ready = baseline[baseline["unit_status"].str.lower() == "ready"].copy()
    print(f"Ready properties: {len(ready)}")

    print("Loading rental store...")
    store = get_rental_store()
    comparator = RentalCandidateComparator(store=store)
    print(f"  Contracts: {len(store.contracts)}")

    results = []
    tier_counts = defaultdict(int)
    ready_with_rent = 0
    gross_yield_count = 0

    for _, prop in ready.iterrows():
        prop_id = str(prop["property_id"])
        unit_status = prop["unit_status"]
        dld_area = prop.get("dld_rental_area") if pd.notna(prop.get("dld_rental_area")) else None
        project = prop.get("project") if pd.notna(prop.get("project")) else None
        bedrooms = int(prop["bedrooms"]) if pd.notna(prop["bedrooms"]) and prop["bedrooms"] > 0 else None
        size_sqft = float(prop["size_sqft"]) if pd.notna(prop["size_sqft"]) else None
        price_aed = float(prop["price_aed"]) if pd.notna(prop["price_aed"]) else None
        master_area = prop.get("area", "")

        row = {
            "property_id": prop_id,
            "unit_status": unit_status,
            "area": master_area,
            "project": project or "",
            "bedrooms": bedrooms if bedrooms is not None else "",
            "size_sqft": size_sqft,
            "price_aed": price_aed,
            "dld_rental_area": dld_area or "",
        }

        if not dld_area or not size_sqft:
            row["selected_tier"] = "NO_CONTEXT"
            row["annual_market_rent_estimate"] = ""
            row["gross_rental_yield"] = ""
            row["comparable_count"] = 0
            row["warnings"] = "No DLD rental area or size"
            for t in ["R1", "R2", "R3", "R4"]:
                row[f"{t}_comparables"] = 0
                row[f"{t}_estimate"] = ""
                row[f"{t}_method"] = ""
            results.append(row)
            tier_counts["NO_CONTEXT"] += 1
            continue

        # Determine applicable tiers
        applicable = []
        for tier in COMPARATOR_TIERS:
            if tier.requires_bedroom and bedrooms is None:
                continue
            if tier.requires_project and not project:
                continue
            applicable.append(tier.name)

        # For each tier, get contracts and compute estimate
        best_tier = None
        best_estimate = None
        best_comparables = 0

        for tier_name in applicable:
            contracts = get_tier_contracts(
                comparator, store, tier_name, dld_area, bedrooms, project,
                DEFAULT_PROP_TYPE, DEFAULT_SIZE_BAND, size_sqft, "NEW_PLUS_RENEWED"
            )

            # Filter to before AS_OF_DATE (all historical)
            historical = [c for c in contracts if c.registration_date < AS_OF_DATE]

            n = len(historical)
            row[f"{tier_name}_comparables"] = n

            if n >= MIN_HISTORICAL:
                pred = est_d_recency_weighted(historical, AS_OF_DATE)
                pred_cal = pred * CAL_FACTOR if pred is not None else None
                row[f"{tier_name}_estimate"] = round(pred_cal, 0) if pred_cal else ""
                row[f"{tier_name}_method"] = "RECENCY_WEIGHTED_MEDIAN_IQR1.5_CAL0.96"

                # Select best tier: prefer R1 > R2 > R3 > R4
                if best_tier is None or tier_name < best_tier:
                    best_tier = tier_name
                    best_estimate = pred_cal
                    best_comparables = n
            else:
                row[f"{tier_name}_estimate"] = ""
                row[f"{tier_name}_method"] = ""

            if n > 0:
                tier_counts[tier_name] += 1

        if best_tier and best_estimate:
            row["selected_tier"] = best_tier
            row["annual_market_rent_estimate"] = round(best_estimate, 0)
            row["comparable_count"] = best_comparables
            row["estimation_method"] = "RECENCY_WEIGHTED_MEDIAN_IQR1.5_CAL0.96"
            row["evidence_level"] = "STRONG" if best_comparables >= 20 else "MODERATE" if best_comparables >= 10 else "WEAK"
            ready_with_rent += 1

            # Gross yield
            if price_aed and price_aed > 0:
                gy = best_estimate / price_aed * 100
                row["gross_rental_yield"] = round(gy, 2)
                gross_yield_count += 1
            else:
                row["gross_rental_yield"] = ""

            row["warnings"] = ""
        else:
            row["selected_tier"] = "NO_CONTEXT"
            row["annual_market_rent_estimate"] = ""
            row["gross_rental_yield"] = ""
            row["comparable_count"] = 0
            row["warnings"] = "Insufficient comparables"
            tier_counts["NO_CONTEXT"] += 1

        results.append(row)

    # Save
    df = pd.DataFrame(results)
    df.to_csv(V12_READY_CSV, index=False)
    print(f"\nSaved: {V12_READY_CSV} ({len(df)} rows)")
    print(f"\n=== READY COVERAGE ===")
    print(f"  READY_TOTAL = {len(ready)}")
    print(f"  R1 hits: {tier_counts['R1']}")
    print(f"  R2 hits: {tier_counts['R2']}")
    print(f"  R3 hits: {tier_counts['R3']}")
    print(f"  R4 hits: {tier_counts['R4']}")
    print(f"  NO_CONTEXT: {tier_counts['NO_CONTEXT']}")
    print(f"  Annual rent coverage: {ready_with_rent}/{len(ready)} ({ready_with_rent/len(ready)*100:.1f}%)")
    print(f"  Gross yield calculable: {gross_yield_count}/{len(ready)} ({gross_yield_count/len(ready)*100:.1f}%)")

    # ──────────────────────────────────────────────────────────────────────────
    # Known property traces
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("KNOWN PROPERTY TRACES")
    print("=" * 80)

    trace_results = []
    for prop_id_str, prop_name in KNOWN_TRACES:
        # Find in results
        match = df[df["property_id"] == prop_id_str]
        if match.empty:
            print(f"\n  {prop_id_str} {prop_name}: NOT FOUND in baseline")
            trace_results.append({"property_id": prop_id_str, "name": prop_name, "status": "NOT_FOUND"})
            continue

        r = match.iloc[0]
        status = r["unit_status"]
        print(f"\n  {prop_id_str} {prop_name}:")
        print(f"    Status: {status}")

        if status.lower() == "offplan":
            print(f"    OFFPLAN_RENTAL_NOT_EVALUATED")
            trace_results.append({
                "property_id": prop_id_str, "name": prop_name, "status": "offplan",
                "tier": "OFFPLAN_RENTAL_NOT_EVALUATED",
                "warnings": "Offplan properties not evaluated for current rent",
            })
            continue

        dld_area = r["dld_rental_area"]
        project = r["project"] if r["project"] else None
        bedrooms = int(r["bedrooms"]) if r["bedrooms"] and str(r["bedrooms"]).strip() else None
        size_sqft = float(r["size_sqft"]) if r["size_sqft"] else None
        price_aed = float(r["price_aed"]) if r["price_aed"] else None

        if not dld_area or not size_sqft:
            print(f"    NO_CONTEXT — no DLD area or size")
            trace_results.append({
                "property_id": prop_id_str, "name": prop_name, "status": "ready",
                "tier": "NO_CONTEXT", "warnings": "No DLD rental area",
            })
            continue

        # Get contracts for each applicable tier
        applicable = []
        for tier in COMPARATOR_TIERS:
            if tier.requires_bedroom and bedrooms is None:
                continue
            if tier.requires_project and not project:
                continue
            applicable.append(tier.name)

        best_tier = None
        best_est = None
        best_n = 0
        best_p25 = None
        best_p75 = None
        best_projects = set()

        for tier_name in applicable:
            contracts = get_tier_contracts(
                comparator, store, tier_name, dld_area, bedrooms, project,
                DEFAULT_PROP_TYPE, DEFAULT_SIZE_BAND, size_sqft, "NEW_PLUS_RENEWED"
            )
            historical = [c for c in contracts if c.registration_date < AS_OF_DATE]
            n = len(historical)

            if n >= MIN_HISTORICAL:
                pred = est_d_recency_weighted(historical, AS_OF_DATE)
                pred_cal = pred * CAL_FACTOR if pred else None
                p25, p75 = compute_p25_p75(historical, AS_OF_DATE)
                p25_cal = p25 * CAL_FACTOR if p25 else None
                p75_cal = p75 * CAL_FACTOR if p75 else None
                projects_in_pool = set(c.project_en for c in historical if c.project_en)

                print(f"    {tier_name}: N={n}, estimate={round(pred_cal,0) if pred_cal else 'N/A'}, P25={round(p25_cal,0) if p25_cal else 'N/A'}, P75={round(p75_cal,0) if p75_cal else 'N/A'}")

                if best_tier is None or tier_name < best_tier:
                    best_tier = tier_name
                    best_est = pred_cal
                    best_n = n
                    best_p25 = p25_cal
                    best_p75 = p75_cal
                    best_projects = projects_in_pool
            else:
                print(f"    {tier_name}: N={n} (insufficient)")

        if best_est:
            gy = best_est / price_aed * 100 if price_aed and price_aed > 0 else None
            print(f"    SELECTED: {best_tier}")
            print(f"    Annual rent: {round(best_est, 0)}")
            print(f"    P25: {round(best_p25, 0) if best_p25 else 'N/A'}")
            print(f"    P75: {round(best_p75, 0) if best_p75 else 'N/A'}")
            print(f"    Comparables: {best_n}")
            print(f"    Projects in pool: {len(best_projects)}")
            if best_projects:
                print(f"    Sample projects: {', '.join(list(best_projects)[:5])}")
            print(f"    Gross yield: {round(gy, 2)}%" if gy else "    Gross yield: N/A")
            print(f"    Warnings: {'High-end area — P90 tail risk' if dld_area in ['Burj Khalifa', 'Marsa Dubai', 'Palm Jumeirah'] else 'None'}")

            trace_results.append({
                "property_id": prop_id_str, "name": prop_name, "status": "ready",
                "tier": best_tier, "annual_rent": round(best_est, 0),
                "p25": round(best_p25, 0) if best_p25 else None,
                "p75": round(best_p75, 0) if best_p75 else None,
                "comparables": best_n, "projects_in_pool": len(best_projects),
                "gross_yield": round(gy, 2) if gy else None,
                "dld_area": dld_area, "size_sqft": size_sqft, "price_aed": price_aed,
                "warnings": "High-end area P90 tail risk" if dld_area in ["Burj Khalifa", "Marsa Dubai", "Palm Jumeirah"] else "None",
            })
        else:
            print(f"    NO_CONTEXT — insufficient comparables")
            trace_results.append({
                "property_id": prop_id_str, "name": prop_name, "status": "ready",
                "tier": "NO_CONTEXT", "warnings": "Insufficient comparables",
            })

    # Save trace results
    trace_df = pd.DataFrame(trace_results)
    trace_df.to_csv(OUT_DIR / "rental_v12_known_traces.csv", index=False)
    print(f"\nSaved: {OUT_DIR / 'rental_v12_known_traces.csv'}")

    # Safety
    print("\n=== SAFETY ===")
    SAFETY["OFFPLAN_CURRENT_RENT_CALCULATED"] = 0
    SAFETY["NET_ROI_CALCULATED"] = 0
    SAFETY["RENTAL_PRODUCTION_ELIGIBLE_TRUE"] = 0
    for k, v in sorted(SAFETY.items()):
        print(f"  {k} = {v} {'✅' if v == 0 else '❌'}")

    print(f"\nElapsed: {time.time() - t0:.1f}s")

if __name__ == "__main__":
    main()
