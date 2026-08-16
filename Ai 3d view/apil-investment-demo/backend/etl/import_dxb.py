"""
ETL: Import DXBInteract scraped developer data.
Loads pre-scraped developer metrics from server scrapers.
"""
from __future__ import annotations

import json
import urllib.request
import re
from typing import Any

from config.settings import DXB_BASE, save_json, BACKEND_DATA_DIR

DEVELOPER_SLUGS = {
    "Emaar Properties": "emaar-properties",
    "Damac Properties": "damac-properties",
    "Binghatti": "binghatti",
    "Danube Properties": "danube-properties",
    "Nakheel": "nakheel",
    "Meraas": "meraas",
    "Dubai Properties": "dubai-properties",
    "MAG Group": "mag",
    "Aldar Properties": "aldar",
    "Azizi Developments": "azizi-developments",
    "Ellington Properties": "ellington",
    "Deyaar": "deyaar",
    "Select Group": "select-group",
    "Tiger Properties": "tiger-properties",
    "Al Futtaim": "majid-al-futtaim",
    "Dubai South": "dubai-south",
    "Diamond Developers": "diamond-developers",
}


def scrape_developer(slug: str) -> dict:
    url = f"{DXB_BASE}/{slug}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        metrics: dict[str, Any] = {}

        m = re.search(r"Sales Volume[^0-9]*(\d+)", html)
        if m: metrics["ytdTransactions"] = int(m.group(1))
        m = re.search(r"Sales Value[^0-9]*(\d[\d,]*)", html)
        if m: metrics["totalValueAED"] = int(m.group(1).replace(",", ""))
        m = re.search(r"Projects[^0-9]*(\d+)", html)
        if m: metrics["totalProjects"] = int(m.group(1))
        m = re.search(r"Absorption Rate[^0-9]*([\d.]+)", html)
        if m: metrics["absorptionRate"] = float(m.group(1))
        m = re.search(r"Capital Gain[^0-9]*([\d.]+)", html)
        if m: metrics["capitalGainPct"] = float(m.group(1))

        return metrics
    except Exception as e:
        print(f"  [WARN] Failed to scrape {slug}: {e}")
        return {}


def import_dxb_local() -> list[dict]:
    """Load pre-scraped DXB data from server files."""
    results = []
    import os
    for fname in ["dev_dxb_real_v2.json", "dev_dxb_real.json"]:
        path = os.path.join("/tmp", fname)
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            for dev_name, metrics in data.items():
                results.append({"developer": dev_name, **metrics})
            print(f"  Loaded {len(results)} developers from {fname}")
            break

    if not results:
        print("  [WARN] No pre-scraped DXB data found. Scraping live...")
        for dev_name, slug in DEVELOPER_SLUGS.items():
            metrics = scrape_developer(slug)
            if metrics:
                results.append({"developer": dev_name, **metrics})

    return results


def import_delivery_data() -> dict:
    """Load delivery rankings from server."""
    import os
    path = os.path.join("/tmp", "dev_delivery_real.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def run():
    print("[ETL] Importing DXBInteract data...")
    dxb_data = import_dxb_local()
    delivery_data = import_delivery_data()

    result = {
        "developers": dxb_data,
        "delivery": delivery_data,
        "imported_at": __import__("datetime").datetime.now().isoformat(),
    }
    save_json(BACKEND_DATA_DIR / "dxb_warehouse.json", result)
    print(f"[ETL] DXB warehouse saved: {len(dxb_data)} developers, {len(delivery_data)} delivery records")
    return result


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    run()
