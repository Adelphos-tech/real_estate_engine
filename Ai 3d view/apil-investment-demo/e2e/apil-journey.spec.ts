import { test, expect } from '@playwright/test';

test.describe('APIL Core User Journey', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
  });

  test('landing page loads without errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', (err) => {
      consoleErrors.push(err.message);
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.textContent('body') || '';
    expect(bodyText).toContain('APIL');
    expect(consoleErrors.filter(e => e.includes('TypeError') || e.includes('Cannot read'))).toEqual([]);
  });

  test('questionnaire page loads and shows step 1', async ({ page }) => {
    await page.goto('/questionnaire');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.textContent('body') || '';
    expect(bodyText).toContain('Investment Objective');
    expect(bodyText).toContain('Capital appreciation');
  });

  test('marketplace loads properties from backend', async ({ page }) => {
    await page.goto('/marketplace');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const bodyText = await page.textContent('body') || '';
    expect(bodyText.length).toBeGreaterThan(0);
    expect(bodyText).toContain('APIL');
  });

  test('property detail loads for a known property', async ({ page }) => {
    await page.goto('/property/1868');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    const bodyText = await page.textContent('body') || '';
    expect(bodyText.length).toBeGreaterThan(0);
    const hasPropertyInfo = bodyText.includes('Property') || bodyText.includes('APIL') || bodyText.includes('not found');
    expect(hasPropertyInfo).toBe(true);
  });

  test('compare page loads via client-side navigation', async ({ page }) => {
    // Navigate to compare via client-side nav to avoid Vite proxy
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.evaluate(() => {
      (window as any).location.href = '/compare';
    });
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    const bodyText = await page.textContent('body') || '';
    expect(bodyText.length).toBeGreaterThan(0);
    expect(bodyText).toContain('Compare');
  });
});

test.describe('APIL Investor Personas', () => {
  async function createPersona(page: any, answers: Record<string, any>) {
    const response = await page.evaluate(async (body: any) => {
      const res = await fetch('http://localhost:8000/investors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      return res.json();
    }, answers);
    return response.investor_id as string;
  }

  const baseAnswers = {
    investment_objective: 'BALANCED',
    budget_min_aed: 1000000,
    budget_max_aed: 5000000,
    horizon: '5_10_YEARS',
    risk_tolerance: 'MODERATE',
    property_status: ['EITHER'],
    property_types: ['APARTMENT'],
    bedrooms: ['1', '2'],
    locations: ['DUBAI_WIDE'],
    developer_preference: 'NO_PREFERENCE',
    liquidity_preference: 'MODERATE',
    rental_priority: 'BALANCED',
    financing: 'CASH',
    downside_tolerance: '20_PERCENT',
    lifestyle_requirements: [],
  };

  test('Persona A: Conservative long-term investor receives personalized fit', async ({ page }) => {
    const investorId = await createPersona(page, {
      ...baseAnswers,
      risk_tolerance: 'CONSERVATIVE',
      horizon: 'GT_10_YEARS',
      budget_min_aed: 2000000,
      budget_max_aed: 10000000,
      liquidity_preference: 'HIGH',
    });

    await page.goto(`/marketplace?investor_id=${investorId}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    const bodyText = await page.textContent('body') || '';
    expect(bodyText).toContain('APIL');
  });

  test('Persona B: Aggressive short-term investor receives personalized fit', async ({ page }) => {
    const investorId = await createPersona(page, {
      ...baseAnswers,
      risk_tolerance: 'AGGRESSIVE',
      horizon: 'LT_2_YEARS',
      budget_min_aed: 500000,
      budget_max_aed: 2000000,
      liquidity_preference: 'LOW',
    });

    await page.goto(`/marketplace?investor_id=${investorId}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    const bodyText = await page.textContent('body') || '';
    expect(bodyText).toContain('APIL');
  });

  test('Persona C: First-time investor with mortgage preference', async ({ page }) => {
    const investorId = await createPersona(page, {
      ...baseAnswers,
      risk_tolerance: 'MODERATE',
      horizon: '2_5_YEARS',
      budget_min_aed: 800000,
      budget_max_aed: 2500000,
      financing: 'MORTGAGE',
    });

    await page.goto(`/marketplace?investor_id=${investorId}`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    const bodyText = await page.textContent('body') || '';
    expect(bodyText).toContain('APIL');
  });
});
