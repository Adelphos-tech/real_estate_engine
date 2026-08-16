/**
 * PropertySection — Context-aware property details.
 *
 * Ready property:
 *   - Building, transactions, rental yield, maintenance, project quality
 *   - Hide construction, payment plan, expected completion
 *
 * Off-plan property:
 *   - Developer, construction progress, completion, launch phase, remaining inventory
 *   - Hide rental yield, maintenance, transactions
 */
import { Building2, Award, Shield, Hammer, Calendar } from 'lucide-react';
import type { ReportContext } from '../ReportContext';
import { isOffPlan } from '../ReportContext';
import { RiskMatrixCard } from '../../components/RiskMatrixCard';
import { ScoreRing, formatAED, formatNumber } from '../../components/Shared';
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
const fmtNumSafe = (v: any): string => {
  const n = safeVal(v);
  if (n === null) return '—';
  return formatNumber(n);
};
const fmtPct = (v: any, prefix = ''): string => {
  const n = safeVal(v);
  if (n === null) return '—';
  return `${n > 0 ? prefix : ''}${n}%`;
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

function scoreContext(value: number | null): { label: string; color: string } {
  if (value === null) return { label: '—', color: 'text-gray-400' };
  if (value >= 80) return { label: 'Excellent', color: 'text-green-600' };
  if (value >= 65) return { label: 'Good', color: 'text-blue-600' };
  if (value >= 50) return { label: 'Fair', color: 'text-amber-600' };
  if (value >= 35) return { label: 'Weak', color: 'text-orange-600' };
  return { label: 'Poor', color: 'text-red-500' };
}

interface PropertySectionProps {
  property: any;
  topRec: any;
  ctx: ReportContext;
  project?: any;
}

export function PropertySection({ property, topRec, ctx, project }: PropertySectionProps) {
  if (isOffPlan(ctx)) {
    return <OffPlanPropertySection property={property} topRec={topRec} ctx={ctx} />;
  }
  return <ReadyPropertySection property={property} topRec={topRec} ctx={ctx} project={project} />;
}

// ═══════════════════════════════════════════════════
// READY PROPERTY
// ═══════════════════════════════════════════════════

function ReadyPropertySection({ property, topRec, ctx, project }: PropertySectionProps) {
  const liqScore = safeVal(property.liquidityScore);
  const liqLabel = property.liquidityLabel || '—';
  const sellTime = liqScore !== null ? (liqScore >= 80 ? 'Within ~30 days' : liqScore >= 60 ? '1–3 months' : liqScore >= 40 ? '3–6 months' : '6+ months') : '—';
  const devScore = safeVal(property.developerScore);
  const devCtx = scoreContext(devScore);
  const liqCtx = scoreContext(liqScore);

  return (
    <div className="space-y-4">
      {/* Building Profile */}
      {project && (
        <div className="premium-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-apil-gray-900">Building: {project.name}</h3>
              <p className="text-xs text-apil-gray-500">
                {project.area || 'Dubai'} · {project.status || 'Ready'} · {fmtCount(project.transactionVolume, 'transactions')}
              </p>
            </div>
            <ScoreRing score={scoreOrNA(project.projectScore)} size={64} label="Building" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-4 bg-apil-gray-50 rounded-lg">
              <p className="text-xs text-apil-gray-500">Price/sqft</p>
              <p className="text-sm font-bold">AED {fmtNumSafe(project.priceSqft)}</p>
            </div>
            {project.medianPrice ? (
              <div className="p-4 bg-apil-gray-50 rounded-lg">
                <p className="text-xs text-apil-gray-500">Median Price</p>
                <p className="text-sm font-bold">{fmtAEDsafe(project.medianPrice)}</p>
              </div>
            ) : null}
            {ctx.hasRentalEvidence && project.rentalYield ? (
              <div className="p-4 bg-apil-gray-50 rounded-lg">
                <p className="text-xs text-apil-gray-500">Rental Yield</p>
                <p className="text-sm font-bold">{fmtPct(project.rentalYield)}</p>
                <p className="text-[10px] text-apil-gray-400 mt-0.5">Based on completed comparable units</p>
              </div>
            ) : null}
            {project.priceChangePct ? (
              <div className="p-4 bg-apil-gray-50 rounded-lg">
                <p className="text-xs text-apil-gray-500">Price Change</p>
                <p className="text-sm font-bold">{fmtPct(project.priceChangePct, '+')}</p>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Developer + Liquidity */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {devScore !== null && (
          <div className="premium-card p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-apil-gray-900">Developer</h3>
              <span className={`text-xs font-semibold ${devCtx.color}`}>{devCtx.label}</span>
            </div>
            <p className="text-sm font-medium text-apil-gray-700 mb-2">{property.developerName || 'Unknown'}</p>
            <div className="flex items-center gap-2 mb-3">
              <div className="flex-1 h-2 bg-apil-gray-200 rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${devScore >= 80 ? 'bg-green-500' : devScore >= 65 ? 'bg-blue-500' : devScore >= 50 ? 'bg-amber-500' : 'bg-red-400'}`} style={{ width: `${devScore}%` }} />
              </div>
              <span className="text-sm font-bold text-apil-gray-700">{devScore}</span>
            </div>
            {property.developerData && (
              <div className="space-y-1.5 text-xs text-apil-gray-600">
                {property.developerData.trackRecord && (
                  <div className="flex justify-between"><span>Track Record</span><span className="font-medium">{property.developerData.trackRecord}/100</span></div>
                )}
                {property.developerData.deliveryHistory && (
                  <div className="flex justify-between"><span>Delivery History</span><span className="font-medium">{property.developerData.deliveryHistory}/100</span></div>
                )}
                {property.developerData.constructionQuality && (
                  <div className="flex justify-between"><span>Construction Quality</span><span className="font-medium">{property.developerData.constructionQuality}/100</span></div>
                )}
                {property.developerData.delayRisk && (
                  <div className="flex justify-between"><span>Delay Risk</span><span className="font-medium">{property.developerData.delayRisk}</span></div>
                )}
              </div>
            )}
          </div>
        )}

        {liqScore !== null && (
          <div className="premium-card p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-apil-gray-900">Resale Liquidity</h3>
              <span className={`text-xs font-semibold ${liqCtx.color}`}>{liqCtx.label}</span>
            </div>
            <div className="flex items-center gap-3 mb-3">
              <div className="flex-1 h-2 bg-apil-gray-200 rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${liqScore >= 80 ? 'bg-green-500' : liqScore >= 65 ? 'bg-blue-500' : liqScore >= 50 ? 'bg-amber-500' : 'bg-red-400'}`} style={{ width: `${liqScore}%` }} />
              </div>
              <span className="text-sm font-bold text-apil-gray-700">{liqScore}</span>
            </div>
            <div className="space-y-1.5 text-sm">
              <div className="flex justify-between"><span className="text-apil-gray-600">Est. Time to Sell</span><span className="font-semibold text-apil-blue">{sellTime}</span></div>
              {property.marketPosition && (
                <div className="flex justify-between"><span className="text-apil-gray-600">Market Position</span><span className="font-semibold">{property.marketPosition}</span></div>
              )}
            </div>
            <p className="text-xs text-apil-gray-500 mt-3">
              {liqScore >= 80 ? 'High demand — should sell quickly at a fair price.' : liqScore >= 60 ? 'Decent resale potential. Sellable within a few months.' : 'Selling may take longer. Consider this if you might need to exit quickly.'}
            </p>
          </div>
        )}
      </div>

      {/* Risk Matrix */}
      <RiskMatrixCard property={property} />
      <CalcTracePanel trace={property} section="property" title="Property Data" />
    </div>
  );
}

// ═══════════════════════════════════════════════════
// OFF-PLAN PROPERTY — developer, construction, completion
// ═══════════════════════════════════════════════════

function OffPlanPropertySection({ property, topRec, ctx }: PropertySectionProps) {
  const devData = topRec?.developerData || {};
  const futureApp = topRec?.futureAppreciation || {};
  const ppAnalysis = topRec?.paymentPlanAnalysis || {};
  const listing = topRec?.listingData || {};
  const risk = topRec?.risk || {};

  return (
    <div className="space-y-4">
      {/* Developer */}
      {devData.developerName && (
        <div className="premium-card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
                <Award className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-apil-gray-900">Developer — {devData.developerName}</h3>
                <p className="text-xs text-apil-gray-500">
                  Delay Risk: <span className={`font-medium ${devData.delayRisk === 'Low' ? 'text-green-600' : devData.delayRisk === 'Medium' ? 'text-amber-600' : 'text-red-500'}`}>{devData.delayRisk || '—'}</span>
                  {devData.marketPosition && ` · ${devData.marketPosition}`}
                </p>
              </div>
            </div>
            <ScoreRing score={scoreOrNA(devData.developerScore)} size={80} label="Developer" />
          </div>

          <div className="space-y-3">
            {[
              { label: 'Track Record', value: devData.trackRecord, weight: '30%' },
              { label: 'Delivery History', value: devData.deliveryHistory, weight: '25%' },
              { label: 'Construction Quality', value: devData.constructionQuality, weight: '20%' },
              { label: 'Capital Appreciation', value: devData.capitalAppreciation, weight: '15%' },
              { label: 'Market Reputation', value: devData.marketReputation, weight: '10%' },
            ].filter(b => b.value !== null && b.value !== undefined).map((b, i) => (
              <div key={i}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-apil-gray-700">{b.label}</span>
                    <span className="text-xs text-apil-gray-400">{b.weight}</span>
                  </div>
                  <span className="text-sm font-bold text-apil-gray-900">{b.value}</span>
                </div>
                <div className="h-2 bg-apil-gray-200 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${(b.value || 0) >= 80 ? 'bg-green-500' : (b.value || 0) >= 65 ? 'bg-blue-500' : (b.value || 0) >= 50 ? 'bg-amber-500' : 'bg-red-400'}`} style={{ width: `${Math.min(100, b.value || 0)}%` }} />
                </div>
              </div>
            ))}
          </div>

          {devData.avgResalePremium !== undefined && devData.avgResalePremium !== null && (
            <div className="mt-4 p-3 bg-apil-gray-50 rounded-lg flex justify-between text-sm">
              <span className="text-apil-gray-600">Avg Resale Premium</span>
              <span className="font-semibold text-green-600">{fmtPct(devData.avgResalePremium)}</span>
            </div>
          )}
        </div>
      )}

      {/* Construction Status */}
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Hammer className="w-5 h-5 text-apil-blue" />
          <h3 className="font-semibold text-apil-gray-900">Construction Status</h3>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Completion Timeline</p>
            <p className="text-lg font-bold text-apil-gray-900 mt-1">{futureApp.completionYears ? `${futureApp.completionYears} years` : '—'}</p>
          </div>
          <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Growth Rate (Annual)</p>
            <p className="text-lg font-bold text-green-600 mt-1">{fmtPct(futureApp.growthRate)}</p>
          </div>
          <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Appreciation Score</p>
            <p className="text-lg font-bold text-apil-gray-900 mt-1">{scoreOrNA(futureApp.futureAppreciationScore)}/100</p>
          </div>
          <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
            <p className="text-xs text-apil-gray-500">Status</p>
            <p className="text-lg font-bold text-apil-gray-900 mt-1 capitalize">{property.status || 'Off-Plan'}</p>
          </div>
        </div>
      </div>

      {/* Property Details */}
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Building2 className="w-5 h-5 text-apil-gold" />
          <h3 className="font-semibold text-apil-gray-900">Property Details</h3>
        </div>
        <h2 className="text-xl font-bold text-apil-gray-900">{property.title}</h2>
        <p className="text-sm text-apil-gray-500">{property.area || 'Dubai'} · {property.bedType || '—'} · {fmtAEDsafe(property.askingPrice)}</p>
        <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div><p className="text-xs text-apil-gray-400">Developer Price</p><p className="text-sm font-bold">{fmtAEDsafe(property.askingPrice)}</p></div>
          <div><p className="text-xs text-apil-gray-400">Est. Completed Value</p><p className="text-sm font-bold text-apil-blue">{fmtAEDsafe(topRec?.fairValue?.fairValue)}</p></div>
          <div><p className="text-xs text-apil-gray-400">Size</p><p className="text-sm font-bold">{fmtNumSafe(property.sizeSqft)} sqft</p></div>
          <div><p className="text-xs text-apil-gray-400">Price/sqft</p><p className="text-sm font-bold">AED {fmtNumSafe(property.priceSqft)}</p></div>
        </div>
      </div>

      {/* Risk Matrix */}
      <RiskMatrixCard property={property} />

      {/* Risk Factors */}
      {risk.riskFactors && risk.riskFactors.length > 0 && (
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-amber-500" />
            <h3 className="font-semibold text-apil-gray-900">Risk Factors</h3>
          </div>
          <ul className="space-y-2">
            {risk.riskFactors.map((rf: string, i: number) => (
              <li key={i} className="flex items-start gap-2 text-sm text-apil-gray-700">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 flex-shrink-0 mt-1.5" />{rf}
              </li>
            ))}
          </ul>
        </div>
      )}
      <CalcTracePanel trace={property} section="property" title="Property Data" />
    </div>
  );
}
