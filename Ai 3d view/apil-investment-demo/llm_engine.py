"""
APIL LLM Advisor Engine
Uses Ollama (kimi-k2.6:cloud) as an ADVISOR ONLY — never for scoring or rent estimation.

The LLM receives already-computed deterministic metrics from the Investment Engine
and Rules Engine, then provides:
  1. validate_listing — LLM checks if listing data is realistic (advisory only)
  2. explain_score — LLM explains why a property received its score
  3. detect_contradictions — LLM flags metrics that contradict each other
  4. investor_recommendation — LLM advises whether an investor should buy
  5. compare_alternatives — LLM compares top properties for an investor
  6. negotiation_strategy — LLM suggests negotiation approach
  7. exit_strategy — LLM suggests exit timeline
  8. generate_report — LLM generates full advisory report section

The LLM NEVER:
  - Calculates investment scores
  - Estimates rent
  - Determines confidence levels
  - Overrides deterministic recommendations

All functions fall back to template-based text if LLM is unavailable.
"""
from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from typing import Any

# Qwen2.5-VL-7B API (OpenAI-compatible, served via FastAPI)
LLM_URL = "http://localhost:8001/v1/chat/completions"
LLM_MODEL = "Qwen2.5-VL-7B-Instruct"
TIMEOUT = 60  # seconds — Qwen 7B can be slower on CPU offload


