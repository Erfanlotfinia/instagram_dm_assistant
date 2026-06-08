import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import type { AgentStudioSettings } from '../types/competitive';

type Mode = AgentStudioSettings['mode'];
type SellingStyle = AgentStudioSettings['selling_style'];

export function AgentStudioSettingsPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const settings = useQuery({ queryKey: ['agent-settings', selectedShopId], queryFn: () => apiClient.getAgentStudioSettings(selectedShopId), enabled: Boolean(selectedShopId) });
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
    mutationFn: () => apiClient.updateAgentStudioSettings(selectedShopId, {
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
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to save settings', 'error'),
  });

  function submit(event: FormEvent) { event.preventDefault(); update.mutate(); }

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Agent Settings</p>
        <h1>Automation mode & safety</h1>
        <p>Choose Copilot, Controlled Autopilot, or Human-first behavior for Instagram fashion orders.</p>
        <ShopSelector />
      </section>
      <section className="dashboard-card dashboard-card--wide">
        <form className="form-grid" onSubmit={submit} aria-label="Agent Settings form">
          <label>Mode selector<select aria-label="Mode selector" value={mode} onChange={(e) => setMode(e.target.value as Mode)}><option value="copilot">Copilot</option><option value="controlled_autopilot">Controlled Autopilot</option><option value="human_first">Human-first</option></select></label>
          <label>Selling style<select value={sellingStyle} onChange={(e) => setSellingStyle(e.target.value as SellingStyle)}><option value="friendly">Friendly</option><option value="formal">Formal</option><option value="concise">Concise</option><option value="promotional">Promotional</option></select></label>
          <label>Brand voice<textarea value={brandVoice} onChange={(e) => setBrandVoice(e.target.value)} placeholder="Warm, fashion-aware, concise" /></label>
          <label>Intent confidence threshold<input type="number" min="0" max="1" step="0.01" value={intentThreshold} onChange={(e) => setIntentThreshold(e.target.value)} /></label>
          <label>Product confidence threshold<input type="number" min="0" max="1" step="0.01" value={productThreshold} onChange={(e) => setProductThreshold(e.target.value)} /></label>
          <label>Variant confidence threshold<input type="number" min="0" max="1" step="0.01" value={variantThreshold} onChange={(e) => setVariantThreshold(e.target.value)} /></label>
          <label>Address confidence threshold<input type="number" min="0" max="1" step="0.01" value={addressThreshold} onChange={(e) => setAddressThreshold(e.target.value)} /></label>
          <label>High-value order threshold<input type="number" min="0" value={highValue} onChange={(e) => setHighValue(e.target.value)} /></label>
          <label className="checkbox-row"><input type="checkbox" checked={autoSend} onChange={(e) => setAutoSend(e.target.checked)} /> Auto-send enabled</label>
          <label className="checkbox-row"><input type="checkbox" checked={previewLowConfidence} onChange={(e) => setPreviewLowConfidence(e.target.checked)} /> Preview required for low confidence</label>
          <label className="checkbox-row"><input type="checkbox" checked={previewFirstOrder} onChange={(e) => setPreviewFirstOrder(e.target.checked)} /> Preview required for first order</label>
          <label className="checkbox-row"><input type="checkbox" checked={previewHighValue} onChange={(e) => setPreviewHighValue(e.target.checked)} /> Preview required for high-value order</label>
          <button type="submit" disabled={update.isPending || !selectedShopId}>Save agent settings</button>
        </form>
      </section>
    </div>
  );
}
