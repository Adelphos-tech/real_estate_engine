"""
investor_api/rental_costs/cost_data_store.py

Read-only loader for DLD service charges CSV.
NOT imported by normal request paths. Called only from audit scripts.
"""
import pandas as pd
from pathlib import Path
from functools import lru_cache

_SERVICE_CHARGES_PATH = Path("/Users/apple/Desktop/Ai 3d view/dld_service_charges.csv")


@lru_cache(maxsize=1)
def load_service_charges() -> pd.DataFrame:
    """Load DLD service charges. Returns DataFrame with all columns."""
    if not _SERVICE_CHARGES_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(_SERVICE_CHARGES_PATH, low_memory=False)
    return df


@lru_cache(maxsize=1)
def load_residential_service_charges_latest() -> pd.DataFrame:
    """Get latest residential service charge per project (by budget_year)."""
    df = load_service_charges()
    if df.empty:
        return df
    residential = df[df["usage"] == "Residential"].copy()
    residential["budget_year"] = pd.to_numeric(residential["budget_year"], errors="coerce")
    residential["grand_total_aed_sqft"] = pd.to_numeric(
        residential["grand_total_aed_sqft"], errors="coerce"
    )
    # Get latest year per project_name
    idx = residential.groupby("project_name")["budget_year"].idxmax()
    return residential.loc[idx].reset_index(drop=True)
