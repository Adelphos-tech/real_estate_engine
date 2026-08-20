# RENTAL GROSS YIELD — PRODUCTION READINESS AUDIT V1

**Date**: 2026-08-20
**Calc Version (Rent)**: RENTAL_MARKET_RENT_V1_CANDIDATE
**Calc Version (Yield)**: GROSS_RENTAL_YIELD_V1_CANDIDATE
**Locked Methodology**: V1.1 (integrity-verified)
**Scope**: Estimated annual market rent + gross rental yield only. NOT Net ROI.

---

## 1. LOCKED CANDIDATE METHODOLOGY

| Parameter | Value |
|-----------|-------|
| Estimator | RECENCY_WEIGHTED_MEDIAN_ANNUAL_RENT |
| Half-life | 12 months |
| Outlier filter | IQR 1.5 |
| Size band | ±25% |
| Contract strategy | NEW_PLUS_RENEWED |
| Calibration | GLOBAL_MULTIPLICATIVE ×0.96 |
| Property type | Unit (default) |
| Min historical | 5 |
| As-of date | 2026-08-09 (latest in data) |

**No methodology tuning was performed in this audit.**

---

## 2. NOT NET ROI

This audit evaluates ONLY:
- **Estimated annual market rent** (AED/year)
- **Gross rental yield** = annual_rent_estimate / MASTER_current_price × 100

NOT calculated:
- Net ROI, net rental yield, vacancy-adjusted return
- Management fees, service charges, maintenance, financing
- Capital appreciation, IRR, total property ROI, cash-on-cash return

---

## 3. AUTHORITATIVE PRICE

Gross yield denominator = `MASTER_FINAL.xlsx` → `current_price_aed` only.

| Counter | Value | Status |
|---------|-------|--------|
| DLD_SALES_PRICE_USED_FOR_GROSS_YIELD | 0 | ✅ PASS |
| AREA_BENCHMARK_USED_FOR_GROSS_YIELD | 0 | ✅ PASS |
| QDRANT_PRICE_USED_FOR_GROSS_YIELD | 0 | ✅ PASS |

---

## 4. DETERMINISTIC TIER SELECTION

Selection rule: `R1 > R2 > R3 > R4 > NONE` (first usable tier wins).

| Tier | Selected Count |
|------|---------------|
| R1_SELECTED | 2 |
| R2_SELECTED | 142 |
| R3_SELECTED | 26 |
| R4_SELECTED | 130 |
| NONE_SELECTED | 15 |
| **Sum** | **315** ✅ |

**Reconciles to 315 Ready properties. ✅**

---

## 5. R2 vs R4 USER SEMANTICS

| Tier | Investor Label | Evidence Quality | Description |
|------|---------------|-----------------|-------------|
| R1 | Estimated Project Rent (Exact Bedroom Match) | STRONGEST | Exact project + same bedroom + similar size |
| R2 | Estimated Project Rent | STRONGER | Exact project + similar size |
| R3 | Estimated Area Rent (Bedroom Match) | STRONG | Same area + same bedroom + similar size |
| R4 | Estimated Area Rent | BROADER | Same area + similar size |

R4 is labeled "Estimated Area Rent" with "BROADER" evidence quality — clearly distinct from R2's "Estimated Project Rent" with "STRONGER" evidence quality.

---

## 6. R4 TAIL-RISK DISCLOSURE

All R4 responses include the caution:

> "Based on broader area rental comparables. Individual building rents may differ materially."

P90 percentages are NOT exposed to normal users. R4 is NOT called "verified project rent" or "exact building rent."

---

## 7. RENT INTERVAL

Every usable estimate includes:
- `annual_rent_estimate_aed` (calibrated weighted median)
- `annual_rent_p25_aed` (calibrated weighted 25th percentile)
- `annual_rent_p75_aed` (calibrated weighted 75th percentile)

**Interval verification**: P25 ≤ estimate ≤ P75 checked for all 300 estimates.
- **Violations: 0** ✅

The interval is guaranteed by construction: the weighted median is the 50th percentile of the same recency-weighted, IQR-filtered distribution from which P25 and P75 are computed. Since P25 ≤ P50 ≤ P75 by definition, the interval always holds.

---

## 8. GROSS RENTAL YIELD

Formula: `gross_rental_yield_pct = annual_rent_estimate_aed / current_price_aed × 100`

Also calculated: `gross_yield_p25_pct` and `gross_yield_p75_pct` using the same MASTER asking price.

**No capping or alteration of yield values.** Per §8, yields are reported as-is even if they appear unusually high or low.

### Yield Distribution (N=300)

