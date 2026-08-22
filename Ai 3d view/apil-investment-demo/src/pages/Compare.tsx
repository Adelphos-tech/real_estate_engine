import { useState } from 'react';
import { Link } from 'react-router-dom';
import { api, investorSession } from '../data/api';
import type { PersonalizedProperty } from '../data/api';

const DECISION_COLORS: Record<string, string> = {
  STRONG_OPPORTUNITY: 'bg-emerald-50 border-emerald-200 text-emerald-700',
  OPPORTUNITY: 'bg-sky-50 border-sky-200 text-sky-700',
  WATCH: 'bg-amber-50 border-amber-200 text-amber-700',
  CAUTION: 'bg-orange-50 border-orange-200 text-orange-700',
  AVOID: 'bg-red-50 border-red-200 text-red-700',
  INSUFFICIENT_EVIDENCE: 'bg-gray-50 border-gray-200 text-gray-600',
};

export default function Compare() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [properties, setProperties] = useState<PersonalizedProperty[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const investorId = investorSession.getId();

  const addProperty = async (id: string) => {
    if (selectedIds.includes(id) || selectedIds.length >= 3) return;
    setSelectedIds(prev => [...prev, id]);
    setLoading(true);
    setError('');
    try {
      const p = await api.getProperty(id, investorId || undefined);
      if (p) setProperties(prev => [...prev, p]);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const removeProperty = (id: string) => {
    setSelectedIds(prev => prev.filter(x => x !== id));
    setProperties(prev => prev.filter(x => x.property.id !== id));
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <Link to="/marketplace" className="text-sm text-apil-blue hover:underline mb-2 inline-block">← Back to Marketplace</Link>
        <h1 className="text-2xl font-bold text-apil-gray-900">Compare Properties</h1>
        <p className="text-apil-gray-500">Select up to 3 properties to compare side-by-side</p>
      </div>

      {/* Add Property Bar */}
      <div className="bg-white rounded-xl border border-apil-gray-200 p-4 mb-6 flex gap-2">
        <input
          type="text"
          placeholder="Enter Property ID (e.g. 6749)"
          className="flex-1 rounded-lg border border-apil-gray-200 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-apil-blue"
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              const v = (e.target as HTMLInputElement).value.trim();
              if (v) addProperty(v);
              (e.target as HTMLInputElement).value = '';
            }
          }}
        />
        <button
          className="bg-apil-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-apil-blue/90 disabled:opacity-50"
          disabled={loading}
          onClick={() => {
            const input = document.querySelector('input') as HTMLInputElement;
            const v = input?.value.trim();
            if (v) { addProperty(v); input.value = ''; }
          }}
        >
          Add to Compare
        </button>
      </div>

      {error && <div className="text-red-600 mb-4 text-sm">{error}</div>}

      {properties.length === 0 ? (
        <div className="text-center py-20 text-apil-gray-500 bg-white rounded-xl border border-dashed border-apil-gray-200">
          <div className="text-4xl mb-4">📊</div>
          <div className="text-lg font-medium text-apil-gray-700 mb-1">No properties selected</div>
          <div className="text-sm">Enter property IDs above to start comparing</div>
        </div>
      ) : (
        <div className={`grid gap-4 ${properties.length === 2 ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3'}`}>
          {properties.map((item) => {
            const p = item.property;
            const obj = item.objective_signal;
            const fit = item.investor_fit;
            const dev = item.developer;

            return (
              <div key={p.id} className="bg-white rounded-xl border border-apil-gray-200 overflow-hidden">
                <div className="p-4 border-b border-apil-gray-100 flex justify-between items-start">
                  <div>
                    <h3 className="font-bold text-apil-gray-900">{p.name || 'Unnamed'}</h3>
                    <p className="text-sm text-apil-gray-500">{p.area || 'Unknown Area'}</p>
                  </div>
                  <button onClick={() => removeProperty(p.id)} className="text-apil-gray-400 hover:text-red-500 text-sm">✕</button>
                </div>

                <div className="p-4 space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-apil-gray-500">Price</span>
                    <span className="font-bold text-apil-gray-900">{p.current_price_aed ? `AED ${p.current_price_aed.toLocaleString()}` : 'N/A'}</span>
                  </div>

                  <div className={`border-2 rounded-lg p-3 ${DECISION_COLORS[obj.decision] || ''}`}>
                    <div className="font-bold">{obj.decision.replace('_', ' ')}</div>
                    <div className="text-xs">{obj.confidence} confidence</div>
                  </div>

                  {fit && (
                    <div className="bg-gradient-to-r from-apil-blue/5 to-sky-50 border border-apil-blue/20 rounded-lg p-3">
                      <div className="flex justify-between">
                        <span className="text-sm font-medium">Your Fit</span>
                        <span className="font-bold text-apil-blue">{fit.score}/100</span>
                      </div>
                      <div className="text-xs text-apil-gray-600">{fit.tier.replace('_', ' ')}</div>
                    </div>
                  )}

                  <div className="text-sm">
                    <div className="text-apil-gray-500 mb-1">Developer</div>
                    <div className="font-medium">{dev.name}</div>
                    <div className="text-apil-gray-500">Grade {dev.grade} · {dev.quality_tier}</div>
                  </div>

                  {item.benchmarks.length > 0 && (
                    <div className="text-sm">
                      <div className="text-apil-gray-500 mb-1">Best Usable Advantage</div>
                      <div className="font-medium">
                        {item.price_analysis.best_usable_advantage_pct !== null
                          ? `${item.price_analysis.best_usable_advantage_pct > 0 ? '+' : ''}${item.price_analysis.best_usable_advantage_pct.toFixed(1)}%`
                          : 'N/A'}
                      </div>
                    </div>
                  )}

                  <div className="text-sm">
                    <div className="text-apil-gray-500 mb-1">Evidence Strength</div>
                    <div className="font-medium">{item.price_analysis.evidence_strength || 'N/A'}</div>
                  </div>

                  {/* Property details from enrichment */}
                  {item.enrichment?.enrichment_status === 'CONFIRMED' ? (
                    <div className="text-sm space-y-2">
                      <div className="text-apil-gray-500 mb-1">Property Details (confirmed)</div>
                      <div className="font-medium">{item.enrichment.property_attributes.category || 'N/A'}</div>
                      <div className="font-medium">
                        {item.enrichment.property_attributes.bedrooms !== undefined
                          ? `${item.enrichment.property_attributes.bedrooms} bed`
                          : 'Bedrooms unavailable'}
                        {' · '}
                        {item.enrichment.property_attributes.bathrooms !== undefined
                          ? `${item.enrichment.property_attributes.bathrooms} bath`
                          : 'Bathrooms unavailable'}
                      </div>
                      <div className="font-medium">
                        {item.enrichment.property_attributes.size_sqm
                          ? `${item.enrichment.property_attributes.size_sqm} sqm`
                          : 'Size unavailable'}
                      </div>
                      <div className="font-medium">{item.enrichment.property_attributes.status || 'Status unavailable'}</div>
                    </div>
                  ) : (
                    <div className="text-sm">
                      <div className="text-apil-gray-500 mb-1">Property Details</div>
                      <div className="font-medium text-apil-gray-400">Not confirmed from listing data</div>
                    </div>
                  )}

                  <Link
                    to={`/property/${p.id}`}
                    className="block text-center bg-apil-blue text-white text-sm font-medium py-2 rounded-lg hover:bg-apil-blue/90"
                  >
                    View Full Details
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
