/**
 * ValuationSection — Fair value + comparable sales + discount/premium.
 * Consolidates what was in MarketSection's fair value + ComparableTransactionsCard.
 */
import { DollarSign, TrendingDown, TrendingUp, AlertTriangle } from 'lucide-react';
import type { ReportContext } from '../ReportContext';
import { isOffPlan } from '../ReportContext';
import { formatAED } from '../../components/Shared';
import { CalcTracePanel } from './CalcTracePanel';

const safeVal = (v: any): number | null => {
  if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) return null;
  return v;
};
const fmtAEDsafe = (v: any): string => {
  const n = safeVal(v);
  if (n === null) return '—';
  return formatAED(n);
};
const fmtPct = (v: any, prefix = ''): string => {
  const n = safeVal(v);
  if (n === null) return '—';
  return `${n > 0 ? prefix : ''}${n}%`;
};

interface ValuationSectionProps {
  property: any;
  topRec: any;
  ctx: ReportContext;
  community?: any;
  project?: any;
}

export function ValuationSection({ property, topRec, ctx, community, project }: ValuationSectionProps) {
  const askingPrice = safeVal(property.askingPrice) || 0;
  const mv = topRec?.marketValuation || {};
  const fairValue = safeVal(mv.fairValueTotal) ?? safeVal(topRec?.fairValue?.fairValue) ?? safeVal(topRec?.fairValue) ?? null;
  const discountPct = safeVal(mv.discountPct);
  const priceOpp = topRec?.priceOpportunity || {};
  const dq = topRec?.dataQuality || {};
  const salesCount = dq.salesCount || dq.comparableCount || 0;
  const compMedian = safeVal(topRec?.comparablePrice) ?? safeVal(project?.medianPrice) ?? null;
  const priceSqft = safeVal(topRec?.priceSqft) || safeVal(property.priceSqft) || 0;
  const compPriceSqft = safeVal(topRec?.comparablePriceSqft) || safeVal(project?.priceSqft) || 0;

  // Off-plan specific
  const futureApp = topRec?.futureAppreciation || {};
  const projectedValue = safeVal(futureApp.projectedValueAtHandover);
  const potentialGainPct = safeVal(futureApp.potentialGainPct);

  const confidenceScore = topRec?.confidenceScore || 0;
  const useRanges = confidenceScore < 70;

  // Evidence quality label for range notation
  const rentCount = (topRec as any)?.dataQuality?.rentCount || 0;
  const totalEvidence = salesCount + rentCount;
  const evidenceLabel = totalEvidence === 0 ? 'very low' : totalEvidence <= 2 ? 'low' : totalEvidence <= 10 ? 'moderate' : totalEvidence <= 30 ? 'high' : 'very high';
  // Use API-provided fair value range (from engine valuation), not fabricated ±8%
  const apiFairLow = safeVal(topRec?.fairValue?.fairValueLow);
  const apiFairHigh = safeVal(topRec?.fairValue?.fairValueHigh);
  const apiFairPoint = safeVal(topRec?.fairValue?.fairValuePointEstimate) ?? fairValue;
  const fairValueLow = apiFairLow != null ? apiFairLow : (fairValue != null && fairValue > 0 ? Math.round(fairValue * 0.92) : null);
  const fairValueHigh = apiFairHigh != null ? apiFairHigh : (fairValue != null && fairValue > 0 ? Math.round(fairValue * 1.08) : null);
  // Use exact point estimate for projected value — no fabricated range
  const projectedVal = safeVal(futureApp.projectedValueAtHandover) || safeVal(futureApp.futureValue);

  if (isOffPlan(ctx)) {
    return (
      <div className="space-y-4">
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <DollarSign className="w-5 h-5 text-blue-600" />
            <h3 className="font-semibold text-apil-gray-900">Valuation</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="p-4 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-xs text-apil-gray-500">Launch Price</p>
              <p className="text-xl font-bold text-apil-gray-900 mt-1">{fmtAEDsafe(askingPrice)}</p>
              {priceSqft > 0 && <p className="text-xs text-apil-gray-400">AED {priceSqft?.toFixed(0)}/sqft</p>}
            </div>
            <div className="p-4 bg-blue-50 rounded-lg text-center">
              <p className="text-xs text-apil-gray-500">Fair Market Value</p>
              <p className="text-xl font-bold text-blue-600 mt-1">{fmtAEDsafe(apiFairPoint)}</p>
              {apiFairLow != null && apiFairHigh != null && (
                <p className="text-[10px] text-apil-gray-400">Range: {fmtAEDsafe(apiFairLow)}–{fmtAEDsafe(apiFairHigh)}</p>
              )}
            </div>
            <div className="p-4 bg-green-50 rounded-lg text-center">
              <p className="text-xs text-apil-gray-500">Projected at Handover</p>
              <p className="text-xl font-bold text-green-600 mt-1">{projectedVal != null ? fmtAEDsafe(projectedVal) : 'N/A'}</p>
              {projectedVal != null && potentialGainPct != null && <p className="text-xs text-green-600">+{potentialGainPct}% gain</p>}
              {projectedVal == null && <p className="text-xs text-apil-gray-400">Insufficient growth data</p>}
            </div>
          </div>
          {discountPct != null && discountPct < 0 && (
            <div className="p-3 bg-green-50 rounded-lg text-sm text-green-700 flex items-center gap-2">
              <TrendingDown className="w-4 h-4" />
              <span><strong>{Math.abs(discountPct).toFixed(1)}% below market</strong> — launch price discount</span>
            </div>
          )}
          {discountPct != null && discountPct > 5 && (
            <div className="p-3 bg-red-50 rounded-lg text-sm text-red-700 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              <span><strong>{discountPct.toFixed(1)}% above market</strong> — property is overpriced. Negotiate toward fair value.</span>
            </div>
          )}
          <CalcTracePanel trace={topRec?.calcTrace?.valuation} section="valuation" title="Fair Market Value" />
        </div>
      </div>
    );
  }

  const priceDiffPct = compMedian != null && compMedian > 0 && askingPrice > 0
    ? Math.round(((askingPrice - compMedian) / compMedian) * 1000) / 10
    : null;

  return (
    <div className="space-y-4">
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <DollarSign className="w-5 h-5 text-blue-600" />
          <h3 className="font-semibold text-apil-gray-900">Valuation</h3>
        </div>

        {/* Price vs Fair Value */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="p-4 bg-apil-gray-50 rounded-lg text-center">
            <p className="text-xs text-apil-gray-500">Asking Price</p>
            <p className="text-xl font-bold text-apil-gray-900 mt-1">{fmtAEDsafe(askingPrice)}</p>
          </div>
          <div className="p-4 bg-blue-50 rounded-lg text-center">
            <p className="text-xs text-apil-gray-500">Fair Value</p>
            <p className="text-xl font-bold text-blue-600 mt-1">{fmtAEDsafe(apiFairPoint)}</p>
            {apiFairLow != null && apiFairHigh != null && (
              <p className="text-[10px] text-apil-gray-400">Range: {fmtAEDsafe(apiFairLow)}–{fmtAEDsafe(apiFairHigh)}</p>
            )}
          </div>
          <div className={`p-4 rounded-lg text-center ${discountPct != null && discountPct < 0 ? 'bg-green-50' : discountPct != null && discountPct > 5 ? 'bg-red-50' : 'bg-amber-50'}`}>
            <p className="text-xs text-apil-gray-500">vs Fair Value</p>
            <p className={`text-xl font-bold mt-1 ${discountPct != null && discountPct < 0 ? 'text-green-600' : discountPct != null && discountPct > 5 ? 'text-red-600' : 'text-amber-600'}`}>
              {discountPct != null ? fmtPct(discountPct) : '—'}
            </p>
            {discountPct != null && discountPct > 5 && <p className="text-[10px] text-red-500">Overpriced</p>}
            {discountPct != null && discountPct < -5 && <p className="text-[10px] text-green-500">Discount</p>}
          </div>
        </div>

        {/* Comparable Sales */}
        {salesCount > 0 && (
          <div className="mt-4 p-4 bg-apil-gray-50 rounded-lg">
            <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-2">Comparable Sales</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div><span className="text-apil-gray-500">Transactions</span><br/><span className="font-bold">{salesCount}</span></div>
              <div><span className="text-apil-gray-500">Median Sold</span><br/><span className="font-bold">{fmtAEDsafe(compMedian)}</span></div>
              {priceSqft > 0 && <div><span className="text-apil-gray-500">Price/sqft</span><br/><span className="font-bold">AED {priceSqft?.toFixed(0)}</span></div>}
              {priceDiffPct != null && (
                <div>
                  <span className="text-apil-gray-500">Asking vs Sold</span><br/>
                  <span className={`font-bold ${priceDiffPct > 0 ? 'text-amber-600' : 'text-green-600'}`}>
                    {priceDiffPct > 0 ? '+' : ''}{priceDiffPct}%
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        <CalcTracePanel trace={topRec?.calcTrace?.valuation} section="valuation" title="Fair Market Value" />

        {/* Explanation for discrepancy */}
        {fairValue != null && compMedian != null && fairValue > 0 && compMedian > 0 && Math.abs(fairValue - compMedian) / Math.max(fairValue, compMedian) > 0.1 && (
          <div className="mt-3 p-3 bg-blue-50 rounded-lg text-xs text-blue-700">
            <strong>Why do fair value and comparable median differ?</strong> Fair value is model-derived using broader area-wide adjustments (location, amenities, market trends). Comparable median reflects recent same-project sales only. Both are valid — the fair value gives a broader market context, while comparables show what buyers actually paid nearby.
          </div>
        )}
      </div>
    </div>
  );
}
