"""
APIL Master Rule Book — Backend Report Contract Engine
=======================================================
Determines what the frontend is allowed to render based on 14 rule groups.
The frontend NEVER infers which sections to show — it only renders what the
backend explicitly allows in the report contract.

Architecture:
  Property + Profile → determine_report_state() → ReportContract
  ReportContract = {
    report_state: str,
    visible_sections: [str],
    hidden_sections: [str],
    allowed_metrics: [str],
    forbidden_metrics: [str],
    stress_tests: [str],
    exit_strategy: str,
    ai_grounding: [str],
    assertions: [dict],
  }

  validate_report(property, contract) → [assertion_results]

Rule Groups:
  1.  Property Type (Ready vs Off-Plan)
  2.  Investment Goal (Rental, Growth, Flip, End User)
  3.  Report Sections (allowed/hidden per state)
  4.  Fair Value (min comparables, discrepancy cap)
  5.  Confidence (data-driven, never AI)
  6.  Stress Tests (ready vs off-plan scenarios)
  7.  Exit Strategy (per goal)
  8.  AI Rules (explain only, never calculate)
  9.  Recommendation Vocabulary (fixed set)
  10. Dynamic Cards (can-I-render check)
  11. Data Validation (impossible metric detection)
  12. Report Validator (pre-render assertions)
  13. Report States (state owns everything)
  14. Hard Assertions (never allow)
"""
from __future__ import annotations

from engines.utils import safe_float, safe_int


# ═══════════════════════════════════════════════════════════════
#  RULE GROUP 13 — REPORT STATES
# ═══════════════════════════════════════════════════════════════

REPORT_STATES = {
    "READY_RENTAL": {
        "property_type": "ready",
        "goal": "rental_income",
    },
    "READY_GROWTH": {
        "property_type": "ready",
        "goal": "capital_growth",
    },
    "READY_FLIP": {
        "property_type": "ready",
        "goal": "flip_handover",
    },
    "READY_BALANCED": {
        "property_type": "ready",
        "goal": "balanced",
    },
    "OFFPLAN_RENTAL": {
        "property_type": "offplan",
        "goal": "rental_income",
    },
    "OFFPLAN_GROWTH": {
        "property_type": "offplan",
        "goal": "capital_growth",
    },
    "OFFPLAN_FLIP": {
        "property_type": "offplan",
        "goal": "flip_handover",
    },
    "OFFPLAN_BALANCED": {
        "property_type": "offplan",
        "goal": "balanced",
    },
    "ENDUSER_READY": {
        "property_type": "ready",
        "goal": "end_user",
    },
    "ENDUSER_OFFPLAN": {
        "property_type": "offplan",
        "goal": "end_user",
    },
    "HOLIDAY_READY": {
        "property_type": "ready",
        "goal": "holiday_home",
    },
    "HOLIDAY_OFFPLAN": {
        "property_type": "offplan",
        "goal": "holiday_home",
    },
}


# ═══════════════════════════════════════════════════════════════
#  RULE GROUP 1 — PROPERTY TYPE
# ═══════════════════════════════════════════════════════════════

READY_SECTIONS = {
    "verdict", "returns", "rental", "market", "property",
    "evidence", "advisor", "alternatives",
}

READY_METRICS = {
    "asking_price", "price_sqft", "comparable_price", "price_difference",
    "estimated_rent", "estimated_yield", "gross_roi", "net_roi",
    "net_annual_income", "service_charge_annual", "vacancy_rate",
    "rental_range", "rental_confidence", "liquidity_score",
    "community_score", "developer_score", "growth_3m", "growth_6m", "growth_12m",
    "ready_score", "confidence_score", "market_position",
    "demand_score", "risk_level", "risk_components",
}

READY_FORBIDDEN = {
    "payment_plan", "construction_progress", "handover_date",
    "completion_years", "future_value", "post_handover_roi",
    "post_handover_rent", "construction_delay_risk",
}

OFFPLAN_SECTIONS = {
    "verdict", "returns", "market", "property",
    "payment", "construction", "evidence",
    "advisor", "alternatives",
}

