import { chromium } from 'playwright';

const PROPERTIES = [
  { id: '6277', name: 'Binghatti_Emerald_Key_Acceptance' },
  { id: '3693', name: 'Elvira' },
  { id: '4434', name: 'Lime_Gardens' },
  { id: '7061', name: 'Azizi_Mina' },
  { id: '8057', name: 'Binghatti_Royale' },
];

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  // Log ALL console messages for debugging
  page.on('console', msg => {
    console.log(`[${msg.type().toUpperCase()}] ${msg.text()}`);
  });
  page.on('pageerror', err => console.log(`Browser page error: ${err.message}`));

  // Intercept network to see failures
  page.on('requestfailed', req => {
    console.log(`Network FAIL: ${req.method()} ${req.url()} — ${req.failure()?.errorText}`);
  });
  page.on('response', resp => {
    if (!resp.ok()) {
      console.log(`Network ERROR: ${resp.request().method()} ${resp.url()} — ${resp.status()}`);
    }
  });

  for (const prop of PROPERTIES) {
    const url = `http://127.0.0.1:5173/property/${prop.id}?debug=benchmarks`;
    console.log(`\n=== Navigating to ${url} ===`);
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.waitForTimeout(4000);

    // Wait for the page content to load (either property detail or error)
    await page.waitForSelector('text=APIL Investment Signal, text=Failed to fetch', { timeout: 10000 }).catch(() => {});

    const html = await page.content();
    const hasFailedToFetch = html.includes('Failed to fetch');
    console.log(`Page contains 'Failed to fetch': ${hasFailedToFetch}`);

    const screenshotPath = `e2e/screenshots/property_${prop.id}_${prop.name.replace(/\s+/g, '_')}.png`;
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`Screenshot saved: ${screenshotPath}`);
  }

  await browser.close();
}

main().catch(console.error);
