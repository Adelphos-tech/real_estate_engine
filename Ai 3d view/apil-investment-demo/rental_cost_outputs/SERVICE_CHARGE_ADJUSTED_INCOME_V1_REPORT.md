# SERVICE CHARGE ADJUSTED INCOME V1 — SHADOW CALCULATION REPORT

**Date**: 2026-08-20
**Verdict**: **SERVICE_CHARGE_ADJUSTED_INCOME_V1_SHADOW_VERIFIED**
**Phase**: Shadow/debug calculation only — no UI changes, no Net Rental Income

---

## 1. SUMMARY

| Metric | Value |
|--------|-------|
| Verified properties | 8 |
| Successfully calculable | 8 |
| Arithmetic failures | 0 |
| Harbour Views alias confirmed | YES |
| Calculation level | SERVICE_CHARGE_ADJUSTED |

---

## 2. CALCULATION FORMULAS

### Service Charge
```
annual_service_charge_aed = official_mollak_rate_aed_sqft × MASTER unit_size_sqft
```

### Income After Service Charges
```
income_after_service_charges_aed = annual_rent_estimate_aed - annual_service_charge_aed
```

### Yield After Service Charges
```
yield_after_service_charges_pct = income_after_service_charges_aed / MASTER current_price_aed × 100
```

### Labels
- **Income label**: "Income After Service Charges" (NOT "Net Rental Income")
- **Yield label**: "Yield After Service Charges" (NOT "Net Rental Yield")

---

## 3. HARBOUR VIEWS ALIAS CONFIRMATION

| Check | MASTER (409) | Mollak (HARBOUR VIEWS) | Match |
|-------|-------------|----------------------|-------|
| Project name | Harbour Views 1 | HARBOUR VIEWS | Phase normalization |
| Area/Community | Dubai Creek Harbour | Dubai Creek Harbour | ✅ |
| Developer | Emaar | EMAAR COMMUNITY MANAGEMENT | ✅ |

**HARBOUR_VIEWS_ALIAS_PRODUCTION_CONFIRMED = YES**

Both area (Dubai Creek Harbour) and developer (Emaar) cross-checks confirm the alias is legitimate.

---

## 4. ALL 8 CALCULATED PROPERTIES

| Property ID | Project | Match Method | SC Year | Rate (AED/sqft) | Size (sqft) | Annual SC (AED) | Annual Rent (AED) | Income After SC (AED) | Price (AED) | Gross Yield | Yield After SC |
|-------------|---------|-------------|---------|-----------------|-------------|-----------------|-------------------|----------------------|-------------|-------------|----------------|
| 4744 | Ahad Residences | EXACT | 2026 | 20.26 | 2,308 | 46,760 | 163,200 | 116,440 | 4,700,000 | 3.47% | 2.48% |
| 6435 | Pantheon Elysee | EXACT | 2025 | 14.60 | 763 | 11,140 | 67,200 | 56,060 | 849,000 | 7.92% | 6.60% |
| 7266 | Ahad Residences | EXACT | 2026 | 20.26 | 894 | 18,112 | 110,400 | 92,288 | 1,800,000 | 6.13% | 5.13% |
| 1074 | Ahad Residences | EXACT | 2026 | 20.26 | 453 | 9,178 | 76,800 | 67,622 | 1,250,000 | 6.14% | 5.41% |
| 6217 | Golf Links | EXACT | 2026 | 18.36 | 4,309 | 79,113 | 122,880 | 43,767 | 4,100,000 | 3.00% | 1.07% |
| 4165 | Ahad Residences | EXACT | 2026 | 20.26 | 1,625 | 32,923 | 187,200 | 154,278 | 3,270,000 | 5.72% | 4.72% |
| 7842 | Azizi Feirouz | NORMALIZED_EXACT | 2026 | 12.11 | 1,008 | 12,207 | 70,560 | 58,353 | 1,020,000 | 6.92% | 5.72% |
| 409 | Harbour Views 1 | VERIFIED_ALIAS | 2026 | 16.82 | 1,526 | 25,667 | 163,200 | 137,533 | 2,700,000 | 6.04% | 5.09% |

### Key Observations

- **Golf Links (6217)**: Service charges consume 64% of rental income (79,113 / 122,880). Yield drops from 3.00% to 1.07%. This is a large villa (4,309 sqft) with high absolute service charges.
- **Ahad Residences (4744)**: Service charges consume 29% of rental income. Yield drops from 3.47% to 2.48%.
- **Pantheon Elysee (6435)**: Service charges consume 17% of rental income. Yield drops from 7.92% to 6.60% — still the highest yield after service charges.
- **Azizi Feirouz (7842)**: Service charges consume 17% of rental income. Yield drops from 6.92% to 5.72%.

---

