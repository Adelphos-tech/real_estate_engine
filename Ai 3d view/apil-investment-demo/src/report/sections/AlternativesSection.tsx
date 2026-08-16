/**
 * AlternativesSection — Context-aware alternatives display.
 *
 * Ready property:
 *   - Sort by overall score, show trade-offs in yield, liquidity, growth
 *
 * Off-plan property:
 *   - Sort by off-plan score, show trade-offs in price vs market, equity gain, developer
 */
import { Link } from 'react-router-dom';
import { GitCompare } from 'lucide-react';
import type { ReportContext } from '../ReportContext';
import { isOffPlan } from '../ReportContext';
import { ScoreRing, MarketPositionBadge, formatAED } from '../../components/Shared';

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

const REC_DISPLAY: Record<string, { label: string; color: string }> = {
  'STRONG BUY': { label: 'Buy', color: '#16a34a' },
  'BUY': { label: 'Buy', color: '#16a34a' },
  'BUY IF NEGOTIATED': { label: 'Buy if Negotiated', color: '#16a34a' },
  'HOLD': { label: 'Hold', color: '#f59e0b' },
  'WATCHLIST': { label: 'Watchlist', color: '#f97316' },
  'REVIEW': { label: 'Review', color: '#6b7280' },
  'INSUFFICIENT_DATA': { label: 'Insufficient Data', color: '#6b7280' },
  'AVOID': { label: 'Avoid', color: '#dc2626' },
};

function getRecDisplay(rec: string) {
  return REC_DISPLAY[rec] || REC_DISPLAY['REVIEW'];
}

interface AlternativesSectionProps {
  alternatives: any[];
  topProperty: any;
  ctx: ReportContext;
}

export function AlternativesSection({ alternatives, topProperty, ctx }: AlternativesSectionProps) {
  if (!alternatives || alternatives.length === 0) {
    return (
      <div className="premium-card p-6 text-center">
        <p className="text-sm text-apil-gray-500">No alternative properties available for this search criteria.</p>
      </div>
    );
  }

  if (isOffPlan(ctx)) {
    return <OffPlanAlternatives alternatives={alternatives} topProperty={topProperty} />;
  }
  return <ReadyAlternatives alternatives={alternatives} topProperty={topProperty} />;
}

// ═══════════════════════════════════════════════════
// READY ALTERNATIVES
// ═══════════════════════════════════════════════════

