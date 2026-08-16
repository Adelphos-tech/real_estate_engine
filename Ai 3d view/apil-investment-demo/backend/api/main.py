"""
APIL Investment Intelligence API
FastAPI server serving precomputed intelligence.

Endpoints:
  GET /health
  GET /communities
  GET /communities/{slug}
  GET /developers
  GET /developers/{name}
  GET /projects
  GET /projects/{slug}
  GET /properties/ready
  GET /properties/ready/{id}
  GET /properties/offplan
  GET /properties/offplan/{slug}
  POST /recommendations  (accepts investor profile)
  GET /report/{report_id}
"""
from __future__ import annotations

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any

from config.settings import (
    COMMUNITY_SCORES_FILE, DEVELOPER_SCORES_FILE, PROJECT_SCORES_FILE,
    READY_PROPERTY_SCORES_FILE, OFFPLAN_SCORES_FILE, RECOMMENDATIONS_FILE,
    API_HOST, API_PORT, BACKEND_DATA_DIR
)
from engines.utils import load_json, safe_float
from engines.recommendation_engine import generate_recommendations, parse_budget

app = FastAPI(title="APIL Investment Intelligence API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Models ───

class InvestorProfile(BaseModel):
    goal: Optional[str] = None
    budget: Optional[str] = None
    property_type: Optional[str] = None
    bedrooms: Optional[str] = None
    location: Optional[str] = None
    ready_offplan: Optional[str] = None
    timeline: Optional[str] = None
    financing: Optional[str] = None
    risk: Optional[str] = None


# ─── Helpers ───

def safe_load(path: Path) -> list[dict] | dict:
    if not path.exists():
        return []
    return load_json(path)


# ─── Health ───

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "3.0.0",
        "timestamp": datetime.now().isoformat(),
        "data_files": {
            "communities": COMMUNITY_SCORES_FILE.exists(),
            "developers": DEVELOPER_SCORES_FILE.exists(),
            "projects": PROJECT_SCORES_FILE.exists(),
            "ready_properties": READY_PROPERTY_SCORES_FILE.exists(),
            "offplan": OFFPLAN_SCORES_FILE.exists(),
            "recommendations": RECOMMENDATIONS_FILE.exists(),
        }
    }


# ─── Communities ───

@app.get("/communities")
async def list_communities():
    return safe_load(COMMUNITY_SCORES_FILE)


@app.get("/communities/{slug}")
async def get_community(slug: str):
    data = safe_load(COMMUNITY_SCORES_FILE)
    for c in data:
        if c.get("slug") == slug:
            return c
    raise HTTPException(404, "Community not found")


# ─── Developers ───

@app.get("/developers")
async def list_developers():
    return safe_load(DEVELOPER_SCORES_FILE)


@app.get("/developers/{name}")
async def get_developer(name: str):
    data = safe_load(DEVELOPER_SCORES_FILE)
    for d in data:
        if d.get("name", "").lower().replace(" ", "-") == name.lower().replace(" ", "-"):
            return d
    raise HTTPException(404, "Developer not found")


# ─── Projects ───

@app.get("/projects")
async def list_projects(limit: int = Query(100, le=500)):
    data = safe_load(PROJECT_SCORES_FILE)
    return data[:limit]


@app.get("/projects/{slug}")
async def get_project(slug: str):
    data = safe_load(PROJECT_SCORES_FILE)
    for p in data:
        if p.get("slug") == slug:
            return p
    raise HTTPException(404, "Project not found")


# ─── Ready Properties ───

@app.get("/properties/ready")
async def list_ready_properties(limit: int = Query(50, le=200)):
    data = safe_load(READY_PROPERTY_SCORES_FILE)
    return data[:limit]


@app.get("/properties/ready/{property_id}")
async def get_ready_property(property_id: str):
    data = safe_load(READY_PROPERTY_SCORES_FILE)
    for p in data:
        if p.get("id") == property_id:
            return p
    raise HTTPException(404, "Ready property not found")


# ─── Off-plan Properties ───

