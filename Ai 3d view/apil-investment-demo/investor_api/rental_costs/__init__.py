"""
investor_api/rental_costs/ — Net Rental Income V1 Data Audit Package

STRICT ISOLATION:
  - Does NOT import or modify rental_benchmark_engine, rental_context_service,
    dld_benchmark_engine, market_context_service, or any frozen runtime.
  - Read-only dependency on rental engine outputs (annual_rent_estimate_aed, etc.)
  - NOT imported by normal request paths during this audit phase.
  - Called only from research/debug scripts (run_cost_audit.py).

Calculation versions:
  SERVICE_CHARGE_V1_AUDIT (data audit only — no calculations exposed to UI)
"""
