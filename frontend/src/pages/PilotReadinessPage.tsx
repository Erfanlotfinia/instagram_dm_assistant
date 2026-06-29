import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field } from '../components/ui';
import type { BadgeTone } from '../components/ui';
import { DataTable, EmptyState, KpiCard, LoadingState } from '../components/data';
import type { Column } from '../components/data';
import { PilotChecklistPanel } from '../components/rollout/PilotChecklistPanel';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { cn } from '../lib/cn';
import { apiClient } from '../services/apiClient';
import type { PilotChecklistItem, PilotEvent, PilotMetrics, PilotReadinessResponse } from '../types/pilot';
import type { EmergencyStopScopePreview } from '../types/trust';

type EventFilter = 'all' | PilotEvent['severity'];

const METRIC_GROUPS: Array<{ title: string; keys: Array<keyof PilotMetrics> }> = [
  {
    title: 'Message traffic',
    keys: ['inbound_messages', 'auto_sent_messages', 'previewed_messages', 'human_handoff_count'],
  },
  {
    title: 'Orders',
    keys: ['draft_orders', 'confirmed_orders', 'paid_orders', 'cancelled_orders'],
  },
  {
    title: 'Reliability',
    keys: ['failed_jobs', 'invalid_llm_outputs', 'operator_takeover_count'],
  },
  {
    title: 'Response time',
    keys: ['average_response_time_ms', 'p95_response_time_ms'],
  },
];

const METRIC_LABELS: Record<keyof PilotMetrics, string> = {
  inbound_messages: 'Inbound messages',
  auto_sent_messages: 'Auto-sent messages',
  previewed_messages: 'Previewed messages',
  human_handoff_count: 'Human handoffs',
  draft_orders: 'Draft orders',
  confirmed_orders: 'Confirmed orders',
  paid_orders: 'Paid orders',
  cancelled_orders: 'Cancelled orders',
  failed_jobs: 'Failed jobs',
  invalid_llm_outputs: 'Invalid LLM outputs',
  average_response_time_ms: 'Avg response time',
  p95_response_time_ms: 'P95 response time',
  operator_takeover_count: 'Operator takeovers',
};

function formatTrlValidationStatus(
  latest: PilotReadinessResponse['latest_trl_validation'],
  criteria: PilotChecklistItem[] | undefined,
): string {
  if (!latest) return 'No run';
  const validationCriterion = criteria?.find((item) => item.key === 'latest_trl_validation');
  if (validationCriterion?.passed || latest.thresholds_met === true) return 'Passed';
  if (latest.status === 'running') return 'Running';
  if (latest.status === 'failed') return 'Failed';
  if (latest.status === 'completed') return 'Thresholds not met';
  return String(latest.status ?? 'Unknown');
}

function formatMetricValue(key: keyof PilotMetrics, value: number) {
  if (key === 'average_response_time_ms' || key === 'p95_response_time_ms') {
    return `${Math.round(value)}ms`;
  }
  return String(Math.round(value));
}

function metricTone(key: keyof PilotMetrics, value: number): 'success' | 'warning' | undefined {
  if (key === 'failed_jobs' || key === 'invalid_llm_outputs') {
    return value > 0 ? 'warning' : 'success';
  }
  return undefined;
}

function severityTone(severity: PilotEvent['severity']): BadgeTone {
  switch (severity) {
    case 'critical':
    case 'error':
      return 'danger';
    case 'warning':
      return 'warning';
    default:
      return 'neutral';
  }
}

