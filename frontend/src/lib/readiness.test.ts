import { describe, expect, it } from 'vitest';

import {
  evaluateCatalogCompleteness,
  evaluateChannelOnboarding,
  evaluateShopReadiness,
  validateCatalogColor,
} from './readiness';
import type { ChannelAccount } from '../types/channel';
import type { Product } from '../types/product';
import type { AgentRiskSettings } from '../types/conversation';
import type { PilotReadinessResponse, PilotSettings } from '../types/pilot';
import type { SimulatorRunSummary } from '../types/trust';
import type { CatalogCompletenessScore } from '../types/sprint2Readiness';

function channel(overrides: Partial<ChannelAccount> = {}): ChannelAccount {
  return {
    id: 'ch1',
    shop_id: 's1',
    provider: 'instagram',
    display_name: 'IG',
    status: 'connected',
    capabilities_json: { supports_text: true },
    settings_json: {},
    token_configured: true,
    bot_token_configured: false,
    webhook_secret_configured: true,
    webhook_verify_token_configured: true,
    external_account_id: 'ig-123',
    last_validation_at: '2026-06-29T00:00:00Z',
    created_at: '2026-06-29T00:00:00Z',
    updated_at: '2026-06-29T00:00:00Z',
    ...overrides,
  };
}

function product(overrides: Partial<Product> = {}): Product {
  return {
    id: 'p1',
    shop_id: 's1',
    title: 'Shirt',
    description: null,
    status: 'active',
    base_price: '19.99',
    currency: 'USD',
    main_image_url: 'https://example.com/img.png',
    created_at: '2026-06-29T00:00:00Z',
    updated_at: '2026-06-29T00:00:00Z',
    ...overrides,
  };
}

function riskSettings(overrides: Partial<AgentRiskSettings> = {}): AgentRiskSettings {
  return {
    shop_id: 's1',
    intent_confidence_threshold: 0.6,
    slot_confidence_threshold: 0.6,
    product_confidence_threshold: 0.6,
    variant_confidence_threshold: 0.6,
    address_confidence_threshold: 0.6,
    high_value_order_threshold: 100,
    handoff_for_high_risk: true,
    handoff_for_low_variant_confidence: true,
    preview_required_for_high_value_order: true,
    ...overrides,
  };
}

function pilotSettings(overrides: Partial<PilotSettings> = {}): PilotSettings {
  return {
    shop_id: 's1',
    pilot_enabled: true,
    pilot_name: 'Pilot',
    pilot_start_date: null,
    pilot_end_date: null,
    max_auto_sent_messages_per_day: 10,
    max_auto_created_orders_per_day: 5,
    require_operator_approval_for_first_50_orders: true,
    allowed_instagram_account_ids: ['ig1'],
    allowed_product_ids: null,
    emergency_stop_enabled: false,
    operating_mode: 'copilot',
    created_at: '2026-06-29T00:00:00Z',
    updated_at: '2026-06-29T00:00:00Z',
    ...overrides,
  };
}

function pilotReadiness(passed: boolean): PilotReadinessResponse {
  return {
    shop_id: 's1',
    ready_for_trl6_pilot: passed,
    checklist: [{ key: 'k1', label: 'Check 1', passed, detail: null }],
    criteria: [],
    latest_trl_validation: null,
    pilot_settings: pilotSettings(),
    warnings: [],
  };
}

function run(overrides: Partial<SimulatorRunSummary> = {}): SimulatorRunSummary {
  return {
    id: 'r1',
    shop_id: 's1',
    source_type: 'scenario_pack',
    model_version: 'm1',
    prompt_version: 'p1',
    catalog_snapshot_hash: 'h',
    status: 'completed',
    total_items: 10,
    passed_items: 10,
    failed_items: 0,
    diff_summary_json: {},
    started_at: '2026-06-29T00:00:00Z',
    ...overrides,
  };
}

function completeCatalog(score = 90): CatalogCompletenessScore {
  return {
    score,
    productsTotal: 5,
    productsActive: 5,
    productsMissingImage: 0,
    productsMissingPrice: 0,
    variantsUnknown: false,
    attributesConfigured: 4,
    aliasesConfigured: 4,
    mappingsConfigured: 3,
    blockingReasons: [],
    warnings: [],
  };
}

describe('evaluateChannelOnboarding', () => {
  it('passes all required steps for a healthy connected channel', () => {
    const state = evaluateChannelOnboarding({
      channel: channel(),
      webhookTest: { status: 'ok', provider: 'instagram', channel_account_id: 'ch1' },
    });
    expect(state.ready).toBe(true);
    expect(state.score).toBe(100);
    expect(state.blockingReasons).toEqual([]);
  });

  it('blocks when webhook is not configured', () => {
    const state = evaluateChannelOnboarding({
      channel: channel({
        status: 'connected',
        webhook_secret_configured: false,
        webhook_verify_token_configured: false,
      }),
    });
    expect(state.ready).toBe(false);
    expect(state.blockingReasons.some((r) => /webhook/i.test(r))).toBe(true);
  });

  it('blocks when channel is disconnected', () => {
    const state = evaluateChannelOnboarding({
      channel: channel({ status: 'disconnected', last_error: 'token expired' }),
    });
    expect(state.ready).toBe(false);
    expect(state.blockingReasons.some((r) => /token expired|status/i.test(r))).toBe(true);
  });

  it('marks webhook_tested as recommended (not blocking) when no test result is supplied', () => {
    const state = evaluateChannelOnboarding({ channel: channel() });
    const tested = state.steps.find((s) => s.key === 'webhook_tested');
    expect(tested?.severity).toBe('recommended');
    expect(tested?.passed).toBe(false);
    expect(state.ready).toBe(true);
  });

  it('marks webhook_tested passed when webhookTest returns success', () => {
    const state = evaluateChannelOnboarding({
      channel: channel(),
      webhookTest: { status: 'ok', provider: 'instagram', channel_account_id: 'ch1' },
    });
    const tested = state.steps.find((s) => s.key === 'webhook_tested');
    expect(tested?.passed).toBe(true);
  });
});

