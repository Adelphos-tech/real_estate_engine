/**
 * VerdictSection — Always visible. Dynamic recommendation display.
 *
 * Changes based on:
 *   - Property type (ready vs off-plan): different recommendation vocabulary
 *   - Investor goal: different "Why Buy" / "Key Risks" content
 *   - Confidence level: confidence banner for low confidence
 */
import {
  CheckCircle2, AlertTriangle, Sparkles, DollarSign, Info,
} from 'lucide-react';
import { useState } from 'react';
import type { ReportContext } from '../ReportContext';
import {
  isReady, isOffPlan, isRentalGoal, isGrowthGoal, isEndUser, isLowConfidence,
  translateRuleFlag, getConfidenceLabel, getConfidenceColor,
  decisionConfidence, evidenceWording,
} from '../ReportContext';
import { ScoreRing, MarketPositionBadge, formatAED } from '../../components/Shared';
import { CalcTracePanel } from './CalcTracePanel';

const safeVal = (v: any): number | null => {
  if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) return null;
  return v;
};

const REC_DISPLAY: Record<string, { label: string; color: string; bg: string; emoji: string }> = {
  'STRONG BUY': { label: 'Buy', color: '#16a34a', bg: 'bg-green-50', emoji: '🟢' },
  'BUY': { label: 'Buy', color: '#16a34a', bg: 'bg-green-50', emoji: '🟢' },
  'HOLD': { label: 'Buy if Negotiated', color: '#f59e0b', bg: 'bg-amber-50', emoji: '🟡' },
  'CAUTION': { label: 'Watchlist', color: '#f97316', bg: 'bg-orange-50', emoji: '🟠' },
  'REVIEW': { label: 'Needs Review', color: '#6b7280', bg: 'bg-gray-50', emoji: '⚪' },
  'INSUFFICIENT_DATA': { label: 'Insufficient Data', color: '#dc2626', bg: 'bg-red-50', emoji: '🔴' },
  'AVOID': { label: 'Avoid', color: '#dc2626', bg: 'bg-red-50', emoji: '🔴' },
};

function getRecDisplay(rec: string) {
  return REC_DISPLAY[rec] || REC_DISPLAY['REVIEW'];
}

function scoreContext(value: number | null): { label: string; color: string } {
  if (value === null) return { label: 'N/A', color: 'text-gray-400' };
  if (value >= 80) return { label: 'Excellent', color: 'text-green-600' };
  if (value >= 65) return { label: 'Good', color: 'text-blue-600' };
  if (value >= 50) return { label: 'Fair', color: 'text-amber-600' };
  if (value >= 35) return { label: 'Weak', color: 'text-orange-600' };
  return { label: 'Poor', color: 'text-red-500' };
}

interface VerdictSectionProps {
  property: any;
  topRec: any;
  ctx: ReportContext;
  community: any;
  project: any;
}

