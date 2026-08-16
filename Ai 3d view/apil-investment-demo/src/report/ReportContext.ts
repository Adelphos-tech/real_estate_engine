/**
 * ReportContext — Centralized context object that drives scenario-aware report rendering.
 *
 * Every report section receives this context and uses it to decide:
 *   1. Whether it should render at all (isApplicable)
 *   2. What content to show (goal-specific KPIs, evidence-aware messaging)
 *
 * No section should independently decide what to show — all decisions flow from context.
 */

export type InvestmentType = 'READY' | 'OFF_PLAN';
export type InvestorGoal = 'RENTAL_INCOME' | 'CAPITAL_GROWTH' | 'BALANCED' | 'END_USER' | 'FLIP_HANDOVER' | 'HOLIDAY_HOME';
export type ConfidenceLevel = 'LOW' | 'MEDIUM' | 'HIGH';

// ── Backend-driven metric states and section visibility ──
export type MetricState = 'AVAILABLE' | 'UNAVAILABLE' | 'NOT_APPLICABLE' | 'ALTERNATIVE_ONLY';
export type SectionVisibility = 'SHOW' | 'SHOW_WITH_LIMITATIONS' | 'HIDE' | 'ALTERNATIVE_ONLY';
export type BackendConfidence = 'VERY_HIGH' | 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW';

export interface BackendReportContext {
  metrics: Record<string, MetricState>;
  sections: Record<string, SectionVisibility>;
  confidence: {
    overall: BackendConfidence;
    decision: BackendConfidence;
    evidence_wording: string;
  };
  strategy: {
    goal: string;
    property_status: string;
    exit_strategy: string;
    primary_return_model: string;
    is_offplan: boolean;
    is_ready: boolean;
  };
  evidence: {
    sales_count: number;
    rental_count: number;
    has_growth: boolean;
    has_developer: boolean;
  };
  risk: { level: string };
  decision: { verdict: string };
}

export interface ReportContractData {
  report_state: string;
  visible_sections: string[];
  hidden_sections: string[];
  allowed_metrics: string[];
  forbidden_metrics: string[];
  exit_strategy: string;
  ai_grounding: string[];
  stress_tests: { id: string; label: string; metric: string; adjustment: number | string }[];
  fair_value: { show: boolean; reason: string };
  confidence: {
    sales: { label: string; score: number; count: number };
    rental: { label: string; score: number; count: number };
    growth: { label: string; score: number; count: number };
    pricing: { label: string; score: number; count: number };
  };
}

export interface ReportContext {
  investmentType: InvestmentType;
  investorGoal: InvestorGoal;
  hasRentalEvidence: boolean;
  hasComparableSales: boolean;
  hasPriceHistory: boolean;
  hasProjectHistory: boolean;
  hasDeveloperData: boolean;
  hasBuildingData: boolean;
  confidence: ConfidenceLevel;
  confidenceScore: number;
  reportState?: string;
  reportContract?: ReportContractData;
  // Backend-driven context
  backend?: BackendReportContext;
}

/**
 * Build a ReportContext from the top recommendation + investor profile.
 */
export function buildReportContext(
  topRec: any,
  profileGoal: string | undefined,
  reportContract?: ReportContractData,
): ReportContext {
  const isOffplan =
    topRec?.propertyType === 'offplan' || topRec?.status === 'offplan';

  const investmentType: InvestmentType = isOffplan ? 'OFF_PLAN' : 'READY';

  const rawGoal = (profileGoal || 'balanced').toLowerCase();
  const investorGoal: InvestorGoal =
    rawGoal === 'rental_income' ? 'RENTAL_INCOME' :
    rawGoal === 'capital_growth' ? 'CAPITAL_GROWTH' :
    rawGoal === 'end_user' ? 'END_USER' :
    rawGoal === 'flip_handover' ? 'FLIP_HANDOVER' :
    rawGoal === 'holiday_home' ? 'HOLIDAY_HOME' :
    'BALANCED';

  const dq = topRec?.dataQuality || {};
  const hasRentalEvidence =
    (dq.rentCount || 0) > 0 ||
    (topRec?.estimatedRent || 0) > 0;
  const hasComparableSales = (dq.salesCount || dq.comparableCount || 0) > 0;
  const hasPriceHistory =
    (topRec?.growth12m !== null && topRec?.growth12m !== undefined && topRec?.growth12m !== 0) ||
    (topRec?.communityData?.growth12m || 0) !== 0;
  const hasProjectHistory =
    (topRec?.projectData?.transactionVolume || 0) > 0;
  const hasDeveloperData =
    (topRec?.developerData?.developerName || topRec?.developerData?.developerScore || 0) > 0;
  const hasBuildingData = !!topRec?.projectData?.name;

  const confidenceScore = topRec?.confidenceScore || 0;
  const confidence: ConfidenceLevel =
    confidenceScore >= 70 ? 'HIGH' :
    confidenceScore >= 40 ? 'MEDIUM' :
    'LOW';

  return {
    investmentType,
    investorGoal,
    hasRentalEvidence,
    hasComparableSales,
    hasPriceHistory,
    hasProjectHistory,
    hasDeveloperData,
    hasBuildingData,
    confidence,
    confidenceScore,
    reportState: reportContract?.report_state,
    reportContract,
    backend: topRec?.reportContext as BackendReportContext | undefined,
  };
}

/**
 * Human-readable translations for internal rule flags.
 * Never expose raw rule names like RULE_1_INSUFFICIENT_SALES to users.
 */
