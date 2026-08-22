import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Questionnaire from '../../pages/Questionnaire';

// Mock the API module
vi.mock('../data/api', () => ({
  api: {
    createInvestor: vi.fn().mockResolvedValue({ investor_id: 'test-id-123' }),
  },
  investorSession: {
    setId: vi.fn(),
  },
}));

describe('Questionnaire — Step 24B', () => {
  it('has exactly 6 steps', () => {
    render(
      <BrowserRouter>
        <Questionnaire />
      </BrowserRouter>
    );
    // Initial step shows "1 / 6"
    expect(screen.getByText('1 / 6')).toBeInTheDocument();
  });

  it('does not show Rental Income Priority', () => {
    render(
      <BrowserRouter>
        <Questionnaire />
      </BrowserRouter>
    );
    expect(screen.queryByText(/Rental Income Priority/i)).not.toBeInTheDocument();
  });

  it('does not show Financing Method', () => {
    render(
      <BrowserRouter>
        <Questionnaire />
      </BrowserRouter>
    );
    expect(screen.queryByText(/Financing Method/i)).not.toBeInTheDocument();
  });

  it('does not show Downside Tolerance', () => {
    render(
      <BrowserRouter>
        <Questionnaire />
      </BrowserRouter>
    );
    expect(screen.queryByText(/Downside Tolerance/i)).not.toBeInTheDocument();
  });

  it('captures Investment Objective in step 1', () => {
    render(
      <BrowserRouter>
        <Questionnaire />
      </BrowserRouter>
    );
    expect(screen.getByText('Investment Objective')).toBeInTheDocument();
    expect(screen.getByText('Capital appreciation')).toBeInTheDocument();
  });

  it('captures Budget in step 2', () => {
    render(
      <BrowserRouter>
        <Questionnaire />
      </BrowserRouter>
    );
    // Advance to budget step
    fireEvent.click(screen.getByText('Balanced growth + income'));
    expect(screen.getByText('Budget')).toBeInTheDocument();
    expect(screen.getByText(/Minimum Budget/i)).toBeInTheDocument();
    expect(screen.getByText(/Maximum Budget/i)).toBeInTheDocument();
  });

  it('captures Time Horizon in step 3', () => {
    render(
      <BrowserRouter>
        <Questionnaire />
      </BrowserRouter>
    );
    fireEvent.click(screen.getByText('Balanced growth + income'));
    fireEvent.click(screen.getByText('Continue'));
    expect(screen.getByText('Time Horizon')).toBeInTheDocument();
    expect(screen.getByText('5–10 years')).toBeInTheDocument();
  });

  it('captures Risk Tolerance in step 4', () => {
    render(
      <BrowserRouter>
        <Questionnaire />
      </BrowserRouter>
    );
    fireEvent.click(screen.getByText('Balanced growth + income'));
    fireEvent.click(screen.getByText('Continue'));
    fireEvent.click(screen.getByText('5–10 years'));
    expect(screen.getByText('Risk Tolerance')).toBeInTheDocument();
    expect(screen.getByText('Conservative')).toBeInTheDocument();
  });

  it('captures Property Preferences in step 5', () => {
    render(
      <BrowserRouter>
        <Questionnaire />
      </BrowserRouter>
    );
    fireEvent.click(screen.getByText('Balanced growth + income'));
    fireEvent.click(screen.getByText('Continue'));
    fireEvent.click(screen.getByText('5–10 years'));
    fireEvent.click(screen.getByText('Moderate'));
    expect(screen.getByText('Property Preferences')).toBeInTheDocument();
    expect(screen.getByText('Property Status')).toBeInTheDocument();
    expect(screen.getByText('Property Type')).toBeInTheDocument();
    expect(screen.getByText('Bedrooms')).toBeInTheDocument();
  });

  it('captures Location in step 6', () => {
    render(
      <BrowserRouter>
        <Questionnaire />
      </BrowserRouter>
    );
    fireEvent.click(screen.getByText('Balanced growth + income'));
    fireEvent.click(screen.getByText('Continue'));
    fireEvent.click(screen.getByText('5–10 years'));
    fireEvent.click(screen.getByText('Moderate'));
    fireEvent.click(screen.getByText('Continue'));
    expect(screen.getByText('Location')).toBeInTheDocument();
    expect(screen.getByText('DUBAI_WIDE')).toBeInTheDocument();
  });
});
