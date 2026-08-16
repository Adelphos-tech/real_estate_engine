/**
 * RentalSection — Ready property with rental evidence only.
 * Shows rental breakdown, comparable rentals, rental confidence.
 * Never shown for off-plan properties (no rental income during construction).
 */
import { Home, Info, AlertTriangle } from 'lucide-react';
import type { ReportContext } from '../ReportContext';
import { getConfidenceLabel, getConfidenceColor } from '../ReportContext';
import { ROIBreakdownCard } from '../../components/ROIBreakdownCard';
import { formatAED } from '../../components/Shared';
import { CalcTracePanel } from './CalcTracePanel';

const safeVal = (v: any): number | null => {
  if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) return null;
  return v;
};
const fmtPct = (v: any): string => {
  const n = safeVal(v);
  if (n === null) return '—';
  return `${n}%`;
};
const fmtAEDsafe = (v: any): string => {
  const n = safeVal(v);
  if (n === null) return '—';
  return formatAED(n);
};

interface RentalSectionProps {
  property: any;
  topRec: any;
  ctx: ReportContext;
  community: any;
}

export function RentalSection({ property, topRec, ctx, community }: RentalSectionProps) {
  const rentRange = topRec?.rentRange;
  const estRent = safeVal(property.estimatedRent);
  const netROI = safeVal(property.netROI);
  const grossROI = safeVal(property.grossROI);
  const rentCount = topRec?.dataQuality?.rentCount || 0;
  const vacancy = safeVal(property.vacancyRate) || 0;
  const rentConfidenceScore = topRec?.confidenceScore || 0;
  const rentConfidenceLabel = getConfidenceLabel(rentConfidenceScore);
  const rentConfidenceColor = getConfidenceColor(rentConfidenceScore);
  const areaAvgRent = community?.medianRent || 0;
  const rentVsArea = areaAvgRent > 0 && estRent != null && estRent > 0 ? Math.round(((estRent - areaAvgRent) / areaAvgRent) * 1000) / 10 : null;
  const isLowEvidence = rentCount <= 3;

  return (
    <div className="space-y-4">
      {/* Rental Breakdown */}
      <ROIBreakdownCard property={property} />

      {/* Rental Range & Confidence */}
      {rentRange && (rentRange.low || rentRange.high) && (
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <Home className="w-5 h-5 text-green-600" />
            <h3 className="font-semibold text-apil-gray-900">Rental Range & Confidence</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="text-center p-4 bg-green-50 rounded-xl">
              <p className="text-xs text-apil-gray-500">Low Estimate</p>
              <p className="text-xl font-bold text-green-600 mt-1">{fmtAEDsafe(rentRange.low)}/yr</p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-xl">
              <p className="text-xs text-apil-gray-500">Most Likely</p>
              <p className="text-xl font-bold text-green-600 mt-1">{fmtAEDsafe(estRent)}/yr</p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-xl">
              <p className="text-xs text-apil-gray-500">High Estimate</p>
              <p className="text-xl font-bold text-green-600 mt-1">{fmtAEDsafe(rentRange.high)}/yr</p>
            </div>
          </div>
          <div className={`p-3 rounded-lg text-xs ${isLowEvidence ? 'bg-amber-50 text-amber-700' : 'bg-apil-gray-50 text-apil-gray-600'}`}>
            <div className="flex items-center justify-between mb-1">
              <strong>Rental confidence:</strong>
              <span className={`font-semibold ${rentConfidenceColor}`}>{rentConfidenceLabel} ({rentConfidenceScore}%)</span>
            </div>
            <p>
              Based on {rentCount} comparable lease transaction{rentCount !== 1 ? 's' : ''} in this area.
              {isLowEvidence && ' This is limited evidence — treat rent estimates as indicative, not precise.'}
            </p>
            {rentVsArea !== null && (
              <p className="mt-1">
                This property's projected rent is {rentVsArea > 0 ? `${rentVsArea}% above` : `${Math.abs(rentVsArea)}% below`} the area median of {fmtAEDsafe(areaAvgRent)}/yr.
              </p>
            )}
            {vacancy > 0 && ` Vacancy allowance: ${(vacancy * 100).toFixed(0)}%.`}
            {rentRange.source && ` Source: ${rentRange.source}.`}
          </div>
        </div>
      )}

      {/* Area Rental Comparison */}
      {community?.rentalYield && (
        <div className="premium-card p-6">
          <h3 className="font-semibold text-apil-gray-900 mb-4">How Does This Compare to the Area?</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-xs text-apil-gray-500">This Property Net Yield</p>
              <p className="text-lg font-bold text-green-600">{fmtPct(netROI)}</p>
            </div>
            <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-xs text-apil-gray-500">Area Average Yield</p>
              <p className="text-lg font-bold text-apil-gray-900">{fmtPct(community.rentalYield)}</p>
            </div>
            <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-xs text-apil-gray-500">Area Median Rent</p>
              <p className="text-lg font-bold text-apil-gray-900">{fmtAEDsafe(community.medianRent)}/yr</p>
            </div>
            <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-xs text-apil-gray-500">Lease Transactions</p>
              <p className="text-lg font-bold text-apil-gray-900">{rentCount || '—'}</p>
            </div>
          </div>
          {netROI != null && community.rentalYield != null && (
            <div className="mt-4 p-3 bg-apil-blue/5 rounded-lg text-xs text-apil-gray-600">
              {netROI > community.rentalYield
                ? `This property's net yield of ${netROI}% is above the area average of ${community.rentalYield}% — a good sign for rental income.`
                : netROI < community.rentalYield
                ? `This property's net yield of ${netROI}% is below the area average of ${community.rentalYield}%. The price may be high relative to rental potential.`
                : `This property's yield is in line with the area average.`}
            </div>
          )}
        </div>
      )}
      <CalcTracePanel trace={topRec?.calcTrace?.rental || topRec?.returns?.rental} section="rental" title="Rental Yield Calculation" />
    </div>
  );
}
