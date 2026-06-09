import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import type { PilotChecklistItem, PilotMetrics } from '../types/pilot';

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

function Checklist({ title, items }: { title: string; items: PilotChecklistItem[] }) {
  return (
    <div className="card">
      <h2>{title}</h2>
      <ul className="checklist">
        {items.map((item) => (
          <li key={item.key}>
            <strong>{item.passed ? '✅' : '❌'} {item.label}</strong>
            {item.detail ? <span> — {item.detail}</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function PilotReadinessPage() {
  const { selectedShop } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const shopId = selectedShop?.id;

  const readiness = useQuery({
    queryKey: ['pilot-readiness', shopId],
    queryFn: () => apiClient.getPilotReadiness(shopId!),
    enabled: Boolean(shopId),
    refetchInterval: 30_000,
  });
  const metrics = useQuery({
    queryKey: ['pilot-metrics', shopId],
    queryFn: () => apiClient.getPilotMetrics(shopId!),
    enabled: Boolean(shopId),
    refetchInterval: 30_000,
  });
  const events = useQuery({
    queryKey: ['pilot-events', shopId],
    queryFn: () => apiClient.getPilotEvents(shopId!),
    enabled: Boolean(shopId),
    refetchInterval: 30_000,
  });

  const refreshPilot = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['pilot-readiness', shopId] }),
      queryClient.invalidateQueries({ queryKey: ['pilot-metrics', shopId] }),
      queryClient.invalidateQueries({ queryKey: ['pilot-events', shopId] }),
    ]);
  };

  const stopMutation = useMutation({
    mutationFn: () => apiClient.activatePilotEmergencyStop(shopId!),
    onSuccess: async () => {
      showToast('Emergency stop activated', 'success');
      await refreshPilot();
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });
  const resumeMutation = useMutation({
    mutationFn: () => apiClient.resumePilot(shopId!),
    onSuccess: async () => {
      showToast('Pilot automation resumed', 'success');
      await refreshPilot();
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  if (!selectedShop) {
    return <section className="card"><h2>Pilot Readiness</h2><p>Select a shop to review pilot readiness.</p></section>;
  }

  const settings = readiness.data?.pilot_settings;
  const failedJobs = metrics.data?.failed_jobs ?? 0;
  const validationOutdated = readiness.data?.criteria.some((item) => item.key === 'latest_trl_validation' && !item.passed) ?? false;

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <h1>TRL 6 Pilot Readiness</h1>
          <p>Operational checklist, safeguards, metrics, and event log for realistic Instagram fashion order pilots.</p>
        </div>
        <div className="button-row">
          <button className="button button--danger" type="button" onClick={() => stopMutation.mutate()} disabled={stopMutation.isPending}>Emergency stop</button>
          <button className="button" type="button" onClick={() => resumeMutation.mutate()} disabled={resumeMutation.isPending}>Resume pilot</button>
        </div>
      </header>

      {readiness.isLoading ? <p>Loading pilot readiness…</p> : null}
      {readiness.error ? <div role="alert" className="alert alert--error">{readiness.error.message}</div> : null}

      {settings?.pilot_enabled ? <div className="alert alert--warning">Pilot mode active: automation is constrained by pilot limits and approvals.</div> : null}
      {settings?.emergency_stop_enabled ? <div className="alert alert--error">Emergency stop active: auto-send and auto-order progression are disabled.</div> : null}
      {settings && !settings.pilot_enabled ? <div className="alert alert--warning">Auto-send disabled for pilot traffic until pilot mode is enabled.</div> : null}
      {validationOutdated ? <div className="alert alert--warning">Validation outdated or failing: run TRL validation before field traffic.</div> : null}
      {failedJobs > 0 ? <div className="alert alert--error">Failed jobs present: resolve worker failures before expanding the pilot.</div> : null}

      {readiness.data ? (
        <>
          <div className="card">
            <h2>Readiness assessment</h2>
            <p>Status: <strong>{readiness.data.ready_for_trl6_pilot ? 'Ready for TRL 6 pilot' : 'Not ready'}</strong></p>
            <p>Latest TRL validation: <strong>{String(readiness.data.latest_trl_validation?.status ?? 'No run')}</strong></p>
          </div>
          <Checklist title="Operational checklist" items={readiness.data.checklist} />
          <Checklist title="TRL 6 acceptance criteria" items={readiness.data.criteria} />
          <div className="card">
            <h2>Pilot settings</h2>
            <div className="metric-grid">
              <div><span>Pilot name</span><strong>{settings?.pilot_name}</strong></div>
              <div><span>Max auto-sends/day</span><strong>{settings?.max_auto_sent_messages_per_day}</strong></div>
              <div><span>Max auto-orders/day</span><strong>{settings?.max_auto_created_orders_per_day}</strong></div>
              <div><span>First 50 approvals</span><strong>{settings?.require_operator_approval_for_first_50_orders ? 'Required' : 'Not required'}</strong></div>
              <div><span>Allowed Instagram accounts</span><strong>{settings?.allowed_instagram_account_ids.length ?? 0}</strong></div>
              <div><span>Allowed products</span><strong>{settings?.allowed_product_ids?.length ?? 'All'}</strong></div>
            </div>
          </div>
        </>
      ) : null}

      <div className="card">
        <h2>Pilot metrics</h2>
        {metrics.data ? (
          <div className="metric-grid">
            {Object.entries(metrics.data).map(([key, value]) => (
              <div key={key}><span>{METRIC_LABELS[key as keyof PilotMetrics]}</span><strong>{Math.round(Number(value))}</strong></div>
            ))}
          </div>
        ) : <p>No metrics loaded.</p>}
      </div>

      <div className="card">
        <h2>Pilot event log</h2>
        {events.data?.events.length ? (
          <table className="data-table">
            <thead><tr><th>Time</th><th>Severity</th><th>Event</th><th>Description</th></tr></thead>
            <tbody>
              {events.data.events.map((event) => (
                <tr key={event.id}>
                  <td>{new Date(event.created_at).toLocaleString()}</td>
                  <td>{event.severity}</td>
                  <td>{event.title}</td>
                  <td>{event.description ?? event.event_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p>No pilot events yet.</p>}
      </div>
    </section>
  );
}
