# Stale Rental Data Archive

## Contents
- `dxb_rents_all_196k_stale.csv` — moved here from `apil-investment-demo/dxb_rents_all.csv` on 2026-08-20.

## Status
**Historical projected/filtered export. NOT an authoritative rental source. Do not use for rental methodology.**

## Why archived
- 196,560 rows, 20 columns (projected schema — missing AR fields, IDs, AREA_ID, PARCEL_ID, PROPERTY_ID).
- Date range 2026-02-01 → 2026-04-08 only (67 dates) — a narrow subset.
- SHA256: `c99f0d83b48bbfdbda7e32e10f748b9041f59b43202fe737c3cbbf12deb11d0b`
- Not used by the rental engine (which reads the 573K-row parent-dir file via `Path(__file__).parent.parent.parent.parent / "dxb_rents_all.csv"`).
- Kept for traceability; contents unchanged. Verified `ACTIVE_REFERENCE_TO_STALE_196K_FILE = 0` before archiving.

## Authoritative rental source (use this instead)
`/Users/apple/Desktop/Ai 3d view/dxb_rents_all.csv`
- 573,001 rows, 44 columns, full DLD Ejari schema.
- SHA256: `92546471b4326a89ca5980381b918cd5077d277eae396edf0374d9448d91129d`
- Date range: 2026-01-01 → 2026-08-09 (215 unique registration dates).
- Deterministically deduplicated (573,001 rows = 573,001 unique keys on the 16-col merge key).
