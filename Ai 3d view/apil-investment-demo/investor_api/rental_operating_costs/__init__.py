"""
investor_api/rental_operating_costs/ — Rental Operating Cost Inputs V1

CONTROLLED USER-INPUT LAYER for vacancy, management, and maintenance.

STRICT ISOLATION:
  - Does NOT modify rental_benchmark_engine, rental_context_service,
    service_charge_provider, dld_benchmark_engine, market_context_service,
    or any frozen runtime.
  - Read-only dependency on rental_context (annual_rent_estimate_aed) and
    service_charge_context (annual_service_charge_aed, production_eligible).
  - User inputs are stored in-memory per session, NEVER written to MASTER,
    Qdrant, or any official data store.

Calculation levels:
  LEVEL 1: GROSS_RENTAL (annual rent → Gross Rental Yield)
  LEVEL 2: SERVICE_CHARGE_ADJUSTED (frozen V2 — Income After Service Charges)
  LEVEL 3: PARTIAL_OPERATING_COSTS (some costs → Income After Known Operating Costs)
  LEVEL 4: NET_RENTAL (all costs → Net Rental Income + Net Rental Yield)

Provenance sources allowed:
  OFFICIAL, VERIFIED_EXTERNAL, USER_INPUT, SELF_MANAGED, MISSING

Forbidden sources:
  ASSUMED, DEFAULT, MARKET_STANDARD, ESTIMATED_WITHOUT_EVIDENCE
"""
