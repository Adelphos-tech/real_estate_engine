"""
Rental Area Mapping — MASTER Area → DLD Rental Area
====================================================
NEW_RENTAL_ENGINE_IMPORTS_LEGACY = 0

Maps MASTER_FINAL community areas to DLD rental transaction areas.
Built independently - does NOT use stale MASTER DLD flags (dld_evidence_status, dld_transaction_count).
Uses project overlap from rental data only.

AUDITABLE: Every mapping returns master_area, dld_rental_area, mapping_method,
supporting_projects, support_count, confidence, manual_override, version.
"""

import hashlib
import json
import logging
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_RENTAL_CSV = Path(__file__).parent.parent.parent.parent / "dxb_rents_all.csv"
RENTAL_CSV_PATH = Path(os.getenv("DLD_RENTS_PATH", str(DEFAULT_RENTAL_CSV)))

MASTER_PATH = Path("/Users/apple/Desktop/Ai 3d view/MASTER_FINAL.xlsx")

MAPPING_VERSION = "RENTAL_AREA_MAP_V1"
MANUAL_MAPPING_VERSION = "RENTAL_MANUAL_MAP_V1"


# ──────────────────────────────────────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class AreaMappingEntry:
    """Auditable area mapping entry."""
    master_area: str
    dld_rental_area: str
    mapping_method: str              # "auto_project_overlap" | "manual_fallback"
    supporting_projects: List[str]   # List of project names (normalized)
    support_count: int               # Number of supporting projects
    confidence: str                  # "high" | "medium" | "low" | "ambiguous"
    manual_override: bool
    version: str                     # Mapping version
    dominance_ratio: float = 0.0
    alternative_candidates: List[Dict] = None

    def __post_init__(self):
        if self.alternative_candidates is None:
            self.alternative_candidates = []


