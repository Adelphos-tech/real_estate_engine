"""
APIL Investor Strategy Engine
Converts questionnaire answers into a dynamic investment strategy profile.

Architecture:
  Questionnaire → Investor Strategy Engine → Property Scoring → Investor Fit Engine → Recommendation

The strategy profile contains:
  - Dynamic scoring weights (different per goal/property type)
  - Minimum thresholds (developer score, area growth, supply score)
  - Exit strategy preferences
  - Risk-adjusted penalties
  - Financing mode (cash/mortgage/payment plan)
  - Holding period considerations
"""
from __future__ import annotations


# ─── Strategy Profiles per Goal ───

STRATEGY_WEIGHTS = {
    # ── Rental Income ──
    "rental_income": {
        "ready": {
            "roi": 0.35,
            "rental_demand": 0.20,
            "vacancy": 0.15,
            "liquidity": 0.15,
            "developer": 0.10,
            "growth": 0.05,
        },
        "offplan": {
            "roi": 0.30,
            "rental_demand": 0.20,
            "developer": 0.20,
            "payment_plan": 0.10,
            "liquidity": 0.10,
            "growth": 0.05,
            "supply_risk": 0.05,
        },
    },
    # ── Capital Growth ──
    "capital_growth": {
        "ready": {
            "growth": 0.30,
            "developer": 0.20,
            "supply": 0.15,
            "pricing": 0.15,
            "liquidity": 0.10,
            "rental": 0.05,
            "demand": 0.05,
        },
        "offplan": {
            "developer": 0.25,
            "price": 0.20,
            "payment_plan": 0.15,
            "growth": 0.10,
            "supply_risk": 0.10,
            "liquidity": 0.05,
            "roi": 0.05,
        },
    },
    # ── Flip Before Handover (off-plan only strategy) ──
    "flip_handover": {
        "ready": {
            # Flipping ready properties = short-term capital gain
            "growth": 0.25,
            "liquidity": 0.25,
            "pricing": 0.20,
            "developer": 0.15,
            "demand": 0.10,
            "rental": 0.05,
        },
        "offplan": {
            "payment_plan": 0.25,
            "developer": 0.20,
            "price": 0.15,
            "growth": 0.15,
            "supply_risk": 0.10,
            "liquidity": 0.10,
            "roi": 0.00,  # Rental irrelevant for flip
        },
    },
    # ── Holiday Home ──
    "holiday_home": {
        "ready": {
            "rental": 0.25,
            "demand": 0.20,
            "liquidity": 0.15,
            "growth": 0.15,
            "developer": 0.10,
            "pricing": 0.10,
            "supply": 0.05,
        },
        "offplan": {
            "developer": 0.25,
            "payment_plan": 0.15,
            "growth": 0.15,
            "price": 0.15,
            "liquidity": 0.10,
            "roi": 0.10,
            "supply_risk": 0.10,
        },
    },
    # ── Balanced (default) ──
    "balanced": {
        "ready": {
            "roi": 0.20,
            "growth": 0.20,
            "liquidity": 0.15,
            "developer": 0.15,
            "pricing": 0.15,
            "demand": 0.10,
            "supply": 0.05,
        },
        "offplan": {
            "developer": 0.25,
            "price": 0.20,
            "payment_plan": 0.15,
            "growth": 0.10,
            "supply_risk": 0.10,
            "liquidity": 0.05,
            "roi": 0.05,
        },
    },
    # ── End User ──
    "end_user": {
        "ready": {
            "developer": 0.25,
            "demand": 0.20,
            "liquidity": 0.15,
            "growth": 0.15,
            "pricing": 0.10,
            "rental": 0.10,
            "supply": 0.05,
        },
        "offplan": {
            "developer": 0.30,
            "payment_plan": 0.20,
            "price": 0.15,
            "growth": 0.10,
            "supply_risk": 0.10,
            "liquidity": 0.05,
            "roi": 0.05,
        },
    },
    # ── Diversification ──
    "diversification": {
        "ready": {
            "growth": 0.20,
            "roi": 0.20,
            "developer": 0.15,
            "liquidity": 0.15,
            "pricing": 0.15,
            "demand": 0.10,
            "supply": 0.05,
        },
        "offplan": {
            "developer": 0.25,
            "price": 0.20,
            "payment_plan": 0.15,
            "growth": 0.10,
            "supply_risk": 0.10,
            "liquidity": 0.05,
            "roi": 0.05,
        },
    },
}

# ─── Minimum Thresholds per Goal + Risk ───

