import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import type { TRLRiskMetrics, TRLValidationRun, TRLValidationScenarioResult } from '../types/trlValidation';

type ScenarioFilter = 'all' | 'passed' | 'failed' | 'unsafe';

const SCENARIO_LIMIT_OPTIONS = [
  { label: 'Quick (10 scenarios)', value: 10 },
  { label: 'Sample (25 scenarios)', value: 25 },
  { label: 'Extended (50 scenarios)', value: 50 },
  { label: 'Full suite (100 scenarios)', value: 100 },
] as const;

const THRESHOLD_LABELS: Record<string, string> = {
  intent_accuracy: 'Intent accuracy ≥ 90%',
  slot_extraction_accuracy: 'Slot extraction ≥ 85%',
  product_resolution_accuracy: 'Product resolution ≥ 90%',
  variant_resolution_accuracy: 'Variant resolution ≥ 85%',
  false_order_creation_count: 'No false order creation',
  false_payment_status_change_count: 'No false payment status changes',
  inventory_double_reservation_count: 'No double inventory reservations',
  invalid_llm_json_handled_rate: 'Invalid LLM JSON handled 100%',
  duplicate_webhook_idempotency_rate: 'Webhook idempotency 100%',
  critical_security_tests_pass_rate: 'Critical security tests 100%',
};

function percent(value: unknown) {
  return typeof value === 'number' ? `${Math.round(value * 100)}%` : '—';
}

function formatRunTimestamp(value: string | null | undefined) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

function runStatusBadge(run: TRLValidationRun) {
  const thresholds = (run.metrics_json.thresholds_passed ?? {}) as Record<string, boolean>;
  const allPassed = Object.values(thresholds).length > 0 && Object.values(thresholds).every(Boolean);
  if (run.status === 'failed') {
    return { label: 'Run failed', className: 'priority-badge priority-badge--urgent' };
  }
  if (run.status === 'running') {
    return { label: 'Running', className: 'priority-badge priority-badge--medium' };
  }
  if (allPassed && run.failed_scenarios === 0) {
    return { label: 'All thresholds passed', className: 'priority-badge priority-badge--low' };
  }
  if (allPassed) {
    return { label: 'Thresholds passed', className: 'priority-badge priority-badge--medium' };
  }
  return { label: 'Thresholds failing', className: 'priority-badge priority-badge--high' };
}

function isUnsafeScenario(row: TRLValidationScenarioResult) {
  const riskLevel = (row.actual_json.risk_score as { risk_level?: string } | undefined)?.risk_level;
  return !row.passed || Boolean(row.actual_json.requires_handoff) || riskLevel === 'critical';
}

function filterScenarios(rows: TRLValidationScenarioResult[], filter: ScenarioFilter) {
  if (filter === 'passed') return rows.filter((row) => row.passed);
  if (filter === 'failed') return rows.filter((row) => !row.passed);
  if (filter === 'unsafe') return rows.filter(isUnsafeScenario);
  return rows;
}

function MetricCard({ label, value, tone }: { label: string; value: string; tone?: 'success' | 'warning' }) {
  const toneClass = tone === 'success' ? ' stat-card--success' : tone === 'warning' ? ' stat-card--warning' : '';
  return (
    <article className={`stat-card${toneClass}`}>
      <p className="stat-card__label">{label}</p>
      <p className="stat-card__value">{value}</p>
    </article>
  );
}

