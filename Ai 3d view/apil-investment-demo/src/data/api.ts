/**
 * APIL Investment Engine API Client — Step 10 Production Version
 * Connects to the locked Step 9 backend.
 * The frontend NEVER calculates investment scores.
 */

const API_BASE = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE) || 'http://127.0.0.1:8000';

export interface Benchmark {
  type: string;
  median_price_aed: number | null;
  mean_price_aed: number | null;
  transaction_count: number;
  match_level: string;
  confidence: string;
  price_advantage_pct: number | null;
  conventional_below_benchmark_pct?: number | null;
  evidence_level?: string;
  usable_for_investment: boolean;
  // Live DLD benchmark fields (optional)
  matched_project?: string;
  bedroom_filter?: number | null;
  status_filter?: string | null;
  matched_transaction_ids?: string[];
  warnings?: string[];
  // Explicit calculation identity (§25–36)
  benchmark_method?: string;
  benchmark_tier?: string;
  is_fallback?: boolean;
  fallback_type?: string | null;
  production_eligible?: boolean;
  validation_status?: string;
  calculation_version?: string;
}

export interface Property {
  id: string;
  name: string;
  area: string;
  sub_project: string;
  property_type: string;
  bedrooms: number | null;
  size_sqm: number | null;
  current_price_aed: number | null;
}

export interface Developer {
  name: string;
  grade: string;
  quality_tier: string;
  grade_explanation: string;
}

export interface PriceAnalysis {
  best_usable_advantage_pct: number | null;
  best_usable_conventional_pct?: number | null;
  best_usable_benchmark_type: string | null;
  advantage_primary_pct: number | null;
  advantage_offplan_pct: number | null;
  advantage_ready_pct: number | null;
  benchmark_agreement: string;
  evidence_strength: string;
  independent_cohort_count?: number;
}

export interface ObjectiveSignal {
  decision: string;
  confidence: string;
  reason: string;
  recommendation: string;
  warnings: string[];
  recomputed?: boolean;
  step5_decision?: string;
  step5_confidence?: string;
}

export interface CanonicalCalculation {
  property_id: string;
  subject_price: number | null;
  subject_bedrooms: number | null;
  subject_status: string | null;
  evidence: {
    level: string;
    matched_project: string | null;
    bedroom_filter: number | null;
    status_filter: string | null;
    transaction_ids: string[];
    transaction_count: number;
    prices: number[];
    median: number | null;
  };
  calculations: {
    apil_advantage_pct: number | null;
    conventional_below_benchmark_pct: number | null;
  };
  confidence: string;
  decision: string;
  // Explicit calculation identity (§25–36)
  benchmark_method?: string;
  benchmark_tier?: string;
  is_fallback?: boolean;
  fallback_type?: string | null;
  production_eligible?: boolean;
  validation_status?: string;
  calculation_version?: string;
}

export interface BenchmarkSources {
  property_id: string;
  canonical: CanonicalCalculation;
  level2: Benchmark | null;
  area_fallback: any;
}

export interface BenchmarkValidation {
  live_benchmark: any;
  step5_comparison: any;
  warnings: string[];
}

export interface DimensionExplanation {
  dimension_key: string;
  dimension_label: string;
  status: "matched" | "unmatched" | "not_evaluated" | "unknown";
  score: number;
  weight: number;
  normalized_weight: number;
  investor_value: string;
  property_value: string;
  explanation: string;
  source?: string;
}

export interface InvestorFit {
  score: number;
  tier: string;
  subscores: Record<string, number>;
  matched_preferences: string[];
  unmatched_preferences: string[];
  unknown_preferences: string[];
  not_evaluated_preferences: string[];
  evaluated_dimensions: string[];
  not_evaluated_dimensions: string[];
  dimension_explanations: DimensionExplanation[];
  fit_reasons: string[];
  fit_warnings: string[];
}

export interface QdrantImage {
  url: string;
  alt: string;
}

