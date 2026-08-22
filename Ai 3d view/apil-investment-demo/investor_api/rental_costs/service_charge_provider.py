"""
investor_api/rental_costs/service_charge_provider.py

Lightweight, read-only provider for service-charge-adjusted income.
Loads the verified mapping at import time (no per-request CSV parsing).

Returns service_charge_context for eligible properties only.
For non-eligible properties, returns a minimal block with production_eligible=false.

PRODUCTION STATE: SERVICE_CHARGE_ADJUSTED_INCOME_V2

V1 (historical): 6 properties, validation GF+RF=GT (retired as semantically incorrect)
V2 (current):    12 properties, validation GF+RF-income=GT, calculation rate=grandTotal

Corrected Mollak semantics (V2.2 research):
  grandTotal = totalGF + totalRF - income
  The income field (gfData.income) represents property-generated income
  that offsets service charges. It was not captured in V1.

V2.5 promotion: 6 new properties added (409, 8201, 1208, 5582, 3160, 7881)
  4 Canal Residence West properties remain HELD_RATE_SCOPE (unresolved tower)
"""
import json
from pathlib import Path
from functools import lru_cache
from typing import Dict, Any, Optional

# ── Production eligible property data ──
# V1 original 6 (unchanged — income=0, same rates)
# V2.5 newly promoted 6 (corrected semantics with income_offset_aed_sqft)
# Do NOT add properties here without a full audit + promotion process.
_FROZEN_ELIGIBLE: Dict[str, Dict[str, Any]] = {
    "4744": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": True,
        "project_match_status": "VERIFIED_EXACT",
        "service_charge_status": "VERIFIED_CALCULABLE",
        "service_charge_source": "DLD/RERA Mollak",
        "service_charge_year": 2026,
        "service_charge_rate_aed_sqft": 20.26,
        "mollak_project_name": "Ahad Residences",
        "annual_service_charge_aed": 46760.08,
        "income_after_service_charges_aed": 116439.92,
        "yield_after_service_charges_pct": 2.48,
        "included_costs": ["Estimated annual market rent", "Official DLD/RERA Mollak service charges"],
        "excluded_costs": ["Vacancy", "Landlord property management", "Unit maintenance"],
    },
    "6435": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": True,
        "project_match_status": "VERIFIED_EXACT",
        "service_charge_status": "VERIFIED_CALCULABLE",
        "service_charge_source": "DLD/RERA Mollak",
        "service_charge_year": 2025,
        "service_charge_rate_aed_sqft": 14.60,
        "mollak_project_name": "PANTHEON ELYSEE",
        "annual_service_charge_aed": 11139.80,
        "income_after_service_charges_aed": 56060.20,
        "yield_after_service_charges_pct": 6.60,
        "included_costs": ["Estimated annual market rent", "Official DLD/RERA Mollak service charges"],
        "excluded_costs": ["Vacancy", "Landlord property management", "Unit maintenance"],
    },
    "7266": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": True,
        "project_match_status": "VERIFIED_EXACT",
        "service_charge_status": "VERIFIED_CALCULABLE",
        "service_charge_source": "DLD/RERA Mollak",
        "service_charge_year": 2026,
        "service_charge_rate_aed_sqft": 20.26,
        "mollak_project_name": "Ahad Residences",
        "annual_service_charge_aed": 18112.44,
        "income_after_service_charges_aed": 92287.56,
        "yield_after_service_charges_pct": 5.13,
        "included_costs": ["Estimated annual market rent", "Official DLD/RERA Mollak service charges"],
        "excluded_costs": ["Vacancy", "Landlord property management", "Unit maintenance"],
    },
    "1074": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": True,
        "project_match_status": "VERIFIED_EXACT",
        "service_charge_status": "VERIFIED_CALCULABLE",
        "service_charge_source": "DLD/RERA Mollak",
        "service_charge_year": 2026,
        "service_charge_rate_aed_sqft": 20.26,
        "mollak_project_name": "Ahad Residences",
        "annual_service_charge_aed": 9177.78,
        "income_after_service_charges_aed": 67622.22,
        "yield_after_service_charges_pct": 5.41,
        "included_costs": ["Estimated annual market rent", "Official DLD/RERA Mollak service charges"],
        "excluded_costs": ["Vacancy", "Landlord property management", "Unit maintenance"],
    },
    "4165": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": True,
        "project_match_status": "VERIFIED_EXACT",
        "service_charge_status": "VERIFIED_CALCULABLE",
        "service_charge_source": "DLD/RERA Mollak",
        "service_charge_year": 2026,
        "service_charge_rate_aed_sqft": 20.26,
        "mollak_project_name": "Ahad Residences",
        "annual_service_charge_aed": 32922.50,
        "income_after_service_charges_aed": 154277.50,
        "yield_after_service_charges_pct": 4.72,
        "included_costs": ["Estimated annual market rent", "Official DLD/RERA Mollak service charges"],
        "excluded_costs": ["Vacancy", "Landlord property management", "Unit maintenance"],
    },
    "7842": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": True,
        "project_match_status": "VERIFIED_NORMALIZED_EXACT",
        "service_charge_status": "VERIFIED_CALCULABLE",
        "service_charge_source": "DLD/RERA Mollak",
        "service_charge_year": 2026,
        "service_charge_rate_aed_sqft": 12.11,
        "mollak_project_name": "AZIZI. FEIROUZ",
        "annual_service_charge_aed": 12206.88,
        "income_after_service_charges_aed": 58353.12,
        "yield_after_service_charges_pct": 5.72,
        "included_costs": ["Estimated annual market rent", "Official DLD/RERA Mollak service charges"],
        "excluded_costs": ["Vacancy", "Landlord property management", "Unit maintenance"],
    },
    # ── V2.5 promoted properties (corrected Mollak semantics: GT = GF + RF - income) ──
    "409": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": True,
        "project_match_status": "VERIFIED_ALIAS",
        "service_charge_status": "VERIFIED_CALCULABLE",
        "service_charge_source": "DLD/RERA Mollak",
        "service_charge_year": 2026,
        "service_charge_rate_aed_sqft": 16.82,
        "total_gf_aed_sqft": 15.61,
        "total_rf_aed_sqft": 1.28,
        "income_offset_aed_sqft": 0.07,
        "grand_total_aed_sqft": 16.82,
        "mollak_project_name": "HARBOUR VIEWS",
        "annual_service_charge_aed": 25667.32,
        "income_after_service_charges_aed": 137532.68,
        "yield_after_service_charges_pct": 5.09,
        "included_costs": ["Estimated annual market rent", "Official DLD/RERA Mollak service charges"],
        "excluded_costs": ["Vacancy", "Landlord property management", "Unit maintenance"],
    },
    "8201": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": True,
        "project_match_status": "VERIFIED",
        "service_charge_status": "VERIFIED_CALCULABLE",
        "service_charge_source": "DLD/RERA Mollak",
        "service_charge_year": 2026,
        "service_charge_rate_aed_sqft": 16.85,
        "total_gf_aed_sqft": 15.85,
        "total_rf_aed_sqft": 1.09,
        "income_offset_aed_sqft": 0.09,
        "grand_total_aed_sqft": 16.85,
        "mollak_project_name": "MARQUISE SQUARE TOWER",
        "annual_service_charge_aed": 39193.10,
        "income_after_service_charges_aed": 124006.90,
        "yield_after_service_charges_pct": 2.88,
        "included_costs": ["Estimated annual market rent", "Official DLD/RERA Mollak service charges"],
        "excluded_costs": ["Vacancy", "Landlord property management", "Unit maintenance"],
    },
    "1208": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": True,
        "project_match_status": "VERIFIED",
        "service_charge_status": "VERIFIED_CALCULABLE",
        "service_charge_source": "DLD/RERA Mollak",
        "service_charge_year": 2026,
        "service_charge_rate_aed_sqft": 16.85,
        "total_gf_aed_sqft": 15.85,
        "total_rf_aed_sqft": 1.09,
        "income_offset_aed_sqft": 0.09,
        "grand_total_aed_sqft": 16.85,
        "mollak_project_name": "MARQUISE SQUARE TOWER",
        "annual_service_charge_aed": 17928.40,
        "income_after_service_charges_aed": 78071.60,
        "yield_after_service_charges_pct": 3.72,
        "included_costs": ["Estimated annual market rent", "Official DLD/RERA Mollak service charges"],
        "excluded_costs": ["Vacancy", "Landlord property management", "Unit maintenance"],
    },
    "5582": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": True,
        "project_match_status": "VERIFIED",
        "service_charge_status": "VERIFIED_CALCULABLE",
        "service_charge_source": "DLD/RERA Mollak",
        "service_charge_year": 2026,
        "service_charge_rate_aed_sqft": 16.85,
        "total_gf_aed_sqft": 15.85,
        "total_rf_aed_sqft": 1.09,
        "income_offset_aed_sqft": 0.09,
        "grand_total_aed_sqft": 16.85,
        "mollak_project_name": "MARQUISE SQUARE TOWER",
        "annual_service_charge_aed": 27937.30,
        "income_after_service_charges_aed": 101662.70,
        "yield_after_service_charges_pct": 3.51,
        "included_costs": ["Estimated annual market rent", "Official DLD/RERA Mollak service charges"],
        "excluded_costs": ["Vacancy", "Landlord property management", "Unit maintenance"],
    },
    "3160": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": True,
        "project_match_status": "VERIFIED",
        "service_charge_status": "VERIFIED_CALCULABLE",
        "service_charge_source": "DLD/RERA Mollak",
        "service_charge_year": 2026,
        "service_charge_rate_aed_sqft": 16.85,
        "total_gf_aed_sqft": 15.85,
        "total_rf_aed_sqft": 1.09,
        "income_offset_aed_sqft": 0.09,
        "grand_total_aed_sqft": 16.85,
        "mollak_project_name": "MARQUISE SQUARE TOWER",
        "annual_service_charge_aed": 8711.45,
        "income_after_service_charges_aed": 48888.55,
        "yield_after_service_charges_pct": 3.99,
        "included_costs": ["Estimated annual market rent", "Official DLD/RERA Mollak service charges"],
        "excluded_costs": ["Vacancy", "Landlord property management", "Unit maintenance"],
    },
    "7881": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": True,
        "project_match_status": "VERIFIED",
        "service_charge_status": "VERIFIED_CALCULABLE",
        "service_charge_source": "DLD/RERA Mollak",
        "service_charge_year": 2026,
        "service_charge_rate_aed_sqft": 16.50,
        "total_gf_aed_sqft": 16.15,
        "total_rf_aed_sqft": 0.57,
        "income_offset_aed_sqft": 0.22,
        "grand_total_aed_sqft": 16.50,
        "mollak_project_name": "THE DUBAI CREEK RESIDENCES",
        "annual_service_charge_aed": 16830.00,
        "income_after_service_charges_aed": 103170.00,
        "yield_after_service_charges_pct": 7.37,
        "included_costs": ["Estimated annual market rent", "Official DLD/RERA Mollak service charges"],
        "excluded_costs": ["Vacancy", "Landlord property management", "Unit maintenance"],
    },
}

