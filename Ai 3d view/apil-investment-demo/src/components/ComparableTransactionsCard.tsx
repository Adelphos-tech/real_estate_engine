import { formatAED, formatNumber } from './Shared';

const naAED = (v: any): string => {
  if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v)) || v === 0) return 'Insufficient Data';
  return formatAED(v);
};
const naNum = (v: any, suffix = ''): string => {
  if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) return 'N/A';
  return `${v}${suffix}`;
};

export function ComparableTransactionsCard({ property, project }: { property: any; project?: any }) {
  const askingPrice = property.askingPrice || 0;
  const comparablePrice = property.comparablePrice || 0;
  const hasComparables = comparablePrice != null && comparablePrice > 0;
  const calculatedDiff = hasComparables && askingPrice > 0
    ? Math.round(((askingPrice - comparablePrice) / comparablePrice) * 1000) / 10
    : null;
  const priceDifference = calculatedDiff !== null ? calculatedDiff : (property.priceDifference || 0);

  // Price per sqft comparison
  const priceSqft = property.priceSqft || 0;
  const projectPriceSqft = project?.priceSqft || 0;
  const sqftDiff = priceSqft > 0 && projectPriceSqft > 0
    ? Math.round(((priceSqft - projectPriceSqft) / projectPriceSqft) * 1000) / 10
    : null;
  const areaSqft = property.areaSqft || 0;

  return (
    <div className="premium-card p-6">
      <h3 className="font-semibold text-apil-gray-900 mb-4">Comparable Transactions</h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
        <div className="text-center p-4 bg-apil-gray-50 rounded-xl">
          <p className="text-xs text-apil-gray-500 font-medium uppercase">Current Asking</p>
          <p className="text-xl font-bold text-apil-gray-900 mt-1">{formatAED(property.askingPrice)}</p>
        </div>
        <div className="text-center p-4 bg-blue-50 rounded-xl">
          <p className="text-xs text-apil-gray-500 font-medium uppercase">Median Sold</p>
          <p className={`text-xl font-bold mt-1 ${hasComparables ? 'text-apil-blue' : 'text-apil-gray-400'}`}>{naAED(property.comparablePrice)}</p>
        </div>
        <div className="text-center p-4 bg-green-50 rounded-xl">
          <p className="text-xs text-apil-gray-500 font-medium uppercase">Difference</p>
          <p className={`text-xl font-bold mt-1 ${hasComparables ? (priceDifference < 0 ? 'text-green-600' : 'text-orange-600') : 'text-apil-gray-400'}`}>
            {hasComparables ? `${priceDifference > 0 ? '+' : ''}${priceDifference}%` : 'N/A'}
          </p>
        </div>
      </div>

      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-apil-gray-500">Price Per Square Foot</h4>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex justify-between text-xs text-apil-gray-500 mb-1">
              <span>This Property</span>
              <span className="font-bold text-apil-gray-900">AED {formatNumber(property.priceSqft)}/sqft</span>
            </div>
            <div className="h-2 bg-apil-gray-200 rounded-full overflow-hidden">
              <div className="h-full bg-apil-blue rounded-full" style={{ width: `${Math.min(100, ((property.priceSqft || 0) / (project?.priceSqft || property.priceSqft || 1)) * 100)}%` }} />
            </div>
          </div>
          <div className="flex-1">
            <div className="flex justify-between text-xs text-apil-gray-500 mb-1">
              <span>Project Median</span>
              <span className={`font-bold ${project?.priceSqft ? 'text-apil-gray-900' : 'text-apil-gray-400'}`}>{project?.priceSqft ? `AED ${formatNumber(project.priceSqft)}/sqft` : 'Insufficient Data'}</span>
            </div>
            <div className="h-2 bg-apil-gray-200 rounded-full overflow-hidden">
              <div className="h-full bg-apil-gray-400 rounded-full" style={{ width: '100%' }} />
            </div>
          </div>
        </div>
      </div>

      <div className="mt-5 p-4 bg-apil-blue/5 rounded-lg">
        <p className="text-sm text-apil-gray-700">
          {!hasComparables
            ? 'Insufficient comparable sales data. Price cannot be verified against market transactions. Consider requesting recent sales evidence from a local agent.'
            : priceDifference < 0
            ? `This property is priced ${Math.abs(priceDifference)}% below the median comparable sold price.`
            : priceDifference < 5
            ? `This property is priced in line with recent comparable sold transactions. Fair market value.`
            : `This property is priced ${priceDifference}% above comparable sold transactions. Verify justification (view, floor, upgrades).`}
        </p>
        {sqftDiff !== null && Math.abs(sqftDiff) > 20 && hasComparables && (
          <div className="mt-3 pt-3 border-t border-apil-gray-200">
            <p className="text-xs font-semibold text-apil-gray-500 uppercase mb-1">Why the Price Difference?</p>
            <p className="text-xs text-apil-gray-600">
              This property is <strong>AED {priceSqft}/sqft</strong> vs the project median of <strong>AED {projectPriceSqft}/sqft</strong> ({sqftDiff > 0 ? '+' : ''}{sqftDiff}%).
              {sqftDiff < 0
                ? ' The lower price per sqft may be explained by: larger unit size (economies of scale), different floor level, less desirable view, or developer launch pricing incentives.'
                : ' The higher price per sqft may be explained by: premium floor, better view, upgraded finishes, or corner unit positioning.'}
              {areaSqft > 0 && ` Unit size: ${areaSqft.toLocaleString()} sqft.`}
            </p>
            <p className="text-[10px] text-apil-gray-400 mt-1.5">
              Always compare price per sqft — not just total price — to account for unit size differences.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
