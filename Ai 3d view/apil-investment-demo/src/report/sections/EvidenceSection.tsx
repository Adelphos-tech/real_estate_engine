/**
 * EvidenceSection — Context-aware evidence display.
 *
 * Never show "0" for unavailable evidence. Instead explain WHY data is unavailable.
 *
 * Ready property:
 *   - Community Evidence, Rental Evidence, Sales Evidence, Building Evidence
 *
 * Off-plan property:
 *   - Developer Evidence, Launch Sales, Construction Data, Area Market, Infrastructure Evidence
 */
import { FileText, Info } from 'lucide-react';
import type { ReportContext } from '../ReportContext';
import { isOffPlan, translateRuleFlag, getConfidenceLabel, getConfidenceColor } from '../ReportContext';
import { formatAED, formatNumber } from '../../components/Shared';
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
const fmtCount = (v: any, label: string): string => {
  const n = safeVal(v);
  if (n === null || n === 0) return '—';
  return `${n} ${label}`;
};
const scoreOrNA = (v: any): number | null => {
  const n = safeVal(v);
  return n === null ? null : n;
};

interface EvidenceSectionProps {
  property: any;
  topRec: any;
  ctx: ReportContext;
  community?: any;
  project?: any;
  dataCompleteness?: any;
}

export function EvidenceSection({ property, topRec, ctx, community, project, dataCompleteness }: EvidenceSectionProps) {
  if (isOffPlan(ctx)) {
    return <OffPlanEvidenceSection property={property} topRec={topRec} ctx={ctx} />;
  }
  return <ReadyEvidenceSection property={property} topRec={topRec} ctx={ctx} community={community} project={project} />;
}

// ═══════════════════════════════════════════════════
// READY EVIDENCE
// ═══════════════════════════════════════════════════

