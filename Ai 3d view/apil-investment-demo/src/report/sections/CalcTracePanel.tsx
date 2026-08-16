import { useState } from 'react';
import { Calculator, Database, ChevronDown, ChevronUp } from 'lucide-react';

interface CalcTracePanelProps {
  trace: any;
  section: string;
  title: string;
}

function fmtAED(v: any): string {
  if (v == null) return '—';
  const n = Number(v);
  if (isNaN(n)) return '—';
  if (n >= 1_000_000) return `AED ${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `AED ${(n / 1_000).toFixed(0)}K`;
  return `AED ${n.toFixed(0)}`;
}

function fmtNum(v: any, decimals = 2): string {
  if (v == null) return '—';
  const n = Number(v);
  if (isNaN(n)) return '—';
  return n.toFixed(decimals);
}

function TraceRow({ label, value, source }: { label: string; value: string; source?: string }) {
  return (
    <div className="flex items-start gap-3 py-1.5 border-b border-gray-50 last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-xs font-medium text-gray-700">{label}</p>
        {source && <p className="text-[10px] text-gray-400 mt-0.5">{source}</p>}
      </div>
      <div className="text-right">
        <p className="text-xs font-semibold text-gray-900 font-mono">{value}</p>
      </div>
    </div>
  );
}

function TraceSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4 last:mb-0">
      <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2">{title}</p>
      {children}
    </div>
  );
}

function LaymanExplanation({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-3 p-3 bg-blue-50/50 rounded-lg border border-blue-100">
      <div className="flex items-start gap-2">
        <Calculator className="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-gray-700 leading-relaxed">{children}</p>
      </div>
    </div>
  );
}

function DataSource({ children }: { children: React.ReactNode }) {
  return (
    <div className="mt-2 p-2 bg-gray-50 rounded-lg flex items-start gap-2">
      <Database className="w-3 h-3 text-gray-400 mt-0.5 flex-shrink-0" />
      <p className="text-[10px] text-gray-500 leading-relaxed">{children}</p>
    </div>
  );
}

export function CalcTracePanel({ trace, section, title }: CalcTracePanelProps) {
  const [expanded, setExpanded] = useState(false);

  if (!trace) return null;

  const renderTrace = () => {
    switch (section) {
      case 'valuation':
        return <ValuationTrace trace={trace} />;
      case 'rental':
        return <RentalTrace trace={trace} />;
      case 'growth':
        return <GrowthTrace trace={trace} />;
      case 'totalReturn':
        return <TotalReturnTrace trace={trace} />;
      case 'leverage':
        return <LeverageTrace trace={trace} />;
      case 'risk':
        return <RiskTrace trace={trace} />;
      case 'score':
        return <ScoreTrace trace={trace} />;
      case 'evidence':
        return <EvidenceTrace trace={trace} />;
      case 'strategy':
        return <StrategyTrace trace={trace} />;
      case 'fit':
        return <FitTrace trace={trace} />;
      case 'property':
        return <PropertyTrace trace={trace} />;
      case 'paymentPlan':
        return <PaymentPlanTrace trace={trace} />;
      case 'construction':
        return <ConstructionTrace trace={trace} />;
      case 'market':
        return <MarketTrace trace={trace} />;
      case 'exitStrategy':
        return <ExitStrategyTrace trace={trace} />;
      default:
        return <pre className="text-xs text-gray-600 overflow-x-auto">{JSON.stringify(trace, null, 2)}</pre>;
    }
  };

  return (
    <div className="mt-2 mb-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-[10px] text-gray-400 hover:text-blue-500 transition-colors"
      >
        <Calculator className="w-3 h-3" />
        <span>How is this calculated?</span>
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {expanded && (
        <div className="mt-2 p-4 bg-gray-50/80 rounded-lg border border-gray-100 max-h-[600px] overflow-y-auto">
          <div className="flex items-center gap-2 mb-3 pb-2 border-b border-gray-100">
            <Calculator className="w-4 h-4 text-blue-500" />
            <h4 className="text-sm font-semibold text-gray-700">Calculation Trace: {title}</h4>
          </div>
          {renderTrace()}
        </div>
      )}
    </div>
  );
}

function ValuationTrace({ trace }: { trace: any }) {
  const t = trace;
  const inp = t.inputs || t;
  const out = t.output || t;
  const askingPrice = inp.asking_price ?? t.askingPrice;
  const sizeSqft = inp.size_sqft ?? t.sizeSqft;
  const medianPriceSqft = inp.median_price_sqft ?? t.medianPriceSqft;
  const comparableCount = inp.comparable_count ?? t.comparableCount ?? 0;
  const method = inp.method ?? t.method;
  const fairValue = out.fairValuePointEstimate ?? t.fairValuePointEstimate;
  const fairValueLow = out.fairValueLow ?? t.fairValueLow;
  const fairValueHigh = out.fairValueHigh ?? t.fairValueHigh;
  const priceDiffPct = t.priceDifferencePct ?? inp.price_difference_pct;
  return (
    <div>
      <TraceSection title="Input Values">
        <TraceRow label="Asking Price (your purchase price)" value={fmtAED(askingPrice)} source="Qdrant listing" />
        <TraceRow label="Property Size" value={`${fmtNum(sizeSqft, 0)} sqft`} source="Qdrant listing" />
        <TraceRow label="Comparable Sales Count" value={`${comparableCount} transactions`} source="DLD transaction records" />
        <TraceRow label="Valuation Method" value={method || '—'} source={method === 'project_bedroom' ? 'Exact project + bedroom match' : 'Area-level match'} />
      </TraceSection>

      <TraceSection title="Calculation Steps">
        <TraceRow label="Step 1: Find comparable sales" value={`${comparableCount} DLD sales`} source="Same project, same bedroom type" />
        <TraceRow label="Step 2: Calculate price/sqft for each" value={`${fmtNum(medianPriceSqft)} AED/sqft (median)`} source="price ÷ area for each transaction" />
        <TraceRow label="Step 3: Fair Value = median price/sqft × your size" value={fmtAED(fairValue)} source={`${fmtNum(medianPriceSqft)} × ${fmtNum(sizeSqft, 0)} sqft`} />
        <TraceRow label="Step 4: Range (±20%)" value={`${fmtAED(fairValueLow)} – ${fmtAED(fairValueHigh)}`} source="Fair value × (1 ± 0.20)" />
        <TraceRow label="Step 5: Your discount/premium" value={`${fmtNum(priceDiffPct)}%`} source={`(${fmtAED(askingPrice)} − ${fmtAED(fairValue)}) ÷ ${fmtAED(fairValue)} × 100`} />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> We found <strong>{comparableCount}</strong> actual DLD-registered sales for the same project ({method === 'project_bedroom' ? 'exact same building and bedroom type' : 'same area and bedroom type'}).
        The median price per square foot was <strong>{fmtNum(medianPriceSqft)} AED/sqft</strong>.
        Your property is <strong>{fmtNum(sizeSqft, 0)} sqft</strong>, so the fair market value is <strong>{fmtAED(fairValue)}</strong>.
        You're buying at <strong>{fmtAED(askingPrice)}</strong>, which is <strong>{fmtNum(priceDiffPct)}%</strong> relative to fair value.
      </LaymanExplanation>

      <DataSource>
        Data source: Dubai Land Department (DLD) verified transaction records. {comparableCount} comparable sales found for this project/bedroom type. Method: {method}.
      </DataSource>
    </div>
  );
}

function RentalTrace({ trace }: { trace: any }) {
  const t = trace;
  const inp = t.inputs || t;
  const out = t.output || t;
  const purchasePrice = inp.purchase_price ?? t.purchasePrice;
  const annualRent = out.annualRent ?? t.annualRent ?? 0;
  const grossYield = out.grossYield ?? t.grossYieldPct ?? 0;
  const netYield = out.netYield ?? t.netYieldPct ?? 0;
  const netIncome = out.netIncome ?? t.netAnnualIncome ?? 0;
  const reason = inp.reason || t.rentSource || '';
  return (
    <div>
      <TraceSection title="Input Values">
        <TraceRow label="Purchase Price" value={fmtAED(purchasePrice)} source="Qdrant listing" />
        <TraceRow label="Rent Source" value={reason || '—'} source="DLD Ejari rental contracts" />
      </TraceSection>

      <TraceSection title="Calculation Steps">
        <TraceRow label="Step 1: Find comparable rentals" value={reason || '—'} source="Same area, same bedroom type" />
        <TraceRow label="Step 2: Annual rent" value={fmtAED(annualRent)} source="Median of comparable rents" />
        <TraceRow label="Step 3: Gross yield = rent ÷ price" value={`${fmtNum(grossYield)}%`} source={`${fmtAED(annualRent)} ÷ ${fmtAED(purchasePrice)} × 100`} />
        <TraceRow label="Step 4: Net income (after costs)" value={fmtAED(netIncome)} source="rent − service charge − vacancy − management" />
        <TraceRow label="Step 5: Net yield = net income ÷ price" value={`${fmtNum(netYield)}%`} source={`${fmtAED(netIncome)} ÷ ${fmtAED(purchasePrice)} × 100`} />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> {reason ? `No rental evidence found — ${reason}.` : `Based on DLD rental data, the estimated annual rent is <strong>${fmtAED(annualRent)}</strong>.`}
        {annualRent > 0 ? ` After deducting service charge, vacancy, and management fees, net income is <strong>${fmtAED(netIncome)}</strong>/year — a <strong>${fmtNum(netYield)}% net yield</strong>.` : ' Rental estimates are not available for this property.'}
      </LaymanExplanation>

      <DataSource>
        Data source: DLD Ejari rental registrations. Comparable rental contracts filtered by area and bedroom type.
      </DataSource>
    </div>
  );
}

function GrowthTrace({ trace }: { trace: any }) {
  const t = trace;
  const inp = t.inputs || t;
  const out = t.output || t;
  const purchasePrice = inp.purchase_price ?? t.purchasePrice;
  const growthRate = inp.growth_rate ?? t.annualGrowthRate;
  const years = inp.years ?? t.holdingYears;
  const futureValue = out.futureValue ?? t.futureValue;
  const capitalGain = out.capitalGain ?? t.capitalGain;
  const capitalGainPct = out.capitalGainPct ?? t.capitalGainPct;
  const growthSource = inp.growth_source ?? t.growthSource;
  const growthConfidence = inp.growth_confidence ?? t.growthConfidence;
  return (
    <div>
      <TraceSection title="Input Values">
        <TraceRow label="Purchase Price" value={fmtAED(purchasePrice)} source="Qdrant listing" />
        <TraceRow label="Annual Growth Rate" value={`${fmtNum(growthRate)}%`} source={t.growthDescription || growthSource} />
        <TraceRow label="Growth Source" value={growthSource || '—'} source={growthConfidence ? `Confidence: ${growthConfidence}` : ''} />
        <TraceRow label="Holding Period" value={`${fmtNum(years, 1)} years`} source="Time to handover / exit" />
      </TraceSection>

      <TraceSection title="Calculation Steps">
        <TraceRow label="Step 1: Get project growth rate" value={`${fmtNum(growthRate)}%/yr`} source={t.growthDescription || growthSource} />
        <TraceRow label="Step 2: Compound over holding period" value={fmtAED(futureValue)} source={`price × (1 + ${fmtNum(growthRate)}%)^${fmtNum(years, 1)}`} />
        <TraceRow label="Step 3: Capital gain" value={fmtAED(capitalGain)} source={`${fmtAED(futureValue)} − purchase price`} />
        <TraceRow label="Step 4: Capital gain %" value={`${fmtNum(capitalGainPct)}%`} source={`gain ÷ price × 100`} />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> The DLD data shows this project's prices growing at <strong>{fmtNum(growthRate)}% per year</strong>.
        If this trend continues for {fmtNum(years, 1)} years, your property could be worth <strong>{fmtAED(futureValue)}</strong> —
        a gain of <strong>{fmtAED(capitalGain)}</strong> ({fmtNum(capitalGainPct)}%).
      </LaymanExplanation>

      <DataSource>
        Data source: DLD project statistics (price_change_pct). Growth rate is annualized from total historical change. Source: {growthSource}, confidence: {growthConfidence}.
      </DataSource>
    </div>
  );
}

function TotalReturnTrace({ trace }: { trace: any }) {
  const t = trace;
  const cashFlows: number[] = t.cashFlows || [];
  const inputs = t.inputs || {};
  return (
    <div>
      <TraceSection title="Input Values">
        <TraceRow label="Purchase Price" value={fmtAED(inputs.purchase_price)} source="Qdrant listing" />
        <TraceRow label="Holding Period" value={`${inputs.holding_years ?? t.holdingYears} years`} source="Construction period (flip at handover)" />
        <TraceRow label="Sale Value (net of selling costs)" value={fmtAED(t.projectedSaleValue)} source="Future value − 6% selling costs" />
        <TraceRow label="Rental Income" value={fmtAED(t.totalRentalIncome)} source={inputs.rental_years > 0 ? `${inputs.rental_years} years of rent` : 'Zero (flip at handover)'} />
        <TraceRow label="Model" value={t.model || '—'} source={inputs.payment_schedule_used ? 'Using staged payment plan' : 'Full price at Year 0'} />
      </TraceSection>

      <TraceSection title="Cash Flow Schedule (used for ROE)">
        {cashFlows.map((cf, i) => (
          <TraceRow
            key={i}
            label={`Year ${i}`}
            value={fmtAED(cf)}
            source={cf < 0 ? 'Money out (payment + service charge)' : cf > 0 ? 'Money in (sale net of selling costs + service charge)' : 'No cash flow'}
          />
        ))}
      </TraceSection>

      <TraceSection title="Costs Deducted">
        {inputs.annual_service_charge != null && inputs.annual_service_charge > 0 ? (
          <>
            <TraceRow label="Annual Service Charge" value={fmtAED(inputs.annual_service_charge)} source="Building maintenance fees (from DLD service charge data)" />
            <TraceRow label="Service Charge Years" value={`${inputs.service_charge_years ?? 1} year(s)`} source="From handover to sale" />
            <TraceRow label="Total Service Charge" value={fmtAED(inputs.total_service_charge)} source={`${fmtAED(inputs.annual_service_charge)} × ${inputs.service_charge_years ?? 1} years`} />
          </>
        ) : (
          <TraceRow label="Annual Service Charge" value="N/A" source="No DLD service charge data found for this project — not deducted from ROE" />
        )}
        <TraceRow label="Selling Costs (6%)" value={fmtAED((inputs.projected_sale_value ?? 0) * 0.06)} source="4% transfer fee + 2% agent commission" />
      </TraceSection>

      <TraceSection title="Calculation Steps">
        <TraceRow label="Step 1: Sale value (before costs)" value={fmtAED(inputs.projected_sale_value ?? t.projectedSaleValue)} source="Future value at handover" />
        {inputs.total_service_charge != null && (
          <TraceRow label="Step 2: Deduct service charges" value={`−${fmtAED(inputs.total_service_charge)}`} source={`${fmtAED(inputs.annual_service_charge)}/yr × ${inputs.service_charge_years ?? 1} yr`} />
        )}
        <TraceRow label={`Step ${inputs.total_service_charge != null ? '3' : '2'}: Total proceeds (net)`} value={fmtAED(t.totalProceeds)} source={`${fmtAED(t.totalRentalIncome)} + ${fmtAED(t.projectedSaleValue)}${inputs.total_service_charge != null ? ` − ${fmtAED(inputs.total_service_charge)}` : ''}`} />
        <TraceRow label={`Step ${inputs.total_service_charge != null ? '4' : '3'}: Total profit`} value={fmtAED(t.totalProfit)} source={`${fmtAED(t.totalProceeds)} − ${fmtAED(inputs.purchase_price)}`} />
        <TraceRow label={`Step ${inputs.total_service_charge != null ? '5' : '4'}: Total return %`} value={`${fmtNum(t.totalReturnPct)}%`} source={`profit ÷ total equity invested × 100`} />
        <TraceRow label={`Step ${inputs.total_service_charge != null ? '6' : '5'}: ROE`} value={`${fmtNum(t.roePct)}%`} source={inputs.total_service_charge != null ? "(sale proceeds + rental income − service charges − total equity invested) ÷ total equity invested × 100" : "(sale proceeds + rental income − total equity invested) ÷ total equity invested × 100"} />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> You invest {fmtAED(inputs.purchase_price)} total, but not all at once — {inputs.payment_schedule_used ? 'the payment plan spreads your investment over time' : 'it all goes in at Year 0'}.
        After {inputs.holding_years ?? t.holdingYears} years you sell for <strong>{fmtAED(t.projectedSaleValue)}</strong> (after 6% selling costs).
        {inputs.total_service_charge != null && <> You also pay <strong>{fmtAED(inputs.total_service_charge)}</strong> in building service charges ({fmtAED(inputs.annual_service_charge)}/yr × {inputs.service_charge_years ?? 1} yr).</>}
        {inputs.annual_service_charge == null && <> Service charge data is <strong>N/A</strong> for this project (not found in DLD records).</>}
        Your net profit is <strong>{fmtAED(t.totalProfit)}</strong>. The <strong>ROE is {fmtNum(t.roePct)}%</strong> — this is net profit (after service charges and selling costs) divided by total equity invested.
      </LaymanExplanation>

      <DataSource>
        Data source: ROE calculated from payment schedule cash flows + DLD-based projected sale value. Selling costs: 4% transfer + 2% agent = 6%. Payment plan from Qdrant property data.
      </DataSource>
    </div>
  );
}

function LeverageTrace({ trace }: { trace: any }) {
  const t = trace;
  const schedule = t.paymentSchedule || [];
  return (
    <div>
      <TraceSection title="Payment Schedule">
        {schedule.map((s: any, i: number) => (
          <TraceRow key={i} label={`${s.label} (Year ${s.year})`} value={fmtAED(Math.abs(s.amount))} source={`${((Math.abs(s.amount) / (t.totalInvested || 1)) * 100).toFixed(0)}% of purchase`} />
        ))}
      </TraceSection>

      <TraceSection title="Calculation Steps">
        <TraceRow label="Down Payment" value={fmtAED(t.downPaymentAmount)} source={`${t.downPaymentPct}% of purchase price`} />
        <TraceRow label="Total Equity Invested" value={fmtAED(t.totalInvested)} source="All payments combined" />
        <TraceRow label="Equity Gain (capital gain)" value={fmtAED(t.equityGain)} source="Sale value − purchase price" />
        <TraceRow label="Equity ROI" value={`${fmtNum(t.equityRoiPct)}%`} source={`gain ÷ total equity × 100`} />
        <TraceRow label="Leverage Ratio" value={`${t.leverageRatio}x`} source={`price ÷ down payment`} />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> You only put down <strong>{fmtAED(t.downPaymentAmount)}</strong> initially ({t.downPaymentPct}% of the price).
        The rest is paid during construction and at handover. Your total gain is <strong>{fmtAED(t.equityGain)}</strong>,
        which is a <strong>{fmtNum(t.equityRoiPct)}% return on your equity</strong>. Because you're using a payment plan (leverage {t.leverageRatio}x),
        your returns are amplified compared to paying all cash upfront.
      </LaymanExplanation>

      <DataSource>
        Data source: Payment plan from Qdrant property listing. ROE calculated from staged cash flow schedule.
      </DataSource>
    </div>
  );
}

function RiskTrace({ trace }: { trace: any }) {
  const t = trace;
  const inp = t.inputs || t;
  const out = t.output || t;
  const components = t.components || out.components || {};
  const weights = t.weights || t.weights || {};
  const overallRisk = out.overallRisk ?? t.overallRisk;
  const componentNames: Record<string, string> = {
    developerRisk: 'Developer Risk',
    supplyRisk: 'Supply Risk',
    pricePremiumRisk: 'Price Premium Risk',
    marketVolatilityRisk: 'Market Volatility Risk',
    rentalRisk: 'Rental Risk',
    constructionRisk: 'Construction Risk',
    liquidityRisk: 'Liquidity Risk',
  };
  return (
    <div>
      <TraceSection title="Risk Components (0-100, higher = riskier)">
        {Object.entries(components).map(([key, val]: [string, any]) => (
          <TraceRow
            key={key}
            label={componentNames[key] || key}
            value={`${val}/100`}
            source={`Weight: ${((weights[key] || 0) * 100).toFixed(1)}%`}
          />
        ))}
      </TraceSection>

      <TraceSection title="Calculation">
        <TraceRow label="Overall Risk Score" value={`${overallRisk}/100`} source="Weighted sum of all components" />
        <TraceRow label="Risk Level" value={t.riskLevel || '—'} source="Derived from overall score" />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> The risk score of <strong>{overallRisk}/100</strong> is calculated by scoring 7 different risk factors and weighting them.
        The biggest risks for this property are highlighted above. Each factor is scored from DLD data — for example, supply risk is based on how many competing projects are being built in the same area.
      </LaymanExplanation>

      <DataSource>
        Data source: DLD transaction data, project counts, area statistics. Risk weights vary by investor goal (capital growth vs rental income).
      </DataSource>
    </div>
  );
}

function ScoreTrace({ trace }: { trace: any }) {
  const t = trace;
  const inp = t.inputs || t;
  const out = t.output || t;
  const breakdown = t.breakdown || {};
  const weights = t.weights || (out.weights || {});
  const componentTrace = t.componentTrace || {};
  const investmentScore = out.score ?? t.investmentScore;
  const componentNames: Record<string, string> = {
    developer: 'Developer Score',
    pricing: 'Price vs Market',
    paymentPlan: 'Payment Plan',
    growth: 'Future Appreciation',
    supply: 'Supply Risk',
    liquidity: 'Liquidity',
    rental: 'Rental Yield',
    roi: 'ROI / Returns',
  };
  const componentExplanations: Record<string, string> = {
    developer: 'Based on the developer\'s track record — past project deliveries, delay history, and market reputation. A score of 100 means a highly trusted developer with strong delivery history.',
    pricing: 'Compares the asking price to fair market value derived from DLD comparable sales. A score of 100 means the price is at or below market value (a good deal).',
    paymentPlan: 'Evaluates the payment plan structure — down payment %, construction installments, and handover payment. Lower down payment and longer construction period = higher score.',
    growth: 'Based on DLD historical price change data for this project/area. A score of 100 means strong historical price appreciation. Annualized from total change over ~3 years.',
    supply: 'Measures future supply risk — how many competing projects are being built in the same area. More competing supply = lower score. A score of 6 means very high future supply.',
    liquidity: 'Based on DLD transaction turnover rate — how easily you can resell. Higher turnover = higher score. A score of 31 means moderate liquidity.',
    rental: 'Based on DLD Ejari rental contracts for comparable properties. Higher rental yield = higher score. A score of 69 means decent but not top-tier rental yield.',
    roi: 'Based on the projected ROE / total return. A score of 100 means excellent projected returns for your investor goal (capital growth).',
  };
  return (
    <div>
      <TraceSection title="Score Components — How Each Was Calculated">
        {Object.entries(breakdown).map(([key, val]: [string, any]) => {
          const ct = componentTrace[key] || {};
          const weight = ((weights[key] || 0) * 100).toFixed(0);
          const contribution = ct.contribution != null ? ct.contribution.toFixed(1) : (val != null && weights[key] != null ? (val * weights[key]).toFixed(1) : '—');
          return (
            <div key={key} className="py-2 border-b border-gray-50 last:border-0">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-700">{componentNames[key] || key}</p>
                  <p className="text-[10px] text-gray-400 mt-0.5">{componentExplanations[key] || ''}</p>
                  {ct.source && <p className="text-[10px] text-blue-400 mt-0.5">Source: {ct.source}</p>}
                </div>
                <div className="text-right ml-2">
                  <p className="text-xs font-semibold text-gray-900 font-mono">{val}/100</p>
                  <p className="text-[10px] text-gray-400">Weight: {weight}%</p>
                  <p className="text-[10px] text-gray-400">Contrib: {contribution}</p>
                </div>
              </div>
            </div>
          );
        })}
      </TraceSection>

      <TraceSection title="Final Score Calculation">
        {t.rawScore != null && <TraceRow label="Raw Weighted Sum" value={`${fmtNum(t.rawScore, 1)}`} source="Sum of (component score × weight) for all available components" />}
        {t.availableWeight != null && <TraceRow label="Available Weight" value={`${fmtNum(t.availableWeight, 3)}`} source="Sum of weights for components that have data" />}
        <TraceRow label="Final Investment Score" value={`${investmentScore}/100`} source={t.formula || "weightedSum ÷ availableWeight × 100"} />
        {inp.goal && <TraceRow label="Investor Goal" value={inp.goal} source="From questionnaire" />}
        {inp.strategy && <TraceRow label="Strategy" value={inp.strategy} source={`Strategy file: ${inp.strategy_file || '—'}`} />}
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> The investment score of <strong>{investmentScore}/100</strong> is a weighted average of {Object.keys(breakdown).length || 'several'} factors.
        Each factor is scored 0-100 based on real DLD data.{Object.keys(breakdown).length > 0 && <> For example:
        <br/><br/>
        {breakdown.developer != null && <><strong>Developer = {breakdown.developer}</strong>: Based on the developer's track record.<br/></>}
        {breakdown.supply != null && <><strong>Supply = {breakdown.supply}</strong>: Based on competing projects in the area.<br/></>}
        {breakdown.liquidity != null && <><strong>Liquidity = {breakdown.liquidity}</strong>: Based on resale activity in the area.<br/></>}</>}
        <br/>
        The final score weights factors based on your investor goal ({inp.goal || 'capital growth'}).
      </LaymanExplanation>

      <DataSource>
        Data sources: DLD transactions (pricing, supply, liquidity, growth), DLD Ejari rentals (rental score), developer_scores.json (developer score), Qdrant payment plan (payment plan score), ROE calculation (ROI score). Weights are strategy-specific — capital growth goal weights growth and developer highest.
      </DataSource>
    </div>
  );
}

function EvidenceTrace({ trace }: { trace: any }) {
  const t = trace;
  const inp = t.inputs || t;
  const out = t.output || t;
  return (
    <div>
      <TraceSection title="Data Coverage">
        <TraceRow label="Project Sales (same building)" value={`${out.project_sales ?? t.projectSalesCount ?? 0} transactions`} source="DLD sales for this exact project" />
        <TraceRow label="Area Sales (same bedroom)" value={`${out.area_sales ?? t.areaSalesCount ?? 0} transactions`} source="DLD sales in same area, same bedroom" />
        <TraceRow label="Comparable Sales Used" value={`${out.comparable_sales ?? t.comparableSalesCount ?? 0} transactions`} source="Filtered to residential, same project + bedroom" />
        <TraceRow label="Comparable Rentals" value={`${out.comparable_rentals ?? t.comparableRentalsCount ?? 0} contracts`} source="DLD Ejari rentals, same area + bedroom" />
        <TraceRow label="Evidence Level" value={t.evidenceLevel || '—'} source="Based on comparable sales count" />
        <TraceRow label="Confidence Level" value={t.confidenceLevel || '—'} source="Mapped from evidence level" />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> We searched DLD records for this project ({inp.project || '—'}, {inp.area || '—'}, {inp.bedroom || '—'}).
        Found <strong>{out.comparable_sales ?? 0} comparable sales</strong> and <strong>{out.comparable_rentals ?? 0} comparable rentals</strong>.
        {out.comparable_sales > 0 ? 'This gives us good data for valuation.' : 'Limited data — valuation may be less precise.'}
      </LaymanExplanation>

      <DataSource>
        Data source: Dubai Land Department (DLD) verified transaction and Ejari rental records. All counts are actual registered transactions, filtered to residential-only.
      </DataSource>
    </div>
  );
}

function StrategyTrace({ trace }: { trace: any }) {
  const t = trace;
  const inp = t.inputs || {};
  const out = t.output || {};
  const weights = out.weights || {};
  return (
    <div>
      <TraceSection title="Investor Inputs">
        <TraceRow label="Goal" value={inp.goal_input || '—'} source="From questionnaire" />
        <TraceRow label="Property Status" value={inp.property_status || '—'} source="Off-plan or ready" />
        <TraceRow label="Timeline" value={`${inp.timeline_years ?? '—'} years`} source="Investor holding period" />
        <TraceRow label="Risk Profile" value={inp.risk_profile || '—'} source="From questionnaire" />
        <TraceRow label="Strategy File" value={inp.strategy_file || '—'} source="JSON config loaded" />
      </TraceSection>

      <TraceSection title="Scoring Weights Applied">
        {Object.entries(weights).map(([k, v]: [string, any]) => (
          <TraceRow key={k} label={k.charAt(0).toUpperCase() + k.slice(1)} value={`${(v * 100).toFixed(0)}%`} source={`Weight for ${k} component`} />
        ))}
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> Based on your goal ({inp.goal_input}), property type ({inp.property_status}), and timeline ({inp.timeline_years}y),
        the system loaded the <strong>{inp.strategy_file}</strong> strategy. This determines how each factor is weighted when scoring the property.
        {inp.goal_input === 'capital_growth' && inp.property_status === 'off_plan' && ' For capital growth on off-plan, a flip-at-handover model is used (sell at completion, no rental period).'}
      </LaymanExplanation>

      <DataSource>
        Data source: Strategy configs in /strategies/*.json. Weights adjusted by timeline and property status. Flip-at-handover hardcoded for capital_growth + off_plan.
      </DataSource>
    </div>
  );
}

function FitTrace({ trace }: { trace: any }) {
  const t = trace;
  const inp = t.inputs || {};
  const out = t.output || {};
  return (
    <div>
      <TraceSection title="Investor vs Property Match">
        <TraceRow label="Asking Price" value={fmtAED(inp.asking_price)} source="Qdrant listing" />
        <TraceRow label="Budget Range" value={`${fmtAED(inp.budget_min)} – ${fmtAED(inp.budget_max)}`} source="From questionnaire" />
        <TraceRow label="Within Budget" value={inp.within_budget ? 'Yes' : 'No'} source={inp.budget_overflow_pct > 0 ? `Overflow: ${inp.budget_overflow_pct}%` : 'Price within budget'} />
        <TraceRow label="Investor Goal" value={inp.goal || '—'} source="From questionnaire" />
        <TraceRow label="Risk Score" value={`${inp.risk_overall ?? '—'}/100`} source="From risk engine" />
        <TraceRow label="Developer Score" value={`${inp.developer_score ?? '—'}/100`} source="From developer_scores.json" />
      </TraceSection>

      <TraceSection title="Result">
        <TraceRow label="Fit Score" value={`${out.fitScore ?? '—'}/100`} source={t.formula || 'Weighted dimensions with budget penalty'} />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> This property is priced at <strong>{fmtAED(inp.asking_price)}</strong> and your budget is <strong>{fmtAED(inp.budget_min)}–{fmtAED(inp.budget_max)}</strong>.
        {inp.within_budget ? ' The price is within your budget.' : ` The price exceeds your budget by ${inp.budget_overflow_pct}%.`}
        The fit score of <strong>{out.fitScore}/100</strong> measures how well this property matches your investor profile.
      </LaymanExplanation>

      <DataSource>
        Data source: Investor questionnaire + property data + risk score + developer score. Budget mismatch hard-caps fit at 40.
      </DataSource>
    </div>
  );
}

function PropertyTrace({ trace }: { trace: any }) {
  const t = trace;
  return (
    <div>
      <TraceSection title="Property Data Source">
        <TraceRow label="Project" value={t.project || t.name || '—'} source="Qdrant property listing" />
        <TraceRow label="Area" value={t.area || '—'} source="Qdrant property listing" />
        <TraceRow label="Developer" value={t.developer || '—'} source="Qdrant → developer_scores.json" />
        <TraceRow label="Bedroom" value={t.bedType || '—'} source="Qdrant property listing" />
        <TraceRow label="Size" value={`${t.sizeSqft ?? '—'} sqft`} source="Qdrant property listing" />
        <TraceRow label="Asking Price" value={fmtAED(t.askingPrice)} source="Qdrant property listing" />
        <TraceRow label="Price/sqft" value={`${fmtNum(t.priceSqft)} AED/sqft`} source={`asking price ÷ size`} />
        <TraceRow label="Status" value={t.status || '—'} source="Off-plan or ready" />
        <TraceRow label="Construction Years" value={t.constructionYears ? `${t.constructionYears} years` : 'Default 2.5'} source={t.constructionYears ? 'Qdrant listing' : 'Fallback (no data in Qdrant)'} />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> This property is a <strong>{t.bedType}</strong> in <strong>{t.project}</strong> by <strong>{t.developer}</strong>, located in <strong>{t.area}</strong>.
        It's priced at <strong>{fmtAED(t.askingPrice)}</strong> ({fmtNum(t.priceSqft)} AED/sqft for {t.sizeSqft} sqft).
        All property data comes from Qdrant (the property listing database).
      </LaymanExplanation>

      <DataSource>
        Data source: Qdrant property database (listing details, price, size, developer, handover date). Developer score from developer_scores.json.
      </DataSource>
    </div>
  );
}

function PaymentPlanTrace({ trace }: { trace: any }) {
  const t = trace;
  const plans = t.plans || (t.downPaymentPct ? [t] : []);
  return (
    <div>
      <TraceSection title="Payment Plan Structure">
        <TraceRow label="Down Payment" value={`${t.downPaymentPct ?? '—'}%`} source={t.askingPrice ? `${fmtAED(t.askingPrice * (t.downPaymentPct || 0) / 100)}` : 'Qdrant listing'} />
        <TraceRow label="During Construction" value={`${t.duringConstructionPct ?? '—'}%`} source="Paid in installments over construction period" />
        <TraceRow label="On Handover" value={`${t.onHandoverPct ?? '—'}%`} source="Final payment at key handover" />
        <TraceRow label="Total" value={`${(t.downPaymentPct || 0) + (t.duringConstructionPct || 0) + (t.onHandoverPct || 0)}%`} source="Should equal 100%" />
        {t.isComplete != null && <TraceRow label="Plan Complete" value={t.isComplete ? 'Yes' : 'No'} source="All percentages sum to 100%" />}
      </TraceSection>

      {t.installments && t.installments.length > 0 && (
        <TraceSection title="Installment Schedule">
          {t.installments.map((inst: any, i: number) => (
            <TraceRow key={i} label={inst.label || inst.milestone || `Installment ${i + 1}`} value={`${inst.percentage || inst.percent}%`} source="From Qdrant payment plan" />
          ))}
        </TraceSection>
      )}

      <LaymanExplanation>
        <strong>In plain English:</strong> You pay <strong>{t.downPaymentPct}%</strong> upfront as a down payment,
        <strong> {t.duringConstructionPct}%</strong> during construction (in installments),
        and <strong>{t.onHandoverPct}%</strong> at handover when you get the keys.
        This structure affects your cash flow timing and leverage.
      </LaymanExplanation>

      <DataSource>
        Data source: Qdrant property listing (payment plan field). Extracted by matching project name to Qdrant project cache.
      </DataSource>
    </div>
  );
}

function ConstructionTrace({ trace }: { trace: any }) {
  const t = trace;
  return (
    <div>
      <TraceSection title="Construction Timeline">
        <TraceRow label="Construction Period" value={`${t.constructionYears ?? '2.5'} years`} source={t.constructionYears ? 'Qdrant listing' : 'Default fallback (2.5 years)'} />
        <TraceRow label="Handover Date" value={t.handoverDate || '—'} source={t.handoverSource || 'Qdrant listing'} />
        <TraceRow label="Handover Confidence" value={t.handoverConfidence || '—'} source="Based on data quality" />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> Construction is expected to take <strong>{t.constructionYears ?? 2.5} years</strong>.
        {t.handoverDate ? ` Estimated handover: ${t.handoverDate}.` : ' No specific handover date available — using estimate.'}
        {t.constructionYears == null && ' Note: Qdrant does not have construction timeline data for this project, so the default of 2.5 years is used.'}
      </LaymanExplanation>

      <DataSource>
        Data source: Qdrant property listing (construction_years, expected_completion). Default fallback: 2.5 years when no data available.
      </DataSource>
    </div>
  );
}

function MarketTrace({ trace }: { trace: any }) {
  const t = trace;
  return (
    <div>
      <TraceSection title="Area Market Data">
        <TraceRow label="Area" value={t.area || '—'} source="Property location" />
        <TraceRow label="Area Sales Count" value={`${t.areaSalesCount ?? '—'} transactions`} source="DLD transactions for this area" />
        <TraceRow label="Area Rentals Count" value={`${t.areaRentalsCount ?? '—'} contracts`} source="DLD Ejari rentals for this area" />
        <TraceRow label="Median Price/sqft" value={`${fmtNum(t.medianPriceSqft)} AED/sqft`} source="From DLD comparable sales" />
        <TraceRow label="Growth Rate" value={`${fmtNum(t.growthRate)}%/yr`} source={t.growthSource || 'DLD project stats'} />
        <TraceRow label="Supply Index" value={`${t.supplyIndex ?? '—'}/100`} source="Based on competing projects in area" />
        <TraceRow label="Liquidity Index" value={`${t.liquidityIndex ?? '—'}/100`} source="Based on transaction turnover rate" />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> The <strong>{t.area}</strong> area has <strong>{t.areaSalesCount} recorded sales</strong> and <strong>{t.areaRentalsCount} rental contracts</strong> in the DLD database.
        Prices have been {'growing' /* placeholder */} at <strong>{fmtNum(t.growthRate)}%/year</strong>.
        Supply risk is <strong>{t.supplyIndex}/100</strong> and liquidity is <strong>{t.liquidityIndex}/100</strong>.
      </LaymanExplanation>

      <DataSource>
        Data source: DLD transaction records (sales, rentals), DLD project stats (growth rate), area-level calculations (supply, liquidity indices).
      </DataSource>
    </div>
  );
}

function ExitStrategyTrace({ trace }: { trace: any }) {
  const t = trace;
  return (
    <div>
      <TraceSection title="Exit Strategy">
        <TraceRow label="Strategy" value={t.exitStrategy || t.strategy || '—'} source="Resolved from investor goal + property status" />
        <TraceRow label="Holding Period" value={t.holdingPeriod || `${t.timelineYears ?? '—'} years`} source="From investor timeline" />
        <TraceRow label="Exit Type" value={t.exitType || '—'} source="Sell at handover, rent then sell, or hold" />
      </TraceSection>

      <TraceSection title="Projected Outcome">
        <TraceRow label="Future Value" value={fmtAED(t.futureValue)} source="Purchase price × (1 + growth)^years" />
        <TraceRow label="Capital Gain" value={fmtAED(t.capitalGain)} source="Future value − purchase price" />
        <TraceRow label="Capital Gain %" value={`${fmtNum(t.capitalGainPct)}%`} source="Gain ÷ price × 100" />
        {t.completionYears && <TraceRow label="Years to Exit" value={`${t.completionYears} years`} source="Construction + holding period" />}
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> The recommended strategy is to <strong>{t.exitStrategy || 'sell at handover'}</strong>.
        {t.exitStrategy === 'flip_handover' || t.exitType === 'flip' ? ' This means buying off-plan, paying installments during construction, and selling at handover for a quick profit.' : ' This means holding the property and either renting it out or waiting for appreciation before selling.'}
        Projected value at exit: <strong>{fmtAED(t.futureValue)}</strong> (a gain of <strong>{fmtAED(t.capitalGain)}</strong>).
      </LaymanExplanation>

      <DataSource>
        Data source: Strategy resolver (goal + property status → exit strategy). Growth projection from DLD data. Flip-at-handover hardcoded for capital_growth + off_plan.
      </DataSource>
    </div>
  );
}
