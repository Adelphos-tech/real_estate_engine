"""
ETL: Import DLD transaction data (sales + rentals).
Reads CSV files and normalizes into structured records.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from typing import Any

from config.settings import DLD_TRANSACTIONS_CSV, DLD_RENTS_CSV, PROJECTS_JSON, save_json, BACKEND_DATA_DIR


def import_dld_transactions() -> list[dict]:
    if not DLD_TRANSACTIONS_CSV.exists():
        print(f"  [WARN] DLD transactions CSV not found: {DLD_TRANSACTIONS_CSV}")
        return []

    transactions = []
    with open(DLD_TRANSACTIONS_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            transactions.append({
                "project": (row.get("PROJECT_EN") or "").strip(),
                "area": (row.get("AREA_EN") or "").strip(),
                "trans_value": float(row.get("TRANS_VALUE", 0) or 0),
                "trans_date": (row.get("TRANS_DATE") or "").strip(),
                "is_offplan": (row.get("IS_OFFPLAN_EN") or "").strip(),
                "property_type": (row.get("PROPERTY_TYPE_EN") or "").strip(),
                "rooms": (row.get("ROOMS_EN") or "").strip(),
            })
    print(f"  Imported {len(transactions)} DLD transactions")
    return transactions


def import_dld_rents() -> list[dict]:
    if not DLD_RENTS_CSV.exists():
        print(f"  [WARN] DLD rents CSV not found: {DLD_RENTS_CSV}")
        return []

    rents = []
    with open(DLD_RENTS_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rents.append({
                "project": (row.get("PROJECT_EN") or "").strip(),
                "area": (row.get("AREA_EN") or "").strip(),
                "annual_rent": float(row.get("ANNUAL_AMOUNT", 0) or 0),
                "reg_date": (row.get("REG_DATE") or "").strip(),
                "rooms": (row.get("ROOMS_EN") or "").strip(),
            })
    print(f"  Imported {len(rents)} DLD rental contracts")
    return rents


def import_projects() -> list[dict]:
    if not PROJECTS_JSON.exists():
        print(f"  [WARN] Projects JSON not found: {PROJECTS_JSON}")
        return []
    with open(PROJECTS_JSON) as f:
        projects = json.load(f)
    print(f"  Imported {len(projects)} projects from DXBInteract")
    return projects


def group_transactions_by_project(transactions: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in transactions:
        if t["project"]:
            groups[t["project"]].append(t)
    return groups


def group_transactions_by_area(transactions: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in transactions:
        if t["area"]:
            groups[t["area"]].append(t)
    return groups


def run():
    print("[ETL] Importing DLD data...")
    transactions = import_dld_transactions()
    rents = import_dld_rents()
    projects = import_projects()

    data = {
        "transactions": transactions,
        "rents": rents,
        "projects": projects,
        "imported_at": __import__("datetime").datetime.now().isoformat(),
    }
    save_json(BACKEND_DATA_DIR / "dld_warehouse.json", data)
    print(f"[ETL] DLD warehouse saved: {len(transactions)} txns, {len(rents)} rents, {len(projects)} projects")
    return data


if __name__ == "__main__":
    import json
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    run()
