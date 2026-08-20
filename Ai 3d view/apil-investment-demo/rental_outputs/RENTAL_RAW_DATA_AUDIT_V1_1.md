# Rental Raw Data Audit V1.1 — History Expansion Investigation

**Date**: 2026-08-20
**Scope**: Handoff §34 — search the project for older raw DLD/Ejari rental files; report path, SHA256, row count, date range, schema; deduplicate deterministically; do not fabricate history.
**Status**: RESEARCH ONLY. No production code touched. No frozen-runtime files modified.

---

## 1. Executive Summary

| Question | Answer |
|----------|--------|
| Does older raw Ejari history (pre-2026) exist in the repository? | **NO** |
| Verdict | **TEMPORAL_HISTORY_LIMITED** |
| Should the 650K file replace the 573K file? | **NO — 573K is the correct deduplicated union; 650K adds duplicates, not history** |
| Authoritative rental source (unchanged) | `/Users/apple/Desktop/Ai 3d view/dxb_rents_all.csv` (573,001 rows, SHA `92546471…`) |
| Full temporal window available | 2026-01-01 → 2026-08-09 (215 unique registration dates) |

**No raw Ejari history prior to 2026-01-01 exists anywhere in the project or its parent directory.** The DLD open-data API fetch scripts (`fetch_dld_rents.py`, `fetch_dld_rents_parallel.py`) were explicitly scoped to `P_FROM_DATE: 01/01/2026`, `P_TO_DATE: 08/10/2026`. No older backup, archive, or alternative source containing pre-2026 rental contracts was found. History will not be fabricated.

---

## 2. Candidate Raw Rental Files — Full Audit

All candidates live in `/Users/apple/Desktop/Ai 3d view/` (parent of the project) unless noted. Personal `~/Downloads` was checked — no rental/Ejari files present there.

| # | File | SHA256 | Data rows | Cols | Date min | Date max | Unique dates | Verdict |
|---|------|--------|-----------|------|----------|----------|--------------|---------|
| 1 | `dxb_rents_all.csv` | `92546471b4326a89ca5980381b918cd5077d277eae396edf0374d9448d91129d` | 573,001 | 44 | 2026-01-01 | 2026-08-09 | 215 | **AUTHORITATIVE** (engine source) |
| 2 | `dxb_rents.csv` | `1e1a0e4ae45da357dce5a93faf6f3ae4cf70cb257d3c5dbf32425b50d79c243a` | 650,040 | 44 | 2026-01-01 | 2026-08-09 | 214 | Redundant superset w/ dupes |
| 3 | `dld_rents_2026_full.csv` | `b48cfa69fe85b2ec390697c23345e713aba513e5da98f28f0fe6d9c17baaecaf` | 650,040 | 44 | 2026-01-01 | 2026-08-09 | 214 | Redundant superset w/ dupes |
| 4 | `dxb_rents_old_backup.csv` | `7a74ea2a9da808d585f56bccae276a9f4528d3dcbe16626304c9160833fa8a73` | 2,235 | 41 | 2026-07-04 | 2026-08-04 | 32 | Small July backup; subset already merged into #1 |
| 5 | `dld_rents_2026.csv` | `5899a2e70794456d28c7d06c537287a21927e1daab759782c7ea6d71c3bd1628` | 34 | 1 | n/a | n/a | 0 | **FAILED FETCH** — HTML error page (`<!doctype html>`), not CSV. Discard. |
| 6 | `apil-investment-demo/dxb_rents_all.csv` (project root) | `c99f0d83b48bbfdbda7e32e10f748b9041f59b43202fe737c3cbbf12deb11d0b` | 196,560 | 20 | 2026-02-01 | 2026-04-08 | 67 | **STALE / DIFFERENT SCHEMA** — 20-col projected export, not raw. NOT used by engine. Discard. |

### Schema notes
- Files #1–#4 share the full 44-column DLD Ejari schema (RN, REGISTRATION_DATE, START_DATE, END_DATE, AREA_EN, CONTRACT_AMOUNT, ANNUAL_AMOUNT, ACTUAL_AREA, PROP_TYPE_EN, PROP_SUB_TYPE_EN, ROOMS, USAGE_EN, PROJECT_EN, MASTER_PROJECT_EN, TOTAL_PROPERTIES, VERSION_EN, …).
- File #4 (`dxb_rents_old_backup.csv`) has 41 cols (missing the 3 `_AR` fields) — otherwise compatible.
- File #6 (project root) has only 20 cols (no AR fields, no IDs, no AREA_ID/PARCEL_ID/PROPERTY_ID) — a projected/filtered export, not a raw pull. **Not a valid raw source.**

---

## 3. Provenance (from fetch / merge scripts)

- `fetch_dld_rents.py` and `fetch_dld_rents_parallel.py` call the DLD open-data API (`gateway.dubailand.gov.ae/open-data/rents`) with `P_FROM_DATE: 01/01/2026`, `P_TO_DATE: 08/10/2026`. Output: `dld_rents_2026_full.csv` (650K). The parallel script splits the pull by month (Jan–Aug 2026).
- `merge_rents.py` deterministically dedupes `dld_rents_2026_full.csv` (new) + `dxb_rents.csv` (old) on a 16-column key (`REGISTRATION_DATE, START_DATE, END_DATE, AREA_EN, CONTRACT_AMOUNT, ANNUAL_AMOUNT, ACTUAL_AREA, PROP_TYPE_EN, PROP_SUB_TYPE_EN, ROOMS, USAGE_EN, PROJECT_EN, MASTER_PROJECT_EN, IS_FREE_HOLD_EN, VERSION_EN`) and writes `dxb_rents_all.csv` (573K).

