import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ShopSelector } from '../components/ShopSelector';
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
  {
    key: 'intent_confidence_threshold',
    label: 'Intent confidence',
    hint: 'Minimum confidence before acting on detected customer intent.',
  },
  {
    key: 'slot_confidence_threshold',
    label: 'Slot extraction confidence',
    hint: 'Minimum confidence for size, color, quantity, and address slots.',
  },
  {
    key: 'product_confidence_threshold',
    label: 'Product resolution confidence',
    hint: 'Minimum confidence before selecting a catalog product from DM context.',
  },
  {
    key: 'variant_confidence_threshold',
    label: 'Variant resolution confidence',
    hint: 'Minimum confidence before locking a size/color variant.',
  },
  {
    key: 'address_confidence_threshold',
    label: 'Address confidence',
    hint: 'Minimum confidence before using extracted shipping details.',
  },
];

const POLICY_FIELDS = [
  {
    key: 'preview_required_for_high_value_order' as const,
    label: 'Preview high-value orders',
    hint: 'Require operator approval before progressing high-value draft orders.',
  },
  {
    key: 'handoff_for_high_risk' as const,
    label: 'Handoff on high risk',
    hint: 'Escalate to a human when the risk scorer flags a high-risk decision.',
  },
  {
    key: 'handoff_for_low_variant_confidence' as const,
    label: 'Handoff on low variant confidence',
    hint: 'Escalate when variant resolution falls below the configured threshold.',
  },
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

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="stat-card">
      <p className="stat-card__label">{label}</p>
      <p className="stat-card__value">{value}</p>
    </article>
  );
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
    if (settingsQuery.data) {
      setForm(settingsToForm(settingsQuery.data));
    }
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
    if (settingsQuery.data) {
      setForm(settingsToForm(settingsQuery.data));
      return;
    }
    setForm(DEFAULT_FORM);
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
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Deterministic safety gates</p>
        <h1>Risk Settings</h1>
        <p>
          Configure confidence thresholds and handoff rules that decide when the agent may act
          autonomously, require preview, or escalate to an operator.
        </p>
        <ShopSelector />
      </section>

      {!selectedShop ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="empty-state">Select a shop to configure risk settings.</p>
        </section>
      ) : null}

      {selectedShopId && settingsQuery.isLoading ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="loading-state">Loading risk settings…</p>
        </section>
      ) : null}

      {settingsQuery.error ? (
        <div role="alert" className="alert alert--error">
          {settingsQuery.error instanceof Error ? settingsQuery.error.message : 'Failed to load risk settings'}
        </div>
      ) : null}

      {selectedShopId && settingsQuery.data ? (
        <form className="agent-studio-form" onSubmit={submit} aria-label="Risk settings form">
          <section className="dashboard-card dashboard-card--wide">
            <div className="section-header section-header--stacked">
              <div>
                <h2>Current policy snapshot</h2>
                <p className="dashboard-card__subtitle">
                  Quick view of the thresholds and safeguards that will apply to the next DM decision.
                </p>
              </div>
              <span className="priority-badge priority-badge--medium">Safety policy</span>
            </div>

            <div className="stats-grid">
              <MetricCard label="Intent threshold" value={toPercent(form.intent_confidence_threshold)} />
              <MetricCard label="Product threshold" value={toPercent(form.product_confidence_threshold)} />
              <MetricCard label="Variant threshold" value={toPercent(form.variant_confidence_threshold)} />
              <MetricCard
                label="High-value preview"
                value={form.preview_required_for_high_value_order ? 'Required' : 'Not required'}
              />
            </div>

            <p className="risk-settings-summary">
              Handoff triggers: {activeHandoffs.length ? activeHandoffs.join(', ') : 'None configured'}
              {form.high_value_order_threshold > 0
                ? ` · High-value threshold: ${form.high_value_order_threshold.toLocaleString()}`
                : ''}
            </p>

            <div className="button-row risk-settings-links">
              <Link className="button button--ghost-dark" to="/trl-validation">
                Review TRL validation
              </Link>
              <Link className="button button--ghost-dark" to="/pilot-readiness">
                Review pilot readiness
              </Link>
            </div>
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>Confidence thresholds</h2>
            <p className="dashboard-card__subtitle">
              Minimum model confidence required before the agent acts on each step of the order flow.
            </p>

            <div className="filter-grid">
              {THRESHOLD_FIELDS.map((field) => (
                <label key={field.key} className="form-field">
                  <span>{field.label}</span>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={form[field.key]}
                    onChange={(event) => updateField(field.key, Number(event.target.value))}
                  />
                  <span className="risk-settings-field-hint">{field.hint}</span>
                </label>
              ))}
            </div>
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>High-value orders</h2>
            <p className="dashboard-card__subtitle">
              Orders above this amount follow stricter preview and handoff rules.
            </p>

            <div className="filter-grid">
              <label className="form-field">
                <span>High-value order threshold</span>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={form.high_value_order_threshold}
                  onChange={(event) => updateField('high_value_order_threshold', Number(event.target.value))}
                />
                <span className="risk-settings-field-hint">
                  Use your shop currency. Set to 0 to disable high-value detection.
                </span>
              </label>
            </div>
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>Handoff &amp; preview policy</h2>
            <p className="dashboard-card__subtitle">
              Decide when the agent must stop and route the conversation to an operator.
            </p>

            <div className="agent-safety-grid">
              {POLICY_FIELDS.map((field) => (
                <label key={field.key} className="form-field form-field--checkbox risk-settings-policy">
                  <input
                    type="checkbox"
                    checked={form[field.key]}
                    onChange={(event) => updateField(field.key, event.target.checked)}
                  />
                  <span>
                    <strong>{field.label}</strong>
                    <span className="risk-settings-field-hint">{field.hint}</span>
                  </span>
                </label>
              ))}
            </div>

            <div className="button-row risk-settings-actions">
              <button
                className="button button--primary"
                type="submit"
                disabled={saveMutation.isPending || !isDirty}
              >
                {saveMutation.isPending ? 'Saving…' : 'Save risk settings'}
              </button>
              <button
                className="button button--ghost-dark"
                type="button"
                onClick={resetForm}
                disabled={saveMutation.isPending || !isDirty}
              >
                Reset changes
              </button>
            </div>
          </section>
        </form>
      ) : null}
    </div>
  );
}
