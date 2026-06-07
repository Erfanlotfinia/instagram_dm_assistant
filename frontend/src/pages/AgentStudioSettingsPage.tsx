import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';
import type { AgentStudioSettings } from '../types/competitive';

export function AgentStudioSettingsPage() {
  const { selectedShopId } = useShop();
  const settings = useQuery({ queryKey: ['agent-studio-settings', selectedShopId], queryFn: () => apiClient.getAgentStudioSettings(selectedShopId), enabled: Boolean(selectedShopId) });
  const [brandVoice, setBrandVoice] = useState('');
  const [sellingStyle, setSellingStyle] = useState('balanced');
  const [autoSend, setAutoSend] = useState(true);
  const [variantThreshold, setVariantThreshold] = useState('0.85');
  const [highValue, setHighValue] = useState('0');
  useEffect(() => {
    if (settings.data) {
      setBrandVoice(settings.data.brand_voice ?? '');
      setSellingStyle(settings.data.selling_style);
      setAutoSend(settings.data.auto_send_enabled);
      setVariantThreshold(String(settings.data.confidence_threshold_variant));
      setHighValue(String(settings.data.high_value_order_threshold));
    }
  }, [settings.data]);
  const update = useMutation({ mutationFn: () => apiClient.updateAgentStudioSettings(selectedShopId, { brand_voice: brandVoice, selling_style: sellingStyle as AgentStudioSettings['selling_style'], auto_send_enabled: autoSend, confidence_threshold_variant: variantThreshold, high_value_order_threshold: highValue }) });
  function submit(event: FormEvent) { event.preventDefault(); update.mutate(); }
  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide"><p className="dashboard-card__eyebrow">Agent Studio</p><h1>Agent settings</h1><p>Control brand voice, preview safety, handoff policy, and deterministic discount boundaries.</p><ShopSelector /></section>
      <section className="dashboard-card dashboard-card--wide"><form className="form-grid" onSubmit={submit}>
        <label>Brand voice<textarea value={brandVoice} onChange={(e) => setBrandVoice(e.target.value)} placeholder="Warm, concise, fashion-aware Persian/English support" /></label>
        <label>Selling style<select value={sellingStyle} onChange={(e) => setSellingStyle(e.target.value)}><option value="educational">Educational</option><option value="balanced">Balanced</option><option value="promotional">Promotional</option></select></label>
        <label>Variant confidence threshold<input type="number" min="0" max="1" step="0.01" value={variantThreshold} onChange={(e) => setVariantThreshold(e.target.value)} /></label>
        <label>High-value preview threshold<input type="number" min="0" value={highValue} onChange={(e) => setHighValue(e.target.value)} /></label>
        <label className="checkbox-row"><input type="checkbox" checked={autoSend} onChange={(e) => setAutoSend(e.target.checked)} /> Auto-send enabled</label>
        <button type="submit" disabled={update.isPending}>Save settings</button>
      </form></section>
      <section className="dashboard-card dashboard-card--wide"><h2>Safety rules</h2><ul><li>Discounts can only come from admin policy JSON.</li><li>Selling style affects wording only, never stock, price, shipping, payment, or order state.</li><li>Low-confidence and high-value orders are previewed before sending.</li></ul></section>
    </div>
  );
}