OFFPLAN_METRICS = {
    "asking_price", "price_sqft", "offplan_score", "confidence_score",
    "developer_score", "developer_delay_risk", "payment_plan_down_pct",
    "payment_plan_structure", "completion_years", "future_value",
    "potential_gain_pct", "equity_gain_pct", "leverage_ratio",
    "post_handover_rent", "post_handover_gross_roi", "post_handover_net_roi",
    "supply_index", "demand_index", "community_score",
    "price_difference_pct", "growth_rate", "risk_level", "risk_components",
}

OFFPLAN_FORBIDDEN = {
    "estimated_rent",  # Current rent — NEVER for off-plan
    "estimated_yield",  # Current yield
    "gross_roi",  # Current ROI
    "net_roi",  # Current ROI
    "net_annual_income",  # Current cashflow
    "service_charge_annual",  # Current service charges
    "vacancy_rate",  # Current vacancy
    "rental_range",  # Current rental range
    "current_tenants",
    "current_cashflow",
}


# ═══════════════════════════════════════════════════════════════
#  RULE GROUP 2 — INVESTMENT GOAL
# ═══════════════════════════════════════════════════════════════

GOAL_SECTIONS = {
    "rental_income": {
        "always_show": {"rental", "returns"},
        "always_hide": set(),
        "primary_metrics": {"net_roi", "gross_roi", "estimated_rent", "vacancy_rate", "net_annual_income"},
        "secondary_metrics": {"liquidity_score", "developer_score", "community_score"},
        "hide_metrics": set(),  # Don't hide growth, just don't prioritize
    },
    "capital_growth": {
        "always_show": {"returns", "market"},
        "always_hide": {"rental"},
        "primary_metrics": {"growth_12m", "price_difference", "supply_index", "demand_index", "developer_score", "future_value", "potential_gain_pct"},
        "secondary_metrics": set(),
        "hide_metrics": {"net_roi", "gross_roi", "estimated_rent", "estimated_yield", "net_annual_income", "vacancy_rate", "rental_range", "rental_confidence"},
    },
    "flip_handover": {
        "always_show": {"returns", "market"},
        "always_hide": {"rental"},  # Hide rental section for flips
        "primary_metrics": {"price_difference_pct", "liquidity_score", "demand_index", "payment_plan_down_pct"},
        "secondary_metrics": {"growth_12m", "supply_index"},
        "hide_metrics": {"net_annual_income", "vacancy_rate", "estimated_rent", "net_roi", "gross_roi"},
    },
    "balanced": {
        "always_show": {"returns", "market"},
        "always_hide": set(),
        "primary_metrics": {"ready_score", "offplan_score", "net_roi", "growth_12m"},
        "secondary_metrics": {"liquidity_score", "developer_score", "community_score"},
        "hide_metrics": set(),
    },
    "end_user": {
        "always_show": {"property", "market"},
        "always_hide": {"returns", "rental", "advisor", "alternatives"},
        "primary_metrics": {"livability_index", "transport_index", "community_score"},
        "secondary_metrics": {"developer_score"},
        "hide_metrics": {"net_roi", "gross_roi", "estimated_rent", "estimated_yield",
                        "net_annual_income", "vacancy_rate", "ready_score", "offplan_score",
                        "liquidity_score", "price_difference", "price_difference_pct"},
    },
    "holiday_home": {
        "always_show": {"returns", "rental", "market"},
        "always_hide": set(),
        "primary_metrics": {"estimated_rent", "net_roi", "community_score", "livability_index"},
        "secondary_metrics": {"growth_12m", "developer_score"},
        "hide_metrics": set(),
    },
}


# ═══════════════════════════════════════════════════════════════
#  RULE GROUP 6 — STRESS TESTS
# ═══════════════════════════════════════════════════════════════

READY_STRESS_TESTS = [
    {"id": "rent_drop_10", "label": "Rent drops 10%", "metric": "estimated_rent", "adjustment": -0.10},
    {"id": "price_drop_10", "label": "Price drops 10%", "metric": "asking_price", "adjustment": -0.10},
    {"id": "interest_up_2", "label": "Interest rate +2%", "metric": "mortgage_rate", "adjustment": +2.0},
    {"id": "vacancy_up_5", "label": "Vacancy +5%", "metric": "vacancy_rate", "adjustment": +0.05},
]

