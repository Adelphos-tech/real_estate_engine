import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, investorSession } from '../data/api';

const DEFAULT_PROFILE = {
  investment_objective: '',
  budget_min_aed: '',
  budget_max_aed: '',
  investment_horizon: '',
  risk_tolerance: '',
  preferred_property_status: [] as string[],
  preferred_property_types: [] as string[],
  preferred_bedrooms: [] as string[],
  preferred_locations: [] as string[],
  developer_grade_preference: '',
  liquidity_preference: '',
  rental_priority: '',
  financing_plan: '',
  downside_tolerance: '',
  lifestyle_requirements: [] as string[],
};

const OPTIONS: Record<string, string[]> = {
  investment_objective: ['capital_growth', 'rental_income', 'balanced', 'flipping', 'holiday_home'],
  investment_horizon: ['1_year', '2_years', '3_years', '5_years', '10_years'],
  risk_tolerance: ['conservative', 'moderate', 'aggressive'],
  preferred_property_status: ['off_plan', 'ready', 'resale'],
  preferred_property_types: ['apartment', 'villa', 'townhouse', 'penthouse', 'studio'],
  preferred_bedrooms: ['studio', '1_bed', '2_bed', '3_bed', '4_plus'],
  preferred_locations: ['downtown_dubai', 'dubai_marina', 'palm_jumeirah', 'business_bay', 'jumeirah_village_circle', 'dubai_hills', 'al_furjan', 'damac_hills', 'arabian_ranches', 'meydan'],
  developer_grade_preference: ['tier_1_only', 'tier_1_and_2', 'no_preference'],
  liquidity_preference: ['high_liquidity', 'medium_liquidity', 'low_liquidity_ok'],
  rental_priority: ['high_yield', 'stable_yield', 'capital_growth_over_yield', 'not_important'],
  financing_plan: ['cash', 'mortgage_50', 'mortgage_75', 'payment_plan'],
  downside_tolerance: ['low', 'medium', 'high'],
  lifestyle_requirements: ['beach_access', 'golf_course', 'family_community', 'nightlife', 'metro_access', 'schools_nearby'],
};

const LABELS: Record<string, string> = {
  capital_growth: 'Capital Growth', rental_income: 'Rental Income', balanced: 'Balanced', flipping: 'Flipping', holiday_home: 'Holiday Home',
  '1_year': '1 Year', '2_years': '2 Years', '3_years': '3 Years', '5_years': '5 Years', '10_years': '10+ Years',
  conservative: 'Conservative', moderate: 'Moderate', aggressive: 'Aggressive',
  off_plan: 'Off-Plan', ready: 'Ready', resale: 'Resale',
  apartment: 'Apartment', villa: 'Villa', townhouse: 'Townhouse', penthouse: 'Penthouse', studio: 'Studio',
  '1_bed': '1 Bed', '2_bed': '2 Bed', '3_bed': '3 Bed', '4_plus': '4+ Bed',
  downtown_dubai: 'Downtown Dubai', dubai_marina: 'Dubai Marina', palm_jumeirah: 'Palm Jumeirah', business_bay: 'Business Bay', jumeirah_village_circle: 'JVC', dubai_hills: 'Dubai Hills', al_furjan: 'Al Furjan', damac_hills: 'Damac Hills', arabian_ranches: 'Arabian Ranches', meydan: 'Meydan',
  tier_1_only: 'Tier 1 Only', tier_1_and_2: 'Tier 1 & 2', no_preference: 'No Preference',
  high_liquidity: 'High Liquidity', medium_liquidity: 'Medium Liquidity', low_liquidity_ok: 'Low Liquidity OK',
  high_yield: 'High Yield', stable_yield: 'Stable Yield', capital_growth_over_yield: 'Capital Growth Over Yield', not_important: 'Not Important',
  cash: 'Cash', mortgage_50: '50% Mortgage', mortgage_75: '75% Mortgage', payment_plan: 'Payment Plan',
  low: 'Low', medium: 'Medium', high: 'High',
  beach_access: 'Beach Access', golf_course: 'Golf Course', family_community: 'Family Community', nightlife: 'Nightlife', metro_access: 'Metro Access', schools_nearby: 'Schools Nearby',
};

