import { Shield, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface RiskDimension {
  label: string;
  value: number;
  description: string;
}

export function RiskMatrixCard({ property }: { property: any }) {
  const rc = property.risk?.components || property.riskComponents || {};
  const dimensions: RiskDimension[] = [
    { label: 'New Supply Nearby', value: rc.futureSupplyRisk ?? 0, description: 'Are many new buildings coming?' },
    { label: 'Developer Track Record', value: rc.developerRisk ?? 0, description: 'Does the developer deliver on time?' },
    { label: 'Area Popularity', value: rc.areaSaturationRisk ?? 0, description: 'Is the area getting oversaturated?' },
    { label: 'Rental Demand', value: rc.rentalRisk ?? 0, description: 'Will tenants want to rent here?' },
    { label: 'Price Stability', value: rc.marketVolatilityRisk ?? 0, description: 'Are prices volatile in this area?' },
    { label: 'Construction Risk', value: rc.constructionDelayRisk ?? 0, description: 'Could the project be delayed?' },
    { label: 'Price vs Market', value: rc.pricePremiumRisk ?? 0, description: 'Is the asking price fair?' },
  ];

  // Calculate weighted overall risk from individual dimensions
  // Weights reflect impact on investment outcome
  const riskWeights: Record<string, number> = {
    'New Supply Nearby': 1.2,
    'Developer Track Record': 1.5,
    'Area Popularity': 0.8,
    'Rental Demand': 1.0,
    'Price Stability': 1.0,
    'Construction Risk': 1.3,
    'Price vs Market': 1.0,
  };
  const validDims = dimensions.filter(d => d.value > 0);
  const totalWeight = validDims.reduce((sum, d) => sum + (riskWeights[d.label] || 1), 0);
  const weightedAvg = totalWeight > 0
    ? validDims.reduce((sum, d) => sum + d.value * (riskWeights[d.label] || 1), 0) / totalWeight
    : 0;
  const calculatedRiskLevel = weightedAvg >= 60 ? 'High' : weightedAvg >= 35 ? 'Medium' : 'Low';

  // Use calculated risk level if individual dimensions contradict the stated level
  const statedRiskLevel = property.riskLevel || 'Medium';
  const individualHighCount = validDims.filter(d => d.value < 35).length;
  const riskLevel = individualHighCount >= 3 && statedRiskLevel === 'Low' ? calculatedRiskLevel : statedRiskLevel;
  const riskColor = riskLevel === 'Low' ? 'text-green-600 bg-green-50' : riskLevel === 'Medium' ? 'text-amber-600 bg-amber-50' : 'text-red-600 bg-red-50';
  const riskEmoji = riskLevel === 'Low' ? '✅' : riskLevel === 'Medium' ? '⚠️' : '🔴';
  const riskOverride = riskLevel !== statedRiskLevel;
  const hasAnyData = validDims.length > 0;

  return (
    <div className="premium-card p-6">
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-semibold text-apil-gray-900">What Could Go Wrong</h3>
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${riskColor}`}>
          <Shield className="w-3.5 h-3.5" />
          {riskLevel} Risk
        </span>
      </div>
      <p className="text-xs text-apil-gray-500 mb-5">Risk factors that could affect your investment</p>

      {riskOverride && (
        <p className="text-xs text-amber-600 mb-3 p-2 bg-amber-50 rounded-lg">
          <strong>Note:</strong> Individual risk dimensions suggest a higher overall risk than the stated level. The overall rating has been adjusted based on the weighted average of individual factors.
        </p>
      )}

      <div className="space-y-3">
        {dimensions.map((dim, i) => {
          const hasData = dim.value > 0;
          const isGood = dim.value >= 60;
          const isMid = dim.value >= 35 && dim.value < 60;
          const verdict = !hasData ? 'Insufficient data' : isGood ? 'Low concern' : isMid ? 'Moderate' : 'High concern';
          return (
            <div key={i} className="flex items-center gap-3">
              <div className="w-36 flex-shrink-0">
                <p className="text-xs font-medium text-apil-gray-700">{dim.label}</p>
                <p className="text-[10px] text-apil-gray-400">{dim.description}</p>
              </div>
              <div className="flex-1 h-2 bg-apil-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${!hasData ? 'bg-gray-300' : isGood ? 'bg-green-500' : isMid ? 'bg-amber-500' : 'bg-red-500'}`}
                  style={{ width: `${Math.min(100, Math.max(0, dim.value))}%` }}
                />
              </div>
              <div className="w-20 text-right flex items-center justify-end gap-1">
                {!hasData ? <span className="text-[10px] text-gray-400">—</span> : isGood ? <CheckCircle2 className="w-3 h-3 text-green-500" /> : <AlertTriangle className="w-3 h-3 text-amber-500" />}
                <span className="text-[10px] font-medium text-apil-gray-600">{verdict}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Weighted Risk Summary Table */}
      <div className="mt-5 pt-4 border-t border-apil-gray-100">
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Weighted Risk Score</p>
            <p className={`text-lg font-bold ${!hasAnyData ? 'text-gray-400' : weightedAvg >= 60 ? 'text-red-500' : weightedAvg >= 35 ? 'text-amber-600' : 'text-green-600'}`}>{hasAnyData ? `${Math.round(weightedAvg)}/100` : 'Insufficient data'}</p>
            <p className="text-[10px] text-apil-gray-400">{hasAnyData ? 'Calculated from individual dimensions' : 'Risk components not available for this property'}</p>
          </div>
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Highest Risk Factor</p>
            <p className="text-sm font-bold text-apil-gray-900">{hasAnyData && validDims.length > 0 ? validDims.reduce((min, d) => d.value < min.value ? d : min).label : 'Insufficient data'}</p>
            <p className="text-[10px] text-apil-gray-400">{hasAnyData && validDims.length > 0 ? `${validDims.reduce((min, d) => d.value < min.value ? d : min).value}/100 risk score` : ''}</p>
          </div>
        </div>
      </div>

      {property.riskFactors && property.riskFactors.length > 0 && (
        <div className="mt-5 pt-4 border-t border-apil-gray-100">
          <h4 className="text-sm font-semibold text-amber-700 mb-2">Things to Watch Out For</h4>
          <div className="space-y-2">
            {property.riskFactors.map((risk: string, i: number) => (
              <div key={i} className="flex items-start gap-2 p-2 bg-amber-50 rounded-lg">
                <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-amber-800">{risk}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
