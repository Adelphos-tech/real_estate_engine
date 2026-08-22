import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api, investorSession } from '../data/api';

/* ─── Human-readable translators ─── */
const RISK_LABELS: Record<string, string> = {
  CONSERVATIVE: 'Conservative',
  MODERATE: 'Moderate',
  AGGRESSIVE: 'Aggressive',
};

const HORIZON_LABELS: Record<string, string> = {
  LT_2_YEARS: 'Less than 2 years',
  '2_5_YEARS': '2–5 years',
  '5_10_YEARS': '5–10 years',
  GT_10_YEARS: '10+ years',
};

function horizonDisplay(answers: any): string {
  const years = answers?.investment_horizon_years;
  if (years != null) return `${years} year${years !== 1 ? 's' : ''}`;
  return HORIZON_LABELS[answers?.horizon] || answers?.horizon || '—';
}

const STATUS_LABELS: Record<string, string> = {
  OFFPLAN: 'Off-plan',
  READY: 'Ready',
  EITHER: 'Either',
};

const OBJ_LABELS: Record<string, string> = {
  CAPITAL_APPRECIATION: 'Capital appreciation',
  RENTAL_INCOME: 'Rental income',
  BALANCED: 'Balanced growth + income',
  SHORT_TERM_FLIP: 'Short-term resale / flip',
};