# ── Held properties (identity verified but rate scope unresolved) ──
# Canal Residence West Phase 1 has 3 separate Mollak residential groups
# (European=13.92, Venetian=13.91, Mediterranean=13.94) with different rates.
# MASTER/Qdrant do not identify which tower each property belongs to.
# Do NOT use a representative rate. Do NOT promote until tower is resolved.
_HELD: Dict[str, Dict[str, Any]] = {
    "884": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": False,
        "project_match_status": "VERIFIED_PHASE_1",
        "service_charge_status": "HELD_RATE_SCOPE",
        "service_charge_source": None,
        "service_charge_year": None,
        "service_charge_rate_aed_sqft": None,
        "mollak_project_name": "CANAL RESIDENCE WEST (PHASE 1)",
        "annual_service_charge_aed": None,
        "income_after_service_charges_aed": None,
        "yield_after_service_charges_pct": None,
        "included_costs": [],
        "excluded_costs": [],
    },
    "4702": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": False,
        "project_match_status": "VERIFIED_PHASE_1",
        "service_charge_status": "HELD_RATE_SCOPE",
        "service_charge_source": None,
        "service_charge_year": None,
        "service_charge_rate_aed_sqft": None,
        "mollak_project_name": "CANAL RESIDENCE WEST (PHASE 1)",
        "annual_service_charge_aed": None,
        "income_after_service_charges_aed": None,
        "yield_after_service_charges_pct": None,
        "included_costs": [],
        "excluded_costs": [],
    },
    "4750": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": False,
        "project_match_status": "VERIFIED_PHASE_1",
        "service_charge_status": "HELD_RATE_SCOPE",
        "service_charge_source": None,
        "service_charge_year": None,
        "service_charge_rate_aed_sqft": None,
        "mollak_project_name": "CANAL RESIDENCE WEST (PHASE 1)",
        "annual_service_charge_aed": None,
        "income_after_service_charges_aed": None,
        "yield_after_service_charges_pct": None,
        "included_costs": [],
        "excluded_costs": [],
    },
    "5513": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": False,
        "project_match_status": "VERIFIED_PHASE_1",
        "service_charge_status": "HELD_RATE_SCOPE",
        "service_charge_source": None,
        "service_charge_year": None,
        "service_charge_rate_aed_sqft": None,
        "mollak_project_name": "CANAL RESIDENCE WEST (PHASE 1)",
        "annual_service_charge_aed": None,
        "income_after_service_charges_aed": None,
        "yield_after_service_charges_pct": None,
        "included_costs": [],
        "excluded_costs": [],
    },
}

