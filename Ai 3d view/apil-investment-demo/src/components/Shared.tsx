import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export function ScoreRing({ score, size = 120, label }: { score: number | null | undefined; size?: number; label?: string }) {
  const s = (score != null && !isNaN(score)) ? score : null;
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = s != null ? circumference - (s / 100) * circumference : circumference;
  const color = s == null ? '#9ca3af' : s >= 80 ? '#16a34a' : s >= 70 ? '#f59e0b' : s >= 60 ? '#f97316' : '#ef4444';

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg className="score-ring" width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#e9ecef" strokeWidth="6" />
        <circle
          className="score-ring-circle"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold" style={{ color }}>{s != null ? s : 'N/A'}</span>
        {label && <span className="text-[10px] text-apil-gray-500 font-medium mt-0.5">{label}</span>}
      </div>
    </div>
  );
}

export function ScoreBadge({ score, label }: { score: number | null | undefined; label?: string }) {
  const s = (score != null && !isNaN(score)) ? score : null;
  if (s == null) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-500">
        N/A
      </span>
    );
  }
  const color = s >= 80 ? 'bg-green-100 text-green-700' : s >= 70 ? 'bg-amber-100 text-amber-700' : 'bg-orange-100 text-orange-700';
  const text = label || (s >= 90 ? 'Excellent' : s >= 80 ? 'Strong' : s >= 70 ? 'Fair' : 'Review');
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${color}`}>
      {s} · {text}
    </span>
  );
}

export function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = { Low: 'bg-green-100 text-green-700', Medium: 'bg-amber-100 text-amber-700', High: 'bg-red-100 text-red-700', 'Insufficient Data': 'bg-gray-100 text-gray-500' };
  const label = level === 'Insufficient Data' ? 'Insufficient Data' : `${level || 'N/A'} Risk`;
  return <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${colors[level] || 'bg-gray-100 text-gray-700'}`}>{label}</span>;
}

export function MarketPositionBadge({ position }: { position: string | null | undefined }) {
  const colors: Record<string, string> = {
    'Value Opportunity': 'bg-green-100 text-green-700 border-green-200',
    'Below Market Value': 'bg-green-100 text-green-700 border-green-200',
    'Strong Discount': 'bg-green-100 text-green-700 border-green-200',
    'Discount': 'bg-green-100 text-green-700 border-green-200',
    'Fair Market Value': 'bg-blue-100 text-blue-700 border-blue-200',
    'Premium Pricing': 'bg-amber-100 text-amber-700 border-amber-200',
    'Premium': 'bg-amber-100 text-amber-700 border-amber-200',
    'High Premium': 'bg-red-100 text-red-700 border-red-200',
    'Insufficient Data': 'bg-gray-100 text-gray-500 border-gray-200',
    'Insufficient Comparables': 'bg-gray-100 text-gray-500 border-gray-200',
  };
  return <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${colors[position || ''] || 'bg-gray-100 text-gray-700 border-gray-200'}`}>{position || 'N/A'}</span>;
}

export function GrowthIndicator({ value, suffix = '%' }: { value: number | null | undefined; suffix?: string }) {
  if (value === 0 || value === null || value === undefined) {
    return <span className="inline-flex items-center gap-1 text-apil-gray-500 text-sm font-medium"><Minus className="w-3 h-3" />0{suffix}</span>;
  }
  const positive = value > 0;
  return (
    <span className={`inline-flex items-center gap-1 text-sm font-medium ${positive ? 'text-green-600' : 'text-red-500'}`}>
      {positive ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
      {positive ? '+' : ''}{value}{suffix}
    </span>
  );
}

export function StatCard({ label, value, sublabel, icon }: { label: string; value: string | number; sublabel?: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <div className="premium-card p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-apil-gray-500 font-medium uppercase tracking-wide">{label}</p>
          <p className="text-xl font-bold text-apil-gray-900 mt-1">{value}</p>
          {sublabel && <div className="mt-1">{sublabel}</div>}
        </div>
        {icon && <div className="text-apil-gray-300">{icon}</div>}
      </div>
    </div>
  );
}

export function formatAED(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(n)) return 'N/A';
  const abs = Math.abs(n);
  const sign = n < 0 ? '-' : '';
  if (abs >= 1_000_000) return `AED ${sign}${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `AED ${sign}${(abs / 1_000).toFixed(0)}K`;
  return `AED ${n.toLocaleString()}`;
}

export function formatNumber(n: number | null | undefined): string {
  if (n === null || n === undefined || isNaN(n)) return 'N/A';
  return n.toLocaleString();
}