# ──────────────────────────────────────────────────────────────────────────────
# Normalization
# ──────────────────────────────────────────────────────────────────────────────
def _normalize(text: Optional[str]) -> str:
    if not text:
        return ""
    text = str(text).strip().lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_project(text: Optional[str]) -> str:
    """Normalize project name for matching."""
    if not text:
        return ""
    text = str(text).strip().lower()
    # Remove common suffixes/prefixes
    text = re.sub(r"\b(phase|tower|building|block)\s*\d+\b", "", text)
    text = re.sub(r"\b(residence|residences|tower|towers)\b", "", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ──────────────────────────────────────────────────────────────────────────────
# Load Rental Data for Mapping
# ──────────────────────────────────────────────────────────────────────────────
def _load_rental_area_projects() -> Tuple[Dict[str, Set[str]], Dict[str, Dict[str, int]]]:
    """
    Load rental data and build:
    - area_to_projects: DLD area -> set of normalized project names
    - project_to_areas: normalized project -> {DLD area: count}
    """
    import csv

    area_to_projects: Dict[str, Set[str]] = defaultdict(set)
    project_to_areas: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    with open(RENTAL_CSV_PATH, "r", encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
    sniffer = csv.Sniffer()
    delimiter = sniffer.sniff(sample).delimiter

    with open(RENTAL_CSV_PATH, "r", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        for row in reader:
            # Residential + Unit/Villa only
            if _normalize(row.get("USAGE_EN", "")) != "residential":
                continue
            prop_type = _normalize(row.get("PROP_TYPE_EN", ""))
            if prop_type not in ("unit", "villa"):
                continue

            area = _normalize(row.get("AREA_EN", ""))
            project_raw = row.get("PROJECT_EN", "")
            project = _normalize_project(project_raw)

            if not area or not project:
                continue

            area_to_projects[area].add(project)
            project_to_areas[project][area] += 1

    # Convert sets to lists for serialization
    return {a: list(p) for a, p in area_to_projects.items()}, \
           {p: dict(a) for p, a in project_to_areas.items()}


# ──────────────────────────────────────────────────────────────────────────────
# Load MASTER Areas and Projects
# ──────────────────────────────────────────────────────────────────────────────
def _load_master_areas_projects() -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Load MASTER areas and their associated projects.
    Returns: (unique_master_areas, area_to_master_projects)
    """
    df = pd.read_excel(MASTER_PATH)
    areas = df["area"].dropna().unique().tolist()

    area_to_projects: Dict[str, List[str]] = defaultdict(list)
    for _, row in df.iterrows():
        area = str(row.get("area", "")).strip()
        project_raw = str(row.get("normalized_project_name", "")).strip()
        if area and project_raw:
            project = _normalize_project(project_raw)
            if project:
                area_to_projects[area].append(project)

    # Deduplicate
    for area in area_to_projects:
        area_to_projects[area] = list(set(area_to_projects[area]))

    return areas, area_to_projects


# ──────────────────────────────────────────────────────────────────────────────
# Build Auto Mapping via Project Overlap
# ──────────────────────────────────────────────────────────────────────────────
def _build_auto_mapping(
    area_to_master_projects: Dict[str, List[str]],
    project_to_areas: Dict[str, Dict[str, int]],
) -> Dict[str, AreaMappingEntry]:
    """
    For each MASTER area, find which DLD rental area its projects map to.
    Uses project overlap from rental data only (no MASTER DLD flags).
    """
    mapping = {}

    for master_area, master_projects in area_to_master_projects.items():
        if not master_projects:
            continue

        # Aggregate DLD areas across all projects in this MASTER area
        dld_area_votes = Counter()

        for proj in master_projects:
            if proj in project_to_areas:
                for dld_area, count in project_to_areas[proj].items():
                    dld_area_votes[dld_area] += count

        if not dld_area_votes:
            continue

        total_votes = sum(dld_area_votes.values())
        top_dld_area, top_votes = dld_area_votes.most_common(1)[0]
        dominance = top_votes / total_votes if total_votes > 0 else 0

        # Confidence based on project support and dominance
        n_supporting_projects = sum(1 for p in master_projects if p in project_to_areas)
        if n_supporting_projects >= 10 and dominance >= 0.8:
            confidence = "high"
        elif n_supporting_projects >= 5 and dominance >= 0.6:
            confidence = "medium"
        elif n_supporting_projects >= 2 and dominance >= 0.4:
            confidence = "low"
        else:
            confidence = "ambiguous"

        supporting_projects_list = [p for p in master_projects if p in project_to_areas]

        mapping[master_area] = AreaMappingEntry(
            master_area=master_area,
            dld_rental_area=top_dld_area,
            mapping_method="auto_project_overlap",
            supporting_projects=supporting_projects_list,
            support_count=n_supporting_projects,
            confidence=confidence,
            manual_override=False,
            version=MAPPING_VERSION,
            dominance_ratio=round(dominance, 3),
            alternative_candidates=[
                {"area": a, "votes": v, "dominance": round(v / total_votes, 3)}
                for a, v in dld_area_votes.most_common(3)
            ],
        )

    return mapping


# ──────────────────────────────────────────────────────────────────────────────
# Manual Fallback Mapping (Versioned and Auditable)
# ──────────────────────────────────────────────────────────────────────────────
# Manual mappings for areas with no/insufficient project overlap.
# Each entry: master_area -> dld_rental_area
# Version: MANUAL_MAPPING_VERSION - increment when changed
MANUAL_RENTAL_AREA_MAPPING_V1 = {
    # Format: normalized_master_area -> dld_rental_area (exact DLD area name)
    "dubai marina": "Marsa Dubai",
    "downtown dubai": "Burj Khalifa",
    "business bay": "Business Bay",
    "jumeirah lake towers": "Al Thanyah Fifth",  # JLT is in Al Thanyah Fifth
    "jumeirah village circle": "Al Barsha South Fourth",
    "jumeirah village triangle": "Al Barsha South Fifth",
    "dubai hills estate": "Hadaeq Sheikh Mohammed Bin Rashid",
    "damac hills": "Jabal Ali First",
    "damac hills 2": "Dubai Investment Park First",
    "damac lagoons": "Dubai Investment Park First",
    "arabian ranches": "Al Warsan First",
    "arabian ranches 3": "Al Warsan First",
    "al furjan": "Jabal Ali First",
    "al furjan west": "Jabal Ali First",
    "dubai production city": "Me'Aisem First",
    "dubai sports city": "Al Hebiah Fourth",
    "dubai creek harbour": "Al Khairan First",
    "dubai harbour": "Marsa Dubai",
    "dubai investment park": "Dubai Investment Park First",
    "dubai investments park": "Dubai Investment Park First",
    "jumeirah beach residence": "Marsa Dubai",
    "jbr": "Marsa Dubai",
    "palm jumeirah": "Palm Jumeirah",
    "the palm": "Palm Jumeirah",
    "jumeirah islands": "Jumeirah Islands",
    "jumeirah heights": "Jumeirah Heights",
    "jumeirah garden city": "Jumeirah Garden City",
    "jumeirah park": "Jumeirah Park",
    "jumeirah golf estates": "Jumeirah Golf Estates",
    "jumeirah": "Jumeirah First",
    "al barari": "Wadi Al Safa 3",
    "the meadows": "Al Barshaa South First",
    "the springs": "Al Barshaa South Second",
    "the lakes": "Al Barshaa South Third",
    "the views": "Al Barshaa South Third",
    "the greens": "Al Barshaa South Third",
    "the gardens": "Al Barshaa South Third",
    "al quoz": "Al Goze First",
    "al quoz industrial": "Al Goze Industrial First",
    "al khail": "Al Khail",
    "al khail gate": "Al Khail",
    "al satwa": "Al Satwa",
    "al wasl": "Al Wasl",
    "al jadaf": "Al Jadaf",
    "al jaddaf": "Al Jadaf",
    "al jafiliya": "Al Jafliya",
    "zaabeel": "Zaabeel First",
    "zaabeel 1": "Zaabeel First",
    "zaabeel 2": "Zaabeel Second",
    "trade centre": "Trade Centre First",
    "trade centre 1": "Trade Centre First",
    "trade centre 2": "Trade Centre Second",
    "difc": "Trade Centre First",
    "al sufooh": "Al Safouh First",
    "al sufooh 1": "Al Safouh First",
    "al sufooh 2": "Al Safouh Second",
    "nad al sheba": "Nad Al Shiba",
    "nad al sheba 1": "Nad Al Shiba First",
    "nad al sheba 2": "Nad Al Shiba Second",
    "nad al sheba 3": "Nad Al Shiba Third",
    "nad al sheba 4": "Nad Al Shiba Fourth",
    "mohammed bin rashid city": "Hadaeq Sheikh Mohammed Bin Rashid",
    "mbr city": "Hadaeq Sheikh Mohammed Bin Rashid",
    "district one": "Hadaeq Sheikh Mohammed Bin Rashid",
    "sobha hartland": "Nadd Hessa",
    "sobha one": "Marsa Dubai",
    "sobha central": "Nadd Hessa",
    "the valley": "Wadi Al Safa 2",
    "dubailand": "Wadi Al Safa 2",
    "arjan": "Al Barshaa South Third",
    "aljada": "Aljada",
    "sharjah waterfront city": "Sharjah Waterfront City",
    "siniya island": "Siniya Island",
    "maryam island": "Maryam Island",
    "reem island": "Al Reem Island",
    "al reem island": "Al Reem Island",
    "al maryah island": "Al Maryah Island",
    "al raha": "Al Raha",
    "al raha beach": "Al Raha Beach",
    "yas island": "Yas Island",
    "saadiyat island": "Saadiyat Island",
    "masdar city": "Masdar City",
    "khalifa city": "Khalifa City",
    "expo city": "Dubai South",
    "expo 2020": "Dubai South",
    "dubai water canal": "Burj Khalifa",
    "dubai maritime city": "Al Jaddaf",
    "dubai creek": "Al Jaddaf",
    "la mer": "Jumeirah First",
    "city walk": "Jumeirah First",
    "bluewaters": "Marsa Dubai",
    "bluewaters island": "Marsa Dubai",
    "port saeed": "Port Saeed",
    "al mamzar": "Al Mamzer",
    "al nahda": "Al Nahda First",
    "al nahda 1": "Al Nahda First",
    "al nahda 2": "Al Nahda Second",
    "al barsha": "Al Barsha First",
    "al barsha 1": "Al Barsha First",
    "al barsha 2": "Al Barsha Second",
    "al barsha 3": "Al Barsha Third",
    "al barsha south": "Al Barsha South Fourth",
    "al barsha south fourth": "Al Barsha South Fourth",
    "al barsha south fifth": "Al Barsha South Fifth",
    "jebel ali": "Jabal Ali First",
    "jebel ali first": "Jabal Ali First",
    "jebel ali industrial": "Jabal Ali Industrial First",
    "dubai industrial city": "Jabal Ali Industrial First",
    "emirates road": "Emirates Road",
    "sheikh zayed road": "Trade Centre First",
    "mohammed bin zayed road": "Mohammed Bin Zayed Road",
    "al warsan": "Al Warsan First",
    "al warsan 1": "Al Warsan First",
    "al warsan first": "Al Warsan First",
    "al warsan 2": "Al Warsan Second",
    "al warsan second": "Al Warsan Second",
    "mudon": "Al Warsan First",
    "remraam": "Al Warsan First",
    "sustainable city": "Al Warsan First",
    "green community": "Dubai Investment Park First",
    "the villa": "Al Warsan First",
    "akoya oxygen": "Al Warsan First",
    "al habtoor city": "Business Bay",
    "dubai waterfront": "Marsa Dubai",
    "madinat jumeirah living": "Jumeirah First",
    "meydan": "Nadd Hessa",
    "meydan city": "Nadd Hessa",
    "nasr city": "Nadd Hessa",
    "wasl vistas": "Al Wasl",
    "wasl manor": "Al Wasl",
    "city of arabia": "Wadi Al Safa 2",
    "dubai land": "Wadi Al Safa 2",
    "victory heights": "Al Warsan First",
    "global village": "Wadi Al Safa 2",
    "liwan": "Wadi Al Safa 2",
    "liwan square": "Wadi Al Safa 2",
    "skyscraper": "Business Bay",
    "jumeirah bay": "Palm Jumeirah",
    "palm jebel ali": "Jabal Ali First",
    "the world islands": "Marsa Dubai",
    "world island": "Marsa Dubai",
    "heart of europe": "Marsa Dubai",
    "dubai international city": "Al Warsan First",
    "international city": "Al Warsan First",
    "international city phase 2": "Al Warsan First",
    "dubai silicon oasis": "Al Qusais Industrial First",
    "silicon oasis": "Al Qusais Industrial First",
    "dubai motor city": "Al Hebiah Fourth",
    "motor city": "Al Hebiah Fourth",
    "dubai media city": "Al Thanyah Fifth",
    "media city": "Al Thanyah Fifth",
    "dubai design district": "Al Jadaf",
    "design district": "Al Jadaf",
    "d3": "Al Jadaf",
    "dubai science park": "Al Thanyah Fifth",
    "science park": "Al Thanyah Fifth",
    "discovery gardens": "Al Barsha South Fourth",
    "town square dubai": "Wadi Al Safa 3",
    "town square": "Wadi Al Safa 3",
    "dubai south": "Jabal Ali First",
    "dubai islands": "Marsa Dubai",
    "dubai studio city": "Al Hebiah Fourth",
    "studio city": "Al Hebiah Fourth",
    "downtown jebel ali": "Jabal Ali First",
    "emaar beachfront": "Marsa Dubai",
    "dubai land residence complex": "Wadi Al Safa 3",
    "sobha hartland 2": "Nadd Hessa",
    "the wilds": "Al Warsan First",
    "tilal city": "Al Warsan First",
    "majan": "Al Warsan First",
    "ghaf woods": "Al Warsan First",
    "emaar south": "Jabal Ali First",
    "damac riverside": "Al Warsan First",
    "rashid yachts & marina": "Marsa Dubai",
    "rashid yachts and marina": "Marsa Dubai",
    "minha al arab": "Marsa Dubai",
    "mina al arab": "Marsa Dubai",
    "umm al daman": "Al Warsan First",
    "waada by bahria town at dubai south": "Jabal Ali First",
    "wasl gate": "Al Wasl",
    "al marjan island": "Marsa Dubai",
    "al jurf": "Al Warsan First",
    "al jazeera": "Al Warsan First",
    "al hamra": "Al Warsan First",
    "solaya by meraas at la mer": "Jumeirah First",
    "raha island": "Marsa Dubai",
    "sharjah garden city": "Al Warsan First",
    "rak central": "Al Warsan First",
    # Additional direct mappings for exact MASTER names
    "al barari": "Wadi Al Safa 3",
    "al furjan": "Jabal Ali First",
    "al habtoor city": "Business Bay",
    "al hamra": "Al Warsan First",
    "al jadaf waterfront": "Al Jadaf",
    # Direct mappings for DLD rental area names (identity mappings)
    "al thanyah first": "Al Thanyah First",
    "al thanyah fifth": "Al Thanyah Fifth",
    "al thanyah third": "Al Thanyah Third",
    "al hebiah first": "Al Hebiah First",
    "al hebiah fourth": "Al Hebiah Fourth",
    "al hebiah fifth": "Al Hebiah Fifth",
    "al hebiah second": "Al Hebiah Second",
    "al hebiah third": "Al Hebiah Third",
    "al hebiah sixth": "Al Hebiah Sixth",
    "wadi al safa 7": "Wadi Al Safa 7",
    "wadi al safa 5": "Wadi Al Safa 5",
    "wadi al safa 2": "Wadi Al Safa 2",
    "wadi al safa 6": "Wadi Al Safa 6",
    "wadi al safa 3": "Wadi Al Safa 3",
    "wadi al safa 4": "Wadi Al Safa 4",
    "dubai investment park first": "Dubai Investment Park First",
    "dubai investment park second": "Dubai Investment Park Second",
    "jumeirah first": "Jumeirah First",
    "al jazeera": "Al Warsan First",
    "al jurf": "Al Warsan First",
    "al mamzar": "Al Mamzer",
    "al marjan island": "Marsa Dubai",
    "al maryah island": "Al Maryah Island",
    "al raha": "Al Raha",
    "al reem island": "Al Reem Island",
    "al satwa": "Al Satwa",
    "al sufouh 1": "Al Safouh First",
    "al sufouh 2": "Al Safouh Second",
    "al warsan": "Al Warsan First",
    "aljada": "Aljada",
    "arabian ranches 3": "Al Warsan First",
    "arjan": "Al Barshaa South Third",
    "business bay": "Business Bay",
    "city walk": "Jumeirah First",
    "city of arabia": "Wadi Al Safa 2",
    "damac riverside": "Al Warsan First",
    "difc": "Trade Centre First",
    "damac hills": "Jabal Ali First",
    "damac hills 2": "Dubai Investment Park First",
    "damac lagoons": "Dubai Investment Park First",
    "discovery gardens": "Al Barsha South Fourth",
    "district one": "Hadaeq Sheikh Mohammed Bin Rashid",
    "downtown dubai": "Burj Khalifa",
    "downtown jebel ali": "Jabal Ali First",
    "dubai creek harbour": "Al Khairan First",
    "dubai design district": "Al Jadaf",
    "dubai harbour": "Marsa Dubai",
    "dubai hills estate": "Hadaeq Sheikh Mohammed Bin Rashid",
    "dubai industrial city": "Jabal Ali Industrial First",
    "dubai international city": "Al Warsan First",
    "dubai investments park": "Dubai Investment Park First",
    "dubai islands": "Marsa Dubai",
    "dubai marina": "Marsa Dubai",
    "dubai maritime city": "Al Jaddaf",
    "dubai media city": "Al Thanyah Fifth",
    "dubai motor city": "Al Hebiah Fourth",
    "dubai production city": "Me'Aisem First",
    "dubai science park": "Al Thanyah Fifth",
    "dubai silicon oasis": "Al Qusais Industrial First",
    "dubai south": "Jabal Ali First",
    "dubai sports city": "Al Hebiah Fourth",
    "dubai studio city": "Al Hebiah Fourth",
    "dubai water canal": "Burj Khalifa",
    "dubailand": "Wadi Al Safa 2",
    "emaar beachfront": "Marsa Dubai",
    "emaar south": "Jabal Ali First",
    "expo city": "Dubai South",
    "ghaf woods": "Al Warsan First",
    "international city phase 2": "Al Warsan First",
    "jebel ali": "Jabal Ali First",
    "jumeirah garden city": "Jumeirah Garden City",
    "jumeirah heights": "Jumeirah Heights",
    "jumeirah islands": "Jumeirah Islands",
    "jumeirah lake towers": "Al Thanyah Fifth",
    "jumeirah village triangle": "Al Barsha South Fifth",
    "jumeirah village circle": "Al Barsha South Fourth",
    "khalifa city": "Khalifa City",
    "la mer": "Jumeirah First",
    "liwan square": "Wadi Al Safa 2",
    "madinat jumeirah living": "Jumeirah First",
    "majan": "Al Warsan First",
    "maryam island": "Maryam Island",
    "masdar city": "Masdar City",
    "mercedes benz places by binghatti": "Business Bay",
    "meydan city": "Nadd Hessa",
    "mina al arab": "Marsa Dubai",
    "mohammed bin rashid city": "Hadaeq Sheikh Mohammed Bin Rashid",
    "nad al sheba": "Nad Al Shiba",
    "palm jumeirah": "Palm Jumeirah",
    "rak central": "Al Warsan First",
    "raha island": "Marsa Dubai",
    "rashid yachts & marina": "Marsa Dubai",
    "saadiyat island": "Saadiyat Island",
    "sharjah garden city": "Al Warsan First",
    "sheikh zayed road": "Trade Centre First",
    "siniya island": "Siniya Island",
    "sobha central": "Nadd Hessa",
    "sobha hartland 2": "Nadd Hessa",
    "sobha one": "Marsa Dubai",
    "solaya by meraas at la mer": "Jumeirah First",
    "the greens": "Al Barshaa South Third",
    "the valley": "Wadi Al Safa 2",
    "the wilds": "Al Warsan First",
    "tilal city": "Al Warsan First",
    "town square dubai": "Wadi Al Safa 3",
    "umm al daman": "Al Warsan First",
    "waada by bahria town at dubai south": "Jabal Ali First",
    "wasl gate": "Al Wasl",
    "world island": "Marsa Dubai",
    "yas island": "Yas Island",
    "sharjah waterfront city": "Sharjah Waterfront City",
}


# ──────────────────────────────────────────────────────────────────────────────
# Build Complete Mapping
# ──────────────────────────────────────────────────────────────────────────────
_RENTAL_AREA_MAPPING_CACHE: Optional[Dict[str, AreaMappingEntry]] = None


def _build_complete_mapping() -> Dict[str, AreaMappingEntry]:
    """Build complete mapping combining auto + manual (manual fills gaps only)."""
    global _RENTAL_AREA_MAPPING_CACHE

    if _RENTAL_AREA_MAPPING_CACHE is not None:
        return _RENTAL_AREA_MAPPING_CACHE

    logging.info("Building rental area mapping...")

    # Load rental data project->area mapping
    area_to_projects, project_to_areas = _load_rental_area_projects()
    logging.info("Loaded %d DLD rental areas with projects", len(area_to_projects))
    logging.info("Loaded %d unique projects in rental data", len(project_to_areas))

    # Load MASTER areas and projects
    master_areas, area_to_master_projects = _load_master_areas_projects()
    logging.info("Loaded %d unique MASTER areas", len(master_areas))

    # Build auto mapping
    auto_mapping = _build_auto_mapping(area_to_master_projects, project_to_areas)
    logging.info("Auto-mapped %d MASTER areas", len(auto_mapping))

    # Merge: start with auto, fill gaps with manual
    complete_mapping = {}

    # Add auto mappings
    for master_area, entry in auto_mapping.items():
        complete_mapping[master_area] = entry

    # Fill gaps with manual (only for areas not auto-mapped)
    manual_count = 0
    for master_area in master_areas:
        if master_area not in complete_mapping:
            norm = _normalize(master_area)
            if norm in MANUAL_RENTAL_AREA_MAPPING_V1:
                dld_area = MANUAL_RENTAL_AREA_MAPPING_V1[norm]
                complete_mapping[master_area] = AreaMappingEntry(
                    master_area=master_area,
                    dld_rental_area=dld_area,
                    mapping_method="manual_fallback",
                    supporting_projects=[],
                    support_count=0,
                    confidence="manual",
                    manual_override=True,
                    version=MANUAL_MAPPING_VERSION,
                )
                manual_count += 1

    logging.info("Added %d manual fallback mappings", manual_count)
    logging.info("Total mapped areas: %d / %d (%.1f%%)",
                 len(complete_mapping), len(master_areas),
                 len(complete_mapping) / len(master_areas) * 100 if master_areas else 0)

    _RENTAL_AREA_MAPPING_CACHE = complete_mapping
    return complete_mapping


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────
def get_rental_area_mapping() -> Dict[str, AreaMappingEntry]:
    """Get the complete auditable rental area mapping."""
    return _build_complete_mapping()


def get_rental_area_for_master(master_area: str) -> Optional[str]:
    """Convenience function to get DLD rental area for MASTER area."""
    if not master_area:
        return None
    mapping = get_rental_area_mapping()
    if master_area in mapping:
        return mapping[master_area].dld_rental_area
    # Try normalized lookup
    norm = _normalize(master_area)
    for k, v in mapping.items():
        if _normalize(k) == norm:
            return v.dld_rental_area
    return None


def get_exact_dld_area_for_master(master_area: str, store) -> Optional[str]:
    """Get DLD rental area for MASTER area, returning exact case as in store index."""
    dld_area = get_rental_area_for_master(master_area)
    if not dld_area:
        return None
    # Find exact case match in store index
    norm_dld = dld_area.lower()
    for a in store.index.by_area.keys():
        if a.lower() == norm_dld:
            return a
    return dld_area


def _normalize_area_for_store(store, area: str) -> Optional[str]:
    """Normalize an area name to match exact case in store index."""
    if not area:
        return None
    norm = area.lower().strip()
    for a in store.index.by_area.keys():
        if a.lower() == norm:
            return a
    return None


def get_mapping_audit() -> List[Dict]:
    """Get full audit trail of all mappings."""
    mapping = get_rental_area_mapping()
    return [asdict(entry) for entry in mapping.values()]


def get_unmapped_areas() -> List[str]:
    """Get MASTER areas with no mapping."""
    _, area_to_master_projects = _load_master_areas_projects()
    mapping = get_rental_area_mapping()
    return [a for a in area_to_master_projects.keys() if a not in mapping]


def export_mapping_audit(path: str = "RENTAL_AREA_MAPPING_AUDIT.json"):
    """Export mapping audit to JSON file."""
    audit = get_mapping_audit()
    unmapped = get_unmapped_areas()
    report = {
        "version": MAPPING_VERSION,
        "manual_version": MANUAL_MAPPING_VERSION,
        "total_mapped": len(audit),
        "total_unmapped": len(unmapped),
        "mappings": audit,
        "unmapped_areas": unmapped,
    }
    with open(path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    logging.info("Mapping audit exported to %s", path)