function ScenarioDetailPanel({
  scenario,
  onClose,
}: {
  scenario: TRLValidationScenarioResult;
  onClose: () => void;
}) {
  const inputMessage = String(scenario.input_json.message_text ?? scenario.input_json.text ?? '—');
  const expectedIntent = String(scenario.expected_json.intent ?? '—');
  const actualIntent = String(scenario.actual_json.intent ?? '—');

  return (
    <section className="dashboard-card dashboard-card--wide trl-scenario-detail" aria-label="Scenario detail">
      <div className="section-header">
        <div>
          <h2>{scenario.scenario_id}</h2>
          <p className="dashboard-card__subtitle">
            {scenario.passed ? 'Scenario passed all checks.' : 'Review mismatches and failure reasons below.'}
          </p>
        </div>
        <span className={scenario.passed ? 'priority-badge priority-badge--low' : 'priority-badge priority-badge--high'}>
          {scenario.passed ? 'Passed' : 'Failed'}
        </span>
      </div>

      <div className="stats-grid">
        <MetricCard label="Intent (actual)" value={actualIntent} tone={scenario.passed ? 'success' : 'warning'} />
        <MetricCard label="State" value={String(scenario.actual_json.state ?? '—')} />
        <MetricCard label="Processing time" value={`${scenario.processing_time_ms}ms`} />
      </div>

      <dl className="detail-grid trl-scenario-detail__grid">
        <div>
          <dt>Customer message</dt>
          <dd dir="auto">{inputMessage}</dd>
        </div>
        <div>
          <dt>Expected intent</dt>
          <dd>{expectedIntent}</dd>
        </div>
        <div>
          <dt>Actual intent</dt>
          <dd>{actualIntent}</dd>
        </div>
      </dl>

      {scenario.failure_reasons.length > 0 ? (
        <div className="trl-scenario-detail__failures">
          <h3>Failure reasons</h3>
          <ul>
            {scenario.failure_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="button-row">
        {scenario.conversation_id ? (
          <>
            <Link className="button button--ghost-dark" to={`/conversations/${scenario.conversation_id}`}>
              Open conversation
            </Link>
            <Link className="button button--ghost-dark" to={`/conversations/${scenario.conversation_id}#decision-trace`}>
              Decision trace
            </Link>
          </>
        ) : null}
        <button className="button button--ghost-dark" type="button" onClick={onClose}>
          Close
        </button>
      </div>

      <details className="match-panel resolver-raw-details">
        <summary>Full scenario payload</summary>
        <pre className="resolver-raw-json">
          {JSON.stringify(
            {
              input: scenario.input_json,
              expected: scenario.expected_json,
              actual: scenario.actual_json,
              failure_reasons: scenario.failure_reasons,
            },
            null,
            2,
          )}
        </pre>
      </details>
    </section>
  );
}

export function TRLValidationPage() {
  const { selectedShop, selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [filter, setFilter] = useState<ScenarioFilter>('all');
  const [detail, setDetail] = useState<TRLValidationScenarioResult | null>(null);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [scenarioLimit, setScenarioLimit] = useState<number>(25);
  const [resetDemoData, setResetDemoData] = useState(false);

  const runsQuery = useQuery({
    queryKey: ['trl-validation-runs', selectedShopId],
    queryFn: () => apiClient.listTRLValidationRuns(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });

  const runs = runsQuery.data ?? [];
  const selectedRun = runs.find((run) => run.id === selectedRunId) ?? runs[0] ?? null;

  useEffect(() => {
    if (!runs.length) {
      setSelectedRunId(null);
      return;
    }
    if (!selectedRunId || !runs.some((run) => run.id === selectedRunId)) {
      setSelectedRunId(runs[0].id);
    }
  }, [runs, selectedRunId]);

  const scenariosQuery = useQuery({
    queryKey: ['trl-validation-scenarios', selectedShopId, selectedRun?.id],
    queryFn: () => apiClient.listTRLValidationScenarios(selectedShopId!, selectedRun!.id),
    enabled: Boolean(selectedShopId && selectedRun?.id),
  });

  const allScenarios = scenariosQuery.data ?? [];
  const scenarios = useMemo(() => filterScenarios(allScenarios, filter), [allScenarios, filter]);

  const riskMetricsQuery = useQuery({
    queryKey: ['trl-validation-risk', selectedShopId, selectedRun?.id],
    queryFn: () => apiClient.getTRLRiskMetrics(selectedShopId!, selectedRun!.id),
    enabled: Boolean(selectedShopId && selectedRun?.id),
  });

  const runMutation = useMutation({
    mutationFn: () =>
      apiClient.runTRLValidation(selectedShopId!, {
        reset_demo_data: resetDemoData,
        scenario_limit: scenarioLimit,
      }),
    onSuccess: async (run) => {
      showToast(
        `Validation complete: ${run.passed_scenarios}/${run.total_scenarios} scenarios passed.`,
        run.failed_scenarios === 0 ? 'success' : 'error',
      );
      setSelectedRunId(run.id);
      setDetail(null);
      await queryClient.invalidateQueries({ queryKey: ['trl-validation-runs', selectedShopId] });
      await queryClient.invalidateQueries({ queryKey: ['trl-validation-scenarios', selectedShopId, run.id] });
      await queryClient.invalidateQueries({ queryKey: ['trl-validation-risk', selectedShopId, run.id] });
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const resetMutation = useMutation({
    mutationFn: () => apiClient.resetTRLValidation(selectedShopId!),
    onSuccess: async (summary) => {
      showToast(
        `Removed ${summary.deleted_runs} run(s), ${summary.deleted_conversations} conversation(s), and ${summary.deleted_orders} order(s).`,
        'success',
      );
      setSelectedRunId(null);
      setDetail(null);
      setResetDialogOpen(false);
      await queryClient.invalidateQueries({ queryKey: ['trl-validation-runs', selectedShopId] });
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const metrics = selectedRun?.metrics_json ?? {};
  const riskMetrics: TRLRiskMetrics | null = riskMetricsQuery.data ?? null;
  const thresholdRows = useMemo(
    () => Object.entries((metrics.thresholds_passed ?? {}) as Record<string, boolean>),
    [metrics],
  );
  const statusBadge = selectedRun ? runStatusBadge(selectedRun) : null;
  const passRate =
    selectedRun && selectedRun.total_scenarios > 0
      ? Math.round((selectedRun.passed_scenarios / selectedRun.total_scenarios) * 100)
      : 0;

  const filterCounts = useMemo(
    () => ({
      all: allScenarios.length,
      passed: allScenarios.filter((row) => row.passed).length,
      failed: allScenarios.filter((row) => !row.passed).length,
      unsafe: allScenarios.filter(isUnsafeScenario).length,
    }),
    [allScenarios],
  );

  if (!selectedShop) {
    return (
      <section className="dashboard-card dashboard-card--wide">
        <h1>TRL 5 Validation</h1>
        <p>Select a shop to run the repeatable relevant-environment validation suite.</p>
        <ShopSelector />
      </section>
    );
  }

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Relevant environment testing</p>
        <h1>TRL 5 Validation</h1>
        <p>
          Runs scripted DM scenarios through the production orchestrator without sending real Instagram
          messages. Use this before enabling pilot traffic.
        </p>
        <ShopSelector />
      </section>

      <section className="dashboard-card dashboard-card--wide trl-validation-controls">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Run validation</h2>
            <p className="dashboard-card__subtitle">
              Choose how many scenarios to execute. Full runs can take a minute — keep this tab open.
            </p>
          </div>
          <span className="priority-badge priority-badge--medium">Test harness</span>
        </div>

        <div className="filter-grid trl-validation-controls__grid">
          <label className="form-field">
            <span>Scenario count</span>
            <select
              value={scenarioLimit}
              onChange={(event) => setScenarioLimit(Number(event.target.value))}
              disabled={runMutation.isPending}
            >
              {SCENARIO_LIMIT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="form-field form-field--checkbox">
            <input
              type="checkbox"
              checked={resetDemoData}
              onChange={(event) => setResetDemoData(event.target.checked)}
              disabled={runMutation.isPending}
            />
            <span>Reset demo catalog before run</span>
          </label>
        </div>

        {runMutation.isPending ? (
          <p className="loading-state trl-validation-status" role="status">
            Running {scenarioLimit} scenarios through the orchestrator…
          </p>
        ) : null}

        <div className="trl-validation-actions">
          <div className="button-row trl-validation-actions__primary">
            <button
              className="button button--primary"
              type="button"
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending || resetMutation.isPending || !selectedShopId}
            >
              {runMutation.isPending ? 'Running…' : 'Run validation'}
            </button>
            <button
              className="button button--ghost-dark"
              type="button"
              disabled={runMutation.isPending || resetMutation.isPending || !selectedShopId}
              onClick={() => setResetDialogOpen(true)}
            >
              Reset validation data
            </button>
          </div>
        </div>
      </section>

      {runsQuery.isLoading ? <p className="loading-state">Loading validation history…</p> : null}
      {runsQuery.error ? (
        <div role="alert" className="alert alert--error">
          {runsQuery.error instanceof Error ? runsQuery.error.message : 'Failed to load validation runs'}
        </div>
      ) : null}

      {!runsQuery.isLoading && runs.length === 0 ? (
        <div className="empty-state-panel">
          <p className="empty-state-panel__title">No validation runs yet</p>
          <p className="empty-state-panel__hint">
            Run validation to generate TRL 5 metrics, threshold checks, and per-scenario evidence.
          </p>
        </div>
      ) : null}

      {selectedRun ? (
        <>
          <section className="dashboard-card dashboard-card--wide">
            <div className="section-header section-header--stacked">
              <div>
                <h2>Run summary</h2>
                <p className="dashboard-card__subtitle">
                  Started {formatRunTimestamp(selectedRun.started_at)}
                  {selectedRun.completed_at ? ` · Completed ${formatRunTimestamp(selectedRun.completed_at)}` : ''}
                </p>
              </div>
              {statusBadge ? <span className={statusBadge.className}>{statusBadge.label}</span> : null}
            </div>

            {runs.length > 1 ? (
              <label className="form-field trl-run-picker">
                <span>Run history</span>
                <select
                  aria-label="Select validation run"
                  value={selectedRun.id}
                  onChange={(event) => {
                    setSelectedRunId(event.target.value);
                    setDetail(null);
                  }}
                >
                  {runs.map((run) => (
                    <option key={run.id} value={run.id}>
                      {formatRunTimestamp(run.started_at)} — {run.passed_scenarios}/{run.total_scenarios} passed ({run.status})
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            <div className="stats-grid">
              <MetricCard label="Validation mode" value={String(selectedRun.validation_mode ?? metrics.validation_mode ?? 'deterministic_regression')} />
              <MetricCard
                label="Evidence type"
                value={metrics.proves_live_llm ? 'Live/staging LLM' : 'Deterministic regression'}
              />
              <MetricCard label="Scenarios passed" value={`${selectedRun.passed_scenarios}/${selectedRun.total_scenarios}`} />
              <MetricCard
                label="Pass rate"
                value={`${passRate}%`}
                tone={passRate >= 90 ? 'success' : passRate >= 70 ? undefined : 'warning'}
              />
              <MetricCard label="Failed scenarios" value={String(selectedRun.failed_scenarios)} tone={selectedRun.failed_scenarios > 0 ? 'warning' : undefined} />
              <MetricCard label="Run status" value={selectedRun.status} />
            </div>

            <div className="stats-grid">
              <MetricCard label="Intent accuracy" value={percent(metrics.intent_accuracy)} />
              <MetricCard label="Slot accuracy" value={percent(metrics.slot_extraction_accuracy)} />
              <MetricCard label="Product resolution" value={percent(metrics.product_resolution_accuracy)} />
              <MetricCard label="Variant resolution" value={percent(metrics.variant_resolution_accuracy)} />
              <MetricCard label="False auto-sends" value={String(metrics.false_auto_send_count ?? 0)} />
              <MetricCard label="False orders" value={String(metrics.false_order_creation_count ?? 0)} />
            </div>
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>Risk &amp; latency</h2>
            <div className="stats-grid">
              <MetricCard label="Invalid LLM JSON" value={String(riskMetrics?.invalid_llm_json_count ?? metrics.invalid_llm_json_count ?? 0)} />
              <MetricCard label="Safe fallbacks" value={String(riskMetrics?.safe_fallback_count ?? metrics.safe_fallback_count ?? 0)} />
              <MetricCard label="Human handoffs" value={String(riskMetrics?.human_handoff_count ?? metrics.human_handoff_count ?? 0)} />
              <MetricCard label="Critical risk events" value={String(riskMetrics?.critical_risk_count ?? metrics.critical_risk_count ?? 0)} />
              <MetricCard
                label="Average risk score"
                value={
                  riskMetrics
                    ? `${Math.round(riskMetrics.average_risk_score * 100)}%`
                    : `${Math.round(Number(metrics.average_risk_score ?? 0) * 100)}%`
                }
              />
              <MetricCard label="P95 latency" value={`${riskMetrics?.p95_processing_latency ?? metrics.p95_processing_latency ?? 0}ms`} />
            </div>

            <h3>Pass rate by category</h3>
            <ul className="trl-category-list">
              {Object.entries(
                riskMetrics?.scenario_pass_rate_by_category ??
                  (metrics.scenario_pass_rate_by_category as Record<string, number> | undefined) ??
                  {},
              ).map(([category, value]) => (
                <li key={category}>
                  <span>{category}</span>
                  <strong>{percent(value)}</strong>
                </li>
              ))}
            </ul>
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>Acceptance thresholds</h2>
            {thresholdRows.length ? (
              <ul className="checklist">
                {thresholdRows.map(([name, ok]) => (
                  <li key={name}>
                    <strong>
                      {ok ? '✅' : '❌'} {THRESHOLD_LABELS[name] ?? name}
                    </strong>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="empty-state">No threshold evaluation yet.</p>
            )}
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <div className="section-header section-header--stacked">
              <div>
                <h2>Scenario results</h2>
                <p className="dashboard-card__subtitle">Click a row to inspect expected vs actual behavior.</p>
              </div>
            </div>

            <div className="filter-chips" role="group" aria-label="Filter scenarios">
              {(['all', 'passed', 'failed', 'unsafe'] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  className={`filter-chip${filter === option ? ' filter-chip--active' : ''}`}
                  aria-pressed={filter === option}
                  onClick={() => setFilter(option)}
                >
                  {option === 'all' ? 'All' : option === 'unsafe' ? 'Failed/unsafe' : option.charAt(0).toUpperCase() + option.slice(1)}
                  {' '}({filterCounts[option] ?? 0})
                </button>
              ))}
            </div>

            {scenariosQuery.isLoading ? <p className="loading-state">Loading scenarios…</p> : null}
            {scenariosQuery.error ? (
              <div role="alert" className="alert alert--error">
                {scenariosQuery.error instanceof Error ? scenariosQuery.error.message : 'Failed to load scenarios'}
              </div>
            ) : null}

            {!scenariosQuery.isLoading && scenarios.length === 0 ? (
              <p className="empty-state">No scenarios match this filter.</p>
            ) : null}

            {scenarios.length > 0 ? (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th scope="col">ID</th>
                      <th scope="col">Status</th>
                      <th scope="col">Intent</th>
                      <th scope="col">State</th>
                      <th scope="col">Time</th>
                      <th scope="col">Links</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scenarios.map((row) => (
                      <tr
                        key={row.id}
                        className={!row.passed || isUnsafeScenario(row) ? 'data-table__row--attention' : 'row-success'}
                        onClick={() => setDetail(row)}
                        tabIndex={0}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            setDetail(row);
                          }
                        }}
                        role="button"
                        aria-label={`Inspect scenario ${row.scenario_id}`}
                      >
                        <td>{row.scenario_id}</td>
                        <td>{row.passed ? 'Passed' : 'Failed'}</td>
                        <td>{String(row.actual_json.intent ?? '—')}</td>
                        <td>{String(row.actual_json.state ?? '—')}</td>
                        <td>{row.processing_time_ms}ms</td>
                        <td>
                          {row.conversation_id ? (
                            <Link
                              className="table-link"
                              to={`/conversations/${row.conversation_id}`}
                              onClick={(event) => event.stopPropagation()}
                            >
                              Conversation
                            </Link>
                          ) : (
                            '—'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </section>

          {detail ? <ScenarioDetailPanel scenario={detail} onClose={() => setDetail(null)} /> : null}
        </>
      ) : null}

      <ConfirmDialog
        open={resetDialogOpen}
        title="Reset validation data?"
        message="This removes all TRL validation runs and TRL-owned simulation conversations, messages, and orders for the selected shop. Real customer data is not affected."
        confirmLabel="Reset validation data"
        onConfirm={() => resetMutation.mutate()}
        onCancel={() => setResetDialogOpen(false)}
        isLoading={resetMutation.isPending}
      />
    </div>
  );
}