function ReadyAlternatives({ alternatives, topProperty }: { alternatives: any[]; topProperty: any }) {
  const topScore = topProperty?.overallScore ?? topProperty?.propertyScore ?? null;
  const topNetROI = topProperty?.netROI ?? null;
  const topLiquidity = topProperty?.liquidityScore ?? null;
  const topGrowth = topProperty?.growth12m ?? null;

  // Sort by score descending
  const sorted = [...alternatives].sort((a, b) => {
    const aScore = a.overallScore ?? a.propertyScore ?? null;
    const bScore = b.overallScore ?? b.propertyScore ?? null;
    return (bScore ?? 0) - (aScore ?? 0);
  });

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold text-apil-gray-900">Alternative Opportunities</h3>
      <p className="text-sm text-apil-gray-500">Compare these against your top pick — each has different trade-offs</p>

      {/* Why #1 summary */}
      <div className="premium-card p-4 bg-green-50/30 border border-green-100">
        <p className="text-xs font-semibold text-green-700 uppercase mb-1">Why This Is Your #1 Pick</p>
        <p className="text-sm text-apil-gray-700">
          <strong>{topProperty?.title || 'This property'}</strong> ranked highest because of its {topScore}/100 investment score
          {topNetROI > 0 ? `, ${topNetROI.toFixed(1)}% net yield` : ''}
          {topLiquidity > 0 ? `, and ${topLiquidity}/100 liquidity score` : ''}.
          The alternatives below were ranked lower for the reasons shown.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sorted.map((alt: any, i: number) => {
          const altScore = alt.overallScore ?? alt.propertyScore ?? null;
          const altNetROI = alt.netROI ?? null;
          const altLiquidity = alt.liquidityScore ?? null;
          const altGrowth = alt.growth12m ?? null;

          const tradeoffs: { label: string; better: boolean; detail: string }[] = [];
          if (altNetROI > topNetROI) tradeoffs.push({ label: 'Rental Yield', better: true, detail: `${altNetROI.toFixed(1)}% vs ${topNetROI.toFixed(1)}%` });
          else if (altNetROI < topNetROI && altNetROI > 0) tradeoffs.push({ label: 'Rental Yield', better: false, detail: `${altNetROI.toFixed(1)}% vs ${topNetROI.toFixed(1)}%` });
          if (altLiquidity > topLiquidity) tradeoffs.push({ label: 'Liquidity', better: true, detail: `${altLiquidity} vs ${topLiquidity}` });
          else if (altLiquidity < topLiquidity) tradeoffs.push({ label: 'Liquidity', better: false, detail: `${altLiquidity} vs ${topLiquidity}` });
          if (altGrowth > topGrowth) tradeoffs.push({ label: 'Growth', better: true, detail: `${altGrowth}% vs ${topGrowth}%` });
          else if (altGrowth < topGrowth && altGrowth !== 0) tradeoffs.push({ label: 'Growth', better: false, detail: `${altGrowth}% vs ${topGrowth}%` });
          if (altScore < topScore) tradeoffs.push({ label: 'Overall Score', better: false, detail: `${altScore} vs ${topScore}` });

          const recDisplay = getRecDisplay(alt.recommendation || 'REVIEW');

          return (
            <Link key={alt.id || i} to={`/investment-property/${alt.id}`} className="premium-card p-5 group">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-apil-gray-900">{alt.title}</h3>
                  <p className="text-xs text-apil-gray-500">{alt.area || '—'} · {alt.bedType || '—'}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs font-bold" style={{ color: recDisplay.color }}>{recDisplay.label}</span>
                    <span className="text-xs text-apil-gray-400">·</span>
                    <span className="text-xs text-apil-gray-500">{fmtAEDsafe(alt.askingPrice)}</span>
                  </div>
                </div>
                <ScoreRing score={altScore} size={56} />
              </div>

              {tradeoffs.length > 0 && (
                <div className="space-y-1.5 mb-3">
                  <p className="text-[10px] font-semibold text-apil-gray-400 uppercase">Why #{i + 2} instead of #1</p>
                  {tradeoffs.slice(0, 4).map((t, j) => (
                    <div key={j} className="flex items-center justify-between text-xs">
                      <span className="text-apil-gray-600">{t.label}</span>
                      <span className={t.better ? 'text-green-600 font-medium' : 'text-amber-600 font-medium'}>
                        {t.better ? '↑' : '↓'} {t.detail}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-3 flex items-center justify-between">
                <MarketPositionBadge position={alt.marketPosition} />
                <span className="text-xs text-apil-blue group-hover:underline">View details →</span>
              </div>
            </Link>
          );
        })}
      </div>

      <div className="text-center">
        <Link to="/investment-compare" className="inline-flex items-center gap-2 bg-apil-blue text-white text-sm font-semibold px-6 py-3 rounded-lg hover:bg-apil-blue-dark">
          <GitCompare className="w-4 h-4" /> Compare All Opportunities
        </Link>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// OFF-PLAN ALTERNATIVES
// ═══════════════════════════════════════════════════

function OffPlanAlternatives({ alternatives, topProperty }: { alternatives: any[]; topProperty: any }) {
  const topScore = topProperty?.offplanScore ?? topProperty?.overallScore ?? topProperty?.propertyScore ?? null;
  const topDeveloperScore = topProperty?.developerData?.developerScore ?? topProperty?.developerScore ?? null;
  const topDownPct = topProperty?.paymentPlanAnalysis?.downPaymentPct || 0;
  const topPriceDiff = topProperty?.priceOpportunity?.priceDifferencePct || 0;

  // Sort by off-plan score descending
  const sorted = [...alternatives].sort((a, b) => {
    const aScore = a.offplanScore ?? null;
    const bScore = b.offplanScore ?? null;
    return (bScore ?? 0) - (aScore ?? 0);
  });

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold text-apil-gray-900">Alternative Off-Plan Opportunities</h3>
      <p className="text-sm text-apil-gray-500">Compare these against your top pick — each has different trade-offs</p>

      {/* Why #1 summary */}
      <div className="premium-card p-4 bg-green-50/30 border border-green-100">
        <p className="text-xs font-semibold text-green-700 uppercase mb-1">Why This Is Your #1 Pick</p>
        <p className="text-sm text-apil-gray-700">
          <strong>{topProperty?.title || 'This property'}</strong> ranked highest with a {topScore}/100 off-plan score
          {topDeveloperScore > 0 ? `, ${topDeveloperScore}/100 developer score` : ''}
          {topDownPct > 0 ? `, ${topDownPct}% down payment` : ''}.
          The alternatives below were ranked lower for the reasons shown.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sorted.map((alt: any, i: number) => {
          const altScore = alt.offplanScore ?? alt.overallScore ?? alt.propertyScore ?? null;
          const priceOpp = alt.priceOpportunity || {};
          const altPP = alt.paymentPlanAnalysis || {};
          const altDevScore = alt.developerData?.developerScore || alt.developerScore || 0;
          const images = alt.listingData?.images || [];

          const tradeoffs: { label: string; better: boolean; detail: string }[] = [];
          if (altDevScore > topDeveloperScore) tradeoffs.push({ label: 'Developer Score', better: true, detail: `${altDevScore} vs ${topDeveloperScore}` });
          else if (altDevScore < topDeveloperScore) tradeoffs.push({ label: 'Developer Score', better: false, detail: `${altDevScore} vs ${topDeveloperScore}` });
          if ((altPP.downPaymentPct || 0) < topDownPct) tradeoffs.push({ label: 'Down Payment', better: true, detail: `${altPP.downPaymentPct || '—'}% vs ${topDownPct}%` });
          else if ((altPP.downPaymentPct || 0) > topDownPct) tradeoffs.push({ label: 'Down Payment', better: false, detail: `${altPP.downPaymentPct || '—'}% vs ${topDownPct}%` });
          const altPriceDiff = priceOpp.priceDifferencePct || 0;
          if (altPriceDiff < topPriceDiff) tradeoffs.push({ label: 'Price vs Market', better: true, detail: `${altPriceDiff}% vs ${topPriceDiff}%` });
          else if (altPriceDiff > topPriceDiff) tradeoffs.push({ label: 'Price vs Market', better: false, detail: `${altPriceDiff}% vs ${topPriceDiff}%` });
          if (altScore < topScore) tradeoffs.push({ label: 'Overall Score', better: false, detail: `${altScore} vs ${topScore}` });

          return (
            <div key={i} className="premium-card p-5 group cursor-pointer">
              {images.length > 0 && (
                <div className="aspect-video rounded-lg overflow-hidden bg-apil-gray-100 mb-3">
                  <img
                    src={images[0].url || images[0]}
                    alt={alt.title}
                    className="w-full h-full object-cover"
                    loading="lazy"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                </div>
              )}
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-apil-gray-900">{alt.title}</h3>
                  <p className="text-xs text-apil-gray-500">{alt.area || '—'} · {alt.bedType || '—'} · {alt.developer || '—'}</p>
                </div>
                <ScoreRing score={altScore} size={56} />
              </div>
              <div className="grid grid-cols-3 gap-2 text-sm">
                <div>
                  <span className="text-apil-gray-400 text-xs">Price</span>
                  <p className="font-semibold">{fmtAEDsafe(alt.askingPrice)}</p>
                </div>
                <div>
                  <span className="text-apil-gray-400 text-xs">vs Market</span>
                  <p className={`font-semibold ${(priceOpp.priceDifferencePct || 0) <= 0 ? 'text-green-600' : 'text-red-500'}`}>
                    {fmtPct(priceOpp.priceDifferencePct)}
                  </p>
                </div>
                <div>
                  <span className="text-apil-gray-400 text-xs">Down Payment</span>
                  <p className="font-semibold text-apil-blue">{altPP.downPaymentPct ? `${altPP.downPaymentPct}%` : '—'}</p>
                </div>
              </div>

              {tradeoffs.length > 0 && (
                <div className="space-y-1.5 mt-3">
                  <p className="text-[10px] font-semibold text-apil-gray-400 uppercase">Why #{i + 2} instead of #1</p>
                  {tradeoffs.slice(0, 4).map((t, j) => (
                    <div key={j} className="flex items-center justify-between text-xs">
                      <span className="text-apil-gray-600">{t.label}</span>
                      <span className={t.better ? 'text-green-600 font-medium' : 'text-amber-600 font-medium'}>
                        {t.better ? '↑' : '↓'} {t.detail}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-3 flex items-center justify-between">
                <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                  alt.recommendation?.includes('STRONG') || alt.recommendation === 'BUY' ? 'bg-green-100 text-green-700' :
                  alt.recommendation === 'NEGOTIATE' || alt.recommendation === 'HOLD' ? 'bg-amber-100 text-amber-700' :
                  'bg-red-100 text-red-700'
                }`}>{alt.recommendation || 'HOLD'}</span>
                {altScore < topScore && <span className="text-xs text-apil-gray-400">Score {altScore} vs {topScore}</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
