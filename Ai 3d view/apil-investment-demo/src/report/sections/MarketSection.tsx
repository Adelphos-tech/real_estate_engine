/**
 * MarketSection — Context-aware market data display.
 *
 * Ready property:
 *   - Show rental market, price trend, sales trend, liquidity
 *
 * Off-plan property:
 *   - Show launch sales, absorption, future supply, infrastructure,
 *     upcoming communities, expected demand
 */
import { MapPin, TrendingUp, Building2 } from 'lucide-react';
import type { ReportContext } from '../ReportContext';
import { isOffPlan, isRentalGoal, isGrowthGoal } from '../ReportContext';
import { ComparableTransactionsCard } from '../../components/ComparableTransactionsCard';
import { ScoreRing, MarketPositionBadge, GrowthIndicator, StatCard, formatAED, formatNumber } from '../../components/Shared';

const safeVal = (v: any): number | null => {
  if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) return null;
  return v;
};
const fmtPct = (v: any, prefix = ''): string => {
  const n = safeVal(v);
  if (n === null) return '—';
  return `${n > 0 ? prefix : ''}${n}%`;
};
const fmtAEDsafe = (v: any): string => {
  const n = safeVal(v);
  if (n === null) return '—';
  return formatAED(n);
};
const fmtNumSafe = (v: any): string => {
  const n = safeVal(v);
  if (n === null) return '—';
  return formatNumber(n);
};
const fmtYield = (v: any): string => {
  const n = safeVal(v);
  if (n === null) return '—';
  return `${n}%`;
};
const fmtCount = (v: any, label: string): string => {
  const n = safeVal(v);
  if (n === null || n === 0) return '—';
  return `${n} ${label}`;
};
const scoreOrNA = (v: any): number | null => {
  const n = safeVal(v);
  return n === null ? null : n;
};

interface MarketSectionProps {
  property: any;
  topRec: any;
  ctx: ReportContext;
  community: any;
  project?: any;
}

export function MarketSection({ property, topRec, ctx, community, project }: MarketSectionProps) {
  if (isOffPlan(ctx)) {
    return <OffPlanMarketSection property={property} topRec={topRec} ctx={ctx} community={community} />;
  }
  return <ReadyMarketSection property={property} topRec={topRec} ctx={ctx} community={community} project={project} />;
}

// ═══════════════════════════════════════════════════
// READY MARKET
// ═══════════════════════════════════════════════════

