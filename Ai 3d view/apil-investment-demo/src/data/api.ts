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
  status?: string;
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
  // Service Charge Context (V2 — service-charge-adjusted income)
  service_charge_context?: ServiceChargeContext;
  // Rental Operating Cost Context (V1 SHADOW — user-input layer)
  rental_operating_cost_context?: RentalOperatingCostContext;
  // Horizon Context (read-only from investor profile)
  horizon_context?: HorizonContext | null;
  // ROI Acquisition Cost Context (V1.2 SHADOW)
  acquisition_cost_context?: AcquisitionCostContext;
  // ROI Scenario Context (V1.3 SHADOW)
  roi_scenario_context?: RoiScenarioContext;
  // Full Property ROI Context (V1.4 SHADOW)
  full_roi_context?: FullRoiContext;
}

export interface HorizonContext {
  investment_horizon_years: number | null;
  investment_horizon_months: number | null;
  source: string;
  annual_supported_income_aed: number | null;
  annual_income_label: string | null;
  cumulative_supported_rental_income_aed: number | null;
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

export interface ServiceChargeTransparency {
  rate_aed_per_sqft: number | null;
  area_sqft_used: number | null;
  annual_service_charge_aed: number | null;
  calculation_method: string | null;
  budget_year: number | null;
  source: string | null;
  rate_source: string | null;
  area_source: string | null;
  pct_of_estimated_rent: number | null;
  pct_of_purchase_price: number | null;
}

export interface ServiceChargeContext {
  calculation_level: string;
  production_eligible: boolean;
  project_match_status: 'VERIFIED_EXACT' | 'VERIFIED_NORMALIZED_EXACT' | 'VERIFIED_ALIAS' | 'VERIFIED_PHASE_1' | 'REJECTED_IDENTITY' | 'VERIFIED' | 'NOT_MATCHED';
  service_charge_status: 'VERIFIED_CALCULABLE' | 'HELD_COMPONENT_MISMATCH' | 'HELD_AREA_BASIS' | 'HELD_USAGE' | 'HELD_YEAR' | 'HELD_RATE_SCOPE' | 'NOT_MATCHED';
  service_charge_source: string | null;
  service_charge_year: number | null;
  service_charge_rate_aed_sqft: number | null;
  mollak_project_name: string | null;
  annual_service_charge_aed: number | null;
  income_after_service_charges_aed: number | null;
  yield_after_service_charges_pct: number | null;
  included_costs: string[];
  excluded_costs: string[];
  transparency: ServiceChargeTransparency | null;
}

export interface RentalOperatingCostContext {
  calculation_level: 'GROSS_RENTAL' | 'SERVICE_CHARGE_ADJUSTED' | 'PARTIAL_OPERATING_COSTS' | 'NET_RENTAL';
  vacancy: {
    status: 'AVAILABLE' | 'MISSING';
    source: 'USER_INPUT' | 'SELF_MANAGED' | 'MISSING';
    input_mode: 'VACANCY_PERCENT' | 'VACANCY_LOSS_AED' | null;
    percent: number | null;
    loss_aed: number | null;
  };
  management: {
    status: 'AVAILABLE' | 'MISSING';
    source: 'USER_INPUT' | 'SELF_MANAGED' | 'MISSING';
    input_mode: 'USER_INPUT_FIXED_AED' | 'USER_INPUT_PERCENT' | 'SELF_MANAGED' | null;
    percent: number | null;
    annual_cost_aed: number | null;
  };
  maintenance: {
    status: 'AVAILABLE' | 'MISSING';
    source: 'USER_INPUT' | 'MISSING';
    annual_cost_aed: number | null;
  };
  effective_rental_income_aed: number | null;
  known_operating_income_aed: number | null;
  adjusted_rental_income_aed: number | null;
  adjusted_rental_yield_pct: number | null;
  net_rental_income_aed: number | null;
  net_rental_yield_pct: number | null;
  included_costs: string[];
  missing_costs: string[];
  disclosure: string;
  partial_disclosure: string | null;
}

export interface OperatingCostInputRequest {
  user_scope?: string | null;
  vacancy_input_mode?: 'VACANCY_PERCENT' | 'VACANCY_LOSS_AED' | null;
  vacancy_percent?: number | null;
  vacancy_loss_aed?: number | null;
  management_input_mode?: 'USER_INPUT_FIXED_AED' | 'USER_INPUT_PERCENT' | 'SELF_MANAGED' | null;
  management_annual_cost_aed?: number | null;
  management_percent?: number | null;
  maintenance_annual_cost_aed?: number | null;
}

export interface AcquisitionCostContext {
  calculation_level: 'NO_ACQUISITION_COSTS' | 'OFFICIAL_ACQUISITION_COSTS' | 'PARTIAL_ACQUISITION_COSTS' | 'COMPLETE_ACQUISITION_COSTS';
  purchase_price: { amount_aed: number | null; source: string };
  dld_transfer: {
    amount_aed: number | null;
    actual_buyer_rate_pct: number | null;
    official_total_rate_pct: number;
    statutory_buyer_default_pct: number;
    buyer_share_status: string;
    source: string;
    input_mode: string;
  };
  trustee_office_fee: { amount_aed: number | null; source: string; input_mode: string };
  title_deed_fee: { amount_aed: number; source: string };
  knowledge_fee: { amount_aed: number; source: string };
  innovation_fee: { amount_aed: number; source: string };
  broker_purchase: { amount_aed: number | null; source: string; input_mode: string };
  developer_admin: { amount_aed: number | null; source: string; input_mode: string };
  known_acquisition_costs_aed: number | null;
  complete_acquisition_costs_aed: number | null;
  total_cash_invested_aed: number | null;
  error?: string;
}

export interface AcquisitionCostInputRequest {
  user_scope?: string | null;
  dld_input_mode?: string | null;
  dld_custom_percent?: number | null;
  dld_custom_aed?: number | null;
  trustee_fee_aed?: number | null;
  broker_purchase_mode?: string | null;
  broker_purchase_percent?: number | null;
  broker_purchase_aed?: number | null;
  developer_admin_mode?: string | null;
  developer_admin_fee_aed?: number | null;
}

export interface RoiScenarioContext {
  holding_period: {
    status: 'AVAILABLE' | 'MISSING';
    months: number | null;
    years: number | null;
    source: string;
  };
  exit_value: {
    status: 'AVAILABLE' | 'MISSING';
    mode: 'USER_EXIT_PRICE' | 'USER_APPRECIATION_RATE' | null;
    exit_sale_price_aed: number | null;
    annual_appreciation_rate_pct: number | null;
    source: string;
    exit_price_source: string | null;
    rate_source: string | null;
  };
  selling_costs: {
    calculation_level: 'NO_SELLING_COSTS' | 'PARTIAL_SELLING_COSTS' | 'COMPLETE_SELLING_COSTS';
    broker: { amount_aed: number | null; source: string; input_mode: string; status: string };
    noc: { amount_aed: number | null; source: string; input_mode: string; status: string };
    other: { amount_aed: number | null; source: string; input_mode: string; status: string };
    complete_selling_costs_aed: number | null;
  };
  net_sale_proceeds_aed: number | null;
  roi_input_readiness: 'INCOMPLETE' | 'READY_FOR_FULL_ROI_CALCULATION' | 'NOT_EVALUATED_OFFPLAN';
  missing_roi_inputs: string[];
  error?: string;
}

export interface RoiScenarioInputRequest {
  user_scope?: string | null;
  holding_period_months?: number | null;
  exit_value_mode?: string | null;
  exit_sale_price_aed?: number | null;
  annual_appreciation_rate_pct?: number | null;
  selling_broker_mode?: string | null;
  selling_broker_percent?: number | null;
  selling_broker_aed?: number | null;
  noc_mode?: string | null;
  noc_fee_aed?: number | null;
  other_selling_mode?: string | null;
  other_selling_costs_aed?: number | null;
}

export interface FullRoiContext {
  calculation_status: 'CALCULATED' | 'INCOMPLETE' | 'NOT_EVALUATED_OFFPLAN';
  methodology_version: string;
  roi_type: string;
  rental_assumption: string;
  purchase_price_aed: number | null;
  complete_acquisition_costs_aed: number | null;
  total_cash_invested_aed: number | null;
  annual_net_rental_income_aed: number | null;
  holding_period_months: number | null;
  holding_period_years: number | null;
  exit_sale_price_aed: number | null;
  complete_selling_costs_aed: number | null;
  net_sale_proceeds_aed: number | null;
  cumulative_net_rental_income_aed: number | null;
  capital_return_aed: number | null;
  total_return_aed: number | null;
  full_property_roi_pct: number | null;
  included_components: string[];
  excluded_components: string[];
  missing_inputs: string[];
  roi_label: string;
  roi_description: string;
  disclosure: string;
  exit_value_mode?: string;
  annual_appreciation_rate_pct?: number | null;
  exit_price_source?: string;
  appreciation_rate_source?: string;
  error?: string;
}

export interface QuestionnaireAnswers {
  investment_objective: string;
  budget_min_aed: number;
  budget_max_aed: number;
  horizon: string;
  investment_horizon_years?: number | null;
  investment_horizon_months?: number | null;
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

