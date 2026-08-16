"""
APIL Rigorous Edge-Case Test Suite
Runs 100+ simulated user combinations and validates every data field.
"""
import json
import sys
import random
import itertools
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engines.recommendation_engine import generate_recommendations, parse_budget
from engines.utils import load_json, safe_float, safe_int
from config.settings import (
    READY_PROPERTY_SCORES_FILE, OFFPLAN_SCORES_FILE,
    COMMUNITY_SCORES_FILE, DEVELOPER_SCORES_FILE, PROJECT_SCORES_FILE
)

# ─── Input spaces (from Questionnaire.tsx) ───
GOALS = ['rental_income', 'capital_growth', 'balanced', 'holiday_home']
BUDGETS = ['500k-1m', '1m-2m', '2m-5m', '5m+', 'custom:300000', 'custom:750000', 'custom:1500000', 'custom:3000000', 'custom:10000000', 'custom:50000', '']
PROPERTY_TYPES = ['apartment', 'villa', 'townhouse', 'penthouse', '']
BEDROOMS = ['studio', '1', '2', '3', '']
LOCATIONS = ['any', 'Business Bay', 'Downtown Dubai', 'Dubai Marina', 'Palm Jumeirah', 'Jumeirah Village Circle', '']
READY_OFFPLAN = ['ready', 'offplan', 'either', '']
TIMELINES = ['1-2y', '3-5y', '5y+', 'undecided', '']
FINANCING = ['cash', 'mortgage', 'either', '']
RISKS = ['low', 'medium', 'high', '']

# Load data
ready_props = load_json(READY_PROPERTY_SCORES_FILE)
offplan_props = load_json(OFFPLAN_SCORES_FILE)
communities = load_json(COMMUNITY_SCORES_FILE)
developers = load_json(DEVELOPER_SCORES_FILE)
projects = load_json(PROJECT_SCORES_FILE)

issues = []
stats = {'total': 0, 'passed': 0, 'failed': 0, 'warnings': 0, 'errors': 0, 'empty': 0}

def log_issue(severity, test_id, field, msg, value=None):
    issues.append({
        'severity': severity,
        'test_id': test_id,
        'field': field,
        'message': msg,
        'value': str(value)[:200] if value else None,
        'timestamp': datetime.now().isoformat()
    })
    if severity == 'ERROR':
        stats['errors'] += 1
    elif severity == 'WARN':
        stats['warnings'] += 1

