import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input } from '../components/ui';
import { EmptyState, KpiCard, LoadingState } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import type { AgentRiskSettings } from '../types/conversation';

type ThresholdKey =
  | 'intent_confidence_threshold'
  | 'slot_confidence_threshold'
  | 'product_confidence_threshold'
  | 'variant_confidence_threshold'
  | 'address_confidence_threshold';

const THRESHOLD_FIELDS: Array<{ key: ThresholdKey; label: string; hint: string }> = [
  { key: 'intent_confidence_threshold', label: 'Intent confidence', hint: 'Minimum confidence before acting on detected customer intent.' },
  { key: 'slot_confidence_threshold', label: 'Slot extraction confidence', hint: 'Minimum confidence for size, color, quantity, and address slots.' },
  { key: 'product_confidence_threshold', label: 'Product resolution confidence', hint: 'Minimum confidence before selecting a catalog product from DM context.' },
  { key: 'variant_confidence_threshold', label: 'Variant resolution confidence', hint: 'Minimum confidence before locking a size/color variant.' },
  { key: 'address_confidence_threshold', label: 'Address confidence', hint: 'Minimum confidence before using extracted shipping details.' },
];

const POLICY_FIELDS = [
  { key: 'preview_required_for_high_value_order' as const, label: 'Preview high-value orders', hint: 'Require operator approval before progressing high-value draft orders.' },
  { key: 'handoff_for_high_risk' as const, label: 'Handoff on high risk', hint: 'Escalate to a human when the risk scorer flags a high-risk decision.' },
  { key: 'handoff_for_low_variant_confidence' as const, label: 'Handoff on low variant confidence', hint: 'Escalate when variant resolution falls below the configured threshold.' },
];

type RiskFormState = Omit<AgentRiskSettings, 'shop_id'>;

const DEFAULT_FORM: RiskFormState = {
  intent_confidence_threshold: 0.75,
  slot_confidence_threshold: 0.85,
  product_confidence_threshold: 0.8,
  variant_confidence_threshold: 0.85,
  address_confidence_threshold: 0.8,
  high_value_order_threshold: 0,
  handoff_for_high_risk: false,
  handoff_for_low_variant_confidence: false,
  preview_required_for_high_value_order: true,
};

function toPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function settingsToForm(settings: AgentRiskSettings): RiskFormState {
  const { shop_id: _shopId, ...form } = settings;
  return form;
}

function validateForm(form: RiskFormState): string | null {
  for (const field of THRESHOLD_FIELDS) {
    const value = form[field.key];
    if (Number.isNaN(value) || value < 0 || value > 1) {
      return `${field.label} must be between 0 and 1.`;
    }
  }
  if (Number.isNaN(form.high_value_order_threshold) || form.high_value_order_threshold < 0) {
    return 'High-value order threshold must be zero or greater.';
  }
  return null;
}