def _call_llm(system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str | None:
    """Call Qwen LLM API and return the response text, or None on failure."""
    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    req = urllib.request.Request(
        LLM_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        print(f"  [LLM] Error calling Qwen: {e}")
        return None


def _extract_json(text: str) -> dict | None:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    if not text:
        return None
    # Try to find JSON in code blocks
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try direct parse
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Try to find first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ─── 1. LISTING VALIDATION ───

VALIDATE_SYSTEM = """You are a Dubai real estate data analyst. Your job is to validate property listings by checking if the price and specifications are realistic.

You have deep knowledge of Dubai property markets:
- Studio apartments: AED 400K-1.5M depending on area
- 1BR apartments: AED 600K-2.5M
- 2BR apartments: AED 1M-5M
- 3BR apartments: AED 2M-10M
- Villas: AED 3M-30M+ depending on area and size
- Penthouse: AED 5M-50M+
- Price/sqft in Dubai: AED 800-3,500 for most areas

Respond ONLY with a JSON object, no other text."""

def validate_listing(
    title: str,
    price: float,
    size_sqft: float,
    bed_type: str,
    category: str,
    area: str,
    community_median_price: float | None,
    community_median_price_sqft: float | None,
) -> dict:
    """
    Use LLM to validate if a listing is realistic.
    Returns: {valid: bool, reason: str, confidence: int}
    """
    user_prompt = f"""Validate this Dubai property listing:

Title: {title}
Price: AED {price:,.0f}
Size: {size_sqft:,.0f} sqft
Bedrooms: {bed_type}
Type: {category}
Area: {area}
Community median price: {('AED ' + format(community_median_price, ',.0f')) if community_median_price else 'N/A'}
Community median price/sqft: {('AED ' + format(community_median_price_sqft, ',.0f')) if community_median_price_sqft else 'N/A'}
Price/sqft: {('AED ' + format(price / size_sqft, ',.0f')) if size_sqft > 0 else 'N/A'}

Is this listing realistic? Check:
1. Is the price reasonable for this property type and area?
2. Is the price/sqft within normal Dubai ranges (AED 200-10,000)?
3. If community median is available, is the price within 70% of median?
4. Could this be a data error (e.g., price in thousands instead of full amount)?

Respond as JSON:
```json
{{
  "valid": true/false,
  "reason": "brief explanation",
  "confidence": 0-100
}}
```"""

    response = _call_llm(VALIDATE_SYSTEM, user_prompt, max_tokens=500)
    result = _extract_json(response) if response else None

    if result and "valid" in result:
        return {
            "valid": bool(result["valid"]),
            "reason": result.get("reason", ""),
            "confidence": int(result.get("confidence", 50)),
            "source": "llm",
        }

    # Fallback: deterministic validation
    price_sqft = price / size_sqft if size_sqft > 0 else 0
    if price_sqft < 200 or price_sqft > 10000:
        return {"valid": False, "reason": f"Price/sqft AED {price_sqft:.0f} is outside realistic range", "confidence": 90, "source": "deterministic"}
    if community_median_price and community_median_price > 0:
        if price < community_median_price * 0.30:
            return {"valid": False, "reason": f"Price is {((community_median_price - price) / community_median_price * 100):.0f}% below community median — likely data error", "confidence": 85, "source": "deterministic"}
    return {"valid": True, "reason": "Price within acceptable range", "confidence": 70, "source": "deterministic"}


# ─── 2. EXPLAIN SCORE ───

EXPLAIN_SYSTEM = """You are a professional Dubai real estate investment advisor. Your job is to explain why a property received its investment score.

You receive ALREADY COMPUTED metrics from a deterministic engine. You do NOT calculate scores. You explain them.

Write in a professional, specific tone. Reference the actual numbers. Do not use generic statements.

Respond ONLY with a JSON object, no other text."""

def explain_score(property_data: dict, investor_profile: dict | None = None) -> dict:
    """
    LLM explains why a property received its deterministic score.
    Returns: {explanation, key_strengths, key_risks, data_quality_note}
    """
    is_offplan = "offplanScore" in property_data
    price = property_data.get("askingPrice", 0)
    area = property_data.get("area", "Unknown")
    bed = property_data.get("bedType", "?")
    size = property_data.get("sizeSqft") or property_data.get("areaSqft", 0)
    score = property_data.get("offplanScore") or property_data.get("readyScore", 0)
    rec = property_data.get("recommendation", "N/A")
    conf = property_data.get("confidenceScore", 50)

    if is_offplan:
        fv = property_data.get("fairValue", {})
        po = property_data.get("priceOpportunity", {})
        fa = property_data.get("futureAppreciation", {})
        roi = property_data.get("postHandoverROI", {})
        dev = property_data.get("developerData", {})
        comm = property_data.get("communityData", {})
        liq = property_data.get("liquidity", {})
        risk = property_data.get("risk", {})
        metrics = f"""Computed Metrics (from Investment Engine):
- Investment Score: {score}/100
- Recommendation: {rec}
- Confidence: {conf}%
- Price: AED {price:,.0f}
- Fair Market Value: AED {fv.get('fairValue', 0):,.0f}
- Price vs Market: {po.get('priceDifferencePct', 'N/A')}%
- Future Value (est): AED {fa.get('futureValue', 0):,.0f}
- Potential Gain: {fa.get('potentialGainPct', 'N/A')}%
- Post-Handover Net ROI: {roi.get('netROI', 'N/A')}%
- Estimated Rent: {roi.get('estimatedRent', 'N/A')}
- Developer: {dev.get('developerName', 'N/A')} (score: {dev.get('developerScore', 'N/A')})
- Community Score: {comm.get('communityScore', 'N/A')}
- Liquidity Score: {liq.get('liquidityScore', 'N/A')}
- Risk Level: {risk.get('riskLevel', 'N/A')}
- Rule Flags: {property_data.get('ruleFlags', [])}"""
    else:
        roi = property_data.get("roi", {})
        liq = property_data.get("liquidity", {})
        risk = property_data.get("risk", {})
        comm_score = property_data.get("communityScore", "N/A")
        dev_score = property_data.get("developerScore", "N/A")
        proj_score = property_data.get("projectScore", "N/A")
        metrics = f"""Computed Metrics (from Investment Engine):
- Investment Score: {score}/100
- Recommendation: {rec}
- Confidence: {conf}%
- Price: AED {price:,.0f}
- Price/sqft: {('AED ' + format(price / size, ',.0f')) if size > 0 else 'N/A'}
- Comparable Price: {property_data.get('comparablePrice', 'N/A')}
- Price Difference: {property_data.get('priceDifference', 'N/A')}%
- Market Position: {property_data.get('marketPosition', 'N/A')}
- Annual Rent: {roi.get('annualRent', 'N/A')}
- Gross ROI: {roi.get('grossROI', 'N/A')}%
- Net ROI: {roi.get('netROI', 'N/A')}%
- Liquidity Score: {liq.get('liquidityScore', 'N/A')} ({liq.get('liquidityLabel', 'N/A')})
- Community Score: {comm_score}
- Developer Score: {dev_score}
- Project Score: {proj_score}
- Risk Level: {risk.get('riskLevel', 'N/A')}
- Growth 12m: {property_data.get('growth12m', 'N/A')}%
- Rule Flags: {property_data.get('ruleFlags', [])}"""

    profile_str = ""
    if investor_profile:
        profile_str = f"\nInvestor Goal: {investor_profile.get('goal', 'balanced')}\nRisk Tolerance: {investor_profile.get('risk', 'medium')}"

    user_prompt = f"""Explain this property's investment score to a client.

Property: {bed} {property_data.get('category', '')} in {area}
{metrics}{profile_str}

Explain:
1. Why did the engine give this score?
2. What are the key strengths driving the score up?
3. What are the key weaknesses pulling it down?
4. Are there any contradictions or data quality concerns?
5. What does the recommendation mean in plain English?

Do NOT recalculate the score. Explain the existing score.

Respond as JSON:
```json
{{
  "explanation": "2-3 sentence explanation of why this score was given",
  "key_strengths": ["specific strength 1", "specific strength 2"],
  "key_risks": ["specific risk 1", "specific risk 2"],
  "data_quality_note": "note about data completeness or reliability",
  "plain_english_verdict": "what the recommendation means for the investor"
}}
```"""

    response = _call_llm(EXPLAIN_SYSTEM, user_prompt, max_tokens=800)
    result = _extract_json(response) if response else None

    if result and "explanation" in result:
        return {
            "explanation": result.get("explanation", ""),
            "key_strengths": result.get("key_strengths", []),
            "key_risks": result.get("key_risks", []),
            "data_quality_note": result.get("data_quality_note", ""),
            "plain_english_verdict": result.get("plain_english_verdict", ""),
            "source": "llm",
        }

    # Fallback: use existing deterministic reasons
    reasons = property_data.get("reasons", [])
    lost_points = property_data.get("lostPoints", [])
    return {
        "explanation": ". ".join(reasons[:3]) if reasons else "Property meets baseline investment criteria",
        "key_strengths": reasons[:3],
        "key_risks": lost_points[:3],
        "data_quality_note": f"Confidence: {conf}%" + (" — low confidence, verify estimates" if conf < 50 else ""),
        "plain_english_verdict": rec,
        "source": "deterministic",
    }


# ─── 3. DETECT CONTRADICTIONS ───

CONTRADICT_SYSTEM = """You are a data quality analyst for a real estate investment platform. Your job is to detect contradictions in computed property metrics.

Examples of contradictions:
- High ROI but no rental data (ROI should be Unknown)
- Strong BUY recommendation but confidence below 40%
- Price marked as "Fair Market Value" but no comparable sales
- High liquidity score but very few transactions
- Low risk but unknown developer

Respond ONLY with a JSON object, no other text."""

def detect_contradictions(property_data: dict) -> dict:
    """
    LLM flags metrics that contradict each other.
    Returns: {contradictions: list, severity: str, recommendations: list}
    """
    is_offplan = "offplanScore" in property_data
    score = property_data.get("offplanScore") or property_data.get("readyScore", 0)
    rec = property_data.get("recommendation", "HOLD")
    conf = property_data.get("confidenceScore", 50)
    flags = property_data.get("ruleFlags", [])

    roi = property_data.get("roi", {}) if not is_offplan else property_data.get("postHandoverROI", {})
    has_rent = roi.get("hasRentData", False)
    net_roi = roi.get("netROI")
    liq = property_data.get("liquidity", {})
    risk = property_data.get("risk", {})

    user_prompt = f"""Check these computed metrics for contradictions:

- Investment Score: {score}/100
- Recommendation: {rec}
- Confidence: {conf}%
- Has Rental Data: {has_rent}
- Net ROI: {net_roi}
- Liquidity Score: {liq.get('liquidityScore', 'N/A')}
- Risk Level: {risk.get('riskLevel', 'N/A')}
- Rule Flags: {flags}
- Comparable Price: {property_data.get('comparablePrice', 'N/A') if not is_offplan else 'N/A (offplan)'}
- Market Position: {property_data.get('marketPosition', 'N/A') if not is_offplan else 'N/A (offplan)'}

Are there any contradictions? For example:
- Recommendation is BUY but confidence is low?
- ROI is shown but no rental data exists?
- Liquidity is high but transaction count is low?
- Risk is Low but developer is unknown?

Respond as JSON:
```json
{{
  "contradictions": ["contradiction 1", "contradiction 2"],
  "severity": "none" | "minor" | "major",
  "recommendations": ["what should be done about each contradiction"]
}}
```"""

    response = _call_llm(CONTRADICT_SYSTEM, user_prompt, max_tokens=600)
    result = _extract_json(response) if response else None

    if result and "contradictions" in result:
        return {
            "contradictions": result.get("contradictions", []),
            "severity": result.get("severity", "none"),
            "recommendations": result.get("recommendations", []),
            "source": "llm",
        }

    # Fallback: simple deterministic checks
    contradictions = []
    if rec in ("STRONG BUY", "BUY") and conf < 50:
        contradictions.append(f"Recommendation is {rec} but confidence is only {conf}%")
    if net_roi is not None and not has_rent:
        contradictions.append("ROI is shown but no rental data exists")
    if not contradictions:
        return {"contradictions": [], "severity": "none", "recommendations": [], "source": "deterministic"}
    return {"contradictions": contradictions, "severity": "major", "recommendations": ["Verify data before presenting to client"], "source": "deterministic"}


# ─── 4. INVESTOR RECOMMENDATION ───

INVESTOR_REC_SYSTEM = """You are a Dubai real estate investment advisor. An investor is considering a property. Your job is to advise whether it suits their profile.

You receive already-computed metrics. You do NOT recalculate. You reason about fit.

Be specific and honest. If the data is insufficient, say so. If the property doesn't match the investor's goal, say why.

Respond ONLY with a JSON object, no other text."""

def investor_recommendation(property_data: dict, investor_profile: dict) -> dict:
    """
    LLM advises whether an investor should buy this property.
    Returns: {advice, fit_score, reasoning, alternative_suggestion}
    """
    is_offplan = "offplanScore" in property_data
    score = property_data.get("offplanScore") or property_data.get("readyScore", 0)
    rec = property_data.get("recommendation", "HOLD")
    conf = property_data.get("confidenceScore", 50)
    price = property_data.get("askingPrice", 0)
    area = property_data.get("area", "Unknown")
    bed = property_data.get("bedType", "?")

    roi = property_data.get("roi", {}) if not is_offplan else property_data.get("postHandoverROI", {})
    net_roi = roi.get("netROI", "N/A")
    growth = property_data.get("growth12m", "N/A") if not is_offplan else property_data.get("futureAppreciation", {}).get("potentialGainPct", "N/A")
    liq = property_data.get("liquidity", {})
    risk = property_data.get("risk", {})

    user_prompt = f"""Advise this investor on whether to buy this property.

Investor Profile:
- Goal: {investor_profile.get('goal', 'balanced')}
- Budget: {investor_profile.get('budget', 'any')}
- Property Type: {investor_profile.get('property_type', 'any')}
- Bedrooms: {investor_profile.get('bedrooms', 'any')}
- Risk Tolerance: {investor_profile.get('risk', 'medium')}

Property: {bed} {property_data.get('category', '')} in {area}
- Price: AED {price:,.0f}
- Investment Score: {score}/100
- Recommendation: {rec}
- Confidence: {conf}%
- Net ROI: {net_roi}%
- Growth: {growth}%
- Liquidity: {liq.get('liquidityLabel', 'N/A')}
- Risk Level: {risk.get('riskLevel', 'N/A')}

Questions:
1. Does this property match the investor's goal?
2. Is the risk level acceptable for their tolerance?
3. Is the price within their budget?
4. What would you advise — buy, wait, or look for alternatives?
5. If not ideal, what type of property would be better?

Respond as JSON:
```json
{{
  "advice": "BUY" | "WAIT" | "LOOK_FOR_ALTERNATIVES" | "INSUFFICIENT_DATA",
  "fit_score": <0-100 how well it matches investor profile>,
  "reasoning": "2-3 sentences explaining the advice",
  "alternative_suggestion": "what to look for instead, if not ideal"
}}
```"""

    response = _call_llm(INVESTOR_REC_SYSTEM, user_prompt, max_tokens=600)
    result = _extract_json(response) if response else None

    if result and "advice" in result:
        return {
            "advice": result.get("advice", "WAIT"),
            "fit_score": int(result.get("fit_score", 50)),
            "reasoning": result.get("reasoning", ""),
            "alternative_suggestion": result.get("alternative_suggestion", ""),
            "source": "llm",
        }

    # Fallback: deterministic
    if conf < 40:
        advice = "INSUFFICIENT_DATA"
    elif rec in ("STRONG BUY", "BUY") and score >= 70:
        advice = "BUY"
    elif rec == "HOLD":
        advice = "WAIT"
    else:
        advice = "LOOK_FOR_ALTERNATIVES"
    return {"advice": advice, "fit_score": score, "reasoning": f"Based on score {score} and recommendation {rec}", "alternative_suggestion": "", "source": "deterministic"}


# ─── 5. COMPARE ALTERNATIVES ───

COMPARE_SYSTEM = """You are a Dubai real estate investment advisor. Compare multiple properties for an investor and explain the trade-offs.

You receive already-computed scores. You do NOT recalculate. You compare and explain.

Be specific about trade-offs. Help the investor understand why one property might be better than another for their specific goals.

Respond ONLY with a JSON object, no other text."""

def compare_alternatives(properties: list[dict], investor_profile: dict) -> dict:
    """
    LLM compares top properties for an investor.
    Returns: {comparison, ranking_reasoning, best_fit_id, trade-offs}
    """
    summaries = []
    for p in properties[:10]:
        is_offplan = "offplanScore" in p
        score = p.get("offplanScore") or p.get("readyScore", 0)
        rec = p.get("recommendation", "HOLD")
        conf = p.get("confidenceScore", 50)
        price = p.get("askingPrice", 0)
        area = p.get("area", "?")
        bed = p.get("bedType", "?")
        roi = p.get("roi", {}) if not is_offplan else p.get("postHandoverROI", {})
        net_roi = roi.get("netROI", "N/A")
        growth = p.get("growth12m", "N/A") if not is_offplan else p.get("futureAppreciation", {}).get("potentialGainPct", "N/A")
        risk_level = p.get("risk", {}).get("riskLevel", "N/A")
        summaries.append(f"ID {p.get('id')}: {bed} {p.get('category', '')} in {area}, AED {price:,.0f}, Score {score}, {rec}, ROI {net_roi}%, Growth {growth}%, Risk {risk_level}, Conf {conf}%")

    user_prompt = f"""Compare these properties for this investor:

Investor:
- Goal: {investor_profile.get('goal', 'balanced')}
- Budget: {investor_profile.get('budget', 'any')}
- Risk: {investor_profile.get('risk', 'medium')}

Properties:
{chr(10).join(summaries)}

Compare them:
1. Which is the best fit for this investor's goal?
2. What are the key trade-offs between the top options?
3. Which offers the best risk-adjusted return?
4. Which has the most reliable data?

Respond as JSON:
```json
{{
  "comparison": "2-3 sentence summary of how they compare",
  "ranking_reasoning": "why one ranks above another",
  "best_fit_id": <id of best property for this investor>,
  "trade_offs": ["trade-off 1", "trade-off 2"]
}}
```"""

    response = _call_llm(COMPARE_SYSTEM, user_prompt, max_tokens=800)
    result = _extract_json(response) if response else None

    if result and "comparison" in result:
        return {
            "comparison": result.get("comparison", ""),
            "ranking_reasoning": result.get("ranking_reasoning", ""),
            "best_fit_id": result.get("best_fit_id"),
            "trade_offs": result.get("trade_offs", []),
            "source": "llm",
        }

    # Fallback: pick highest score
    best = max(properties, key=lambda p: p.get("offplanScore") or p.get("readyScore", 0)) if properties else None
    return {
        "comparison": "Sorted by investment score (deterministic)",
        "ranking_reasoning": "Higher score = better investment potential",
        "best_fit_id": best.get("id") if best else None,
        "trade_offs": [],
        "source": "deterministic",
    }


# ─── 6. NEGOTIATION STRATEGY ───

NEGOTIATION_SYSTEM = """You are a Dubai real estate negotiation advisor. Your job is to suggest a negotiation strategy for a property buyer.

You receive computed metrics (price vs market, comparable prices, market position). You do NOT recalculate. You use them to advise on negotiation.

Be specific and actionable. Reference the actual numbers.

Respond ONLY with a JSON object, no other text."""

def negotiation_strategy(property_data: dict) -> dict:
    """
    LLM suggests negotiation approach based on computed price metrics.
    Returns: {strategy, suggested_offer, leverage_points, risks}
    """
    is_offplan = "offplanScore" in property_data
    price = property_data.get("askingPrice", 0)

    if is_offplan:
        fv = property_data.get("fairValue", {})
        po = property_data.get("priceOpportunity", {})
        price_diff = po.get("priceDifferencePct", 0)
        fair_value = fv.get("fairValue", 0)
        user_prompt = f"""Suggest a negotiation strategy for this off-plan property:

- Asking Price: AED {price:,.0f}
- Fair Market Value: AED {fair_value:,.0f}
- Price vs Market: {price_diff:.1f}%
- Developer: {property_data.get('developerData', {}).get('developerName', 'N/A')}
- Developer Score: {property_data.get('developerData', {}).get('developerScore', 'N/A')}

Advise:
1. Should the buyer negotiate? By how much?
2. What leverage points exist?
3. What payment plan terms should they request?
4. What are the risks of pushing too hard?

Respond as JSON:
```json
{{
  "strategy": "2-3 sentence negotiation approach",
  "suggested_offer": "suggested offer price or payment terms",
  "leverage_points": ["leverage 1", "leverage 2"],
  "risks": ["risk of negotiating too hard"]
}}
```"""
    else:
        comp = property_data.get("comparablePrice")
        price_diff = property_data.get("priceDifference")
        market_pos = property_data.get("marketPosition", "N/A")
        days_on_market = property_data.get("liquidity", {}).get("avgDaysOnMarket", "N/A")
        user_prompt = f"""Suggest a negotiation strategy for this ready property:

- Asking Price: AED {price:,.0f}
- Comparable Sold Price: {('AED ' + format(comp, ',.0f')) if comp else 'N/A'}
- Price vs Comparables: {price_diff if price_diff is not None else 'N/A'}%
- Market Position: {market_pos}
- Avg Days on Market: {days_on_market}

Advise:
1. Should the buyer negotiate? By how much?
2. What leverage points exist?
3. What is a reasonable opening offer?
4. What are the risks of pushing too hard?

Respond as JSON:
```json
{{
  "strategy": "2-3 sentence negotiation approach",
  "suggested_offer": "suggested opening offer price",
  "leverage_points": ["leverage 1", "leverage 2"],
  "risks": ["risk of negotiating too hard"]
}}
```"""

    response = _call_llm(NEGOTIATION_SYSTEM, user_prompt, max_tokens=600)
    result = _extract_json(response) if response else None

    if result and "strategy" in result:
        return {
            "strategy": result.get("strategy", ""),
            "suggested_offer": result.get("suggested_offer", ""),
            "leverage_points": result.get("leverage_points", []),
            "risks": result.get("risks", []),
            "source": "llm",
        }

    # Fallback
    if is_offplan:
        fv_val = property_data.get("fairValue", {}).get("fairValue", 0)
        if fv_val > 0 and price > fv_val:
            offer = int(fv_val * 0.98)
        else:
            offer = int(price * 0.95)
    else:
        comp_val = property_data.get("comparablePrice")
        if comp_val and comp_val > 0:
            offer = int(comp_val * 0.97)
        else:
            offer = int(price * 0.95)
    return {
        "strategy": f"Offer below asking price based on market position",
        "suggested_offer": f"AED {offer:,.0f}",
        "leverage_points": ["Comparable sales data", "Days on market"],
        "risks": ["Seller may reject and sell to another buyer"],
        "source": "deterministic",
    }


# ─── 7. EXIT STRATEGY ───

EXIT_SYSTEM = """You are a Dubai real estate investment advisor. Your job is to suggest an exit strategy for a property investor.

You receive computed metrics (growth, liquidity, ROI, market position). You do NOT recalculate. You advise on timing and exit options.

Be specific about timelines and conditions. Reference the actual numbers.

Respond ONLY with a JSON object, no other text."""

def exit_strategy(property_data: dict, investor_profile: dict | None = None) -> dict:
    """
    LLM suggests exit timeline and strategy.
    Returns: {strategy, timeline, exit_conditions, risks}
    """
    is_offplan = "offplanScore" in property_data
    score = property_data.get("offplanScore") or property_data.get("readyScore", 0)
    growth = property_data.get("growth12m", 0) if not is_offplan else property_data.get("futureAppreciation", {}).get("potentialGainPct", 0)
    liq = property_data.get("liquidity", {})
    liq_label = liq.get("liquidityLabel", "N/A")
    roi = property_data.get("roi", {}) if not is_offplan else property_data.get("postHandoverROI", {})
    net_roi = roi.get("netROI", "N/A")

    goal = investor_profile.get("goal", "balanced") if investor_profile else "balanced"

    user_prompt = f"""Suggest an exit strategy for this property investment:

- Investment Score: {score}/100
- Investor Goal: {goal}
- Net ROI: {net_roi}%
- Growth: {growth}%
- Liquidity: {liq_label}
- Property Type: {'Off-Plan' if is_offplan else 'Ready'}

Advise:
1. When should the investor exit?
2. What conditions should trigger the exit?
3. What are the risks of holding too long?
4. What is the expected exit price range?

Respond as JSON:
```json
{{
  "strategy": "2-3 sentence exit strategy",
  "timeline": "recommended hold period",
  "exit_conditions": ["condition 1", "condition 2"],
  "risks": ["risk 1", "risk 2"]
}}
```"""

    response = _call_llm(EXIT_SYSTEM, user_prompt, max_tokens=600)
    result = _extract_json(response) if response else None

    if result and "strategy" in result:
        return {
            "strategy": result.get("strategy", ""),
            "timeline": result.get("timeline", ""),
            "exit_conditions": result.get("exit_conditions", []),
            "risks": result.get("risks", []),
            "source": "llm",
        }

    # Fallback
    if goal == "rental_income":
        timeline = "Hold 5-7 years for rental yield accumulation"
    elif goal == "capital_growth":
        timeline = "Hold 3-5 years then sell at peak appreciation"
    else:
        timeline = "Hold 5 years, monitor market conditions"
    return {
        "strategy": f"{'Hold for rental income' if goal == 'rental_income' else 'Hold for capital appreciation then exit'}",
        "timeline": timeline,
        "exit_conditions": ["Price reaches target gain", "Market shows signs of cooling"],
        "risks": ["Market downturn", "Liquidity constraints"],
        "source": "deterministic",
    }


# ─── 8. GENERATE FULL ADVISORY REPORT ───

REPORT_SYSTEM = """You are a professional Dubai real estate investment advisor. Generate a complete advisory report section for a property.

You receive ALL computed metrics. You do NOT recalculate anything. You write the advisory narrative.

Write in a professional, client-facing tone. Be specific to this property. Structure it clearly.

Respond ONLY with a JSON object, no other text."""

def generate_advisory_report(property_data: dict, investor_profile: dict | None = None) -> dict:
    """
    LLM generates a full advisory report combining all sections.
    Returns: {executive_summary, investment_thesis, strengths, risks, negotiation_tips, exit_plan, data_reliability}
    """
    is_offplan = "offplanScore" in property_data
    score = property_data.get("offplanScore") or property_data.get("readyScore", 0)
    rec = property_data.get("recommendation", "HOLD")
    conf = property_data.get("confidenceScore", 50)
    price = property_data.get("askingPrice", 0)
    area = property_data.get("area", "Unknown")
    bed = property_data.get("bedType", "?")
    flags = property_data.get("ruleFlags", [])

    # Build comprehensive metrics summary
    if is_offplan:
        fv = property_data.get("fairValue", {})
        po = property_data.get("priceOpportunity", {})
        fa = property_data.get("futureAppreciation", {})
        roi = property_data.get("postHandoverROI", {})
        dev = property_data.get("developerData", {})
        comm = property_data.get("communityData", {})
        liq = property_data.get("liquidity", {})
        risk = property_data.get("risk", {})
        metrics = f"""Score: {score}/100 | Recommendation: {rec} | Confidence: {conf}%
Price: AED {price:,.0f} | Fair Value: AED {fv.get('fairValue', 0):,.0f} | Price vs Market: {po.get('priceDifferencePct', 'N/A')}%
Future Gain: {fa.get('potentialGainPct', 'N/A')}% | Post-Handover ROI: {roi.get('netROI', 'N/A')}%
Developer: {dev.get('developerName', 'N/A')} ({dev.get('developerScore', 'N/A')}/100)
Community: {comm.get('communityScore', 'N/A')}/100 | Liquidity: {liq.get('liquidityScore', 'N/A')}/100
Risk: {risk.get('riskLevel', 'N/A')} | Rule Flags: {flags}"""
    else:
        roi = property_data.get("roi", {})
        liq = property_data.get("liquidity", {})
        risk = property_data.get("risk", {})
        metrics = f"""Score: {score}/100 | Recommendation: {rec} | Confidence: {conf}%
Price: AED {price:,.0f} | Comparable: {property_data.get('comparablePrice', 'N/A')} | Price Diff: {property_data.get('priceDifference', 'N/A')}%
Net ROI: {roi.get('netROI', 'N/A')}% | Annual Rent: {roi.get('annualRent', 'N/A')}
Liquidity: {liq.get('liquidityScore', 'N/A')}/100 ({liq.get('liquidityLabel', 'N/A')})
Growth 12m: {property_data.get('growth12m', 'N/A')}% | Risk: {risk.get('riskLevel', 'N/A')}
Rule Flags: {flags}"""

    profile_str = ""
    if investor_profile:
        profile_str = f"\nInvestor: Goal={investor_profile.get('goal', 'balanced')}, Risk={investor_profile.get('risk', 'medium')}, Budget={investor_profile.get('budget', 'any')}"

    user_prompt = f"""Write a complete advisory report for this property.

Property: {bed} {property_data.get('category', '')} in {area}
{metrics}{profile_str}

Write a professional, client-facing report with these sections:
1. Executive Summary (2 sentences)
2. Investment Thesis (3-4 sentences explaining the opportunity or lack thereof)
3. Key Strengths (2-3 specific points)
4. Key Risks (2-3 specific points)
5. Negotiation Tips (1-2 actionable suggestions)
6. Exit Strategy (1-2 sentences on when to sell)
7. Data Reliability Note (1 sentence on confidence and data quality)

Be specific to THIS property. No generic statements.

Respond as JSON:
```json
{{
  "executive_summary": "2 sentence summary",
  "investment_thesis": "3-4 sentence thesis",
  "strengths": ["strength 1", "strength 2"],
  "risks": ["risk 1", "risk 2"],
  "negotiation_tips": ["tip 1", "tip 2"],
  "exit_plan": "1-2 sentence exit strategy",
  "data_reliability": "1 sentence on data confidence"
}}
```"""

    response = _call_llm(REPORT_SYSTEM, user_prompt, max_tokens=1200)
    result = _extract_json(response) if response else None

    if result and "executive_summary" in result:
        return {
            "executive_summary": result.get("executive_summary", ""),
            "investment_thesis": result.get("investment_thesis", ""),
            "strengths": result.get("strengths", []),
            "risks": result.get("risks", []),
            "negotiation_tips": result.get("negotiation_tips", []),
            "exit_plan": result.get("exit_plan", ""),
            "data_reliability": result.get("data_reliability", ""),
            "source": "llm",
        }

    # Fallback: assemble from deterministic data
    reasons = property_data.get("reasons", [])
    lost_points = property_data.get("lostPoints", [])
    return {
        "executive_summary": f"Score {score}/100 — {rec}",
        "investment_thesis": ". ".join(reasons[:3]) if reasons else "Property meets baseline criteria",
        "strengths": reasons[:3],
        "risks": lost_points[:3],
        "negotiation_tips": [],
        "exit_plan": "Hold 3-5 years depending on market conditions",
        "data_reliability": f"Confidence: {conf}%" + (" — low confidence" if conf < 50 else ""),
        "source": "deterministic",
    }


# ─── TEST ───

if __name__ == "__main__":
    print("=== Testing LLM Advisor Engine ===\n")

    # Test 1: Validate listing
    print("1. Listing Validation")
    result = validate_listing(
        title="4BR Elie Saab Villa",
        price=400000,
        size_sqft=3000,
        bed_type="4 B/R",
        category="Villa",
        area="Arabian Ranches 3",
        community_median_price=3800000,
        community_median_price_sqft=1267,
    )
    print(f"   Result: {result}\n")

    # Test 2: Explain score
    print("2. Explain Score")
    result = explain_score(
        property_data={
            "title": "2BR Apartment in Dubai Marina",
            "askingPrice": 1800000,
            "areaSqft": 1200,
            "bedType": "2 B/R",
            "category": "Apartment",
            "area": "Dubai Marina",
            "readyScore": 78,
            "recommendation": "BUY",
            "confidenceScore": 72,
            "roi": {"netROI": 7.5, "annualRent": 135000, "grossROI": 9.0, "hasRentData": True},
            "comparablePrice": 1750000,
            "priceDifference": 2.8,
            "marketPosition": "Fair Market Value",
            "liquidity": {"liquidityScore": 75, "liquidityLabel": "Good"},
            "communityScore": 80,
            "developerScore": 70,
            "growth12m": 8.5,
            "risk": {"riskLevel": "Low"},
            "ruleFlags": [],
            "reasons": ["Net rental yield of 7.5% is above Dubai market average"],
            "lostPoints": ["Growth limited"],
        },
        investor_profile={"goal": "rental_income", "risk": "medium"},
    )
    print(f"   Result: {result}\n")

    # Test 3: Detect contradictions
    print("3. Detect Contradictions")
    result = detect_contradictions(
        property_data={
            "readyScore": 45,
            "recommendation": "BUY",
            "confidenceScore": 25,
            "roi": {"netROI": None, "hasRentData": False},
            "liquidity": {"liquidityScore": 90},
            "risk": {"riskLevel": "Low"},
            "comparablePrice": None,
            "ruleFlags": ["RULE_3_NO_RENT_DATA", "RULE_6_INSUFFICIENT_DATA"],
        }
    )
    print(f"   Result: {result}\n")

    # Test 4: Investor recommendation
    print("4. Investor Recommendation")
    result = investor_recommendation(
        property_data={
            "askingPrice": 1800000,
            "area": "Dubai Marina",
            "bedType": "2 B/R",
            "category": "Apartment",
            "readyScore": 78,
            "recommendation": "BUY",
            "confidenceScore": 72,
            "roi": {"netROI": 7.5},
            "growth12m": 8.5,
            "liquidity": {"liquidityLabel": "Good"},
            "risk": {"riskLevel": "Low"},
        },
        investor_profile={"goal": "rental_income", "budget": "1m-2m", "risk": "medium"},
    )
    print(f"   Result: {result}\n")

    # Test 5: Negotiation strategy
    print("5. Negotiation Strategy")
    result = negotiation_strategy(
        property_data={
            "askingPrice": 1800000,
            "comparablePrice": 1750000,
            "priceDifference": 2.8,
            "marketPosition": "Fair Market Value",
            "liquidity": {"avgDaysOnMarket": 45},
        }
    )
    print(f"   Result: {result}\n")

    # Test 6: Exit strategy
    print("6. Exit Strategy")
    result = exit_strategy(
        property_data={
            "readyScore": 78,
            "roi": {"netROI": 7.5},
            "growth12m": 8.5,
            "liquidity": {"liquidityLabel": "Good"},
        },
        investor_profile={"goal": "rental_income", "risk": "medium"},
    )
    print(f"   Result: {result}\n")

    # Test 7: Generate advisory report
    print("7. Advisory Report")
    result = generate_advisory_report(
        property_data={
            "title": "2BR Apartment in Dubai Marina",
            "askingPrice": 1800000,
            "areaSqft": 1200,
            "bedType": "2 B/R",
            "category": "Apartment",
            "area": "Dubai Marina",
            "readyScore": 78,
            "recommendation": "BUY",
            "confidenceScore": 72,
            "roi": {"netROI": 7.5, "annualRent": 135000, "grossROI": 9.0, "hasRentData": True},
            "comparablePrice": 1750000,
            "priceDifference": 2.8,
            "marketPosition": "Fair Market Value",
            "liquidity": {"liquidityScore": 75, "liquidityLabel": "Good"},
            "communityScore": 80,
            "growth12m": 8.5,
            "risk": {"riskLevel": "Low"},
            "ruleFlags": [],
            "reasons": ["Net rental yield of 7.5% is above Dubai market average"],
            "lostPoints": ["Growth limited"],
        },
        investor_profile={"goal": "rental_income", "risk": "medium"},
    )
    print(f"   Result: {result}\n")

    print("=== All tests complete ===")
