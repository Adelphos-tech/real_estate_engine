/**
 * E2E Business Logic Invariants — tests against LIVE API at 87.200.15.174:8090
 * Covers all 12 issue categories the user identified.
 */
import { test, expect, Page } from '@playwright/test';

test.setTimeout(120000);

const API_BASE = 'http://87.200.15.174:8090';

const PROFILES = [
  { goal: 'capital_growth', budget: '500k-2m', property_type: 'apartment', bedrooms: '2', ready_offplan: 'offplan', timeline: '3-5y', financing: 'cash', risk: 'medium' },
  { goal: 'rental_income', budget: '500k-1m', property_type: 'apartment', bedrooms: '1', ready_offplan: 'ready', timeline: '3-5y', financing: 'mortgage', risk: 'low' },
  { goal: 'balanced', budget: '1m-2m', property_type: 'any', bedrooms: '2', ready_offplan: 'either', timeline: '3-5y', financing: 'cash', risk: 'medium' },
  { goal: 'flip_handover', budget: '500k-1m', property_type: 'apartment', bedrooms: '1', ready_offplan: 'offplan', timeline: '1-2y', financing: 'cash', risk: 'high' },
  { goal: 'capital_growth', budget: '2m-5m', property_type: 'villa', bedrooms: '3', ready_offplan: 'ready', timeline: '5y+', financing: 'cash', risk: 'medium' },
  { goal: 'end_user', budget: '1m-2m', property_type: 'apartment', bedrooms: '2', ready_offplan: 'ready', timeline: '5y+', financing: 'mortgage', risk: 'low' },
];

