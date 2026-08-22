import { useState, useEffect, useCallback } from 'react';
import { formatAED } from './Shared';
import type { RentalOperatingCostContext, OperatingCostInputRequest, ServiceChargeContext } from '../data/api';

function formatAEDFull(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(n)) return 'N/A';
  return `AED ${n.toLocaleString()}`;
}

// Generate or retrieve a per-session user scope for input isolation.
// This is EPHEMERAL — stored in sessionStorage, disappears when tab closes.
function getSessionUserScope(): string {
  const KEY = 'apil_operating_cost_user_scope';
  let scope = sessionStorage.getItem(KEY);
  if (!scope) {
    scope = `session_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    sessionStorage.setItem(KEY, scope);
  }
  return scope;
}

interface OperatingCostsCardProps {
  propertyId: string;
  operatingCost: RentalOperatingCostContext | null | undefined;
  serviceCharge: ServiceChargeContext | null | undefined;
}

export function OperatingCostsCard({ propertyId, operatingCost, serviceCharge }: OperatingCostsCardProps) {
  const [vacancyMode, setVacancyMode] = useState<'VACANCY_PERCENT' | 'VACANCY_LOSS_AED' | ''>('');
  const [vacancyPercent, setVacancyPercent] = useState<string>('');
  const [vacancyLossAed, setVacancyLossAed] = useState<string>('');
  const [managementMode, setManagementMode] = useState<'USER_INPUT_FIXED_AED' | 'USER_INPUT_PERCENT' | 'SELF_MANAGED' | ''>('');
  const [managementAed, setManagementAed] = useState<string>('');
  const [managementPercent, setManagementPercent] = useState<string>('');
  const [maintenanceAed, setMaintenanceAed] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Sync local state from backend context (when inputs are already stored)
  useEffect(() => {
    if (!operatingCost) return;
    const v = operatingCost.vacancy;
    if (v?.input_mode) {
      setVacancyMode(v.input_mode);
      if (v.input_mode === 'VACANCY_PERCENT' && v.percent != null) setVacancyPercent(String(v.percent));
      if (v.input_mode === 'VACANCY_LOSS_AED' && v.loss_aed != null) setVacancyLossAed(String(v.loss_aed));
    }
    const m = operatingCost.management;
    if (m?.input_mode) {
      setManagementMode(m.input_mode);
      if (m.input_mode === 'USER_INPUT_FIXED_AED' && m.annual_cost_aed != null) setManagementAed(String(m.annual_cost_aed));
      if (m.input_mode === 'USER_INPUT_PERCENT' && m.percent != null) setManagementPercent(String(m.percent));
    }
    const mt = operatingCost.maintenance;
    if (mt?.annual_cost_aed != null) setMaintenanceAed(String(mt.annual_cost_aed));
  }, [operatingCost]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);

    const userScope = getSessionUserScope();
    const payload: OperatingCostInputRequest = { user_scope: userScope };

    if (vacancyMode) {
      payload.vacancy_input_mode = vacancyMode;
      if (vacancyMode === 'VACANCY_PERCENT') {
        payload.vacancy_percent = vacancyPercent ? parseFloat(vacancyPercent) : null;
      } else {
        payload.vacancy_loss_aed = vacancyLossAed ? parseFloat(vacancyLossAed) : null;
      }
    }

    if (managementMode) {
      payload.management_input_mode = managementMode;
      if (managementMode === 'USER_INPUT_FIXED_AED') {
        payload.management_annual_cost_aed = managementAed ? parseFloat(managementAed) : null;
      } else if (managementMode === 'USER_INPUT_PERCENT') {
        payload.management_percent = managementPercent ? parseFloat(managementPercent) : null;
      }
    }

    if (maintenanceAed) {
      payload.maintenance_annual_cost_aed = parseFloat(maintenanceAed);
    }

    try {
      const res = await fetch(`/properties/${propertyId}/operating-costs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.detail?.errors?.join('; ') || 'Validation error');
      } else {
        setSuccess('Saved. Calculations updated.');
        setTimeout(() => window.location.reload(), 500);
      }
    } catch (e) {
      setError('Network error');
    } finally {
      setSaving(false);
    }
  }, [propertyId, vacancyMode, vacancyPercent, vacancyLossAed, managementMode, managementAed, managementPercent, maintenanceAed]);

  const handleClear = useCallback(async () => {
    setSaving(true);
    setError(null);
    const userScope = getSessionUserScope();
    try {
      await fetch(`/properties/${propertyId}/operating-costs?user_scope=${encodeURIComponent(userScope)}`, { method: 'DELETE' });
      setVacancyMode(''); setVacancyPercent(''); setVacancyLossAed('');
      setManagementMode(''); setManagementAed(''); setManagementPercent('');
      setMaintenanceAed('');
      setSuccess('Cleared.');
      setTimeout(() => window.location.reload(), 500);
    } catch {
      setError('Network error');
    } finally {
      setSaving(false);
    }
  }, [propertyId]);

  if (!operatingCost) return null;

  const level = operatingCost.calculation_level;
  const isNetRental = level === 'NET_RENTAL';
  const isPartial = level === 'PARTIAL_OPERATING_COSTS';
  const hasAnyInput = operatingCost.vacancy?.status === 'AVAILABLE' ||
                      operatingCost.management?.status === 'AVAILABLE' ||
                      operatingCost.maintenance?.status === 'AVAILABLE';

  // Only show operating costs section if service charges are eligible
  // (Net Rental requires SC; partial can show without SC but we gate the whole section
  // on SC eligibility for V1 to keep the UI clean)
  const scEligible = serviceCharge?.production_eligible === true;

  return (
    <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
      <h2 className="text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-4">Operating Costs</h2>

      {/* ── Input Section ── */}
      <div className="space-y-4 mb-4">
        {/* Vacancy */}
        <div>
          <label className="text-xs font-semibold text-apil-gray-600 mb-1 block">Vacancy</label>
          <div className="flex flex-wrap gap-2 items-center">
            <select
              value={vacancyMode}
              onChange={(e) => setVacancyMode(e.target.value as any)}
              className="text-sm border border-apil-gray-200 rounded-lg px-2 py-1.5 bg-white"
            >
              <option value="">— Not entered —</option>
              <option value="VACANCY_PERCENT">Percentage (%)</option>
              <option value="VACANCY_LOSS_AED">AED / year</option>
            </select>
            {vacancyMode === 'VACANCY_PERCENT' && (
              <input
                type="number" min="0" max="100" step="0.1" placeholder="5.0"
                value={vacancyPercent}
                onChange={(e) => setVacancyPercent(e.target.value)}
                className="text-sm border border-apil-gray-200 rounded-lg px-2 py-1.5 w-24"
              />
            )}
            {vacancyMode === 'VACANCY_PERCENT' && <span className="text-sm text-apil-gray-400">%</span>}
            {vacancyMode === 'VACANCY_LOSS_AED' && (
              <input
                type="number" min="0" step="100" placeholder="8000"
                value={vacancyLossAed}
                onChange={(e) => setVacancyLossAed(e.target.value)}
                className="text-sm border border-apil-gray-200 rounded-lg px-2 py-1.5 w-32"
              />
            )}
            {vacancyMode === 'VACANCY_LOSS_AED' && <span className="text-sm text-apil-gray-400">AED/year</span>}
          </div>
          {operatingCost.vacancy?.status === 'AVAILABLE' && (
            <p className="text-[11px] text-apil-gray-400 mt-0.5">
              Source: {operatingCost.vacancy.source}
              {operatingCost.vacancy.loss_aed != null && ` · Loss: ${formatAEDFull(operatingCost.vacancy.loss_aed)}`}
            </p>
          )}
        </div>

        {/* Management */}
        <div>
          <label className="text-xs font-semibold text-apil-gray-600 mb-1 block">Property Management</label>
          <div className="flex flex-wrap gap-2 items-center">
            <select
              value={managementMode}
              onChange={(e) => setManagementMode(e.target.value as any)}
              className="text-sm border border-apil-gray-200 rounded-lg px-2 py-1.5 bg-white"
            >
              <option value="">— Not entered —</option>
              <option value="USER_INPUT_FIXED_AED">AED / year</option>
              <option value="USER_INPUT_PERCENT">% of effective rent</option>
              <option value="SELF_MANAGED">I will self-manage</option>
            </select>
            {managementMode === 'USER_INPUT_FIXED_AED' && (
              <input
                type="number" min="0" step="500" placeholder="12000"
                value={managementAed}
                onChange={(e) => setManagementAed(e.target.value)}
                className="text-sm border border-apil-gray-200 rounded-lg px-2 py-1.5 w-32"
              />
            )}
            {managementMode === 'USER_INPUT_FIXED_AED' && <span className="text-sm text-apil-gray-400">AED/year</span>}
            {managementMode === 'USER_INPUT_PERCENT' && (
              <input
                type="number" min="0" step="0.5" placeholder="8.0"
                value={managementPercent}
                onChange={(e) => setManagementPercent(e.target.value)}
                className="text-sm border border-apil-gray-200 rounded-lg px-2 py-1.5 w-24"
              />
            )}
            {managementMode === 'USER_INPUT_PERCENT' && <span className="text-sm text-apil-gray-400">% of effective rent</span>}
            {managementMode === 'SELF_MANAGED' && (
              <span className="text-sm text-apil-gray-400">Management cost = 0 (self-managed)</span>
            )}
          </div>
          {operatingCost.management?.status === 'AVAILABLE' && (
            <p className="text-[11px] text-apil-gray-400 mt-0.5">
              Source: {operatingCost.management.source}
              {operatingCost.management.annual_cost_aed != null && ` · Cost: ${formatAEDFull(operatingCost.management.annual_cost_aed)}`}
            </p>
          )}
        </div>

        {/* Maintenance */}
        <div>
          <label className="text-xs font-semibold text-apil-gray-600 mb-1 block">Unit Maintenance</label>
          <div className="flex flex-wrap gap-2 items-center">
            <input
              type="number" min="0" step="500" placeholder="5000"
              value={maintenanceAed}
              onChange={(e) => setMaintenanceAed(e.target.value)}
              className="text-sm border border-apil-gray-200 rounded-lg px-2 py-1.5 w-32"
            />
            <span className="text-sm text-apil-gray-400">AED/year</span>
          </div>
          {operatingCost.maintenance?.status === 'AVAILABLE' && (
            <p className="text-[11px] text-apil-gray-400 mt-0.5">
              Source: {operatingCost.maintenance.source}
              {operatingCost.maintenance.annual_cost_aed != null && ` · Cost: ${formatAEDFull(operatingCost.maintenance.annual_cost_aed)}`}
            </p>
          )}
        </div>
      </div>

      {/* Error / Success messages */}
      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
      {success && <p className="text-sm text-emerald-600 mb-2">{success}</p>}

      {/* Save / Clear buttons */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={handleSave}
          disabled={saving}
          className="text-sm bg-apil-blue text-white rounded-lg px-4 py-2 hover:bg-apil-blue-dark disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Inputs'}
        </button>
        {hasAnyInput && (
          <button
            onClick={handleClear}
            disabled={saving}
            className="text-sm border border-apil-gray-200 text-apil-gray-600 rounded-lg px-4 py-2 hover:bg-apil-gray-50 disabled:opacity-50"
          >
            Clear
          </button>
        )}
      </div>

      {/* ── Progressive Results ── */}
      {hasAnyInput && (
        <div className="mt-4 pt-4 border-t-2 border-apil-gray-100">
          {/* Partial: Income After Known Operating Costs */}
          {isPartial && operatingCost.known_operating_income_aed != null && (
            <div className="mb-3 p-3 bg-amber-50 rounded-xl">
              <p className="text-xs text-apil-gray-500 font-medium mb-1">Income After Known Operating Costs</p>
              <p className="text-xl font-bold text-amber-700">
                {formatAEDFull(operatingCost.known_operating_income_aed)} <span className="text-sm font-normal text-apil-gray-400">/ year</span>
              </p>
            </div>
          )}

          {/* Net Rental Income — only when ALL costs available */}
          {isNetRental && operatingCost.net_rental_income_aed != null && (
            <>
              <div className="mb-3 p-3 bg-emerald-50 rounded-xl">
                <p className="text-xs text-apil-gray-500 font-medium mb-1">Net Rental Income</p>
                <p className="text-xl font-bold text-emerald-700">
                  {formatAEDFull(operatingCost.net_rental_income_aed)} <span className="text-sm font-normal text-apil-gray-400">/ year</span>
                </p>
              </div>
              <div className="mb-4 p-3 bg-emerald-50 rounded-xl">
                <p className="text-xs text-apil-gray-500 font-medium mb-1">Net Rental Yield</p>
                <p className="text-xl font-bold text-emerald-700">
                  {operatingCost.net_rental_yield_pct != null ? `${operatingCost.net_rental_yield_pct}%` : 'N/A'}
                </p>
              </div>
            </>
          )}

          {/* Included / Not Included */}
          <div className="mb-3 p-3 bg-apil-gray-50 rounded-lg">
            {operatingCost.included_costs && operatingCost.included_costs.length > 0 && (
              <div className="mb-2">
                <p className="text-[11px] font-semibold text-apil-gray-500 mb-1">Included in this calculation:</p>
                <ul className="space-y-0.5">
                  {operatingCost.included_costs.map((cost, i) => (
                    <li key={i} className="text-[11px] text-apil-gray-600 flex items-start">
                      <span className="text-emerald-600 mr-1.5">✓</span> {cost}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {operatingCost.missing_costs && operatingCost.missing_costs.length > 0 && (
              <div>
                <p className="text-[11px] font-semibold text-apil-gray-500 mb-1">Not included:</p>
                <ul className="space-y-0.5">
                  {operatingCost.missing_costs.map((cost, i) => (
                    <li key={i} className="text-[11px] text-apil-gray-500 flex items-start">
                      <span className="text-apil-gray-400 mr-1.5">—</span> {cost}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Disclosures */}
          <p className="text-[11px] text-apil-gray-400 leading-relaxed mb-1">
            {operatingCost.disclosure}
          </p>
          {operatingCost.partial_disclosure && (
            <p className="text-[11px] text-amber-600 leading-relaxed">
              {operatingCost.partial_disclosure}
            </p>
          )}
        </div>
      )}

      {/* If no inputs entered yet, show a hint */}
      {!hasAnyInput && (
        <p className="text-[11px] text-apil-gray-400 leading-relaxed">
          Enter vacancy, property management, and maintenance costs above to calculate Net Rental Income.
          These values are based on your inputs only — they are not verified data.
        </p>
      )}

      {/* Ephemeral persistence disclosure */}
      <p className="text-[11px] text-apil-gray-400 leading-relaxed mt-3 pt-2 border-t border-apil-gray-100">
        Your operating-cost inputs are temporary and may not be available after the session ends.
      </p>
    </div>
  );
}
