#!/usr/bin/env python3
"""
Build real developer scores from 3 sources:
1. Existing DLD transaction + project data (projects delivered, resale premium, rental demand, sales volume)
2. DXBInteract developer page scraping (absorption rate, capital gain, sales volume cross-check)
3. Server LLM (Qwen2.5-VL via vLLM) for qualitative metrics (construction quality, customer reviews, market reputation)

Output: src/data/developers.json with all real computed values.
"""

import json
import re
import csv
import os
import sys
import time
import urllib.request
import urllib.parse
from collections import defaultdict

# ─── Paths ───
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_FILE = os.path.join(BASE_DIR, 'src', 'data', 'dxb_projects.json')
TRANSACTIONS_FILE = '/Users/apple/Desktop/Ai 3d view/dxb_transactions.csv'
OUTPUT_FILE = os.path.join(BASE_DIR, 'src', 'data', 'developers.json')

# ─── Developer keyword mapping (from project name → developer) ───
DEVELOPER_KEYWORDS = {
    'Emaar Properties': ['EMAAR', 'BURJ KHALIFA', 'DOWNTOWN VIEWS', 'DUBAI HILLS', 'CREEK HARBOUR', 'CREEK GATE', 'MUDON', 'ARABIAN RANCHES', 'THE VALLEY', 'GRAND BLEU', 'THE LAKES', 'EMERALD HILLS', 'SPRING', 'MEADOWS', 'ADDRESS SKY VIEW', 'THE ADDRESS', 'VIDA', 'DUBAI CREEK'],
    'Damac Properties': ['DAMAC', 'AKOYA', 'PARAMOUNT', 'CASA', 'GHALIA', 'AVENUE', 'CHERIE', 'SERA', 'VERONA', 'MALIBU', 'PLAYBOY', 'SIX SENSES'],
    'Binghatti': ['BINGHATTI', 'ONE BINGHATTI', 'BINGHATTI SKYRISE', 'BINGHATTI AQUARISE', 'BINGHATTI SKYHALL', 'BINGHATTI CREEK', 'BINGHATTI GATE', 'BINGHATTI MOONLIGHT', 'BINGHATTI STARLIGHT', 'BINGHATTI DOWNTOWN'],
    'Danube Properties': ['DANUBE', 'BAYZ', 'DANUBE GEMZ', 'DANUBE ELAN', 'DANUBE OPAL', 'DANUBE PEARLZ', 'DANUBE SPORT CITY'],
    'Nakheel': ['NAKHEEL', 'PALM JUMEIRAH', 'PALM DEIRA', 'THE WORLD', 'WORLD ISLANDS', 'DEIRA ISLAND', 'JEBEL ALI', 'AL KHAN', 'IBN BATTUTA', 'DRAGON MART', 'THE PALM'],
    'Meraas': ['MERAAS', 'CITY WALK', 'BLUEWATERS', 'LA MER', 'PEARL JUMEIRAH', 'AL WATAN', 'BULGARI', 'CENTRAL KITCHEN', 'SUR LA MER', 'MADINAT JUMEIRAH LIVING', 'JUMEIRAH BAY'],
    'Dubai Properties (Dubai Holding)': ['DUBAI PROPERTIES', 'MADINAT JUMEIRAH', 'JUMEIRAH BEACH', '1 JBR', 'VILLA', 'SHAMSI', 'WARSAN', 'CULTURE VILLAGE', 'DUBAI WHARF', 'MANAMA'],
    'Sobha Realty': ['SOBHA', 'HARTLAND', 'SOBHA ONE', 'SOBHA HARTLAND', 'MEYDAN', 'SOBHA ORBIS', 'SOBHA NEBULA'],
    'MAG Group': ['MAG ', 'MAGKAFALA', 'MAG 318', 'MAG 214', 'MAG 5', 'MAG EYE', 'MAG PARK', 'MAG WORLD', 'MAG CITY'],
    'Aldar Properties': ['ALDAR', 'YAS ISLAND', 'AL GHARB', 'AL MUNEERA', 'AL Raha'],
    'Azizi Developments': ['AZIZI', 'AZIZI MIRAGE', 'AZIZI RIVIERA', 'AZIZI VENICE', 'AZIZI ALYA', 'AZIZI SAMANA', 'AZIZI RIVERA', 'AZIZI PARIS', 'AZIZI MINC'],
    'Ellington Properties': ['ELLINGTON', 'BELLAGIO', 'WILTON', 'CARLTON', 'PARK HOUSE', 'MEREDITH', 'TIARA', 'SPECTRUM', 'DELANO'],
    'Deyaar': ['DEYAAR', 'DEYAAR MIDORI', 'DEYAAR BLOOM', 'DEYAAR MONTROSE', 'DEYAAR TIVOLI', 'DEYAAR SIDRA'],
    'Select Group': ['SELECT', 'SIX SENSES', 'PALM VIEWS', 'PALM 360', 'SELECT ONE', 'SELECT ONE PALM'],
    'Dubai South': ['DUBAI SOUTH', 'DUBAI SOUTH RESIDENCE', 'MAG 5 DUBAI SOUTH'],
    'Emaar Malls': ['EMAAR MALL', 'DUBAI MALL', 'SPRING SOUK'],
    'Meraas Holding': ['MERAAS HOLDING', 'JUMEIRAH BAY ISLAND'],
    'Property Finder': ['PROPERTY FINDER'],
    'Aqarat Dubai': ['AQARAT'],
    'Premium Partners': ['PREMIUM'],
    'Presight': ['PRESIGHT'],
    'FAM Properties': ['FAM '],
    'Sobha Hartland': ['SOBHA HARTLAND'],
    'Imtiaz': ['IMTIAZ'],
    'GJ Properties': ['GJ '],
    'RPG': ['RPG '],
    'Ora Developers': ['ORA ', 'NEOM'],
    'Reportage': ['REPORTAGE'],
    'Aqar': ['AQAR '],
    'Palma': ['PALMA '],
    'Tanami': ['TANAMI'],
    'Shamal': ['SHAMAL'],
    'Al Futtaim': ['AL FUTTAIM', 'FESTIVAL CITY', 'FESTIVAL PLAZA', 'FESTIVAL WATERFRONT'],
    'Union Properties': ['UNION PROPERTIES', 'UP TOWN', 'GREEN COMMUNITY', 'INDEX TOWER'],
    'Omnix': ['OMNIX'],
    'Schon': ['SCHON', 'SCHON BUSINESS', 'SCHON RESIDENCE'],
    'Diamond Developers': ['DIAMOND', 'SUSTAINABLE CITY'],
    'Tiger Properties': ['TIGER ', 'TIGER WOOD', 'TIGER TOWER', 'TIGER SKY', 'TIGER VENICE'],
    'Presight AI': ['PRESIGHT'],
    'Amlak': ['AMLAKE'],
    'Dubai Investments': ['DUBAI INVESTMENTS', 'DUBAI INVESTMENTS PARK', 'DIP'],
    'Rashid Al Rashed': ['RASHID'],
    'Khalifa Group': ['KHALIFA'],
    'Al Mazroui': ['MAZROUI'],
    'Yousuf Al Hashimi': ['HASHIMI'],
}

