"""
Rental Normalization — Field Cleaning & Derived Metrics
========================================================
NEW_RENTAL_ENGINE_IMPORTS_LEGACY = 0

Pure functions for normalizing rental data fields.
No external dependencies beyond stdlib.

CRITICAL: ACTUAL_AREA in source data is in SQUARE METRES (sqm).
Must convert to sqft: actual_area_sqft = ACTUAL_AREA * 10.7639104167
"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────
SQM_TO_SQFT = 10.7639104167

_ROOMS_NUM_RE = re.compile(r"(\d+)")
_STUDIO_KEYWORDS = {"studio", "hotel", "hotel apartment", "staff accommodation"}
_OFFICE_KEYWORDS = {"office", "workshop", "workshop complex"}
_RETAIL_KEYWORDS = {"shop", "showroom", "kiosk", "restaurant", "cafe", "cafeteria"}
_INDUSTRIAL_KEYWORDS = {"warehouse", "factory", "industrial", "workshop"}

# ──────────────────────────────────────────────────────────────────────────────
# Text Normalization
# ──────────────────────────────────────────────────────────────────────────────
def _norm_text(val: Optional[str]) -> str:
    if not val:
        return ""
    return str(val).strip()

def _norm_lower(val: Optional[str]) -> str:
    return _norm_text(val).lower()

# Harmless punctuation to strip for project matching (keeps meaning)
_PROJECT_STRIP_CHARS = ".,-/\\()'\""
_WHITESPACE_RE = re.compile(r"\s+")

def normalize_project_name(val: Optional[str]) -> str:
    """
    Deterministic normalized project key for exact-match lookup.
    - lowercase
    - strip surrounding/harmless punctuation
    - collapse internal whitespace
    - trim
    """
    if not val:
        return ""
    s = str(val).strip().lower()
    # Remove harmless punctuation
    for ch in _PROJECT_STRIP_CHARS:
        s = s.replace(ch, " ")
    # Collapse whitespace
    s = _WHITESPACE_RE.sub(" ", s).strip()
    return s

def parse_date_yyyymmdd(val: Any) -> Optional[str]:
    """Extract YYYY-MM-DD from various date string formats."""
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    # ISO with T separator
    if "T" in s:
        return s[:10]
    # Space separated datetime
    if " " in s:
        return s[:10]
    # Already YYYY-MM-DD
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None

def parse_float(val: Any) -> Optional[float]:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def parse_int(val: Any) -> Optional[int]:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None

# ──────────────────────────────────────────────────────────────────────────────
# Bedroom Inference
# ──────────────────────────────────────────────────────────────────────────────
def infer_bedrooms_from_rooms(rooms_raw: str, prop_sub_type_en: str) -> Optional[int]:
    """
    Infer bedroom count from ROOMS field and property sub-type.
    Returns None if cannot infer.
    """
    rooms_norm = _norm_lower(rooms_raw)
    sub_norm = _norm_lower(prop_sub_type_en)

    # 1. Studio detection from sub-type (highest confidence)
    for kw in _STUDIO_KEYWORDS:
        if kw in sub_norm:
            return 0

    # 2. Numeric bedrooms from ROOMS field
    m = _ROOMS_NUM_RE.search(rooms_norm)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass

    # 3. b/r or br patterns
    if "b/r" in rooms_norm or "br" in rooms_norm:
        m = _ROOMS_NUM_RE.search(rooms_norm)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass

    return None


def infer_property_class(prop_type_en: str, prop_sub_type_en: str) -> str:
    """
    Classify property into: residential, commercial, industrial, other
    For rental engine we only care about residential.
    """
    pt = _norm_lower(prop_type_en)
    pst = _norm_lower(prop_sub_type_en)

    if pt == "villa":
        return "residential"
    if pt == "unit":
        for kw in _STUDIO_KEYWORDS:
            if kw in pst:
                return "residential"
        for kw in _OFFICE_KEYWORDS:
            if kw in pst:
                return "commercial"
        for kw in _RETAIL_KEYWORDS:
            if kw in pst:
                return "commercial"
        for kw in _INDUSTRIAL_KEYWORDS:
            if kw in pst:
                return "industrial"
        # Default Unit = residential (Flat, Studio, etc.)
        return "residential"
    if pt == "land":
        return "land"
    if pt == "building":
        return "commercial"
    if pt == "virtual unit":
        return "other"
    return "other"


# ──────────────────────────────────────────────────────────────────────────────
# PSF & Rent Normalization
# ──────────────────────────────────────────────────────────────────────────────
def convert_sqm_to_sqft(area_sqm: float) -> float:
    """Convert square metres to square feet."""
    return area_sqm * SQM_TO_SQFT


def compute_psf(annual_rent: float, area_sqft: float) -> Optional[float]:
    """Compute price per sqft. Returns None if invalid inputs."""
    if annual_rent <= 0 or area_sqft <= 0:
        return None
    return annual_rent / area_sqft


def normalize_rent_to_annual(contract_amount: float, version: str, start_date: str, end_date: str) -> Optional[float]:
    """
    Normalize contract amount to annual rent.
    For 'New' contracts: contract_amount might be for full term, need to annualize.
    For 'Renewed': typically already annual (Ejari standard).
    """
    v = _norm_lower(version)
    if v == "renewed":
        return contract_amount  # Ejari renewed = annual

    if v == "new":
        # Try to compute term in years
        try:
            start = datetime.fromisoformat(start_date[:10])
            end = datetime.fromisoformat(end_date[:10])
            days = (end - start).days
            if days > 0:
                years = days / 365.25
                if years > 0:
                    return contract_amount / years
        except Exception:
            pass
    # Fallback: assume annual
    return contract_amount


# ──────────────────────────────────────────────────────────────────────────────
# Row Normalization (for CSV ingestion)
# ──────────────────────────────────────────────────────────────────────────────
def normalize_rental_row(raw_row: Dict[str, Any], source_file: str) -> Optional[Dict[str, Any]]:
    """
    Normalize a raw CSV row to standard rental contract dict.
    Returns None if row should be filtered out.

    CRITICAL: ACTUAL_AREA in source is SQM. Convert to SQFT for all internal use.
    """
    # Usage filter
    usage = _norm_text(raw_row.get("USAGE_EN", ""))
    if usage != "Residential":
        return None

    # Property type filter
    prop_type = _norm_text(raw_row.get("PROP_TYPE_EN", ""))
    if prop_type not in ("Unit", "Villa"):
        return None

    # Annual rent
    annual = parse_float(raw_row.get("ANNUAL_AMOUNT"))
    if annual is None or annual < 10_000 or annual > 5_000_000:
        return None

    # Actual area - SOURCE UNIT IS SQM, CONVERT TO SQFT
    area_sqm = parse_float(raw_row.get("ACTUAL_AREA"))
    if area_sqm is None or area_sqm < 10 or area_sqm > 20_000:
        return None
    actual_area_sqft = area_sqm * SQM_TO_SQFT

    # PSF bounds (after conversion to sqft)
    psf = annual / actual_area_sqft
    if psf < 20 or psf > 5_000:
        return None

    # Dates
    reg_date = parse_date_yyyymmdd(raw_row.get("REGISTRATION_DATE"))
    start_date = parse_date_yyyymmdd(raw_row.get("START_DATE"))
    end_date = parse_date_yyyymmdd(raw_row.get("END_DATE"))

    if not reg_date or not start_date:
        return None

    # Bedrooms
    rooms_raw = _norm_text(raw_row.get("ROOMS", ""))
    prop_sub = _norm_text(raw_row.get("PROP_SUB_TYPE_EN", ""))
    bedrooms = infer_bedrooms_from_rooms(rooms_raw, prop_sub)

    # Project / Master
    project = _norm_text(raw_row.get("PROJECT_EN", ""))
    master_project = _norm_text(raw_row.get("MASTER_PROJECT_EN", ""))

    # Total properties - MUST BE EXPLICITLY 1 (no assumption)
    tp_raw = raw_row.get("TOTAL_PROPERTIES", "")
    tp = parse_int(tp_raw) if tp_raw != "" else None
    # We track total_properties but filter later to only == 1

    # Freehold
    fh = _norm_lower(raw_row.get("IS_FREE_HOLD_EN", ""))
    is_free_hold = fh in ("free hold", "yes", "true", "1")

    return {
        "registration_date": reg_date,
        "start_date": start_date,
        "end_date": end_date,
        "version": _norm_text(raw_row.get("VERSION_EN", "New")),
        "area_en": _norm_text(raw_row.get("AREA_EN", "")),
        "annual_amount": annual,
        "actual_area_sqft": actual_area_sqft,
        "actual_area_sqm": area_sqm,  # Keep original for audit
        "prop_type_en": prop_type,
        "prop_sub_type_en": prop_sub,
        "rooms_raw": rooms_raw,
        "bedrooms": bedrooms,
        "psf": psf,
        "project_en": project,
        "master_project_en": master_project,
        "total_properties": tp,  # Can be None, int, or 1+
        "is_free_hold": is_free_hold,
        "usage_en": usage,
        "source_file": source_file,
        "property_class": infer_property_class(prop_type, prop_sub),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Aggregation Helpers
# ──────────────────────────────────────────────────────────────────────────────
def median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 0:
        return (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / 2
    return sorted_vals[n//2]


def percentile(values: List[float], p: float) -> Optional[float]:
    """p in [0, 100]"""
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if p <= 0:
        return sorted_vals[0]
    if p >= 100:
        return sorted_vals[-1]
    idx = (p / 100) * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def iqr_bounds(values: List[float], multiplier: float = 1.5) -> Tuple[Optional[float], Optional[float]]:
    """Return (lower_bound, upper_bound) using IQR method."""
    if len(values) < 4:
        return None, None
    q1 = percentile(values, 25)
    q3 = percentile(values, 75)
    if q1 is None or q3 is None:
        return None, None
    iqr = q3 - q1
    return q1 - multiplier * iqr, q3 + multiplier * iqr


def filter_outliers_iqr(values: List[float], multiplier: float = 1.5) -> List[float]:
    """Filter values using IQR outlier detection."""
    lower, upper = iqr_bounds(values, multiplier)
    if lower is None or upper is None:
        return values
    return [v for v in values if lower <= v <= upper]


def weighted_median(values: List[float], weights: List[float]) -> Optional[float]:
    """Compute weighted median."""
    if not values or not weights or len(values) != len(weights):
        return None
    pairs = sorted(zip(values, weights))
    total_weight = sum(weights)
    half = total_weight / 2
    cumsum = 0
    for v, w in pairs:
        cumsum += w
        if cumsum >= half:
            return v
    return pairs[-1][0]