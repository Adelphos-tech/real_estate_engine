// Mock API responses for E2E tests — no dependency on remote backend
import { Page, Route } from '@playwright/test';

const mockRecommendation = {
  recommendations: [{
    id: 1868,
    title: 'Amazonia Residence | 1 Bedroom Apartment',
    project: 'Amazonia Residence',
    area: 'Al Jadaf Waterfront',
    bedType: '1 B/R',
    askingPrice: 1250000,
    priceSqft: 2023,
    areaSqft: 618,
    comparablePrice: 1150000,
    priceDifference: 8.7,
    marketPosition: 'Premium Pricing',
    estimatedRent: 150000,
    estimatedYield: 12.0,
    readyScore: 78,
    scoreLabel: 'Fair Investment',
    priceScore: 74,
    recommendation: 'BUY',
    reasons: ['Good rental yield', 'Excellent liquidity', 'Strong demand'],
    lostPoints: ['Developer is unknown', 'No growth history'],
    propertyType: 'ready',
    growth3m: 0,
    growth6m: 0,
    growth12m: 0,
    growthMetadata: { hasGrowthData: false, reason: 'Insufficient historical data' },
    roi: {
      grossROI: 12.0,
      netROI: 10.06,
      annualRent: 150000,
      serviceChargeAnnual: 9270,
      vacancyRate: 0.05,
      managementFee: 7500,
      netAnnualIncome: 125730,
    },
    risk: {
      overallRisk: 21,
      riskLevel: 'Low',
      riskFactors: ['Developer has average track record', 'Growth history limited'],
      components: {
        futureSupplyRisk: 2,
        developerRisk: 50,
        areaSaturationRisk: 0,
        rentalRisk: 20,
        marketVolatilityRisk: 0,
        constructionDelayRisk: 5,
        pricePremiumRisk: 44,
      },
    },
    liquidity: {
      liquidityScore: 100,
      liquidityLabel: 'Excellent',
      absorptionRate: 300,
    },
    developerData: {
      name: 'Independent / Other',
      developerScore: 50,
      marketPosition: 'Mid-Tier',
      summary: 'Independent developer with limited track record.',
      projectsDelivered: 0,
      constructionQuality: 5,
      marketReputation: 5,
      scoreBreakdown: { delivery: 5, quality: 5, reputation: 5, volume: 0 },
      deliveryDelayRisk: 'Medium',
    },
    communityData: {
      name: 'Al Jadaf Waterfront',
      communityScore: 69,
      riskLevel: 'Low',
      subScores: { growth: 50, yield: 80, liquidity: 70, transactions: 90 },
    },
    projectData: {
      name: 'Amazonia Residence',
      priceSqft: 2023,
      status: 'Ready',
    },
    dataCompleteness: {
      hasROI: true,
      hasRisk: true,
      hasLiquidity: true,
      hasGrowth: false,
      hasDeveloper: true,
      hasCommunity: true,
    },
    scoreBreakdown: {
      price: 74,
      roi: 80,
      liquidity: 100,
      community: 69,
      developer: 50,
      project: 75,
    },
  }],
};

const mockCommunities = [
  {
    name: 'Al Jadaf Waterfront',
    slug: 'al-jadaf-waterfront',
    communityScore: 69,
    medianPriceSqft: 2000,
    medianRent: 125000,
    rentalYield: 10.0,
    priceIndex: { medianPriceSqft: 2000, totalSales: 100 },
    rentalIndex: { medianRent: 125000, totalRentContracts: 50 },
    demandIndex: 80,
    supplyIndex: 20,
    growthIndex: { growth3m: 0, growth6m: 0, growth12m: 0 },
    growth3m: 0,
    growth6m: 0,
    growth12m: 0,
    livabilityIndex: 70,
    transportIndex: 60,
    luxuryIndex: 50,
    subScores: { growth: 50, yield: 80, liquidity: 70, transactions: 90 },
    riskLevel: 'Low',
    salesVolume: 100,
    rentVolume: 50,
    totalProjects: 5,
    totalSupply: 200,
  },
];

const mockProjects = [
  {
    name: 'Amazonia Residence',
    slug: 'amazonia-residence',
    area: 'Al Jadaf Waterfront',
    status: 'Ready',
    priceSqft: 2023,
    priceChangePct: 0,
    transactionVolume: 39,
    rentalYield: 12.0,
    demandScore: 100,
    projectScore: 75,
    unitTypes: ['1 B/R', '2 B/R'],
    riskLevel: 'Low',
  },
];

export async function mockAPI(page: Page) {
  // Route specific API endpoints only — let all other requests pass through
  await page.route('**/recommendations**', async (route: Route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockRecommendation),
    });
  });

  await page.route('**/communities', async (route: Route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockCommunities),
    });
  });

  await page.route('**/communities/*', async (route: Route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockCommunities[0]),
    });
  });

  await page.route('**/projects**', async (route: Route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockProjects),
    });
  });

  await page.route('**/developers**', async (route: Route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.route('**/properties/**', async (route: Route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.route('**/health', async (route: Route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', version: '1.0' }),
    });
  });

  await page.route('**/report**', async (route: Route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockRecommendation),
    });
  });
}
