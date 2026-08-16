/**
 * RiskSection — Consolidated risk analysis.
 * Shows: Overall risk level + top risk factors + stress test (collapsed).
 * No duplicate risk sections, no "Risk Matrix" with 0% values.
 */
import { useState } from 'react';
import { ShieldAlert, ChevronDown, ChevronUp } from 'lucide-react';
import type { ReportContext } from '../ReportContext';
import { isOffPlan } from '../ReportContext';
import { CalcTracePanel } from './CalcTracePanel';

const safeVal = (v: any): number | null => {
  if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) return null;
  return v;
};

interface RiskSectionProps {
  property: any;
  topRec: any;
  ctx: ReportContext;
}

function RiskWeightsTable({ components, weights, overallRisk }: {
  components: Record<string, number | null>;
  weights: Record<string, number>;
  overallRisk: number | null;
}) {
  const [expanded, setExpanded] = useState(false);

  const riskLabels: Record<string, string> = {
    developerRisk: 'Developer', supplyRisk: 'Supply', pricePremiumRisk: 'Pricing',
    marketVolatilityRisk: 'Market Volatility', rentalRisk: 'Rental',
    constructionRisk: 'Construction', liquidityRisk: 'Liquidity',
  };

  const totalWeight = Object.entries(weights)
    .filter(([key]) => components[key] != null)
    .reduce((sum, [, w]) => sum + (w as number), 0);

  const rows = Object.entries(weights)
    .filter(([key]) => components[key] != null)
    .map(([key, weight]) => {
      const score = components[key] ?? 0;
      const contribution = (score * weight) / (totalWeight || 100);
      return { key, label: riskLabels[key] || key, weight, score, contribution };
    })
    .sort((a, b) => b.contribution - a.contribution);

  return (
    <div className="mt-4">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-left p-2 bg-apil-gray-50 rounded-lg"
      >
        <span className="text-xs font-semibold text-apil-gray-500 uppercase">How is the risk score calculated?</span>
        <span className="text-xs text-apil-gray-400">{expanded ? 'Hide' : 'Show'}</span>
      </button>
      {expanded && (
        <div className="mt-2 p-3 bg-apil-gray-50 rounded-lg">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-apil-gray-200">
                <th className="text-left py-1.5 font-semibold text-apil-gray-500">Risk Component</th>
                <th className="text-center py-1.5 font-semibold text-apil-gray-500">Score</th>
                <th className="text-center py-1.5 font-semibold text-apil-gray-500">Weight</th>
                <th className="text-right py-1.5 font-semibold text-apil-gray-500">Contribution</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.key} className="border-b border-apil-gray-100">
                  <td className="py-1.5 text-apil-gray-700">{row.label}</td>
                  <td className="py-1.5 text-center font-semibold text-apil-gray-700">{Math.round(row.score)}</td>
                  <td className="py-1.5 text-center text-apil-gray-500">{row.weight}</td>
                  <td className="py-1.5 text-right font-semibold text-apil-gray-700">{row.contribution.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-apil-gray-200">
                <td className="py-1 font-bold text-apil-gray-900" colSpan={3}>Final Risk Score</td>
                <td className="py-1 text-right font-bold text-apil-gray-900">{overallRisk != null ? `${overallRisk}/100` : 'N/A'}</td>
              </tr>
            </tfoot>
          </table>
          <p className="text-[10px] text-apil-gray-400 mt-2">
            Formula: Risk Score = Σ(component_score × weight) / Σ(active_weights).
            Higher scores indicate higher risk. Missing components are excluded.
          </p>
        </div>
      )}
    </div>
  );
}

