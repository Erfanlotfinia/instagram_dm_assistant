/**
 * Sprint 5 — Quick reply templates.
 *
 * Default templates are deterministic, frontend-first strings. Custom templates
 * created by operators are persisted to localStorage per shop as a TEMPORARY
 * frontend-only store until a backend template API is added. No network calls,
 * no auto-send: rendering produces an OperatorReplyDraft that always requires
 * approval before sending.
 */
import type { OperatorReplyDraft, QuickReplyCategory, QuickReplyTemplate } from '../types/sprint5Operator';
import { renderQuickReply, type QuickReplyContext } from './operatorWorkspace';

export const DEFAULT_QUICK_REPLY_TEMPLATES: QuickReplyTemplate[] = [
  {
    id: 'qr-greeting',
    title: 'Greeting',
    category: 'greeting',
    body: 'Hi {{customer_name}}! Thanks for reaching out. How can I help you today?',
    variables: ['customer_name'],
    enabled: true,
  },
  {
    id: 'qr-ask-size-color',
    title: 'Ask size & color',
    category: 'stock',
    body: 'Sure! Which size and color would you like for {{product_name}}?',
    variables: ['product_name'],
    enabled: true,
  },
  {
    id: 'qr-price-explanation',
    title: 'Price explanation',
    category: 'price',
    body: 'The price for {{product_name}} is listed on the post. Shipping is calculated based on your city ({{city}}). Would you like me to confirm availability?',
    variables: ['product_name', 'city'],
    enabled: true,
  },
  {
    id: 'qr-payment-reminder',
    title: 'Payment link reminder',
    category: 'payment',
    body: 'Hi {{customer_name}}, here is your payment link for order {{order_id}}: {{payment_link}}. It will expire soon — please complete checkout when ready.',
    variables: ['customer_name', 'order_id', 'payment_link'],
    enabled: true,
  },
  {
    id: 'qr-shipping-request',
    title: 'Shipping info request',
    category: 'shipping',
    body: 'Could you share your full name, phone, city, and address so I can prepare shipping for {{product_name}}?',
    variables: ['product_name'],
    enabled: true,
  },
  {
    id: 'qr-unavailable-apology',
    title: 'Unavailable product apology',
    category: 'stock',
    body: "I'm sorry, {{product_name}} is currently out of stock in the requested variant. Would you like a similar option or a restock notification?",
    variables: ['product_name'],
    enabled: true,
  },
  {
    id: 'qr-restock-notification',
    title: 'Restock notification offer',
    category: 'recovery',
    body: 'Thanks for your interest in {{product_name}}! I can notify you as soon as it is back in stock. Would you like that?',
    variables: ['product_name'],
    enabled: true,
  },
  {
    id: 'qr-human-handoff',
    title: 'Human handoff message',
    category: 'handoff',
    body: 'Hi {{customer_name}}, I am a human teammate on {{channel_name}} and I will take it from here. Could you give me a moment to review your conversation?',
    variables: ['customer_name', 'channel_name'],
    enabled: true,
  },
];

export const QUICK_REPLY_CATEGORIES: { id: QuickReplyCategory | 'all'; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'greeting', label: 'Greeting' },
  { id: 'price', label: 'Price' },
  { id: 'stock', label: 'Stock' },
  { id: 'payment', label: 'Payment' },
  { id: 'shipping', label: 'Shipping' },
  { id: 'handoff', label: 'Handoff' },
  { id: 'recovery', label: 'Recovery' },
  { id: 'custom', label: 'Custom' },
];

export function renderQuickReplyTemplate(
  template: QuickReplyTemplate,
  context: QuickReplyContext,
  conversationId = '',
): OperatorReplyDraft {
  return renderQuickReply(template, context, conversationId);
}

/**
 * TEMPORARY frontend-only persistence for custom quick replies.
 * Replace with a backend template API when available.
 */
function storageKey(shopId: string): string {
  return `modira.quickReplies.${shopId}`;
}

export function loadCustomQuickReplies(shopId: string): QuickReplyTemplate[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(storageKey(shopId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((t): t is QuickReplyTemplate =>
      typeof t === 'object' && t !== null && typeof (t as QuickReplyTemplate).id === 'string' && typeof (t as QuickReplyTemplate).body === 'string',
    );
  } catch {
    return [];
  }
}

/** TEMPORARY frontend-only persistence. Replace with backend template API when available. */
export function saveCustomQuickReplies(shopId: string, templates: QuickReplyTemplate[]): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(storageKey(shopId), JSON.stringify(templates));
  } catch {
    // Ignore quota / serialization errors — non-critical frontend-only cache.
  }
}

export function clearCustomQuickReplies(shopId: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.removeItem(storageKey(shopId));
  } catch {
    // ignore
  }
}

/** Merge defaults with custom templates, deduping by id. Custom wins on conflict. */
export function mergeQuickReplies(
  defaults: QuickReplyTemplate[],
  custom: QuickReplyTemplate[],
): QuickReplyTemplate[] {
  const byId = new Map<string, QuickReplyTemplate>();
  for (const t of defaults) byId.set(t.id, t);
  for (const t of custom) byId.set(t.id, t);
  return Array.from(byId.values());
}

export function createCustomTemplate(input: {
  title: string;
  body: string;
  category?: QuickReplyCategory;
}): QuickReplyTemplate {
  const variables: string[] = [];
  const varPattern = /\{\{([a-z_]+)\}\}/g;
  let match: RegExpExecArray | null;
  while ((match = varPattern.exec(input.body)) !== null) {
    if (!variables.includes(match[1])) variables.push(match[1]);
  }
  return {
    id: `custom-${Math.random().toString(36).slice(2, 10)}`,
    title: input.title.trim() || 'Untitled',
    category: input.category ?? 'custom',
    body: input.body,
    variables,
    enabled: true,
  };
}
