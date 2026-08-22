import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  formatAED,
  formatNumber,
  ScoreRing,
  ScoreBadge,
  RiskBadge,
  MarketPositionBadge,
  GrowthIndicator,
  StatCard,
} from '../../components/Shared';

describe('formatAED', () => {
  it('formats millions correctly', () => {
    expect(formatAED(3_465_820)).toBe('AED 3.5M');
  });

  it('formats thousands correctly', () => {
    expect(formatAED(125_000)).toBe('AED 125K');
  });

  it('formats small numbers correctly', () => {
    expect(formatAED(500)).toBe('AED 500');
  });

  it('handles null', () => {
    expect(formatAED(null)).toBe('N/A');
  });

  it('handles undefined', () => {
    expect(formatAED(undefined)).toBe('N/A');
  });

  it('handles NaN', () => {
    expect(formatAED(NaN)).toBe('N/A');
  });

  it('handles zero', () => {
    expect(formatAED(0)).toBe('AED 0');
  });

  it('handles negative numbers', () => {
    expect(formatAED(-5000)).toBe('AED -5K');
  });
});

describe('formatNumber', () => {
  it('formats numbers with commas', () => {
    expect(formatNumber(1_234_567)).toBe('1,234,567');
  });

  it('handles null', () => {
    expect(formatNumber(null)).toBe('N/A');
  });

  it('handles undefined', () => {
    expect(formatNumber(undefined)).toBe('N/A');
  });

  it('handles NaN', () => {
    expect(formatNumber(NaN)).toBe('N/A');
  });
});

describe('ScoreRing', () => {
  it('renders with valid score', () => {
    render(<ScoreRing score={85} size={80} label="Overall" />);
    expect(screen.getByText('85')).toBeInTheDocument();
    expect(screen.getByText('Overall')).toBeInTheDocument();
  });

  it('does not crash with null score', () => {
    render(<ScoreRing score={null} size={80} />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('does not crash with undefined score', () => {
    render(<ScoreRing score={undefined} size={80} />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('does not crash with NaN score', () => {
    render(<ScoreRing score={NaN} size={80} />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });
});

describe('ScoreBadge', () => {
  it('renders with valid score', () => {
    render(<ScoreBadge score={90} />);
    expect(screen.getByText(/90/)).toBeInTheDocument();
    expect(screen.getByText(/Excellent/)).toBeInTheDocument();
  });

  it('does not crash with null score', () => {
    render(<ScoreBadge score={null} />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('does not crash with undefined score', () => {
    render(<ScoreBadge score={undefined} />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });
});

describe('RiskBadge', () => {
  it('renders Low risk', () => {
    render(<RiskBadge level="Low" />);
    expect(screen.getByText('Low Risk')).toBeInTheDocument();
  });

  it('renders Medium risk', () => {
    render(<RiskBadge level="Medium" />);
    expect(screen.getByText('Medium Risk')).toBeInTheDocument();
  });

  it('does not crash with unknown level', () => {
    render(<RiskBadge level="Unknown" />);
    expect(screen.getByText('Unknown Risk')).toBeInTheDocument();
  });

  it('does not crash with null level', () => {
    render(<RiskBadge level={null as any} />);
    expect(screen.getByText('N/A Risk')).toBeInTheDocument();
  });

  it('does not crash with undefined level', () => {
    render(<RiskBadge level={undefined as any} />);
    expect(screen.getByText('N/A Risk')).toBeInTheDocument();
  });
});

describe('MarketPositionBadge', () => {
  it('renders known positions', () => {
    const { rerender } = render(<MarketPositionBadge position="Below Market Value" />);
    expect(screen.getByText('Below Market Value')).toBeInTheDocument();

    rerender(<MarketPositionBadge position="Premium Pricing" />);
    expect(screen.getByText('Premium Pricing')).toBeInTheDocument();
  });

  it('does not crash with null', () => {
    render(<MarketPositionBadge position={null} />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('does not crash with undefined', () => {
    render(<MarketPositionBadge position={undefined} />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });
});

describe('GrowthIndicator', () => {
  it('renders positive growth', () => {
    render(<GrowthIndicator value={15} />);
    expect(screen.getByText('+15%')).toBeInTheDocument();
  });

  it('renders negative growth', () => {
    render(<GrowthIndicator value={-5} />);
    expect(screen.getByText('-5%')).toBeInTheDocument();
  });

  it('renders zero growth', () => {
    render(<GrowthIndicator value={0} />);
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('does not crash with null', () => {
    render(<GrowthIndicator value={null} />);
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('does not crash with undefined', () => {
    render(<GrowthIndicator value={undefined} />);
    expect(screen.getByText('0%')).toBeInTheDocument();
  });
});

describe('StatCard', () => {
  it('renders with all props', () => {
    render(<StatCard label="Price" value="AED 1.2M" sublabel={<span>sub</span>} />);
    expect(screen.getByText('Price')).toBeInTheDocument();
    expect(screen.getByText('AED 1.2M')).toBeInTheDocument();
    expect(screen.getByText('sub')).toBeInTheDocument();
  });

  it('renders with minimal props', () => {
    render(<StatCard label="Score" value={85} />);
    expect(screen.getByText('Score')).toBeInTheDocument();
    expect(screen.getByText('85')).toBeInTheDocument();
  });
});
