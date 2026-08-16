"""
Shared utilities for APIL Intelligence Engines.
"""
from __future__ import annotations

import json
import re
import math
from datetime import datetime, timedelta
from typing import Any
from statistics import median as stats_median


def clamp(val: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, val))


def safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        if f != f:  # NaN
            return default
        if math.isinf(f):  # Infinity
            return default
        return f
    except (TypeError, ValueError, OverflowError):
        return default


def safe_int(val: Any, default: int = 0) -> int:
    f = safe_float(val, default)
    try:
        return int(f)
    except (OverflowError, ValueError):
        return default


def median(arr: list[float]) -> float:
    if not arr:
        return 0
    return stats_median(arr)


def parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    s = date_str.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:len(fmt) + 5 if 'T' in fmt else len(fmt)], fmt)
        except ValueError:
            continue
    if re.match(r"^\d{4}-\d{2}-\d{2}", s):
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            pass
    return None


def months_between(d1: datetime, d2: datetime) -> int:
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def normalize_bed_type(beds: str) -> str:
    if not beds:
        return "Unknown"
    s = beds.strip().lower()
    if "studio" in s:
        return "Studio"
    m = re.search(r"(\d+)", s)
    return f"{m.group(1)} B/R" if m else "Unknown"


def load_json(path) -> Any:
    with open(path) as f:
        return json.load(f)


def save_json(path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _build_monthly_median_index(sales: list[dict]) -> dict[str, float]:
    """Build a monthly median price/sqft index from sales data.
    Returns {YYYY-MM: median_price_sqft} for each month with enough data."""
    from collections import defaultdict
    monthly = defaultdict(list)
    for s in sales:
        d = parse_date(s.get("date", ""))
        if not d:
            continue
        psqft = s.get("price_sqft")
        if psqft and psqft > 0:
            monthly[d.strftime("%Y-%m")].append(psqft)

    index = {}
    for month, prices in sorted(monthly.items()):
        clean = _remove_iqr_outliers(prices)
        if len(clean) >= 2:
            index[month] = median(clean)
    return index


def _rolling_median(index: dict[str, float], target_month: str, window: int = 3) -> float | None:
    """Get rolling 3-month median around target month."""
    from datetime import datetime as dt
    parts = target_month.split("-")
    y, m = int(parts[0]), int(parts[1])
    values = []
    for i in range(window):
        mm = m - i
        yy = y
        if mm <= 0:
            mm = 12 + mm
            yy -= 1
        key = f"{yy:04d}-{mm:02d}"
        if key in index:
            values.append(index[key])
    if not values:
        return None
    return median(values)


def _month_offset(month_key: str, delta: int) -> str:
    """Shift a YYYY-MM key by delta months."""
    parts = month_key.split("-")
    y, m = int(parts[0]), int(parts[1])
    m += delta
    while m <= 0:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return f"{y:04d}-{m:02d}"


def calculate_growth(sales: list[dict], months: int) -> float:
    """Calculate growth using rolling monthly median price/sqft index.
    Uses the latest available month in the data, not the current date."""
    index = _build_monthly_median_index(sales)
    if len(index) < 2:
        return 0.0

    latest_month = max(index.keys())
    past_key = _month_offset(latest_month, -months)

    current_rolling = _rolling_median(index, latest_month, window=min(3, months))
    past_rolling = _rolling_median(index, past_key, window=min(3, months))

    if current_rolling is None or past_rolling is None or past_rolling == 0:
        return 0.0

    if past_key == latest_month:
        return 0.0

    growth = ((current_rolling - past_rolling) / past_rolling) * 100
    growth = max(-60.0, min(60.0, growth))
    return round(growth, 2)


def calculate_growth_with_metadata(sales: list[dict], months: int) -> dict:
    """Calculate growth with sample size and confidence metadata using rolling median index."""
    index = _build_monthly_median_index(sales)

    if len(index) < 2:
        return {"growth": 0.0, "recentSamples": 0, "olderSamples": 0, "totalSamples": len(sales), "confidence": "low"}

    latest_month = max(index.keys())
    past_key = _month_offset(latest_month, -months)

    current_rolling = _rolling_median(index, latest_month, window=min(3, months))
    past_rolling = _rolling_median(index, past_key, window=min(3, months))

    if current_rolling is None or past_rolling is None or past_rolling == 0:
        return {"growth": 0.0, "recentSamples": len(index), "olderSamples": len(index), "totalSamples": len(sales), "confidence": "low"}

    if past_key == latest_month:
        return {"growth": 0.0, "recentSamples": len(index), "olderSamples": len(index), "totalSamples": len(sales), "confidence": "low"}

    growth = ((current_rolling - past_rolling) / past_rolling) * 100
    growth = max(-60.0, min(60.0, growth))

    months_with_data = len(index)
    if months_with_data >= 10:
        confidence = "high"
    elif months_with_data >= 6:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "growth": round(growth, 2),
        "recentSamples": months_with_data,
        "olderSamples": months_with_data,
        "totalSamples": len(sales),
        "confidence": confidence,
        "currentMedian": round(current_rolling, 2),
        "pastMedian": round(past_rolling, 2),
        "latestMonth": latest_month,
    }


def _remove_iqr_outliers(values: list[float], multiplier: float = 2.0) -> list[float]:
    """Remove IQR-based outliers from a list of values."""
    if len(values) < 4:
        return values
    sorted_v = sorted(values)
    n = len(sorted_v)
    q1 = sorted_v[n // 4]
    q3 = sorted_v[3 * n // 4]
    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    return [v for v in values if lower <= v <= upper]


def risk_from_score(score: float) -> str:
    if score >= 80:
        return "Low"
    if score >= 65:
        return "Medium"
    return "High"


def score_to_label(score: float) -> str:
    if score >= 90:
        return "Excellent Investment"
    if score >= 80:
        return "Strong Opportunity"
    if score >= 70:
        return "Fair Investment"
    return "Review Carefully"


def recommendation_from_score(score: float, confidence: float = 100, goal: str = "balanced") -> str:
    """Stage 5+6: Goal-aware recommendation with hard rule overrides."""
    if confidence < 25:
        return "INSUFFICIENT_DATA"
    if confidence < 40:
        return "REVIEW"
    if goal == "rental_income":
        if score >= 85 and confidence >= 85:
            return "STRONG BUY"
        if score >= 75 and confidence >= 75:
            return "BUY"
        if score >= 65:
            return "HOLD"
        if score >= 55:
            return "WATCHLIST"
        return "REVIEW"
    elif goal == "capital_growth":
        if score >= 85 and confidence >= 75:
            return "STRONG BUY"
        if score >= 75 and confidence >= 65:
            return "BUY"
        if score >= 65:
            return "HOLD"
        if score >= 55:
            return "WATCHLIST"
        return "REVIEW"
    else:
        if score >= 85:
            return "STRONG BUY" if confidence >= 80 else "BUY"
        if score >= 75:
            return "BUY" if confidence >= 70 else "HOLD"
        if score >= 65:
            return "HOLD" if confidence >= 65 else "CAUTION"
        if score >= 55:
            return "WATCHLIST"
        return "REVIEW"