  getProperty: (id: string, investorId?: string, operatingCostUserScope?: string, roiUserScope?: string) => {
    const qs = new URLSearchParams();
    if (investorId) qs.set('investor_id', investorId);
    if (operatingCostUserScope) qs.set('operating_cost_user_scope', operatingCostUserScope);
    if (roiUserScope) qs.set('roi_user_scope', roiUserScope);
    const qsStr = qs.toString();
    return fetchAPI<PersonalizedProperty>(`/properties/${id}${qsStr ? `?${qsStr}` : ''}`);
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

  // ROI Acquisition Cost inputs (V1.2 SHADOW)
  saveAcquisitionCosts: (propertyId: string, req: AcquisitionCostInputRequest) =>
    fetchAPI<{ property_id: string; status: string; stored_inputs: any }>(`/properties/${propertyId}/acquisition-costs`, {
      method: 'POST', body: JSON.stringify(req),
    }),
  clearAcquisitionCosts: (propertyId: string, userScope: string) =>
    fetchAPI<{ property_id: string; status: string }>(`/properties/${propertyId}/acquisition-costs?user_scope=${encodeURIComponent(userScope)}`, {
      method: 'DELETE',
    }),

  // ROI Scenario inputs (V1.3 SHADOW)
  saveRoiScenario: (propertyId: string, req: RoiScenarioInputRequest) =>
    fetchAPI<{ property_id: string; status: string; stored_inputs: any }>(`/properties/${propertyId}/roi-scenario`, {
      method: 'POST', body: JSON.stringify(req),
    }),
  clearRoiScenario: (propertyId: string, userScope: string) =>
    fetchAPI<{ property_id: string; status: string }>(`/properties/${propertyId}/roi-scenario?user_scope=${encodeURIComponent(userScope)}`, {
      method: 'DELETE',
    }),
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
