#!/usr/bin/env python3
"""
Merge dxb_project_stats.csv into the synced JSON to add service_charge
and fill any missing fields. Matches by slug.
"""
import json
import csv
import sys

JSON_PATH = sys.argv[1] if len(sys.argv) > 1 else "src/data/dxb_projects_synced.json"
CSV_PATH = sys.argv[2] if len(sys.argv) > 2 else "../dxb_project_stats.csv"

# Load JSON
with open(JSON_PATH) as f:
    projects = json.load(f)

# Load CSV
stats = {}
with open(CSV_PATH) as f:
    reader = csv.DictReader(f)
    for row in reader:
        slug = row.get("slug", "").strip()
        if slug:
            stats[slug] = row

print(f"JSON projects: {len(projects)}", file=sys.stderr)
print(f"CSV stats: {len(stats)}", file=sys.stderr)

# Build slug index for JSON
by_slug = {}
for p in projects:
    by_slug[p.get("slug", "")] = p

# Merge
matched = 0
for slug, csv_row in stats.items():
    if slug in by_slug:
        proj = by_slug[slug]
        matched += 1

        # Fill service_charge
        sc = csv_row.get("service_charge", "").strip()
        if sc and not proj.get("service_charge"):
            try:
                proj["service_charge"] = float(sc)
            except ValueError:
                pass

        # Fill sales_volume if missing
        sc_count = csv_row.get("sales_count", "").strip()
        if sc_count:
            try:
                csv_count = int(sc_count)
                if not proj.get("sales_volume") or csv_count > proj["sales_volume"]:
                    proj["sales_volume"] = csv_count
            except ValueError:
                pass

        # Fill rent_count
        rc = csv_row.get("rent_count", "").strip()
        if rc:
            try:
                proj.setdefault("rent_count", int(rc))
            except ValueError:
                pass

        # Fill avg_rent if missing
        avg_rent = csv_row.get("avg_rent", "").strip()
        if avg_rent and not proj.get("avg_rent"):
            try:
                proj["avg_rent"] = float(avg_rent)
            except ValueError:
                pass

        # Fill rental_yield_pct if missing
        ry = csv_row.get("rental_yield_pct", "").strip()
        if ry and not proj.get("rental_yield_pct"):
            try:
                proj["rental_yield_pct"] = float(ry)
            except ValueError:
                pass

        # Fill rent_change_pct if missing
        rcp = csv_row.get("rent_change_pct", "").strip()
        if rcp and not proj.get("rent_change_pct"):
            try:
                proj["rent_change_pct"] = float(rcp)
            except ValueError:
                pass

print(f"Matched & merged: {matched}", file=sys.stderr)

# Output merged JSON
print(json.dumps(projects, indent=2, ensure_ascii=False))
