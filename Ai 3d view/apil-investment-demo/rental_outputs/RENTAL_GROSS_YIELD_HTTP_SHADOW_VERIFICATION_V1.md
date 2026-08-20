# GROSS RENTAL YIELD V1 — HTTP SHADOW VERIFICATION REPORT

**Date**: 2026-08-20
**Verdict**: **GROSS_RENTAL_YIELD_V1_HTTP_SHADOW_VERIFIED**
**Endpoint**: `GET /debug/rental-context/{property_id}`
**Normal Investor UI**: NOT WIRED — awaiting explicit approval

---

## 1. SHADOW ENDPOINT IMPLEMENTATION

**Endpoint**: `GET /debug/rental-context/{property_id}`

**File**: `investor_api/main_v2.py` (lines ~2796–2848)
**Service**: `investor_api/rental/rental_context_service.py`

### Response Fields

| Field | Description |
|-------|-------------|
| `shadow` | Always `true` — marks this as shadow-only |
| `property_id` | Property ID |
| `property_name` | Property name |
| `resolved_status` | Ready / Offplan / Unknown (from production path) |
| `selected_rental_tier` | R1 / R2 / R3 / R4 / NONE |
| `investor_label` | Human-readable tier label |
| `evidence_quality` | STRONGEST / STRONGER / STRONG / BROADER / NONE |
| `annual_rent_estimate_aed` | Calibrated estimated annual rent |
| `annual_rent_p25_aed` | Calibrated P25 rent |
| `annual_rent_p75_aed` | Calibrated P75 rent |
| `comparable_count` | Number of comparable contracts |
| `projects_in_pool` | Number of distinct projects in pool |
| `gross_rental_yield_pct` | Gross yield = rent / MASTER price × 100 |
| `gross_yield_p25_pct` | P25 yield |
| `gross_yield_p75_pct` | P75 yield |
| `warnings` | Tier-specific disclosure (R4 tail-risk) |
| `data_quality_warning` | Yield anomaly warning (disclosure only) |
| `calc_version_rent` | `RENTAL_MARKET_RENT_V1_CANDIDATE` |
| `calc_version_yield` | `GROSS_RENTAL_YIELD_V1_CANDIDATE` |
| `master_available` | Whether MASTER data was available |
| `rental_csv_sha256` | SHA256 of rental CSV |
| `rental_csv_rows` | Row count of rental CSV |
| `rental_csv_path` | Path to rental CSV |

### Normal investor UI is NOT modified.

---

## 2. STATUS PARITY

**Requirement**: Rental endpoint must use the SAME status-resolution function/path as the normal production API.

**Implementation**: The shadow endpoint calls `_build_apil_attributes(r, enrichment)` — the exact same function used by `/properties/{property_id}`. This function resolves status via:
1. MASTER `unit_status` (authoritative, takes precedence)
2. `_resolve_property_status()` (canonical resolver: Qdrant > DLD > APIL)

The rental endpoint does NOT independently recreate status logic.

### Results (all 2,614 properties)

| Status | Normal API Count | Rental Endpoint Count | Match |
|--------|-----------------|----------------------|-------|
| Ready | 315 | 315 | ✅ |
| Offplan | 2,249 | 2,249 | ✅ |
| Unknown | 50 | 50 | ✅ |
| **Total** | **2,614** | **2,614** | ✅ |

**RENTAL_STATUS_PARITY_MISMATCH = 0** ✅

### Specific test properties

| Property ID | Normal API Status | Rental Endpoint Status | Match |
|-------------|-------------------|----------------------|-------|
| 4204 | Offplan | Offplan | ✅ |
| 6834 | Offplan | Offplan | ✅ |

---

## 3. NORMAL API SAFETY REGRESSION

**Requirement**: Implementing the debug endpoint must not alter market_context, production_signal, APIL advantage, conventional position, or investor fit.

**Method**: For 20 properties, call `/properties/{id}` before and after calling `/debug/rental-context/{id}`. Compare key fields.

| Counter | Value | Status |
|---------|-------|--------|
| RENTAL_CHANGED_MARKET_CONTEXT | 0 | ✅ PASS |
| RENTAL_CHANGED_PRODUCTION_SIGNAL | 0 | ✅ PASS |
| RENTAL_CHANGED_APIL_ADVANTAGE | 0 | ✅ PASS |
| RENTAL_CHANGED_CONVENTIONAL_POSITION | 0 | ✅ PASS |
| RENTAL_CHANGED_FIT_SCORE | 0 | ✅ PASS |

**All zero.** ✅

---

## 4. RENTAL SOURCE PARITY

| Item | Value | Status |
|------|-------|--------|
| Rental CSV path | `/Users/apple/Desktop/Ai 3d view/dxb_rents_all.csv` | ✅ |
| Rental CSV SHA256 | `92546471b4326a89ca5980381b918cd5077d277eae396edf0374d9448d91129d` | ✅ MATCH |
| Rental CSV rows | 573,097 | ✅ |

**SHA256 is the authoritative identity.** The previous documentation claim of 573,001 rows was incorrect. The actual row count is 573,097, verified by SHA256 match. The production readiness audit report has been updated to reflect this.

---

## 5. DATA-QUALITY WARNING

