import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, investorSession } from '../data/api';
import type { QuestionnaireAnswers } from '../data/api';

const STEPS = [
  { id: 'objective', title: 'Investment Objective', question: 'What is your primary investment objective?' },
  { id: 'budget', title: 'Budget', question: 'What is your investment budget range (AED)?' },
  { id: 'horizon', title: 'Investment Holding Period', question: 'How long do you plan to hold this property investment?' },
  { id: 'risk', title: 'Risk Tolerance', question: 'What is your risk tolerance?' },
  { id: 'property', title: 'Property Preferences', question: 'What kind of property are you looking for?' },
  { id: 'location', title: 'Location', question: 'Which areas interest you?' },
];

export default function Questionnaire() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [answers, setAnswers] = useState<QuestionnaireAnswers>({
    investment_objective: 'BALANCED',
    budget_min_aed: 1000000,
    budget_max_aed: 3000000,
    horizon: '5_10_YEARS',
    investment_horizon_years: 5,
    risk_tolerance: 'MODERATE',
    property_status: ['EITHER'],
    property_types: ['APARTMENT'],
    bedrooms: ['2', '3'],
    locations: ['DUBAI_WIDE'],
  });
  const [customHorizon, setCustomHorizon] = useState<string>('');
  const [showCustomHorizon, setShowCustomHorizon] = useState(false);

  const update = (key: string, value: any) => setAnswers(prev => ({ ...prev, [key]: value }));

  const toggleMulti = (key: string, value: string) => {
    setAnswers(prev => {
      const arr = prev[key] || [];
      if (arr.includes(value)) return { ...prev, [key]: arr.filter((v: string) => v !== value) };
      return { ...prev, [key]: [...arr, value] };
    });
  };

  const submit = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.createInvestor(answers);
      investorSession.setId(res.investor_id);
      navigate('/marketplace');
    } catch (e: any) {
      setError(e.message || 'Failed to create profile');
      setLoading(false);
    }
  };

  const renderStep = () => {
    switch (step) {
      case 0:
        return (
          <div className="space-y-4">
            {[
              { value: 'CAPITAL_APPRECIATION', label: 'Capital appreciation' },
              { value: 'RENTAL_INCOME', label: 'Rental income' },
              { value: 'BALANCED', label: 'Balanced growth + income' },
              { value: 'SHORT_TERM_FLIP', label: 'Short-term resale / flip' },
            ].map(opt => (
              <button key={opt.value} onClick={() => { update('investment_objective', opt.value); setStep(1); }}
                className={`w-full text-left p-4 rounded-xl border-2 transition-all ${answers.investment_objective === opt.value ? 'border-apil-blue bg-apil-blue/5' : 'border-apil-gray-200 hover:border-apil-gray-300'}`}>
                <div className="font-semibold">{opt.label}</div>
              </button>
            ))}
          </div>
        );
      case 1:
        return (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-apil-gray-700 mb-2">Minimum Budget (AED)</label>
              <input type="range" min="500000" max="10000000" step="500000" value={answers.budget_min_aed}
                onChange={e => update('budget_min_aed', parseInt(e.target.value))}
                className="w-full accent-apil-blue" />
              <div className="text-center font-semibold text-apil-blue">AED {answers.budget_min_aed.toLocaleString()}</div>
            </div>
            <div>
              <label className="block text-sm font-medium text-apil-gray-700 mb-2">Maximum Budget (AED)</label>
              <input type="range" min="1000000" max="50000000" step="500000" value={answers.budget_max_aed}
                onChange={e => update('budget_max_aed', parseInt(e.target.value))}
                className="w-full accent-apil-blue" />
              <div className="text-center font-semibold text-apil-blue">AED {answers.budget_max_aed.toLocaleString()}</div>
            </div>
            <button onClick={() => setStep(2)} className="w-full bg-apil-blue text-white py-3 rounded-xl font-semibold hover:bg-apil-blue-dark">Continue</button>
          </div>
        );
      case 2:
        return (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {[1, 2, 3, 4, 5].map(years => (
                <button key={years} onClick={() => {
                  update('investment_horizon_years', years);
                  update('horizon', years <= 2 ? 'LT_2_YEARS' : years <= 5 ? '2_5_YEARS' : '5_10_YEARS');
                  setShowCustomHorizon(false);
                  setStep(3);
                }}
                  className={`px-5 py-3 rounded-xl border-2 text-sm font-semibold transition-all ${answers.investment_horizon_years === years && !showCustomHorizon ? 'border-apil-blue bg-apil-blue/5 text-apil-blue' : 'border-apil-gray-200 text-apil-gray-600 hover:border-apil-gray-300'}`}>
                  {years} year{years > 1 ? 's' : ''}
                </button>
              ))}
              <button onClick={() => setShowCustomHorizon(true)}
                className={`px-5 py-3 rounded-xl border-2 text-sm font-semibold transition-all ${showCustomHorizon ? 'border-apil-blue bg-apil-blue/5 text-apil-blue' : 'border-apil-gray-200 text-apil-gray-600 hover:border-apil-gray-300'}`}>
                Custom
              </button>
            </div>
            {showCustomHorizon && (
              <div className="animate-fade-in">
                <label className="block text-sm font-medium text-apil-gray-700 mb-2">Holding period in years</label>
                <div className="flex flex-wrap gap-2 items-center">
                  <input type="number" min="0" step="0.5" placeholder="e.g. 1.5, 2.5, 6, 7.5"
                    value={customHorizon}
                    onChange={e => setCustomHorizon(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && customHorizon && parseFloat(customHorizon) > 0) {
                        const val = parseFloat(customHorizon);
                        update('investment_horizon_years', val);
                        update('horizon', val <= 2 ? 'LT_2_YEARS' : val <= 5 ? '2_5_YEARS' : '5_10_YEARS');
                        setStep(3);
                      }
                    }}
                    className="text-sm border border-apil-gray-200 rounded-lg px-3 py-2 w-48 bg-white" />
                  <span className="text-sm text-apil-gray-400">years</span>
                  <button onClick={() => {
                    if (customHorizon && parseFloat(customHorizon) > 0) {
                      const val = parseFloat(customHorizon);
                      update('investment_horizon_years', val);
                      update('horizon', val <= 2 ? 'LT_2_YEARS' : val <= 5 ? '2_5_YEARS' : '5_10_YEARS');
                      setStep(3);
                    }
                  }}
                    className="bg-apil-blue text-white rounded-lg px-4 py-2 text-sm font-semibold hover:bg-apil-blue-dark disabled:opacity-50"
                    disabled={!customHorizon || parseFloat(customHorizon) <= 0}>
                    Continue
                  </button>
                </div>
                <p className="text-xs text-apil-gray-400 mt-1">Positive decimal values allowed (e.g. 1.5, 2.5, 6, 7.5 years).</p>
              </div>
            )}
          </div>
        );
      case 3:
        return (
          <div className="space-y-4">
            {[
              { value: 'CONSERVATIVE', label: 'Conservative', desc: 'Prefer lower risk, established developers, ready properties' },
              { value: 'MODERATE', label: 'Moderate', desc: 'Balanced approach, willing to take some risk for better returns' },
              { value: 'AGGRESSIVE', label: 'Aggressive', desc: 'Higher risk tolerance, seeking maximum upside' },
            ].map(opt => (
              <button key={opt.value} onClick={() => { update('risk_tolerance', opt.value); setStep(4); }}
                className={`w-full text-left p-4 rounded-xl border-2 transition-all ${answers.risk_tolerance === opt.value ? 'border-apil-blue bg-apil-blue/5' : 'border-apil-gray-200 hover:border-apil-gray-300'}`}>
                <div className="font-semibold">{opt.label}</div>
                <div className="text-sm text-apil-gray-500">{opt.desc}</div>
              </button>
            ))}
          </div>
        );
      case 4:
        return (
          <div className="space-y-6">
            <div>
              <p className="font-medium text-apil-gray-700 mb-2">Property Status</p>
              <div className="flex flex-wrap gap-2">
                {['OFFPLAN', 'READY', 'EITHER'].map(v => (
                  <button key={v} onClick={() => toggleMulti('property_status', v)}
                    className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-all ${answers.property_status?.includes(v) ? 'border-apil-blue bg-apil-blue/5 text-apil-blue' : 'border-apil-gray-200 text-apil-gray-600'}`}>
                    {v === 'OFFPLAN' ? 'Off-plan' : v === 'READY' ? 'Ready' : 'Either'}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="font-medium text-apil-gray-700 mb-2">Property Type</p>
              <div className="flex flex-wrap gap-2">
                {['APARTMENT', 'VILLA', 'TOWNHOUSE', 'PENTHOUSE', 'ANY'].map(v => (
                  <button key={v} onClick={() => toggleMulti('property_types', v)}
                    className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-all capitalize ${answers.property_types?.includes(v) ? 'border-apil-blue bg-apil-blue/5 text-apil-blue' : 'border-apil-gray-200 text-apil-gray-600'}`}>
                    {v.toLowerCase()}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="font-medium text-apil-gray-700 mb-2">Bedrooms</p>
              <div className="flex flex-wrap gap-2">
                {['STUDIO', '1', '2', '3', '4+', 'ANY'].map(v => (
                  <button key={v} onClick={() => toggleMulti('bedrooms', v)}
                    className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-all ${answers.bedrooms?.includes(v) ? 'border-apil-blue bg-apil-blue/5 text-apil-blue' : 'border-apil-gray-200 text-apil-gray-600'}`}>
                    {v === 'STUDIO' ? 'Studio' : v === '4+' ? '4+' : `${v} BR`}
                  </button>
                ))}
              </div>
            </div>
            <button onClick={() => setStep(5)} className="w-full bg-apil-blue text-white py-3 rounded-xl font-semibold hover:bg-apil-blue-dark">Continue</button>
          </div>
        );
      case 5:
        return (
          <div className="space-y-4">
            <p className="text-sm text-apil-gray-500">Select all that apply, or choose "Dubai-wide" for no preference.</p>
            <div className="flex flex-wrap gap-2">
              {['DUBAI_WIDE', 'Dubai Hills Estate', 'Jumeirah Village Circle', 'Business Bay', 'Palm Jumeirah', 'Downtown Dubai', 'Dubai Marina', 'Damac Hills'].map(v => (
                <button key={v} onClick={() => toggleMulti('locations', v)}
                  className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-all ${answers.locations?.includes(v) ? 'border-apil-blue bg-apil-blue/5 text-apil-blue' : 'border-apil-gray-200 text-apil-gray-600'}`}>
                  {v}
                </button>
              ))}
            </div>
            <button onClick={submit} disabled={loading}
              className="w-full bg-emerald-500 text-white py-4 rounded-xl font-bold text-lg hover:bg-emerald-400 disabled:opacity-50">
              {loading ? 'Creating Your Profile...' : 'Create My Investment Profile →'}
            </button>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="max-w-xl mx-auto px-4 py-12">
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-apil-gray-900">{STEPS[step]?.title}</h1>
          <span className="text-sm text-apil-gray-500">{step + 1} / {STEPS.length}</span>
        </div>
        <div className="w-full bg-apil-gray-200 rounded-full h-2">
          <div className="bg-apil-blue h-2 rounded-full transition-all" style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} />
        </div>
        <p className="text-apil-gray-600 mt-4">{STEPS[step]?.question}</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-6">{error}</div>
      )}

      <div className="animate-fade-in">{renderStep()}</div>

      {step > 0 && (
        <button onClick={() => setStep(s => s - 1)} className="mt-6 text-sm text-apil-gray-500 hover:text-apil-blue">
          ← Back
        </button>
      )}
    </div>
  );
}
