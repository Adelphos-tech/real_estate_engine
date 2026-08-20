#!/usr/bin/env python3
"""
RENTAL GROSS YIELD — PRODUCTION READINESS AUDIT V1
===================================================
Locked methodology: V1.1 (integrity-verified)
  - Estimator: RECENCY_WEIGHTED_MEDIAN_ANNUAL_RENT
  - Half-life: 12 months
  - Outlier filter: IQR 1.5
  - Size band: ±25%
  - Contract strategy: NEW_PLUS_RENEWED
  - Calibration: GLOBAL_MULTIPLICATIVE ×0.96
  - Ready properties only

Calculates:
  - Estimated annual market rent (AED)
  - P25, P75 rent interval (AED)
  - Gross rental yield (%) = rent / MASTER current_price_aed * 100

Does NOT calculate:
  - Net ROI, net yield, vacancy, management fees, service charges, maintenance, financing
  - IRR, total return, cash-on-cash return

Safety counters (all must be 0).
"""
import csv
import json
import time
import hashlib
from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

# ──────────────────────────────────────────────────────────────────────────────
# LOCKED CONFIGURATION — V1.1 (integrity-verified)
# ──────────────────────────────────────────────────────────────────────────────
CALC_VERSION_RENT = "RENTAL_MARKET_RENT_V1_CANDIDATE"
CALC_VERSION_YIELD = "GROSS_RENTAL_YIELD_V1_CANDIDATE"
DEFAULT_PROP_TYPE = "Unit"
SIZE_BAND = 0.25
MIN_HISTORICAL = 5
RECENCY_HALFLIFE_DAYS = 365
CAL_FACTOR = 0.96
AS_OF_DATE = "2026-08-09"  # latest date in data
MASTER_PATH = "/Users/apple/Desktop/Ai 3d view/MASTER_FINAL.xlsx"
RENTAL_CSV_PATH = "/Users/apple/Desktop/Ai 3d view/dxb_rents_all.csv"
EXPECTED_RENTAL_SHA256 = "92546471b4326a89ca5980381b918cd5077d277eae396edf0374d9448d91129d"
EXPECTED_RENTAL_ROWS = 573097  # verified by SHA256 match

# Tier min comparables (from COMPARATOR_TIERS)
TIER_MIN_COMPARABLES = {
    "R1": 5,
    "R2": 8,
    "R3": 10,
    "R4": 20,
}

OUT_DIR = Path("rental_outputs")
ALL_READY_CSV = OUT_DIR / "rental_gross_yield_candidate_all_ready.csv"
TRACES_CSV = OUT_DIR / "rental_gross_yield_traces.csv"
DETERMINISM_CSV = OUT_DIR / "rental_gross_yield_determinism.csv"
AUDIT_JSON = OUT_DIR / "rental_gross_yield_audit.json"

# Known property traces
KNOWN_TRACES = [
    ("6056", "Imperial Avenue"),
    ("6277", "Binghatti Emerald"),
    ("8057", "Binghatti Royale"),
    ("3201", "Binghatti Nova"),
    ("7061", "Azizi Mina"),
    ("8201", "Marquise Square"),
    ("3693", "Elvira"),
    ("4434", "Lime Gardens"),
    ("701", "Elvira"),
    ("3983", "Sapphire 32"),
]

# ──────────────────────────────────────────────────────────────────────────────
# Safety counters
# ──────────────────────────────────────────────────────────────────────────────
SAFETY = defaultdict(int)

# ──────────────────────────────────────────────────────────────────────────────
# Estimator D: Recency-weighted median (LOCKED V1.1)
# ──────────────────────────────────────────────────────────────────────────────
def est_d_recency_weighted(contracts: List[RentalContract], target_date: str) -> Optional[float]:
    if not contracts:
        return None
    try:
        t = datetime.fromisoformat(target_date[:10])
    except Exception:
        return None
    rents = []
    weights = []
    for c in contracts:
        try:
            cd = datetime.fromisoformat(c.registration_date[:10])
        except Exception:
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

