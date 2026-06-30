import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input } from '../components/ui';
import { Callout } from '../components/ui';
import { EmptyState } from '../components/data';
import { RolloutGateChecklist } from '../components/rollout/RolloutGateChecklist';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import { evaluateRolloutGate } from '../lib/rolloutGate';
import { loadCachedTrustSummary } from '../lib/trustEvaluation';
import { useShopReadiness } from '../lib/useShopReadiness';
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

  // Rollout gate inputs — all read-only, reused from existing endpoints.
  const riskSettingsQuery = useQuery({
    queryKey: ['agent-risk-settings', selectedShopId],
    queryFn: () => apiClient.getAgentRiskSettings(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });
  const channelsQuery = useQuery({
    queryKey: ['channel-accounts', selectedShopId],
    queryFn: () => apiClient.listChannelAccounts(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });
  const replayRunsQuery = useQuery({
    queryKey: ['replay-runs', selectedShopId],
    queryFn: () => apiClient.listReplayRuns(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });
  const failedJobsQuery = useQuery({
    queryKey: ['failed-jobs', selectedShopId, 'active'],
    queryFn: () => apiClient.listFailedJobs(selectedShopId!, { status: 'failed', page: 1 }),
    enabled: Boolean(selectedShopId),
  });

  // Sprint 2 shop readiness — feeds the rollout gate as an optional augment.
  // Fails open: while loading or errored, the gate keeps its Sprint 3 behavior.
  const shopReadinessQuery = useShopReadiness(selectedShopId);

  const gateLoading =
    riskSettingsQuery.isLoading ||
    channelsQuery.isLoading ||
    replayRunsQuery.isLoading ||
    failedJobsQuery.isLoading;

  const gateState = useMemo(() => {
    if (!selectedShopId) return null;
    return evaluateRolloutGate({
      // The aggregate regression metrics are not auto-run here; the gate
      // treats a missing regression as a blocker, prompting the operator to
      // run the suite on the Regression tab.
      regression: null,
      latestRun: replayRunsQuery.data?.[0] ?? null,
      riskSettings: riskSettingsQuery.data ?? null,
      channels: channelsQuery.data ?? [],
      pilot: settingsQuery.data ?? null,
      failedJobsCount: failedJobsQuery.data?.total ?? 0,
      // Sprint 6 — optional red-team summary from the Trust Center cache.
      // Null when no trust run has been recorded; gate keeps Sprint 3 behavior.
      trustEvaluationSummary: loadCachedTrustSummary(selectedShopId),
    });
  }, [
    selectedShopId,
    replayRunsQuery.data,
    riskSettingsQuery.data,
    channelsQuery.data,
    settingsQuery.data,
    failedJobsQuery.data,
  ]);

  const enableAutomation = () => {
    if (!gateState?.ready) {
      showToast('Resolve all blocking reasons before enabling automation.', 'error');
      return;
    }
    modeMutation.mutate('autonomous_low_risk');
  };

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
          <RolloutGateChecklist
            state={gateState}
            loading={gateLoading}
            onEnableAutomation={enableAutomation}
            enabling={modeMutation.isPending}
            automationEnabled={currentMode === 'autonomous_low_risk'}
            shopReadiness={shopReadinessQuery.shopReadiness}
            shopReadinessLoading={shopReadinessQuery.isLoading}
            trustEvaluationSummary={loadCachedTrustSummary(selectedShopId)}
            trustEvaluationLoading={false}
          />

          {shopReadinessQuery.error ? (
            <Callout title="Shop readiness unavailable">
              Sprint 2 readiness could not be loaded — the rollout gate is using its existing checks only.
            </Callout>
          ) : null}

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
                {MODES.map((mode) => {
                  const gateBlocksAutonomous = Boolean(
                    mode.id === 'autonomous_low_risk' && gateState && !gateState.ready,
                  );
                  return (
                    <Button
                      key={mode.id}
                      type="button"
                      size="sm"
                      variant={currentMode === mode.id ? 'primary' : 'secondary'}
                      disabled={modeMutation.isPending || gateBlocksAutonomous}
                      onClick={() => modeMutation.mutate(mode.id)}
                      aria-disabled={gateBlocksAutonomous || undefined}
                      title={
                        gateBlocksAutonomous
                          ? 'Rollout readiness gate must pass before enabling autonomous mode.'
                          : undefined
                      }
                    >
                      {mode.label}
                    </Button>
                  );
                })}
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
