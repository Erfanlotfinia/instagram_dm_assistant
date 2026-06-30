import { useMemo, useState } from 'react';

import { Badge, Button, Field, Input, Select } from '../ui';
import { EmptyState, LoadingState } from '../data';
import {
  DEFAULT_QUICK_REPLY_TEMPLATES,
  QUICK_REPLY_CATEGORIES,
  createCustomTemplate,
  loadCustomQuickReplies,
  mergeQuickReplies,
  renderQuickReplyTemplate,
  saveCustomQuickReplies,
} from '../../lib/quickReplies';
import type { QuickReplyCategory, QuickReplyTemplate } from '../../types/sprint5Operator';
import type { QuickReplyContext } from '../../lib/operatorWorkspace';
import { cn } from '../../lib/cn';

interface QuickReplyPanelProps {
  shopId: string;
  /** Called with the rendered body when a composer is available to insert into. */
  onInsert?: (text: string) => void;
  /** Customer/conversation context for variable resolution. */
  customerContext?: QuickReplyContext;
  /** When true, shows the create-custom-template form. */
  allowCreate?: boolean;
  isLoading?: boolean;
}

const CATEGORY_LABEL: Record<QuickReplyCategory, string> = {
  greeting: 'Greeting',
  price: 'Price',
  stock: 'Stock',
  payment: 'Payment',
  shipping: 'Shipping',
  handoff: 'Handoff',
  recovery: 'Recovery',
  custom: 'Custom',
};

/**
 * Sprint 5 — Quick reply picker. Frontend-first: default templates plus
 * per-shop custom templates stored in localStorage (TEMPORARY until a backend
 * template API exists). Copy-to-clipboard always available; insert-via-callback
 * only when a composer is wired up. NO send button — drafts must be approved.
 */
