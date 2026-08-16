import {
  CheckCircle2, AlertTriangle, TrendingUp, Building2, MapPin, Award,
  DollarSign, Calendar, Home, ImageIcon, CreditCard, Target
} from 'lucide-react';
import { ScoreRing, ScoreBadge, RiskBadge, formatAED, formatNumber } from './Shared';

const safeVal = (v: any): number | null => {
  if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) return null;
  return v;
};
const fmtPct = (v: any, prefix = ''): string => {
  const n = safeVal(v);
  if (n === null) return 'N/A';
  return `${n > 0 ? prefix : ''}${n}%`;
};
const fmtAEDsafe = (v: any): string => {
  const n = safeVal(v);
  if (n === null) return 'N/A';
  return formatAED(n);
};
const fmtNumSafe = (v: any): string => {
  const n = safeVal(v);
  if (n === null) return 'N/A';
  return formatNumber(n);
};
const scoreOrNA = (v: any): number | null => {
  const n = safeVal(v);
  return n === null ? null : n;
};

export function isOffplanV2(rec: any): boolean {
  return rec?.propertyType === 'offplan' || rec?.status === 'offplan';
}

export function OffplanOverviewSection({ property, topRec }: any) {
  const overallScore = topRec?.investmentScore ?? property.offplanScore ?? null;
  const recommendation = topRec?.recommendation || 'HOLD';
  const stars = overallScore != null ? (overallScore >= 90 ? 5 : overallScore >= 80 ? 4 : overallScore >= 70 ? 3 : overallScore >= 60 ? 2 : 1) : 0;
  const recColor = recommendation.includes('STRONG') ? '#16a34a' : recommendation === 'BUY' ? '#16a34a' : recommendation === 'NEGOTIATE' ? '#f59e0b' : recommendation === 'HOLD' ? '#f59e0b' : recommendation === 'AVOID' ? '#dc2626' : '#f97316';
  const recBg = recommendation.includes('STRONG') || recommendation === 'BUY' ? 'bg-green-50' : recommendation === 'NEGOTIATE' || recommendation === 'HOLD' ? 'bg-amber-50' : 'bg-red-50';

  const fairValue = topRec?.fairValue || {};
  const priceOpp = topRec?.priceOpportunity || {};
  const futureApp = topRec?.futureAppreciation || {};
  const postROI = topRec?.postHandoverROI || {};
  const devData = topRec?.developerData || {};
  const commData = topRec?.communityData || {};
  const liquidity = topRec?.liquidity || {};
  const risk = topRec?.risk || {};
  const listing = topRec?.listingData || {};
  const ppAnalysis = topRec?.paymentPlanAnalysis || {};
  const exitStrats = topRec?.exitStrategies || {};

  // Score breakdown for offplan v2 (off-plan specific weights)
  const breakdownCards = [
    { label: 'Developer', value: safeVal(devData.developerScore), color: '#f59e0b', weight: '25%' },
    { label: 'Price vs Market', value: safeVal(priceOpp.priceOpportunityScore), color: '#1e40af', weight: '20%' },
    { label: 'Payment Plan', value: safeVal(ppAnalysis.paymentPlanScore), color: '#8b5cf6', weight: '15%' },
    { label: 'Future Appreciation', value: safeVal(futureApp.futureAppreciationScore), color: '#16a34a', weight: '10%' },
    { label: 'Supply Risk', value: safeVal(topRec?.scoreBreakdown?.supplyRisk) ?? safeVal(commData.futureSupplyScore), color: '#06b6d4', weight: '10%' },
    { label: 'Liquidity', value: safeVal(liquidity.liquidityScore), color: '#6366f1', weight: '5%' },
    { label: 'Post-Handover ROI', value: safeVal(postROI.roiScore), color: '#ec4899', weight: '5%' },
  ];

  const deductions = breakdownCards
    .filter(c => c.value != null)
    .map(c => ({ label: c.label, points: 100 - (c.value as number), weight: parseFloat(c.weight) / 100 }))
    .filter(d => d.points > 0)
    .sort((a, b) => (b.points * b.weight) - (a.points * a.weight));

  const buyReasons: string[] = [];
  const watchItems: string[] = [];

  if ((priceOpp.priceOpportunityScore || 0) >= 80) buyReasons.push(`Developer price ${fmtPct(priceOpp.priceDifferencePct)} vs fair market value`);
  if ((futureApp.futureAppreciationScore || 0) >= 80) buyReasons.push(`Projected ${fmtPct(futureApp.potentialGainPct)} capital gain over ${futureApp.completionYears} years`);
  if ((devData.developerScore || 0) >= 75) buyReasons.push(`Strong developer (${devData.developerName})`);
  if ((commData.communityScore || 0) >= 75) buyReasons.push(`Excellent community fundamentals`);
  if ((ppAnalysis.paymentPlanScore || 0) >= 85) buyReasons.push(`Favorable payment plan: ${ppAnalysis.downPaymentPct}% down, ${ppAnalysis.structure}`);
  if ((ppAnalysis.equityGainPct || 0) > 100) buyReasons.push(`Equity gain of ${fmtPct(ppAnalysis.equityGainPct)} on down payment (${ppAnalysis.leverageRatio}x leverage)`);
  if ((liquidity.liquidityScore || 0) >= 80) buyReasons.push('High resale liquidity');
  if ((postROI.netROI || 0) >= 8) buyReasons.push(`Healthy post-handover net ROI of ${fmtPct(postROI.netROI)}`);

  if ((devData.developerScore || 0) < 70) watchItems.push(`Developer score ${devData.developerScore}/100 — below average track record`);
  if ((devData.delayRisk || '') === 'High') watchItems.push('High delivery delay risk');
  if ((priceOpp.priceDifferencePct || 0) > 10) watchItems.push(`Priced ${fmtPct(priceOpp.priceDifferencePct)} above fair market value`);
  if ((commData.supplyIndex || 0) > 70) watchItems.push('Significant future supply in area');
  if ((risk.overallRisk || 0) > 30) watchItems.push(`Overall risk score ${risk.overallRisk}/100`);

  const images = listing.images || [];
  const paymentPlans = listing.paymentPlans || [];
  const amenities = listing.amenities || [];
  const highlights = listing.highlights || [];

  return (
    <div className="space-y-6">
      {/* Executive Summary */}
      <div className={`premium-card p-6 ${recBg} border-l-4`} style={{ borderLeftColor: recColor }}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-semibold text-apil-gray-500 uppercase">AI Recommendation</span>
              <span className="text-xs bg-apil-blue/10 text-apil-blue px-2 py-0.5 rounded-full font-medium">Off-Plan</span>
            </div>
            <h2 className="text-3xl font-bold" style={{ color: recColor }}>{recommendation}</h2>
            <div className="flex items-center gap-1 mt-1">
              {[1,2,3,4,5].map(s => (
                <span key={s} className={`text-lg ${s <= stars ? 'text-apil-gold' : 'text-apil-gray-200'}`}>★</span>
              ))}
              <span className="text-xs text-apil-gray-500 ml-2">{overallScore != null ? `${overallScore}/100` : 'N/A'}</span>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-apil-gray-500">Investment Score</p>
            <p className="text-4xl font-bold" style={{ color: recColor }}>{overallScore != null ? overallScore : 'N/A'}</p>
          </div>
        </div>

        {/* Quick Stats — off-plan priority: Price, Future Gain, Down Payment, Developer */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          <div className="p-2.5 bg-white/60 rounded-lg text-center">
            <p className="text-xs text-apil-gray-500">Price vs Market</p>
            <p className="text-lg font-bold" style={{ color: (priceOpp.priceDifferencePct || 0) <= 0 ? '#16a34a' : '#dc2626' }}>
              {fmtPct(priceOpp.priceDifferencePct)}
            </p>
          </div>
          <div className="p-2.5 bg-white/60 rounded-lg text-center">
            <p className="text-xs text-apil-gray-500">Future Gain</p>
            <p className="text-lg font-bold text-green-600">{fmtPct(futureApp.potentialGainPct)}</p>
          </div>
          <div className="p-2.5 bg-white/60 rounded-lg text-center">
            <p className="text-xs text-apil-gray-500">Down Payment</p>
            <p className="text-lg font-bold text-apil-blue">{safeVal(ppAnalysis.downPaymentPct) !== null ? `${ppAnalysis.downPaymentPct}%` : 'N/A'}</p>
          </div>
          <div className="p-2.5 bg-white/60 rounded-lg text-center">
            <p className="text-xs text-apil-gray-500">Developer Score</p>
            <p className="text-lg font-bold" style={{ color: (devData.developerScore || 0) >= 70 ? '#16a34a' : (devData.developerScore || 0) >= 50 ? '#f59e0b' : '#dc2626' }}>
              {scoreOrNA(devData.developerScore) != null ? `${scoreOrNA(devData.developerScore)}/100` : 'N/A'}
            </p>
          </div>
        </div>

        {/* Key Reasons */}
        <div className="mt-4">
          <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-2">Why?</p>
          <ul className="space-y-1.5">
            {(topRec?.reasons || property.reasons || []).slice(0, 5).map((r: string, i: number) => (
              <li key={i} className="flex items-start gap-2 text-sm text-apil-gray-700">
                <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />{r}
              </li>
            ))}
          </ul>
        </div>

        {/* Investment Thesis */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 bg-green-50/50 rounded-lg border border-green-100">
            <p className="text-xs font-semibold text-green-700 uppercase mb-2">Buy Because</p>
            <ul className="space-y-1">
              {buyReasons.length > 0 ? buyReasons.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-apil-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />{r}
                </li>
              )) : <li className="text-sm text-apil-gray-400">No strong buy signals</li>}
            </ul>
          </div>
          <div className="p-4 bg-amber-50/50 rounded-lg border border-amber-100">
            <p className="text-xs font-semibold text-amber-700 uppercase mb-2">Watch</p>
            <ul className="space-y-1">
              {watchItems.length > 0 ? watchItems.map((w, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-apil-gray-700">
                  <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />{w}
                </li>
              )) : <li className="text-sm text-apil-gray-400">No major concerns</li>}
            </ul>
          </div>
        </div>
      </div>

      {/* Property Images */}
      {images.length > 0 && (
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-apil-blue/10 text-apil-blue flex items-center justify-center">
              <ImageIcon className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-apil-gray-900">Property Images</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {images.slice(0, 8).map((img: any, i: number) => (
              <div key={i} className="aspect-video rounded-lg overflow-hidden bg-apil-gray-100">
                <img
                  src={img.url || img}
                  alt={img.alt || property.title}
                  className="w-full h-full object-cover hover:scale-105 transition-transform"
                  loading="lazy"
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Property Description */}
      {listing.description && (
        <div className="premium-card p-6">
          <h3 className="font-semibold text-apil-gray-900 mb-3">About This Property</h3>
          <p className="text-sm text-apil-gray-600 leading-relaxed whitespace-pre-line">
            {listing.description}
          </p>
          {highlights.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {highlights.map((h: any, i: number) => (
                <span key={i} className="text-xs bg-apil-blue/5 text-apil-blue px-3 py-1 rounded-full font-medium">
                  {typeof h === 'string' ? h : h?.label || h?.name || JSON.stringify(h)}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Property Details */}
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-lg bg-apil-gold/10 text-apil-gold flex items-center justify-center">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-apil-gray-900">Property Details</h3>
        </div>
        <h2 className="text-xl font-bold text-apil-gray-900">{property.title}</h2>
        <p className="text-sm text-apil-gray-500">{property.area || 'N/A'} · {property.bedType || 'N/A'} · {fmtAEDsafe(property.askingPrice)}</p>

        <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div><p className="text-xs text-apil-gray-400">Developer Price</p><p className="text-sm font-bold">{fmtAEDsafe(property.askingPrice)}</p></div>
          <div><p className="text-xs text-apil-gray-400">Est. Completed Value</p><p className="text-sm font-bold text-apil-blue">{fmtAEDsafe(fairValue.fairValue)}</p></div>
          <div><p className="text-xs text-apil-gray-400">Size</p><p className="text-sm font-bold">{property.sizeSqft ? `${fmtNumSafe(property.sizeSqft)} sqft` : 'Insufficient data'}</p></div>
          <div><p className="text-xs text-apil-gray-400">Price/sqft</p><p className="text-sm font-bold">{property.sizeSqft && property.priceSqft ? `AED ${fmtNumSafe(property.priceSqft)}` : 'Insufficient data'}</p></div>
          <div><p className="text-xs text-apil-gray-400">Developer</p><p className="text-sm font-bold">{devData.developerName || property.developer || 'N/A'}</p></div>
          <div><p className="text-xs text-apil-gray-400">Category</p><p className="text-sm font-bold">{property.category || 'N/A'}</p></div>
          <div><p className="text-xs text-apil-gray-400">Completion</p><p className="text-sm font-bold">{futureApp.completionYears ? `${futureApp.completionYears} years` : 'N/A'}</p></div>
          <div><p className="text-xs text-apil-gray-400">Status</p><p className="text-sm font-bold capitalize">{property.status || 'offplan'}</p></div>
        </div>
      </div>

      {/* Price Comparison — off-plan specific */}
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-lg bg-blue-50 text-apil-blue flex items-center justify-center">
            <DollarSign className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-apil-gray-900">Price Comparison</h3>
        </div>
        <p className="text-xs text-apil-gray-500 mb-4">
          Developer asking price vs estimated completed value derived from DLD transactions
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
          <div className="p-4 bg-apil-gray-50 rounded-xl text-center">
            <p className="text-xs text-apil-gray-500">Developer Price</p>
            <p className="text-2xl font-bold text-apil-gray-900 mt-1">{fmtAEDsafe(property.askingPrice)}</p>
          </div>
          <div className="p-4 bg-blue-50 rounded-xl text-center">
            <p className="text-xs text-apil-gray-500">Estimated Completed Value</p>
            <p className="text-2xl font-bold text-apil-blue mt-1">{fmtAEDsafe(futureApp.futureValue ?? fairValue.fairValue ?? null)}</p>
            <p className="text-xs text-apil-gray-400 mt-1">At handover</p>
          </div>
          <div className={`p-4 rounded-xl text-center ${(priceOpp.priceDifferencePct || 0) <= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
            <p className="text-xs text-apil-gray-500">Price vs Market Today</p>
            <p className={`text-2xl font-bold mt-1 ${(priceOpp.priceDifferencePct || 0) <= 0 ? 'text-green-600' : 'text-red-500'}`}>
              {fmtPct(priceOpp.priceDifferencePct)}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Community Median/sqft</p>
            <p className="font-semibold">AED {fmtNumSafe(fairValue.communityMedianSqft)}</p>
          </div>
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Project Median/sqft</p>
            <p className="font-semibold">AED {fmtNumSafe(fairValue.projectMedianSqft)}</p>
          </div>
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Location Factor</p>
            <p className="font-semibold">{safeVal(fairValue.locationFactor) !== null ? `${fairValue.locationFactor}x` : 'N/A'}</p>
          </div>
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Project Premium</p>
            <p className="font-semibold">{safeVal(fairValue.projectPremium) !== null ? `${fairValue.projectPremium}x` : 'N/A'}</p>
          </div>
        </div>

        <div className="mt-4 p-4 bg-apil-blue/5 rounded-lg">
          <p className="text-sm text-apil-gray-700">
            <strong className="text-apil-blue">{priceOpp.label || 'Analysis'}:</strong> The developer is asking{' '}
            {Math.abs(priceOpp.priceDifferencePct || 0) < 0.1 ? 'at fair market value' :
             (priceOpp.priceDifferencePct || 0) < 0 ? `${Math.abs(priceOpp.priceDifferencePct).toFixed(1)}% below` :
             `${(priceOpp.priceDifferencePct || 0).toFixed(1)}% above`}{' '}
            the current estimated market value of {fmtAEDsafe(fairValue.fairValue)}. Estimated completed value at handover: {fmtAEDsafe(futureApp.futureValue || fairValue.fairValue)}.
          </p>
        </div>
      </div>

      {/* Future Appreciation */}
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-lg bg-green-50 text-green-600 flex items-center justify-center">
            <TrendingUp className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-apil-gray-900">Future Appreciation Projection</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
          <div className="p-4 bg-apil-gray-50 rounded-xl text-center">
            <p className="text-xs text-apil-gray-500">Purchase Price</p>
            <p className="text-2xl font-bold text-apil-gray-900 mt-1">{fmtAEDsafe(property.askingPrice)}</p>
          </div>
          <div className="p-4 bg-green-50 rounded-xl text-center">
            <p className="text-xs text-apil-gray-500">Projected Future Value</p>
            <p className="text-2xl font-bold text-green-600 mt-1">{fmtAEDsafe(futureApp.futureValue)}</p>
            <p className="text-xs text-apil-gray-400 mt-1">in {futureApp.completionYears || 'N/A'} years</p>
          </div>
          <div className="p-4 bg-green-50 rounded-xl text-center">
            <p className="text-xs text-apil-gray-500">Potential Gain</p>
            <p className="text-2xl font-bold text-green-600 mt-1">{fmtPct(futureApp.potentialGainPct)}</p>
            <p className="text-xs text-apil-gray-400 mt-1">{fmtAEDsafe(futureApp.potentialGain)}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Growth Rate (Annual)</p>
            <p className="font-semibold text-green-600">{fmtPct(futureApp.growthRate)}</p>
          </div>
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Completion Timeline</p>
            <p className="font-semibold">{futureApp.completionYears ? `${futureApp.completionYears} years` : 'N/A'}</p>
          </div>
          <div className="p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500">Appreciation Score</p>
            <p className="font-semibold">{scoreOrNA(futureApp.futureAppreciationScore) != null ? `${scoreOrNA(futureApp.futureAppreciationScore)}/100` : 'N/A'}</p>
          </div>
        </div>
      </div>

      {/* Payment Plan Analysis with Equity Gain */}
      {ppAnalysis && safeVal(ppAnalysis.downPaymentPct) !== null && (
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <CreditCard className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-apil-gray-900">Payment Plan & Equity Gain</h3>
          </div>
          <p className="text-xs text-apil-gray-500 mb-4">{ppAnalysis.structure || 'Payment structure analysis'}</p>

          {/* Payment Structure */}
          <div className="grid grid-cols-3 gap-3 mb-5">
            <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-xs text-apil-gray-500">Down Payment</p>
              <p className="text-xl font-bold text-apil-blue mt-1">{ppAnalysis.downPaymentPct}%</p>
              <p className="text-xs text-apil-gray-400">{fmtAEDsafe(ppAnalysis.downPaymentAmount)}</p>
            </div>
            <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-xs text-apil-gray-500">During Construction</p>
              <p className="text-xl font-bold text-amber-600 mt-1">{ppAnalysis.duringConstructionPct}%</p>
            </div>
            <div className="p-3 bg-apil-gray-50 rounded-lg text-center">
              <p className="text-xs text-apil-gray-500">On Handover</p>
              <p className="text-xl font-bold text-green-600 mt-1">{ppAnalysis.onHandoverPct}%</p>
            </div>
          </div>

          {/* Equity Gain Analysis */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
            <div className="p-4 bg-apil-blue/5 rounded-xl text-center">
              <p className="text-xs text-apil-gray-500">Cash Invested Today</p>
              <p className="text-2xl font-bold text-apil-blue mt-1">{fmtAEDsafe(ppAnalysis.cashInvestedToday)}</p>
              <p className="text-xs text-apil-gray-400 mt-1">Down payment only</p>
            </div>
            <div className="p-4 bg-green-50 rounded-xl text-center">
              <p className="text-xs text-apil-gray-500">Projected Value at Handover</p>
              <p className="text-2xl font-bold text-green-600 mt-1">{safeVal(ppAnalysis.projectedValueAtHandover) != null && ppAnalysis.projectedValueAtHandover > 0 ? fmtAEDsafe(ppAnalysis.projectedValueAtHandover) : 'N/A'}</p>
              <p className="text-xs text-apil-gray-400 mt-1">{safeVal(ppAnalysis.projectedValueAtHandover) != null && ppAnalysis.projectedValueAtHandover > 0 ? 'Based on area growth' : 'Insufficient growth data'}</p>
            </div>
            <div className="p-4 bg-green-50 rounded-xl text-center border-2 border-green-200">
              <p className="text-xs text-apil-gray-500">Equity Gain on Down Payment</p>
              <p className="text-2xl font-bold text-green-600 mt-1">{fmtPct(ppAnalysis.equityGainPct)}</p>
              <p className="text-xs text-apil-gray-400 mt-1">{fmtAEDsafe(ppAnalysis.equityGain)} gain · {ppAnalysis.leverageRatio}x leverage</p>
            </div>
          </div>

          <div className="p-3 bg-apil-gray-50 rounded-lg text-xs text-apil-gray-600">
            <strong>How off-plan leverage works:</strong> You invest {fmtAEDsafe(ppAnalysis.cashInvestedToday)} today as down payment. If the property value rises to {fmtAEDsafe(ppAnalysis.projectedValueAtHandover)} by handover, your equity grows by {fmtPct(ppAnalysis.equityGainPct)} on your invested capital — a {ppAnalysis.leverageRatio}x leverage advantage.
          </div>

          {/* Installment Schedule */}
          {ppAnalysis.installments && ppAnalysis.installments.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-xs font-semibold text-apil-gray-500 uppercase">Installment Schedule</p>
              {ppAnalysis.installments.map((inst: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-3 bg-apil-gray-50 rounded-lg">
                  <div>
                    <span className="text-sm font-medium text-apil-gray-700">{inst.label || `Installment ${i + 1}`}</span>
                    {inst.timing && <p className="text-xs text-apil-gray-400">{inst.timing}</p>}
                  </div>
                  <span className="text-sm font-bold text-apil-gray-900">{inst.percentage}%</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Exit Strategies */}
      {exitStrats && exitStrats.strategies && exitStrats.strategies.length > 0 && (
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-green-50 text-green-600 flex items-center justify-center">
              <Target className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-apil-gray-900">Exit Strategies</h3>
          </div>
          <p className="text-xs text-apil-gray-500 mb-4">Multiple ways to exit this off-plan investment</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {exitStrats.strategies.map((strat: any, i: number) => {
              const isRecommended = exitStrats.recommendedStrategy === strat.id;
              return (
                <div key={i} className={`p-4 rounded-xl border-2 ${isRecommended ? 'border-green-300 bg-green-50/50' : 'border-apil-gray-200 bg-apil-gray-50/50'}`}>
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h4 className="text-sm font-bold text-apil-gray-900">{strat.name}</h4>
                      {isRecommended && <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium mt-1 inline-block">Recommended</span>}
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${strat.difficulty === 'Easy' ? 'bg-green-100 text-green-700' : strat.difficulty === 'Medium' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}`}>{strat.difficulty}</span>
                  </div>
                  <p className="text-xs text-apil-gray-600 mb-3">{strat.description}</p>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {strat.projectedValue && (
                      <div><span className="text-apil-gray-400">Projected Value:</span> <span className="font-semibold">{fmtAEDsafe(strat.projectedValue)}</span></div>
                    )}
                    {strat.profit !== undefined && (
                      <div><span className="text-apil-gray-400">Profit:</span> <span className="font-semibold text-green-600">{fmtAEDsafe(strat.profit)}</span></div>
                    )}
                    {strat.roiOnDownPayment !== undefined && (
                      <div><span className="text-apil-gray-400">ROI on Down Payment:</span> <span className="font-semibold text-green-600">{fmtPct(strat.roiOnDownPayment)}</span></div>
                    )}
                    {strat.annualRent !== undefined && strat.annualRent !== null && (
                      <div><span className="text-apil-gray-400">Annual Rent:</span> <span className="font-semibold">{fmtAEDsafe(strat.annualRent)}</span></div>
                    )}
                    {strat.netROI !== undefined && strat.netROI !== null && (
                      <div><span className="text-apil-gray-400">Net ROI:</span> <span className="font-semibold">{fmtPct(strat.netROI)}</span></div>
                    )}
                  </div>
                  <div className="mt-2 text-xs text-apil-gray-400">
                    <span className="font-medium">Timeline:</span> {strat.timeline}
                  </div>
                  <div className="mt-1 text-xs text-apil-gray-400">
                    <span className="font-medium">Requires:</span> {strat.requirements}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Post-Handover Rental Income — clearly labeled as AFTER completion */}
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-lg bg-pink-50 text-pink-600 flex items-center justify-center">
            <Calendar className="w-5 h-5" />
          </div>
          <h3 className="font-semibold text-apil-gray-900">Rental Income After Handover</h3>
        </div>
        <p className="text-xs text-apil-gray-500 mb-4">Estimated rental income after construction completion. No rental income during construction period.</p>

        {/* Current vs After Handover */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
          <div className="p-4 bg-apil-gray-100 rounded-xl text-center">
            <p className="text-xs text-apil-gray-500">Current Rental Income</p>
            <p className="text-2xl font-bold text-apil-gray-400 mt-1">N/A</p>
            <p className="text-xs text-apil-gray-400 mt-1">Property under construction</p>
          </div>
          <div className="p-4 bg-green-50 rounded-xl text-center">
            <p className="text-xs text-apil-gray-500">Expected After Handover</p>
            <p className="text-2xl font-bold text-green-600 mt-1">{fmtAEDsafe(postROI.estimatedRent)}<span className="text-sm text-apil-gray-400">/year</span></p>
            <p className="text-xs text-apil-gray-400 mt-1">Rental start: After completion (~{futureApp.completionYears || 'N/A'} years)</p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
          <div><p className="text-xs text-apil-gray-400">Est. Annual Rent</p><p className="text-lg font-bold text-green-600">{fmtAEDsafe(postROI.estimatedRent)}</p></div>
          <div><p className="text-xs text-apil-gray-400">Gross ROI</p><p className="text-lg font-bold">{fmtPct(postROI.grossROI)}</p></div>
          <div><p className="text-xs text-apil-gray-400">Net ROI (After Handover)</p><p className="text-lg font-bold text-green-600">{fmtPct(postROI.netROI)}</p></div>
          <div><p className="text-xs text-apil-gray-400">Net Annual Income</p><p className="text-lg font-bold">{fmtAEDsafe(postROI.netAnnualIncome)}</p></div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <div className="p-3 bg-apil-gray-50 rounded-lg flex justify-between">
            <span className="text-apil-gray-600">Service Charge</span>
            <span className="font-semibold">{fmtAEDsafe(postROI.serviceChargeAnnual)}</span>
          </div>
          <div className="p-3 bg-apil-gray-50 rounded-lg flex justify-between">
            <span className="text-apil-gray-600">Management Fee</span>
            <span className="font-semibold">{fmtAEDsafe(postROI.managementFee)}</span>
          </div>
          <div className="p-3 bg-apil-gray-50 rounded-lg flex justify-between">
            <span className="text-apil-gray-600">Vacancy Cost</span>
            <span className="font-semibold">{fmtAEDsafe(postROI.vacancyCost)}</span>
          </div>
        </div>

        <div className="mt-3 p-3 bg-apil-gray-50 rounded-lg text-xs text-apil-gray-500">
          Rent source: <span className="font-medium capitalize">{postROI.rentSource || 'estimated'}</span> · ROI applies only after handover
        </div>
      </div>

      {/* Score Breakdown */}
      <div className="premium-card p-6">
        <h3 className="font-semibold text-apil-gray-900 mb-1">What Makes Up the Score</h3>
        <p className="text-xs text-apil-gray-500 mb-5">The investment score of {overallScore != null ? `${overallScore}/100` : 'N/A'} is based on 7 factors (off-plan specific formula)</p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {breakdownCards.map((card, i) => {
            const v = card.value;
            const verdict = v == null ? 'N/A' : v >= 80 ? 'Excellent' : v >= 65 ? 'Good' : v >= 50 ? 'Fair' : 'Weak';
            const verdictColor = v == null ? 'text-gray-400' : v >= 80 ? 'text-green-600' : v >= 65 ? 'text-blue-600' : v >= 50 ? 'text-amber-600' : 'text-red-500';
            return (
              <div key={i} className="p-4 bg-apil-gray-50 rounded-xl">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-apil-gray-700">{card.label}</span>
                  <span className={`text-xs font-semibold ${verdictColor}`}>{verdict}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-apil-gray-200 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width: `${v != null ? Math.min(100, v) : 0}%`, backgroundColor: card.color }} />
                  </div>
                  <span className="text-sm font-bold" style={{ color: card.color }}>{v != null ? Math.round(v) : 'N/A'}</span>
                </div>
                <p className="text-xs text-apil-gray-400 mt-1">{card.weight} weight</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Things to Keep in Mind */}
      <div className="premium-card p-6">
        <div className="flex items-center gap-2 mb-1">
          <AlertTriangle className="w-5 h-5 text-amber-500" />
          <h3 className="font-semibold text-apil-gray-900">Things to Keep in Mind</h3>
        </div>
        <p className="text-xs text-apil-gray-500 mb-4">Areas where this off-plan property loses points</p>
        <div className="space-y-2.5">
          {deductions.map((d, i) => {
            const verdict = d.points >= 40 ? 'Needs attention' : d.points >= 20 ? 'Could be better' : 'Minor concern';
            return (
              <div key={i} className="flex items-center justify-between p-3 bg-amber-50/50 rounded-lg">
                <div>
                  <span className="text-sm font-medium text-apil-gray-700">{d.label}</span>
                  <p className="text-xs text-amber-600">{verdict}</p>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-1.5 bg-apil-gray-200 rounded-full overflow-hidden">
                    <div className="h-full bg-amber-400 rounded-full" style={{ width: `${Math.min(100, d.points)}%` }} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Payment Plans */}
      {paymentPlans.length > 0 && (
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
              <CreditCard className="w-5 h-5" />
            </div>
            <h3 className="font-semibold text-apil-gray-900">Payment Plans</h3>
          </div>
          <div className="space-y-3">
            {paymentPlans.map((plan: any, i: number) => (
              <div key={i} className="p-4 bg-apil-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-semibold text-apil-gray-700">
                    {plan.title || plan.name || `Plan ${i + 1}`}
                  </span>
                  {plan.milestone && <span className="text-xs text-apil-gray-500">{plan.milestone}</span>}
                </div>
                {plan.description && <p className="text-sm text-apil-gray-600">{plan.description}</p>}
                {plan.installments && Array.isArray(plan.installments) && (
                  <div className="mt-3 space-y-1">
                    {plan.installments.map((inst: any, j: number) => (
                      <div key={j} className="flex justify-between text-xs text-apil-gray-600">
                        <span>{inst.label || inst.milestone || `Installment ${j + 1}`}</span>
                        <span className="font-medium">{inst.percentage || inst.percent}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Amenities */}
      {amenities.length > 0 && (
        <div className="premium-card p-6">
          <h3 className="font-semibold text-apil-gray-900 mb-3">Amenities</h3>
          <div className="flex flex-wrap gap-2">
            {amenities.map((a: any, i: number) => (
              <span key={i} className="text-xs bg-apil-gray-100 text-apil-gray-700 px-3 py-1.5 rounded-full font-medium">
                {typeof a === 'string' ? a : a?.label || a?.name || JSON.stringify(a)}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Risk Factors */}
      {risk.riskFactors && risk.riskFactors.length > 0 && (
        <div className="premium-card p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <h3 className="font-semibold text-apil-gray-900">Risk Factors</h3>
          </div>
          <ul className="space-y-2">
            {risk.riskFactors.map((rf: string, i: number) => (
              <li key={i} className="flex items-start gap-2 text-sm text-apil-gray-700">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 flex-shrink-0 mt-1.5" />{rf}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function OffplanDeveloperSection({ topRec }: any) {
  const devData = topRec?.developerData || {};
  if (!devData.developerName) return null;

  const breakdown = [
    { label: 'Track Record', value: safeVal(devData.trackRecord), weight: '30%' },
    { label: 'Delivery History', value: safeVal(devData.deliveryHistory), weight: '25%' },
    { label: 'Construction Quality', value: safeVal(devData.constructionQuality), weight: '20%' },
    { label: 'Capital Appreciation', value: safeVal(devData.capitalAppreciation), weight: '15%' },
    { label: 'Market Reputation', value: safeVal(devData.marketReputation), weight: '10%' },
  ];

  return (
    <div className="premium-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
            <Award className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-apil-gray-900">Developer — {devData.developerName}</h3>
            <p className="text-xs text-apil-gray-500">
              Delay Risk: <span className={`font-medium ${devData.delayRisk === 'Low' ? 'text-green-600' : devData.delayRisk === 'Medium' ? 'text-amber-600' : 'text-red-500'}`}>{devData.delayRisk || 'N/A'}</span>
              {devData.marketPosition && ` · ${devData.marketPosition}`}
            </p>
          </div>
        </div>
        <ScoreRing score={scoreOrNA(devData.developerScore)} size={80} label="Developer" />
      </div>

      <div className="space-y-3">
        {breakdown.map((b, i) => (
          <div key={i}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="text-sm text-apil-gray-700">{b.label}</span>
                <span className="text-xs text-apil-gray-400">{b.weight}</span>
              </div>
              <span className="text-sm font-bold text-apil-gray-900">{b.value != null ? b.value : 'N/A'}</span>
            </div>
            <div className="h-2 bg-apil-gray-200 rounded-full overflow-hidden">
              <div className={`h-full rounded-full ${b.value != null ? (b.value >= 80 ? 'bg-green-500' : b.value >= 65 ? 'bg-blue-500' : b.value >= 50 ? 'bg-amber-500' : 'bg-red-400') : 'bg-gray-300'}`} style={{ width: `${b.value != null ? Math.min(100, b.value) : 0}%` }} />
            </div>
          </div>
        ))}
      </div>

      {devData.avgResalePremium !== undefined && devData.avgResalePremium !== null && (
        <div className="mt-4 p-3 bg-apil-gray-50 rounded-lg flex justify-between text-sm">
          <span className="text-apil-gray-600">Avg Resale Premium</span>
          <span className="font-semibold text-green-600">{fmtPct(devData.avgResalePremium)}</span>
        </div>
      )}
    </div>
  );
}

export function OffplanCommunitySection({ topRec }: any) {
  const commData = topRec?.communityData || {};
  if (!commData.communityScore) return null;

  const subScores = [
    { label: 'Demand', value: safeVal(commData.demandIndex) },
    { label: 'Growth', value: safeVal(commData.growthIndex) },
    { label: 'Future Supply', value: safeVal(commData.futureSupplyScore) },
    { label: 'Liquidity', value: safeVal(commData.liquidityScore) },
    { label: 'Rental Demand', value: safeVal(commData.rentalDemand) },
    { label: 'Livability', value: safeVal(commData.livabilityIndex) },
    { label: 'Luxury', value: safeVal(commData.luxuryIndex) },
    { label: 'Transport', value: safeVal(commData.transportIndex) },
  ];

  return (
    <div className="premium-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-50 text-apil-blue flex items-center justify-center">
            <MapPin className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-apil-gray-900">Area Profile — {topRec?.area || 'N/A'}</h3>
            <p className="text-xs text-apil-gray-500">Community investment fundamentals</p>
          </div>
        </div>
        <ScoreRing score={scoreOrNA(commData.communityScore)} size={80} label="Community" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-5">
        {subScores.map((s, i) => (
          <div key={i} className="text-center p-3 bg-apil-gray-50 rounded-lg">
            <p className="text-xs text-apil-gray-500 font-medium">{s.label}</p>
            <p className={`text-xl font-bold mt-1 ${s.value === null ? 'text-apil-gray-300' : 'text-apil-gray-900'}`}>
              {s.value === null ? '—' : s.value}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-3 bg-apil-gray-50 rounded-lg">
          <p className="text-xs text-apil-gray-500">12M Growth</p>
          <p className="text-lg font-bold text-green-600">{fmtPct(commData.growth12m, '+')}</p>
        </div>
        <div className="p-3 bg-apil-gray-50 rounded-lg">
          <p className="text-xs text-apil-gray-500">Supply Index</p>
          <p className="text-lg font-bold">{scoreOrNA(commData.supplyIndex) != null ? `${scoreOrNA(commData.supplyIndex)}/100` : 'N/A'}</p>
        </div>
        <div className="p-3 bg-apil-gray-50 rounded-lg">
          <p className="text-xs text-apil-gray-500">Rental Demand</p>
          <p className="text-lg font-bold">{scoreOrNA(commData.rentalDemand) != null ? `${scoreOrNA(commData.rentalDemand)}/100` : 'N/A'}</p>
        </div>
      </div>
    </div>
  );
}

export function OffplanLiquiditySection({ topRec }: any) {
  const liquidity = topRec?.liquidity || {};
  const ppAnalysis = topRec?.paymentPlanAnalysis || {};
  const liqScore = safeVal(liquidity.liquidityScore);
  const sellTime = liqScore == null ? 'N/A' : liqScore >= 80 ? 'High assignment demand' : liqScore >= 60 ? 'Moderate demand' : liqScore >= 40 ? 'Limited demand' : 'Low demand';

  return (
    <div className="premium-card p-6">
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-semibold text-apil-gray-900">Resale & Assignment Liquidity</h3>
        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${
          liqScore == null ? 'bg-gray-100 text-gray-500' : liqScore >= 80 ? 'bg-green-100 text-green-700' : liqScore >= 60 ? 'bg-blue-100 text-blue-700' : 'bg-amber-100 text-amber-700'
        }`}>{liqScore == null ? 'N/A' : liqScore >= 80 ? 'Excellent' : liqScore >= 60 ? 'Good' : 'Moderate'}</span>
      </div>
      <p className="text-xs text-apil-gray-500 mb-5">Assignment demand, transfer restrictions, and payment plan attractiveness</p>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-5">
        <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
          <p className="text-xs text-apil-gray-500">Liquidity Score</p>
          <p className="text-2xl font-bold text-apil-gray-900 mt-1">{liqScore != null ? liqScore : 'N/A'}<span className="text-sm text-apil-gray-400">{liqScore != null ? '/100' : ''}</span></p>
        </div>
        <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
          <p className="text-xs text-apil-gray-500">Assignment Demand</p>
          <p className="text-lg font-bold text-apil-blue mt-1">{sellTime}</p>
        </div>
        <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
          <p className="text-xs text-apil-gray-500">Transaction Volume</p>
          <p className="text-lg font-bold text-apil-gray-900 mt-1">{fmtNumSafe(liquidity.transactionVolume)}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
        <div className="p-3 bg-apil-gray-50 rounded-lg flex justify-between">
          <span className="text-apil-gray-600">Community Liquidity</span>
          <span className="font-semibold">{scoreOrNA(liquidity.communityLiquidity) != null ? `${scoreOrNA(liquidity.communityLiquidity)}/100` : 'N/A'}</span>
        </div>
        <div className="p-3 bg-apil-gray-50 rounded-lg flex justify-between">
          <span className="text-apil-gray-600">Project Liquidity</span>
          <span className="font-semibold">{scoreOrNA(liquidity.projectLiquidity) != null ? `${scoreOrNA(liquidity.projectLiquidity)}/100` : 'N/A'}</span>
        </div>
      </div>

      {ppAnalysis.downPaymentPct && (
        <div className="mt-3 p-3 bg-apil-gray-50 rounded-lg text-xs text-apil-gray-600">
          <strong>Payment plan impact:</strong> {ppAnalysis.downPaymentPct}% down payment with {ppAnalysis.structure}. Lower down payments and favorable installment structures increase assignment marketability.
        </div>
      )}
    </div>
  );
}

export function OffplanFinalVerdict({ property, topRec }: any) {
  const overallScore = topRec?.investmentScore ?? property.offplanScore ?? null;
  const recommendation = topRec?.recommendation || 'HOLD';
  const recColor = recommendation.includes('STRONG') || recommendation === 'BUY' ? '#16a34a' : recommendation === 'NEGOTIATE' || recommendation === 'HOLD' ? '#f59e0b' : '#dc2626';
  const recEmoji = recommendation.includes('STRONG') || recommendation === 'BUY' ? '🟢' : recommendation === 'NEGOTIATE' || recommendation === 'HOLD' ? '🟡' : '🔴';

  const priceOpp = topRec?.priceOpportunity || {};
  const futureApp = topRec?.futureAppreciation || {};
  const postROI = topRec?.postHandoverROI || {};
  const risk = topRec?.risk || {};
  const devData = topRec?.developerData || {};
  const ppAnalysis = topRec?.paymentPlanAnalysis || {};

  const benchmarks = [
    { label: 'This Property (Equity Gain)', return: ppAnalysis.equityGainPct ? `${Math.round(ppAnalysis.equityGainPct)}%` : 'N/A', risk: risk.riskLevel || 'N/A', highlight: true },
    { label: 'Dubai Real Estate', return: '6.8%', risk: 'Medium', note: 'historical benchmark' },
    { label: 'Bank Fixed Deposit', return: '4.0%', risk: 'Very Low', note: 'historical benchmark' },
    { label: 'S&P 500', return: '10.0%', risk: 'High', note: 'historical benchmark' },
  ];

  const mainRisks: string[] = [];
  if ((devData.developerScore || 0) < 70) mainRisks.push(`Developer score ${devData.developerScore}/100 — moderate track record`);
  if ((devData.delayRisk || '') === 'High') mainRisks.push('High delivery delay risk');
  if ((priceOpp.priceDifferencePct || 0) > 5) mainRisks.push(`Priced ${fmtPct(priceOpp.priceDifferencePct)} above fair value`);
  if ((risk.overallRisk || 0) > 30) mainRisks.push(`Overall risk score ${risk.overallRisk}/100`);
  if (mainRisks.length === 0) mainRisks.push('No major risks identified');

  return (
    <div className="premium-card p-6 border-2" style={{ borderColor: recColor }}>
      <div className="text-center mb-5">
        <p className="text-xs font-bold tracking-widest uppercase text-apil-gray-400">Final APIL Decision</p>
      </div>

      <div className="flex items-center justify-center gap-3 mb-6">
        <span className="text-3xl">{recEmoji}</span>
        <div className="text-center">
          <p className="text-2xl font-bold" style={{ color: recColor }}>{recommendation}</p>
          <p className="text-xs text-apil-gray-500">Off-Plan Investment</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
        <div className="text-center p-3 bg-apil-gray-50 rounded-lg">
          <p className="text-xs text-apil-gray-500">Investment Score</p>
          <p className="text-2xl font-bold" style={{ color: recColor }}>{overallScore != null ? overallScore : 'N/A'}<span className="text-sm text-apil-gray-400">{overallScore != null ? '/100' : ''}</span></p>
        </div>
        <div className="text-center p-3 bg-apil-gray-50 rounded-lg">
          <p className="text-xs text-apil-gray-500">Price vs Market</p>
          <p className="text-2xl font-bold" style={{ color: (priceOpp.priceDifferencePct || 0) <= 0 ? '#16a34a' : '#dc2626' }}>{fmtPct(priceOpp.priceDifferencePct)}</p>
        </div>
        <div className="text-center p-3 bg-apil-gray-50 rounded-lg">
          <p className="text-xs text-apil-gray-500">Equity Gain</p>
          <p className="text-2xl font-bold text-green-600">{fmtPct(ppAnalysis.equityGainPct)}</p>
        </div>
        <div className="text-center p-3 bg-apil-gray-50 rounded-lg">
          <p className="text-xs text-apil-gray-500">Developer</p>
          <p className="text-2xl font-bold" style={{ color: (devData.developerScore || 0) >= 70 ? '#16a34a' : '#f59e0b' }}>{scoreOrNA(devData.developerScore)}<span className="text-sm text-apil-gray-400">/100</span></p>
        </div>
      </div>

      <div className="mb-5 p-4 bg-amber-50/50 rounded-lg border border-amber-100">
        <p className="text-xs font-semibold text-amber-700 uppercase mb-2">Main Risks</p>
        <ul className="space-y-1.5">
          {mainRisks.map((risk, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-apil-gray-700">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 flex-shrink-0 mt-1.5" />{risk}
            </li>
          ))}
        </ul>
      </div>

      <div className="mb-5">
        <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-3">Should I Buy This or...</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-apil-gray-200">
                <th className="text-left py-2 px-3 font-semibold text-apil-gray-500">Investment</th>
                <th className="text-center py-2 px-3 font-semibold text-apil-gray-500">Return</th>
                <th className="text-center py-2 px-3 font-semibold text-apil-gray-500">Risk</th>
              </tr>
            </thead>
            <tbody>
              {benchmarks.map((b, i) => (
                <tr key={i} className={`border-b border-apil-gray-100 last:border-0 ${b.highlight ? 'bg-apil-blue/5' : ''}`}>
                  <td className={`py-2.5 px-3 ${b.highlight ? 'font-bold text-apil-blue' : 'font-medium text-apil-gray-700'}`}>{b.label}</td>
                  <td className={`py-2.5 px-3 text-center font-semibold ${b.highlight ? 'text-green-600' : 'text-apil-gray-700'}`}>{b.return}</td>
                  <td className={`py-2.5 px-3 text-center ${b.risk === 'Low' || b.risk === 'Very Low' ? 'text-green-600' : b.risk === 'Medium' ? 'text-amber-600' : 'text-red-500'}`}>{b.risk}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="p-4 bg-apil-gray-50 rounded-lg">
        <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-2">Investment Thesis</p>
        <p className="text-sm text-apil-gray-700 leading-relaxed">
          {recommendation === 'AVOID'
            ? `This off-plan property is priced above fair market value and the investment case is weak. The developer asking price is ${fmtPct(priceOpp.priceDifferencePct)} vs fair value, with a developer score of ${devData.developerScore}/100. Consider negotiating or exploring alternatives.`
            : `This off-plan property in ${topRec?.area || 'Dubai'} offers ${fmtPct(futureApp.potentialGainPct)} projected capital gain over ${futureApp.completionYears} years. ${devData.developerName ? `Developer: ${devData.developerName} (score ${devData.developerScore}/100).` : ''} ${ppAnalysis.downPaymentPct ? `Payment plan: ${ppAnalysis.downPaymentPct}% down payment (${fmtAEDsafe(ppAnalysis.cashInvestedToday)}), ${ppAnalysis.structure}.` : ''} ${ppAnalysis.equityGainPct ? `Equity gain on down payment: ${fmtPct(ppAnalysis.equityGainPct)} (${ppAnalysis.leverageRatio}x leverage).` : ''} ${postROI.netROI ? `Post-handover rental yield: ${fmtPct(postROI.netROI)} net.` : 'Rental yield data unavailable.'}`
          }
        </p>
      </div>
    </div>
  );
}

export function OffplanAlternativesSection({ alternatives, topProperty }: any) {
  if (!alternatives || alternatives.length === 0) {
    return (
      <div className="premium-card p-6 text-center">
        <p className="text-sm text-apil-gray-500">No alternative off-plan properties available for this search criteria.</p>
      </div>
    );
  }

  const topScore = topProperty?.investmentScore ?? topProperty?.offplanScore ?? null;

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-bold text-apil-gray-900">Alternative Off-Plan Opportunities</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {alternatives.map((alt: any, i: number) => {
          const altScore = alt.investmentScore ?? alt.offplanScore ?? null;
          const priceOpp = alt.priceOpportunity || {};
          const futureApp = alt.futureAppreciation || {};
          const altPP = alt.paymentPlanAnalysis || {};
          const images = alt.listingData?.images || [];

          return (
            <div key={i} className="premium-card p-5 group cursor-pointer">
              {images.length > 0 && (
                <div className="aspect-video rounded-lg overflow-hidden bg-apil-gray-100 mb-3">
                  <img
                    src={images[0].url || images[0]}
                    alt={alt.title}
                    className="w-full h-full object-cover"
                    loading="lazy"
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                </div>
              )}
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-apil-gray-900">{alt.title}</h3>
                  <p className="text-xs text-apil-gray-500">{alt.area || 'N/A'} · {alt.bedType || 'N/A'} · {alt.developer || 'N/A'}</p>
                </div>
                <ScoreRing score={altScore} size={56} />
              </div>
              <div className="grid grid-cols-3 gap-2 text-sm">
                <div>
                  <span className="text-apil-gray-400 text-xs">Price</span>
                  <p className="font-semibold">{fmtAEDsafe(alt.askingPrice)}</p>
                </div>
                <div>
                  <span className="text-apil-gray-400 text-xs">vs Market</span>
                  <p className={`font-semibold ${(priceOpp.priceDifferencePct || 0) <= 0 ? 'text-green-600' : 'text-red-500'}`}>
                    {fmtPct(priceOpp.priceDifferencePct)}
                  </p>
                </div>
                <div>
                  <span className="text-apil-gray-400 text-xs">Down Payment</span>
                  <p className="font-semibold text-apil-blue">{altPP.downPaymentPct ? `${altPP.downPaymentPct}%` : 'N/A'}</p>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between">
                <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                  alt.recommendation?.includes('STRONG') || alt.recommendation === 'BUY' ? 'bg-green-100 text-green-700' :
                  alt.recommendation === 'NEGOTIATE' || alt.recommendation === 'HOLD' ? 'bg-amber-100 text-amber-700' :
                  'bg-red-100 text-red-700'
                }`}>{alt.recommendation || 'HOLD'}</span>
                {altScore < topScore && <span className="text-xs text-apil-gray-400">Score {altScore} vs {topScore}</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