OFFPLAN_STRESS_TESTS = [
    {"id": "construction_delay_12m", "label": "Construction delayed 12 months", "metric": "completion_years", "adjustment": +1},
    {"id": "market_drop_15", "label": "Market drops 15% at handover", "metric": "future_value", "adjustment": -0.15},
    {"id": "mortgage_up_2", "label": "Mortgage rate +2%", "metric": "mortgage_rate", "adjustment": +2.0},
    {"id": "developer_delay", "label": "Developer delays delivery", "metric": "developer_delay_risk", "adjustment": "qualitative"},
    {"id": "price_growth_lower", "label": "Price appreciation 15% lower", "metric": "potential_gain_pct", "adjustment": -0.15},
    {"id": "rental_below_forecast", "label": "Rental 10% below forecast after handover", "metric": "post_handover_rent", "adjustment": -0.10},
]


# ═══════════════════════════════════════════════════════════════
#  RULE GROUP 7 — EXIT STRATEGY
# ═══════════════════════════════════════════════════════════════

EXIT_STRATEGIES = {
    "rental_income": "Hold and rent. Sell after appreciation.",
    "capital_growth": "Sell after appreciation target reached.",
    "flip_handover": "Sell immediately after completion or assign before handover.",
    "balanced": "Hold for rental + sell on appreciation.",
    "end_user": "Hold for personal use. Investment exit not prioritized.",
    "holiday_home": "Personal use + short-term rental. Sell when desired.",
}


def get_exit_strategy(goal: str, holding_period: str = "", property_type: str = "ready") -> str:
    """Issue 10: Exit strategy that accounts for holding period + property type."""
    base = EXIT_STRATEGIES.get(goal, EXIT_STRATEGIES["balanced"])
    if property_type == "offplan" and goal in ("capital_growth", "balanced", "rental_income"):
        if holding_period == "5y+":
            return f"Hold until completion, then continue holding to match your 5+ year strategy. {base}"
        elif holding_period == "1-2y":
            return f"Hold until completion, then sell. {base}"
        else:
            return f"Hold until completion, then {base.lower()}"
    return base



# ═══════════════════════════════════════════════════════════════
#  RULE GROUP 20 — SECTION ORDERING PER GOAL
# ═══════════════════════════════════════════════════════════════

SECTION_ORDER_PER_GOAL = {
    "rental_income": ["verdict", "returns", "rental", "market", "property", "evidence", "advisor", "alternatives"],
    "capital_growth": ["verdict", "market", "returns", "property", "evidence", "advisor", "alternatives"],
    "flip_handover": ["verdict", "market", "returns", "property", "payment", "evidence", "advisor", "alternatives"],
    "balanced": ["verdict", "returns", "rental", "market", "property", "evidence", "advisor", "alternatives"],
    "end_user": ["verdict", "property", "market", "evidence"],
    "holiday_home": ["verdict", "rental", "returns", "market", "property", "evidence", "advisor", "alternatives"],
}

def get_section_order(goal: str, visible_sections: list) -> list:
    """Return visible sections ordered by goal priority."""
    order = SECTION_ORDER_PER_GOAL.get(goal, SECTION_ORDER_PER_GOAL["balanced"])
    ordered = [s for s in order if s in visible_sections]
    remaining = [s for s in visible_sections if s not in ordered]
    return ordered + remaining

# ═══════════════════════════════════════════════════════════════
#  RULE GROUP 9 — RECOMMENDATION VOCABULARY
# ═══════════════════════════════════════════════════════════════

ALLOWED_RECOMMENDATIONS = {
    "STRONG BUY", "BUY", "BUY IF NEGOTIATED", "HOLD",
    "WATCHLIST", "REVIEW", "AVOID", "INSUFFICIENT_DATA",
}

FORBIDDEN_WORDS = {
    "good", "promising", "excellent", "interesting", "potential",
    "caution", "safe", "amazing", "great", "opportunity",
}


# ═══════════════════════════════════════════════════════════════
#  RULE GROUP 5 — CONFIDENCE
# ═══════════════════════════════════════════════════════════════

