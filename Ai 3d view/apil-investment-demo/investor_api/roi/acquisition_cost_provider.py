"""
investor_api/roi/acquisition_cost_provider.py

Official DLD/RERA fee rules — versioned local configuration.
No external DLD API call per property.

All rates verified from:
  - Executive Council Resolution No. 30 of 2013 (DLD fee schedule)
  - Law No. 1 of 2018 (Knowledge Dirham Fee)
  - Law No. 2 of 2018 (Innovation Dirham Fee)

TRUSTEE OFFICE FEE: NOT in DLD statute.
  Trustee offices are private entities authorised by DLD.
  Their fees are NOT fixed by official government rule.
  Therefore: status = MISSING (not OFFICIAL_VERIFIED).
  The investor must enter this as USER_INPUT if known.

DLD TRANSFER FEE PAYER ALLOCATION:
  ECR 30/2013 Article 3(1): "unless agreed otherwise, the Fee for the sale
  of Real Property will be shared equally by the seller and purchaser."
  → Statutory default: 2% buyer + 2% seller
  → However, market practice commonly has buyer pay full 4%.
  → Payer allocation is CONTRACT_DEPENDENT.
  → For buyer ROI, we use the buyer's contractual share as USER_INPUT,
    defaulting to the statutory 2% only when explicitly selected.
"""
from typing import Dict, Any


# ── Methodology version ──
METHODOLOGY_VERSION = "ACQUISITION_COST_V1_1"
VALUATION_DATE = "2026-08-22"


# ── Official fee rules (verified from statute) ──
OFFICIAL_FEE_RULES: Dict[str, Any] = {
    "methodology_version": METHODOLOGY_VERSION,
    "valuation_date": VALUATION_DATE,

    "dld_transfer": {
        "fee_name": "DLD Transfer / Registration Fee",
        "source": "OFFICIAL_DLD_RERA",
        "source_date": "2013-09-18",
        "effective_date": "2013-09-18",
        "legal_basis": "Executive Council Resolution No. 30 of 2013, Article 2, Schedule Item 1",
        "calculation_method": "PERCENTAGE_OF_SALE_VALUE",
        "total_rate_pct": 4.0,
        "buyer_statutory_share_pct": 2.0,
        "seller_statutory_share_pct": 2.0,
        "payer_allocation_status": "CONTRACT_DEPENDENT",
        "payer_rule": (
            "ECR 30/2013 Article 3(1): 'unless agreed otherwise, the Fee for "
            "the sale of Real Property will be shared equally by the seller "
            "and purchaser.' Market practice commonly has buyer pay full 4%."
        ),
        "threshold_rules": None,
        "status": "OFFICIAL_VERIFIED",
    },

    "title_deed": {
        "fee_name": "Title Deed Issuance Fee",
        "source": "OFFICIAL_DLD_RERA",
        "source_date": "2013-09-18",
        "effective_date": "2013-09-18",
        "legal_basis": "Executive Council Resolution No. 30 of 2013, Schedule Item 22",
        "calculation_method": "FIXED_AMOUNT",
        "fixed_amount_aed": 250.0,
        "percentage_rate": None,
        "threshold_rules": None,
        "payer": "Buyer (purchaser of title deed)",
        "status": "OFFICIAL_VERIFIED",
        "note": "AED 250 per title deed issuance. Does NOT include knowledge/innovation fees.",
    },

    "knowledge_fee": {
        "fee_name": "Knowledge Dirham Fee",
        "source": "OFFICIAL_DLD_RERA",
        "source_date": "2018",
        "effective_date": "2018",
        "legal_basis": "Law No. 1 of 2018 (Knowledge Dirham Fee)",
        "calculation_method": "FIXED_AMOUNT",
        "fixed_amount_aed": 10.0,
        "percentage_rate": None,
        "threshold_rules": "Not charged for transactions less than AED 50",
        "payer": "Applicant (buyer for property transactions)",
        "status": "OFFICIAL_VERIFIED",
        "note": "Charged per government service transaction. Separate from title deed fee.",
    },

    "innovation_fee": {
        "fee_name": "Innovation Dirham Fee",
        "source": "OFFICIAL_DLD_RERA",
        "source_date": "2018",
        "effective_date": "2018",
        "legal_basis": "Law No. 2 of 2018 (Innovation Dirham Fee)",
        "calculation_method": "FIXED_AMOUNT",
        "fixed_amount_aed": 10.0,
        "percentage_rate": None,
        "threshold_rules": "Not charged for transactions less than AED 50",
        "payer": "Applicant (buyer for property transactions)",
        "status": "OFFICIAL_VERIFIED",
        "note": "Charged per government service transaction. Separate from title deed fee.",
    },

    "trustee_office_fee": {
        "fee_name": "Trustee Office Fee",
        "source": "MISSING",
        "source_date": None,
        "effective_date": None,
        "legal_basis": None,
        "calculation_method": None,
        "fixed_amount_aed": None,
        "percentage_rate": None,
        "threshold_rules": None,
        "payer": "Typically buyer, but varies by trustee office",
        "status": "MISSING",
        "note": (
            "Trustee offices are private entities authorised by DLD. "
            "Their fees are NOT fixed by official government statute. "
            "Market sources cite AED 2,000–4,000 but this is NOT "
            "OFFICIAL_VERIFIED. Must be USER_INPUT."
        ),
    },

    "property_map_fee": {
        "fee_name": "Property Map / Plan Fee",
        "source": "OFFICIAL_DLD_RERA",
        "source_date": "2013-09-18",
        "effective_date": "2013-09-18",
        "legal_basis": "Executive Council Resolution No. 30 of 2013, Schedule Item 62",
        "calculation_method": "FIXED_AMOUNT",
        "fixed_amount_aed": 250.0,
        "percentage_rate": None,
        "threshold_rules": "AED 250 for villa/apartment plan; AED 100 for land map; AED 225 for unified land map (Dubai Municipality)",
        "payer": "Applicant",
        "status": "OFFICIAL_VERIFIED",
        "note": "Optional — only if a new map/plan is required. Not always charged.",
    },
}


def get_official_fee_rules() -> Dict[str, Any]:
    """Return the full official fee rules configuration."""
    return dict(OFFICIAL_FEE_RULES)


def get_dld_transfer_rules() -> Dict[str, Any]:
    """Return DLD transfer fee rules."""
    return dict(OFFICIAL_FEE_RULES["dld_transfer"])


def get_title_deed_rules() -> Dict[str, Any]:
    """Return title deed fee rules."""
    return dict(OFFICIAL_FEE_RULES["title_deed"])


def get_knowledge_fee_rules() -> Dict[str, Any]:
    """Return knowledge fee rules."""
    return dict(OFFICIAL_FEE_RULES["knowledge_fee"])


def get_innovation_fee_rules() -> Dict[str, Any]:
    """Return innovation fee rules."""
    return dict(OFFICIAL_FEE_RULES["innovation_fee"])


def get_trustee_fee_rules() -> Dict[str, Any]:
    """Return trustee fee rules."""
    return dict(OFFICIAL_FEE_RULES["trustee_office_fee"])


def get_property_map_rules() -> Dict[str, Any]:
    """Return property map fee rules."""
    return dict(OFFICIAL_FEE_RULES["property_map_fee"])
