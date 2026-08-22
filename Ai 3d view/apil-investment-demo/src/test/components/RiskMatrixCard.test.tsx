import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskMatrixCard } from '../../components/RiskMatrixCard';
import { mockPropertyFull, mockPropertySparse } from '../fixtures/mockData';

describe('RiskMatrixCard', () => {
  it('renders with full property data', () => {
    render(<RiskMatrixCard property={mockPropertyFull} />);
    expect(screen.getByText('What Could Go Wrong')).toBeInTheDocument();
    expect(screen.getByText(/Risk factors that could affect/)).toBeInTheDocument();
  });

  it('shows all 7 risk dimensions with plain English labels', () => {
    render(<RiskMatrixCard property={mockPropertyFull} />);
    // Use getAllByText because some labels also appear in summary sections
    expect(screen.getAllByText('New Supply Nearby').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Developer Track Record')).toBeInTheDocument();
    expect(screen.getByText('Area Popularity')).toBeInTheDocument();
    expect(screen.getByText('Rental Demand')).toBeInTheDocument();
    expect(screen.getByText('Price Stability')).toBeInTheDocument();
    expect(screen.getByText('Construction Risk')).toBeInTheDocument();
    expect(screen.getByText('Price vs Market')).toBeInTheDocument();
  });

  it('shows risk level badge', () => {
    render(<RiskMatrixCard property={mockPropertyFull} />);
    expect(screen.getByText('Low Risk')).toBeInTheDocument();
  });

  it('shows risk factors when present', () => {
    render(<RiskMatrixCard property={mockPropertyFull} />);
    expect(screen.getByText('Things to Watch Out For')).toBeInTheDocument();
    expect(screen.getByText('Developer has average track record')).toBeInTheDocument();
  });

  it('does not crash with sparse data', () => {
    expect(() => render(<RiskMatrixCard property={mockPropertySparse} />)).not.toThrow();
    expect(screen.getByText('What Could Go Wrong')).toBeInTheDocument();
  });

  it('does not crash with missing risk components', () => {
    const prop = { ...mockPropertySparse, risk: { components: null } };
    expect(() => render(<RiskMatrixCard property={prop} />)).not.toThrow();
  });

  it('does not crash with no risk object at all', () => {
    const prop = { ...mockPropertySparse, risk: undefined };
    expect(() => render(<RiskMatrixCard property={prop} />)).not.toThrow();
  });

  it('hides risk factors section when empty', () => {
    const prop = { ...mockPropertyFull, riskFactors: [] };
    render(<RiskMatrixCard property={prop} />);
    expect(screen.queryByText('Things to Watch Out For')).not.toBeInTheDocument();
  });
});