function ScoreWeightsTable({ breakdown, weights, weightedSum, availableWeight, investmentScore }: {
  breakdown: Record<string, number | null>;
  weights: Record<string, number>;
  weightedSum: number | null;
  availableWeight: number | null;
  investmentScore: number | null;
}) {
  const [expanded, setExpanded] = useState(false);

  const componentLabels: Record<string, string> = {
    developer: 'Developer', pricing: 'Pricing', paymentPlan: 'Payment Plan',
    growth: 'Growth', supply: 'Supply', liquidity: 'Liquidity',
    rental: 'Rental', roi: 'ROI',
  };

  const rows = Object.entries(weights)
    .filter(([key]) => breakdown[key] != null)
    .map(([key, weight]) => {
      const score = breakdown[key] ?? 0; // OK: already filtered to non-null via .filter above
      const contribution = (score * weight) / (availableWeight || 100);
      return { key, label: componentLabels[key] || key, weight, score, contribution };
    });

  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-left p-2 bg-white/30 rounded-lg"
      >
        <span className="text-xs font-semibold text-apil-gray-500 uppercase">How is the score calculated?</span>
        <span className="text-xs text-apil-gray-400">{expanded ? 'Hide' : 'Show'}</span>
      </button>
      {expanded && (
        <div className="mt-2 p-3 bg-white/50 rounded-lg">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-apil-gray-200">
                <th className="text-left py-1.5 font-semibold text-apil-gray-500">Component</th>
                <th className="text-center py-1.5 font-semibold text-apil-gray-500">Score</th>
                <th className="text-center py-1.5 font-semibold text-apil-gray-500">Weight</th>
                <th className="text-right py-1.5 font-semibold text-apil-gray-500">Contribution</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.key} className="border-b border-apil-gray-100">
                  <td className="py-1.5 text-apil-gray-700">{row.label}</td>
                  <td className="py-1.5 text-center font-semibold text-apil-gray-700">{Math.round(row.score)}</td>
                  <td className="py-1.5 text-center text-apil-gray-500">{row.weight}%</td>
                  <td className="py-1.5 text-right font-semibold text-apil-gray-700">{row.contribution.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-apil-gray-200">
                <td className="py-2 font-bold text-apil-gray-900" colSpan={3}>Weighted Sum ÷ Available Weight</td>
                <td className="py-2 text-right font-bold text-apil-gray-900">
                  {weightedSum != null ? weightedSum.toFixed(1) : '—'} ÷ {availableWeight ?? 100}
                </td>
              </tr>
              <tr>
                <td className="py-1 font-bold text-blue-600" colSpan={3}>Final Investment Score</td>
                <td className="py-1 text-right font-bold text-blue-600">{investmentScore != null ? `${investmentScore}/100` : 'N/A'}</td>
              </tr>
            </tfoot>
          </table>
          <p className="text-[10px] text-apil-gray-400 mt-2">
            Formula: Final Score = Σ(component_score × weight) / Σ(active_weights).
            Missing components are excluded from both numerator and denominator.
          </p>
        </div>
      )}
    </div>
  );
}