# ── Rejected properties (permanently blacklisted) ──
_REJECTED: Dict[str, Dict[str, Any]] = {
    "6217": {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": False,
        "project_match_status": "REJECTED_IDENTITY",
        "service_charge_status": "NOT_MATCHED",
        "service_charge_source": None,
        "service_charge_year": None,
        "service_charge_rate_aed_sqft": None,
        "mollak_project_name": None,
        "annual_service_charge_aed": None,
        "income_after_service_charges_aed": None,
        "yield_after_service_charges_pct": None,
        "included_costs": [],
        "excluded_costs": [],
    },
}


def get_service_charge_context(property_id: str) -> Dict[str, Any]:
    """
    Return the service_charge_context block for a property.

    For eligible properties: full context with calculated values.
    For held/rejected: minimal block with production_eligible=false.
    For all others: minimal block with production_eligible=false and NOT_MATCHED.

    This is O(1) dict lookup — no CSV parsing, no heavy computation.
    """
    pid = str(property_id)

    if pid in _FROZEN_ELIGIBLE:
        return dict(_FROZEN_ELIGIBLE[pid])

    if pid in _HELD:
        return dict(_HELD[pid])

    if pid in _REJECTED:
        return dict(_REJECTED[pid])

    # Default: not matched
    return {
        "calculation_level": "SERVICE_CHARGE_ADJUSTED",
        "production_eligible": False,
        "project_match_status": "NOT_MATCHED",
        "service_charge_status": "NOT_MATCHED",
        "service_charge_source": None,
        "service_charge_year": None,
        "service_charge_rate_aed_sqft": None,
        "mollak_project_name": None,
        "annual_service_charge_aed": None,
        "income_after_service_charges_aed": None,
        "yield_after_service_charges_pct": None,
        "included_costs": [],
        "excluded_costs": [],
    }