| Statistic | Value |
|-----------|-------|
| Min | 1.19% |
| P25 | 4.39% |
| Median | 5.37% |
| P75 | 6.70% |
| P90 | 7.57% |
| Max | 93.87% |
| Mean | 5.87% |

### Notable yield outliers
- **Property 2725** (Saba 2, JLT, 950 sqft): 93.87% yield — MASTER price is 90,000 AED (likely a data entry error; should probably be 900,000). Rent estimate 84,480 AED is reasonable for JLT. Yield is mathematically correct per the formula.
- **Property 93** (Marina Star, Dubai Marina, 2463 sqft): 23.2% yield — MASTER price is 807,000 AED for a large unit. Rent estimate 187,200 AED. High yield but not implausible for a below-market asking price.

These are NOT capped. The formula is applied faithfully. Data quality issues in MASTER_FINAL.xlsx are outside the scope of this rental engine audit.

---

## 9. OFFPLAN

Offplan properties: **NOT EVALUATED**

| Counter | Value | Status |
|---------|-------|--------|
| OFFPLAN_CURRENT_RENT_CALCULATED | 0 | ✅ PASS |

No future completed rent is forecasted.

---

## 10. UNKNOWN STATUS

Unknown status properties: **NOT EVALUATED**

| Counter | Value | Status |
|---------|-------|--------|
| UNKNOWN_STATUS_RENT_CALCULATED | 0 | ✅ PASS |

No guessing of Ready status.

---

## 11. PRODUCTION STATUS RESOLUTION

Status source: `MASTER_FINAL.xlsx` → `unit_status` (authoritative, matches production overlay in `main_v2.py`).

| Status | Count |
|--------|-------|
| READY | 315 |
| OFFPLAN | 2,249 |
| UNKNOWN | 50 |
| **Total** | **2,614** ✅ |

Reconciles to 2,614 MASTER properties. ✅

---

## 12. PROPERTY TRACE AUDIT

### Ready Properties

| Property ID | Name | Status | MASTER Price (AED) | Tier | Annual Rent (AED) | P25 | P75 | Comparables | Projects | Gross Yield | Yield P25 | Yield P75 | Interval OK | Arith OK |
|-------------|------|--------|-------------------|------|-------------------|-----|-----|-------------|----------|-------------|-----------|-----------|-------------|----------|
| 6056 | Imperial Avenue | Ready | 6,300,000 | R2 | 278,400 | 264,000 | 297,600 | 27 | 1 | 4.42% | 4.19% | 4.72% | ✅ | ✅ |
| 6277 | Binghatti Emerald | Ready | 1,300,000 | R2 | 100,800 | 96,000 | 105,600 | 13 | 1 | 7.75% | 7.38% | 8.12% | ✅ | ✅ |
| 8057 | Binghatti Royale | Ready | 4,500,000 | R2 | 172,800 | 163,200 | 172,800 | 5 | 1 | 3.84% | 3.63% | 3.84% | ✅ | ✅ |
| 3201 | Binghatti Nova | Ready | 1,380,000 | R2 | 72,000 | 67,200 | 76,800 | 13 | 1 | 5.22% | 4.87% | 5.57% | ✅ | ✅ |
| 7061 | Azizi Mina | Ready | 4,500,000 | R4 | 172,800 | 148,800 | 200,376 | 1,081 | 18 | 3.84% | 3.31% | 4.45% | ✅ | ✅ |
| 8201 | Marquise Square | Ready | 4,300,000 | R4 | 163,200 | 143,109 | 192,004 | 834 | 44 | 3.80% | 3.33% | 4.47% | ✅ | ✅ |

### Offplan Properties (Controls)

| Property ID | Name | Status | MASTER Price (AED) | Tier | Annual Rent | Reason |
|-------------|------|--------|-------------------|------|-------------|--------|
| 3693 | Elvira | Offplan | 1,900,000 | — | NOT EVALUATED | OFFPLAN_RENTAL_NOT_EVALUATED |
| 4434 | Lime Gardens | Offplan | 2,100,000 | — | NOT EVALUATED | OFFPLAN_RENTAL_NOT_EVALUATED |
| 701 | Elvira | Offplan | 3,000,000 | — | NOT EVALUATED | OFFPLAN_RENTAL_NOT_EVALUATED |
| 3983 | Sapphire 32 | Offplan | 2,111,140 | — | NOT EVALUATED | OFFPLAN_RENTAL_NOT_EVALUATED |

**All arithmetic independently verified**: `rent / price × 100 = yield` for all 6 Ready traces. ✅

---

## 13. NO SALES SIGNAL CONTAMINATION

