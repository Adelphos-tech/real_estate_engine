"""
Patch script to add Qdrant enrichment to the API.
"""
import re

path = '/home/shivang/apil-investment-new/backend/api/main.py'
with open(path) as f:
    content = f.read()

# 1. Add import after the recommendation_engine import
old_import = 'from engines.recommendation_engine import generate_recommendations, parse_budget'
new_import = (
    'from engines.recommendation_engine import generate_recommendations, parse_budget\n'
    'from engines.qdrant_enrichment import enrich_recommendations, enrich_property'
)
content = content.replace(old_import, new_import)

# 2. Modify the recommendations endpoint
old_rec = (
    '@app.post("/recommendations")\n'
    'async def recommendations(profile: InvestorProfile):\n'
    '    recs = generate_recommendations(profile.model_dump())\n'
    '    return recs'
)
new_rec = (
    '@app.post("/recommendations")\n'
    'async def recommendations(profile: InvestorProfile):\n'
    '    recs = generate_recommendations(profile.model_dump())\n'
    '    recs = enrich_recommendations(recs, max_enrich=10)\n'
    '    return recs'
)
content = content.replace(old_rec, new_rec)

# 3. Modify the report endpoint to enrich before picking top
old_report = '    top = recs["recommendations"][0] if recs["recommendations"] else None'
new_report = (
    '    recs = enrich_recommendations(recs, max_enrich=5)\n'
    '    top = recs["recommendations"][0] if recs["recommendations"] else None'
)
content = content.replace(old_report, new_report)

with open(path, 'w') as f:
    f.write(content)

# Verify
with open(path) as f:
    c = f.read()
print('Has qdrant import:', 'qdrant_enrichment' in c)
print('Has enrich_recommendations call:', 'enrich_recommendations' in c)
print('Done')
