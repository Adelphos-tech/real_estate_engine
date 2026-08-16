/**
 * MarketSection — Simplified area profile.
 * Shows: Area score + top strengths + main concern.
 * Details expandable on click.
 */
import { useState } from 'react';
import { MapPin, ChevronDown, ChevronUp } from 'lucide-react';
import type { ReportContext } from '../ReportContext';
import { ScoreRing, formatAED, formatNumber } from '../../components/Shared';
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
const fmtCount = (v: any, label: string): string => {
  const n = safeVal(v);
  if (n === null || n === 0) return '—';
  return `${n} ${label}`;
};

interface MarketSectionProps {
  property: any;
  topRec: any;
  ctx: ReportContext;
  community: any;
  project?: any;
}

export function MarketSection({ property, topRec, ctx, community, project }: MarketSectionProps) {
  const [showDetails, setShowDetails] = useState(false);

  if (!community) return null;

  const areaScore = safeVal(community.investmentScore) ?? 0;
  const growth12 = safeVal(community.growth12m);
  const growth6m = safeVal(community.growth6m);
  const growth3m = safeVal(community.growth3m);
  const demandScore = safeVal(community.demandScore);
  const supplyIndex = safeVal(community.supplyIndex);
  const rentalYield = safeVal(community.rentalYield);
  const medianRent = safeVal(community.medianRent);
  const medianPriceSqft = safeVal(community.medianPriceSqft);
  const salesVolume = safeVal(community.salesVolume);
  const rentVolume = safeVal(community.rentVolume);
  const livabilityIndex = safeVal(community.livabilityIndex);

  // Determine top strengths and main concern
  const strengths: string[] = [];
  const concerns: string[] = [];

  if (demandScore != null && demandScore >= 70) strengths.push('High demand');
  if (growth12 != null && growth12 > 5) strengths.push(`Growing prices (+${growth12}%)`);
  if (rentalYield != null && rentalYield >= 6) strengths.push(`Good yields (${rentalYield}%)`);
  if (livabilityIndex != null && livabilityIndex >= 70) strengths.push('High livability');
  if (salesVolume != null && salesVolume > 500) strengths.push('Active market');

  if (supplyIndex != null && supplyIndex > 60) concerns.push('Oversupply risk');
  if (growth12 != null && growth12 < 0) concerns.push('Declining prices');
  if (rentalYield != null && rentalYield < 4) concerns.push('Low rental yields');
  if (salesVolume != null && salesVolume < 50) concerns.push('Low transaction volume');

  return (
    <div className="space-y-4">
      <div className="premium-card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <MapPin className="w-5 h-5 text-blue-600" />
            <div>
              <h3 className="font-semibold text-apil-gray-900">{community.name}</h3>
              <p className="text-xs text-apil-gray-500">
                {fmtCount(salesVolume, 'sales')} · {fmtCount(rentVolume, 'rents')} · {fmtCount(community.totalProjects, 'projects')}
              </p>
            </div>
          </div>
          <ScoreRing score={areaScore} size={64} label="Area Score" />
        </div>

        {/* Supporting metrics — always visible */}
        <div className="grid grid-cols-3 gap-2 mb-3">
          {demandScore != null && (
            <div className="p-2 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-[10px] text-apil-gray-500">Demand</p>
              <p className="text-sm font-bold text-apil-gray-900">{demandScore}<span className="text-[10px] text-apil-gray-400">/100</span></p>
            </div>
          )}
          {supplyIndex != null && (
            <div className="p-2 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-[10px] text-apil-gray-500">Supply</p>
              <p className="text-sm font-bold text-apil-gray-900">{supplyIndex}<span className="text-[10px] text-apil-gray-400">/100</span></p>
            </div>
          )}
          {rentalYield != null && (
            <div className="p-2 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-[10px] text-apil-gray-500">Avg Yield</p>
              <p className="text-sm font-bold text-apil-gray-900">{rentalYield.toFixed(1)}%</p>
            </div>
          )}
        </div>

        {/* Top strengths */}
        {strengths.length > 0 && (
          <div className="mb-3">
            <p className="text-xs font-semibold text-green-600 uppercase mb-2">Top Strengths</p>
            <div className="flex flex-wrap gap-2">
              {strengths.slice(0, 3).map((s, i) => (
                <span key={i} className="text-xs bg-green-50 text-green-700 px-3 py-1 rounded-full font-medium">{s}</span>
              ))}
            </div>
          </div>
        )}

        {/* Main concern */}
        {concerns.length > 0 && (
          <div className="mb-3">
            <p className="text-xs font-semibold text-amber-600 uppercase mb-2">Main Concern</p>
            <div className="flex flex-wrap gap-2">
              {concerns.slice(0, 2).map((c, i) => (
                <span key={i} className="text-xs bg-amber-50 text-amber-700 px-3 py-1 rounded-full font-medium">{c}</span>
              ))}
            </div>
          </div>
        )}

        {/* Expandable details */}
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="w-full flex items-center justify-between text-left mt-3 pt-3 border-t border-apil-gray-100"
        >
          <span className="text-xs font-medium text-apil-gray-500">Area Statistics</span>
          {showDetails ? <ChevronUp className="w-4 h-4 text-apil-gray-400" /> : <ChevronDown className="w-4 h-4 text-apil-gray-400" />}
        </button>
        {showDetails && (
          <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
            {medianPriceSqft != null && (
              <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
                <p className="text-xs text-apil-gray-500">Median Price/sqft</p>
                <p className="text-sm font-bold text-apil-gray-900 mt-1">AED {formatNumber(medianPriceSqft)}</p>
              </div>
            )}
            {rentalYield != null && (
              <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
                <p className="text-xs text-apil-gray-500">Avg Yield</p>
                <p className="text-sm font-bold text-apil-gray-900 mt-1">{fmtPct(rentalYield)}</p>
              </div>
            )}
            {medianRent != null && (
              <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
                <p className="text-xs text-apil-gray-500">Median Rent</p>
                <p className="text-sm font-bold text-apil-gray-900 mt-1">{fmtAEDsafe(medianRent)}/yr</p>
              </div>
            )}
            {demandScore != null && (
              <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
                <p className="text-xs text-apil-gray-500">Demand Index</p>
                <p className="text-sm font-bold text-apil-gray-900 mt-1">{demandScore}/100</p>
              </div>
            )}
            {growth3m != null && growth3m !== 0 && (
              <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
                <p className="text-xs text-apil-gray-500">Growth (3M)</p>
                <p className={`text-sm font-bold mt-1 ${growth3m > 0 ? 'text-green-600' : 'text-red-500'}`}>{fmtPct(growth3m, '+')}</p>
              </div>
            )}
            {growth6m != null && growth6m !== 0 && (
              <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
                <p className="text-xs text-apil-gray-500">Growth (6M)</p>
                <p className={`text-sm font-bold mt-1 ${growth6m > 0 ? 'text-green-600' : 'text-red-500'}`}>{fmtPct(growth6m, '+')}</p>
              </div>
            )}
            {growth12 != null && growth12 !== 0 && (
              <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
                <p className="text-xs text-apil-gray-500">Growth (12M)</p>
                <p className={`text-sm font-bold mt-1 ${growth12 > 0 ? 'text-green-600' : 'text-red-500'}`}>{fmtPct(growth12, '+')}</p>
              </div>
            )}
            {supplyIndex != null && (
              <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
                <p className="text-xs text-apil-gray-500">Supply Index</p>
                <p className="text-sm font-bold text-apil-gray-900 mt-1">{supplyIndex}/100</p>
              </div>
            )}
          </div>
        )}
      </div>
      <CalcTracePanel trace={{ ...community, area: property?.area, medianPriceSqft, supplyIndex, areaSalesCount: salesVolume, areaRentalsCount: rentVolume, growthRate: growth12, liquidityIndex: livabilityIndex }} section="market" title="Area Market Data" />
    </div>
  );
}
