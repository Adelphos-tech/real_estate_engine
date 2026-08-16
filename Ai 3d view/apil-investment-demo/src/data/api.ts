/**
 * APIL Investment Engine API Client — Step 10 Production Version
 * Connects to the locked Step 9 backend.
 * The frontend NEVER calculates investment scores.
 */

const API_BASE = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE) || 'http://localhost:8000';

export interface Benchmark {
  type: string;
  median_price_aed: number | null;
  mean_price_aed: number | null;
  transaction_count: number;
  match_level: string;
  confidence: string;
  price_advantage_pct: number | null;
  usable_for_investment: boolean;
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
  best_usable_benchmark_type: string | null;
  advantage_primary_pct: number | null;
  advantage_offplan_pct: number | null;
  advantage_ready_pct: number | null;
  benchmark_agreement: string;
  evidence_strength: string;
}

export interface ObjectiveSignal {
  decision: string;
  confidence: string;
  reason: string;
  recommendation: string;
  warnings: string[];
}

export interface InvestorFit {
  score: number;
  tier: string;
  subscores: Record<string, number>;
  matched_preferences: string[];
  unmatched_preferences: string[];
  unknown_preferences: string[];
  fit_reasons: string[];
  fit_warnings: string[];
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
  developer_preference: string;
  liquidity_preference: string;
  rental_priority: string;
  financing: string;
  downside_tolerance: string;
  lifestyle_requirements?: string[];
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
    return fetchAPI<{ total: number; page: number; per_page: number; results: PersonalizedProperty[] }>(`/opportunities?${qs.toString()}`);
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
