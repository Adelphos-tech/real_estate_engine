import { useState, useEffect } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api, investorSession } from '../data/api';
import type { PersonalizedProperty } from '../data/api';

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
      'Priced significantly below comparable DLD resale transactions.',
    OPPORTUNITY:
      'Priced below comparable DLD resale transactions.',
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

function translateAgreement(agreement?: string): string {
  if (!agreement) return '';
  if (agreement.includes('CONSISTENT_POSITIVE')) return 'Consistent positive signal across benchmarks';
  if (agreement.includes('CONSISTENT_NEGATIVE')) return 'Consistent negative signal across benchmarks';
  if (agreement.includes('MIXED')) return 'Mixed signals across benchmarks';
  return agreement.replace(/_/g, ' ').toLowerCase();
}

function translatePreferenceName(name: string): string {
  const map: Record<string, string> = {
    budget:              'Fits your budget',
    property_type:       'Fits your preferred property type',
    bedrooms:            'Fits your bedroom preference',
    location:            'Fits your preferred location',
    developer_grade:     'Fits your developer quality preference',
    risk_compatibility:  'Fits your risk profile',
    horizon_compatibility:'Fits your investment horizon',
    liquidity:           'Fits your liquidity preference',
    property_status:     'Fits your preferred property status',
    rental_yield:        'Rental yield preference',
    financing_compatibility: 'Financing compatibility',
    lifestyle:           'Lifestyle requirements',
  };
  return map[name] || name.replace(/_/g, ' ');
}