async function fetchRecommendations(profile: typeof PROFILES[0]) {
  const r = await fetch(`${API_BASE}/recommendations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  });
  expect(r.status).toBe(200);
  return r.json();
}

// ═══════════════════════════════════════════════════════════
// Issue 1: Timeline consistency
// ═══════════════════════════════════════════════════════════
test.describe('Issue 1: Timeline consistency', () => {
  for (const profile of PROFILES) {
    test(`timeline ${profile.timeline} matches strategy for ${profile.goal}`, async () => {
      const data = await fetchRecommendations(profile);
      const strategy = data.investorStrategy;
      expect(strategy.holding_period).toBe(profile.timeline);
      expect(strategy.holding_description).toContain(profile.timeline);
    });
  }

  test('exit strategy accounts for holding period', async () => {
    const shortProfile = PROFILES.find(p => p.timeline === '1-2y')!;
    const data = await fetchRecommendations(shortProfile);
    const exit = data.reportContract?.exit_strategy || '';
    expect(exit.length).toBeGreaterThan(10);
    expect(exit.toLowerCase()).toMatch(/sell|assignment|handover|flip/);
  });
});

// ═══════════════════════════════════════════════════════════
// Issue 2: Bedroom consistency
// ═══════════════════════════════════════════════════════════
test.describe('Issue 2: Bedroom consistency', () => {
  test('2BR request never returns Studio', async () => {
    for (const profile of PROFILES.filter(p => p.bedrooms === '2')) {
      const data = await fetchRecommendations(profile);
      for (const rec of data.recommendations) {
        expect(rec.bedType?.toLowerCase()).not.toContain('studio');
      }
    }
  });

  test('1BR request returns 1BR or adjacent', async () => {
    const profile = PROFILES.find(p => p.bedrooms === '1')!;
    const data = await fetchRecommendations(profile);
    for (const rec of data.recommendations) {
      const bt = rec.bedType?.toLowerCase() || '';
      expect(bt).toMatch(/studio|1|2/);
    }
  });

  test('3BR request returns 3BR or adjacent', async () => {
    const profile = PROFILES.find(p => p.bedrooms === '3')!;
    const data = await fetchRecommendations(profile);
    for (const rec of data.recommendations) {
      const bt = rec.bedType?.toLowerCase() || '';
      expect(bt).toMatch(/2|3|4|5/);
    }
  });
});

// ═══════════════════════════════════════════════════════════
// Issue 3/11: Alternative ranking consistency
// ═══════════════════════════════════════════════════════════
test.describe('Issue 3/11: Alternative ranking', () => {
  test('all alternatives have non-zero scores', async () => {
    for (const profile of PROFILES) {
      const data = await fetchRecommendations(profile);
      for (const rec of data.recommendations) {
        const score = rec.offplanScore || rec.readyScore || 0;
        expect(score).toBeGreaterThan(0);
      }
    }
  });

  test('offplan alternatives have developer scores', async () => {
    for (const profile of PROFILES.filter(p => p.ready_offplan === 'offplan')) {
      const data = await fetchRecommendations(profile);
      for (const rec of data.recommendations) {
        const ds = rec.developerData?.developerScore;
        expect(ds).toBeTruthy();
        expect(ds).toBeGreaterThan(0);
      }
    }
  });

  test('top recommendation has highest score', async () => {
    for (const profile of PROFILES) {
      const data = await fetchRecommendations(profile);
      if (data.recommendations.length < 2) continue;
      const topScore = data.recommendations[0].offplanScore || data.recommendations[0].readyScore || 0;
      for (const rec of data.recommendations.slice(1)) {
        const score = rec.offplanScore || rec.readyScore || 0;
        expect(score).toBeLessThanOrEqual(topScore);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════
// Issue 4-7: Rule flags and AI grounding
// ═══════════════════════════════════════════════════════════
test.describe('Issue 4-7: Rule flags', () => {
  test('rule flags are human-readable', async () => {
    for (const profile of PROFILES) {
      const data = await fetchRecommendations(profile);
      for (const rec of data.recommendations) {
        const flags = rec.rulesFlags || [];
        const human = rec.rulesFlagsHuman || [];
        if (flags.length > 0) {
          expect(human.length).toBe(flags.length);
          for (const h of human) {
            expect(h).not.toMatch(/^RULE_/);
          }
        }
      }
    }
  });

  test('no raw RULE_ codes in human-readable flags', async () => {
    const data = await fetchRecommendations(PROFILES[0]);
    for (const rec of data.recommendations) {
      for (const h of (rec.rulesFlagsHuman || [])) {
        expect(h).not.toContain('RULE_');
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════
// Issue 8: Recommendation vocabulary
// ═══════════════════════════════════════════════════════════
test.describe('Issue 8: Recommendation vocabulary', () => {
  const VALID = ['STRONG BUY', 'BUY', 'BUY IF NEGOTIATED', 'HOLD', 'WATCHLIST', 'REVIEW', 'INSUFFICIENT_DATA', 'AVOID'];

  test('no CAUTION in any recommendation', async () => {
    for (const profile of PROFILES) {
      const data = await fetchRecommendations(profile);
      for (const rec of data.recommendations) {
        expect(rec.recommendation).not.toContain('CAUTION');
      }
    }
  });

  test('all recommendations use valid vocabulary', async () => {
    for (const profile of PROFILES) {
      const data = await fetchRecommendations(profile);
      for (const rec of data.recommendations) {
        expect(VALID).toContain(rec.recommendation);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════
// Issue 9: Risk consistency
// ═══════════════════════════════════════════════════════════
test.describe('Issue 9: Risk consistency', () => {
  test('offplan properties have risk components', async () => {
    for (const profile of PROFILES.filter(p => p.ready_offplan === 'offplan')) {
      const data = await fetchRecommendations(profile);
      for (const rec of data.recommendations) {
        if (rec.propertyType === 'offplan') {
          const comps = rec.risk?.components || {};
          expect(Object.keys(comps).length).toBeGreaterThanOrEqual(5);
        }
      }
    }
  });

  test('risk level matches overall risk score', async () => {
    for (const profile of PROFILES) {
      const data = await fetchRecommendations(profile);
      for (const rec of data.recommendations.slice(0, 3)) {
        const overall = rec.risk?.overallRisk || 0;
        const level = rec.risk?.riskLevel || '';
        if (overall <= 25) {
          expect(level).toBe('Low');
        } else if (overall <= 50) {
          expect(level).toBe('Medium');
        } else {
          expect(level).toBe('High');
        }
      }
    }
  });

  test('developer tier is never null for offplan', async () => {
    for (const profile of PROFILES.filter(p => p.ready_offplan === 'offplan')) {
      const data = await fetchRecommendations(profile);
      for (const rec of data.recommendations) {
        if (rec.propertyType === 'offplan') {
          const tier = rec.developerData?.marketPosition;
          expect(tier).not.toBeNull();
          expect(String(tier)).toContain('Tier');
        }
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════
// Issue 10/12: Confidence consistency
// ═══════════════════════════════════════════════════════════
test.describe('Issue 10/12: Confidence', () => {
  test('offplan properties have confidence explanation', async () => {
    for (const profile of PROFILES.filter(p => p.ready_offplan === 'offplan')) {
      const data = await fetchRecommendations(profile);
      for (const rec of data.recommendations) {
        if (rec.propertyType === 'offplan') {
          expect(rec.confidenceExplanation).toBeTruthy();
          expect(rec.confidenceExplanation.length).toBeGreaterThan(10);
        }
      }
    }
  });

  test('confidence score is in valid range', async () => {
    for (const profile of PROFILES) {
      const data = await fetchRecommendations(profile);
      for (const rec of data.recommendations) {
        const score = rec.confidenceScore || 0;
        expect(score).toBeGreaterThanOrEqual(0);
        expect(score).toBeLessThanOrEqual(100);
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════
// Issue 11: Property type consistency
// ═══════════════════════════════════════════════════════════
test.describe('Issue 11: Property type', () => {
  test('offplan-only profile gets only offplan properties', async () => {
    for (const profile of PROFILES.filter(p => p.ready_offplan === 'offplan')) {
      const data = await fetchRecommendations(profile);
      for (const rec of data.recommendations) {
        expect(rec.propertyType).toBe('offplan');
      }
    }
  });

  test('ready-only profile gets only ready properties', async () => {
    for (const profile of PROFILES.filter(p => p.ready_offplan === 'ready')) {
      const data = await fetchRecommendations(profile);
      for (const rec of data.recommendations) {
        expect(rec.propertyType).toBe('ready');
      }
    }
  });
});

// ═══════════════════════════════════════════════════════════
// Structural completeness
// ═══════════════════════════════════════════════════════════
test.describe('Response structure', () => {
  test('has all required top-level fields', async () => {
    const data = await fetchRecommendations(PROFILES[0]);
    expect(data.investorStrategy).toBeDefined();
    expect(data.reportContract).toBeDefined();
    expect(data.reportValidation).toBeDefined();
    expect(data.recommendationConfidence).toBeDefined();
    expect(data.recommendations).toBeDefined();
    expect(data.recommendations.length).toBeGreaterThan(0);
  });

  test('investor strategy has all fields', async () => {
    const data = await fetchRecommendations(PROFILES[0]);
    const s = data.investorStrategy;
    expect(s.goal).toBeDefined();
    expect(s.holding_period).toBeDefined();
    expect(s.exit_strategy).toBeDefined();
    expect(s.strategy_summary).toBeDefined();
  });

  test('report contract has exit strategy', async () => {
    const data = await fetchRecommendations(PROFILES[0]);
    expect(data.reportContract.exit_strategy).toBeTruthy();
    expect(data.reportContract.exit_strategy.length).toBeGreaterThan(10);
  });
});
