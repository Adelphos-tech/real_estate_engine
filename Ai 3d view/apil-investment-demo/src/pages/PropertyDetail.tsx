import { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, investorSession } from '../data/api';
import type { PersonalizedProperty, Benchmark } from '../data/api';
import { RentalReturnCard } from '../components/RentalReturnCard';

/* ─── Decision badge colors ─── */
const DECISION_BADGE: Record<string, string> = {
  STRONG_OPPORTUNITY: 'bg-emerald-600 text-white',
  OPPORTUNITY:        'bg-sky-600 text-white',
  WATCH:              'bg-amber-500 text-white',
  CAUTION:            'bg-orange-500 text-white',
  AVOID:              'bg-red-600 text-white',
  INSUFFICIENT_EVIDENCE: 'bg-gray-500 text-white',
};

const DECISION_DOT: Record<string, string> = {
  STRONG_OPPORTUNITY: 'bg-emerald-500',
  OPPORTUNITY:        'bg-sky-500',
  WATCH:              'bg-amber-500',
  CAUTION:            'bg-orange-500',
  AVOID:              'bg-red-500',
  INSUFFICIENT_EVIDENCE: 'bg-gray-400',
};

/* ─── Plain-English translators (presentation-only) ─── */

function translateMatch(level: string): string {
  const map: Record<string, string> = {
    project_exact: 'Exact project match',
    project_fuzzy: 'Project-level match',
    area_exact:    'Exact area match',
    area_fallback: 'Area-level comparison',
  };
  return map[level] || level.replace(/_/g, ' ');
}

function translateDecision(decision: string, confidence: string): string {
  const m: Record<string, string> = {
    STRONG_OPPORTUNITY:
      'Priced significantly below comparable DLD sales transactions.',
    OPPORTUNITY:
      'Priced below comparable DLD sales transactions.',
    WATCH:
      'A pricing signal is present, but evidence is not yet strong enough for a firm recommendation.',
    CAUTION:
      'Mixed or weaker evidence. Proceed with additional due diligence.',
    AVOID:
      'Evidence suggests unfavorable pricing or risk factors relative to comparable transactions.',
    INSUFFICIENT_EVIDENCE:
      'Not enough DLD transaction data to evaluate this property.',
  };
  return m[decision] || decision.replace(/_/g, ' ');
}

function translateAgreement(agreement?: string, independentCount?: number): string {
  if (!agreement) return '';
  if (agreement.includes('CONSISTENT_POSITIVE')) {
    if (independentCount !== undefined && independentCount < 2) {
      return 'Single underlying evidence cohort (multiple benchmark labels)';
    }
    return 'Consistent positive signal across benchmarks';
  }
  if (agreement.includes('CONSISTENT_NEGATIVE')) return 'Consistent negative signal across benchmarks';
  if (agreement.includes('MIXED')) return 'Mixed signals across benchmarks';
  if (agreement.includes('SINGLE_BENCHMARK')) return 'Single benchmark available';
  return agreement.replace(/_/g, ' ').toLowerCase();
}

function translateProvenance(prov?: string): string {
  if (!prov) return 'Source: unavailable';
  if (prov.startsWith('master:')) return 'Source: MASTER dataset (verified)';
  if (prov.includes('exact unit match')) return 'Source: Qdrant exact unit';
  if (prov.includes('qdrant:')) return 'Source: Qdrant project metadata';
  if (prov.includes('apil:')) return 'Source: APIL property record';
  return `Source: ${prov}`;
}

function translatePreferenceName(name: string): string {
  const map: Record<string, string> = {
    budget:              'Fits your budget',
    property_type:       'Property type — evaluated when confirmed',
    bedrooms:            'Bedroom count — evaluated when confirmed',
    location:            'Fits your preferred location',
    risk_compatibility:  'Fits your risk profile',
    horizon_compatibility:'Fits your investment horizon',
    property_status:     'Fits your preferred property status',
    rental_yield:        'Rental yield — not currently evaluated',
    lifestyle:           'Lifestyle requirements — not currently evaluated',
  };
  return map[name] || name.replace(/_/g, ' ');
}

/* ─── Build "Why This Stands Out" bullets ─── */
function buildHighlights(property: PersonalizedProperty): string[] {
  const { developer, objective_signal, canonical_calculation } = property;
  const h: string[] = [];

  if (developer?.grade) {
    h.push(`Grade ${developer.grade} developer — ${developer.quality_tier}`);
  }

  // ── Canonical DLD highlights only when truly usable (§25–36 source sync) ──
  const cc = canonical_calculation;
  const canonicalUsableForHighlights = cc !== undefined && cc !== null &&
    cc.benchmark_method === 'CANONICAL_DLD' &&
    cc.benchmark_tier === 'LEVEL_1' &&
    cc.is_fallback === false &&
    cc.production_eligible === true &&
    cc.validation_status === 'VERIFIED_PRODUCTION' &&
    cc.evidence?.median !== null;

  if (canonicalUsableForHighlights) {
    const txCount = cc.evidence.transaction_count ?? 0;
    if (txCount >= 3) {
      h.push(`Based on ${txCount} verified DLD sales`);
    }

    const conv = cc.calculations?.conventional_below_benchmark_pct;
    if (conv !== null && conv !== undefined && !isNaN(conv)) {
      if (conv > 0) {
        h.push(`Priced ${conv.toFixed(1)}% below comparable DLD sales benchmark`);
      } else if (conv < 0) {
        h.push(`Priced ${Math.abs(conv).toFixed(1)}% above comparable DLD sales benchmark`);
      }
    } else {
      const adv = cc.calculations?.apil_advantage_pct;
      if (adv !== null && adv !== undefined && !isNaN(adv)) {
        if (adv > 0) {
          h.push(`APIL Price Advantage +${adv.toFixed(1)}%`);
        } else if (adv < 0) {
          h.push(`APIL Price Disadvantage ${adv.toFixed(1)}%`);
        }
      }
    }
  }

  if (objective_signal.confidence === 'HIGH') {
    h.push('High-confidence analytical signal');
  }

  return h;
}

/* ─── Build contextual warning text ─── */
function buildWarning(warning: string, benchmarks: any[]): string {
  const text = warning.toLowerCase();

  if (text.includes('transaction count') || text.includes('low sample')) {
    const lowTxn = benchmarks.filter(b => (b.transaction_count || 0) < 10 && b.usable_for_investment);
    if (lowTxn.length > 0) {
      const names = lowTxn.map(b => b.type.replace(/_/g, ' ')).join(', ');
      return `Low transaction count for ${names} (${lowTxn.map(b => `N=${b.transaction_count}`).join(', ')}).`;
    }
    const anyLow = benchmarks.filter(b => (b.transaction_count || 0) < 10);
    if (anyLow.length > 0) {
      return `Some secondary benchmark data has limited transaction history. See detailed evidence.`;
    }
    return `Some secondary benchmark data has limited transaction history. See detailed evidence.`;
  }

  if (text.includes('extreme price advantage')) {
    return `Extreme price difference detected. This should be reviewed before any investment decision.`;
  }

  if (text.includes('low confidence') || text.includes('indicative only')) {
    return `Lower confidence signal — treat as indicative and conduct additional due diligence.`;
  }

  if (text.includes('area-level fallback') || text.includes('not used for investment signal')) {
    return `Only area-level data is available. Project-specific evidence is not yet sufficient.`;
  }

  return warning;
}