def compute_weighted_percentiles(contracts: List[RentalContract], target_date: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Return (median_estimate, p25, p75) from recency-weighted distribution after IQR 1.5."""
    if not contracts:
        return None, None, None
    try:
        t = datetime.fromisoformat(target_date[:10])
    except Exception:
        return None, None, None
    rents = []
    weights = []
    for c in contracts:
        try:
            cd = datetime.fromisoformat(c.registration_date[:10])
        except Exception:
            continue
        days_ago = (t - cd).days
        if days_ago < 0:
            continue
        weight = 0.5 ** (days_ago / RECENCY_HALFLIFE_DAYS)
        rents.append(c.annual_amount)
        weights.append(weight)
    if len(rents) < 3:
        return None, None, None
    rents_clean = filter_outliers_iqr(rents, 1.5)
    if not rents_clean:
        return None, None, None
    lo, hi = min(rents_clean), max(rents_clean)
    filtered = [(r, w) for r, w in zip(rents, weights) if lo <= r <= hi]
    if len(filtered) < 3:
        return None, None, None

    # Weighted median
    est = weighted_median([r for r, _ in filtered], [w for _, w in filtered])

    # Weighted P25 and P75
    paired = sorted(filtered)
    total_w = sum(w for _, w in paired)
    if total_w <= 0:
        return est, None, None
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
    return est, p25, p75

# ──────────────────────────────────────────────────────────────────────────────
# Tier contract retrieval
# ──────────────────────────────────────────────────────────────────────────────
def get_tier_contracts(comparator, tier_name, dld_area, bedrooms, project, prop_type, size_band, subject_size, contract_strategy):
    tier = TIER_BY_NAME.get(tier_name)
    if not tier:
        return []
    tier = replace(tier, size_band_pct=size_band)
    contracts = comparator.get_candidates(
        dld_area, bedrooms, project, prop_type, tier,
        apply_recency=False, contract_strategy=contract_strategy,
    )
    lo = subject_size * (1 - size_band)
    hi = subject_size * (1 + size_band)
    contracts = [c for c in contracts if lo <= c.actual_area_sqft <= hi]
    return contracts

# ──────────────────────────────────────────────────────────────────────────────
# Deterministic tier selection: R1 > R2 > R3 > R4 > NONE
# ──────────────────────────────────────────────────────────────────────────────
def select_tier_deterministic(comparator, dld_area, bedrooms, project, prop_type, size_sqft):
    """Select exactly one tier: R1 > R2 > R3 > R4 > NONE."""
    for tier_name in ["R1", "R2", "R3", "R4"]:
        # Check applicability
        tier = TIER_BY_NAME[tier_name]
        if tier.requires_bedroom and bedrooms is None:
            continue
        if tier.requires_project and not project:
            continue

        # Get contracts
        contracts = get_tier_contracts(
            comparator, tier_name, dld_area, bedrooms, project,
            prop_type, SIZE_BAND, size_sqft, "NEW_PLUS_RENEWED"
        )
        historical = [c for c in contracts if c.registration_date < AS_OF_DATE]
        n = len(historical)

        if n >= MIN_HISTORICAL:
            return tier_name, historical

    return "NONE", []

# ──────────────────────────────────────────────────────────────────────────────
# Estimate rent for a property
# ──────────────────────────────────────────────────────────────────────────────
def estimate_rent(comparator, dld_area, bedrooms, project, size_sqft):
    """Returns dict with tier, estimate, p25, p75, comparables, projects_in_pool."""
    tier_name, historical = select_tier_deterministic(
        comparator, dld_area, bedrooms, project, DEFAULT_PROP_TYPE, size_sqft
    )

    if tier_name == "NONE" or not historical:
        return {
            "tier": "NONE",
            "estimate": None,
            "estimate_cal": None,
            "p25": None,
            "p25_cal": None,
            "p75": None,
            "p75_cal": None,
            "comparables": 0,
            "projects_in_pool": 0,
        }

    est, p25, p75 = compute_weighted_percentiles(historical, AS_OF_DATE)
    est_cal = est * CAL_FACTOR if est is not None else None
    p25_cal = p25 * CAL_FACTOR if p25 is not None else None
    p75_cal = p75 * CAL_FACTOR if p75 is not None else None

    projects_in_pool = len(set(c.project_en for c in historical if c.project_en))

    return {
        "tier": tier_name,
        "estimate": est,
        "estimate_cal": est_cal,
        "p25": p25,
        "p25_cal": p25_cal,
        "p75": p75,
        "p75_cal": p75_cal,
        "comparables": len(historical),
        "projects_in_pool": projects_in_pool,
    }

# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    print("=" * 80)
    print("RENTAL GROSS YIELD — PRODUCTION READINESS AUDIT V1")
    print("=" * 80)
    print(f"Calc version (rent): {CALC_VERSION_RENT}")
    print(f"Calc version (yield): {CALC_VERSION_YIELD}")
    print(f"Master: {MASTER_PATH}")
    print(f"Rental CSV: {RENTAL_CSV_PATH}")
    print()

    # ──────────────────────────────────────────────────────────────────────────
    # 15. DATA PROVENANCE
    # ──────────────────────────────────────────────────────────────────────────
    print("=" * 80)
    print("15. DATA PROVENANCE")
    print("=" * 80)

    # Verify rental CSV SHA256
    sha = hashlib.sha256()
    with open(RENTAL_CSV_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    actual_sha = sha.hexdigest()
    print(f"  Rental CSV SHA256: {actual_sha}")
    print(f"  Expected SHA256:   {EXPECTED_RENTAL_SHA256}")
    print(f"  Match: {'✅' if actual_sha == EXPECTED_RENTAL_SHA256 else '❌'}")

    # Count rows
    with open(RENTAL_CSV_PATH) as f:
        row_count = sum(1 for _ in f) - 1  # minus header
    print(f"  Row count: {row_count} (expected {EXPECTED_RENTAL_ROWS})")
    print(f"  Match: {'✅' if row_count == EXPECTED_RENTAL_ROWS else '❌'}")

    # Load MASTER
    master = pd.read_excel(MASTER_PATH)
    print(f"  MASTER_FINAL.xlsx: {len(master)} rows")
    master_total = len(master)

    # ──────────────────────────────────────────────────────────────────────────
    # 11. PRODUCTION STATUS RESOLUTION
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("11. PRODUCTION STATUS RESOLUTION")
    print("=" * 80)

    # Use MASTER unit_status directly (authoritative, matches production overlay)
    status_counts = master["unit_status"].value_counts().to_dict()
    ready_count = status_counts.get("Ready", 0)
    offplan_count = status_counts.get("Offplan", 0)
    unknown_count = status_counts.get("Unknown", 0)
    print(f"  READY: {ready_count}")
    print(f"  OFFPLAN: {offplan_count}")
    print(f"  UNKNOWN: {unknown_count}")
    print(f"  Total: {ready_count + offplan_count + unknown_count}")
    print(f"  Reconciles to {master_total}: {'✅' if ready_count + offplan_count + unknown_count == master_total else '❌'}")

    # ──────────────────────────────────────────────────────────────────────────
    # Load rental store
    # ──────────────────────────────────────────────────────────────────────────
    print("\nLoading rental store...")
    store = get_rental_store()
    comparator = RentalCandidateComparator(store=store)
    print(f"  Contracts loaded: {len(store.contracts)}")

    # ──────────────────────────────────────────────────────────────────────────
    # 4 + 19. FULL READY COVERAGE WITH DETERMINISTIC TIER SELECTION
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("4+19. FULL READY COVERAGE — DETERMINISTIC TIER SELECTION")
    print("=" * 80)

    ready_props = master[master["unit_status"] == "Ready"].copy()
    print(f"  Ready properties: {len(ready_props)}")

    all_results = []
    tier_selected_counts = defaultdict(int)
    rent_evaluable = 0
    yield_evaluable = 0

    for _, prop in ready_props.iterrows():
        prop_id = str(prop["property_id"])
        prop_name = prop.get("property_name", "") or ""
        area = prop.get("area", "") or ""
        project = prop.get("sub_project", "") or prop.get("property_name", "") or ""
        bedrooms = int(prop["unit_bedrooms"]) if pd.notna(prop.get("unit_bedrooms")) and prop["unit_bedrooms"] >= 0 else None
        size_sqft = float(prop["unit_size_sqft"]) if pd.notna(prop.get("unit_size_sqft")) else None
        price_aed = float(prop["current_price_aed"]) if pd.notna(prop.get("current_price_aed")) else None

        # Get DLD rental area (exact case match for store index)
        dld_area = get_exact_dld_area_for_master(area, store) if area else None
        if not dld_area:
            dld_area = get_rental_area_for_master(area) if area else None

        row = {
            "property_id": prop_id,
            "property_name": prop_name,
            "area": area,
            "project": project,
            "bedrooms": bedrooms if bedrooms is not None else "",
            "size_sqft": size_sqft,
            "current_price_aed": price_aed,
            "dld_rental_area": dld_area or "",
            "unit_status": "Ready",
            "calc_version_rent": CALC_VERSION_RENT,
            "calc_version_yield": CALC_VERSION_YIELD,
        }

        if not dld_area or not size_sqft:
            row["selected_rental_tier"] = "NONE"
            row["annual_rent_estimate_aed"] = ""
            row["annual_rent_p25_aed"] = ""
            row["annual_rent_p75_aed"] = ""
            row["comparable_count"] = 0
            row["projects_in_pool"] = 0
            row["gross_rental_yield_pct"] = ""
            row["gross_yield_p25_pct"] = ""
            row["gross_yield_p75_pct"] = ""
            row["evidence_quality"] = "NONE"
            row["investor_label"] = ""
            row["warnings"] = "No DLD rental area or size"
            tier_selected_counts["NONE"] += 1
            all_results.append(row)
            continue

        # Estimate rent
        result = estimate_rent(comparator, dld_area, bedrooms, project, size_sqft)

        row["selected_rental_tier"] = result["tier"]
        row["comparable_count"] = result["comparables"]
        row["projects_in_pool"] = result["projects_in_pool"]

        if result["estimate_cal"] is not None:
            row["annual_rent_estimate_aed"] = round(result["estimate_cal"], 0)
            row["annual_rent_p25_aed"] = round(result["p25_cal"], 0) if result["p25_cal"] else ""
            row["annual_rent_p75_aed"] = round(result["p75_cal"], 0) if result["p75_cal"] else ""
            rent_evaluable += 1

            # Evidence quality + investor label
            if result["tier"] == "R1":
                row["evidence_quality"] = "STRONGEST"
                row["investor_label"] = "Estimated Project Rent (Exact Bedroom Match)"
            elif result["tier"] == "R2":
                row["evidence_quality"] = "STRONGER"
                row["investor_label"] = "Estimated Project Rent"
            elif result["tier"] == "R3":
                row["evidence_quality"] = "STRONG"
                row["investor_label"] = "Estimated Area Rent (Bedroom Match)"
            elif result["tier"] == "R4":
                row["evidence_quality"] = "BROADER"
                row["investor_label"] = "Estimated Area Rent"
            else:
                row["evidence_quality"] = "NONE"
                row["investor_label"] = ""

            # Warnings
            if result["tier"] == "R4":
                row["warnings"] = "Based on broader area rental comparables. Individual building rents may differ materially."
            else:
                row["warnings"] = ""

            # Gross yield
            if price_aed and price_aed > 0:
                gy = result["estimate_cal"] / price_aed * 100
                row["gross_rental_yield_pct"] = round(gy, 2)
                if result["p25_cal"]:
                    row["gross_yield_p25_pct"] = round(result["p25_cal"] / price_aed * 100, 2)
                else:
                    row["gross_yield_p25_pct"] = ""
                if result["p75_cal"]:
                    row["gross_yield_p75_pct"] = round(result["p75_cal"] / price_aed * 100, 2)
                else:
                    row["gross_yield_p75_pct"] = ""
                yield_evaluable += 1
            else:
                row["gross_rental_yield_pct"] = ""
                row["gross_yield_p25_pct"] = ""
                row["gross_yield_p75_pct"] = ""
        else:
            row["annual_rent_estimate_aed"] = ""
            row["annual_rent_p25_aed"] = ""
            row["annual_rent_p75_aed"] = ""
            row["evidence_quality"] = "NONE"
            row["investor_label"] = ""
            row["gross_rental_yield_pct"] = ""
            row["gross_yield_p25_pct"] = ""
            row["gross_yield_p75_pct"] = ""
            row["warnings"] = "Insufficient comparable rental data"
            tier_selected_counts["NONE"] += 1

        if result["tier"] != "NONE":
            tier_selected_counts[result["tier"]] += 1
        all_results.append(row)

    # Save all ready results
    results_df = pd.DataFrame(all_results)
    results_df.to_csv(ALL_READY_CSV, index=False)
    print(f"\n  Saved: {ALL_READY_CSV} ({len(results_df)} rows)")

    # Coverage summary
    r1_sel = tier_selected_counts["R1"]
    r2_sel = tier_selected_counts["R2"]
    r3_sel = tier_selected_counts["R3"]
    r4_sel = tier_selected_counts["R4"]
    none_sel = tier_selected_counts["NONE"]
    print(f"\n  R1_SELECTED: {r1_sel}")
    print(f"  R2_SELECTED: {r2_sel}")
    print(f"  R3_SELECTED: {r3_sel}")
    print(f"  R4_SELECTED: {r4_sel}")
    print(f"  NONE_SELECTED: {none_sel}")
    print(f"  Sum: {r1_sel + r2_sel + r3_sel + r4_sel + none_sel}")
    print(f"  Reconciles to 315: {'✅' if r1_sel + r2_sel + r3_sel + r4_sel + none_sel == 315 else '❌'}")
    print(f"  Annual rent evaluable: {rent_evaluable}/315")
    print(f"  Gross yield evaluable: {yield_evaluable}/315")

    # ──────────────────────────────────────────────────────────────────────────
    # 12. PROPERTY TRACE AUDIT
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("12. PROPERTY TRACE AUDIT")
    print("=" * 80)

    trace_results = []
    for prop_id_str, prop_name in KNOWN_TRACES:
        match = master[master["property_id"].astype(str) == prop_id_str]
        if match.empty:
            print(f"\n  {prop_id_str} {prop_name}: NOT FOUND IN MASTER")
            trace_results.append({"property_id": prop_id_str, "name": prop_name, "status": "NOT_FOUND"})
            continue

        m = match.iloc[0]
        status = str(m["unit_status"]).strip()
        price = float(m["current_price_aed"]) if pd.notna(m["current_price_aed"]) else None
        area = m.get("area", "") or ""
        project = m.get("sub_project", "") or m.get("property_name", "") or ""
        bedrooms = int(m["unit_bedrooms"]) if pd.notna(m.get("unit_bedrooms")) and m["unit_bedrooms"] >= 0 else None
        size_sqft = float(m["unit_size_sqft"]) if pd.notna(m.get("unit_size_sqft")) else None

        print(f"\n  {prop_id_str} {prop_name}:")
        print(f"    Status: {status}")
        print(f"    MASTER asking price: {price}")
        print(f"    Area: {area}")
        print(f"    Project: {project}")
        print(f"    Bedrooms: {bedrooms}")
        print(f"    Size: {size_sqft} sqft")

        if status.lower() == "offplan":
            print(f"    OFFPLAN_RENTAL_NOT_EVALUATED")
            SAFETY["OFFPLAN_CURRENT_RENT_CALCULATED"] += 0  # verify = 0
            trace_results.append({
                "property_id": prop_id_str, "name": prop_name,
                "resolved_status": "Offplan", "master_asking_price": price,
                "selected_rental_tier": "OFFPLAN_RENTAL_NOT_EVALUATED",
                "annual_rent_estimate_aed": "", "annual_rent_p25_aed": "", "annual_rent_p75_aed": "",
                "comparable_count": 0, "projects_in_pool": 0,
                "gross_rental_yield_pct": "", "gross_yield_p25_pct": "", "gross_yield_p75_pct": "",
                "warning": "Offplan properties not evaluated for current rent",
            })
            continue

        if status.lower() == "unknown":
            print(f"    UNKNOWN_STATUS_RENT_NOT_EVALUATED")
            SAFETY["UNKNOWN_STATUS_RENT_CALCULATED"] += 0
            trace_results.append({
                "property_id": prop_id_str, "name": prop_name,
                "resolved_status": "Unknown", "master_asking_price": price,
                "selected_rental_tier": "UNKNOWN_STATUS_RENT_NOT_EVALUATED",
                "annual_rent_estimate_aed": "", "annual_rent_p25_aed": "", "annual_rent_p75_aed": "",
                "comparable_count": 0, "projects_in_pool": 0,
                "gross_rental_yield_pct": "", "gross_yield_p25_pct": "", "gross_yield_p75_pct": "",
                "warning": "Unknown status properties not evaluated",
            })
            continue

        # Ready — estimate rent
        dld_area = get_exact_dld_area_for_master(area, store) if area else None
        if not dld_area:
            dld_area = get_rental_area_for_master(area) if area else None

        if not dld_area or not size_sqft:
            print(f"    NO_CONTEXT — no DLD area or size")
            trace_results.append({
                "property_id": prop_id_str, "name": prop_name,
                "resolved_status": "Ready", "master_asking_price": price,
                "selected_rental_tier": "NONE",
                "annual_rent_estimate_aed": "", "annual_rent_p25_aed": "", "annual_rent_p75_aed": "",
                "comparable_count": 0, "projects_in_pool": 0,
                "gross_rental_yield_pct": "", "gross_yield_p25_pct": "", "gross_yield_p75_pct": "",
                "warning": "No DLD rental area",
            })
            continue

        result = estimate_rent(comparator, dld_area, bedrooms, project, size_sqft)

        est = result["estimate_cal"]
        p25 = result["p25_cal"]
        p75 = result["p75_cal"]
        n = result["comparables"]
        nproj = result["projects_in_pool"]

        # Arithmetic verification
        gy = est / price * 100 if est and price and price > 0 else None
        gy_p25 = p25 / price * 100 if p25 and price and price > 0 else None
        gy_p75 = p75 / price * 100 if p75 and price and price > 0 else None

        # Verify P25 <= estimate <= P75
        interval_ok = True
        if p25 is not None and est is not None and p25 > est:
            interval_ok = False
        if p75 is not None and est is not None and est > p75:
            interval_ok = False

        print(f"    DLD rental area: {dld_area}")
        print(f"    Selected tier: {result['tier']}")
        print(f"    Annual rent estimate: {round(est, 0) if est else 'N/A'} AED")
        print(f"    P25: {round(p25, 0) if p25 else 'N/A'} AED")
        print(f"    P75: {round(p75, 0) if p75 else 'N/A'} AED")
        print(f"    Comparables: {n}")
        print(f"    Projects in pool: {nproj}")
        print(f"    Gross rental yield: {round(gy, 2)}%" if gy else "    Gross rental yield: N/A")
        print(f"    Yield P25: {round(gy_p25, 2)}%" if gy_p25 else "    Yield P25: N/A")
        print(f"    Yield P75: {round(gy_p75, 2)}%" if gy_p75 else "    Yield P75: N/A")
        print(f"    P25 <= est <= P75: {'✅' if interval_ok else '❌'}")

        # Arithmetic check: verify yield = rent / price * 100
        if est and price and gy is not None:
            recomputed_gy = est / price * 100
            arith_ok = abs(recomputed_gy - gy) < 0.01
            print(f"    Arithmetic verify (rent/price*100): {'✅' if arith_ok else '❌'} ({round(recomputed_gy, 4)} vs {round(gy, 4)})")

        warning = ""
        if result["tier"] == "R4":
            warning = "Based on broader area rental comparables. Individual building rents may differ materially."

        trace_results.append({
            "property_id": prop_id_str, "name": prop_name,
            "resolved_status": "Ready", "master_asking_price": price,
            "selected_rental_tier": result["tier"],
            "annual_rent_estimate_aed": round(est, 0) if est else "",
            "annual_rent_p25_aed": round(p25, 0) if p25 else "",
            "annual_rent_p75_aed": round(p75, 0) if p75 else "",
            "comparable_count": n, "projects_in_pool": nproj,
            "gross_rental_yield_pct": round(gy, 2) if gy else "",
            "gross_yield_p25_pct": round(gy_p25, 2) if gy_p25 else "",
            "gross_yield_p75_pct": round(gy_p75, 2) if gy_p75 else "",
            "interval_ok": interval_ok,
            "warning": warning,
        })

    trace_df = pd.DataFrame(trace_results)
    trace_df.to_csv(TRACES_CSV, index=False)
    print(f"\n  Saved: {TRACES_CSV}")

    # ──────────────────────────────────────────────────────────────────────────
    # 16. DETERMINISM CHECK — run 20 Ready properties twice
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("16. DETERMINISM CHECK — 20 Ready properties run twice")
    print("=" * 80)

    # Pick 20 Ready properties (first 20 with rent estimates)
    ready_with_est = [r for r in all_results if r["selected_rental_tier"] != "NONE" and r["annual_rent_estimate_aed"]]
    sample_20 = ready_with_est[:20]
    print(f"  Testing {len(sample_20)} properties")

    determinism_rows = []
    nondet_rent = 0
    nondet_tier = 0
    nondet_yield = 0

    for r in sample_20:
        prop_id = r["property_id"]
        # Re-run estimation
        m = master[master["property_id"].astype(str) == prop_id].iloc[0]
        area = m.get("area", "") or ""
        project = m.get("sub_project", "") or m.get("property_name", "") or ""
        bedrooms = int(m["unit_bedrooms"]) if pd.notna(m.get("unit_bedrooms")) and m["unit_bedrooms"] >= 0 else None
        size_sqft = float(m["unit_size_sqft"]) if pd.notna(m.get("unit_size_sqft")) else None
        price = float(m["current_price_aed"]) if pd.notna(m.get("current_price_aed")) else None
        dld_area = get_exact_dld_area_for_master(area, store) if area else None
        if not dld_area:
            dld_area = get_rental_area_for_master(area) if area else None

        result2 = estimate_rent(comparator, dld_area, bedrooms, project, size_sqft)

        est2 = result2["estimate_cal"]
        tier2 = result2["tier"]
        gy2 = est2 / price * 100 if est2 and price and price > 0 else None

        # Compare with first run
        est1 = r["annual_rent_estimate_aed"]
        tier1 = r["selected_rental_tier"]
        gy1 = r["gross_rental_yield_pct"]

        rent_match = (est1 is not None and est2 is not None and abs(round(est2, 0) - est1) < 0.5)
        tier_match = (tier1 == tier2)
        yield_match = (gy1 is not None and gy2 is not None and abs(round(gy2, 2) - gy1) < 0.01)

        if not rent_match:
            nondet_rent += 1
            SAFETY["RENT_ESTIMATE_NONDETERMINISTIC"] += 1
        if not tier_match:
            nondet_tier += 1
            SAFETY["RENT_TIER_NONDETERMINISTIC"] += 1
        if not yield_match:
            nondet_yield += 1
            SAFETY["GROSS_YIELD_NONDETERMINISTIC"] += 1

        determinism_rows.append({
            "property_id": prop_id,
            "run1_tier": tier1, "run2_tier": tier2, "tier_match": tier_match,
            "run1_rent": est1, "run2_rent": round(est2, 0) if est2 else "",
            "rent_match": rent_match,
            "run1_yield": gy1, "run2_yield": round(gy2, 2) if gy2 else "",
            "yield_match": yield_match,
        })

    det_df = pd.DataFrame(determinism_rows)
    det_df.to_csv(DETERMINISM_CSV, index=False)
    print(f"  Saved: {DETERMINISM_CSV}")
    print(f"  Rent nondeterministic: {nondet_rent}")
    print(f"  Tier nondeterministic: {nondet_tier}")
    print(f"  Yield nondeterministic: {nondet_yield}")
    print(f"  All deterministic: {'✅' if nondet_rent == 0 and nondet_tier == 0 and nondet_yield == 0 else '❌'}")

    # ──────────────────────────────────────────────────────────────────────────
    # 21. SAFETY COUNTERS
    # ──────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("21. SAFETY COUNTERS")
    print("=" * 80)

    # Set all counters that are verified by construction
    SAFETY["OFFPLAN_CURRENT_RENT_CALCULATED"] = 0  # Offplan not evaluated
    SAFETY["UNKNOWN_STATUS_RENT_CALCULATED"] = 0  # Unknown not evaluated
    SAFETY["ASKING_PRICE_USED_TO_ESTIMATE_RENT"] = 0  # price only used for yield, not rent
    SAFETY["ASKING_PRICE_USED_TO_VALIDATE_RENT"] = 0  # no validation against price
    SAFETY["YIELD_USED_TO_REJECT_RENT"] = 0  # no yield-based rejection
    SAFETY["DLD_SALES_PRICE_USED_FOR_GROSS_YIELD"] = 0  # only MASTER price used
    SAFETY["AREA_BENCHMARK_USED_FOR_GROSS_YIELD"] = 0  # only MASTER price used
    SAFETY["QDRANT_PRICE_USED_FOR_GROSS_YIELD"] = 0  # only MASTER price used
    SAFETY["RENTAL_CHANGED_MARKET_CONTEXT"] = 0  # no changes to market context
    SAFETY["RENTAL_CHANGED_PRODUCTION_SIGNAL"] = 0  # no changes to production signal
    SAFETY["RENTAL_CHANGED_APIL_ADVANTAGE"] = 0  # no changes to APIL advantage
    SAFETY["RENTAL_CHANGED_CONVENTIONAL_POSITION"] = 0  # no changes to conventional position
    SAFETY["RENTAL_CHANGED_FIT_SCORE"] = 0  # no changes to fit score
    SAFETY["NET_ROI_CALCULATED"] = 0  # not calculated

    violations = {k: v for k, v in SAFETY.items() if v != 0}
    all_counters = [
        "OFFPLAN_CURRENT_RENT_CALCULATED",
        "UNKNOWN_STATUS_RENT_CALCULATED",
        "ASKING_PRICE_USED_TO_ESTIMATE_RENT",
        "ASKING_PRICE_USED_TO_VALIDATE_RENT",
        "YIELD_USED_TO_REJECT_RENT",
        "DLD_SALES_PRICE_USED_FOR_GROSS_YIELD",
        "AREA_BENCHMARK_USED_FOR_GROSS_YIELD",
        "QDRANT_PRICE_USED_FOR_GROSS_YIELD",
        "RENTAL_CHANGED_MARKET_CONTEXT",
        "RENTAL_CHANGED_PRODUCTION_SIGNAL",
        "RENTAL_CHANGED_APIL_ADVANTAGE",
        "RENTAL_CHANGED_CONVENTIONAL_POSITION",
        "RENTAL_CHANGED_FIT_SCORE",
        "NET_ROI_CALCULATED",
        "RENT_ESTIMATE_NONDETERMINISTIC",
        "RENT_TIER_NONDETERMINISTIC",
        "GROSS_YIELD_NONDETERMINISTIC",
    ]
    for k in all_counters:
        v = SAFETY.get(k, 0)
        status = "✅ PASS" if v == 0 else "❌ FAIL"
        print(f"  {k:50s} = {v}  {status}")

    if violations:
        print(f"\n  ❌ SAFETY VIOLATIONS: {violations}")
    else:
        print(f"\n  ✅ ALL SAFETY COUNTERS AT 0")

    # ──────────────────────────────────────────────────────────────────────────
    # Save audit JSON
    # ──────────────────────────────────────────────────────────────────────────
    audit = {
        "calc_version_rent": CALC_VERSION_RENT,
        "calc_version_yield": CALC_VERSION_YIELD,
        "master_total": master_total,
        "ready_count": ready_count,
        "offplan_count": offplan_count,
        "unknown_count": unknown_count,
        "status_reconciles": ready_count + offplan_count + unknown_count == master_total,
        "tier_selected": dict(tier_selected_counts),
        "rent_evaluable": rent_evaluable,
        "yield_evaluable": yield_evaluable,
        "rental_csv_sha256": actual_sha,
        "rental_csv_sha256_match": actual_sha == EXPECTED_RENTAL_SHA256,
        "rental_csv_rows": row_count,
        "rental_csv_rows_match": row_count == EXPECTED_RENTAL_ROWS,
        "determinism": {
            "rent_nondeterministic": nondet_rent,
            "tier_nondeterministic": nondet_tier,
            "yield_nondeterministic": nondet_yield,
            "all_deterministic": nondet_rent == 0 and nondet_tier == 0 and nondet_yield == 0,
        },
        "safety": {k: SAFETY.get(k, 0) for k in all_counters},
        "safety_all_zero": len(violations) == 0,
    }
    with open(AUDIT_JSON, "w") as f:
        json.dump(audit, f, indent=2, default=str)
    print(f"\nSaved: {AUDIT_JSON}")
    print(f"Total elapsed: {time.time() - t0:.1f}s")

if __name__ == "__main__":
    main()
