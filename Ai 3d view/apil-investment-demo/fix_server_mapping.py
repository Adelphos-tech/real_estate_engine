"""Fix apil_server.py recommendations endpoint to properly map all profile fields."""

path = '/home/shivang/apil-investment-new/apil_server.py'
with open(path) as f:
    content = f.read()

old_mapping = '''    body = await request.json()
    profile = {
        "budget": body.get("budget", ""),
        "property_type": body.get("propertyType", "ready"),
        "bedrooms": body.get("bedrooms", "any"),
        "strategy": body.get("strategy", "balanced"),
        "risk": body.get("riskTolerance", "medium"),
        "location": body.get("area", "any"),
    }

    recs = generate_recommendations(profile)
    return recs'''

new_mapping = '''    body = await request.json()
    profile = {
        "goal": body.get("goal", body.get("strategy", "balanced")),
        "budget": body.get("budget", ""),
        "property_type": body.get("property_type", body.get("propertyType", "")),
        "bedrooms": body.get("bedrooms", "any"),
        "location": body.get("location", body.get("area", "any")),
        "ready_offplan": body.get("ready_offplan", body.get("readyOffplan", "ready")),
        "timeline": body.get("timeline", ""),
        "financing": body.get("financing", ""),
        "risk": body.get("risk", body.get("riskTolerance", "medium")),
    }

    recs = generate_recommendations(profile)
    return recs'''

if old_mapping in content:
    content = content.replace(old_mapping, new_mapping)
    print('Fixed profile field mapping in apil_server.py')
else:
    print('WARNING: Could not find old mapping')

with open(path, 'w') as f:
    f.write(content)
print('Done')
