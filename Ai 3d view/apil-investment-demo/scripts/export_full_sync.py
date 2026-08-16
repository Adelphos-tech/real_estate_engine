#!/usr/bin/env python3
"""
Full data export: Fetch all 4,283 real property listings from admin API,
match each to DLD transaction + rent data directly, and output
dxb_projects.json with REAL asking prices, REAL rents, REAL yields.

This bypasses the sync script's conservative fuzzy matching and does
direct project+bedroom segment matching against the raw DLD CSVs.
"""

import pandas as pd
import json
import sys
import re
import os
from collections import defaultdict

# ─── Paths (on server) ───
TRANSACTIONS_FILE = "/home/amlak/Voicexa/live_apis/investment_api/data/transactions/transactions-2025-real.csv"
TRANSACTIONS_2026_FILE = "/home/amlak/Voicexa/live_apis/investment_api/data/transactions/transactions-2026-02-16.csv"
RENTS_FILE = "/home/amlak/Voicexa/live_apis/investment_api/data/rents/rents.csv"

# ─── Helpers ───
def clean_text(text):
    if not text or str(text).strip().lower() in ('nan', 'none', ''):
        return ''
    s = str(text).strip().upper()
    s = re.sub(r'[^A-Z0-9 ]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def normalize_bedroom(val):
    if not val or str(val).strip().lower() in ('nan', 'none', ''):
        return None
    s = str(val).strip().lower()
    if 'studio' in s:
        return 'Studio'
    m = re.search(r'(\d+)', s)
    if m:
        return f"{m.group(1)} B/R"
    return None

def infer_bedroom_from_size(size_sqft):
    if size_sqft <= 0:
        return None
    if size_sqft < 500:
        return 'Studio'
    if size_sqft < 700:
        return '1 B/R'
    if size_sqft < 1100:
        return '1 B/R'
    if size_sqft < 1500:
        return '2 B/R'
    if size_sqft < 2000:
        return '3 B/R'
    return '4 B/R'

def fuzzy_match(query, choices, threshold=80):
    """Simple fuzzy match using difflib."""
    from difflib import get_close_matches
    if not query or not choices:
        return None, 0
    matches = get_close_matches(query, list(choices), n=1, cutoff=threshold/100)
    if matches:
        return matches[0], 100  # difflib ratio would need SequenceMatcher
    return None, 0

# ─── Load DLD Transaction Data ───
print("Loading DLD transactions...", file=sys.stderr)
df_2025 = pd.read_csv(TRANSACTIONS_FILE, low_memory=False)
df_2026 = pd.read_csv(TRANSACTIONS_2026_FILE, low_memory=False) if os.path.exists(TRANSACTIONS_2026_FILE) else pd.DataFrame()

df_txn = pd.concat([df_2025, df_2026], ignore_index=True)
df_txn = df_txn[df_txn['GROUP_EN'] == 'Sales'].copy()
df_txn['price'] = pd.to_numeric(df_txn['TRANS_VALUE'], errors='coerce')
df_txn = df_txn[df_txn['price'] > 10000].copy()
df_txn['area_sqm'] = pd.to_numeric(df_txn['ACTUAL_AREA'], errors='coerce')
df_txn['area_sqft'] = df_txn['area_sqm'] * 10.7639
df_txn = df_txn[df_txn['area_sqft'] > 1].copy()
df_txn['pps'] = df_txn['price'] / df_txn['area_sqft']
df_txn = df_txn[(df_txn['pps'] >= 100) & (df_txn['pps'] <= 20000)].copy()
df_txn['project_clean'] = df_txn['PROJECT_EN'].apply(clean_text)
df_txn['bedroom'] = df_txn['ROOMS_EN'].apply(normalize_bedroom)
df_txn['segment_key'] = df_txn['project_clean'] + '|' + df_txn['bedroom'].fillna('')
df_txn['month'] = pd.to_datetime(df_txn['INSTANCE_DATE'], errors='coerce').dt.to_period('M').astype(str)
df_txn['year'] = pd.to_datetime(df_txn['INSTANCE_DATE'], errors='coerce').dt.year

print(f"  Loaded {len(df_txn):,} sales transactions", file=sys.stderr)
print(f"  Unique projects: {df_txn['project_clean'].nunique()}", file=sys.stderr)
print(f"  Unique areas: {df_txn['AREA_EN'].nunique()}", file=sys.stderr)

# Build transaction lookups by segment (project|bedroom)
txn_by_segment = defaultdict(list)
for _, row in df_txn.iterrows():
    seg = row['segment_key']
    if not seg or seg == '|':
        continue
    txn_by_segment[seg].append({
        'date': str(row['INSTANCE_DATE']),
        'price': float(row['price']),
        'price_sqft': float(row['pps']),
        'beds': row['bedroom'] or 'Unknown',
        'area_sqft': float(row['area_sqft']),
    })

# Also build by project (all bedrooms)
txn_by_project = defaultdict(list)
for _, row in df_txn.iterrows():
    proj = row['project_clean']
    if not proj:
        continue
    txn_by_project[proj].append({
        'date': str(row['INSTANCE_DATE']),
        'price': float(row['price']),
        'price_sqft': float(row['pps']),
        'beds': row['bedroom'] or 'Unknown',
        'area_sqft': float(row['area_sqft']),
    })

# ─── Load DLD Rent Data ───
print("Loading DLD rents...", file=sys.stderr)
df_rent = pd.read_csv(RENTS_FILE, low_memory=False)
df_rent = df_rent[
    (df_rent['PROJECT_EN'].notna()) &
    (pd.to_numeric(df_rent['ANNUAL_AMOUNT'], errors='coerce') > 0) &
    (pd.to_numeric(df_rent['ACTUAL_AREA'], errors='coerce') > 1) &
    (df_rent['PROP_SUB_TYPE_EN'].isin(['Flat', 'Studio', 'Villa']))
].copy()
df_rent['annual_rent'] = pd.to_numeric(df_rent['ANNUAL_AMOUNT'], errors='coerce')
df_rent['area_sqft'] = pd.to_numeric(df_rent['ACTUAL_AREA'], errors='coerce')
df_rent['rent_per_sqft'] = df_rent['annual_rent'] / df_rent['area_sqft']
df_rent = df_rent[(df_rent['rent_per_sqft'] >= 10) & (df_rent['rent_per_sqft'] <= 1000)].copy()
df_rent['project_clean'] = df_rent['PROJECT_EN'].apply(clean_text)
df_rent['bedroom'] = df_rent['ROOMS'].apply(normalize_bedroom)
mask = df_rent['bedroom'].isna()
df_rent.loc[mask, 'bedroom'] = df_rent.loc[mask, 'area_sqft'].apply(infer_bedroom_from_size)
df_rent['segment_key'] = df_rent['project_clean'] + '|' + df_rent['bedroom'].fillna('')

print(f"  Loaded {len(df_rent):,} rent records", file=sys.stderr)
print(f"  Unique rent projects: {df_rent['project_clean'].nunique()}", file=sys.stderr)

# Build rent lookups by segment
rent_by_segment = defaultdict(list)
for _, row in df_rent.iterrows():
    seg = row['segment_key']
    if not seg or seg == '|':
        continue
    rent_by_segment[seg].append({
        'date': str(row.get('REGISTRATION_DATE', '2026-01-01')),
        'annual_rent': float(row['annual_rent']),
        'beds': row['bedroom'] or 'Unknown',
        'area_sqft': float(row['area_sqft']),
    })

# Also by project (all bedrooms)
rent_by_project = defaultdict(list)
for _, row in df_rent.iterrows():
    proj = row['project_clean']
    if not proj:
        continue
    rent_by_project[proj].append({
        'date': str(row.get('REGISTRATION_DATE', '2026-01-01')),
        'annual_rent': float(row['annual_rent']),
        'beds': row['bedroom'] or 'Unknown',
        'area_sqft': float(row['area_sqft']),
    })

# ─── Fetch Properties from Admin API ───
print("Fetching properties from admin API...", file=sys.stderr)
import requests
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=10, pool_maxsize=10,
    max_retries=requests.adapters.Retry(total=5, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
)
session.mount('https://', adapter)
session.headers.update({'User-Agent': 'Mozilla/5.0'})

all_properties = []
page = 1
while True:
    resp = session.get('https://admin.apilproperties.com/api/properties', params={'page': page}, timeout=(10, 30))
    if resp.status_code == 404:
        break
    resp.raise_for_status()
    data = resp.json()
    props = data.get('data', []) or data.get('properties', []) or data.get('results', [])
    if not props:
        break
    all_properties.extend(props)
    print(f"  Page {page}: {len(props)} properties (total: {len(all_properties)})", file=sys.stderr)
    page += 1
    if page > 500:
        break
    import time; time.sleep(0.2)

session.close()
print(f"  Total fetched: {len(all_properties)} properties", file=sys.stderr)

# ─── Match Properties to DLD Data ───
print("Matching properties to DLD data...", file=sys.stderr)

# Build set of all DLD project names for fuzzy matching
txn_projects = set(txn_by_project.keys())
rent_projects = set(rent_by_project.keys())

projects_output = defaultdict(lambda: {
    "name": None,
    "area": None,
    "slug": None,
    "url": None,
    "scraped_at": None,
    "avg_price": None,
    "avg_price_sqft": None,
    "price_change_pct": None,
    "avg_rent": None,
    "rent_change_pct": None,
    "rental_yield_pct": None,
    "sales_volume": None,
    "service_charge": None,
    "sales_history": [],
    "rent_history": [],
    "listings": [],
})

matched_count = 0
rent_matched = 0

for prop in all_properties:
    prop_name = str(prop.get('name', '') or prop.get('title', ''))
    project_name = str(prop.get('project_name', '') or '').strip()
    if not project_name or project_name.lower() == 'nan':
        project_name = prop_name.split('|')[0].strip() if '|' in prop_name else prop_name
    
    community = str(prop.get('community_area', '') or prop.get('community', '') or 'Unknown').strip()
    if not community or community.lower() == 'nan':
        community = 'Unknown'
    
    listing_price = float(prop.get('price', 0) or 0)
    size_sqft = float(prop.get('size_sq_ft', 0) or prop.get('size_sqft', 0) or 0)
    bedrooms = normalize_bedroom(prop.get('bedrooms') or prop.get('bedroom'))
    if not bedrooms:
        bedrooms = infer_bedroom_from_size(size_sqft) or 'Unknown'
    
    project_clean = clean_text(project_name)
    
    # Try exact segment match first
    seg_key = f"{project_clean}|{bedrooms}"
    matched_txn = txn_by_segment.get(seg_key, [])
    matched_rent = rent_by_segment.get(seg_key, [])
    
    # If no segment match, try project-level match (all bedrooms)
    if not matched_txn and project_clean in txn_projects:
        matched_txn = txn_by_project[project_clean]
    if not matched_rent and project_clean in rent_projects:
        matched_rent = rent_by_project[project_clean]
    
    # If still no match, try fuzzy on project name
    if not matched_txn and project_clean:
        from difflib import get_close_matches
        matches = get_close_matches(project_clean, list(txn_projects), n=1, cutoff=0.6)
        if matches:
            matched_txn = txn_by_project[matches[0]]
    if not matched_rent and project_clean:
        from difflib import get_close_matches
        matches = get_close_matches(project_clean, list(rent_projects), n=1, cutoff=0.6)
        if matches:
            matched_rent = rent_by_project[matches[0]]
    
    if matched_txn or matched_rent:
        matched_count += 1
    if matched_rent:
        rent_matched += 1
    
    # Get or create project entry
    proj = projects_output[project_name]
    proj["name"] = project_name
    proj["area"] = community
    proj["slug"] = project_name.lower().replace(' ', '-').replace('/', '-')
    proj["url"] = f"https://dxbinteract.com/projects/{proj['slug']}"
    
    # Add sales history
    for t in matched_txn:
        proj["sales_history"].append(t)
    
    # Add rent history
    for r in matched_rent:
        proj["rent_history"].append(r)
    
    # Store real property listing
    proj["listings"].append({
        "id": str(prop.get('id', '')),
        "title": prop_name,
        "price": listing_price,
        "size_sqft": size_sqft,
        "bedrooms": bedrooms,
        "community": community,
        "images": prop.get('images', []),
        "status": str(prop.get('status', '') or '').strip(),
        "bathrooms": prop.get('bathrooms', None),
        "category": str(prop.get('category', '') or '').strip(),
    })

print(f"  Matched: {matched_count}/{len(all_properties)} properties to DLD data", file=sys.stderr)
print(f"  Rent matched: {rent_matched}/{len(all_properties)}", file=sys.stderr)

# ─── Finalize: Calculate aggregates, remove internal fields ───
print("Finalizing output...", file=sys.stderr)
result = []
for name, proj in projects_output.items():
    if not proj["sales_history"] and not proj["rent_history"] and not proj["listings"]:
        continue
    
    # Calculate avg price from sales
    prices = [s["price"] for s in proj["sales_history"] if s["price"] and s["price"] > 0]
    prices_sqft = [s["price_sqft"] for s in proj["sales_history"] if s["price_sqft"] and s["price_sqft"] > 0]
    
    if prices:
        proj["avg_price"] = round(sum(prices) / len(prices))
    elif proj["listings"]:
        lp = [p["price"] for p in proj["listings"] if p["price"] > 0]
        if lp:
            proj["avg_price"] = round(sum(lp) / len(lp))
    
    if prices_sqft:
        proj["avg_price_sqft"] = round(sum(prices_sqft) / len(prices_sqft))
    
    # Calculate avg rent
    rents = [r["annual_rent"] for r in proj["rent_history"] if r["annual_rent"] and r["annual_rent"] > 0]
    if rents:
        proj["avg_rent"] = round(sum(rents) / len(rents))
    
    # Calculate rental yield
    if proj["avg_rent"] and proj["avg_price"] and proj["avg_price"] > 0:
        proj["rental_yield_pct"] = round((proj["avg_rent"] / proj["avg_price"]) * 100, 2)
    
    # Sales volume
    proj["sales_volume"] = len(proj["sales_history"])
    
    # Price change: compare recent vs older
    if len(prices_sqft) >= 4:
        sorted_sales = sorted(proj["sales_history"], key=lambda x: x["date"])
        half = len(sorted_sales) // 2
        old_prices = [s["price_sqft"] for s in sorted_sales[:half] if s["price_sqft"] > 0]
        new_prices = [s["price_sqft"] for s in sorted_sales[half:] if s["price_sqft"] > 0]
        if old_prices and new_prices:
            old_med = sum(old_prices) / len(old_prices)
            new_med = sum(new_prices) / len(new_prices)
            if old_med > 0:
                proj["price_change_pct"] = round(((new_med - old_med) / old_med) * 100, 2)
    
    result.append(proj)

print(f"Output: {len(result)} projects", file=sys.stderr)
print(json.dumps(result, indent=2, ensure_ascii=False))
