/**
 * ReturnsSection — Context-aware returns display.
 *
 * Ready property:
 *   - Show annual rent, gross/net yield, costs, net income, total return
 *   - Hide rental calculator if rental confidence is weak
 *   - For capital growth goal: emphasize appreciation, de-emphasize rental
 *
 * Off-plan property:
 *   - Replace entire section with purchase price, payment schedule,
 *     construction progress, expected exit value, capital gain, ROE
 *   - Never display rental ROI, annual rent, vacancy, rental calculator
 */
import { TrendingUp, Calendar, Target, DollarSign, ChevronDown } from 'lucide-react';
import { useState } from 'react';
import type { ReportContext } from '../ReportContext';
import { isOffPlan, isRentalGoal, isGrowthGoal, shouldHideSection, isAvailable, isUnavailable, isAlternativeOnly, evidenceWording } from '../ReportContext';
import { formatAED, formatNumber } from '../../components/Shared';
import { CalcTracePanel } from './CalcTracePanel';

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
const formatHandoverDate = (v: any): string | null => {
  if (!v || typeof v !== 'string') return null;
  // API returns ISO date like "2030-03-31"
  const m = v.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return v; // already a string like "Q1 2030"
  const year = m[1];
  const month = parseInt(m[2]);
  const quarters: Record<number, string> = { 1: 'Q1', 2: 'Q1', 3: 'Q1', 4: 'Q2', 5: 'Q2', 6: 'Q2', 7: 'Q3', 8: 'Q3', 9: 'Q3', 10: 'Q4', 11: 'Q4', 12: 'Q4' };
  const q = quarters[month];
  if (q) return `${q} ${year}`;
  return v;
};

interface ReturnsSectionProps {
  property: any;
  topRec: any;
  ctx: ReportContext;
  community?: any;
}

export function ReturnsSection({ property, topRec, ctx, community }: ReturnsSectionProps) {
  if (isOffPlan(ctx)) {
    return <OffPlanReturnsSection property={property} topRec={topRec} ctx={ctx} />;
  }
  return <ReadyReturnsSection property={property} topRec={topRec} ctx={ctx} community={community} />;
}

// ═══════════════════════════════════════════════════
// READY PROPERTY RETURNS
// ═══════════════════════════════════════════════════