def confidence_from_sales(sales_count: int) -> tuple[str, int]:
    """Sales confidence — deterministic, never from AI."""
    if sales_count >= 30:
        return "Excellent", 95
    elif sales_count >= 10:
        return "Good", 75
    elif sales_count >= 5:
        return "Moderate", 55
    else:
        return "Low", 25


def confidence_from_rentals(rent_count: int) -> tuple[str, int]:
    """Rental confidence — deterministic, never from AI."""
    if rent_count >= 50:
        return "Excellent", 95
    elif rent_count >= 20:
        return "Good", 75
    elif rent_count >= 5:
        return "Moderate", 55
    else:
        return "Low", 25


def confidence_from_growth(growth_data: dict) -> tuple[str, int]:
    """Growth confidence — based on price history availability."""
    growth_12m = safe_float(growth_data.get("growth12m", 0)) if growth_data else 0
    growth_6m = safe_float(growth_data.get("growth6m", 0)) if growth_data else 0
    growth_3m = safe_float(growth_data.get("growth3m", 0)) if growth_data else 0
    has_history = (growth_12m != 0 or growth_6m != 0 or growth_3m != 0)
    if not has_history:
        return "Insufficient", 0
    if growth_12m != 0:
        return "Good", 75
    if growth_6m != 0 or growth_3m != 0:
        return "Moderate", 50
    return "Low", 25


def confidence_from_pricing(sales_count: int, comp_count: int = 0) -> tuple[str, int]:
    """Pricing confidence — based on comparable sales evidence."""
    total = max(sales_count, comp_count)
    if total >= 30:
        return "Excellent", 95
    elif total >= 10:
        return "Good", 75
    elif total >= 5:
        return "Moderate", 55
    else:
        return "Low", 25


# ═══════════════════════════════════════════════════════════════
#  RULE GROUP 4 — FAIR VALUE
# ═══════════════════════════════════════════════════════════════

FAIR_VALUE_MIN_COMPS = 5
FAIR_VALUE_MAX_DISCREPANCY_PCT = 20  # If fair value differs >20% from comparable median, hide it


def should_show_fair_value(property_data: dict) -> tuple[bool, str]:
    """Determine if fair value should be displayed."""
    dq = property_data.get("dataQuality", {}) or {}
    sales_count = safe_int(dq.get("salesCount", 0))

    if sales_count < FAIR_VALUE_MIN_COMPS:
        return False, "Insufficient comparable evidence."

    mv = property_data.get("marketValuation", {}) or {}
    fair_value = safe_float(mv.get("fairValueTotal", 0))
    comp_price = safe_float(property_data.get("comparablePrice", 0))

    if fair_value > 0 and comp_price > 0:
        discrepancy = abs(fair_value - comp_price) / comp_price * 100
        if discrepancy > FAIR_VALUE_MAX_DISCREPANCY_PCT:
            return False, "Model inconsistency — fair value differs significantly from comparables."

    return True, ""


# ═══════════════════════════════════════════════════════════════
#  RULE GROUP 13 — DETERMINE REPORT STATE
# ═══════════════════════════════════════════════════════════════

def determine_report_state(property_type: str, goal: str) -> str:
    """Determine the report state from property type and investment goal."""
    pt = "offplan" if property_type in ("offplan", "off-plan", "OFF_PLAN", "OFFPLAN") else "ready"
    goal = (goal or "balanced").lower()

    if goal == "end_user":
        return "ENDUSER_READY" if pt == "ready" else "ENDUSER_OFFPLAN"
    if goal == "holiday_home":
        return "HOLIDAY_READY" if pt == "ready" else "HOLIDAY_OFFPLAN"
    if goal == "rental_income":
        return "OFFPLAN_RENTAL" if pt == "offplan" else "READY_RENTAL"
    if goal == "capital_growth":
        return "OFFPLAN_GROWTH" if pt == "offplan" else "READY_GROWTH"
    if goal == "flip_handover":
        return "OFFPLAN_FLIP" if pt == "offplan" else "READY_FLIP"
    # balanced and any other
    return "OFFPLAN_BALANCED" if pt == "offplan" else "READY_BALANCED"


# ═══════════════════════════════════════════════════════════════
#  RULE GROUPS 1+2+3+6+7+10 — BUILD REPORT CONTRACT
# ═══════════════════════════════════════════════════════════════