/* ─── Build "Why This Stands Out" bullets ─── */
function buildHighlights(property: PersonalizedProperty): string[] {
  const { developer, benchmarks, price_analysis, objective_signal } = property;
  const h: string[] = [];

  if (developer?.grade) {
    h.push(`Grade ${developer.grade} developer — ${developer.quality_tier}`);
  }

  const usable = benchmarks.filter(b => b.usable_for_investment);
  if (usable.length > 0) {
    const best = usable[0];
    if (best.match_level) {
      h.push(translateMatch(best.match_level));
    }
    if (best.transaction_count >= 30) {
      h.push(`Based on ${best.transaction_count} DLD transactions`);
    } else if (best.transaction_count >= 10) {
      h.push(`Based on ${best.transaction_count} DLD transactions`);
    }
  }

  if (price_analysis?.evidence_strength) {
    h.push(`${price_analysis.evidence_strength.replace(/_/g, ' ')} evidence confidence`);
  }

  if (price_analysis?.best_usable_advantage_pct !== null && price_analysis?.best_usable_advantage_pct !== undefined) {
    const adv = price_analysis.best_usable_advantage_pct;
    if (adv > 0) {
      h.push(`Priced ${adv.toFixed(1)}% below comparable DLD resale`);
    } else if (adv < 0) {
      h.push(`Priced ${Math.abs(adv).toFixed(1)}% above comparable DLD resale`);
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
function PriceComparison({ price, median, advantagePct }: { price: number | null; median: number | null; advantagePct: number | null }) {
  if (!price || !median || advantagePct === null) return null;
  const below = advantagePct > 0;
  const ratio = below ? advantagePct : 0;
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
      <div className="text-center mt-2">
        <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${below ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
          {below ? `${advantagePct.toFixed(1)}% below benchmark` : `${Math.abs(advantagePct).toFixed(1)}% above benchmark`}
        </span>
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
  const investorId = investorSession.getId();

  useEffect(() => {
    if (!propertyId) return;
    api.getProperty(propertyId, investorId || undefined)
      .then(setProperty)
      .catch((e: any) => setError(e.message))
      .finally(() => setLoading(false));
  }, [propertyId]);

  if (loading) return <div className="text-center py-20 text-apil-gray-500">Loading property…</div>;
  if (error)   return <div className="text-center py-20 text-red-600">{error}</div>;
  if (!property) return <div className="text-center py-20 text-apil-gray-500">Property not found</div>;

  const p   = property.property;
  const dev = property.developer;
  const obj = property.objective_signal;
  const fit = property.investor_fit;
  const pa  = property.price_analysis;
  const highlights = buildHighlights(property);

  // Best usable benchmark for price comparison
  const bestBench = property.benchmarks.find(b => b.usable_for_investment) || property.benchmarks[0];

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Link to="/marketplace" className="text-sm text-apil-blue hover:underline mb-4 inline-block">← Back to Marketplace</Link>

      {/* ── 1. PROPERTY HEADER ────────────────────────────── */}
      <div className="mb-6">
        <h1 className="text-2xl md:text-3xl font-bold text-apil-gray-900 break-words leading-tight">{p.name || 'Unnamed Property'}</h1>
        <p className="text-apil-gray-500 mt-1">{p.area || 'Unknown Area'}{p.sub_project ? ` · ${p.sub_project}` : ''}</p>
        <div className="text-3xl md:text-4xl font-bold text-apil-gray-900 mt-3">
          {p.current_price_aed ? `AED ${(p.current_price_aed / 1_000_000).toFixed(2)}M` : 'N/A'}
          {p.size_sqm && <span className="text-base font-normal text-apil-gray-400 ml-2">· {p.size_sqm} sqm</span>}
        </div>
      </div>

      {/* ── 2. APIL INVESTMENT SIGNAL ─────────────────────── */}
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
            {obj.confidence} confidence
          </span>
        </div>

        <p className="text-apil-gray-700 text-base leading-relaxed">
          {translateDecision(obj.decision, obj.confidence)}
        </p>

        {/* Simple price comparison */}
        {bestBench?.median_price_aed && p.current_price_aed && (
          <PriceComparison
            price={p.current_price_aed}
            median={bestBench.median_price_aed}
            advantagePct={pa?.best_usable_advantage_pct}
          />
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
          {pa?.best_usable_advantage_pct !== null && pa?.best_usable_advantage_pct !== undefined && bestBench?.transaction_count !== undefined ? (
            <p>
              The asking price is{' '}
              {pa.best_usable_advantage_pct > 0 ? (
                <strong>{pa.best_usable_advantage_pct.toFixed(1)}% below</strong>
              ) : pa.best_usable_advantage_pct < 0 ? (
                <strong>{Math.abs(pa.best_usable_advantage_pct).toFixed(1)}% above</strong>
              ) : (
                <strong>at</strong>
              )}{' '}
              the historical DLD resale benchmark for the selected comparable evidence.
              The comparison is supported by{' '}
              <strong>{bestBench.transaction_count} DLD transaction{bestBench.transaction_count !== 1 ? 's' : ''}</strong>
              {' '}with a <strong>{translateMatch(bestBench.match_level)}</strong>.
            </p>
          ) : (
            <p>There is not enough DLD transaction data to compare this property against resale benchmarks.</p>
          )}
          <p className="text-sm text-apil-gray-500">
            This is a pricing signal, not a forecast of future investment return.
          </p>
        </div>
      </div>

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
          <div className="flex items-center gap-2 mb-4">
            <span className="w-2.5 h-2.5 rounded-full bg-apil-blue" />
            <span className="text-xs font-bold uppercase tracking-wider text-apil-gray-400">Your Fit</span>
          </div>

          <div className="flex items-baseline gap-3 mb-2">
            <span className="text-4xl font-bold text-apil-blue">{fit.score}</span>
            <span className="text-xl text-apil-gray-400">/100</span>
            <span className="ml-2 inline-block px-3 py-1 rounded-full text-sm font-semibold bg-apil-blue/10 text-apil-blue border border-apil-blue/20">
              {fit.tier.replace('_', ' ')}
            </span>
          </div>

          <p className="text-sm text-apil-gray-600 mb-5 bg-apil-gray-50 rounded-lg p-3 border border-apil-gray-100 leading-relaxed">
            Fit score measures how well this property matches your stated preferences. It does not measure investment performance or expected return.
          </p>

          {property.combined_explanation && (
            <p className="text-apil-gray-700 mb-5 leading-relaxed">{property.combined_explanation}</p>
          )}

          {/* Matched */}
          {fit.matched_preferences.length > 0 && (
            <div className="mb-4">
              <div className="text-sm font-semibold text-apil-gray-800 mb-2">
                {fit.matched_preferences.length} preference{fit.matched_preferences.length !== 1 ? 's' : ''} match
              </div>
              <div className="flex flex-wrap gap-2">
                {fit.matched_preferences.map((pref, i) => (
                  <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 text-sm border border-emerald-100">
                    <span className="text-emerald-500">✓</span> {translatePreferenceName(pref)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Unmatched */}
          {fit.unmatched_preferences.length > 0 && (
            <div className="mb-4">
              <div className="text-sm font-semibold text-apil-gray-800 mb-2">
                Weaker match
              </div>
              <div className="flex flex-wrap gap-2">
                {fit.unmatched_preferences.map((pref, i) => (
                  <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 text-amber-700 text-sm border border-amber-100">
                    <span className="text-amber-500">⚠</span> {translatePreferenceName(pref)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Unknown */}
          {fit.unknown_preferences.length > 0 && (
            <div>
              <div className="text-sm font-semibold text-apil-gray-800 mb-2">
                Unknown information
              </div>
              <div className="flex flex-wrap gap-2">
                {fit.unknown_preferences.map((pref, i) => (
                  <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-apil-gray-50 text-apil-gray-500 text-sm border border-apil-gray-100">
                    <span>?</span> {translatePreferenceName(pref)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── 7. HOW STRONG IS THE EVIDENCE? ────────────────── */}
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-4">How strong is the evidence?</h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
          {bestBench?.transaction_count !== undefined && (
            <div className="text-center">
              <div className="text-2xl font-bold text-apil-gray-900">{bestBench.transaction_count}</div>
              <div className="text-xs text-apil-gray-500 uppercase tracking-wide mt-1">DLD Transactions</div>
            </div>
          )}
          {bestBench?.match_level && (
            <div className="text-center">
              <div className="text-lg font-bold text-apil-gray-900">{translateMatch(bestBench.match_level)}</div>
              <div className="text-xs text-apil-gray-500 uppercase tracking-wide mt-1">Match Level</div>
            </div>
          )}
          {obj.confidence && (
            <div className="text-center">
              <div className="text-lg font-bold text-apil-gray-900">{obj.confidence}</div>
              <div className="text-xs text-apil-gray-500 uppercase tracking-wide mt-1">Confidence</div>
            </div>
          )}
          {pa?.benchmark_agreement && (
            <div className="text-center">
              <div className="text-sm font-bold text-apil-gray-900 leading-tight">{translateAgreement(pa.benchmark_agreement)}</div>
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
                <table className="w-full text-sm min-w-[600px]">
                  <thead>
                    <tr className="border-b border-apil-gray-200">
                      <th className="text-left py-2 px-3 text-apil-gray-500 font-medium">Benchmark</th>
                      <th className="text-left py-2 px-3 text-apil-gray-500 font-medium">Median</th>
                      <th className="text-left py-2 px-3 text-apil-gray-500 font-medium">Transactions</th>
                      <th className="text-left py-2 px-3 text-apil-gray-500 font-medium">Match</th>
                      <th className="text-left py-2 px-3 text-apil-gray-500 font-medium">Confidence</th>
                      <th className="text-left py-2 px-3 text-apil-gray-500 font-medium">Price comparison</th>
                    </tr>
                  </thead>
                  <tbody>
                    {property.benchmarks.map((b, i) => (
                      <tr key={i} className={`border-b border-apil-gray-100 ${b.usable_for_investment ? '' : 'bg-gray-50/50'}`}>
                        <td className="py-2.5 px-3">
                          <div className="font-medium text-apil-gray-800">{b.type.replace(/_/g, ' ')}</div>
                          {!b.usable_for_investment && (
                            <span className="text-xs text-apil-gray-400">Not used for signal</span>
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
                          {b.price_advantage_pct !== null && b.price_advantage_pct !== undefined && b.usable_for_investment ? (
                            <span className={`font-semibold ${b.price_advantage_pct >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                              {b.price_advantage_pct > 0 ? `${b.price_advantage_pct.toFixed(1)}% below benchmark` : `${Math.abs(b.price_advantage_pct).toFixed(1)}% above benchmark`}
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
    </div>
  );
}
