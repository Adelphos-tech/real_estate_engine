import { useState } from 'react';
import { Link } from 'react-router-dom';
import type {
  RentalContext,
  ServiceChargeContext,
  ServiceChargeTransparency,
  RentalOperatingCostContext,
  HorizonContext,
  QuestionnaireAnswers,
} from '../data/api';

// ── Helpers ──
function formatAEDFull(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(n)) return 'N/A';
  return `AED ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPct(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(n)) return 'N/A';
  return `${n}%`;
}

// ── Evidence badges ──
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

// ── Coverage badge text per level (customer-friendly, no raw enums) ──
const COVERAGE_BADGE: Record<number, { label: string; color: string }> = {
  1: { label: 'Rent Only', color: 'bg-blue-100 text-blue-700 border-blue-200' },
  2: { label: 'Rent + Official Service Charges', color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
  3: { label: 'Rent + Service Charges + Vacancy', color: 'bg-amber-100 text-amber-700 border-amber-200' },
  4: { label: 'All Operating Costs Included', color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
};

// ── Plain-language explanations per level ──
const LEVEL_EXPLANATION: Record<number, string> = {
  1: 'This return uses estimated annual rent only.',
  2: 'This return deducts verified official service charges from estimated annual rent.',
  3: 'This return deducts official service charges and your vacancy allowance.',
  4: 'This return deducts service charges, vacancy, property management, and unit maintenance.',
};

// ── Not Included lists (simplified, customer-friendly) ──
const NOT_INCLUDED_OPERATING: string[] = [
  'Vacancy',
  'Property Management',
  'Unit Maintenance',
];

const NOT_INCLUDED_INVESTMENT: string[] = [
  'Acquisition Costs',
  'Financing / Mortgage Costs',
  'Capital Appreciation',
  'Selling Costs',
  'Future Sale Price',
];

// ── Disclosures per level ──
const DISCLOSURE_LEVEL_1 = 'This is a Gross Rental Yield calculation based on estimated annual rent and the property\'s current price. It is not Full Property ROI.';
const DISCLOSURE_LEVEL_2 = 'This return deducts verified official service charges from estimated annual rent. It does not yet include all operating costs and is not Net Rental Income or Full Property ROI.';
const DISCLOSURE_LEVEL_3 = 'Adjusted Rental Income includes the operating costs currently available to APIL. It is not Net Rental Income while required operating costs remain missing, and it is not Full Property ROI.';
const DISCLOSURE_LEVEL_4 = 'This is Net Rental Yield based on the operating-income data shown above. It is not Full Property ROI because acquisition costs, financing, holding period, future sale value and selling costs are not included.';

// ── Collapsible Section wrapper ──
function CollapsibleSection({ title, children, defaultOpen = false }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-apil-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-semibold text-apil-gray-700 hover:bg-apil-gray-50"
      >
        <span>{title}</span>
        <span className="text-apil-gray-400">{open ? '▲' : '▼'}</span>
      </button>
      {open && <div className="px-3 py-3 space-y-2">{children}</div>}
    </div>
  );
}

// ── Included item component ──
function IncludedItem({ label, value, source, note }: { label: string; value: string; source?: string; note?: string }) {
  return (
    <li className="text-sm text-apil-gray-600 flex items-start">
      <span className="text-emerald-600 mr-2">✓</span>
      <span>
        <span className="font-medium">{label}</span> — {value}
        {source && <span className="text-apil-gray-400 text-xs"> · Source: {source}</span>}
        {note && <span className="text-apil-gray-400 text-xs block ml-4">{note}</span>}
      </span>
    </li>
  );
}

// ── Not Included item ──
function NotIncludedItem({ label }: { label: string }) {
  return (
    <li className="text-sm text-apil-gray-500 flex items-start">
      <span className="text-apil-gray-300 mr-2">—</span> {label}
    </li>
  );
}

// ── Service Charge Transparency Block (inside Sources & Calculation Details) ──
function ServiceChargeTransparencyBlock({ transparency }: { transparency: ServiceChargeTransparency | null }) {
  if (!transparency) return null;

  const rate = transparency.rate_aed_per_sqft;
  const area = transparency.area_sqft_used;
  const annual = transparency.annual_service_charge_aed;
  const method = transparency.calculation_method;
  const pctRent = transparency.pct_of_estimated_rent;
  const pctPrice = transparency.pct_of_purchase_price;
  const source = transparency.source;
  const year = transparency.budget_year;
  const areaSource = transparency.area_source;

  return (
    <div className="ml-2 border-l-2 border-apil-gray-200 pl-3 space-y-1.5 text-xs text-apil-gray-600 leading-relaxed">
      {rate != null && (
        <div><span className="font-semibold text-apil-gray-700">Rate:</span> AED {rate.toFixed(2)} / sqft / year</div>
      )}
      {area != null && (
        <div><span className="font-semibold text-apil-gray-700">Area Used:</span> {area.toLocaleString()} sqft</div>
      )}
      {method === 'RATE_X_AREA' && rate != null && area != null && annual != null && (
        <div className="bg-apil-gray-50 rounded px-2 py-1.5">
          {rate.toFixed(2)} × {area.toLocaleString()} = {formatAEDFull(annual)} / year
        </div>
      )}
      {year && (
        <div><span className="font-semibold text-apil-gray-700">Budget Year:</span> {year}</div>
      )}
      {source && (
        <div><span className="font-semibold text-apil-gray-700">Source:</span> {source}</div>
      )}
      {areaSource && (
        <div><span className="font-semibold text-apil-gray-700">Area Source:</span> {areaSource === 'MASTER_UNIT_SIZE' ? 'MASTER verified property size' : areaSource}</div>
      )}
      {pctRent != null && (
        <div><span className="font-semibold text-apil-gray-700">Service Charge as % of Annual Rent:</span> {pctRent}%</div>
      )}
      {pctPrice != null && (
        <div><span className="font-semibold text-apil-gray-700">Service Charge as % of Purchase Price:</span> {pctPrice}%</div>
      )}
      <p className="text-[10px] text-apil-gray-400 italic mt-1">
        Percentages are transparency metrics only, not the service charge rate.
      </p>
    </div>
  );
}

// ── Props ──
interface RentalReturnCardProps {
  purchasePrice: number | null;
  rental: RentalContext | null | undefined;
  serviceCharge: ServiceChargeContext | null | undefined;
  operatingCost: RentalOperatingCostContext | null | undefined;
  investorProfile?: QuestionnaireAnswers | null;
  horizonContext?: HorizonContext | null;
}

export function RentalReturnCard({
  purchasePrice,
  rental,
  serviceCharge,
  operatingCost,
  investorProfile,
  horizonContext,
}: RentalReturnCardProps) {
  // ── Holding period from investor profile (read-only) ──
  const horizonYears = horizonContext?.investment_horizon_years ?? investorProfile?.investment_horizon_years ?? null;
  const cumulativeIncome = horizonContext?.cumulative_supported_rental_income_aed ?? null;
  const annualIncomeLabel = horizonContext?.annual_income_label ?? null;
  const annualSupportedIncome = horizonContext?.annual_supported_income_aed ?? null;

  // ══════════════════════════════════════════════════════════════
  // EARLY RETURNS: Offplan, Unknown, No rent
  // ══════════════════════════════════════════════════════════════
  if (!rental || rental.error) {
    return (
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <h2 className="text-base font-bold text-apil-gray-800 mb-2">Rental Return</h2>
        <p className="text-sm text-apil-gray-500">Rental estimate unavailable.</p>
      </div>
    );
  }

  const status = rental.resolved_status;
  const tier = rental.selected_rental_tier;
  const badge = EVIDENCE_BADGE[rental.evidence_quality] || EVIDENCE_BADGE.NONE;
  const hasRent = rental.annual_rent_estimate_aed !== null && rental.annual_rent_estimate_aed !== undefined;
  const hasYield = rental.gross_rental_yield_pct !== null && rental.gross_rental_yield_pct !== undefined;

  // Offplan — no fabricated return
  if (status === 'Offplan') {
    return (
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <h2 className="text-base font-bold text-apil-gray-800 mb-2">Rental Return</h2>
        <p className="font-semibold text-apil-gray-800 mb-1">Rental Return — Not Evaluated</p>
        <p className="text-sm text-apil-gray-500">This property is currently off-plan, so current rental income is not evaluated. No rental return percentage is shown.</p>
      </div>
    );
  }

  // Unknown status
  if (status === 'Unknown') {
    return (
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <h2 className="text-base font-bold text-apil-gray-800 mb-2">Rental Return</h2>
        <p className="font-semibold text-apil-gray-800 mb-1">Rental Return — Not Evaluated</p>
        <p className="text-sm text-apil-gray-500">Property status is unknown, so rental income is not evaluated.</p>
      </div>
    );
  }

  // Ready but no usable rental
  if (tier === 'NONE' || !hasRent) {
    return (
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <h2 className="text-base font-bold text-apil-gray-800 mb-2">Rental Return</h2>
        <p className="font-semibold text-apil-gray-800 mb-1">No Reliable Rental Estimate Available</p>
        <p className="text-sm text-apil-gray-500">APIL could not find enough comparable rental evidence for this property. No rental return percentage is shown.</p>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════════════
  // DETERMINE LEVEL
  // ══════════════════════════════════════════════════════════════
  const scEligible = serviceCharge?.production_eligible === true;
  const scAmount = serviceCharge?.annual_service_charge_aed ?? null;
  const scTransparency = serviceCharge?.transparency ?? null;
  const hasSC = scEligible && scAmount !== null;

  const hasVacancy = operatingCost?.vacancy?.status === 'AVAILABLE';
  const hasManagement = operatingCost?.management?.status === 'AVAILABLE';
  const hasMaintenance = operatingCost?.maintenance?.status === 'AVAILABLE';

  const isLevel4 = hasSC && hasVacancy && hasManagement && hasMaintenance;
  const isLevel3 = hasSC && hasVacancy && !isLevel4;
  const isLevel2 = hasSC && !hasVacancy;
  const isLevel1 = !hasSC;
  const level = isLevel4 ? 4 : isLevel3 ? 3 : isLevel2 ? 2 : 1;

  // ── Values from backend (NO frontend math) ──
  const annualRent = rental.annual_rent_estimate_aed;
  const grossYield = rental.gross_rental_yield_pct;
  const incomeAfterSC = serviceCharge?.income_after_service_charges_aed ?? null;
  const yieldAfterSC = serviceCharge?.yield_after_service_charges_pct ?? null;
  const adjustedRentalIncome = operatingCost?.adjusted_rental_income_aed ?? null;
  const netRentalIncome = operatingCost?.net_rental_income_aed ?? null;
  const netRentalYield = operatingCost?.net_rental_yield_pct ?? null;

  // Vacancy details
  const vacancyPercentVal = operatingCost?.vacancy?.percent ?? null;
  const vacancyLossVal = operatingCost?.vacancy?.loss_aed ?? null;
  const vacancyModeVal = operatingCost?.vacancy?.input_mode ?? null;

  // Management details
  const mgmtPercentVal = operatingCost?.management?.percent ?? null;
  const mgmtAedVal = operatingCost?.management?.annual_cost_aed ?? null;
  const mgmtModeVal = operatingCost?.management?.input_mode ?? null;
  const isSelfManaged = mgmtModeVal === 'SELF_MANAGED';

  // Maintenance details
  const maintenanceVal = operatingCost?.maintenance?.annual_cost_aed ?? null;

  const supportText = TIER_SUPPORT_TEXT[tier] || '';
  const rentLabel = rental.investor_label || 'Estimated Annual Rent';
  const hasRange = rental.annual_rent_p25_aed !== null && rental.annual_rent_p25_aed !== undefined
    && rental.annual_rent_p75_aed !== null && rental.annual_rent_p75_aed !== undefined;
  const hasYieldRange = rental.gross_yield_p25_pct !== null && rental.gross_yield_p25_pct !== undefined
    && rental.gross_yield_p75_pct !== null && rental.gross_yield_p75_pct !== undefined;

  // ── Level-specific primary/secondary results ──
  let primaryValue = '';
  let primaryLabel = '';
  let primarySuffix = '';
  let secondaryValue: string | null = null;
  let secondaryLabel = '';
  let disclosure = '';

  if (isLevel4) {
    primaryValue = formatAEDFull(netRentalIncome);
    primaryLabel = 'Net Rental Income';
    primarySuffix = '/ year';
    secondaryValue = formatPct(netRentalYield);
    secondaryLabel = 'Net Rental Yield';
    disclosure = DISCLOSURE_LEVEL_4;
  } else if (isLevel3) {
    primaryValue = formatAEDFull(adjustedRentalIncome);
    primaryLabel = 'Adjusted Rental Income';
    primarySuffix = '/ year';
    secondaryValue = null;
    disclosure = DISCLOSURE_LEVEL_3;
  } else if (isLevel2) {
    primaryValue = formatAEDFull(incomeAfterSC);
    primaryLabel = 'Income After Service Charges';
    primarySuffix = '/ year';
    secondaryValue = formatPct(yieldAfterSC);
    secondaryLabel = 'Yield After Service Charges';
    disclosure = DISCLOSURE_LEVEL_2;
  } else {
    primaryValue = hasYield ? formatPct(grossYield) : 'N/A';
    primaryLabel = 'Gross Rental Yield';
    primarySuffix = '';
    secondaryValue = formatAEDFull(annualRent);
    secondaryLabel = 'Estimated Annual Rent';
    disclosure = DISCLOSURE_LEVEL_1;
  }

  const covBadge = COVERAGE_BADGE[level];
  const headlineColor = isLevel4 ? 'text-emerald-700' : isLevel3 ? 'text-amber-700' : isLevel2 ? 'text-emerald-700' : 'text-apil-blue';
  const headlineBg = isLevel4 ? 'bg-emerald-50' : isLevel3 ? 'bg-amber-50' : isLevel2 ? 'bg-emerald-50' : 'bg-blue-50';

  // ── Vacancy display string ──
  const vacancyDisplay = vacancyModeVal === 'VACANCY_PERCENT' && vacancyPercentVal != null
    ? `${vacancyPercentVal}% · ${formatAEDFull(vacancyLossVal)}`
    : formatAEDFull(vacancyLossVal);

  // ── Management display string ──
  const mgmtDisplay = isSelfManaged
    ? 'Self-managed (AED 0)'
    : mgmtModeVal === 'USER_INPUT_PERCENT' && mgmtPercentVal != null
      ? `${mgmtPercentVal}% · ${formatAEDFull(mgmtAedVal)}`
      : formatAEDFull(mgmtAedVal);

  return (
    <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">

      {/* ══════════════════════════════════════════════════════════════
          CARD TITLE + COVERAGE BADGE
          ══════════════════════════════════════════════════════════════ */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-bold text-apil-gray-800">Rental Return</h2>
        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${covBadge.color}`}>
          {covBadge.label}
        </span>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          HEADLINE — Primary + Secondary result
          ══════════════════════════════════════════════════════════════ */}
      <div className={`mb-4 p-4 ${headlineBg} rounded-xl`}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Primary result */}
          <div>
            <p className="text-xs text-apil-gray-500 font-medium mb-1">{primaryLabel}</p>
            <p className={`text-2xl md:text-3xl font-bold ${headlineColor}`}>
              {primaryValue}
              {primarySuffix && <span className="text-sm font-normal text-apil-gray-400 ml-1">{primarySuffix}</span>}
            </p>
          </div>
          {/* Secondary result */}
          {secondaryValue && (
            <div>
              <p className="text-xs text-apil-gray-500 font-medium mb-1">{secondaryLabel}</p>
              <p className={`text-2xl md:text-3xl font-bold ${headlineColor}`}>{secondaryValue}</p>
            </div>
          )}
        </div>
        {/* One-line explanation */}
        <p className="text-sm text-apil-gray-500 mt-3">{LEVEL_EXPLANATION[level]}</p>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          COMPACT "BASED ON" LINE — shows input relationship without
          duplicating headline values in a separate table.
          Level 3 excludes Purchase Price (not used in Adjusted Rental Income).
          Detailed input breakdown remains in Sources & Calculation Details.
          ══════════════════════════════════════════════════════════════ */}
      <div className="mb-4">
        <p className="text-sm text-apil-gray-500 leading-relaxed">
          {isLevel1 && (
            <>Based on {formatAEDFull(annualRent)} annual rent ÷ {formatAEDFull(purchasePrice)} property price.</>
          )}
          {isLevel2 && (
            <>Based on {formatAEDFull(annualRent)} estimated rent less {formatAEDFull(scAmount)} official service charges.</>
          )}
          {isLevel3 && (
            <>Based on {formatAEDFull(annualRent)} estimated rent − {formatAEDFull(scAmount)} service charges − {formatAEDFull(vacancyLossVal)} vacancy.</>
          )}
          {isLevel4 && (
            <>Includes service charges, vacancy, property management and maintenance.</>
          )}
        </p>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          AVAILABLE INPUTS NOT YET INCLUDED (Level 3 only)
          ══════════════════════════════════════════════════════════════ */}
      {isLevel3 && (hasManagement || hasMaintenance) && (
        <div className="mb-4 p-3 bg-blue-50/50 rounded-lg">
          <p className="text-xs font-semibold text-blue-600 mb-1">Available input — not yet included in the displayed return:</p>
          <ul className="space-y-0.5">
            {hasManagement && (
              <li className="text-xs text-apil-gray-600 flex items-start">
                <span className="text-blue-500 mr-1.5">ℹ</span> Property Management — {mgmtDisplay} — Your Input
              </li>
            )}
            {hasMaintenance && (
              <li className="text-xs text-apil-gray-600 flex items-start">
                <span className="text-blue-500 mr-1.5">ℹ</span> Unit Maintenance — {formatAEDFull(maintenanceVal)} — Your Input
              </li>
            )}
          </ul>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════
          THREE COLLAPSIBLE SECTIONS (collapsed by default)
          ══════════════════════════════════════════════════════════════ */}
      <div className="space-y-2 mb-4">
        {/* ── 1. What's Included ── */}
        <CollapsibleSection title="What's Included">
          <ul className="space-y-1.5">
            <IncludedItem label="Estimated Annual Rent" value={`${formatAEDFull(annualRent)} / year`} source="APIL Rental Evidence" />
            {level >= 2 && hasSC && (
              <IncludedItem label="Official Service Charges" value={`${formatAEDFull(scAmount)} / year`} source="DLD/RERA Mollak" />
            )}
            {level >= 3 && hasVacancy && (
              <IncludedItem
                label="Vacancy"
                value={vacancyDisplay}
                source="Your Input"
              />
            )}
            {level === 4 && hasManagement && (
              <IncludedItem
                label="Property Management"
                value={mgmtDisplay}
                source="Your Input"
              />
            )}
            {level === 4 && hasMaintenance && (
              <IncludedItem label="Unit Maintenance" value={`${formatAEDFull(maintenanceVal)} / year`} source="Your Input" />
            )}
            {/* Purchase Price — only for levels that use it as yield denominator (not Level 3) */}
            {level !== 3 && (
              <IncludedItem label="Purchase Price" value={formatAEDFull(purchasePrice)} source="MASTER dataset" note="Used as yield denominator" />
            )}
          </ul>
        </CollapsibleSection>

        {/* ── 2. What's Not Included ── */}
        <CollapsibleSection title="What's Not Included">
          {/* Operating costs not yet included */}
          {level < 4 && (
            <div className="mb-3">
              <p className="text-xs font-semibold text-apil-gray-500 mb-1">Operating costs not yet included:</p>
              <ul className="space-y-0.5">
                {level < 3 && <NotIncludedItem label="Vacancy" />}
                {level < 4 && <NotIncludedItem label="Property Management" />}
                {level < 4 && <NotIncludedItem label="Unit Maintenance" />}
              </ul>
            </div>
          )}
          {/* Other investment costs not part of this rental return */}
          <div>
            <p className="text-xs font-semibold text-apil-gray-500 mb-1">Other investment costs not part of this rental return:</p>
            <ul className="space-y-0.5">
              {NOT_INCLUDED_INVESTMENT.map((item) => (
                <NotIncludedItem key={item} label={item} />
              ))}
            </ul>
          </div>
          {/* Disclosure */}
          <div className="mt-3 p-2.5 bg-orange-50 border border-orange-200 rounded-lg">
            <p className="text-xs text-orange-700 leading-relaxed">{disclosure}</p>
          </div>
        </CollapsibleSection>

        {/* ── 3. Sources & Calculation Details ── */}
        <CollapsibleSection title="Sources & Calculation Details">
          {/* Sources */}
          <div className="space-y-1.5 mb-3">
            <div className="text-xs text-apil-gray-600"><span className="font-semibold">Estimated Annual Rent</span> — Source: APIL Rental Evidence</div>
            {level >= 2 && hasSC && (
              <div className="text-xs text-apil-gray-600"><span className="font-semibold">Official Service Charges</span> — Source: DLD/RERA Mollak</div>
            )}
            {level !== 3 && (
              <div className="text-xs text-apil-gray-600"><span className="font-semibold">Purchase Price</span> — Source: MASTER dataset</div>
            )}
            {level >= 3 && hasVacancy && (
              <div className="text-xs text-apil-gray-600"><span className="font-semibold">Vacancy</span> — Source: Your Input</div>
            )}
            {level === 4 && hasManagement && (
              <div className="text-xs text-apil-gray-600"><span className="font-semibold">Property Management</span> — Source: Your Input</div>
            )}
            {level === 4 && hasMaintenance && (
              <div className="text-xs text-apil-gray-600"><span className="font-semibold">Unit Maintenance</span> — Source: Your Input</div>
            )}
            <div className="text-xs text-apil-gray-600"><span className="font-semibold">Derived result</span> — Source: Derived by APIL</div>
          </div>

          {/* Input values breakdown (detailed, for auditability) */}
          <div className="mb-3">
            <p className="text-xs font-semibold text-apil-gray-700 mb-1.5">Input Values:</p>
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-apil-gray-600">
                <span>Estimated Annual Rent</span>
                <span className="font-medium text-apil-gray-800">{formatAEDFull(annualRent)}</span>
              </div>
              {level >= 2 && hasSC && (
                <div className="flex justify-between text-xs text-apil-gray-600">
                  <span>Official Service Charges</span>
                  <span className="font-medium text-apil-gray-800">{formatAEDFull(scAmount)}</span>
                </div>
              )}
              {level >= 3 && hasVacancy && (
                <div className="flex justify-between text-xs text-apil-gray-600">
                  <span>Vacancy {vacancyModeVal === 'VACANCY_PERCENT' && vacancyPercentVal != null ? `(${vacancyPercentVal}%)` : ''}</span>
                  <span className="font-medium text-apil-gray-800">{formatAEDFull(vacancyLossVal)}</span>
                </div>
              )}
              {level === 4 && hasManagement && (
                <div className="flex justify-between text-xs text-apil-gray-600">
                  <span>Property Management {mgmtModeVal === 'USER_INPUT_PERCENT' && mgmtPercentVal != null ? `(${mgmtPercentVal}%)` : ''}</span>
                  <span className="font-medium text-apil-gray-800">{formatAEDFull(mgmtAedVal)}</span>
                </div>
              )}
              {level === 4 && hasMaintenance && (
                <div className="flex justify-between text-xs text-apil-gray-600">
                  <span>Unit Maintenance</span>
                  <span className="font-medium text-apil-gray-800">{formatAEDFull(maintenanceVal)}</span>
                </div>
              )}
              {/* Purchase Price — shown for levels that use it as yield denominator */}
              {(level === 1 || level === 2 || level === 4) && (
                <div className="flex justify-between text-xs text-apil-gray-600">
                  <span>Purchase Price <span className="text-apil-gray-400">(yield denominator)</span></span>
                  <span className="font-medium text-apil-gray-800">{formatAEDFull(purchasePrice)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Exact formula per level */}
          <div className="p-3 bg-apil-gray-50 rounded-lg space-y-1 mb-3">
            <p className="text-xs font-semibold text-apil-gray-700 mb-1">Calculation:</p>
            <div className="text-xs text-apil-gray-700 space-y-1 ml-2">
              {isLevel1 && (
                <>
                  <div>{formatAEDFull(annualRent)} ÷ {formatAEDFull(purchasePrice)} × 100</div>
                  <div className="font-semibold text-apil-blue">= {hasYield ? `${grossYield}%` : 'N/A'} Gross Rental Yield</div>
                </>
              )}
              {isLevel2 && (
                <>
                  <div>{formatAEDFull(annualRent)} − {formatAEDFull(scAmount)}</div>
                  <div className="font-semibold">= {formatAEDFull(incomeAfterSC)} Income After Service Charges</div>
                  <div className="text-apil-gray-400 mt-1.5">{formatAEDFull(incomeAfterSC)} ÷ {formatAEDFull(purchasePrice)} × 100</div>
                  <div className="font-semibold text-emerald-700">= {formatPct(yieldAfterSC)} Yield After Service Charges</div>
                </>
              )}
              {isLevel3 && (
                <>
                  <div>{formatAEDFull(annualRent)} − {formatAEDFull(scAmount)} − {formatAEDFull(vacancyLossVal)}</div>
                  <div className="font-semibold text-amber-700">= {formatAEDFull(adjustedRentalIncome)} Adjusted Rental Income</div>
                </>
              )}
              {isLevel4 && (
                <>
                  <div>{formatAEDFull(annualRent)} − {formatAEDFull(vacancyLossVal)} − {formatAEDFull(scAmount)} − {formatAEDFull(mgmtAedVal)} − {formatAEDFull(maintenanceVal)}</div>
                  <div className="font-semibold text-emerald-700">= {formatAEDFull(netRentalIncome)} Net Rental Income</div>
                  <div className="text-apil-gray-400 mt-1.5">{formatAEDFull(netRentalIncome)} ÷ {formatAEDFull(purchasePrice)} × 100</div>
                  <div className="font-semibold text-emerald-700">= {formatPct(netRentalYield)} Net Rental Yield</div>
                </>
              )}
            </div>
          </div>

          {/* Service Charge Transparency (Level 2+) */}
          {level >= 2 && hasSC && (
            <div className="mb-3">
              <p className="text-xs font-semibold text-apil-gray-700 mb-1.5">Official Service Charge Calculation</p>
              <ServiceChargeTransparencyBlock transparency={scTransparency} />
            </div>
          )}

          {/* Rental Evidence */}
          <div className="mb-3">
            <p className="text-xs font-semibold text-apil-gray-700 mb-1">Rental Evidence</p>
            {badge.label && (
              <div className="mb-2">
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${badge.color}`}>
                  {badge.label}
                </span>
              </div>
            )}
            {hasRange && (
              <p className="text-xs text-apil-gray-500">
                Estimated range: {formatAEDFull(rental.annual_rent_p25_aed)} – {formatAEDFull(rental.annual_rent_p75_aed)} / year
              </p>
            )}
            {hasYieldRange && (
              <p className="text-xs text-apil-gray-500">
                Gross Yield Range: {rental.gross_yield_p25_pct}% – {rental.gross_yield_p75_pct}%
              </p>
            )}
            {supportText && (
              <p className="text-xs text-apil-gray-500 mt-1">{supportText}</p>
            )}
          </div>

          {/* R4 warning */}
          {rental.warnings && tier === 'R4' && (
            <div className="mb-3 p-2.5 bg-amber-50 rounded-lg">
              <p className="text-xs text-amber-700 leading-relaxed">{rental.warnings}</p>
            </div>
          )}

          {/* Data-quality warning */}
          {rental.data_quality_warning && (
            <div className="p-2.5 bg-orange-50 border border-orange-200 rounded-lg">
              <p className="text-xs text-orange-700 leading-relaxed">
                <span className="font-semibold">Check asking price:</span> {rental.data_quality_warning}
              </p>
            </div>
          )}
        </CollapsibleSection>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          HOLDING PERIOD (compact, read-only from investor profile)
          ══════════════════════════════════════════════════════════════ */}
      <div className="mt-4 pt-4 border-t border-apil-gray-100">
        <p className="text-xs font-bold text-apil-gray-700 mb-2">Your Holding Period</p>
        {horizonYears != null ? (
          <>
            <div className="flex items-center justify-between mb-2">
              <div>
                <span className="text-base font-bold text-apil-gray-800">
                  {horizonYears} year{horizonYears !== 1 ? 's' : ''}
                </span>
                <span className="text-xs text-apil-gray-400 ml-2">Source: Your Investment Profile</span>
              </div>
              <Link to="/questionnaire" className="text-xs text-apil-blue hover:underline">
                Edit Investment Profile
              </Link>
            </div>
            {cumulativeIncome != null && annualSupportedIncome != null && (
              <div className="p-2.5 bg-apil-blue/5 border border-apil-blue/20 rounded-lg">
                <div className="text-xs text-apil-gray-500 mb-0.5">
                  Estimated Income Over Your {horizonYears}-Year Holding Period
                </div>
                <div className="text-base font-bold text-apil-gray-800">
                  {formatAEDFull(cumulativeIncome)}
                </div>
                <div className="text-[11px] text-apil-gray-400 mt-0.5">
                  Based on {annualIncomeLabel || 'annual income'} of {formatAEDFull(annualSupportedIncome)} × {horizonYears} year{horizonYears !== 1 ? 's' : ''}.
                  This is not Full Property ROI.
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <p className="text-sm text-apil-gray-500 mb-2">
              Set your investment holding period in your Investment Profile
              to see cumulative rental income over your horizon.
            </p>
            <Link to="/questionnaire" className="text-xs text-apil-blue hover:underline">
              Edit Investment Profile →
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
