"""
Rental Data Store — Safe, Normalized Access Layer
==================================================
NEW_RENTAL_ENGINE_IMPORTS_LEGACY = 0

Loads, normalizes, and indexes rental contracts for benchmark computation.
NO legacy ROI/rental code dependencies.

Data source: DLD_RENTS_PATH environment variable (defaults to project-relative dxb_rents_all.csv)
File: dxb_rents_all.csv
SHA256: 92546471b4326a89ca5980381b918cd5077d277eae396edf0374d9448d91129d
Raw rows: 573,001
"""

import csv
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_RENTAL_CSV = Path(__file__).parent.parent.parent.parent / "dxb_rents_all.csv"
RENTAL_CSV_PATH = Path(os.getenv("DLD_RENTS_PATH", str(DEFAULT_RENTAL_CSV)))

EXPECTED_SHA256 = "92546471b4326a89ca5980381b918cd5077d277eae396edf0374d9448d91129d"
EXPECTED_RAW_ROWS = 573001

RESIDENTIAL_USAGE = "Residential"
ALLOWED_PROP_TYPES = {"Unit", "Villa"}

# Validation bounds (applied AFTER sqm→sqft conversion)
MIN_ANNUAL_RENT = 10_000
MAX_ANNUAL_RENT = 5_000_000
MIN_ACTUAL_AREA_SQFT = 100      # ~9.3 sqm minimum
MAX_ACTUAL_AREA_SQFT = 215_000  # ~20,000 sqm maximum
MIN_PSF = 20
MAX_PSF = 5_000

# ──────────────────────────────────────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class RentalContract:
    """Normalized, validated rental contract."""
    registration_date: str          # YYYY-MM-DD
    start_date: str                 # YYYY-MM-DD
    end_date: str                   # YYYY-MM-DD
    version: str                    # "New" | "Renewed"
    area_en: str
    annual_amount: float            # AED
    actual_area_sqft: float         # sqft (converted from source sqm)
    actual_area_sqm: float          # original sqm for audit
    prop_type_en: str               # "Unit" | "Villa"
    prop_sub_type_en: str
    rooms_raw: str                  # original ROOMS value
    bedrooms: Optional[int]         # inferred (0=studio, 1,2,3,...)
    psf: float                      # annual_amount / actual_area_sqft
    project_en: str                 # may be empty (original case-preserving)
    project_key: str                # normalized key for exact-match lookup
    master_project_en: str          # may be empty
    total_properties: Optional[int] # None if missing, else integer
    is_free_hold: bool
    usage_en: str
    source_file: str                # which CSV this came from
    row_id: int                     # original row index
    property_class: str             # residential/commercial/industrial/other


@dataclass
class RentalIndex:
    """Fast lookup indexes for candidate comparator."""
    by_area: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))
    by_project: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))
    by_bedrooms: Dict[int, List[int]] = field(default_factory=lambda: defaultdict(list))
    by_area_bedrooms: Dict[Tuple[str, int], List[int]] = field(default_factory=lambda: defaultdict(list))
    by_project_bedrooms: Dict[Tuple[str, int], List[int]] = field(default_factory=lambda: defaultdict(list))
    by_area_prop_type: Dict[Tuple[str, str], List[int]] = field(default_factory=lambda: defaultdict(list))
    by_project_prop_type: Dict[Tuple[str, str], List[int]] = field(default_factory=lambda: defaultdict(list))

    def add(self, idx: int, contract: RentalContract):
        self.by_area[contract.area_en].append(idx)
        if contract.project_key:
            self.by_project[contract.project_key].append(idx)
        if contract.bedrooms is not None:
            self.by_bedrooms[contract.bedrooms].append(idx)
            self.by_area_bedrooms[(contract.area_en, contract.bedrooms)].append(idx)
            if contract.project_key:
                self.by_project_bedrooms[(contract.project_key, contract.bedrooms)].append(idx)
        # Property type indexes for type-filtered lookups
        self.by_area_prop_type[(contract.area_en, contract.prop_type_en)].append(idx)
        if contract.project_key:
            self.by_project_prop_type[(contract.project_key, contract.prop_type_en)].append(idx)

    def get_by_area_bedrooms(self, area: str, bedrooms: int) -> List[int]:
        return self.by_area_bedrooms.get((area, bedrooms), [])

    def get_by_project_bedrooms(self, project_key: str, bedrooms: int) -> List[int]:
        return self.by_project_bedrooms.get((project_key, bedrooms), [])

    def get_by_area(self, area: str) -> List[int]:
        return self.by_area.get(area, [])

    def get_by_project(self, project_key: str) -> List[int]:
        return self.by_project.get(project_key, [])

    def get_by_area_prop_type(self, area: str, prop_type: str) -> List[int]:
        return self.by_area_prop_type.get((area, prop_type), [])

    def get_by_project_prop_type(self, project_key: str, prop_type: str) -> List[int]:
        return self.by_project_prop_type.get((project_key, prop_type), [])


