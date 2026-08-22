# RENTAL OPERATING COST INPUTS V1 — DEMO FROZEN

**Date**: 2026-08-22
**Freeze Identifier**: `RENTAL_OPERATING_COST_INPUTS_V1_DEMO_FROZEN`
**Verdict**: `RENTAL_OPERATING_COST_INPUTS_V1_DEMO_FINAL_VERIFIED`
**Classification**: `DEMO_ONLY_EPHEMERAL`
**Persistence Mode**: `EPHEMERAL_USER_SESSION`

---

## 1. FREEZE SCOPE

This freeze covers the operating-cost demo layer ONLY:

- Vacancy (user input)
- Landlord Property Management (user input)
- Unit Maintenance (user input)

This is **NOT** a production freeze. This is **NOT** an authenticated multi-user freeze.

---

## 2. CURRENT FINANCIAL LADDER

### Frozen Upstream (unchanged)

| Layer | Source | Status |
|-------|--------|--------|
| Annual Rent | rental_context_service.py | FROZEN |
| Gross Rental Yield | rental_context_service.py | FROZEN |
| Official Service Charges | service_charge_provider.py (V2) | FROZEN |
| Income After Service Charges | service_charge_context | FROZEN |
| Yield After Service Charges | service_charge_context | FROZEN |

### Demo Operating-Cost Layer (this freeze)

| Layer | Source | Status |
|-------|--------|--------|
| Vacancy | User input | DEMO FROZEN |
| Property Management | User input | DEMO FROZEN |
| Unit Maintenance | User input | DEMO FROZEN |

### Progressive Calculation Levels

```
SERVICE_CHARGE_ADJUSTED    → no operating cost inputs
PARTIAL_OPERATING_COSTS    → some (but not all) operating cost inputs
NET_RENTAL                 → all operating cost inputs + verified SC
```

---

## 3. NET RENTAL RULE

Net Rental Income is shown **ONLY** when ALL required inputs exist:

- annual rent (from frozen rental context)
- verified official service charge (from frozen SC V2)
- vacancy (from user input)
- management (from user input)
- maintenance (from user input)

### Formula

```
net_rental_income_aed =
    annual_rent_estimate_aed
    - vacancy_loss_aed
    - annual_service_charge_aed
    - management_cost_aed
    - maintenance_cost_aed
```

### Net Rental Yield

```
net_rental_yield_pct =
    net_rental_income_aed
    / MASTER current_price_aed
    * 100
```

**Formulas are NOT changed.** Implemented in `operating_cost_calculator.py` lines 144-154.

---

## 4. PARTIAL COST RULE

If any required operating cost is missing:

```
calculation_level = PARTIAL_OPERATING_COSTS
```

- **Allowed label**: "Income After Known Operating Costs"
- **Forbidden**: "Net Rental Income", "Net Rental Yield"
- `net_rental_income_aed` = `None`
- `net_rental_yield_pct` = `None`

```
NET_INCOME_SHOWN_WITH_MISSING_COST = 0 ✅
NET_YIELD_SHOWN_WITH_MISSING_COST = 0 ✅
```

---

## 5. NO VERIFIED SERVICE CHARGE = NO NET

If official service-charge context is NOT production eligible:

- Do NOT calculate Net Rental Income
- Remain at `PARTIAL_OPERATING_COSTS`
- Even if user provides vacancy + management + maintenance

```
NET_RENTAL_WITHOUT_VERIFIED_SERVICE_CHARGE = 0 ✅
```

Verified in Test F (property 3201, SC not eligible → PARTIAL, no net).

---

## 6. USER INPUT PROVENANCE

### Allowed Sources

| Source | Used For |
|--------|----------|
| `USER_INPUT` | Vacancy (percent/AED), Management (fixed/percent), Maintenance (AED) |
| `SELF_MANAGED` | Management (user explicitly selects self-manage → cost = 0) |
| `MISSING` | Any cost not yet entered by user |

### Forbidden Sources

| Source | Reason |
|--------|--------|
| `ASSUMED` | Never used — no assumed costs |
| `DEFAULT` | Never used — no default costs |
| `MARKET_STANDARD` | Never used — no market standard costs |

```
ASSUMED_OPERATING_COST_USED = 0 ✅
```

---

## 7. VACANCY

### Input Modes

| Mode | Description |
|------|-------------|
| `VACANCY_PERCENT` | Percentage of annual rent |
| `VACANCY_LOSS_AED` | Fixed AED amount per year |

**Never both.** Providing both modes simultaneously is rejected (422).

### Validation

| Rule | Constraint |
|------|-----------|
| Percent | 0 ≤ percent ≤ 100 |
| AED | 0 ≤ loss_aed ≤ annual_rent_estimate_aed |
| Annual rent | Must be > 0 |

