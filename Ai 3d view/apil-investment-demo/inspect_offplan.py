"""Inspect offplan data for building the new engine."""
import json

d = json.load(open('/home/shivang/apil-investment-new/backend/data/offplan_scores.json'))
print(f'Offplan count: {len(d)}')
with_units = [p for p in d if p.get('unitTypes')]
print(f'With unitTypes: {len(with_units)}')

print()
print('Sample launchPricing:')
for p in d[:5]:
    lp = p.get('launchPricing', {})
    name = p.get('projectName', '')[:30]
    ppsqft = lp.get('projectPriceSqft')
    npsqft = lp.get('nearbyPriceSqft')
    disc = lp.get('discountToMarket')
    print(f'  {name} | priceSqft: {ppsqft} | nearbySqft: {npsqft} | discount: {disc}%')

print()
print('Sample growthForecast:')
for p in d[:5]:
    gf = p.get('growthForecast', {})
    name = p.get('projectName', '')[:30]
    pg = gf.get('predictedGrowth')
    gs = gf.get('growthPotentialScore')
    print(f'  {name} | predictedGrowth: {pg} | growthScore: {gs}')

print()
print('Sample full record:')
print(json.dumps(d[0], indent=2)[:2000])

# Check community scores for medianPriceSqft
print()
cs = json.load(open('/home/shivang/apil-investment-new/backend/data/community_scores.json'))
print(f'Communities: {len(cs)}')
c = cs[0]
pi = c.get('priceIndex', {})
ri = c.get('rentalIndex', {})
print(f'  {c["name"]} | medianPriceSqft: {pi.get("medianPriceSqft")} | medianRent: {ri.get("medianRent")} | growth12m: {c.get("growthIndex",{}).get("growth12m")}')

# Check developer scores
print()
ds = json.load(open('/home/shivang/apil-investment-new/backend/data/developer_scores.json'))
print(f'Developers: {len(ds)}')
d0 = ds[0]
print(f'  {d0["name"]} | score: {d0.get("developerScore")} | delayed: {d0.get("delayedProjects")}% | tier: {d0.get("marketPosition")} | avgResalePremium: {d0.get("avgResalePremium")}%')

# Check feature_store for offplan data
print()
fs = json.load(open('/home/shivang/apil-investment-new/backend/data/feature_store.json'))
print(f'Feature store: {len(fs)} records')
f0 = fs[0]
print(f'  Keys: {list(f0.keys())}')
uf = f0.get('unitFeatures', {})
print(f'  Unit types: {list(uf.keys())[:5]}')