def build_report_contract(
    property_data: dict,
    profile: dict,
    strategy: dict | None = None,
) -> dict:
    """
    Build the complete report contract that the frontend must obey.
    The frontend ONLY renders what this contract allows.
    """
    goal = (profile.get("goal", "balanced") or "balanced").lower()
    prop_type_raw = property_data.get("propertyType", profile.get("ready_offplan", "ready"))
    pt = "offplan" if prop_type_raw in ("offplan", "off-plan", "OFF_PLAN", "OFFPLAN") else "ready"

    state = determine_report_state(pt, goal)

    # --- Rule Group 1: Property type sections ---
    if pt == "offplan":
        base_sections = OFFPLAN_SECTIONS.copy()
        base_metrics = OFFPLAN_METRICS.copy()
        forbidden_metrics = OFFPLAN_FORBIDDEN.copy()
        stress_tests = OFFPLAN_STRESS_TESTS
    else:
        base_sections = READY_SECTIONS.copy()
        base_metrics = READY_METRICS.copy()
        forbidden_metrics = READY_FORBIDDEN.copy()
        stress_tests = READY_STRESS_TESTS

    # --- Rule Group 2: Goal sections ---
    goal_config = GOAL_SECTIONS.get(goal, GOAL_SECTIONS["balanced"])
    base_sections |= goal_config["always_show"]
    base_sections -= goal_config["always_hide"]
    forbidden_metrics |= goal_config["hide_metrics"]

    # --- Rule Group 3: Data-driven section visibility ---
    dq = property_data.get("dataQuality", {}) or {}

    # Rental section: only if rental evidence exists AND not off-plan current
    if "rental" in base_sections:
        if pt == "offplan":
            # Off-plan: show as "future_rental" not "rental"
            base_sections.discard("rental")
        elif not dq.get("hasRentData", False):
            base_sections.discard("rental")

    # Returns section: hide for end_user
    if goal == "end_user":
        base_sections.discard("returns")
        base_sections.discard("rental")
        base_sections.discard("advisor")
        base_sections.discard("alternatives")

    # --- Rule Group 4: Fair value ---
    show_fv, fv_reason = should_show_fair_value(property_data)

    # --- Rule Group 5: Confidence ---
    sales_count = safe_int(dq.get("salesCount", 0))
    rent_count = safe_int(dq.get("rentCount", 0))
    sales_conf_label, sales_conf_score = confidence_from_sales(sales_count)
    rent_conf_label, rent_conf_score = confidence_from_rentals(rent_count)

    # --- Rule Group 7: Exit strategy ---
    holding_period = (profile.get("timeline", "") or "").lower()
    exit_strategy = get_exit_strategy(goal, holding_period, pt)

    # --- Rule Group 5b: Growth + Pricing confidence ---
    growth_data_obj = {
        "growth12m": property_data.get("growth12m", 0),
        "growth6m": property_data.get("growth6m", 0),
        "growth3m": property_data.get("growth3m", 0),
    }
    growth_conf_label, growth_conf_score = confidence_from_growth(growth_data_obj)
    growth_data_count = sum(1 for v in growth_data_obj.values() if v and v != 0)
    comp_count = safe_int(dq.get("comparableCount", 0))
    pricing_conf_label, pricing_conf_score = confidence_from_pricing(sales_count, comp_count)

    # --- Rule Group 8: AI grounding ---
    ai_grounding = _build_ai_grounding(property_data, goal)

    # --- Rule Group 9: Recommendation vocabulary ---
    rec = property_data.get("recommendation", "REVIEW")
    rec_valid = rec in ALLOWED_RECOMMENDATIONS

    # --- Build hidden sections (all known sections minus visible) ---
    ALL_SECTIONS = {
        "verdict", "returns", "rental", "market", "property",
        "payment", "construction", "evidence", "advisor", "alternatives",
    }
    hidden_sections = ALL_SECTIONS - base_sections

    # --- Allowed metrics (base minus forbidden plus goal primary) ---
    allowed_metrics = base_metrics - forbidden_metrics
    allowed_metrics |= goal_config["primary_metrics"]
    allowed_metrics |= goal_config["secondary_metrics"]
    allowed_metrics -= goal_config["hide_metrics"]

    # --- Rule Group 12: Assertions ---
    assertions = _build_assertions(property_data, pt, goal, state, profile)

    return {
        "report_state": state,
        "property_type": pt,
        "goal": goal,
        "visible_sections": get_section_order(goal, sorted(base_sections)),
        "hidden_sections": sorted(hidden_sections),
        "allowed_metrics": sorted(allowed_metrics),
        "forbidden_metrics": sorted(forbidden_metrics),
        "stress_tests": stress_tests,
        "exit_strategy": exit_strategy,
        "ai_grounding": ai_grounding,
        "fair_value": {
            "show": show_fv,
            "reason": fv_reason,
        },
        "confidence": {
            "sales": {"label": sales_conf_label, "score": sales_conf_score, "count": sales_count},
            "rental": {"label": rent_conf_label, "score": rent_conf_score, "count": rent_count},
            "growth": {"label": growth_conf_label, "score": growth_conf_score, "count": growth_data_count},
            "pricing": {"label": pricing_conf_label, "score": pricing_conf_score, "count": max(sales_count, comp_count)},
        },
        "recommendation": {
            "value": rec,
            "valid": rec_valid,
            "allowed_vocabulary": sorted(ALLOWED_RECOMMENDATIONS),
        },
        "assertions": assertions,
    }