function ReadyEvidenceSection({ property, topRec, ctx, community, project }: EvidenceSectionProps) {
  const dq = topRec?.dataQuality || {};
  const salesCount = dq.salesCount || 0;
  const rentCount = dq.rentCount || 0;
  const confidenceScore = topRec?.confidenceScore || 0;
  const confidenceLevel = getConfidenceLabel(confidenceScore);
  const confidenceColor = getConfidenceColor(confidenceScore);
  const pricingConfidence = (topRec as any)?.pricingConfidence;
  const rentalConfidence = (topRec as any)?.rentalConfidence;
  const pricingConfidenceLabel = (topRec as any)?.pricingConfidenceLabel;
  const rentalConfidenceLabel = (topRec as any)?.rentalConfidenceLabel;
  const rulesFlags = topRec?.rulesFlags || [];
  const riskLevel = property.riskLevel || '—';

  // Build evidence items — explain WHY unavailable instead of showing 0
  const evidenceItems: { label: string; count: number; status: string; explanation?: string }[] = [];

  evidenceItems.push({
    label: 'Comparable Sales',
    count: salesCount,
    status: salesCount >= 20 ? 'Strong' : salesCount >= 10 ? 'Adequate' : salesCount > 0 ? 'Limited' : 'Unavailable',
    explanation: salesCount === 0 ? 'No comparable sales found for this unit type in recent transactions.' : undefined,
  });

  if (ctx.hasRentalEvidence) {
    evidenceItems.push({
      label: 'Rental Contracts',
      count: rentCount,
      status: rentCount >= 20 ? 'Strong' : rentCount >= 10 ? 'Adequate' : rentCount > 0 ? 'Limited' : 'Unavailable',
      explanation: rentCount === 0 ? 'No rental contracts found for this unit type.' : undefined,
    });
  }

  if (project?.transactionVolume) {
    evidenceItems.push({
      label: 'Building Transactions',
      count: project.transactionVolume,
      status: project.transactionVolume >= 50 ? 'Strong' : project.transactionVolume >= 20 ? 'Adequate' : 'Limited',
    });
  } else {
    evidenceItems.push({
      label: 'Building Transactions',
      count: 0,
      status: 'Unavailable',
      explanation: 'Building transaction history is not available for this property.',
    });
  }

  if (community?.salesVolume) {
    evidenceItems.push({
      label: 'Area Sales Volume',
      count: community.salesVolume,
      status: community.salesVolume >= 500 ? 'Strong' : community.salesVolume >= 100 ? 'Adequate' : 'Limited',
    });
  }

  const statusColor: Record<string, string> = {
    'Strong': 'text-green-600',
    'Adequate': 'text-blue-600',
    'Limited': 'text-amber-600',
    'Unavailable': 'text-red-500',
  };

  return (
    <div className="space-y-4">
      <div className="premium-card p-6">
        <h3 className="font-semibold text-apil-gray-900 mb-1">Evidence Used</h3>
        <p className="text-xs text-apil-gray-500 mb-4">The real market data behind this recommendation</p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          {evidenceItems.map((e, i) => (
            <div key={i} className="text-center p-4 bg-apil-gray-50 rounded-xl">
              <p className="text-xs text-apil-gray-500">{e.label}</p>
              <p className="text-2xl font-bold text-apil-gray-900 mt-1">{e.count > 0 ? e.count : '—'}</p>
              <p className={`text-xs font-medium mt-1 ${statusColor[e.status]}`}>{e.status}</p>
              {e.explanation && (
                <p className="text-[10px] text-apil-gray-400 mt-1">{e.explanation}</p>
              )}
            </div>
          ))}
        </div>

        {/* Confidence */}
        <div className="p-4 bg-apil-blue/5 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-apil-gray-700">Recommendation Confidence</span>
            <span className={`text-sm font-bold ${confidenceColor}`}>{confidenceLevel}</span>
          </div>
          <p className="text-xs text-apil-gray-600">
            {salesCount === 0 && rentCount === 0
              ? `Model confidence is ${confidenceLevel.toLowerCase()} (${confidenceScore}%), but comparable transaction evidence is limited. No sales or rental transactions found for this area.`
              : salesCount === 0
              ? `Model confidence is ${confidenceLevel.toLowerCase()} (${confidenceScore}%), but no comparable sales transactions found. ${rentCount} rental transactions available.`
              : rentCount === 0
              ? `Model confidence is ${confidenceLevel.toLowerCase()} (${confidenceScore}%), based on ${salesCount} sales transactions. No rental evidence available.`
              : confidenceScore >= 85
              ? `Very strong evidence — ${salesCount} sales and ${rentCount} rentals support this assessment.`
              : confidenceScore >= 70
              ? `Strong evidence — ${salesCount} sales and ${rentCount} rentals support this assessment.`
              : confidenceScore >= 55
              ? `Moderate evidence — ${salesCount} sales and ${rentCount} rentals. Some projections may be less reliable.`
              : confidenceScore >= 40
              ? `Limited evidence — ${salesCount} sales and ${rentCount} rentals. Treat this recommendation with caution.`
              : `Very limited evidence — only ${salesCount} sales and ${rentCount} rentals. Treat this recommendation with extra caution.`}
          </p>
        </div>

        {/* Split Confidence — pricing vs rental */}
        {pricingConfidence != null && rentalConfidence != null && (
          <div className="mt-3 grid grid-cols-2 gap-3">
            <div className="p-3 bg-apil-gray-50 rounded-lg">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-apil-gray-600">Pricing Confidence</span>
                <span className={`text-xs font-bold ${pricingConfidence >= 70 ? 'text-green-600' : pricingConfidence >= 40 ? 'text-amber-600' : 'text-red-500'}`}>{pricingConfidenceLabel}</span>
              </div>
              <p className="text-[11px] text-apil-gray-500">Based on {salesCount} comparable sales transactions</p>
            </div>
            <div className="p-3 bg-apil-gray-50 rounded-lg">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-apil-gray-600">Rental Confidence</span>
                <span className={`text-xs font-bold ${rentalConfidence >= 60 ? 'text-green-600' : rentalConfidence >= 30 ? 'text-amber-600' : 'text-red-500'}`}>{rentalConfidenceLabel}</span>
              </div>
              <p className="text-[11px] text-apil-gray-500">{rentCount > 0 ? `Based on ${rentCount} lease transactions` : 'No rental evidence available'}</p>
            </div>
          </div>
        )}

        {/* Rule flags — human readable */}
        {rulesFlags.length > 0 && (
          <div className="mt-3 pt-3 border-t border-apil-gray-200">
            <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-2">Validation Notes</p>
            <ul className="space-y-1.5">
              {rulesFlags.map((flag: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-xs text-apil-gray-600">
                  <Info className="w-3 h-3 text-amber-500 flex-shrink-0 mt-0.5" />
                  {translateRuleFlag(flag)}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Risk vs Confidence */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="premium-card p-5">
          <h3 className="font-semibold text-apil-gray-900 mb-2">Investment Risk</h3>
          <p className={`text-2xl font-bold ${riskLevel === 'Low' ? 'text-green-600' : riskLevel === 'Medium' ? 'text-amber-600' : 'text-red-500'}`}>{riskLevel}</p>
          <p className="text-xs text-apil-gray-500 mt-1">Overall risk profile of this investment</p>
        </div>
        <div className="premium-card p-5">
          <h3 className="font-semibold text-apil-gray-900 mb-2">Data Confidence</h3>
          <p className={`text-2xl font-bold ${confidenceColor}`}>{confidenceLevel}</p>
          <p className="text-xs text-apil-gray-500 mt-1">How much market evidence supports this analysis</p>
        </div>
      </div>

      {/* Data Sources */}
      <div className="premium-card p-5">
        <h3 className="text-sm font-semibold text-apil-gray-900 mb-3">Data Sources</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          {community && (
            <div className="p-3 bg-apil-gray-50 rounded-lg">
              <p className="font-semibold text-apil-gray-700 mb-1">Area: {community.name}</p>
              <p className="text-apil-gray-500">{fmtCount(community.salesVolume, 'sales')} · {fmtCount(community.rentVolume, 'rents')}</p>
              {community.medianPriceSqft && <p className="text-apil-gray-500">Median: AED {fmtNumSafe(community.medianPriceSqft)}/sqft</p>}
            </div>
          )}
          {project && (
            <div className="p-3 bg-apil-gray-50 rounded-lg">
              <p className="font-semibold text-apil-gray-700 mb-1">Building: {project.name}</p>
              <p className="text-apil-gray-500">{fmtCount(project.transactionVolume, 'transactions')}</p>
              {project.medianPrice && <p className="text-apil-gray-500">Median: {fmtAEDsafe(project.medianPrice)}</p>}
            </div>
          )}
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="font-semibold text-apil-gray-700 mb-1">This Property</p>
            <p className="text-apil-gray-500">Score: {scoreOrNA(property.overallScore || property.propertyScore)}/100</p>
            {property.developerName && <p className="text-apil-gray-500">Developer: {property.developerName}</p>}
          </div>
        </div>
        <p className="text-xs text-apil-gray-400 mt-3">Data sourced from Dubai Land Department (DLD) verified transaction records. Scores are analytical estimates based on historical data. Past performance does not predict future results.</p>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════
// OFF-PLAN EVIDENCE
// ═══════════════════════════════════════════════════

function OffPlanEvidenceSection({ property, topRec, ctx }: EvidenceSectionProps) {
  const devData = topRec?.developerData || {};
  const commData = topRec?.communityData || {};
  const liquidity = topRec?.liquidity || {};
  const futureApp = topRec?.futureAppreciation || {};
  const ppAnalysis = topRec?.paymentPlanAnalysis || {};
  const confidenceScore = topRec?.confidenceScore || 0;
  const confidenceLevel = getConfidenceLabel(confidenceScore);
  const confidenceColor = getConfidenceColor(confidenceScore);
  const rulesFlags = topRec?.rulesFlags || [];
  const riskLevel = topRec?.risk?.riskLevel || property.riskLevel || '—';

  const evidenceItems: { label: string; value: string; status: string; explanation?: string }[] = [];

  // Developer Evidence
  evidenceItems.push({
    label: 'Developer Evidence',
    value: devData.developerName ? `${devData.developerScore || '—'}/100` : '—',
    status: (devData.developerScore || 0) >= 70 ? 'Strong' : (devData.developerScore || 0) >= 50 ? 'Adequate' : devData.developerName ? 'Limited' : 'Unavailable',
    explanation: !devData.developerName ? 'Developer information is not available for this project.' : undefined,
  });

  // Launch Sales
  evidenceItems.push({
    label: 'Launch Sales',
    value: liquidity.transactionVolume ? fmtNumSafe(liquidity.transactionVolume) : '—',
    status: (liquidity.transactionVolume || 0) >= 100 ? 'Strong' : (liquidity.transactionVolume || 0) >= 20 ? 'Adequate' : (liquidity.transactionVolume || 0) > 0 ? 'Limited' : 'Unavailable',
    explanation: !liquidity.transactionVolume ? 'Launch sales data is not yet available.' : undefined,
  });

  // Construction Data
  evidenceItems.push({
    label: 'Construction Data',
    value: futureApp.completionYears ? `${futureApp.completionYears} years to completion` : '—',
    status: futureApp.completionYears ? 'Available' : 'Unavailable',
    explanation: !futureApp.completionYears ? 'Construction timeline has not been confirmed.' : undefined,
  });

  // Area Market
  evidenceItems.push({
    label: 'Area Market',
    value: commData.communityScore ? `${commData.communityScore}/100` : '—',
    status: (commData.communityScore || 0) >= 70 ? 'Strong' : (commData.communityScore || 0) >= 50 ? 'Adequate' : commData.communityScore ? 'Limited' : 'Unavailable',
    explanation: !commData.communityScore ? 'Area market data is limited for this location.' : undefined,
  });

  const statusColor: Record<string, string> = {
    'Strong': 'text-green-600',
    'Adequate': 'text-blue-600',
    'Available': 'text-blue-600',
    'Limited': 'text-amber-600',
    'Unavailable': 'text-red-500',
  };

  return (
    <div className="space-y-4">
      <div className="premium-card p-6">
        <h3 className="font-semibold text-apil-gray-900 mb-1">Evidence Used</h3>
        <p className="text-xs text-apil-gray-500 mb-4">The data behind this off-plan recommendation</p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
          {evidenceItems.map((e, i) => (
            <div key={i} className="text-center p-4 bg-apil-gray-50 rounded-xl">
              <p className="text-xs text-apil-gray-500">{e.label}</p>
              <p className="text-lg font-bold text-apil-gray-900 mt-1">{e.value}</p>
              <p className={`text-xs font-medium mt-1 ${statusColor[e.status]}`}>{e.status}</p>
              {e.explanation && (
                <p className="text-[10px] text-apil-gray-400 mt-1">{e.explanation}</p>
              )}
            </div>
          ))}
        </div>

        {/* Confidence */}
        <div className="p-4 bg-apil-blue/5 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-apil-gray-700">Recommendation Confidence</span>
            <span className={`text-sm font-bold ${confidenceColor}`}>{confidenceLevel}</span>
          </div>
          <p className="text-xs text-apil-gray-600">
            {(liquidity.transactionVolume || 0) === 0 && (devData.developerScore || 0) <= 50
              ? `Model confidence is ${confidenceLevel.toLowerCase()} (${confidenceScore}%), but evidence is limited — no launch sales data and developer score is ${devData.developerScore || '—'}/100.`
              : (liquidity.transactionVolume || 0) === 0
              ? `Model confidence is ${confidenceLevel.toLowerCase()} (${confidenceScore}%), based on developer score ${devData.developerScore || '—'}/100. No launch sales data available.`
              : confidenceScore >= 85
              ? `Very strong evidence — developer score ${devData.developerScore || '—'}/100 and ${liquidity.transactionVolume || 0} launch transactions.`
              : confidenceScore >= 70
              ? `Strong evidence — developer score ${devData.developerScore || '—'}/100 and ${liquidity.transactionVolume || 0} launch transactions.`
              : confidenceScore >= 55
              ? `Moderate evidence — developer score ${devData.developerScore || '—'}/100. Some projections are based on area trends.`
              : confidenceScore >= 40
              ? `Limited evidence — developer and market data are incomplete. Treat with caution.`
              : `Very limited evidence — developer and market data are incomplete. Treat with extra caution.`}
          </p>
        </div>

        {/* Rule flags — human readable */}
        {rulesFlags.length > 0 && (
          <div className="mt-3 pt-3 border-t border-apil-gray-200">
            <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-2">Validation Notes</p>
            <ul className="space-y-1.5">
              {rulesFlags.map((flag: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-xs text-apil-gray-600">
                  <Info className="w-3 h-3 text-amber-500 flex-shrink-0 mt-0.5" />
                  {translateRuleFlag(flag)}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Risk vs Confidence */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="premium-card p-5">
          <h3 className="font-semibold text-apil-gray-900 mb-2">Investment Risk</h3>
          <p className={`text-2xl font-bold ${riskLevel === 'Low' ? 'text-green-600' : riskLevel === 'Medium' ? 'text-amber-600' : 'text-red-500'}`}>{riskLevel}</p>
          <p className="text-xs text-apil-gray-500 mt-1">Construction, developer, and market risk</p>
        </div>
        <div className="premium-card p-5">
          <h3 className="font-semibold text-apil-gray-900 mb-2">Data Confidence</h3>
          <p className={`text-2xl font-bold ${confidenceColor}`}>{confidenceLevel}</p>
          <p className="text-xs text-apil-gray-500 mt-1">How much evidence supports this analysis</p>
        </div>
      </div>

      {/* Data Sources */}
      <div className="premium-card p-5">
        <h3 className="text-sm font-semibold text-apil-gray-900 mb-3">Data Sources</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          {devData.developerName && (
            <div className="p-3 bg-apil-gray-50 rounded-lg">
              <p className="font-semibold text-apil-gray-700 mb-1">Developer: {devData.developerName}</p>
              <p className="text-apil-gray-500">Score: {devData.developerScore || '—'}/100</p>
              <p className="text-apil-gray-500">Delay Risk: {devData.delayRisk || '—'}</p>
            </div>
          )}
          {commData.name && (
            <div className="p-3 bg-apil-gray-50 rounded-lg">
              <p className="font-semibold text-apil-gray-700 mb-1">Area: {commData.name}</p>
              <p className="text-apil-gray-500">Community Score: {commData.communityScore || '—'}/100</p>
              <p className="text-apil-gray-500">Growth: {commData.growth12m || '—'}%</p>
            </div>
          )}
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="font-semibold text-apil-gray-700 mb-1">This Project</p>
            <p className="text-apil-gray-500">Score: {scoreOrNA(property.offplanScore || property.overallScore)}/100</p>
            <p className="text-apil-gray-500">Completion: {futureApp.completionYears ? `${futureApp.completionYears} years` : '—'}</p>
          </div>
        </div>
        <p className="text-xs text-apil-gray-400 mt-3">Developer data from project filings. Area data from DLD verified transaction records. Growth projections are analytical estimates. Past performance does not predict future results.</p>
      </div>
      <CalcTracePanel trace={topRec?.calcTrace?.evidence} section="evidence" title="Evidence Quality" />
    </div>
  );
}
