"""Check Qdrant offplan properties for pricing data."""
import json, urllib.request

url = 'http://localhost:6333/collections/Dubai_real_estate_calculation_data_/points/scroll'
body = json.dumps({
    'limit': 200,
    'with_payload': True,
    'with_vector': False,
    'filter': {
        'must': [
            {'key': 'status_norm', 'match': {'value': 'offplan'}}
        ]
    }
}).encode()
req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
resp = json.loads(urllib.request.urlopen(req, timeout=30).read())
pts = resp['result']['points']
print(f'Offplan properties in Qdrant: {len(pts)}')

# Check which have prices
with_price = [p for p in pts if p['payload'].get('price')]
print(f'With price: {len(with_price)}')

# Show sample
for p in pts[:5]:
    pl = p['payload']
    name = pl.get('name', '')[:40]
    price = pl.get('price')
    size = pl.get('size_sq_ft') or pl.get('size_sqft')
    beds = pl.get('bedroom_norm', '')
    area = pl.get('community_area', '')
    dev = pl.get('developer', '')
    proj = pl.get('project_name', '')
    images = len(pl.get('images', []))
    pp = pl.get('payment_plans')
    roi = pl.get('roi')
    gy = pl.get('gross_yield')
    mar = pl.get('median_annual_rent')
    ca = pl.get('capital_appreciation')
    emv = pl.get('estimated_market_value')
    pvm = pl.get('price_vs_market_pct')
    pvl = pl.get('price_vs_market_label')
    is_score = pl.get('investment_score')
    ir = pl.get('investment_rating')
    tc = pl.get('transaction_count')
    print(f'  {name}')
    print(f'    project={proj} | area={area} | dev={dev} | beds={beds} | price={price} | size={size}')
    print(f'    roi={roi} | grossYield={gy} | medianRent={mar} | capApprec={ca} | estMarketVal={emv}')
    print(f'    priceVsMarket={pvm}% ({pvl}) | invScore={is_score} | invRating={ir} | txCount={tc}')
    print(f'    images={images} | paymentPlans={bool(pp)}')
    print()

# Scroll more
offset = resp['result'].get('next_page_offset')
total = len(pts)
while offset and total < 5000:
    body2 = json.dumps({
        'limit': 200,
        'with_payload': True,
        'with_vector': False,
        'offset': offset,
        'filter': {
            'must': [
                {'key': 'status_norm', 'match': {'value': 'offplan'}}
            ]
        }
    }).encode()
    req2 = urllib.request.Request(url, data=body2, headers={'Content-Type': 'application/json'})
    resp2 = json.loads(urllib.request.urlopen(req2, timeout=30).read())
    pts2 = resp2['result']['points']
    if not pts2:
        break
    total += len(pts2)
    offset = resp2['result'].get('next_page_offset')
print(f'Total offplan in Qdrant: {total}')
