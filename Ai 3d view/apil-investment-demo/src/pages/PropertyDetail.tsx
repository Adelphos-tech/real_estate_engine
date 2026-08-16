import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, investorSession } from '../data/api';
import type { PersonalizedProperty } from '../data/api';

const DECISION_COLORS: Record<string, string> = {
  STRONG_OPPORTUNITY: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  OPPORTUNITY: 'text-sky-700 bg-sky-50 border-sky-200',
  WATCH: 'text-amber-700 bg-amber-50 border-amber-200',
  CAUTION: 'text-orange-700 bg-orange-50 border-orange-200',
  AVOID: 'text-red-700 bg-red-50 border-red-200',
  INSUFFICIENT_EVIDENCE: 'text-gray-600 bg-gray-50 border-gray-200',
};

export default function PropertyDetail() {
  const { propertyId } = useParams();
  const [property, setProperty] = useState<PersonalizedProperty | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const investorId = investorSession.getId();

  useEffect(() => {
    if (!propertyId) return;
    api.getProperty(propertyId, investorId || undefined)
      .then(setProperty)
      .catch((e: any) => setError(e.message))
      .finally(() => setLoading(false));
  }, [propertyId]);

  if (loading) return <div className="text-center py-20">Loading property...</div>;
  if (error) return <div className="text-center py-20 text-red-600">{error}</div>;
  if (!property) return <div className="text-center py-20">Property not found</div>;

  const p = property.property;
  const dev = property.developer;
  const obj = property.objective_signal;
  const fit = property.investor_fit;
  const pa = property.price_analysis;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Link to="/marketplace" className="text-sm text-apil-blue hover:underline mb-4 inline-block">← Back to Marketplace</Link>

      <div className="bg-white rounded-xl border border-apil-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-apil-gray-900">{p.name || 'Unnamed Property'}</h1>
            <p className="text-apil-gray-500">{p.area || 'Unknown Area'} {p.sub_project ? `| ${p.sub_project}` : ''}</p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-apil-gray-900">{p.current_price_aed ? `AED ${p.current_price_aed.toLocaleString()}` : 'N/A'}</div>
            {p.size_sqm && <div className="text-sm text-apil-gray-500">{p.size_sqm} sqm</div>}
          </div>
        </div>

        {/* OBJECTIVE SIGNAL */}
        <div className={`border-2 rounded-xl p-5 mb-6 ${DECISION_COLORS[obj.decision] || ''}`}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-bold">Investment Signal</h2>
            <span className="px-3 py-1 rounded-full text-xs font-bold uppercase bg-white/80">
              {obj.confidence} confidence
            </span>
          </div>
          <div className="text-3xl font-bold mb-2">{obj.decision.replace('_', ' ')}</div>
          <p className="text-sm mb-3">{obj.reason}</p>
          {obj.warnings.length > 0 && (
            <div className="bg-white/60 rounded-lg p-3 text-sm">
              <div className="font-semibold mb-1">⚠️ Warnings</div>
              <ul className="list-disc list-inside space-y-1">
                {obj.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
        </div>

        {/* INVESTOR FIT */}
        {fit && (
          <div className="bg-gradient-to-r from-apil-blue/5 to-sky-50 border border-apil-blue/20 rounded-xl p-5 mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-bold text-apil-gray-900">Your Fit</h2>
              <div className="text-right">
                <div className="text-3xl font-bold text-apil-blue">{fit.score}/100</div>
                <div className="text-sm text-apil-gray-600">{fit.tier.replace('_', ' ')}</div>
              </div>
            </div>
            <p className="text-sm text-apil-gray-700 mb-3">{property.combined_explanation}</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
              <div className="bg-white rounded-lg p-3">
                <div className="font-semibold text-emerald-700 mb-1">✓ Matched ({fit.matched_preferences.length})</div>
                <div className="text-apil-gray-600">{fit.matched_preferences.join(', ')}</div>
              </div>
              <div className="bg-white rounded-lg p-3">
                <div className="font-semibold text-red-700 mb-1">✗ Unmatched ({fit.unmatched_preferences.length})</div>
                <div className="text-apil-gray-600">{fit.unmatched_preferences.join(', ') || 'None'}</div>
              </div>
              <div className="bg-white rounded-lg p-3">
                <div className="font-semibold text-apil-gray-500 mb-1">? Unknown ({fit.unknown_preferences.length})</div>
                <div className="text-apil-gray-600">{fit.unknown_preferences.join(', ') || 'None'}</div>
              </div>
            </div>
          </div>
        )}

        {/* BENCHMARKS */}
        <div className="mb-6">
          <h3 className="font-bold text-apil-gray-900 mb-3">DLD Benchmark Evidence</h3>
          {property.benchmarks.length === 0 ? (
            <div className="text-apil-gray-500 text-sm">No benchmark data available</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-apil-gray-200">
                    <th className="text-left py-2 px-3 text-apil-gray-500">Type</th>
                    <th className="text-left py-2 px-3 text-apil-gray-500">Median</th>
                    <th className="text-left py-2 px-3 text-apil-gray-500">N</th>
                    <th className="text-left py-2 px-3 text-apil-gray-500">Match</th>
                    <th className="text-left py-2 px-3 text-apil-gray-500">Confidence</th>
                    <th className="text-left py-2 px-3 text-apil-gray-500">Advantage</th>
                  </tr>
                </thead>
                <tbody>
                  {property.benchmarks.map((b, i) => (
                    <tr key={i} className="border-b border-apil-gray-100">
                      <td className="py-2 px-3 font-medium">{b.type.replace('_', ' ')}</td>
                      <td className="py-2 px-3">{b.median_price_aed ? `AED ${b.median_price_aed.toLocaleString()}` : 'N/A'}</td>
                      <td className="py-2 px-3">{b.transaction_count}</td>
                      <td className="py-2 px-3">{b.match_level}</td>
                      <td className="py-2 px-3">
                        <span className={`px-2 py-0.5 rounded text-xs ${b.confidence === 'High' ? 'bg-emerald-100 text-emerald-700' : b.confidence === 'Medium' ? 'bg-sky-100 text-sky-700' : 'bg-gray-100 text-gray-600'}`}>
                          {b.confidence}
                        </span>
                      </td>
                      <td className="py-2 px-3">
                        {b.price_advantage_pct !== null && b.price_advantage_pct !== undefined ? (
                          <span className={`font-semibold ${b.price_advantage_pct >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                            {b.price_advantage_pct > 0 ? '+' : ''}{b.price_advantage_pct.toFixed(1)}%
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
        </div>

        {/* DEVELOPER */}
        <div className="bg-apil-gray-50 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-bold text-apil-gray-900">{dev.name}</h3>
              <p className="text-sm text-apil-gray-600">{dev.grade_explanation}</p>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-apil-gray-900">Grade {dev.grade}</div>
              <div className="text-sm text-apil-gray-500">{dev.quality_tier}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
