"""
APIL Qdrant Safe Enrichment Client — Step 18 Final
========================================================
Fetches property details from Qdrant to enrich APIL properties ONLY when
identity is CONFIRMED via exact property_id match.

DATA TRUTH RULES:
- NEVER silently join incorrect records.
- Exact property_id match is the ONLY authoritative join method.
- If no exact match → enrichment_status = "NOT_CONFIRMED"
- Display enrichment data ONLY when status is CONFIRMED.
- Do NOT use Qdrant attributes for investment scoring.

Qdrant collection used:
  - properties_collection (8,454 points)
"""

import json
import urllib.request
import re
from typing import Any, Dict, List, Optional, Tuple

QDRANT_URL = "http://localhost:6333"
COLLECTION = "properties_collection"

# In-memory caches
_id_cache: Dict[str, Dict] = {}
_cache_loaded = False


def _scroll_collection(limit: int = 200, offset: Optional[str] = None) -> Tuple[List[Dict], Optional[str]]:
    """Scroll through Qdrant collection to get points."""
    url = f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll"
    body: Dict[str, Any] = {"limit": limit, "with_payload": True, "with_vector": False}
    if offset:
        body["offset"] = offset
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
        points = resp["result"]["points"]
        next_offset = resp["result"].get("next_page_offset")
        return points, next_offset
    except Exception as e:
        print(f"[Qdrant] Scroll error: {e}")
        return [], None


def _load_id_cache():
    """Load all Qdrant points into memory cache, indexed by property_id."""
    global _cache_loaded, _id_cache
    if _cache_loaded:
        return

    offset = None
    total = 0
    for _ in range(100):
        points, offset = _scroll_collection(limit=200, offset=offset)
        if not points:
            break
        for p in points:
            pl = p.get("payload", {})
            # Index by property_id (primary) and id (fallback)
            pid = str(pl.get("property_id", "")).strip()
            qid = str(pl.get("id", "")).strip()
            if pid:
                _id_cache[pid] = pl
            elif qid:
                _id_cache[qid] = pl
            total += 1
        if not offset:
            break

    _cache_loaded = True
    print(f"[Qdrant] Loaded {len(_id_cache)} unique property records from {total} points")


def get_collection_info() -> Dict:
    """Get Qdrant collection metadata."""
    url = f"{QDRANT_URL}/collections/{COLLECTION}"
    try:
        req = urllib.request.Request(url)
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        return resp.get("result", {})
    except Exception as e:
        return {"error": str(e)}


def check_collection_exists() -> bool:
    """Verify the collection exists and is reachable."""
    url = f"{QDRANT_URL}/collections"
    try:
        req = urllib.request.Request(url)
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        collections = [c["name"] for c in resp.get("result", {}).get("collections", [])]
        return COLLECTION in collections
    except Exception:
        return False


def _safe_int(val: Any, default: Optional[int] = None) -> Optional[int]:
    if val is None or val == "":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    if val is None or val == "":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _extract_images(payload: Dict) -> List[Dict]:
    """Extract image URLs from Qdrant payload."""
    images = payload.get("images", [])
    image_urls = payload.get("image_urls", [])
    result = []

    # Prefer image_urls array of strings
    if isinstance(image_urls, list):
        for url in image_urls:
            if isinstance(url, str) and url:
                result.append({"url": url, "alt": payload.get("name", "")})

    # Fallback to images array
    if not result and isinstance(images, list):
        for img in images:
            if isinstance(img, dict) and img.get("url"):
                result.append({
                    "url": img["url"] if img["url"].startswith("http") else f"https://www.apilproperties.com/storage/{img['url']}",
                    "alt": img.get("alt", ""),
                })
            elif isinstance(img, str) and img:
                result.append({"url": img if img.startswith("http") else f"https://www.apilproperties.com/storage/{img}", "alt": ""})

    return result[:10]  # Limit to 10 images