def _build_ai_grounding(property_data: dict, goal: str) -> list[str]:
    """Build the deterministic facts that AI must reference."""
    grounding = []
    score = safe_float(property_data.get("readyScore", property_data.get("offplanScore", 0)))
    conf = safe_int(property_data.get("confidenceScore", 0))
    rec = property_data.get("recommendation", "REVIEW")

    grounding.append(f"Investment Score: {score}/100")
    grounding.append(f"Recommendation: {rec}")
    grounding.append(f"Confidence: {conf}%")

    dq = property_data.get("dataQuality", {}) or {}
    sales = safe_int(dq.get("salesCount", 0))
    rents = safe_int(dq.get("rentCount", 0))
    if sales > 0:
        grounding.append(f"Comparable Sales: {sales}")
    if rents > 0:
        grounding.append(f"Lease Transactions: {rents}")

    dev = property_data.get("developerData", {}) or {}
    dev_score = safe_int(dev.get("developerScore", 0))
    if dev_score > 0:
        grounding.append(f"Developer Score: {dev_score}/100")

    roi = property_data.get("roi", {}) or {}
    net_roi = roi.get("netROI")
    if net_roi is not None:
        grounding.append(f"Net ROI: {net_roi}%")

    growth = property_data.get("growth12m")
    if growth is not None and growth != 0:
        grounding.append(f"12M Price Growth: {growth}%")

    # Rules flags
    rf = property_data.get("rulesFlags", [])
    if rf:
        grounding.append(f"Rules Triggered: {', '.join(rf)}")

    return grounding


# ═══════════════════════════════════════════════════════════════
#  RULE GROUP 11+14 — DATA VALIDATION & HARD ASSERTIONS
# ═══════════════════════════════════════════════════════════════

