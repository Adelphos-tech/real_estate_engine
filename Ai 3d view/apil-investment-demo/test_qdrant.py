"""Test Qdrant enrichment on a single property."""
import sys, json
sys.path.insert(0, '/home/shivang/apil-investment-new/backend')
from engines.qdrant_enrichment import enrich_property

data = json.load(open('/home/shivang/apil-investment-new/backend/data/ready_property_scores.json'))
p = data[0]
title = p['title']
has_ld = bool(p.get('listingData'))
print(f'Before: {title} | has listingData: {has_ld}')

enrich_property(p)
ld = p.get('listingData', {})
n_imgs = len(ld.get('images', []))
desc_len = len(ld.get('description', ''))
n_pp = len(ld.get('paymentPlans', []))
print(f'After: enriched={bool(ld)} | images={n_imgs} | desc={desc_len} chars | paymentPlans={n_pp}')
if ld.get('images'):
    print(f'  First image: {ld["images"][0]}')
if ld.get('paymentPlans'):
    print(f'  Payment plan: {ld["paymentPlans"][:200]}')

# Test a few more
print()
print('=== Testing 5 properties ===')
enriched = 0
for prop in data[:20]:
    enrich_property(prop)
    ld = prop.get('listingData', {})
    if ld:
        enriched += 1
        if enriched <= 3:
            t = prop['title'][:50]
            ni = len(ld.get('images', []))
            nd = len(ld.get('description', ''))
            print(f'  {t} | images={ni} | desc={nd} chars')
print(f'Enriched: {enriched}/20')
