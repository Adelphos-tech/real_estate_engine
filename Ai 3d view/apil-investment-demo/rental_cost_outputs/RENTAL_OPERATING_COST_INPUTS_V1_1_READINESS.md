# RENTAL OPERATING COST INPUTS V1.1 — READINESS AUDIT

**Date**: 2026-08-21
**Phase**: V1.1 READINESS AUDIT
**Verdict**: **RENTAL_OPERATING_COST_INPUTS_V1_1_VERIFIED**
**Production Readiness**: **DEMO_ONLY_EPHEMERAL**
**Persistence Mode**: **EPHEMERAL_USER_SESSION**

---

## 1. GOAL

Verify and harden the V1 operating-cost input layer for:
1. User/property input isolation
2. Persistence semantics
3. Restart behavior
4. API validation
5. UI state synchronization
6. Calculation determinism
7. Upstream regression isolation

---

## 2. CRITICAL ISSUE FOUND AND FIXED

### Before V1.1

The `user_input_store.py` used a **global process-memory dict keyed by `property_id` only** — no user/session scoping.

**Classification**: A (global process memory) + D (property scoped) — NOT user/session scoped.

**Result**: `GLOBAL_UNSCOPED_USER_INPUT_STORE = 1` (FAIL — one user's assumptions visible to another).

### After V1.1 Fix

The store is now keyed by **`(user_scope, property_id)`** tuple. Every stored assumption is isolated by user/session identifier + property_id.

**Result**: `GLOBAL_UNSCOPED_USER_INPUT_STORE = 0` ✅

---

## 3. KEYING MODEL

Every stored assumption is isolated by:

```
(user_scope, property_id)
```

- `user_scope`: User/session identifier (passed via API query param or request body)
- `property_id`: Property identifier
- Default: `"anonymous"` if no user_scope provided (demo mode)

**Counters**:
- `CROSS_USER_OPERATING_COST_LEAKAGE = 0` ✅
- `CROSS_PROPERTY_OPERATING_COST_LEAKAGE = 0` ✅

---

## 4. PERSISTENCE MODE

**Declared mode**: `EPHEMERAL_USER_SESSION`

- Inputs exist only in process memory for the current session
- Inputs disappear when the server/process is restarted
- NOT written to MASTER, Qdrant, Mollak, or any official data store
- UI discloses: "Your operating-cost inputs are temporary and may not be available after the session ends."

**Counter**: `RESTART_BEHAVIOR_CONTRADICTS_DECLARED_MODE = 0` ✅

---

## 5. DATA PROVENANCE

Every operating-cost field carries a `source` field:

| Source | Used |
|--------|------|
| USER_INPUT | ✅ |
| SELF_MANAGED | ✅ (only on explicit user selection) |
| MISSING | ✅ |
| ASSUMED | ❌ FORBIDDEN |
| DEFAULT | ❌ FORBIDDEN |
| MARKET_STANDARD | ❌ FORBIDDEN |

**Counter**: `ASSUMED_OPERATING_COST_USED = 0` ✅

---

## 6. VALIDATION RESULTS

### Vacancy

| Rule | Result |
|------|--------|
| PERCENT or AED (not both) | ✅ |
| 0 ≤ percent ≤ 100 | ✅ |
| 0 ≤ loss_aed ≤ annual_rent | ✅ |
| Invalid rejected with 422 | ✅ |
| No silent clamping | ✅ |

**Counters**: `INVALID_VACANCY_ACCEPTED = 0` ✅, `VACANCY_VALUE_SILENTLY_CLAMPED = 0` ✅

### Management

| Rule | Result |
|------|--------|
| FIXED_AED, PERCENT, or SELF_MANAGED | ✅ |
| Exactly one active mode | ✅ |
| SELF_MANAGED → cost = 0 (only on explicit selection) | ✅ |
| Percent base = effective_rental_income_after_vacancy | ✅ (frozen) |

**Counters**: `MULTIPLE_MANAGEMENT_MODES_ACTIVE = 0` ✅, `AUTO_SELF_MANAGED_ASSUMPTION = 0` ✅

### Maintenance

| Rule | Result |
|------|--------|
| annual AED ≥ 0 | ✅ |
| No default % of price/rent/SC/area | ✅ |

**Counter**: `DEFAULT_MAINTENANCE_ASSUMPTION_USED = 0` ✅

---

## 7. DELETE / CLEAR SEMANTICS

`DELETE /properties/{id}/operating-costs?user_scope=X` clears only:
- The specified user_scope + property_id combination

It does NOT clear:
- Another user's same property ✅
- Another property ✅
- Official service-charge context ✅
- Rental context ✅

**Counters**:
- `DELETE_CLEARED_WRONG_USER_DATA = 0` ✅
- `DELETE_CLEARED_WRONG_PROPERTY_DATA = 0` ✅
- `DELETE_CHANGED_OFFICIAL_DATA = 0` ✅

---

## 8. RESTART TEST

| Step | Result |
|------|--------|
| Before restart: inputs saved | ✅ |
| Store type: in-memory dict | ✅ |
| Persistence mode: EPHEMERAL_USER_SESSION | ✅ |
| After restart: inputs disappear | ✅ (by design) |
| Matches declared mode | ✅ |

**Counter**: `RESTART_BEHAVIOR_CONTRADICTS_DECLARED_MODE = 0` ✅

---

## 9. TEST MATRIX (A-N)

| Test | Description | Property | Result |
|------|-------------|----------|--------|
| A | No inputs | 409 | PASS ✅ |
| B | Vacancy only (5%) | 409 | PASS ✅ |
| C | Vacancy + management | 409 | PASS ✅ |
| D | All costs | 409 | PASS ✅ |
| E | SELF_MANAGED | 409 | PASS ✅ |
| F | All costs, no SC | 3201 | PASS ✅ |
| G | Negative net income stress | 409 | PASS ✅ |
| H | Multi-property isolation | 409/8201 | PASS ✅ |
| I | Multi-user isolation | 409 (user_A/user_B) | PASS ✅ |
| J | Restart behavior (ephemeral) | — | PASS ✅ |
| K | DELETE isolation | 409 (user_A/user_B) | PASS ✅ |
| L | Invalid vacancy 101% | 409 | PASS ✅ (422) |
| M | Negative maintenance | 409 | PASS ✅ (422) |
| N | Invalid management mode | 409 | PASS ✅ (422) |

**All 14 tests: PASS ✅**

### Test D Detail (409 — all costs)

| Field | Value |
|-------|-------|
| Annual rent | AED 158,400 |
| Vacancy (5%) | -AED 7,920 |
| Service charges | -AED 25,667.32 |
| Management (fixed) | -AED 12,000 |
| Maintenance | -AED 5,000 |
| **Net Rental Income** | **AED 107,812.68** |
| **Net Rental Yield** | **3.99%** |

### Test G Detail (409 — negative stress)

| Field | Value |
|-------|-------|
| Vacancy (80%) | -AED 126,720 |
| Service charges | -AED 25,667.32 |
| Management | -AED 30,000 |
| Maintenance | -AED 20,000 |
| **Net Rental Income** | **AED -43,987.32** (negative, NOT clamped) |

### Test I Detail (multi-user isolation)

| User | Vacancy | Management | Net Income |
|------|---------|------------|------------|
| user_A | 5% | SELF_MANAGED | AED 120,812.68 |
| user_B | 10% | AED 15,000 | AED 95,892.68 |

**Cross-user leakage: NONE ✅**

---

## 10. CALCULATION DETERMINISM

For identical inputs, backend results are identical across repeated calls.

**Counter**: `NON_DETERMINISTIC_OPERATING_COST_RESULT = 0` ✅

---

## 11. PARTIAL CALCULATION RULE

If any required cost is missing:
- `calculation_level = PARTIAL_OPERATING_COSTS`
- Output: "Income After Known Operating Costs"
- Forbidden: "Net Rental Income", "Net Rental Yield"

**Counters**:
- `NET_INCOME_SHOWN_WITH_MISSING_COST = 0` ✅
- `NET_YIELD_SHOWN_WITH_MISSING_COST = 0` ✅

---

## 12. NET RENTAL RULE

Only when ALL required inputs available:
- annual rent + official SC + vacancy + management + maintenance

```
net_rental_income_aed = annual_rent - vacancy_loss - SC - management - maintenance
net_rental_yield_pct = net_rental_income_aed / MASTER current_price × 100
```

Denominator: MASTER current_price (unchanged) ✅

---

## 13. NO SERVICE CHARGE = NO NET

For properties without verified SC:
- `calculation_level = PARTIAL_OPERATING_COSTS` (even with all user costs)
- Net Rental Income NOT produced

**Counter**: `NET_RENTAL_WITHOUT_VERIFIED_SERVICE_CHARGE = 0` ✅

---

## 14. NEGATIVE / EXTREME RESULTS

- Negative net income allowed (not clamped to zero) ✅
- Negative net yield allowed ✅

**Counter**: `NEGATIVE_NET_INCOME_CLAMPED = 0` ✅

---

## 15. FRONTEND STATE

| Operation | UI Behavior |
|-----------|-------------|
| POST | Reloads page, uses backend response |
| DELETE | Reloads page, uses backend response |
| Refresh | Reads from backend |
| Property navigation | Fresh fetch from backend |

Frontend does NOT maintain independent financial state.

**Counter**: `FRONTEND_BACKEND_INPUT_STATE_MISMATCH = 0` ✅

---

## 16. FRONTEND CALCULATION SAFETY

All calculations performed on backend. Frontend does formatting only.

| Counter | Value |
|---------|-------|
| FRONTEND_VACANCY_CALCULATION | 0 ✅ |
| FRONTEND_MANAGEMENT_CALCULATION | 0 ✅ |
| FRONTEND_MAINTENANCE_CALCULATION | 0 ✅ |
| FRONTEND_PARTIAL_INCOME_CALCULATION | 0 ✅ |
| FRONTEND_NET_INCOME_CALCULATION | 0 ✅ |
| FRONTEND_NET_YIELD_CALCULATION | 0 ✅ |

---

## 17. UI PROVENANCE

| Data Type | Label | Visually Distinguished |
|-----------|-------|----------------------|
| Official SC | "Official Service Charges" | ✅ |
| User vacancy | "Vacancy" (input field) | ✅ |
| User management | "Property Management" (input field) | ✅ |
| User maintenance | "Unit Maintenance" (input field) | ✅ |

**Counter**: `USER_INPUT_PRESENTED_AS_OFFICIAL_DATA = 0` ✅

---

## 18. UI EDITING

| Operation | Supported |
|-----------|-----------|
| Edit | ✅ (change input fields) |
| Save/Update | ✅ (POST to backend) |
| Clear | ✅ (DELETE to backend) |
| Source of truth | Backend response ✅ |
| Optimistic recalculation | None ✅ |

---

## 19. SC V2 FREEZE REGRESSION

SC provider file NOT modified in V1.1 (git diff empty).

| Counter | Value |
|---------|-------|
| V11_CHANGED_SC_ELIGIBILITY | 0 ✅ |
| V11_CHANGED_SC_RATE | 0 ✅ |
| V11_CHANGED_SC_ANNUAL | 0 ✅ |
| V11_CHANGED_INCOME_AFTER_SC | 0 ✅ |
| V11_CHANGED_YIELD_AFTER_SC | 0 ✅ |

---

## 20. RENTAL ENGINE REGRESSION

| Counter | Value |
|---------|-------|
| V11_CHANGED_ANNUAL_RENT | 0 ✅ |
| V11_CHANGED_RENT_RANGE | 0 ✅ |
| V11_CHANGED_RENT_TIER | 0 ✅ |
| V11_CHANGED_GROSS_YIELD | 0 ✅ |
| V11_CHANGED_GROSS_YIELD_RANGE | 0 ✅ |

---

## 21. SALES / SIGNAL / FIT REGRESSION

| Counter | Value |
|---------|-------|
| V11_CHANGED_MARKET_CONTEXT | 0 ✅ |
| V11_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| V11_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| V11_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| V11_CHANGED_FIT_SCORE | 0 ✅ |

Net Rental Yield does NOT affect Investor Fit. ✅

---

## 22. SECURITY / LOGGING

- User-entered financial assumptions not logged to verbose production logs ✅
- Debug endpoints do not expose another user's inputs ✅

**Counter**: `USER_INPUT_EXPOSED_CROSS_SCOPE_IN_DEBUG = 0` ✅

---

## 23. ALL SAFETY COUNTERS

| Counter | Value |
|---------|-------|
| GLOBAL_UNSCOPED_USER_INPUT_STORE | 0 ✅ |
| CROSS_USER_OPERATING_COST_LEAKAGE | 0 ✅ |
| CROSS_PROPERTY_OPERATING_COST_LEAKAGE | 0 ✅ |
| INVALID_VACANCY_ACCEPTED | 0 ✅ |
| VACANCY_VALUE_SILENTLY_CLAMPED | 0 ✅ |
| MULTIPLE_MANAGEMENT_MODES_ACTIVE | 0 ✅ |
| AUTO_SELF_MANAGED_ASSUMPTION | 0 ✅ |
| DEFAULT_MAINTENANCE_ASSUMPTION_USED | 0 ✅ |
| ASSUMED_OPERATING_COST_USED | 0 ✅ |
| NET_INCOME_SHOWN_WITH_MISSING_COST | 0 ✅ |
| NET_YIELD_SHOWN_WITH_MISSING_COST | 0 ✅ |
| NET_RENTAL_WITHOUT_VERIFIED_SERVICE_CHARGE | 0 ✅ |
| NEGATIVE_NET_INCOME_CLAMPED | 0 ✅ |
| DELETE_CLEARED_WRONG_USER_DATA | 0 ✅ |
| DELETE_CLEARED_WRONG_PROPERTY_DATA | 0 ✅ |
| DELETE_CHANGED_OFFICIAL_DATA | 0 ✅ |
| USER_INPUT_OVERWROTE_MASTER | 0 ✅ |
| USER_INPUT_OVERWROTE_QDRANT | 0 ✅ |
| USER_INPUT_OVERWROTE_MOLLAK | 0 ✅ |
| USER_INPUT_OVERWROTE_RENTAL_EVIDENCE | 0 ✅ |
| EPHEMERAL_INPUT_PRESENTED_AS_PERSISTED | 0 ✅ |
| USER_INPUT_PRESENTED_AS_OFFICIAL_DATA | 0 ✅ |
| USER_INPUT_EXPOSED_CROSS_SCOPE_IN_DEBUG | 0 ✅ |
| FRONTEND_VACANCY_CALCULATION | 0 ✅ |
| FRONTEND_MANAGEMENT_CALCULATION | 0 ✅ |
| FRONTEND_MAINTENANCE_CALCULATION | 0 ✅ |
| FRONTEND_PARTIAL_INCOME_CALCULATION | 0 ✅ |
| FRONTEND_NET_INCOME_CALCULATION | 0 ✅ |
| FRONTEND_NET_YIELD_CALCULATION | 0 ✅ |
| FRONTEND_BACKEND_INPUT_STATE_MISMATCH | 0 ✅ |
| NON_DETERMINISTIC_OPERATING_COST_RESULT | 0 ✅ |
| RESTART_BEHAVIOR_CONTRADICTS_DECLARED_MODE | 0 ✅ |
| OPERATING_COST_V1_CHANGED_RENTAL_MESSAGE_LOGIC | 0 ✅ |

---

## 24. PRODUCTION READINESS CLASSIFICATION

### **DEMO_ONLY_EPHEMERAL**

**Reason**: The application has no real user authentication/identity system. User scoping is implemented via a session-generated identifier stored in `sessionStorage`, which provides isolation between browser sessions but is not a production-grade auth system.

**Implications**:
- Safe for controlled demo / internal use
- NOT ready for multi-user production deployment
- To upgrade to production: implement real authentication and switch to `USER_SCOPED_PERSISTED` mode

---

## 25. FILES MODIFIED IN V1.1

| File | Change |
|------|--------|
| `investor_api/rental_operating_costs/user_input_store.py` | Rewritten: keyed by (user_scope, property_id), added created_at/updated_at |
| `investor_api/main_v2.py` | Added user_scope to GET/POST/DELETE endpoints, passed to build_response |
| `src/components/OperatingCostsCard.tsx` | Added session user_scope generation, ephemeral disclosure, fixed API paths |

---

## 26. FINAL VERDICT

### **RENTAL_OPERATING_COST_INPUTS_V1_1_VERIFIED**

| Check | Result |
|-------|--------|
| OPERATING_COST_INPUT_PERSISTENCE_MODE | EPHEMERAL_USER_SESSION |
| User isolation result | VERIFIED ✅ |
| Property isolation result | VERIFIED ✅ |
| Restart behavior | EPHEMERAL (matches declared mode) ✅ |
| API validation result | VERIFIED (422 for invalid) ✅ |
| UI synchronization result | VERIFIED (backend as source of truth) ✅ |
| Calculation result | VERIFIED (deterministic, backend-only) ✅ |
| All safety/regression counters | 0 ✅ |
| Production readiness | DEMO_ONLY_EPHEMERAL |
| All 14 test cases | PASS ✅ |

**NOT FROZEN. Do NOT start Full Property ROI.**
