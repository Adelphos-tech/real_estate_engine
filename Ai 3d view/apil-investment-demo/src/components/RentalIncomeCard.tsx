import { formatAED } from './Shared';
import type { RentalContext } from '../data/api';

const EVIDENCE_BADGE: Record<string, { label: string; color: string }> = {
  STRONGEST: { label: 'Strongest Rental Evidence', color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  STRONGER: { label: 'Strong Rental Evidence', color: 'bg-blue-100 text-blue-700 border-blue-200' },
  STRONG: { label: 'Broader Rental Evidence', color: 'bg-amber-100 text-amber-700 border-amber-200' },
  BROADER: { label: 'Broader Rental Evidence', color: 'bg-amber-100 text-amber-700 border-amber-200' },
  NONE: { label: '', color: '' },
};

const TIER_SUPPORT_TEXT: Record<string, string> = {
  R1: 'Based on recent comparable leases in the same project, same bedroom category, and similar-sized units.',
  R2: 'Based on recent comparable leases in the same project and similar-sized units.',
  R3: 'Based on recent comparable leases in the surrounding area, same bedroom category, and similar-sized units.',
  R4: 'Based on broader comparable leases in the surrounding area and similar-sized units. Individual building rents may differ.',
};

function formatAEDFull(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(n)) return 'N/A';
  return `AED ${n.toLocaleString()}`;
}

export function RentalIncomeCard({ rental }: { rental: RentalContext | null | undefined }) {
  if (!rental || rental.error) {
    return (
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-3">Rental Income</h2>
        <p className="text-sm text-apil-gray-500">Rental estimate unavailable.</p>
      </div>
    );
  }

  const status = rental.resolved_status;
  const tier = rental.selected_rental_tier;
  const badge = EVIDENCE_BADGE[rental.evidence_quality] || EVIDENCE_BADGE.NONE;
  const hasRent = rental.annual_rent_estimate_aed !== null && rental.annual_rent_estimate_aed !== undefined;
  const hasYield = rental.gross_rental_yield_pct !== null && rental.gross_rental_yield_pct !== undefined;

  // ── Offplan ──
  if (status === 'Offplan') {
    return (
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-3">Rental Income</h2>
        <div className="text-apil-gray-700">
          <p className="font-semibold text-apil-gray-800 mb-1">Gross Rental Yield — Not Evaluated</p>
          <p className="text-sm text-apil-gray-500">This property is currently off-plan, so current rental income is not evaluated.</p>
        </div>
      </div>
    );
  }

  // ── Unknown status ──
  if (status === 'Unknown') {
    return (
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-3">Rental Income</h2>
        <div className="text-apil-gray-700">
          <p className="font-semibold text-apil-gray-800 mb-1">Rental Yield Not Evaluated</p>
          <p className="text-sm text-apil-gray-500">Property status is unknown, so rental income is not evaluated.</p>
        </div>
      </div>
    );
  }

  // ── Ready with no usable rental context (NONE) ──
  if (tier === 'NONE' || !hasRent) {
    return (
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-3">Rental Income</h2>
        <div className="text-apil-gray-700">
          <p className="font-semibold text-apil-gray-800 mb-1">Rental Estimate — No Reliable Rental Estimate Available</p>
          <p className="text-sm text-apil-gray-500">APIL could not find enough comparable rental evidence for this property.</p>
        </div>
      </div>
    );
  }

  // ── Ready with rental evidence (R1/R2/R3/R4) ──
  const supportText = TIER_SUPPORT_TEXT[tier] || '';
  const rentLabel = rental.investor_label || 'Estimated Annual Rent';
  const hasRange = rental.annual_rent_p25_aed !== null && rental.annual_rent_p75_aed !== null;
  const hasYieldRange = rental.gross_yield_p25_pct !== null && rental.gross_yield_p75_pct !== null;

  return (
    <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
      <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-4">Rental Income</h2>

      {/* Evidence badge */}
      {badge.label && (
        <div className="mb-4">
          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${badge.color}`}>
            {badge.label}
          </span>
        </div>
      )}

      {/* Primary: Estimated Annual Rent */}
      <div className="mb-5">
        <p className="text-xs text-apil-gray-500 font-medium mb-1">{rentLabel}</p>
        <p className="text-2xl font-bold text-apil-blue">{formatAEDFull(rental.annual_rent_estimate_aed)} <span className="text-sm font-normal text-apil-gray-400">/ year</span></p>
        {hasRange && (
          <p className="text-sm text-apil-gray-500 mt-1">
            Estimated Rent Range: {formatAEDFull(rental.annual_rent_p25_aed)} – {formatAEDFull(rental.annual_rent_p75_aed)} / year
          </p>
        )}
      </div>

      {/* Primary: Gross Rental Yield */}
      <div className="mb-4 p-4 bg-blue-50 rounded-xl">
        <p className="text-xs text-apil-gray-500 font-medium mb-1">Gross Rental Yield</p>
        <p className="text-2xl font-bold text-apil-blue">{hasYield ? `${rental.gross_rental_yield_pct}%` : 'N/A'}</p>
        {hasYieldRange && (
          <p className="text-sm text-apil-gray-500 mt-1">
            Gross Yield Range: {rental.gross_yield_p25_pct}% – {rental.gross_yield_p75_pct}%
          </p>
        )}
      </div>

      {/* Support text */}
      {supportText && (
        <p className="text-xs text-apil-gray-500 leading-relaxed mb-3">{supportText}</p>
      )}

      {/* R4 warning */}
      {rental.warnings && tier === 'R4' && (
        <div className="mb-3 p-3 bg-amber-50 rounded-lg">
          <p className="text-xs text-amber-700 leading-relaxed">{rental.warnings}</p>
        </div>
      )}

      {/* Data-quality warning (disclosure only) */}
      {rental.data_quality_warning && (
        <div className="mb-3 p-3 bg-orange-50 border border-orange-200 rounded-lg">
          <p className="text-xs text-orange-700 leading-relaxed">
            <span className="font-semibold">Check asking price:</span> {rental.data_quality_warning}
          </p>
        </div>
      )}

      {/* Mandatory footer disclosure */}
      <div className="mt-4 pt-3 border-t border-apil-gray-100">
        <p className="text-[11px] text-apil-gray-400 leading-relaxed">
          Gross Rental Yield is estimated annual rent divided by the property's current asking price, before service charges, vacancy, management fees, maintenance, financing and other ownership costs.
        </p>
      </div>
    </div>
  );
}
