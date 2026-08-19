"""
APIL Investment Engine API — Step 10 Production Version
========================================================
Serves locked Steps 1–9 data to the frontend.
Does NOT recalculate grades, benchmarks, or decisions.
Safety rules enforced at API layer.

New endpoints:
- POST /investors           → create investor profile
- GET  /investors/{id}      → retrieve profile
- GET  /opportunities       → default marketplace (no personalization)
- GET  /opportunities/me    → personalized marketplace (requires investor_id header)
- GET  /properties/{id}     → property detail (optionally personalized)
- POST /compare             → side-by-side comparison
- GET  /developers          → developer list
- GET  /developers/{name}   → developer detail
- GET  /ui                  → demo frontend
"""

import json
import os
import sys
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Add parent directory to path for qdrant client import
sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend_qdrant_client import enrich_property, health_check as qdrant_health

# Defensive DLD benchmark engine
from investor_api.dld_benchmark_engine import (
    compute_project_benchmark,
    resolve_canonical_status,
    validate_step5_benchmark,
    _canonical_status,
)

# Market Context Service — single runtime orchestration layer
from investor_api.fallback.market_context_service import (
    get_level2_context,
    get_area_context,
    select_market_context,
    AREA_CONTEXT_CONFIG_V1,
)


app = FastAPI(
    title="APIL Investment Engine API",
    description="Investor-facing API for property investment decisions. Objective signal locked. Investor fit is personalization-only.",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# LOAD LOCKED STEP 5 DATA
# ============================================================
DATA_PATH = os.environ.get("STEP5_PATH", "./data/STEP_5_RANKED_OPPORTUNITIES.jsonl")
PROFILE_PATH = os.environ.get("PROFILE_PATH", "./data/investor_profiles.json")

if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(
        f"STEP 5 data file not found at '{DATA_PATH}'. "
        f"Set the STEP5_PATH environment variable to the path of your data file. "
        f"Example: STEP5_PATH=/path/to/STEP_5_RANKED_OPPORTUNITIES.jsonl"
    )

records: List[Dict[str, Any]] = []
with open(DATA_PATH, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            records.append(json.loads(line))

# Build indices
by_id: Dict[str, Dict] = {}
by_decision: Dict[str, List[Dict]] = {}
by_developer: Dict[str, List[Dict]] = {}

for r in records:
    pid = r["property"]["id"]
    by_id[pid] = r
    dec = r["investment_decision"]["decision"]
    by_decision.setdefault(dec, []).append(r)
    dev = r["developer"]["name"]
    by_developer.setdefault(dev, []).append(r)

ranked_opportunities = [r for r in records if r["investment_decision"]["decision"] != "INSUFFICIENT_EVIDENCE"]
ranked_opportunities.sort(key=lambda r: r["_ranking"]["overall_rank"])

# Developer summary stats
developer_stats: Dict[str, Dict] = {}
for dev_name, props in by_developer.items():
    grades = [p["developer"]["grade"] for p in props]
    decisions = {}
    for p in props:
        d = p["investment_decision"]["decision"]
        decisions[d] = decisions.get(d, 0) + 1
    developer_stats[dev_name] = {
        "name": dev_name,
        "grade": props[0]["developer"]["grade"],
        "quality_tier": props[0]["developer"]["quality_tier"],
        "property_count": len(props),
        "grade_distribution": {g: grades.count(g) for g in set(grades)},
        "decision_distribution": decisions,
    }

print(f"API loaded: {len(records)} properties, {len(ranked_opportunities)} ranked opportunities, {len(developer_stats)} developers")

# ============================================================
# LOAD MASTER PROPERTIES DATASET (authoritative unit-level facts)
# ============================================================
MASTER_XLSX_PATH = os.environ.get("MASTER_XLSX_PATH", "/Users/apple/Desktop/Ai 3d view/MASTER_FINAL.xlsx")
master_by_id: Dict[str, Dict] = {}
try:
    import pandas as pd
    if os.path.exists(MASTER_XLSX_PATH):
        master_df = pd.read_excel(MASTER_XLSX_PATH)
        for _, row in master_df.iterrows():
            pid = str(int(row["property_id"])) if not pd.isna(row.get("property_id")) else ""
            if pid:
                master_by_id[pid] = row.to_dict()
        print(f"MASTER loaded: {len(master_by_id)} properties from {MASTER_XLSX_PATH}")
    else:
        print(f"MASTER file not found at {MASTER_XLSX_PATH} — falling back to STEP_5 + Qdrant only")
except Exception as e:
    print(f"MASTER load error: {e} — continuing without master dataset")
    master_by_id = {}

# ── Lazy cache for MASTER df used by Area fallback lookups ──
_FALLBACK_MASTER_DF_CACHE = None

def _get_fallback_master_df():
    global _FALLBACK_MASTER_DF_CACHE
    if _FALLBACK_MASTER_DF_CACHE is None:
        try:
            _FALLBACK_MASTER_DF_CACHE = pd.read_excel(MASTER_XLSX_PATH)
        except Exception:
            _FALLBACK_MASTER_DF_CACHE = None
    return _FALLBACK_MASTER_DF_CACHE


# ============================================================
# OVERLAY MASTER VALUES ONTO STEP_5 RECORDS
# ============================================================
import math

def _safe_overlay_float(val):
    if val is None or (isinstance(val, float) and val != val):
        return None
    try:
        f = float(val)
        if math.isinf(f) or math.isnan(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _safe_overlay_int(val):
    f = _safe_overlay_float(val)
    if f is None:
        return None
    return int(f)


def _safe_overlay_str(val) -> str:
    """Clean string values from pandas: treat 'nan', 'null', 'none' as empty."""
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "null", "none", ""):
        return ""
    return s


def _overlay_master_onto_step5(record: Dict) -> Dict:
    """
    Overlay MASTER unit-level values onto the STEP_5 property record.
    This makes MASTER the source of truth for investor matching without
    rewriting the data pipeline.
    """
    pid = str(record.get("property", {}).get("id", "")).strip()
    master = master_by_id.get(pid)
    if not master:
        record["_master_overlay"] = {"available": False}
        return record

    p = record["property"]

    # Unit-level values from MASTER (authoritative)
    m_beds = _safe_overlay_int(master.get("unit_bedrooms"))
    m_baths = _safe_overlay_int(master.get("unit_bathrooms"))
    m_size_sqft = _safe_overlay_float(master.get("unit_size_sqft"))
    m_size_sqm = _safe_overlay_float(master.get("unit_size_sqm"))
    m_price = _safe_overlay_float(master.get("current_price_aed"))
    m_status = _safe_overlay_str(master.get("unit_status"))
    m_type = _safe_overlay_str(master.get("property_type"))
    m_name = _safe_overlay_str(master.get("property_name"))
    m_area = _safe_overlay_str(master.get("area"))

    # Overlay onto STEP_5 property dict (only when MASTER has a value)
    if m_beds is not None:
        p["bedrooms"] = m_beds
    if m_baths is not None:
        p["bathrooms"] = m_baths
    if m_size_sqft is not None:
        p["size_sqft"] = round(m_size_sqft, 1)
        if m_size_sqm is not None:
            p["size_sqm"] = round(m_size_sqm, 1)
        else:
            p["size_sqm"] = round(m_size_sqft / 10.764, 1)
    if m_price is not None:
        p["current_price_aed"] = m_price
    if m_status:
        p["status"] = m_status
    if m_type:
        p["property_type"] = m_type
    if m_name:
        p["name"] = m_name
    if m_area:
        p["area"] = m_area

    # Preserve audit metadata for downstream use
    record["_master_overlay"] = {
        "available": True,
        "final_data_status": str(master.get("final_data_status", "")).strip() or "UNKNOWN",
        "bedroom_value_status": str(master.get("bedroom_value_status", "")).strip() or "UNKNOWN",
        "dld_evidence_status": str(master.get("dld_evidence_status", "")).strip() or "UNKNOWN",
        "price_validation_status": str(master.get("price_validation_status", "")).strip() or "UNKNOWN",
        "audit_classification": str(master.get("audit_classification", "")).strip() or "UNKNOWN",
    }
    return record


# Apply overlay to all loaded records
_overlayed_count = 0
for r in records:
    _overlay_master_onto_step5(r)
    if r.get("_master_overlay", {}).get("available"):
        _overlayed_count += 1

print(f"MASTER overlay applied to {_overlayed_count} / {len(records)} STEP_5 records")


def _sanitize_for_json(obj):
    """Recursively replace NaN, Inf, -Inf with None for JSON compliance."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj

# ============================================================
# INVESTOR PROFILE STORE
# ============================================================
investor_profiles: Dict[str, Dict] = {}

if os.path.exists(PROFILE_PATH):
    try:
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            investor_profiles = data.get("profiles", {})
        print(f"Loaded {len(investor_profiles)} investor profiles")
    except Exception:
        investor_profiles = {}

def save_profiles():
    os.makedirs(os.path.dirname(os.path.abspath(PROFILE_PATH)), exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump({"profiles": investor_profiles}, f, ensure_ascii=False, indent=2)

# ============================================================
# STEP 8/9 FIT SCORING (inline to avoid dependency)
# ============================================================
GRADE_ORDER = {"A+": 0, "A": 1, "A-": 2, "B+": 3, "B": 4, "B-": 5, "C+": 6, "C": 7, "C-": 8, "D": 9}
DECISION_ORDER = {"STRONG_OPPORTUNITY": 0, "OPPORTUNITY": 1, "WATCH": 2, "CAUTION": 3, "AVOID": 4, "INSUFFICIENT_EVIDENCE": 5}

def grade_rank(grade: str) -> int:
    return GRADE_ORDER.get(grade, 99)

def grade_floor_rank(floor: str) -> int:
    if floor == "ANY":
        return 99
    return grade_rank(floor)

class InvestorProfileModel:
    def __init__(self, raw: Dict):
        self.raw = raw
        self._derive()

    def _derive(self):
        raw = self.raw
        risk_map = {"CONSERVATIVE": "LOW", "MODERATE": "MEDIUM", "AGGRESSIVE": "HIGH"}
        self.preferred_risk_level = risk_map.get(raw.get("risk_tolerance"), "MEDIUM")
        horizon_map = {"LT_2_YEARS": (0, 2), "2_5_YEARS": (2, 5), "5_10_YEARS": (5, 10), "GT_10_YEARS": (10, 50)}
        self.preferred_horizon_years_min, self.preferred_horizon_years_max = horizon_map.get(raw.get("horizon"), (0, 50))
        self.budget_min = raw.get("budget_min_aed", 0)
        self.budget_max = raw.get("budget_max_aed", 999999999)
        dev_pref = raw.get("developer_preference") or "NO_PREFERENCE"
        dev_floor_map = {"NO_PREFERENCE": "ANY", "A_ONLY": "A", "A_B_PREFERRED": "B-", "ANY": "D"}
        self.preferred_developer_grade_floor = dev_floor_map.get(dev_pref, "ANY")
        obj = raw.get("investment_objective", "BALANCED")
        income_map = {"CAPITAL_APPRECIATION": "GROWTH", "RENTAL_INCOME": "INCOME", "BALANCED": "BALANCED", "SHORT_TERM_FLIP": "GROWTH"}
        self.income_vs_growth_priority = income_map.get(obj, "BALANCED")
        pt = raw.get("property_types", [])
        self.property_type_preferences = pt if pt else ["ANY"]
        # STEP 22: property_type and bedrooms are now EVALUABLE when Qdrant
        # enrichment provides CONFIRMED data. When Qdrant data is unavailable,
        # they are marked not_evaluated per-property by the scorer.
        self.evaluable_preferences = [
            "budget", "location",
            "risk_compatibility", "horizon_compatibility",
            "property_status",
            "property_type", "bedrooms",
        ]
        self.not_evaluated_preferences = []
        self.unknown_preferences = ["rental_yield"]

    def to_dict(self):
        return {
            "preferred_risk_level": self.preferred_risk_level,
            "preferred_horizon_years_min": self.preferred_horizon_years_min,
            "preferred_horizon_years_max": self.preferred_horizon_years_max,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "preferred_developer_grade_floor": self.preferred_developer_grade_floor,
            "income_vs_growth_priority": self.income_vs_growth_priority,
            "property_type_preferences": self.property_type_preferences,
            "evaluable_preferences": self.evaluable_preferences,
            "not_evaluated_preferences": self.not_evaluated_preferences,
            "unknown_preferences": self.unknown_preferences,
        }

class InvestorFitScorer:
    # STEP 22: Qdrant-enriched property_type and bedrooms now participate when
    # CONFIRMED Qdrant data is available. When unavailable, they are marked
    # not_evaluated and do not contribute weight.
    WEIGHTS = {
        "budget_fit": 30,
        "location_fit": 20,
        "status_fit": 20,
        "risk_compatibility": 20,
        "horizon_compatibility": 10,
        "property_type_fit": 10,
        "bedroom_fit": 10,
    }

    def __init__(self, profile: InvestorProfileModel):
        self.profile = profile

    def score_property(self, property_record: Dict, enrichment: Optional[Dict] = None) -> Dict:
        p = property_record["property"]
        dev = property_record["developer"]
        benchs = property_record["benchmarks"]
        dec = property_record["investment_decision"]
        matched, unmatched, unknown, not_evaluated, reasons, warnings, subscores = [], [], [], [], [], [], {}
        evaluated_dimensions = []
        not_evaluated_dimensions = []

        # Determine MASTER availability directly from master_by_id (same logic as _build_apil_attributes)
        pid = str(p.get("id", "")).strip()
        master = master_by_id.get(pid) if pid else None
        master_available = master is not None
        master_attrs = property_record.get("master_attributes", {}) or {}

        # ── Budget ── (EVALUABLE)
        price = p.get("current_price_aed")
        if price and price > 0:
            if self.profile.budget_min <= price <= self.profile.budget_max:
                subscores["budget_fit"] = 100; matched.append("budget")
                reasons.append(f"Price AED {price:,} is within budget")
            elif price < self.profile.budget_min:
                subscores["budget_fit"] = max(0, int((price / self.profile.budget_min) * 50))
                unmatched.append("budget")
                reasons.append(f"Price AED {price:,} is below minimum budget")
            else:
                overage = (price - self.profile.budget_max) / self.profile.budget_max
                subscores["budget_fit"] = max(0, int(100 - overage * 100))
                unmatched.append("budget")
                reasons.append(f"Price AED {price:,} exceeds maximum budget")
        else:
            subscores["budget_fit"] = 0; unmatched.append("budget")
            reasons.append("Property price unavailable")
        evaluated_dimensions.append("budget")

        # ── Property type ── (EVALUABLE)
        # Priority: MASTER attributes > Qdrant CONFIRMED > not_evaluated
        investor_types = self.profile.raw.get("property_types", [])
        investor_types_upper = [str(t).strip().upper() for t in investor_types]
        prop_type_raw = str(master.get("property_type") if master else (master_attrs.get("property_type") or p.get("property_type", ""))).strip()
        qdrant_attrs = enrichment.get("property_attributes", {}) if enrichment else {}
        qdrant_type_raw = str(qdrant_attrs.get("category", "")).strip() if enrichment else ""

        def _normalize_prop_type(raw: str) -> set:
            parts = [t.strip().upper() for t in raw.split(",")]
            normalized = set()
            for pt in parts:
                if pt in ("APARTMENT", "FLAT", "شقة"): normalized.add("APARTMENT")
                elif pt in ("VILLA", "HOUSE", "فيلا"): normalized.add("VILLA")
                elif pt in ("TOWNHOUSE", "TOWN HOUSE", "تاون هاوس"): normalized.add("TOWNHOUSE")
                elif pt in ("PENTHOUSE", "بنتهاوس"): normalized.add("PENTHOUSE")
                elif pt in ("DUPLEX", "دوبلكس"): normalized.add("DUPLEX")
                elif pt in ("STUDIO"): normalized.add("STUDIO")
                else: normalized.add(pt)
            return normalized

        type_evaluated = False
        has_master_type = master_available and prop_type_raw and prop_type_raw.lower() not in ("nan", "none", "null", "", "unknown")
        if has_master_type:
            prop_types_norm = _normalize_prop_type(prop_type_raw)
            if "ANY" in investor_types_upper or any(t in investor_types_upper for t in prop_types_norm):
                subscores["property_type_fit"] = 100; matched.append("property_type")
                reasons.append(f"Property type '{prop_type_raw}' matches your preference (MASTER)")
            else:
                subscores["property_type_fit"] = 0; unmatched.append("property_type")
                reasons.append(f"Property type '{prop_type_raw}' does not match your preference ({', '.join(investor_types)})")
            evaluated_dimensions.append("property_type")
            type_evaluated = True
        elif qdrant_type_raw and enrichment and enrichment.get("enrichment_status") == "CONFIRMED":
            qdrant_types_norm = _normalize_prop_type(qdrant_type_raw)
            if "ANY" in investor_types_upper or any(t in investor_types_upper for t in qdrant_types_norm):
                subscores["property_type_fit"] = 100; matched.append("property_type")
                reasons.append(f"Property type '{qdrant_type_raw}' matches your preference (Qdrant)")
            else:
                subscores["property_type_fit"] = 0; unmatched.append("property_type")
                reasons.append(f"Property type '{qdrant_type_raw}' does not match your preference ({', '.join(investor_types)})")
            evaluated_dimensions.append("property_type")
            type_evaluated = True
        else:
            not_evaluated.append("property_type")
            not_evaluated_dimensions.append("property_type")
            reasons.append("Property type not currently evaluated — no MASTER or confirmed Qdrant data")

        # ── Bedrooms ── (EVALUABLE)
        # Priority: MASTER overlay (exact unit value) > Qdrant CONFIRMED > not_evaluated
        # NEVER use project-level ranges as the property's bedroom count.
        investor_beds = self.profile.raw.get("bedrooms", [])
        investor_beds_upper = [str(b).strip().upper() for b in investor_beds]
        wants_any = "ANY" in investor_beds_upper
        wants_studio = "STUDIO" in investor_beds_upper
        wants_4plus = "4+" in investor_beds

        prop_beds = master.get("unit_bedrooms") if master else (master_attrs.get("bedrooms") if master_attrs else p.get("bedrooms"))
        beds_evaluated = False
        import math
        if prop_beds is not None and master_available and not (isinstance(prop_beds, float) and math.isnan(prop_beds)):
            prop_beds_val = int(prop_beds)
            if wants_any:
                subscores["bedroom_fit"] = 100; matched.append("bedrooms")
                reasons.append(f"{prop_beds_val}BR matches your preference (MASTER)")
            elif prop_beds_val == 0 and wants_studio:
                subscores["bedroom_fit"] = 100; matched.append("bedrooms")
                reasons.append("Studio (0BR) matches your preference (MASTER)")
            elif prop_beds_val >= 4 and wants_4plus:
                subscores["bedroom_fit"] = 100; matched.append("bedrooms")
                reasons.append(f"{prop_beds_val}BR matches your 4+ preference (MASTER)")
            elif str(prop_beds_val) in [str(b) for b in investor_beds]:
                subscores["bedroom_fit"] = 100; matched.append("bedrooms")
                reasons.append(f"{prop_beds_val}BR matches your preference (MASTER)")
            else:
                subscores["bedroom_fit"] = 0; unmatched.append("bedrooms")
                reasons.append(f"{prop_beds_val}BR does not match your preference ({', '.join(investor_beds)})")
            evaluated_dimensions.append("bedrooms")
            beds_evaluated = True
        elif enrichment and enrichment.get("enrichment_status") == "CONFIRMED":
            qdrant_beds_options = qdrant_attrs.get("bedrooms_options")
            if qdrant_beds_options is None:
                qdrant_beds_options = qdrant_attrs.get("bedrooms")
            if qdrant_beds_options is not None:
                if isinstance(qdrant_beds_options, list):
                    qdrant_beds_list = [int(b) for b in qdrant_beds_options if b is not None]
                else:
                    qdrant_beds_list = [int(qdrant_beds_options)]
                match = False
                matched_beds = []
                for qb in qdrant_beds_list:
                    if wants_any:
                        match = True; matched_beds.append(qb)
                    elif qb == 0 and wants_studio:
                        match = True; matched_beds.append(qb)
                    elif qb >= 4 and wants_4plus:
                        match = True; matched_beds.append(qb)
                    elif str(qb) in [str(b) for b in investor_beds]:
                        match = True; matched_beds.append(qb)
                beds_str = ", ".join(str(b) for b in sorted(qdrant_beds_list))
                if match:
                    subscores["bedroom_fit"] = 100; matched.append("bedrooms")
                    reasons.append(f"Bedroom option(s) [{beds_str}] include a match (Qdrant)")
                else:
                    subscores["bedroom_fit"] = 0; unmatched.append("bedrooms")
                    reasons.append(f"Bedroom option(s) [{beds_str}] do not match ({', '.join(investor_beds)})")
                evaluated_dimensions.append("bedrooms")
                beds_evaluated = True
        if not beds_evaluated:
            not_evaluated.append("bedrooms")
            not_evaluated_dimensions.append("bedrooms")
            reasons.append("Bedroom count not currently evaluated — no MASTER or confirmed Qdrant data")

        # ── Location ── (EVALUABLE)
        area = str(p.get("area", "")).strip()
        locs = self.profile.raw.get("locations", [])
        if "DUBAI_WIDE" in locs or not locs:
            subscores["location_fit"] = 100; matched.append("location")
            reasons.append("Dubai-wide location acceptable")
        elif any(loc.lower() in area.lower() or area.lower() in loc.lower() for loc in locs if loc):
            subscores["location_fit"] = 100; matched.append("location")
            reasons.append(f"Location '{area}' matches preferred areas")
        else:
            subscores["location_fit"] = 0; unmatched.append("location")
            reasons.append(f"Location '{area}' does not match preferred areas")
        evaluated_dimensions.append("location")

        # ── Status ── (EVALUABLE)
        # Hierarchy: MASTER unit_status > exact Qdrant unit_status > APIL benchmark classification
        status_pref = [str(s).strip().upper() for s in self.profile.raw.get("property_status", [])]
        if "EITHER" in status_pref:
            subscores["status_fit"] = 100; matched.append("property_status")
            reasons.append("Either off-plan or ready acceptable")
        else:
            # 1. Use MASTER status first (authoritative)
            master_status_raw = str(master.get("unit_status") if master else (master_attrs.get("status") or p.get("status", ""))).strip().upper() if master_available else ""
            has_master_status = master_available and master_status_raw and master_status_raw not in ("NAN", "NONE", "NULL", "", "UNKNOWN")

            if has_master_status:
                # Normalize MASTER status
                if master_status_raw in ("OFFPLAN", "OFF-PLAN", "OFF_PLAN", "OFF PLAN"):
                    canonical_master = "OFFPLAN"
                elif master_status_raw in ("READY", "READY_RESALE"):
                    canonical_master = "READY"
                else:
                    canonical_master = master_status_raw

                display_status = master_attrs.get("status", p.get("status")) if master_attrs else p.get("status")
                if canonical_master in status_pref:
                    subscores["status_fit"] = 100; matched.append("property_status")
                    reasons.append(f"Property status ({display_status}) matches your preference. Source: MASTER dataset (verified)")
                else:
                    subscores["status_fit"] = 0; unmatched.append("property_status")
                    reasons.append(f"Property status ({display_status}) does not match your preference ({', '.join(status_pref)}). Source: MASTER dataset (verified)")
            # 2. Fall back to Qdrant exact unit status only if MASTER missing
            elif enrichment and enrichment.get("enrichment_status") == "CONFIRMED":
                qdrant_status_raw = str(qdrant_attrs.get("unit_status", "")).strip()
                if not qdrant_status_raw:
                    qdrant_status_raw = str(qdrant_attrs.get("status", "")).strip()
                if qdrant_status_raw:
                    qdrant_statuses = set(s.strip().upper().replace(" ", "") for s in qdrant_status_raw.split(","))
                    canonical = set()
                    for qs in qdrant_statuses:
                        if qs in ("OFFPLAN", "OFF-PLAN", "OFF_PLAN"):
                            canonical.add("OFFPLAN")
                        elif qs in ("READY", "READY_RESALE"):
                            canonical.add("READY")
                    if canonical & set(status_pref):
                        matched_status = ", ".join(sorted(canonical & set(status_pref)))
                        subscores["status_fit"] = 100; matched.append("property_status")
                        reasons.append(f"Qdrant-confirmed status ({qdrant_status_raw}) includes '{matched_status}' matching your preference")
                    else:
                        subscores["status_fit"] = 0; unmatched.append("property_status")
                        reasons.append(f"Qdrant-confirmed status ({qdrant_status_raw}) does not match your preference ({', '.join(status_pref)})")
                else:
                    # Fall back to APIL benchmark classification
                    has_offplan = any(b["type"] == "OFFPLAN_RESALE" for b in benchs)
                    has_ready = any(b["type"] == "READY_RESALE" for b in benchs)
                    prop_status = "OFFPLAN" if has_offplan else ("READY" if has_ready else "UNKNOWN")
                    if prop_status in status_pref:
                        subscores["status_fit"] = 100; matched.append("property_status")
                        reasons.append(f"Property status '{prop_status}' matches preference")
                    elif prop_status == "UNKNOWN":
                        subscores["status_fit"] = 50; matched.append("property_status")
                        reasons.append("Property status unclear — neutral")
                    else:
                        subscores["status_fit"] = 0; unmatched.append("property_status")
                        reasons.append(f"Property status '{prop_status}' does not match preference")
            else:
                # Fall back to APIL benchmark classification when Qdrant not confirmed
                has_offplan = any(b["type"] == "OFFPLAN_RESALE" for b in benchs)
                has_ready = any(b["type"] == "READY_RESALE" for b in benchs)
                prop_status = "OFFPLAN" if has_offplan else ("READY" if has_ready else "UNKNOWN")
                if prop_status in status_pref:
                    subscores["status_fit"] = 100; matched.append("property_status")
                    reasons.append(f"Property status '{prop_status}' matches preference")
                elif prop_status == "UNKNOWN":
                    subscores["status_fit"] = 50; matched.append("property_status")
                    reasons.append("Property status unclear — neutral")
                else:
                    subscores["status_fit"] = 0; unmatched.append("property_status")
                    reasons.append(f"Property status '{prop_status}' does not match preference")
        evaluated_dimensions.append("property_status")

        # ── Risk compatibility ── (EVALUABLE)
        risk = self.profile.preferred_risk_level
        conf = dec.get("confidence", "NONE")
        dec_val = dec.get("decision", "")
        if risk == "LOW":
            if conf == "HIGH" and dec_val in ("STRONG_OPPORTUNITY", "OPPORTUNITY"):
                subscores["risk_compatibility"] = 100; matched.append("risk_compatibility")
                reasons.append("HIGH confidence + positive decision matches conservative preference")
            elif conf == "HIGH":
                subscores["risk_compatibility"] = 70; matched.append("risk_compatibility")
                reasons.append("HIGH confidence acceptable for conservative investor")
            elif conf == "MEDIUM":
                subscores["risk_compatibility"] = 40; unmatched.append("risk_compatibility")
                reasons.append("MEDIUM confidence below conservative preference")
            else:
                subscores["risk_compatibility"] = 0; unmatched.append("risk_compatibility")
                reasons.append("LOW/NO confidence does not match conservative preference")
        elif risk == "MEDIUM":
            if conf in ("HIGH", "MEDIUM"):
                subscores["risk_compatibility"] = 100; matched.append("risk_compatibility")
                reasons.append(f"{conf} confidence matches moderate risk tolerance")
            else:
                subscores["risk_compatibility"] = 30; unmatched.append("risk_compatibility")
                reasons.append("LOW confidence below moderate risk tolerance")
        else:
            subscores["risk_compatibility"] = 100; matched.append("risk_compatibility")
            reasons.append("Aggressive risk tolerance accepts all confidence levels")
        evaluated_dimensions.append("risk_compatibility")

        # ── Horizon compatibility ── (EVALUABLE)
        horizon = self.profile.raw.get("horizon", "5_10_YEARS")
        has_offplan = any(b["type"] == "OFFPLAN_RESALE" for b in benchs)
        has_ready = any(b["type"] == "READY_RESALE" for b in benchs)
        if horizon in ("LT_2_YEARS", "2_5_YEARS"):
            if has_ready:
                subscores["horizon_compatibility"] = 100; matched.append("horizon_compatibility")
                reasons.append("Ready property matches short-term horizon")
            elif has_offplan:
                subscores["horizon_compatibility"] = 40; unmatched.append("horizon_compatibility")
                reasons.append("Off-plan property may not suit short-term horizon")
            else:
                subscores["horizon_compatibility"] = 50; matched.append("horizon_compatibility")
                reasons.append("Property status unclear for horizon compatibility")
        else:
            subscores["horizon_compatibility"] = 100; matched.append("horizon_compatibility")
            reasons.append("Long-term horizon compatible with both statuses")
        evaluated_dimensions.append("horizon_compatibility")

        # ── Unknown preferences ── (no property data available)
        for up in self.profile.unknown_preferences:
            unknown.append(up)
            reasons.append(f"Preference '{up}' cannot be evaluated from available data — marked as UNKNOWN")

        # ── Score calculation ──
        # Only evaluable dimensions contribute to the weighted score.
        total_weight = 0; weighted_sum = 0
        for key, weight in self.WEIGHTS.items():
            if key in subscores:
                total_weight += weight
                weighted_sum += subscores[key] * weight
        raw_score = weighted_sum / total_weight if total_weight > 0 else 0
        score = round(raw_score)

        if score >= 90: tier = "EXCELLENT_FIT"
        elif score >= 75: tier = "STRONG_FIT"
        elif score >= 60: tier = "MODERATE_FIT"
        elif score >= 40: tier = "WEAK_FIT"
        else: tier = "POOR_FIT"

        if dec_val in ("AVOID", "CAUTION") and score >= 75:
            warnings.append("WARNING: Strong investor fit but objective investment signal is negative. Proceed with caution.")
        if dec_val == "INSUFFICIENT_EVIDENCE" and score >= 60:
            warnings.append("WARNING: Moderate investor fit but insufficient objective evidence to support investment decision.")

        return {
            "score": score, "tier": tier, "subscores": subscores,
            "matched_preferences": matched, "unmatched_preferences": unmatched,
            "unknown_preferences": unknown, "not_evaluated_preferences": not_evaluated,
            "evaluated_dimensions": evaluated_dimensions,
            "not_evaluated_dimensions": not_evaluated_dimensions,
            "reasons": reasons, "warnings": warnings,
        }


class InvestorEligibilityChecker:
    """Hard eligibility filter — remove properties that fail investor's stated requirements."""

    # Normalization maps
    TYPE_NORMALIZED = {
        "APARTMENT": {"apartment", "flat", "شقة"},
        "VILLA": {"villa", "house", "فيلا"},
        "TOWNHOUSE": {"townhouse", "town house", "تاون هاوس"},
        "PENTHOUSE": {"penthouse", "بنتهاوس"},
        "DUPLEX": {"duplex", "دوبلكس"},
        "STUDIO": {"studio"},
    }

    def __init__(self, profile: InvestorProfileModel):
        self.profile = profile

    @staticmethod
    def _normalize_type(raw: str) -> set:
        """Normalize a comma-separated Qdrant category string into canonical type set."""
        result = set()
        for part in raw.split(","):
            part = part.strip().lower()
            for canonical, variants in InvestorEligibilityChecker.TYPE_NORMALIZED.items():
                if part in variants:
                    result.add(canonical)
                    break
            else:
                result.add(part.upper())
        return result

    @staticmethod
    def _normalize_investor_types(types: List[str]) -> set:
        """Normalize investor property type preferences."""
        return set(str(t).strip().upper() for t in types)

    @staticmethod
    def _normalize_investor_beds(beds: List[str]) -> tuple:
        """Return (exact_beds: set[int], wants_any: bool, wants_studio: bool, wants_4plus: bool)"""
        exact = set()
        wants_any = False
        wants_studio = False
        wants_4plus = False
        for b in beds:
            b = str(b).strip().upper()
            if b == "ANY":
                wants_any = True
            elif b == "STUDIO":
                wants_studio = True
            elif b == "4+":
                wants_4plus = True
            else:
                try:
                    exact.add(int(b))
                except ValueError:
                    pass
        return exact, wants_any, wants_studio, wants_4plus

    def check(self, property_record: Dict, enrichment: Optional[Dict] = None) -> Dict:
        """
        Returns eligibility result dict.
        MASTER unit-level values are authoritative.
        Qdrant is only used when MASTER has no value.
        Project-level aggregates are NEVER used as unit-level values.
        """
        p = property_record["property"]
        benchs = property_record["benchmarks"]
        reasons = []
        failed = []
        not_evaluated = []
        checks = {}
        master_available = property_record.get("_master_overlay", {}).get("available", False)

        # ── Budget ── (MASTER current_price_aed via overlay)
        price = p.get("current_price_aed")
        budget_min = self.profile.budget_min
        budget_max = self.profile.budget_max
        if price is not None and price > 0:
            if budget_min <= price <= budget_max:
                checks["budget"] = {"pass": True, "reason": f"AED {price:,.0f} within budget (AED {budget_min:,.0f}–{budget_max:,.0f})"}
                reasons.append("✓ Within budget")
            else:
                checks["budget"] = {"pass": False, "reason": f"AED {price:,.0f} outside budget (AED {budget_min:,.0f}–{budget_max:,.0f})"}
                failed.append("budget")
                reasons.append("✗ Outside budget")
        else:
            checks["budget"] = {"pass": False, "reason": "Property price unavailable"}
            failed.append("budget")
            reasons.append("✗ Price unavailable")

        # ── Location ── (MASTER area via overlay)
        area = str(p.get("area", "")).strip()
        locs = self.profile.raw.get("locations", [])
        locs_upper = [str(loc).strip().upper() for loc in locs if loc]
        if "DUBAI_WIDE" in locs_upper or not locs_upper:
            checks["location"] = {"pass": True, "reason": "Dubai-wide location acceptable"}
            reasons.append("✓ Dubai-wide")
        elif area and any(loc in area.upper() or area.upper() in loc for loc in locs_upper):
            checks["location"] = {"pass": True, "reason": f"{area} matches preferred areas"}
            reasons.append(f"✓ {area}")
        else:
            checks["location"] = {"pass": False, "reason": f"{area or 'Unknown area'} does not match preferred areas ({', '.join(locs)})"}
            failed.append("location")
            reasons.append("✗ Location mismatch")

        # ── Property Status ── (MASTER unit_status is authoritative)
        status_prefs = [str(s).strip().upper() for s in self.profile.raw.get("property_status", [])]
        if "EITHER" in status_prefs:
            checks["property_status"] = {"pass": True, "reason": "Either ready or off-plan acceptable"}
            reasons.append("✓ Either status OK")
        else:
            # 1. Use MASTER status first (overlayed onto p["status"])
            master_status_raw = str(p.get("status", "")).strip().upper() if master_available else ""
            has_master_status = master_available and master_status_raw and master_status_raw not in ("NAN", "NONE", "NULL", "", "UNKNOWN")

            if has_master_status:
                # Normalize MASTER status
                if master_status_raw in ("OFFPLAN", "OFF-PLAN", "OFF_PLAN", "OFF PLAN"):
                    canonical_master = "OFFPLAN"
                elif master_status_raw in ("READY", "READY_RESALE"):
                    canonical_master = "READY"
                else:
                    canonical_master = master_status_raw

                requested_ready = "READY" in status_prefs
                requested_offplan = "OFFPLAN" in status_prefs
                if requested_ready and canonical_master == "READY":
                    checks["property_status"] = {"pass": True, "reason": f"Ready status confirmed by MASTER. Source: master:unit_status"}
                    reasons.append("✓ Ready (MASTER)")
                elif requested_offplan and canonical_master == "OFFPLAN":
                    checks["property_status"] = {"pass": True, "reason": f"Off-plan status confirmed by MASTER. Source: master:unit_status"}
                    reasons.append("✓ Off-plan (MASTER)")
                else:
                    checks["property_status"] = {"pass": False, "reason": f"MASTER status ({master_status_raw}) does not include {', '.join(status_prefs)}"}
                    failed.append("property_status")
                    reasons.append("✗ Status mismatch (MASTER)")
            else:
                # 2. Fall back to Qdrant only when MASTER status is truly missing
                qdrant_status_raw = str(enrichment.get("property_attributes", {}).get("status", "")).strip() if enrichment else ""
                if qdrant_status_raw and enrichment and enrichment.get("enrichment_status") == "CONFIRMED":
                    qdrant_statuses = set(s.strip().upper().replace(" ", "") for s in qdrant_status_raw.split(","))
                    canonical = set()
                    for qs in qdrant_statuses:
                        if qs in ("OFFPLAN", "OFF-PLAN", "OFF_PLAN"):
                            canonical.add("OFFPLAN")
                        elif qs in ("READY", "READY_RESALE"):
                            canonical.add("READY")
                    requested_ready = "READY" in status_prefs
                    requested_offplan = "OFFPLAN" in status_prefs
                    if requested_ready and "READY" in canonical:
                        checks["property_status"] = {"pass": True, "reason": f"Qdrant-confirmed Ready status. Source: {enrichment.get('provenance', {}).get('status', 'qdrant:status')}"}
                        reasons.append("✓ Ready (Qdrant)")
                    elif requested_offplan and "OFFPLAN" in canonical:
                        checks["property_status"] = {"pass": True, "reason": f"Qdrant-confirmed Off-plan status. Source: {enrichment.get('provenance', {}).get('status', 'qdrant:status')}"}
                        reasons.append("✓ Off-plan (Qdrant)")
                    else:
                        checks["property_status"] = {"pass": False, "reason": f"Qdrant status ({qdrant_status_raw}) does not include {', '.join(status_prefs)}"}
                        failed.append("property_status")
                        reasons.append("✗ Status mismatch (Qdrant)")
                else:
                    # 3. Final fallback to APIL benchmark classification
                    has_offplan = any(b["type"] == "OFFPLAN_RESALE" for b in benchs)
                    has_ready = any(b["type"] == "READY_RESALE" for b in benchs)
                    if not has_offplan and not has_ready:
                        checks["property_status"] = {"pass": False, "reason": "Property status unknown"}
                        failed.append("property_status")
                        reasons.append("✗ Status unknown")
                    else:
                        requested_ready = "READY" in status_prefs
                        requested_offplan = "OFFPLAN" in status_prefs
                        if requested_ready and has_ready:
                            checks["property_status"] = {"pass": True, "reason": "Ready status confirmed"}
                            reasons.append("✓ Ready")
                        elif requested_offplan and has_offplan:
                            checks["property_status"] = {"pass": True, "reason": "Off-plan status confirmed"}
                            reasons.append("✓ Off-plan")
                        else:
                            status_str = "Ready" if has_ready else ("Off-plan" if has_offplan else "Unknown")
                            checks["property_status"] = {"pass": False, "reason": f"Property is {status_str} — investor wants {', '.join(status_prefs)}"}
                            failed.append("property_status")
                            reasons.append("✗ Status mismatch")

        # ── Property Type ──
        # MASTER property_type is authoritative when populated.
        # When missing, mark as NOT_EVALUATED — do NOT hard-reject.
        investor_types = self.profile.raw.get("property_types", [])
        inv_types_norm = self._normalize_investor_types(investor_types)
        if "ANY" in inv_types_norm:
            checks["property_type"] = {"pass": True, "reason": "Any property type acceptable"}
            reasons.append("✓ Any type OK")
        else:
            prop_type_raw = str(p.get("property_type", "")).strip().lower()
            has_master_type = master_available and prop_type_raw and prop_type_raw not in ("nan", "none", "null", "")
            if has_master_type:
                prop_types_norm = self._normalize_type(prop_type_raw)
                if prop_types_norm & inv_types_norm:
                    checks["property_type"] = {"pass": True, "reason": f"Type '{prop_type_raw}' matches preference (MASTER)"}
                    reasons.append(f"✓ {prop_type_raw} (MASTER)")
                else:
                    checks["property_type"] = {"pass": False, "reason": f"Type '{prop_type_raw}' does not match preference ({', '.join(investor_types)})"}
                    failed.append("property_type")
                    reasons.append("✗ Type mismatch")
            else:
                # No MASTER property_type — mark as NOT_EVALUATED.
                # Do NOT fabricate or infer. Qdrant project aggregates must NEVER be used as unit values.
                checks["property_type"] = {"pass": None, "reason": "Property type data unavailable from MASTER — not evaluated"}
                not_evaluated.append("property_type")
                reasons.append("⊘ Property type not evaluated (MASTER missing)")

        # ── Bedrooms ──
        # MASTER unit_bedrooms is authoritative.
        # NEVER use Qdrant project-level bedrooms_options as unit-level bedroom count.
        investor_beds = self.profile.raw.get("bedrooms", [])
        exact, wants_any, wants_studio, wants_4plus = self._normalize_investor_beds(investor_beds)
        if wants_any:
            checks["bedrooms"] = {"pass": True, "reason": "Any bedroom count acceptable"}
            reasons.append("✓ Any bedrooms OK")
        else:
            prop_beds = p.get("bedrooms")
            if prop_beds is not None and master_available:
                prop_beds_val = int(prop_beds)
                if wants_studio and prop_beds_val == 0:
                    checks["bedrooms"] = {"pass": True, "reason": "Studio (0BR) matches preference (MASTER)"}
                    reasons.append("✓ Studio (MASTER)")
                elif wants_4plus and prop_beds_val >= 4:
                    checks["bedrooms"] = {"pass": True, "reason": f"{prop_beds_val}BR matches 4+ preference (MASTER)"}
                    reasons.append(f"✓ {prop_beds_val}BR (MASTER)")
                elif prop_beds_val in exact:
                    checks["bedrooms"] = {"pass": True, "reason": f"{prop_beds_val}BR matches preference (MASTER)"}
                    reasons.append(f"✓ {prop_beds_val}BR (MASTER)")
                else:
                    checks["bedrooms"] = {"pass": False, "reason": f"{prop_beds_val}BR does not match preference ({', '.join(investor_beds)})"}
                    failed.append("bedrooms")
                    reasons.append("✗ Bedroom mismatch")
            else:
                # MASTER bedroom data missing — mark as NOT_EVALUATED.
                # Do NOT fall back to Qdrant project-level aggregates.
                checks["bedrooms"] = {"pass": None, "reason": "Bedroom data unavailable from MASTER — not evaluated"}
                not_evaluated.append("bedrooms")
                reasons.append("⊘ Bedrooms not evaluated (MASTER missing)")

        eligible = len(failed) == 0
        return {
            "eligible": eligible,
            "eligibility_reasons": reasons,
            "failed_preferences": failed,
            "not_evaluated_preferences": not_evaluated,
            "checks": checks,
        }


def build_dimension_explanations(fit: Dict, property_record: Dict, profile: InvestorProfileModel, enrichment: Optional[Dict] = None, canonical_decision: Optional[Dict] = None) -> List[Dict]:
    """Build human-readable per-dimension explanations for investor fit."""
    p = property_record["property"]
    dev = property_record["developer"]
    benchs = property_record["benchmarks"]
    # Use canonical decision if provided (post-recomputation), else fall back to STEP_5 stale decision
    if canonical_decision:
        dec = canonical_decision
    else:
        dec = property_record["investment_decision"]
    explanations = []
    subscores = fit.get("subscores", {})
    # Determine MASTER availability directly from master_by_id (same logic as _build_apil_attributes)
    pid = str(p.get("id", "")).strip()
    master = master_by_id.get(pid) if pid else None
    master_available = master is not None
    master_attrs = property_record.get("master_attributes", {}) or {}

    # Helper to add explanation
    def add_exp(key: str, label: str, status: str, score: int, investor_val: str, property_val: str, explanation: str, source: str = ""):
        # Map dimension keys to WEIGHTS dict keys
        weight_key_map = {
            "budget": "budget_fit",
            "location": "location_fit",
            "property_status": "status_fit",
            "risk_compatibility": "risk_compatibility",
            "horizon_compatibility": "horizon_compatibility",
            "property_type": "property_type_fit",
            "bedrooms": "bedroom_fit",
        }
        weight = InvestorFitScorer.WEIGHTS.get(weight_key_map.get(key, key), 0)
        explanations.append({
            "dimension_key": key,
            "dimension_label": label,
            "status": status,
            "score": score,
            "weight": weight,
            "investor_value": investor_val,
            "property_value": property_val,
            "explanation": explanation,
            "source": _clean_source_label(source),
        })

    def _clean_source_label(raw: str) -> str:
        """Map internal provenance strings to investor-facing source labels."""
        if raw.startswith("master:"):
            return "MASTER dataset (verified)"
        if raw.startswith("qdrant:"):
            if "exact unit" in raw or "exact_unit" in raw:
                return "Qdrant exact unit"
            return "Qdrant project metadata"
        if raw.startswith("apil:"):
            return "APIL property record"
        if raw.startswith("canonical:"):
            return "Canonical resolution"
        return raw

    # Budget — price is from MASTER when available, else APIL property record
    price = p.get("current_price_aed")
    budget_range = f"AED {profile.budget_min:,}–{profile.budget_max:,}"
    if price:
        price_str = f"AED {price:,}"
    else:
        price_str = "Unknown"
    budget_source = "MASTER dataset (verified)" if (master_available and price) else "APIL property record"
    budget_score = subscores.get("budget_fit", 0)
    if budget_score >= 100:
        add_exp("budget", "Budget", "matched", budget_score, budget_range, price_str,
                f"The property price ({price_str}) is within your preferred budget range ({budget_range}).", budget_source)
    elif price and price < profile.budget_min:
        add_exp("budget", "Budget", "unmatched", budget_score, budget_range, price_str,
                f"The property price ({price_str}) is below your minimum budget ({budget_range}).", budget_source)
    else:
        add_exp("budget", "Budget", "unmatched", budget_score, budget_range, price_str,
                f"The property price ({price_str}) is outside your preferred budget range ({budget_range}).", budget_source)

    # Location — area is from MASTER when available, else APIL property record
    area = str(p.get("area", "")).strip()
    locs = profile.raw.get("locations", [])
    loc_score = subscores.get("location_fit", 0)
    area_source = "MASTER dataset (verified)" if (master_available and area) else "APIL property record"
    if "DUBAI_WIDE" in locs or not locs:
        add_exp("location", "Location", "matched", loc_score, "Dubai-wide" if not locs else "Any", area,
                f"'{area}' is acceptable under your Dubai-wide location preference.", area_source)
    elif loc_score >= 100:
        add_exp("location", "Location", "matched", loc_score, ", ".join(locs), area,
                f"'{area}' matches your preferred location(s): {', '.join(locs)}.", area_source)
    else:
        add_exp("location", "Location", "unmatched", loc_score, ", ".join(locs), area,
                f"'{area}' does not match your preferred location(s): {', '.join(locs)}.", area_source)

    # Property status — Hierarchy: MASTER unit_status > exact Qdrant unit_status > APIL benchmark
    status_pref = profile.raw.get("property_status", [])
    master_status = str(master.get("unit_status") if master else (master_attrs.get("status") or p.get("status", ""))).strip() if master_available else ""
    if master_status and master_status.lower() not in ("nan", "none", "null", "unknown", ""):
        prop_status = master_status
        status_source = "MASTER dataset (verified)"
    else:
        qdrant_status_raw = str(enrichment.get("property_attributes", {}).get("unit_status", "")).strip() if enrichment else ""
        if not qdrant_status_raw:
            qdrant_status_raw = str(enrichment.get("property_attributes", {}).get("status", "")).strip() if enrichment else ""
        if qdrant_status_raw and enrichment and enrichment.get("enrichment_status") == "CONFIRMED":
            prop_status = qdrant_status_raw
            status_source = "Qdrant exact unit" if (enrichment.get("provenance", {}).get("unit_status")) else "Qdrant project metadata"
        else:
            has_offplan = any(b["type"] == "OFFPLAN_RESALE" for b in benchs)
            has_ready = any(b["type"] == "READY_RESALE" for b in benchs)
            prop_status = "Off-plan" if has_offplan else ("Ready" if has_ready else "Unknown")
            status_source = "APIL benchmark classification"
    status_score = subscores.get("status_fit", 0)
    if "EITHER" in status_pref:
        add_exp("property_status", "Property Status", "matched", status_score, "Either", prop_status,
                f"Property status ({prop_status}) is acceptable — you selected 'Either'.", status_source)
    elif status_score >= 100:
        add_exp("property_status", "Property Status", "matched", status_score, ", ".join(status_pref), prop_status,
                f"Property status ({prop_status}) matches your preference.", status_source)
    else:
        add_exp("property_status", "Property Status", "unmatched", status_score, ", ".join(status_pref), prop_status,
                f"Property status ({prop_status}) does not match your preference.", status_source)

    # Risk compatibility
    risk = profile.preferred_risk_level
    conf = dec.get("confidence", "NONE")
    dec_val = dec.get("decision", "")
    risk_score = subscores.get("risk_compatibility", 0)
    risk_labels = {"LOW": "Conservative", "MEDIUM": "Moderate", "HIGH": "Aggressive"}
    if risk_score >= 100:
        add_exp("risk_compatibility", "Risk Compatibility", "matched", risk_score, risk_labels.get(risk, risk), f"{conf} confidence / {dec_val}",
                f"The property's evidence confidence ({conf}) and decision ({dec_val.replace('_', ' ')}) align with your {risk_labels.get(risk, risk).lower()} risk preference.")
    elif risk_score >= 50:
        add_exp("risk_compatibility", "Risk Compatibility", "matched", risk_score, risk_labels.get(risk, risk), f"{conf} confidence / {dec_val}",
                f"The property's evidence confidence ({conf}) partially aligns with your {risk_labels.get(risk, risk).lower()} risk preference.")
    else:
        add_exp("risk_compatibility", "Risk Compatibility", "unmatched", risk_score, risk_labels.get(risk, risk), f"{conf} confidence / {dec_val}",
                f"The property's evidence confidence ({conf}) and decision ({dec_val.replace('_', ' ')}) do not align well with your {risk_labels.get(risk, risk).lower()} risk preference.")

    # Horizon compatibility
    horizon_raw = profile.raw.get("horizon", "5_10_YEARS")
    horizon_labels = {"LT_2_YEARS": "<2 years", "2_5_YEARS": "2–5 years", "5_10_YEARS": "5–10 years", "GT_10_YEARS": "10+ years"}
    horizon_score = subscores.get("horizon_compatibility", 0)
    if horizon_score >= 100:
        add_exp("horizon_compatibility", "Investment Horizon", "matched", horizon_score, horizon_labels.get(horizon_raw, horizon_raw), prop_status,
                f"The property's status ({prop_status}) is compatible with your {horizon_labels.get(horizon_raw, horizon_raw)} investment horizon.")
    elif horizon_score >= 40:
        add_exp("horizon_compatibility", "Investment Horizon", "matched", horizon_score, horizon_labels.get(horizon_raw, horizon_raw), prop_status,
                f"The property's status ({prop_status}) is partially compatible with your {horizon_labels.get(horizon_raw, horizon_raw)} investment horizon.")
    else:
        add_exp("horizon_compatibility", "Investment Horizon", "unmatched", horizon_score, horizon_labels.get(horizon_raw, horizon_raw), prop_status,
                f"The property's status ({prop_status}) may not suit your {horizon_labels.get(horizon_raw, horizon_raw)} investment horizon.")

    # Property type — Hierarchy: MASTER property_type > Qdrant category > APIL record
    pt_score = subscores.get("property_type_fit")
    if pt_score is not None:
        investor_types = profile.raw.get("property_types", [])
        master_type = str(master.get("property_type") if master else (master_attrs.get("property_type") or p.get("property_type", ""))).strip() if master_available else ""
        if master_type and master_type.lower() not in ("nan", "none", "null", "unknown", ""):
            prop_type = master_type
            pt_source = "MASTER dataset (verified)"
        else:
            qdrant_attrs = enrichment.get("property_attributes", {}) if enrichment else {}
            prop_type = str(qdrant_attrs.get("category", "")).strip()
            pt_source = "Qdrant exact unit" if (enrichment and enrichment.get("enrichment_status") == "CONFIRMED" and "category" in enrichment.get("provenance", {})) else "APIL property record"
        if pt_score >= 100:
            add_exp("property_type", "Property Type", "matched", pt_score, ", ".join(investor_types), prop_type or "Confirmed",
                    f"Property type '{prop_type}' matches your preference ({', '.join(investor_types)}).", pt_source)
        else:
            add_exp("property_type", "Property Type", "unmatched", pt_score, ", ".join(investor_types), prop_type or "Confirmed",
                    f"Property type '{prop_type}' does not match your preference ({', '.join(investor_types)}).", pt_source)

    # Bedrooms — Hierarchy: MASTER unit_bedrooms > exact Qdrant unit_bedrooms > Qdrant project options
    bed_score = subscores.get("bedroom_fit")
    if bed_score is not None:
        investor_beds = profile.raw.get("bedrooms", [])
        master_beds = master.get("unit_bedrooms") if master else (master_attrs.get("bedrooms") if master_attrs else p.get("bedrooms"))
        has_master_beds = master_available and master_beds is not None and not (isinstance(master_beds, float) and math.isnan(master_beds))

        if has_master_beds:
            bed_int = int(master_beds) if isinstance(master_beds, float) and master_beds == int(master_beds) else master_beds
            bed_label = f"{bed_int} BR" if bed_int != 0 else "Studio"
            bed_source = "MASTER dataset (verified)"
            if bed_score >= 100:
                add_exp("bedrooms", "Bedrooms", "matched", bed_score, ", ".join(investor_beds), bed_label,
                        f"{bed_label} matches your preference ({', '.join(investor_beds)}).", bed_source)
            else:
                add_exp("bedrooms", "Bedrooms", "unmatched", bed_score, ", ".join(investor_beds), bed_label,
                        f"{bed_label} does not match your preference ({', '.join(investor_beds)}).", bed_source)
        elif enrichment and enrichment.get("enrichment_status") == "CONFIRMED":
            qdrant_attrs = enrichment.get("property_attributes", {}) if enrichment else {}
            opts = qdrant_attrs.get("bedrooms_options")
            bed_source = enrichment.get("provenance", {}).get("bedrooms", "qdrant:bedroom_norm")
            if opts and isinstance(opts, list) and len(opts) > 0:
                mn = min(opts); mx = max(opts)
                bed_label = f"{mn}–{mx} BR" if mn != mx else f"{mn} BR"
                if bed_score >= 100:
                    add_exp("bedrooms", "Bedrooms", "matched", bed_score, ", ".join(investor_beds), bed_label,
                            f"Bedroom options [{bed_label}] in the matched Qdrant units include your preference ({', '.join(investor_beds)}).", bed_source)
                else:
                    add_exp("bedrooms", "Bedrooms", "unmatched", bed_score, ", ".join(investor_beds), bed_label,
                            f"Bedroom options [{bed_label}] in the matched Qdrant units do not include your preference ({', '.join(investor_beds)}).", bed_source)
            else:
                qdrant_beds = qdrant_attrs.get("bedrooms")
                bed_label = f"{qdrant_beds} bedroom(s)" if qdrant_beds is not None else "Confirmed"
                if bed_score >= 100:
                    add_exp("bedrooms", "Bedrooms", "matched", bed_score, ", ".join(investor_beds), bed_label,
                            f"{bed_label} matches your preference ({', '.join(investor_beds)}).", bed_source)
                else:
                    add_exp("bedrooms", "Bedrooms", "unmatched", bed_score, ", ".join(investor_beds), bed_label,
                            f"{bed_label} does not match your preference ({', '.join(investor_beds)}).", bed_source)
        else:
            bed_source = "APIL property record"
            bed_label = "Confirmed"
            if bed_score >= 100:
                add_exp("bedrooms", "Bedrooms", "matched", bed_score, ", ".join(investor_beds), bed_label,
                        f"{bed_label} matches your preference ({', '.join(investor_beds)}).", bed_source)
            else:
                add_exp("bedrooms", "Bedrooms", "unmatched", bed_score, ", ".join(investor_beds), bed_label,
                        f"{bed_label} does not match your preference ({', '.join(investor_beds)}).", bed_source)

    # Not evaluated dimensions
    for dim in fit.get("not_evaluated_dimensions", []):
        reasons_for_dim = [r for r in fit.get("reasons", []) if dim.replace('_', ' ') in r.lower() or dim.lower() in r.lower()]
        reason = reasons_for_dim[0] if reasons_for_dim else f"{dim.replace('_', ' ').title()} not currently evaluated — data unavailable."
        add_exp(dim, dim.replace('_', ' ').title(), "not_evaluated", 0, "Collected in profile", "Unavailable",
                reason)

    # Unknown preferences
    for up in fit.get("unknown_preferences", []):
        up_label = up.replace('_', ' ').title()
        add_exp(up, up_label, "unknown", 0, "Collected in profile", "Unavailable",
                f"{up_label} cannot be evaluated — required data is not currently linked to properties.")

    # Normalize weights so displayed percentages sum to 100%
    eval_weight_sum = sum(e["weight"] for e in explanations if e["status"] in ("matched", "unmatched"))
    if eval_weight_sum > 0:
        for e in explanations:
            if e["status"] in ("matched", "unmatched"):
                e["normalized_weight"] = round((e["weight"] / eval_weight_sum) * 100, 1)
            else:
                e["normalized_weight"] = 0.0

    return explanations


def compute_fit(property_record: Dict, investor_id: Optional[str], enrichment: Optional[Dict] = None) -> Optional[Dict]:
    if not investor_id or investor_id not in investor_profiles:
        return None
    profile_data = investor_profiles[investor_id]
    profile = InvestorProfileModel(profile_data["answers"])
    scorer = InvestorFitScorer(profile)
    return scorer.score_property(property_record, enrichment)


def _resolve_property_status(property_record: Dict, enrichment: Optional[Dict] = None) -> Dict:
    """Resolve canonical status from APIL benchmarks, Qdrant, and DLD with full provenance."""
    benchs = property_record.get("benchmarks", [])

    # APIL status from benchmarks
    has_offplan = any(b["type"] == "OFFPLAN_RESALE" for b in benchs)
    has_ready = any(b["type"] == "READY_RESALE" for b in benchs)
    if has_offplan and has_ready:
        apil_status = "Mixed (Off-plan + Ready)"
    elif has_offplan:
        apil_status = "Off-plan"
    elif has_ready:
        apil_status = "Ready"
    else:
        apil_status = "Unknown"

    # Qdrant status
    qdrant_status = None
    enrichment_confirmed = False
    if enrichment and enrichment.get("enrichment_status") == "CONFIRMED":
        enrichment_confirmed = True
        qdrant_status = enrichment.get("property_attributes", {}).get("status")

    return resolve_canonical_status(
        apil_status=apil_status,
        qdrant_status=qdrant_status,
        dld_statuses=None,
        enrichment_confirmed=enrichment_confirmed,
    )


def _safe_normalize(val):
    """
    Normalize a value to None if it represents missing/empty/invalid data.
    Handles: pandas NaN, numpy NaN, None, "", whitespace, "nan", "NaN",
    "none", "None", "null", "NULL", "undefined", float('nan').
    """
    if val is None:
        return None
    if isinstance(val, float) and val != val:  # NaN check
        return None
    s = str(val).strip()
    if s == "" or s.lower() in ("nan", "none", "null", "undefined", ""):
        return None
    return s


def _safe_master_float(val):
    if val is None or (isinstance(val, float) and val != val):  # NaN check
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def _safe_master_int(val):
    f = _safe_master_float(val)
    if f is None:
        return None
    return int(f)


def _validate_description_bedrooms(description: Optional[str], master_bedrooms: Optional[int]) -> Dict:
    """
    Validate a Qdrant description against MASTER bedroom facts.
    Returns validation result with status and reason.
    """
    result = {"status": "UNAVAILABLE", "reason": "No description to validate"}
    if not description:
        return result

    text = str(description).lower()
    import re

    # Extract explicit bedroom claims from description
    claims = set()

    # Pattern: "1-bedroom", "1 bedroom", "one-bedroom", "one bedroom"
    for num_word, num_val in [("one", 1), ("two", 2), ("three", 3), ("four", 4), ("five", 5)]:
        if re.search(rf'\b{num_word}[-\s]?bedroom', text):
            claims.add(num_val)
        if re.search(rf'\b{num_word}[-\s]?br\b', text):
            claims.add(num_val)

    # Pattern: decimal bedrooms like "1.5-bedroom", "1.5 bedroom"
    for match in re.finditer(r'(\d+\.\d+)[-\s]?bedroom', text):
        claims.add(float(match.group(1)))
    for match in re.finditer(r'(\d+\.\d+)[-\s]?br\b', text):
        claims.add(float(match.group(1)))

    # Pattern: integer bedrooms "1-bedroom", "2-bedroom", etc.
    # Use negative lookbehind to avoid matching digits inside decimals (e.g. 1.5)
    for num in range(0, 10):
        if re.search(rf'(?<![.\d]){num}[-\s]?bedroom', text):
            claims.add(num)
        if re.search(rf'(?<![.\d]){num}[-\s]?br\b', text):
            claims.add(num)

    # Pattern: "studio"
    if re.search(r'\bstudio\b', text):
        claims.add(0)

    if not claims:
        # No explicit bedroom claim found — ambiguous but not conflicting
        return {"status": "AMBIGUOUS_BEDROOM", "reason": "No explicit bedroom claim in description"}

    if master_bedrooms is not None:
        # Round decimal claims to nearest int for compatibility check
        rounded_claims = {round(c) for c in claims}
        if master_bedrooms in rounded_claims:
            return {"status": "VERIFIED_COMPATIBLE", "reason": f"Description claims {sorted(claims)}BR, matching MASTER"}
        else:
            return {"status": "CONFLICT", "reason": f"Description claims {sorted(claims)}BR but MASTER says {master_bedrooms}BR"}

    return {"status": "AMBIGUOUS_BEDROOM", "reason": "MASTER bedroom unavailable for validation"}


def _clean_description(text: Optional[str]) -> Optional[str]:
    """
    Clean and normalize Qdrant description text.
    - Decode HTML entities
    - Remove unsafe script/style tags
    - Preserve paragraphs and headings
    - Normalize whitespace
    - Fix common mojibake
    """
    if not text:
        return None

    import html
    import re

    s = str(text)

    # Decode HTML entities
    s = html.unescape(s)

    # Remove script and style tags completely
    s = re.sub(r'<script[^>]*>.*?</script>', '', s, flags=re.DOTALL | re.IGNORECASE)
    s = re.sub(r'<style[^>]*>.*?</style>', '', s, flags=re.DOTALL | re.IGNORECASE)

    # Replace common mojibake
    replacements = {
        '’': "'",   # right single quotation mark
        '‘': "'",   # left single quotation mark
        '“': '"',   # left double quotation mark
        '”': '"',   # right double quotation mark
        '–': '-',   # en dash
        '—': '-',   # em dash
        ' ': ' ',   # non-breaking space
        '�': '',    # replacement character
    }
    for bad, good in replacements.items():
        s = s.replace(bad, good)

    # Fix common mojibake patterns
    s = s.replace('â\x80\x99', "'")
    s = s.replace('â\x80\x9c', '"')
    s = s.replace('â\x80\x9d', '"')
    s = s.replace('â\x80\x93', '-')
    s = s.replace('â\x80\x94', '-')
    s = s.replace('&amp;', '&')
    s = s.replace('&nbsp;', ' ')

    # Remove other HTML tags but preserve structure with newlines
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'</p>', '\n\n', s, flags=re.IGNORECASE)
    s = re.sub(r'<p[^>]*>', '', s, flags=re.IGNORECASE)
    s = re.sub(r'</h[1-6]>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'<h[1-6][^>]*>', '', s, flags=re.IGNORECASE)
    s = re.sub(r'<li[^>]*>', '\n• ', s, flags=re.IGNORECASE)
    s = re.sub(r'</li>', '', s, flags=re.IGNORECASE)
    s = re.sub(r'<ul[^>]*>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'</ul>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'<ol[^>]*>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'</ol>', '\n', s, flags=re.IGNORECASE)
    s = re.sub(r'<[^>]+>', ' ', s)

    # Normalize whitespace
    s = re.sub(r'\n{3,}', '\n\n', s)
    s = re.sub(r'[ \t]+', ' ', s)
    s = s.strip()

    return s if s else None

def _build_apil_attributes(property_record: Dict, enrichment: Optional[Dict] = None) -> Dict:
    """
    Extract property attributes with FULL provenance hierarchy:
    1. MASTER dataset (authoritative unit-level facts)
    2. Qdrant unit-level data (exact match)
    3. APIL STEP_5 property record
    4. Qdrant project-level aggregate (fallback only)

    Conflict detection: master vs Qdrant unit vs Qdrant project.
    """
    p = property_record["property"]
    dev = property_record["developer"]
    pid = str(p.get("id", "")).strip()
    master = master_by_id.get(pid) if pid else None

    attrs = {}
    prov = {}
    conflicts = {}

    # ── Helper: set attribute with provenance and conflict detection ──
    def set_attr(key, value, source, master_val=None, qdrant_val=None):
        if value is not None:
            attrs[key] = value
            prov[key] = source
            if master_val is not None and qdrant_val is not None and master_val != qdrant_val:
                conflicts[key] = {"master": master_val, "qdrant": qdrant_val}

    # ── Bedrooms ──
    master_beds = _safe_master_int(master.get("unit_bedrooms")) if master else None
    qdrant_unit_beds = None
    qdrant_proj_beds = None
    if enrichment:
        qdrant_unit_beds = enrichment.get("property_attributes", {}).get("unit_bedrooms")
        qdrant_proj_beds = enrichment.get("property_attributes", {}).get("project_bedroom_options")
    step5_beds = p.get("bedrooms")

    if master_beds is not None:
        set_attr("bedrooms", master_beds, "master:verified")
    elif qdrant_unit_beds is not None:
        set_attr("bedrooms", int(qdrant_unit_beds), "qdrant:exact_unit")
    elif step5_beds is not None:
        set_attr("bedrooms", int(step5_beds), "apil:property_record")
    # Conflict detection
    if master_beds is not None and qdrant_unit_beds is not None and master_beds != int(qdrant_unit_beds):
        conflicts["bedrooms"] = {"master": master_beds, "qdrant": int(qdrant_unit_beds)}

    # ── Bathrooms ──
    master_baths = _safe_master_int(master.get("unit_bathrooms")) if master else None
    qdrant_unit_baths = enrichment.get("property_attributes", {}).get("unit_bathrooms") if enrichment else None
    if master_baths is not None:
        set_attr("bathrooms", master_baths, "master:verified")
    elif qdrant_unit_baths is not None:
        set_attr("bathrooms", int(qdrant_unit_baths), "qdrant:exact_unit")
    if master_baths is not None and qdrant_unit_baths is not None and master_baths != int(qdrant_unit_baths):
        conflicts["bathrooms"] = {"master": master_baths, "qdrant": int(qdrant_unit_baths)}

    # ── Size ──
    master_size_sqft = _safe_master_float(master.get("unit_size_sqft")) if master else None
    master_size_sqm = _safe_master_float(master.get("unit_size_sqm")) if master else None
    qdrant_unit_size_sqft = enrichment.get("property_attributes", {}).get("unit_size_sqft") if enrichment else None
    qdrant_unit_size_sqm = enrichment.get("property_attributes", {}).get("unit_size_sqm") if enrichment else None
    step5_size_sqm = p.get("size_sqm")

    if master_size_sqft is not None:
        set_attr("size_sqft", round(master_size_sqft, 1), "master:verified")
        if master_size_sqm is not None:
            set_attr("size_sqm", round(master_size_sqm, 1), "master:verified")
        else:
            set_attr("size_sqm", round(master_size_sqft / 10.764, 1), "master:verified")
    elif qdrant_unit_size_sqft is not None:
        set_attr("size_sqft", round(qdrant_unit_size_sqft, 1), "qdrant:exact_unit")
        if qdrant_unit_size_sqm:
            set_attr("size_sqm", round(qdrant_unit_size_sqm, 1), "qdrant:exact_unit")
    elif step5_size_sqm is not None:
        set_attr("size_sqm", float(step5_size_sqm), "apil:property_record")
        set_attr("size_sqft", round(float(step5_size_sqm) * 10.764, 1), "apil:property_record")
    if master_size_sqft is not None and qdrant_unit_size_sqft is not None and abs(master_size_sqft - qdrant_unit_size_sqft) > 1:
        conflicts["size_sqft"] = {"master": round(master_size_sqft, 1), "qdrant": round(qdrant_unit_size_sqft, 1)}

    # ── Price ──
    master_price = _safe_master_float(master.get("current_price_aed")) if master else None
    qdrant_unit_price = enrichment.get("property_attributes", {}).get("unit_price_aed") if enrichment else None
    step5_price = p.get("current_price_aed")
    if master_price is not None:
        set_attr("price", master_price, "master:verified")
    elif step5_price is not None:
        set_attr("price", float(step5_price), "apil:property_record")
    if master_price is not None and qdrant_unit_price is not None and abs(master_price - qdrant_unit_price) > 1:
        conflicts["price"] = {"master": master_price, "qdrant": qdrant_unit_price}

    # ── Status ──
    master_status = str(master.get("unit_status", "")).strip() if master else ""
    qdrant_unit_status = enrichment.get("property_attributes", {}).get("unit_status") if enrichment else None
    status_resolution = _resolve_property_status(property_record, enrichment)
    canonical_status = status_resolution["canonical_status"]
    if master_status:
        attrs["status"] = master_status
        prov["status"] = "master:verified"
    elif canonical_status:
        attrs["status"] = canonical_status
        prov["status"] = f"canonical:{status_resolution['chosen_source']}"
    if status_resolution.get("conflict_detected"):
        conflicts["status"] = status_resolution["conflict_details"]
    if master_status and qdrant_unit_status and master_status.lower() != str(qdrant_unit_status).lower():
        conflicts["status"] = {"master": master_status, "qdrant": qdrant_unit_status}

    # ── Property type ──
    # Hierarchy: MASTER property_type > exact Qdrant unit category > APIL record > unknown
    master_type = _safe_normalize(master.get("property_type")) if master else None
    pt = _safe_normalize(p.get("property_type"))
    qdrant_unit_cat = _safe_normalize(enrichment.get("property_attributes", {}).get("unit_category")) if enrichment else None
    qdrant_proj_cat = _safe_normalize(enrichment.get("property_attributes", {}).get("project_category")) if enrichment else None

    if master_type:
        set_attr("property_type", master_type, "master:property_type")
    elif qdrant_unit_cat:
        set_attr("property_type", qdrant_unit_cat, "qdrant:category (exact unit match)")
    elif pt:
        set_attr("property_type", pt, "apil:property_record")

    # ── Description ──
    # Use exact Qdrant unit description when available and compatible with MASTER facts
    qdrant_unit_desc = enrichment.get("property_attributes", {}).get("unit_description") if enrichment else None
    if qdrant_unit_desc:
        cleaned = _clean_description(qdrant_unit_desc)
        validation = _validate_description_bedrooms(cleaned, master_beds)
        attrs["description"] = cleaned
        attrs["description_status"] = validation["status"]
        attrs["description_reason"] = validation["reason"]
        if validation["status"] == "VERIFIED_COMPATIBLE":
            prov["description"] = "qdrant:description (exact unit match, verified compatible)"
        elif validation["status"] == "AMBIGUOUS_BEDROOM":
            prov["description"] = "qdrant:description (exact unit match, ambiguous bedroom claim)"
        elif validation["status"] == "CONFLICT":
            prov["description"] = "qdrant:description (exact unit match, CONFLICT with MASTER)"
            attrs["description_conflict"] = True
        else:
            prov["description"] = "qdrant:description (exact unit match)"
    elif enrichment and enrichment.get("property_attributes", {}).get("project_description"):
        # Project-level description only if no exact unit description
        proj_desc = _clean_description(enrichment["property_attributes"]["project_description"])
        if proj_desc:
            attrs["description"] = proj_desc
            attrs["description_status"] = "PROJECT_LEVEL_ONLY"
            attrs["description_reason"] = "Project-level description — not exact unit"
            prov["description"] = "qdrant:description (project aggregate)"

    # ── Images ──
    qdrant_unit_images = enrichment.get("property_attributes", {}).get("unit_images") if enrichment else None
    if qdrant_unit_images:
        attrs["images"] = qdrant_unit_images
        prov["images"] = "qdrant:images (exact unit match)"
    elif enrichment and enrichment.get("property_attributes", {}).get("project_images"):
        attrs["images"] = enrichment["property_attributes"]["project_images"]
        prov["images"] = "qdrant:images (project aggregate)"

    # ── Amenities ──
    qdrant_unit_amenities = enrichment.get("property_attributes", {}).get("unit_amenities") if enrichment else None
    if qdrant_unit_amenities:
        attrs["amenities"] = qdrant_unit_amenities
        prov["amenities"] = "qdrant:amenities (exact unit match)"
    elif enrichment and enrichment.get("property_attributes", {}).get("project_amenities"):
        attrs["amenities"] = enrichment["property_attributes"]["project_amenities"]
        prov["amenities"] = "qdrant:amenities (project aggregate)"

    # ── Developer ──
    master_dev = str(master.get("developer_name", "")).strip() if master else ""
    dev_name = dev.get("name", "").strip()
    if master_dev:
        set_attr("developer", master_dev, "master:verified")
    elif dev_name:
        set_attr("developer", dev_name, "apil:developer_record")

    # ── Area ──
    master_area = str(master.get("area", "")).strip() if master else ""
    area = p.get("area", "").strip()
    if master_area:
        set_attr("area", master_area, "master:verified")
    elif area:
        set_attr("area", area, "apil:property_record")

    # ── Project-level ranges (for reference, NEVER as unit values) ──
    if enrichment:
        q_attrs = enrichment.get("property_attributes", {})
        if "project_bedroom_options" in q_attrs:
            attrs["project_bedroom_options"] = q_attrs["project_bedroom_options"]
            prov["project_bedroom_options"] = "qdrant:project aggregate"
        if "project_bathroom_options" in q_attrs:
            attrs["project_bathroom_options"] = q_attrs["project_bathroom_options"]
            prov["project_bathroom_options"] = "qdrant:project aggregate"
        if "project_size_min_sqft" in q_attrs:
            attrs["project_size_min_sqft"] = q_attrs["project_size_min_sqft"]
            attrs["project_size_max_sqft"] = q_attrs["project_size_max_sqft"]
            prov["project_size_range"] = "qdrant:project aggregate"
        if "project_status_options" in q_attrs:
            attrs["project_status_options"] = q_attrs["project_status_options"]
            prov["project_status_options"] = "qdrant:project aggregate"

    # ── Master metadata ──
    if master:
        attrs["master_matched"] = True
        attrs["master_qdrant_match_quality"] = master.get("qdrant_match_quality")
        attrs["master_qdrant_match_note"] = master.get("qdrant_match_note")
        attrs["master_dld_match_quality"] = master.get("dld_match_quality")
        attrs["master_dld_transaction_count"] = master.get("dld_transaction_count")
        attrs["master_dld_median_price"] = master.get("dld_median_price_aed")
    else:
        attrs["master_matched"] = False

    return {
        "attributes": attrs,
        "provenance": prov,
        "conflicts": conflicts,
        "master_available": master is not None,
    }


def _live_to_step5_format(live: Dict) -> Dict:
    """Convert live benchmark output to STEP_5 benchmark format."""
    # Compute both percentage formulas
    med = live.get("benchmark_median")
    price = live.get("subject_price")
    apil_pct = live.get("price_difference_percentage")
    conventional_pct = None
    if med is not None and price and price > 0:
        conventional_pct = ((med - price) / med) * 100

    return {
        "type": "LIVE_DLD",
        "median_price_aed": live["benchmark_median"],
        "mean_price_aed": live["benchmark_mean"],
        "transaction_count": live["transaction_count"],
        "match_level": live["match_method"],
        "confidence": live["match_confidence"].capitalize() if live.get("match_confidence") else "Medium",
        "price_advantage_pct": round(apil_pct, 2) if apil_pct is not None else None,
        "conventional_below_benchmark_pct": round(conventional_pct, 2) if conventional_pct is not None else None,
        "usable_for_investment": live["usable_for_investment"],
        "matched_project": live["matched_project"],
        "bedroom_filter": live["bedroom_filter"],
        "status_filter": live["status_filter"],
        "matched_transaction_ids": live["matched_transaction_ids"],
        "evidence_level": live.get("evidence_level", "UNKNOWN"),
        "warnings": live.get("warnings", []),
        # ── Explicit calculation identity (§25–36) ──
        "benchmark_method": live.get("benchmark_method", "CANONICAL_DLD"),
        "benchmark_tier": live.get("benchmark_tier", "LEVEL_1"),
        "is_fallback": live.get("is_fallback", False),
        "fallback_type": live.get("fallback_type"),
        "production_eligible": live.get("production_eligible", False),
        "validation_status": live.get("validation_status", "VERIFIED_PRODUCTION"),
        "calculation_version": live.get("calculation_version", "CANONICAL_DLD_SALES_ONLY_V1"),
    }


def _recompute_price_analysis(benchmarks: List[Dict], subject_price: float) -> Dict:
    """Recompute price_analysis from a fresh set of benchmarks."""
    usable = [b for b in benchmarks if b.get("usable_for_investment")]
    if not usable:
        return {
            "best_usable_advantage_pct": None,
            "best_usable_benchmark_type": None,
            "advantage_primary_pct": None,
            "advantage_offplan_pct": None,
            "advantage_ready_pct": None,
            "benchmark_agreement": "INSUFFICIENT_EVIDENCE",
            "evidence_strength": "NONE",
        }

    best = max(usable, key=lambda b: b.get("price_advantage_pct") or -999)
    advantages = [b["price_advantage_pct"] for b in usable if b.get("price_advantage_pct") is not None]

    agreement = "INSUFFICIENT_EVIDENCE"
    if len(advantages) >= 2:
        if all(a > 0 for a in advantages):
            agreement = "CONSISTENT_POSITIVE"
        elif all(a < 0 for a in advantages):
            agreement = "CONSISTENT_NEGATIVE"
        else:
            agreement = "MIXED"
    elif len(advantages) == 1:
        agreement = "SINGLE_BENCHMARK"

    evidence = "USABLE" if len(usable) >= 1 and usable[0].get("transaction_count", 0) >= 3 else "WEAK"

    # Compute conventional below-benchmark percentage
    conv_best = None
    best_median = best.get("median_price_aed")
    if best_median is not None and subject_price and subject_price > 0:
        conv_best = round(((best_median - subject_price) / best_median) * 100, 2)

    # Detect duplicate evidence among benchmarks
    benchmarks = _detect_duplicate_benchmarks(benchmarks)
    independent = [b for b in usable if b.get("_evidence_independence") != "DUPLICATE"]
    independent_count = max(1, len(independent)) if usable else 0

    # Adjust agreement: duplicate rows should not inflate to CONSISTENT_POSITIVE
    if agreement == "CONSISTENT_POSITIVE" and independent_count < 2:
        agreement = "SINGLE_BENCHMARK"

    return {
        "best_usable_advantage_pct": best.get("price_advantage_pct"),
        "best_usable_conventional_pct": conv_best,
        "best_usable_benchmark_type": best.get("type"),
        "advantage_primary_pct": next((b["price_advantage_pct"] for b in usable if b["type"] == "PRIMARY"), None),
        "advantage_offplan_pct": next((b["price_advantage_pct"] for b in usable if b["type"] in ("OFFPLAN_RESALE", "LIVE_DLD")), None),
        "advantage_ready_pct": next((b["price_advantage_pct"] for b in usable if b["type"] == "READY_RESALE"), None),
        "benchmark_agreement": agreement,
        "evidence_strength": evidence,
        "independent_cohort_count": independent_count,
    }


def _is_strong_evidence(evidence: str) -> bool:
    """Return True if evidence strength is sufficient for MEDIUM+ confidence."""
    return evidence in ("USABLE", "STRONG")


def _detect_duplicate_benchmarks(benchmarks: List[Dict]) -> List[Dict]:
    """Mark benchmarks that share identical underlying evidence as duplicates.

    Two benchmarks are considered duplicate if they share the same
    transaction IDs, OR the same median + mean + count (indicating they
    were computed from the same transaction set).
    """
    seen = {}
    for b in benchmarks:
        tx_ids = tuple(sorted(b.get("matched_transaction_ids", []) or []))
        if tx_ids:
            key = tx_ids
        else:
            # Fallback: compare by median + mean + count
            key = (
                b.get("median_price_aed"),
                b.get("mean_price_aed"),
                b.get("transaction_count"),
            )
        if key in seen:
            b["_evidence_duplicate_of"] = seen[key]
            b["_evidence_independence"] = "DUPLICATE"
        else:
            seen[key] = b.get("type", "UNKNOWN")
            b["_evidence_independence"] = "INDEPENDENT"
    return benchmarks


def _recompute_investment_decision(price_analysis: Dict, developer: Dict) -> Dict[str, Any]:
    """Recompute investment decision from live price analysis."""
    adv = price_analysis.get("best_usable_advantage_pct")
    evidence = price_analysis.get("evidence_strength", "NONE")
    agreement = price_analysis.get("benchmark_agreement", "INSUFFICIENT_EVIDENCE")
    independent_count = price_analysis.get("independent_cohort_count", 1)

    if adv is None or agreement == "INSUFFICIENT_EVIDENCE":
        return {
            "decision": "INSUFFICIENT_EVIDENCE",
            "confidence": "LOW",
            "decision_reason": "No usable benchmark available after live recalculation.",
            "recommendation": "Insufficient data to evaluate this property.",
            "warnings": ["Benchmark recalculated from DLD but produced insufficient evidence."],
            "source_calculation": "CANONICAL_DLD",
        }

    # Effective agreement: if only one independent cohort, treat as SINGLE_BENCHMARK
    # even if duplicate benchmark rows say CONSISTENT_POSITIVE
    effective_agreement = agreement
    if agreement == "CONSISTENT_POSITIVE" and independent_count < 2:
        effective_agreement = "SINGLE_BENCHMARK"

    strong = _is_strong_evidence(evidence)

    # Decision gates
    if adv >= 30 and strong and effective_agreement == "CONSISTENT_POSITIVE":
        decision = "STRONG_OPPORTUNITY"
        confidence = "HIGH"
    elif adv > 0 and effective_agreement in ("CONSISTENT_POSITIVE", "SINGLE_BENCHMARK"):
        decision = "OPPORTUNITY"
        confidence = "MEDIUM" if strong else "LOW"
    elif adv > 0:
        decision = "WATCH"
        confidence = "LOW"
    elif -20 <= adv <= 0:
        decision = "CAUTION"
        confidence = "MEDIUM" if strong else "LOW"
    else:
        decision = "AVOID"
        confidence = "MEDIUM" if strong else "LOW"

    dev_name = developer.get("name", "Unknown")
    dev_grade = developer.get("grade", "")
    dev_tier = developer.get("quality_tier", "")

    reason = (
        f"Developer: {dev_name} ({dev_grade}) | "
        f"Live benchmark: {adv:+.1f}% | "
        f"Evidence: {evidence} | "
        f"Agreement: {effective_agreement}"
    )

    recommendation = f"Decision: {decision} | {reason}"

    warnings = []
    if evidence == "WEAK":
        warnings.append("Low transaction count for benchmark.")
    if independent_count < 2 and agreement == "CONSISTENT_POSITIVE":
        warnings.append("Multiple benchmark labels share the same underlying transaction set — treated as single evidence cohort.")

    return {
        "decision": decision,
        "confidence": confidence,
        "decision_reason": reason,
        "recommendation": recommendation,
        "warnings": warnings,
        "source_calculation": "CANONICAL_DLD",
    }


def build_response(r: Dict, fit: Optional[Dict] = None, investor_id: Optional[str] = None, enrichment: Optional[Dict] = None, use_live_benchmark: bool = True) -> Dict:
    """Build investor-facing response with clear objective/fit separation and optional Qdrant enrichment.

    If use_live_benchmark is True (default), computes a live DLD benchmark and
    replaces STEP_5 benchmarks when there is a material discrepancy (wrong project,
    wrong bedroom, missing transactions, etc.).
    """
    # --- Live benchmark computation (defensive) ---
    live_benchmark = None
    benchmark_validation = None
    if use_live_benchmark:
        try:
            prop = r.get("property", {})
            subject_price = prop.get("current_price_aed", 0)
            project_name = prop.get("name", "")

            # Determine bedroom from enrichment or APIL
            bedroom = prop.get("bedrooms")
            if bedroom is None and enrichment and enrichment.get("enrichment_status") == "CONFIRMED":
                bedroom = enrichment.get("property_attributes", {}).get("bedrooms")

            # Determine status via canonical resolver
            status_resolution = _resolve_property_status(r, enrichment)
            status = status_resolution["canonical_status"]

            live_benchmark = compute_project_benchmark(
                project_name=project_name,
                subject_price=subject_price,
                bedroom=bedroom,
                status=status if status in ("Ready", "Offplan") else None,
            )

            # Compare with STEP_5
            benchmark_validation = validate_step5_benchmark(r)
        except Exception as e:
            benchmark_validation = {"error": str(e)}

    # Decide which benchmarks to serve
    # IMPORTANT: Deep-copy benchmarks to avoid mutating the original STEP_5 record,
    # which would corrupt data for subsequent endpoint calls.
    import copy
    final_benchmarks = copy.deepcopy(r["benchmarks"])
    final_price_analysis = copy.deepcopy(r["price_analysis"])
    benchmark_warnings = []

    # Decide which benchmarks to serve
    step5_bench = r["benchmarks"][0] if r["benchmarks"] else {}
    step5_match = step5_bench.get("match_level", "")

    # ── LIVE CANONICAL OVERRIDE ──
    # When a live canonical result exists, it ALWAYS drives the investor-facing response.
    # STEP_5 is retained only as audit/provenance metadata under benchmark_validation.
    # No median-diff tolerance (AED 50k or any other) may retain stale STEP_5 data.
    if live_benchmark:
        if step5_match == "project_fuzzy":
            benchmark_warnings.append(
                f"STEP_5 benchmark used fuzzy project matching. "
                f"Live benchmark recalculated from exact project '{live_benchmark.get('matched_project')}'."
            )
        elif live_benchmark.get("evidence_level") in ("NO_SAME_BEDROOM_EVIDENCE", "NO_VERIFIED_EVIDENCE"):
            benchmark_warnings.append(
                f"Live DLD shows {live_benchmark['evidence_level'].replace('_', ' ').lower()} for exact project "
                f"'{live_benchmark.get('matched_project')}'. Replacing STEP_5 benchmark."
            )
        else:
            benchmark_warnings.append(
                "Live canonical DLD benchmark available. Replacing STEP_5 with canonical calculation."
            )
        final_benchmarks = [_live_to_step5_format(live_benchmark)]
        final_price_analysis = _recompute_price_analysis(final_benchmarks, prop.get("current_price_aed", 0))

    # Ensure every benchmark has conventional_below_benchmark_pct for frontend table
    subj_price = prop.get("current_price_aed")
    for b in final_benchmarks:
        if b.get("conventional_below_benchmark_pct") is None and b.get("median_price_aed") is not None and subj_price and subj_price > 0:
            b["conventional_below_benchmark_pct"] = round(((b["median_price_aed"] - subj_price) / b["median_price_aed"]) * 100, 2)

    # ── Detect duplicate evidence in STEP_5 benchmarks ──
    # Even when keeping STEP_5 data, mark benchmarks that share identical
    # transaction sets so the UI does not overstate analytical agreement.
    final_benchmarks = _detect_duplicate_benchmarks(final_benchmarks)

    # ── Minimum transaction validation for STEP_5 benchmarks ──
    # STEP_5 data may have been generated before the 3-transaction minimum rule.
    # Any benchmark with < 3 transactions must be marked unusable for investment.
    MIN_TXN = 3
    benchmarks_modified = False
    for b in final_benchmarks:
        if b.get("usable_for_investment") and (b.get("transaction_count") or 0) < MIN_TXN:
            b["usable_for_investment"] = False
            b["_min_txn_override"] = f"Marked unusable: only {b.get('transaction_count', 0)} transaction(s), minimum required is {MIN_TXN}"
            benchmark_warnings.append(b["_min_txn_override"])
            benchmarks_modified = True

    # Recompute price_analysis if benchmarks were modified by validation
    any_usable = any(b.get("usable_for_investment") for b in final_benchmarks)
    if benchmarks_modified:
        if any_usable:
            final_price_analysis = _recompute_price_analysis(final_benchmarks, prop.get("current_price_aed", 0))
        elif final_price_analysis.get("best_usable_advantage_pct") is not None:
            # Clear the advantage percentages — insufficient evidence to compute
            final_price_analysis["best_usable_advantage_pct"] = None
            final_price_analysis["best_usable_conventional_pct"] = None
            final_price_analysis["best_usable_benchmark_type"] = None
            final_price_analysis["evidence_strength"] = "NONE"
            final_price_analysis["benchmark_agreement"] = "INSUFFICIENT_EVIDENCE"
    elif final_price_analysis.get("best_usable_advantage_pct") is not None and final_price_analysis.get("best_usable_conventional_pct") is None:
        # Benchmarks unchanged but conventional % was missing — compute from the SAME
        # benchmark that produced best_usable_advantage_pct to ensure consistency.
        target_adv = final_price_analysis["best_usable_advantage_pct"]
        matching_b = None
        min_diff = float("inf")
        for b in final_benchmarks:
            if b.get("usable_for_investment") and b.get("price_advantage_pct") is not None:
                diff = abs(b["price_advantage_pct"] - target_adv)
                if diff < min_diff:
                    min_diff = diff
                    matching_b = b
        if matching_b is None:
            matching_b = final_benchmarks[0] if final_benchmarks else {}
        best_med = matching_b.get("median_price_aed") if matching_b else None
        if best_med is not None and subj_price and subj_price > 0:
            final_price_analysis["best_usable_conventional_pct"] = round(((best_med - subj_price) / best_med) * 100, 2)

    # Update agreement and independent cohort count for kept STEP_5 benchmarks
    # that may have duplicate evidence rows.
    if not benchmarks_modified and final_price_analysis.get("best_usable_advantage_pct") is not None:
        usable = [b for b in final_benchmarks if b.get("usable_for_investment")]
        independent = [b for b in usable if b.get("_evidence_independence") != "DUPLICATE"]
        independent_count = max(1, len(independent)) if usable else 0
        final_price_analysis["independent_cohort_count"] = independent_count
        if final_price_analysis.get("benchmark_agreement") == "CONSISTENT_POSITIVE" and independent_count < 2:
            final_price_analysis["benchmark_agreement"] = "SINGLE_BENCHMARK"

    clean = {
        "property": r["property"],
        "developer": r["developer"],
        "benchmarks": final_benchmarks,
        "price_analysis": final_price_analysis,
        "data_quality": r["data_quality"],
        "meta": r["meta"],
    }
    apil_attrs_result = _build_apil_attributes(r, enrichment)
    clean["apil_attributes"] = apil_attrs_result
    clean["master_attributes"] = apil_attrs_result.get("attributes", {})
    clean["master_provenance"] = apil_attrs_result.get("provenance", {})
    clean["data_quality_conflicts"] = apil_attrs_result.get("conflicts", {})
    clean["master_available"] = apil_attrs_result.get("master_available", False)

    # Add MASTER audit status for downstream consumers
    master_overlay = r.get("_master_overlay", {})
    if master_overlay.get("available"):
        clean["final_data_status"] = master_overlay.get("final_data_status", "UNKNOWN")
        clean["master_data_status"] = {
            "bedroom_value_status": master_overlay.get("bedroom_value_status", "UNKNOWN"),
            "dld_evidence_status": master_overlay.get("dld_evidence_status", "UNKNOWN"),
            "price_validation_status": master_overlay.get("price_validation_status", "UNKNOWN"),
            "audit_classification": master_overlay.get("audit_classification", "UNKNOWN"),
        }
    else:
        clean["final_data_status"] = "NO_MASTER_DATA"
        clean["master_data_status"] = None

    # Recompute objective signal if benchmark was replaced OR modified in place
    if final_benchmarks is not r["benchmarks"] or benchmarks_modified:
        recomputed_decision = _recompute_investment_decision(final_price_analysis, r["developer"])
        # Determine if canonical is actually production-usable
        canonical_usable = (
            live_benchmark is not None and
            live_benchmark.get("production_eligible") is True and
            live_benchmark.get("benchmark_median") is not None and
            live_benchmark.get("transaction_count", 0) >= 3
        )
        source_calc = "CANONICAL_DLD" if canonical_usable else "NONE"
        clean["objective_signal"] = {
            "decision": recomputed_decision["decision"],
            "confidence": recomputed_decision["confidence"],
            "reason": recomputed_decision["decision_reason"],
            "recommendation": recomputed_decision["recommendation"],
            "warnings": recomputed_decision["warnings"] + benchmark_warnings,
            "step5_decision": r["investment_decision"]["decision"],
            "step5_confidence": r["investment_decision"]["confidence"],
            "recomputed": True,
            "source_calculation": source_calc,
        }
    else:
        clean["objective_signal"] = {
            "decision": r["investment_decision"]["decision"],
            "confidence": r["investment_decision"]["confidence"],
            "reason": r["investment_decision"]["decision_reason"],
            "recommendation": r["investment_decision"]["recommendation"],
            "warnings": r["investment_decision"]["warnings"] + benchmark_warnings,
            "recomputed": False,
            "source_calculation": "NONE",
        }

    # ── Recompute investor fit using FINAL canonical decision ──
    # The fit passed in was computed using STEP_5 stale investment_decision.
    # After live DLD recomputation, the canonical decision may differ (e.g. WATCH → OPPORTUNITY).
    # Recompute fit so risk_compatibility uses the same decision as objective_signal.
    final_decision = clean["objective_signal"]["decision"]
    final_confidence = clean["objective_signal"]["confidence"]
    if fit and investor_id and investor_id in investor_profiles:
        temp_r = copy.deepcopy(r)
        temp_r["investment_decision"] = {
            "decision": final_decision,
            "confidence": final_confidence,
            "decision_reason": clean["objective_signal"]["reason"],
            "recommendation": clean["objective_signal"]["recommendation"],
            "warnings": clean["objective_signal"]["warnings"],
        }
        profile_data = investor_profiles[investor_id]
        profile = InvestorProfileModel(profile_data["answers"])
        scorer = InvestorFitScorer(profile)
        fit = scorer.score_property(temp_r, enrichment)

    # ── Canonical Calculation Object ──
    # FROZEN — DLD_CANONICAL_UI_V1_FROZEN
    # DO NOT MODIFY WITHOUT EXPLICIT RE-APPROVAL
    # This block defines the canonical calculation identity and formulas.
    # Any change requires: new version marker, full 2,614-property re-audit, regression re-verification.
    # One unified analytical result consumed by all endpoints
    best_bench = final_benchmarks[0] if final_benchmarks else {}

    # Determine evidence level
    evidence_level = "UNKNOWN"
    if live_benchmark and live_benchmark.get("evidence_level"):
        evidence_level = live_benchmark["evidence_level"]
    elif best_bench.get("match_level") == "project_fuzzy":
        evidence_level = "PROJECT_LEVEL_EVIDENCE"
    elif best_bench.get("match_level") == "project_exact" and best_bench.get("transaction_count", 0) > 0:
        evidence_level = "EXACT_PROJECT_SAME_BEDROOM_EVIDENCE"
    elif prop.get("bedrooms") is not None and live_benchmark and live_benchmark.get("provenance", {}).get("dld_records_total", 0) > 0:
        # Project exists in DLD but no matching bedroom
        evidence_level = "NO_SAME_BEDROOM_EVIDENCE"
    else:
        evidence_level = "NO_VERIFIED_EVIDENCE"

    # ── Direct canonical math from live benchmark (§25–36 source sync) ──
    lb_med = live_benchmark.get("benchmark_median") if live_benchmark else None
    subj = prop.get("current_price_aed", 0)
    canonical_apil = round(((lb_med - subj) / subj) * 100, 2) if lb_med is not None and subj and subj > 0 else None
    canonical_conv = round(((lb_med - subj) / lb_med) * 100, 2) if lb_med is not None and subj and subj > 0 else None

    canonical = {
        "property_id": prop.get("id"),
        "subject_price": prop.get("current_price_aed"),
        "subject_bedrooms": prop.get("bedrooms"),
        "subject_status": status_resolution.get("canonical_status") if 'status_resolution' in locals() else prop.get("status"),
        "evidence": {
            "level": evidence_level,
            "matched_project": live_benchmark.get("matched_project") if live_benchmark else best_bench.get("matched_project"),
            "bedroom_filter": live_benchmark.get("bedroom_filter") if live_benchmark else best_bench.get("bedroom_filter"),
            "status_filter": live_benchmark.get("status_filter") if live_benchmark else best_bench.get("status_filter"),
            "transaction_ids": live_benchmark.get("matched_transaction_ids", []) if live_benchmark else best_bench.get("matched_transaction_ids", []),
            "transaction_count": live_benchmark.get("transaction_count") if live_benchmark else best_bench.get("transaction_count", 0),
            "prices": [t["price_aed"] for t in live_benchmark.get("transactions", [])] if live_benchmark else ([t["price_aed"] for t in best_bench.get("transactions", [])] if best_bench else []),
            "median": lb_med if live_benchmark is not None else best_bench.get("median_price_aed"),
        },
        "calculations": {
            "apil_advantage_pct": canonical_apil,
            "conventional_below_benchmark_pct": canonical_conv,
        },
        "confidence": clean["objective_signal"]["confidence"],
        "decision": clean["objective_signal"]["decision"],
        # ── Explicit calculation identity (§25–36) ──
        "benchmark_method": live_benchmark.get("benchmark_method", "CANONICAL_DLD") if live_benchmark else "NONE",
        "benchmark_tier": live_benchmark.get("benchmark_tier", "LEVEL_1") if live_benchmark else "NONE",
        "is_fallback": live_benchmark.get("is_fallback", False) if live_benchmark else False,
        "fallback_type": live_benchmark.get("fallback_type") if live_benchmark else None,
        "production_eligible": live_benchmark.get("production_eligible", False) if live_benchmark else False,
        "validation_status": live_benchmark.get("validation_status", "VERIFIED_PRODUCTION") if live_benchmark else "INSUFFICIENT_EVIDENCE",
        "calculation_version": live_benchmark.get("calculation_version", "CANONICAL_DLD_SALES_ONLY_V1") if live_benchmark else "UNKNOWN",
    }
    clean["canonical_calculation"] = canonical

    # ── Fallback Market Context (DLD_CANONICAL_UI_V1_FROZEN extension) ──
    # Delegates to market_context_service — single runtime orchestration layer.
    # Fallback is DISPLAY CONTEXT ONLY — never drives production signal.
    canonical_usable = (
        canonical.get("benchmark_method") == "CANONICAL_DLD" and
        canonical.get("benchmark_tier") == "LEVEL_1" and
        canonical.get("is_fallback") == False and
        canonical.get("production_eligible") == True and
        canonical.get("validation_status") == "VERIFIED_PRODUCTION" and
        canonical.get("evidence", {}).get("median") is not None and
        canonical.get("evidence", {}).get("transaction_count", 0) >= 3
    )

    level2_result = None
    area_result = None

    if not canonical_usable:
        # Try Level 2
        try:
            level2_result = get_level2_context(
                project_name=project_name,
                subject_price=subject_price,
                bedroom=bedroom,
            )
        except Exception:
            pass

        # Try Area fallback only if Level 2 not available
        if level2_result is None:
            try:
                # Lookup property row from MASTER for unit-level values
                mcs_master_df = _get_fallback_master_df()
                if mcs_master_df is not None:
                    prop_row = None
                    for _, row in mcs_master_df.iterrows():
                        if str(int(row.get("property_id", 0))) == prop.get("id"):
                            prop_row = row
                            break
                    if prop_row is not None:
                        import math as _math
                        bedrooms = prop_row.get("unit_bedrooms")
                        size_sqft = prop_row.get("unit_size_sqft")
                        size_sqm = prop_row.get("unit_size_sqm")
                        area_result = get_area_context(
                            property_id=str(int(prop_row.get("property_id", 0))),
                            property_name=str(prop_row.get("property_name", "")),
                            area=str(prop_row.get("area", "")),
                            developer_name=str(prop_row.get("developer_name", "")),
                            current_price_aed=float(prop_row.get("current_price_aed", 0)) if pd.notna(prop_row.get("current_price_aed")) else 0,
                            unit_bedrooms=int(bedrooms) if bedrooms is not None and not (isinstance(bedrooms, float) and _math.isnan(bedrooms)) else None,
                            unit_bathrooms=prop_row.get("unit_bathrooms"),
                            unit_size_sqft=float(size_sqft) if size_sqft is not None and not (isinstance(size_sqft, float) and _math.isnan(size_sqft)) else None,
                            unit_size_sqm=float(size_sqm) if size_sqm is not None and not (isinstance(size_sqm, float) and _math.isnan(size_sqm)) else None,
                            unit_status=str(prop_row.get("unit_status", "")),
                            property_type=str(prop_row.get("property_type", "")) if pd.notna(prop_row.get("property_type")) else None,
                            bedroom_value_status=str(prop_row.get("bedroom_value_status", "")),
                            dld_evidence_status=str(prop_row.get("dld_evidence_status", "")),
                        )
            except Exception:
                pass

    market_context_source, production_signal_source, fallback_context = select_market_context(
        canonical_usable=canonical_usable,
        level2_result=level2_result,
        area_result=area_result,
    )

    clean["fallback_context"] = fallback_context
    clean["market_context_source"] = market_context_source
    clean["production_signal_source"] = production_signal_source

    # Attach benchmark validation / provenance
    clean["benchmark_validation"] = {
        "live_benchmark": live_benchmark,
        "step5_comparison": benchmark_validation,
        "warnings": benchmark_warnings,
    }
    # STEP 18: Add Qdrant enrichment if available
    if enrichment:
        clean["enrichment"] = enrichment
    if fit:
        # Build structured dimension explanations
        profile_for_explanations = None
        if investor_id and investor_id in investor_profiles:
            profile_for_explanations = InvestorProfileModel(investor_profiles[investor_id]["answers"])
        dimension_explanations = []
        if profile_for_explanations:
            # Pass canonical decision so explanations use final live DLD decision, not stale STEP_5
            canonical_decision = {
                "decision": clean["objective_signal"]["decision"],
                "confidence": clean["objective_signal"]["confidence"],
                "decision_reason": clean["objective_signal"]["reason"],
                "recommendation": clean["objective_signal"]["recommendation"],
                "warnings": clean["objective_signal"]["warnings"],
            }
            dimension_explanations = build_dimension_explanations(fit, r, profile_for_explanations, enrichment, canonical_decision)

        clean["investor_fit"] = {
            "score": fit["score"], "tier": fit["tier"], "subscores": fit["subscores"],
            "matched_preferences": fit["matched_preferences"],
            "unmatched_preferences": fit["unmatched_preferences"],
            "unknown_preferences": fit["unknown_preferences"],
            "not_evaluated_preferences": fit.get("not_evaluated_preferences", []),
            "evaluated_dimensions": fit.get("evaluated_dimensions", []),
            "not_evaluated_dimensions": fit.get("not_evaluated_dimensions", []),
            "dimension_explanations": dimension_explanations,
            "fit_reasons": fit["reasons"], "fit_warnings": fit["warnings"],
        }
        # Use recomputed decision if available
        obj_dec = clean["objective_signal"]["decision"]
        fit_tier = fit["tier"]
        if obj_dec in ("STRONG_OPPORTUNITY", "OPPORTUNITY") and fit["score"] >= 75:
            combined = f"{obj_dec.replace('_', ' ')} with {fit_tier.replace('_', ' ').lower()}. Strong investment signal and a strong match for your preferences."
        elif obj_dec in ("STRONG_OPPORTUNITY", "OPPORTUNITY"):
            combined = f"{obj_dec.replace('_', ' ')} but {fit_tier.replace('_', ' ').lower()}. Good investment signal but may not fully match your preferences."
        elif obj_dec in ("CAUTION", "AVOID") and fit["score"] >= 75:
            combined = f"{obj_dec.replace('_', ' ')} despite {fit_tier.replace('_', ' ').lower()}. Objective investment signal is negative even though this matches your preferences."
        elif obj_dec == "WATCH":
            combined = f"WATCH — potential signal detected with {fit_tier.replace('_', ' ').lower()}. Evidence is not yet strong enough for a firm recommendation."
        elif obj_dec == "INSUFFICIENT_EVIDENCE":
            combined = f"INSUFFICIENT EVIDENCE — {fit_tier.replace('_', ' ').lower()}. We do not have enough data to evaluate this property."
        else:
            combined = f"{obj_dec.replace('_', ' ')} — {fit_tier.replace('_', ' ').lower()}."
        if clean["objective_signal"].get("recomputed"):
            combined = f"[RECOMPUTED FROM LIVE DLD] {combined}"
        clean["combined_explanation"] = combined
    else:
        clean["investor_fit"] = None
        clean["combined_explanation"] = clean["objective_signal"]["reason"]

    # Attach investor profile for transparency
    if investor_id and investor_id in investor_profiles:
        clean["investor_profile"] = investor_profiles[investor_id]["answers"]
    else:
        clean["investor_profile"] = None

    return _sanitize_for_json(clean)


def personalized_rank(pool: List[Dict], investor_id: Optional[str]) -> List[Dict]:
    if not investor_id or investor_id not in investor_profiles:
        return sorted(pool, key=lambda r: (
            DECISION_ORDER.get(r["investment_decision"]["decision"], 99),
            -(r["price_analysis"].get("best_usable_advantage_pct") or -999),
            -(r["_ranking"]["evidence_strength_score"]),
            grade_rank(r["developer"]["grade"]),
            r["property"].get("current_price_aed") or 999999999,
        ))

    profile_data = investor_profiles[investor_id]
    profile = InvestorProfileModel(profile_data["answers"])
    scorer = InvestorFitScorer(profile)

    enriched = []
    for r in pool:
        enrichment = enrich_property(r["property"]["id"], r["property"], r.get("developer"))
        fit = scorer.score_property(r, enrichment)
        enriched.append({"record": r, "fit": fit, "enrichment": enrichment})

    enriched.sort(key=lambda item: (
        DECISION_ORDER.get(item["record"]["investment_decision"]["decision"], 99),
        -item["fit"]["score"],
        -(item["record"]["price_analysis"].get("best_usable_advantage_pct") or -999),
        -(item["record"]["_ranking"]["evidence_strength_score"]),
        grade_rank(item["record"]["developer"]["grade"]),
        item["record"]["property"].get("current_price_aed") or 999999999,
    ))
    return [e["record"] for e in enriched]

# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================
class QuestionnaireRequest(BaseModel):
    investment_objective: str
    budget_min_aed: int = Field(..., ge=100000)
    budget_max_aed: int = Field(..., ge=100000)
    horizon: str
    risk_tolerance: str
    property_status: List[str]
    property_types: List[str]
    bedrooms: List[str]
    locations: List[str]
    developer_preference: Optional[str] = "NO_PREFERENCE"
    liquidity_preference: Optional[str] = "MODERATE"

class InvestorProfileResponse(BaseModel):
    id: str
    created_at: str
    normalized_profile: Dict

class OpportunityListResponse(BaseModel):
    total: int
    page: int
    per_page: int
    investor_id: Optional[str]
    results: List[Dict]
    other_opportunities: Optional[List[Dict]] = None
    eligible_count: int
    other_count: int

# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/health")
def health():
    qdrant = qdrant_health()
    return {
        "service": "APIL Investment Engine API",
        "version": "2.1.0",
        "properties_loaded": len(records),
        "ranked_opportunities": len(ranked_opportunities),
        "developers": len(developer_stats),
        "investor_profiles": len(investor_profiles),
        "qdrant": qdrant,
    }

@app.get("/")
def root():
    return {"service": "APIL Investment Engine API", "version": "2.1.0", "source": "STEP_5_LOCKED", "properties": len(records), "ranked_opportunities": len(ranked_opportunities)}

@app.post("/investors")
def create_investor(req: QuestionnaireRequest):
    investor_id = str(uuid.uuid4())
    profile = InvestorProfileModel(req.dict())
    investor_profiles[investor_id] = {
        "id": investor_id,
        "created_at": datetime.utcnow().isoformat(),
        "answers": req.dict(),
        "normalized_profile": profile.to_dict(),
    }
    save_profiles()
    return {"investor_id": investor_id, "profile": investor_profiles[investor_id]}

@app.get("/investors/{investor_id}")
def get_investor(investor_id: str):
    profile = investor_profiles.get(investor_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Investor profile not found")
    return profile

@app.get("/opportunities")
def list_opportunities(
    decision: Optional[str] = Query(None),
    min_price: Optional[int] = Query(None, ge=0),
    max_price: Optional[int] = Query(None, ge=0),
    developer_grade: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    bedrooms: Optional[int] = Query(None, ge=0),
    min_advantage_pct: Optional[float] = Query(None),
    max_advantage_pct: Optional[float] = Query(None),
    include_insufficient: bool = Query(False),
    sort_by: str = Query("rank"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    investor_id: Optional[str] = Query(None),
    include_other_opportunities: bool = Query(False),
):
    """
    STEP 25: Marketplace now filters by investor eligibility BEFORE ranking.
    Only properties satisfying the investor's hard preferences are returned
    in the main results. Optional `include_other_opportunities` adds a
    secondary list of strong APIL signals that do NOT match preferences.
    """
    pool = records if include_insufficient else ranked_opportunities
    results = []
    for r in pool:
        p = r["property"]
        d = r["investment_decision"]
        price = p.get("current_price_aed")
        adv = r["price_analysis"].get("best_usable_advantage_pct")
        if decision and d["decision"] != decision: continue
        if min_price is not None and (price is None or price < min_price): continue
        if max_price is not None and (price is None or price > max_price): continue
        if developer_grade and not d.get("developer", {}).get("grade", "").startswith(developer_grade): continue
        if area and area.lower() not in str(p.get("area", "")).lower(): continue
        if bedrooms is not None and p.get("bedrooms") != bedrooms: continue
        if min_advantage_pct is not None and (adv is None or adv < min_advantage_pct): continue
        if max_advantage_pct is not None and (adv is None or adv > max_advantage_pct): continue
        results.append(r)

    # STEP 25: Apply investor eligibility filtering when investor_id present
    if investor_id and investor_id in investor_profiles:
        profile_data = investor_profiles[investor_id]
        profile = InvestorProfileModel(profile_data["answers"])
        checker = InvestorEligibilityChecker(profile)
        scorer = InvestorFitScorer(profile)

        eligible_results = []
        other_results = []
        for r in results:
            enrichment = enrich_property(r["property"]["id"], r["property"], r.get("developer"))
            eligibility = checker.check(r, enrichment)
            if eligibility["eligible"]:
                fit = scorer.score_property(r, enrichment)
                resp = build_response(r, fit, investor_id, enrichment)
                resp["eligibility"] = eligibility
                eligible_results.append({"record": r, "fit": fit, "response": resp})
            elif include_other_opportunities:
                fit = scorer.score_property(r, enrichment)
                resp = build_response(r, fit, investor_id, enrichment)
                resp["eligibility"] = eligibility
                other_results.append({"record": r, "fit": fit, "response": resp})

        # Sort eligible by investor fit first, then investment signal quality
        # This ensures personalization controls ranking, not just objective signal
        eligible_results.sort(key=lambda item: (
            -item["fit"]["score"],                                      # 1. Investor fit (primary)
            DECISION_ORDER.get(item["record"]["investment_decision"]["decision"], 99),  # 2. Signal quality
            -(item["record"]["price_analysis"].get("best_usable_advantage_pct") or -999),
            -(item["record"]["_ranking"]["evidence_strength_score"]),
            grade_rank(item["record"]["developer"]["grade"]),
            item["record"]["property"].get("current_price_aed") or 999999999,
        ))

        total = len(eligible_results)
        start = (page - 1) * per_page
        end = start + per_page
        page_results = [e["response"] for e in eligible_results[start:end]]

        other_page = []
        if include_other_opportunities:
            # Sort other opportunities by APIL signal strength only (not investor fit)
            other_results.sort(key=lambda item: (
                DECISION_ORDER.get(item["record"]["investment_decision"]["decision"], 99),
                -(item["record"]["price_analysis"].get("best_usable_advantage_pct") or -999),
                -(item["record"]["_ranking"]["evidence_strength_score"]),
                grade_rank(item["record"]["developer"]["grade"]),
            ))
            other_page = [e["response"] for e in other_results[:per_page]]

        resp = {
            "total": total, "page": page, "per_page": per_page,
            "investor_id": investor_id,
            "results": page_results,
            "other_opportunities": other_page if include_other_opportunities else None,
            "eligible_count": len(eligible_results),
            "other_count": len(other_results),
        }
        if investor_id and investor_id in investor_profiles:
            resp["investor_profile"] = investor_profiles[investor_id]["answers"]
        return _sanitize_for_json(resp)

    # Non-personalized fallback (no investor_id)
    results = personalized_rank(results, investor_id)
    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page
    page_results = results[start:end]

    enriched_results = []
    for r in page_results:
        enrichment = enrich_property(r["property"]["id"], r["property"], r.get("developer"))
        fit = compute_fit(r, investor_id, enrichment)
        enriched_results.append(build_response(r, fit, investor_id, enrichment))
    resp = {
        "total": total, "page": page, "per_page": per_page,
        "investor_id": investor_id,
        "results": enriched_results,
        "other_opportunities": None,
        "eligible_count": total,
        "other_count": 0,
    }
    if investor_id and investor_id in investor_profiles:
        resp["investor_profile"] = investor_profiles[investor_id]["answers"]
    return _sanitize_for_json(resp)

@app.get("/properties/{property_id}")
def get_property(property_id: str, investor_id: Optional[str] = Query(None)):
    r = by_id.get(property_id)
    if not r:
        raise HTTPException(status_code=404, detail="Property not found")
    enrichment = enrich_property(property_id, r["property"], r.get("developer"))
    fit = compute_fit(r, investor_id, enrichment)
    return build_response(r, fit, investor_id, enrichment)

@app.post("/compare")
def compare_properties(req: Dict):
    ids = req.get("property_ids", [])
    investor_id = req.get("investor_id")
    # Deduplicate while preserving order
    seen = set()
    unique_ids = []
    for pid in ids:
        if pid not in seen:
            seen.add(pid)
            unique_ids.append(pid)
    if len(unique_ids) < 2 or len(unique_ids) > 3:
        raise HTTPException(status_code=400, detail="Compare requires 2–3 unique property IDs")
    results = []
    for pid in unique_ids:
        r = by_id.get(pid)
        if not r:
            raise HTTPException(status_code=404, detail=f"Property {pid} not found")
        enrichment = enrich_property(pid, r["property"], r.get("developer"))
        fit = compute_fit(r, investor_id, enrichment)
        results.append(build_response(r, fit, investor_id, enrichment))
    return {"properties": results, "investor_id": investor_id}


@app.get("/debug/eligibility")
def debug_eligibility(investor_id: str = Query(...)):
    """
    Diagnostic endpoint: run the full eligibility pipeline for every property
    and return aggregate counts per dimension.
    """
    if investor_id not in investor_profiles:
        raise HTTPException(status_code=404, detail="Investor profile not found")

    profile_data = investor_profiles[investor_id]
    profile = InvestorProfileModel(profile_data["answers"])
    checker = InvestorEligibilityChecker(profile)

    stats = {
        "total_candidates": len(records),
        "budget": {"pass": 0, "fail": 0},
        "location": {"pass": 0, "fail": 0},
        "property_status": {"pass": 0, "fail": 0},
        "property_type": {"pass": 0, "fail": 0, "not_evaluated": 0},
        "bedrooms": {"pass": 0, "fail": 0, "not_evaluated": 0},
        "final_eligible": 0,
        "final_other": 0,
        "sample_failures": [],
    }

    for r in records:
        enrichment = enrich_property(r["property"]["id"], r["property"], r.get("developer"))
        eligibility = checker.check(r, enrichment)
        checks = eligibility["checks"]

        for dim in ["budget", "location", "property_status"]:
            c = checks.get(dim, {})
            if c.get("pass") is True:
                stats[dim]["pass"] += 1
            elif c.get("pass") is False:
                stats[dim]["fail"] += 1

        pt = checks.get("property_type", {})
        if pt.get("pass") is True:
            stats["property_type"]["pass"] += 1
        elif pt.get("pass") is False:
            stats["property_type"]["fail"] += 1
        else:
            stats["property_type"]["not_evaluated"] += 1

        bd = checks.get("bedrooms", {})
        if bd.get("pass") is True:
            stats["bedrooms"]["pass"] += 1
        elif bd.get("pass") is False:
            stats["bedrooms"]["fail"] += 1
        else:
            stats["bedrooms"]["not_evaluated"] += 1

        if eligibility["eligible"]:
            stats["final_eligible"] += 1
        else:
            stats["final_other"] += 1
            if len(stats["sample_failures"]) < 5:
                stats["sample_failures"].append({
                    "property_id": r["property"]["id"],
                    "property_name": r["property"]["name"],
                    "failed_preferences": eligibility["failed_preferences"],
                    "checks": {k: v for k, v in checks.items() if v.get("pass") is False},
                })

    return _sanitize_for_json(stats)


@app.get("/developers")
def list_developers(grade: Optional[str] = Query(None), page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200)):
    devs = list(developer_stats.values())
    if grade:
        devs = [d for d in devs if d["grade"].startswith(grade)]
    devs.sort(key=lambda d: d["property_count"], reverse=True)
    total = len(devs)
    start = (page - 1) * per_page
    return {"total": total, "page": page, "per_page": per_page, "results": devs[start:start + per_page]}

@app.get("/developers/{developer_name}")
def get_developer(developer_name: str):
    props = by_developer.get(developer_name)
    if not props:
        raise HTTPException(status_code=404, detail="Developer not found")
    stats = developer_stats[developer_name]
    return {"developer": stats, "properties": [build_response(p) for p in props]}

# ============================================================
# DEBUG ENDPOINTS (Phase 9 — remove or protect in production)
# ============================================================
@app.get("/debug/profile/{investor_id}")
def debug_profile(investor_id: str):
    """Return full investor profile and evaluability status."""
    profile = investor_profiles.get(investor_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Investor profile not found")
    model = InvestorProfileModel(profile["answers"])
    return {
        "profile": profile,
        "derived": model.to_dict(),
    }

@app.get("/debug/fit/{investor_id}/{property_id}")
def debug_fit(investor_id: str, property_id: str):
    """Return per-dimension fit breakdown for a specific investor+property pair."""
    if investor_id not in investor_profiles:
        raise HTTPException(status_code=404, detail="Investor profile not found")
    r = by_id.get(property_id)
    if not r:
        raise HTTPException(status_code=404, detail="Property not found")
    enrichment = enrich_property(property_id, r["property"], r.get("developer"))
    fit = compute_fit(r, investor_id, enrichment)
    profile = InvestorProfileModel(investor_profiles[investor_id]["answers"])
    # STEP 25: Add eligibility check to debug endpoint
    checker = InvestorEligibilityChecker(profile)
    eligibility = checker.check(r, enrichment)
    # Debug endpoint shows raw STEP_5 decision for transparency
    explanations = build_dimension_explanations(fit, r, profile, enrichment, r.get("investment_decision")) if fit else []
    apil_attrs = _build_apil_attributes(r)

    # Build sources map showing where each attribute comes from
    # Qdrant provenance keys differ from APIL keys — map them explicitly
    QDRANT_KEY_MAP = {
        "status": "status",
        "property_type": "category",
        "bedrooms": "bedrooms",
        "size_sqm": "size_sqm",  # not directly in qdrant provenance
        "developer": "developer",
        "price": "price",
        "area": "community_area",
    }
    sources = {}
    for key in ["status", "property_type", "bedrooms", "size_sqm", "developer", "price", "area"]:
        qdrant_key = QDRANT_KEY_MAP.get(key, key)
        if enrichment and enrichment.get("enrichment_status") == "CONFIRMED":
            # Try Qdrant first
            qdrant_prov = enrichment.get("provenance", {})
            qdrant_attrs = enrichment.get("property_attributes", {})
            if qdrant_key in qdrant_prov or qdrant_key in qdrant_attrs:
                sources[key] = {
                    "value": qdrant_attrs.get(qdrant_key),
                    "source": qdrant_prov.get(qdrant_key, f"qdrant:{qdrant_key}"),
                    "confidence": "CONFIRMED",
                }
                continue
        # Fall back to APIL
        if key in apil_attrs["provenance"]:
            sources[key] = {
                "value": apil_attrs["attributes"].get(key),
                "source": apil_attrs["provenance"][key],
                "confidence": "APIL_DERIVED",
            }
        else:
            sources[key] = {"value": None, "source": "unavailable", "confidence": "NONE"}

    # Live benchmark validation
    live_benchmark = None
    benchmark_validation = None
    try:
        prop = r.get("property", {})
        subject_price = prop.get("current_price_aed", 0)
        project_name = prop.get("name", "")
        bedroom = prop.get("bedrooms")
        if bedroom is None and enrichment and enrichment.get("enrichment_status") == "CONFIRMED":
            bedroom = enrichment.get("property_attributes", {}).get("bedrooms")
        status_resolution = _resolve_property_status(r, enrichment)
        status = status_resolution["canonical_status"]
        live_benchmark = compute_project_benchmark(
            project_name=project_name,
            subject_price=subject_price,
            bedroom=bedroom,
            status=status if status in ("Ready", "Offplan") else None,
        )
        benchmark_validation = validate_step5_benchmark(r)
    except Exception as e:
        benchmark_validation = {"error": str(e)}

    return {
        "investor_id": investor_id,
        "property_id": property_id,
        "property_name": r["property"]["name"],
        "objective_signal": r["investment_decision"]["decision"],
        "enrichment_status": enrichment.get("enrichment_status") if enrichment else "NOT_CONFIRMED",
        "identity_match": enrichment.get("identity_match") if enrichment else None,
        "matched_qdrant_records": enrichment.get("matched_qdrant_records", []) if enrichment else [],
        "rejected_candidates": enrichment.get("rejected_candidates", []) if enrichment else [],
        "sources": sources,
        "apil_attributes": apil_attrs,
        "enrichment": enrichment,
        "fit": fit,
        "dimension_explanations": explanations,
        "eligible": eligibility["eligible"],
        "eligibility_reasons": eligibility["eligibility_reasons"],
        "failed_preferences": eligibility["failed_preferences"],
        "checks": eligibility["checks"],
        "live_benchmark": live_benchmark,
        "benchmark_validation": benchmark_validation,
    }

# ============================================================
# DEBUG: Benchmark Sources — returns canonical + active fallbacks
# ============================================================

@app.get("/debug/benchmark-sources/{property_id}")
def debug_benchmark_sources(property_id: str):
    """
    Development-only endpoint returning canonical, Level 2, and Area fallback
    calculations for a property. Uses market_context_service (same runtime as
    production). Does NOT affect production signals.
    """
    try:
        import math
        master_df = pd.read_excel(MASTER_XLSX_PATH)
        row_match = master_df[master_df["property_id"] == int(property_id)]
        if row_match.empty:
            raise HTTPException(status_code=404, detail="Property not found in MASTER")

        row = row_match.iloc[0]
        project_name = str(row.get("property_name", ""))
        subject_price = float(row.get("current_price_aed", 0)) if pd.notna(row.get("current_price_aed")) else 0
        bedrooms = row.get("unit_bedrooms")
        if isinstance(bedrooms, float) and math.isnan(bedrooms):
            bedrooms = None
        status = str(row.get("unit_status", ""))
        area = str(row.get("area", ""))
        developer_name = str(row.get("developer_name", ""))
        property_type = str(row.get("property_type", "")) if pd.notna(row.get("property_type")) else None
        bedroom_value_status = str(row.get("bedroom_value_status", ""))
        dld_evidence_status = str(row.get("dld_evidence_status", ""))
        size_sqft = row.get("unit_size_sqft")
        if isinstance(size_sqft, float) and math.isnan(size_sqft):
            size_sqft = None
        size_sqm = row.get("unit_size_sqm")
        bathrooms = row.get("unit_bathrooms")

        # ── Canonical (same as production) ──
        canonical = compute_project_benchmark(
            project_name=project_name,
            subject_price=subject_price,
            bedroom=int(bedrooms) if bedrooms is not None else None,
            status=status if status in ("Ready", "Offplan") else None,
        )

        # ── Level 2 fallback (via market_context_service) ──
        level2 = get_level2_context(
            project_name=project_name,
            subject_price=subject_price,
            bedroom=int(bedrooms) if bedrooms is not None else None,
        )

        # ── Area fallback (via market_context_service) ──
        area_fallback = get_area_context(
            property_id=str(int(row["property_id"])),
            property_name=project_name,
            area=area,
            developer_name=developer_name,
            current_price_aed=subject_price,
            unit_bedrooms=int(bedrooms) if bedrooms is not None else None,
            unit_bathrooms=bathrooms,
            unit_size_sqft=float(size_sqft) if size_sqft is not None else None,
            unit_size_sqm=float(size_sqm) if size_sqm is not None and not math.isnan(size_sqm) else None,
            unit_status=status,
            property_type=property_type,
            bedroom_value_status=bedroom_value_status,
            dld_evidence_status=dld_evidence_status,
        )

        return {
            "property_id": property_id,
            "canonical": canonical,
            "level2": level2,
            "area_fallback": area_fallback,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Benchmark sources error: {str(e)}")


# ============================================================
# SIMPLE HTML DEMO FRONTEND
# ============================================================
@app.get("/ui", response_class=HTMLResponse)
def investor_ui():
    frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist", "index.html")
    return open(frontend_dist).read() if os.path.exists(frontend_dist) else "<h1>Build the frontend first</h1>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
