"""
APIL Intelligence Platform — Full Pipeline Runner
Executes all engines in dependency order and starts the API server.

Usage:
  python run_pipeline.py              # Run all engines + start API
  python run_pipeline.py --engines    # Run all engines only (no API)
  python run_pipeline.py --api        # Start API only (engines must have been run)
"""
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import API_HOST, API_PORT


def run_engine(name: str, script: str):
    base = Path(__file__).resolve().parent
    print(f"\n{'─'*50}")
    print(f"  [{datetime.now().strftime('%H:%M:%S')}] Running: {name}")
    print(f"{'─'*50}")
    try:
        result = subprocess.run(
            [sys.executable, script],
            cwd=str(base),
            check=True,
        )
        print(f"  ✅ {name} — OK")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ {name} — FAILED (exit {e.returncode})")
        return False
    except FileNotFoundError:
        print(f"  ⚠️  {name} — SKIPPED (file not found)")
        return False


def run_all_engines():
    base = Path(__file__).resolve().parent
    print(f"\n{'═'*60}")
    print(f"  APIL INTELLIGENCE PLATFORM — FULL PIPELINE")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'═'*60}")

    steps = [
        # ETL
        ("ETL: Import DLD", "etl/import_dld.py"),
        ("ETL: Import DXBInteract", "etl/import_dxb.py"),
        ("ETL: Import Google Reviews", "etl/import_google.py"),
        # Validation (before scoring)
        ("Data Validation Engine", "engines/validation_engine.py"),
        # Feature Engineering (normalize + clean)
        ("Feature Engineering Engine", "engines/feature_engine.py"),
        # Scoring Engines (in dependency order)
        ("Community Engine", "engines/community_engine.py"),
        ("Developer Engine", "engines/developer_engine.py"),
        ("Project Engine", "engines/project_engine.py"),
        ("Ready Property Engine", "engines/ready_engine.py"),
        ("Off-plan Engine", "engines/offplan_engine.py"),
        ("Recommendation Engine", "engines/recommendation_engine.py"),
    ]

    results = {}
    for name, script in steps:
        script_path = str(base / script)
        ok = run_engine(name, script_path)
        results[name] = ok

    # Summary
    print(f"\n{'═'*60}")
    print(f"  PIPELINE SUMMARY")
    print(f"{'═'*60}")
    for name, ok in results.items():
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")

    succeeded = sum(1 for ok in results.values() if ok)
    total = len(results)
    print(f"\n  {succeeded}/{total} engines completed successfully")
    print(f"  Completed at {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'═'*60}\n")

    return results


def start_api():
    print(f"\n  Starting API server on {API_HOST}:{API_PORT}...")
    base = Path(__file__).resolve().parent
    subprocess.run(
        [sys.executable, str(base / "api" / "main.py")],
        cwd=str(base),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="APIL Intelligence Platform Runner")
    parser.add_argument("--engines", action="store_true", help="Run all engines only (no API)")
    parser.add_argument("--api", action="store_true", help="Start API server only")
    args = parser.parse_args()

    if args.api:
        start_api()
    elif args.engines:
        run_all_engines()
    else:
        run_all_engines()
        start_api()