THRESHOLDS = {
    "rental_income": {
        "min_developer_score": {"low": 70, "medium": 60, "high": 50},
        "min_area_growth": {"low": 5, "medium": 3, "high": 0},
        "min_supply_score": {"low": 60, "medium": 50, "high": 30},
        "min_net_roi": {"low": 7, "medium": 5, "high": 3},
        "max_premium_pct": {"low": 5, "medium": 10, "high": 15},
    },
    "capital_growth": {
        "min_developer_score": {"low": 75, "medium": 65, "high": 50},
        "min_area_growth": {"low": 15, "medium": 10, "high": 5},
        "min_supply_score": {"low": 60, "medium": 50, "high": 30},
        "min_net_roi": {"low": 0, "medium": 0, "high": 0},
        "max_premium_pct": {"low": 5, "medium": 10, "high": 20},
    },
    "flip_handover": {
        "min_developer_score": {"low": 75, "medium": 65, "high": 55},
        "min_area_growth": {"low": 10, "medium": 8, "high": 5},
        "min_supply_score": {"low": 55, "medium": 45, "high": 30},
        "min_net_roi": {"low": 0, "medium": 0, "high": 0},
        "max_premium_pct": {"low": 0, "medium": 5, "high": 10},
    },
    "holiday_home": {
        "min_developer_score": {"low": 70, "medium": 60, "high": 50},
        "min_area_growth": {"low": 8, "medium": 5, "high": 3},
        "min_supply_score": {"low": 55, "medium": 45, "high": 30},
        "min_net_roi": {"low": 5, "medium": 3, "high": 0},
        "max_premium_pct": {"low": 10, "medium": 15, "high": 25},
    },
    "balanced": {
        "min_developer_score": {"low": 70, "medium": 60, "high": 45},
        "min_area_growth": {"low": 8, "medium": 5, "high": 3},
        "min_supply_score": {"low": 55, "medium": 45, "high": 30},
        "min_net_roi": {"low": 5, "medium": 3, "high": 0},
        "max_premium_pct": {"low": 5, "medium": 10, "high": 20},
    },
    "end_user": {
        "min_developer_score": {"low": 75, "medium": 65, "high": 50},
        "min_area_growth": {"low": 5, "medium": 3, "high": 0},
        "min_supply_score": {"low": 60, "medium": 50, "high": 30},
        "min_net_roi": {"low": 0, "medium": 0, "high": 0},
        "max_premium_pct": {"low": 5, "medium": 10, "high": 15},
    },
    "diversification": {
        "min_developer_score": {"low": 70, "medium": 60, "high": 45},
        "min_area_growth": {"low": 8, "medium": 5, "high": 3},
        "min_supply_score": {"low": 55, "medium": 45, "high": 30},
        "min_net_roi": {"low": 4, "medium": 3, "high": 0},
        "max_premium_pct": {"low": 5, "medium": 10, "high": 20},
    },
}

# ─── Exit Strategy Preferences per Goal + Holding Period ───

EXIT_PREFERENCES = {
    "rental_income": "rent_hold",
    "capital_growth": "sell_handover",
    "flip_handover": "assignment",
    "holiday_home": "rent_hold",
    "balanced": "sell_handover",
    "end_user": "hold_5yr",
    "diversification": "hold_5yr",
}

# ─── Holding Period Adjustments ───

HOLDING_PERIOD_IMPACT = {
    "1-2y": {
        "description": "Short-term",
        "weight_adjustment": {"liquidity": 1.3, "growth": 0.7, "rental": 0.5},
        "exit_strategy": "assignment",
    },
    "3-5y": {
        "description": "Medium-term",
        "weight_adjustment": {},
        "exit_strategy": None,  # Use goal default
    },
    "5y+": {
        "description": "Long-term",
        "weight_adjustment": {"rental": 1.2, "growth": 1.1, "liquidity": 0.8},
        "exit_strategy": "hold_5yr",
    },
    "undecided": {
        "description": "Flexible",
        "weight_adjustment": {},
        "exit_strategy": None,
    },
}

# ─── Financing Mode Impact ───

FINANCING_IMPACT = {
    "cash": {
        "description": "Cash purchase",
        "metrics": ["simple_roi", "total_return"],
        "weight_adjustment": {},
    },
    "mortgage": {
        "description": "Mortgage financed",
        "metrics": ["cash_on_cash_return", "dscr", "ltv", "monthly_payment"],
        "weight_adjustment": {"roi": 1.2, "pricing": 1.1},  # ROI more important with mortgage
    },
    "either": {
        "description": "Flexible financing",
        "metrics": ["simple_roi", "cash_on_cash_return"],
        "weight_adjustment": {},
    },
}


