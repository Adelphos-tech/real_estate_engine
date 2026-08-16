"""
APIL Investment Intelligence Platform — Configuration
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "src" / "data"
BACKEND_DATA_DIR = BASE_DIR / "backend" / "data"

DLD_TRANSACTIONS_CSV = Path(os.environ.get(
    "DLD_TRANSACTIONS_CSV",
    str(Path.home() / "Desktop" / "Ai 3d view" / "dxb_transactions.csv")
))
DLD_RENTS_CSV = Path(os.environ.get(
    "DLD_RENTS_CSV",
    str(Path.home() / "Desktop" / "Ai 3d view" / "dxb_rents.csv")
))
PROJECTS_JSON = DATA_DIR / "dxb_projects.json"
DEVELOPERS_JSON = DATA_DIR / "developers.json"

DXB_BASE = "https://dxbinteract.com"
LLM_SERVER = "http://87.200.15.174:8001/v1/chat/completions"
LLM_MODEL = "Qwen2.5-VL-7B-Instruct"

OUTPUT_DIR = BACKEND_DATA_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COMMUNITY_SCORES_FILE = OUTPUT_DIR / "community_scores.json"
DEVELOPER_SCORES_FILE = OUTPUT_DIR / "developer_scores.json"
PROJECT_SCORES_FILE = OUTPUT_DIR / "project_scores.json"
READY_PROPERTY_SCORES_FILE = OUTPUT_DIR / "ready_property_scores.json"
OFFPLAN_SCORES_FILE = OUTPUT_DIR / "offplan_scores.json"
RECOMMENDATIONS_FILE = OUTPUT_DIR / "recommendations.json"

API_HOST = os.environ.get("APIL_API_HOST", "0.0.0.0")
API_PORT = int(os.environ.get("APIL_API_PORT", "8000"))
