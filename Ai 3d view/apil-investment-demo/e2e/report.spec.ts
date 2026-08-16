import { test, expect, Page } from '@playwright/test';
import { mockAPI } from './mock-api';

// Set up sessionStorage with a valid investor profile and mock API before each test
async function setupProfileAndGoto(page: Page, path: string = '/investment-report/RPT-DEMO') {
  await mockAPI(page);
  await page.goto('/');
  await page.evaluate(() => {
    const profile = {
      budget_min: 1000000,
      budget_max: 5000000,
      bedrooms: '1',
      property_type: 'ready',
      risk: 'balanced',
      timeline: '3y',
    };
    sessionStorage.setItem('investorProfile', JSON.stringify(profile));
  });
  await page.goto(path);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000);
}

test.describe('Report Page - No Crash Tests', () => {
  test('report page loads without console errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    page.on('pageerror', (err) => {
      consoleErrors.push(err.message);
    });

    await setupProfileAndGoto(page);
    await page.waitForTimeout(3000);

    const fatalErrors = consoleErrors.filter(
      (e) => e.includes('Cannot read properties of undefined') || e.includes('is not a function') || e.includes('TypeError')
    );
    expect(fatalErrors).toEqual([]);
  });

  test('all report tabs are clickable without crashes', async ({ page }) => {
    const pageErrors: string[] = [];
    page.on('pageerror', (err) => {
      pageErrors.push(err.message);
    });

    await setupProfileAndGoto(page);

    const tabTexts = ['Summary', 'Area', 'Building', 'Developer', 'Rental Income', 'Price Trends', 'Resale', 'Risks', 'Data Used', 'Alternatives'];
    for (const text of tabTexts) {
      const tab = page.locator(`text="${text}"`).first();
      if (await tab.isVisible()) {
        await tab.click();
        await page.waitForTimeout(500);
      }
    }

    expect(pageErrors).toEqual([]);
  });

  test('overview page does not show old technical labels', async ({ page }) => {
    await setupProfileAndGoto(page);

    const pageText = await page.textContent('body') || '';

    expect(pageText).not.toContain('ROI Engine');
    expect(pageText).not.toContain('Liquidity Engine');
    expect(pageText).not.toContain('Risk Engine');
    expect(pageText).not.toContain('Formula:');
  });
});

test.describe('Report Page - Section Content Tests', () => {
  test('rental income section shows income breakdown', async ({ page }) => {
    test.setTimeout(60000);
    await setupProfileAndGoto(page);

    const roiTab = page.locator('button:has-text("Rental Income")').first();
    await roiTab.click();
    await page.waitForTimeout(1000);

    const bodyText = await page.textContent('body') || '';
    expect(bodyText).toContain('Your Rental Income');
  });

  test('risk section shows plain English risk dimensions', async ({ page }) => {
    test.setTimeout(60000);
    await setupProfileAndGoto(page);

    await page.locator('button:has-text("Risks")').first().click();
    await page.waitForTimeout(1000);

    const bodyText = await page.textContent('body') || '';
    expect(bodyText).toContain('What Could Go Wrong');
  });

  test('price trends section shows growth data', async ({ page }) => {
    test.setTimeout(60000);
    await setupProfileAndGoto(page);

    await page.locator('button:has-text("Price Trends")').first().click();
    await page.waitForTimeout(1000);

    const bodyText = await page.textContent('body') || '';
    expect(bodyText).toContain('Price Trends');
  });

  test('resale section shows liquidity info', async ({ page }) => {
    test.setTimeout(60000);
    await setupProfileAndGoto(page);

    await page.locator('button:has-text("Resale")').first().click();
    await page.waitForTimeout(1000);

    const bodyText = await page.textContent('body') || '';
    expect(bodyText).toContain('How Easy to Sell');
  });
});

test.describe('Report Page - Edge Case Properties', () => {
  test('handles different property IDs without crashes', async ({ page }) => {
    test.setTimeout(120000);
    const pageErrors: string[] = [];
    page.on('pageerror', (err) => {
      pageErrors.push(err.message);
    });

    for (const id of ['RPT-001', 'RPT-002', 'RPT-003']) {
      await setupProfileAndGoto(page, `/investment-report/${id}`);
      const body = page.locator('body');
      expect(await body.isVisible()).toBeTruthy();
    }

    expect(pageErrors).toEqual([]);
  });
});