def build_investor_strategy(profile: dict) -> dict:
    """
    Convert questionnaire answers into a structured investment strategy.

    Input: profile dict with keys:
        goal, budget, property_type, bedrooms, location,
        ready_offplan, timeline, financing, risk

    Output: strategy dict with:
        weights (ready + offplan), thresholds, exit_preference,
        financing_mode, holding_period, risk_level, strategy_summary
    """
    goal = profile.get("goal", "balanced")
    risk = profile.get("risk", "medium")
    timeline = profile.get("timeline", "3-5y")
    financing = profile.get("financing", "cash")
    ready_offplan = profile.get("ready_offplan", "ready")

    # Get base weights for this goal
    goal_weights = STRATEGY_WEIGHTS.get(goal, STRATEGY_WEIGHTS["balanced"])

    # Clone weights for adjustment
    ready_weights = dict(goal_weights.get("ready", {}))
    offplan_weights = dict(goal_weights.get("offplan", {}))

    # Apply holding period adjustments
    period_config = HOLDING_PERIOD_IMPACT.get(timeline, HOLDING_PERIOD_IMPACT["3-5y"])
    period_adj = period_config.get("weight_adjustment", {})
    for key, multiplier in period_adj.items():
        if key in ready_weights:
            ready_weights[key] = round(ready_weights[key] * multiplier, 3)
        if key in offplan_weights:
            offplan_weights[key] = round(offplan_weights[key] * multiplier, 3)

    # Apply financing adjustments
    fin_config = FINANCING_IMPACT.get(financing, FINANCING_IMPACT["cash"])
    fin_adj = fin_config.get("weight_adjustment", {})
    for key, multiplier in fin_adj.items():
        if key in ready_weights:
            ready_weights[key] = round(ready_weights[key] * multiplier, 3)
        if key in offplan_weights:
            offplan_weights[key] = round(offplan_weights[key] * multiplier, 3)

    # Normalize weights to sum to 1.0
    ready_weights = _normalize_weights(ready_weights)
    offplan_weights = _normalize_weights(offplan_weights)

    # Get thresholds for this goal + risk level
    goal_thresholds = THRESHOLDS.get(goal, THRESHOLDS["balanced"])
    thresholds = {}
    for key, risk_map in goal_thresholds.items():
        thresholds[key] = risk_map.get(risk, risk_map.get("medium"))

    # Determine exit strategy
    exit_pref = EXIT_PREFERENCES.get(goal, "sell_handover")
    if period_config.get("exit_strategy"):
        exit_pref = period_config["exit_strategy"]

    # Build strategy summary
    strategy_summary = _build_summary(goal, risk, timeline, financing, ready_offplan, exit_pref)

    return {
        "goal": goal,
        "risk_level": risk,
        "holding_period": timeline,
        "financing_mode": financing,
        "property_preference": ready_offplan,

        # Dynamic scoring weights
        "ready_weights": ready_weights,
        "offplan_weights": offplan_weights,

        # Minimum thresholds (risk-adjusted)
        "thresholds": thresholds,

        # Exit strategy preference
        "exit_strategy": exit_pref,

        # Financing details
        "financing_metrics": fin_config.get("metrics", []),

        # Human-readable summary
        "strategy_summary": strategy_summary,

        # Period description
        "holding_description": period_config.get("description", "Medium-term"),
        "financing_description": fin_config.get("description", "Cash purchase"),
    }


def _normalize_weights(weights: dict) -> dict:
    """Normalize weight values to sum to 1.0."""
    total = sum(weights.values())
    if total > 0:
        return {k: round(v / total, 4) for k, v in weights.items()}
    return weights


def _build_summary(goal: str, risk: str, timeline: str,
                   financing: str, ready_offplan: str, exit_pref: str) -> str:
    """Build a human-readable strategy summary."""
    goal_labels = {
        "rental_income": "Rental Income",
        "capital_growth": "Capital Growth",
        "flip_handover": "Flip Before Handover",
        "holiday_home": "Holiday Home",
        "balanced": "Balanced",
        "end_user": "End User",
        "diversification": "Diversification",
    }
    risk_labels = {"low": "Conservative", "medium": "Balanced", "high": "Aggressive"}
    period_labels = {"1-2y": "1-2 years", "3-5y": "3-5 years", "5y+": "5+ years", "undecided": "Flexible"}
    prop_labels = {"ready": "Ready Property", "offplan": "Off-Plan", "either": "Either"}
    exit_labels = {
        "assignment": "Assignment before completion",
        "sell_handover": "Sell after appreciation",
        "rent_hold": "Rent after handover",
        "hold_5yr": "Hold 5+ years",
    }

    parts = []
    parts.append(f"Goal: {goal_labels.get(goal, goal or 'N/A')}")
    parts.append(f"Risk: {risk_labels.get(risk, risk or 'N/A')}")
    parts.append(f"Holding: {period_labels.get(timeline, timeline or 'N/A')}")
    parts.append(f"Financing: {(financing or 'N/A').capitalize()}")
    parts.append(f"Property: {prop_labels.get(ready_offplan, ready_offplan or 'N/A')}")
    parts.append(f"Exit: {exit_labels.get(exit_pref, exit_pref or 'N/A')}")

    return " · ".join(parts)
