import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Select } from '../components/ui';
import type { BadgeTone } from '../components/ui';
import { DataTable, EmptyState, KpiCard, LoadingState } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { cn } from '../lib/cn';
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

function runStatusBadge(run: TRLValidationRun): { label: string; tone: BadgeTone } {
  const thresholds = (run.metrics_json.thresholds_passed ?? {}) as Record<string, boolean>;
  const allPassed = Object.values(thresholds).length > 0 && Object.values(thresholds).every(Boolean);
  if (run.status === 'failed') {
    return { label: 'Run failed', tone: 'danger' };
  }
  if (run.status === 'running') {
    return { label: 'Running', tone: 'warning' };
  }
  if (allPassed && run.failed_scenarios === 0) {
    return { label: 'All thresholds passed', tone: 'success' };
  }
  if (allPassed) {
    return { label: 'Thresholds passed', tone: 'warning' };
  }
  return { label: 'Thresholds failing', tone: 'danger' };
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
    <Card aria-label="Scenario detail">
      <CardHeader
        title={scenario.scenario_id}
        description={
          scenario.passed ? 'Scenario passed all checks.' : 'Review mismatches and failure reasons below.'
        }
        actions={<Badge tone={scenario.passed ? 'success' : 'danger'}>{scenario.passed ? 'Passed' : 'Failed'}</Badge>}
      />
      <CardBody className="flex flex-col gap-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <KpiCard
            label="Intent (actual)"
            value={actualIntent}
            tone={scenario.passed ? 'success' : 'warning'}
          />
          <KpiCard label="State" value={String(scenario.actual_json.state ?? '—')} />
          <KpiCard label="Processing time" value={`${scenario.processing_time_ms}ms`} />
        </div>

        <dl className="detail-grid">
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
          <div>
            <h3 className="mb-2 text-sm font-semibold text-fg">Failure reasons</h3>
            <ul className="list-inside list-disc space-y-1 text-sm text-muted">
              {scenario.failure_reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          {scenario.conversation_id ? (
            <>
              <Link
                className="inline-flex h-10 items-center rounded-lg border border-border bg-surface px-4 text-sm font-medium text-fg hover:bg-surface-sunken"
                to={`/conversations/${scenario.conversation_id}`}
              >
                Open conversation
              </Link>
              <Link
                className="inline-flex h-10 items-center rounded-lg border border-border bg-surface px-4 text-sm font-medium text-fg hover:bg-surface-sunken"
                to={`/conversations/${scenario.conversation_id}#decision-trace`}
              >
                Decision trace
              </Link>
            </>
          ) : null}
          <Button variant="secondary" type="button" onClick={onClose}>
            Close
          </Button>
        </div>

        <details className="text-sm">
          <summary className="cursor-pointer text-accent hover:underline">Full scenario payload</summary>
          <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-surface-sunken p-3 text-xs text-subtle">
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
      </CardBody>
    </Card>
  );
}