export function QuickReplyPanel({
  shopId,
  onInsert,
  customerContext = {},
  allowCreate = false,
  isLoading = false,
}: QuickReplyPanelProps) {
  const [customTemplates, setCustomTemplates] = useState<QuickReplyTemplate[]>(() =>
    loadCustomQuickReplies(shopId),
  );
  const [category, setCategory] = useState<QuickReplyCategory | 'all'>('all');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newBody, setNewBody] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const allTemplates = useMemo(
    () => mergeQuickReplies(DEFAULT_QUICK_REPLY_TEMPLATES, customTemplates),
    [customTemplates],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return allTemplates.filter((t) => {
      if (category !== 'all' && t.category !== category) return false;
      if (!q) return true;
      return (
        t.title.toLowerCase().includes(q) ||
        t.body.toLowerCase().includes(q) ||
        CATEGORY_LABEL[t.category].toLowerCase().includes(q)
      );
    });
  }, [allTemplates, category, search]);

  function persistCustom(next: QuickReplyTemplate[]) {
    setCustomTemplates(next);
    saveCustomQuickReplies(shopId, next);
  }

  function handleCreate() {
    if (!newTitle.trim() && !newBody.trim()) return;
    const template = createCustomTemplate({ title: newTitle, body: newBody, category: 'custom' });
    persistCustom([...customTemplates, template]);
    setNewTitle('');
    setNewBody('');
    setShowCreate(false);
  }

  function handleToggleEnabled(template: QuickReplyTemplate) {
    if (DEFAULT_QUICK_REPLY_TEMPLATES.some((d) => d.id === template.id)) {
      // Defaults are not editable here; only custom templates can be toggled.
      return;
    }
    persistCustom(
      customTemplates.map((t) => (t.id === template.id ? { ...t, enabled: !t.enabled } : t)),
    );
  }

  function handleDelete(template: QuickReplyTemplate) {
    if (DEFAULT_QUICK_REPLY_TEMPLATES.some((d) => d.id === template.id)) return;
    persistCustom(customTemplates.filter((t) => t.id !== template.id));
  }

  async function handleCopy(template: QuickReplyTemplate) {
    const draft = renderQuickReplyTemplate(template, customerContext);
    try {
      await navigator.clipboard.writeText(draft.body);
      setCopiedId(template.id);
      window.setTimeout(() => setCopiedId((id) => (id === template.id ? null : id)), 1500);
    } catch {
      // Clipboard may be unavailable; fall back to no-op.
    }
  }

  function handleInsert(template: QuickReplyTemplate) {
    const draft = renderQuickReplyTemplate(template, customerContext);
    onInsert?.(draft.body);
  }

  if (isLoading) {
    return <LoadingState label="Loading quick replies…" />;
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="min-w-[160px] flex-1">
          <Input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search replies…"
          />
        </div>
        <Select
          value={category}
          onChange={(e) => setCategory(e.target.value as QuickReplyCategory | 'all')}
          aria-label="Filter by category"
        >
          {QUICK_REPLY_CATEGORIES.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </Select>
        {allowCreate ? (
          <Button variant="secondary" size="sm" onClick={() => setShowCreate((v) => !v)}>
            {showCreate ? 'Cancel' : 'New reply'}
          </Button>
        ) : null}
      </div>

      {showCreate && allowCreate ? (
        <div className="rounded-lg border border-border bg-surface-sunken p-3">
          <div className="flex flex-col gap-2">
            <Field label="Title" htmlFor="qr-title">
              <Input id="qr-title" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
            </Field>
            <Field label="Body (use {{customer_name}}, {{product_name}}, {{order_id}}, {{payment_link}}, {{city}}, {{channel_name}})" htmlFor="qr-body">
              <textarea
                id="qr-body"
                rows={3}
                value={newBody}
                onChange={(e) => setNewBody(e.target.value)}
                className={cn(
                  'w-full resize-y rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg',
                  'placeholder:text-subtle focus:border-accent focus:outline-none',
                )}
              />
            </Field>
            <div className="flex justify-end">
              <Button size="sm" onClick={handleCreate} disabled={!newTitle.trim() && !newBody.trim()}>
                Save custom
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {filtered.length === 0 ? (
        <EmptyState
          title="No quick replies match"
          description="Try a different category or search term."
        />
      ) : (
        <ul className="flex flex-col gap-2">
          {filtered.map((template) => {
            const draft = renderQuickReplyTemplate(template, customerContext);
            const isCustom = !DEFAULT_QUICK_REPLY_TEMPLATES.some((d) => d.id === template.id);
            return (
              <li
                key={template.id}
                className={cn(
                  'rounded-lg border border-border bg-surface p-3',
                  !template.enabled && 'opacity-60',
                )}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-fg">{template.title}</span>
                      <Badge tone="neutral">{CATEGORY_LABEL[template.category]}</Badge>
                      {isCustom ? <Badge tone="accent">Custom</Badge> : null}
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-muted" dir="auto">
                      {draft.body}
                    </p>
                    {draft.warnings.length > 0 ? (
                      <p className="mt-1 text-xs text-warning">
                        {draft.warnings.join(' · ')}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-1.5">
                    <Button size="sm" variant="secondary" onClick={() => handleCopy(template)}>
                      {copiedId === template.id ? 'Copied' : 'Copy'}
                    </Button>
                    {onInsert ? (
                      <Button size="sm" onClick={() => handleInsert(template)}>
                        Insert
                      </Button>
                    ) : null}
                    {isCustom ? (
                      <>
                        <Button size="sm" variant="ghost" onClick={() => handleToggleEnabled(template)}>
                          {template.enabled ? 'Disable' : 'Enable'}
                        </Button>
                        <Button size="sm" variant="danger" onClick={() => handleDelete(template)}>
                          Delete
                        </Button>
                      </>
                    ) : null}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <p className="text-xs text-subtle">
        Quick replies are drafts — review and approve before sending. No automatic sending.
      </p>
    </div>
  );
}
