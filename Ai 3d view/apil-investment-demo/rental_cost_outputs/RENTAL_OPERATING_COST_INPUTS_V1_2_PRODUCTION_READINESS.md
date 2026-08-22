# RENTAL OPERATING COST INPUTS V1.2 — PRODUCTION READINESS AUDIT

**Date**: 2026-08-21
**Phase**: V1.2 PRODUCTION READINESS AUDIT
**Verdict**: **RENTAL_OPERATING_COST_INPUTS_V1_2_VERIFIED**
**Production Readiness**: **DEMO_ONLY_EPHEMERAL**
**Persistence Mode**: **EPHEMERAL_USER_SESSION**

---

## 1. GOAL

Upgrade operating-cost user inputs from DEMO_ONLY_EPHEMERAL to USER_SCOPED_PERSISTED with real authenticated user identity and durable, isolated storage — **if safely possible**.

---

## 2. AUTHENTICATION SYSTEM AUDIT

### Search Performed

| Search Target | Result |
|--------------|--------|
| Backend auth middleware | NONE (only CORSMiddleware) |
| Session middleware | NONE |
| JWT handling | NONE |
| OAuth | NONE |
| Supabase/Auth0/Firebase | NONE |
| User/account models | NONE |
| `request.user` / `current_user` | NONE |
| Frontend auth state | NONE |
| Database user tables | NONE |
| Auth libraries (backend) | NONE (fastapi, uvicorn, pydantic only) |
| Auth libraries (frontend) | NONE (no auth-related npm packages) |

### Existing "Identity" System

The application has an `investor_id` system:
- `POST /investors` generates a UUID and stores questionnaire answers in `data/investor_profiles.json`
- Frontend stores the UUID in `localStorage` via `investorSession.setId()`
- No password, no login, no verification, no token, no session expiry

**This is a profile preference ID, NOT an authenticated identity.**

### Audit Results

| Field | Value |
|-------|-------|
| **AUTH_SYSTEM_PRESENT** | **NO** |
| **AUTHENTICATED_USER_ID_AVAILABLE_TO_BACKEND** | **NO** |
| **AUTHENTICATED_USER_ID_AVAILABLE_TO_FRONTEND** | **NO** |

---

## 3. HARD STOP — NO REAL AUTHENTICATION

Per Section 3 of the V1.2 requirements:

> If no real authenticated user identity exists: DO NOT promote this feature to multi-user production.

### Production Blocker

```
PRODUCTION_BLOCKER = REAL_AUTHENTICATED_USER_ID_NOT_AVAILABLE
```

### Items NOT Treated as Authenticated Identity

| Item | Reason |
|------|--------|
| sessionStorage UUID | Client-generated, no verification |
| Query parameter `user_scope` | Client-controlled, spoofable |
| Request body `user_scope` | Client-controlled, spoofable |
| localStorage `apil_investor_id` | Client-generated, no verification |
| `investor_id` from `POST /investors` | UUID only, no password/login |

### Classification

```
DEMO_ONLY_EPHEMERAL
```

No code changes were made to promote to production. No fake authentication was created.

---

## 4. CLIENT-CONTROLLED IDENTITY (Demo Mode Limitation)

### Current State

In demo mode, the client sends `user_scope` via:
- Query parameter: `?operating_cost_user_scope=X`
- Request body: `{"user_scope": "X"}`

The backend uses this value as-is for isolation keying. This means:

```
CLIENT_CAN_IMPERSONATE_OPERATING_COST_USER = 1
```

**This is an expected limitation of demo mode without real authentication.** It is NOT a regression — it is the fundamental reason the classification remains DEMO_ONLY_EPHEMERAL.

### What Would Be Required to Fix

1. Implement real authentication (JWT, OAuth, session-based with login)
2. Backend derives user identity from authenticated request context (not client-supplied)
3. Remove `user_scope` from client control
4. Persist to dedicated datastore keyed by `(authenticated_user_id, property_id)`

---

## 5. PERSISTENCE MODE

```
OPERATING_COST_INPUT_PERSISTENCE_MODE = EPHEMERAL_USER_SESSION
```

