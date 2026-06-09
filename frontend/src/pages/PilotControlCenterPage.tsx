import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import type { EmergencyStopScopePreview } from '../types/trust';

const MODES = [
  { id: 'shadow', label: 'Shadow', detail: 'Suggestions only — no state-changing writes' },
  { id: 'copilot', label: 'Copilot', detail: 'Operator approval required for writes' },
  { id: 'autonomous_low_risk', label: 'Autonomous low-risk', detail: 'Writes only when all policies pass' },
] as const;

export function PilotControlCenterPage() {
  const { selectedShop, selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [stopDialogOpen, setStopDialogOpen] = useState(false);
  const [stopReason, setStopReason] = useState('');
  const [scopePreview, setScopePreview] = useState<EmergencyStopScopePreview | null>(null);
  const [modeReason, setModeReason] = useState('');

  const settingsQuery = useQuery({
    queryKey: ['pilot-settings', selectedShopId],
    queryFn: () => apiClient.getPilotSettings(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });

  const modeMutation = useMutation({
    mutationFn: (operating_mode: string) =>
      apiClient.updatePilotMode(selectedShopId!, { operating_mode, reason: modeReason || null }),
    onSuccess: () => {
      showToast('Pilot operating mode updated', 'success');
      void queryClient.invalidateQueries({ queryKey: ['pilot-settings', selectedShopId] });
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const stopMutation = useMutation({
    mutationFn: () => apiClient.activatePilotModeEmergencyStop(selectedShopId!, stopReason || undefined),
    onSuccess: (data) => {
      showToast('Emergency stop activated', 'success');
      setScopePreview(data.scope_preview);
      setStopDialogOpen(false);
      void queryClient.invalidateQueries({ queryKey: ['pilot-settings', selectedShopId] });
      if (data.incident_id) {
        showToast(`Incident opened: ${data.incident_id}`, 'info');
      }
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const settings = settingsQuery.data;
  const currentMode = settings?.operating_mode ?? 'copilot';

  if (!selectedShop) {
    return (
      <section className="dashboard-card dashboard-card--wide">
        <h1>Pilot Control Center</h1>
        <ShopSelector />
      </section>
    );
  }

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Trust layer</p>
        <h1>Pilot Control Center</h1>
        <p>Control operating mode, category/campaign overrides, and emergency stop for the selected shop.</p>
        <ShopSelector />
      </section>

      <section className="dashboard-card dashboard-card--wide pilot-safeguards">
        <div className="section-header">
          <h2>Operating mode</h2>
          <span
            className={
              settings?.emergency_stop_enabled
                ? 'priority-badge priority-badge--urgent'
                : 'priority-badge priority-badge--medium'
            }
          >
            {settings?.emergency_stop_enabled ? 'Emergency stop active' : currentMode}
          </span>
        </div>
        <label className="form-field">
          <span>Reason for mode change</span>
          <input value={modeReason} onChange={(e) => setModeReason(e.target.value)} placeholder="Optional" />
        </label>
        <div className="filter-chips" role="group" aria-label="Operating mode">
          {MODES.map((mode) => (
            <button
              key={mode.id}
              type="button"
              className={`filter-chip${currentMode === mode.id ? ' filter-chip--active' : ''}`}
              disabled={modeMutation.isPending}
              onClick={() => modeMutation.mutate(mode.id)}
            >
              {mode.label}
            </button>
          ))}
        </div>
        <ul className="checklist">
          {MODES.map((mode) => (
            <li key={mode.id}>
              <strong>{mode.label}</strong> — {mode.detail}
            </li>
          ))}
        </ul>
        <div className="button-row pilot-safeguards__actions">
          <button
            className="button button--danger"
            type="button"
            onClick={() => setStopDialogOpen(true)}
            disabled={stopMutation.isPending || settings?.emergency_stop_enabled}
          >
            Emergency stop
          </button>
          <Link className="button button--ghost-dark" to="/incidents">
            View incidents
          </Link>
        </div>
        {scopePreview ? (
          <div className="alert alert--warning">
            Last stop affected {scopePreview.active_conversation_count} active conversation(s),{' '}
            {scopePreview.simulation_conversation_count} simulation conversation(s).
          </div>
        ) : null}
      </section>

      <ConfirmDialog
        open={stopDialogOpen}
        title="Activate emergency stop?"
        message="This immediately blocks all state-changing automation for the selected shop. Review scope before confirming."
        confirmLabel="Activate emergency stop"
        onConfirm={() => stopMutation.mutate()}
        onCancel={() => setStopDialogOpen(false)}
        isLoading={stopMutation.isPending}
      />
      {stopDialogOpen ? (
        <section className="dashboard-card dashboard-card--wide">
          <h3>Scope preview</h3>
          <p className="dashboard-card__subtitle">
            Active conversations will remain open but automation will not write orders or send messages.
          </p>
          <label className="form-field">
            <span>Reason</span>
            <textarea value={stopReason} onChange={(e) => setStopReason(e.target.value)} rows={3} />
          </label>
        </section>
      ) : null}
    </div>
  );
}