function ReadyMarketSection({ property, topRec, ctx, community, project }: MarketSectionProps) {
  if (!community) return null;
  const growth12 = safeVal(property.growth12m);
  const growth6m = safeVal(property.growth6m);
  const growth3m = safeVal(property.growth3m);
  const mv = topRec?.marketValuation;
  const rawDiscountPct = mv?.discountPct;
  // Cap displayed discount to ±50% — anything beyond is likely a data issue (different property types/sizes)
  const discountPct = rawDiscountPct != null ? Math.max(-50, Math.min(50, rawDiscountPct)) : null;
  const fairValue = mv?.fairValueTotal;
  const fairValueCapped = discountPct !== rawDiscountPct;

  const growthMetrics = [
    { label: 'Price Growth (3M)', value: growth3m },
    { label: 'Price Growth (6M)', value: growth6m },
    { label: 'Price Growth (12M)', value: growth12 },
  ];

  // Build stat cards — only with data
  const statCards: { label: string; value: string; sublabel?: React.ReactNode }[] = [];
  statCards.push({ label: 'Median Price/sqft', value: `AED ${fmtNumSafe(community.medianPriceSqft)}` });

  if (ctx.hasRentalEvidence) {
    statCards.push({
      label: 'Avg Rental Yield',
      value: fmtYield(community.rentalYield),
      sublabel: <span className="text-xs text-green-600 font-medium">{fmtAEDsafe(community.medianRent)}/yr median</span>,
    });
  }

  if (growth12 !== null && growth12 !== 0) {
    statCards.push({
      label: '12M Growth',
      value: fmtPct(community.growth12m, '+'),
      sublabel: <GrowthIndicator value={scoreOrNA(community.growth12m)} />,
    });
  }

  if (community.demandScore) {
    statCards.push({ label: 'Demand Index', value: `${community.demandScore}/100` });
  }

  return (
    <div className="space-y-4">
      {/* Fair Value Assessment */}
      <div className="premium-card p-6">
        <h3 className="font-semibold text-apil-gray-900 mb-1">Fair Value Assessment</h3>
        <p className="text-xs text-apil-gray-500 mb-4">What is this property actually worth?</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Asking Price</p>
            <p className="text-xl font-bold text-apil-gray-900 mt-1">{fmtAEDsafe(property.askingPrice)}</p>
          </div>
          {fairValue ? (
            <div className="text-center p-4 bg-blue-50 rounded-xl">
              <p className="text-xs text-apil-gray-500">Fair Market Value</p>
              <p className="text-xl font-bold text-apil-blue mt-1">{formatAED(fairValue)}</p>
            </div>
          ) : (
            <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
              <p className="text-xs text-apil-gray-500">Fair Market Value</p>
              <p className="text-sm text-apil-gray-400 mt-2">Insufficient comparables to estimate</p>
            </div>
          )}
          {discountPct != null ? (
            <div className="text-center p-4 bg-green-50 rounded-xl">
              <p className="text-xs text-apil-gray-500">Price vs Fair Value</p>
              <p className={`text-xl font-bold mt-1 ${discountPct < -5 ? 'text-green-600' : discountPct > 5 ? 'text-red-500' : 'text-blue-600'}`}>
                {discountPct > 0 ? '+' : ''}{discountPct.toFixed(1)}%
              </p>
            </div>
          ) : (
            <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
              <p className="text-xs text-apil-gray-500">Price vs Fair Value</p>
              <p className="text-sm text-apil-gray-400 mt-2">Not enough data to compare</p>
            </div>
          )}
        </div>
        {mv?.description && <p className="text-sm text-apil-gray-600">{mv.description}</p>}
        {fairValue && discountPct != null && property.comparablePrice && (
          <div className="mt-2 space-y-1">
            <p className="text-xs text-apil-gray-400">
              Fair value ({formatAED(fairValue)}) is model-derived using broader area-wide adjustments (location factor, project premium, community median price/sqft). The comparable median sold price ({formatAED(property.comparablePrice)}) reflects recent same-project transactions only. The two can differ because fair value incorporates wider market data, while comparables are unit-specific.
            </p>
            {fairValueCapped && (
              <p className="text-xs text-amber-600">
                <strong>Note:</strong> The raw price difference exceeded 50% and has been capped for display. This large gap likely indicates the fair value estimate includes different property types or sizes. Always cross-check against the comparable sold price below.
              </p>
            )}
            {property.comparablePrice && fairValue && Math.abs(fairValue - property.comparablePrice) / (property.comparablePrice || 1) > 0.3 && (
              <p className="text-xs text-amber-600">
                <strong>Discrepancy:</strong> Fair value estimate ({formatAED(fairValue)}) differs significantly from median comparable sold price ({formatAED(property.comparablePrice)}). The comparable sold price is based on similar units and is generally more reliable.
              </p>
            )}
          </div>
        )}
        <div className="mt-3"><MarketPositionBadge position={property.marketPosition} /></div>
      </div>

      {/* Comparable Transactions */}
      <ComparableTransactionsCard property={property} project={project} />

      {/* Area Profile */}
      <div className="premium-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold text-apil-gray-900">Area: {community.name}</h3>
            <p className="text-xs text-apil-gray-500">
              {fmtCount(community.salesVolume, 'sales')} · {fmtCount(community.rentVolume, 'rents')} · {fmtCount(community.totalProjects, 'projects')}
            </p>
          </div>
          <ScoreRing score={scoreOrNA(community.investmentScore)} size={64} label="Area Score" />
        </div>

        <div className={`grid grid-cols-2 ${statCards.length > 2 ? 'md:grid-cols-4' : 'md:grid-cols-2'} gap-3 mb-4`}>
          {statCards.map((card, i) => (
            <StatCard key={i} label={card.label} value={card.value} sublabel={card.sublabel} />
          ))}
        </div>

        {/* Price Trends — only show if we have data */}
        {growthMetrics.some(g => g.value !== null && g.value !== 0) && (
          <div className="grid grid-cols-3 gap-3">
            {growthMetrics.map((g, i) => {
              const noData = g.value === null || g.value === 0;
              if (noData) return null;
              return (
                <div key={i} className="text-center p-3 bg-apil-gray-50 rounded-lg">
                  <p className="text-xs text-apil-gray-500">{g.label}</p>
                  <p className={`text-lg font-bold mt-1 ${(g.value || 0) > 0 ? 'text-green-600' : 'text-red-500'}`}>
                    {(g.value || 0) > 0 ? '+' : ''}{g.value}%
                  </p>
                </div>
              );
            })}
          </div>
        )}

        {/* Growth data availability note */}
        {growth3m !== null && growth3m !== 0 && (growth6m === null || growth6m === 0) && (growth12 === null || growth12 === 0) && (
          <p className="text-xs text-apil-gray-400 mt-2 italic">
            Only recent (3-month) transaction data is available for this area. Longer-term growth trends will appear as more transaction history accumulates.
          </p>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// OFF-PLAN MARKET — launch sales, absorption, supply
// ═══════════════════════════════════════════════════

function OffPlanMarketSection({ property, topRec, ctx, community }: MarketSectionProps) {
  const commData = topRec?.communityData || {};
  const liquidity = topRec?.liquidity || {};
  const futureApp = topRec?.futureAppreciation || {};

  const statCards: { label: string; value: string; sublabel?: React.ReactNode }[] = [];

  if (commData.growth12m) {
    statCards.push({
      label: 'Price Growth (12M)',
      value: fmtPct(commData.growth12m, '+'),
      sublabel: <GrowthIndicator value={scoreOrNA(commData.growth12m)} />,
    });
  }
  if (commData.supplyIndex) {
    statCards.push({ label: 'Future Supply Index', value: `${commData.supplyIndex}/100` });
  }
  if (commData.rentalDemand) {
    statCards.push({ label: 'Rental Demand Index', value: `${commData.rentalDemand}/100` });
  }
  if (commData.demandIndex) {
    statCards.push({ label: 'Demand Index', value: `${commData.demandIndex}/100` });
  }

  return (
    <div className="space-y-4">
      {/* Area Profile */}
      {commData.communityScore && (
        <div className="premium-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-50 text-apil-blue flex items-center justify-center">
                <MapPin className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-apil-gray-900">Area: {topRec?.area || 'Dubai'}</h3>
                <p className="text-xs text-apil-gray-500">Community investment fundamentals</p>
              </div>
            </div>
            <ScoreRing score={scoreOrNA(commData.communityScore)} size={80} label="Community" />
          </div>

          {statCards.length > 0 && (
            <div className={`grid grid-cols-2 ${statCards.length > 2 ? 'md:grid-cols-4' : 'md:grid-cols-2'} gap-3 mb-5`}>
              {statCards.map((card, i) => (
                <StatCard key={i} label={card.label} value={card.value} sublabel={card.sublabel} />
              ))}
            </div>
          )}

          {/* Sub-scores */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
            {[
              { label: 'Demand', value: safeVal(commData.demandIndex) },
              { label: 'Growth', value: safeVal(commData.growthIndex) },
              { label: 'Supply', value: safeVal(commData.futureSupplyScore) },
              { label: 'Liquidity', value: safeVal(commData.liquidityScore) },
              { label: 'Rental', value: safeVal(commData.rentalDemand) },
              { label: 'Livability', value: safeVal(commData.livabilityIndex) },
              { label: 'Luxury', value: safeVal(commData.luxuryIndex) },
              { label: 'Transport', value: safeVal(commData.transportIndex) },
            ].filter(s => s.value !== null).map((s, i) => (
              <div key={i} className="text-center p-3 bg-apil-gray-50 rounded-lg">
                <p className="text-xs text-apil-gray-500 font-medium">{s.label}</p>
                <p className="text-xl font-bold mt-1 text-apil-gray-900">{s.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Future Supply & Infrastructure */}
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Building2 className="w-5 h-5 text-amber-500" />
          <h3 className="font-semibold text-apil-gray-900">Future Supply & Infrastructure</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Future Supply Score</p>
            <p className="text-lg font-bold text-apil-gray-900">{scoreOrNA(commData.futureSupplyScore || commData.supplyIndex)}/100</p>
            <p className="text-xs text-apil-gray-400 mt-1">
              {(commData.futureSupplyScore || commData.supplyIndex || 0) > 70
                ? 'Significant new supply coming — may pressure prices'
                : (commData.futureSupplyScore || commData.supplyIndex || 0) > 40
                ? 'Moderate supply — balanced market expected'
                : 'Low supply — favorable for price appreciation'}
            </p>
          </div>
          <div className="p-4 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Expected Demand</p>
            <p className="text-lg font-bold text-apil-gray-900">{scoreOrNA(commData.demandIndex)}/100</p>
            <p className="text-xs text-apil-gray-400 mt-1">
              {(commData.demandIndex || 0) >= 70
                ? 'Strong demand drivers in this area'
                : 'Moderate demand — verify growth drivers'}
            </p>
          </div>
        </div>
      </div>

      {/* Absorption / Launch Sales */}
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-green-600" />
          <h3 className="font-semibold text-apil-gray-900">Launch Sales & Absorption</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Transaction Volume</p>
            <p className="text-xl font-bold text-apil-gray-900 mt-1">{fmtNumSafe(liquidity.transactionVolume)}</p>
          </div>
          <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Liquidity Score</p>
            <p className="text-xl font-bold text-apil-gray-900 mt-1">{liquidity.liquidityScore || '—'}/100</p>
          </div>
          <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Assignment Demand</p>
            <p className="text-lg font-bold text-apil-blue mt-1">
              {(liquidity.liquidityScore || 0) >= 80 ? 'High' : (liquidity.liquidityScore || 0) >= 60 ? 'Moderate' : 'Limited'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