@app.get("/properties/offplan")
async def list_offplan_properties(limit: int = Query(50, le=200)):
    data = safe_load(OFFPLAN_SCORES_FILE)
    return data[:limit]


@app.get("/properties/offplan/{slug}")
async def get_offplan_property(slug: str):
    data = safe_load(OFFPLAN_SCORES_FILE)
    for p in data:
        if p.get("slug") == slug:
            return p
    raise HTTPException(404, "Off-plan property not found")


# ─── Recommendations ───

@app.post("/recommendations")
async def recommendations(profile: InvestorProfile):
    recs = generate_recommendations(profile.model_dump())
    return recs


# ─── Report ───

@app.post("/report")
async def generate_report(profile: InvestorProfile):
    """Generate a full investment report from precomputed scores."""
    report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
    recs = generate_recommendations(profile.model_dump())

    top = recs["recommendations"][0] if recs["recommendations"] else None

    if not top:
        return {
            "reportId": report_id,
            "error": "No properties found matching criteria",
            "profile": profile.model_dump(),
        }

    # Data integrity checks — verify entity relationships
    integrity_checks = []
    prop_area = top.get("area", "")
    prop_project = top.get("project", "")

    # Check: property area should match project area
    proj_data = top.get("projectData", {})
    if proj_data and proj_data.get("area") and prop_area:
        if proj_data["area"].lower() != prop_area.lower():
            integrity_checks.append({
                "check": "property_area_matches_project",
                "passed": False,
                "detail": f"Property area '{prop_area}' != project area '{proj_data['area']}'"
            })
        else:
            integrity_checks.append({"check": "property_area_matches_project", "passed": True})

    # Check: community data should exist for property area
    comm_data = top.get("communityData", {})
    if not comm_data:
        integrity_checks.append({
            "check": "community_data_available",
            "passed": False,
            "detail": f"No community data for area '{prop_area}'"
        })
    else:
        integrity_checks.append({"check": "community_data_available", "passed": True})

    # Check: developer should not be Independent/Other if project has a known developer
    dev_data = top.get("developerData", {})
    if dev_data and dev_data.get("name") == "Independent / Other":
        integrity_checks.append({
            "check": "developer_identified",
            "passed": False,
            "detail": f"Developer not matched for project '{prop_project}'"
        })
    else:
        integrity_checks.append({"check": "developer_identified", "passed": True})

    # Check: budget compliance
    min_p, max_p = parse_budget(profile.budget or "")
    asking = safe_float(top.get("askingPrice", 0))
    if min_p > 0 and asking > 0:
        if not (min_p <= asking <= max_p):
            integrity_checks.append({
                "check": "price_within_budget",
                "passed": False,
                "detail": f"Price AED {asking:,.0f} outside budget AED {min_p:,.0f}–{max_p:,.0f}"
            })
        else:
            integrity_checks.append({"check": "price_within_budget", "passed": True})

    # Build report from precomputed data
    report: dict[str, Any] = {
        "reportId": report_id,
        "profile": profile.model_dump(),
        "generatedAt": datetime.now().isoformat(),
        "totalMatches": recs["totalReadyMatches"] + recs["totalOffplanMatches"],
        "recommendation": top.get("recommendation", "HOLD"),
        "topProperty": top,
        "alternatives": recs["recommendations"][1:5],
        "communityScore": top.get("communityScore"),
        "projectScore": top.get("projectScore"),
        "developerScore": top.get("developerScore"),
        "propertyScore": top.get("readyScore") or top.get("offplanScore"),
        "integrityChecks": integrity_checks,
        "relaxed": recs.get("relaxed", False),
        "relaxationNote": recs.get("relaxationNote", ""),
        "relaxationSteps": recs.get("relaxationSteps", []),
        "recommendationConfidence": recs.get("recommendationConfidence", {}),
    }

    # Save report
    report_path = BACKEND_DATA_DIR / f"report_{report_id}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    return report


@app.get("/report/{report_id}")
async def get_report(report_id: str):
    report_path = BACKEND_DATA_DIR / f"report_{report_id}.json"
    if not report_path.exists():
        raise HTTPException(404, "Report not found")
    return load_json(report_path)


# ─── Main ───

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
