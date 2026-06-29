import { describe, expect, it } from 'vitest';

import { explainBlockedDecision } from './automationCoach';
import type { AgentDecisionTrace } from '../types/conversation';

function trace(overrides: Partial<AgentDecisionTrace> = {}): AgentDecisionTrace {
  return {
    id: 't1',
    conversation_id: 'c1',
    message_id: null,
    agent_run_id: null,
    intent: 'order',
    extracted_slots: {},
    normalized_slots: {},
    product_candidates: [],
    selected_product_id: 'p1',
    variant_resolution: {},
    inventory_result: {},
    risk_score: { risk_level: 'low', score: 0.1, risk_reasons: [], requires_handoff: false, requires_preview: false },
    order_action: {},
    next_state: 'idle',
    outbound_message_id: null,
    auto_send_allowed: true,
    human_handoff_required: false,
    reasoning_summary: null,
    created_at: '2026-06-29T00:00:00Z',
    ...overrides,
  };
}

describe('explainBlockedDecision', () => {
  it('returns no insights when the decision was not blocked', () => {
    expect(explainBlockedDecision(trace())).toEqual([]);
  });

  it('surfaces human handoff first with a conversation action link', () => {
    const insights = explainBlockedDecision(
      trace({ auto_send_allowed: false, human_handoff_required: true }),
    );
    expect(insights).toHaveLength(1);
    expect(insights[0].category).toBe('human_handoff_required');
    expect(insights[0].severity).toBe('danger');
    expect(insights[0].actionTo).toBe('/inbox/c1/intelligence');
  });

  it('surfaces a high-risk insight with a risk-settings action link', () => {
    const insights = explainBlockedDecision(
      trace({
        auto_send_allowed: false,
        risk_score: { risk_level: 'high', score: 0.8, risk_reasons: [], requires_handoff: false, requires_preview: false },
      }),
    );
    expect(insights[0].category).toBe('risk');
    expect(insights[0].actionTo).toBe('/automation/risk');
  });

  it('surfaces low confidence from risk_reasons', () => {
    const insights = explainBlockedDecision(
      trace({
        auto_send_allowed: false,
        risk_score: {
          risk_level: 'medium',
          score: 0.4,
          risk_reasons: ['low_variant_confidence:0.3<0.6'],
          requires_handoff: false,
          requires_preview: false,
        },
      }),
    );
    const low = insights.find((i) => i.category === 'low_confidence');
    expect(low).toBeDefined();
    expect(low?.reason).toMatch(/Variant confidence/i);
  });

  it('surfaces missing product data when no product was resolved', () => {
    const insights = explainBlockedDecision(
      trace({
        auto_send_allowed: false,
        selected_product_id: null,
        risk_score: { risk_level: 'medium', score: 0.4, risk_reasons: [], requires_handoff: false, requires_preview: false },
      }),
    );
    expect(insights.some((i) => i.category === 'missing_product_data')).toBe(true);
  });

  it('surfaces missing product data when the variant is unavailable', () => {
    const insights = explainBlockedDecision(
      trace({
        auto_send_allowed: false,
        risk_score: {
          risk_level: 'medium',
          score: 0.4,
          risk_reasons: ['unavailable_variant'],
          requires_handoff: false,
          requires_preview: false,
        },
      }),
    );
    expect(insights.some((i) => i.category === 'missing_product_data')).toBe(true);
  });

  it('surfaces a policy restriction when preview is required but risk/handoff are clean', () => {
    const insights = explainBlockedDecision(
      trace({
        auto_send_allowed: false,
        risk_score: {
          risk_level: 'low',
          score: 0.2,
          risk_reasons: [],
          requires_handoff: false,
          requires_preview: true,
        },
      }),
    );
    expect(insights[0].category).toBe('policy_restriction');
  });

  it('deduplicates insights by category', () => {
    const insights = explainBlockedDecision(
      trace({
        auto_send_allowed: false,
        human_handoff_required: true,
        risk_score: {
          risk_level: 'high',
          score: 0.9,
          risk_reasons: ['low_intent_confidence:0.2<0.6', 'low_product_confidence:0.3<0.6'],
          requires_handoff: true,
          requires_preview: true,
        },
      }),
    );
    const categories = insights.map((i) => i.category);
    expect(new Set(categories).size).toBe(categories.length);
  });

  it('emits a fallback insight when blocked without any specific signal', () => {
    const insights = explainBlockedDecision(
      trace({
        auto_send_allowed: false,
        risk_score: { risk_level: 'low', score: 0.1, risk_reasons: [], requires_handoff: false, requires_preview: false },
        selected_product_id: 'p1',
      }),
    );
    expect(insights).toHaveLength(1);
    expect(insights[0].category).toBe('policy_restriction');
  });
});
