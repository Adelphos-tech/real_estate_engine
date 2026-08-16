import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ComparableTransactionsCard } from '../../components/ComparableTransactionsCard';
import { mockPropertyFull, mockPropertySparse, mockProject } from '../fixtures/mockData';

describe('ComparableTransactionsCard', () => {
  it('renders with full property data', () => {
    render(<ComparableTransactionsCard property={mockPropertyFull} project={mockProject} />);
    expect(screen.getByText('Comparable Transactions')).toBeInTheDocument();
    expect(screen.getByText('Current Asking')).toBeInTheDocument();
    expect(screen.getByText('Median Sold')).toBeInTheDocument();
  });

  it('shows price difference', () => {
    render(<ComparableTransactionsCard property={mockPropertyFull} project={mockProject} />);
    expect(screen.getByText('+8.7%')).toBeInTheDocument();
  });

  it('does not crash with sparse data', () => {
    expect(() =>
      render(<ComparableTransactionsCard property={mockPropertySparse} project={undefined} />)
    ).not.toThrow();
  });

  it('does not crash with null priceDifference', () => {
    const prop = { ...mockPropertySparse, priceDifference: null };
    expect(() =>
      render(<ComparableTransactionsCard property={prop} project={mockProject} />)
    ).not.toThrow();
  });

  it('does not crash with undefined priceSqft', () => {
    const prop = { ...mockPropertySparse, priceSqft: undefined };
    expect(() =>
      render(<ComparableTransactionsCard property={prop} project={mockProject} />)
    ).not.toThrow();
  });

  it('shows below market message for negative price difference', () => {
    const prop = { ...mockPropertyFull, priceDifference: -5.2 };
    render(<ComparableTransactionsCard property={prop} project={mockProject} />);
    expect(screen.getByText(/5.2% below the median/)).toBeInTheDocument();
  });
});
