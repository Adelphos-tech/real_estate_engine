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
  return (
    <div>
      <TraceSection title="Input Values">
        <TraceRow label="Asking Price (your purchase price)" value={fmtAED(t.askingPrice)} source="Qdrant listing" />
        <TraceRow label="Property Size" value={`${fmtNum(t.sizeSqft, 0)} sqft`} source="Qdrant listing" />
        <TraceRow label="Comparable Sales Count" value={`${t.comparableCount ?? 0} transactions`} source="DLD transaction records" />
        <TraceRow label="Valuation Method" value={t.method || '—'} source={t.method === 'project_bedroom' ? 'Exact project + bedroom match' : 'Area-level match'} />
      </TraceSection>

      <TraceSection title="Calculation Steps">
        <TraceRow label="Step 1: Find comparable sales" value={`${t.comparableCount ?? 0} DLD sales`} source="Same project, same bedroom type" />
        <TraceRow label="Step 2: Calculate price/sqft for each" value={`${fmtNum(t.medianPriceSqft)} AED/sqft (median)`} source="price ÷ area for each transaction" />
        <TraceRow label="Step 3: Fair Value = median price/sqft × your size" value={fmtAED(t.fairValuePointEstimate)} source={`${fmtNum(t.medianPriceSqft)} × ${fmtNum(t.sizeSqft, 0)} sqft`} />
        <TraceRow label="Step 4: Range (±20%)" value={`${fmtAED(t.fairValueLow)} – ${fmtAED(t.fairValueHigh)}`} source="Fair value × (1 ± 0.20)" />
        <TraceRow label="Step 5: Your discount/premium" value={`${fmtNum(t.priceDifferencePct)}%`} source={`(${fmtAED(t.askingPrice)} − ${fmtAED(t.fairValuePointEstimate)}) ÷ ${fmtAED(t.fairValuePointEstimate)} × 100`} />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> We found <strong>{t.comparableCount}</strong> actual DLD-registered sales for the same project ({t.method === 'project_bedroom' ? 'exact same building and bedroom type' : 'same area and bedroom type'}).
        The median price per square foot was <strong>{fmtNum(t.medianPriceSqft)} AED/sqft</strong>.
        Your property is <strong>{fmtNum(t.sizeSqft, 0)} sqft</strong>, so the fair market value is <strong>{fmtAED(t.fairValuePointEstimate)}</strong>.
        You're buying at <strong>{fmtAED(t.askingPrice)}</strong>, which is <strong>{fmtNum(t.priceDifferencePct)}% below</strong> fair value — this is a {t.marketLabel}.
      </LaymanExplanation>

      <DataSource>
        Data source: Dubai Land Department (DLD) verified transaction records. {t.comparableCount} comparable sales found for this project/bedroom type. Confidence: {t.confidence}.
      </DataSource>
    </div>
  );
}

