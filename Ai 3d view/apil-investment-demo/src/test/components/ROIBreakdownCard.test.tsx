import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ROIBreakdownCard } from '../../components/ROIBreakdownCard';
import { mockPropertyFull, mockPropertySparse, mockPropertyNegativeROI } from '../fixtures/mockData';

describe('ROIBreakdownCard', () => {
  it('renders with full property data', () => {
    render(<ROIBreakdownCard property={mockPropertyFull} />);
    expect(screen.getByText('Your Rental Income')).toBeInTheDocument();
    expect(screen.getByText('12%')).toBeInTheDocument(); // grossROI
    expect(screen.getByText('10.06%')).toBeInTheDocument(); // netROI
  });

  it('shows rent and cost breakdown', () => {
    render(<ROIBreakdownCard property={mockPropertyFull} />);
    expect(screen.getByText('Estimated Annual Rent')).toBeInTheDocument();
    expect(screen.getByText('Building Service Charges')).toBeInTheDocument();
    expect(screen.getByText('Property Management')).toBeInTheDocument();
    expect(screen.getByText('Empty Periods')).toBeInTheDocument();
    expect(screen.getByText('Your Take-Home Income')).toBeInTheDocument();
  });

  it('does not crash with sparse/empty data', () => {
    expect(() => render(<ROIBreakdownCard property={mockPropertySparse} />)).not.toThrow();
    expect(screen.getByText('Your Rental Income')).toBeInTheDocument();
  });

  it('does not crash with undefined fields', () => {
    const prop = { ...mockPropertySparse, estimatedRent: undefined, vacancyRate: undefined };
    expect(() => render(<ROIBreakdownCard property={prop} />)).not.toThrow();
  });

  it('handles negative ROI correctly', () => {
    render(<ROIBreakdownCard property={mockPropertyNegativeROI} />);
    expect(screen.getByText('Your Rental Income')).toBeInTheDocument();
    // Negative ROI should show red text
    const netROIElement = screen.getByText('-0.5%');
    expect(netROIElement).toHaveClass('text-red-500');
  });

  it('shows vacancy allowance percentage', () => {
    render(<ROIBreakdownCard property={mockPropertyFull} />);
    expect(screen.getByText(/5% vacancy allowance/)).toBeInTheDocument();
  });

  it('shows plain English explainer', () => {
    render(<ROIBreakdownCard property={mockPropertyFull} />);
    expect(screen.getByText(/healthy rental yield|below the 5%|lose money/i)).toBeInTheDocument();
  });
});
