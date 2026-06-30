import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import {
  DEFAULT_QUICK_REPLY_TEMPLATES,
  clearCustomQuickReplies,
  createCustomTemplate,
  loadCustomQuickReplies,
  mergeQuickReplies,
  renderQuickReplyTemplate,
  saveCustomQuickReplies,
} from './quickReplies';

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  localStorage.clear();
});

describe('DEFAULT_QUICK_REPLY_TEMPLATES', () => {
  it('includes the eight spec templates', () => {
    const ids = DEFAULT_QUICK_REPLY_TEMPLATES.map((t) => t.id);
    expect(ids).toContain('qr-greeting');
    expect(ids).toContain('qr-ask-size-color');
    expect(ids).toContain('qr-price-explanation');
    expect(ids).toContain('qr-payment-reminder');
    expect(ids).toContain('qr-shipping-request');
    expect(ids).toContain('qr-unavailable-apology');
    expect(ids).toContain('qr-restock-notification');
    expect(ids).toContain('qr-human-handoff');
    expect(DEFAULT_QUICK_REPLY_TEMPLATES.length).toBe(8);
  });

  it('all defaults are enabled and declare their variables', () => {
    for (const t of DEFAULT_QUICK_REPLY_TEMPLATES) {
      expect(t.enabled).toBe(true);
      for (const v of t.variables) {
        expect(t.body).toContain(`{{${v}}}`);
      }
    }
  });
});

describe('renderQuickReplyTemplate', () => {
  it('substitutes variables and marks approval required', () => {
    const template = DEFAULT_QUICK_REPLY_TEMPLATES.find((t) => t.id === 'qr-greeting')!;
    const draft = renderQuickReplyTemplate(template, { customer_name: 'Jane' }, 'c1');
    expect(draft.body).toBe('Hi Jane! Thanks for reaching out. How can I help you today?');
    expect(draft.warnings).toEqual([]);
    expect(draft.requires_approval).toBe(true);
    expect(draft.conversation_id).toBe('c1');
  });

  it('warns about unresolved variables', () => {
    const template = DEFAULT_QUICK_REPLY_TEMPLATES.find((t) => t.id === 'qr-payment-reminder')!;
    const draft = renderQuickReplyTemplate(template, { customer_name: 'Jane' }, 'c1');
    expect(draft.warnings).toContain('Unresolved variable: order_id');
    expect(draft.warnings).toContain('Unresolved variable: payment_link');
    expect(draft.body).toContain('{{order_id}}');
    expect(draft.body).toContain('{{payment_link}}');
  });
});

describe('custom quick replies (localStorage)', () => {
  it('round-trips custom templates through localStorage', () => {
    const shopId = 'shop-1';
    expect(loadCustomQuickReplies(shopId)).toEqual([]);
    const t = createCustomTemplate({ title: 'My reply', body: 'Hello {{customer_name}}' });
    saveCustomQuickReplies(shopId, [t]);
    const loaded = loadCustomQuickReplies(shopId);
    expect(loaded).toHaveLength(1);
    expect(loaded[0].title).toBe('My reply');
    expect(loaded[0].variables).toEqual(['customer_name']);
    expect(loaded[0].category).toBe('custom');
  });

  it('clearCustomQuickReplies removes the store', () => {
    const shopId = 'shop-2';
    saveCustomQuickReplies(shopId, [createCustomTemplate({ title: 'x', body: 'hi' })]);
    expect(loadCustomQuickReplies(shopId)).toHaveLength(1);
    clearCustomQuickReplies(shopId);
    expect(loadCustomQuickReplies(shopId)).toEqual([]);
  });

  it('returns [] on corrupted storage', () => {
    localStorage.setItem('modira.quickReplies.shop-bad', '{not json');
    expect(loadCustomQuickReplies('shop-bad')).toEqual([]);
  });
});

describe('mergeQuickReplies', () => {
  it('dedupes by id with custom taking precedence', () => {
    const defaults = DEFAULT_QUICK_REPLY_TEMPLATES;
    const overridden = { ...defaults[0], title: 'Overridden greeting' };
    const extra = createCustomTemplate({ title: 'Extra', body: 'hi' });
    const merged = mergeQuickReplies(defaults, [overridden, extra]);
    const greeting = merged.find((t) => t.id === defaults[0].id);
    expect(greeting?.title).toBe('Overridden greeting');
    expect(merged.find((t) => t.id === extra.id)).toBeTruthy();
    // No duplicate ids
    const ids = merged.map((t) => t.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

describe('createCustomTemplate', () => {
  it('extracts variables from body', () => {
    const t = createCustomTemplate({ title: 'T', body: 'a {{x}} b {{y}} {{x}}' });
    expect(t.variables).toEqual(['x', 'y']);
  });
});
