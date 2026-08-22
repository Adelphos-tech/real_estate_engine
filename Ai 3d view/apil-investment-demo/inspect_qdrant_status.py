"""Check Qdrant status values and is_off_plan field."""
import json, urllib.request
from collections import Counter

COLLECTION = 'properties_collection'
url = f'http://localhost:6333/collections/{COLLECTION}/points/scroll'
body = json.dumps({'limit': 200, 'with_payload': True, 'with_vector': False}).encode()
req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
pts = resp['result']['points']

statuses = Counter()
is_off = Counter()
for p in pts:
    pl = p['payload']
    statuses[pl.get('status', 'MISSING')] += 1
    is_off[pl.get('is_off_plan', 'MISSING')] += 1

print('Status values:')
for s, c in statuses.most_common():
    print(f'  {s}: {c}')
print()
print('is_off_plan values:')
for s, c in is_off.most_common():
    print(f'  {s}: {c}')

# Show a few offplan ones
print()
offplan = [p for p in pts if p['payload'].get('is_off_plan') == True or 'off' in str(p['payload'].get('status', '')).lower()]
print(f'Offplan samples: {len(offplan)}')
for p in offplan[:3]:
    pl = p['payload']
    name = pl.get('name', '')[:40]
    price = pl.get('price')
    size = pl.get('size_sq_ft') or pl.get('size_sqft')
    beds = pl.get('bedroom_norm', '')
    area = pl.get('community_area', '')
    proj = pl.get('project_name', '')
    pvm = pl.get('price_vs_market_pct')
    emv = pl.get('estimated_market_value')
    is_score = pl.get('investment_score')
    print(f'  {name} | proj={proj} | area={area} | beds={beds} | price={price} | size={size} | priceVsMarket={pvm}% | estMarketVal={emv} | invScore={is_score}')

# Scroll all to get counts
offset = resp['result'].get('next_page_offset')
total = len(pts)
while offset and total < 5000:
    body2 = json.dumps({'limit': 200, 'with_payload': True, 'with_vector': False, 'offset': offset}).encode()
    req2 = urllib.request.Request(url, data=body2, headers={'Content-Type': 'application/json'})
    resp2 = json.loads(urllib.request.urlopen(req2, timeout=30).read())
    pts2 = resp2['result']['points']
    if not pts2:
        break
    for p in pts2:
        statuses[p['payload'].get('status', 'MISSING')] += 1
        is_off[p['payload'].get('is_off_plan', 'MISSING')] += 1
    total += len(pts2)
    offset = resp2['result'].get('next_page_offset')

print(f'\nTotal scanned: {total}')
print('Status values (all):')
for s, c in statuses.most_common():
    print(f'  {s}: {c}')
print('is_off_plan (all):')
for s, c in is_off.most_common():
    print(f'  {s}: {c}')
