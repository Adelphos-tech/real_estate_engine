# APIL Investment Engine — Investor API

**Version:** 1.0.0
**Source:** Locked Step 5 (`STEP_5_API_READY.jsonl`)
**Status:** Production-ready (Steps 1–7 locked)

---

## Architecture

```
Data → Classification → Developer Grade → DLD Benchmark → Investment Logic → Confidence Gate → API → Investor UI
```

This API is a **read-only presentation layer**. It does not recalculate grades, benchmarks, price advantages, or investment decisions. All data is sourced from the locked Step 5 JSONL file.

---

## Quick Start

```bash
pip install -r requirements.txt
python3 main.py
```

Open http://localhost:8000/ui in your browser for the demo frontend.

---

## API Endpoints

### `GET /`
Service status and loaded counts.

### `GET /properties/{property_id}`
Full investor card for a single property. Includes all benchmarks (even unusable ones) for transparency, but unusable benchmarks have `price_advantage_pct = null`.

### `GET /opportunities`
Ranked opportunity marketplace.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `decision` | string | Filter by decision tier |
| `min_price` | int | Minimum price (AED) |
| `max_price` | int | Maximum price (AED) |
| `developer_grade` | string | Grade prefix (e.g., `A`, `B+`) |
| `area` | string | Area name substring |
| `bedrooms` | int | Bedroom count |
| `min_advantage_pct` | float | Minimum best usable advantage |
| `max_advantage_pct` | float | Maximum best usable advantage |
| `include_insufficient` | bool | Default: `false`. Include `INSUFFICIENT_EVIDENCE` |
| `sort_by` | string | `rank`, `price`, `advantage`, `developer_grade` |
| `page` | int | Default: 1 |
| `per_page` | int | Default: 20, max: 100 |

**Safety:** `INSUFFICIENT_EVIDENCE` is excluded by default. The caller must explicitly set `include_insufficient=true` to see these.

### `GET /developers`
List all developers with summary statistics.

### `GET /developers/{developer_name}`
Developer detail page with all properties and grade/decision distribution.

### `POST /compare`
Side-by-side comparison of 2–3 properties.

**Request Body:**
```json
{"property_ids": ["id1", "id2", "id3"]}
```

### `GET /ui`
Simple HTML demo frontend.

---

## Response Schema (Property)

```json
{
  "property": {
    "id": "...",
    "name": "...",
    "area": "...",
    "sub_project": "...",
    "property_type": "...",
    "bedrooms": 2,
    "size_sqm": 85.5,
    "current_price_aed": 715000
  },
  "developer": {
    "name": "...",
    "grade": "A",
    "quality_tier": "HIGH QUALITY",
    "grade_explanation": "..."
  },
  "benchmarks": [
    {
      "type": "OFFPLAN_RESALE",
      "median_price_aed": 1719777,
      "mean_price_aed": 1778043,
      "transaction_count": 15,
      "match_level": "project_fuzzy",
      "confidence": "Medium",
      "price_advantage_pct": 140.53,
      "usable_for_investment": true
    }
  ],
  "price_analysis": {
    "best_usable_advantage_pct": 140.53,
    "best_usable_benchmark_type": "OFFPLAN_RESALE",
    "advantage_primary_pct": 140.53,
    "advantage_offplan_pct": 140.53,
    "advantage_ready_pct": null,
    "benchmark_agreement": "CONSISTENT_POSITIVE",
    "evidence_strength": "STRONG"
  },
  "investment_decision": {
    "decision": "STRONG_OPPORTUNITY",
    "confidence": "HIGH",
    "gate_applied": "GATE: High confidence + strong positive → Strong Opportunity",
    "decision_reason": "...",
    "recommendation": "...",
    "warnings": []
  },
  "data_quality": {
    "benchmark_confidence": "Medium",
    "usable_for_signal": true,
    "quality_flags": [],
    "last_updated": "2026-08-12"
  },
  "meta": {
    "pipeline_version": "1.0.0",
    "step_3c_locked": true,
    "step_4_locked": true,
    "step_5_locked": true
  }
}
```

---

## Frontend Safety Rules (API-Enforced)

| Rule | Enforcement |
|------|-------------|
| **No recalculation** | API reads locked Step 5 JSONL only |
| **No internal fields leaked** | `_ranking`, raw scores removed from responses |
| **Unusable benchmarks null** | `price_advantage_pct = null` when `usable_for_investment = false` |
| **INSUFFICIENT_EVIDENCE excluded** | Default `include_insufficient=false` |
| **Every decision has context** | `decision`, `confidence`, `reason`, `recommendation`, `warnings` always present |
| **Benchmarks bundled with metadata** | Every benchmark includes `transaction_count`, `confidence`, `match_level`, `usable_for_investment` |

---

## Pipeline Status

| Step | Status |
|------|--------|
| Step 1 — Qdrant ↔ DLD matching | Locked |
| Step 2 — Pricing benchmarks | Locked |
| Step 3A — Developer grading | Locked |
| Step 3C — Investment decision + confidence gate | Locked |
| Step 4 — Investor-facing explanation | Locked |
| Step 5 — API normalization + ranking | Locked |
| Step 6 — Evidence integrity audit | `PASS_WITH_WARNINGS` — Locked |
| Step 7 — Production acceptance test | `PASS` — Locked |
| **Investor API** | **Built on Step 5** |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STEP5_PATH` | `/Users/apple/Desktop/STEP_5_API_READY.jsonl` | Path to locked Step 5 data |

---

## License

Proprietary — APIL Investment Engine