export function RiskSettingsPage() {
  const { selectedShop, selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<RiskFormState>(DEFAULT_FORM);

  const settingsQuery = useQuery({
    queryKey: ['agent-risk-settings', selectedShopId],
    queryFn: () => apiClient.getAgentRiskSettings(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });

  useEffect(() => {
    if (settingsQuery.data) setForm(settingsToForm(settingsQuery.data));
  }, [settingsQuery.data]);

  const saveMutation = useMutation({
    mutationFn: () => apiClient.updateAgentRiskSettings(selectedShopId!, form),
    onSuccess: (saved) => {
      showToast('Risk settings saved.', 'success');
      setForm(settingsToForm(saved));
      queryClient.setQueryData(['agent-risk-settings', selectedShopId], saved);
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const isDirty = useMemo(() => {
    if (!settingsQuery.data) return false;
    return JSON.stringify(form) !== JSON.stringify(settingsToForm(settingsQuery.data));
  }, [form, settingsQuery.data]);

  function updateField<K extends keyof RiskFormState>(key: K, value: RiskFormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function resetForm() {
    if (settingsQuery.data) setForm(settingsToForm(settingsQuery.data));
    else setForm(DEFAULT_FORM);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!selectedShopId) return;
    const validationError = validateForm(form);
    if (validationError) {
      showToast(validationError, 'error');
      return;
    }
    saveMutation.mutate();
  }

  const activeHandoffs = [
    form.handoff_for_high_risk ? 'High risk' : null,
    form.handoff_for_low_variant_confidence ? 'Low variant confidence' : null,
  ].filter(Boolean);

  return (
    <HubPage
      eyebrow="Automation"
      title="Risk settings"
      description="Configure confidence thresholds and handoff rules for autonomous agent decisions."
    >
      {!selectedShop ? (
        <Card>
          <CardBody>
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          </CardBody>
        </Card>
      ) : null}

      {selectedShopId && settingsQuery.isLoading ? (
        <Card>
          <CardBody>
            <LoadingState label="Loading risk settings…" />
          </CardBody>
        </Card>
      ) : null}

      {settingsQuery.error ? (
        <Card>
          <CardBody>
            <p className="text-sm text-danger" role="alert">
              {settingsQuery.error instanceof Error ? settingsQuery.error.message : 'Failed to load risk settings'}
            </p>
          </CardBody>
        </Card>
      ) : null}

      {selectedShopId && settingsQuery.data ? (
        <form className="flex flex-col gap-5" onSubmit={submit} aria-label="Risk settings form">
          <Card>
            <CardHeader
              title="Current policy snapshot"
              description="Quick view of thresholds and safeguards for the next DM decision."
              actions={<Badge tone="warning">Safety policy</Badge>}
            />
            <CardBody className="flex flex-col gap-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <KpiCard label="Intent threshold" value={toPercent(form.intent_confidence_threshold)} />
                <KpiCard label="Product threshold" value={toPercent(form.product_confidence_threshold)} />
                <KpiCard label="Variant threshold" value={toPercent(form.variant_confidence_threshold)} />
                <KpiCard
                  label="High-value preview"
                  value={form.preview_required_for_high_value_order ? 'Required' : 'Not required'}
                />
              </div>
              <p className="text-sm text-muted">
                Handoff triggers: {activeHandoffs.length ? activeHandoffs.join(', ') : 'None configured'}
                {form.high_value_order_threshold > 0
                  ? ` · High-value threshold: ${form.high_value_order_threshold.toLocaleString()}`
                  : ''}
              </p>
              <div className="flex flex-wrap gap-2">
                <Link to="/system/rollout?view=trl">
                  <Button type="button" variant="secondary" size="sm">Review TRL validation</Button>
                </Link>
                <Link to="/system/rollout?view=readiness">
                  <Button type="button" variant="secondary" size="sm">Review pilot readiness</Button>
                </Link>
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Confidence thresholds" description="Minimum model confidence required before each order-flow step." />
            <CardBody>
              <div className="grid gap-4 sm:grid-cols-2">
                {THRESHOLD_FIELDS.map((field) => (
                  <Field key={field.key} label={field.label}>
                    <Input
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                      value={form[field.key]}
                      onChange={(e) => updateField(field.key, Number(e.target.value))}
                    />
                    <span className="text-xs text-muted">{field.hint}</span>
                  </Field>
                ))}
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="High-value orders" description="Orders above this amount follow stricter preview and handoff rules." />
            <CardBody>
              <Field label="High-value order threshold">
                <Input
                  type="number"
                  min="0"
                  step="1"
                  value={form.high_value_order_threshold}
                  onChange={(e) => updateField('high_value_order_threshold', Number(e.target.value))}
                />
                <span className="text-xs text-muted">Use your shop currency. Set to 0 to disable high-value detection.</span>
              </Field>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Handoff & preview policy" description="When the agent must stop and route to an operator." />
            <CardBody className="flex flex-col gap-4">
              <div className="grid gap-3 sm:grid-cols-2">
                {POLICY_FIELDS.map((field) => (
                  <label key={field.key} className="flex gap-3 rounded-lg border border-border p-3 text-sm">
                    <input
                      type="checkbox"
                      className="mt-0.5 rounded border-border"
                      checked={form[field.key]}
                      onChange={(e) => updateField(field.key, e.target.checked)}
                    />
                    <span>
                      <strong className="text-fg">{field.label}</strong>
                      <span className="mt-0.5 block text-xs text-muted">{field.hint}</span>
                    </span>
                  </label>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={saveMutation.isPending || !isDirty}>
                  {saveMutation.isPending ? 'Saving…' : 'Save risk settings'}
                </Button>
                <Button type="button" variant="secondary" onClick={resetForm} disabled={saveMutation.isPending || !isDirty}>
                  Reset changes
                </Button>
              </div>
            </CardBody>
          </Card>
        </form>
      ) : null}
    </HubPage>
  );
}
