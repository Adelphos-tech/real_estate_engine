# RENTAL OPERATING COST INPUTS V1 — UI DEMO FROZEN

**Date**: 2026-08-22
**Freeze Identifier**: `RENTAL_OPERATING_COST_INPUTS_V1_UI_DEMO_FROZEN`
**Component**: `src/components/OperatingCostsCard.tsx`

---

## 1. COMPONENT BEHAVIOR

### OperatingCostsCard Responsibilities

| Responsibility | Status |
|----------------|--------|
| Collect user inputs (vacancy, management, maintenance) | YES ✅ |
| Send inputs to backend via POST | YES ✅ |
| Display backend response (calculated values) | YES ✅ |
| Format values for display only | YES ✅ |

### What the Frontend Does NOT Do

| Calculation | Counter | Value |
|-------------|---------|-------|
| Vacancy loss | FRONTEND_VACANCY_CALCULATION | 0 ✅ |
| Management cost | FRONTEND_MANAGEMENT_CALCULATION | 0 ✅ |
| Maintenance cost | FRONTEND_MAINTENANCE_CALCULATION | 0 ✅ |
| Partial income | FRONTEND_PARTIAL_INCOME_CALCULATION | 0 ✅ |
| Net Rental Income | FRONTEND_NET_INCOME_CALCULATION | 0 ✅ |
| Net Rental Yield | FRONTEND_NET_YIELD_CALCULATION | 0 ✅ |

**All calculations happen on the backend.** The frontend only sends raw inputs and displays the backend's calculated results.

---

## 2. "YOUR INPUTS" LABELS

### User Input Section

The input section header is:

```
OPERATING COSTS
```

Individual input labels:

| Input | Label |
|-------|-------|
| Vacancy | "Vacancy" |
| Property Management | "Property Management" |
| Unit Maintenance | "Unit Maintenance" |

### Provenance Display

Each input shows its source when available:

| Source Display | Meaning |
|----------------|---------|
| `Source: USER_INPUT` | User entered this value |
| `Source: SELF_MANAGED` | User selected self-manage |

### Official Data (Separate)

Official service charges are displayed in a separate card (`RentalIncomeCard`) with:

```
Source: DLD/RERA Mollak
```

User inputs and official data are visually and semantically separated.

```
USER_INPUT_PRESENTED_AS_OFFICIAL_DATA = 0 ✅
```

---

## 3. TEMPORARY-INPUT DISCLOSURE

### Ephemeral Persistence Disclosure

Displayed at the bottom of OperatingCostsCard (line 356-358):

```
Your operating-cost inputs are temporary and may not be available
after the session ends.
```

This disclosure is **always visible** when the OperatingCostsCard is shown.

```
EPHEMERAL_INPUT_PRESENTED_AS_PERSISTED = 0 ✅
```

### No-Inputs Hint

When no inputs have been entered (line 348-353):

```
Enter vacancy, property management, and maintenance costs above
to calculate Net Rental Income. These values are based on your
inputs only — they are not verified data.
```

---

## 4. PARTIAL vs NET LABELS

### PARTIAL_OPERATING_COSTS Level

When some (but not all) operating costs are entered:

- **Label**: "Income After Known Operating Costs"
- **Color**: Amber (amber-50 background, amber-700 text)
- **Partial disclosure**: "This is not Net Rental Income because one or more operating cost inputs are still missing."
- `net_rental_income_aed` is NOT displayed
- `net_rental_yield_pct` is NOT displayed

### NET_RENTAL Level

When ALL operating costs + verified SC are available:

- **Label**: "Net Rental Income"
- **Color**: Emerald (emerald-50 background, emerald-700 text)
- **Also shows**: "Net Rental Yield" with percentage
- No partial disclosure

### SERVICE_CHARGE_ADJUSTED Level

When no operating cost inputs are entered:

- No results section shown
- Only the no-inputs hint is displayed

---

## 5. INCLUDED / NOT INCLUDED LISTS

### Included Costs

When inputs are present, the card shows a list of included costs:

```
Included in this calculation:
  ✓ Estimated annual market rent
  ✓ Official DLD/RERA Mollak service charges
  ✓ Your vacancy allowance
  ✓ Your property management cost
  ✓ Your unit maintenance cost
```

### Not Included (Missing) Costs

```
Not included:
  — Unit maintenance
```

This makes it clear to the user what is and isn't in the calculation.

