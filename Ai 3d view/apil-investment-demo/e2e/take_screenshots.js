const { chromium } = require('playwright');

const PROPERTIES = [
  { id: '3693', name: 'Elvira' },
  { id: '4434', name: 'Lime Gardens' },
  { id: '701', name: 'Elvira' },
  { id: '7061', name: 'Azizi Mina' },
  { id: '8057', name: 'Binghatti Royale' },
];

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  for (const prop of PROPERTIES) {
    const url = `http://localhost:3000/property/${prop.id}?debug=benchmarks`;
    console.log(`Navigating to ${url}`);
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    const screenshotPath = `e2e/screenshots/property_${prop.id}_${prop.name.replace(/\s+/g, '_')}.png`;
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`Screenshot saved: ${screenshotPath}`);
  }

  await browser.close();
}

main().catch(console.error);