# ─── DXBInteract developer URLs ───
DXB_BASE = "https://dxbinteract.com/top-property-developers-in-dubai"
DEVELOPER_SLUGS = {
    'Emaar Properties': 'emaar-properties',
    'Damac Properties': 'damac-properties',
    'Binghatti': 'binghatti',
    'Danube Properties': 'danube-properties',
    'Nakheel': 'nakheel',
    'Meraas': 'meraas',
    'Dubai Properties (Dubai Holding)': 'dubai-properties',
    'Sobha Realty': 'sobha-realty',
    'MAG Group': 'mag-group',
    'Aldar Properties': 'aldar-properties',
    'Azizi Developments': 'azizi-developments',
    'Ellington Properties': 'ellington-properties',
    'Deyaar': 'deyaar',
    'Select Group': 'select-group',
    'Tiger Properties': 'tiger-properties',
    'Al Futtaim': 'al-futtaim',
    'Union Properties': 'union-properties',
    'Dubai Investments': 'dubai-investments-real-estate',
    'Dubai South': 'dubai-south',
    'Diamond Developers': 'diamond-developers',
}


def match_developer(project_name: str) -> str:
    """Match project name to developer using keyword matching."""
    clean = project_name.upper().strip()
    for dev, keywords in DEVELOPER_KEYWORDS.items():
        for kw in keywords:
            if kw in clean:
                return dev
    return 'Independent / Other'