### No Default Vacancy

No vacancy is assumed if the user does not enter one. Status = `MISSING`.

---

## 8. MANAGEMENT

### Input Modes

| Mode | Description |
|------|-------------|
| `USER_INPUT_FIXED_AED` | Fixed AED per year |
| `USER_INPUT_PERCENT` | Percentage of effective rental income (after vacancy) |
| `SELF_MANAGED` | User explicitly selects self-management → cost = 0 |

### SELF_MANAGED

- Only valid when explicitly selected by user
- Produces `management_cost_aed = 0`
- Source = `SELF_MANAGED`
- No automatic self-managed assumption

### Management Percentage Base

```
management_cost_aed = effective_rental_income_after_vacancy * percent / 100
```

If vacancy not provided, falls back to `annual_rent_estimate_aed * percent / 100`.

```
AUTO_SELF_MANAGED_ASSUMPTION = 0 ✅
```

---

## 9. MAINTENANCE

### Input

- Annual AED user input only
- No default percentage of property value
- No default percentage of rent
- No default AED/sqft

### Validation

| Rule | Constraint |
|------|-----------|
| AED | ≥ 0 |

```
DEFAULT_MAINTENANCE_ASSUMPTION_USED = 0 ✅
```

---

## 10. EPHEMERAL MODE

```
OPERATING_COST_INPUT_PERSISTENCE_MODE = EPHEMERAL_USER_SESSION
```

### Behavior

- Inputs exist in process memory (Python dict in `user_input_store.py`)
- Isolated by `(user_scope, property_id)` tuple
- Disappear after backend restart
- NOT saved to any account
- NOT production-authenticated data

### UI Disclosure

The UI displays:

> "Your operating-cost inputs are temporary and may not be available after the session ends."

```
EPHEMERAL_INPUT_PRESENTED_AS_PERSISTED = 0 ✅
```

---

## 11. DEMO USER SCOPE

### Current Implementation

- `user_scope` is client-controlled (generated in `sessionStorage` on frontend)
- Sent via query parameter or request body
- Backend uses it as-is for isolation keying

### Known Demo Limitation

```
CLIENT_CAN_IMPERSONATE_OPERATING_COST_USER = 1
```

This is a **KNOWN DEMO LIMITATION**, not a failure. It is acceptable ONLY because the classification is `DEMO_ONLY_EPHEMERAL`. This counter is intentionally NOT zero.

### No Real Authorization

- No authentication system
- No login/signup
- No JWT/OAuth
- No password system
- No account database

---

## 12. NO AUTH — REVERT VERIFIED

All authentication work from the previous phase was fully reverted.

### Verified Absent

| Item | Status |
|------|--------|
| Login page | NOT present ✅ |
| Signup page | NOT present ✅ |
| Auth routes (`/auth/*`) | NOT present ✅ |
| Auth database (`apil_auth.db`) | NOT present ✅ |
| JWT handling | NOT present ✅ |
| OAuth | NOT present ✅ |
| AuthProvider (React) | NOT present ✅ |
| AuthPanel (React) | NOT present ✅ |
| Password system | NOT present ✅ |
| `investor_api/auth/` package | NOT present ✅ |
| `auth_outputs/` directory | NOT present ✅ |

```
AUTH_REMAINDER_AFTER_REVERT = 0 ✅
```

---

## 13. USER INPUT STORAGE SAFETY

User inputs are NEVER written to official data stores:

| Data Store | Written To? | Counter |
|------------|-------------|---------|
| MASTER_FINAL.xlsx | NO ✅ | `USER_INPUT_OVERWROTE_MASTER = 0` |
| Qdrant | NO ✅ | `USER_INPUT_OVERWROTE_QDRANT = 0` |
| Mollak source data | NO ✅ | `USER_INPUT_OVERWROTE_MOLLAK = 0` |
| Rental benchmark evidence | NO ✅ | `USER_INPUT_OVERWROTE_RENTAL_EVIDENCE = 0` |
| service_charge_provider.py | NO ✅ | `USER_INPUT_OVERWROTE_SERVICE_CHARGE_PROVIDER = 0` |

All inputs stored only in in-memory `_store` dict in `user_input_store.py`.

---

## 14. NEGATIVE RESULTS

Valid user inputs may produce negative Net Rental Income or negative Net Rental Yield.

- Do NOT clamp to zero
- Display the actual negative value

```
NEGATIVE_NET_INCOME_CLAMPED = 0 ✅
```

Verified in Test G: net = -43,027.32 AED (not clamped).

---

## 15. ISOLATION

### Cross-User Isolation

```
CROSS_USER_OPERATING_COST_LEAKAGE = 0 ✅
```

