/**
 * PaymentPlanSection — Off-plan only.
 * Shows payment plan analysis, equity gain, installment schedule.
 * Never shown for ready properties.
 */
import { CreditCard, Calendar } from 'lucide-react';
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

interface PaymentPlanSectionProps {
  property: any;
  topRec: any;
  ctx: ReportContext;
}

export function PaymentPlanSection({ property, topRec, ctx }: PaymentPlanSectionProps) {
  const ppAnalysis = topRec?.paymentPlanAnalysis || {};
  const listing = topRec?.listingData || {};
  const paymentPlans = listing.paymentPlans || [];

  // If no payment plan data at all, don't render
  if (!ppAnalysis.downPaymentPct && paymentPlans.length === 0) return null;

  return (
    <div className="space-y-4">
      {/* Payment Plan Analysis with Equity Gain */}
      {ppAnalysis.downPaymentPct != null && (
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <CreditCard className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-apil-gray-900">Payment Plan & Equity Gain</h3>
          </div>
          {ppAnalysis.structure && <p className="text-xs text-apil-gray-500 mb-4">{ppAnalysis.structure}</p>}

          {/* Payment Structure */}
          <div className="grid grid-cols-3 gap-3 mb-5">
            <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-xs text-apil-gray-500">Down Payment</p>
              <p className="text-xl font-bold text-apil-blue mt-1">{ppAnalysis.downPaymentPct}%</p>
              <p className="text-xs text-apil-gray-400">{fmtAEDsafe(ppAnalysis.downPaymentAmount)}</p>
            </div>
            <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-xs text-apil-gray-500">During Construction</p>
              <p className="text-xl font-bold text-amber-600 mt-1">{ppAnalysis.duringConstructionPct || '—'}%</p>
            </div>
            <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-xs text-apil-gray-500">On Handover</p>
              <p className="text-xl font-bold text-green-600 mt-1">{ppAnalysis.onHandoverPct || '—'}%</p>
            </div>
          </div>

          {/* Equity Gain Analysis */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
            <div className="p-4 bg-apil-blue/5 rounded-xl text-center">
              <p className="text-xs text-apil-gray-500">Cash Invested Today</p>
              <p className="text-2xl font-bold text-apil-blue mt-1">{fmtAEDsafe(ppAnalysis.cashInvestedToday)}</p>
              <p className="text-xs text-apil-gray-400 mt-1">Down payment only</p>
            </div>
            <div className="p-4 bg-green-50 rounded-xl text-center">
              <p className="text-xs text-apil-gray-500">Projected Value at Handover</p>
              <p className="text-2xl font-bold text-green-600 mt-1">{fmtAEDsafe(ppAnalysis.projectedValueAtHandover)}</p>
              <p className="text-xs text-apil-gray-400 mt-1">Based on area growth</p>
            </div>
            <div className="p-4 bg-green-50 rounded-xl text-center border-2 border-green-200">
              <p className="text-xs text-apil-gray-500">Equity Gain on Down Payment</p>
              <p className="text-2xl font-bold text-green-600 mt-1">{fmtPct(ppAnalysis.equityGainPct)}</p>
              <p className="text-xs text-apil-gray-400 mt-1">{fmtAEDsafe(ppAnalysis.equityGain)} gain · {ppAnalysis.leverageRatio || '—'}x leverage</p>
            </div>
          </div>

          <div className="p-3 bg-apil-gray-50 rounded-lg text-xs text-apil-gray-600">
            <strong>How off-plan leverage works:</strong> You invest {fmtAEDsafe(ppAnalysis.cashInvestedToday)} today as down payment.
            If the property value rises to {fmtAEDsafe(ppAnalysis.projectedValueAtHandover)} by handover, your equity grows by {fmtPct(ppAnalysis.equityGainPct)} on your invested capital —
            a {ppAnalysis.leverageRatio || '—'}x leverage advantage.
          </div>

          {/* Installment Schedule */}
          {ppAnalysis.installments && ppAnalysis.installments.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-xs font-semibold text-apil-gray-500 uppercase">Installment Schedule</p>
              {ppAnalysis.installments.map((inst: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-3 bg-apil-gray-50 rounded-lg">
                  <div>
                    <span className="text-sm font-medium text-apil-gray-700">{inst.label || `Installment ${i + 1}`}</span>
                    {inst.timing && <p className="text-xs text-apil-gray-400">{inst.timing}</p>}
                  </div>
                  <span className="text-sm font-bold text-apil-gray-900">{inst.percentage}%</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Raw Payment Plans from listing */}
      {paymentPlans.length > 0 && (
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="w-5 h-5 text-purple-500" />
            <h3 className="font-semibold text-apil-gray-900">Available Payment Plans</h3>
          </div>
          <div className="space-y-3">
            {paymentPlans.map((plan: any, i: number) => (
              <div key={i} className="p-4 bg-apil-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-apil-gray-700">
                    {plan.title || plan.name || `Plan ${i + 1}`}
                  </span>
                  {plan.milestone && <span className="text-xs text-apil-gray-500">{plan.milestone}</span>}
                </div>
                {plan.description && <p className="text-sm text-apil-gray-600">{plan.description}</p>}
                {plan.installments && Array.isArray(plan.installments) && (
                  <div className="mt-3 space-y-1">
                    {plan.installments.map((inst: any, j: number) => (
                      <div key={j} className="flex justify-between text-xs text-apil-gray-600">
                        <span>{inst.label || inst.milestone || `Installment ${j + 1}`}</span>
                        <span className="font-medium">{inst.percentage || inst.percent}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      <CalcTracePanel trace={{ ...ppAnalysis, askingPrice: property?.askingPrice, installments: paymentPlans.flatMap((p: any) => p.installments || []) }} section="paymentPlan" title="Payment Plan" />
    </div>
  );
}