export default function Profile() {
  const [form, setForm] = useState(DEFAULT_PROFILE);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const stored = investorSession.getProfile();
    if (stored) {
      setForm({ ...DEFAULT_PROFILE, ...stored });
    }
  }, []);

  const toggleMulti = (field: string, value: string) => {
    setForm(prev => {
      const arr = prev[field as keyof typeof prev] as string[];
      if (arr.includes(value)) return { ...prev, [field]: arr.filter(v => v !== value) };
      return { ...prev, [field]: [...arr, value] };
    });
  };

  const save = async () => {
    setSaving(true);
    setMessage('');
    try {
      const payload = {
        ...form,
        budget_min_aed: Number(form.budget_min_aed) || 0,
        budget_max_aed: Number(form.budget_max_aed) || 0,
      };
      const res = await api.createInvestor(payload as any);
      investorSession.setId(res.investor_id);
      investorSession.setProfile(payload);
      setMessage('Profile saved successfully!');
      setTimeout(() => navigate('/marketplace'), 800);
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const singleSelect = (field: keyof typeof form, value: string) => setForm(prev => ({ ...prev, [field]: value }));

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-apil-gray-900">Investor Profile</h1>
        <p className="text-apil-gray-500">Review and edit your investment preferences</p>
      </div>

      {message && (
        <div className={`p-4 rounded-lg mb-6 ${message.includes('Error') ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'}`}>
          {message}
        </div>
      )}

      <div className="bg-white rounded-xl border border-apil-gray-200 p-6 space-y-8">
        {/* Single-select fields */}
        {(['investment_objective', 'investment_horizon', 'risk_tolerance', 'developer_grade_preference', 'liquidity_preference', 'rental_priority', 'financing_plan', 'downside_tolerance'] as const).map((field) => (
          <div key={field}>
            <label className="block text-sm font-semibold text-apil-gray-700 mb-2 capitalize">{field.replace(/_/g, ' ')}</label>
            <div className="flex flex-wrap gap-2">
              {OPTIONS[field].map((opt) => (
                <button
                  key={opt}
                  onClick={() => singleSelect(field, opt)}
                  className={`px-3 py-2 rounded-lg text-sm border transition-colors ${
                    form[field] === opt
                      ? 'bg-apil-blue text-white border-apil-blue'
                      : 'bg-white text-apil-gray-700 border-apil-gray-200 hover:border-apil-blue'
                  }`}
                >
                  {LABELS[opt] || opt}
                </button>
              ))}
            </div>
          </div>
        ))}

        {/* Budget */}
        <div>
          <label className="block text-sm font-semibold text-apil-gray-700 mb-2">Budget Range (AED)</label>
          <div className="flex gap-4">
            <input
              type="number"
              placeholder="Min"
              value={form.budget_min_aed}
              onChange={(e) => setForm(prev => ({ ...prev, budget_min_aed: e.target.value }))}
              className="flex-1 rounded-lg border border-apil-gray-200 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-apil-blue"
            />
            <input
              type="number"
              placeholder="Max"
              value={form.budget_max_aed}
              onChange={(e) => setForm(prev => ({ ...prev, budget_max_aed: e.target.value }))}
              className="flex-1 rounded-lg border border-apil-gray-200 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-apil-blue"
            />
          </div>
        </div>

        {/* Multi-select fields */}
        {(['preferred_property_status', 'preferred_property_types', 'preferred_bedrooms', 'preferred_locations', 'lifestyle_requirements'] as const).map((field) => (
          <div key={field}>
            <label className="block text-sm font-semibold text-apil-gray-700 mb-2 capitalize">{field.replace(/_/g, ' ')}</label>
            <div className="flex flex-wrap gap-2">
              {OPTIONS[field].map((opt) => {
                const arr = form[field] as string[];
                return (
                  <button
                    key={opt}
                    onClick={() => toggleMulti(field, opt)}
                    className={`px-3 py-2 rounded-lg text-sm border transition-colors ${
                      arr.includes(opt)
                        ? 'bg-apil-blue text-white border-apil-blue'
                        : 'bg-white text-apil-gray-700 border-apil-gray-200 hover:border-apil-blue'
                    }`}
                  >
                    {LABELS[opt] || opt}
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        <div className="pt-4">
          <button
            onClick={save}
            disabled={saving}
            className="bg-apil-blue text-white px-6 py-3 rounded-lg font-medium hover:bg-apil-blue/90 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </div>
    </div>
  );
}