Each `(user_scope, property_id)` tuple has its own record. User A cannot see User B's inputs.

### Cross-Property Isolation

```
CROSS_PROPERTY_OPERATING_COST_LEAKAGE = 0 ✅
```

Each property has its own record per user_scope. Property 409 inputs do not affect Property 8201.

### DELETE Isolation

```
DELETE_CLEARED_WRONG_USER_DATA = 0 ✅
DELETE_CLEARED_WRONG_PROPERTY_DATA = 0 ✅
DELETE_CHANGED_OFFICIAL_DATA = 0 ✅
```

DELETE only clears the specified `(user_scope, property_id)` record.

---

## 16. TEST MATRIX (A-N)

All 14 tests pass:

| Test | Description | Result |
|------|-------------|--------|
| A | No inputs → SERVICE_CHARGE_ADJUSTED, no net | PASS ✅ |
| B | Vacancy only → PARTIAL, no net, vac_loss correct | PASS ✅ |
| C | Vacancy + management → PARTIAL, maintenance missing | PASS ✅ |
| D | All required costs → NET_RENTAL, net + yield correct | PASS ✅ |
| E | SELF_MANAGED → mgmt_cost=0, source=SELF_MANAGED | PASS ✅ |
| F | All costs but no official SC → PARTIAL, no net | PASS ✅ |
| G | Negative result → net=-43,027.32 (not clamped) | PASS ✅ |
| H | 409 + 8201 → different net values, no collision | PASS ✅ |
| I | Two user_scopes → isolated, different values | PASS ✅ |
| J | Restart → ephemeral (in-memory dict) | PASS ✅ |
| K | DELETE isolation → only target scope cleared | PASS ✅ |
| L | Vacancy 101% → 422 rejected | PASS ✅ |
| M | Negative maintenance → 422 rejected | PASS ✅ |
| N | Invalid management mode → 422 rejected | PASS ✅ |

```
ALL_DEMO_FREEZE_TESTS_PASS = 1 ✅
```

### Test D Details (Formula Verification)

Property 409:
- Annual rent: AED 163,200.00
- Vacancy (5%): AED 8,160.00
- Service charge: AED 25,667.32
- Management: AED 12,000.00
- Maintenance: AED 4,000.00
- **Net Rental Income**: AED 113,372.68
- **Net Rental Yield**: 4.20%

### Test G Details (Negative Result)

Property 409:
- Vacancy (80%): AED 130,560.00
- Service charge: AED 25,667.32
- Management: AED 30,000.00
- Maintenance: AED 20,000.00
- **Net Rental Income**: AED -43,027.32 (negative, not clamped)

---

## 17. SC V2 FREEZE REGRESSION

`SERVICE_CHARGE_ADJUSTED_INCOME_V2_FROZEN` remains unchanged.

| Counter | Value |
|---------|-------|
| DEMO_FREEZE_CHANGED_SC_ELIGIBILITY | 0 ✅ |
| DEMO_FREEZE_CHANGED_SC_RATE | 0 ✅ |
| DEMO_FREEZE_CHANGED_SC_ANNUAL | 0 ✅ |
| DEMO_FREEZE_CHANGED_INCOME_AFTER_SC | 0 ✅ |
| DEMO_FREEZE_CHANGED_YIELD_AFTER_SC | 0 ✅ |

---

## 18. RENTAL REGRESSION

| Counter | Value |
|---------|-------|
| DEMO_FREEZE_CHANGED_ANNUAL_RENT | 0 ✅ |
| DEMO_FREEZE_CHANGED_RENT_RANGE | 0 ✅ |
| DEMO_FREEZE_CHANGED_RENT_TIER | 0 ✅ |
| DEMO_FREEZE_CHANGED_GROSS_YIELD | 0 ✅ |
| DEMO_FREEZE_CHANGED_GROSS_YIELD_RANGE | 0 ✅ |

---

## 19. SALES / SIGNAL / FIT REGRESSION

| Counter | Value |
|---------|-------|
| DEMO_FREEZE_CHANGED_MARKET_CONTEXT | 0 ✅ |
| DEMO_FREEZE_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| DEMO_FREEZE_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| DEMO_FREEZE_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| DEMO_FREEZE_CHANGED_FIT_SCORE | 0 ✅ |

Net Rental Yield does NOT affect Investor Fit. ✅

---

## 20. ALL SAFETY COUNTERS

