import { chromium } from 'playwright';

const PROPERTIES = [
  { id: '6277', name: 'Binghatti_Emerald_Area_Fallback' },
  { id: '3201', name: 'Binghatti_Nova_Area_Fallback' },
  { id: '3983', name: 'Sapphire_32_Area_Fallback' },
  { id: '7061', name: 'Azizi_Mina_Area_Fallback' },
  { id: '8201', name: 'Marquise_Square_Area_Fallback' },
  { id: '8057', name: 'Binghatti_Royale_Level2' },
];

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  page.on('console', msg => console.log(`[${msg.type().toUpperCase()}] ${msg.text()}`));
  page.on('pageerror', err => console.log(`Browser page error: ${err.message}`));

  for (const prop of PROPERTIES) {
    const url = `http://127.0.0.1:5173/property/${prop.id}?debug=benchmarks`;
    console.log(`\n=== Navigating to ${url} ===`);
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.waitForTimeout(4000);

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