# ──────────────────────────────────────────────────────────────────────────────
# Normalization Helpers (delegated to rental_normalization module)
# ──────────────────────────────────────────────────────────────────────────────
from investor_api.rental.rental_normalization import (
    _norm_text,
    parse_date_yyyymmdd,
    parse_float,
    parse_int,
    infer_bedrooms_from_rooms,
    infer_property_class,
    normalize_rental_row,
    normalize_project_name,
)


# ──────────────────────────────────────────────────────────────────────────────
# Rental Data Store
# ──────────────────────────────────────────────────────────────────────────────
class RentalDataStore:
    """
    Singleton-ish lazy-loaded rental data store.
    Thread-safe for read access after initialization.
    """

    _instance: Optional["RentalDataStore"] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._contracts: List[RentalContract] = []
        self._index = RentalIndex()
        self._load_stats = {}
        self._load_all()
        self._initialized = True

    def _verify_source_file(self, path: Path) -> bool:
        """Verify file exists and matches expected SHA256."""
        if not path.exists():
            logging.error("Rental CSV not found: %s", path)
            return False

        import hashlib
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        actual_hash = sha256.hexdigest()

        if actual_hash != EXPECTED_SHA256:
            logging.error("SHA256 mismatch! Expected: %s, Got: %s", EXPECTED_SHA256, actual_hash)
            return False

        logging.info("Source file verified: SHA256 matches")
        return True

    def _load_all(self):
        logging.info("Loading rental data from: %s", RENTAL_CSV_PATH)

        if not self._verify_source_file(RENTAL_CSV_PATH):
            raise RuntimeError(f"Source file validation failed: {RENTAL_CSV_PATH}")

        total_loaded = 0
        total_filtered = 0
        total_rows = 0

        logging.info("Loading %s...", RENTAL_CSV_PATH.name)
        loaded, filtered, rows = self._load_csv(RENTAL_CSV_PATH, RENTAL_CSV_PATH.name)
        total_loaded += loaded
        total_filtered += filtered
        total_rows += rows
        logging.info("  Loaded %d, filtered %d, total rows %d", loaded, filtered, rows)

        self._load_stats = {
            "source_path": str(RENTAL_CSV_PATH),
            "sha256": EXPECTED_SHA256,
            "raw_row_count": total_rows,
            "loaded": total_loaded,
            "filtered": total_filtered,
            "single_property": sum(1 for c in self._contracts if c.total_properties == 1),
            "multi_property": sum(1 for c in self._contracts if c.total_properties and c.total_properties > 1),
            "missing_total_properties": sum(1 for c in self._contracts if c.total_properties is None),
            "by_version": {},
            "by_prop_type": {},
            "by_prop_sub_type": {},
        }

        # Populate stats
        for c in self._contracts:
            self._load_stats["by_version"][c.version] = self._load_stats["by_version"].get(c.version, 0) + 1
            self._load_stats["by_prop_type"][c.prop_type_en] = self._load_stats["by_prop_type"].get(c.prop_type_en, 0) + 1
            self._load_stats["by_prop_sub_type"][c.prop_sub_type_en] = self._load_stats["by_prop_sub_type"].get(c.prop_sub_type_en, 0) + 1

        logging.info("Total rental contracts loaded: %d", len(self._contracts))
        logging.info("  Single property (TOTAL_PROPERTIES==1): %d", self._load_stats["single_property"])
        logging.info("  Multi-property (TOTAL_PROPERTIES>1): %d", self._load_stats["multi_property"])
        logging.info("  Missing TOTAL_PROPERTIES: %d", self._load_stats["missing_total_properties"])

    def _load_csv(self, path: Path, source_name: str) -> Tuple[int, int, int]:
        """Load and normalize a single rental CSV. Returns (kept, filtered, total_rows)."""
        kept = 0
        filtered = 0
        total_rows = 0

        # Detect delimiter
        with open(path, "r", encoding="utf-8-sig") as fh:
            sample = fh.read(4096)
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter

        with open(path, "r", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh, delimiter=delimiter)
            for row_idx, row in enumerate(reader):
                total_rows += 1

                # Use normalization function
                normalized = normalize_rental_row(row, source_name)
                if normalized is None:
                    filtered += 1
                    continue

                # CRITICAL: Filter to ONLY TOTAL_PROPERTIES == 1 (no assumption for missing)
                tp = normalized.get("total_properties")
                if tp != 1:
                    filtered += 1
                    continue

                contract = RentalContract(
                    registration_date=normalized["registration_date"],
                    start_date=normalized["start_date"],
                    end_date=normalized["end_date"],
                    version=normalized["version"],
                    area_en=normalized["area_en"],
                    annual_amount=normalized["annual_amount"],
                    actual_area_sqft=normalized["actual_area_sqft"],
                    actual_area_sqm=normalized["actual_area_sqm"],
                    prop_type_en=normalized["prop_type_en"],
                    prop_sub_type_en=normalized["prop_sub_type_en"],
                    rooms_raw=normalized["rooms_raw"],
                    bedrooms=normalized["bedrooms"],
                    psf=normalized["psf"],
                    project_en=normalized["project_en"],
                    project_key=normalize_project_name(normalized["project_en"]),
                    master_project_en=normalized["master_project_en"],
                    total_properties=normalized["total_properties"],
                    is_free_hold=normalized["is_free_hold"],
                    usage_en=normalized["usage_en"],
                    source_file=normalized["source_file"],
                    row_id=row_idx,
                    property_class=normalized["property_class"],
                )

                idx = len(self._contracts)
                self._contracts.append(contract)
                self._index.add(idx, contract)
                kept += 1

        return kept, filtered, total_rows

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────
    @property
    def contracts(self) -> List[RentalContract]:
        return self._contracts

    @property
    def index(self) -> RentalIndex:
        return self._index

    def get_contracts_by_indices(self, indices: List[int]) -> List[RentalContract]:
        return [self._contracts[i] for i in indices if 0 <= i < len(self._contracts)]

    def get_area_coverage(self) -> Dict[str, int]:
        """Return transaction count per area."""
        return {area: len(idxs) for area, idxs in self._index.by_area.items()}

    def get_project_coverage(self, area: str) -> Dict[str, int]:
        """Return transaction count per project within an area."""
        result = {}
        for proj_key, idxs in self._index.by_project.items():
            area_count = sum(1 for i in idxs if self._contracts[i].area_en == area)
            if area_count:
                # Map project_key back to original display name
                original = next((self._contracts[i].project_en for i in idxs if self._contracts[i].project_en), proj_key)
                result[original or proj_key] = area_count
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Summary statistics."""
        if not self._contracts:
            return {"total": 0}

        annuals = [c.annual_amount for c in self._contracts]
        psfs = [c.psf for c in self._contracts]
        areas = [c.actual_area_sqft for c in self._contracts]
        bedrooms_dist = defaultdict(int)
        for c in self._contracts:
            if c.bedrooms is not None:
                bedrooms_dist[c.bedrooms] += 1

        return {
            "total_contracts": len(self._contracts),
            "unique_areas": len(self._index.by_area),
            "unique_projects": len(self._index.by_project),
            "bedrooms_distribution": dict(bedrooms_dist),
            "annual_rent": {"min": min(annuals), "max": max(annuals), "median": sorted(annuals)[len(annuals)//2]},
            "psf": {"min": min(psfs), "max": max(psfs), "median": sorted(psfs)[len(psfs)//2]},
            "area_sqft": {"min": min(areas), "max": max(areas), "median": sorted(areas)[len(areas)//2]},
            "date_range": {
                "reg_min": min(c.registration_date for c in self._contracts),
                "reg_max": max(c.registration_date for c in self._contracts),
                "start_min": min(c.start_date for c in self._contracts),
                "start_max": max(c.start_date for c in self._contracts),
            },
            "source_files": list(set(c.source_file for c in self._contracts)),
            "load_stats": self._load_stats,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Module-level accessor
# ──────────────────────────────────────────────────────────────────────────────
def get_rental_store() -> RentalDataStore:
    """Get the singleton rental data store instance."""
    return RentalDataStore()