export default function Profile() {
  const navigate = useNavigate();
  const investorId = investorSession.getId();
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!investorId) {
      setLoading(false);
      return;
    }
    api.getInvestor(investorId)
      .then((data) => {
        setProfile(data);
        setLoading(false);
      })
      .catch((e: any) => {
        setError(e.message || 'Failed to load profile');
        setLoading(false);
      });
  }, [investorId]);

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 text-center text-apil-gray-500">
        Loading your investor profile…
      </div>
    );
  }

  if (!investorId || !profile) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-20 text-center">
        <h1 className="text-2xl font-bold text-apil-gray-900 mb-4">No Investor Profile Found</h1>
        <p className="text-apil-gray-600 mb-8">Create your investment profile to get personalized property recommendations.</p>
        <Link to="/questionnaire" className="inline-block bg-apil-blue text-white px-6 py-3 rounded-xl font-semibold hover:bg-apil-blue/90">
          Create Your Profile →
        </Link>
      </div>
    );
  }

  const answers = profile.answers || {};
  const normalized = profile.normalized_profile || {};

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-apil-gray-900">Your Investor Profile</h1>
        <p className="text-apil-gray-500 mt-1">Review and understand your investment preferences</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-6">{error}</div>
      )}

      {/* ── Your Preferences Summary ── */}
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-6 mb-6 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-5">Your Preferences</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          <div>
            <div className="text-xs text-apil-gray-400 uppercase tracking-wide mb-1">Investment Objective</div>
            <div className="font-semibold text-apil-gray-800">{OBJ_LABELS[answers.investment_objective] || answers.investment_objective || '—'}</div>
          </div>
          <div>
            <div className="text-xs text-apil-gray-400 uppercase tracking-wide mb-1">Risk Tolerance</div>
            <div className="font-semibold text-apil-gray-800">{RISK_LABELS[answers.risk_tolerance] || answers.risk_tolerance || '—'}</div>
          </div>
          <div>
            <div className="text-xs text-apil-gray-400 uppercase tracking-wide mb-1">Investment Horizon</div>
            <div className="font-semibold text-apil-gray-800">{horizonDisplay(answers)}</div>
          </div>
          <div>
            <div className="text-xs text-apil-gray-400 uppercase tracking-wide mb-1">Property Status</div>
            <div className="font-semibold text-apil-gray-800">
              {(answers.property_status || []).map((s: string) => STATUS_LABELS[s] || s).join(', ') || '—'}
            </div>
          </div>
          <div>
            <div className="text-xs text-apil-gray-400 uppercase tracking-wide mb-1">Budget</div>
            <div className="font-semibold text-apil-gray-800">
              AED {(answers.budget_min_aed || 0).toLocaleString()} – {(answers.budget_max_aed || 0).toLocaleString()}
            </div>
          </div>
          <div className="sm:col-span-2">
            <div className="text-xs text-apil-gray-400 uppercase tracking-wide mb-1">Preferred Locations</div>
            <div className="font-semibold text-apil-gray-800">
              {(answers.locations || []).join(', ') || '—'}
            </div>
          </div>
        </div>
      </div>

      {/* ── What APIL Can Evaluate ── */}
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-6 mb-6 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-4">What APIL Can Currently Evaluate</h2>
        <p className="text-sm text-apil-gray-600 mb-4 leading-relaxed">
          These are the dimensions APIL uses when matching properties to your preferences. Each is calculated from actual property data.
        </p>
        <div className="space-y-3">
          {[
            { key: 'budget', label: 'Budget', desc: 'Compares property price against your stated budget range.' },
            { key: 'location', label: 'Location', desc: 'Checks if the property area matches your preferred locations.' },
            { key: 'property_status', label: 'Property Status', desc: 'Determines if the property is ready or off-plan based on confirmed data.' },
            { key: 'risk_compatibility', label: 'Risk Compatibility', desc: 'Measures how well the evidence confidence aligns with your risk tolerance.' },
            { key: 'horizon_compatibility', label: 'Investment Horizon', desc: 'Checks if property status suits your stated time horizon.' },
            { key: 'property_type', label: 'Property Type', desc: 'Matches property type when confirmed data is available.' },
            { key: 'bedrooms', label: 'Bedrooms', desc: 'Matches bedroom count when confirmed data is available.' },
          ].map((dim) => (
            <div key={dim.key} className="flex items-start gap-3">
              <span className="text-emerald-500 mt-0.5 flex-shrink-0 text-sm">✓</span>
              <div>
                <div className="font-medium text-apil-gray-800 text-sm">{dim.label}</div>
                <div className="text-xs text-apil-gray-500 leading-relaxed">{dim.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── What APIL Cannot Evaluate ── */}
      <div className="bg-apil-gray-50 rounded-2xl border border-apil-gray-200 p-6 mb-6">
        <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-4">What APIL Cannot Currently Evaluate</h2>
        <p className="text-sm text-apil-gray-600 mb-4 leading-relaxed">
          These preferences are collected in your profile but cannot be evaluated because the required data is not currently available in the APIL dataset.
        </p>
        <div className="space-y-3">
          {[
            { label: 'Rental Yield', reason: 'Rental data is not linked to properties.' },
          ].map((item, i) => (
            <div key={i} className="flex items-start gap-3">
              <span className="text-apil-gray-400 mt-0.5 flex-shrink-0 text-sm">⊘</span>
              <div>
                <div className="font-medium text-apil-gray-700 text-sm">{item.label}</div>
                <div className="text-xs text-apil-gray-500 leading-relaxed">{item.reason}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Score Transparency ── */}
      <div className="bg-white rounded-2xl border border-apil-gray-200 p-6 mb-6 shadow-sm">
        <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-4">How Your Fit Score Is Calculated</h2>
        <p className="text-sm text-apil-gray-600 mb-4 leading-relaxed">
          Your fit score is a weighted average of only the evaluable dimensions. Unsupported dimensions are excluded — they do not receive a default score.
        </p>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between"><span className="text-apil-gray-600">Budget</span><span className="font-medium text-apil-gray-800">30%</span></div>
          <div className="flex justify-between"><span className="text-apil-gray-600">Location</span><span className="font-medium text-apil-gray-800">20%</span></div>
          <div className="flex justify-between"><span className="text-apil-gray-600">Property Status</span><span className="font-medium text-apil-gray-800">20%</span></div>
          <div className="flex justify-between"><span className="text-apil-gray-600">Risk Compatibility</span><span className="font-medium text-apil-gray-800">20%</span></div>
          <div className="flex justify-between"><span className="text-apil-gray-600">Investment Horizon</span><span className="font-medium text-apil-gray-800">10%</span></div>
          <div className="flex justify-between"><span className="text-apil-gray-600">Property Type</span><span className="font-medium text-apil-gray-800">10% (when confirmed)</span></div>
          <div className="flex justify-between"><span className="text-apil-gray-600">Bedrooms</span><span className="font-medium text-apil-gray-800">10% (when confirmed)</span></div>
        </div>
        <div className="mt-4 pt-3 border-t border-apil-gray-100 text-xs text-apil-gray-500 leading-relaxed">
          Score = weighted average of dimension scores (0–100 each). Only evaluable dimensions participate. Property type and bedroom weights apply when confirmed data is available.
        </div>
      </div>

      {/* ── Actions ── */}
      <div className="flex flex-col sm:flex-row gap-3 mb-8">
        <button
          onClick={() => navigate('/questionnaire')}
          className="flex-1 bg-apil-blue text-white text-center py-3.5 rounded-xl font-semibold hover:bg-apil-blue/90 transition-colors"
        >
          Edit Preferences →
        </button>
        <button
          onClick={() => navigate('/marketplace')}
          className="flex-1 bg-white text-apil-gray-700 border border-apil-gray-300 text-center py-3.5 rounded-xl font-medium hover:bg-apil-gray-50 transition-colors"
        >
          Back to Marketplace
        </button>
      </div>
    </div>
  );
}
