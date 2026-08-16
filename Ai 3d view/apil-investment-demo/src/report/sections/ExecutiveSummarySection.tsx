/**
 * ExecutiveSummarySection — Clean, product-grade summary.
 *
 * Shows: Verdict + Investment Score + Investor Fit + 3 Strengths + 3 Risks
 * No score component bars, no goal alignment paragraph, no validation notes.
 */
import { CheckCircle2, AlertTriangle, TrendingDown, TrendingUp, Minus } from 'lucide-react';
import type { ReportContext } from '../ReportContext';
import { isOffPlan, isRentalGoal, isGrowthGoal, isLowConfidence } from '../ReportContext';
import { formatAED } from '../../components/Shared';
import { CalcTracePanel } from './CalcTracePanel';

const safeVal = (v: any): number | null => {
  if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) return null;
  return v;
};

const REC_DISPLAY: Record<string, { label: string; color: string; bg: string }> = {
  'STRONG BUY': { label: 'Buy', color: '#16a34a', bg: 'bg-green-50' },
  'BUY': { label: 'Buy', color: '#16a34a', bg: 'bg-green-50' },
  'BUY IF NEGOTIATED': { label: 'Buy if Negotiated', color: '#16a34a', bg: 'bg-green-50' },
  'HOLD': { label: 'Hold', color: '#f59e0b', bg: 'bg-amber-50' },
  'WATCHLIST': { label: 'Watchlist', color: '#f97316', bg: 'bg-orange-50' },
  'REVIEW': { label: 'Needs Review', color: '#6b7280', bg: 'bg-gray-50' },
  'INSUFFICIENT_DATA': { label: 'Insufficient Data', color: '#dc2626', bg: 'bg-red-50' },
  'AVOID': { label: 'Avoid', color: '#dc2626', bg: 'bg-red-50' },
};

function getRecDisplay(rec: string) {
  return REC_DISPLAY[rec] || REC_DISPLAY['REVIEW'];
}

interface ExecutiveSummaryProps {
  property: any;
  topRec: any;
  ctx: ReportContext;
  investorFit?: any;
  strategySummary?: string;
}

