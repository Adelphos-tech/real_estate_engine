import { test, expect } from '@playwright/test';

const KNOWN_PROPERTIES = [
  { id: '3693', name: 'Elvira', expected_benchmark: 'AED 2.50M', expected_tx: 9, expected_apil: '+31.6%', expected_conventional: '24.0% below', expected_usable: true },
  { id: '4434', name: 'Lime Gardens', expected_benchmark: 'AED 2.64M', expected_tx: 9, expected_apil: '+25.7%', expected_conventional: '20.4% below', expected_usable: true },
  { id: '701', name: 'Elvira', expected_benchmark: 'AED 4.00M', expected_tx: 8, expected_apil: '+33.3%', expected_conventional: '25.0% below', expected_usable: true },
  { id: '5319', name: 'LIV Residence', expected_benchmark: 'AED 1.92M', expected_tx: 3, expected_apil: '-23.2%', expected_conventional: '30.1% above', expected_usable: true },
  { id: '6956', name: 'Cubix Residences', expected_benchmark: 'AED 2.35M', expected_tx: 6, expected_apil: '+28.9%', expected_conventional: '22.4% below', expected_usable: true },
  { id: '7546', name: 'Helvetia Residences', expected_benchmark: 'AED 1.90M', expected_tx: 27, expected_apil: '+15.3%', expected_conventional: '13.3% below', expected_usable: true },
  { id: '3201', name: 'Binghatti Nova', expected_tx: 0, expected_usable: false },
  { id: '3983', name: 'Sapphire 32', expected_tx: 0, expected_usable: false },
  { id: '7061', name: 'Azizi Mina', expected_tx: 0, expected_usable: false },
  { id: '8057', name: 'Binghatti Royale', expected_tx: 1, expected_usable: false },
  { id: '8201', name: 'Marquise Square', expected_tx: 0, expected_usable: false },
];

// Counters for UI audit
const counters: Record<string, number> = {
  UI_BENCHMARK_MISMATCH: 0,
  UI_TX_COUNT_MISMATCH: 0,
  UI_APIL_MISMATCH: 0,
  UI_CONVENTIONAL_MISMATCH: 0,
  UI_EVIDENCE_STATE_MISMATCH: 0,
  UI_SIGNAL_MISMATCH: 0,
  UI_NAN_RENDER_COUNT: 0,
  STALE_MASTER_BENCHMARK_USED: 0,
  CANONICAL_MARKED_AS_FALLBACK: 0,
  FALLBACK_MARKED_AS_CANONICAL: 0,
  LEVEL2_USED_AS_CANONICAL: 0,
  AREA_FALLBACK_USED_AS_CANONICAL: 0,
  LEVEL2_USED_FOR_SIGNAL: 0,
  AREA_FALLBACK_USED_FOR_SIGNAL: 0,
  LEVEL2_USED_FOR_APIL: 0,
  AREA_FALLBACK_USED_FOR_CONVENTIONAL: 0,
};

