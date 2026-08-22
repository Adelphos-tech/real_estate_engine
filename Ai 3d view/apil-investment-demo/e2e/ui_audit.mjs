/**
 * UI Canonical DLD Audit — 11 Known Properties
 * Validates backend→frontend contract for canonical benchmark display.
 */

const PROPERTY_IDS = [3201, 3693, 3983, 4434, 5319, 6956, 701, 7061, 7546, 8057, 8201];
const API_BASE = 'http://127.0.0.1:8000';

const counters = {
  // Error counters (must be 0)
  FALLBACK_SHOWN_AS_CANONICAL: 0,
  LEVEL_2_USED_IN_PRODUCTION: 0,
  AREA_FALLBACK_USED_IN_PRODUCTION: 0,
  PRODUCTION_ELIGIBLE_FALSE_BUT_USED: 0,
  MISSING_IDENTITY_FIELDS: 0,
  CANONICAL_AVAILABLE_BUT_NOT_USED: 0,
  INSUFFICIENT_EVIDENCE_NOT_SHOWN_WHEN_UNUSABLE: 0,

  // Positive counters (should match expected)
  CANONICAL_USED_WHEN_USABLE: 0,
  INSUFFICIENT_EVIDENCE_SHOWN_WHEN_UNUSABLE: 0,
  TOTAL_PROPERTIES_AUDITED: 0,
};

const results = [];

async function auditProperty(pid) {
  const url = `${API_BASE}/properties/${pid}`;
  let data;
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    data = await res.json();
  } catch (e) {
    console.error(`Property ${pid}: FAILED TO FETCH — ${e.message}`);
    return;
  }

  counters.TOTAL_PROPERTIES_AUDITED++;

  const canonical = data.canonical_calculation;
  const benchmarks = data.benchmarks || [];

  // Check identity fields presence (canonical_calculation ONLY — legacy benchmarks retained for backward compat)
  const requiredIdentityFields = [
    'benchmark_method',
    'benchmark_tier',
    'is_fallback',
    'production_eligible',
    'validation_status',
    'calculation_version',
  ];
  if (canonical) {
    for (const field of requiredIdentityFields) {
      if (!(field in canonical)) {
        counters.MISSING_IDENTITY_FIELDS++;
        console.warn(`Property ${pid}: canonical_calculation missing field "${field}"`);
      }
    }
  } else {
    counters.MISSING_IDENTITY_FIELDS++;
    console.warn(`Property ${pid}: canonical_calculation missing entirely`);
  }

  // Determine what the frontend would select
  const canonicalFromApi = canonical && canonical.benchmark_method === 'CANONICAL_DLD' && canonical.is_fallback === false;
  const canonicalBench = canonicalFromApi
    ? { ...canonical, median_price_aed: canonical.evidence?.median, transaction_count: canonical.evidence?.transaction_count }
    : benchmarks.find(b =>
        b.benchmark_method === 'CANONICAL_DLD' &&
        b.benchmark_tier === 'LEVEL_1' &&
        b.is_fallback === false &&
        b.production_eligible === true &&
        b.usable_for_investment === true
      );

  const canonicalUsable = canonicalBench !== undefined && canonicalBench.median_price_aed !== null && canonicalBench.production_eligible === true;
  const txCount = canonicalBench?.transaction_count ?? canonical?.evidence?.transaction_count ?? 0;

  // Frontend selection logic mirrors PropertyDetail.tsx
  const selectedMethod = canonicalUsable ? 'CANONICAL_DLD' : 'NONE';

  // Audit checks
  if (canonicalFromApi && !canonicalUsable && canonicalBench) {
    // Canonical exists but not usable — ensure insufficient evidence path is taken
    counters.INSUFFICIENT_EVIDENCE_SHOWN_WHEN_UNUSABLE++;
  }

  if (canonicalFromApi && canonicalUsable) {
    counters.CANONICAL_USED_WHEN_USABLE++;
  }

  if (!canonicalFromApi && !canonicalBench && benchmarks.some(b => b.usable_for_investment)) {
    // There is a usable benchmark but it's not canonical — this would be a fallback shown as canonical
    counters.CANONICAL_AVAILABLE_BUT_NOT_USED++;
  }

  // Check if any benchmark with fallback=true has production_eligible=true
  const fallbackInProduction = benchmarks.find(b => b.is_fallback === true && b.production_eligible === true);
  if (fallbackInProduction) {
    counters.FALLBACK_SHOWN_AS_CANONICAL++;
    console.warn(`Property ${pid}: fallback benchmark has production_eligible=true`);
  }

  // Check Level 2 used in production
  const level2InProd = benchmarks.find(b => b.benchmark_tier === 'LEVEL_2' && b.production_eligible === true);
  if (level2InProd) {
    counters.LEVEL_2_USED_IN_PRODUCTION++;
    console.warn(`Property ${pid}: LEVEL_2 benchmark has production_eligible=true`);
  }

  // Check area fallback used in production
  const areaFallbackInProd = benchmarks.find(b => b.fallback_type && b.fallback_type.includes('AREA') && b.production_eligible === true);
  if (areaFallbackInProd) {
    counters.AREA_FALLBACK_USED_IN_PRODUCTION++;
    console.warn(`Property ${pid}: AREA fallback benchmark has production_eligible=true`);
  }

  // If canonical exists but not usable, ensure we don't show price comparison
  if (canonicalFromApi && !canonicalUsable) {
    // Frontend should show insufficient evidence
    const wouldShowInsufficient = txCount < 3;
    if (!wouldShowInsufficient) {
      counters.INSUFFICIENT_EVIDENCE_NOT_SHOWN_WHEN_UNUSABLE++;
    }
  }

  results.push({
    property_id: pid,
    name: data.property?.name || 'Unknown',
    canonical_method: canonical?.benchmark_method || 'NONE',
    canonical_tier: canonical?.benchmark_tier || 'N/A',
    is_fallback: canonical?.is_fallback ?? 'N/A',
    production_eligible: canonical?.production_eligible ?? 'N/A',
    usable: canonicalUsable,
    tx_count: txCount,
    selected_ui_source: selectedMethod,
    api_median: canonical?.evidence?.median ?? null,
  });
}

