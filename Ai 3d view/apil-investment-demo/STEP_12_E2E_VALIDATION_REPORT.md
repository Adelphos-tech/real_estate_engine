# STEP 12 — FULL APIL ENGINE + E2E VALIDATION

**Timestamp:** 2026-08-16T19:15:43.560784
**API Base:** http://localhost:8000
**Data Source:** /Users/apple/Desktop/STEP_5_API_READY.jsonl

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | 845 |
| Passed | 845 |
| Failed | 0 |
| Warnings | 0 |
| Critical Failures | 0 |
| **Final Status** | **PASS** |

## Performance

- Total API calls: 84
- Min: 1.69ms
- Median: 2.94ms
- P95: 37.61ms
- Max: 116.49ms

## Failures
No failures.

## Invariants Verified

- Locked investment decisions are immutable across investor profiles
- Developer grades are invariant across investor profiles
- Benchmark data is invariant across investor profiles
- Objective decisions cannot be upgraded/downgraded by investor fit
- Fit score boundaries enforced (0-100)
- INSUFFICIENT_EVIDENCE excluded from default marketplace
- usable_for_investment=false → price_advantage_pct is null
- No duplicate property IDs in locked data
- No stack traces or internal paths in API errors
- API handles invalid IDs gracefully