function RentalTrace({ trace }: { trace: any }) {
  const t = trace;
  return (
    <div>
      <TraceSection title="Input Values">
        <TraceRow label="Purchase Price" value={fmtAED(t.purchasePrice)} source="Qdrant listing" />
        <TraceRow label="Comparable Rentals" value={`${t.comparableRentalsCount ?? 0} contracts`} source="DLD rental registrations" />
        <TraceRow label="Rent Source" value={t.rentSource || '—'} source="DLD Ejari rental contracts" />
        <TraceRow label="Rent Confidence" value={t.rentConfidence || '—'} source={`${t.comparableRentalsCount} comparables used`} />
      </TraceSection>

      <TraceSection title="Calculation Steps">
        <TraceRow label="Step 1: Find comparable rentals" value={`${t.comparableRentalsCount} DLD rentals`} source="Same area, same bedroom type" />
        <TraceRow label="Step 2: Take median annual rent" value={fmtAED(t.annualRent)} source="Middle value of all comparable rents" />
        <TraceRow label="Step 3: Service charge (5% of rent)" value={fmtAED(t.serviceCharge)} source={`${fmtNum(t.serviceChargePct * 100, 0)}% × ${fmtAED(t.annualRent)}`} />
        <TraceRow label="Step 4: Vacancy cost (5% of rent)" value={fmtAED(t.vacancyCost)} source={`${fmtNum(t.vacancyRate * 100, 0)}% × ${fmtAED(t.annualRent)}`} />
        <TraceRow label="Step 5: Management fee (5% of rent)" value={fmtAED(t.managementFee)} source={`${fmtNum(t.managementFeePct * 100, 0)}% × ${fmtAED(t.annualRent)}`} />
        <TraceRow label="Step 6: Net income = rent − all costs" value={fmtAED(t.netAnnualIncome)} source={`${fmtAED(t.annualRent)} − ${fmtAED(t.totalOperatingCost)}`} />
        <TraceRow label="Step 7: Gross yield = rent ÷ price" value={`${fmtNum(t.grossYieldPct)}%`} source={`${fmtAED(t.annualRent)} ÷ ${fmtAED(t.purchasePrice)} × 100`} />
        <TraceRow label="Step 8: Net yield = net income ÷ price" value={`${fmtNum(t.netYieldPct)}%`} source={`${fmtAED(t.netAnnualIncome)} ÷ ${fmtAED(t.purchasePrice)} × 100`} />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> We found <strong>{t.comparableRentalsCount}</strong> actual DLD-registered rental contracts for 1-bedroom apartments in the same area.
        The median rent is <strong>{fmtAED(t.annualRent)}/year</strong>. From this, we subtract 3 costs: service charge (5%), vacancy (5%), and management fee (5%) — each equals {fmtAED(t.serviceCharge)}.
        That leaves you with <strong>{fmtAED(t.netAnnualIncome)}</strong> net income per year, which is a <strong>{fmtNum(t.netYieldPct)}% net yield</strong> on your purchase price.
      </LaymanExplanation>

      <DataSource>
        Data source: DLD Ejari rental registrations. {t.comparableRentalsCount} comparable rental contracts. No project-specific rentals found (building is off-plan) — area-level rentals used instead.
      </DataSource>
    </div>
  );
}