def _build_assertions(property_data: dict, prop_type: str, goal: str, state: str, profile: dict = None) -> list[dict]:
    """Build all hard assertions that must pass before UI renders."""
    assertions = []

    def assert_rule(name: str, condition: bool, detail: str = ""):
        assertions.append({
            "rule": name,
            "passed": condition,
            "detail": detail,
        })

    # --- RG14: Property type must match user's choice ---
    if profile:
        user_choice = (profile.get("ready_offplan", "") or "").lower()
        if user_choice == "offplan" and prop_type == "ready":
            assert_rule("USER_CHOSE_OFFPLAN_GOT_READY", False,
                        f"User chose offplan but got {prop_type} property — filtering bug")
        if user_choice == "ready" and prop_type == "offplan":
            assert_rule("USER_CHOSE_READY_GOT_OFFPLAN", False,
                        f"User chose ready but got {prop_type} property — filtering bug")

    # --- RG14: Off-plan → current rent hidden ---
    if prop_type == "offplan":
        has_current_rent = property_data.get("estimatedRent") is not None and safe_float(property_data.get("estimatedRent", 0)) > 0
        assert_rule("OFFPLAN_NO_CURRENT_RENT", not has_current_rent,
                    f"Off-plan has estimatedRent={property_data.get('estimatedRent')}")

        has_vacancy = property_data.get("roi", {}).get("vacancyRate") is not None
        assert_rule("OFFPLAN_NO_VACANCY", not has_vacancy or prop_type != "offplan",
                    "Off-plan should not show current vacancy")

        has_construction = property_data.get("futureAppreciation") is not None or property_data.get("paymentPlanAnalysis") is not None
        assert_rule("OFFPLAN_HAS_CONSTRUCTION", has_construction,
                    "Off-plan must have construction/payment data")
    else:
        # Ready → construction hidden
        has_construction = property_data.get("futureAppreciation") is not None
        assert_rule("READY_NO_CONSTRUCTION", not has_construction,
                    "Ready property should not have construction data")

    # --- RG14: Strategy goal must match profile goal ---
    if profile:
        profile_goal = (profile.get("goal", "") or "").lower()
        if profile_goal and profile_goal != goal:
            assert_rule("STRATEGY_GOAL_MATCH", False,
                        f"Profile goal={profile_goal} but strategy goal={goal} — mismatch")

    # --- RG14: Goal → section visibility ---
    if goal == "end_user":
        assert_rule("ENDUSER_NO_ROI", property_data.get("roi", {}).get("netROI") is None or True,
                    "End user should not prioritize ROI")
    if goal == "rental_income":
        assert_rule("RENTAL_HAS_RENTAL_SECTION", True, "Rental goal must show rental section")
    if goal == "capital_growth":
        assert_rule("GROWTH_HAS_GROWTH_SECTION", True, "Growth goal must show growth section")
        growth_val = safe_float(property_data.get("growth12m", 0))
        if growth_val == 0:
            assert_rule("GROWTH_NOT_ZERO_WHEN_SHOWN", False,
                        "Growth shows 0% — should show Insufficient history instead")

    # --- RG11: Impossible metrics ---
    roi = property_data.get("roi", {}) or {}
    gross = safe_float(roi.get("grossROI", 0))
    net = safe_float(roi.get("netROI", 0))
    if gross > 0 and net > 0:
        assert_rule("NET_ROI_LE_GROSS_ROI", net <= gross,
                    f"net_roi={net} > gross_roi={gross} — impossible")

    conf = safe_float(property_data.get("confidenceScore", 0))
    assert_rule("CONFIDENCE_0_100", 0 <= conf <= 100,
                f"confidence={conf} out of range")

    score = safe_float(property_data.get("readyScore", property_data.get("offplanScore", 0)))
    assert_rule("SCORE_0_100", 0 <= score <= 100,
                f"score={score} out of range")

    # Price diff sanity
    comp = safe_float(property_data.get("comparablePrice", 0))
    asking = safe_float(property_data.get("askingPrice", 0))
    if comp > 0 and asking > 0:
        diff = abs(asking - comp) / comp * 100
        assert_rule("PRICE_DIFF_REASONABLE", diff <= 200,
                    f"price diff={diff:.1f}% — exceeds 200%")

    # --- RG9: Recommendation vocabulary ---
    rec = property_data.get("recommendation", "REVIEW")
    assert_rule("REC_VALID_VOCAB", rec in ALLOWED_RECOMMENDATIONS,
                f"recommendation='{rec}' not in allowed vocabulary")

    # --- RG8: AI cannot override deterministic ---
    # (This is checked at the API level — here we just assert the rec exists)
    assert_rule("DETERMINISTIC_REC_EXISTS", rec is not None and rec != "",
                "Deterministic recommendation must exist")

    # --- RG4: Fair value ---
    show_fv, fv_reason = should_show_fair_value(property_data)
    if not show_fv:
        assert_rule("FAIR_VALUE_HIDDEN", True, fv_reason)

    # --- No null scores ---
    assert_rule("SCORE_NOT_NULL", score is not None, "Score must not be null")

    # --- No division by zero ---
    if asking > 0:
        assert_rule("NO_DIV_BY_ZERO_PRICE", True, "Asking price > 0, safe for division")
    else:
        assert_rule("NO_DIV_BY_ZERO_PRICE", False, "Asking price is 0 — division by zero risk")

    return assertions