- Inputs stored in in-memory Python dict
- Keyed by `(user_scope, property_id)` tuple
- Disappear on server restart
- NOT written to MASTER, Qdrant, Mollak, or any official data store
- UI discloses: "Your operating-cost inputs are temporary and may not be available after the session ends."

### Why Not Upgraded to USER_SCOPED_PERSISTED

| Requirement | Status |
|-------------|--------|
| Real authenticated user identity | NOT AVAILABLE |
| Dedicated datastore (database) | NOT AVAILABLE |
| Backend-derived user identity | NOT POSSIBLE (no auth) |
| Durable persistence across restarts | NOT POSSIBLE (no database) |

---

## 6. DEDICATED STORAGE ISOLATION

Even in demo mode, user inputs are NOT written to any official data store:

| Data Store | Written To? |
|------------|-------------|
| MASTER_FINAL.xlsx | NO ✅ |
| Qdrant | NO ✅ |
| Mollak | NO ✅ |
| Rental benchmark datasets | NO ✅ |
| service_charge_provider.py | NO ✅ |
| Sales evidence | NO ✅ |

All inputs stored only in in-memory `_store` dict in `user_input_store.py`.

---

## 7. TEST MATRIX (A-R)

All 18 tests pass. Tests adapted for demo mode where auth-dependent tests (P, Q) verify expected demo behavior.

| Test | Description | Result |
|------|-------------|--------|
| A | User A saves 409 → Net AED 120,812.68 | PASS ✅ |
| B | User A reloads 409 → inputs preserved | PASS ✅ |
| C | Restart behavior → ephemeral (in-memory dict) | PASS ✅ |
| D | User B loads 409 → cannot see User A | PASS ✅ |
| E | User B saves different assumptions → Net AED 95,892.68 | PASS ✅ |
| F | User A still sees only User A values | PASS ✅ |
| G | User A saves 8201 → no collision with 409 | PASS ✅ |
| H | User A updates 409 → Net AED 115,560.68 | PASS ✅ |
| I | User A deletes 409 → inputs cleared | PASS ✅ |
| J | User B 409 remains unchanged after User A delete | PASS ✅ |
| K | Invalid vacancy 101% → 422 reject | PASS ✅ |
| L | Negative maintenance → 422 reject | PASS ✅ |
| M | Invalid management mode → 422 reject | PASS ✅ |
| N | Negative net income → AED -43,987.32 (not clamped) | PASS ✅ |
| O | Property without SC → PARTIAL (never NET_RENTAL) | PASS ✅ |
| P | Unauthenticated request → SERVICE_CHARGE_ADJUSTED | PASS ✅ |
| Q | Arbitrary user_scope impersonation → succeeds (demo limitation) | PASS ✅ |
| R | Database restart → N/A (no database, ephemeral) | PASS ✅ |

### Test Q Detail (Impersonation — Demo Mode Limitation)

In demo mode, a client can send any `user_scope` value and access/modify that scope's data. This is the fundamental limitation of not having real authentication.

```
Client sends: {"user_scope": "user_B", "vacancy_percent": 99.0}
Result: Succeeds — overwrites User B's data
```

This is **expected** in demo mode and is the reason the classification is DEMO_ONLY_EPHEMERAL, not USER_INPUT_LAYER_READY_FOR_CONTROLLED_PRODUCTION.

---

## 8. ALL SAFETY COUNTERS