def compute_metrics_from_local_data():
    """Compute real developer metrics from existing project + transaction data."""
    with open(PROJECTS_FILE) as f:
        projects = json.load(f)

    # Load transactions
    transactions = []
    if os.path.exists(TRANSACTIONS_FILE):
        with open(TRANSACTIONS_FILE) as f:
            reader = csv.DictReader(f)
            transactions = list(reader)

    # Group projects by developer
    dev_projects = defaultdict(list)
    for p in projects:
        dev = match_developer(p['name'])
        dev_projects[dev].append(p)

    # Group transactions by developer (via project name match)
    dev_txns = defaultdict(list)
    for t in transactions:
        pj = (t.get('PROJECT_EN') or '').strip()
        if pj:
            dev = match_developer(pj)
            dev_txns[dev].append(t)

    results = {}
    for dev, projs in dev_projects.items():
        if dev == 'Independent / Other':
            continue

        # Projects delivered (status Ready or has sales_history with old dates)
        ready_projects = [p for p in projs if (p.get('avg_price') or 0) > 0]
        total_projects = len(projs)

        # Sales volume from transactions
        txns = dev_txns.get(dev, [])
        sales_count = len(txns)
        sales_value = sum(float(t.get('TRANS_VALUE', 0)) for t in txns if t.get('TRANS_VALUE'))

        # Off-plan vs ready ratio from transactions
        offplan_count = sum(1 for t in txns if 'Off-Plan' in (t.get('IS_OFFPLAN_EN') or ''))
        ready_count = sum(1 for t in txns if 'Ready' in (t.get('IS_OFFPLAN_EN') or ''))

        # Average price change (capital gain) from project data
        price_changes = [p.get('price_change_pct') for p in projs if p.get('price_change_pct') is not None]
        avg_capital_gain = sum(price_changes) / len(price_changes) if price_changes else 0

        # Rental yield average
        yields = [p.get('rental_yield_pct') for p in projs if p.get('rental_yield_pct')]
        avg_yield = sum(yields) / len(yields) if yields else 0

        # Rental demand: total rent transactions
        rent_counts = [p.get('rent_count') or 0 for p in projs]
        total_rent_contracts = sum(rent_counts)

        # Sales count from project data
        sales_counts = [p.get('sales_count') or 0 for p in projs]
        total_sales_from_projects = sum(sales_counts)

        # Average price per sqft
        price_sqfts = [p.get('avg_price_sqft') for p in projs if p.get('avg_price_sqft')]
        avg_price_sqft = sum(price_sqfts) / len(price_sqfts) if price_sqfts else 0

        # Areas covered
        areas = list(set(p['area'] for p in projs if p.get('area')))

        results[dev] = {
            'name': dev,
            'totalProjects': total_projects,
            'readyProjects': len(ready_projects),
            'salesCount': sales_count,
            'salesValue': sales_value,
            'offplanCount': offplan_count,
            'readyTxnCount': ready_count,
            'avgCapitalGain': round(avg_capital_gain, 2),
            'avgRentalYield': round(avg_yield, 2),
            'totalRentContracts': total_rent_contracts,
            'totalSalesFromProjects': total_sales_from_projects,
            'avgPriceSqft': round(avg_price_sqft, 0),
            'areasCovered': areas,
            'projectNames': [p['name'] for p in projs],
        }

    return results