describe('evaluateCatalogCompleteness', () => {
  it('returns a high score for a complete catalog', () => {
    const score = evaluateCatalogCompleteness({
      products: [product(), product({ id: 'p2' })],
      attributeAliases: [{ id: 'a1' }],
      productMappings: [{ id: 'm1' }],
    });
    expect(score.score).toBeGreaterThanOrEqual(80);
    expect(score.blockingReasons).toEqual([]);
  });

  it('flags missing variants as a warning (unknown) by default', () => {
    const score = evaluateCatalogCompleteness({
      products: [product()],
      attributeAliases: [{ id: 'a1' }],
      productMappings: [{ id: 'm1' }],
    });
    expect(score.variantsUnknown).toBe(true);
    expect(score.warnings.some((w) => /variant/i.test(w))).toBe(true);
    expect(score.blockingReasons).toEqual([]);
  });

  it('blocks when products are missing a price', () => {
    const score = evaluateCatalogCompleteness({
      products: [product({ base_price: '' })],
      attributeAliases: [{ id: 'a1' }],
      productMappings: [{ id: 'm1' }],
    });
    expect(score.blockingReasons.some((r) => /price/i.test(r))).toBe(true);
  });

  it('blocks when no products exist', () => {
    const score = evaluateCatalogCompleteness({
      products: [],
      attributeAliases: [],
      productMappings: [],
    });
    expect(score.blockingReasons.some((r) => /no products/i.test(r))).toBe(true);
  });
});

describe('evaluateShopReadiness', () => {
  function baseInput(overrides: Partial<Parameters<typeof evaluateShopReadiness>[0]> = {}) {
    return {
      channelStates: [evaluateChannelOnboarding({ channel: channel() })],
      catalog: completeCatalog(),
      pilotReadiness: pilotReadiness(true),
      pilotSettings: pilotSettings(),
      riskSettings: riskSettings(),
      latestRun: run(),
      failedJobsCount: 0,
      ...overrides,
    };
  }

  it('is ready for pilot and automation when everything passes', () => {
    const score = evaluateShopReadiness(baseInput());
    expect(score.readyForPilot).toBe(true);
    expect(score.readyForAutomation).toBe(true);
    expect(score.blockingReasons).toEqual([]);
  });

  it('blocks when no channel is connected', () => {
    const score = evaluateShopReadiness(baseInput({ channelStates: [] }));
    expect(score.readyForPilot).toBe(false);
    expect(score.readyForAutomation).toBe(false);
    expect(score.blockingReasons.some((r) => /channel/i.test(r))).toBe(true);
  });

  it('blocks when failed jobs exist', () => {
    const score = evaluateShopReadiness(baseInput({ failedJobsCount: 4 }));
    expect(score.readyForPilot).toBe(false);
    expect(score.blockingReasons.some((r) => /4 failed job/i.test(r))).toBe(true);
  });

  it('blocks when the latest replay run has failures', () => {
    const score = evaluateShopReadiness(baseInput({ latestRun: run({ failed_items: 3 }) }));
    expect(score.readyForPilot).toBe(false);
    expect(score.readyForAutomation).toBe(false);
    expect(score.blockingReasons.some((r) => /3 failed scenario/i.test(r))).toBe(true);
  });

  it('blocks automation (not pilot) when catalog score is below threshold', () => {
    const score = evaluateShopReadiness(
      baseInput({ catalog: completeCatalog(70) }),
    );
    // Pilot tolerates warnings, but a below-threshold catalog is a blocker.
    expect(score.readyForPilot).toBe(false);
    expect(score.readyForAutomation).toBe(false);
  });

  it('treats missing pilot settings as a warning, not a blocker', () => {
    const score = evaluateShopReadiness(
      baseInput({
        pilotSettings: pilotSettings({ operating_mode: undefined, pilot_enabled: false }),
        pilotReadiness: pilotReadiness(true),
      }),
    );
    const policy = score.checks.find((c) => c.key === 'policy_configured');
    expect(policy?.severity).toBe('warning');
    expect(score.readyForPilot).toBe(true);
  });
});

describe('validateCatalogColor', () => {
  it('accepts a valid hex color', () => {
    expect(validateCatalogColor('#FF0000')).toEqual({
      raw: '#FF0000',
      normalized: '#ff0000',
      valid: true,
    });
  });

  it('accepts a safe color name', () => {
    expect(validateCatalogColor('red').valid).toBe(true);
    expect(validateCatalogColor('red').normalized).toBe('red');
  });

  it('rejects unsafe values', () => {
    expect(validateCatalogColor('url(javascript:alert(1))').valid).toBe(false);
    expect(validateCatalogColor('var(--c-accent)').valid).toBe(false);
    expect(validateCatalogColor('rgb(1,2,3)').valid).toBe(false);
    expect(validateCatalogColor('red;').valid).toBe(false);
  });
});