## 5. ARITHMETIC VALIDATION

| Check | Mismatches | Status |
|-------|-----------|--------|
| SERVICE_CHARGE_ARITHMETIC_MISMATCH | 0 | ✅ |
| ADJUSTED_INCOME_ARITHMETIC_MISMATCH | 0 | ✅ |
| ADJUSTED_YIELD_ARITHMETIC_MISMATCH | 0 | ✅ |

All 8 properties pass independent arithmetic verification:
- `rate × sqft = annual_service_charge_aed` ✅
- `annual_rent - annual_service_charge = income_after_service_charges` ✅
- `income_after_service_charges / price × 100 = yield_after_service_charges` ✅

---

## 6. CALCULATION LEVEL DISCLOSURE

```json
{
  "calculation_level": "SERVICE_CHARGE_ADJUSTED",
  "cost_coverage": {
    "annual_rent": "AVAILABLE",
    "service_charge": "VERIFIED",
    "vacancy": "MISSING",
    "management": "MISSING",
    "maintenance": "MISSING"
  },
  "NOT_INCLUDED": ["vacancy", "landlord_management", "unit_maintenance"],
  "label_income": "Income After Service Charges",
  "label_yield": "Yield After Service Charges",
  "explicit_disclaimer": "Only one verified operating cost (service charge) has been deducted. This is NOT Net Rental Income."
}
```

### What This IS
- Income after deducting **one** verified operating cost (official DLD/Mollak service charge)
- A more conservative yield than Gross Rental Yield
- Based on official, verified data only

### What This IS NOT
- Net Rental Income (requires vacancy, management, maintenance)
- Net Rental Yield
- Property ROI
- Total ROI

---

## 7. ENGINE ISOLATION — ALL SAFETY COUNTERS AT 0

| Counter | Value | Status |
|---------|-------|--------|
| SERVICE_CHARGE_LAYER_CHANGED_RENT_ESTIMATE | 0 | ✅ |
| SERVICE_CHARGE_LAYER_CHANGED_RENT_TIER | 0 | ✅ |
| SERVICE_CHARGE_LAYER_CHANGED_GROSS_YIELD | 0 | ✅ |
| SERVICE_CHARGE_LAYER_CHANGED_MARKET_CONTEXT | 0 | ✅ |
| SERVICE_CHARGE_LAYER_CHANGED_PRODUCTION_SIGNAL | 0 | ✅ |
| SERVICE_CHARGE_LAYER_CHANGED_APIL_ADVANTAGE | 0 | ✅ |
| SERVICE_CHARGE_LAYER_CHANGED_CONVENTIONAL_POSITION | 0 | ✅ |
| SERVICE_CHARGE_LAYER_CHANGED_FIT_SCORE | 0 | ✅ |
| NORMAL_PROPERTY_API_PERFORMANCE_CHANGED | 0 | ✅ |
| RENTAL_ENDPOINT_PERFORMANCE_CHANGED | 0 | ✅ |

**All 10 safety counters at 0.** No existing runtime modified.

---

## 8. DATA QUALITY OBSERVATIONS

1. **Golf Links (6217)**: The yield after service charges (1.07%) is very low. This is a 4,309 sqft villa with AED 79,113/year in service charges. The service charge-to-rent ratio (64%) is unusually high. This may indicate either high service charges for this property type or a low rent estimate. No data is altered — this is disclosure only.

2. **Ahad Residences**: 4 of 8 verified properties are in Ahad Residences. This gives good coverage for this specific project but highlights the limited overall coverage (8/315 = 2.5%).

3. **No data-quality warnings triggered**: None of the 8 properties have yields after service charges that would trigger a data-quality warning (no threshold defined for this layer yet).

---

## 9. OUTPUT FILES

| File | Description |
|------|-------------|
| `rental_cost_outputs/service_charge_adjusted_income_v1.csv` | 8 properties with all calculations |
| `rental_cost_outputs/service_charge_adjusted_income_v1_debug.json` | Debug/calculation level metadata |
| `rental_cost_outputs/service_charge_adjusted_income_v1_verdict.json` | Verdict data |
| `rental_cost_outputs/SERVICE_CHARGE_ADJUSTED_INCOME_V1_REPORT.md` | This report |

---

## 10. VERDICT

### **SERVICE_CHARGE_ADJUSTED_INCOME_V1_SHADOW_VERIFIED**

| Check | Result |
|-------|--------|
| Verified properties | 8 |
| Successfully calculable | 8 |
| Arithmetic failures | 0 |
| Harbour Views alias confirmed | YES |
| All safety counters | 0 |
| Engine isolation | ✅ |

**STOP. No UI wired. No vacancy calculated. No Net Rental Income calculated. No Full Property ROI started. Waiting for explicit approval.**
