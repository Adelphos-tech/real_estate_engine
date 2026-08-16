/**
 * ConstructionSection — Off-plan only.
 * Shows construction progress, completion timeline, post-handover rental potential.
 * Never shown for ready properties.
 */
import { Hammer, Calendar, Home, Info } from 'lucide-react';
import type { ReportContext } from '../ReportContext';
import { formatAED } from '../../components/Shared';
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

interface ConstructionSectionProps {
  property: any;
  topRec: any;
  ctx: ReportContext;
}

export function ConstructionSection({ property, topRec, ctx }: ConstructionSectionProps) {
  const futureApp = topRec?.futureAppreciation || {};
  const postROI = topRec?.postHandoverROI || {};
  const devData = topRec?.developerData || {};

  return (
    <div className="space-y-4">
      {/* Construction Timeline */}
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Hammer className="w-5 h-5 text-apil-blue" />
          <h3 className="font-semibold text-apil-gray-900">Construction Timeline</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Years to Completion</p>
            <p className="text-xl font-bold text-apil-gray-900 mt-1">{futureApp.completionYears ? `${futureApp.completionYears} years` : '—'}</p>
          </div>
          <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Annual Growth Rate</p>
            <p className="text-xl font-bold text-green-600 mt-1">{fmtPct(futureApp.growthRate)}</p>
          </div>
          <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Developer Delay Risk</p>
            <p className={`text-xl font-bold mt-1 ${devData.delayRisk === 'Low' ? 'text-green-600' : devData.delayRisk === 'Medium' ? 'text-amber-600' : 'text-red-500'}`}>
              {devData.delayRisk || '—'}
            </p>
          </div>
          <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Appreciation Score</p>
            <p className="text-xl font-bold text-apil-gray-900 mt-1">{safeVal(futureApp.futureAppreciationScore) !== null ? `${futureApp.futureAppreciationScore}/100` : '—'}</p>
          </div>
        </div>

        {/* Future value projection */}
        <div className="mt-5 p-4 bg-green-50/50 rounded-lg">
          <p className="text-sm text-apil-gray-700">
            <strong className="text-green-700">Projected Value at Handover:</strong>{' '}
            {fmtAEDsafe(futureApp.futureValue)}
            {futureApp.potentialGainPct && ` (${fmtPct(futureApp.potentialGainPct)} gain from current price)`}
          </p>
        </div>
      </div>

      {/* Post-Handover Rental Income — clearly labeled as AFTER completion */}
      {postROI.estimatedRent && (
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-pink-50 text-pink-600 flex items-center justify-center">
              <Calendar className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-apil-gray-900">Rental Income After Handover</h3>
          </div>
          <p className="text-xs text-apil-gray-500 mb-4">
            Estimated rental income after construction completion. No rental income during construction.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
            <div className="p-4 bg-apil-gray-100 rounded-xl text-center">
              <p className="text-xs text-apil-gray-500">Rental Income Today</p>
              <p className="text-2xl font-bold text-apil-gray-400 mt-1">N/A</p>
              <p className="text-xs text-apil-gray-400 mt-1">Property under construction</p>
            </div>
            <div className="p-4 bg-green-50 rounded-xl text-center">
              <p className="text-xs text-apil-gray-500">Projected First-Year Rent</p>
              <p className="text-2xl font-bold text-green-600 mt-1">{fmtAEDsafe(postROI.estimatedRent)}<span className="text-sm text-apil-gray-400">/year</span></p>
              <p className="text-xs text-apil-gray-400 mt-1">Rental start: After completion (~{futureApp.completionYears || '—'} years)</p>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
            <div><p className="text-xs text-apil-gray-400">Projected Annual Rent</p><p className="text-lg font-bold text-green-600">{fmtAEDsafe(postROI.estimatedRent)}</p></div>
            {postROI.grossROI && <div><p className="text-xs text-apil-gray-400">Projected Gross Yield</p><p className="text-lg font-bold">{fmtPct(postROI.grossROI)}</p></div>}
            {postROI.netROI && <div><p className="text-xs text-apil-gray-400">Projected Net Yield (After Handover)</p><p className="text-lg font-bold text-green-600">{fmtPct(postROI.netROI)}</p></div>}
            {postROI.netAnnualIncome && <div><p className="text-xs text-apil-gray-400">Projected Net Income</p><p className="text-lg font-bold">{fmtAEDsafe(postROI.netAnnualIncome)}</p></div>}
          </div>

          <div className="mt-3 p-3 bg-amber-50/50 rounded-lg text-xs text-amber-700">
            <strong>All rental figures are projected, not current.</strong> Rent source: <span className="font-medium capitalize">{postROI.rentSource || 'estimated'}</span> · ROI applies only after handover · Actual rent may vary based on market conditions at completion.
          </div>
        </div>
      )}

      {/* Exit Strategies */}
      {topRec?.exitStrategies?.strategies?.length > 0 && (
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="w-5 h-5 text-green-600" />
            <h3 className="font-semibold text-apil-gray-900">Exit Strategies</h3>
          </div>
          <p className="text-xs text-apil-gray-500 mb-4">Multiple ways to exit this off-plan investment</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {topRec.exitStrategies.strategies.map((strat: any, i: number) => {
              const isRecommended = topRec.exitStrategies.recommendedStrategy === strat.id;
              return (
                <div key={i} className={`p-4 rounded-xl border-2 ${isRecommended ? 'border-green-300 bg-green-50/50' : 'border-apil-gray-200 bg-apil-gray-50/50'}`}>
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="text-sm font-bold text-apil-gray-900">{strat.name}</h4>
                      {isRecommended && <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium mt-1 inline-block">Recommended</span>}
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${strat.difficulty === 'Easy' ? 'bg-green-100 text-green-700' : strat.difficulty === 'Medium' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}`}>{strat.difficulty}</span>
                  </div>
                  <p className="text-xs text-apil-gray-600 mb-3">{strat.description}</p>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {strat.projectedValue && <div><span className="text-apil-gray-400">Projected Value:</span> <span className="font-semibold">{fmtAEDsafe(strat.projectedValue)}</span></div>}
                    {strat.profit !== undefined && <div><span className="text-apil-gray-400">Profit:</span> <span className="font-semibold text-green-600">{fmtAEDsafe(strat.profit)}</span></div>}
                    {strat.roiOnDownPayment !== undefined && <div><span className="text-apil-gray-400">ROI on Down Payment:</span> <span className="font-semibold text-green-600">{fmtPct(strat.roiOnDownPayment)}</span></div>}
                    {strat.netROI !== undefined && strat.netROI !== null && <div><span className="text-apil-gray-400">Net ROI:</span> <span className="font-semibold">{fmtPct(strat.netROI)}</span></div>}
                  </div>
                  <div className="mt-2 text-xs text-apil-gray-400">
                    <span className="font-medium">Timeline:</span> {strat.timeline}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
      <CalcTracePanel trace={property} section="construction" title="Construction Timeline" />
    </div>
  );
}
