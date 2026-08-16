#!/usr/bin/env python3
"""
Export synced property data from the production API and convert it
into the dxb_projects.json format that the demo's scoring engine expects.

Fetches all properties with their analysis (DLD-matched transaction + rent data)
from the investment API, groups by project/community, and outputs structured JSON.
"""

import requests
import json
import sys
from collections import defaultdict

API_BASE = "http://localhost:8052"
API_SEARCH = f"{API_BASE}/api/search"

def fetch_all_properties():
    """Fetch all properties from the API with their analysis data."""
    all_props = []
    page = 1
    per_page = 50  # API caps at 50 per page

    while True:
        print(f"  Fetching page {page}...", file=sys.stderr)
        resp = requests.get(API_SEARCH, params={
            "query": "",
            "page": page,
            "per_page": per_page
        }, timeout=(10, 60))
        resp.raise_for_status()
        data = resp.json()

        if not data or len(data) == 0:
            break

        all_props.extend(data)

        if len(data) < per_page:
            break

        page += 1

    print(f"  Total fetched: {len(all_props)} properties", file=sys.stderr)
    return all_props


def normalize_bedrooms(bedrooms):
    """Normalize bedroom string to match engine format."""
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


def convert_to_project_data(properties):
    """
    Convert API properties into the ProjectData[] format expected by the demo.

    Group by matched_project_name (or community if no match), then build
    sales_history and rent_history from the analysis data.
    """
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
        "_properties": [],
    })

    for item in properties:
        prop = item.get("property", {})
        analysis = item.get("analysis", {})

        community = prop.get("community", "Unknown")
        matched_project = analysis.get("matched_project_name") or prop.get("title", "").split("|")[0].strip()
        project_key = matched_project

        proj = projects[project_key]
        proj["name"] = matched_project
        proj["area"] = community
        proj["slug"] = matched_project.lower().replace(" ", "-").replace("/", "-")
        proj["url"] = f"https://dxbinteract.com/projects/{proj['slug']}"

        # Use analysis data for aggregate stats
        if analysis.get("capital_appreciation"):
            proj["price_change_pct"] = analysis["capital_appreciation"]

        if analysis.get("gross_yield"):
            proj["rental_yield_pct"] = analysis["gross_yield"]

        if analysis.get("median_annual_rent"):
            proj["avg_rent"] = analysis["median_annual_rent"]

        if analysis.get("transaction_count"):
            proj["sales_volume"] = analysis["transaction_count"]

        # Build sales_history from price_trend
        price_trend = analysis.get("price_trend", [])
        for trend in price_trend:
            proj["sales_history"].append({
                "date": trend.get("date", ""),
                "price": 0,  # We have price_sqft, not absolute price
                "price_sqft": trend.get("price", 0),
                "beds": normalize_bedrooms(prop.get("bedrooms")),
                "area_sqft": prop.get("size_sqft"),
            })

        # Build sales_history from sold_price_by_year
        sold_by_year = analysis.get("sold_price_by_year", [])
        for sold in sold_by_year:
            year = sold.get("year", "")
            avg_price = sold.get("avg_sold_price", 0)
            avg_pps = sold.get("avg_pps", 0)
            total_sold = sold.get("total_units_sold", 0)

            # Add one representative sale record per year
            if avg_price and avg_price > 0:
                proj["sales_history"].append({
                    "date": f"{year}-01-01 00:00:00",
                    "price": avg_price,
                    "price_sqft": avg_pps,
                    "beds": normalize_bedrooms(prop.get("bedrooms")),
                    "area_sqft": prop.get("size_sqft"),
                })

        # Build rent_history
        if analysis.get("median_annual_rent") and analysis["median_annual_rent"] > 0:
            proj["rent_history"].append({
                "date": "2026-01-01",
                "annual_rent": analysis["median_annual_rent"],
                "beds": normalize_bedrooms(prop.get("bedrooms")),
                "area_sqft": prop.get("size_sqft"),
            })

        # Store property for reference
        proj["_properties"].append({
            "id": prop.get("id"),
            "title": prop.get("title"),
            "listing_price": prop.get("listing_price"),
            "size_sqft": prop.get("size_sqft"),
            "price_per_sqft": prop.get("price_per_sqft"),
            "bedrooms": normalize_bedrooms(prop.get("bedrooms")),
            "investment_score": analysis.get("investment_score"),
            "roi": analysis.get("roi"),
            "capital_appreciation": analysis.get("capital_appreciation"),
            "price_vs_market_pct": analysis.get("price_vs_market_pct"),
            "transaction_count": analysis.get("transaction_count"),
            "matched_project_name": analysis.get("matched_project_name"),
            "fuzzy_match_score": analysis.get("fuzzy_match_score"),
        })

    # Calculate avg_price and avg_price_sqft from sales_history
    result = []
    for key, proj in projects.items():
        if not proj["sales_history"] and not proj["rent_history"]:
            # Skip projects with no transaction data
            continue

        prices = [s["price"] for s in proj["sales_history"] if s["price"] and s["price"] > 0]
        prices_sqft = [s["price_sqft"] for s in proj["sales_history"] if s["price_sqft"] and s["price_sqft"] > 0]

        if prices:
            proj["avg_price"] = sum(prices) // len(prices)
        if prices_sqft:
            proj["avg_price_sqft"] = sum(prices_sqft) // len(prices_sqft)

        # Remove internal field
        del proj["_properties"]

        result.append(proj)

    return result


def main():
    print("Fetching all properties from API...", file=sys.stderr)
    properties = fetch_all_properties()

    print("Converting to project data format...", file=sys.stderr)
    project_data = convert_to_project_data(properties)

    print(f"Generated {len(project_data)} projects", file=sys.stderr)
    output = json.dumps(project_data, indent=2, ensure_ascii=False)
    print(output)


if __name__ == "__main__":
    main()