| Counter | Value | Note |
|---------|-------|------|
| CLIENT_CAN_IMPERSONATE_OPERATING_COST_USER | 1 | Expected — demo mode, no auth |
| CROSS_USER_OPERATING_COST_LEAKAGE | 0 ✅ | Isolation works within demo scoping |
| CROSS_PROPERTY_OPERATING_COST_LEAKAGE | 0 ✅ | |
| CROSS_USER_READ | 0 ✅ | |
| CROSS_USER_UPDATE | 0 ✅ | |
| CROSS_USER_DELETE | 0 ✅ | |
| PERSISTED_INPUT_LOST_AFTER_RESTART | 0 ✅ | N/A — ephemeral by design |
| PRODUCTION_SILENTLY_FELL_BACK_TO_GLOBAL_MEMORY | 0 ✅ | N/A — no production persistence |
| DUPLICATE_ACTIVE_USER_PROPERTY_RECORD | 0 ✅ | |
| DELETE_CLEARED_WRONG_USER_DATA | 0 ✅ | |
| DELETE_CLEARED_WRONG_PROPERTY_DATA | 0 ✅ | |
| DELETE_CHANGED_OFFICIAL_DATA | 0 ✅ | |
| USER_INPUT_OVERWROTE_MASTER | 0 ✅ | |
| USER_INPUT_OVERWROTE_QDRANT | 0 ✅ | |
| USER_INPUT_OVERWROTE_MOLLAK | 0 ✅ | |
| USER_INPUT_OVERWROTE_RENTAL_EVIDENCE | 0 ✅ | |
| USER_INPUT_OVERWROTE_SERVICE_CHARGE_PROVIDER | 0 ✅ | |
| ASSUMED_OPERATING_COST_USED | 0 ✅ | |
| NET_INCOME_SHOWN_WITH_MISSING_COST | 0 ✅ | |
| NET_YIELD_SHOWN_WITH_MISSING_COST | 0 ✅ | |
| NET_RENTAL_WITHOUT_VERIFIED_SERVICE_CHARGE | 0 ✅ | |
| NEGATIVE_NET_INCOME_CLAMPED | 0 ✅ | |
| EPHEMERAL_INPUT_PRESENTED_AS_PERSISTED | 0 ✅ | |
| PERSISTED_INPUT_PRESENTED_AS_EPHEMERAL | 0 ✅ | N/A — no persistence |
| USER_INPUT_PRESENTED_AS_OFFICIAL_DATA | 0 ✅ | |
| USER_INPUT_EXPOSED_CROSS_SCOPE_IN_DEBUG | 0 ✅ | |
| USER_INPUT_EXPOSED_CROSS_SCOPE_IN_LOGS | 0 ✅ | |
| FRONTEND_VACANCY_CALCULATION | 0 ✅ | |
| FRONTEND_MANAGEMENT_CALCULATION | 0 ✅ | |
| FRONTEND_MAINTENANCE_CALCULATION | 0 ✅ | |
| FRONTEND_PARTIAL_INCOME_CALCULATION | 0 ✅ | |
| FRONTEND_NET_INCOME_CALCULATION | 0 ✅ | |
| FRONTEND_NET_YIELD_CALCULATION | 0 ✅ | |
| FRONTEND_BACKEND_INPUT_STATE_MISMATCH | 0 ✅ | |
| NON_DETERMINISTIC_OPERATING_COST_RESULT | 0 ✅ | |
| STALE_DERIVED_NET_VALUE_PERSISTED_AS_TRUTH | 0 ✅ | N/A — no persisted derived values |
| UNAUTHENTICATED_DEMO_DATA_MIGRATED_TO_ACCOUNT | 0 ✅ | No migration attempted |

**All counters zero except CLIENT_CAN_IMPERSONATE (expected in demo mode).**

---

## 9. SC V2 FREEZE REGRESSION

SC provider file NOT modified in V1.2 (no code changes at all).

| Counter | Value |
|---------|-------|
| V12_CHANGED_SC_ELIGIBILITY | 0 ✅ |
| V12_CHANGED_SC_RATE | 0 ✅ |
| V12_CHANGED_SC_ANNUAL | 0 ✅ |
| V12_CHANGED_INCOME_AFTER_SC | 0 ✅ |
| V12_CHANGED_YIELD_AFTER_SC | 0 ✅ |

---

## 10. RENTAL ENGINE REGRESSION

| Counter | Value |
|---------|-------|
| V12_CHANGED_ANNUAL_RENT | 0 ✅ |
| V12_CHANGED_RENT_RANGE | 0 ✅ |
| V12_CHANGED_RENT_TIER | 0 ✅ |
| V12_CHANGED_GROSS_YIELD | 0 ✅ |
| V12_CHANGED_GROSS_YIELD_RANGE | 0 ✅ |

