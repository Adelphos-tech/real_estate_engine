"""Patch recommendation_engine.py to handle new offplan v2 data structure."""

path = '/home/shivang/apil-investment-new/backend/engines/recommendation_engine.py'
with open(path) as f:
    content = f.read()

# Add bed type normalization helper after BEDROOM_MAP
old_bedroom_map = '''BEDROOM_MAP = {
    "studio": ["Studio"],
    "1": ["1 B/R"],
    "2": ["2 B/R"],
    "3": ["3 B/R", "4 B/R", "5 B/R", "6 B/R"],
}'''

new_bedroom_map = '''BEDROOM_MAP = {
    "studio": ["Studio"],
    "1": ["1 B/R"],
    "2": ["2 B/R"],
    "3": ["3 B/R", "4 B/R", "5 B/R", "6 B/R"],
}


def normalize_bedtype(bed_type: str) -> str:
    """Normalize bed type strings to a common format for matching."""
    if not bed_type:
        return ""
    b = bed_type.lower().strip()
    if "studio" in b:
        return "studio"
    if b.startswith("1") or b == "1br":
        return "1br"
    if b.startswith("2") or b == "2br":
        return "2br"
    if b.startswith("3") or b == "3br":
        return "3br"
    if any(b.startswith(x) for x in ["4", "5", "6", "7"]) or "br+" in b:
        return "4br+"
    return b'''

if old_bedroom_map in content:
    content = content.replace(old_bedroom_map, new_bedroom_map)
    print('Added normalize_bedtype helper')
else:
    print('WARNING: Could not find BEDROOM_MAP')

# Replace filter_offplan_properties with enhanced version
old_filter = '''def filter_offplan_properties(profile: dict, offplan_props: list[dict]) -> list[dict]:
    props = offplan_props

    # Location filter
    location = profile.get("location")
    if location and location != "any":
        props = [p for p in props if location.lower() in p.get("area", "").lower()]

    # Risk filter
    if profile.get("risk") == "low":
        props = [p for p in props if p.get("risk", {}).get("riskLevel") != "High"]

    # Developer filter — if conservative, only Tier 1/2
    if profile.get("risk") == "low":
        props = [p for p in props if p.get("developerScore", 0) >= 70]

    return props'''

new_filter = '''def filter_offplan_properties(profile: dict, offplan_props: list[dict]) -> list[dict]:
    props = offplan_props

    # Step 1: Property type (HARD)
    prop_type = profile.get("property_type")
    if prop_type and prop_type in PROPERTY_TYPE_MAP:
        categories = PROPERTY_TYPE_MAP[prop_type]
        props = [p for p in props if p.get("category", "") in categories]

    # Step 2: Bedrooms (HARD) — normalize bed types for matching
    bedrooms = profile.get("bedrooms")
    if bedrooms and bedrooms in BEDROOM_MAP:
        target_norm = normalize_bedtype(bedrooms)
        if target_norm == "3br":
            target_set = {"3br", "4br+"}
        else:
            target_set = {target_norm}
        props = [p for p in props if normalize_bedtype(p.get("bedType", "")) in target_set]

    # Step 3: Budget (HARD)
    min_price, max_price = parse_budget(profile.get("budget", ""))
    if min_price > 0 or max_price < float("inf"):
        props = [p for p in props if p.get("askingPrice", 0) > 0 and
                 min_price <= p.get("askingPrice", 0) <= max_price]

    # Step 4: Location
    location = profile.get("location")
    if location and location != "any":
        props = [p for p in props if location.lower() in p.get("area", "").lower() or
                 location.lower() in p.get("project", "").lower()]

    # Step 5: Risk filter
    if profile.get("risk") == "low":
        props = [p for p in props if p.get("risk", {}).get("riskLevel") != "High"]
        props = [p for p in props if p.get("developerData", {}).get("developerScore", 0) >= 70 or
                 p.get("developerScore", 0) >= 70]

    # Step 6: Exclude AVOID recommendations for low-risk investors
    if profile.get("risk") == "low":
        props = [p for p in props if p.get("recommendation", "") != "AVOID"]

    return props'''

if old_filter in content:
    content = content.replace(old_filter, new_filter)
    print('Replaced filter_offplan_properties')
else:
    print('WARNING: Could not find filter_offplan_properties to replace')

# Update sort_by_goal to handle offplan v2 fields
old_sort = '''def sort_by_goal(props: list[dict], goal: str, score_field: str) -> list[dict]:
    if goal == "rental_income":
        return sorted(props, key=lambda p: -safe_float(p.get("roi", {}).get("netROI", 0)))
    elif goal == "capital_growth":
        return sorted(props, key=lambda p: -safe_float(p.get("growth12m", 0)))
    elif goal == "holiday_home":
        return sorted(props, key=lambda p: -(safe_float(p.get(score_field, 0)) + safe_float(p.get("growth12m", 0))))
    else:
        return sorted(props, key=lambda p: -safe_float(p.get(score_field, 0)))'''

new_sort = '''def sort_by_goal(props: list[dict], goal: str, score_field: str) -> list[dict]:
    if goal == "rental_income":
        return sorted(props, key=lambda p: -(
            safe_float(p.get("postHandoverROI", {}).get("netROI", 0)) or
            safe_float(p.get("roi", {}).get("netROI", 0))
        ))
    elif goal == "capital_growth":
        return sorted(props, key=lambda p: -(
            safe_float(p.get("futureAppreciation", {}).get("potentialGainPct", 0)) or
            safe_float(p.get("growth12m", 0))
        ))
    elif goal == "holiday_home":
        return sorted(props, key=lambda p: -(
            safe_float(p.get(score_field, 0)) +
            (safe_float(p.get("futureAppreciation", {}).get("potentialGainPct", 0)) or
             safe_float(p.get("growth12m", 0)))
        ))
    else:
        return sorted(props, key=lambda p: -safe_float(p.get(score_field, 0)))'''

if old_sort in content:
    content = content.replace(old_sort, new_sort)
    print('Replaced sort_by_goal')
else:
    print('WARNING: Could not find sort_by_goal to replace')

with open(path, 'w') as f:
    f.write(content)

print('Done patching recommendation_engine.py')