export function VerdictSection({ property, topRec, ctx, community, project }: VerdictSectionProps) {
  const overallScore = (topRec as any)?.investmentScore ?? property.overallScore ?? property.propertyScore ?? property.offplanScore ?? null;
  const recommendation = topRec?.recommendation || 'REVIEW';
  const recDisplay = getRecDisplay(recommendation);
  const confidenceScore = topRec?.confidenceScore || 0;
  const confidenceLevel = getConfidenceLabel(confidenceScore);
  const confidenceColor = getConfidenceColor(confidenceScore);
  const decConfidence = decisionConfidence(ctx);
  const evidenceText = evidenceWording(ctx);
  const breakdown = topRec?.scoreBreakdown || {};
  const rulesFlags = topRec?.rulesFlags || [];

  // ── Dynamic "Why Buy" reasons based on property type + goal ──
  const buyReasons: string[] = [];
  const mv = topRec?.marketValuation;
  const discountPct = mv?.discountPct;
  const priceOpp = topRec?.priceOpportunity || {};
  const futureApp = topRec?.futureAppreciation || {};
  const devData = topRec?.developerData || {};
  const ppAnalysis = topRec?.paymentPlanAnalysis || {};
  const netROI = safeVal(property.netROI);
  const growth12 = safeVal(property.growth12m);

  if (isOffPlan(ctx)) {
    // Off-plan specific reasons
    if ((priceOpp.priceOpportunityScore || 0) >= 80)
      buyReasons.push(`Launch price ${Math.abs(priceOpp.priceDifferencePct || 0).toFixed(1)}% below fair market value`);
    if ((futureApp.futureAppreciationScore || 0) >= 80)
      buyReasons.push(`Projected ${futureApp.potentialGainPct}% capital gain over ${futureApp.completionYears} years`);
    if ((devData.developerScore || 0) >= 75)
      buyReasons.push(`Trusted developer: ${devData.developerName}`);
    if ((ppAnalysis.paymentPlanScore || 0) >= 85)
      buyReasons.push(`Favorable payment plan: ${ppAnalysis.downPaymentPct}% down, ${ppAnalysis.structure}`);
    if ((ppAnalysis.equityGainPct || 0) > 100)
      buyReasons.push(`Equity gain of ${ppAnalysis.equityGainPct}% on down payment (${ppAnalysis.leverageRatio}x leverage)`);
    if ((topRec?.communityData?.communityScore || 0) >= 75)
      buyReasons.push('Strong area fundamentals with upcoming infrastructure');
  } else {
    // Ready property reasons
    if (discountPct != null && discountPct < -15)
      buyReasons.push(`Strong discount: ${Math.abs(discountPct).toFixed(1)}% below fair market value`);
    else if (discountPct != null && discountPct < -5)
      buyReasons.push(`Priced ${Math.abs(discountPct).toFixed(1)}% below fair value`);
    else if (discountPct != null && Math.abs(discountPct) <= 5)
      buyReasons.push('Priced fairly at market value');

    if (isRentalGoal(ctx) && netROI != null && netROI >= 8)
      buyReasons.push(`Strong rental yield: ${netROI.toFixed(1)}% net`);
    if (isGrowthGoal(ctx) && growth12 != null && growth12 > 10)
      buyReasons.push(`Solid 12-month price growth: ${growth12}%`);
    if ((property.liquidityScore || 0) >= 80)
      buyReasons.push('Excellent resale liquidity');
    if ((property.developerScore || 0) >= 75)
      buyReasons.push('Reputable developer with track record');
    if ((breakdown.community || 0) >= 75)
      buyReasons.push('Strong area fundamentals');
    if (isRentalGoal(ctx) && ctx.hasRentalEvidence)
      buyReasons.push(`Rental estimate based on ${topRec?.dataQuality?.rentCount || 0} comparable lease transaction${(topRec?.dataQuality?.rentCount || 0) !== 1 ? 's' : ''}`);
  }

  if (buyReasons.length === 0 && (property.reasons || []).length > 0)
    buyReasons.push(...property.reasons.slice(0, 3));

  // ── Dynamic risks based on property type ──
  const risks: string[] = [];
  if (isOffPlan(ctx)) {
    if ((devData.developerScore || 0) < 70)
      risks.push(`Developer score ${devData.developerScore}/100 — below average track record`);
    if ((devData.delayRisk || '') === 'High')
      risks.push('High delivery delay risk');
    if ((priceOpp.priceDifferencePct || 0) > 10)
      risks.push(`Priced ${priceOpp.priceDifferencePct}% above fair market value`);
    if ((topRec?.communityData?.supplyIndex || 0) > 70)
      risks.push('Significant future supply in area');
    if ((topRec?.risk?.overallRisk || 0) > 30)
      risks.push(`Overall risk score ${topRec?.risk?.overallRisk}/100`);
    risks.push('No rental income until construction completion');
    if (!ctx.hasComparableSales)
      risks.push('No comparable sales available');
    if (!ctx.hasRentalEvidence)
      risks.push('No rental transaction evidence available');
    if (!futureApp.futureValue)
      risks.push('Capital growth cannot currently be estimated');
  } else {
    if (discountPct != null && discountPct > 15)
      risks.push(`High premium: ${discountPct.toFixed(1)}% above fair value — negotiate down`);
    if (!ctx.hasRentalEvidence && isRentalGoal(ctx))
      risks.push('No rental evidence — income projections unavailable');
    if (ctx.hasRentalEvidence && (topRec?.dataQuality?.rentCount || 0) < 10)
      risks.push(`Rental estimate based on only ${topRec?.dataQuality?.rentCount} leases`);
    if (ctx.hasComparableSales && (topRec?.dataQuality?.salesCount || 0) < 5)
      risks.push(`Only ${topRec?.dataQuality?.salesCount} comparable sales — limited market evidence`);
    if (!ctx.hasPriceHistory)
      risks.push('Insufficient price history for growth estimate');
    if ((property.developerScore || 0) < 50)
      risks.push('Weak developer track record');
    if ((property.risk?.components?.futureSupplyRisk || 0) > 25)
      risks.push('Moderate future supply in area');
  }
  if (isLowConfidence(ctx))
    risks.push(`Low data confidence (${confidenceScore}%) — evidence is thin`);
  if (risks.length === 0) risks.push('No major risks identified');

  // ── Actionable advice ──
  const askingPrice = safeVal(property.askingPrice) || 0;
  const fairValue = topRec?.fairValue || topRec?.marketValuation?.fairValueTotal;
  const advice: string[] = [];
  if (isOffPlan(ctx)) {
    if ((priceOpp.priceDifferencePct || 0) > 5)
      advice.push('Negotiate the launch price or wait for a promotional offer');
    if ((devData.delayRisk || '') === 'High')
      advice.push('Add a penalty clause for late delivery in your contract');
    if ((ppAnalysis.downPaymentPct || 0) > 30)
      advice.push('Consider negotiating a lower down payment to reduce upfront risk');
    if (advice.length === 0)
      advice.push(`Hold until completion (~${futureApp.completionYears || '2-3'} years) to realize full capital gain`);
  } else {
    if (discountPct != null && discountPct > 5 && fairValue) {
      const offerPrice = Math.round(fairValue);
      const newROI = netROI != null ? ((netROI * askingPrice) / offerPrice).toFixed(1) : null;
      advice.push(`Offer ${formatAED(offerPrice)} instead of ${formatAED(askingPrice)}${newROI ? ` to improve ROI from ${netROI}% to ~${newROI}%` : ''}`);
    }
    if (discountPct != null && discountPct < -10)
      advice.push('Price is below market — current pricing appears attractive. Availability may change as inventory is sold.');
    if (!ctx.hasRentalEvidence && isRentalGoal(ctx))
      advice.push('Verify rental income with a local agent before committing');
    if (isLowConfidence(ctx))
      advice.push('Request more transaction data or wait for additional evidence before deciding');
    if (advice.length === 0)
      advice.push(`Hold for ${(growth12 || 0) > 10 ? '2–4' : '3–5'} years to realize full return potential`);
  }

  // ── Goal alignment ──
  const goalLabel = ctx.investorGoal.replace(/_/g, ' ').toLowerCase();
  let goalAlignment = '';
  if (isEndUser(ctx)) {
    goalAlignment = `This property is evaluated for livability and lifestyle fit. Community amenities, accessibility, and future value potential are the primary considerations.`;
  } else if (isOffPlan(ctx)) {
    if (isGrowthGoal(ctx))
      goalAlignment = `This off-plan property aligns with your capital growth objective — projected ${futureApp.potentialGainPct || 'N/A'}% appreciation over ${futureApp.completionYears || 'N/A'} years with ${ppAnalysis.leverageRatio || 'N/A'}x leverage on your down payment.`;
    else
      goalAlignment = `This off-plan property offers a balanced profile — projected capital gain of ${futureApp.potentialGainPct || 'N/A'}% and post-handover rental yield of ${topRec?.postHandoverROI?.netROI || 'N/A'}%.`;
  } else if (isRentalGoal(ctx)) {
    if (netROI != null && netROI >= 8)
      goalAlignment = `This property aligns strongly with your rental income objective — estimated ${netROI.toFixed(1)}% net yield is above the Dubai average.`;
    else if (netROI != null && netROI >= 6)
      goalAlignment = `This property has moderate alignment with your rental income goal — ${netROI.toFixed(1)}% net yield is reasonable but not exceptional.`;
    else if (!ctx.hasRentalEvidence)
      goalAlignment = `This property aligns poorly with your rental income objective — no rental evidence is available for this unit type.`;
    else if (netROI == null && ctx.hasRentalEvidence)
      goalAlignment = `Limited rental evidence (${topRec?.dataQuality?.rentCount || 0} leases) — ROI could not be calculated. Verify rental rates with a local agent before deciding.`;
    else
      goalAlignment = `This property may not meet your rental income expectations — estimated yield of ${netROI != null ? netROI.toFixed(1) : 'N/A'}% is below typical targets.`;
  } else if (isGrowthGoal(ctx)) {
    if (growth12 != null && growth12 > 10)
      goalAlignment = `This property aligns well with your capital growth objective — prices in this area have risen ${growth12}% over the past year.`;
    else if (growth12 != null && growth12 > 0)
      goalAlignment = `This property has moderate alignment with your capital growth goal — price growth of ${growth12}% is positive but modest.`;
    else
      goalAlignment = `This property aligns poorly with your capital growth objective — there is insufficient price appreciation history.`;
  } else {
    goalAlignment = `This property offers a balanced profile${netROI != null ? ` with ${netROI.toFixed(1)}% net yield` : ''}${growth12 != null ? ` and ${growth12}% price growth` : ''}, suitable for a ${goalLabel} strategy.`;
  }

  // Score component bars
  const componentLabels: Record<string, string> = {
    price: 'Price', roi: 'ROI', rental: 'Rental', growth: 'Growth', liquidity: 'Liquidity',
    community: 'Area', developer: 'Developer', project: 'Project', risk: 'Risk',
    supplyRisk: 'Supply Risk', paymentPlan: 'Payment Plan',
    futureAppreciation: 'Future Appreciation',
  };
  const components = Object.entries(breakdown)
    .filter(([k, v]: [string, any]) => v !== null && v !== undefined)
    .slice(0, 6);

  // End user: hide investment score, show livability
  if (isEndUser(ctx)) {
    return (
      <div className="space-y-4">
        <div className="premium-card p-6 bg-blue-50 border-l-4" style={{ borderLeftColor: '#2563eb' }}>
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-1">Property Assessment</p>
              <h2 className="text-3xl font-bold text-blue-700">{property.title}</h2>
              <p className="text-sm text-apil-gray-600 mt-1">{property.area} · {property.bedType} · {formatAED(property.askingPrice)}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-apil-gray-500">Livability Score</p>
              <p className="text-4xl font-bold text-blue-600">{community?.livabilityIndex || '—'}<span className="text-lg text-apil-gray-400">/100</span></p>
            </div>
          </div>
          <p className="text-sm text-apil-gray-700 leading-relaxed">{goalAlignment}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Verdict Card */}
      <div className={`premium-card p-6 ${recDisplay.bg} border-l-4`} style={{ borderLeftColor: recDisplay.color }}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <p className="text-xs font-semibold text-apil-gray-500 uppercase">Investment Verdict</p>
              {isOffPlan(ctx) && (
                <span className="text-xs bg-apil-blue/10 text-apil-blue px-2 py-0.5 rounded-full font-medium">Off-Plan</span>
              )}
            </div>
            <h2 className="text-4xl font-bold" style={{ color: recDisplay.color }}>{recDisplay.label}</h2>
            <p className="text-sm text-apil-gray-600 mt-1">{property.title}</p>
            <p className="text-xs text-apil-gray-500">{property.area || 'Dubai'} · {property.bedType || 'N/A'} · {formatAED(property.askingPrice)}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-apil-gray-500">{isOffPlan(ctx) ? 'Investment' : 'Investment'} Quality</p>
            <p className="text-5xl font-bold" style={{ color: recDisplay.color }}>{overallScore != null ? overallScore : 'N/A'}<span className="text-lg text-apil-gray-400">{overallScore != null ? '/100' : ''}</span></p>
            <p className={`text-xs font-semibold mt-1 ${confidenceColor}`}>{confidenceLevel} ({confidenceScore}%)</p>
            <p className="text-[10px] text-apil-gray-400 mt-0.5">Decision Confidence: {decConfidence.replace(/_/g, ' ')}</p>
          </div>
        </div>

        {/* Score component bars */}
        {components.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-4 p-4 bg-white/50 rounded-lg">
            {components.map(([key, val]: [string, any]) => {
              const sc = scoreContext(val);
              return (
                <div key={key}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-apil-gray-600">{componentLabels[key] || key}</span>
                    <span className={`text-xs font-semibold ${sc.color}`}>{sc.label}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-apil-gray-200 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${val == null ? 'bg-gray-300' : val >= 80 ? 'bg-green-500' : val >= 65 ? 'bg-blue-500' : val >= 50 ? 'bg-amber-500' : 'bg-red-400'}`} style={{ width: `${val != null ? Math.min(100, val) : 0}%` }} />
                    </div>
                    <span className="text-xs font-bold text-apil-gray-700">{val != null ? Math.round(val) : 'N/A'}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Score weights breakdown — makes Investment Score auditable */}
        {topRec?.scoreWeights && components.length > 0 && (
          <ScoreWeightsTable
            breakdown={breakdown}
            weights={topRec.scoreWeights}
            weightedSum={topRec.weightedSum}
            availableWeight={topRec.availableWeight}
            investmentScore={overallScore}
          />
        )}
        <CalcTracePanel trace={topRec?.calcTrace?.score} section="score" title="Investment Score" />
      </div>

      {/* Low confidence banner */}
      {(isLowConfidence(ctx) || decConfidence === 'VERY_LOW' || decConfidence === 'LOW') && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-sm font-semibold text-amber-900">{evidenceText}</h3>
              <p className="text-xs text-amber-700 mt-1">
                This recommendation is based on limited market evidence. Some metrics may be less reliable.
                Consider gathering more data before making a final decision.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Why Buy + Key Risks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="premium-card p-5">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-5 h-5 text-green-500" />
            <h3 className="font-semibold text-apil-gray-900">
              {isOffPlan(ctx) ? 'Why Buy' : 'Why Buy'}
            </h3>
          </div>
          <ul className="space-y-2">
            {buyReasons.slice(0, 3).map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-apil-gray-700">
                <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />{r}
              </li>
            ))}
          </ul>
        </div>
        <div className="premium-card p-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <h3 className="font-semibold text-apil-gray-900">Key Risks</h3>
          </div>
          <ul className="space-y-2">
            {risks.slice(0, 3).map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-apil-gray-700">
                <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />{r}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Goal Alignment */}
      <div className="premium-card p-5">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles className="w-4 h-4 text-apil-blue" />
          <h3 className="text-sm font-semibold text-apil-gray-900">Your Goal: <span className="capitalize">{goalLabel}</span></h3>
        </div>
        <p className="text-sm text-apil-gray-700 leading-relaxed">{goalAlignment}</p>
      </div>

      {/* Actionable Advice */}
      <div className="premium-card p-5 bg-apil-blue/5">
        <div className="flex items-center gap-2 mb-3">
          <DollarSign className="w-5 h-5 text-apil-blue" />
          <h3 className="font-semibold text-apil-gray-900">What Should You Do?</h3>
        </div>
        <ul className="space-y-2">
          {advice.map((a, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-apil-gray-700">
              <span className="w-1.5 h-1.5 rounded-full bg-apil-blue flex-shrink-0 mt-1.5" />{a}
            </li>
          ))}
        </ul>
      </div>

      {/* Rule flags — human readable */}
      {rulesFlags.length > 0 && (
        <div className="premium-card p-4 bg-amber-50/30">
          <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-2">Validation Notes</p>
          <ul className="space-y-1.5">
            {rulesFlags.map((flag: string, i: number) => (
              <li key={i} className="flex items-start gap-2 text-xs text-apil-gray-600">
                <Info className="w-3 h-3 text-amber-500 flex-shrink-0 mt-0.5" />
                {translateRuleFlag(flag)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
