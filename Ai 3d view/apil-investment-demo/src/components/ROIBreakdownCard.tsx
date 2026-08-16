import { formatAED } from './Shared';

const na = (v: any, suffix = ''): string => {
  if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) return 'N/A';
  return `${v}${suffix}`;
};
const naAED = (v: any): string => {
  if (v === null || v === undefined || v === '' || (typeof v === 'number' && isNaN(v))) return 'N/A';
  return formatAED(v);
};

export function ROIBreakdownCard({ property, isProjected = false }: { property: any; isProjected?: boolean }) {
  const roi = {
    grossROI: property.grossROI,
    netROI: property.netROI,
    annualRent: property.estimatedRent,
    serviceChargeAnnual: property.serviceChargeAnnual,
    vacancyRate: property.vacancyRate,
    managementFee: property.managementFee,
    netAnnualIncome: property.netAnnualIncome,
  };

  const hasRent = (roi.annualRent || 0) > 0 && roi.annualRent !== null && roi.annualRent !== undefined;
  const netIncomeColor = !hasRent ? 'text-apil-gray-400' : (roi.netAnnualIncome || 0) >= 0 ? 'text-green-600' : 'text-red-500';
  const netRoiColor = !hasRent ? 'text-apil-gray-400' : (roi.netROI || 0) >= 0 ? 'text-green-600' : 'text-red-500';

  return (
    <div className="premium-card p-6">
      <h3 className="font-semibold text-apil-gray-900 mb-1">{isProjected ? 'Projected Rental Income' : 'Your Rental Income'}</h3>
      <p className="text-xs text-apil-gray-500 mb-5">{isProjected ? 'Estimated rental income after completion, based on comparable leases' : 'How much you\'d earn from rent after costs'}</p>

      {/* Headline numbers */}
      <div className="grid grid-cols-2 gap-4 mb-5">
        <div className="text-center p-4 bg-blue-50 rounded-xl">
          <p className="text-xs text-apil-gray-500 font-medium">Before Costs</p>
          <p className="text-2xl font-bold text-apil-blue mt-1">{hasRent ? na(roi.grossROI, '%') : 'N/A'}</p>
          <p className="text-[10px] text-apil-gray-400 mt-0.5">Gross rental yield</p>
        </div>
        <div className="text-center p-4 bg-green-50 rounded-xl">
          <p className="text-xs text-apil-gray-500 font-medium">After Costs</p>
          <p className={`text-2xl font-bold ${netRoiColor} mt-1`}>{hasRent ? na(roi.netROI, '%') : 'N/A'}</p>
          <p className="text-[10px] text-apil-gray-400 mt-0.5">What you actually keep</p>
        </div>
      </div>

      {/* Simple income breakdown */}
      <div className="space-y-2.5">
        <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
          <div>
            <span className="text-sm text-apil-gray-700 font-medium">Estimated Annual Rent</span>
            <p className="text-[10px] text-apil-gray-400">What tenants would pay you</p>
          </div>
          <span className="font-semibold text-green-600">{naAED(roi.annualRent)}</span>
        </div>

        <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
          <div>
            <span className="text-sm text-apil-gray-700">Building Service Charges</span>
            <p className="text-[10px] text-apil-gray-400">Paid to the building management</p>
          </div>
          <span className="font-semibold text-red-500">{hasRent ? `-${naAED(roi.serviceChargeAnnual)}` : 'N/A'}</span>
        </div>

        <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
          <div>
            <span className="text-sm text-apil-gray-700">Property Management</span>
            <p className="text-[10px] text-apil-gray-400">{roi.managementFee > 0 ? 'Agent/management fees' : 'Not modeled'}</p>
          </div>
          <span className="font-semibold text-red-500">{hasRent ? (roi.managementFee > 0 ? `-${naAED(roi.managementFee)}` : 'AED 0') : 'N/A'}</span>
        </div>

        <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
          <div>
            <span className="text-sm text-apil-gray-700">Empty Periods</span>
            <p className="text-[10px] text-apil-gray-400">{roi.vacancyRate > 0 ? `${Math.round(roi.vacancyRate * 100)}% vacancy allowance` : 'Not modeled'}</p>
          </div>
          <span className="font-semibold text-red-500">{hasRent ? (roi.vacancyRate > 0 ? `-${formatAED(Math.round((roi.annualRent || 0) * roi.vacancyRate))}` : 'AED 0') : 'N/A'}</span>
        </div>

        <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg border-t-2 border-green-200">
          <div>
            <span className="text-sm font-semibold text-apil-gray-700">Your Take-Home Income</span>
            <p className="text-[10px] text-apil-gray-400">Per year, after all costs</p>
          </div>
          <span className={`font-bold ${netIncomeColor}`}>{naAED(roi.netAnnualIncome)}</span>
        </div>
      </div>

      {/* Plain English explainer */}
      <div className="mt-4 p-3 bg-apil-blue/5 rounded-lg">
        <p className="text-xs text-apil-gray-600 leading-relaxed">
          {hasRent
            ? `${isProjected ? 'After completion, this property is projected to generate about ' : 'This property generates about '}${formatAED(roi.netAnnualIncome)} per year${isProjected ? ' in rental income' : ' after all costs'}. That's a ${roi.netROI}% return on your investment. ${roi.netROI >= 5 ? 'Slightly above area average but supported by limited rental evidence.' : roi.netROI > 0 ? 'This yield is below the 5% typically considered good for rental income.' : 'The costs exceed the rental income — you would lose money each year on rent alone.'}`
            : 'No rental data is available for this unit type. ROI cannot be calculated. Consider verifying rental rates with a local agent before making investment decisions.'
          }
        </p>
      </div>
    </div>
  );
}