**Requirement**: Add a disclosure-only warning for unusual yields. Must NOT change rent, yield, price, or APIL signal.

**Implementation**: When `gross_rental_yield_pct > 15%`, the response includes:

```
"data_quality_warning": "Gross yield is unusually high relative to the supplied asking price. Verify property price before relying on this figure."
```

### Example: Property 2725

```json
{
  "property_id": "2725",
  "resolved_status": "Ready",
  "selected_rental_tier": "R4",
  "annual_rent_estimate_aed": 84480.0,
  "gross_rental_yield_pct": 93.87,
  "data_quality_warning": "Gross yield is unusually high relative to the supplied asking price. Verify property price before relying on this figure."
}
```

**The warning does NOT:**
- Change the rent estimate (84,480 AED)
- Change the yield (93.87%)
- Change the property price (90,000 AED from MASTER)
- Change any APIL signal

**No claim is made about what the "correct" price should be.**

---

## 6. TRACE ENDPOINT MISMATCH

**Requirement**: Compare debug rental endpoint results vs production-readiness audit results.

| Property ID | Status | Tier | Rent (AED) | Yield | Match |
|-------------|--------|------|-----------|-------|-------|
| 6056 | Ready | R2 | 278,400 | 4.42% | ✅ |
| 6277 | Ready | R2 | 100,800 | 7.75% | ✅ |
| 8057 | Ready | R2 | 172,800 | 3.84% | ✅ |
| 3201 | Ready | R2 | 72,000 | 5.22% | ✅ |
| 7061 | Ready | R4 | 172,800 | 3.84% | ✅ |
| 8201 | Ready | R4 | 163,200 | 3.80% | ✅ |
| 2725 | Ready | R4 | 84,480 | 93.87% | ✅ |
| 3693 | Offplan | NONE | — | — | ✅ |
| 4434 | Offplan | NONE | — | — | ✅ |
| 701 | Offplan | NONE | — | — | ✅ |
| 3983 | Offplan | NONE | — | — | ✅ |

**RENT_TRACE_MISMATCH = 0** ✅

No results changed due to status resolution parity — the production path and the audit both resolve to the same statuses.

---

## 7. FULL HTTP COVERAGE

**All 2,614 properties hit via HTTP.**

| Category | Count |
|----------|-------|
| Ready evaluated | 300 |
| Ready NONE | 15 |
| Offplan not evaluated | 2,249 |
| Unknown not evaluated | 50 |
| **Total** | **2,614** ✅ |

### Selected Tiers

| Tier | Count |
|------|-------|
| R1 | 2 |
| R2 | 142 |
| R3 | 26 |
| R4 | 130 |
| NONE | 2,314 |
| **Sum** | **2,614** ✅ |

NONE = 2,314 = 15 (Ready no data) + 2,249 (Offplan) + 50 (Unknown) = 2,314 ✅

---

## 8. PERFORMANCE

| Metric | Value |
|--------|-------|
| Cold first request | 3 ms |
| Warm request median | 4 ms |
| Warm request P95 | 7 ms |

**Rental CSV is loaded/indexed once** at startup via the `RentalDataStore` singleton. The `RentalCandidateComparator` is also cached as a module-level singleton in `rental_context_service.py`. No reloading per request.

**No methodology optimization was performed.** The performance is a natural result of the singleton pattern + pre-built indices.

---

## 9. FINAL VERDICT

### **GROSS_RENTAL_YIELD_V1_HTTP_SHADOW_VERIFIED**

| Check | Status |
|-------|--------|
| Rental source SHA256 match | ✅ |
| Status parity mismatch = 0 | ✅ |
| Normal API safety all zero | ✅ |
| Trace mismatch = 0 | ✅ |
| Full coverage reconciles to 2,614 | ✅ |

### What is verified
- Shadow endpoint `GET /debug/rental-context/{property_id}` is live and returns all required fields
- Status resolution uses the SAME production path (`_build_apil_attributes` → MASTER > `_resolve_property_status`)
- All 2,614 properties produce identical status via both paths
- No production signal is altered (market_context, production_signal, APIL advantage, conventional position, fit)
- All 11 trace properties match the audit exactly
- Data-quality warning is disclosure-only (no capping, no price changes)
- Rental CSV SHA256 verified
- Performance: cold 3ms, warm median 4ms, P95 7ms
- Rental store loaded once (singleton)

### What is NOT done
- Normal investor UI is NOT wired
- No Net ROI calculation
- No full-property ROI
- No modification to any production signal

### Output Files

| File | Description |
|------|-------------|
| `rental_outputs/rental_http_status_parity.csv` | Status parity for all 2,614 properties |
| `rental_outputs/rental_http_trace_mismatch.csv` | 11 trace property comparisons |
| `rental_outputs/rental_http_full_coverage.csv` | All 2,614 properties via HTTP |
| `rental_outputs/rental_http_performance.json` | Performance metrics |
| `rental_outputs/rental_http_verdict.json` | Full verdict data |
| `rental_outputs/RENTAL_GROSS_YIELD_HTTP_SHADOW_VERIFICATION_V1.md` | This report |

---

**WAITING FOR APPROVAL before any normal UI integration or full-property ROI.**
