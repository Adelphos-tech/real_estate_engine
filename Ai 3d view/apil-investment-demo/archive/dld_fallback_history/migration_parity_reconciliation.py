"""
FINAL MIGRATION PARITY CHECK — Reconcile Phase 6 shadow vs post-migration production.
==================================================
Do NOT modify production code.
Run side-by-side comparison using existing functions.
"""

import math
import os
from collections import Counter
from datetime import datetime
from statistics import median
from typing import Dict, List, Optional, Tuple

import pandas as pd

OUTPUT_DIR = "/Users/apple/Desktop/Ai 3d view/apil-investment-demo"


def _canonical_status(status_raw: str) -> str:
    s = str(status_raw).lower()
    if "pre" in s or "offplan" in s or "sell - pre" in s:
        return "Offplan"
    return "Ready"


def run_parity_reconciliation():
    import sys
    sys.path.insert(0, '/Users/apple/Desktop/Ai 3d view/apil-investment-demo')
    from investor_api.dld_benchmark_engine import (
        compute_project_benchmark, _DLD_STORE, _is_sale_transaction,
        _build_composite_transaction_key, _parse_price
    )
    from investor_api.fallback.dld_fallback_v6_phase6 import (
        compute_project_benchmark_sales_only_v2
    )
    from investor_api.fallback.dld_fallback_engine import load_master_df

    print("=" * 70)
    print("MIGRATION PARITY RECONCILIATION")
    print("=" * 70)

    master_df = load_master_df()
    print(f"\nMASTER loaded: {len(master_df)} properties")

    # Reconstruct "pre-migration" by temporarily running current engine
    # WITHOUT sales-only filtering.  We do this by calling a helper that
    # bypasses the sales filter in compute_project_benchmark.
    # Since compute_project_benchmark is now monolithic, we replicate the
    # OLD pipeline here for a clean pre-migration baseline.

    def old_compute_project_benchmark_no_sales(
        project_name: str,
        subject_price: float,
        bedroom: Optional[int] = None,
        status: Optional[str] = None,
        exact_project_only: bool = True,
    ) -> Dict:
        """Replicate pre-migration logic: no sales filter, no dedup."""
        raw_txs = _DLD_STORE.get_transactions(project_name)
        if not raw_txs:
            return {
                "benchmark_median": None,
                "transaction_count": 0,
                "usable_for_investment": False,
                "insufficient_evidence_reason": f"No DLD transactions found for project '{project_name}'",
                "evidence_level": None,
                "matched_transaction_ids": [],
            }

        def _dld_procedure_to_status(p):
            p_norm = str(p).strip().lower()
            if "pre registration" in p_norm or "pre-registration" in p_norm:
                return "Offplan"
            if p_norm in ("sale", "sell"):
                return "Ready"
            return "Unknown"

        def _local_parse_bedrooms(rooms_raw):
            if not rooms_raw:
                return None
            rooms_norm = str(rooms_raw).strip().lower()
            if "studio" in rooms_norm:
                return 0
            if "b/r" in str(rooms_raw).lower() or "br" in rooms_norm:
                import re
                m = re.search(r"(\d+)", rooms_norm)
                if m:
                    return int(m.group(1))
            return None

        # Status filter
        if status is not None:
            status_filtered = [
                row for row in raw_txs
                if _dld_procedure_to_status(row.get("PROCEDURE_EN", "")) == status
            ]
        else:
            status_filtered = list(raw_txs)

        # Bedroom filter
        bedroom_filtered = []
        for row in status_filtered:
            parsed_br = _local_parse_bedrooms(row.get("ROOMS_EN", ""))

            if bedroom is None:
                bedroom_filtered.append(row)
            elif parsed_br is not None and parsed_br == bedroom:
                bedroom_filtered.append(row)

        # Outlier removal
        final_txs = []
        MIN_TRANSACTION_VALUE = 100_000
        for row in bedroom_filtered:
            price = _parse_price(row.get("TRANS_VALUE"))
            if price is None:
                continue
            if price >= MIN_TRANSACTION_VALUE:
                final_txs.append(row)

        # Fallback if status produced 0 — re-run bedroom filter on ALL raw_txs (no status filter)
        if not final_txs and status is not None:
            bedroom_filtered_all = []
            for row in raw_txs:
                parsed_br = _local_parse_bedrooms(row.get("ROOMS_EN", ""))
                if bedroom is None:
                    bedroom_filtered_all.append(row)
                elif parsed_br is not None and parsed_br == bedroom:
                    bedroom_filtered_all.append(row)
            final_txs = []
            for row in bedroom_filtered_all:
                price = _parse_price(row.get("TRANS_VALUE"))
                if price is not None and price >= MIN_TRANSACTION_VALUE:
                    final_txs.append(row)

        if not final_txs:
            return {
                "benchmark_median": None,
                "transaction_count": 0,
                "usable_for_investment": False,
                "insufficient_evidence_reason": "No usable transactions",
                "evidence_level": "NO_VERIFIED_EVIDENCE",
                "matched_transaction_ids": [],
            }

        prices = [float(r["TRANS_VALUE"]) for r in final_txs]
        med = median(prices)
        tx_ids = [r.get("TRANSACTION_NUMBER", "") for r in final_txs]

        return {
            "benchmark_median": med,
            "transaction_count": len(final_txs),
            "usable_for_investment": len(final_txs) >= 3,
            "insufficient_evidence_reason": None,
            "evidence_level": "EXACT_PROJECT_SAME_BEDROOM_EVIDENCE",
            "matched_transaction_ids": tx_ids,
        }

    all_rows = []
    parity_counters = {
        "SHADOW_PRODUCTION_USABLE_MISMATCH": 0,
        "SHADOW_PRODUCTION_MEDIAN_MISMATCH": 0,
        "SHADOW_PRODUCTION_TX_COUNT_MISMATCH": 0,
        "SHADOW_PRODUCTION_TRANSACTION_SET_MISMATCH": 0,
        "SHADOW_PRODUCTION_EVIDENCE_LEVEL_MISMATCH": 0,
    }

    # Decision-change definition comparison
    # Phase 6 compared: live.usable != shadow.usable (usable_for_investment bool)
    # Post-migration compared: master["dld_evidence_status"] == "DLD_MATCH" vs new_usable
    # These are DIFFERENT comparisons!

    # For standardized comparison, we'll compute:
    # old_usable = pre-migration usable_for_investment
    # shadow_usable = phase 6 shadow usable
    # prod_usable = current production usable

    for _, row in master_df.iterrows():
        prop_id = int(row["property_id"])
        property_name = str(row.get("property_name", "")).strip()
        bedrooms = row.get("unit_bedrooms")
        status = str(row.get("unit_status", "")).strip()
        price = float(row.get("current_price_aed", 0)) if pd.notna(row.get("current_price_aed")) else 0

        if isinstance(bedrooms, float) and math.isnan(bedrooms):
            bedrooms = None
        if bedrooms is not None:
            bedrooms = int(bedrooms)
        canonical_status = _canonical_status(status)

        # A. PRE-MIGRATION (old logic, no sales filter)
        pre = old_compute_project_benchmark_no_sales(
            project_name=property_name,
            subject_price=price,
            bedroom=bedrooms,
            status=canonical_status,
            exact_project_only=True,
        )

        # B. PHASE 6 SHADOW
        shadow = compute_project_benchmark_sales_only_v2(
            project_name=property_name,
            subject_price=price,
            bedroom=bedrooms,
            status=canonical_status,
            exact_project_only=True,
        )

        # C. CURRENT PRODUCTION
        prod = compute_project_benchmark(
            project_name=property_name,
            subject_price=price,
            bedroom=bedrooms,
            status=canonical_status,
            exact_project_only=True,
        )

        # Standardized comparisons
        pre_usable = pre.get("usable_for_investment", False)
        shadow_usable = shadow.get("usable_for_investment", False)
        prod_usable = prod.get("usable_for_investment", False)

        pre_median = pre.get("benchmark_median")
        shadow_median = shadow.get("benchmark_median")
        prod_median = prod.get("benchmark_median")

        pre_tx_count = pre.get("transaction_count", 0)
        shadow_tx_count = shadow.get("transaction_count", 0)
        prod_tx_count = prod.get("transaction_count", 0)

        pre_tx_ids = set(pre.get("matched_transaction_ids", []))
        shadow_tx_ids = set(shadow.get("matched_transaction_ids", []))
        prod_tx_ids = set(prod.get("matched_transaction_ids", []))

        pre_evidence = pre.get("evidence_level")
        shadow_evidence = shadow.get("evidence_level")
        prod_evidence = prod.get("evidence_level")

        # Parity checks
        if shadow_usable != prod_usable:
            parity_counters["SHADOW_PRODUCTION_USABLE_MISMATCH"] += 1
        if shadow_median != prod_median:
            parity_counters["SHADOW_PRODUCTION_MEDIAN_MISMATCH"] += 1
        if shadow_tx_count != prod_tx_count:
            parity_counters["SHADOW_PRODUCTION_TX_COUNT_MISMATCH"] += 1
        if shadow_tx_ids != prod_tx_ids:
            parity_counters["SHADOW_PRODUCTION_TRANSACTION_SET_MISMATCH"] += 1
        if shadow_evidence != prod_evidence:
            parity_counters["SHADOW_PRODUCTION_EVIDENCE_LEVEL_MISMATCH"] += 1

        # Classification of why production lost usable evidence
        expected_loss = (pre_usable and not shadow_usable)
        shadow_predicted = (pre_usable and not shadow_usable)
        logic_diff = (shadow_usable != prod_usable)

        if pre_usable and not prod_usable:
            if shadow_usable != prod_usable:
                loss_reason = "SHADOW_PRODUCTION_LOGIC_DIFFERENCE"
            elif not shadow_usable:
                loss_reason = "EXPECTED_SALES_ONLY_LOSS"
            else:
                loss_reason = "OTHER"
        elif not pre_usable and not prod_usable:
            loss_reason = "ALREADY_INSUFFICIENT"
        else:
            loss_reason = "N/A"

        # Classification of median changes
        median_changed = (pre_median != prod_median) and (pre_median is not None or prod_median is not None)
        if median_changed:
            # Determine cause
            pre_vs_shadow = (pre_median != shadow_median) and (pre_median is not None or shadow_median is not None)
            shadow_vs_prod = (shadow_median != prod_median) and (shadow_median is not None or prod_median is not None)

            if pre_vs_shadow and not shadow_vs_prod:
                median_reason = "SALE_FILTER_CHANGE"
            elif not pre_vs_shadow and shadow_vs_prod:
                median_reason = "DEDUPLICATION_CHANGE"
            elif pre_vs_shadow and shadow_vs_prod:
                median_reason = "BOTH_SALE_AND_DEDUP"
            else:
                median_reason = "OTHER"
        else:
            median_reason = "UNCHANGED"

        # Decision change classification
        # Standardized: usable_for_investment changed
        decision_changed_standard = (pre_usable != prod_usable)
        # Phase 6 definition: same as above but shadow vs pre
        phase6_decision_changed = (pre_usable != shadow_usable)

        all_rows.append({
            "property_id": prop_id,
            "property_name": property_name,
            "pre_usable": pre_usable,
            "shadow_usable": shadow_usable,
            "prod_usable": prod_usable,
            "pre_median": pre_median,
            "shadow_median": shadow_median,
            "prod_median": prod_median,
            "pre_tx_count": pre_tx_count,
            "shadow_tx_count": shadow_tx_count,
            "prod_tx_count": prod_tx_count,
            "pre_tx_ids": ",".join(sorted(pre_tx_ids))[:500],
            "shadow_tx_ids": ",".join(sorted(shadow_tx_ids))[:500],
            "prod_tx_ids": ",".join(sorted(prod_tx_ids))[:500],
            "pre_evidence": pre_evidence,
            "shadow_evidence": shadow_evidence,
            "prod_evidence": prod_evidence,
            "pre_decision": pre_usable,
            "shadow_decision": shadow_usable,
            "prod_decision": prod_usable,
            "decision_changed_standard": decision_changed_standard,
            "phase6_decision_changed": phase6_decision_changed,
            "loss_reason": loss_reason,
            "median_changed": median_changed,
            "median_reason": median_reason,
        })

    df = pd.DataFrame(all_rows)

    # Summaries
    total = len(df)
    pre_usable_count = df["pre_usable"].sum()
    shadow_usable_count = df["shadow_usable"].sum()
    prod_usable_count = df["prod_usable"].sum()

    phase6_decision_changes = df["phase6_decision_changed"].sum()
    standard_decision_changes = df["decision_changed_standard"].sum()
    phase6_median_changes = df[df["pre_median"] != df["shadow_median"]].shape[0]
    standard_median_changes = df[df["pre_median"] != df["prod_median"]].shape[0]

    # Loss classification
    loss_counts = Counter(df[df["loss_reason"] != "N/A"]["loss_reason"])

    # Median change classification
    median_counts = Counter(df[df["median_changed"] == True]["median_reason"])

    # Known property verification
    known_ids = [3201, 3693, 3983, 4434, 5319, 6956, 701, 7061, 7546, 8057, 8201]
    known_df = df[df["property_id"].isin(known_ids)]

    # Export
    df.to_excel(os.path.join(OUTPUT_DIR, "MIGRATION_PARITY_FULL.xlsx"), index=False)
    known_df.to_excel(os.path.join(OUTPUT_DIR, "MIGRATION_PARITY_KNOWN.xlsx"), index=False)

    report_lines = [
        "# MIGRATION PARITY RECONCILIATION REPORT",
        f"**Generated:** {datetime.now().isoformat()}",
        "",
        "## SUMMARY",
        f"- Total properties: {total}",
        f"- Pre-migration usable: {pre_usable_count}",
        f"- Phase 6 shadow usable: {shadow_usable_count}",
        f"- Post-migration production usable: {prod_usable_count}",
        "",
        "## DECISION CHANGES (usable_for_investment)",
        f"- Phase 6 definition (pre vs shadow): {phase6_decision_changes}",
        f"- Standard definition (pre vs production): {standard_decision_changes}",
        "",
        "## MEDIAN CHANGES",
        f"- Phase 6 (pre vs shadow): {phase6_median_changes}",
        f"- Standard (pre vs production): {standard_median_changes}",
        "",
        "## PARITY COUNTERS (shadow vs production)",
        f"- SHADOW_PRODUCTION_USABLE_MISMATCH: {parity_counters['SHADOW_PRODUCTION_USABLE_MISMATCH']}",
        f"- SHADOW_PRODUCTION_MEDIAN_MISMATCH: {parity_counters['SHADOW_PRODUCTION_MEDIAN_MISMATCH']}",
        f"- SHADOW_PRODUCTION_TX_COUNT_MISMATCH: {parity_counters['SHADOW_PRODUCTION_TX_COUNT_MISMATCH']}",
        f"- SHADOW_PRODUCTION_TRANSACTION_SET_MISMATCH: {parity_counters['SHADOW_PRODUCTION_TRANSACTION_SET_MISMATCH']}",
        f"- SHADOW_PRODUCTION_EVIDENCE_LEVEL_MISMATCH: {parity_counters['SHADOW_PRODUCTION_EVIDENCE_LEVEL_MISMATCH']}",
        "",
        "## LOSS CLASSIFICATION (properties losing usable evidence)",
    ]
    for reason, count in loss_counts.most_common():
        report_lines.append(f"- {reason}: {count}")

    report_lines.extend([
        "",
        "## MEDIAN CHANGE CLASSIFICATION",
    ])
    for reason, count in median_counts.most_common():
        report_lines.append(f"- {reason}: {count}")

    report_lines.extend([
        "",
        "## KNOWN PROPERTIES (shadow vs production parity)",
        "| PID | Name | Pre Usable | Shadow Usable | Prod Usable | Pre Median | Shadow Median | Prod Median | Pre Tx | Shadow Tx | Prod Tx | Usable Match | Median Match | Tx Match |",
        "|-----|------|------------|---------------|-------------|------------|---------------|-------------|--------|-----------|---------|--------------|--------------|----------|",
    ])
    for _, r in known_df.iterrows():
        usable_match = "YES" if r["shadow_usable"] == r["prod_usable"] else "NO"
        median_match = "YES" if r["shadow_median"] == r["prod_median"] else "NO"
        tx_match = "YES" if r["shadow_tx_count"] == r["prod_tx_count"] else "NO"
        report_lines.append(
            f"| {r['property_id']} | {r['property_name']} | {r['pre_usable']} | {r['shadow_usable']} | {r['prod_usable']} | "
            f"{r['pre_median']} | {r['shadow_median']} | {r['prod_median']} | "
            f"{r['pre_tx_count']} | {r['shadow_tx_count']} | {r['prod_tx_count']} | "
            f"{usable_match} | {median_match} | {tx_match} |"
        )

    report_lines.extend([
        "",
        "## DECISION-CHANGE DEFINITIONS",
        "- Phase 6: compared live.usable_for_investment vs shadow.usable_for_investment (both current engine at time)",
        "- Post-migration audit: compared master.dld_evidence_status == 'DLD_MATCH' vs new_usable",
        "- Standardized: old_compute (no sales filter).usable_for_investment vs production.usable_for_investment",
        "",
        "## VERDICT",
    ])

    all_parity_zero = all(v == 0 for v in parity_counters.values())
    if all_parity_zero:
        report_lines.append("**MIGRATION_VERIFIED_AND_FREEZE**")
        report_lines.append("Shadow and production implementations are identical.")
    else:
        report_lines.append("**MIGRATION_REQUIRES_FIX**")
        report_lines.append("Shadow and production implementations differ. See parity counters above.")

    report = "\n".join(report_lines)
    with open(os.path.join(OUTPUT_DIR, "MIGRATION_PARITY_REPORT.md"), "w") as f:
        f.write(report)

    print("\n" + "=" * 70)
    print("PARITY RECONCILIATION COMPLETE")
    print("=" * 70)
    print(f"\nParity counters: {parity_counters}")
    print(f"Decision changes — Phase 6: {phase6_decision_changes}, Standard: {standard_decision_changes}")
    print(f"Median changes — Phase 6: {phase6_median_changes}, Standard: {standard_median_changes}")
    print(f"Loss classification: {dict(loss_counts)}")
    print(f"Median reason: {dict(median_counts)}")
    print(f"\nVerdict: {'MIGRATION_VERIFIED_AND_FREEZE' if all_parity_zero else 'MIGRATION_REQUIRES_FIX'}")

    return {
        "parity_counters": parity_counters,
        "phase6_decision_changes": phase6_decision_changes,
        "standard_decision_changes": standard_decision_changes,
        "phase6_median_changes": phase6_median_changes,
        "standard_median_changes": standard_median_changes,
        "loss_counts": dict(loss_counts),
        "median_counts": dict(median_counts),
        "all_parity_zero": all_parity_zero,
    }


if __name__ == "__main__":
    run_parity_reconciliation()