**File mtimes**:
- `fetch_dld_rents_parallel.py`: 2026-08-10 18:14
- `merge_rents.py`: 2026-08-10 20:57
- `dxb_rents_all.csv` (573K, merge output): 2026-08-10 20:57
- `dxb_rents.csv` (650K): 2026-08-11 00:58
- `dxb_rents_old_backup.csv`: 2026-08-11 00:58
- `dld_rents_2026_full.csv` (650K): 2026-08-12 14:24
- project-root `dxb_rents_all.csv` (196K stale): 2026-08-20 12:37

The 650K files were re-pulled/overwritten on 08-11/08-12, **after** the 573K merge was produced on 08-10. The subset analysis below confirms the newer 650K pulls do **not** add unique data beyond the 573K file.

---

## 4. 573K vs 650K — Deterministic Subset Analysis

Dedup key = the 16-column key from `merge_rents.py` (deterministic, no fuzzy matching).

| Metric | Value |
|--------|-------|
| 573K file rows | 573,001 |
| 573K file unique keys | 573,001 (zero internal dups) |
| 650K file (`dxb_rents.csv`) rows | 650,040 |
| 650K file unique keys | 570,808 (**79,232 internal duplicates**) |
| Intersection (keys in both) | 570,808 |
| Rows in 573K NOT in 650K | **2,193** |
| Rows in 650K NOT in 573K | **0** |

**Findings:**
1. The 650K file's entire unique content (570,808 keys) is a **strict subset** of the 573K file.
2. The 650K file carries **~79,232 duplicate rows** (same contract key repeated) — almost certainly from the parallel month-bounded fetch re-emitting contracts near month boundaries.
3. The 573K file contains **2,193 unique contracts the 650K file does not** — all legitimate July 2026 registrations (2026-07-04 → 2026-08-04, 32 dates), all `VERSION_EN=New`, all `TOTAL_PROPERTIES=1`, real projects (e.g. Business Bay / Century). These originated from the `dld_rents_2026_full.csv` present at merge time (later overwritten).

**Conclusion:** The 573K `dxb_rents_all.csv` is the **cleanest, most complete** raw source — it is the deduplicated union of both 650K pulls plus 2,193 July contracts. Switching to a 650K file would:
- add **zero** new unique contracts,
- inject **~79K duplicate comparables**, which would **bias medians** (duplicate contracts counted multiple times) and **harm** every estimator (A/B/C/D).

**Recommendation: KEEP the 573K `dxb_rents_all.csv` as the V1.1 rental source. Do NOT switch to 650K.**

---

## 5. Deterministic Dedupe Status

The authoritative 573K file is **already deterministically deduplicated** (573,001 rows = 573,001 unique keys; zero internal duplicates on the 16-col key). No further dedupe is required for V1.1. The rental data store's existing load filter (`TOTAL_PROPERTIES==1` + residential + bounds) then reduces 573,001 → 384,161 usable comparables (per `RENTAL_RAW_DATA_AUDIT_V1.md`).

---

## 6. Temporal History Verdict

**TEMPORAL_HISTORY_LIMITED**

- Earliest registration date in any candidate: **2026-01-01**.
- Latest registration date: **2026-08-09**.
- No pre-2026 Ejari history exists in the repository or parent directory.
- The DLD API fetch was scoped to 2026-01-01 onwards by script; no older archive/backup is present.
- Personal `~/Downloads` contains no rental/Ejari files (excluded per handoff §34).

**Implications for V1.1 (carried forward to bias/robustness work):**
- True walk-forward holdout is constrained to an ~8-month window. The V1 cutoff of 2026-03-31 leaves only ~4 months of test data (Apr–Aug), which is why only 13/301 tier-hit properties had sufficient train+test leases.
- Recency-weighting research (handoff §38) must be evaluated within this window; do not assume longer history exists.
- Do NOT fabricate pre-2026 history. Do NOT synthesize a longer time series.

---

## 7. Safety / Compliance Check

| Rule | Status |
|------|--------|
| No personal Downloads used | ✅ confirmed (none present) |
| No legacy rental estimates / ROI outputs reused | ✅ (audit only reads raw CSVs) |
| No frozen-runtime file modified | ✅ (only this report written to `rental_outputs/`) |
| No history fabricated | ✅ |
| Deterministic dedupe (no fuzzy matching) | ✅ (16-col exact key) |

---

## 8. Decisions Carried Into V1.1

1. **Rental CSV source**: unchanged — `/Users/apple/Desktop/Ai 3d view/dxb_rents_all.csv` (573,001 rows, SHA `92546471…`, 2026-01-01 → 2026-08-09). The 650K files are rejected (redundant + duplicate-laden).
2. **Temporal window**: 2026-01-01 → 2026-08-09 only. TEMPORAL_HISTORY_LIMITED. Walk-forward holdout cutoffs must respect this.
3. **Stale project-root `dxb_rents_all.csv` (196K, 20-col)**: explicitly NOT used; flagged for cleanup (not removed in this pass — removal is a destructive op requiring user confirmation).
4. **Next V1.1 step**: proceed to bias breakdown (handoff §32) and estimator/area-balanced validation (§35–37), reusing the existing V1 holdout predictions where possible and re-running with the confirmed 573K source.