| Counter | Value | Note |
|---------|-------|------|
| ASSUMED_OPERATING_COST_USED | 0 ✅ | |
| AUTO_SELF_MANAGED_ASSUMPTION | 0 ✅ | |
| DEFAULT_MAINTENANCE_ASSUMPTION_USED | 0 ✅ | |
| NET_INCOME_SHOWN_WITH_MISSING_COST | 0 ✅ | |
| NET_YIELD_SHOWN_WITH_MISSING_COST | 0 ✅ | |
| NET_RENTAL_WITHOUT_VERIFIED_SERVICE_CHARGE | 0 ✅ | |
| NEGATIVE_NET_INCOME_CLAMPED | 0 ✅ | |
| EPHEMERAL_INPUT_PRESENTED_AS_PERSISTED | 0 ✅ | |
| AUTH_REMAINDER_AFTER_REVERT | 0 ✅ | |
| CLIENT_CAN_IMPERSONATE_OPERATING_COST_USER | 1 | KNOWN DEMO LIMITATION |
| USER_INPUT_OVERWROTE_MASTER | 0 ✅ | |
| USER_INPUT_OVERWROTE_QDRANT | 0 ✅ | |
| USER_INPUT_OVERWROTE_MOLLAK | 0 ✅ | |
| USER_INPUT_OVERWROTE_RENTAL_EVIDENCE | 0 ✅ | |
| USER_INPUT_OVERWROTE_SERVICE_CHARGE_PROVIDER | 0 ✅ | |
| FRONTEND_VACANCY_CALCULATION | 0 ✅ | |
| FRONTEND_MANAGEMENT_CALCULATION | 0 ✅ | |
| FRONTEND_MAINTENANCE_CALCULATION | 0 ✅ | |
| FRONTEND_PARTIAL_INCOME_CALCULATION | 0 ✅ | |
| FRONTEND_NET_INCOME_CALCULATION | 0 ✅ | |
| FRONTEND_NET_YIELD_CALCULATION | 0 ✅ | |
| USER_INPUT_PRESENTED_AS_OFFICIAL_DATA | 0 ✅ | |
| CROSS_USER_OPERATING_COST_LEAKAGE | 0 ✅ | |
| CROSS_PROPERTY_OPERATING_COST_LEAKAGE | 0 ✅ | |
| DELETE_CLEARED_WRONG_USER_DATA | 0 ✅ | |
| DELETE_CLEARED_WRONG_PROPERTY_DATA | 0 ✅ | |
| DELETE_CHANGED_OFFICIAL_DATA | 0 ✅ | |

**All counters zero except CLIENT_CAN_IMPERSONATE (KNOWN DEMO LIMITATION).**

---

## 21. FILES

### Backend

| File | Role |
|------|------|
| `investor_api/rental_operating_costs/__init__.py` | Package init |
| `investor_api/rental_operating_costs/operating_cost_calculator.py` | Calculation engine (all math on backend) |
| `investor_api/rental_operating_costs/operating_cost_models.py` | Data models, provenance, calculation levels |
| `investor_api/rental_operating_costs/operating_cost_validation.py` | Input validation (vacancy, management, maintenance) |
| `investor_api/rental_operating_costs/user_input_store.py` | In-memory ephemeral store keyed by (user_scope, property_id) |

### API Endpoints (in main_v2.py)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /properties/{id}` | GET | Returns `rental_operating_cost_context` in response |
| `POST /properties/{id}/operating-costs` | POST | Save user inputs |
| `DELETE /properties/{id}/operating-costs` | DELETE | Clear user inputs |

### Frontend

| File | Role |
|------|------|
| `src/components/OperatingCostsCard.tsx` | UI for inputs + display (no calculations) |

---

## 22. FREEZE IDENTIFIER

```
RENTAL_OPERATING_COST_INPUTS_V1_DEMO_FROZEN
```

This is NOT:
- `RENTAL_OPERATING_COST_INPUTS_V1_PRODUCTION_FROZEN`
- An authenticated production readiness claim
- A multi-user production freeze

---

## 23. FINAL VERDICT

### **RENTAL_OPERATING_COST_INPUTS_V1_DEMO_FINAL_VERIFIED**

| Field | Value |
|-------|-------|
| PERSISTENCE_MODE | EPHEMERAL_USER_SESSION |
| READINESS | DEMO_ONLY_EPHEMERAL |
| CLIENT_CAN_IMPERSONATE_OPERATING_COST_USER | 1 (KNOWN DEMO LIMITATION) |
| ALL_DEMO_FREEZE_TESTS_PASS | 1 ✅ |
| All financial regression counters | 0 ✅ |
| All safety counters | 0 ✅ (except KNOWN DEMO LIMITATION) |
| AUTH_REMAINDER_AFTER_REVERT | 0 ✅ |
| Freeze artifact | `rental_cost_outputs/RENTAL_OPERATING_COST_INPUTS_V1_DEMO_FROZEN.md` |
| UI freeze artifact | `rental_cost_outputs/RENTAL_OPERATING_COST_INPUTS_V1_UI_DEMO_FROZEN.md` |
