import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
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

function MetricCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: 'success' | 'warning';
}) {
  const toneClass = tone === 'success' ? ' stat-card--success' : tone === 'warning' ? ' stat-card--warning' : '';
  return (
    <article className={`stat-card${toneClass}`}>
      <p className="stat-card__label">{label}</p>
      <p className="stat-card__value">{value}</p>
    </article>
  );
}

function severityBadge(severity: PilotEvent['severity']) {
  switch (severity) {
    case 'critical':
      return { label: severity, className: 'priority-badge priority-badge--urgent' };
    case 'error':
      return { label: severity, className: 'priority-badge priority-badge--high' };
    case 'warning':
      return { label: severity, className: 'priority-badge priority-badge--medium' };
    default:
      return { label: severity, className: 'priority-badge priority-badge--low' };
  }
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
    <section className="dashboard-card dashboard-card--wide">
      <div className="section-header section-header--stacked">
        <div>
          <h2>{title}</h2>
          <p className="dashboard-card__subtitle">{subtitle}</p>
        </div>
        <span className={passed === items.length ? 'priority-badge priority-badge--low' : 'priority-badge priority-badge--high'}>
          {passed}/{items.length} passed
        </span>
      </div>
      <ul className="checklist">
        {items.map((item) => (
          <li key={item.key} className={item.passed ? 'pilot-checklist__item pilot-checklist__item--passed' : 'pilot-checklist__item pilot-checklist__item--failed'}>
            <strong>
              {item.passed ? '✅' : '❌'} {item.label}
            </strong>
            {item.detail ? <span className="pilot-checklist__detail"> — {item.detail}</span> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

function filterEvents(events: PilotEvent[], filter: EventFilter) {
  if (filter === 'all') return events;
  return events.filter((event) => event.severity === filter);
}

export function PilotReadinessPage() {
  const { selectedShop, selectedShopId } = useShop();
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

  if (!selectedShop) {
    return (
      <section className="dashboard-card dashboard-card--wide">
        <h1>TRL 6 Pilot Readiness</h1>
        <p>Select a shop to review operational checklist, safeguards, and pilot metrics.</p>
        <ShopSelector />
      </section>
    );
  }

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Field pilot operations</p>
        <h1>TRL 6 Pilot Readiness</h1>
        <p>
          Operational checklist, safeguards, live metrics, and event log for realistic Instagram fashion
          order pilots.
        </p>
        <ShopSelector />
      </section>

      <section className="dashboard-card dashboard-card--wide pilot-safeguards">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Pilot safeguards</h2>
            <p className="dashboard-card__subtitle">
              Emergency stop immediately disables auto-send and auto-order progression for the selected shop.
            </p>
          </div>
          <span
            className={
              settings?.emergency_stop_enabled
                ? 'priority-badge priority-badge--urgent'
                : settings?.pilot_enabled
                  ? 'priority-badge priority-badge--medium'
                  : 'priority-badge priority-badge--low'
            }
          >
            {settings?.emergency_stop_enabled ? 'Emergency stop active' : settings?.pilot_enabled ? 'Pilot active' : 'Pilot idle'}
          </span>
        </div>

        <div className="pilot-status-alerts">
          {settings?.pilot_enabled ? (
            <div className="alert alert--warning">Pilot mode active: automation is constrained by pilot limits and approvals.</div>
          ) : null}
          {settings?.emergency_stop_enabled ? (
            <div className="alert alert--error">Emergency stop active: auto-send and auto-order progression are disabled.</div>
          ) : null}
          {scopePreview ? (
            <div className="alert alert--warning">
              Last emergency stop affected {scopePreview.active_conversation_count} active conversation(s),{' '}
              {scopePreview.simulation_conversation_count} simulation conversation(s).
            </div>
          ) : null}
          {settings && !settings.pilot_enabled ? (
            <div className="alert alert--warning">Auto-send disabled for pilot traffic until pilot mode is enabled.</div>
          ) : null}
          {validationOutdated ? (
            <div className="alert alert--warning">
              Validation outdated or failing:{' '}
              <Link className="table-link" to="/trl-validation">
                run TRL validation
              </Link>{' '}
              before field traffic.
            </div>
          ) : null}
          {failedJobs > 0 ? (
            <div className="alert alert--error">
              Failed jobs present:{' '}
              <Link className="table-link" to="/system-health">
                resolve worker failures
              </Link>{' '}
              before expanding the pilot.
            </div>
          ) : null}
        </div>

        <div className="button-row pilot-safeguards__actions">
          <button
            className="button button--danger"
            type="button"
            onClick={() => setStopDialogOpen(true)}
            disabled={stopMutation.isPending || resumeMutation.isPending || settings?.emergency_stop_enabled}
          >
            {stopMutation.isPending ? 'Stopping…' : 'Emergency stop'}
          </button>
          <button
            className="button button--primary"
            type="button"
            onClick={() => resumeMutation.mutate()}
            disabled={resumeMutation.isPending || stopMutation.isPending || !settings?.emergency_stop_enabled}
          >
            {resumeMutation.isPending ? 'Resuming…' : 'Resume pilot'}
          </button>
          <button
            className="button button--ghost-dark"
            type="button"
            onClick={() => void refreshPilot()}
            disabled={readinessQuery.isFetching || metricsQuery.isFetching || eventsQuery.isFetching}
          >
            {readinessQuery.isFetching ? 'Refreshing…' : 'Refresh data'}
          </button>
        </div>
      </section>

      {readinessQuery.isLoading ? <p className="loading-state">Loading pilot readiness…</p> : null}
      {readinessQuery.error ? (
        <div role="alert" className="alert alert--error">
          {readinessQuery.error instanceof Error ? readinessQuery.error.message : 'Failed to load pilot readiness'}
        </div>
      ) : null}

      {readiness ? (
        <>
          <section className="dashboard-card dashboard-card--wide">
            <div className="section-header section-header--stacked">
              <div>
                <h2>Readiness assessment</h2>
                <p className="dashboard-card__subtitle">
                  Combines operational checklist, TRL 6 criteria, and the latest validation run.
                </p>
              </div>
              <span
                className={
                  readiness.ready_for_trl6_pilot
                    ? 'priority-badge priority-badge--low'
                    : 'priority-badge priority-badge--high'
                }
              >
                {readiness.ready_for_trl6_pilot ? 'Ready for TRL 6 pilot' : 'Not ready'}
              </span>
            </div>

            <div className="stats-grid">
              <MetricCard
                label="Operational checklist"
                value={`${checklistPassed}/${checklistTotal}`}
                tone={checklistPassed === checklistTotal ? 'success' : 'warning'}
              />
              <MetricCard
                label="TRL 6 criteria"
                value={`${criteriaPassed}/${criteriaTotal}`}
                tone={criteriaPassed === criteriaTotal ? 'success' : 'warning'}
              />
              <MetricCard
                label="Latest TRL validation"
                value={formatTrlValidationStatus(readiness.latest_trl_validation, readiness.criteria)}
                tone={validationPassed ? 'success' : validationOutdated ? 'warning' : undefined}
              />
              <MetricCard
                label="Pilot status"
                value={settings?.pilot_enabled ? 'Enabled' : 'Disabled'}
              />
            </div>

            {readiness.warnings.length > 0 ? (
              <div className="pilot-warnings">
                <h3>Warnings</h3>
                <ul>
                  {readiness.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>

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

          <section className="dashboard-card dashboard-card--wide">
            <h2>Pilot settings</h2>
            <div className="stats-grid">
              <MetricCard label="Pilot name" value={settings?.pilot_name ?? '—'} />
              <MetricCard label="Max auto-sends/day" value={String(settings?.max_auto_sent_messages_per_day ?? '—')} />
              <MetricCard label="Max auto-orders/day" value={String(settings?.max_auto_created_orders_per_day ?? '—')} />
              <MetricCard
                label="First 50 approvals"
                value={settings?.require_operator_approval_for_first_50_orders ? 'Required' : 'Not required'}
              />
              <MetricCard label="Allowed Instagram accounts" value={String(settings?.allowed_instagram_account_ids.length ?? 0)} />
              <MetricCard label="Allowed products" value={String(settings?.allowed_product_ids?.length ?? 'All')} />
            </div>
          </section>
        </>
      ) : null}

      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Pilot metrics</h2>
            <p className="dashboard-card__subtitle">Live counters for the selected shop, refreshed every 30 seconds.</p>
          </div>
        </div>

        {metricsQuery.isLoading ? <p className="loading-state">Loading pilot metrics…</p> : null}
        {metricsQuery.error ? (
          <div role="alert" className="alert alert--error">
            {metricsQuery.error instanceof Error ? metricsQuery.error.message : 'Failed to load pilot metrics'}
          </div>
        ) : null}

        {metrics ? (
          <div className="pilot-metrics-groups">
            {METRIC_GROUPS.map((group) => (
              <div key={group.title} className="pilot-metrics-group">
                <h3>{group.title}</h3>
                <div className="stats-grid">
                  {group.keys.map((key) => (
                    <MetricCard
                      key={key}
                      label={METRIC_LABELS[key]}
                      value={formatMetricValue(key, metrics[key])}
                      tone={metricTone(key, metrics[key])}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : !metricsQuery.isLoading ? (
          <p className="empty-state">No metrics loaded.</p>
        ) : null}
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Pilot event log</h2>
            <p className="dashboard-card__subtitle">Recent safeguard actions, configuration changes, and operational alerts.</p>
          </div>
        </div>

        <div className="filter-chips" role="group" aria-label="Filter pilot events">
          {(['all', 'info', 'warning', 'error', 'critical'] as const).map((option) => (
            <button
              key={option}
              type="button"
              className={`filter-chip${eventFilter === option ? ' filter-chip--active' : ''}`}
              aria-pressed={eventFilter === option}
              onClick={() => setEventFilter(option)}
            >
              {option === 'all' ? 'All' : option.charAt(0).toUpperCase() + option.slice(1)} ({eventCounts[option]})
            </button>
          ))}
        </div>

        {eventsQuery.isLoading ? <p className="loading-state">Loading pilot events…</p> : null}
        {eventsQuery.error ? (
          <div role="alert" className="alert alert--error">
            {eventsQuery.error instanceof Error ? eventsQuery.error.message : 'Failed to load pilot events'}
          </div>
        ) : null}

        {!eventsQuery.isLoading && events.length === 0 ? (
          <p className="empty-state">No pilot events match this filter.</p>
        ) : null}

        {events.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Time</th>
                  <th scope="col">Severity</th>
                  <th scope="col">Event</th>
                  <th scope="col">Description</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => {
                  const badge = severityBadge(event.severity);
                  return (
                    <tr key={event.id} className={event.severity === 'critical' || event.severity === 'error' ? 'data-table__row--attention' : undefined}>
                      <td>{new Date(event.created_at).toLocaleString()}</td>
                      <td>
                        <span className={badge.className}>{badge.label}</span>
                      </td>
                      <td>{event.title}</td>
                      <td>{event.description ?? event.event_type}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

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
        <section className="dashboard-card dashboard-card--wide">
          <h3>Scope preview</h3>
          <p className="dashboard-card__subtitle">
            Active conversations remain open but automation will not write orders or send messages.
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