function ReadyReturnsSection({ property, topRec, ctx, community }: ReturnsSectionProps) {
  // Use engine-provided values from returns.rental — never recalculate in frontend
  const rentalData = topRec?.returns?.rental || {};
  const stressTests = topRec?.returns?.totalReturn?.stressTests || {};
  const netROI = safeVal(rentalData.netYieldPct) ?? safeVal(property.netROI);
  const grossROI = safeVal(rentalData.grossYieldPct) ?? safeVal(property.grossROI);
  const growth12 = safeVal(property.growth12m);
  const hasRentData = ctx.hasRentalEvidence;
  const askingPrice = safeVal(property.askingPrice) || 0;
  const estRent = safeVal(rentalData.annualRent) ?? safeVal(property.estimatedRent) ?? 0;
  const serviceCharge = safeVal(rentalData.serviceCharge) ?? safeVal(property.serviceChargeAnnual) ?? 0;
  const mgmtFee = safeVal(rentalData.managementFee) ?? safeVal(property.managementFee) ?? 0;
  const vacancyCost = safeVal(rentalData.vacancyCost) ?? 0;
  const netIncome = safeVal(rentalData.netAnnualIncome) ?? safeVal(property.netAnnualIncome) ?? 0;
  const isCapitalGrowth = isGrowthGoal(ctx);

  // Scenarios — use engine stress test data when available
  const rentStress = stressTests.rent_minus_10pct || {};
  const rentDownROI = safeVal(rentStress.new_net_yield) != null
    ? safeVal(rentStress.new_net_yield)!
    : (askingPrice > 0 && netIncome > 0
      ? Math.round(((netIncome * 0.9) / askingPrice) * 1000) / 10
      : 0);
  const negotiatedPrice = askingPrice * 0.95;
  const negotiatedROI = negotiatedPrice > 0 && netIncome > 0 ? Math.round((netIncome / negotiatedPrice) * 1000) / 10 : null;
  const stressRec = rentDownROI >= 6.8 ? 'Still a Buy' : rentDownROI >= 4 ? 'Hold — yield drops below average' : 'Caution — income at risk';

  // Build KPI cards — always show key rental metrics when available
  const kpiCards: { label: string; value: string; sublabel: string; bg: string; textColor: string }[] = [];

  if (hasRentData) {
    if (estRent > 0) {
      kpiCards.push({
        label: 'Expected Annual Rent',
        value: formatAED(estRent),
        sublabel: 'Gross rental income',
        bg: 'bg-green-50',
        textColor: 'text-green-600',
      });
    }
    if (grossROI != null) {
      kpiCards.push({
        label: 'Gross Yield',
        value: `${grossROI.toFixed(1)}%`,
        sublabel: 'Rent / Price',
        bg: 'bg-teal-50',
        textColor: 'text-teal-600',
      });
    }
    if (netROI != null) {
      kpiCards.push({
        label: 'Net Yield',
        value: `${netROI.toFixed(1)}%`,
        sublabel: 'After all costs',
        bg: 'bg-blue-50',
        textColor: 'text-blue-600',
      });
    }
    if (netIncome !== 0) {
      kpiCards.push({
        label: 'Net Income / Year',
        value: formatAED(netIncome),
        sublabel: 'After costs & vacancy',
        bg: 'bg-green-50',
        textColor: 'text-green-600',
      });
    }
    if (growth12 !== null && growth12 !== 0) {
      kpiCards.push({
        label: 'Total Return Est.',
        value: `${((netROI ?? 0) + Math.max(0, growth12 ?? 0)).toFixed(1)}%`,
        sublabel: 'Yield + Growth combined',
        bg: 'bg-amber-50',
        textColor: 'text-amber-600',
      });
    }
  } else {
    kpiCards.push({
      label: 'Net Income / Year',
      value: formatAED(netIncome),
      sublabel: 'After all costs',
      bg: 'bg-green-50',
      textColor: 'text-green-600',
    });
    kpiCards.push({
      label: 'Net Yield',
      value: netROI != null ? `${netROI.toFixed(1)}%` : '—',
      sublabel: 'Annual return on price',
      bg: 'bg-blue-50',
      textColor: 'text-blue-600',
    });
  }

  if (growth12 !== null && growth12 !== 0) {
    kpiCards.push({
      label: 'Price Growth (12m)',
      value: `${growth12 > 0 ? '+' : ''}${growth12}%`,
      sublabel: 'Historical trend',
      bg: 'bg-purple-50',
      textColor: 'text-purple-600',
    });
  }

  // If no KPI cards at all, show what we can
  if (kpiCards.length === 0) {
    kpiCards.push({
      label: 'Purchase Price',
      value: fmtAEDsafe(askingPrice),
      sublabel: 'Current asking price',
      bg: 'bg-apil-gray-50',
      textColor: 'text-apil-gray-900',
    });
  }

  // Benchmarks — only show if we have a return to compare
  const benchmarks = [
    { label: 'This Property', return: netROI !== null ? `${Math.round(netROI)}%` : '—', risk: property.riskLevel || '—', highlight: true, note: 'Net rental yield' },
    { label: 'Dubai Real Estate Avg', return: '6.8%', risk: 'Medium' },
    { label: 'Bank Fixed Deposit', return: '4.0%', risk: 'Very Low' },
    { label: 'S&P 500 (Historical)', return: '10.0%', risk: 'High' },
  ];

  return (
    <div className="space-y-4">
      <div className="premium-card p-6">
        <h3 className="font-semibold text-apil-gray-900 mb-4">
          {isCapitalGrowth ? 'Expected Returns' : 'Expected Returns'}
        </h3>
        <div className={`grid grid-cols-2 ${kpiCards.length > 2 ? 'md:grid-cols-4' : 'md:grid-cols-2'} gap-4`}>
          {kpiCards.map((card, i) => (
            <div key={i} className={`text-center p-4 ${card.bg} rounded-xl`}>
              <p className="text-xs text-apil-gray-500">{card.label}</p>
              <p className={`text-2xl font-bold ${card.textColor} mt-1`}>{card.value}</p>
              <p className="text-[10px] text-apil-gray-400 mt-0.5">{card.sublabel}</p>
            </div>
          ))}
        </div>

        {/* Operating Costs Breakdown */}
        {hasRentData && estRent > 0 && (
          <div className="mt-5 p-4 bg-apil-gray-50 rounded-lg">
            <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-3">Operating Costs Breakdown</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div>
                <p className="text-xs text-apil-gray-500">Gross Rent</p>
                <p className="font-semibold text-apil-gray-900">{formatAED(estRent)}</p>
              </div>
              <div>
                <p className="text-xs text-apil-gray-500">Service Charge</p>
                <p className="font-semibold text-red-500">-{formatAED(serviceCharge)}</p>
              </div>
              <div>
                <p className="text-xs text-apil-gray-500">Mgmt + Vacancy</p>
                <p className="font-semibold text-red-500">{mgmtFee > 0 || vacancyCost > 0 ? `-${formatAED(Math.round(mgmtFee + vacancyCost))}` : 'Not modeled'}</p>
              </div>
              <div>
                <p className="text-xs text-apil-gray-500">Net Cash Flow</p>
                <p className={`font-semibold ${netIncome > 0 ? 'text-green-600' : 'text-red-500'}`}>{formatAED(Math.round(netIncome))}</p>
              </div>
            </div>
          </div>
        )}

        {/* For capital growth with no rental data, show growth explanation */}
        {isCapitalGrowth && !hasRentData && growth12 !== null && (
          <div className="mt-5 p-4 bg-purple-50/50 rounded-lg">
            <p className="text-sm text-apil-gray-700">
              <strong className="text-purple-700">Capital Growth Focus:</strong> This property has shown {growth12}% price growth
              over the past 12 months. Rental income data is limited — this investment is best evaluated on appreciation potential.
            </p>
          </div>
        )}
      </div>

      {/* Scenario Analysis — only if we have rental data */}
      {hasRentData && (
        <div className="premium-card p-6">
          <h3 className="font-semibold text-apil-gray-900 mb-1">What If? — Stress Test</h3>
          <p className="text-xs text-apil-gray-500 mb-4">How does the investment hold up under pressure?</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-red-50/30 rounded-lg border border-red-100">
              <p className="text-sm font-semibold text-apil-gray-700 mb-2">If market rents drop 10%</p>
              <div className="flex items-center gap-3 text-sm mb-2">
                <div>
                  <p className="text-xs text-apil-gray-500">Net Yield</p>
                  <p className="font-semibold text-apil-gray-900">{netROI != null ? `${netROI.toFixed(2)}%` : '—'}</p>
                </div>
                <span className="text-apil-gray-400">→</span>
                <div>
                  <p className="text-xs text-apil-gray-500">Stressed Yield</p>
                  <p className="font-semibold text-red-500">{rentDownROI.toFixed(2)}%</p>
                </div>
              </div>
              <div className="text-xs text-apil-gray-500 mb-2">
                {estRent > 0 && (
                  <>Rent: {formatAED(estRent)} → {formatAED(estRent * 0.9)} · </>
                )}
                Net income: {formatAED(netIncome)} → {formatAED(safeVal(rentStress.new_net_income) ?? netIncome * 0.9)}
              </div>
              <p className={`text-xs font-medium ${rentDownROI >= 6.8 ? 'text-green-600' : rentDownROI >= 4 ? 'text-amber-600' : 'text-red-500'}`}>{stressRec}</p>
            </div>
            <div className="p-4 bg-green-50/30 rounded-lg border border-green-100">
              <p className="text-sm font-semibold text-apil-gray-700 mb-2">If you negotiate 5% off</p>
              <div className="flex items-center gap-3 text-sm mb-2">
                <div>
                  <p className="text-xs text-apil-gray-500">Price</p>
                  <p className="font-semibold text-apil-gray-900">{fmtAEDsafe(property.askingPrice)}</p>
                </div>
                <span className="text-apil-gray-400">→</span>
                <div>
                  <p className="text-xs text-apil-gray-500">New Price</p>
                  <p className="font-semibold text-green-600">{formatAED(negotiatedPrice)}</p>
                </div>
              </div>
              <p className="text-xs text-green-600 font-medium">{negotiatedROI !== null ? `ROI improves to ${negotiatedROI}%` : 'ROI improvement depends on rental data'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Benchmark Comparison */}
      <div className="premium-card p-6">
        <h3 className="font-semibold text-apil-gray-900 mb-1">Should I Buy This or...</h3>
        <p className="text-xs text-apil-gray-500 mb-4">Compare this property's expected return against other investments</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-apil-gray-200">
                <th className="text-left py-2 px-3 font-semibold text-apil-gray-500">Investment</th>
                <th className="text-center py-2 px-3 font-semibold text-apil-gray-500">Expected Return</th>
                <th className="text-center py-2 px-3 font-semibold text-apil-gray-500">Risk Level</th>
              </tr>
            </thead>
            <tbody>
              {benchmarks.map((b, i) => (
                <tr key={i} className={`border-b border-apil-gray-100 last:border-0 ${b.highlight ? 'bg-apil-blue/5' : ''}`}>
                  <td className={`py-2.5 px-3 ${b.highlight ? 'font-bold text-apil-blue' : 'font-medium text-apil-gray-700'}`}>{b.label}{b.note && <span className="text-xs text-apil-gray-400 ml-1">({b.note})</span>}</td>
                  <td className={`py-2.5 px-3 text-center font-semibold ${b.highlight ? 'text-green-600' : 'text-apil-gray-700'}`}>{b.return}</td>
                  <td className={`py-2.5 px-3 text-center ${b.risk === 'Low' || b.risk === 'Very Low' ? 'text-green-600' : b.risk === 'Medium' ? 'text-amber-600' : 'text-red-500'}`}>{b.risk}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// OFF-PLAN RETURNS — capital gain focused, no rental
// ═══════════════════════════════════════════════════

function OffPlanReturnsSection({ property, topRec, ctx }: ReturnsSectionProps) {
  const priceOpp = topRec?.priceOpportunity || {};
  const futureApp = topRec?.futureAppreciation || {};
  const ppAnalysis = topRec?.paymentPlanAnalysis || {};
  const askingPrice = safeVal(property.askingPrice) || 0;
  const postHandoverROI = topRec?.postHandoverROI || {};
  const rentalGoal = isRentalGoal(ctx);
  const growthGoal = isGrowthGoal(ctx);
  const hasExitValue = isAvailable(ctx, 'projected_exit_value');
  const hasGrowthRate = isAvailable(ctx, 'growth_rate');
  const hasRental = isAvailable(ctx, 'rental_income') || isAlternativeOnly(ctx, 'rental_income');
  const showRentalStress = !shouldHideSection(ctx, 'rental_stress');
  const showSalePriceStress = !shouldHideSection(ctx, 'sale_price_stress');
  const showConstructionStress = !shouldHideSection(ctx, 'construction_stress');
  const showPaymentStress = !shouldHideSection(ctx, 'payment_stress');

  const kpiCards: { label: string; value: string; sublabel: string; bg: string; textColor: string }[] = [];

  kpiCards.push({
    label: 'Purchase Price',
    value: fmtAEDsafe(askingPrice),
    sublabel: 'Developer launch price',
    bg: 'bg-apil-gray-50',
    textColor: 'text-apil-gray-900',
  });

  // Rental-focused metrics first for rental_income goal
  if (rentalGoal) {
    if (postHandoverROI.estimatedRent) {
      kpiCards.push({
        label: 'Expected Annual Rent',
        value: fmtAEDsafe(postHandoverROI.estimatedRent),
        sublabel: 'Post-handover estimate',
        bg: 'bg-green-50',
        textColor: 'text-green-600',
      });
    }
    if (postHandoverROI.netROI) {
      kpiCards.push({
        label: 'Net Yield (Post-Handover)',
        value: fmtPct(postHandoverROI.netROI),
        sublabel: 'After handover + costs',
        bg: 'bg-blue-50',
        textColor: 'text-blue-600',
      });
    }
    if (postHandoverROI.grossROI) {
      kpiCards.push({
        label: 'Gross Yield (Post-Handover)',
        value: fmtPct(postHandoverROI.grossROI),
        sublabel: 'Before costs',
        bg: 'bg-teal-50',
        textColor: 'text-teal-600',
      });
    }
  }

  // Capital gain metrics — primary for growth goal, secondary for rental
  if (hasExitValue && futureApp.futureValue) {
    const handoverLabel = isOffPlan(ctx)
      ? `In ${futureApp.completionYears || '—'} years (at exit)`
      : `In ${futureApp.completionYears || '—'} years`;
    kpiCards.push({
      label: isOffPlan(ctx) ? 'Projected Exit Value' : 'Expected Exit Value',
      value: fmtAEDsafe(futureApp.futureValue),
      sublabel: handoverLabel,
      bg: rentalGoal ? 'bg-apil-gray-50' : 'bg-green-50',
      textColor: rentalGoal ? 'text-apil-gray-900' : 'text-green-600',
    });
  }

  if (hasExitValue && futureApp.potentialGainPct !== null && futureApp.potentialGainPct !== undefined) {
    const gainSublabel = askingPrice > 0 && futureApp.futureValue
      ? `${fmtAEDsafe(askingPrice)} → ${fmtAEDsafe(futureApp.futureValue)}`
      : fmtAEDsafe(futureApp.potentialGain);
    kpiCards.push({
      label: 'Expected Capital Gain',
      value: fmtPct(futureApp.potentialGainPct),
      sublabel: gainSublabel,
      bg: rentalGoal ? 'bg-apil-gray-50' : 'bg-green-50',
      textColor: rentalGoal ? 'text-apil-gray-700' : 'text-green-600',
    });
  }

  if (ppAnalysis.equityGainPct) {
    kpiCards.push({
      label: 'Equity Gain on Down Payment',
      value: fmtPct(ppAnalysis.equityGainPct),
      sublabel: `${ppAnalysis.leverageRatio || '—'}x leverage`,
      bg: 'bg-purple-50',
      textColor: 'text-purple-600',
    });
  }

  // ROE if available
  const roePct = topRec?.returns?.totalReturn?.roePct;
  if (roePct != null) {
    kpiCards.push({
      label: 'ROE',
      value: `${roePct.toFixed(1)}%`,
      sublabel: 'Return on Equity',
      bg: 'bg-emerald-50',
      textColor: 'text-emerald-600',
    });
  }

  // Capital multiple
  const capitalMultiple = hasExitValue && futureApp.futureValue && askingPrice > 0
    ? (futureApp.futureValue / askingPrice).toFixed(2) + 'x'
    : null;
  if (capitalMultiple && !rentalGoal) {
    kpiCards.push({
      label: 'Capital Multiple',
      value: capitalMultiple,
      sublabel: 'Value / Price at exit',
      bg: 'bg-amber-50',
      textColor: 'text-amber-600',
    });
  }

  return (
    <div className="space-y-4">
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-green-600" />
          <h3 className="font-semibold text-apil-gray-900">Investment Returns — {rentalGoal ? 'Rental Income' : isGrowthGoal(ctx) ? 'Capital Growth' : 'Balanced'}</h3>
        </div>

        <div className={`grid grid-cols-2 ${kpiCards.length > 2 ? 'md:grid-cols-4' : 'md:grid-cols-2'} gap-4`}>
          {kpiCards.map((card, i) => (
            <div key={i} className={`text-center p-4 ${card.bg} rounded-xl`}>
              <p className="text-xs text-apil-gray-500">{card.label}</p>
              <p className={`text-2xl font-bold ${card.textColor} mt-1`}>{card.value}</p>
              <p className="text-[10px] text-apil-gray-400 mt-0.5">{card.sublabel}</p>
            </div>
          ))}
        </div>

        {/* Growth rate detail */}
        <div className="mt-5 grid grid-cols-2 md:grid-cols-3 gap-3">
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Growth Rate (Annual)</p>
            <p className="font-semibold text-green-600">
              {hasGrowthRate
                ? fmtPct(futureApp.growthRate)
                : <span className="text-apil-gray-400">N/A</span>}
              {hasGrowthRate && futureApp.growthDescription && (
                <span className="block text-[10px] text-apil-gray-400 mt-0.5">{futureApp.growthDescription}</span>
              )}
              {!hasGrowthRate && (
                <span className="block text-[10px] text-apil-gray-400 mt-0.5">No project or area growth data available</span>
              )}
            </p>
          </div>
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Time to Handover</p>
            <p className="font-semibold">{safeVal(property.constructionYears) != null ? `${property.constructionYears} years` : '—'}</p>
          </div>
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Handover Date</p>
            <p className="font-semibold">{formatHandoverDate(property.handoverDate) || '—'}</p>
          </div>
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Investment Horizon</p>
            <p className="font-semibold">{futureApp.completionYears ? `${futureApp.completionYears} years` : '—'}</p>
          </div>
        </div>

        {/* Calculation trace — click to expand */}
        <CalcTracePanel trace={topRec?.calcTrace?.growth} section="growth" title="Capital Growth Projection" />
        <CalcTracePanel trace={topRec?.calcTrace?.totalReturn} section="totalReturn" title="ROE & Total Return" />

        {/* Unavailable metrics explanation */}
        {!hasExitValue && (
          <div className="mt-4 p-4 bg-amber-50/50 rounded-lg border border-amber-100">
            <p className="text-sm text-apil-gray-700">
              <strong className="text-amber-700">Capital growth rate cannot be estimated</strong> because there is insufficient comparable sales / project growth data.
              Projected growth metrics are therefore marked as N/A. ROE is calculated independently from the purchase price, payment plan, and exit value.
            </p>
          </div>
        )}

        {/* Rental income note for rental goal */}
        {rentalGoal && (
          <div className="mt-4 p-4 bg-blue-50/50 rounded-lg">
            <p className="text-sm text-apil-gray-700">
              <strong className="text-blue-700">Rental Income Focus:</strong> No rental income until handover{safeVal(property.constructionYears) != null ? ` (~${property.constructionYears} years)` : ''}.
              {postHandoverROI.estimatedRent
                ? ` Post-handover estimated rent: ${fmtAEDsafe(postHandoverROI.estimatedRent)}/year.`
                : ' Rental estimates will be available after handover.'}
              Capital appreciation shown above is secondary to rental yield for this strategy.
            </p>
            {topRec?.returns?.rental?.annualRent != null && topRec.returns.rental.annualRent > 0 && (
              <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                <div>
                  <p className="text-xs text-apil-gray-500">Gross Yield</p>
                  <p className="font-semibold text-apil-gray-900">{topRec.returns.rental.grossYieldPct != null ? `${topRec.returns.rental.grossYieldPct.toFixed(2)}%` : '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-apil-gray-500">Net Yield</p>
                  <p className="font-semibold text-apil-gray-900">{topRec.returns.rental.netYieldPct != null ? `${topRec.returns.rental.netYieldPct.toFixed(2)}%` : '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-apil-gray-500">Service Charge</p>
                  <p className="font-semibold text-red-500">-{fmtAEDsafe(topRec.returns.rental.serviceCharge)}</p>
                </div>
                <div>
                  <p className="text-xs text-apil-gray-500">Net Income/Year</p>
                  <p className="font-semibold text-green-600">{fmtAEDsafe(topRec.returns.rental.netAnnualIncome)}</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Price comparison — developer price vs completed value */}
      {hasExitValue && (
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <DollarSign className="w-5 h-5 text-apil-blue" />
          <h3 className="font-semibold text-apil-gray-900">Price vs Completed Value</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Developer Price</p>
            <p className="text-xl font-bold text-apil-gray-900 mt-1">{fmtAEDsafe(askingPrice)}</p>
          </div>
          <div className="text-center p-4 bg-blue-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Estimated Completed Value</p>
            <p className="text-xl font-bold text-apil-blue mt-1">{fmtAEDsafe(futureApp.futureValue)}</p>
            <p className="text-xs text-apil-gray-400 mt-1">At handover</p>
          </div>
          <div className={`text-center p-4 rounded-xl ${safeVal(priceOpp.priceDifferencePct) != null ? (priceOpp.priceDifferencePct <= 0 ? 'bg-green-50' : 'bg-red-50') : 'bg-apil-gray-50'}`}>
            <p className="text-xs text-apil-gray-500">Price vs Market Today</p>
            <p className={`text-xl font-bold mt-1 ${safeVal(priceOpp.priceDifferencePct) != null ? (priceOpp.priceDifferencePct <= 0 ? 'text-green-600' : 'text-red-500') : 'text-apil-gray-400'}`}>
              {fmtPct(priceOpp.priceDifferencePct)}
            </p>
          </div>
        </div>
        {priceOpp.label && (
          <p className="text-sm text-apil-gray-600">
            <strong className="text-apil-blue">{priceOpp.label}:</strong> The developer is asking{' '}
            {safeVal(priceOpp.priceDifferencePct) == null ? 'N/A' :
             Math.abs(priceOpp.priceDifferencePct) < 0.1 ? 'at fair market value' :
             priceOpp.priceDifferencePct < 0 ? `${Math.abs(priceOpp.priceDifferencePct).toFixed(1)}% below` :
             `${priceOpp.priceDifferencePct.toFixed(1)}% above`}{' '}
            the current estimated market value.
          </p>
        )}
      </div>
      )}

      {/* Alternative rental strategy for capital growth investors */}
      {growthGoal && hasRental && (
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <DollarSign className="w-5 h-5 text-apil-gray-400" />
            <h3 className="font-semibold text-apil-gray-700">Alternative: Rent After Handover</h3>
          </div>
          <p className="text-xs text-apil-gray-500 mb-3">Rental income is not the primary return model for this strategy, but may be considered as an alternative.</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
              <p className="text-xs text-apil-gray-500">Expected Rent</p>
              <p className="font-semibold text-apil-gray-900">{fmtAEDsafe(postHandoverROI.estimatedRent)}</p>
            </div>
            <div>
              <p className="text-xs text-apil-gray-500">Gross Yield</p>
              <p className="font-semibold text-apil-gray-900">{postHandoverROI.grossYield != null ? `${postHandoverROI.grossYield.toFixed(2)}%` : '—'}</p>
            </div>
            <div>
              <p className="text-xs text-apil-gray-500">Net Yield</p>
              <p className="font-semibold text-apil-gray-900">{postHandoverROI.netYield != null ? `${postHandoverROI.netYield.toFixed(2)}%` : '—'}</p>
            </div>
            <div>
              <p className="text-xs text-apil-gray-500">Net Income</p>
              <p className="font-semibold text-apil-gray-900">{fmtAEDsafe(postHandoverROI.netAnnualIncome)}</p>
            </div>
          </div>
          <CalcTracePanel trace={topRec?.calcTrace?.rental} section="rental" title="Rental Yield Calculation" />
        </div>
      )}

      {growthGoal && !hasRental && (
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="w-5 h-5 text-apil-gray-400" />
            <h3 className="font-semibold text-apil-gray-700">Alternative: Rent After Handover</h3>
          </div>
          <p className="text-sm text-apil-gray-500">Alternative rental strategy unavailable — insufficient rental transaction data.</p>
        </div>
      )}

      {/* Off-Plan Stress Tests — real off-plan risk scenarios */}
      <div className="premium-card p-6">
        <h3 className="font-semibold text-apil-gray-900 mb-1">What If? — Off-Plan Risk Scenarios</h3>
        <p className="text-xs text-apil-gray-500 mb-4">How does the investment hold up under real-world off-plan risks?</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Construction Delay */}
          {showConstructionStress && (
          <div className="p-4 bg-red-50/30 rounded-lg border border-red-100">
            <p className="text-sm font-semibold text-apil-gray-700 mb-2">Construction delayed 12 months</p>
            <div className="flex items-center gap-3 text-sm mb-2">
              <div>
                <p className="text-xs text-apil-gray-500">Expected Exit</p>
                <p className="font-semibold text-apil-gray-900">{futureApp.completionYears ? `${futureApp.completionYears}y` : '—'}</p>
              </div>
              <span className="text-apil-gray-400">→</span>
              <div>
                <p className="text-xs text-apil-gray-500">Delayed Exit</p>
                <p className="font-semibold text-red-500">{futureApp.completionYears ? `${futureApp.completionYears + 1}y` : '—'}</p>
              </div>
            </div>
            <p className="text-xs text-amber-600 font-medium">Additional carrying costs + delayed rental income. Opportunity cost of tied-up capital.</p>
          </div>
          )}

          {/* Payment Plan Increase */}
          {showPaymentStress && (
          <div className="p-4 bg-amber-50/30 rounded-lg border border-amber-100">
            <p className="text-sm font-semibold text-apil-gray-700 mb-2">Developer increases down payment</p>
            <div className="flex items-center gap-3 text-sm mb-2">
              <div>
                <p className="text-xs text-apil-gray-500">Current Down</p>
                <p className="font-semibold text-apil-gray-900">{ppAnalysis.downPaymentPct ? `${ppAnalysis.downPaymentPct}%` : '—'}</p>
              </div>
              <span className="text-apil-gray-400">→</span>
              <div>
                <p className="text-xs text-apil-gray-500">Stressed</p>
                <p className="font-semibold text-amber-600">{ppAnalysis.downPaymentPct ? `${ppAnalysis.downPaymentPct + 10}%` : '—'}</p>
              </div>
            </div>
            <p className="text-xs text-amber-600 font-medium">+10% down payment increases upfront capital commitment and reduces leverage.</p>
          </div>
          )}

          {/* Rental Below Forecast — only if rental data exists */}
          {showRentalStress && (
            <div className={`p-4 bg-orange-50/30 rounded-lg border border-orange-100 ${growthGoal ? 'opacity-70' : ''}`}>
              <p className="text-sm font-semibold text-apil-gray-700 mb-2">Rental 10% below forecast after handover{growthGoal ? ' (alternative scenario)' : ''}</p>
              {topRec?.postHandoverROI?.estimatedRent != null ? (
                <>
                  <div className="flex items-center gap-3 text-sm mb-2">
                    <div>
                      <p className="text-xs text-apil-gray-500">Projected Rent</p>
                      <p className="font-semibold text-apil-gray-900">{fmtAEDsafe(topRec?.postHandoverROI?.estimatedRent)}</p>
                    </div>
                    <span className="text-apil-gray-400">→</span>
                    <div>
                      <p className="text-xs text-apil-gray-500">Stressed Rent</p>
                      <p className="font-semibold text-orange-500">{fmtAEDsafe(topRec.postHandoverROI.estimatedRent * 0.9)}</p>
                    </div>
                  </div>
                  <p className="text-xs text-amber-600 font-medium">Lower yield extends break-even period. Verify rent estimates with local agents.</p>
                </>
              ) : (
                <p className="text-xs text-apil-gray-500">Rental forecast unavailable due to insufficient lease data.</p>
              )}
            </div>
          )}

          {/* Price Appreciation Lower — only if exit value exists */}
          {showSalePriceStress && (
          <div className="p-4 bg-purple-50/30 rounded-lg border border-purple-100">
            <p className="text-sm font-semibold text-apil-gray-700 mb-2">Sale price 10% lower than projected</p>
            <div className="flex items-center gap-3 text-sm mb-2">
              <div>
                <p className="text-xs text-apil-gray-500">Base ROE (total return)</p>
                <p className="font-semibold text-apil-gray-900">{topRec?.returns?.totalReturn?.roePct != null ? `${topRec.returns.totalReturn.roePct.toFixed(2)}%` : (futureApp.potentialGainPct != null ? `${futureApp.potentialGainPct.toFixed(2)}% (capital gain)` : '—')}</p>
              </div>
              <span className="text-apil-gray-400">→</span>
              <div>
                <p className="text-xs text-apil-gray-500">Stressed ROE</p>
                <p className="font-semibold text-purple-500">{topRec?.returns?.totalReturn?.stressTests?.price_minus_10pct?.roe != null ? `${topRec.returns.totalReturn.stressTests.price_minus_10pct.roe.toFixed(2)}%` : (futureApp.potentialGainPct != null ? `${(futureApp.potentialGainPct * 0.90).toFixed(2)}% (capital gain)` : '—')}</p>
              </div>
            </div>
            {topRec?.returns?.totalReturn?.roePct == null && (
              <p className="text-[10px] text-apil-gray-400 mb-1">ROE unavailable — showing capital gain % as proxy. ROE includes rental income; capital gain does not.</p>
            )}
            {topRec?.returns?.totalReturn?.available && (
              <p className="text-[10px] text-apil-gray-400 mb-1">
                {growthGoal
                  ? 'ROE measures the total return generated on the investor\'s equity. It is calculated as net profit divided by total equity invested. For a sell-at-completion strategy, rental income is zero and ROE reflects the net capital gain after applicable costs.'
                  : 'ROE measures the total return generated on the investor\'s equity. It is calculated as net profit (sale proceeds + rental income − total equity invested − applicable costs) divided by total equity invested. It is not the same as gross rental yield.'
                }
              </p>
            )}
            <p className="text-xs text-amber-600 font-medium">10% price reduction at sale. Reduced capital gain impacts overall ROI.</p>
          </div>
          )}

          {/* Sale price stress unavailable */}
          {!showSalePriceStress && (
            <div className="p-4 bg-gray-50/30 rounded-lg border border-gray-100">
              <p className="text-sm font-semibold text-apil-gray-500 mb-1">Sale-price stress test unavailable</p>
              <p className="text-xs text-apil-gray-400">Projected exit value is not available — cannot calculate price appreciation stress.</p>
            </div>
          )}
        </div>
      </div>

      {/* ROE Cash-Flow Schedule — expandable */}
      {topRec?.returns?.totalReturn?.available && topRec.returns.totalReturn.cashFlows && (
        <ROECashFlowCard totalReturn={topRec.returns.totalReturn} futureApp={futureApp} property={property} />
      )}
    </div>
  );
}

function ROECashFlowCard({ totalReturn, futureApp, property }: { totalReturn: any; futureApp: any; property?: any }) {
  const [expanded, setExpanded] = useState(false);
  const cashFlows: number[] = totalReturn.cashFlows || [];
  const paymentSchedule: {year: number; amount: number; label: string}[] = totalReturn.paymentSchedule || [];
  const inputs = totalReturn.inputs || {};
  const holdingYears = totalReturn.holdingYears || cashFlows.length - 1;
  const rentalStartYear = inputs.rental_start_year ?? 0;
  const timeToHandover = property?.constructionYears ?? null;
  const saleValue = totalReturn.projectedSaleValue || 0;
  const totalRental = totalReturn.totalRentalIncome || 0;

  // Build itemized rows from payment schedule + sale
  const rows: { year: string; inflow: string; outflow: string; net: string; note: string }[] = [];

  if (paymentSchedule.length > 0) {
    // Build descriptive rows from payment schedule
    const saleYear = cashFlows.length - 1;
    let totalOutflowAll = 0;
    let totalInflowAll = 0;

    for (const ps of paymentSchedule) {
      const amt = Math.abs(ps.amount);
      totalOutflowAll += amt;
      const label = ps.label.toLowerCase().includes('down') ? 'Initial'
        : ps.label.toLowerCase().includes('construction') ? 'Construction'
        : ps.label.toLowerCase().includes('handover') ? 'Handover'
        : ps.label;
      rows.push({
        year: label,
        inflow: '—',
        outflow: formatAED(amt),
        net: formatAED(-amt),
        note: ps.label,
      });
    }

    // Add rental income rows if applicable
    if (totalRental > 0 && rentalStartYear < saleYear) {
      const annualRent = totalRental / Math.max(1, saleYear - rentalStartYear);
      totalInflowAll += totalRental;
      rows.push({
        year: 'Rental',
        inflow: formatAED(totalRental),
        outflow: '—',
        net: formatAED(totalRental),
        note: `Rental income (${Math.max(1, saleYear - rentalStartYear)} years × ${formatAED(annualRent)}/yr)`,
      });
    }

    // Add sale row
    if (saleValue > 0) {
      totalInflowAll += saleValue;
      rows.push({
        year: 'Sale',
        inflow: formatAED(saleValue),
        outflow: '—',
        net: formatAED(saleValue),
        note: 'Sale proceeds (net of selling costs)',
      });
    }

    // Add total row
    rows.push({
      year: 'Total',
      inflow: formatAED(totalInflowAll),
      outflow: formatAED(totalOutflowAll),
      net: formatAED(totalInflowAll - totalOutflowAll),
      note: 'Net profit = total inflow − total outflow',
    });
  } else {
    // Fallback: show net cash flows per year
    for (let i = 0; i < cashFlows.length; i++) {
      const cf = cashFlows[i];
      if (i === 0) {
        rows.push({
          year: 'Year 0',
          inflow: '—',
          outflow: formatAED(Math.abs(cf)),
          net: formatAED(cf),
          note: timeToHandover != null ? 'Purchase / deposit payment' : 'Purchase price',
        });
      } else {
        const isSaleYear = i === cashFlows.length - 1;
        const isRentalYear = i > rentalStartYear;
        const notes: string[] = [];
        if (isRentalYear) notes.push('rental income');
        if (isSaleYear) notes.push('sale proceeds');
        if (!isRentalYear && !isSaleYear) notes.push(timeToHandover != null ? 'construction period — no rental' : 'no rental data');
        rows.push({
          year: `Year ${i}`,
          inflow: cf > 0 ? formatAED(cf) : '—',
          outflow: cf < 0 ? formatAED(Math.abs(cf)) : '—',
          net: formatAED(cf),
          note: notes.join(' + '),
        });
      }
    }
  }

  return (
    <div className="premium-card p-6">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full text-left"
      >
        <DollarSign className="w-5 h-5 text-blue-600" />
        <h3 className="font-semibold text-apil-gray-900 flex-1">ROE Cash-Flow Schedule</h3>
        <span className="text-xs text-apil-gray-500">{totalReturn.roePct?.toFixed(2)}% ROE</span>
        <ChevronDown className={`w-4 h-4 text-apil-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>

      {expanded && (
        <div className="mt-4">
          <p className="text-xs text-apil-gray-500 mb-3">
            ROE: <strong>{totalReturn.roePct?.toFixed(2)}%</strong>
            {' · '}Investment period: <strong>{holdingYears} years</strong>
            {timeToHandover != null ? <>{' · '}Exit: <strong>At handover</strong></> : null}
            {' · '}Rental income: <strong>{totalRental > 0 ? formatAED(totalRental) : 'AED 0'}</strong>
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-apil-gray-200">
                  <th className="text-left py-2 px-3 font-semibold text-apil-gray-500">Period</th>
                  <th className="text-right py-2 px-3 font-semibold text-apil-gray-500">Inflow</th>
                  <th className="text-right py-2 px-3 font-semibold text-apil-gray-500">Outflow</th>
                  <th className="text-right py-2 px-3 font-semibold text-apil-gray-500">Net Cash Flow</th>
                  <th className="text-left py-2 px-3 font-semibold text-apil-gray-500">Description</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => {
                  const isTotal = r.year === 'Total';
                  return (
                    <tr key={i} className={`border-b border-apil-gray-100 last:border-0 ${isTotal ? 'border-t-2 border-apil-gray-300 font-bold bg-apil-gray-50' : ''}`}>
                      <td className="py-2 px-3 font-medium text-apil-gray-700">{r.year}</td>
                      <td className="py-2 px-3 text-right text-green-600">{r.inflow}</td>
                      <td className="py-2 px-3 text-right text-red-500">{r.outflow}</td>
                      <td className={`py-2 px-3 text-right font-semibold ${r.net.startsWith('-') ? 'text-red-500' : 'text-green-600'}`}>{r.net}</td>
                      <td className="py-2 px-3 text-xs text-apil-gray-500">{r.note}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div className="p-3 bg-apil-gray-50 rounded-lg">
              <p className="text-xs text-apil-gray-500">Purchase Price</p>
              <p className="font-semibold text-apil-gray-900">{formatAED(inputs.purchase_price)}</p>
            </div>
            <div className="p-3 bg-apil-gray-50 rounded-lg">
              <p className="text-xs text-apil-gray-500">Total Rental Income</p>
              <p className="font-semibold text-green-600">{formatAED(totalReturn.totalRentalIncome)}</p>
            </div>
            <div className="p-3 bg-apil-gray-50 rounded-lg">
              <p className="text-xs text-apil-gray-500">Sale Proceeds</p>
              <p className="font-semibold text-green-600">{formatAED(totalReturn.projectedSaleValue)}</p>
            </div>
            <div className="p-3 bg-apil-gray-50 rounded-lg">
              <p className="text-xs text-apil-gray-500">Total Profit</p>
              <p className="font-semibold text-blue-600">{formatAED(totalReturn.totalProfit)}</p>
            </div>
          </div>

          {/* ROE metrics */}
          {totalReturn.roePct != null && (
            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div className="p-3 bg-emerald-50 rounded-lg">
                <p className="text-xs text-apil-gray-500">Return on Equity (ROE)</p>
                <p className="font-semibold text-emerald-600">{totalReturn.roePct?.toFixed(2)}%</p>
                <p className="text-[10px] text-apil-gray-400 mt-0.5">Net profit / total equity invested</p>
              </div>
              <div className="p-3 bg-apil-gray-50 rounded-lg">
                <p className="text-xs text-apil-gray-500">Total Equity Invested</p>
                <p className="font-semibold text-apil-gray-900">{formatAED(totalReturn.totalEquityInvested)}</p>
                <p className="text-[10px] text-apil-gray-400 mt-0.5">Sum of all investor payments</p>
              </div>
            </div>
          )}

          <p className="mt-3 text-[10px] text-apil-gray-400">
            Model: {totalReturn.model || 'unlevered ROE'}. Formula: {inputs.formula || 'Year 0: -price; Years 1..N: +rent (after construction); Year N: +rent +sale'}.
          </p>
        </div>
      )}
    </div>
  );
}