def validate_property(prop, test_id, profile):
    """Validate every field in a property recommendation."""
    if not prop:
        log_issue('ERROR', test_id, 'property', 'No property returned', None)
        return

    pid = prop.get('id', '?')
    ptype = prop.get('propertyType', '?')

    # ─── 1. Score validation ───
    if ptype == 'ready':
        score = prop.get('readyScore')
        if score is None:
            log_issue('ERROR', test_id, f'readyScore[{pid}]', 'Missing readyScore', None)
        elif score < 0 or score > 100:
            log_issue('ERROR', test_id, f'readyScore[{pid}]', f'Score out of range: {score}', score)

    if ptype == 'offplan':
        score = prop.get('offplanScore')
        if score is None:
            log_issue('ERROR', test_id, f'offplanScore[{pid}]', 'Missing offplanScore', None)
        elif score < 0 or score > 100:
            log_issue('ERROR', test_id, f'offplanScore[{pid}]', f'Score out of range: {score}', score)

    # ─── 2. Price validation ───
    price = safe_float(prop.get('askingPrice'))
    if ptype == 'ready' and price <= 0:
        log_issue('ERROR', test_id, f'askingPrice[{pid}]', f'Invalid price: {price}', price)
    if price > 0:
        price_sqft = safe_float(prop.get('priceSqft'))
        area_sqft = safe_float(prop.get('areaSqft'))
        if area_sqft > 0 and price_sqft > 0:
            calc_sqft = price / area_sqft
            if abs(calc_sqft - price_sqft) / price_sqft > 0.15:
                log_issue('WARN', test_id, f'priceSqft[{pid}]', f'Price/sqft mismatch: stated={price_sqft}, calc={calc_sqft:.0f}', (price_sqft, calc_sqft))

    # ─── 3. Budget compliance ───
    budget = profile.get('budget', '')
    if budget and budget != 'any':
        min_p, max_p = parse_budget(budget)
        if min_p > 0 or max_p < float('inf'):
            if not (min_p <= price <= max_p):
                # Check if relaxation was noted
                pass  # Will check relaxation flag separately

    # ─── 4. ROI validation ───
    roi = prop.get('roi', {})
    if roi:
        gross = safe_float(roi.get('grossROI'))
        net = safe_float(roi.get('netROI'))
        annual_rent = safe_float(roi.get('annualRent'))
        service_charge = safe_float(roi.get('serviceChargeAnnual'))
        mgmt_fee = safe_float(roi.get('managementFee'))
        vacancy = safe_float(roi.get('vacancyRate'))
        net_income = safe_float(roi.get('netAnnualIncome'))

        if price > 0 and annual_rent > 0:
            calc_gross = (annual_rent / price) * 100
            if abs(calc_gross - gross) > 2:
                log_issue('ERROR', test_id, f'grossROI[{pid}]', f'Gross ROI mismatch: stated={gross}, calc={calc_gross:.2f}', (gross, calc_gross))

        # Net ROI = netIncome / price * 100 (works for negative too)
        if price > 0 and net_income != 0:
            calc_net = (net_income / price) * 100
            if abs(calc_net - net) > 2:
                log_issue('ERROR', test_id, f'netROI[{pid}]', f'Net ROI mismatch: stated={net}, calc={calc_net:.2f}', (net, calc_net))

        # Net income = rent - service_charge - management_fee - vacancy_loss
        # vacancy is fraction (0.05), not percentage (5)
        vacancy_loss = round(annual_rent * vacancy)
        calc_net_income = annual_rent - service_charge - mgmt_fee - vacancy_loss
        if abs(calc_net_income - net_income) > 10:  # Allow AED 10 rounding
            log_issue('ERROR', test_id, f'netAnnualIncome[{pid}]', f'Net income mismatch: stated={net_income}, calc={calc_net_income:.0f}', (net_income, calc_net_income))

        # Vacancy rate should be a fraction (0-1), not percentage (0-100)
        if vacancy > 1:
            log_issue('ERROR', test_id, f'vacancyRate[{pid}]', f'Vacancy rate={vacancy} looks like percentage, expected fraction (0-1)', vacancy)

        # ROI score check (handle negative ROI)
        roi_score = safe_int(prop.get('roiScore'))
        if net > 0 and roi_score > 0:
            expected_score = min(100, net * 8)
            if abs(roi_score - expected_score) > 15:
                log_issue('WARN', test_id, f'roiScore[{pid}]', f'ROI score vs netROI: score={roi_score}, expected~{expected_score:.0f}', (roi_score, expected_score))
        if net <= 0 and roi_score != 0:
            log_issue('WARN', test_id, f'roiScore[{pid}]', f'Net ROI={net} but roiScore={roi_score} (expected 0)', (net, roi_score))

    # ─── 4b. Data consistency: hasRentData vs estimatedRent ───
    dq = prop.get('dataQuality', {})
    has_rent = dq.get('hasRentData', True) if dq else True
    est_rent = safe_float(prop.get('estimatedRent'))
    if has_rent is False and est_rent > 0:
        log_issue('WARN', test_id, f'rentData[{pid}]', f'hasRentData=False but estimatedRent={est_rent} > 0', (has_rent, est_rent))
    if has_rent is True and est_rent == 0 and roi and net <= 0:
        log_issue('INFO', test_id, f'rentData[{pid}]', f'hasRentData=True but estimatedRent=0 and netROI={net}', (has_rent, est_rent, net))

    # ─── 5. Rent range validation ───
    rent_range = prop.get('rentRange')
    if rent_range:
        rr_low = safe_float(rent_range.get('low'))
        rr_high = safe_float(rent_range.get('high'))
        rr_mid = safe_float(rent_range.get('mid'))
        rr_sample = safe_int(rent_range.get('sampleSize'))
        rr_conf = rent_range.get('confidence', '')

        if rr_low > rr_high:
            log_issue('ERROR', test_id, f'rentRange[{pid}]', f'Low > High: {rr_low} > {rr_high}', rent_range)
        if rr_mid > 0 and (rr_mid < rr_low or rr_mid > rr_high):
            log_issue('WARN', test_id, f'rentRange[{pid}]', f'Mid outside range: {rr_mid} not in [{rr_low}, {rr_high}]', rent_range)

        # Rent range should relate to annual rent
        if roi and annual_rent > 0 and rr_mid > 0:
            if abs(rr_mid - annual_rent) / max(annual_rent, 1) > 0.3:
                log_issue('WARN', test_id, f'rentRange[{pid}]', f'Rent mid {rr_mid} vs annual rent {annual_rent} — large gap', (rr_mid, annual_rent))

        # Confidence vs sample size
        if rr_sample <= 3 and rr_conf == 'High':
            log_issue('WARN', test_id, f'rentRange[{pid}]', f'High confidence but only {rr_sample} samples', rent_range)
        if rr_sample == 0 and rr_conf != '':
            log_issue('WARN', test_id, f'rentRange[{pid}]', f'0 samples but confidence={rr_conf}', rent_range)

    # ─── 6. Growth validation ───
    g3 = safe_float(prop.get('growth3m'))
    g6 = safe_float(prop.get('growth6m'))
    g12 = safe_float(prop.get('growth12m'))
    growth_meta = prop.get('growthMetadata', {})

    # 3m and 6m being exactly the same non-zero value is suspicious (sparse data overlap)
    # But not when both are at the clamp boundary (-60 or 60) — that's expected for extreme moves
    if g3 == g6 and g3 != 0 and abs(g3) < 60:
        log_issue('WARN', test_id, f'growth[{pid}]', f'3m and 6m growth identical: {g3}%', (g3, g6))

    # Growth outside reasonable range
    for label, val in [('3m', g3), ('6m', g6), ('12m', g12)]:
        if abs(val) > 100:
            log_issue('ERROR', test_id, f'growth_{label}[{pid}]', f'Growth {label}={val}% — extreme value', val)

    # Growth metadata confidence
    for period in ['3m', '6m', '12m']:
        meta = growth_meta.get(period, {})
        if meta:
            samples = safe_int(meta.get('totalSamples'))
            conf = meta.get('confidence', '')
            if samples == 0 and conf == 'high':
                log_issue('WARN', test_id, f'growthMeta[{pid}]', f'{period}: 0 samples but high confidence', meta)

    # ─── 7. Score breakdown validation ───
    sb = prop.get('scoreBreakdown')
    if sb:
        components = ['price', 'roi', 'liquidity', 'community', 'developer', 'project']
        weights = {'price': 0.25, 'roi': 0.25, 'liquidity': 0.20, 'community': 0.15, 'developer': 0.10, 'project': 0.05}
        total_weighted = 0
        for comp in components:
            val = sb.get(comp)
            if val is None:
                log_issue('WARN', test_id, f'scoreBreakdown[{pid}]', f'Missing component: {comp}', sb)
            elif val < 0 or val > 100:
                log_issue('ERROR', test_id, f'scoreBreakdown[{pid}]', f'{comp}={val} out of range', val)
            else:
                total_weighted += val * weights[comp]

        # Check if weighted total roughly matches readyScore
        if ptype == 'ready':
            rs = safe_int(prop.get('readyScore'))
            if rs > 0 and abs(total_weighted - rs) > 5:
                log_issue('WARN', test_id, f'scoreBreakdown[{pid}]', f'Weighted total={total_weighted:.1f} vs readyScore={rs}', (total_weighted, rs))

    # ─── 8. Risk validation ───
    risk = prop.get('risk', {})
    if risk:
        rl = risk.get('riskLevel', '')
        rf = risk.get('riskFactors', [])
        components = risk.get('components', {})

        if rl not in ['Low', 'Medium', 'High', '']:
            log_issue('WARN', test_id, f'riskLevel[{pid}]', f'Unexpected risk level: {rl}', rl)

        # Risk level should align with overall risk score (backend: <35=Low, <60=Medium, >=60=High)
        overall = safe_int(risk.get('overallRisk'))
        if overall < 35 and rl != 'Low':
            log_issue('WARN', test_id, f'riskLevel[{pid}]', f'Overall risk={overall} but level={rl}', (overall, rl))
        if overall >= 60 and rl != 'High':
            log_issue('WARN', test_id, f'riskLevel[{pid}]', f'Overall risk={overall} but level={rl}', (overall, rl))
        if 35 <= overall < 60 and rl != 'Medium':
            log_issue('WARN', test_id, f'riskLevel[{pid}]', f'Overall risk={overall} but level={rl} (expected Medium)', (overall, rl))

        # Risk factors should not be empty
        if not rf and rl != 'Low':
            log_issue('WARN', test_id, f'riskFactors[{pid}]', f'Risk level={rl} but no risk factors listed', rf)

        # Risk components should sum approximately to overall risk
        # Backend weights: futureSupply=0.15, developer=0.20, areaSat=0.10, rental=0.15, volatility=0.10, construction=0.15, pricePremium=0.15
        if components:
            calc_overall = (
                safe_float(components.get('futureSupplyRisk', 0)) * 0.15 +
                safe_float(components.get('developerRisk', 0)) * 0.20 +
                safe_float(components.get('areaSaturationRisk', 0)) * 0.10 +
                safe_float(components.get('rentalRisk', 0)) * 0.15 +
                safe_float(components.get('marketVolatilityRisk', 0)) * 0.10 +
                safe_float(components.get('constructionDelayRisk', 0)) * 0.15 +
                safe_float(components.get('pricePremiumRisk', 0)) * 0.15
            )
            if abs(calc_overall - overall) > 5:
                log_issue('WARN', test_id, f'riskCalc[{pid}]', f'Risk components weighted={calc_overall:.1f} vs overallRisk={overall}', (calc_overall, overall))

        # Each risk component should be 0-100
        for ck, cv in components.items():
            v = safe_float(cv)
            if v < 0 or v > 100:
                log_issue('ERROR', test_id, f'riskComponent[{pid}]', f'{ck}={v} out of range 0-100', (ck, v))

    # ─── 9. Developer validation ───
    dev = prop.get('developerData', {})
    if dev:
        ds = safe_int(dev.get('developerScore'))
        if ds < 0 or ds > 100:
            log_issue('ERROR', test_id, f'developerScore[{pid}]', f'Score out of range: {ds}', ds)

        # Score breakdown
        dsb = dev.get('scoreBreakdown')
        if dsb:
            total = sum(safe_int(v) for v in dsb.values())
            if abs(total - ds) > 2:
                log_issue('ERROR', test_id, f'devScoreBreakdown[{pid}]', f'Breakdown total={total} vs score={ds}', (total, ds))

            # Check each component max
            maxes = {'trackRecord': 25, 'deliveryPerformance': 20, 'capitalGain': 15, 'rentalDemand': 10, 'salesVolume': 10, 'constructionQuality': 10, 'marketReputation': 10}
            for k, max_v in maxes.items():
                v = safe_int(dsb.get(k))
                if v > max_v:
                    log_issue('ERROR', test_id, f'devScoreBreakdown[{pid}]', f'{k}={v} exceeds max={max_v}', (v, max_v))
                if v < 0:
                    log_issue('ERROR', test_id, f'devScoreBreakdown[{pid}]', f'{k}={v} negative', v)

        # Delivery delay
        delay = dev.get('deliveryDelayPercent')
        if delay is not None:
            d = safe_float(delay)
            if d < 0 or d > 100:
                log_issue('ERROR', test_id, f'deliveryDelay[{pid}]', f'Delay % out of range: {d}', d)

    # ─── 10. Community validation ───
    comm = prop.get('communityData', {})
    if comm:
        cs = safe_int(comm.get('communityScore'))
        if cs < 0 or cs > 100:
            log_issue('ERROR', test_id, f'communityScore[{pid}]', f'Score out of range: {cs}', cs)

        # Score breakdown
        csb = comm.get('scoreBreakdown')
        if csb:
            total_contrib = sum(safe_float(v.get('contribution', 0)) for v in csb.values())
            if abs(total_contrib - cs) > 3:
                log_issue('ERROR', test_id, f'commScoreBreakdown[{pid}]', f'Contributions total={total_contrib} vs score={cs}', (total_contrib, cs))

            # Check each component
            for k, v in csb.items():
                contrib = safe_float(v.get('contribution', 0))
                max_v = safe_float(v.get('max', 0))
                score_v = safe_float(v.get('score', 0))
                if contrib > max_v:
                    log_issue('ERROR', test_id, f'commScoreBreakdown[{pid}]', f'{k} contribution={contrib} exceeds max={max_v}', (contrib, max_v))
                if score_v > 100:
                    log_issue('WARN', test_id, f'commScoreBreakdown[{pid}]', f'{k} score={score_v} > 100', score_v)

        # Sub-scores
        ss = comm.get('subScores', {})
        if ss:
            for k, v in ss.items():
                if safe_int(v) > 100 or safe_int(v) < 0:
                    log_issue('WARN', test_id, f'commSubScores[{pid}]', f'{k}={v} out of range', v)

    # ─── 11. Project validation ───
    proj = prop.get('projectData', {})
    if proj:
        ps = safe_int(proj.get('projectScore'))
        if ps < 0 or ps > 100:
            log_issue('ERROR', test_id, f'projectScore[{pid}]', f'Score out of range: {ps}', ps)

        # Project score breakdown
        psb = proj.get('scoreBreakdown')
        if psb:
            weights = psb.get('weights', {})
            # Map weight keys to score keys
            key_map = {'yield': 'yieldScore', 'growth': 'growthScore', 'demand': 'demandScore', 'liquidity': 'liquidityScore', 'stability': 'priceStabilityScore'}
            scores = {}
            for wk, sk in key_map.items():
                scores[wk] = safe_float(psb.get(sk, 0))
            if weights:
                total = sum(scores.get(k, 0) * safe_float(w) for k, w in weights.items())
                if abs(total - ps) > 5:
                    log_issue('WARN', test_id, f'projScoreBreakdown[{pid}]', f'Weighted total={total:.1f} vs projectScore={ps}', (total, ps))

    # ─── 12. Data quality validation ───
    dq = prop.get('dataQuality', {})
    if dq:
        sales = safe_int(dq.get('salesCount'))
        rent = safe_int(dq.get('rentCount'))
        if sales == 0 and rent == 0:
            log_issue('WARN', test_id, f'dataQuality[{pid}]', 'No sales or rent data', dq)
        # hasRentData=False should mean rentCount=0 or estimatedRent=0
        has_rent = dq.get('hasRentData')
        if has_rent is False and rent > 0 and roi and safe_float(roi.get('annualRent', 0)) > 0:
            log_issue('WARN', test_id, f'dataQuality[{pid}]', f'hasRentData=False but rentCount={rent} and annualRent>0', (has_rent, rent))
        # roiValidation should make sense
        roi_val = dq.get('roiValidation', '')
        if roi_val == 'NO_RENT_DATA' and roi and safe_float(roi.get('annualRent', 0)) > 0:
            log_issue('ERROR', test_id, f'dataQuality[{pid}]', f'roiValidation=NO_RENT_DATA but annualRent>0', roi_val)

    # ─── 13. Data completeness ───
    dc = prop.get('dataCompleteness', {})
    if dc:
        overall = safe_int(dc.get('overall'))
        if overall < 100:
            missing = [k for k, v in dc.items() if k != 'overall' and safe_int(v) < 100]
            if missing:
                log_issue('INFO', test_id, f'dataCompleteness[{pid}]', f'Incomplete: {missing}', dc)

    # ─── 14. Recommendation label ───
    rec = prop.get('recommendation', '')
    if rec:
        if rec not in ['STRONG BUY', 'BUY', 'HOLD', 'CAUTION', 'AVOID', 'WATCH', 'REVIEW']:
            log_issue('WARN', test_id, f'recommendation[{pid}]', f'Unexpected label: {rec}', rec)

        # Check alignment with score
        if ptype == 'ready':
            rs = safe_int(prop.get('readyScore'))
            if rs >= 85 and rec != 'STRONG BUY':
                log_issue('WARN', test_id, f'recommendation[{pid}]', f'Score={rs} but rec={rec} (expected STRONG BUY)', (rs, rec))
            if rs < 65 and rec == 'STRONG BUY':
                log_issue('ERROR', test_id, f'recommendation[{pid}]', f'Score={rs} but rec={rec}', (rs, rec))

    # ─── 15. Reasons and lost points ───
    reasons = prop.get('reasons', [])
    lost = prop.get('lostPoints', [])
    if not reasons:
        log_issue('WARN', test_id, f'reasons[{pid}]', 'No buy reasons provided', None)
    if not lost and score and score < 90:
        log_issue('INFO', test_id, f'lostPoints[{pid}]', f'Score={score} but no lost points listed', None)

    # ─── 16. Confidence score ───
    conf = safe_int(prop.get('confidenceScore'))
    if conf < 0 or conf > 100:
        log_issue('ERROR', test_id, f'confidenceScore[{pid}]', f'Out of range: {conf}', conf)

    # ─── 17. Liquidity ───
    liq = prop.get('liquidity', {})
    if liq:
        ls = safe_int(liq.get('liquidityScore'))
        if ls < 0 or ls > 100:
            log_issue('ERROR', test_id, f'liquidityScore[{pid}]', f'Out of range: {ls}', ls)
        absorption = safe_float(liq.get('absorptionRate'))
        if absorption > 1000:
            log_issue('WARN', test_id, f'absorptionRate[{pid}]', f'Very high absorption: {absorption}', absorption)

    # ─── 18. Bedroom filter compliance ───
    bed = profile.get('bedrooms', '')
    if bed and bed in ['studio', '1', '2', '3']:
        bed_map = {'studio': ['Studio'], '1': ['1 B/R'], '2': ['2 B/R'], '3': ['3 B/R', '4 B/R', '5 B/R', '6 B/R']}
        expected_beds = bed_map.get(bed, [])
        actual_bed = prop.get('bedType', '')
        if expected_beds and actual_bed and actual_bed not in expected_beds:
            # Check if relaxation was noted
            pass  # Will verify relaxation flag

    # ─── 19. Property type compliance ───
    pt = profile.get('property_type', '')
    if pt and pt in ['apartment', 'villa', 'townhouse', 'penthouse']:
        type_map = {
            'apartment': ['Apartment', 'Flat', 'Studio', 'Hotel Apartment'],
            'villa': ['Villa', 'Mansions', 'Mansion'],
            'townhouse': ['Townhouse'],
            'penthouse': ['Penthouse', 'Duplex', 'Triplex'],
        }
        expected_cats = type_map.get(pt, [])
        actual_cat = prop.get('category', '')
        if expected_cats and actual_cat and actual_cat not in expected_cats:
            pass  # Will verify relaxation flag

    # ─── 20. Estimated rent vs rent range ───
    est_rent = safe_float(prop.get('estimatedRent'))
    if est_rent > 0 and rent_range:
        rr_low = safe_float(rent_range.get('low'))
        rr_high = safe_float(rent_range.get('high'))
        if est_rent < rr_low * 0.7 or est_rent > rr_high * 1.3:
            log_issue('WARN', test_id, f'estimatedRent[{pid}]', f'Est rent {est_rent} outside rent range [{rr_low}, {rr_high}]', (est_rent, rr_low, rr_high))

    # ─── 21. Reasons consistency with data ───
    if reasons:
        for r in reasons:
            r_lower = r.lower()
            # Should not claim 'rental yield' when no rent data
            if has_rent is False and ('yield' in r_lower or 'rental' in r_lower):
                log_issue('WARN', test_id, f'reasons[{pid}]', f'hasRentData=False but reason mentions yield/rental: "{r}"', r)
            # Should not claim 'value opportunity' when price is above comparables
            if 'value' in r_lower and price > 0:
                comp_price = safe_float(prop.get('comparablePrice'))
                if comp_price > 0 and price > comp_price * 1.05:
                    log_issue('WARN', test_id, f'reasons[{pid}]', f'Reason claims value but price {price} > comparable {comp_price}', (price, comp_price))

    # ─── 22. Market position vs price difference ───
    market_pos = prop.get('marketPosition', '')
    price_diff = safe_float(prop.get('priceDifference'))
    if market_pos and price_diff != 0:
        if 'Value' in market_pos and price_diff > 5:
            log_issue('WARN', test_id, f'marketPosition[{pid}]', f'Market position={market_pos} but priceDiff=+{price_diff}% (above market)', (market_pos, price_diff))
        if 'Premium' in market_pos and price_diff < -5:
            log_issue('WARN', test_id, f'marketPosition[{pid}]', f'Market position={market_pos} but priceDiff={price_diff}% (below market)', (market_pos, price_diff))

    # ─── 23. Confidence score formula check ───
    conf = safe_int(prop.get('confidenceScore'))
    if conf and dq:
        sales = safe_int(dq.get('salesCount'))
        has_rent_data = dq.get('hasRentData', True)
        has_comp = dq.get('hasComparables', False)
        # Expected: 100 - 20(no comp) - 20(no rent) - 15(sales<10) - 10(no dev) - 10(rent<5)
        expected_conf = 100
        if not has_comp:
            expected_conf -= 20
        if not has_rent_data:
            expected_conf -= 20
        if sales < 10:
            expected_conf -= 15
        if not prop.get('developerData'):
            expected_conf -= 10
        rent_count = safe_int(dq.get('rentCount'))
        if rent_count < 5:
            expected_conf -= 10
        if abs(conf - expected_conf) > 15:
            log_issue('WARN', test_id, f'confidenceScore[{pid}]', f'Confidence={conf} but expected~{expected_conf} based on data quality', (conf, expected_conf))

    # ─── 24. Liquidity score validation ───
    liq = prop.get('liquidity', {})
    if liq:
        ls = safe_int(liq.get('liquidityScore'))
        ll = liq.get('liquidityLabel', '')
        if ls >= 80 and ll != 'Excellent' and ll != 'Good':
            log_issue('WARN', test_id, f'liquidityLabel[{pid}]', f'Score={ls} but label={ll} (expected Excellent/Good)', (ls, ll))
        if ls < 50 and ll == 'Excellent':
            log_issue('ERROR', test_id, f'liquidityLabel[{pid}]', f'Score={ls} but label=Excellent', (ls, ll))

    # ─── 25. Project rental yield label check ───
    proj = prop.get('projectData', {})
    if proj:
        proj_yield = safe_float(proj.get('rentalYield'))
        if proj_yield > 0 and proj_yield < 5:
            # Low yield should not be labeled 'Good yield'
            pass  # Frontend fix handles this, just log
            log_issue('INFO', test_id, f'projectYield[{pid}]', f'Project yield={proj_yield}% is low (<5%)', proj_yield)