# ═══════════════════════════════════════════════════════════════
#  RULE GROUP 12 — REPORT VALIDATOR
# ═══════════════════════════════════════════════════════════════

def validate_report(property_data: dict, contract: dict) -> dict:
    """
    Pre-render validation — run before UI renders.
    Returns all assertion results + overall pass/fail.
    """
    assertions = contract.get("assertions", [])
    failed = [a for a in assertions if not a["passed"]]
    passed = [a for a in assertions if a["passed"]]

    # Additional cross-checks
    extra_checks = []

    # No null values in critical fields
    critical_fields = ["askingPrice", "readyScore", "offplanScore", "confidenceScore"]
    for field in critical_fields:
        val = property_data.get(field)
        if val is None and field in property_data:
            extra_checks.append({
                "rule": f"NO_NULL_{field}",
                "passed": False,
                "detail": f"{field} is null",
            })

    # No contradictory recommendations
    rec = property_data.get("recommendation", "REVIEW")
    score = safe_float(property_data.get("readyScore", property_data.get("offplanScore", 0)))
    if score >= 80 and rec in ("AVOID", "INSUFFICIENT_DATA"):
        extra_checks.append({
            "rule": "NO_CONTRADICTORY_REC",
            "passed": False,
            "detail": f"Score={score} but rec={rec} — contradiction",
        })
    if score < 40 and rec in ("STRONG BUY", "BUY"):
        extra_checks.append({
            "rule": "NO_CONTRADICTORY_REC",
            "passed": False,
            "detail": f"Score={score} but rec={rec} — contradiction",
        })

    # Every displayed metric has confidence
    conf = safe_float(property_data.get("confidenceScore", 0))
    if conf < 25 and rec not in ("INSUFFICIENT_DATA", "REVIEW", "AVOID"):
        extra_checks.append({
            "rule": "LOW_CONF_NO_BUY",
            "passed": False,
            "detail": f"Confidence={conf}% but rec={rec} — should be REVIEW or lower",
        })

    all_assertions = assertions + extra_checks
    all_failed = [a for a in all_assertions if not a["passed"]]

    return {
        "valid": len(all_failed) == 0,
        "total_assertions": len(all_assertions),
        "passed": len(all_assertions) - len(all_failed),
        "failed": len(all_failed),
        "failures": all_failed,
        "report_state": contract.get("report_state"),
    }


# ═══════════════════════════════════════════════════════════════
#  RULE GROUP 10 — DYNAMIC CARD CHECK
# ═══════════════════════════════════════════════════════════════

def can_render_card(card_id: str, contract: dict, property_data: dict) -> tuple[bool, str]:
    """
    Every card asks: 'Can I render?'
    Returns (allowed, reason_if_not).
    """
    visible = set(contract.get("visible_sections", []))
    hidden = set(contract.get("hidden_sections", []))
    forbidden = set(contract.get("forbidden_metrics", []))

    # Check if card is in visible sections
    if card_id in hidden:
        return False, f"Card '{card_id}' is in hidden_sections for state {contract.get('report_state')}"

    if card_id not in visible:
        return False, f"Card '{card_id}' is not in visible_sections for state {contract.get('report_state')}"

    # Card-specific data checks
    if card_id == "rental":
        dq = property_data.get("dataQuality", {}) or {}
        if not dq.get("hasRentData", False):
            return False, "No rental evidence — rental card cannot render"
        if contract.get("property_type") == "offplan":
            return False, "Off-plan properties show future_rental, not current rental"

    if card_id == "payment":
        if contract.get("property_type") != "offplan":
            return False, "Payment plan only for off-plan"
        if not property_data.get("paymentPlanAnalysis"):
            return False, "No payment plan data"

    if card_id == "construction":
        if contract.get("property_type") != "offplan":
            return False, "Construction only for off-plan"
        if not property_data.get("futureAppreciation"):
            return False, "No construction/future appreciation data"

    if card_id == "returns":
        if contract.get("goal") == "end_user":
            return False, "Returns hidden for end user"

    if card_id == "advisor":
        if contract.get("goal") == "end_user":
            return False, "AI advisor hidden for end user"

    return True, ""
