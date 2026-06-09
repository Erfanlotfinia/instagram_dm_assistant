import { FormEvent, useEffect, useState } from 'react';

import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';
import type { AgentRiskSettings } from '../types/conversation';

export function RiskSettingsPage() {
  const { selectedShop } = useShop();
  const [settings, setSettings] = useState<AgentRiskSettings | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedShop) return;
    apiClient.getAgentRiskSettings(selectedShop.id).then(setSettings).catch((exc) => setStatus(exc instanceof Error ? exc.message : 'Failed to load risk settings'));
  }, [selectedShop?.id]);

  if (!selectedShop) return <section className="card"><h1>Risk Settings</h1><p>Select a shop.</p></section>;
  if (!settings) return <section className="card"><h1>Risk Settings</h1><p>Loading…</p></section>;

  function update<K extends keyof AgentRiskSettings>(key: K, value: AgentRiskSettings[K]) {
    setSettings((current) => current ? { ...current, [key]: value } : current);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!selectedShop || !settings) return;
    const saved = await apiClient.updateAgentRiskSettings(selectedShop.id, settings);
    setSettings(saved); setStatus('Risk settings saved.');
  }

  return (
    <section className="page-stack">
      <header className="page-header"><div><h1>Risk Settings</h1><p>Configure deterministic safety gates for preview and handoff.</p></div></header>
      {status ? <div className="alert" role="status">{status}</div> : null}
      <form className="card form-grid" onSubmit={submit} aria-label="Risk settings form">
        {(['intent_confidence_threshold', 'slot_confidence_threshold', 'product_confidence_threshold', 'variant_confidence_threshold', 'address_confidence_threshold'] as const).map((key) => (
          <label key={key}>{key.replaceAll('_', ' ')}<input type="number" min="0" max="1" step="0.01" value={settings[key]} onChange={(event) => update(key, Number(event.target.value))} /></label>
        ))}
        <label>High value order threshold<input type="number" min="0" step="1" value={settings.high_value_order_threshold} onChange={(event) => update('high_value_order_threshold', Number(event.target.value))} /></label>
        <label><input type="checkbox" checked={settings.preview_required_for_high_value_order} onChange={(event) => update('preview_required_for_high_value_order', event.target.checked)} /> Preview high-value orders</label>
        <label><input type="checkbox" checked={settings.handoff_for_high_risk} onChange={(event) => update('handoff_for_high_risk', event.target.checked)} /> Handoff high risk</label>
        <label><input type="checkbox" checked={settings.handoff_for_low_variant_confidence} onChange={(event) => update('handoff_for_low_variant_confidence', event.target.checked)} /> Handoff low variant confidence</label>
        <button className="button" type="submit">Save risk settings</button>
      </form>
    </section>
  );
}