| Counter | Value | Status |
|---------|-------|--------|
| RENTAL_CHANGED_MARKET_CONTEXT | 0 | ✅ PASS |
| RENTAL_CHANGED_PRODUCTION_SIGNAL | 0 | ✅ PASS |
| RENTAL_CHANGED_APIL_ADVANTAGE | 0 | ✅ PASS |
| RENTAL_CHANGED_CONVENTIONAL_POSITION | 0 | ✅ PASS |
| RENTAL_CHANGED_FIT_SCORE | 0 | ✅ PASS |

Rental output does not alter any sales-side signals.

---

## 14. NO RENT VALIDATION USING ASKING PRICE

| Counter | Value | Status |
|---------|-------|--------|
| ASKING_PRICE_USED_TO_ESTIMATE_RENT | 0 | ✅ PASS |
| ASKING_PRICE_USED_TO_VALIDATE_RENT | 0 | ✅ PASS |
| YIELD_USED_TO_REJECT_RENT | 0 | ✅ PASS |

Asking price is used ONLY AFTER rent is estimated, to calculate gross yield. It never selects comparables, rejects estimates, or calibrates.

---

## 15. DATA PROVENANCE

| Item | Value | Status |
|------|-------|--------|
| Rental CSV path | `/Users/apple/Desktop/Ai 3d view/dxb_rents_all.csv` | ✅ |
| Rental CSV SHA256 | `92546471b4326a89ca5980381b918cd5077d277eae396edf0374d9448d91129d` | ✅ MATCH |
| Rental CSV rows | 573,097 | ✅ |
| MASTER path | `/Users/apple/Desktop/Ai 3d view/MASTER_FINAL.xlsx` | ✅ |
| MASTER rows | 2,614 | ✅ |

No active runtime references to:
- 650K duplicate-heavy files
- Stale 196K export (archived to `archive/stale_rental_data/`)
- Legacy ROI files

---

## 16. DETERMINISM

20 Ready properties run twice. Results compared:

| Counter | Value | Status |
|---------|-------|--------|
| RENT_ESTIMATE_NONDETERMINISTIC | 0 | ✅ PASS |
| RENT_TIER_NONDETERMINISTIC | 0 | ✅ PASS |
| GROSS_YIELD_NONDETERMINISTIC | 0 | ✅ PASS |

**All 20 properties produced identical results on both runs.** ✅

---

## 17. API SHADOW ENDPOINT

A debug/shadow endpoint concept is proposed (NOT implemented):

```
GET /debug/rental-context/{property_id}

Response:
{
  "shadow": true,
  "calc_version_rent": "RENTAL_MARKET_RENT_V1_CANDIDATE",
  "calc_version_yield": "GROSS_RENTAL_YIELD_V1_CANDIDATE",
  "property_id": "6056",
  "resolved_status": "Ready",
  "selected_rental_tier": "R2",
  "investor_label": "Estimated Project Rent",
  "evidence_quality": "STRONGER",
  "annual_rent_estimate_aed": 278400,
  "annual_rent_p25_aed": 264000,
  "annual_rent_p75_aed": 297600,
  "comparable_count": 27,
  "projects_in_pool": 1,
  "gross_rental_yield_pct": 4.42,
  "gross_yield_p25_pct": 4.19,
  "gross_yield_p75_pct": 4.72,
  "warnings": "",
  "source": "DLD rental transactions (dxb_rents_all.csv, 573K rows)"
}
```

**Normal investor UI is NOT wired.** No production investment signal is modified.

---

## 18. CALCULATION VERSION

| Component | Version |
|-----------|---------|
| Rent estimate | RENTAL_MARKET_RENT_V1_CANDIDATE |
| Gross yield | GROSS_RENTAL_YIELD_V1_CANDIDATE |

NOT called frozen or production-final.

---

## 19. FULL READY COVERAGE

| Metric | Value |
|--------|-------|
| READY_TOTAL | 315 |
| R1_SELECTED | 2 |
| R2_SELECTED | 142 |
| R3_SELECTED | 26 |
| R4_SELECTED | 130 |
| NONE_SELECTED | 15 |
| **Sum** | **315** ✅ |
| Annual rent evaluable | 300/315 (95.2%) |
| Gross yield evaluable | 300/315 (95.2%) |

15 properties have NONE (no DLD rental area mapping or insufficient comparables).

---

## 20. INVESTOR-FACING WORDING PROPOSAL

### R2 (Estimated Project Rent)

> **Estimated Annual Rent**
> AED 278,400 / year
>
> **Gross Rental Yield**
> 4.42%
>
> Based on recent comparable leases in the same project and similar-sized units.

### R4 (Estimated Area Rent)

> **Estimated Annual Rent**
> AED 163,200 / year
>
> **Gross Rental Yield**
> 3.80%
>
> Based on broader comparable leases in the surrounding area. Individual building rents may differ.

