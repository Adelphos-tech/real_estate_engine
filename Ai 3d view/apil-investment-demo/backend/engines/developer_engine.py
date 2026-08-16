"""
APIL Developer Intelligence Engine
Runs weekly. Produces developer_scores.json

Pipeline:
  DXBInteract + Google Reviews + Construction History +
  Delivered Projects + Delay History + Market Reputation →
  Developer Intelligence → Developer Score
"""
from __future__ import annotations

import sys
import os
import json
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.utils import clamp, safe_float, safe_int, save_json, load_json
from config.settings import (
    DEVELOPER_SCORES_FILE, DEVELOPERS_JSON, PROJECTS_JSON,
    LLM_SERVER, LLM_MODEL, BACKEND_DATA_DIR
)

DEVELOPER_KEYWORDS: dict[str, list[str]] = {
    "Emaar Properties": ["EMAAR", "BURJ KHALIFA", "DUBAI HILLS", "DOWNTOWN", "CREEK HARBOUR", "EMAAR BEACHFRONT", "EMAAR VALLEY", "EMAAR OCEAN"],
    "Damac Properties": ["DAMAC", "AKOYA", "DAMAC HILLS", "CAVALLI", "JUST CAVALLI", "CAVALLI COUTURE", "CAVALLI ESTATES", "PARAMOUNT", "DA TOWER", "GOLF VISTA", "CHESS TOWER", "LAKE TERRACE", "LAKE VIEW", "PARK TOWER", "GREENS AVENUE", "LAKESIDE", "BERJAYA"],
    "Binghatti": ["BINGHATTI"],
    "Danube Properties": ["DANUBE", "PEARL", "ELIZA", "BEACH MONT"],
    "Nakheel": ["NAKHEEL", "PALM JUMEIRAH", "PALM DEIRA", "THE WORLD", "PALM 360", "NAD AL SHEBA"],
    "Meraas": ["MERAAS", "CITY WALK", "BLUEWATERS", "LA MER", "BVLGARI", "PORT DE LA MER", "SUR LA MER", "AL MIZHAR"],
    "Dubai Properties": ["DUBAI PROPERTIES", "MUDON", "REMRAAM", "SERENA", "MADINAT JUMEIRAH"],
    "MAG Group": ["MAG", "MAG EYE", "MAG 318", "MAG PARK", "MAG CITY"],
    "Aldar Properties": ["ALDAR", "AL GHADEER", "AL MUNIRA", "YAS ISLAND"],
    "Azizi Developments": ["AZIZI", "RIVIERA", "ALIYA", "MONTENEGRO", "MIRAGE", "SAPHIRE", "PEARL HOUSE", "ALYA", "VICTORIA", "AL FAYROUZ", "MINC", "RIVIERA BEACH", "SCHON"],
    "Ellington Properties": ["ELLINGTON", "BELTON", "WILTON", "PARK VIEWS", "MERIDIA", "WILTON PARK"],
    "Deyaar": ["DEYAAR", "MIDORA", "ROSE", "REGAL", "SAFFRON", "BLOSSOM", "CEDAR"],
    "Select Group": ["SELECT GROUP", "SELECT", "SIX SENSES", "PALM JEBEL ALI"],
    "Tiger Properties": ["TIGER", "TIGER TOWER", "TIGER WOOD", "TIGER VINE"],
    "Al Futtaim": ["AL FUTTAIM", "MAJID AL FUTTAIM", "DUBAI FESTIVAL", "FESTIVAL CITY", "FESTIVAL PLAZA"],
    "Dubai South": ["DUBAI SOUTH", "MAGZ", "EXPO CITY", "EXPO VILLAGE"],
    "Diamond Developers": ["DIAMOND", "DIAMOND DEVELOPERS", "THE SUSTAINABLE CITY"],
    "Dar Al Arkan": ["DAR AL ARKAN", "MISSONI", "URBAN OASIS", "OCTA ISLE", "W RESIDENCES"],
    "Sobha Realty": ["SOBHA", "SOBHA HARTLAND", "SOBHA CITY", "MEYDAN", "CRESCENT"],
    "Arada": ["ARADA", "AL JADA", "MASAAR", "SEDRA", "NUKHAILA", "SHARJAH GATE"],
    "Siroya": ["SIROYA", "GARNET", "X11", "SABA"],
    "Meraki": ["MERAKI", "MERAKI PIRAEUS", "ROYAL BOUTIQUE"],
    "Izi Properties": ["IZI", "IZI LUX"],
    "Reportage Properties": ["REPORTAGE", "REPORTAGE PROPERTIES"],
    "Sekenkou": ["SEKENKOU", "ELYSIAN", "AMARA", "ALAYA"],
    "Aqarat": ["AQARAT", "LEVENTE", "LEVANTE", "OASIS RESIDENCES"],
    "Palma Development": ["PALMA", "PALMA DEVELOPMENT", "PAPANDREOU", "MILTIADOU", "RODOPOIS", "XANTHOU", "FLEVAS", "ELINIKO"],
    "Metropolitan": ["METRO SUITES", "METROPOLITAN"],
    "Trinity": ["TRINITY", "TRINITY VIEWS"],
    "Lucky Group": ["LUCKY", "LUCKY OASIS", "LUCKY RESIDENCE"],
    "Maison": ["MAISON", "MAISON ELYSEE", "ELYSEE"],
    "Elevia": ["ELEVIA", "ELEVIA RESIDENCES"],
    "Celesto": ["CELESTO", "CELESTO TOWER"],
    "Radiant": ["RADIANT", "RADIANT ELITE", "RADIANT VIEWS"],
    "Samana Developers": ["SAMANA", "SAMANA GREENFIELD", "SAMANA BEACH VIEW", "SAMANA CALIFORNIA", "SAMANA IVY GARDENS"],
}