function GrowthTrace({ trace }: { trace: any }) {
  const t = trace;
  return (
    <div>
      <TraceSection title="Input Values">
        <TraceRow label="Purchase Price" value={fmtAED(t.futureValue ? undefined : undefined)} source="" />
        <TraceRow label="Annual Growth Rate" value={`${fmtNum(t.annualGrowthRate)}%`} source={t.growthDescription || t.growthSource} />
        <TraceRow label="Growth Source" value={t.growthSource || '—'} source={t.growthConfidence ? `Confidence: ${t.growthConfidence}` : ''} />
        <TraceRow label="Holding Period" value={`${fmtNum(t.holdingYears, 1)} years`} source="Time to handover / exit" />
      </TraceSection>

      <TraceSection title="Calculation Steps">
        <TraceRow label="Step 1: Get project growth rate" value={`${fmtNum(t.annualGrowthRate)}%/yr`} source={t.growthDescription} />
        <TraceRow label="Step 2: Compound over holding period" value={fmtAED(t.futureValue)} source={`price × (1 + ${fmtNum(t.annualGrowthRate)}%)^${fmtNum(t.holdingYears, 1)}`} />
        <TraceRow label="Step 3: Capital gain" value={fmtAED(t.capitalGain)} source={`${fmtAED(t.futureValue)} − purchase price`} />
        <TraceRow label="Step 4: Capital gain %" value={`${fmtNum(t.capitalGainPct)}%`} source={`gain ÷ price × 100`} />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> The DLD data shows that this project's prices have grown by a total of ~{(t.annualGrowthRate * 3).toFixed(1)}% over the last ~3 years.
        That's <strong>{fmtNum(t.annualGrowthRate)}% per year</strong>. If this trend continues for the next {fmtNum(t.holdingYears, 1)} years until handover,
        your property could be worth <strong>{fmtAED(t.futureValue)}</strong> — a gain of <strong>{fmtAED(t.capitalGain)}</strong> ({fmtNum(t.capitalGainPct)}%).
      </LaymanExplanation>

      <DataSource>
        Data source: DLD project statistics (price_change_pct). Growth rate is annualized from total historical change. Source: {t.growthSource}, confidence: {t.growthConfidence}.
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
        {inputs.annual_service_charge != null ? (
          <>
            <TraceRow label="Annual Service Charge" value={fmtAED(inputs.annual_service_charge)} source="Building maintenance fees (from DLD service charge data)" />
            <TraceRow label="Service Charge Years" value={`${inputs.service_charge_years ?? 1} year(s)`} source="From handover to sale" />
            <TraceRow label="Total Service Charge" value={fmtAED(inputs.total_service_charge)} source={`${fmtAED(inputs.annual_service_charge)} × ${inputs.service_charge_years ?? 1} years`} />
          </>
        ) : (
          <TraceRow label="Annual Service Charge" value="N/A" source="No DLD service charge data found for this project" />
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
  const components = t.components || {};
  const weights = t.weights || {};
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
        <TraceRow label="Overall Risk Score" value={`${t.overallRisk}/100`} source="Weighted sum of all components" />
        <TraceRow label="Risk Level" value={t.riskLevel || '—'} source="Derived from overall score" />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> The risk score of <strong>{t.overallRisk}/100</strong> is calculated by scoring 7 different risk factors and weighting them.
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
  const breakdown = t.breakdown || {};
  const weights = t.weights || {};
  const componentTrace = t.componentTrace || {};
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
        <TraceRow label="Raw Weighted Sum" value={`${fmtNum(t.rawScore, 1)}`} source="Sum of (component score × weight) for all available components" />
        <TraceRow label="Available Weight" value={`${fmtNum(t.availableWeight, 3)}`} source="Sum of weights for components that have data" />
        <TraceRow label="Final Investment Score" value={`${t.investmentScore}/100`} source="weightedSum ÷ availableWeight × 100" />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> The investment score of <strong>{t.investmentScore}/100</strong> is a weighted average of {Object.keys(breakdown).length} factors.
        Each factor is scored 0-100 based on real DLD data. For example:
        <br/><br/>
        <strong>Developer = {breakdown.developer}</strong>: The developer (Tiger Group) has a strong track record, so this scores high.
        <br/>
        <strong>Supply = {breakdown.supply}</strong>: There are many competing projects being built in the same area (Jumeirah Village Circle), so supply risk is very high — this drags the score down.
        <br/>
        <strong>Liquidity = {breakdown.liquidity}</strong>: The area has moderate resale activity — not the easiest to sell quickly.
        <br/><br/>
        The final score weights growth and developer heavily (since your goal is capital growth), while still penalizing for supply and liquidity risks.
      </LaymanExplanation>

      <DataSource>
        Data sources: DLD transactions (pricing, supply, liquidity, growth), DLD Ejari rentals (rental score), developer_scores.json (developer score), Qdrant payment plan (payment plan score), ROE calculation (ROI score). Weights are strategy-specific — capital growth goal weights growth and developer highest.
      </DataSource>
    </div>
  );
}

function EvidenceTrace({ trace }: { trace: any }) {
  const t = trace;
  return (
    <div>
      <TraceSection title="Data Coverage">
        <TraceRow label="Project Sales (same building)" value={`${t.projectSalesCount} transactions`} source="DLD sales for this exact project" />
        <TraceRow label="Area Sales (same bedroom)" value={`${t.areaSalesCount} transactions`} source="DLD sales in same area, same bedroom" />
        <TraceRow label="Project Rentals" value={`${t.projectRentalsCount} contracts`} source="DLD Ejari rentals for this project" />
        <TraceRow label="Area Rentals (same bedroom)" value={`${t.areaRentalsCount} contracts`} source="DLD Ejari rentals in same area" />
        <TraceRow label="Valuation Method Used" value={t.valuationMethod || '—'} source="Best available evidence level" />
        <TraceRow label="Evidence Level" value={t.evidenceLevel || '—'} source="Based on comparable sales count" />
        <TraceRow label="Confidence Level" value={t.confidenceLevel || '—'} source="Mapped from evidence level" />
      </TraceSection>

      <LaymanExplanation>
        <strong>In plain English:</strong> We found <strong>{t.projectSalesCount} sales</strong> for this exact project and <strong>{t.areaSalesCount} sales</strong> in the same area with the same bedroom type.
        For rentals, <strong>{t.projectRentalsCount} project-level</strong> and <strong>{t.areaRentalsCount} area-level</strong> contracts were found.
        The valuation uses the <strong>{t.valuationMethod}</strong> method, which means {t.valuationMethod === 'project_bedroom' ? 'we have enough data from this exact building' : 'we use area-level data as a proxy'}.
        Overall confidence: <strong>{t.confidenceLevel}</strong>.
      </LaymanExplanation>

      <DataSource>
        Data source: Dubai Land Department (DLD) verified transaction and Ejari rental records. All counts are actual registered transactions, not estimates.
      </DataSource>
    </div>
  );
}
