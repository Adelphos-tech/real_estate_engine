"""Test offplan filter directly."""
import sys
sys.path.insert(0, '/home/shivang/apil-investment-new/backend')
from engines.recommendation_engine import filter_offplan_properties, normalize_bedtype
from engines.utils import load_json
from config.settings import OFFPLAN_SCORES_FILE

offplan = load_json(OFFPLAN_SCORES_FILE)
print(f'Total offplan: {len(offplan)}')

# Test normalize
print(f'normalize_bedtype("1br"): {normalize_bedtype("1br")}')
print(f'normalize_bedtype("1"): {normalize_bedtype("1")}')
print(f'normalize_bedtype("Studio"): {normalize_bedtype("Studio")}')

# Test filter
profile = {
    'budget': '1m-2m',
    'property_type': 'apartment',
    'bedrooms': '1',
    'goal': 'capital_growth',
    'ready_offplan': 'offplan',
    'risk': 'medium',
}

filtered = filter_offplan_properties(profile, offplan)
print(f'Filtered offplan: {len(filtered)}')

if filtered:
    p = filtered[0]
    print(f'Top: {p.get("title", "")[:50]} | score={p.get("offplanScore")} | rec={p.get("recommendation")}')
    print(f'  bedType={p.get("bedType")} | category={p.get("category")} | price={p.get("askingPrice")}')
else:
    # Debug: check each filter step
    props = offplan
    print(f'After load: {len(props)}')

    # Property type
    from engines.recommendation_engine import PROPERTY_TYPE_MAP
    categories = PROPERTY_TYPE_MAP.get('apartment', [])
    props = [p for p in props if p.get('category', '') in categories]
    print(f'After property type (apartment, {categories}): {len(props)}')

    # Bedrooms
    target_norm = normalize_bedtype('1')
    target_set = {target_norm}
    props = [p for p in props if normalize_bedtype(p.get('bedType', '')) in target_set]
    print(f'After bedrooms (1br, set={target_set}): {len(props)}')

    # Budget
    from engines.recommendation_engine import parse_budget
    min_p, max_p = parse_budget('1m-2m')
    print(f'Budget range: {min_p} - {max_p}')
    props = [p for p in props if p.get('askingPrice', 0) > 0 and min_p <= p.get('askingPrice', 0) <= max_p]
    print(f'After budget: {len(props)}')

    # Sample bedTypes in apartment range
    apts = [p for p in offplan if p.get('category') == 'Apartment']
    from collections import Counter
    beds = Counter(normalize_bedtype(p.get('bedType', '')) for p in apts)
    print(f'Apartment bedTypes (normalized): {dict(beds)}')