export interface EnrichmentAttributes {
  category?: string;
  // Unit-level fields (exact match)
  unit_bedrooms?: number;
  unit_bathrooms?: number;
  unit_size_sqft?: number;
  unit_size_sqm?: number;
  unit_price_aed?: number;
  unit_status?: string;
  unit_category?: string;
  // Backward compat / deprecated
  bedrooms?: number;
  bedrooms_options?: number[];
  bathrooms?: number;
  bathrooms_options?: number[];
  size_sqft?: number;
  size_sqft_min?: number;
  size_sqft_max?: number;
  size_sqm?: number;
  size_sqm_min?: number;
  size_sqm_max?: number;
  price?: number;
  status?: string;
  developer?: string;
  community_area?: string;
  district?: string;
  latitude?: number;
  longitude?: number;
  parking?: number;
  images?: QdrantImage[];
  description?: string;
  // Project-level fields (aggregate across units)
  project_category?: string;
  project_bedroom_options?: number[];
  project_bathroom_options?: number[];
  project_size_min_sqft?: number;
  project_size_max_sqft?: number;
  project_size_min_sqm?: number;
  project_size_max_sqm?: number;
  project_status_options?: string;
  project_developer?: string;
  project_community_area?: string;
  project_district?: string;
  project_images?: QdrantImage[];
  project_description?: string;
  // Exact unit metadata
  exact_unit_matched?: boolean;
  exact_unit_qdrant_id?: string;
  exact_unit_name?: string;
}

export interface EnrichmentMedia {
  images: QdrantImage[];
  description: string;
}

export interface EnrichmentDataQuality {
  fields_present: number;
  fields_total: number;
  coverage_pct: number;
}

export interface IdentityMatch {
  strategy: string;
  apil_property_id: string;
  matched_qdrant_id: string | null;
  qdrant_name: string | null;
  confidence: string;
  reason: string;
}

export interface MatchedQdrantRecord {
  qdrant_id: number;
  qdrant_name: string;
  qdrant_project: string;
  score: number;
}

export interface PropertyEnrichment {
  enrichment_status: 'CONFIRMED' | 'NOT_CONFIRMED';
  enrichment_source: string;
  matched_qdrant_id: string | null;
  match_confidence: 'EXACT_ID' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';
  match_strategy?: string;
  identity_match?: IdentityMatch;
  property_attributes: EnrichmentAttributes;
  media: EnrichmentMedia;
  data_quality: EnrichmentDataQuality;
  provenance: Record<string, string>;
  matched_qdrant_records?: MatchedQdrantRecord[];
  rejected_candidates?: any[];
}

export interface ApilAttributes {
  attributes: {
    status?: string;
    property_type?: string;
    bedrooms?: number;
    bathrooms?: number;
    size_sqm?: number;
    size_sqft?: number;
    developer?: string;
    price?: number;
    area?: string;
    description?: string;
    description_status?: string;
    description_reason?: string;
    // Project-level reference fields
    project_bedroom_options?: number[];
    project_bathroom_options?: number[];
    project_size_min_sqft?: number;
    project_size_max_sqft?: number;
    project_status_options?: string;
    // Master metadata
    master_matched?: boolean;
  };
  provenance: Record<string, string>;
}

export interface EligibilityCheck {
  pass: boolean;
  reason: string;
}

export interface EligibilityInfo {
  eligible: boolean;
  eligibility_reasons: string[];
  failed_preferences: string[];
  checks: Record<string, EligibilityCheck>;
}

export interface PersonalizedProperty {
  property: Property;
  developer: Developer;
  benchmarks: Benchmark[];
  price_analysis: PriceAnalysis;
  objective_signal: ObjectiveSignal;
  investor_fit: InvestorFit | null;
  combined_explanation: string;
  data_quality: {
    benchmark_confidence: string;
    usable_for_signal: boolean;
    quality_flags: string[];
    last_updated: string;
  };
  meta: Record<string, any>;
  enrichment?: PropertyEnrichment;
  apil_attributes?: ApilAttributes;
  eligibility?: EligibilityInfo;
  benchmark_validation?: BenchmarkValidation;
  // MASTER dataset fields (Phase 2)
  master_attributes?: Record<string, any>;
  master_provenance?: Record<string, string>;
  data_quality_conflicts?: Record<string, { master: any; qdrant: any }>;
  master_available?: boolean;
  // MASTER FINAL audit status (Phase 3)
  final_data_status?: 'VERIFIED' | 'REVIEW_REQUIRED' | 'MISSING_DATA' | 'NO_MASTER_DATA';
  master_data_status?: {
    bedroom_value_status: string;
    dld_evidence_status: string;
    price_validation_status: string;
    audit_classification: string;
  } | null;
  investor_profile?: QuestionnaireAnswers | null;
  canonical_calculation?: CanonicalCalculation | null;
  fallback_context?: {
    level2?: {
      benchmark_median: number | null;
      transaction_count: number;
      matched_project?: string;
      bedroom_filter?: number | null;
      status_filter?: string | null;
      evidence_level?: string;
      benchmark_method?: string;
      benchmark_tier?: string;
      is_fallback?: boolean;
      fallback_type?: string;
      production_eligible?: boolean;
      validation_status?: string;
      calculation_version?: string;
      usable_for_investment?: boolean;
      warnings?: string[];
      source_distribution?: Record<string, number>;
      transaction_source_label?: string;
    } | null;
    area_fallback?: {
      benchmark_median: number | null;
      transaction_count: number;
      raw_transaction_count?: number;
      matched_area?: string;
      bedroom_filter?: number | null;
      status_filter?: string | null;
      evidence_level?: string;
      benchmark_method?: string;
      benchmark_tier?: string;
      is_fallback?: boolean;
      fallback_type?: string;
      production_eligible?: boolean;
      validation_status?: string;
      calculation_version?: string;
      size_band_applied?: boolean;
      unique_projects?: number;
      largest_project_share?: number;
      area_mapping_confidence?: string;
      source_distribution?: Record<string, number>;
      transaction_source_label?: string;
    } | null;
  } | null;
  market_context_source?: 'CANONICAL_DLD' | 'LEVEL_2_FALLBACK' | 'AREA_FALLBACK' | 'NONE';
  production_signal_source?: 'CANONICAL_DLD' | 'NONE';
  // Rental Context (DISPLAY-ONLY — gross rental yield)
  rental_context?: RentalContext;
}

