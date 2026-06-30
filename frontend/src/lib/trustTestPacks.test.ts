import { describe, expect, it } from 'vitest';

import {
  BUILTIN_TRUST_TEST_PACKS,
  allTrustTestCases,
  getPackById,
} from './trustTestPacks';
import type { TrustTestCategory, TrustTestExpectedOutcome, TrustTestSeverity } from '../types/sprint6Trust';

const EXPECTED_PACK_IDS = [
  'pack_prompt_injection_basics',
  'pack_commerce_safety',
  'pack_privacy_secret_protection',
  'pack_policy_boundary',
] as const;

const VALID_CATEGORIES: TrustTestCategory[] = [
  'prompt_injection',
  'policy_bypass',
  'unsafe_discount',
  'payment_risk',
  'privacy_leak',
  'secret_extraction',
  'wrong_product',
  'wrong_variant',
  'fake_order_confirmation',
  'refund_or_cancel_abuse',
  'human_handoff_required',
  'provider_window_violation',
];

const VALID_SEVERITIES: TrustTestSeverity[] = ['critical', 'high', 'medium', 'low'];

const VALID_OUTCOMES: TrustTestExpectedOutcome[] = [
  'block',
  'handoff',
  'preview',
  'safe_reply',
  'no_order',
  'no_payment',
  'no_secret',
  'ask_clarifying_question',
];

describe('BUILTIN_TRUST_TEST_PACKS', () => {
  it('exposes the four required packs', () => {
    expect(BUILTIN_TRUST_TEST_PACKS).toHaveLength(4);
    for (const id of EXPECTED_PACK_IDS) {
      expect(BUILTIN_TRUST_TEST_PACKS.find((p) => p.id === id)).toBeTruthy();
    }
  });

  it('each pack has 5 test cases with unique ids and required fields', () => {
    const seen = new Set<string>();
    for (const pack of BUILTIN_TRUST_TEST_PACKS) {
      expect(pack.testCases).toHaveLength(5);
      expect(pack.builtIn).toBe(true);
      for (const tc of pack.testCases) {
        expect(seen.has(tc.id)).toBe(false);
        seen.add(tc.id);
        expect(VALID_CATEGORIES).toContain(tc.category);
        expect(VALID_SEVERITIES).toContain(tc.severity);
        expect(VALID_OUTCOMES).toContain(tc.expectedOutcome);
        expect(tc.title.trim()).not.toBe('');
        expect(tc.customerMessage.trim()).not.toBe('');
        expect(tc.expectedReason.trim()).not.toBe('');
        expect(Array.isArray(tc.tags)).toBe(true);
        expect(tc.tags.length).toBeGreaterThan(0);
      }
    }
  });

  it('covers prompt injection, policy bypass, privacy leak, payment risk, wrong product/variant', () => {
    const cats = new Set(allTrustTestCases().map((c) => c.category));
    expect(cats.has('prompt_injection')).toBe(true);
    expect(cats.has('policy_bypass')).toBe(true);
    expect(cats.has('privacy_leak')).toBe(true);
    expect(cats.has('payment_risk')).toBe(true);
    expect(cats.has('wrong_product')).toBe(true);
    expect(cats.has('wrong_variant')).toBe(true);
    expect(cats.has('secret_extraction')).toBe(true);
    expect(cats.has('refund_or_cancel_abuse')).toBe(true);
    expect(cats.has('unsafe_discount')).toBe(true);
    expect(cats.has('human_handoff_required')).toBe(true);
  });

  it('getPackById returns the pack and allTrustTestCases returns 20 cases', () => {
    expect(getPackById('pack_prompt_injection_basics')?.name).toBe('Prompt Injection Basics');
    expect(getPackById('does-not-exist')).toBeUndefined();
    expect(allTrustTestCases()).toHaveLength(20);
  });
});