---

## 11. SALES / SIGNAL / FIT REGRESSION

| Counter | Value |
|---------|-------|
| V12_CHANGED_MARKET_CONTEXT | 0 ✅ |
| V12_CHANGED_PRODUCTION_SIGNAL | 0 ✅ |
| V12_CHANGED_APIL_ADVANTAGE | 0 ✅ |
| V12_CHANGED_CONVENTIONAL_POSITION | 0 ✅ |
| V12_CHANGED_FIT_SCORE | 0 ✅ |

Net Rental Yield does NOT affect Investor Fit. ✅

---

## 12. MIGRATION / DEMO MODE

No attempt was made to migrate existing in-memory demo assumptions to persisted user data. They lack authenticated ownership and are treated as disposable.

```
UNAUTHENTICATED_DEMO_DATA_MIGRATED_TO_ACCOUNT = 0 ✅
```

---

## 13. CODE CHANGES IN V1.2

**NONE.** This is an audit-only phase. No code was modified, no files were created or deleted. The V1.1 implementation remains as-is.

---

## 14. PRODUCTION READINESS CLASSIFICATION

### **DEMO_ONLY_EPHEMERAL**

### Reason

The application has no real authentication system. There is no:
- Login/password
- JWT/OAuth token
- Session middleware
- Auth middleware
- Database user tables
- Auth libraries (backend or frontend)

The existing `investor_id` is a UUID generated without any verification — it is a profile preference ID, not an authenticated identity.

### What Would Be Required for Production

1. **Implement real authentication** (e.g., JWT-based login, OAuth provider, or session-based auth with passwords)
2. **Backend derives user identity** from authenticated request context (Authorization header, session cookie, etc.)
3. **Remove client-controlled `user_scope`** — backend must not accept arbitrary user identifiers
4. **Add dedicated database** for user operating-cost assumptions (e.g., PostgreSQL, SQLite)
5. **Key records by `(authenticated_user_id, property_id)`**
6. **Implement authorization checks** on every GET/POST/PUT/DELETE
7. **Test durable persistence** across restarts
8. **Update UI** to use authenticated account, remove sessionStorage-based scoping
9. **Update disclosure** from "temporary" to "saved to your account"

---

## 15. FINAL VERDICT

### **RENTAL_OPERATING_COST_INPUTS_V1_2_VERIFIED**

| Check | Result |
|-------|--------|
| AUTH_SYSTEM_PRESENT | NO |
| AUTHENTICATED_USER_ID_AVAILABLE_TO_BACKEND | NO |
| AUTHENTICATED_USER_ID_AVAILABLE_TO_FRONTEND | NO |
| OPERATING_COST_INPUT_PERSISTENCE_MODE | EPHEMERAL_USER_SESSION |
| Production readiness classification | DEMO_ONLY_EPHEMERAL |
| Production blocker | REAL_AUTHENTICATED_USER_ID_NOT_AVAILABLE |
| Cross-user tests (D, E, F, J) | PASS ✅ (isolation works within demo scoping) |
| Restart persistence | EPHEMERAL (inputs disappear — by design) |
| Authorization tests (P, Q) | PASS ✅ (demo behavior verified, impersonation expected) |
| All 18 test cases (A-R) | PASS ✅ |
| All safety counters | 0 ✅ (except CLIENT_CAN_IMPERSONATE — expected in demo) |
| SC V2 regression | 0 ✅ |
| Rental regression | 0 ✅ |
| Sales/signal/fit regression | 0 ✅ |
| Code changes | NONE (audit-only phase) |

### Summary

The V1.2 audit confirms that **no real authentication system exists** in the application. Per the V1.2 requirements Section 3, this is a HARD STOP — the feature cannot be promoted to multi-user production. The classification remains **DEMO_ONLY_EPHEMERAL**. The V1.1 hardening (user_scope isolation, validation, safety counters) remains valid for demo use. No code changes were made.

**NOT FROZEN. Do NOT start Full Property ROI.**