def scrape_dxbinteract_developer(dev_name: str, slug: str) -> dict:
    """Scrape DXBInteract developer page for real metrics."""
    url = f"{DXB_BASE}/{slug}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        metrics = {}

        # Try to extract sales volume
        m = re.search(r'Sales Volume[^0-9]*(\d+)', html)
        if m: metrics['dxbSalesVolume'] = int(m.group(1))

        # Try to extract sales value
        m = re.search(r'Sales Value[^0-9]*(\d[\d,]*)', html)
        if m: metrics['dxbSalesValue'] = int(m.group(1).replace(',', ''))

        # Try to extract projects count
        m = re.search(r'Projects[^0-9]*(\d+)', html)
        if m: metrics['dxbProjects'] = int(m.group(1))

        # Try to extract absorption rate
        m = re.search(r'Absorption Rate[^0-9]*([\d.]+)', html)
        if m: metrics['dxbAbsorptionRate'] = float(m.group(1))

        # Try to extract capital gain
        m = re.search(r'Capital Gain[^0-9]*([\d.]+)', html)
        if m: metrics['dxbCapitalGain'] = float(m.group(1))

        return metrics
    except Exception as e:
        print(f"  [WARN] Failed to scrape {slug}: {e}")
        return {}


def llm_qualitative_analysis(dev_name: str, metrics: dict) -> dict:
    """
    Use server LLM (Qwen2.5-VL via vLLM at 87.200.15.174:8001) for qualitative metrics.
    Sends the real data we have and asks LLM to assess:
    - Construction Quality (1-10)
    - Customer Reviews (1-10)
    - Market Reputation (1-10)
    - Delivery Delay Risk (Low/Medium/High)
    - Buyer Confidence (Excellent/Good/Average/Poor)
    """
    import subprocess

    prompt = f"""You are a Dubai real estate expert analyst. Based on the following REAL transaction data for developer "{dev_name}", provide a qualitative assessment.

REAL DATA:
- Total Projects: {metrics.get('totalProjects', 'N/A')}
- Ready Projects: {metrics.get('readyProjects', 'N/A')}
- Sales Transactions: {metrics.get('salesCount', 'N/A')}
- Sales Value: AED {metrics.get('salesValue', 0):,}
- Off-Plan Transactions: {metrics.get('offplanCount', 'N/A')}
- Average Capital Gain: {metrics.get('avgCapitalGain', 'N/A')}%
- Average Rental Yield: {metrics.get('avgRentalYield', 'N/A')}%
- Total Rent Contracts: {metrics.get('totalRentContracts', 'N/A')}
- Average Price/sqft: AED {metrics.get('avgPriceSqft', 0):,}
- Areas Covered: {', '.join(metrics.get('areasCovered', [])[:5])}

Based on this data AND your knowledge of Dubai real estate, respond as JSON ONLY (no markdown, no explanation):
{{
  "constructionQuality": <1-10 score>,
  "customerReviews": <1-10 score>,
  "marketReputation": <1-10 score>,
  "deliveryDelayRisk": "<Low|Medium|High>",
  "deliveryDelayPercent": <estimated % of delayed projects>,
  "buyerConfidence": "<Excellent|Good|Average|Poor>",
  "marketPosition": "<Tier 1|Tier 2|Tier 3>",
  "summary": "<2-3 sentence assessment>"
}}"""

    # Call vLLM API on server
    payload = json.dumps({
        "model": "Qwen2.5-VL-7B-Instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 500,
    })

    try:
        req = urllib.request.Request(
            "http://87.200.15.174:8001/v1/chat/completions",
            data=payload.encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            content = result['choices'][0]['message']['content'].strip()

            # Parse JSON from response (handle markdown code blocks)
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            content = content.strip()

            return json.loads(content)
    except Exception as e:
        print(f"  [WARN] LLM analysis failed for {dev_name}: {e}")
        # Fallback: estimate from data
        total = metrics.get('totalProjects', 0)
        ready = metrics.get('readyProjects', 0)
        gain = metrics.get('avgCapitalGain', 0)
        yield_ = metrics.get('avgRentalYield', 0)
        sales = metrics.get('salesCount', 0)

        # Rough heuristic
        score = 50
        if total > 20: score += 15
        elif total > 10: score += 10
        elif total > 5: score += 5
        if gain > 10: score += 10
        elif gain > 0: score += 5
        if yield_ > 6: score += 5
        if sales > 100: score += 10
        elif sales > 50: score += 5

        if score >= 80:
            confidence = 'Excellent'
            quality = 9
        elif score >= 70:
            confidence = 'Good'
            quality = 7
        elif score >= 60:
            confidence = 'Average'
            quality = 5
        else:
            confidence = 'Poor'
            quality = 3

        return {
            'constructionQuality': quality,
            'customerReviews': max(4, quality - 1),
            'marketReputation': quality,
            'deliveryDelayRisk': 'Low' if ready > total * 0.5 else 'Medium',
            'deliveryDelayPercent': round((1 - ready / max(total, 1)) * 100, 1) if total > 0 else 50,
            'buyerConfidence': confidence,
            'marketPosition': 'Tier 1' if score >= 80 else 'Tier 2' if score >= 65 else 'Tier 3',
            'summary': f"Automated assessment based on {total} projects, {sales} transactions, {gain}% capital gain."
        }


def compute_developer_score(metrics: dict, qualitative: dict) -> int:
    """Compute final developer score (0-100) from all metrics."""
    score = 0

    # Track record (25 pts) — based on total projects
    total = metrics.get('totalProjects', 0)
    if total >= 50: score += 25
    elif total >= 20: score += 20
    elif total >= 10: score += 15
    elif total >= 5: score += 10
    elif total >= 2: score += 5

    # Delivery performance (20 pts) — ready projects ratio
    ready = metrics.get('readyProjects', 0)
    delivery_pct = qualitative.get('deliveryDelayPercent', 50)
    if delivery_pct < 5: score += 20
    elif delivery_pct < 10: score += 16
    elif delivery_pct < 20: score += 12
    elif delivery_pct < 30: score += 8
    else: score += 4

    # Capital gain (15 pts)
    gain = metrics.get('avgCapitalGain', 0)
    if gain > 15: score += 15
    elif gain > 10: score += 12
    elif gain > 5: score += 10
    elif gain > 0: score += 7
    else: score += 2

    # Rental demand (10 pts)
    rent_contracts = metrics.get('totalRentContracts', 0)
    if rent_contracts > 500: score += 10
    elif rent_contracts > 200: score += 8
    elif rent_contracts > 50: score += 6
    elif rent_contracts > 10: score += 4
    else: score += 2

    # Sales volume (10 pts)
    sales = metrics.get('salesCount', 0)
    if sales > 200: score += 10
    elif sales > 100: score += 8
    elif sales > 50: score += 6
    elif sales > 10: score += 4
    else: score += 2

    # Construction quality from LLM (10 pts)
    quality = qualitative.get('constructionQuality', 5)
    score += int(quality * 1.0)

    # Market reputation from LLM (10 pts)
    reputation = qualitative.get('marketReputation', 5)
    score += int(reputation * 1.0)

    return min(100, max(0, score))


def main():
    print("=" * 60)
    print("Building Real Developer Scores")
    print("=" * 60)

    # Step 1: Compute metrics from local data
    print("\n[1/4] Computing metrics from local DLD data...")
    local_metrics = compute_metrics_from_local_data()
    print(f"  Found {len(local_metrics)} developers in project data")

    # Step 2: Load DXBInteract scraped data (from server scraper)
    print("\n[2/5] Loading DXBInteract scraped data...")
    dxb_metrics = {}
    dxb_file = '/tmp/dev_dxb_real_v2.json'
    if not os.path.exists(dxb_file):
        dxb_file = '/tmp/dev_dxb_real.json'
    if os.path.exists(dxb_file):
        with open(dxb_file) as f:
            dxb_metrics = json.load(f)
        print(f"  Loaded {len(dxb_metrics)} developers from {dxb_file}")
        for name, d in dxb_metrics.items():
            txn = d.get('ytdTransactions', 'N/A')
            val = d.get('totalValueStr', 'N/A')
            proj = d.get('totalProjects', 'N/A')
            print(f"    {name}: YTD_Txn={txn}, Val={val}, Projects={proj}")
    else:
        print(f"  [WARN] No DXB data found")

    # Step 2b: Load delivery rankings (real RERA-style delivery data)
    print("\n[2b/5] Loading delivery rankings...")
    delivery_data = {}
    delivery_file = '/tmp/dev_delivery_real.json'
    if os.path.exists(delivery_file):
        with open(delivery_file) as f:
            delivery_data = json.load(f)
        du = delivery_data.get('deliveredUnits', {})
        dp = delivery_data.get('deliveredProjects', {})
        print(f"  Loaded delivery data: {len(du)} units, {len(dp)} projects")
        for name, units in sorted(du.items(), key=lambda x: -x[1]):
            print(f"    {name}: {units} units delivered (2026)")
    else:
        print(f"  [WARN] No delivery data at {delivery_file}")

    # Step 2c: Load Google Maps reviews (real customer ratings)
    print("\n[2c/5] Loading Google Maps reviews...")
    google_reviews = {}
    reviews_file = '/tmp/dev_google_reviews.json'
    if os.path.exists(reviews_file):
        with open(reviews_file) as f:
            google_reviews = json.load(f)
        print(f"  Loaded {len(google_reviews)} Google review ratings")
        for name, rev in sorted(google_reviews.items(), key=lambda x: -(x[1].get('rating') or 0)):
            rating = rev.get('rating', 'N/A')
            count = rev.get('reviewCount', 'N/A')
            print(f"    {name}: Rating={rating}, Reviews={count}")
    else:
        print(f"  [WARN] No Google reviews at {reviews_file}")

    # Step 3: LLM qualitative analysis
    print("\n[3/5] Loading LLM qualitative analysis...")
    qualitative = {}
    llm_results_file = '/tmp/dev_qualitative.json'
    if os.path.exists(llm_results_file):
        with open(llm_results_file) as f:
            qualitative = json.load(f)
        print(f"  Loaded {len(qualitative)} LLM assessments from {llm_results_file}")
        for dev_name, qual in qualitative.items():
            print(f"    {dev_name}: {qual.get('buyerConfidence', 'N/A')} (quality={qual.get('constructionQuality', 0)}, rep={qual.get('marketReputation', 0)})")
    else:
        print(f"  [WARN] No LLM results at {llm_results_file}, using heuristic fallback")
        for dev_name, metrics in local_metrics.items():
            print(f"  Analyzing {dev_name} (fallback)...")
            qualitative[dev_name] = llm_qualitative_analysis(dev_name, metrics)

    # Step 4: Merge all sources and compute final scores
    print("\n[4/5] Merging sources and computing final scores...")
    developers = []

    # Name matching helper for delivery + google reviews (which use short names)
    def match_delivery_name(dev_name, delivery_dict):
        """Match developer full name to short delivery name."""
        # Direct match
        if dev_name in delivery_dict:
            return delivery_dict[dev_name]
        # Try short forms
        short = dev_name.replace(' Properties', '').replace(' Developments', '').replace(' Realty', '').replace(' Group', '').replace(' (Dubai Holding)', '').strip()
        if short in delivery_dict:
            return delivery_dict[short]
        # Try case-insensitive
        for key in delivery_dict:
            if key.lower() == dev_name.lower() or key.lower() == short.lower():
                return delivery_dict[key]
            if short.lower() in key.lower() or key.lower() in short.lower():
                return delivery_dict[key]
        return None

    def match_google_name(dev_name, reviews_dict):
        """Match developer full name to Google reviews name."""
        if dev_name in reviews_dict:
            return reviews_dict[dev_name]
        short = dev_name.replace(' Properties', '').replace(' Developments', '').replace(' Realty', '').replace(' Group', '').replace(' (Dubai Holding)', '').strip()
        if short in reviews_dict:
            return reviews_dict[short]
        for key in reviews_dict:
            if key.lower() == dev_name.lower() or key.lower() == short.lower():
                return reviews_dict[key]
            if short.lower() in key.lower() or key.lower() in short.lower():
                return reviews_dict[key]
        return None

    for dev_name, metrics in local_metrics.items():
        qual = qualitative.get(dev_name, {})
        dxb = dxb_metrics.get(dev_name, {})

        # Also try matching DXB data by short name
        if not dxb.get('ytdTransactions'):
            for dxb_name, dxb_data in dxb_metrics.items():
                if dxb_name.lower() == dev_name.lower() or dev_name.lower().replace(' properties', '').replace(' developments', '') in dxb_name.lower():
                    if dxb_data.get('ytdTransactions'):
                        dxb = dxb_data
                        break

        # Prefer real DXB scraped data, fall back to local data
        has_dxb = dxb.get('ytdTransactions') is not None

        if has_dxb:
            final_projects = dxb.get('totalProjects', metrics.get('totalProjects', 0))
            final_delivered = dxb.get('deliveredProjects', metrics.get('readyProjects', 0))
            final_under_construction = dxb.get('underConstructionProjects', 0)
            final_total_units = dxb.get('totalUnits', 0)
            final_ytd_txn = dxb.get('ytdTransactions', metrics.get('salesCount', 0))
            final_total_value = dxb.get('totalValueAED', metrics.get('salesValue', 0))
            final_total_value_str = dxb.get('totalValueStr', '')
            final_capital_gain_aed = dxb.get('capitalGainAED', 0)
            final_capital_gain_str = dxb.get('capitalGainStr', '')
            data_source = 'DXBInteract + Google Reviews + DLD'
        else:
            final_projects = metrics.get('totalProjects', 0)
            final_delivered = metrics.get('readyProjects', 0)
            final_under_construction = 0
            final_total_units = 0
            final_ytd_txn = metrics.get('salesCount', 0)
            final_total_value = metrics.get('salesValue', 0)
            final_total_value_str = ''
            final_capital_gain_aed = 0
            final_capital_gain_str = ''
            data_source = 'DLD local data + Google Reviews'

        # Merge real delivery data (2026 delivered units/projects)
        delivered_units_2026 = match_delivery_name(dev_name, delivery_data.get('deliveredUnits', {})) if delivery_data else None
        delivered_projects_2026 = match_delivery_name(dev_name, delivery_data.get('deliveredProjects', {})) if delivery_data else None
        if delivered_units_2026 is not None:
            final_total_units = max(final_total_units, delivered_units_2026)
            data_source += ' + DXB Delivery'
        if delivered_projects_2026 is not None:
            final_delivered = max(final_delivered, delivered_projects_2026)

        # Merge real Google Maps reviews
        google_rev = match_google_name(dev_name, google_reviews) if google_reviews else None
        real_rating = None
        real_review_count = None
        if google_rev and google_rev.get('rating'):
            real_rating = google_rev['rating']
            real_review_count = google_rev.get('reviewCount', 0)
            data_source += ' + Google Maps'

        # Convert Google rating (1-5) to our scale (1-10)
        if real_rating is not None:
            customer_reviews_score = round(real_rating * 2, 1)  # 4.5 -> 9.0
        else:
            customer_reviews_score = qual.get('customerReviews', 5)

        # Capital gain percentage = capital gain AED / total value AED * 100
        if final_total_value > 0 and final_capital_gain_aed > 0:
            capital_gain_pct = round((final_capital_gain_aed / final_total_value) * 100, 1)
        else:
            capital_gain_pct = metrics.get('avgCapitalGain', 0)

        # Delivery delay: compute from real delivery data
        if final_projects > 0 and final_under_construction > 0:
            delay_pct = round((final_under_construction / final_projects) * 100, 1)
        elif delivered_projects_2026 is not None and final_projects > 0:
            # Use real delivery ratio
            delay_pct = round(((final_projects - delivered_projects_2026) / final_projects) * 100, 1)
        else:
            delay_pct = qual.get('deliveryDelayPercent', 0)

        # Real delivery delay risk based on actual data
        if delay_pct < 30:
            delivery_delay_risk = 'Low'
        elif delay_pct < 50:
            delivery_delay_risk = 'Medium'
        else:
            delivery_delay_risk = 'High'

        score = compute_developer_score(metrics, qual)

        # Build aliases for matching
        aliases = []
        for kw in DEVELOPER_KEYWORDS.get(dev_name, []):
            if kw not in aliases:
                aliases.append(kw)

        dev_entry = {
            'name': dev_name,
            'slug': DEVELOPER_SLUGS.get(dev_name, dev_name.lower().replace(' ', '-')),
            'developerScore': score,
            'projectsDelivered': final_delivered,
            'projectsUnderConstruction': final_under_construction,
            'totalProjects': final_projects,
            'totalUnits': final_total_units,
            'delayedProjects': delay_pct,
            'avgResalePremium': capital_gain_pct,
            'capitalGainAED': final_capital_gain_aed,
            'capitalGainStr': final_capital_gain_str,
            'buyerConfidence': qual.get('buyerConfidence', 'Average'),
            'marketPosition': qual.get('marketPosition', 'Tier 3'),
            'constructionQuality': qual.get('constructionQuality', 5),
            'customerReviews': customer_reviews_score,
            'googleRating': real_rating,
            'googleReviewCount': real_review_count,
            'marketReputation': qual.get('marketReputation', 5),
            'deliveryDelayRisk': delivery_delay_risk,
            'salesCount': final_ytd_txn,
            'salesValue': final_total_value,
            'salesValueStr': final_total_value_str,
            'avgRentalYield': metrics.get('avgRentalYield', 0),
            'totalRentContracts': metrics.get('totalRentContracts', 0),
            'avgPriceSqft': metrics.get('avgPriceSqft', 0),
            'areasCovered': metrics.get('areasCovered', []),
            'projectNames': metrics.get('projectNames', []),
            'aliases': aliases,
            'summary': qual.get('summary', ''),
            'dataSource': data_source,
        }
        developers.append(dev_entry)

    # Sort by score descending
    developers.sort(key=lambda x: -x['developerScore'])

    # Add Independent / Other at the end
    developers.append({
        'name': 'Independent / Other',
        'slug': 'independent-other',
        'developerScore': 70,
        'projectsDelivered': 0,
        'readyProjects': 0,
        'delayedProjects': 0,
        'avgResalePremium': 0,
        'buyerConfidence': 'Average',
        'marketPosition': 'Tier 3',
        'constructionQuality': 5,
        'customerReviews': 5,
        'marketReputation': 5,
        'deliveryDelayRisk': 'Medium',
        'salesCount': 0,
        'salesValue': 0,
        'avgRentalYield': 0,
        'totalRentContracts': 0,
        'avgPriceSqft': 0,
        'areasCovered': [],
        'projectNames': [],
        'aliases': [],
        'summary': 'Independent developer or not enough data to classify.',
        'dataSource': 'Default fallback',
    })

    # Write output
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(developers, f, indent=2)

    print(f"\n✅ Written {len(developers)} developers to {OUTPUT_FILE}")
    print("\nTop 10 developers by score:")
    for d in developers[:10]:
        print(f"  {d['developerScore']:3d}  {d['name']:30s}  Projects: {d['projectsDelivered']:3d}  Delay: {d['delayedProjects']}%  Confidence: {d['buyerConfidence']}")


if __name__ == '__main__':
    main()