function Chip({
  active,
  onClick,
  children,
}: {
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
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

function ChecklistPanel({
  title,
  subtitle,
  items,
}: {
  title: string;
  subtitle: string;
  items: PilotChecklistItem[];
}) {
  const passed = items.filter((item) => item.passed).length;

  return (
    <Card>
      <CardHeader
        title={title}
        description={subtitle}
        actions={
          <Badge tone={passed === items.length ? 'success' : 'warning'}>
            {passed}/{items.length} passed
          </Badge>
        }
      />
      <CardBody>
        <ul className="space-y-2 text-sm">
          {items.map((item) => (
            <li
              key={item.key}
              className={cn(
                'rounded-md border px-3 py-2',
                item.passed ? 'border-success/30 bg-success-soft/20' : 'border-danger/30 bg-danger-soft/20',
              )}
            >
              <strong className="text-fg">
                {item.passed ? '✅' : '❌'} {item.label}
              </strong>
              {item.detail ? <span className="text-muted"> — {item.detail}</span> : null}
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

function filterEvents(events: PilotEvent[], filter: EventFilter) {
  if (filter === 'all') return events;
  return events.filter((event) => event.severity === filter);
}

export function PilotReadinessPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [stopDialogOpen, setStopDialogOpen] = useState(false);
  const [stopReason, setStopReason] = useState('');
  const [scopePreview, setScopePreview] = useState<EmergencyStopScopePreview | null>(null);
  const [eventFilter, setEventFilter] = useState<EventFilter>('all');

  const readinessQuery = useQuery({
    queryKey: ['pilot-readiness', selectedShopId],
    queryFn: () => apiClient.getPilotReadiness(selectedShopId!),
    enabled: Boolean(selectedShopId),
    refetchInterval: 30_000,
  });

  const metricsQuery = useQuery({
    queryKey: ['pilot-metrics', selectedShopId],
    queryFn: () => apiClient.getPilotMetrics(selectedShopId!),
    enabled: Boolean(selectedShopId),
    refetchInterval: 30_000,
  });

  const eventsQuery = useQuery({
    queryKey: ['pilot-events', selectedShopId],
    queryFn: () => apiClient.getPilotEvents(selectedShopId!),
    enabled: Boolean(selectedShopId),
    refetchInterval: 30_000,
  });

  const refreshPilot = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['pilot-readiness', selectedShopId] }),
      queryClient.invalidateQueries({ queryKey: ['pilot-metrics', selectedShopId] }),
      queryClient.invalidateQueries({ queryKey: ['pilot-events', selectedShopId] }),
    ]);
  };

  const stopMutation = useMutation({
    mutationFn: () => apiClient.activatePilotModeEmergencyStop(selectedShopId!, stopReason || undefined),
    onSuccess: async (data) => {
      showToast('Emergency stop activated', 'success');
      setScopePreview(data.scope_preview);
      setStopDialogOpen(false);
      queryClient.setQueryData(['pilot-readiness', selectedShopId], (current) =>
        current ? { ...current, pilot_settings: data.pilot_settings } : current,
      );
      await queryClient.invalidateQueries({ queryKey: ['pilot-events', selectedShopId] });
      await queryClient.invalidateQueries({ queryKey: ['pilot-readiness', selectedShopId] });
      if (data.incident_id) {
        showToast(`Incident opened: ${data.incident_id}`, 'info');
      }
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const resumeMutation = useMutation({
    mutationFn: () => apiClient.resumePilot(selectedShopId!),
    onSuccess: async (data) => {
      showToast('Pilot automation resumed', 'success');
      queryClient.setQueryData(['pilot-readiness', selectedShopId], (current) =>
        current ? { ...current, pilot_settings: data.pilot_settings } : current,
      );
      await queryClient.invalidateQueries({ queryKey: ['pilot-events', selectedShopId] });
      await queryClient.invalidateQueries({ queryKey: ['pilot-readiness', selectedShopId] });
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const readiness = readinessQuery.data;
  const settings = readiness?.pilot_settings;
  const metrics = metricsQuery.data;
  const allEvents = eventsQuery.data?.events ?? [];
  const events = useMemo(() => filterEvents(allEvents, eventFilter), [allEvents, eventFilter]);

  const eventCounts = useMemo(
    () => ({
      all: allEvents.length,
      info: allEvents.filter((event) => event.severity === 'info').length,
      warning: allEvents.filter((event) => event.severity === 'warning').length,
      error: allEvents.filter((event) => event.severity === 'error').length,
      critical: allEvents.filter((event) => event.severity === 'critical').length,
    }),
    [allEvents],
  );

  const failedJobs = metrics?.failed_jobs ?? 0;
  const validationPassed =
    readiness?.criteria.some((item) => item.key === 'latest_trl_validation' && item.passed) ?? false;
  const validationOutdated = Boolean(readiness && !validationPassed);
  const criteriaPassed = readiness?.criteria.filter((item) => item.passed).length ?? 0;
  const criteriaTotal = readiness?.criteria.length ?? 0;
  const checklistPassed = readiness?.checklist.filter((item) => item.passed).length ?? 0;
  const checklistTotal = readiness?.checklist.length ?? 0;

  const eventColumns: Column<PilotEvent>[] = [
    {
      key: 'time',
      header: 'Time',
      render: (event) => new Date(event.created_at).toLocaleString(),
    },
    {
      key: 'severity',
      header: 'Severity',
      render: (event) => <Badge tone={severityTone(event.severity)}>{event.severity}</Badge>,
    },
    {
      key: 'title',
      header: 'Event',
      render: (event) => event.title,
    },
    {
      key: 'description',
      header: 'Description',
      render: (event) => event.description ?? event.event_type,
    },
  ];

  const pilotStatusBadge = settings?.emergency_stop_enabled
    ? { label: 'Emergency stop active', tone: 'danger' as const }
    : settings?.pilot_enabled
      ? { label: 'Pilot active', tone: 'warning' as const }
      : { label: 'Pilot idle', tone: 'neutral' as const };

  return (
    <HubPage
      eyebrow="Field pilot operations"
      title="TRL 6 Pilot Readiness"
      description="Operational checklist, safeguards, live metrics, and event log for realistic multi-channel commerce pilots."
    >
      {!selectedShopId ? (
        <Card>
          <CardBody>
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          </CardBody>
        </Card>
      ) : null}

      {selectedShopId ? (
        <>
          <PilotChecklistPanel shopId={selectedShopId} />

          <Card>
            <CardHeader
              title="Pilot safeguards"
              description="Emergency stop immediately disables auto-send and auto-order progression for the selected shop."
              actions={<Badge tone={pilotStatusBadge.tone}>{pilotStatusBadge.label}</Badge>}
            />
            <CardBody className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                {settings?.pilot_enabled ? (
                  <div className="rounded-md border border-warning/30 bg-warning-soft/30 px-3 py-2 text-sm text-fg" role="note">
                    Pilot mode active: automation is constrained by pilot limits and approvals.
                  </div>
                ) : null}
                {settings?.emergency_stop_enabled ? (
                  <div className="rounded-md border border-danger/30 bg-danger-soft/30 px-3 py-2 text-sm text-fg" role="alert">
                    Emergency stop active: auto-send and auto-order progression are disabled.
                  </div>
                ) : null}
                {scopePreview ? (
                  <div className="rounded-md border border-warning/30 bg-warning-soft/30 px-3 py-2 text-sm text-fg" role="note">
                    Last emergency stop affected {scopePreview.active_conversation_count} active conversation(s),{' '}
                    {scopePreview.simulation_conversation_count} simulation conversation(s).
                  </div>
                ) : null}
                {settings && !settings.pilot_enabled ? (
                  <div className="rounded-md border border-warning/30 bg-warning-soft/30 px-3 py-2 text-sm text-fg" role="note">
                    Auto-send disabled for pilot traffic until pilot mode is enabled.
                  </div>
                ) : null}
                {validationOutdated ? (
                  <div className="rounded-md border border-warning/30 bg-warning-soft/30 px-3 py-2 text-sm text-fg" role="note">
                    Validation outdated or failing:{' '}
                    <Link className="font-medium text-accent hover:underline" to="/trl-validation">
                      run TRL validation
                    </Link>{' '}
                    before field traffic.
                  </div>
                ) : null}
                {failedJobs > 0 ? (
                  <div className="rounded-md border border-danger/30 bg-danger-soft/30 px-3 py-2 text-sm text-fg" role="alert">
                    Failed jobs present:{' '}
                    <Link className="font-medium text-accent hover:underline" to="/system-health">
                      resolve worker failures
                    </Link>{' '}
                    before expanding the pilot.
                  </div>
                ) : null}
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  variant="danger"
                  type="button"
                  onClick={() => setStopDialogOpen(true)}
                  disabled={stopMutation.isPending || resumeMutation.isPending || settings?.emergency_stop_enabled}
                >
                  {stopMutation.isPending ? 'Stopping…' : 'Emergency stop'}
                </Button>
                <Button
                  type="button"
                  onClick={() => resumeMutation.mutate()}
                  disabled={resumeMutation.isPending || stopMutation.isPending || !settings?.emergency_stop_enabled}
                >
                  {resumeMutation.isPending ? 'Resuming…' : 'Resume pilot'}
                </Button>
                <Button
                  variant="secondary"
                  type="button"
                  onClick={() => void refreshPilot()}
                  disabled={readinessQuery.isFetching || metricsQuery.isFetching || eventsQuery.isFetching}
                >
                  {readinessQuery.isFetching ? 'Refreshing…' : 'Refresh data'}
                </Button>
              </div>
            </CardBody>
          </Card>

          {readinessQuery.isLoading ? (
            <Card>
              <CardBody>
                <LoadingState label="Loading pilot readiness…" />
              </CardBody>
            </Card>
          ) : null}
          {readinessQuery.error ? (
            <Card>
              <CardBody>
                <p className="text-sm text-danger" role="alert">
                  {readinessQuery.error instanceof Error ? readinessQuery.error.message : 'Failed to load pilot readiness'}
                </p>
              </CardBody>
            </Card>
          ) : null}

          {readiness ? (
            <>
              <Card>
                <CardHeader
                  title="Readiness assessment"
                  description="Combines operational checklist, TRL 6 criteria, and the latest validation run."
                  actions={
                    <Badge tone={readiness.ready_for_trl6_pilot ? 'success' : 'danger'}>
                      {readiness.ready_for_trl6_pilot ? 'Ready for TRL 6 pilot' : 'Not ready'}
                    </Badge>
                  }
                />
                <CardBody className="flex flex-col gap-4">
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <KpiCard
                      label="Operational checklist"
                      value={`${checklistPassed}/${checklistTotal}`}
                      tone={checklistPassed === checklistTotal ? 'success' : 'warning'}
                    />
                    <KpiCard
                      label="TRL 6 criteria"
                      value={`${criteriaPassed}/${criteriaTotal}`}
                      tone={criteriaPassed === criteriaTotal ? 'success' : 'warning'}
                    />
                    <KpiCard
                      label="Latest TRL validation"
                      value={formatTrlValidationStatus(readiness.latest_trl_validation, readiness.criteria)}
                      tone={validationPassed ? 'success' : validationOutdated ? 'warning' : 'accent'}
                    />
                    <KpiCard
                      label="Pilot status"
                      value={settings?.pilot_enabled ? 'Enabled' : 'Disabled'}
                    />
                  </div>

                  {readiness.warnings.length > 0 ? (
                    <div>
                      <h3 className="mb-2 text-sm font-semibold text-fg">Warnings</h3>
                      <ul className="list-inside list-disc space-y-1 text-sm text-muted">
                        {readiness.warnings.map((warning) => (
                          <li key={warning}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </CardBody>
              </Card>

              <ChecklistPanel
                title="Operational checklist"
                subtitle="Infrastructure and catalog prerequisites before live pilot traffic."
                items={readiness.checklist}
              />

              <ChecklistPanel
                title="TRL 6 acceptance criteria"
                subtitle="Safety, validation, and control requirements for field pilots."
                items={readiness.criteria}
              />

              <Card>
                <CardHeader title="Pilot settings" />
                <CardBody>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    <KpiCard label="Pilot name" value={settings?.pilot_name ?? '—'} />
                    <KpiCard label="Max auto-sends/day" value={String(settings?.max_auto_sent_messages_per_day ?? '—')} />
                    <KpiCard label="Max auto-orders/day" value={String(settings?.max_auto_created_orders_per_day ?? '—')} />
                    <KpiCard
                      label="First 50 approvals"
                      value={settings?.require_operator_approval_for_first_50_orders ? 'Required' : 'Not required'}
                    />
                    <KpiCard label="Allowed Instagram accounts" value={String(settings?.allowed_instagram_account_ids.length ?? 0)} />
                    <KpiCard label="Allowed products" value={String(settings?.allowed_product_ids?.length ?? 'All')} />
                  </div>
                </CardBody>
              </Card>
            </>
          ) : null}

          <Card>
            <CardHeader
              title="Pilot metrics"
              description="Live counters for the selected shop, refreshed every 30 seconds."
            />
            <CardBody>
              {metricsQuery.isLoading ? <LoadingState label="Loading pilot metrics…" /> : null}
              {metricsQuery.error ? (
                <p className="text-sm text-danger" role="alert">
                  {metricsQuery.error instanceof Error ? metricsQuery.error.message : 'Failed to load pilot metrics'}
                </p>
              ) : null}

              {metrics ? (
                <div className="flex flex-col gap-6">
                  {METRIC_GROUPS.map((group) => (
                    <div key={group.title}>
                      <h3 className="mb-3 text-sm font-semibold text-fg">{group.title}</h3>
                      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                        {group.keys.map((key) => {
                          const tone = metricTone(key, metrics[key]);
                          return (
                            <KpiCard
                              key={key}
                              label={METRIC_LABELS[key]}
                              value={formatMetricValue(key, metrics[key])}
                              tone={tone ?? 'accent'}
                            />
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              ) : !metricsQuery.isLoading ? (
                <EmptyState title="No metrics loaded" />
              ) : null}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Pilot event log"
              description="Recent safeguard actions, configuration changes, and operational alerts."
            />
            <CardBody className="flex flex-col gap-4">
              <div className="flex flex-wrap gap-2" role="group" aria-label="Filter pilot events">
                {(['all', 'info', 'warning', 'error', 'critical'] as const).map((option) => (
                  <Chip key={option} active={eventFilter === option} onClick={() => setEventFilter(option)}>
                    {option === 'all' ? 'All' : option.charAt(0).toUpperCase() + option.slice(1)} ({eventCounts[option]})
                  </Chip>
                ))}
              </div>

              <DataTable
                columns={eventColumns}
                rows={events}
                rowKey={(event) => event.id}
                isLoading={eventsQuery.isLoading}
                error={eventsQuery.error instanceof Error ? eventsQuery.error.message : null}
                emptyTitle="No pilot events match this filter"
              />
            </CardBody>
          </Card>
        </>
      ) : null}

      <ConfirmDialog
        open={stopDialogOpen}
        title="Activate emergency stop?"
        message="This immediately disables auto-send and auto-order progression for the selected shop. Review scope before confirming."
        confirmLabel="Activate emergency stop"
        onConfirm={() => stopMutation.mutate()}
        onCancel={() => setStopDialogOpen(false)}
        isLoading={stopMutation.isPending}
      />
      {stopDialogOpen ? (
        <Card>
          <CardHeader
            title="Scope preview"
            description="Active conversations remain open but automation will not write orders or send messages."
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
    </HubPage>
  );
}
