/**
 * EvidenceSection — Evidence quality panel.
 * Shows: Evidence quality label + transaction counts + coverage assessment.
 * No opaque confidence percentages — transparent evidence-based assessment.
 */
import { FileText, Info, Database, Home, TrendingUp, Building2 } from 'lucide-react';
import type { ReportContext } from '../ReportContext';
import { isOffPlan, translateRuleFlag } from '../ReportContext';
import { formatNumber } from '../../components/Shared';

const safeVal = (v: any): number | null => {
  if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) return null;
  return v;
};
const fmtCount = (v: any, label: string): string => {
  const n = safeVal(v);
  if (n === null || n === 0) return '—';
  return `${n} ${label}`;
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
  const rulesFlags = topRec?.rulesFlags || [];

  const recAny = topRec as any;
  const dq = recAny?.dataQuality || {};
  const salesCount = dq.salesCount || dq.comparableCount || 0;
  const rentCount = dq.rentCount || recAny?.rentRange?.sampleSize || 0;
  const commCount = community?.salesVolume || 0;
  const compCount = dq.comparableCount || salesCount;

  // Developer history
  const devData = recAny?.developerData || {};
  const devScore = safeVal(devData?.developerScore) || 0;
  const devProjects = safeVal(devData?.totalProjects) || 0;

  // Determine evidence quality from data counts
  const totalEvidence = salesCount + rentCount;
  let evidenceQuality = '';
  let evidenceColor = '';
  let evidenceIcon = Database;
  let evidenceDesc = '';

  if (totalEvidence === 0) {
    evidenceQuality = 'Very Low';
    evidenceColor = 'text-red-500';
    evidenceDesc = 'No comparable transaction data available for this property. All estimates are indicative and should be independently verified.';
  } else if (totalEvidence <= 2) {
    evidenceQuality = 'Low';
    evidenceColor = 'text-red-500';
    evidenceDesc = `Based on ${salesCount} comparable sale${salesCount === 1 ? '' : 's'} and ${rentCount} lease transaction${rentCount === 1 ? '' : 's'}. Valuation estimates should be treated as indicative only.`;
  } else if (totalEvidence <= 10) {
    evidenceQuality = 'Moderate';
    evidenceColor = 'text-amber-600';
    evidenceDesc = `${salesCount} sales and ${rentCount} rental transactions support this assessment. Some projections may carry wider ranges.`;
  } else if (totalEvidence <= 30) {
    evidenceQuality = 'High';
    evidenceColor = 'text-blue-600';
    evidenceDesc = `${salesCount} sales and ${rentCount} rentals provide solid market evidence for this assessment.`;
  } else {
    evidenceQuality = 'Very High';
    evidenceColor = 'text-green-600';
    evidenceDesc = `${salesCount} sales and ${rentCount} rentals provide robust market evidence.`;
  }

  // Coverage assessment
  const hasSales = salesCount > 0;
  const hasRentals = rentCount > 0;
  const hasDevHistory = devProjects > 0 || devScore > 0;
  const hasCommunityData = commCount > 0;

  const coverageItems = [
    { label: 'Comparable Sales', value: salesCount > 0 ? `${salesCount}` : 'None', ok: hasSales, icon: TrendingUp },
    { label: 'Lease Transactions', value: rentCount > 0 ? `${rentCount}` : 'None', ok: hasRentals, icon: Home },
    { label: 'Developer History', value: hasDevHistory ? (devProjects > 0 ? `${devProjects} projects` : 'Available') : 'Limited', ok: hasDevHistory, icon: Building2 },
    { label: 'Area Market Data', value: commCount > 0 ? `${formatNumber(commCount)} sales` : 'Limited', ok: hasCommunityData, icon: Database },
  ];

  return (
    <div className="space-y-4">
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="w-5 h-5 text-blue-600" />
          <h3 className="font-semibold text-apil-gray-900">Evidence Quality</h3>
        </div>

        {/* Evidence quality label */}
        <div className="flex items-center justify-between mb-4 p-4 bg-apil-gray-50 rounded-lg">
          <div>
            <p className="text-xs text-apil-gray-500">Evidence Quality</p>
            <p className={`text-2xl font-bold ${evidenceColor}`}>{evidenceQuality}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-apil-gray-400">Total evidence used</p>
            <p className="text-sm font-semibold text-apil-gray-700">{salesCount + rentCount} transactions</p>
          </div>
        </div>

        {/* Evidence summary — explicit breakdown */}
        <div className="mb-4 p-3 bg-apil-gray-50 rounded-lg">
          <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-2">Evidence Summary</p>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <p className="text-xs text-apil-gray-500">Comparable Sales</p>
              <p className="text-sm font-bold text-apil-gray-900">{salesCount}</p>
            </div>
            <div>
              <p className="text-xs text-apil-gray-500">Comparable Rentals</p>
              <p className="text-sm font-bold text-apil-gray-900">{rentCount}</p>
            </div>
            <div>
              <p className="text-xs text-apil-gray-500">Total Transactions</p>
              <p className="text-sm font-bold text-apil-gray-900">{salesCount + rentCount}</p>
            </div>
          </div>
        </div>

        {/* Evidence description */}
        <p className="text-sm text-apil-gray-600 mb-4">{evidenceDesc}</p>

        {/* Coverage grid */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          {coverageItems.map((item, i) => {
            const Icon = item.icon;
            return (
              <div key={i} className="flex items-center gap-3 p-3 bg-apil-gray-50 rounded-lg">
                <Icon className={`w-4 h-4 flex-shrink-0 ${item.ok ? 'text-green-500' : 'text-amber-400'}`} />
                <div>
                  <p className="text-xs text-apil-gray-500">{item.label}</p>
                  <p className="text-sm font-semibold text-apil-gray-900">{item.value}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Low evidence warning */}
        {(evidenceQuality === 'Low' || evidenceQuality === 'Very Low') && (
          <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-xs text-amber-700">
              <strong>Note:</strong> Due to {evidenceQuality.toLowerCase()} evidence quality, future value and return estimates cannot be reliably calculated from available transaction data. All estimates should be independently verified.
            </p>
          </div>
        )}

        {/* Validation notes — plain language, no rule codes */}
        {rulesFlags.length > 0 && (
          <div className="pt-3 border-t border-apil-gray-200">
            <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-2">Notes</p>
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

        <p className="text-xs text-apil-gray-400 mt-4">
          Data sourced from Dubai Land Department (DLD) verified transaction records. Scores are analytical estimates based on historical data.
        </p>
      </div>
    </div>
  );
}