export function ExecutiveSummarySection({ property, topRec, ctx, investorFit, strategySummary }: ExecutiveSummaryProps) {
  const overallScore = (topRec as any)?.investmentScore ?? property.overallScore ?? property.propertyScore ?? property.offplanScore ?? property.readyScore ?? null;
  const recommendation = topRec?.recommendation || 'REVIEW';
  const recDisplay = getRecDisplay(recommendation);
  const confidenceScore = topRec?.confidenceScore || 0;
  // Evidence quality from data counts
  const dq = (topRec as any)?.dataQuality || {};
  const evSales = dq.salesCount || dq.comparableCount || 0;
  const evRent = dq.rentCount || 0;
  const evTotal = evSales + evRent;
  const evidenceQuality = evTotal === 0 ? 'Very Low' : evTotal <= 2 ? 'Low' : evTotal <= 10 ? 'Moderate' : evTotal <= 30 ? 'High' : 'Very High';
  const evidenceColor = evTotal <= 2 ? 'text-red-500' : evTotal <= 10 ? 'text-amber-600' : evTotal <= 30 ? 'text-blue-600' : 'text-green-600';
  const fitScore = investorFit?.fitScore ?? topRec?.investorFit?.fitScore ?? 0;
  const fitLabel = investorFit?.fitLabel ?? topRec?.investorFit?.fitLabel ?? '—';
  const mismatchReasons = investorFit?.mismatchReasons ?? topRec?.investorFit?.mismatchReasons ?? [];
  const matchReasons = investorFit?.matchReasons ?? topRec?.investorFit?.matchReasons ?? [];

  // ── Score Breakdown ──
  const scoreBreakdown = topRec?.scoreBreakdown || topRec?.subScores || {};
  const lostPoints: string[] = topRec?.lostPoints || [];
  const scoreFactors: { label: string; score: number; impact: string }[] = [];
  const FACTOR_LABELS: Record<string, string> = {
    price: 'Pricing', roi: 'ROI', rental: 'Rental', liquidity: 'Liquidity',
    community: 'Area', developer: 'Developer', project: 'Project',
    growth: 'Growth', supply: 'Supply',
  };
  if (scoreBreakdown && Object.keys(scoreBreakdown).length > 0) {
    for (const [key, val] of Object.entries(scoreBreakdown)) {
      const n = safeVal(val);
      if (n === null) continue;
      const label = FACTOR_LABELS[key] || key.charAt(0).toUpperCase() + key.slice(1);
      const impact = n >= 80 ? 'positive' : n >= 50 ? 'neutral' : 'negative';
      scoreFactors.push({ label, score: n, impact });
    }
  }

  // ── Strengths (top 3) ──
  const strengths: string[] = [];
  const mv = topRec?.marketValuation;
  const discountPct = mv?.discountPct;
  const priceOpp = topRec?.priceOpportunity || {};
  const futureApp = topRec?.futureAppreciation || {};
  const devData = topRec?.developerData || {};
  const ppAnalysis = topRec?.paymentPlanAnalysis || {};
  const netROI = safeVal(property.netROI);
  const growth12 = safeVal(property.growth12m);

  if (isOffPlan(ctx)) {
    if ((priceOpp.priceOpportunityScore || 0) >= 80)
      strengths.push(`Launch price ${Math.abs(priceOpp.priceDifferencePct || 0).toFixed(1)}% below fair market value`);
    if ((futureApp.futureAppreciationScore || 0) >= 80)
      strengths.push(`Projected ${futureApp.potentialGainPct}% capital gain over ${futureApp.completionYears} years`);
    if ((devData.developerScore || 0) >= 75)
      strengths.push(`Trusted developer: ${devData.developerName}`);
    if ((ppAnalysis.equityGainPct || 0) > 100)
      strengths.push(`${ppAnalysis.equityGainPct}% equity gain on down payment (${ppAnalysis.leverageRatio}x leverage)`);
  } else {
    if (discountPct != null && discountPct < -10)
      strengths.push(`${Math.abs(discountPct).toFixed(1)}% below fair market value`);
    if (isRentalGoal(ctx) && netROI != null && netROI >= 7)
      strengths.push(`Rental yield: ${netROI.toFixed(1)}% net`);
    if (isGrowthGoal(ctx) && growth12 != null && growth12 > 8)
      strengths.push(`Price growth: ${growth12}% in 12 months`);
    if ((property.liquidityScore || 0) >= 75)
      strengths.push('High resale liquidity');
    if ((property.developerScore || 0) >= 70)
      strengths.push('Reputable developer');
  }
  if (strengths.length === 0 && matchReasons.length > 0)
    strengths.push(...matchReasons.slice(0, 3));
  if (strengths.length === 0)
    strengths.push('Property meets basic investment criteria');

  // ── Risks (top 3) ──
  const risks: string[] = [];
  if (isOffPlan(ctx)) {
    if ((devData.developerScore || 0) < 70)
      risks.push(`Developer score ${devData.developerScore}/100 — below average`);
    if ((devData.delayRisk || '') === 'High')
      risks.push('High delivery delay risk');
    if ((topRec?.communityData?.supplyIndex || 0) > 70)
      risks.push('Significant future supply in area');
    risks.push('No rental income until handover');
  } else {
    if (discountPct != null && discountPct > 10)
      risks.push(`Priced ${discountPct.toFixed(1)}% above fair value`);
    if (ctx.hasRentalEvidence && (topRec?.dataQuality?.rentCount || 0) < 10 && (topRec?.dataQuality?.rentCount || 0) > 0)
      risks.push(`Limited rental evidence (${topRec?.dataQuality?.rentCount} leases)`);
    if (!ctx.hasRentalEvidence && isRentalGoal(ctx))
      risks.push('No rental evidence available');
    if ((property.developerScore || 0) < 50)
      risks.push('Weak developer track record');
  }
  if (isLowConfidence(ctx))
    risks.push(`Low evidence quality (${evSales} sales, ${evRent} rentals)`);
  if (risks.length === 0) risks.push('No major risks identified');

  // Add mismatch reasons as risks if fit is weak
  if (fitScore < 50 && mismatchReasons.length > 0) {
    mismatchReasons.slice(0, 2).forEach((r: string) => {
      if (!risks.includes(r)) risks.push(r);
    });
  }

  return (
    <div className="space-y-4">
      {/* Verdict Card — compact */}
      <div className={`premium-card p-6 ${recDisplay.bg} border-l-4`} style={{ borderLeftColor: recDisplay.color }}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-1">Verdict</p>
            <h2 className="text-3xl font-bold" style={{ color: recDisplay.color }}>{recDisplay.label}</h2>
            <p className="text-sm text-apil-gray-600 mt-1">{property.title}</p>
            <p className="text-xs text-apil-gray-500">{property.area || 'Dubai'} · {property.bedType || 'N/A'} · {formatAED(property.askingPrice)}</p>
          </div>
          <div className="text-right flex flex-col gap-3">
            <div>
              <p className="text-xs text-apil-gray-500">Investment Score</p>
              <p className="text-4xl font-bold" style={{ color: recDisplay.color }}>{overallScore != null ? overallScore : 'N/A'}<span className="text-lg text-apil-gray-400">{overallScore != null ? '/100' : ''}</span></p>
            </div>
            <div>
              <p className="text-xs text-apil-gray-500">Investor Fit</p>
              <p className="text-2xl font-bold text-apil-gray-700">{fitScore}<span className="text-sm text-apil-gray-400">/100</span></p>
              <p className="text-xs font-medium text-apil-gray-500">{fitLabel}</p>
            </div>
          </div>
        </div>

        {/* Evidence Quality + Strategy in one line */}
        <div className="flex items-center gap-4 text-xs">
          <span className={`font-semibold ${evidenceColor}`}>Evidence Quality: {evidenceQuality}</span>
          {strategySummary && <span className="text-apil-gray-500">· {strategySummary}</span>}
        </div>
      </div>

      {/* Score Breakdown — why the score is X */}
      {scoreFactors.length > 0 && (
        <div className="premium-card p-5">
          <h3 className="font-semibold text-apil-gray-900 mb-3">Why the Score is {overallScore != null ? `${overallScore}/100` : 'N/A'}</h3>
          <div className="space-y-2">
            {scoreFactors.map((f, i) => (
              <div key={i} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {f.impact === 'positive' ? (
                    <TrendingUp className="w-3.5 h-3.5 text-green-500" />
                  ) : f.impact === 'negative' ? (
                    <TrendingDown className="w-3.5 h-3.5 text-red-500" />
                  ) : (
                    <Minus className="w-3.5 h-3.5 text-amber-500" />
                  )}
                  <span className="text-sm text-apil-gray-700">{f.label}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-20 h-1.5 bg-apil-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${f.impact === 'positive' ? 'bg-green-400' : f.impact === 'negative' ? 'bg-red-400' : 'bg-amber-400'}`}
                      style={{ width: `${Math.min(100, f.score)}%` }}
                    />
                  </div>
                  <span className={`text-xs font-bold w-8 text-right ${f.impact === 'positive' ? 'text-green-600' : f.impact === 'negative' ? 'text-red-500' : 'text-amber-600'}`}>
                    {f.score}
                  </span>
                </div>
              </div>
            ))}
          </div>
          {lostPoints.length > 0 && (
            <div className="mt-3 pt-3 border-t border-apil-gray-100">
              <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-2">Score Deductions</p>
              <ul className="space-y-1">
                {lostPoints.slice(0, 4).map((lp, i) => (
                  <li key={i} className="text-xs text-apil-gray-600 flex items-start gap-1.5">
                    <span className="text-red-400 flex-shrink-0">−</span> {lp}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Calculation trace for score */}
      <CalcTracePanel trace={topRec?.calcTrace?.score} section="score" title="Investment Score Calculation" />

      {/* Strengths + Risks — two columns, max 3 each */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="premium-card p-5">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-5 h-5 text-green-500" />
            <h3 className="font-semibold text-apil-gray-900">Strengths</h3>
          </div>
          <ul className="space-y-2">
            {strengths.slice(0, 3).map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-apil-gray-700">
                <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />{r}
              </li>
            ))}
          </ul>
        </div>
        <div className="premium-card p-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <h3 className="font-semibold text-apil-gray-900">Risks</h3>
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

      {/* Investor Fit mismatch reasons — only if weak */}
      {fitScore < 60 && mismatchReasons.length > 0 && (
        <div className="premium-card p-4 bg-amber-50/30">
          <p className="text-xs font-semibold text-amber-700 uppercase mb-2">Why the fit score is {fitScore}/100</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
            {mismatchReasons.map((reason: string, i: number) => (
              <div key={i} className="flex items-center gap-2 text-xs text-amber-700">
                <span className="text-amber-500">⚠</span> {reason}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
