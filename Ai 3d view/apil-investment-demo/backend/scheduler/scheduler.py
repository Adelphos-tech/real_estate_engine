"""
APIL Intelligence Scheduler
Runs all engines on a schedule:
  - Daily: ETL + Community + Project + Ready + Off-plan + Recommendations
  - Weekly: Developer Engine
  - Monthly: Full rebuild
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import API_HOST, API_PORT


def run_step(name: str, module_path: str):
    print(f"\n{'='*60}")
    print(f"  [{datetime.now().strftime('%H:%M:%S')}] {name}")
    print(f"{'='*60}")
    try:
        subprocess.run(
            [sys.executable, module_path],
            cwd=str(Path(__file__).resolve().parent.parent),
            check=True,
        )
        print(f"  ✅ {name} completed")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ {name} failed: {e}")


def daily_jobs():
    """Run daily: ETL imports + Community + Project + Ready + Off-plan + Recommendations."""
    print(f"\n{'#'*60}")
    print(f"# DAILY JOBS — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'#'*60}")

    base = Path(__file__).resolve().parent.parent

    # ETL
    run_step("ETL: Import DLD", str(base / "etl" / "import_dld.py"))
    run_step("ETL: Import DXBInteract", str(base / "etl" / "import_dxb.py"))
    run_step("ETL: Import Google", str(base / "etl" / "import_google.py"))

    # Engines
    run_step("Community Engine", str(base / "engines" / "community_engine.py"))
    run_step("Project Engine", str(base / "engines" / "project_engine.py"))
    run_step("Ready Property Engine", str(base / "engines" / "ready_engine.py"))
    run_step("Off-plan Engine", str(base / "engines" / "offplan_engine.py"))
    run_step("Recommendation Engine", str(base / "engines" / "recommendation_engine.py"))

    print(f"\n{'#'*60}")
    print(f"# DAILY JOBS COMPLETE — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'#'*60}")


def weekly_jobs():
    """Run weekly: Developer Engine (needs DXBInteract + Google scraping)."""
    print(f"\n{'#'*60}")
    print(f"# WEEKLY JOBS — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'#'*60}")

    base = Path(__file__).resolve().parent.parent

    # Re-import DXB + Google (scraped on server)
    run_step("ETL: Import DXBInteract", str(base / "etl" / "import_dxb.py"))
    run_step("ETL: Import Google", str(base / "etl" / "import_google.py"))

    # Developer Engine
    run_step("Developer Engine", str(base / "engines" / "developer_engine.py"))

    # Re-run dependent engines
    run_step("Project Engine", str(base / "engines" / "project_engine.py"))
    run_step("Ready Property Engine", str(base / "engines" / "ready_engine.py"))
    run_step("Off-plan Engine", str(base / "engines" / "offplan_engine.py"))
    run_step("Recommendation Engine", str(base / "engines" / "recommendation_engine.py"))

    print(f"\n{'#'*60}")
    print(f"# WEEKLY JOBS COMPLETE — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'#'*60}")


def monthly_jobs():
    """Run monthly: Full rebuild from scratch."""
    print(f"\n{'#'*60}")
    print(f"# MONTHLY JOBS (FULL REBUILD) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'#'*60}")
    daily_jobs()
    weekly_jobs()
    print(f"\n{'#'*60}")
    print(f"# MONTHLY JOBS COMPLETE")
    print(f"{'#'*60}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="APIL Intelligence Scheduler")
    parser.add_argument("--mode", choices=["daily", "weekly", "monthly"], default="daily")
    args = parser.parse_args()

    if args.mode == "daily":
        daily_jobs()
    elif args.mode == "weekly":
        weekly_jobs()
    elif args.mode == "monthly":
        monthly_jobs()
