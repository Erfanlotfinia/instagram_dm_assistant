import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import type { AgentStudioSettings } from '../types/competitive';

type Mode = AgentStudioSettings['mode'];
type SellingStyle = AgentStudioSettings['selling_style'];

const MODE_OPTIONS: { id: Mode; label: string; description: string }[] = [
  {
    id: 'copilot',
    label: 'Copilot',
    description: 'Draft replies for operators. Nothing sends until a human approves.',
  },
  {
    id: 'controlled_autopilot',
    label: 'Controlled Autopilot',
    description: 'Auto-send when confidence and safety gates pass; preview when they do not.',
  },
  {
    id: 'human_first',
    label: 'Human-first',
    description: 'Prioritize operator handoff with minimal automated sending.',
  },
];

const SELLING_STYLE_OPTIONS: { value: SellingStyle; label: string }[] = [
  { value: 'friendly', label: 'Friendly' },
  { value: 'formal', label: 'Formal' },
  { value: 'concise', label: 'Concise' },
  { value: 'promotional', label: 'Promotional' },
  { value: 'educational', label: 'Educational' },
  { value: 'balanced', label: 'Balanced' },
];

export function AgentStudioSettingsPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const settings = useQuery({
    queryKey: ['agent-settings', selectedShopId],
    queryFn: () => apiClient.getAgentStudioSettings(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const [mode, setMode] = useState<Mode>('copilot');
  const [brandVoice, setBrandVoice] = useState('');
  const [sellingStyle, setSellingStyle] = useState<SellingStyle>('friendly');
  const [autoSend, setAutoSend] = useState(false);
  const [previewLowConfidence, setPreviewLowConfidence] = useState(true);
  const [previewFirstOrder, setPreviewFirstOrder] = useState(true);
  const [previewHighValue, setPreviewHighValue] = useState(true);
  const [intentThreshold, setIntentThreshold] = useState('0.75');
  const [productThreshold, setProductThreshold] = useState('0.80');
  const [variantThreshold, setVariantThreshold] = useState('0.85');
  const [addressThreshold, setAddressThreshold] = useState('0.80');
  const [highValue, setHighValue] = useState('0');

  useEffect(() => {
    if (settings.data) {
      setMode(settings.data.mode);
      setBrandVoice(settings.data.brand_voice ?? '');
      setSellingStyle(settings.data.selling_style);
      setAutoSend(settings.data.auto_send_enabled);
      setPreviewLowConfidence(settings.data.preview_required_for_low_confidence);
      setPreviewFirstOrder(settings.data.preview_required_for_first_order);
      setPreviewHighValue(settings.data.preview_required_for_high_value_order);
      setIntentThreshold(String(settings.data.confidence_threshold_intent));
      setProductThreshold(String(settings.data.confidence_threshold_product));
      setVariantThreshold(String(settings.data.confidence_threshold_variant));
      setAddressThreshold(String(settings.data.confidence_threshold_address));
      setHighValue(String(settings.data.high_value_order_threshold));
    }
  }, [settings.data]);

  const update = useMutation({
    mutationFn: () =>
      apiClient.updateAgentStudioSettings(selectedShopId, {
        mode,
        brand_voice: brandVoice || null,
        selling_style: sellingStyle,
        auto_send_enabled: autoSend,
        preview_required_for_low_confidence: previewLowConfidence,
        preview_required_for_first_order: previewFirstOrder,
        preview_required_for_high_value_order: previewHighValue,
        confidence_threshold_intent: intentThreshold,
        confidence_threshold_product: productThreshold,
        confidence_threshold_variant: variantThreshold,
        confidence_threshold_address: addressThreshold,
        high_value_order_threshold: highValue,
      }),
    onSuccess: () => {
      showToast('Agent settings saved.', 'success');
      queryClient.invalidateQueries({ queryKey: ['agent-settings', selectedShopId] });
    },
    onError: (error) =>
      showToast(error instanceof Error ? error.message : 'Failed to save settings', 'error'),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    update.mutate();
  }

  const selectedMode = MODE_OPTIONS.find((option) => option.id === mode);

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Agent studio</p>
        <h1>Automation mode & safety</h1>
        <p>
          Configure how the Instagram DM agent drafts replies, auto-sends messages, and escalates
          to operators for fashion orders.
        </p>
        <ShopSelector />
      </section>

      {!selectedShopId ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="empty-state">Select a shop to configure agent behavior.</p>
        </section>
      ) : null}

      {selectedShopId && settings.isLoading ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="loading-state">Loading agent settings...</p>
        </section>
      ) : null}

      {settings.error ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="form-error">
            {settings.error instanceof Error ? settings.error.message : 'Failed to load settings'}
          </p>
        </section>
      ) : null}

      {selectedShopId && !settings.isLoading && !settings.error ? (
        <form className="agent-studio-form" onSubmit={submit} aria-label="Agent Settings form">
          <section className="dashboard-card dashboard-card--wide">
            <h2>Automation mode</h2>
            <p className="analytics-toolbar__summary">
              Choose how much autonomy the agent has before an operator gets involved.
            </p>

            <div className="agent-mode-grid" role="radiogroup" aria-label="Automation mode">
              {MODE_OPTIONS.map((option) => {
                const isActive = mode === option.id;
                return (
                  <button
                    key={option.id}
                    type="button"
                    className={`agent-mode-card${isActive ? ' agent-mode-card--active' : ''}`}
                    aria-label={option.label}
                    aria-pressed={isActive}
                    onClick={() => setMode(option.id)}
                  >
                    <span className="agent-mode-card__label">{option.label}</span>
                    <span className="agent-mode-card__description">{option.description}</span>
                  </button>
                );
              })}
            </div>

            {selectedMode ? (
              <p className="match-panel agent-studio-form__mode-summary">{selectedMode.description}</p>
            ) : null}
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>Voice & tone</h2>
            <p className="analytics-toolbar__summary">
              Shape how the agent sounds when it replies to customers.
            </p>

            <div className="filter-grid">
              <label className="form-field">
                <span>Selling style</span>
                <select
                  value={sellingStyle}
                  onChange={(event) => setSellingStyle(event.target.value as SellingStyle)}
                >
                  {SELLING_STYLE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field form-field--wide">
                <span>Brand voice</span>
                <textarea
                  value={brandVoice}
                  onChange={(event) => setBrandVoice(event.target.value)}
                  placeholder="Warm, fashion-aware, concise"
                  rows={4}
                />
              </label>
            </div>
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>Confidence thresholds</h2>
            <p className="analytics-toolbar__summary">
              Minimum model confidence required before the agent acts on each step of the order flow.
            </p>

            <div className="filter-grid">
              <label className="form-field">
                <span>Intent confidence</span>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  value={intentThreshold}
                  onChange={(event) => setIntentThreshold(event.target.value)}
                />
              </label>
              <label className="form-field">
                <span>Product confidence</span>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  value={productThreshold}
                  onChange={(event) => setProductThreshold(event.target.value)}
                />
              </label>
              <label className="form-field">
                <span>Variant confidence</span>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  value={variantThreshold}
                  onChange={(event) => setVariantThreshold(event.target.value)}
                />
              </label>
              <label className="form-field">
                <span>Address confidence</span>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  value={addressThreshold}
                  onChange={(event) => setAddressThreshold(event.target.value)}
                />
              </label>
              <label className="form-field">
                <span>High-value order threshold</span>
                <input
                  type="number"
                  min="0"
                  value={highValue}
                  onChange={(event) => setHighValue(event.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>Safety gates</h2>
            <p className="analytics-toolbar__summary">
              Decide when the agent may send automatically and when a human preview is required.
            </p>

            <div className="agent-safety-grid">
              <label className="form-field form-field--checkbox">
                <input
                  type="checkbox"
                  checked={autoSend}
                  onChange={(event) => setAutoSend(event.target.checked)}
                />
                <span>Auto-send enabled</span>
              </label>
              <label className="form-field form-field--checkbox">
                <input
                  type="checkbox"
                  checked={previewLowConfidence}
                  onChange={(event) => setPreviewLowConfidence(event.target.checked)}
                />
                <span>Preview required for low confidence</span>
              </label>
              <label className="form-field form-field--checkbox">
                <input
                  type="checkbox"
                  checked={previewFirstOrder}
                  onChange={(event) => setPreviewFirstOrder(event.target.checked)}
                />
                <span>Preview required for first order</span>
              </label>
              <label className="form-field form-field--checkbox">
                <input
                  type="checkbox"
                  checked={previewHighValue}
                  onChange={(event) => setPreviewHighValue(event.target.checked)}
                />
                <span>Preview required for high-value order</span>
              </label>
            </div>

            <div className="button-row">
              <button
                className="button button--primary"
                type="submit"
                disabled={update.isPending || !selectedShopId}
              >
                {update.isPending ? 'Saving…' : 'Save agent settings'}
              </button>
            </div>
          </section>
        </form>
      ) : null}
    </div>
  );
}
