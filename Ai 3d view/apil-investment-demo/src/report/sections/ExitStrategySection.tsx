/**
 * ExitStrategySection — Clean exit strategy display.
 * Shows: Recommended exit + timeline + alternative exits.
 */
import { LogOut, Clock, TrendingUp, Home, Repeat } from 'lucide-react';
import type { ReportContext } from '../ReportContext';
import { isOffPlan, isRentalGoal, isGrowthGoal } from '../ReportContext';
import { formatAED } from '../../components/Shared';
import { CalcTracePanel } from './CalcTracePanel';

const safeVal = (v: any): number | null => {
  if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) return null;
  return v;
};

interface ExitStrategyProps {
  property: any;
  topRec: any;
  ctx: ReportContext;
  strategy?: any;
  reportContract?: any;
}

export function ExitStrategySection({ property, topRec, ctx, strategy, reportContract }: ExitStrategyProps) {
  const exitStrategy = reportContract?.exit_strategy || strategy?.exit_strategy || '';
  const timelineYears = safeVal(strategy?.timelineYears);
  const holdingPeriod = strategy?.holding_description
    || (timelineYears != null ? `${timelineYears}+ years` : '5+ years');

  const futureApp = topRec?.futureAppreciation || {};
  const completionYears = safeVal(futureApp.completionYears);
  const potentialGainPct = safeVal(futureApp.potentialGainPct);
  const ppAnalysis = topRec?.paymentPlanAnalysis || {};
  const liquidityScore = safeVal(property.liquidityScore) ?? safeVal(topRec?.liquidityScore);
  const netROI = safeVal(property.netROI);
  const hasRentalEvidence = (topRec?.dataQuality?.rentCount || 0) > 0;
  const timeToHandover = safeVal(property.constructionYears);

  // ── Single source of truth: exitStrategy from backend strategy ──
  // Build all exit options, then pick primary from strategy, rest as alternatives
  type ExitOption = { icon: any; label: string; detail: string };

  const offPlanExits: Record<string, ExitOption> = {
    assignment: {
      icon: TrendingUp,
      label: 'Sell before handover (Assignment)',
      detail: 'Sell your contract to a new buyer before construction completes. Profit from launch price appreciation.',
    },
    sell_handover: {
      icon: Home,
      label: 'Sell at completion',
      detail: timeToHandover != null
        ? `Hold until handover${property.handoverDate ? ` in ${property.handoverDate}` : ` (~${timeToHandover} years)`}, then sell at completed value${potentialGainPct != null ? ` (+${potentialGainPct}%)` : ''}.`
        : 'Sell once construction is complete.',
    },
    rent_hold: {
      icon: Repeat,
      label: 'Rent after handover',
      detail: hasRentalEvidence
        ? `Keep the property and rent it out for ongoing income after construction completes.`
        : 'Rental performance cannot be estimated — insufficient lease data in this area.',
    },
    hold_5yr: {
      icon: Repeat,
      label: 'Rent after handover & hold long-term',
      detail: hasRentalEvidence
        ? `After handover${timeToHandover != null ? ` (~${timeToHandover} years)` : ''}, rent the property and hold for ${holdingPeriod.toLowerCase()}. Build long-term rental income.`
        : `After handover, hold for ${holdingPeriod.toLowerCase()}. Rental performance cannot be estimated — insufficient lease data.`,
    },
  };

  const readyExits: Record<string, ExitOption> = {
    rent_hold: {
      icon: Home,
      label: 'Rent and hold',
      detail: netROI != null ? `Rent out for ${netROI.toFixed(1)}% net yield annually. Build long-term equity while collecting income.` : 'Rent out for ongoing rental income while building equity.',
    },
    hold_5yr: {
      icon: Home,
      label: 'Rent and hold long-term',
      detail: netROI != null ? `Rent out for ${netROI.toFixed(1)}% net yield annually. Hold for ${holdingPeriod.toLowerCase()} to build equity.` : `Rent out for ongoing rental income. Hold for ${holdingPeriod.toLowerCase()}.`,
    },
    sell_handover: {
      icon: TrendingUp,
      label: 'Sell for capital gain',
      detail: `Hold ${holdingPeriod.toLowerCase()}, then sell when price appreciates. ${liquidityScore != null && liquidityScore >= 70 ? 'High liquidity — should sell within 1-3 months.' : 'May take 3-6 months to sell.'}`,
    },
    assignment: {
      icon: TrendingUp,
      label: 'Sell for capital gain',
      detail: `Hold ${holdingPeriod.toLowerCase()}, then sell when price appreciates. ${liquidityScore != null && liquidityScore >= 70 ? 'High liquidity — should sell within 1-3 months.' : 'May take 3-6 months to sell.'}`,
    },
  };

  const allExits = isOffPlan(ctx) ? offPlanExits : readyExits;

  // Primary exit from strategy — single source of truth
  const primaryKey = exitStrategy || (isRentalGoal(ctx) ? 'rent_hold' : 'sell_handover');
  const primary = allExits[primaryKey] || allExits['sell_handover'] || allExits['rent_hold'];
  // Deduplicate alternatives by label — some exit codes map to the same display text
  const seenLabels = new Set<string>([primary.label]);
  const alternatives = Object.entries(allExits)
    .filter(([key]) => key !== primaryKey)
    .filter(([, exit]) => {
      if (seenLabels.has(exit.label)) return false;
      seenLabels.add(exit.label);
      return true;
    });

  // For off-plan, show time-to-handover (remaining construction time) and investment horizon separately
  const showConstructionPeriod = isOffPlan(ctx) && (timeToHandover != null || completionYears != null);

  return (
    <div className="space-y-4">
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <LogOut className="w-5 h-5 text-blue-600" />
          <h3 className="font-semibold text-apil-gray-900">Exit Strategy</h3>
        </div>

        {/* Investor Holding Period */}
        <div className="flex items-center gap-3 mb-3 p-3 bg-blue-50 rounded-lg">
          <Clock className="w-5 h-5 text-blue-600" />
          <div>
            <p className="text-xs text-apil-gray-500">Investor Holding Period</p>
            <p className="text-sm font-semibold text-blue-700">{holdingPeriod}</p>
          </div>
        </div>

        {/* Time to Handover — only for off-plan */}
        {showConstructionPeriod && (
          <div className="flex items-center gap-3 mb-5 p-3 bg-amber-50 rounded-lg">
            <Clock className="w-5 h-5 text-amber-600" />
            <div>
              <p className="text-xs text-apil-gray-500">Time to Handover</p>
              <p className="text-sm font-semibold text-amber-700">
                {timeToHandover != null ? `${timeToHandover} years` : '—'}
                {property.handoverDate ? ` · ${property.handoverDate}` : ''}
              </p>
            </div>
          </div>
        )}

        {/* Primary Strategy */}
        <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-2">Primary Strategy</p>
        <div className="p-4 rounded-lg border border-blue-200 bg-blue-50 mb-4">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-blue-100 text-blue-600">
              <primary.icon className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-apil-gray-900">{primary.label}</p>
                <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">Recommended</span>
              </div>
              <p className="text-xs text-apil-gray-600 mt-1">{primary.detail}</p>
            </div>
          </div>
        </div>

        {/* Alternative Strategies */}
        {alternatives.length > 0 && (
          <>
            <p className="text-xs font-semibold text-apil-gray-400 uppercase mb-2">Alternative Scenarios</p>
            <div className="space-y-3">
              {alternatives.map(([key, exit], i) => {
                const Icon = exit.icon;
                return (
                  <div key={i} className="p-4 rounded-lg border border-apil-gray-100 bg-apil-gray-50">
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-apil-gray-100 text-apil-gray-500">
                        <Icon className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-apil-gray-900">{exit.label}</p>
                        <p className="text-xs text-apil-gray-600 mt-1">{exit.detail}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {/* Off-plan payment plan summary */}
        {isOffPlan(ctx) && ppAnalysis.downPaymentPct != null && (
          <div className="mt-4 p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-2">Payment Plan</p>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div><span className="text-apil-gray-500">Down Payment</span><br/><span className="font-bold">{ppAnalysis.downPaymentPct}%</span>{safeVal(property.askingPrice) && <span className="text-xs text-apil-gray-400 ml-1">({formatAED(safeVal(property.askingPrice)! * ppAnalysis.downPaymentPct / 100)})</span>}</div>
              <div><span className="text-apil-gray-500">During Construction</span><br/><span className="font-bold">{ppAnalysis.duringConstructionPct || '—'}%</span>{safeVal(property.askingPrice) && ppAnalysis.duringConstructionPct && <span className="text-xs text-apil-gray-400 ml-1">({formatAED(safeVal(property.askingPrice)! * ppAnalysis.duringConstructionPct / 100)})</span>}</div>
              <div><span className="text-apil-gray-500">On Handover</span><br/><span className="font-bold">{ppAnalysis.onHandoverPct || '—'}%</span>{safeVal(property.askingPrice) && ppAnalysis.onHandoverPct && <span className="text-xs text-apil-gray-400 ml-1">({formatAED(safeVal(property.askingPrice)! * ppAnalysis.onHandoverPct / 100)})</span>}</div>
            </div>
            {ppAnalysis.equityGainPct != null && (
              <p className="text-xs text-green-600 mt-2">Equity gain on down payment: {ppAnalysis.equityGainPct}% ({ppAnalysis.leverageRatio || '—'}x leverage)</p>
            )}
          </div>
        )}
      </div>
      <CalcTracePanel trace={{ ...futureApp, exitStrategy, timelineYears, holdingPeriod }} section="exitStrategy" title="Exit Strategy" />
    </div>
  );
}