def validate_response(recs, profile, test_id):
    """Validate the overall recommendation response."""
    stats['total'] += 1

    if not recs:
        stats['empty'] += 1
        stats['failed'] += 1
        log_issue('ERROR', test_id, 'response', 'No response returned', None)
        return

    recommendations = recs.get('recommendations', [])
    if not recommendations:
        stats['empty'] += 1
        stats['failed'] += 1
        log_issue('ERROR', test_id, 'recommendations', 'Empty recommendations array', recs)
        return

    # Check relaxation
    relaxed = recs.get('relaxed', False)
    relaxation_steps = recs.get('relaxationSteps', [])

    # Validate each property
    for prop in recommendations:
        validate_property(prop, test_id, profile)

    # Check top property matches profile constraints
    top = recommendations[0]
    top_type = top.get('propertyType', 'ready')
    if not relaxed and top_type == 'ready':
        # Budget check
        budget = profile.get('budget', '')
        if budget and budget != 'any':
            min_p, max_p = parse_budget(budget)
            if min_p > 0 or max_p < float('inf'):
                price = safe_float(top.get('askingPrice'))
                if not (min_p <= price <= max_p):
                    log_issue('ERROR', test_id, 'budget_compliance', f'Not relaxed but price {price} outside budget [{min_p}, {max_p}]', (price, min_p, max_p))

        # Bedroom check
        bed = profile.get('bedrooms', '')
        if bed and bed in ['studio', '1', '2', '3']:
            bed_map = {'studio': ['Studio'], '1': ['1 B/R'], '2': ['2 B/R'], '3': ['3 B/R', '4 B/R', '5 B/R', '6 B/R']}
            expected_beds = bed_map.get(bed, [])
            actual_bed = top.get('bedType', '')
            if expected_beds and actual_bed and actual_bed not in expected_beds:
                log_issue('ERROR', test_id, 'bedroom_compliance', f'Not relaxed but bedType {actual_bed} not in {expected_beds}', (actual_bed, expected_beds))

        # Property type check
        pt = profile.get('property_type', '')
        if pt and pt in ['apartment', 'villa', 'townhouse', 'penthouse']:
            type_map = {
                'apartment': ['Apartment', 'Flat', 'Studio', 'Hotel Apartment'],
                'villa': ['Villa', 'Mansions', 'Mansion'],
                'townhouse': ['Townhouse'],
                'penthouse': ['Penthouse', 'Duplex', 'Triplex'],
            }
            expected_cats = type_map.get(pt, [])
            actual_cat = top.get('category', '')
            if expected_cats and actual_cat and actual_cat not in expected_cats:
                log_issue('ERROR', test_id, 'property_type_compliance', f'Not relaxed but category {actual_cat} not in {expected_cats}', (actual_cat, expected_cats))

    # Check recommendation confidence
    rc = recs.get('recommendationConfidence', {})
    if rc:
        conf = safe_int(rc.get('confidence'))
        if conf < 0 or conf > 100:
            log_issue('ERROR', test_id, 'recConfidence', f'Confidence out of range: {conf}', conf)

    # Check sorting by goal
    goal = profile.get('goal', 'balanced')
    if goal == 'rental_income' and len(recommendations) > 1:
        rois = [safe_float(p.get('roi', {}).get('netROI', 0)) for p in recommendations if p.get('propertyType') == 'ready']
        if rois and rois != sorted(rois, reverse=True):
            log_issue('WARN', test_id, 'sorting', 'Rental income goal but results not sorted by ROI', rois)

    stats['passed'] += 1


