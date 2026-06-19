import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input } from '../components/ui';
import { DataTable, EmptyState } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { cn } from '../lib/cn';
import { apiClient } from '../services/apiClient';
import type { RecoveryRule } from '../types/sprintD';

const DEFAULT_TEMPLATE =
  'Hi {customer_name}, your order ({order_total} {currency}) is waiting for payment. Reply here if you need help.';

const TEMPLATE_TOKENS = ['{customer_name}', '{order_total}', '{currency}', '{order_id}'] as const;

const TIMING_PRESETS = [
  { label: '30 min', minutes: 30 },
  { label: '1 hour', minutes: 60 },
  { label: '2 hours', minutes: 120 },
  { label: '6 hours', minutes: 360 },
] as const;

function previewTemplate(template: string): string {
  return template
    .replace('{customer_name}', 'Sara')
    .replace('{order_total}', '49.99')
    .replace('{currency}', 'USD')
    .replace('{order_id}', 'a1b2c3d4');
}

function formatTiming(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  if (minutes % 60 === 0) return `${minutes / 60} hr`;
  return `${minutes} min`;
}

function Chip({ active, onClick, children }: { active?: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
        active ? 'border-accent bg-accent-soft text-accent' : 'border-border bg-surface text-muted hover:text-fg',
      )}
    >
      {children}
    </button>
  );
}

