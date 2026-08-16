"""
APIL Qdrant Enrichment Client
Fetches property details (images, descriptions, payment plans, amenities) from Qdrant
to enrich the scored properties from the DLD-based recommendation engine.

Qdrant collections used:
  - Dubai_real_estate_calculation_data_ (4284 points) — rich property listings with images, ROI, payment plans
  - properties_collection (2706 points) — additional property listings

Matching strategy:
  1. Exact match on project_name (case-insensitive)
  2. If multiple matches, pick closest by bedroom type + price
"""
from __future__ import annotations

import json
import urllib.request
from typing import Any
from difflib import SequenceMatcher

QDRANT_URL = "http://localhost:6333"
COLLECTION = "Dubai_real_estate_calculation_data_"
FALLBACK_COLLECTION = "properties_collection"

# Cache for project -> Qdrant points mapping
_project_cache: dict[str, list[dict]] = {}
_cache_loaded = False


def _scroll_collection(collection: str, limit: int = 200, offset: str | None = None) -> tuple[list[dict], str | None]:
    """Scroll through Qdrant collection to get all points."""
    url = f"{QDRANT_URL}/collections/{collection}/points/scroll"
    body: dict[str, Any] = {"limit": limit, "with_payload": True, "with_vector": False}
    if offset:
        body["offset"] = offset
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
    points = resp["result"]["points"]
    next_offset = resp["result"].get("next_page_offset")
    return points, next_offset


def _load_project_cache():
    """Load all Qdrant points into memory cache, indexed by project_name (lowercase)."""
    global _cache_loaded, _project_cache
    if _cache_loaded:
        return

    offset = None
    for _ in range(50):
        points, offset = _scroll_collection(COLLECTION, limit=200, offset=offset)
        if not points:
            break
        for p in points:
            pl = p.get("payload", {})
            proj = (pl.get("project_name") or "").strip().lower()
            if proj:
                if proj not in _project_cache:
                    _project_cache[proj] = []
                _project_cache[proj].append(pl)
        if not offset:
            break

    _cache_loaded = True
    print(f"  [Qdrant] Cached {len(_project_cache)} projects from {sum(len(v) for v in _project_cache.values())} points")


def _normalize_bed(bed: str) -> str:
    """Normalize bedroom strings for matching."""
    b = bed.lower().strip()
    if "studio" in b:
        return "studio"
    if "1" in b:
        return "1br"
    if "2" in b:
        return "2br"
    if "3" in b:
        return "3br"
    if "4" in b or "5" in b or "6" in b:
        return "4br+"
    return b


def _pick_best_match(qdrant_points: list[dict], bed_type: str, price: float) -> dict | None:
    """From multiple Qdrant points for the same project, pick the best match by bedroom + price."""
    if not qdrant_points:
        return None
    if len(qdrant_points) == 1:
        return qdrant_points[0]

    target_bed = _normalize_bed(bed_type)
    scored = []
    for qp in qdrant_points:
        qp_bed = _normalize_bed(qp.get("bedroom_norm", "") or qp.get("bedroom", ""))
        qp_price = float(qp.get("price") or qp.get("listing_price") or 0)

        bed_score = 1.0 if qp_bed == target_bed else 0.0
        price_score = 0.0
        if price > 0 and qp_price > 0:
            diff = abs(qp_price - price) / max(price, 1)
            price_score = max(0, 1.0 - diff)

        total = bed_score * 0.7 + price_score * 0.3
        scored.append((total, qp))

    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


def enrich_property(prop: dict) -> dict:
    """
    Enrich a scored property with Qdrant data (images, description, payment plans, amenities).

    Args:
        prop: A property dict from ready_property_scores.json

    Returns:
        The same dict with added 'listingData' field containing Qdrant enrichment.
    """
    _load_project_cache()

    project = prop.get("project", "").strip().lower()
    bed_type = prop.get("bedType", "")
    price = float(prop.get("askingPrice", 0) or 0)

    # Try exact project match
    candidates = _project_cache.get(project, [])

    # Try fuzzy match if no exact match
    if not candidates and project:
        best_key = None
        best_score = 0
        for qk in _project_cache:
            score = SequenceMatcher(None, project, qk).ratio()
            if score > best_score:
                best_score = score
                best_key = qk
        if best_key and best_score > 0.75:
            candidates = _project_cache[best_key]

    if not candidates:
        return prop

    best = _pick_best_match(candidates, bed_type, price)
    if not best:
        return prop

    # Extract enrichment fields
    images = best.get("images", [])
    image_urls = []
    for img in images:
        if isinstance(img, dict) and img.get("url"):
            image_urls.append({
                "url": f"https://www.apilproperties.com/storage/{img['url']}",
                "alt": img.get("alt", ""),
            })
        elif isinstance(img, str):
            image_urls.append({"url": f"https://www.apilproperties.com/storage/{img}", "alt": ""})

    # Parse payment plans
    payment_plans = best.get("payment_plans", [])
    if isinstance(payment_plans, str):
        try:
            payment_plans = json.loads(payment_plans)
        except Exception:
            payment_plans = []

    # Parse highlights
    highlights = best.get("highlights", [])
    if isinstance(highlights, str):
        try:
            highlights = json.loads(highlights)
        except Exception:
            highlights = []

    # Parse features and amenities
    amenities = best.get("feature_and_amenities") or best.get("features_and_amenities", {})
    if isinstance(amenities, str):
        try:
            amenities = json.loads(amenities)
        except Exception:
            amenities = {}

    # Strip HTML from description
    description = best.get("description", "")
    if description:
        import re
        description = re.sub(r"<[^>]+>", "", description).strip()

    prop["listingData"] = {
        "name": best.get("name", ""),
        "slug": best.get("slug", ""),
        "description": description,
        "images": image_urls[:10],
        "paymentPlans": payment_plans,
        "highlights": highlights,
        "amenities": amenities,
        "developer": best.get("developer", ""),
        "latitude": best.get("latitude"),
        "longitude": best.get("longitude"),
        "floorPlanImage": best.get("floor_plan_image"),
        "virtualTourUrl": best.get("virtual_tour_url"),
        "videoId": best.get("video_id"),
        "canonicalUrl": best.get("canonical_url", ""),
        "sizeSqft": best.get("size_sq_ft") or best.get("size_sqft"),
        "noOfParking": best.get("no_of_parking"),
        "noOfBathroom": best.get("no_of_bathroom"),
        "roi": best.get("roi"),
        "grossYield": best.get("gross_yield"),
        "medianAnnualRent": best.get("median_annual_rent"),
        "capitalAppreciation": best.get("capital_appreciation"),
        "estimatedMarketValue": best.get("estimated_market_value"),
        "priceVsMarketPct": best.get("price_vs_market_pct"),
        "priceVsMarketLabel": best.get("price_vs_market_label"),
        "transactionCount": best.get("transaction_count"),
        "investmentScore": best.get("investment_score"),
        "investmentRating": best.get("investment_rating"),
        "whyThisProject": best.get("why_this_project"),
    }

    return prop


def enrich_recommendations(recs: dict, max_enrich: int = 10) -> dict:
    """
    Enrich the top N recommendations with Qdrant listing data.

    Args:
        recs: Recommendation response from generate_recommendations()
        max_enrich: How many top properties to enrich (default 10)

    Returns:
        The same recs dict with 'listingData' added to each recommendation.
    """
    _load_project_cache()

    for rec in recs.get("recommendations", [])[:max_enrich]:
        enrich_property(rec)

    return recs
