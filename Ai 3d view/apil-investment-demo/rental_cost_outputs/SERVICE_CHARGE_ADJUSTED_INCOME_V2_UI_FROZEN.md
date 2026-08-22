# SERVICE CHARGE ADJUSTED INCOME V2 — UI FROZEN

**Freeze Date**: 2026-08-21
**Freeze Identifier**: `SERVICE_CHARGE_ADJUSTED_INCOME_V2_UI_FROZEN`
**Status**: FROZEN — UI

---

## 1. UI COMPONENT

| Item | Value |
|------|-------|
| Component | `src/components/RentalIncomeCard.tsx` |
| Behavior | Existing component — no new component created |
| Gating | `serviceCharge.production_eligible === true && serviceCharge.annual_service_charge_aed !== null` |
| No UI logic duplication | YES ✅ |

---

## 2. ELIGIBLE UI PROPERTIES (12)

All 12 production-eligible properties display the service-charge-adjusted income section:

| Property ID | Project | Eligible | Shows SC Section |
|-------------|---------|----------|-----------------|
| 4744 | Ahad Residences | True | YES |
| 6435 | Pantheon Elysee | True | YES |
| 7266 | Ahad Residences | True | YES |
| 1074 | Ahad Residences | True | YES |
| 4165 | Ahad Residences | True | YES |
| 7842 | Azizi Feirouz | True | YES |
| 409 | Harbour Views 1 | True | YES |
| 8201 | Marquise Square | True | YES |
| 1208 | Marquise Square | True | YES |
| 5582 | Marquise Square | True | YES |
| 3160 | Marquise Square | True | YES |
| 7881 | Dubai Creek Residence T2N | True | YES |

---

## 3. UI LABELS

| Label | Source Field | Used |
|-------|-------------|------|
| Official Service Charges | `annual_service_charge_aed` | YES ✅ |
| Income After Service Charges | `income_after_service_charges_aed` | YES ✅ |
| Yield After Service Charges | `yield_after_service_charges_pct` | YES ✅ |

### Labels NEVER Used

| Forbidden Label | Used |
|----------------|------|
| Net Rental Income | NO ✅ |
| Net Rental Yield | NO ✅ |
| Net Income | NO ✅ |
| Net Yield | NO ✅ |

---

## 4. DISCLOSURE TEXT

Displayed at the bottom of the service-charge section:

> "Income After Service Charges deducts verified official service charges only. It is not Net Rental Income."

---

## 5. INCLUDED / NOT INCLUDED

### Included in this calculation:
- ✓ Estimated annual market rent
- ✓ Official DLD/RERA Mollak service charges

### Not included:
- — Vacancy
- — Landlord property management
- — Unit maintenance

---

## 6. HELD / REJECTED SUPPRESSION

| Property ID | Type | SC Section Visible | Reason |
|-------------|------|-------------------|--------|
| 884 | HELD_RATE_SCOPE | NO | `production_eligible=false` |
| 4702 | HELD_RATE_SCOPE | NO | `production_eligible=false` |
| 4750 | HELD_RATE_SCOPE | NO | `production_eligible=false` |
| 5513 | HELD_RATE_SCOPE | NO | `production_eligible=false` |
| 6217 | REJECTED_IDENTITY | NO | `production_eligible=false` |
| 6056 | NOT_MATCHED | NO | `production_eligible=false` |
| 8057 | NOT_MATCHED | NO | `production_eligible=false` |
| 3201 | NOT_MATCHED | NO | `production_eligible=false` |

**V2_FREEZE_NON_ELIGIBLE_UI_LEAKAGE = 0** ✅

Non-eligible properties show only the existing Rental Income section (Gross Rental Yield). No service-charge-adjusted values are visible.

---

## 7. FRONTEND NO-RECALCULATION RULE

The frontend **formats backend values only**. It does NOT recalculate:

| Check | Result |
|-------|--------|
| V2_FREEZE_FRONTEND_SC_RECALCULATION | 0 ✅ |
| V2_FREEZE_FRONTEND_INCOME_RECALCULATION | 0 ✅ |
| V2_FREEZE_FRONTEND_YIELD_RECALCULATION | 0 ✅ |

- `annual_service_charge_aed` → displayed via `formatAEDFull()` (formatting only)
- `income_after_service_charges_aed` → displayed via `formatAEDFull()` (formatting only)
- `yield_after_service_charges_pct` → displayed as `{value}%` (formatting only)

No arithmetic operations performed in the frontend.

---

## 8. RENTAL MESSAGE BEHAVIOR (Unchanged)

| Scenario | Behavior | Status |
|----------|----------|--------|
| Ready + evaluated | No unknown rental-yield warning | Unchanged ✅ |
| Ready + unevaluated | "No Reliable Rental Estimate Available" | Unchanged ✅ |
| Offplan | Existing OFFPLAN_RENTAL_NOT_EVALUATED semantics | Unchanged ✅ |

**V2_FREEZE_CHANGED_RENTAL_MESSAGE_LOGIC = 0** ✅

---

## 9. UI REGRESSION COUNTERS

| Counter | Value |
|---------|-------|
| V2_FREEZE_ELIGIBLE_UI_MISSING | 0 ✅ |
| V2_FREEZE_UI_VALUE_MISMATCH | 0 ✅ |
| V2_FREEZE_NON_ELIGIBLE_UI_LEAKAGE | 0 ✅ |
| V2_FREEZE_FRONTEND_SC_RECALCULATION | 0 ✅ |
| V2_FREEZE_FRONTEND_INCOME_RECALCULATION | 0 ✅ |
| V2_FREEZE_FRONTEND_YIELD_RECALCULATION | 0 ✅ |
| NET_RENTAL_INCOME_LABEL_USED | 0 ✅ |
| NET_RENTAL_YIELD_LABEL_USED | 0 ✅ |
| NET_INCOME_LABEL_USED | 0 ✅ |
| NET_YIELD_LABEL_USED | 0 ✅ |
| V2_FREEZE_CHANGED_RENTAL_MESSAGE_LOGIC | 0 ✅ |

---

## 10. FREEZE VERDICT

### **SERVICE_CHARGE_ADJUSTED_INCOME_V2_UI_FROZEN**

| Check | Result |
|-------|--------|
| Eligible UI properties | 12 ✅ |
| Labels correct | YES ✅ |
| Disclosure present | YES ✅ |
| Held/rejected suppressed | YES ✅ |
| No frontend recalculation | YES ✅ |
| No forbidden labels | YES ✅ |
| Rental message logic unchanged | YES ✅ |
| All UI counters | 0 ✅ |

**This UI freeze is immutable. Do NOT change labels, add recalculation, or modify suppression logic without a full audit + freeze process.**