/* ─── Price comparison bar component ─── */
function PriceComparison({ price, median, apilPct, conventionalPct }: { price: number | null; median: number | null; apilPct: number | null | undefined; conventionalPct: number | null | undefined }) {
  if (!price || !median) return null;
  const apilValid = apilPct !== null && apilPct !== undefined && !isNaN(apilPct);
  const convValid = conventionalPct !== null && conventionalPct !== undefined && !isNaN(conventionalPct);
  if (!apilValid && !convValid) return null;
  return (
    <div className="mt-5 mb-2">
      <div className="flex items-end justify-between gap-4 mb-2">
        <div className="flex-1">
          <div className="text-xs text-apil-gray-500 uppercase tracking-wide mb-1">Your property</div>
          <div className="text-xl font-bold text-apil-gray-900">AED {(price / 1_000_000).toFixed(2)}M</div>
        </div>
        <div className="text-apil-gray-300 text-xl pb-1">vs.</div>
        <div className="flex-1 text-right">
          <div className="text-xs text-apil-gray-500 uppercase tracking-wide mb-1">DLD resale benchmark</div>
          <div className="text-xl font-bold text-apil-gray-900">AED {(median / 1_000_000).toFixed(2)}M</div>
        </div>
      </div>
      <div className="h-3 bg-apil-gray-100 rounded-full overflow-hidden flex">
        <div className="bg-apil-blue h-full" style={{ width: `${Math.min(100, (price / median) * 100)}%` }} />
      </div>
      <div className="text-center mt-3 flex flex-col sm:flex-row flex-wrap items-center justify-center gap-3">
        {apilValid && (
          <div className="flex flex-col items-center">
            <span className="text-xs text-apil-gray-500 uppercase tracking-wide">APIL Price Advantage</span>
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold mt-0.5 ${apilPct! > 0 ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
              {apilPct! > 0 ? '+' : ''}{apilPct!.toFixed(1)}%
            </span>
          </div>
        )}
        {convValid && (
          <div className="flex flex-col items-center">
            <span className="text-xs text-apil-gray-500 uppercase tracking-wide">Conventional Price Position</span>
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold mt-0.5 ${conventionalPct! > 0 ? 'bg-sky-100 text-sky-700' : 'bg-red-100 text-red-700'}`}>
              {conventionalPct! > 0 ? `${conventionalPct!.toFixed(1)}% below benchmark` : `${Math.abs(conventionalPct!).toFixed(1)}% above benchmark`}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Main component ─── */
export default function PropertyDetail() {
  const { propertyId } = useParams();
  const navigate = useNavigate();
  const [property, setProperty] = useState<PersonalizedProperty | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAudit, setShowAudit] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);
  const [showScoreCalc, setShowScoreCalc] = useState(false);
  // ── Debug / validation mode ───────────────────────────────────────
  const [showDebugPanel, setShowDebugPanel] = useState(() => {
    // Enable via URL param ?debug=benchmarks
    return window.location.search.includes('debug=benchmarks');
  });
  const [debugSources, setDebugSources] = useState<any>(null);
  const investorId = investorSession.getId();

  useEffect(() => {
    if (!propertyId) return;
    const ocScope = sessionStorage.getItem('apil_operating_cost_user_scope') || undefined;
    const roiScope = sessionStorage.getItem('apil_roi_user_scope') || undefined;
    api.getProperty(propertyId, investorId || undefined, ocScope, roiScope)
      .then(setProperty)
      .catch((e: any) => setError(e.message))
      .finally(() => setLoading(false));
  }, [propertyId]);

  // Fetch real fallback calculations when debug panel is visible
  useEffect(() => {
    if (!showDebugPanel || !propertyId) return;
    api.getBenchmarkSources(propertyId)
      .then(setDebugSources)
      .catch(() => setDebugSources(null));
  }, [showDebugPanel, propertyId]);

  if (loading) return <div className="text-center py-20 text-apil-gray-500">Loading property…</div>;
  if (error)   return <div className="text-center py-20 text-red-600">{error}</div>;
  if (!property) return <div className="text-center py-20 text-apil-gray-500">Property not found</div>;

  const p   = property.property;
  const dev = property.developer;
  const obj = property.objective_signal;
  const fit = property.investor_fit;
  const pa  = property.price_analysis;
  const highlights = buildHighlights(property);
  const enrichment = property.enrichment;
  const isEnriched = enrichment?.enrichment_status === 'CONFIRMED';
  const canonical = property.canonical_calculation;

  // ── Canonical benchmark selection (§25–36 source sync) ─────────────────────────
  // FROZEN — DLD_CANONICAL_UI_V1_FROZEN
  // DO NOT MODIFY WITHOUT EXPLICIT RE-APPROVAL
  // This logic determines which benchmark source drives investor-facing DLD results.
  // Any change requires: new version marker, full 2,614-property re-audit, regression re-verification.
  // ONE canonical result drives everything. No legacy bestBench fallback.
  const isCanonicalIdentityValid = canonical !== undefined && canonical !== null &&
    canonical.benchmark_method === 'CANONICAL_DLD' &&
    canonical.benchmark_tier === 'LEVEL_1' &&
    canonical.is_fallback === false &&
    canonical.validation_status === 'VERIFIED_PRODUCTION';

  const canonicalUsable = isCanonicalIdentityValid &&
    canonical.production_eligible === true &&
    canonical.evidence?.median !== null &&
    canonical.evidence?.median !== undefined;

  const canonicalTxCount = canonical?.evidence?.transaction_count ?? 0;
  const canonicalApil = canonical?.calculations?.apil_advantage_pct ?? null;
  const canonicalConv = canonical?.calculations?.conventional_below_benchmark_pct ?? null;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Link to="/marketplace" className="text-sm text-apil-blue hover:underline mb-4 inline-block">← Back to Marketplace</Link>

      {/* ── IMAGE GALLERY (Qdrant enrichment) ───────────────── */}
      {isEnriched && enrichment?.media?.images && enrichment.media.images.length > 0 && (
        <div className="mb-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {enrichment.media.images.slice(0, 4).map((img, i) => (
              <div key={i} className={`rounded-xl overflow-hidden border border-apil-gray-200 ${i === 0 ? 'sm:col-span-2' : ''}`}>
                <img
                  src={img.url}
                  alt={img.alt || p.name}
                  className="w-full h-48 sm:h-64 object-cover"
                  loading="lazy"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
              </div>
            ))}
          </div>
          {enrichment.media.images.length > 4 && (
            <p className="text-xs text-apil-gray-400 mt-2 text-center">+{enrichment.media.images.length - 4} more images</p>
          )}
        </div>
      )}

      {/* ── 1. PROPERTY HEADER ────────────────────────────── */}
      <div className="mb-6">
        <h1 className="text-2xl md:text-3xl font-bold text-apil-gray-900 break-words leading-tight">{p.name || 'Unnamed Property'}</h1>
        <p className="text-apil-gray-500 mt-1">{p.area || 'Unknown Area'}{p.sub_project ? ` · ${p.sub_project}` : ''}</p>
        <div className="text-3xl md:text-4xl font-bold text-apil-gray-900 mt-3">
          {p.current_price_aed ? `AED ${(p.current_price_aed / 1_000_000).toFixed(2)}M` : 'N/A'}
          {isEnriched && enrichment?.property_attributes?.size_sqm && (
            <span className="text-base font-normal text-apil-gray-400 ml-2">· {enrichment.property_attributes.size_sqm} sqm</span>
          )}
        </div>
      </div>

      {/* ── DATA QUALITY WARNINGS ───────────────────────── */}
      {(() => {
        const warnings: JSX.Element[] = [];
        const bval = property.benchmark_validation;
        const step5Warnings = property.objective_signal?.warnings || [];

        // Recomputed benchmark warning
        const liveTxCount = bval?.live_benchmark?.transaction_count ?? 0;
        if (property.objective_signal?.recomputed && liveTxCount > 0) {
          warnings.push(
            <div key="recomputed" className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4 text-sm text-amber-800">
              <div className="font-semibold mb-1">⚠ Benchmark Recalculated from Live DLD Data</div>
              <div>The displayed benchmark was recomputed from raw DLD transactions because the stored benchmark contained a material discrepancy.</div>
              {bval?.live_benchmark?.matched_project && (
                <div className="mt-1 text-xs text-amber-700">
                  Matched project: <strong>{bval.live_benchmark.matched_project}</strong> ·
                  Bedroom filter: {bval.live_benchmark.bedroom_filter ?? 'unspecified'} ·
                  Status filter: {bval.live_benchmark.status_filter ?? 'all'} ·
                  Transactions used: {bval.live_benchmark.transaction_count}
                </div>
              )}
            </div>
          );
        } else if (property.objective_signal?.recomputed && liveTxCount === 0) {
          warnings.push(
            <div key="no-canonical" className="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-4 text-sm text-gray-700">
              <div className="font-semibold mb-1">ℹ No Usable Canonical DLD Benchmark</div>
              <div>Not enough verified same-bedroom DLD sales were found for this exact project. The APIL investment signal cannot be derived from DLD data for this property.</div>
              {property.fallback_context?.level2 && (
                <div className="mt-1 text-xs text-gray-600">Fallback market context is shown for reference.</div>
              )}
            </div>
          );
        }

        // Fuzzy match warning
        const hasFuzzy = property.benchmarks.some((b: any) => b.match_level === 'project_fuzzy');
        if (hasFuzzy) {
          warnings.push(
            <div key="fuzzy" className="bg-orange-50 border border-orange-200 rounded-xl p-4 mb-4 text-sm text-orange-800">
              <div className="font-semibold mb-1">⚠ Fuzzy Project Match</div>
              <div>This benchmark is based on a similar project name, not the exact project. Verify the comparable before investing.</div>
            </div>
          );
        }

        // Status conflict warning
        const apilStatus = property.apil_attributes?.attributes?.status;
        const qdrantStatus = enrichment?.property_attributes?.status;
        if (apilStatus && qdrantStatus && apilStatus !== qdrantStatus) {
          warnings.push(
            <div key="status" className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4 text-sm text-blue-800">
              <div className="font-semibold mb-1">ℹ Status Conflict Detected</div>
              <div>APIL classifies this property as <strong>{apilStatus}</strong>, but Qdrant reports <strong>{qdrantStatus}</strong>. The canonical status used is <strong>{property.apil_attributes?.attributes?.status || 'Unknown'}</strong>.</div>
            </div>
          );
        }

        return warnings.length > 0 ? <>{warnings}</> : null;
      })()}

      {/* ── 2. PROPERTY DETAILS ────────────────── */}
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <h2 className="text-xs font-bold uppercase tracking-wider text-apil-gray-400 mb-4">Property Details</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
          {/* Property type — canonical: MASTER > APIL > Qdrant exact unit > unavailable */}
          <div>
            <div className="text-apil-gray-500 text-xs mb-0.5">Type</div>
            <div className="font-semibold text-apil-gray-900">
              {property.master_attributes?.property_type
                ? property.master_attributes.property_type
                : property.apil_attributes?.attributes?.property_type
                  ? property.apil_attributes.attributes.property_type
                  : isEnriched && enrichment?.property_attributes?.unit_category
                    ? enrichment.property_attributes.unit_category
                    : isEnriched && enrichment?.property_attributes?.category
                      ? enrichment.property_attributes.category
                      : 'Unavailable'}
            </div>
            <div className="text-[10px] text-apil-gray-400 mt-0.5">
              {/* Use provenance to determine actual source — master_attributes may contain Qdrant-enriched values */}
              {(() => {
                const prov = property.apil_attributes?.provenance?.property_type || '';
                if (prov.startsWith('master:')) return 'Source: MASTER dataset (verified)';
                if (prov.includes('exact unit match')) return 'Source: Qdrant exact unit';
                if (prov.includes('qdrant')) return 'Source: Qdrant project metadata';
                if (isEnriched && enrichment?.provenance?.unit_category) return 'Source: Qdrant exact unit';
                if (isEnriched && enrichment?.provenance?.category) return 'Source: Qdrant project metadata';
                return 'Source: unavailable';
              })()}
            </div>
          </div>

          {/* Bedrooms — MASTER > APIL > Qdrant unit > Qdrant project range */}
          <div>
            <div className="text-apil-gray-500 text-xs mb-0.5">Bedrooms</div>
            <div className="font-semibold text-apil-gray-900">
              {(() => {
                // 1. MASTER dataset (authoritative)
                const masterBeds = property.master_attributes?.bedrooms;
                if (masterBeds !== undefined && masterBeds !== null) return `${masterBeds} bedroom${masterBeds !== 1 ? 's' : ''}`;

                // 2. APIL specific unit record
                const apilBeds = property.apil_attributes?.attributes?.bedrooms;
                if (apilBeds !== undefined && apilBeds !== null) return `${apilBeds} bedroom${apilBeds !== 1 ? 's' : ''}`;

                // 3. Qdrant specific unit value
                const single = enrichment?.property_attributes?.unit_bedrooms ?? enrichment?.property_attributes?.bedrooms;
                if (isEnriched && single !== undefined && single !== null) {
                  return `${single} bedroom${single !== 1 ? 's' : ''}`;
                }

                // 4. Project-level range (clearly labeled)
                const opts = enrichment?.property_attributes?.project_bedroom_options ?? enrichment?.property_attributes?.bedrooms_options;
                if (isEnriched && Array.isArray(opts) && opts.length > 1) {
                  const min = Math.min(...opts);
                  const max = Math.max(...opts);
                  return `${min}–${max} BR`;
                }
                if (isEnriched && Array.isArray(opts) && opts.length === 1) {
                  return `${opts[0]} bedroom${opts[0] !== 1 ? 's' : ''}`;
                }

                return 'Unavailable';
              })()}
            </div>
            <div className="text-[10px] text-apil-gray-400 mt-0.5">
              {(() => {
                if (property.master_attributes?.bedrooms !== undefined) {
                  return 'Source: MASTER dataset (verified)';
                }
                const opts = enrichment?.property_attributes?.project_bedroom_options ?? enrichment?.property_attributes?.bedrooms_options;
                if (isEnriched && Array.isArray(opts) && opts.length > 1) {
                  return 'Source: qdrant (project-level aggregate across units)';
                }
                if (isEnriched && enrichment?.provenance?.unit_bedrooms) {
                  return translateProvenance(enrichment.provenance.unit_bedrooms);
                }
                if (isEnriched && enrichment?.provenance?.bedrooms) {
                  return translateProvenance(enrichment.provenance.bedrooms);
                }
                if (property.apil_attributes?.provenance?.bedrooms) {
                  return translateProvenance(property.apil_attributes.provenance.bedrooms);
                }
                return 'Source: unavailable';
              })()}
            </div>
            {property.data_quality_conflicts?.bedrooms && (
              <div className="text-[10px] text-amber-600 mt-0.5">
                Conflict: MASTER={property.data_quality_conflicts.bedrooms.master} vs Qdrant={property.data_quality_conflicts.bedrooms.qdrant}
              </div>
            )}
          </div>

          {/* Bathrooms — MASTER > APIL > Qdrant unit > Qdrant project range */}
          <div>
            <div className="text-apil-gray-500 text-xs mb-0.5">Bathrooms</div>
            <div className="font-semibold text-apil-gray-900">
              {(() => {
                // 1. MASTER dataset (authoritative)
                const masterBaths = property.master_attributes?.bathrooms;
                if (masterBaths !== undefined && masterBaths !== null) return `${masterBaths}`;

                // 2. APIL specific unit record
                const apilBaths = property.apil_attributes?.attributes?.bathrooms;
                if (apilBaths !== undefined && apilBaths !== null) return `${apilBaths}`;

                // 3. Qdrant specific unit value
                const single = enrichment?.property_attributes?.unit_bathrooms ?? enrichment?.property_attributes?.bathrooms;
                if (isEnriched && single !== undefined && single !== null) return `${single}`;

                // 4. Project-level range (clearly labeled in source line)
                const opts = enrichment?.property_attributes?.project_bathroom_options ?? enrichment?.property_attributes?.bathrooms_options;
                if (isEnriched && Array.isArray(opts) && opts.length > 1) {
                  const min = Math.min(...opts);
                  const max = Math.max(...opts);
                  return `${min}–${max}`;
                }
                if (isEnriched && Array.isArray(opts) && opts.length === 1) {
                  return `${opts[0]}`;
                }

                return 'Unavailable';
              })()}
            </div>
            <div className="text-[10px] text-apil-gray-400 mt-0.5">
              {(() => {
                if (property.master_attributes?.bathrooms !== undefined) {
                  return 'Source: MASTER dataset (verified)';
                }
                const opts = enrichment?.property_attributes?.project_bathroom_options ?? enrichment?.property_attributes?.bathrooms_options;
                if (isEnriched && Array.isArray(opts) && opts.length > 1) {
                  return 'Source: qdrant (project-level aggregate across units)';
                }
                if (isEnriched && enrichment?.provenance?.unit_bathrooms) {
                  return translateProvenance(enrichment.provenance.unit_bathrooms);
                }
                if (isEnriched && enrichment?.provenance?.bathrooms) {
                  return translateProvenance(enrichment.provenance.bathrooms);
                }
                return 'Source: unavailable';
              })()}
            </div>
            {property.data_quality_conflicts?.bathrooms && (
              <div className="text-[10px] text-amber-600 mt-0.5">
                Conflict: MASTER={property.data_quality_conflicts.bathrooms.master} vs Qdrant={property.data_quality_conflicts.bathrooms.qdrant}
              </div>
            )}
          </div>

          {/* Size — MASTER > APIL > Qdrant unit > Qdrant project range */}
          <div>
            <div className="text-apil-gray-500 text-xs mb-0.5">Size</div>
            <div className="font-semibold text-apil-gray-900">
              {(() => {
                // 1. MASTER dataset (authoritative)
                const masterSizeSqft = property.master_attributes?.size_sqft;
                const masterSizeSqm = property.master_attributes?.size_sqm;
                if (masterSizeSqft) return `${Math.round(masterSizeSqft).toLocaleString()} sqft`;
                if (masterSizeSqm) return `${masterSizeSqm} sqm`;

                // 2. APIL specific unit size
                const apilSize = property.apil_attributes?.attributes?.size_sqm;
                if (apilSize) return `${apilSize} sqm`;

                // 3. Qdrant specific unit size
                const unitSqft = enrichment?.property_attributes?.unit_size_sqft;
                const unitSqm = enrichment?.property_attributes?.unit_size_sqm;
                if (isEnriched && unitSqft) return `${Math.round(unitSqft).toLocaleString()} sqft`;
                if (isEnriched && unitSqm) return `${unitSqm} sqm`;
                const sqm = enrichment?.property_attributes?.size_sqm;
                const sqft = enrichment?.property_attributes?.size_sqft;
                if (isEnriched && sqm) return `${sqm} sqm`;
                if (isEnriched && sqft) return `${Math.round(sqft).toLocaleString()} sqft`;

                // 4. Project-level range (clearly labeled)
                const sqmMin = enrichment?.property_attributes?.project_size_min_sqm ?? enrichment?.property_attributes?.size_sqm_min;
                const sqmMax = enrichment?.property_attributes?.project_size_max_sqm ?? enrichment?.property_attributes?.size_sqm_max;
                if (isEnriched && sqmMin !== undefined && sqmMax !== undefined) {
                  if (sqmMin === sqmMax) return `${sqmMin} sqm`;
                  return `${sqmMin}–${sqmMax} sqm`;
                }

                return 'Unavailable';
              })()}
            </div>
            <div className="text-[10px] text-apil-gray-400 mt-0.5">
              {(() => {
                if (property.master_attributes?.size_sqft !== undefined || property.master_attributes?.size_sqm !== undefined) {
                  return 'Source: MASTER dataset (verified)';
                }
                const sqmMin = enrichment?.property_attributes?.project_size_min_sqm ?? enrichment?.property_attributes?.size_sqm_min;
                const sqmMax = enrichment?.property_attributes?.project_size_max_sqm ?? enrichment?.property_attributes?.size_sqm_max;
                if (isEnriched && sqmMin !== undefined && sqmMax !== undefined && sqmMin !== sqmMax) {
                  return 'Source: qdrant (project-level range across units)';
                }
                if (isEnriched && enrichment?.provenance?.unit_size_sqft) {
                  return translateProvenance(enrichment.provenance.unit_size_sqft);
                }
                if (isEnriched && enrichment?.provenance?.size_sqft) {
                  return translateProvenance(enrichment.provenance.size_sqft);
                }
                if (property.apil_attributes?.provenance?.size_sqm) {
                  return translateProvenance(property.apil_attributes.provenance.size_sqm);
                }
                return 'Source: unavailable';
              })()}
            </div>
            {property.data_quality_conflicts?.size_sqft && (
              <div className="text-[10px] text-amber-600 mt-0.5">
                Conflict: MASTER={property.data_quality_conflicts.size_sqft.master}sqft vs Qdrant={property.data_quality_conflicts.size_sqft.qdrant}sqft
              </div>
            )}
          </div>

          {/* Status — canonical: MASTER > APIL > Qdrant exact unit > unavailable */}
          <div>
            <div className="text-apil-gray-500 text-xs mb-0.5">Status</div>
            <div className="font-semibold text-apil-gray-900">
              {(() => {
                const ms = property.master_attributes?.status;
                if (ms && ms.toLowerCase() !== 'unknown') return ms;
                return property.apil_attributes?.attributes?.status
                  ? property.apil_attributes.attributes.status
                  : isEnriched && enrichment?.property_attributes?.unit_status
                    ? enrichment.property_attributes.unit_status
                    : isEnriched && enrichment?.property_attributes?.status
                      ? enrichment.property_attributes.status
                      : 'Unavailable';
              })()}
            </div>
            <div className="text-[10px] text-apil-gray-400 mt-0.5">
              {/* Use provenance to determine actual source — master_attributes may contain Qdrant-enriched values */}
              {(() => {
                const prov = property.apil_attributes?.provenance?.status || '';
                if (prov.startsWith('master:')) return 'Source: MASTER dataset (verified)';
                if (prov.includes('qdrant')) return 'Source: Qdrant exact unit';
                if (isEnriched && enrichment?.provenance?.unit_status) return 'Source: Qdrant exact unit';
                if (isEnriched && enrichment?.provenance?.status) return 'Source: Qdrant project metadata';
                return 'Source: unavailable';
              })()}
            </div>
          </div>

          {/* Developer */}
          <div>
            <div className="text-apil-gray-500 text-xs mb-0.5">Developer</div>
            <div className="font-semibold text-apil-gray-900">{dev.name || 'Unavailable'}</div>
            <div className="text-[10px] text-apil-gray-400 mt-0.5">
              {translateProvenance(property.apil_attributes?.provenance?.developer)}
            </div>
          </div>
        </div>

        {/* Description — exact unit, with conflict validation */}
        {/* Use cleaned description from apil_attributes (backend-normalized text) instead of raw enrichment HTML */}
        {(() => {
          const cleanedDesc = property.apil_attributes?.attributes?.description;
          const rawHtmlDesc = enrichment?.media?.description;
          const descToShow = cleanedDesc || rawHtmlDesc || '';
          const hasDesc = !!descToShow;
          if (!hasDesc) return null;
          return (
            <div className="mt-4 pt-4 border-t border-apil-gray-100">
              {property.apil_attributes?.attributes?.description_status === 'CONFLICT' ? (
                <>
                  <p className="text-sm text-apil-gray-500 italic">Detailed unit description is not currently available.</p>
                  <p className="text-[10px] text-amber-600 mt-1">
                    Description conflict: Qdrant text claims a different bedroom count than verified MASTER data.
                  </p>
                </>
              ) : (
                <>
                  <p className="text-sm text-apil-gray-600 leading-relaxed">{descToShow}</p>
                  <p className="text-[10px] text-apil-gray-400 mt-1">
                    Source: {property.apil_attributes?.provenance?.description
                      ? (property.apil_attributes.provenance.description.includes('exact unit match') ? 'Qdrant exact unit' : 'Qdrant project metadata')
                      : (enrichment?.provenance?.media_description ? 'Qdrant exact unit' : 'Not available')}
                    {property.apil_attributes?.attributes?.description_status && (
                      <span className="ml-1">· {property.apil_attributes.attributes.description_status.replace(/_/g, ' ')}</span>
                    )}
                  </p>
                </>
              )}
            </div>
          );
        })()}

        {/* Data provenance badge */}
        {enrichment && (
          <div className="mt-4 pt-3 border-t border-apil-gray-100 flex flex-wrap items-center gap-2">
            <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${isEnriched ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'}`}>
              {isEnriched ? '✓ Qdrant exact-unit enrichment confirmed' : '⊘ Qdrant data not confirmed'}
            </span>
            {isEnriched && (enrichment?.matched_qdrant_records?.length ?? 0) > 0 && (
              <span className="text-[10px] text-apil-gray-500">{enrichment.matched_qdrant_records?.length} unit record(s) matched</span>
            )}
            {enrichment?.identity_match?.reason && (
              <span className="text-[10px] text-apil-gray-500">{enrichment.identity_match.reason}</span>
            )}
          </div>
        )}
      </div>

      {/* ── 3. APIL INVESTMENT SIGNAL ─────────────────────── */}
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <span className={`w-2.5 h-2.5 rounded-full ${DECISION_DOT[obj.decision] || 'bg-gray-400'}`} />
          <span className="text-xs font-bold uppercase tracking-wider text-apil-gray-400">APIL Investment Signal</span>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-4">
          <span className={`inline-block px-4 py-2 rounded-xl text-sm font-bold uppercase ${DECISION_BADGE[obj.decision] || 'bg-gray-500 text-white'}`}>
            {obj.decision.replace('_', ' ')}
          </span>
          <span className="text-sm text-apil-gray-500">
            {obj.confidence?.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())} confidence
          </span>
        </div>

        <p className="text-apil-gray-700 text-base leading-relaxed">
          {translateDecision(obj.decision, obj.confidence)}
        </p>

        {/* Simple price comparison — canonical only */}
        {canonicalUsable && canonical?.evidence?.median && p.current_price_aed && (
          <PriceComparison
            price={p.current_price_aed}
            median={canonical.evidence.median}
            apilPct={canonicalApil}
            conventionalPct={canonicalConv}
          />
        )}

        {/* ── Fallback Market Context — display only, never drives signal ── */}
        {!canonicalUsable && property.fallback_context && (
          <div className="mt-5 pt-5 border-t border-apil-gray-100">
            {/* Canonical evidence status */}
            <div className="mb-4">
              <div className="text-xs font-bold uppercase tracking-wider text-apil-gray-400 mb-1">Verified DLD Benchmark</div>
              <div className="text-sm text-apil-gray-600">
                {canonical?.evidence?.transaction_count === 0
                  ? 'No verified same-bedroom sales found for this exact project.'
                  : `Only ${canonical?.evidence?.transaction_count ?? 0} verified same-bedroom sale${(canonical?.evidence?.transaction_count ?? 0) !== 1 ? 's' : ''} available. At least 3 are required for a reliable benchmark.`}
              </div>
            </div>

            {/* Level 2 fallback */}
            {property.fallback_context.level2 && property.fallback_context.level2.benchmark_median !== null && (
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Fallback Market Context</div>
                  <div className="flex gap-1.5">
                    <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-200 text-slate-700">Fallback · Level 2</span>
                    <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-700">Context Only</span>
                  </div>
                </div>
                <div className="flex items-end justify-between gap-3 mb-2">
                  <div>
                    <div className="text-xs text-slate-500 uppercase tracking-wide">Fallback estimate</div>
                    <div className="text-lg font-bold text-slate-800">
                      AED {(property.fallback_context.level2.benchmark_median / 1_000_000).toFixed(2)}M
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-500 uppercase tracking-wide">Transactions</div>
                    <div className="text-sm font-semibold text-slate-700">{property.fallback_context.level2.transaction_count}</div>
                  </div>
                </div>
                <div className="text-[11px] text-slate-500">
                  Same project · Same bedroom · Status broadened · {property.fallback_context.level2.transaction_source_label || 'verified sales evidence'}
                </div>
                <div className="mt-2 text-[11px] text-slate-400 italic">
                  Context estimate only — not used in the APIL investment signal.
                </div>
              </div>
            )}

            {/* Area fallback */}
            {!property.fallback_context.level2 && property.fallback_context.area_fallback && property.fallback_context.area_fallback.benchmark_median !== null && (
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-bold uppercase tracking-wider text-slate-500">Area Market Context</div>
                  <div className="flex gap-1.5">
                    <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-200 text-slate-700">Fallback · Area</span>
                    <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-700">Context Only</span>
                  </div>
                </div>
                <div className="flex items-end justify-between gap-3 mb-2">
                  <div>
                    <div className="text-xs text-slate-500 uppercase tracking-wide">Fallback estimate</div>
                    <div className="text-lg font-bold text-slate-800">
                      AED {(property.fallback_context.area_fallback.benchmark_median / 1_000_000).toFixed(2)}M
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-500 uppercase tracking-wide">Transactions</div>
                    <div className="text-sm font-semibold text-slate-700">{property.fallback_context.area_fallback.transaction_count}</div>
                  </div>
                </div>
                <div className="text-[11px] text-slate-500">
                  Same area · Same bedroom · Similar size · {property.fallback_context.area_fallback.transaction_source_label || 'comparable sales evidence'}
                </div>
                <div className="mt-2 text-[11px] text-slate-400 italic">
                  Context estimate only — not used in the APIL investment signal.
                </div>
              </div>
            )}

            {/* No fallback at all */}
            {!property.fallback_context.level2 && !property.fallback_context.area_fallback && (
              <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
                <div className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">Market Context</div>
                <div className="text-sm text-gray-600">Insufficient market evidence — no comparable benchmark or fallback estimate is available for this property.</div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── 3. WHY THIS STANDS OUT ────────────────────────── */}
      {highlights.length > 0 && (
        <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-4">Why this stands out</h2>
          <ul className="space-y-2.5">
            {highlights.map((h, i) => (
              <li key={i} className="flex items-start gap-3 text-apil-gray-700">
                <span className="text-emerald-500 mt-0.5 flex-shrink-0">✓</span>
                <span className="leading-relaxed">{h}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ── 4. WHAT DOES THIS MEAN? ───────────────────────── */}
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-3">What does this mean?</h2>
        <div className="text-apil-gray-700 leading-relaxed space-y-3">
          {canonicalUsable && canonicalConv !== null && canonicalConv !== undefined && !isNaN(canonicalConv) ? (
            <>
              <p>
                The asking price is{' '}
                {canonicalConv > 0 ? (
                  <strong>{canonicalConv.toFixed(1)}% below</strong>
                ) : canonicalConv < 0 ? (
                  <strong>{Math.abs(canonicalConv).toFixed(1)}% above</strong>
                ) : (
                  <strong>at</strong>
                )}{' '}
                the verified DLD sales benchmark for the selected comparable evidence.
                The comparison is supported by{' '}
                <strong>{canonicalTxCount} verified DLD sale{canonicalTxCount !== 1 ? 's' : ''}</strong>
                {' '}with a <strong>{translateMatch('project_exact')}</strong>.
              </p>
              {/* Source badge */}
              <div className="flex items-center gap-2 mt-2">
                <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700 border border-emerald-200">
                  DLD Canonical
                </span>
                <span className="text-xs text-apil-gray-400" title="Exact-project, same-bedroom verified sales evidence. At least 3 qualifying sales are required.">
                  Exact-project, same-bedroom verified sales evidence
                </span>
              </div>
            </>
          ) : (
            <>
              <p className="text-apil-gray-600">
                <strong>Insufficient verified sales evidence</strong>
              </p>
              <p className="text-sm text-apil-gray-500">
                {canonicalTxCount === 0
                  ? 'No verified same-bedroom sales available for this property.'
                  : canonicalTxCount === 1
                  ? 'Only 1 verified same-bedroom sale available. At least 3 qualifying sales are required for a reliable benchmark.'
                  : canonicalTxCount === 2
                  ? 'Only 2 verified same-bedroom sales available. At least 3 qualifying sales are required for a reliable benchmark.'
                  : 'There is not enough DLD transaction data to compare this property against sales benchmarks.'}
              </p>
            </>
          )}
          {canonicalUsable && canonicalApil !== null && canonicalApil !== undefined && !isNaN(canonicalApil) && (
            <p className="text-sm text-apil-gray-500">
              APIL Price Advantage: {' '}
              <strong>{canonicalApil > 0 ? '+' : ''}{canonicalApil.toFixed(1)}%</strong>
              . This is a pricing signal, not a forecast of future investment return.
            </p>
          )}
          {!canonicalUsable && (
            <p className="text-sm text-apil-gray-500">
              This is a pricing signal, not a forecast of future investment return.
            </p>
          )}
        </div>
      </div>

      {/* ── 4b. RENTAL RETURN LADDER (progressive: Gross → After SC → Adjusted → Net) ── */}
      <RentalReturnCard
        purchasePrice={p.current_price_aed}
        rental={property.rental_context}
        serviceCharge={property.service_charge_context}
        operatingCost={property.rental_operating_cost_context}
        investorProfile={property.investor_profile}
        horizonContext={property.horizon_context}
      />

      {/* ── 5. TWO SEPARATE ASSESSMENTS ───────────────────── */}
      <div className="bg-apil-gray-50 rounded-2xl border border-apil-gray-200 p-4 mb-6">
        <h3 className="text-xs font-bold uppercase tracking-wider text-apil-gray-500 mb-3">Two separate assessments</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div className="bg-white rounded-xl p-4 border border-apil-gray-100">
            <div className="flex items-center gap-2 mb-2">
              <span className={`w-2.5 h-2.5 rounded-full ${DECISION_DOT[obj.decision] || 'bg-gray-400'}`} />
              <span className="font-semibold text-apil-gray-800">Investment signal</span>
            </div>
            <p className="text-apil-gray-600 leading-relaxed">
              What the DLD evidence and investment model indicate about the property.
            </p>
          </div>
          <div className="bg-white rounded-xl p-4 border border-apil-gray-100">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-2.5 h-2.5 rounded-full bg-apil-blue" />
              <span className="font-semibold text-apil-gray-800">Investor fit</span>
            </div>
            <p className="text-apil-gray-600 leading-relaxed">
              How well the property matches your stated preferences. Investor fit cannot upgrade or downgrade the investment signal.
            </p>
          </div>
        </div>
      </div>

      {/* ── 6. YOUR FIT ───────────────────────────────────── */}
      {fit && (
        <div className="bg-white rounded-2xl border border-apil-blue/20 p-5 md:p-6 mb-6 shadow-sm">
          {/* Header with score secondary */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-apil-blue" />
              <span className="text-xs font-bold uppercase tracking-wider text-apil-gray-400">Your Fit</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-apil-blue">{fit.score}</span>
              <span className="text-sm text-apil-gray-400">/100</span>
              <span className="ml-1 inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-apil-blue/10 text-apil-blue border border-apil-blue/20">
                {fit.tier.replace('_', ' ')}
              </span>
            </div>
          </div>

          <p className="text-sm text-apil-gray-600 mb-6 bg-apil-gray-50 rounded-lg p-3 border border-apil-gray-100 leading-relaxed">
            This measures how well this property matches your stated preferences using only the dimensions APIL can currently evaluate. It does not measure investment performance or expected return.
          </p>

          {property.combined_explanation && (
            <p className="text-apil-gray-700 mb-5 leading-relaxed">{property.combined_explanation}</p>
          )}

          {/* Why it fits you */}
          {fit.dimension_explanations && fit.dimension_explanations.filter(e => e.status === 'matched').length > 0 && (
            <div className="mb-5">
              <h3 className="text-sm font-bold text-apil-gray-800 mb-3 flex items-center gap-2">
                <span className="text-emerald-500">✓</span> Why it fits you
              </h3>
              <div className="space-y-3">
                {fit.dimension_explanations
                  .filter(e => e.status === 'matched')
                  .map((exp, i) => (
                    <div key={i} className="flex items-start gap-3 text-sm">
                      <span className="text-emerald-500 mt-0.5 flex-shrink-0">✓</span>
                      <div className="flex-1">
                        <div className="font-semibold text-apil-gray-800">{exp.dimension_label}</div>
                        <div className="text-apil-gray-600 leading-relaxed">{exp.explanation}</div>
                        {exp.source && (
                          <div className="text-[10px] text-apil-gray-400 mt-0.5">Source: {exp.source}</div>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Where it doesn't */}
          {fit.dimension_explanations && fit.dimension_explanations.filter(e => e.status === 'unmatched').length > 0 && (
            <div className="mb-5">
              <h3 className="text-sm font-bold text-apil-gray-800 mb-3 flex items-center gap-2">
                <span className="text-amber-500">⚠</span> Where it doesn't fit as well
              </h3>
              <div className="space-y-3">
                {fit.dimension_explanations
                  .filter(e => e.status === 'unmatched')
                  .map((exp, i) => (
                    <div key={i} className="flex items-start gap-3 text-sm">
                      <span className="text-amber-500 mt-0.5 flex-shrink-0">⚠</span>
                      <div className="flex-1">
                        <div className="font-semibold text-apil-gray-800">{exp.dimension_label}</div>
                        <div className="text-apil-gray-600 leading-relaxed">{exp.explanation}</div>
                        {exp.source && (
                          <div className="text-[10px] text-apil-gray-400 mt-0.5">Source: {exp.source}</div>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Not currently evaluated */}
          {fit.dimension_explanations && fit.dimension_explanations.filter(e => e.status === 'not_evaluated').length > 0 && (
            <div className="mb-5">
              <h3 className="text-sm font-bold text-apil-gray-800 mb-3 flex items-center gap-2">
                <span className="text-apil-gray-400">⊘</span> Not currently evaluated
              </h3>
              <div className="space-y-3">
                {fit.dimension_explanations
                  .filter(e => e.status === 'not_evaluated')
                  .map((exp, i) => (
                    <div key={i} className="flex items-start gap-3 text-sm">
                      <span className="text-apil-gray-400 mt-0.5 flex-shrink-0">⊘</span>
                      <div className="flex-1">
                        <div className="font-semibold text-apil-gray-800">{exp.dimension_label}</div>
                        <div className="text-apil-gray-500 leading-relaxed">{exp.explanation}</div>
                        {exp.source && (
                          <div className="text-[10px] text-apil-gray-400 mt-0.5">Source: {exp.source}</div>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
              <p className="text-xs text-apil-gray-400 mt-3 leading-relaxed">
                These dimensions are collected in your profile but cannot be evaluated because the required property data is not currently available.
              </p>
            </div>
          )}

          {/* Unknown information */}
          {fit.dimension_explanations && fit.dimension_explanations.filter(e => e.status === 'unknown').length > 0 && (
            <div className="mb-5">
              <h3 className="text-sm font-bold text-apil-gray-800 mb-3 flex items-center gap-2">
                <span className="text-apil-gray-400">?</span> Unknown information
              </h3>
              <div className="space-y-3">
                {fit.dimension_explanations
                  .filter(e => e.status === 'unknown')
                  .map((exp, i) => (
                    <div key={i} className="flex items-start gap-3 text-sm">
                      <span className="text-apil-gray-400 mt-0.5 flex-shrink-0">?</span>
                      <div className="flex-1">
                        <div className="font-semibold text-apil-gray-800">{exp.dimension_label}</div>
                        <div className="text-apil-gray-500 leading-relaxed">{exp.explanation}</div>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Expandable score calculation */}
          <button
            onClick={() => setShowScoreCalc(prev => !prev)}
            className="w-full text-center py-2.5 rounded-xl border border-apil-gray-200 text-sm font-medium text-apil-gray-500 hover:bg-apil-gray-50 transition-colors"
          >
            {showScoreCalc ? 'Hide how this score is calculated' : 'How this score is calculated'}
          </button>

          {showScoreCalc && (
            <div className="mt-4 bg-apil-gray-50 rounded-xl p-4 border border-apil-gray-100 text-sm space-y-3">
              <p className="text-apil-gray-700">
                Your fit score is calculated from <strong>only the dimensions APIL can currently evaluate</strong>:
              </p>
              <div className="space-y-2">
                {fit.dimension_explanations
                  ?.filter(e => e.status === 'matched' || e.status === 'unmatched')
                  .map((exp, i) => (
                    <div key={i} className="flex justify-between items-center">
                      <span className="text-apil-gray-600">{exp.dimension_label}</span>
                      <div className="flex items-center gap-3">
                        <span className={`text-xs font-medium ${exp.score >= 70 ? 'text-emerald-600' : exp.score >= 40 ? 'text-amber-600' : 'text-red-600'}`}>
                          {exp.score}/100
                        </span>
                        <span className="text-xs text-apil-gray-400">× {exp.normalized_weight}%</span>
                      </div>
                    </div>
                  ))}
              </div>
              <div className="pt-2 border-t border-apil-gray-200 flex justify-between items-center font-semibold">
                <span className="text-apil-gray-800">Final score</span>
                <span className="text-apil-blue">{fit.score}/100 — {fit.tier.replace('_', ' ')}</span>
              </div>
              <p className="text-xs text-apil-gray-500 leading-relaxed">
                Property type and bedroom dimensions are included in the score only when confirmed data is available. Unsupported dimensions are excluded — they do not receive a default score.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── 7. HOW STRONG IS THE EVIDENCE? ────────────────── */}
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-4">How strong is the evidence?</h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
          {canonicalTxCount !== undefined && (
            <div className="text-center">
              <div className="text-2xl font-bold text-apil-gray-900">{canonicalTxCount}</div>
              <div className="text-xs text-apil-gray-500 uppercase tracking-wide mt-1">DLD Transactions</div>
            </div>
          )}
          {canonicalUsable && (
            <div className="text-center">
              <div className="text-lg font-bold text-apil-gray-900">{translateMatch('project_exact')}</div>
              <div className="text-xs text-apil-gray-500 uppercase tracking-wide mt-1">Match Level</div>
            </div>
          )}
          {obj.confidence && (
            <div className="text-center">
              <div className="text-lg font-bold text-apil-gray-900">{obj.confidence.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, c => c.toUpperCase())}</div>
              <div className="text-xs text-apil-gray-500 uppercase tracking-wide mt-1">Confidence</div>
            </div>
          )}
          {pa?.benchmark_agreement && (
            <div className="text-center">
              <div className="text-sm font-bold text-apil-gray-900 leading-tight">{translateAgreement(pa.benchmark_agreement, pa.independent_cohort_count)}</div>
              <div className="text-xs text-apil-gray-500 uppercase tracking-wide mt-1">Agreement</div>
            </div>
          )}
        </div>

        {/* Expandable detailed evidence */}
        <button
          onClick={() => setShowEvidence(prev => !prev)}
          className="w-full text-center py-2.5 rounded-xl border border-apil-gray-200 text-sm font-medium text-apil-gray-600 hover:bg-apil-gray-50 transition-colors"
        >
          {showEvidence ? 'Hide detailed DLD evidence' : 'View detailed DLD evidence & methodology'}
        </button>

        {showEvidence && (
          <div className="mt-4">
            {property.benchmarks.length === 0 ? (
              <div className="text-apil-gray-500 text-sm">No benchmark data available</div>
            ) : (
              <div className="overflow-x-auto -mx-2 px-2">
                <table className="w-full text-sm min-w-[700px]">
                  <thead>
                    <tr className="border-b border-apil-gray-200">
                      <th className="text-left py-2 px-3 text-apil-gray-500 font-medium">Benchmark</th>
                      <th className="text-left py-2 px-3 text-apil-gray-500 font-medium">Median</th>
                      <th className="text-left py-2 px-3 text-apil-gray-500 font-medium">Transactions</th>
                      <th className="text-left py-2 px-3 text-apil-gray-500 font-medium">Match</th>
                      <th className="text-left py-2 px-3 text-apil-gray-500 font-medium">Confidence</th>
                      <th className="text-left py-2 px-3 text-apil-gray-500 font-medium">APIL %</th>
                      <th className="text-left py-2 px-3 text-apil-gray-500 font-medium">Conventional %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {property.benchmarks.map((b, i) => (
                      <tr key={i} className={`border-b border-apil-gray-100 ${b.usable_for_investment ? '' : 'bg-gray-50/50'}`}>
                        <td className="py-2.5 px-3">
                          <div className="font-medium text-apil-gray-800">{b.type.replace(/_/g, ' ')}</div>
                          {/* Calculation identity badge */}
                          {b.benchmark_method === 'CANONICAL_DLD' && !b.is_fallback && (
                            <span className="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-100 text-emerald-700 mt-1">DLD Canonical</span>
                          )}
                          {b.is_fallback && b.benchmark_tier === 'LEVEL_2' && (
                            <span className="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-700 mt-1">Fallback · Level 2 · Context Only</span>
                          )}
                          {b.is_fallback && (b.benchmark_tier === 'LEVEL_3' || b.benchmark_tier === 'LEVEL_4') && (
                            <span className="inline-block px-2 py-0.5 rounded text-[10px] font-medium bg-orange-100 text-orange-700 mt-1">Fallback · Area · Shadow Only</span>
                          )}
                          {!b.usable_for_investment && (
                            <span className="text-xs text-apil-gray-400 block mt-0.5">Not used for signal</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-apil-gray-700">{b.median_price_aed ? `AED ${b.median_price_aed.toLocaleString()}` : 'N/A'}</td>
                        <td className="py-2.5 px-3 text-apil-gray-700">{b.transaction_count}</td>
                        <td className="py-2.5 px-3 text-apil-gray-700">{translateMatch(b.match_level)}</td>
                        <td className="py-2.5 px-3">
                          <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${b.confidence === 'High' ? 'bg-emerald-100 text-emerald-700' : b.confidence === 'Medium' ? 'bg-sky-100 text-sky-700' : 'bg-gray-100 text-gray-600'}`}>
                            {b.confidence}
                          </span>
                        </td>
                        <td className="py-2.5 px-3">
                          {b.price_advantage_pct !== null && b.price_advantage_pct !== undefined && !isNaN(b.price_advantage_pct) && b.usable_for_investment ? (
                            <span className={`font-semibold ${b.price_advantage_pct >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                              {b.price_advantage_pct >= 0 ? `+${b.price_advantage_pct.toFixed(1)}%` : `${b.price_advantage_pct.toFixed(1)}%`}
                            </span>
                          ) : (
                            <span className="text-apil-gray-400">N/A</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3">
                          {b.conventional_below_benchmark_pct !== null && b.conventional_below_benchmark_pct !== undefined && !isNaN(b.conventional_below_benchmark_pct) && b.usable_for_investment ? (
                            <span className={`font-semibold ${b.conventional_below_benchmark_pct >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                              {b.conventional_below_benchmark_pct > 0 ? `${b.conventional_below_benchmark_pct.toFixed(1)}% below benchmark` : `${Math.abs(b.conventional_below_benchmark_pct).toFixed(1)}% above benchmark`}
                            </span>
                          ) : (
                            <span className="text-apil-gray-400">N/A</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p className="text-xs text-apil-gray-500 mt-3">
              Price comparisons use historical DLD resale benchmarks. They are not forecasts of investment return.
            </p>

            {/* Methodology / Audit disclosure */}
            <div className="mt-4">
              <button
                onClick={() => setShowAudit(prev => !prev)}
                className="text-xs text-apil-gray-400 hover:text-apil-gray-600 underline"
              >
                {showAudit ? 'Hide' : 'Show'} methodology & audit disclosure
              </button>
              {showAudit && (
                <div className="mt-2 text-xs text-apil-gray-500 bg-apil-gray-50 rounded-lg p-3 border border-apil-gray-100 leading-relaxed">
                  <p className="mb-1">
                    <strong>Methodology:</strong> This property was evaluated against verified Dubai Land Department (DLD) transaction benchmarks. The investment signal combines developer grade, benchmark price comparison, evidence confidence, and transaction count. It does not include forecasts of future price appreciation.
                  </p>
                  <p>
                    <strong>Technical:</strong> {obj.reason}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── 8. DATA QUALITY WARNINGS ──────────────────────── */}
      {obj.warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-100 rounded-2xl p-5 mb-6">
          <div className="flex items-start gap-3">
            <span className="text-amber-600 mt-0.5 flex-shrink-0 text-lg">⚠</span>
            <div>
              <div className="font-semibold text-amber-800 mb-2">Data quality note</div>
              <ul className="space-y-2 text-amber-700 text-sm leading-relaxed">
                {obj.warnings.map((w, i) => (
                  <li key={i}>{buildWarning(w, property.benchmarks)}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* ── 9. DEVELOPER ──────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-3">Developer</h2>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="text-lg font-bold text-apil-gray-900">{dev.name}</div>
            <p className="text-sm text-apil-gray-600 mt-1 leading-relaxed">{dev.grade_explanation}</p>
          </div>
          <div className="text-left sm:text-right flex-shrink-0">
            <div className="text-2xl font-bold text-apil-gray-900">Grade {dev.grade}</div>
            <div className="text-sm text-apil-gray-500">{dev.quality_tier}</div>
          </div>
        </div>
      </div>

      {/* ── 10. DISCLAIMERS ──────────────────────────────── */}
      <div className="bg-apil-gray-50 rounded-2xl border border-apil-gray-200 p-5 mb-6">
        <p className="text-xs text-apil-gray-500 leading-relaxed">
          Past performance does not predict future results. Price comparisons use historical DLD resale benchmarks — they are not forecasts of investment return. Fit score measures how well this property matches your stated preferences; it does not measure investment performance or expected return. Please conduct independent due diligence before making investment decisions.
        </p>
      </div>

      {/* ── 11. CTAs ────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row gap-3 mb-8">
        <button
          onClick={() => navigate('/compare')}
          className="flex-1 bg-apil-blue text-white text-center py-3.5 rounded-xl font-semibold hover:bg-apil-blue/90 transition-colors text-base"
        >
          Compare Property
        </button>
        <button
          onClick={() => alert('Advisor booking not yet implemented.')}
          className="flex-1 bg-white text-apil-gray-700 border border-apil-gray-300 text-center py-3.5 rounded-xl font-medium hover:bg-apil-gray-50 transition-colors text-base"
        >
          Speak to Advisor
        </button>
      </div>

      {/* ── 12. DEBUG / VALIDATION PANEL (development only) ─ */}
      <div className="mb-8">
        <button
          onClick={() => setShowDebugPanel(prev => !prev)}
          className="text-xs text-apil-gray-400 hover:text-apil-gray-600 underline"
        >
          {showDebugPanel ? 'Hide' : 'Show'} benchmark source validation
        </button>

        {showDebugPanel && (
          <div className="mt-4 bg-apil-gray-50 rounded-xl p-4 border border-apil-gray-200 text-sm space-y-4">
            <h3 className="font-bold text-apil-gray-800">Benchmark Source Validation</h3>

            {/* Canonical */}
            <div className="bg-white rounded-lg p-3 border border-apil-gray-100">
              <div className="font-semibold text-apil-gray-800 mb-2">Canonical</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><span className="text-apil-gray-500">Available:</span> {canonical ? 'YES' : 'NO'}</div>
                <div><span className="text-apil-gray-500">Usable:</span> {canonicalUsable ? 'YES' : 'NO'}</div>
                <div><span className="text-apil-gray-500">Benchmark:</span> {canonical?.evidence?.median ? `AED ${(canonical.evidence.median / 1_000_000).toFixed(2)}M` : 'None'}</div>
                <div><span className="text-apil-gray-500">Tx Count:</span> {canonicalTxCount}</div>
                <div><span className="text-apil-gray-500">Method:</span> {canonical?.benchmark_method || 'N/A'}</div>
                <div><span className="text-apil-gray-500">Tier:</span> {canonical?.benchmark_tier || 'N/A'}</div>
                <div><span className="text-apil-gray-500">Version:</span> {canonical?.calculation_version || 'N/A'}</div>
              </div>
              <div className="mt-2 text-[10px] text-apil-gray-400">
                {canonical ? (
                  <span className="inline-block px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-100">DLD Canonical · LEVEL_1 · production eligible {canonical.production_eligible ? 'YES' : 'NO'}</span>
                ) : (
                  <span className="inline-block px-1.5 py-0.5 rounded bg-gray-50 text-gray-500 border border-gray-100">No canonical data</span>
                )}
              </div>
            </div>

            {/* Level 2 */}
            <div className="bg-white rounded-lg p-3 border border-apil-gray-100">
              <div className="font-semibold text-apil-gray-800 mb-2">Level 2 Fallback</div>
              {(() => {
                const level2 = property.fallback_context?.level2 || debugSources?.level2;
                return (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div><span className="text-apil-gray-500">Available:</span> {level2?.benchmark_median !== null && level2?.benchmark_median !== undefined ? 'YES' : 'NO'}</div>
                    <div><span className="text-apil-gray-500">Benchmark:</span> {level2?.benchmark_median ? `AED ${(level2.benchmark_median / 1_000_000).toFixed(2)}M` : 'None'}</div>
                    <div><span className="text-apil-gray-500">Tx Count:</span> {level2?.transaction_count ?? 'N/A'}</div>
                    <div><span className="text-apil-gray-500">usable_for_investment:</span> {level2?.usable_for_investment?.toString() ?? 'N/A'}</div>
                    <div><span className="text-apil-gray-500">is_fallback:</span> {level2?.is_fallback?.toString() ?? 'N/A'}</div>
                    <div><span className="text-apil-gray-500">production_eligible:</span> {level2?.production_eligible?.toString() ?? 'N/A'}</div>
                    <div><span className="text-apil-gray-500">validation_status:</span> {level2?.validation_status ?? 'N/A'}</div>
                    <div><span className="text-apil-gray-500">source_label:</span> {level2?.transaction_source_label ?? 'N/A'}</div>
                    <div className="col-span-2"><span className="text-apil-gray-500">source_distribution:</span> {level2?.source_distribution ? JSON.stringify(level2.source_distribution) : 'N/A'}</div>
                    {level2?.warnings && level2.warnings.length > 0 && (
                      <div className="col-span-2"><span className="text-apil-gray-500">warnings:</span> {level2.warnings.join('; ')}</div>
                    )}
                  </div>
                );
              })()}
              <div className="mt-2 text-[10px] text-apil-gray-400">
                <span className="inline-block px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-100">Fallback · Exact Project Status Broadened · CONTEXT ONLY · production eligible = false</span>
              </div>
            </div>

            {/* Area Fallback */}
            <div className="bg-white rounded-lg p-3 border border-apil-gray-100">
              <div className="font-semibold text-apil-gray-800 mb-2">Area Fallback</div>
              {(() => {
                const area = property.fallback_context?.area_fallback || debugSources?.area_fallback;
                const areaEligible = area?.benchmark_median !== null && area?.benchmark_median !== undefined;
                return (
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div><span className="text-apil-gray-500">Available:</span> {areaEligible ? 'YES' : 'NO'}</div>
                    <div><span className="text-apil-gray-500">Benchmark:</span> {areaEligible ? `AED ${(area.benchmark_median / 1_000_000).toFixed(2)}M` : 'None'}</div>
                    <div><span className="text-apil-gray-500">Tx Count:</span> {area?.transaction_count ?? 'N/A'}</div>
                    <div><span className="text-apil-gray-500">is_fallback:</span> {area?.is_fallback?.toString() ?? 'N/A'}</div>
                    <div><span className="text-apil-gray-500">production_eligible:</span> {area?.production_eligible?.toString() ?? 'N/A'}</div>
                    <div><span className="text-apil-gray-500">validation_status:</span> {area?.validation_status ?? 'N/A'}</div>
                    <div><span className="text-apil-gray-500">source_label:</span> {area?.transaction_source_label ?? 'N/A'}</div>
                    <div className="col-span-2"><span className="text-apil-gray-500">source_distribution:</span> {area?.source_distribution ? JSON.stringify(area.source_distribution) : 'N/A'}</div>
                    <div><span className="text-apil-gray-500">unique_projects:</span> {area?.unique_projects ?? 'N/A'}</div>
                    <div><span className="text-apil-gray-500">area_confidence:</span> {area?.area_mapping_confidence ?? 'N/A'}</div>
                  </div>
                );
              })()}
              <div className="mt-2 text-[10px] text-apil-gray-400">
                <span className="inline-block px-1.5 py-0.5 rounded bg-orange-50 text-orange-700 border border-orange-100">Fallback · Area · SHADOW ONLY · production eligible = false</span>
              </div>
            </div>

            {/* Selected UI Source */}
            <div className="bg-white rounded-lg p-3 border border-apil-gray-100">
              <div className="font-semibold text-apil-gray-800 mb-2">Selected Market Context Source</div>
              <div className="text-xs mb-2">
                <span className={`inline-block px-2 py-0.5 rounded font-medium ${
                  property.market_context_source === 'CANONICAL_DLD' ? 'bg-emerald-100 text-emerald-700' :
                  property.market_context_source === 'LEVEL_2_FALLBACK' ? 'bg-amber-100 text-amber-700' :
                  property.market_context_source === 'AREA_FALLBACK' ? 'bg-orange-100 text-orange-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {property.market_context_source || (canonicalUsable ? 'CANONICAL_DLD' : 'NONE')}
                </span>
                <span className="ml-2 text-apil-gray-500">
                  {property.market_context_source === 'CANONICAL_DLD' ? 'Used for market context' :
                   property.market_context_source === 'LEVEL_2_FALLBACK' ? 'Level 2 fallback context only' :
                   property.market_context_source === 'AREA_FALLBACK' ? 'Area fallback context only' :
                   'No market context available'}
                </span>
              </div>
              <div className="font-semibold text-apil-gray-800 mb-1">Selected Production Signal Source</div>
              <div className="text-xs">
                <span className={`inline-block px-2 py-0.5 rounded font-medium ${property.production_signal_source === 'CANONICAL_DLD' ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'}`}>
                  {property.production_signal_source || (canonicalUsable ? 'CANONICAL_DLD' : 'NONE')}
                </span>
                <span className="ml-2 text-apil-gray-500">
                  {property.production_signal_source === 'CANONICAL_DLD' ? 'Drives investment signal' : 'No DLD signal'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