export function RiskSection({ property, topRec, ctx }: RiskSectionProps) {
  const [showStress, setShowStress] = useState(false);
  const risk = topRec?.risk || property.risk || {};
  const overallRisk = safeVal(risk.overallRisk) != null ? Math.round(safeVal(risk.overallRisk) as number) : null;
  const riskLevel = risk.riskLevel || '—';
  const components = risk.components || {};
  const devData = topRec?.developerData || {};
  const communityData = topRec?.communityData || {};
  const dq = topRec?.dataQuality || {};

  // Map component keys to readable labels
  const riskLabels: Record<string, string> = {
    priceRisk: 'Pricing',
    liquidityRisk: 'Liquidity',
    futureSupplyRisk: 'Supply',
    developerRisk: 'Developer',
    rentalRisk: 'Rental',
    marketRisk: 'Market',
    constructionRisk: 'Construction',
    areaRisk: 'Area',
    financialRisk: 'Financial',
    delayRisk: 'Delay',
    marketVolatilityRisk: 'Market Volatility',
    constructionDelayRisk: 'Construction Delay',
    supplyRisk: 'Supply',
    paymentPlanRisk: 'Payment Plan',
  };

  // Build risk factors — only show non-zero, sorted by severity
  const riskFactors = Object.entries(components)
    .filter(([, v]: [string, any]) => { const n = safeVal(v); return n !== null && n > 0; })
    .map(([k, v]: [string, any]) => ({ key: k, label: riskLabels[k] || k, value: Math.round(v as number) }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 5);

  // Stress test scenarios
  const netROI = safeVal(property.netROI);
  const askingPrice = safeVal(property.askingPrice) || 0;
  const estRent = safeVal(property.estimatedRent) || 0;
  const stressScenarios = [];

  if (estRent > 0) {
    const rentDown = estRent * 0.9;
    const serviceCharge = safeVal(property.serviceChargeAnnual) || 0;
    const mgmtFee = safeVal(property.managementFee) || 0;
    const vacancy = safeVal(property.vacancyRate) || 0;
    const rentDownNet = rentDown - serviceCharge - (rentDown * (mgmtFee / estRent || 0)) - (rentDown * vacancy);
    const rentDownROI = askingPrice > 0 ? Math.round((rentDownNet / askingPrice) * 1000) / 10 : 0;
    stressScenarios.push({
      label: 'Rents drop 10%',
      impact: `ROI: ${netROI != null ? netROI.toFixed(1) : '—'}% → ${rentDownROI}%`,
      severity: rentDownROI >= 6 ? 'low' : rentDownROI >= 4 ? 'medium' : 'high',
    });
  }

  if (askingPrice > 0 && netROI != null && netROI > 0) {
    const negotiatedPrice = askingPrice * 0.95;
    const negotiatedROI = Math.round((netROI * askingPrice / negotiatedPrice) * 10) / 10;
    stressScenarios.push({
      label: 'Negotiate 5% off price',
      impact: `ROI: ${netROI.toFixed(1)}% → ${negotiatedROI}%`,
      severity: 'low',
    });
  }

  if (isOffPlan(ctx)) {
    const futureApp = topRec?.futureAppreciation || {};
    if (futureApp.completionYears) {
      stressScenarios.push({
        label: '1-year construction delay',
        impact: `Additional carrying cost, delayed rental start`,
        severity: 'medium',
      });
    }
  }

  const isInsufficientRisk = riskLevel === 'Insufficient Data';
  const riskColor = isInsufficientRisk ? 'text-gray-500' : riskLevel === 'Low' ? 'text-green-600' : riskLevel === 'Medium' ? 'text-amber-600' : 'text-red-500';
  const riskBg = isInsufficientRisk ? 'bg-gray-50' : riskLevel === 'Low' ? 'bg-green-50' : riskLevel === 'Medium' ? 'bg-amber-50' : 'bg-red-50';

  return (
    <div className="space-y-4">
      {/* Overall Risk */}
      <div className={`premium-card p-6 ${riskBg} border-l-4`} style={{ borderLeftColor: isInsufficientRisk ? '#9ca3af' : riskLevel === 'Low' ? '#16a34a' : riskLevel === 'Medium' ? '#f59e0b' : '#dc2626' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-6 h-6 text-apil-gray-600" />
            <div>
              <p className="text-xs font-semibold text-apil-gray-500 uppercase">Property Risk</p>
              <h3 className={`text-2xl font-bold ${riskColor}`}>{riskLevel}</h3>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-apil-gray-500">Risk Score</p>
            <p className={`text-3xl font-bold ${riskColor}`}>{(isInsufficientRisk || overallRisk == null) ? 'N/A' : overallRisk}{!isInsufficientRisk && overallRisk != null && <span className="text-sm text-apil-gray-400">/100</span>}</p>
          </div>
        </div>
      </div>

      {/* Main Concerns — top risk factors */}
      {riskFactors.length > 0 && (
        <div className="premium-card p-5">
          <h3 className="font-semibold text-apil-gray-900 mb-3">Main Concerns</h3>
          <div className="space-y-3">
            {riskFactors.map((rf, i) => (
              <div key={i}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-apil-gray-700">{rf.label}</span>
                  <span className={`text-xs font-bold ${rf.value > 40 ? 'text-red-500' : rf.value > 20 ? 'text-amber-600' : 'text-green-600'}`}>
                    {rf.value}/100
                  </span>
                </div>
                <div className="h-1.5 bg-apil-gray-200 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${rf.value > 40 ? 'bg-red-400' : rf.value > 20 ? 'bg-amber-400' : 'bg-green-400'}`} style={{ width: `${Math.min(100, rf.value)}%` }} />
                </div>
              </div>
            ))}
          </div>

          {/* Risk weights breakdown — makes Risk Score auditable */}
          {risk.weights && Object.keys(risk.weights).length > 0 && (
            <RiskWeightsTable
              components={components}
              weights={risk.weights}
              overallRisk={overallRisk}
            />
          )}
          <CalcTracePanel trace={topRec?.calcTrace?.risk} section="risk" title="Risk Score Calculation" />
        </div>
      )}

      {/* Insufficient data explanation */}
      {isInsufficientRisk && (
        <div className="premium-card p-4 bg-gray-50 border border-gray-200">
          <p className="text-sm text-apil-gray-600">
            An overall risk score cannot be calculated reliably because insufficient market, sales, rental, and liquidity data is available. Available risk signals are shown individually above.
          </p>
        </div>
      )}

    </div>
  );
}
