#!/usr/bin/env python3
"""
Export all properties from Qdrant directly and convert to dxb_projects.json format.
Much faster than paginating through the API.
"""

import json
import sys
import requests
from collections import defaultdict

QDRANT_URL = "http://localhost:6333"
COLLECTION = "properties_collection"

def scroll_all_points():
    """Scroll through all Qdrant points to get all property data."""
    all_points = []
    offset = None

    while True:
        payload = {
            "limit": 100,
            "with_payload": True,
            "with_vector": False,
        }
        if offset:
            payload["offset"] = offset

        resp = requests.post(
            f"{QDRANT_URL}/collections/{COLLECTION}/points/scroll",
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()["result"]

        points = data.get("points", [])
        if not points:
            break

        all_points.extend(points)
        print(f"  Fetched {len(all_points)} points so far...", file=sys.stderr)

        offset = data.get("next_page_offset")
        if not offset:
            break

    print(f"  Total: {len(all_points)} points", file=sys.stderr)
    return all_points


def normalize_bedrooms(bedrooms):
    if not bedrooms:
        return "Unknown"
    s = str(bedrooms).strip().lower()
    if "studio" in s:
        return "Studio"
    if "1" in s:
        return "1 B/R"
    if "2" in s:
        return "2 B/R"
    if "3" in s:
        return "3 B/R"
    if "4" in s:
        return "4 B/R"
    if "5" in s:
        return "5 B/R"
    return "Unknown"


def convert_to_project_data(points):
    """Convert Qdrant points to ProjectData[] format."""
    projects = defaultdict(lambda: {
        "name": None,
        "area": None,
        "slug": None,
        "url": None,
        "scraped_at": None,
        "avg_price": None,
        "avg_price_sqft": None,
        "price_change_pct": None,
        "avg_rent": None,
        "rent_change_pct": None,
        "rental_yield_pct": None,
        "sales_volume": None,
        "service_charge": None,
        "sales_history": [],
        "rent_history": [],
        "_property_count": 0,
    })

    for point in points:
        payload = point.get("payload", {})

        # Extract property info from Qdrant payload
        prop_id = payload.get("property_id", payload.get("id", ""))
        title = payload.get("name", payload.get("meta_title", ""))
        community = payload.get("community_area", "Unknown")
        project_name = payload.get("project_name") or title.split("|")[0].strip()
        bedrooms = payload.get("bedroom_norm", payload.get("bedroom", ""))
        listing_price = payload.get("listing_price", payload.get("price", 0))
        size_sqft = payload.get("size_sqft", payload.get("size_sq_ft", 0))
        price_per_sqft = payload.get("display_price_rate", 0)

        investment_score = payload.get("investment_score", 0)
        roi = payload.get("gross_yield", payload.get("roi", 0))
        capital_appreciation = payload.get("capital_appreciation", 0)
        median_rent = payload.get("median_annual_rent", 0)
        transaction_count = payload.get("transaction_count", 0)
        price_vs_market = payload.get("price_vs_market_pct")

        proj = projects[project_name]
        proj["name"] = project_name
        proj["area"] = community
        proj["slug"] = project_name.lower().replace(" ", "-").replace("/", "-")
        proj["url"] = f"https://dxbinteract.com/projects/{proj['slug']}"
        proj["_property_count"] += 1

        if capital_appreciation:
            proj["price_change_pct"] = capital_appreciation
        if roi:
            proj["rental_yield_pct"] = roi
        if median_rent:
            proj["avg_rent"] = median_rent
        if transaction_count:
            proj["sales_volume"] = max(proj["sales_volume"] or 0, transaction_count)

        # Build sales history from price_trend if available
        price_trend = payload.get("price_trend", [])
        for trend in price_trend:
            proj["sales_history"].append({
                "date": trend.get("date", ""),
                "price": 0,
                "price_sqft": trend.get("price", 0),
                "beds": normalize_bedrooms(bedrooms),
                "area_sqft": size_sqft,
            })

        # Build sales history from sold_price_by_year
        sold_by_year = payload.get("sold_price_by_year", [])
        for sold in sold_by_year:
            year = sold.get("year", "")
            avg_price = sold.get("avg_sold_price", 0)
            avg_pps = sold.get("avg_pps", 0)
            if avg_price and avg_price > 0:
                proj["sales_history"].append({
                    "date": f"{year}-01-01 00:00:00",
                    "price": avg_price,
                    "price_sqft": avg_pps,
                    "beds": normalize_bedrooms(bedrooms),
                    "area_sqft": size_sqft,
                })

        # Build rent history
        if median_rent and median_rent > 0:
            proj["rent_history"].append({
                "date": "2026-01-01",
                "annual_rent": median_rent,
                "beds": normalize_bedrooms(bedrooms),
                "area_sqft": size_sqft,
            })

    # Finalize: calculate averages, remove internal fields
    result = []
    for key, proj in projects.items():
        if not proj["sales_history"] and not proj["rent_history"]:
            continue

        prices = [s["price"] for s in proj["sales_history"] if s["price"] and s["price"] > 0]
        prices_sqft = [s["price_sqft"] for s in proj["sales_history"] if s["price_sqft"] and s["price_sqft"] > 0]

        if prices:
            proj["avg_price"] = sum(prices) // len(prices)
        if prices_sqft:
            proj["avg_price_sqft"] = sum(prices_sqft) // len(prices_sqft)

        del proj["_property_count"]
        result.append(proj)

    return result


def main():
    print("Scrolling all Qdrant points...", file=sys.stderr)
    points = scroll_all_points()

    print("Converting to project data format...", file=sys.stderr)
    project_data = convert_to_project_data(points)

    print(f"Generated {len(project_data)} projects", file=sys.stderr)
    output = json.dumps(project_data, indent=2, ensure_ascii=False)
    print(output)


if __name__ == "__main__":
    main()