export function TRLValidationPage() {
  const { selectedShopId } = useShop();
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

  const scenarioColumns: Column<TRLValidationScenarioResult>[] = [
    { key: 'id', header: 'ID', render: (row) => row.scenario_id },
    {
      key: 'status',
      header: 'Status',
      render: (row) => (
        <Badge tone={row.passed ? 'success' : 'danger'}>{row.passed ? 'Passed' : 'Failed'}</Badge>
      ),
    },
    { key: 'intent', header: 'Intent', render: (row) => String(row.actual_json.intent ?? '—') },
    { key: 'state', header: 'State', render: (row) => String(row.actual_json.state ?? '—') },
    { key: 'time', header: 'Time', render: (row) => `${row.processing_time_ms}ms` },
    {
      key: 'links',
      header: 'Links',
      render: (row) =>
        row.conversation_id ? (
          <Link
            className="font-medium text-accent hover:underline"
            to={`/conversations/${row.conversation_id}`}
            onClick={(event) => event.stopPropagation()}
          >
            Conversation
          </Link>
        ) : (
          '—'
        ),
    },
  ];

  return (
    <HubPage
      eyebrow="Relevant environment testing"
      title="TRL 5 Validation"
      description="Runs scripted DM scenarios through the production orchestrator without sending real Instagram messages. Use this before enabling pilot traffic."
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
          <Card>
            <CardHeader
              title="Run validation"
              description="Choose how many scenarios to execute. Full runs can take a minute — keep this tab open."
              actions={<Badge tone="info">Test harness</Badge>}
            />
            <CardBody className="flex flex-col gap-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Scenario count">
                  <Select
                    value={scenarioLimit}
                    onChange={(event) => setScenarioLimit(Number(event.target.value))}
                    disabled={runMutation.isPending}
                  >
                    {SCENARIO_LIMIT_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </Field>

                <label className="flex items-center gap-2 self-end pb-1 text-sm text-fg">
                  <input
                    type="checkbox"
                    checked={resetDemoData}
                    onChange={(event) => setResetDemoData(event.target.checked)}
                    disabled={runMutation.isPending}
                    className="rounded border-border"
                  />
                  Reset demo catalog before run
                </label>
              </div>

              {runMutation.isPending ? (
                <LoadingState label={`Running ${scenarioLimit} scenarios through the orchestrator…`} />
              ) : null}

              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  onClick={() => runMutation.mutate()}
                  disabled={runMutation.isPending || resetMutation.isPending}
                >
                  {runMutation.isPending ? 'Running…' : 'Run validation'}
                </Button>
                <Button
                  variant="secondary"
                  type="button"
                  disabled={runMutation.isPending || resetMutation.isPending}
                  onClick={() => setResetDialogOpen(true)}
                >
                  Reset validation data
                </Button>
              </div>
            </CardBody>
          </Card>

          {runsQuery.isLoading ? (
            <Card>
              <CardBody>
                <LoadingState label="Loading validation history…" />
              </CardBody>
            </Card>
          ) : null}
          {runsQuery.error ? (
            <Card>
              <CardBody>
                <p className="text-sm text-danger" role="alert">
                  {runsQuery.error instanceof Error ? runsQuery.error.message : 'Failed to load validation runs'}
                </p>
              </CardBody>
            </Card>
          ) : null}

          {!runsQuery.isLoading && runs.length === 0 ? (
            <Card>
              <CardBody>
                <EmptyState
                  title="No validation runs yet"
                  description="Run validation to generate TRL 5 metrics, threshold checks, and per-scenario evidence."
                />
              </CardBody>
            </Card>
          ) : null}

          {selectedRun ? (
            <>
              <Card>
                <CardHeader
                  title="Run summary"
                  description={`Started ${formatRunTimestamp(selectedRun.started_at)}${selectedRun.completed_at ? ` · Completed ${formatRunTimestamp(selectedRun.completed_at)}` : ''}`}
                  actions={statusBadge ? <Badge tone={statusBadge.tone}>{statusBadge.label}</Badge> : null}
                />
                <CardBody className="flex flex-col gap-4">
                  {runs.length > 1 ? (
                    <Field label="Run history">
                      <Select
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
                      </Select>
                    </Field>
                  ) : null}

                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    <KpiCard label="Validation mode" value={String(selectedRun.validation_mode ?? metrics.validation_mode ?? 'deterministic_regression')} />
                    <KpiCard label="Evidence type" value={metrics.proves_live_llm ? 'Live/staging LLM' : 'Deterministic regression'} />
                    <KpiCard label="Scenarios passed" value={`${selectedRun.passed_scenarios}/${selectedRun.total_scenarios}`} />
                    <KpiCard label="Pass rate" value={`${passRate}%`} tone={passRate >= 90 ? 'success' : passRate >= 70 ? 'accent' : 'warning'} />
                    <KpiCard label="Failed scenarios" value={String(selectedRun.failed_scenarios)} tone={selectedRun.failed_scenarios > 0 ? 'warning' : 'accent'} />
                    <KpiCard label="Run status" value={selectedRun.status} />
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    <KpiCard label="Intent accuracy" value={percent(metrics.intent_accuracy)} />
                    <KpiCard label="Slot accuracy" value={percent(metrics.slot_extraction_accuracy)} />
                    <KpiCard label="Product resolution" value={percent(metrics.product_resolution_accuracy)} />
                    <KpiCard label="Variant resolution" value={percent(metrics.variant_resolution_accuracy)} />
                    <KpiCard label="False auto-sends" value={String(metrics.false_auto_send_count ?? 0)} />
                    <KpiCard label="False orders" value={String(metrics.false_order_creation_count ?? 0)} />
                  </div>
                </CardBody>
              </Card>

              <Card>
                <CardHeader title="Risk & latency" />
                <CardBody className="flex flex-col gap-4">
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    <KpiCard label="Invalid LLM JSON" value={String(riskMetrics?.invalid_llm_json_count ?? metrics.invalid_llm_json_count ?? 0)} />
                    <KpiCard label="Safe fallbacks" value={String(riskMetrics?.safe_fallback_count ?? metrics.safe_fallback_count ?? 0)} />
                    <KpiCard label="Human handoffs" value={String(riskMetrics?.human_handoff_count ?? metrics.human_handoff_count ?? 0)} />
                    <KpiCard label="Critical risk events" value={String(riskMetrics?.critical_risk_count ?? metrics.critical_risk_count ?? 0)} />
                    <KpiCard
                      label="Average risk score"
                      value={
                        riskMetrics
                          ? `${Math.round(riskMetrics.average_risk_score * 100)}%`
                          : `${Math.round(Number(metrics.average_risk_score ?? 0) * 100)}%`
                      }
                    />
                    <KpiCard label="P95 latency" value={`${riskMetrics?.p95_processing_latency ?? metrics.p95_processing_latency ?? 0}ms`} />
                  </div>

                  <div>
                    <h3 className="mb-2 text-sm font-semibold text-fg">Pass rate by category</h3>
                    <ul className="space-y-1 text-sm">
                      {Object.entries(
                        riskMetrics?.scenario_pass_rate_by_category ??
                          (metrics.scenario_pass_rate_by_category as Record<string, number> | undefined) ??
                          {},
                      ).map(([category, value]) => (
                        <li key={category} className="flex justify-between gap-4 text-muted">
                          <span>{category}</span>
                          <strong className="text-fg">{percent(value)}</strong>
                        </li>
                      ))}
                    </ul>
                  </div>
                </CardBody>
              </Card>

              <Card>
                <CardHeader title="Acceptance thresholds" />
                <CardBody>
                  {thresholdRows.length ? (
                    <ul className="space-y-2 text-sm">
                      {thresholdRows.map(([name, ok]) => (
                        <li
                          key={name}
                          className={cn(
                            'rounded-md border px-3 py-2',
                            ok ? 'border-success/30 bg-success-soft/20' : 'border-danger/30 bg-danger-soft/20',
                          )}
                        >
                          <strong className="text-fg">
                            {ok ? '✅' : '❌'} {THRESHOLD_LABELS[name] ?? name}
                          </strong>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <EmptyState title="No threshold evaluation yet" />
                  )}
                </CardBody>
              </Card>

              <Card>
                <CardHeader title="Scenario results" description="Click a row to inspect expected vs actual behavior." />
                <CardBody className="flex flex-col gap-4">
                  <div className="flex flex-wrap gap-2" role="group" aria-label="Filter scenarios">
                    {(['all', 'passed', 'failed', 'unsafe'] as const).map((option) => (
                      <Chip key={option} active={filter === option} onClick={() => setFilter(option)}>
                        {option === 'all' ? 'All' : option === 'unsafe' ? 'Failed/unsafe' : option.charAt(0).toUpperCase() + option.slice(1)}
                        {' '}({filterCounts[option] ?? 0})
                      </Chip>
                    ))}
                  </div>

                  <DataTable
                    columns={scenarioColumns}
                    rows={scenarios}
                    rowKey={(row) => row.id}
                    onRowClick={setDetail}
                    isLoading={scenariosQuery.isLoading}
                    error={scenariosQuery.error instanceof Error ? scenariosQuery.error.message : null}
                    emptyTitle="No scenarios match this filter"
                    rowClassName={(row) =>
                      !row.passed || isUnsafeScenario(row) ? 'bg-danger-soft/10' : undefined
                    }
                  />
                </CardBody>
              </Card>

              {detail ? <ScenarioDetailPanel scenario={detail} onClose={() => setDetail(null)} /> : null}
            </>
          ) : null}
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
    </HubPage>
  );
}
