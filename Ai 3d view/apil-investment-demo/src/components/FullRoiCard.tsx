import { useState, useEffect, useCallback } from 'react';
import { formatAED } from './Shared';
import type {
  AcquisitionCostContext,
  RoiScenarioContext,
  FullRoiContext,
  RentalOperatingCostContext,
  ServiceChargeContext,
  RentalContext,
  AcquisitionCostInputRequest,
  RoiScenarioInputRequest,
} from '../data/api';
import { api } from '../data/api';

function formatAEDFull(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(n)) return 'N/A';
  return `AED ${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatAEDShort(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(n)) return 'N/A';
  const abs = Math.abs(n);
  const sign = n < 0 ? '-' : '';
  if (abs >= 1_000_000) return `AED ${sign}${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `AED ${sign}${(abs / 1_000).toFixed(0)}K`;
  return `AED ${n.toLocaleString()}`;
}

function getSessionUserScope(): string {
  const KEY = 'apil_roi_user_scope';
  let scope = sessionStorage.getItem(KEY);
  if (!scope) {
    scope = `roi_session_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    sessionStorage.setItem(KEY, scope);
  }
  return scope;
}

interface FullRoiCardProps {
  propertyId: string;
  purchasePrice: number | null;
  acquisitionCost: AcquisitionCostContext | null | undefined;
  roiScenario: RoiScenarioContext | null | undefined;
  fullRoi: FullRoiContext | null | undefined;
  operatingCost: RentalOperatingCostContext | null | undefined;
  serviceCharge: ServiceChargeContext | null | undefined;
  rentalContext: RentalContext | null | undefined;
  unitStatus: string | null | undefined;
}

export function FullRoiCard({
  propertyId,
  purchasePrice,
  acquisitionCost,
  roiScenario,
  fullRoi,
  operatingCost,
  serviceCharge,
  rentalContext,
  unitStatus,
}: FullRoiCardProps) {
  // ── Acquisition cost input state ──
  const [dldMode, setDldMode] = useState<string>('');
  const [dldCustomPercent, setDldCustomPercent] = useState<string>('');
  const [dldCustomAed, setDldCustomAed] = useState<string>('');
  const [trusteeFee, setTrusteeFee] = useState<string>('');
  const [brokerMode, setBrokerMode] = useState<string>('');
  const [brokerPercent, setBrokerPercent] = useState<string>('');
  const [brokerAed, setBrokerAed] = useState<string>('');
  const [devAdminMode, setDevAdminMode] = useState<string>('');
  const [devAdminAed, setDevAdminAed] = useState<string>('');

  // ── Scenario input state ──
  const [holdingMonths, setHoldingMonths] = useState<string>('');
  const [exitMode, setExitMode] = useState<string>('');
  const [exitPrice, setExitPrice] = useState<string>('');
  const [appreciationRate, setAppreciationRate] = useState<string>('');
  const [sellingBrokerMode, setSellingBrokerMode] = useState<string>('');
  const [sellingBrokerPercent, setSellingBrokerPercent] = useState<string>('');
  const [sellingBrokerAed, setSellingBrokerAed] = useState<string>('');
  const [nocMode, setNocMode] = useState<string>('');
  const [nocFee, setNocFee] = useState<string>('');
  const [otherSellingMode, setOtherSellingMode] = useState<string>('');
  const [otherSellingAed, setOtherSellingAed] = useState<string>('');

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const isOffplan = unitStatus && unitStatus.toLowerCase() === 'offplan';
  const isReady = unitStatus && unitStatus.toLowerCase() === 'ready';
  const scEligible = serviceCharge?.production_eligible === true;
  const roiStatus = fullRoi?.calculation_status || 'INCOMPLETE';
  const isCalculated = roiStatus === 'CALCULATED';

  // ── ROI UI VISIBILITY RULE ──
  // Show Full Property ROI UI only when the property has the minimum
  // verified evidence needed to support the ROI workflow:
  //   1. property_status = Ready
  //   2. verified production-eligible service charge exists
  //   3. rental_operating_cost_context can potentially reach NET_RENTAL
  //      (requires SC eligible — NET_RENTAL needs service charges)
  // If any prerequisite fails → HIDE the entire section.
  // No reliable data = no customer-facing section.
  const roiUiVisible = isReady && scEligible;

  // ── Sync acquisition inputs from backend context ──
  useEffect(() => {
    if (!acquisitionCost) return;
    const dld = acquisitionCost.dld_transfer;
    if (dld?.input_mode) {
      setDldMode(dld.input_mode);
      if (dld.input_mode === 'USE_CUSTOM_BUYER_PERCENT' && dld.actual_buyer_rate_pct != null) {
        setDldCustomPercent(String(dld.actual_buyer_rate_pct));
      }
    }
    if (acquisitionCost.trustee_office_fee?.amount_aed != null) {
      setTrusteeFee(String(acquisitionCost.trustee_office_fee.amount_aed));
    }
    const bp = acquisitionCost.broker_purchase;
    if (bp?.input_mode) {
      setBrokerMode(bp.input_mode);
      if (bp.input_mode === 'BROKER_PERCENT' && bp.amount_aed != null && purchasePrice) {
        setBrokerPercent(String((bp.amount_aed / purchasePrice) * 100));
      }
      if (bp.input_mode === 'BROKER_FIXED_AED' && bp.amount_aed != null) {
        setBrokerAed(String(bp.amount_aed));
      }
    }
    const da = acquisitionCost.developer_admin;
    if (da?.input_mode) {
      setDevAdminMode(da.input_mode);
      if (da.input_mode === 'DEVELOPER_ADMIN_FEE_AED' && da.amount_aed != null) {
        setDevAdminAed(String(da.amount_aed));
      }
    }
  }, [acquisitionCost, purchasePrice]);

  // ── Sync scenario inputs from backend context ──
  useEffect(() => {
    if (!roiScenario) return;
    const hp = roiScenario.holding_period;
    if (hp?.months != null) setHoldingMonths(String(hp.months));
    const ev = roiScenario.exit_value;
    if (ev?.mode) {
      setExitMode(ev.mode);
      if (ev.mode === 'USER_EXIT_PRICE' && ev.exit_sale_price_aed != null) {
        setExitPrice(String(ev.exit_sale_price_aed));
      }
      if (ev.mode === 'USER_APPRECIATION_RATE' && ev.annual_appreciation_rate_pct != null) {
        setAppreciationRate(String(ev.annual_appreciation_rate_pct));
      }
    }
    const sc = roiScenario.selling_costs;
    if (sc?.broker?.input_mode) {
      setSellingBrokerMode(sc.broker.input_mode);
      if (sc.broker.input_mode === 'SELLING_BROKER_PERCENT' && sc.broker.amount_aed != null && ev?.exit_sale_price_aed) {
        setSellingBrokerPercent(String((sc.broker.amount_aed / ev.exit_sale_price_aed) * 100));
      }
      if (sc.broker.input_mode === 'SELLING_BROKER_FIXED_AED' && sc.broker.amount_aed != null) {
        setSellingBrokerAed(String(sc.broker.amount_aed));
      }
    }
    if (sc?.noc?.input_mode) {
      setNocMode(sc.noc.input_mode);
      if (sc.noc.input_mode === 'NOC_FIXED_AED' && sc.noc.amount_aed != null) {
        setNocFee(String(sc.noc.amount_aed));
      }
    }
    if (sc?.other?.input_mode) {
      setOtherSellingMode(sc.other.input_mode);
      if (sc.other.input_mode === 'OTHER_SELLING_COSTS_AED' && sc.other.amount_aed != null) {
        setOtherSellingAed(String(sc.other.amount_aed));
      }
    }
  }, [roiScenario]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    const userScope = getSessionUserScope();

    try {
      // Save acquisition costs
      const acqPayload: AcquisitionCostInputRequest = { user_scope: userScope };
      if (dldMode) {
        acqPayload.dld_input_mode = dldMode;
        if (dldMode === 'USE_CUSTOM_BUYER_PERCENT' && dldCustomPercent) {
          acqPayload.dld_custom_percent = parseFloat(dldCustomPercent);
        }
        if (dldMode === 'USE_CUSTOM_BUYER_AED' && dldCustomAed) {
          acqPayload.dld_custom_aed = parseFloat(dldCustomAed);
        }
      }
      if (trusteeFee) acqPayload.trustee_fee_aed = parseFloat(trusteeFee);
      if (brokerMode) {
        acqPayload.broker_purchase_mode = brokerMode;
        if (brokerMode === 'BROKER_PERCENT' && brokerPercent) acqPayload.broker_purchase_percent = parseFloat(brokerPercent);
        if (brokerMode === 'BROKER_FIXED_AED' && brokerAed) acqPayload.broker_purchase_aed = parseFloat(brokerAed);
      }
      if (devAdminMode) {
        acqPayload.developer_admin_mode = devAdminMode;
        if (devAdminMode === 'DEVELOPER_ADMIN_FEE_AED' && devAdminAed) acqPayload.developer_admin_fee_aed = parseFloat(devAdminAed);
      }
      await api.saveAcquisitionCosts(propertyId, acqPayload);

      // Save scenario
      const scnPayload: RoiScenarioInputRequest = { user_scope: userScope };
      if (holdingMonths) scnPayload.holding_period_months = parseFloat(holdingMonths);
      if (exitMode) {
        scnPayload.exit_value_mode = exitMode;
        if (exitMode === 'USER_EXIT_PRICE' && exitPrice) scnPayload.exit_sale_price_aed = parseFloat(exitPrice);
        if (exitMode === 'USER_APPRECIATION_RATE' && appreciationRate) scnPayload.annual_appreciation_rate_pct = parseFloat(appreciationRate);
      }
      if (sellingBrokerMode) {
        scnPayload.selling_broker_mode = sellingBrokerMode;
        if (sellingBrokerMode === 'SELLING_BROKER_PERCENT' && sellingBrokerPercent) scnPayload.selling_broker_percent = parseFloat(sellingBrokerPercent);
        if (sellingBrokerMode === 'SELLING_BROKER_FIXED_AED' && sellingBrokerAed) scnPayload.selling_broker_aed = parseFloat(sellingBrokerAed);
      }
      if (nocMode) {
        scnPayload.noc_mode = nocMode;
        if (nocMode === 'NOC_FIXED_AED' && nocFee) scnPayload.noc_fee_aed = parseFloat(nocFee);
      }
      if (otherSellingMode) {
        scnPayload.other_selling_mode = otherSellingMode;
        if (otherSellingMode === 'OTHER_SELLING_COSTS_AED' && otherSellingAed) scnPayload.other_selling_costs_aed = parseFloat(otherSellingAed);
      }
      await api.saveRoiScenario(propertyId, scnPayload);

      setSuccess('Saved. ROI calculations updated.');
      setTimeout(() => window.location.reload(), 600);
    } catch (e: any) {
      setError(e.message || 'Failed to save inputs');
    } finally {
      setSaving(false);
    }
  }, [propertyId, dldMode, dldCustomPercent, dldCustomAed, trusteeFee, brokerMode, brokerPercent, brokerAed,
      devAdminMode, devAdminAed, holdingMonths, exitMode, exitPrice, appreciationRate,
      sellingBrokerMode, sellingBrokerPercent, sellingBrokerAed, nocMode, nocFee, otherSellingMode, otherSellingAed]);

  const handleClear = useCallback(async () => {
    setSaving(true);
    setError(null);
    const userScope = getSessionUserScope();
    try {
      await api.clearAcquisitionCosts(propertyId, userScope);
      await api.clearRoiScenario(propertyId, userScope);
      setSuccess('Cleared.');
      setTimeout(() => window.location.reload(), 500);
    } catch {
      setError('Network error');
    } finally {
      setSaving(false);
    }
  }, [propertyId]);

  // ── ROI UI VISIBILITY GATE ──
  // Hide the entire Full Property ROI section if minimum prerequisites are not met.
  // No partial UI, no placeholder, no disabled calculator, no missing-input list.
  if (!roiUiVisible) return null;

  const hasAnyInput = holdingMonths || exitMode || sellingBrokerMode || nocMode || otherSellingMode || trusteeFee || brokerMode || devAdminMode || dldMode;

  const inputSelectClass = "text-sm border border-apil-gray-200 rounded-lg px-2 py-1.5 bg-white";
  const inputNumberClass = "text-sm border border-apil-gray-200 rounded-lg px-2 py-1.5 w-28";
  const labelClass = "text-xs font-semibold text-apil-gray-600 mb-1 block";
  const sectionHeaderClass = "text-sm font-bold uppercase tracking-wider text-apil-gray-500 mb-3";
  const sourceClass = "text-[11px] text-apil-gray-400 mt-0.5";

  return (
    <div className="bg-white rounded-2xl border border-apil-gray-200 p-5 md:p-6 mb-6 shadow-sm">
      <h2 className={sectionHeaderClass}>Full Property ROI</h2>

      {/* ── ROI HEADLINE ── */}
      {isCalculated && fullRoi ? (
        <div className="mb-6 p-6 bg-gradient-to-br from-blue-50 to-emerald-50 rounded-2xl text-center">
          <p className="text-4xl font-bold text-apil-gray-900">
            {fullRoi.full_property_roi_pct != null ? `${fullRoi.full_property_roi_pct}%` : 'N/A'}
          </p>
          <p className="text-sm text-apil-gray-600 mt-2">
            Total unlevered return over your selected {fullRoi.holding_period_years}-
            {fullRoi.holding_period_years === 1 ? 'year' : 'year'} holding period.
          </p>
          <div className="mt-3 text-xs text-apil-gray-500 bg-white/60 rounded-lg p-3 inline-block">
            <p className="font-semibold mb-1">This is NOT:</p>
            <div className="flex flex-wrap gap-x-3 justify-center">
              <span>{fullRoi.full_property_roi_pct}% per year</span>
              <span>· Annualized ROI</span>
              <span>· CAGR</span>
              <span>· IRR</span>
              <span>· Leveraged return</span>
            </div>
          </div>
        </div>
      ) : roiStatus === 'NOT_EVALUATED_OFFPLAN' ? (
        <div className="mb-6 p-4 bg-gray-50 rounded-xl text-center">
          <p className="text-sm text-apil-gray-500">Full Property ROI is not available for offplan properties.</p>
        </div>
      ) : (
        <div className="mb-6 p-4 bg-amber-50 rounded-xl text-center">
          <p className="text-sm text-amber-700 font-medium">Complete all inputs below to calculate Full Property ROI.</p>
          {fullRoi?.missing_inputs && fullRoi.missing_inputs.length > 0 && (
            <p className="text-xs text-amber-600 mt-1">
              Missing: {fullRoi.missing_inputs.map(m => m.replace(/_/g, ' ')).join(', ')}
            </p>
          )}
        </div>
      )}

      {/* ── INPUT SECTION ── */}
      <div className="space-y-5 mb-4">
        {/* ── Acquisition Costs ── */}
        <div className="border border-apil-gray-100 rounded-xl p-4">
          <p className="text-xs font-bold text-apil-gray-700 mb-3">Initial Investment / Acquisition Costs</p>
          <div className="space-y-3">
            {/* DLD */}
            <div>
              <label className={labelClass}>Buyer DLD Transfer Cost</label>
              <div className="flex flex-wrap gap-2 items-center">
                <select value={dldMode} onChange={(e) => setDldMode(e.target.value)} className={inputSelectClass}>
                  <option value="">— Not entered —</option>
                  <option value="USE_STATUTORY_DEFAULT">Use statutory default (2% buyer)</option>
                  <option value="USE_CUSTOM_BUYER_PERCENT">Custom buyer %</option>
                  <option value="USE_CUSTOM_BUYER_AED">Custom AED</option>
                </select>
                {dldMode === 'USE_CUSTOM_BUYER_PERCENT' && (
                  <input type="number" min="0" max="4" step="0.1" placeholder="2.0" value={dldCustomPercent}
                    onChange={(e) => setDldCustomPercent(e.target.value)} className={inputNumberClass} />
                )}
                {dldMode === 'USE_CUSTOM_BUYER_PERCENT' && <span className="text-sm text-apil-gray-400">% buyer share</span>}
                {dldMode === 'USE_CUSTOM_BUYER_AED' && (
                  <input type="number" min="0" step="100" placeholder="54000" value={dldCustomAed}
                    onChange={(e) => setDldCustomAed(e.target.value)} className={inputNumberClass} />
                )}
                {dldMode === 'USE_CUSTOM_BUYER_AED' && <span className="text-sm text-apil-gray-400">AED</span>}
              </div>
              {dldMode && <p className={sourceClass}>Official DLD: 4% total · Default: 2% buyer / 2% seller</p>}
            </div>

            {/* Trustee */}
            <div>
              <label className={labelClass}>Trustee Office Fee</label>
              <div className="flex gap-2 items-center">
                <input type="number" min="0" step="100" placeholder="4000" value={trusteeFee}
                  onChange={(e) => setTrusteeFee(e.target.value)} className={inputNumberClass} />
                <span className="text-sm text-apil-gray-400">AED</span>
              </div>
            </div>

            {/* Broker */}
            <div>
              <label className={labelClass}>Purchase Broker Cost</label>
              <div className="flex flex-wrap gap-2 items-center">
                <select value={brokerMode} onChange={(e) => setBrokerMode(e.target.value)} className={inputSelectClass}>
                  <option value="">— Not entered —</option>
                  <option value="NO_BROKER_COST">No broker cost</option>
                  <option value="BROKER_PERCENT">Percentage (%)</option>
                  <option value="BROKER_FIXED_AED">Fixed AED</option>
                </select>
                {brokerMode === 'BROKER_PERCENT' && (
                  <input type="number" min="0" max="10" step="0.1" placeholder="2.0" value={brokerPercent}
                    onChange={(e) => setBrokerPercent(e.target.value)} className={inputNumberClass} />
                )}
                {brokerMode === 'BROKER_PERCENT' && <span className="text-sm text-apil-gray-400">% of price</span>}
                {brokerMode === 'BROKER_FIXED_AED' && (
                  <input type="number" min="0" step="500" placeholder="54000" value={brokerAed}
                    onChange={(e) => setBrokerAed(e.target.value)} className={inputNumberClass} />
                )}
                {brokerMode === 'BROKER_FIXED_AED' && <span className="text-sm text-apil-gray-400">AED</span>}
              </div>
            </div>

            {/* Developer/Admin */}
            <div>
              <label className={labelClass}>Developer / Admin Fee</label>
              <div className="flex flex-wrap gap-2 items-center">
                <select value={devAdminMode} onChange={(e) => setDevAdminMode(e.target.value)} className={inputSelectClass}>
                  <option value="">— Not entered —</option>
                  <option value="NO_DEVELOPER_ADMIN_FEE">No developer/admin fee</option>
                  <option value="DEVELOPER_ADMIN_FEE_AED">Fixed AED</option>
                </select>
                {devAdminMode === 'DEVELOPER_ADMIN_FEE_AED' && (
                  <input type="number" min="0" step="500" placeholder="2000" value={devAdminAed}
                    onChange={(e) => setDevAdminAed(e.target.value)} className={inputNumberClass} />
                )}
                {devAdminMode === 'DEVELOPER_ADMIN_FEE_AED' && <span className="text-sm text-apil-gray-400">AED</span>}
              </div>
            </div>
          </div>

          {/* Acquisition summary */}
          {acquisitionCost?.calculation_level === 'COMPLETE_ACQUISITION_COSTS' && (
            <div className="mt-3 pt-3 border-t border-apil-gray-100 space-y-1">
              <div className="flex justify-between text-sm">
                <span className="text-apil-gray-600">Title Deed Fee</span>
                <span className="text-apil-gray-700">{formatAEDFull(acquisitionCost.title_deed_fee?.amount_aed)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-apil-gray-600">Knowledge Fee</span>
                <span className="text-apil-gray-700">{formatAEDFull(acquisitionCost.knowledge_fee?.amount_aed)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-apil-gray-600">Innovation Fee</span>
                <span className="text-apil-gray-700">{formatAEDFull(acquisitionCost.innovation_fee?.amount_aed)}</span>
              </div>
              <div className="flex justify-between text-sm font-semibold pt-1 border-t border-apil-gray-100">
                <span className="text-apil-gray-700">Total Acquisition Costs</span>
                <span className="text-apil-gray-900">{formatAEDFull(acquisitionCost.complete_acquisition_costs_aed)}</span>
              </div>
              <div className="flex justify-between text-sm font-bold">
                <span className="text-apil-gray-800">Total Cash Invested</span>
                <span className="text-apil-blue">{formatAEDFull(acquisitionCost.total_cash_invested_aed)}</span>
              </div>
            </div>
          )}
        </div>

        {/* ── Scenario Inputs ── */}
        <div className="border border-apil-gray-100 rounded-xl p-4">
          <p className="text-xs font-bold text-apil-gray-700 mb-3">Holding Period & Exit Scenario</p>
          <div className="space-y-3">
            {/* Holding Period */}
            <div>
              <label className={labelClass}>Holding Period (months)</label>
              <div className="flex gap-2 items-center">
                <input type="number" min="1" max="1200" step="1" placeholder="60" value={holdingMonths}
                  onChange={(e) => setHoldingMonths(e.target.value)} className={inputNumberClass} />
                <span className="text-sm text-apil-gray-400">months</span>
                {holdingMonths && parseFloat(holdingMonths) > 0 && (
                  <span className="text-xs text-apil-gray-400">= {(parseFloat(holdingMonths) / 12).toFixed(1)} years</span>
                )}
              </div>
            </div>

            {/* Exit Value */}
            <div>
              <label className={labelClass}>Exit Value Method</label>
              <div className="flex flex-wrap gap-2 items-center">
                <select value={exitMode} onChange={(e) => { setExitMode(e.target.value); setExitPrice(''); setAppreciationRate(''); }} className={inputSelectClass}>
                  <option value="">— Not entered —</option>
                  <option value="USER_EXIT_PRICE">Direct exit price (AED)</option>
                  <option value="USER_APPRECIATION_RATE">Annual appreciation rate (%)</option>
                </select>
                {exitMode === 'USER_EXIT_PRICE' && (
                  <input type="number" min="0" step="10000" placeholder="3500000" value={exitPrice}
                    onChange={(e) => setExitPrice(e.target.value)} className={inputNumberClass} />
                )}
                {exitMode === 'USER_EXIT_PRICE' && <span className="text-sm text-apil-gray-400">AED</span>}
                {exitMode === 'USER_APPRECIATION_RATE' && (
                  <input type="number" min="-100" max="1000" step="0.1" placeholder="5.0" value={appreciationRate}
                    onChange={(e) => setAppreciationRate(e.target.value)} className={inputNumberClass} />
                )}
                {exitMode === 'USER_APPRECIATION_RATE' && <span className="text-sm text-apil-gray-400">% per year</span>}
              </div>
              {exitMode === 'USER_APPRECIATION_RATE' && (
                <p className="text-[11px] text-amber-600 mt-1">
                  Exit price is derived from your assumption. This is not an APIL market forecast.
                </p>
              )}
            </div>
          </div>
        </div>

        {/* ── Selling Costs ── */}
        <div className="border border-apil-gray-100 rounded-xl p-4">
          <p className="text-xs font-bold text-apil-gray-700 mb-3">Selling Costs</p>
          <div className="space-y-3">
            {/* Selling Broker */}
            <div>
              <label className={labelClass}>Selling Broker Cost</label>
              <div className="flex flex-wrap gap-2 items-center">
                <select value={sellingBrokerMode} onChange={(e) => setSellingBrokerMode(e.target.value)} className={inputSelectClass}>
                  <option value="">— Not entered —</option>
                  <option value="NO_SELLING_BROKER_COST">No selling broker</option>
                  <option value="SELLING_BROKER_PERCENT">Percentage (%)</option>
                  <option value="SELLING_BROKER_FIXED_AED">Fixed AED</option>
                </select>
                {sellingBrokerMode === 'SELLING_BROKER_PERCENT' && (
                  <input type="number" min="0" max="10" step="0.1" placeholder="2.0" value={sellingBrokerPercent}
                    onChange={(e) => setSellingBrokerPercent(e.target.value)} className={inputNumberClass} />
                )}
                {sellingBrokerMode === 'SELLING_BROKER_PERCENT' && <span className="text-sm text-apil-gray-400">% of exit price</span>}
                {sellingBrokerMode === 'SELLING_BROKER_FIXED_AED' && (
                  <input type="number" min="0" step="500" placeholder="70000" value={sellingBrokerAed}
                    onChange={(e) => setSellingBrokerAed(e.target.value)} className={inputNumberClass} />
                )}
                {sellingBrokerMode === 'SELLING_BROKER_FIXED_AED' && <span className="text-sm text-apil-gray-400">AED</span>}
              </div>
            </div>

            {/* NOC */}
            <div>
              <label className={labelClass}>Developer / NOC Fee</label>
              <div className="flex flex-wrap gap-2 items-center">
                <select value={nocMode} onChange={(e) => setNocMode(e.target.value)} className={inputSelectClass}>
                  <option value="">— Not entered —</option>
                  <option value="NO_NOC_FEE">No NOC fee</option>
                  <option value="NOC_FIXED_AED">Fixed AED</option>
                </select>
                {nocMode === 'NOC_FIXED_AED' && (
                  <input type="number" min="0" step="500" placeholder="5000" value={nocFee}
                    onChange={(e) => setNocFee(e.target.value)} className={inputNumberClass} />
                )}
                {nocMode === 'NOC_FIXED_AED' && <span className="text-sm text-apil-gray-400">AED</span>}
              </div>
            </div>

            {/* Other Selling */}
            <div>
              <label className={labelClass}>Other Selling Costs</label>
              <div className="flex flex-wrap gap-2 items-center">
                <select value={otherSellingMode} onChange={(e) => setOtherSellingMode(e.target.value)} className={inputSelectClass}>
                  <option value="">— Not entered —</option>
                  <option value="NO_OTHER_SELLING_COSTS">No other selling costs</option>
                  <option value="OTHER_SELLING_COSTS_AED">Fixed AED</option>
                </select>
                {otherSellingMode === 'OTHER_SELLING_COSTS_AED' && (
                  <input type="number" min="0" step="500" placeholder="3000" value={otherSellingAed}
                    onChange={(e) => setOtherSellingAed(e.target.value)} className={inputNumberClass} />
                )}
                {otherSellingMode === 'OTHER_SELLING_COSTS_AED' && <span className="text-sm text-apil-gray-400">AED</span>}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Error / Success */}
      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
      {success && <p className="text-sm text-emerald-600 mb-2">{success}</p>}

      {/* Save / Clear */}
      <div className="flex gap-2 mb-4">
        <button onClick={handleSave} disabled={saving}
          className="text-sm bg-apil-blue text-white rounded-lg px-4 py-2 hover:bg-apil-blue-dark disabled:opacity-50">
          {saving ? 'Saving...' : 'Save & Calculate ROI'}
        </button>
        {hasAnyInput && (
          <button onClick={handleClear} disabled={saving}
            className="text-sm border border-apil-gray-200 text-apil-gray-600 rounded-lg px-4 py-2 hover:bg-apil-gray-50 disabled:opacity-50">
            Clear
          </button>
        )}
      </div>

      {/* ── ROI RESULTS ── */}
      {isCalculated && fullRoi && (
        <div className="mt-4 pt-4 border-t-2 border-apil-gray-100 space-y-4">
          {/* Return Breakdown */}
          <div className="bg-apil-gray-50 rounded-xl p-4">
            <p className="text-xs font-bold text-apil-gray-500 mb-3">Return Breakdown</p>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-apil-gray-600">Total Cash Invested</span>
                <span className="text-apil-gray-800 font-medium">{formatAEDFull(fullRoi.total_cash_invested_aed)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-apil-gray-600">Cumulative Net Rental Income</span>
                <span className="text-emerald-600 font-medium">+ {formatAEDFull(fullRoi.cumulative_net_rental_income_aed)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-apil-gray-600">Capital Return</span>
                <span className={`font-medium ${(fullRoi.capital_return_aed || 0) >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                  {(fullRoi.capital_return_aed || 0) >= 0 ? '+ ' : ''}{formatAEDFull(fullRoi.capital_return_aed)}
                </span>
              </div>
              <div className="flex justify-between text-base font-bold pt-2 border-t border-apil-gray-200">
                <span className="text-apil-gray-800">Total Return</span>
                <span className={`text-apil-gray-900`}>{formatAEDFull(fullRoi.total_return_aed)}</span>
              </div>
              <div className="flex justify-between text-base font-bold">
                <span className="text-apil-blue">Full Property ROI</span>
                <span className="text-apil-blue text-lg">{fullRoi.full_property_roi_pct}%</span>
              </div>
              <p className="text-[11px] text-apil-gray-400 mt-1">
                Formula: Total Return ÷ Total Cash Invested × 100
              </p>
            </div>
          </div>

          {/* Scenario Summary */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white border border-apil-gray-100 rounded-xl p-3">
              <p className="text-[11px] text-apil-gray-500 font-medium">Holding Period</p>
              <p className="text-sm font-bold text-apil-gray-800">
                {fullRoi.holding_period_years} {fullRoi.holding_period_years === 1 ? 'year' : 'years'}
              </p>
              <p className="text-[10px] text-apil-gray-400">Source: Your input</p>
            </div>
            <div className="bg-white border border-apil-gray-100 rounded-xl p-3">
              <p className="text-[11px] text-apil-gray-500 font-medium">Exit Sale Price</p>
              <p className="text-sm font-bold text-apil-gray-800">{formatAEDFull(fullRoi.exit_sale_price_aed)}</p>
              <p className="text-[10px] text-apil-gray-400">
                Source: {fullRoi.exit_price_source === 'DERIVED' ? 'Derived from your appreciation assumption' : 'Your input'}
              </p>
            </div>
            <div className="bg-white border border-apil-gray-100 rounded-xl p-3">
              <p className="text-[11px] text-apil-gray-500 font-medium">Annual Net Rental Income</p>
              <p className="text-sm font-bold text-apil-gray-800">{formatAEDFull(fullRoi.annual_net_rental_income_aed)}</p>
              <p className="text-[10px] text-apil-gray-400">Source: Operating cost context</p>
            </div>
            <div className="bg-white border border-apil-gray-100 rounded-xl p-3">
              <p className="text-[11px] text-apil-gray-500 font-medium">Net Sale Proceeds</p>
              <p className="text-sm font-bold text-apil-gray-800">{formatAEDFull(fullRoi.net_sale_proceeds_aed)}</p>
              <p className="text-[10px] text-apil-gray-400">Exit price − selling costs</p>
            </div>
          </div>

          {/* Included / Excluded */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="bg-emerald-50/50 rounded-xl p-3">
              <p className="text-[11px] font-semibold text-emerald-700 mb-1">Included in this ROI</p>
              <ul className="space-y-0.5">
                {fullRoi.included_components?.map((c, i) => (
                  <li key={i} className="text-[11px] text-apil-gray-600 flex items-start">
                    <span className="text-emerald-600 mr-1.5">✓</span> {c.replace(/_/g, ' ')}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-gray-50 rounded-xl p-3">
              <p className="text-[11px] font-semibold text-apil-gray-500 mb-1">Not included</p>
              <ul className="space-y-0.5">
                {fullRoi.excluded_components?.map((c, i) => (
                  <li key={i} className="text-[11px] text-apil-gray-500 flex items-start">
                    <span className="text-apil-gray-400 mr-1.5">—</span> {c.replace(/_/g, ' ')}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Disclosures */}
          <div className="bg-amber-50/30 rounded-xl p-3">
            <p className="text-[11px] font-semibold text-amber-700 mb-1">Important Disclosures</p>
            <ol className="space-y-1 text-[11px] text-apil-gray-600 leading-relaxed list-decimal list-inside">
              <li>This Full Property ROI is a TOTAL return over the selected holding period. It is not an annual return.</li>
              <li>User-entered assumptions materially affect the result.</li>
              <li>If appreciation is used, the future sale price is based on your assumption and is not a market forecast.</li>
              <li>Net Rental Income is shown only when all required operating costs are available.</li>
              <li>Missing costs are never automatically treated as zero.</li>
              <li>This version is unlevered and does not include mortgage financing.</li>
              <li>Scenario inputs are temporary in the current demo and may not be available after the session ends.</li>
            </ol>
          </div>
        </div>
      )}

      {/* Ephemeral disclosure */}
      <p className="text-[11px] text-apil-gray-400 leading-relaxed mt-3 pt-2 border-t border-apil-gray-100">
        Your ROI scenario inputs are temporary and may not be available after the session ends.
      </p>
    </div>
  );
}