def run_tests():
    """Run 100+ test combinations."""

    # ─── Systematic combinations ───
    systematic = list(itertools.product(
        GOALS[:4],           # 4 goals
        BUDGETS[:4],         # 4 standard budgets
        PROPERTY_TYPES[:4],  # 4 property types
        BEDROOMS[:4],        # 4 bedroom types
        RISKS[:3],           # 3 risk levels
    ))
    # = 4 × 4 × 4 × 4 × 3 = 768 combinations — too many, sample 60

    random.seed(42)
    sampled = random.sample(systematic, min(60, len(systematic)))

    test_num = 0
    for goal, budget, ptype, beds, risk in sampled:
        test_num += 1
        test_id = f'sys_{test_num:03d}'
        profile = {
            'goal': goal,
            'budget': budget,
            'property_type': ptype,
            'bedrooms': beds,
            'risk': risk,
            'location': 'any',
            'ready_offplan': 'ready',
        }
        try:
            recs = generate_recommendations(profile)
            validate_response(recs, profile, test_id)
        except Exception as e:
            stats['failed'] += 1
            log_issue('ERROR', test_id, 'exception', str(e), None)

    # ─── Edge cases ───
    edge_cases = [
        # Extreme budgets
        {'goal': 'balanced', 'budget': 'custom:50000', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': 'custom:10000000', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': 'custom:0', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': 'custom:1', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},

        # Empty profile
        {},
        {'goal': ''},
        {'budget': ''},
        {'property_type': ''},
        {'bedrooms': ''},

        # Mismatched combos
        {'goal': 'rental_income', 'budget': '5m+', 'property_type': 'villa', 'bedrooms': 'studio', 'risk': 'low', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'capital_growth', 'budget': '500k-1m', 'property_type': 'penthouse', 'bedrooms': '3', 'risk': 'high', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'holiday_home', 'budget': '1m-2m', 'property_type': 'townhouse', 'bedrooms': 'studio', 'risk': 'low', 'location': 'Palm Jumeirah', 'ready_offplan': 'ready'},

        # Specific locations
        {'goal': 'balanced', 'budget': '500k-1m', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'Business Bay', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': '500k-1m', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'Downtown Dubai', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': '500k-1m', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'Dubai Marina', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': '500k-1m', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'Jumeirah Village Circle', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': '500k-1m', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'Palm Jumeirah', 'ready_offplan': 'ready'},

        # Off-plan
        {'goal': 'balanced', 'budget': '1m-2m', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'offplan'},
        {'goal': 'balanced', 'budget': '1m-2m', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'either'},

        # All empty/None
        {'goal': None, 'budget': None, 'property_type': None, 'bedrooms': None, 'risk': None, 'location': None, 'ready_offplan': None},

        # Custom budgets at boundaries
        {'goal': 'balanced', 'budget': 'custom:500000', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': 'custom:1000000', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': 'custom:2000000', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': 'custom:5000000', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},

        # All property types with all bedrooms
        {'goal': 'balanced', 'budget': '2m-5m', 'property_type': 'villa', 'bedrooms': 'studio', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': '2m-5m', 'property_type': 'villa', 'bedrooms': '1', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': '2m-5m', 'property_type': 'villa', 'bedrooms': '2', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': '2m-5m', 'property_type': 'villa', 'bedrooms': '3', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': '500k-1m', 'property_type': 'penthouse', 'bedrooms': 'studio', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': '500k-1m', 'property_type': 'penthouse', 'bedrooms': '1', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': '500k-1m', 'property_type': 'townhouse', 'bedrooms': 'studio', 'risk': 'medium', 'location': 'any', 'ready_offplan': 'ready'},

        # Risk filtering
        {'goal': 'balanced', 'budget': '500k-1m', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'low', 'location': 'any', 'ready_offplan': 'ready'},
        {'goal': 'balanced', 'budget': '500k-1m', 'property_type': 'apartment', 'bedrooms': '1', 'risk': 'high', 'location': 'any', 'ready_offplan': 'ready'},
    ]

    for i, profile in enumerate(edge_cases):
        test_num += 1
        test_id = f'edge_{test_num:03d}'
        try:
            recs = generate_recommendations(profile)
            validate_response(recs, profile, test_id)
        except Exception as e:
            stats['failed'] += 1
            log_issue('ERROR', test_id, 'exception', str(e), None)

    # ─── Random fuzz tests ───
    all_budgets = BUDGETS + ['custom:' + str(random.randint(100000, 8000000)) for _ in range(10)]
    for i in range(30):
        test_num += 1
        test_id = f'fuzz_{test_num:03d}'
        profile = {
            'goal': random.choice(GOALS),
            'budget': random.choice(all_budgets),
            'property_type': random.choice(PROPERTY_TYPES),
            'bedrooms': random.choice(BEDROOMS),
            'risk': random.choice(RISKS),
            'location': random.choice(LOCATIONS),
            'ready_offplan': random.choice(READY_OFFPLAN),
        }
        try:
            recs = generate_recommendations(profile)
            validate_response(recs, profile, test_id)
        except Exception as e:
            stats['failed'] += 1
            log_issue('ERROR', test_id, 'exception', str(e), None)

    return test_num


if __name__ == '__main__':
    print('=' * 80)
    print('APIL Rigorous Edge-Case Test Suite')
    print(f'Started: {datetime.now().isoformat()}')
    print(f'Data: {len(ready_props)} ready, {len(offplan_props)} offplan, {len(communities)} communities, {len(developers)} developers, {len(projects)} projects')
    print('=' * 80)

    total = run_tests()

    print()
    print('=' * 80)
    print('TEST SUMMARY')
    print('=' * 80)
    print(f'Total tests:    {stats["total"]}')
    print(f'Passed:         {stats["passed"]}')
    print(f'Failed:         {stats["failed"]}')
    print(f'Empty results:  {stats["empty"]}')
    print(f'Errors:         {stats["errors"]}')
    print(f'Warnings:       {stats["warnings"]}')
    print(f'Total issues:   {len(issues)}')
    print()

    # Group issues by type
    errors = [i for i in issues if i['severity'] == 'ERROR']
    warnings = [i for i in issues if i['severity'] == 'WARN']
    infos = [i for i in issues if i['severity'] == 'INFO']

    if errors:
        print(f'\n{"=" * 80}')
        print(f'ERRORS ({len(errors)})')
        print(f'{"=" * 80}')
        # Group by field
        by_field = {}
        for e in errors:
            field_key = e['field'].split('[')[0]
            by_field.setdefault(field_key, []).append(e)
        for field, items in sorted(by_field.items(), key=lambda x: -len(x[1])):
            print(f'\n  [{field}] — {len(items)} errors')
            seen = set()
            for item in items:
                msg_key = item['message'][:80]
                if msg_key not in seen:
                    seen.add(msg_key)
                    print(f'    • {item["test_id"]}: {item["message"]}')
                    if item['value']:
                        print(f'      value: {item["value"][:100]}')

    if warnings:
        print(f'\n{"=" * 80}')
        print(f'WARNINGS ({len(warnings)})')
        print(f'{"=" * 80}')
        by_field = {}
        for w in warnings:
            field_key = w['field'].split('[')[0]
            by_field.setdefault(field_key, []).append(w)
        for field, items in sorted(by_field.items(), key=lambda x: -len(x[1])):
            print(f'\n  [{field}] — {len(items)} warnings')
            seen = set()
            for item in items[:5]:  # Show first 5 unique
                msg_key = item['message'][:80]
                if msg_key not in seen:
                    seen.add(msg_key)
                    print(f'    • {item["test_id"]}: {item["message"]}')
                    if item['value']:
                        print(f'      value: {item["value"][:100]}')
            if len(items) > 5:
                print(f'    ... and {len(items) - 5} more')

    # Save full report
    report = {
        'summary': stats,
        'total_issues': len(issues),
        'errors': len(errors),
        'warnings': len(warnings),
        'infos': len(infos),
        'issues': issues,
        'timestamp': datetime.now().isoformat(),
    }
    report_path = Path(__file__).parent / 'data' / 'test_results.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f'\nFull report saved to: {report_path}')
    print('=' * 80)