export interface RentalContext {
  shadow: boolean;
  property_id?: string;
  resolved_status: string;
  selected_rental_tier: 'R1' | 'R2' | 'R3' | 'R4' | 'NONE';
  investor_label: string;
  evidence_quality: 'STRONGEST' | 'STRONGER' | 'STRONG' | 'BROADER' | 'NONE';
  annual_rent_estimate_aed: number | null;
  annual_rent_p25_aed: number | null;
  annual_rent_p75_aed: number | null;
  comparable_count: number;
  projects_in_pool: number;
  gross_rental_yield_pct: number | null;
  gross_yield_p25_pct: number | null;
  gross_yield_p75_pct: number | null;
  warnings: string;
  data_quality_warning: string | null;
  calc_version_rent: string;
  calc_version_yield: string;
  error?: string;
}

export interface QuestionnaireAnswers {
  investment_objective: string;
  budget_min_aed: number;
  budget_max_aed: number;
  horizon: string;
  risk_tolerance: string;
  property_status: string[];
  property_types: string[];
  bedrooms: string[];
  locations: string[];
  developer_preference?: string;
  [key: string]: any;
}

export interface InvestorProfile {
  id: string;
  created_at: string;
  answers: QuestionnaireAnswers;
  normalized_profile: Record<string, any>;
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    cache: 'no-cache',
    ...options,
  });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`API ${path} returned ${res.status}: ${err}`);
  }
  return res.json();
}

export const api = {
  createInvestor: (answers: QuestionnaireAnswers) =>
    fetchAPI<{ investor_id: string; profile: InvestorProfile }>('/investors', { method: 'POST', body: JSON.stringify(answers) }),

  getInvestor: (id: string) =>
    fetchAPI<InvestorProfile>(`/investors/${id}`),

  getOpportunities: (params: Record<string, string | number | boolean | undefined>, investorId?: string) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== undefined) qs.set(k, String(v)); });
    if (investorId) qs.set('investor_id', investorId);
    qs.set('include_other_opportunities', 'true');
    return fetchAPI<{
      total: number; page: number; per_page: number;
      results: PersonalizedProperty[];
      other_opportunities?: PersonalizedProperty[];
      eligible_count: number; other_count: number;
    }>(`/opportunities?${qs.toString()}`);
  },

  getProperty: (id: string, investorId?: string) => {
    const qs = investorId ? `?investor_id=${investorId}` : '';
    return fetchAPI<PersonalizedProperty>(`/properties/${id}${qs}`);
  },

  compareProperties: (propertyIds: string[], investorId?: string) =>
    fetchAPI<{ properties: PersonalizedProperty[] }>('/compare', {
      method: 'POST',
      body: JSON.stringify({ property_ids: propertyIds, investor_id: investorId }),
    }),

  getDevelopers: () =>
    fetchAPI<{ results: Developer[] }>('/developers'),

  getBenchmarkSources: (id: string) =>
    fetchAPI<BenchmarkSources>(`/debug/benchmark-sources/${id}`),
};

// Local storage helpers for investor session
export const investorSession = {
  getId: () => localStorage.getItem('apil_investor_id'),
  setId: (id: string) => localStorage.setItem('apil_investor_id', id),
  clear: () => localStorage.removeItem('apil_investor_id'),
  getProfile: () => {
    const raw = localStorage.getItem('apil_investor_profile');
    return raw ? JSON.parse(raw) : null;
  },
  setProfile: (profile: any) => localStorage.setItem('apil_investor_profile', JSON.stringify(profile)),
};