def match_developer(project_name: str) -> str:
    clean = project_name.upper().strip()
    for dev, keywords in DEVELOPER_KEYWORDS.items():
        for kw in keywords:
            if kw in clean:
                return dev
    return "Independent / Other"


def load_dxb_data() -> dict:
    path = BACKEND_DATA_DIR / "dxb_warehouse.json"
    if path.exists():
        data = load_json(path)
        return {d["developer"]: d for d in data.get("developers", [])}
    return {}


def load_delivery_data() -> dict:
    path = BACKEND_DATA_DIR / "dxb_warehouse.json"
    if path.exists():
        data = load_json(path)
        return data.get("delivery", {})
    return {}


def load_google_reviews() -> dict:
    path = BACKEND_DATA_DIR / "google_warehouse.json"
    if path.exists():
        data = load_json(path)
        return data.get("reviews", {})
    return {}


def load_existing_developers() -> list[dict]:
    if DEVELOPERS_JSON.exists():
        return load_json(DEVELOPERS_JSON)
    return []


def llm_qualitative(dev_name: str, metrics: dict) -> dict:
    import json as _json
    prompt = f"""You are a Dubai real estate expert analyst. Based on the following REAL transaction data for developer "{dev_name}", provide a qualitative assessment.

REAL DATA:
- Total Projects: {metrics.get('totalProjects', 'N/A')}
- Ready Projects: {metrics.get('readyProjects', 'N/A')}
- Sales Transactions: {metrics.get('salesCount', 'N/A')}
- Sales Value: AED {metrics.get('salesValue', 0):,}
- Average Capital Gain: {metrics.get('avgCapitalGain', 'N/A')}%
- Average Rental Yield: {metrics.get('avgRentalYield', 'N/A')}%

Respond as JSON ONLY:
{{
  "constructionQuality": <1-10>,
  "marketReputation": <1-10>,
  "buyerConfidence": "<Excellent|Good|Average|Poor>",
  "marketPosition": "<Tier 1|Tier 2|Tier 3>",
  "summary": "<2-3 sentence assessment>"
}}"""
    payload = _json.dumps({
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 500,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(LLM_SERVER, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"].strip()
            content = content.replace("```json", "").replace("```", "").strip()
            return _json.loads(content)
    except Exception as e:
        print(f"  [WARN] LLM failed for {dev_name}: {e}")
        return {}


def compute_developer_score(metrics: dict, qualitative: dict) -> int:
    score = 0
    breakdown = {}

    # Track Record (25 pts)
    total = safe_int(metrics.get("totalProjects"))
    if total >= 50: pts = 25
    elif total >= 20: pts = 20
    elif total >= 10: pts = 15
    elif total >= 5: pts = 10
    elif total >= 2: pts = 5
    else: pts = 0
    score += pts
    breakdown["trackRecord"] = pts

    # Delivery Performance (20 pts)
    delay_pct = safe_float(qualitative.get("deliveryDelayPercent"), 50)
    if delay_pct < 5: pts = 20
    elif delay_pct < 10: pts = 16
    elif delay_pct < 20: pts = 12
    elif delay_pct < 30: pts = 8
    else: pts = 4
    score += pts
    breakdown["deliveryPerformance"] = pts

    # Capital Gain (15 pts)
    gain = safe_float(metrics.get("avgCapitalGain"))
    if gain > 15: pts = 15
    elif gain > 10: pts = 12
    elif gain > 5: pts = 10
    elif gain > 0: pts = 7
    else: pts = 2
    score += pts
    breakdown["capitalGain"] = pts

    # Rental Demand (10 pts)
    rent_contracts = safe_int(metrics.get("totalRentContracts"))
    if rent_contracts > 500: pts = 10
    elif rent_contracts > 200: pts = 8
    elif rent_contracts > 50: pts = 6
    elif rent_contracts > 10: pts = 4
    else: pts = 2
    score += pts
    breakdown["rentalDemand"] = pts

    # Sales Volume (10 pts)
    sales = safe_int(metrics.get("salesCount"))
    if sales > 200: pts = 10
    elif sales > 100: pts = 8
    elif sales > 50: pts = 6
    elif sales > 10: pts = 4
    else: pts = 2
    score += pts
    breakdown["salesVolume"] = pts

    # Construction Quality from LLM (10 pts)
    quality = safe_float(qualitative.get("constructionQuality"), 5)
    pts = int(quality)
    score += pts
    breakdown["constructionQuality"] = pts

    # Market Reputation from LLM (10 pts)
    reputation = safe_float(qualitative.get("marketReputation"), 5)
    pts = int(reputation)
    score += pts
    breakdown["marketReputation"] = pts

    final_score = min(100, max(0, score))
    return final_score, breakdown


def run():
    print("[Developer Engine] Starting...")
    projects = load_json(PROJECTS_JSON)
    existing_devs = load_existing_developers()
    dxb_data = load_dxb_data()
    delivery_data = load_delivery_data()
    google_reviews = load_google_reviews()

    # Compute local metrics from projects
    dev_projects: dict[str, list[dict]] = defaultdict(list)
    for p in projects:
        dev = match_developer(p["name"])
        dev_projects[dev].append(p)

    results = []
    for dev_name, projs in dev_projects.items():
        if dev_name == "Independent / Other":
            continue

        # Local metrics
        ready = sum(1 for p in projs if safe_float(p.get("avg_price")) > 0)
        yields = [safe_float(p.get("rental_yield_pct")) for p in projs if p.get("rental_yield_pct")]
        avg_yield = sum(yields) / len(yields) if yields else 0
        price_changes = [safe_float(p.get("price_change_pct")) for p in projs if p.get("price_change_pct") is not None]
        avg_gain = sum(price_changes) / len(price_changes) if price_changes else 0
        rent_counts = [safe_int(p.get("rent_count")) for p in projs]
        total_rent = sum(rent_counts)

        metrics = {
            "totalProjects": len(projs),
            "readyProjects": ready,
            "avgCapitalGain": round(avg_gain, 2),
            "avgRentalYield": round(avg_yield, 2),
            "totalRentContracts": total_rent,
            "salesCount": 0,
            "salesValue": 0,
        }

        # Merge DXB data
        dxb = dxb_data.get(dev_name, {})
        if dxb:
            metrics["totalProjects"] = safe_int(dxb.get("totalProjects"), metrics["totalProjects"])
            metrics["readyProjects"] = safe_int(dxb.get("deliveredProjects"), ready)
            metrics["salesCount"] = safe_int(dxb.get("ytdTransactions"))
            metrics["salesValue"] = safe_int(dxb.get("totalValueAED"))
            metrics["underConstruction"] = safe_int(dxb.get("underConstructionProjects"))
            metrics["totalUnits"] = safe_int(dxb.get("totalUnits"))

        # Merge Google reviews
        google = google_reviews.get(dev_name, {})
        google_rating = safe_float(google.get("rating")) if google else None
        google_review_count = safe_int(google.get("reviewCount")) if google else None

        # Delivery delay from real data
        uc = safe_int(dxb.get("underConstructionProjects"))
        total_p = safe_int(dxb.get("totalProjects"), len(projs))
        if total_p > 0 and uc > 0:
            delay_pct = round((uc / total_p) * 100, 1)
        elif ready > 0 and total_p > 0:
            delay_pct = round(((total_p - ready) / total_p) * 100, 1)
        else:
            delay_pct = 50

        if delay_pct < 30:
            delay_risk = "Low"
        elif delay_pct < 50:
            delay_risk = "Medium"
        else:
            delay_risk = "High"

        # LLM qualitative
        existing = next((d for d in existing_devs if d["name"] == dev_name), {})
        qualitative = {}
        if existing:
            qualitative = {
                "constructionQuality": existing.get("constructionQuality", 5),
                "marketReputation": existing.get("marketReputation", 5),
                "buyerConfidence": existing.get("buyerConfidence", "Average"),
                "marketPosition": existing.get("marketPosition", "Tier 3"),
                "summary": existing.get("summary", ""),
            }

        # Try LLM for missing
        if not qualitative.get("constructionQuality"):
            qualitative = llm_qualitative(dev_name, metrics)

        # Fallback heuristics
        if not qualitative.get("constructionQuality"):
            score_heuristic = 50
            if len(projs) > 20: score_heuristic += 15
            elif len(projs) > 10: score_heuristic += 10
            if avg_gain > 10: score_heuristic += 10
            qualitative = {
                "constructionQuality": 9 if score_heuristic >= 80 else 7 if score_heuristic >= 70 else 5,
                "marketReputation": 9 if score_heuristic >= 80 else 7 if score_heuristic >= 70 else 5,
                "buyerConfidence": "Excellent" if score_heuristic >= 80 else "Good" if score_heuristic >= 70 else "Average",
                "marketPosition": "Tier 1" if score_heuristic >= 80 else "Tier 2" if score_heuristic >= 65 else "Tier 3",
                "summary": f"Automated assessment based on {len(projs)} projects, {avg_gain}% capital gain.",
            }

        qualitative["deliveryDelayPercent"] = delay_pct
        qualitative["deliveryDelayRisk"] = delay_risk

        # Compute score
        dev_score, dev_breakdown = compute_developer_score(metrics, qualitative)

        # Ensure market reputation is consistent with developer score
        # If LLM gave a value that's inconsistent with the actual score, derive from score
        llm_reputation = safe_int(qualitative.get("marketReputation"), 5)
        expected_reputation = round(dev_score / 10)  # 71 → 7, 85 → 9, 50 → 5
        if abs(llm_reputation - expected_reputation) > 2:
            qualitative["marketReputation"] = expected_reputation
        # Also ensure construction quality is consistent
        llm_quality = safe_int(qualitative.get("constructionQuality"), 5)
        expected_quality = round(dev_score / 10)
        if abs(llm_quality - expected_quality) > 2:
            qualitative["constructionQuality"] = expected_quality

        # Google rating → customerReviews
        customer_reviews = round(google_rating * 2, 1) if google_rating else safe_float(qualitative.get("customerReviews"), 5)

        entry = {
            "name": dev_name,
            "developerScore": dev_score,
            "scoreBreakdown": dev_breakdown,
            "projectsDelivered": metrics["readyProjects"],
            "projectsUnderConstruction": safe_int(dxb.get("underConstructionProjects")),
            "totalProjects": metrics["totalProjects"],
            "totalUnits": safe_int(dxb.get("totalUnits")),
            "delayedProjects": delay_pct,
            "deliveryDelayRisk": delay_risk,
            "avgResalePremium": round(avg_gain, 2),
            "capitalGainAED": safe_int(dxb.get("capitalGainAED")),
            "capitalGainStr": dxb.get("capitalGainStr", ""),
            "buyerConfidence": qualitative.get("buyerConfidence", "Average"),
            "marketPosition": qualitative.get("marketPosition", "Tier 3"),
            "constructionQuality": safe_int(qualitative.get("constructionQuality"), 5),
            "customerReviews": customer_reviews,
            "googleRating": google_rating,
            "googleReviewCount": google_review_count,
            "marketReputation": safe_int(qualitative.get("marketReputation"), 5),
            "salesCount": metrics["salesCount"],
            "salesValue": metrics["salesValue"],
            "salesValueStr": dxb.get("totalValueStr", ""),
            "avgRentalYield": metrics["avgRentalYield"],
            "totalRentContracts": metrics["totalRentContracts"],
            "areasCovered": list(set(p.get("area", "") for p in projs if p.get("area"))),
            "projectNames": [p["name"] for p in projs],
            "aliases": DEVELOPER_KEYWORDS.get(dev_name, []),
            "summary": qualitative.get("summary", ""),
            "dataSource": "DXBInteract + Google + DLD" if dxb else "DLD local",
            "computedAt": datetime.now().isoformat(),
        }
        results.append(entry)

    results.sort(key=lambda x: -x["developerScore"])
    save_json(DEVELOPER_SCORES_FILE, results)
    print(f"[Developer Engine] Computed {len(results)} developer scores")
    return results


if __name__ == "__main__":
    run()