export function RecoveryRulesPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const rules = useQuery({
    queryKey: ['recovery-rules', selectedShopId],
    queryFn: () => apiClient.listRecoveryRules(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const [triggerAfterMinutes, setTriggerAfterMinutes] = useState(60);
  const [maxAttempts, setMaxAttempts] = useState(3);
  const [messageTemplate, setMessageTemplate] = useState(DEFAULT_TEMPLATE);
  const [onlyInsideWindow, setOnlyInsideWindow] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<RecoveryRule | null>(null);

  const activeCount = useMemo(() => (rules.data ?? []).filter((rule) => rule.is_active).length, [rules.data]);

  const create = useMutation({
    mutationFn: () =>
      apiClient.createRecoveryRule(selectedShopId, {
        trigger_after_minutes: triggerAfterMinutes,
        max_attempts: maxAttempts,
        message_template: messageTemplate.trim(),
        only_inside_allowed_messaging_window: onlyInsideWindow,
        is_active: true,
      }),
    onSuccess: () => {
      showToast('Recovery rule created.', 'success');
      queryClient.invalidateQueries({ queryKey: ['recovery-rules', selectedShopId] });
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to create rule', 'error'),
  });

  const toggleActive = useMutation({
    mutationFn: ({ ruleId, isActive }: { ruleId: string; isActive: boolean }) =>
      apiClient.updateRecoveryRule(selectedShopId, ruleId, { is_active: isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recovery-rules', selectedShopId] }),
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to update rule', 'error'),
  });

  const remove = useMutation({
    mutationFn: (ruleId: string) => apiClient.deleteRecoveryRule(selectedShopId, ruleId),
    onSuccess: () => {
      showToast('Recovery rule deleted.', 'success');
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ['recovery-rules', selectedShopId] });
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to delete rule', 'error'),
  });

  function appendToken(token: string) {
    setMessageTemplate((current) => (current.trim() ? `${current.trim()} ${token}` : token));
  }

  function resetForm() {
    setTriggerAfterMinutes(60);
    setMaxAttempts(3);
    setMessageTemplate(DEFAULT_TEMPLATE);
    setOnlyInsideWindow(true);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!selectedShopId) {
      showToast('Select a shop first.', 'error');
      return;
    }
    if (!messageTemplate.trim()) {
      showToast('Message template cannot be empty.', 'error');
      return;
    }
    create.mutate();
  }

  const canSubmit = Boolean(selectedShopId && messageTemplate.trim() && !create.isPending);

  const columns: Column<RecoveryRule>[] = [
    { key: 'timing', header: 'Timing', render: (rule) => formatTiming(rule.trigger_after_minutes) },
    { key: 'attempts', header: 'Attempts', align: 'right', render: (rule) => rule.max_attempts },
    {
      key: 'policy',
      header: 'Channel policy',
      className: 'hidden md:table-cell',
      render: (rule) => (rule.only_inside_allowed_messaging_window ? '24h window' : 'Always allowed'),
    },
    {
      key: 'template',
      header: 'Template',
      render: (rule) => (
        <div className="max-w-xs">
          <p className="truncate text-sm">{rule.message_template}</p>
          <p className="text-xs text-muted">Preview: {previewTemplate(rule.message_template)}</p>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (rule) => <Badge tone={rule.is_active ? 'success' : 'neutral'}>{rule.is_active ? 'Active' : 'Paused'}</Badge>,
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (rule) => (
        <div className="flex justify-end gap-1">
          <Button
            variant="ghost"
            size="sm"
            type="button"
            disabled={toggleActive.isPending}
            onClick={() => toggleActive.mutate({ ruleId: rule.id, isActive: !rule.is_active })}
          >
            {rule.is_active ? 'Pause' : 'Activate'}
          </Button>
          <Button variant="ghost" size="sm" type="button" onClick={() => setDeleteTarget(rule)}>
            Delete
          </Button>
        </div>
      ),
    },
  ];

  return (
    <HubPage
      eyebrow="Automation"
      title="Abandoned recovery rules"
      description="Send template-based payment reminders when orders stay in waiting-for-payment. Messages are never generated by the LLM."
    >
      <Card>
        <CardHeader
          title="Create recovery rule"
          description="The scheduler marks eligible unpaid orders, then sends your template if channel policy allows."
        />
        <CardBody>
          {!selectedShopId ? (
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          ) : (
            <form className="flex flex-col gap-4" onSubmit={submit}>
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Trigger after (minutes)">
                  <Input
                    type="number"
                    min={1}
                    max={10080}
                    value={triggerAfterMinutes}
                    onChange={(e) => setTriggerAfterMinutes(Number(e.target.value))}
                    required
                  />
                </Field>
                <Field label="Max attempts">
                  <Input
                    type="number"
                    min={1}
                    max={10}
                    value={maxAttempts}
                    onChange={(e) => setMaxAttempts(Number(e.target.value))}
                    required
                  />
                </Field>
              </div>

              <Field label="Quick timing presets">
                <div className="flex flex-wrap gap-2" role="group" aria-label="Timing presets">
                  {TIMING_PRESETS.map((preset) => (
                    <Chip
                      key={preset.minutes}
                      active={triggerAfterMinutes === preset.minutes}
                      onClick={() => setTriggerAfterMinutes(preset.minutes)}
                    >
                      {preset.label}
                    </Chip>
                  ))}
                </div>
              </Field>

              <Field label="Message template">
                <textarea
                  rows={4}
                  value={messageTemplate}
                  onChange={(e) => setMessageTemplate(e.target.value)}
                  placeholder={DEFAULT_TEMPLATE}
                  required
                  className="w-full resize-y rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg focus:border-accent focus:outline-none"
                />
              </Field>

              <Field label="Insert template variables">
                <div className="flex flex-wrap gap-2" role="group" aria-label="Template variables">
                  {TEMPLATE_TOKENS.map((token) => (
                    <Chip key={token} onClick={() => appendToken(token)}>
                      {token}
                    </Chip>
                  ))}
                </div>
              </Field>

              <label className="flex items-center gap-2 text-sm text-fg">
                <input
                  type="checkbox"
                  className="rounded border-border"
                  checked={onlyInsideWindow}
                  onChange={(e) => setOnlyInsideWindow(e.target.checked)}
                />
                Only send inside Instagram 24-hour messaging window
              </label>

              <Field label="Preview">
                <p className="rounded-lg border border-border bg-surface-sunken px-3 py-2 text-sm text-fg">
                  {previewTemplate(messageTemplate.trim() || DEFAULT_TEMPLATE)}
                </p>
              </Field>

              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={!canSubmit}>
                  {create.isPending ? 'Creating…' : 'Create recovery rule'}
                </Button>
                <Button type="button" variant="secondary" onClick={resetForm}>
                  Reset form
                </Button>
              </div>

              {create.error ? (
                <p className="text-sm text-danger">
                  {create.error instanceof Error ? create.error.message : 'Failed to create rule'}
                </p>
              ) : null}
            </form>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Configured rules"
          description={`${activeCount} active · ${(rules.data?.length ?? 0) - activeCount} paused`}
        />
        <DataTable
          columns={columns}
          rows={rules.data ?? []}
          rowKey={(rule) => rule.id}
          isLoading={rules.isLoading}
          error={rules.error instanceof Error ? rules.error.message : null}
          emptyTitle="No recovery rules yet"
          emptyDescription="Create one above."
        />
      </Card>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete recovery rule?"
        message="Customers will no longer receive automated payment reminders from this rule."
        confirmLabel="Delete rule"
        onConfirm={() => deleteTarget && remove.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
        isLoading={remove.isPending}
      />
    </HubPage>
  );
}
