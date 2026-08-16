import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api, investorSession } from '../data/api';
import type { PersonalizedProperty } from '../data/api';

const DECISION_BADGES: Record<string, string> = {
  STRONG_OPPORTUNITY: 'bg-emerald-100 text-emerald-800',
  OPPORTUNITY: 'bg-sky-100 text-sky-800',
  WATCH: 'bg-amber-100 text-amber-800',
  CAUTION: 'bg-orange-100 text-orange-800',
  AVOID: 'bg-red-100 text-red-800',
  INSUFFICIENT_EVIDENCE: 'bg-gray-100 text-gray-600',
};

const FIT_BADGES: Record<string, string> = {
  EXCELLENT_FIT: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  STRONG_FIT: 'bg-sky-50 text-sky-700 border-sky-200',
  MODERATE_FIT: 'bg-amber-50 text-amber-700 border-amber-200',
  WEAK_FIT: 'bg-orange-50 text-orange-700 border-orange-200',
  POOR_FIT: 'bg-red-50 text-red-700 border-red-200',
};

function PropertyCard({ property }: { property: PersonalizedProperty }) {
  const obj = property.objective_signal;
  const fit = property.investor_fit;
  const p = property.property;
  const adv = property.price_analysis.best_usable_advantage_pct;

  return (
    <div className="bg-white rounded-xl border border-apil-gray-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-semibold text-apil-gray-900">{p.name || 'Unnamed Property'}</h3>
          <p className="text-sm text-apil-gray-500">{p.area || 'Unknown Area'}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${DECISION_BADGES[obj.decision] || 'bg-gray-100'}`}>
          {obj.decision.replace('_', ' ')}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3 text-sm">
        <div>
          <span className="text-apil-gray-500">Price</span>
          <div className="font-semibold">{p.current_price_aed ? `AED ${p.current_price_aed.toLocaleString()}` : 'N/A'}</div>
        </div>
        <div>
          <span className="text-apil-gray-500">Developer</span>
          <div className="font-semibold">{property.developer.name} ({property.developer.grade})</div>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs text-apil-gray-500">Objective:</span>
        <span className="text-xs font-semibold text-apil-blue">{obj.confidence} confidence</span>
        {adv !== null && adv !== undefined && (
          <span className={`text-xs font-semibold ${adv >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
            {adv > 0 ? '+' : ''}{adv.toFixed(1)}%
          </span>
        )}
      </div>

      {fit && (
        <div className={`border rounded-lg p-3 mb-3 ${FIT_BADGES[fit.tier] || 'border-gray-200'}`}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase">Your Fit</span>
            <span className="text-lg font-bold">{fit.score}/100</span>
          </div>
          <div className="text-xs mt-1">{fit.tier.replace('_', ' ')}</div>
        </div>
      )}

      <Link
        to={`/property/${p.id}`}
        className="block w-full text-center bg-apil-blue text-white py-2 rounded-lg font-semibold text-sm hover:bg-apil-blue-dark transition-colors"
      >
        View Details →
      </Link>
    </div>
  );
}

export default function Marketplace() {
  const [properties, setProperties] = useState<PersonalizedProperty[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    decision: '',
    min_price: '',
    max_price: '',
    developer_grade: '',
    page: 1,
  });
  const [total, setTotal] = useState(0);
  const investorId = investorSession.getId();

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const params: Record<string, any> = { page: filters.page, per_page: 20 };
      if (filters.decision) params.decision = filters.decision;
      if (filters.min_price) params.min_price = parseInt(filters.min_price);
      if (filters.max_price) params.max_price = parseInt(filters.max_price);
      if (filters.developer_grade) params.developer_grade = filters.developer_grade;
      const res = await api.getOpportunities(params, investorId || undefined);
      setProperties(res.results);
      setTotal(res.total);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [filters.page, filters.decision]);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-apil-gray-900 mb-2">Investment Opportunities</h1>
        <p className="text-apil-gray-500">
          {investorId
            ? 'Personalized based on your investment profile. Objective decisions locked; fit scores personalize ranking within each tier.'
            : 'Default marketplace. Complete the questionnaire for personalized ranking.'}
        </p>
      </div>

      <div className="bg-white rounded-xl border border-apil-gray-200 p-4 mb-8 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs font-medium text-apil-gray-700 mb-1">Decision</label>
          <select
            value={filters.decision}
            onChange={e => setFilters(prev => ({ ...prev, decision: e.target.value, page: 1 }))}
            className="border border-apil-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All Opportunities</option>
            <option value="STRONG_OPPORTUNITY">Strong Opportunity</option>
            <option value="OPPORTUNITY">Opportunity</option>
            <option value="WATCH">Watch</option>
            <option value="CAUTION">Caution</option>
            <option value="AVOID">Avoid</option>
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-apil-gray-700 mb-1">Min Price</label>
          <input
            type="number"
            value={filters.min_price}
            onChange={e => setFilters(prev => ({ ...prev, min_price: e.target.value }))}
            placeholder="AED"
            className="border border-apil-gray-300 rounded-lg px-3 py-2 text-sm w-32"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-apil-gray-700 mb-1">Max Price</label>
          <input
            type="number"
            value={filters.max_price}
            onChange={e => setFilters(prev => ({ ...prev, max_price: e.target.value }))}
            placeholder="AED"
            className="border border-apil-gray-300 rounded-lg px-3 py-2 text-sm w-32"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-apil-gray-700 mb-1">Dev Grade</label>
          <select
            value={filters.developer_grade}
            onChange={e => setFilters(prev => ({ ...prev, developer_grade: e.target.value }))}
            className="border border-apil-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">Any</option>
            <option value="A">A</option>
            <option value="B">B</option>
            <option value="C">C</option>
          </select>
        </div>
        <button
          onClick={() => { setFilters(prev => ({ ...prev, page: 1 })); load(); }}
          className="bg-apil-blue text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-apil-blue-dark"
        >
          Apply Filters
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-6">{error}</div>
      )}

      {loading ? (
        <div className="text-center py-20 text-apil-gray-500">Loading opportunities...</div>
      ) : properties.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-4xl mb-4">🔍</div>
          <h3 className="text-lg font-semibold text-apil-gray-900 mb-2">No properties match your filters</h3>
          <p className="text-apil-gray-500 max-w-md mx-auto">
            Try relaxing your filters or completing the questionnaire so we can personalize recommendations.
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {properties.map(p => (
              <PropertyCard key={p.property.id} property={p} />
            ))}
          </div>

          <div className="flex justify-center gap-4 mt-10">
            <button
              onClick={() => setFilters(prev => ({ ...prev, page: Math.max(1, prev.page - 1) }))}
              disabled={filters.page <= 1}
              className="px-4 py-2 border border-apil-gray-300 rounded-lg disabled:opacity-50"
            >
              ← Prev
            </button>
            <span className="px-4 py-2 text-apil-gray-600">
              Page {filters.page} of {Math.ceil(total / 20)}
            </span>
            <button
              onClick={() => setFilters(prev => ({ ...prev, page: prev.page + 1 }))}
              disabled={filters.page >= Math.ceil(total / 20)}
              className="px-4 py-2 border border-apil-gray-300 rounded-lg disabled:opacity-50"
            >
              Next →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
