import { useState, useEffect } from 'react';
import { Sparkles, AlertTriangle, CheckCircle2, Handshake, FileText, Loader2 } from 'lucide-react';

interface AdvisoryData {
  explanation?: {
    explanation: string;
    key_strengths: string[];
    key_risks: string[];
    data_quality_note: string;
    plain_english_verdict: string;
    source: string;
  };
  contradictions?: {
    contradictions: string[];
    severity: string;
    recommendations: string[];
    source: string;
  };
  negotiation?: {
    strategy: string;
    suggested_offer: string;
    leverage_points: string[];
    risks: string[];
    source: string;
  };
  exitStrategy?: {
    strategy: string;
    timeline: string;
    exit_conditions: string[];
    risks: string[];
    source: string;
  };
  report?: {
    executive_summary: string;
    investment_thesis: string;
    strengths: string[];
    risks: string[];
    negotiation_tips: string[];
    exit_plan: string;
    data_reliability: string;
    source: string;
  };
}

interface LLMAdvisorySectionProps {
  propertyId?: string;
  propertySlug?: string;
  propertyType: 'ready' | 'offplan';
  topRec?: any;
  profile?: {
    goal?: string;
    budget?: string;
    risk?: string;
    timeline?: string;
    property_type?: string;
    bedrooms?: string;
  };
}

export function LLMAdvisorySection({ propertyId, propertySlug, propertyType, topRec, profile }: LLMAdvisorySectionProps) {
  const [advisory, setAdvisory] = useState<AdvisoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // If topRec already has LLM data from recommendations endpoint, use it
    if (topRec?.llmAdvisoryReport || topRec?.llmExplanation) {
      setAdvisory({
        explanation: topRec.llmExplanation,
        report: topRec.llmAdvisoryReport,
      });
      setLoading(false);
      return;
    }

    // Otherwise fetch from advisory endpoint — pass real investor profile as query params
    const baseUrl = 'http://87.200.15.174:8090';
    const profileParams = profile
      ? `?goal=${encodeURIComponent(profile.goal || 'balanced')}&budget=${encodeURIComponent(profile.budget || '')}&risk=${encodeURIComponent(profile.risk || 'medium')}&timeline=${encodeURIComponent(profile.timeline || '')}&property_type=${encodeURIComponent(profile.property_type || '')}&bedrooms=${encodeURIComponent(profile.bedrooms || 'any')}`
      : '';
    const url = propertyType === 'ready' && propertyId
      ? `${baseUrl}/properties/ready/${propertyId}/advisory${profileParams}`
      : propertyType === 'offplan' && propertySlug
      ? `${baseUrl}/properties/offplan/${propertySlug}/advisory${profileParams}`
      : null;

    if (!url) {
      setLoading(false);
      return;
    }

    fetch(url, { cache: 'no-cache' })
      .then(r => r.json())
      .then(data => {
        setAdvisory(data.advisory);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [propertyId, propertySlug, propertyType, topRec, profile]);

  if (loading) {
    return (
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="w-5 h-5 text-purple-500" />
          <h3 className="text-lg font-bold text-apil-gray-700">AI Advisor Analysis</h3>
        </div>
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-purple-500" />
          <span className="ml-2 text-sm text-apil-gray-500">Generating AI advisory report...</span>
        </div>
      </div>
    );
  }

  if (error || !advisory) {
    return null;
  }

  const report = advisory.report;
  const contradictions = advisory.contradictions;
  const negotiation = advisory.negotiation;

  const isLLM = (report?.source === 'llm');

  return (
    <div className="space-y-4">
      {report && (
        <div className="premium-card p-6 border border-purple-200 bg-gradient-to-br from-purple-50/30 to-blue-50/20">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-apil-gray-700">AI Insights</h3>
              <p className="text-xs text-apil-gray-400">
                {isLLM ? 'Powered by Qwen2.5-VL' : 'Deterministic fallback'}
              </p>
            </div>
          </div>

          {/* Investment Thesis — the "so what?" */}
          {report.investment_thesis && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-apil-gray-500 uppercase tracking-wider mb-1">Investment Thesis</p>
              <p className="text-sm text-apil-gray-700 leading-relaxed">{report.investment_thesis}</p>
            </div>
          )}

          {/* Fallback: use executive_summary if no thesis */}
          {!report.investment_thesis && report.executive_summary && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-apil-gray-500 uppercase tracking-wider mb-1">Summary</p>
              <p className="text-sm text-apil-gray-700 leading-relaxed">{report.executive_summary}</p>
            </div>
          )}

          {/* Negotiation Tips */}
          {report.negotiation_tips && report.negotiation_tips.length > 0 && (
            <div className="mb-4 p-4 bg-blue-50/40 rounded-lg border border-blue-100">
              <div className="flex items-center gap-1.5 mb-2">
                <Handshake className="w-4 h-4 text-blue-600" />
                <p className="text-xs font-semibold text-blue-700 uppercase tracking-wider">Negotiation Tips</p>
              </div>
              <ul className="space-y-1.5">
                {report.negotiation_tips.map((tip: string, i: number) => (
                  <li key={i} className="text-sm text-apil-gray-700 flex items-start gap-2">
                    <span className="text-blue-500 mt-0.5">→</span>
                    <span>{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Due Diligence — from data_reliability + risks */}
          {report.data_reliability && (
            <div className="p-3 bg-apil-gray-50 rounded-lg">
              <div className="flex items-center gap-1.5 mb-1">
                <FileText className="w-3.5 h-3.5 text-apil-gray-400" />
                <p className="text-xs font-semibold text-apil-gray-500 uppercase tracking-wider">Due Diligence</p>
              </div>
              <p className="text-xs text-apil-gray-600">{report.data_reliability}</p>
            </div>
          )}
        </div>
      )}

      {/* Data Quality Warnings — only if contradictions exist */}
      {contradictions && contradictions.contradictions && contradictions.contradictions.length > 0 && (
        <div className="premium-card p-5 border border-amber-200 bg-amber-50/30">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <h4 className="text-sm font-bold text-apil-gray-700">Data Quality Warnings</h4>
          </div>
          <ul className="space-y-2">
            {contradictions.contradictions.map((c: string, i: number) => (
              <li key={i} className="text-sm text-apil-gray-700 flex items-start gap-2">
                <span className="text-amber-500 mt-0.5">⚠</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Negotiation Strategy Detail — if available */}
      {negotiation && negotiation.strategy && (
        <div className="premium-card p-5 border border-blue-200 bg-blue-50/20">
          <div className="flex items-center gap-2 mb-3">
            <Handshake className="w-5 h-5 text-blue-500" />
            <h4 className="text-sm font-bold text-apil-gray-700">Negotiation Strategy</h4>
          </div>
          <p className="text-sm text-apil-gray-700 mb-3">{negotiation.strategy}</p>
          {negotiation.suggested_offer && (
            <div className="mb-3 p-3 bg-blue-50 rounded-lg">
              <p className="text-xs text-blue-600 font-semibold mb-0.5">Suggested Offer</p>
              <p className="text-lg font-bold text-blue-700">{negotiation.suggested_offer}</p>
            </div>
          )}
          {negotiation.leverage_points && negotiation.leverage_points.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-green-600 mb-1.5">Leverage Points</p>
              <ul className="space-y-1">
                {negotiation.leverage_points.map((p: string, i: number) => (
                  <li key={i} className="text-xs text-apil-gray-600 flex items-start gap-1.5">
                    <CheckCircle2 className="w-3 h-3 text-green-500 mt-0.5 flex-shrink-0" />
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