### Footer (all tiers)

> *Gross Rental Yield is estimated annual rent divided by the property's current asking price, before service charges, vacancy, management fees, maintenance, financing and other ownership costs.*

**NOT implemented in normal UI. Awaiting approval.**

---

## 21. SAFETY COUNTERS

| Counter | Value | Status |
|---------|-------|--------|
| OFFPLAN_CURRENT_RENT_CALCULATED | 0 | ✅ PASS |
| UNKNOWN_STATUS_RENT_CALCULATED | 0 | ✅ PASS |
| ASKING_PRICE_USED_TO_ESTIMATE_RENT | 0 | ✅ PASS |
| ASKING_PRICE_USED_TO_VALIDATE_RENT | 0 | ✅ PASS |
| YIELD_USED_TO_REJECT_RENT | 0 | ✅ PASS |
| DLD_SALES_PRICE_USED_FOR_GROSS_YIELD | 0 | ✅ PASS |
| AREA_BENCHMARK_USED_FOR_GROSS_YIELD | 0 | ✅ PASS |
| QDRANT_PRICE_USED_FOR_GROSS_YIELD | 0 | ✅ PASS |
| RENTAL_CHANGED_MARKET_CONTEXT | 0 | ✅ PASS |
| RENTAL_CHANGED_PRODUCTION_SIGNAL | 0 | ✅ PASS |
| RENTAL_CHANGED_APIL_ADVANTAGE | 0 | ✅ PASS |
| RENTAL_CHANGED_CONVENTIONAL_POSITION | 0 | ✅ PASS |
| RENTAL_CHANGED_FIT_SCORE | 0 | ✅ PASS |
| NET_ROI_CALCULATED | 0 | ✅ PASS |
| RENT_ESTIMATE_NONDETERMINISTIC | 0 | ✅ PASS |
| RENT_TIER_NONDETERMINISTIC | 0 | ✅ PASS |
| GROSS_YIELD_NONDETERMINISTIC | 0 | ✅ PASS |

**ALL 17 SAFETY COUNTERS AT 0. ✅**

---

## 22. OUTPUT FILES

| File | Description | Rows |
|------|-------------|------|
| `rental_outputs/rental_gross_yield_candidate_all_ready.csv` | All 315 Ready properties with rent + yield | 315 |
| `rental_outputs/rental_gross_yield_traces.csv` | 10 known property traces | 10 |
| `rental_outputs/rental_gross_yield_determinism.csv` | 20-property determinism check | 20 |
| `rental_outputs/rental_gross_yield_audit.json` | Full audit summary | — |
| `rental_outputs/RENTAL_GROSS_YIELD_PRODUCTION_READINESS_AUDIT_V1.md` | This report | — |

---

## 23. FINAL VERDICT

### **GROSS_RENTAL_YIELD_V1_READY_FOR_CONTROLLED_PRODUCTION_INTEGRATION**

**All requirements met:**

| Requirement | Status |
|-------------|--------|
| Locked V1.1 methodology (no tuning) | ✅ |
| Gross yield only (no Net ROI) | ✅ |
| Authoritative price = MASTER_FINAL only | ✅ |
| Deterministic tier selection (R1>R2>R3>R4>NONE) | ✅ |
| Sum = 315 | ✅ |
| R2/R4 different user semantics | ✅ |
| R4 tail-risk disclosure | ✅ |
| Rent interval (P25 ≤ est ≤ P75) | ✅ (0 violations) |
| Gross yield formula correct | ✅ (arithmetic verified) |
| No yield capping | ✅ |
| Offplan not evaluated | ✅ |
| Unknown not evaluated | ✅ |
| Status reconciles to 2,614 | ✅ |
| Property traces verified | ✅ (6 Ready + 4 Offplan controls) |
| No sales signal contamination | ✅ |
| No asking price in rent estimation | ✅ |
| Data provenance verified (SHA256) | ✅ |
| Determinism verified (20 properties × 2 runs) | ✅ |
| All 17 safety counters at 0 | ✅ |
| Calculation version labeled as candidate | ✅ |
| Full Ready coverage (300/315 = 95.2%) | ✅ |
| Investor-facing wording proposed | ✅ |

**Conditions for controlled production integration:**
1. Shadow endpoint only (`/debug/rental-context/{property_id}`)
2. Normal investor UI NOT wired — awaiting explicit approval
3. No Net ROI calculation
4. No modification to sales-side signals
5. R4 responses must include tail-risk disclosure
6. Yield values NOT capped or altered
7. Data quality issues in MASTER_FINAL.xlsx (e.g., property 2725 price = 90,000 AED) are outside rental engine scope

**WAITING FOR APPROVAL before any UI integration.**
