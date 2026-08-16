"""Fix the bed type matching in filter_offplan_properties to use normalize_bedtype."""

path = '/home/shivang/apil-investment-new/backend/engines/recommendation_engine.py'
with open(path) as f:
    content = f.read()

old_bed_filter = '''    # Step 2: Bedrooms (HARD) — new v2 uses bedType
    bedrooms = profile.get("bedrooms")
    if bedrooms and bedrooms in BEDROOM_MAP:
        bed_types = BEDROOM_MAP[bedrooms]
        props = [p for p in props if p.get("bedType") in bed_types or
                 any(bt in (p.get("bedType") or "") for bt in bed_types)]'''

new_bed_filter = '''    # Step 2: Bedrooms (HARD) — normalize bed types for matching
    bedrooms = profile.get("bedrooms")
    if bedrooms and bedrooms in BEDROOM_MAP:
        target_norm = normalize_bedtype(bedrooms)
        if target_norm == "3br":
            target_set = {"3br", "4br+"}
        else:
            target_set = {target_norm}
        props = [p for p in props if normalize_bedtype(p.get("bedType", "")) in target_set]'''

if old_bed_filter in content:
    content = content.replace(old_bed_filter, new_bed_filter)
    print('Fixed bed type filter in filter_offplan_properties')
else:
    print('WARNING: Could not find old bed filter')

with open(path, 'w') as f:
    f.write(content)
print('Done')