export const RULE_FLAG_TRANSLATIONS: Record<string, string> = {
  'RULE_1_INSUFFICIENT_SALES':
    'Only a few comparable sales were available, limiting the reliability of pricing estimates.',
  'RULE_1_DOWNGRADED_TO_REVIEW':
    'Recommendation downgraded to Review due to limited sales evidence.',
  'RULE_2_HIGH_PREMIUM':
    'The asking price is significantly above fair market value. Negotiate before buying.',
  'RULE_2_DOWNGRADED_TO_CAUTION':
    'Recommendation downgraded to Caution due to high price premium.',
  'RULE_3_NO_RENT_FOR_RENTAL_INVESTOR':
    'No rental evidence exists for this property. Rental income projections are unavailable.',
  'RULE_3_DOWNGRADED_TO_HOLD':
    'Recommendation limited to Hold because rental data is missing.',
  'RULE_4_LOW_CONFIDENCE':
    'Limited comparable transaction evidence. Treat estimates as indicative and verify independently.',
  'RULE_5_PRICE_OUTLIER':
    'This price is an outlier compared to similar properties. Verify before proceeding.',
  'RULE_6_UNKNOWN_DEVELOPER':
    'The developer has limited track record. Construction risk is elevated.',
  'RULE_6_DOWNGRADED_TO_REVIEW':
    'Recommendation downgraded to Review due to unknown developer.',
  'RULE_7_NO_PRICE_HISTORY':
    'No historical price data available. Growth projections are speculative.',
  'RULE_8_LOW_DEVELOPER_SCORE':
    'Developer track record is weak. Delivery and quality risk is high.',
  'RULE_8_DOWNGRADED_TO_REVIEW':
    'Recommendation downgraded to Review due to low developer score.',
};

export function translateRuleFlag(flag: string): string {
  return RULE_FLAG_TRANSLATIONS[flag] || flag.replace(/_/g, ' ').toLowerCase().replace(/^\w/, c => c.toUpperCase());
}

/**
 * Standardized confidence label mapping — used everywhere confidence is shown.
 * Ensures Verdict, Evidence, and header always agree.
 */
export function getConfidenceLabel(score: number): string {
  if (score >= 85) return 'Very High';
  if (score >= 70) return 'High';
  if (score >= 55) return 'Moderate';
  if (score >= 40) return 'Low';
  return 'Very Low';
}

export function getConfidenceColor(score: number): string {
  if (score >= 70) return 'text-green-600';
  if (score >= 55) return 'text-blue-600';
  if (score >= 40) return 'text-amber-600';
  return 'text-red-500';
}

/**
 * Convenience predicates
 */
export function isReady(ctx: ReportContext): boolean {
  return ctx.investmentType === 'READY';
}
export function isOffPlan(ctx: ReportContext): boolean {
  return ctx.investmentType === 'OFF_PLAN';
}
export function isRentalGoal(ctx: ReportContext): boolean {
  return ctx.investorGoal === 'RENTAL_INCOME';
}
export function isGrowthGoal(ctx: ReportContext): boolean {
  return ctx.investorGoal === 'CAPITAL_GROWTH';
}
export function isEndUser(ctx: ReportContext): boolean {
  return ctx.investorGoal === 'END_USER';
}
export function isLowConfidence(ctx: ReportContext): boolean {
  return ctx.confidence === 'LOW';
}

// ── Backend context helpers ──

/** Get the state of a metric from the backend report context. */
export function metricState(ctx: ReportContext, metric: string): MetricState {
  return ctx.backend?.metrics?.[metric] ?? 'UNAVAILABLE';
}

/** Check if a metric is AVAILABLE. */
export function isAvailable(ctx: ReportContext, metric: string): boolean {
  return metricState(ctx, metric) === 'AVAILABLE';
}

/** Check if a metric is UNAVAILABLE. */
export function isUnavailable(ctx: ReportContext, metric: string): boolean {
  const s = metricState(ctx, metric);
  return s === 'UNAVAILABLE' || s === 'NOT_APPLICABLE';
}

/** Check if a metric is ALTERNATIVE_ONLY. */
export function isAlternativeOnly(ctx: ReportContext, metric: string): boolean {
  return metricState(ctx, metric) === 'ALTERNATIVE_ONLY';
}

/** Get section visibility from the backend report context. */
export function sectionVisibility(ctx: ReportContext, section: string): SectionVisibility {
  return ctx.backend?.sections?.[section] ?? 'SHOW';
}

/** Check if a section should be shown (SHOW or SHOW_WITH_LIMITATIONS). */
export function shouldShowSection(ctx: ReportContext, section: string): boolean {
  const v = sectionVisibility(ctx, section);
  return v === 'SHOW' || v === 'SHOW_WITH_LIMITATIONS';
}

/** Check if a section should be hidden. */
export function shouldHideSection(ctx: ReportContext, section: string): boolean {
  return sectionVisibility(ctx, section) === 'HIDE';
}

/** Get decision confidence from backend. */
export function decisionConfidence(ctx: ReportContext): BackendConfidence {
  return ctx.backend?.confidence?.decision ?? 'LOW';
}

/** Get evidence wording from backend. */
export function evidenceWording(ctx: ReportContext): string {
  return ctx.backend?.confidence?.evidence_wording ?? 'Limited evidence';
}

/** Get primary return model from backend. */
export function primaryReturnModel(ctx: ReportContext): string {
  return ctx.backend?.strategy?.primary_return_model ?? 'total_return';
}
