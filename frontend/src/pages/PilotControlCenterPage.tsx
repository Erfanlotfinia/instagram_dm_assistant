import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input } from '../components/ui';
import { EmptyState } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import type { EmergencyStopScopePreview } from '../types/trust';

const MODES = [
  { id: 'shadow', label: 'Shadow', detail: 'Suggestions only — no state-changing writes' },
  { id: 'copilot', label: 'Copilot', detail: 'Operator approval required for writes' },
  { id: 'autonomous_low_risk', label: 'Autonomous low-risk', detail: 'Writes only when all policies pass' },
] as const;

const ghostLinkClass =
  'inline-flex h-10 items-center rounded-lg px-4 text-sm font-medium text-muted transition-colors hover:bg-surface-sunken hover:text-fg';

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

  return (
    <HubPage
      eyebrow="Trust layer"
      title="Pilot Control Center"
      description="Control operating mode, category/campaign overrides, and emergency stop for the selected shop."
    >
      {!selectedShop ? (
        <Card>
          <CardBody>
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          </CardBody>
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader
              title="Operating mode"
              description={`Current shop: ${selectedShop.name}`}
              actions={
                settings?.emergency_stop_enabled ? (
                  <Badge tone="danger">Emergency stop active</Badge>
                ) : (
                  <Badge tone="neutral">{currentMode}</Badge>
                )
              }
            />
            <CardBody className="flex flex-col gap-4">
              <Field label="Reason for mode change">
                <Input value={modeReason} onChange={(e) => setModeReason(e.target.value)} placeholder="Optional" />
              </Field>

              <div className="flex flex-wrap gap-2" role="group" aria-label="Operating mode">
                {MODES.map((mode) => (
                  <Button
                    key={mode.id}
                    type="button"
                    size="sm"
                    variant={currentMode === mode.id ? 'primary' : 'secondary'}
                    disabled={modeMutation.isPending}
                    onClick={() => modeMutation.mutate(mode.id)}
                  >
                    {mode.label}
                  </Button>
                ))}
              </div>

              <ul className="list-inside list-disc space-y-1 text-sm text-muted">
                {MODES.map((mode) => (
                  <li key={mode.id}>
                    <strong className="text-fg">{mode.label}</strong> — {mode.detail}
                  </li>
                ))}
              </ul>

              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="danger"
                  onClick={() => setStopDialogOpen(true)}
                  disabled={stopMutation.isPending || settings?.emergency_stop_enabled}
                >
                  Emergency stop
                </Button>
                <Link className={ghostLinkClass} to="/incidents">
                  View incidents
                </Link>
              </div>

              {scopePreview ? (
                <div className="rounded-lg border border-warning/30 bg-warning-soft/30 px-4 py-3 text-sm text-fg" role="note">
                  Last stop affected {scopePreview.active_conversation_count} active conversation(s),{' '}
                  {scopePreview.simulation_conversation_count} simulation conversation(s).
                </div>
              ) : null}
            </CardBody>
          </Card>

          {stopDialogOpen ? (
            <Card>
              <CardHeader
                title="Scope preview"
                description="Active conversations will remain open but automation will not write orders or send messages."
              />
              <CardBody>
                <Field label="Reason">
                  <textarea
                    value={stopReason}
                    onChange={(e) => setStopReason(e.target.value)}
                    rows={3}
                    className="w-full resize-y rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg focus:border-accent focus:outline-none"
                  />
                </Field>
              </CardBody>
            </Card>
          ) : null}
        </>
      )}

      <ConfirmDialog
        open={stopDialogOpen}
        title="Activate emergency stop?"
        message="This immediately blocks all state-changing automation for the selected shop. Review scope before confirming."
        confirmLabel="Activate emergency stop"
        onConfirm={() => stopMutation.mutate()}
        onCancel={() => setStopDialogOpen(false)}
        isLoading={stopMutation.isPending}
      />
    </HubPage>
  );
}