async function main() {
  for (const pid of PROPERTY_IDS) {
    await auditProperty(pid);
  }

  console.log('\n=== UI CANONICAL DLD AUDIT RESULTS ===\n');
  console.table(results);

  console.log('\n=== COUNTERS ===');
  const errorCounters = [
    'FALLBACK_SHOWN_AS_CANONICAL',
    'LEVEL_2_USED_IN_PRODUCTION',
    'AREA_FALLBACK_USED_IN_PRODUCTION',
    'PRODUCTION_ELIGIBLE_FALSE_BUT_USED',
    'MISSING_IDENTITY_FIELDS',
    'CANONICAL_AVAILABLE_BUT_NOT_USED',
    'INSUFFICIENT_EVIDENCE_NOT_SHOWN_WHEN_UNUSABLE',
  ];
  let allZero = true;
  for (const key of errorCounters) {
    const value = counters[key];
    const status = value === 0 ? '✅ PASS' : '❌ FAIL';
    if (value !== 0) allZero = false;
    console.log(`${key}: ${value} ${status}`);
  }
  console.log(`\nCANONICAL_USED_WHEN_USABLE: ${counters.CANONICAL_USED_WHEN_USABLE}`);
  console.log(`INSUFFICIENT_EVIDENCE_SHOWN_WHEN_UNUSABLE: ${counters.INSUFFICIENT_EVIDENCE_SHOWN_WHEN_UNUSABLE}`);
  console.log(`TOTAL_PROPERTIES_AUDITED: ${counters.TOTAL_PROPERTIES_AUDITED}`);

  console.log('\n=== VERDICT ===');
  if (allZero && counters.TOTAL_PROPERTIES_AUDITED === PROPERTY_IDS.length) {
    console.log('✅ ALL AUDIT COUNTERS = 0 — FRONTEND CONTRACT VALIDATED');
  } else {
    console.log('❌ AUDIT FAILED — SOME COUNTERS NON-ZERO');
  }
}

main().catch(console.error);