test.describe('UI Benchmark Source Validation', () => {
  for (const prop of KNOWN_PROPERTIES) {
    test(`Property ${prop.id} — ${prop.name}`, async ({ page }) => {
      // Navigate with debug panel open
      await page.goto(`/property/${prop.id}?debug=benchmarks`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      // Wait for key content to load
      await page.waitForSelector('text=Property', { timeout: 30000 });

      // Give extra time for async benchmark data
      await page.waitForTimeout(2000);

      // Take screenshot
      await page.screenshot({ path: `e2e/screenshots/property_${prop.id}_${prop.name.replace(/\s+/g, '_')}.png`, fullPage: true });

      // ── Audit: Check for NaN rendering anywhere ──
      const pageText = await page.locator('body').textContent() || '';
      if (pageText.includes('NaN') || pageText.includes('undefined') || pageText.includes('null%')) {
        counters.UI_NAN_RENDER_COUNT++;
        expect(false, `Property ${prop.id}: Page contains NaN/undefined/null%`).toBeTruthy();
      }

      // ── Audit: evidence state ──
      const hasInsufficientEvidence = await page.locator('text=Insufficient verified sales evidence').first().isVisible().catch(() => false);
      const hasInsufficientEvidence2 = await page.locator('text=Not enough DLD transaction data').first().isVisible().catch(() => false);
      const isInsufficient = hasInsufficientEvidence || hasInsufficientEvidence2;

      // ── Audit: debug panel selected source ──
      const debugPanelVisible = await page.locator('text=Benchmark Source Validation').first().isVisible().catch(() => false);
      let selectedSource = '';
      if (debugPanelVisible) {
        const debugPanelText = await page.locator('text=Selected UI Benchmark Source').first().locator('xpath=..').textContent().catch(() => '');
        selectedSource = debugPanelText;
      }

      if (prop.expected_usable) {
        // Should NOT show insufficient evidence
        expect(isInsufficient, `Property ${prop.id}: Should NOT show insufficient evidence`).toBeFalsy();

        // Should show benchmark value somewhere on page
        if (prop.expected_benchmark) {
          const hasBenchmark = pageText.includes(prop.expected_benchmark);
          if (!hasBenchmark) counters.UI_BENCHMARK_MISMATCH++;
          expect(hasBenchmark, `Property ${prop.id}: Expected benchmark ${prop.expected_benchmark} on page`).toBeTruthy();
        }

        // Should show correct transaction count
        if (prop.expected_tx !== undefined) {
          const hasTxCount = pageText.includes(`${prop.expected_tx} DLD`) || pageText.includes(`Transactions used: ${prop.expected_tx}`);
          if (!hasTxCount) counters.UI_TX_COUNT_MISMATCH++;
          expect(hasTxCount, `Property ${prop.id}: Expected ${prop.expected_tx} DLD transactions on page`).toBeTruthy();
        }

        // Should show correct APIL advantage
        if (prop.expected_apil) {
          const hasApil = pageText.includes(prop.expected_apil);
          if (!hasApil) counters.UI_APIL_MISMATCH++;
          expect(hasApil, `Property ${prop.id}: Expected APIL ${prop.expected_apil} on page`).toBeTruthy();
        }

        // Should show correct conventional below benchmark
        if (prop.expected_conventional) {
          const hasConv = pageText.includes(prop.expected_conventional);
          if (!hasConv) counters.UI_CONVENTIONAL_MISMATCH++;
          expect(hasConv, `Property ${prop.id}: Expected conventional ${prop.expected_conventional} on page`).toBeTruthy();
        }

        // Debug panel should show CANONICAL_DLD selected
        if (debugPanelVisible) {
          const isCanonical = selectedSource.includes('CANONICAL_DLD');
          if (!isCanonical) counters.UI_SIGNAL_MISMATCH++;
          expect(isCanonical, `Property ${prop.id}: Selected source should be CANONICAL_DLD`).toBeTruthy();
        }
      } else {
        // Should show insufficient evidence
        expect(isInsufficient, `Property ${prop.id}: Expected insufficient evidence`).toBeTruthy();

        // Should NOT show APIL percentage (only insufficient evidence message)
        const hasApilPercent = /APIL Advantage.*\+?\d+\.?\d*%/.test(pageText);
        if (hasApilPercent) counters.UI_APIL_MISMATCH++;
        expect(hasApilPercent, `Property ${prop.id}: Should NOT show APIL percentage in insufficient-evidence state`).toBeFalsy();

        // Debug panel should show NONE selected
        if (debugPanelVisible) {
          const isNone = selectedSource.includes('NONE');
          if (!isNone) counters.UI_SIGNAL_MISMATCH++;
          expect(isNone, `Property ${prop.id}: Selected source should be NONE`).toBeTruthy();
        }
      }
    });
  }

  test('Summary: all counters should be 0', async () => {
    console.log('UI Audit Counters:', JSON.stringify(counters, null, 2));
    for (const [key, value] of Object.entries(counters)) {
      expect(value, `${key} should be 0`).toBe(0);
    }
  });
});