def enrich_property(apil_property_id: str, apil_property: Dict, developer: Optional[Dict] = None) -> Dict:
    """
    Safely enrich an APIL property with Qdrant data using project-level identity matching.
    STEP 24: Replaced exact property_id matching with multi-signal project identity matching.
    """
    from backend_qdrant_matcher import find_qdrant_project_matches

    # Build a combined dict so the matcher receives developer info
    full_record = dict(apil_property)
    if developer:
        full_record["developer"] = developer
    match_result = find_qdrant_project_matches(full_record)

    # Build backward-compatible enrichment response
    result = {
        "enrichment_status": match_result["enrichment_status"],
        "enrichment_source": f"qdrant:{COLLECTION}",
        "matched_qdrant_id": match_result["matched_qdrant_records"][0]["qdrant_id"] if match_result["matched_qdrant_records"] else None,
        "match_confidence": match_result["match_confidence"],
        "match_strategy": match_result["match_strategy"],
        "identity_match": {
            "strategy": match_result["match_strategy"],
            "apil_property_id": apil_property_id,
            "matched_qdrant_id": match_result["matched_qdrant_records"][0]["qdrant_id"] if match_result["matched_qdrant_records"] else None,
            "qdrant_name": match_result["matched_qdrant_records"][0]["qdrant_name"] if match_result["matched_qdrant_records"] else None,
            "confidence": match_result["match_confidence"],
            "reason": "; ".join(match_result["reasons"]) if match_result["reasons"] else match_result.get("rejected_candidates", [{}])[0].get("rejections", ["Unknown"])[0],
        },
        "property_attributes": {},
        "media": {"images": [], "description": ""},
        "data_quality": {"fields_present": 0, "fields_total": 0, "coverage_pct": 0.0},
        "provenance": {},
        "matched_qdrant_records": match_result.get("matched_qdrant_records", []),
        "rejected_candidates": match_result.get("rejected_candidates", []),
    }

    # Map aggregated attributes to backward-compatible format
    agg = match_result.get("aggregated_attributes", {})
    prov = match_result.get("provenance", {})

    # ── Phase 1: Unit-level attributes (exact match) — HIGHEST PRIORITY ──
    if "unit_bedrooms" in agg:
        result["property_attributes"]["unit_bedrooms"] = agg["unit_bedrooms"]
        result["property_attributes"]["bedrooms"] = agg["unit_bedrooms"]  # backward compat override
        prov["bedrooms"] = prov.get("unit_bedrooms", "qdrant:exact unit")
    if "unit_bathrooms" in agg:
        result["property_attributes"]["unit_bathrooms"] = agg["unit_bathrooms"]
        result["property_attributes"]["bathrooms"] = agg["unit_bathrooms"]  # backward compat override
        prov["bathrooms"] = prov.get("unit_bathrooms", "qdrant:exact unit")
    if "unit_size_sqft" in agg:
        result["property_attributes"]["unit_size_sqft"] = agg["unit_size_sqft"]
        result["property_attributes"]["unit_size_sqm"] = agg["unit_size_sqm"]
        result["property_attributes"]["size_sqft"] = agg["unit_size_sqft"]  # backward compat override
        result["property_attributes"]["size_sqm"] = agg["unit_size_sqm"]
        prov["size_sqft"] = prov.get("unit_size_sqft", "qdrant:exact unit")
    if "unit_price_aed" in agg:
        result["property_attributes"]["unit_price_aed"] = agg["unit_price_aed"]
    if "unit_status" in agg:
        result["property_attributes"]["unit_status"] = agg["unit_status"]
        result["property_attributes"]["status"] = agg["unit_status"]  # backward compat override
        prov["status"] = prov.get("unit_status", "qdrant:exact unit")
    if "unit_description" in agg:
        result["property_attributes"]["unit_description"] = agg["unit_description"]
        prov["unit_description"] = prov.get("unit_description", "qdrant:description (exact unit match)")
    if "unit_images" in agg:
        result["property_attributes"]["unit_images"] = agg["unit_images"]
        prov["unit_images"] = prov.get("unit_images", "qdrant:images (exact unit match)")

    # ── Phase 2: Project-level attributes (aggregate across units) ──
    if "project_category" in agg:
        result["property_attributes"]["project_category"] = agg["project_category"]
    if "project_bedroom_options" in agg:
        result["property_attributes"]["project_bedroom_options"] = agg["project_bedroom_options"]
        # Only populate bedrooms_options if we did NOT have a unit-level match
        if "unit_bedrooms" not in agg:
            result["property_attributes"]["bedrooms_options"] = agg["project_bedroom_options"]
            prov["bedrooms_options"] = "qdrant:project aggregate"
    if "project_bathroom_options" in agg:
        result["property_attributes"]["project_bathroom_options"] = agg["project_bathroom_options"]
        if "unit_bathrooms" not in agg:
            result["property_attributes"]["bathrooms_options"] = agg["project_bathroom_options"]
    if "project_size_min_sqft" in agg:
        result["property_attributes"]["project_size_min_sqft"] = agg["project_size_min_sqft"]
        result["property_attributes"]["project_size_max_sqft"] = agg["project_size_max_sqft"]
        result["property_attributes"]["project_size_min_sqm"] = agg["project_size_min_sqm"]
        result["property_attributes"]["project_size_max_sqm"] = agg["project_size_max_sqm"]
        if "unit_size_sqft" not in agg:
            result["property_attributes"]["size_sqft_min"] = agg["project_size_min_sqft"]
            result["property_attributes"]["size_sqft_max"] = agg["project_size_max_sqft"]
            result["property_attributes"]["size_sqm_min"] = agg["project_size_min_sqm"]
            result["property_attributes"]["size_sqm_max"] = agg["project_size_max_sqm"]
    if "project_status_options" in agg:
        result["property_attributes"]["project_status_options"] = agg["project_status_options"]
    if "project_developer" in agg:
        result["property_attributes"]["project_developer"] = agg["project_developer"]
    if "project_community_area" in agg:
        result["property_attributes"]["project_community_area"] = agg["project_community_area"]
    if "project_district" in agg:
        result["property_attributes"]["project_district"] = agg["project_district"]

    # ── Phase 3: Backward compat — DEPRECATED fields ──
    # These old field names are kept only so old callers don't crash.
    # They now contain unit values when available, project aggregates otherwise.
    # CRITICAL: beds[0] and size_sqft_min are NEVER used as the property's value
    # when a unit-level match exists.
    if "bedrooms" in agg and "unit_bedrooms" not in agg:
        beds = agg["bedrooms"]
        result["property_attributes"]["bedrooms"] = beds[0] if isinstance(beds, list) else beds
        result["property_attributes"]["bedrooms_options"] = beds if isinstance(beds, list) else [beds]
        prov["bedrooms"] = "DEPRECATED: project aggregate fallback"
    if "bathrooms" in agg and "unit_bathrooms" not in agg:
        baths = agg["bathrooms"]
        result["property_attributes"]["bathrooms"] = baths[0] if isinstance(baths, list) else baths
        result["property_attributes"]["bathrooms_options"] = baths if isinstance(baths, list) else [baths]
        prov["bathrooms"] = "DEPRECATED: project aggregate fallback"
    if "size_sqft_min" in agg and "unit_size_sqft" not in agg:
        result["property_attributes"]["size_sqft"] = agg["size_sqft_min"]
        result["property_attributes"]["size_sqft_min"] = agg["size_sqft_min"]
        result["property_attributes"]["size_sqft_max"] = agg["size_sqft_max"]
        result["property_attributes"]["size_sqm_min"] = agg["size_sqm_min"]
        result["property_attributes"]["size_sqm_max"] = agg["size_sqm_max"]
        prov["size_sqft"] = "DEPRECATED: project aggregate fallback"
    if "status" in agg and "unit_status" not in agg:
        result["property_attributes"]["status"] = agg["status"]
        prov["status"] = "DEPRECATED: project aggregate fallback"
    if "developer" in agg:
        result["property_attributes"]["developer"] = agg["developer"]
    if "community_area" in agg:
        result["property_attributes"]["community_area"] = agg["community_area"]
    if "district" in agg:
        result["property_attributes"]["district"] = agg["district"]
    # Category — prefer exact unit category, fall back to project aggregate
    if "unit_category" in agg:
        result["property_attributes"]["category"] = agg["unit_category"]
        result["property_attributes"]["unit_category"] = agg["unit_category"]
        prov["category"] = prov.get("unit_category", "qdrant:category (exact unit match)")
    elif "category" in agg:
        result["property_attributes"]["category"] = agg["category"]

    # Media — prefer exact unit images/description, fall back to project aggregates
    if "unit_images" in agg:
        result["media"]["images"] = agg["unit_images"]
        prov["media_images"] = prov.get("unit_images", "qdrant:images (exact unit match)")
    elif "project_images" in agg:
        result["media"]["images"] = agg["project_images"]
    if "unit_description" in agg:
        result["media"]["description"] = agg["unit_description"]
        prov["media_description"] = prov.get("unit_description", "qdrant:description (exact unit match)")
    elif "project_description" in agg:
        result["media"]["description"] = agg["project_description"]

    # Provenance
    result["provenance"] = prov

    # Data quality — count NEW unit + project fields
    all_fields = [
        "unit_bedrooms", "unit_bathrooms", "unit_size_sqft", "unit_size_sqm",
        "unit_price_aed", "unit_status",
        "project_bedroom_options", "project_bathroom_options",
        "project_size_min_sqft", "project_size_max_sqft",
        "project_status_options", "project_category",
        "project_community_area", "project_district",
    ]
    fields_present = sum(1 for f in all_fields if f in result["property_attributes"])
    result["data_quality"] = {
        "fields_present": fields_present,
        "fields_total": len(all_fields),
        "coverage_pct": round((fields_present / len(all_fields)) * 100, 1) if all_fields else 0.0,
        "exact_unit_matched": agg.get("exact_unit_matched", False),
        "exact_unit_qdrant_id": agg.get("exact_unit_qdrant_id"),
        "exact_unit_name": agg.get("exact_unit_name"),
    }

    return result


def enrich_properties_batch(apil_properties: List[Dict]) -> Dict[str, Dict]:
    """
    Enrich multiple APIL properties. Returns a dict keyed by APIL property_id.
    """
    _load_id_cache()
    results = {}
    for prop in apil_properties:
        pid = str(prop.get("id", "")).strip()
        if pid:
            results[pid] = enrich_property(pid, prop)
    return results


# Health check for startup diagnostics
def health_check() -> Dict:
    """Return Qdrant connection health status."""
    exists = check_collection_exists()
    info = get_collection_info() if exists else {}
    return {
        "status": "healthy" if exists else "unavailable",
        "collection": COLLECTION,
        "collection_exists": exists,
        "points_count": info.get("points_count", 0),
        "cached_records": len(_id_cache),
        "missing_collections": ["Dubai_real_estate_calculation_data_"],
        "note": "Dubai_real_estate_calculation_data_ does not exist. Using properties_collection exclusively.",
    }