---

## 6. NO FRONTEND CALCULATIONS

### Data Flow

```
User enters inputs in OperatingCostsCard
    ↓
Frontend sends POST /properties/{id}/operating-costs
    with {user_scope, vacancy_input_mode, vacancy_percent, ...}
    ↓
Backend validates inputs (operating_cost_validation.py)
    ↓
Backend stores inputs in-memory (user_input_store.py)
    ↓
Backend calculates all values (operating_cost_calculator.py)
    ↓
Frontend reloads page → GET /properties/{id}
    ↓
Backend returns rental_operating_cost_context with all calculated values
    ↓
Frontend displays the values (formatting only)
```

### Value Formatting

The frontend uses `formatAEDFull()` for display:

```typescript
function formatAEDFull(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(n)) return 'N/A';
  return `AED ${n.toLocaleString()}`;
}
```

This is **formatting only** — no calculation.

---

## 7. NEGATIVE-RESULT BEHAVIOR

When user inputs produce a negative Net Rental Income:

- The actual negative value is displayed (e.g., "AED -43,027")
- The value is NOT clamped to zero
- The value is NOT hidden
- The Net Rental Yield is also shown as negative (e.g., "-1.59%")

```
NEGATIVE_NET_INCOME_CLAMPED = 0 ✅
```

---

## 8. SESSION USER SCOPE

### Generation

```typescript
function getSessionUserScope(): string {
  const KEY = 'apil_operating_cost_user_scope';
  let scope = sessionStorage.getItem(KEY);
  if (!scope) {
    scope = `session_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    sessionStorage.setItem(KEY, scope);
  }
  return scope;
}
```

### Properties

- Stored in `sessionStorage` (disappears when tab closes)
- Generated once per browser tab session
- Sent as `user_scope` in POST body and DELETE query parameter
- NOT an authenticated identity
- Client-controlled (KNOWN DEMO LIMITATION)

---

## 9. SAVE / CLEAR BEHAVIOR

### Save Inputs

1. Collects all input fields into `OperatingCostInputRequest`
2. Sends POST to `/properties/{id}/operating-costs`
3. On success: shows "Saved. Calculations updated." then reloads page
4. On error: shows validation error message

### Clear Inputs

1. Sends DELETE to `/properties/{id}/operating-costs?user_scope=...`
2. Resets all local input state
3. Shows "Cleared." then reloads page

### Page Reload

After save/clear, the page reloads to fetch fresh data from the backend. This ensures the displayed values come from the backend, not from frontend state.

---

## 10. UI ELEMENTS SUMMARY

| Element | Purpose | Calculation? |
|---------|---------|-------------|
| Vacancy select + input | Collect vacancy mode + value | NO |
| Management select + input | Collect management mode + value | NO |
| Maintenance input | Collect maintenance AED | NO |
| Save button | Send inputs to backend | NO |
| Clear button | Delete inputs from backend | NO |
| "Income After Known Operating Costs" | Display partial result | NO (display only) |
| "Net Rental Income" | Display net result | NO (display only) |
| "Net Rental Yield" | Display yield | NO (display only) |
| Included/Not included lists | Display what's in calculation | NO (display only) |
| Disclosure text | Inform user about ephemeral nature | N/A |
| Source labels | Show provenance | NO (display only) |

---

## 11. FREEZE IDENTIFIER

```
RENTAL_OPERATING_COST_INPUTS_V1_UI_DEMO_FROZEN
```

This is NOT:
- `RENTAL_OPERATING_COST_INPUTS_V1_UI_PRODUCTION_FROZEN`
- An authenticated UI freeze
- A multi-user production UI freeze

---

## 12. VERIFICATION

| Check | Result |
|-------|--------|
| Frontend calculates vacancy loss | NO ✅ |
| Frontend calculates management cost | NO ✅ |
| Frontend calculates maintenance cost | NO ✅ |
| Frontend calculates partial income | NO ✅ |
| Frontend calculates Net Rental Income | NO ✅ |
| Frontend calculates Net Rental Yield | NO ✅ |
| UI discloses ephemeral nature | YES ✅ |
| UI labels user inputs separately from official data | YES ✅ |
| UI shows partial label (not Net) when costs missing | YES ✅ |
| UI shows negative values (not clamped) | YES ✅ |
| UI shows provenance source for each input | YES ✅ |
| UI shows included/missing cost lists | YES ✅ |
