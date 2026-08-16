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
 *     construction progress, expected exit value, capital gain, total return
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
  // CRITICAL: Never coalesce null to 0 for financial metrics.
  // null = genuinely unknown (N/A), 0 = confirmed zero.
  const serviceChargeRaw = safeVal(rentalData.serviceCharge) ?? safeVal(property.serviceChargeAnnual);
  const mgmtFeeRaw = safeVal(rentalData.managementFee) ?? safeVal(property.managementFee);
  const vacancyCostRaw = safeVal(rentalData.vacancyCost);
  const netIncomeRaw = safeVal(rentalData.netAnnualIncome) ?? safeVal(property.netAnnualIncome);

  // For calculations that need numbers, use 0 fallback only if ALL components are available
  const hasCompleteCostData = serviceChargeRaw !== null && mgmtFeeRaw !== null && vacancyCostRaw !== null;
  const serviceCharge = serviceChargeRaw ?? 0;
  const mgmtFee = mgmtFeeRaw ?? 0;
  const vacancyCost = vacancyCostRaw ?? 0;
  const netIncome = netIncomeRaw; // Keep null if unknown
  const isCapitalGrowth = isGrowthGoal(ctx);

  // Scenarios — use engine stress test data when available
  const rentStress = stressTests.rent_minus_10pct || {};
  const rentDownROI = safeVal(rentStress.new_net_yield) != null
    ? safeVal(rentStress.new_net_yield)!
    : (askingPrice > 0 && netIncomeRaw != null && netIncomeRaw > 0
      ? Math.round(((netIncomeRaw * 0.9) / askingPrice) * 1000) / 10
      : 0);
  const negotiatedPrice = askingPrice * 0.95;
  const negotiatedROI = negotiatedPrice > 0 && netIncomeRaw != null && netIncomeRaw > 0 ? Math.round((netIncomeRaw / negotiatedPrice) * 1000) / 10 : null;
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
    } else if (grossROI != null && serviceChargeRaw === null) {
      // Gross yield available but net N/A because service charge unknown
      kpiCards.push({
        label: 'Net Yield',
        value: 'N/A',
        sublabel: 'Service charge data unavailable',
        bg: 'bg-gray-50',
        textColor: 'text-gray-400',
      });
    }
    if (netIncomeRaw !== null && netIncomeRaw !== 0) {
      kpiCards.push({
        label: 'Net Income / Year',
        value: formatAED(netIncomeRaw),
        sublabel: 'After costs & vacancy',
        bg: 'bg-green-50',
        textColor: 'text-green-600',
      });
    }
    // Total-return figures come from the engine's dated cash-flow model — never
    // recomputed here. IRR (annualizedReturnPct) prices every payment/rent/sale
    // on its actual year; Total ROI (totalReturnPct) is profit over equity.
    // A 12-month historical trend (growth12) is NOT an annualized projection and
    // must never be added to yield to fake a "total return".
    const totalRoi = safeVal(topRec?.returns?.totalReturn?.totalReturnPct);
    const annualizedIrr = safeVal(topRec?.returns?.totalReturn?.annualizedReturnPct);
    if (annualizedIrr != null) {
      kpiCards.push({
        label: 'Annualized Return (IRR)',
        value: `${annualizedIrr.toFixed(1)}%`,
        sublabel: 'On dated cash flows',
        bg: 'bg-amber-50',
        textColor: 'text-amber-600',
      });
    } else if (totalRoi != null) {
      kpiCards.push({
        label: 'Total Return (ROI)',
        value: `${totalRoi.toFixed(1)}%`,
        sublabel: 'Profit / equity over hold',
        bg: 'bg-amber-50',
        textColor: 'text-amber-600',
      });
    }
  } else {
    kpiCards.push({
      label: 'Net Income / Year',
      value: netIncomeRaw != null ? formatAED(netIncomeRaw) : 'N/A',
      sublabel: netIncomeRaw != null ? 'After all costs' : 'Service charge data unavailable',
      bg: netIncomeRaw != null ? 'bg-green-50' : 'bg-gray-50',
      textColor: netIncomeRaw != null ? 'text-green-600' : 'text-gray-400',
    });
    kpiCards.push({
      label: 'Net Yield',
      value: netROI != null ? `${netROI.toFixed(1)}%` : (grossROI != null ? 'N/A' : '—'),
      sublabel: netROI != null ? 'Annual return on price' : (grossROI != null ? 'Service charge data unavailable' : 'No rental data'),
      bg: netROI != null ? 'bg-blue-50' : (grossROI != null ? 'bg-gray-50' : 'bg-gray-50'),
      textColor: netROI != null ? 'text-blue-600' : 'text-gray-400',
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
                <p className={`font-semibold ${serviceChargeRaw !== null ? 'text-red-500' : 'text-apil-gray-400'}`}>
                  {serviceChargeRaw !== null ? `-${formatAED(serviceCharge)}` : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-xs text-apil-gray-500">Mgmt + Vacancy</p>
                <p className={`font-semibold ${mgmtFeeRaw !== null && vacancyCostRaw !== null ? 'text-red-500' : 'text-apil-gray-400'}`}>
                  {mgmtFeeRaw !== null && vacancyCostRaw !== null
                    ? `-${formatAED(Math.round(mgmtFee + vacancyCost))}`
                    : 'Not modeled'}
                </p>
              </div>
              <div>
                <p className="text-xs text-apil-gray-500">Net Cash Flow</p>
                <p className={`font-semibold ${netIncomeRaw !== null ? (netIncomeRaw > 0 ? 'text-green-600' : 'text-red-500') : 'text-apil-gray-400'}`}>
                  {netIncomeRaw !== null ? formatAED(Math.round(netIncomeRaw)) : 'N/A'}
                </p>
                {netIncomeRaw === null && serviceChargeRaw === null && (
                  <p className="text-[10px] text-amber-600 mt-0.5">Service charge data unavailable</p>
                )}
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
  const hasExitValue = futureApp.futureValue != null && futureApp.futureValue !== undefined;
  const hasGrowthRate = futureApp.growthRate != null && futureApp.growthRate !== undefined;
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

  // Total-return metrics from the engine's dated cash-flow model.
  // roePct here equals totalReturnPct (simple profit / equity) — it is a Total
  // ROI, not an ROE in the financial-accounting sense, so it is labeled as such.
  // The IRR (annualizedReturnPct) prices each payment on its actual year and is
  // shown separately. Neither is ever recomputed in the frontend.
  const trTotal = topRec?.returns?.totalReturn;
  const roePct = safeVal(trTotal?.roePct);
  const irrPct = safeVal(trTotal?.annualizedReturnPct);
  if (roePct != null) {
    kpiCards.push({
      label: 'Total Return on Equity',
      value: `${roePct.toFixed(1)}%`,
      sublabel: 'Profit / total equity invested',
      bg: 'bg-emerald-50',
      textColor: 'text-emerald-600',
    });
  }
  if (irrPct != null) {
    kpiCards.push({
      label: 'Annualized Return (IRR)',
      value: `${irrPct.toFixed(1)}%`,
      sublabel: 'On dated cash flows',
      bg: 'bg-amber-50',
      textColor: 'text-amber-600',
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
            <p className="font-semibold">{futureApp.holdingYears ? `${futureApp.holdingYears} years` : '—'}</p>
          </div>
        </div>

        {/* Calculation trace — click to expand */}
        <CalcTracePanel trace={topRec?.calcTrace?.growth} section="growth" title="Capital Growth Projection" />
        <CalcTracePanel trace={topRec?.calcTrace?.totalReturn} section="totalReturn" title="Total Return & IRR" />

        {/* Unavailable metrics explanation */}
        {!hasExitValue && (
          <div className="mt-4 p-4 bg-amber-50/50 rounded-lg border border-amber-100">
            <p className="text-sm text-apil-gray-700">
              <strong className="text-amber-700">Capital growth rate cannot be estimated</strong> because there is insufficient comparable sales / project growth data.
              Projected growth metrics are therefore marked as N/A. Total ROI is calculated independently from the purchase price, payment plan, and exit value.
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

      {/* Cash-Flow Schedule — expandable */}
      {topRec?.returns?.totalReturn?.available && topRec.returns.totalReturn.cashFlows && (
        <CashFlowCard totalReturn={topRec.returns.totalReturn} futureApp={futureApp} property={property} />
      )}
    </div>
  );
}

function CashFlowCard({ totalReturn, futureApp, property }: { totalReturn: any; futureApp: any; property?: any }) {
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
        <h3 className="font-semibold text-apil-gray-900 flex-1">Cash-Flow Schedule</h3>
        <span className="text-xs text-apil-gray-500">{totalReturn.roePct?.toFixed(2)}% Total ROI</span>
        <ChevronDown className={`w-4 h-4 text-apil-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </button>

      {expanded && (
        <div className="mt-4">
          <p className="text-xs text-apil-gray-500 mb-3">
            Total ROI: <strong>{totalReturn.roePct?.toFixed(2)}%</strong>
            {totalReturn.annualizedReturnPct != null ? <>{' · '}IRR: <strong>{totalReturn.annualizedReturnPct.toFixed(2)}%</strong></> : null}
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

          {/* Total-return metrics: simple Total ROI and timed IRR, both engine-derived */}
          {totalReturn.roePct != null && (
            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div className="p-3 bg-emerald-50 rounded-lg">
                <p className="text-xs text-apil-gray-500">Total Return on Equity (Total ROI)</p>
                <p className="font-semibold text-emerald-600">{totalReturn.roePct?.toFixed(2)}%</p>
                <p className="text-[10px] text-apil-gray-400 mt-0.5">Net profit / total equity invested</p>
              </div>
              {totalReturn.annualizedReturnPct != null && (
                <div className="p-3 bg-amber-50 rounded-lg">
                  <p className="text-xs text-apil-gray-500">Annualized Return (IRR)</p>
                  <p className="font-semibold text-amber-600">{totalReturn.annualizedReturnPct.toFixed(2)}%</p>
                  <p className="text-[10px] text-apil-gray-400 mt-0.5">IRR on dated cash flows</p>
                </div>
              )}
              <div className="p-3 bg-apil-gray-50 rounded-lg">
                <p className="text-xs text-apil-gray-500">Total Equity Invested</p>
                <p className="font-semibold text-apil-gray-900">{formatAED(totalReturn.totalEquityInvested)}</p>
                <p className="text-[10px] text-apil-gray-400 mt-0.5">Sum of all investor payments</p>
              </div>
            </div>
          )}

          <p className="mt-3 text-[10px] text-apil-gray-400">
            Model: {totalReturn.model || 'unlevered Total ROI'}. Formula: {inputs.formula || 'Year 0: -price; Years 1..N: +rent (after construction); Year N: +rent +sale'}.
          </p>

          <CalcTracePanel trace={totalReturn} section="totalReturn" title="Total Return & IRR" />
        </div>
      )}
    </div>
  );
}
