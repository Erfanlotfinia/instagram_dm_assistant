import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Callout, Card, CardBody, CardHeader, Field, FilterChip, Input, RadioCard, RadioCardGrid, StatusBanner } from '../components/ui';
import { KpiCard, DataTable, LoadingState, EmptyState } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import { cn } from '../lib/cn';
import type {
  AdminTask,
  AutomationSuggestion,
  OperatorCorrection,
  ScenarioCoverageRow,
  ScenarioRegressionMetrics,
} from '../types/socialAdmin';
import type { SimulatorRunItem, SimulatorRunSummary } from '../types/trust';

const PROVIDER_LABELS = ['Instagram', 'WhatsApp', 'Telegram', 'Bale', 'Rubika'];

function Page({
  eyebrow = 'Automation',
  title,
  description,
  actions,
  children,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <HubPage eyebrow={eyebrow} title={title} description={description} actions={actions}>
      {children}
    </HubPage>
  );
}

function formatRate(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function StatCard({
  label,
  value,
  hint,
  tone = 'accent',
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: 'success' | 'warning' | 'accent' | 'danger';
}) {
  return <KpiCard label={label} value={value} hint={hint} tone={tone} />;
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'implemented') {
    return <Badge tone="success">Implemented</Badge>;
  }
  if (status === 'partially_implemented') {
    return <Badge tone="warning">Partial</Badge>;
  }
  return <Badge tone="neutral">{status.replace(/_/g, ' ')}</Badge>;
}

function AutomationTierBadge({ tier, children }: { tier: string; children: React.ReactNode }) {
  const toneClass =
    tier === 'deterministic'
      ? 'bg-accent-soft text-accent'
      : tier === 'llm'
        ? 'bg-info-soft text-info'
        : tier === 'human'
          ? 'bg-warning-soft text-warning'
          : 'bg-surface-sunken text-muted';
  return (
    <span className={cn('inline-flex rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide', toneClass)}>
      {children}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const tone = priority === 'P0' ? 'danger' : priority === 'P1' ? 'warning' : 'neutral';
  return <Badge tone={tone}>{priority}</Badge>;
}

/* ───────────────────────────── Scenario Coverage ───────────────────────────── */

const GROUP_LABELS: Record<string, string> = {
  A: 'Referenced content',
  B: 'Product discovery',
  C: 'Orders',
  D: 'Payments',
  E: 'Shipping',
  F: 'Support',
  G: 'Marketing / admin',
};

const CAPABILITIES = [
  { key: 'deterministic_handler_exists', short: 'D', label: 'Deterministic handler' },
  { key: 'LLM_fallback_exists', short: 'L', label: 'LLM fallback' },
  { key: 'human_handoff_exists', short: 'H', label: 'Human handoff' },
  { key: 'tests_exist', short: 'T', label: 'Automated tests' },
  { key: 'frontend_support_exists', short: 'F', label: 'Frontend support' },
] as const;

function groupOf(row: ScenarioCoverageRow): string {
  return row.scenario_code.charAt(0).toUpperCase();
}

export function ScenarioCoveragePage() {
  const { selectedShop, selectedShopId } = useShop();
  const [groupFilter, setGroupFilter] = useState<string>('all');

  const coverageQuery = useQuery({
    queryKey: ['scenario-coverage', selectedShopId],
    queryFn: () => apiClient.getScenarioCoverage(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });

  const rows = coverageQuery.data ?? [];

  const groups = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of rows) {
      const key = groupOf(row);
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [rows]);

  const stats = useMemo(() => {
    const fullyCovered = rows.filter((row) =>
      CAPABILITIES.every((cap) => row[cap.key as keyof ScenarioCoverageRow] === true),
    ).length;
    return {
      total: rows.length,
      implemented: rows.filter((row) => row.current_status === 'implemented').length,
      partial: rows.filter((row) => row.current_status === 'partially_implemented').length,
      p0: rows.filter((row) => row.priority === 'P0').length,
      fullyCovered,
    };
  }, [rows]);

  const visibleRows = useMemo(
    () => (groupFilter === 'all' ? rows : rows.filter((row) => groupOf(row) === groupFilter)),
    [rows, groupFilter],
  );

  if (!selectedShop) {
    return (
      <Page
        title="Scenario Coverage"
        description="Track which social-admin scenarios are automated, where LLM fallback applies, and which still rely on human handoff."
      >
        <Card>
          <CardBody>
            <EmptyState
              title="Select a shop"
              description="Use the shop switcher in the top bar to load the scenario coverage matrix."
            />
          </CardBody>
        </Card>
      </Page>
    );
  }

  return (
    <Page
      title="Scenario Coverage"
      description="Track which social-admin scenarios are automated, where LLM fallback applies, and which still rely on human handoff."
    >
      {coverageQuery.isLoading ? (
        <Card>
          <CardBody>
            <LoadingState label="Loading scenario coverage…" />
          </CardBody>
        </Card>
      ) : null}

      {coverageQuery.error ? (
        <Card>
          <CardBody>
            <p className="text-sm text-danger" role="alert">
              {coverageQuery.error instanceof Error
                ? coverageQuery.error.message
                : 'Failed to load scenario coverage'}
            </p>
          </CardBody>
        </Card>
      ) : null}

      {coverageQuery.data ? (
        <>
          <Card>
            <CardHeader
              title="Coverage summary"
              description={`Every scenario is exercised across ${PROVIDER_LABELS.join(' · ')}.`}
            />
            <CardBody>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <StatCard label="Total scenarios" value={String(stats.total)} />
                <StatCard
                  label="Implemented"
                  value={String(stats.implemented)}
                  tone={stats.implemented > 0 ? 'success' : undefined}
                />
                <StatCard
                  label="Partially implemented"
                  value={String(stats.partial)}
                  tone={stats.partial > 0 ? 'warning' : undefined}
                />
                <StatCard label="P0 priority" value={String(stats.p0)} tone="accent" />
                <StatCard
                  label="Full automation stack"
                  value={`${stats.fullyCovered}/${stats.total}`}
                  hint="Deterministic + LLM + handoff + tests + UI"
                  tone={stats.fullyCovered === stats.total ? 'success' : undefined}
                />
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Coverage matrix"
              description="Filter by scenario group to inspect status, automation layers, and priority."
            />
            <CardBody>

            <div className="flex flex-wrap gap-2" role="group" aria-label="Filter scenarios by group">
              <FilterChip active={groupFilter === 'all'} onClick={() => setGroupFilter('all')}>
                All ({stats.total})
              </FilterChip>
              {groups.map(([key, count]) => (
                <FilterChip key={key} active={groupFilter === key} onClick={() => setGroupFilter(key)}>
                  {GROUP_LABELS[key] ?? key} ({count})
                </FilterChip>
              ))}
            </div>

            <div
              className="mt-4 flex flex-wrap gap-x-4 gap-y-2 rounded-lg border border-dashed border-border bg-surface-sunken px-3 py-2"
              aria-hidden="true"
            >
              {CAPABILITIES.map((cap) => (
                <span key={cap.key} className="inline-flex items-center gap-1.5 text-xs text-muted">
                  <span className="inline-flex h-5 w-5 items-center justify-center rounded bg-success-soft text-[10px] font-bold text-success">
                    {cap.short}
                  </span>
                  {cap.label}
                </span>
              ))}
            </div>

            <DataTable
              columns={[
                {
                  key: 'scenario',
                  header: 'Scenario',
                  render: (row) => (
                    <div className="flex flex-col gap-0.5">
                      <span className="font-medium text-fg">{row.scenario_name}</span>
                      <span className="font-mono text-xs text-subtle">{row.scenario_code}</span>
                    </div>
                  ),
                },
                {
                  key: 'group',
                  header: 'Group',
                  className: 'hidden md:table-cell',
                  render: (row) => <Badge tone="neutral">{GROUP_LABELS[groupOf(row)] ?? groupOf(row)}</Badge>,
                },
                {
                  key: 'status',
                  header: 'Status',
                  render: (row) => <StatusBadge status={row.current_status} />,
                },
                {
                  key: 'layers',
                  header: 'Automation layers',
                  className: 'hidden md:table-cell',
                  render: (row) => (
                    <span className="inline-flex gap-1">
                      {CAPABILITIES.map((cap) => {
                        const on = row[cap.key as keyof ScenarioCoverageRow] === true;
                        return (
                          <span
                            key={cap.key}
                            className={cn(
                              'inline-flex h-5 w-5 items-center justify-center rounded text-[10px] font-bold',
                              on ? 'bg-success-soft text-success' : 'bg-surface-sunken text-subtle',
                            )}
                            title={`${cap.label}: ${on ? 'yes' : 'no'}`}
                          >
                            {cap.short}
                          </span>
                        );
                      })}
                    </span>
                  ),
                },
                {
                  key: 'priority',
                  header: 'Priority',
                  className: 'hidden md:table-cell',
                  render: (row) => <PriorityBadge priority={row.priority} />,
                },
              ]}
              rows={visibleRows}
              rowKey={(row) => row.scenario_code}
              emptyTitle="No scenarios match this group"
            />
            </CardBody>
          </Card>
        </>
      ) : null}
    </Page>
  );
}

/* ───────────────────────────── Automation Rules ───────────────────────────── */

const TIER_LABELS: Record<string, string> = {
  deterministic: 'Deterministic',
  llm: 'LLM',
  human: 'Human',
};

export function AutomationRulesPage() {
  const { selectedShopId } = useShop();

  const rulesQuery = useQuery({
    queryKey: ['automation-rules', selectedShopId],
    queryFn: () => apiClient.listAutomationRules(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });

  return (
    <Page
      title="Automation Rules"
      description="The agent evaluates each incoming message top-to-bottom. The first matching layer wins, keeping responses deterministic and auditable before any model is invoked."
    >
      <Card>
        <CardHeader
          title="Handler priority ladder"
          description="Evaluated in order — deterministic handlers are always preferred over the LLM, and the LLM is always preferred over interrupting a human."
        />
        <CardBody>

        {rulesQuery.isLoading ? <LoadingState label="Loading handler priority…" /> : null}
        {rulesQuery.error ? (
          <p className="text-sm text-danger" role="alert">
            {rulesQuery.error instanceof Error ? rulesQuery.error.message : 'Failed to load rules'}
          </p>
        ) : null}

        {rulesQuery.data ? (
          <>
            <ol className="mt-5 grid gap-2.5">
              {rulesQuery.data.map((step) => (
                <li
                  key={step.order}
                  className="grid items-center gap-3 rounded-lg border border-border bg-surface-sunken px-4 py-3 sm:grid-cols-[auto_minmax(0,1fr)_auto]"
                >
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-fg text-sm font-bold text-canvas">
                    {step.order}
                  </span>
                  <div className="min-w-0">
                    <p className="font-semibold text-fg">{step.label}</p>
                    <p className="mt-0.5 text-sm text-muted">{step.detail}</p>
                  </div>
                  <AutomationTierBadge tier={step.tier}>
                    {TIER_LABELS[step.tier] ?? step.tier}
                  </AutomationTierBadge>
                </li>
              ))}
            </ol>

            <div className="mt-4 flex flex-wrap items-center gap-2 text-sm text-muted" aria-hidden="true">
              <AutomationTierBadge tier="deterministic">Deterministic</AutomationTierBadge>
              <span>→</span>
              <AutomationTierBadge tier="llm">LLM fallback</AutomationTierBadge>
              <span>→</span>
              <AutomationTierBadge tier="human">Human handoff</AutomationTierBadge>
            </div>
          </>
        ) : null}
        </CardBody>
      </Card>
    </Page>
  );
}

/* ───────────────────────────── Scenario Simulator ───────────────────────────── */

const LAST_METRICS_STORAGE_KEY = 'modira:last-regression-metrics';

function loadLastMetrics(shopId: string): ScenarioRegressionMetrics | null {
  try {
    const raw = localStorage.getItem(LAST_METRICS_STORAGE_KEY);
    if (!raw) return null;
    const map = JSON.parse(raw) as Record<string, ScenarioRegressionMetrics>;
    return map[shopId] ?? null;
  } catch {
    return null;
  }
}

function saveLastMetrics(shopId: string, metrics: ScenarioRegressionMetrics): void {
  try {
    const raw = localStorage.getItem(LAST_METRICS_STORAGE_KEY);
    const map = raw ? (JSON.parse(raw) as Record<string, ScenarioRegressionMetrics>) : {};
    map[shopId] = metrics;
    localStorage.setItem(LAST_METRICS_STORAGE_KEY, JSON.stringify(map));
  } catch {
    // Ignore quota / privacy-mode errors — comparison is a best-effort UI hint.
  }
}

function runStatusTone(status: string): 'success' | 'warning' | 'danger' | 'neutral' {
  if (status === 'completed') return 'success';
  if (status === 'running') return 'warning';
  if (status === 'failed') return 'danger';
  return 'neutral';
}

function deltaLabel(delta?: number): string {
  if (delta === undefined) return '—';
  if (delta === 0) return '0';
  return delta > 0 ? `+${delta}` : `${delta}`;
}

function deltaTone(delta?: number): 'success' | 'danger' | 'accent' {
  if (delta === undefined || delta === 0) return 'accent';
  return delta > 0 ? 'success' : 'danger';
}

export function ScenarioSimulatorPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const [metrics, setMetrics] = useState<ScenarioRegressionMetrics | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const runMutation = useMutation({
    mutationFn: () => apiClient.runScenarioRegression(selectedShopId!),
    onSuccess: (data) => {
      setMetrics(data);
      if (selectedShopId) saveLastMetrics(selectedShopId, data);
      const safe =
        data.unsafe_action_count === 0 &&
        data.false_order_count === 0 &&
        data.false_payment_count === 0;
      showToast(
        safe
          ? `Regression complete: ${formatRate(data.scenario_accuracy)} handler accuracy`
          : 'Regression finished with safety warnings — review counts below',
        safe ? 'success' : 'error',
      );
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  // Recent replay runs (history) — separate from the aggregate scenario pack run.
  const runsQuery = useQuery({
    queryKey: ['replay-runs', selectedShopId],
    queryFn: () => apiClient.listReplayRuns(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });

  // Selected run detail (item-level pass/fail).
  const runDetailQuery = useQuery({
    queryKey: ['replay-run', selectedShopId, selectedRunId],
    queryFn: () => apiClient.getReplayRun(selectedShopId!, selectedRunId!),
    enabled: Boolean(selectedShopId) && Boolean(selectedRunId),
  });

  const runs = runsQuery.data ?? [];
  const completedRuns = useMemo(
    () => runs.filter((run) => run.status === 'completed' || run.status === 'failed'),
    [runs],
  );
  const currentRun = completedRuns[0];
  const previousRun = completedRuns[1];

  const comparison = useMemo(() => {
    if (!currentRun) return null;
    const total = previousRun ? currentRun.total_items - previousRun.total_items : undefined;
    const passed = previousRun ? currentRun.passed_items - previousRun.passed_items : undefined;
    const failed = previousRun ? currentRun.failed_items - previousRun.failed_items : undefined;
    return { total, passed, failed };
  }, [currentRun, previousRun]);

  const previousMetrics = selectedShopId ? loadLastMetrics(selectedShopId) : null;

  const failedItems = useMemo(
    () => (runDetailQuery.data?.items ?? []).filter((item) => !item.passed),
    [runDetailQuery.data],
  );

  const safetyOk =
    metrics &&
    metrics.unsafe_action_count === 0 &&
    metrics.false_order_count === 0 &&
    metrics.false_payment_count === 0;

  const runColumns: Column<SimulatorRunSummary>[] = [
    {
      key: 'label',
      header: 'Run',
      render: (run) => run.label ?? run.id,
    },
    {
      key: 'status',
      header: 'Status',
      render: (run) => <Badge tone={runStatusTone(run.status)}>{run.status}</Badge>,
    },
    { key: 'total', header: 'Total', render: (run) => String(run.total_items) },
    { key: 'passed', header: 'Passed', render: (run) => String(run.passed_items) },
    {
      key: 'failed',
      header: 'Failed',
      render: (run) => (
        <Badge tone={run.failed_items === 0 ? 'success' : 'danger'}>{run.failed_items}</Badge>
      ),
    },
    {
      key: 'started',
      header: 'Started',
      render: (run) => (
        <time className="text-xs text-muted" dateTime={run.started_at}>
          {new Date(run.started_at).toLocaleString()}
        </time>
      ),
    },
  ];

  const failedColumns: Column<SimulatorRunItem>[] = [
    { key: 'item', header: 'Scenario', render: (item) => item.item_key },
    {
      key: 'mismatches',
      header: 'Mismatches',
      render: (item) => {
        const mismatches = item.diff_json?.mismatches ?? [];
        const count = mismatches.length;
        if (count === 0) return <span className="text-muted">—</span>;
        return (
          <Badge tone={count > 2 ? 'danger' : 'warning'}>{count}</Badge>
        );
      },
    },
    {
      key: 'detail',
      header: 'Detail',
      render: (item) => {
        const mismatches = item.diff_json?.mismatches ?? [];
        return (
          <span className="line-clamp-2 text-xs text-muted">
            {mismatches.join(' · ') || 'Failed without mismatch detail'}
          </span>
        );
      },
    },
    {
      key: 'trace',
      header: '',
      align: 'right',
      render: (item) =>
        item.trace_id && item.conversation_id ? (
          <Link
            className="text-xs text-accent hover:underline"
            to={`/inbox/${item.conversation_id}/intelligence`}
          >
            Trace
          </Link>
        ) : (
          <span className="text-xs text-muted">—</span>
        ),
    },
  ];

  return (
    <Page
      title="Scenario Simulator"
      description="Run the social-admin regression pack against the selected shop and inspect automation rate, LLM fallback rate, handoff rate, accuracy, and safety counters."
    >
      <Card>
        <CardHeader
          title="Regression pack"
          description="Replays the full 150-scenario pack and scores handler accuracy alongside safety guardrails. Nothing is sent to customers."
        />
        <CardBody className="flex flex-col gap-4">
        <Button
          type="button"
          disabled={!selectedShopId || runMutation.isPending}
          onClick={() => runMutation.mutate()}
        >
          {runMutation.isPending ? 'Running scenario pack…' : 'Run regression suite'}
        </Button>

        {!selectedShopId ? (
          <EmptyState title="Select a shop" description="Use the shop switcher in the top bar to enable the regression run." />
        ) : null}

        {runMutation.isError ? (
          <p className="text-sm text-danger" role="alert">
            {runMutation.error instanceof Error ? runMutation.error.message : 'Regression failed'}
          </p>
        ) : null}
        </CardBody>
      </Card>

      {metrics ? (
        <Card aria-live="polite">
          <CardHeader
            title="Regression results"
            description="Latest run for the selected shop."
            actions={
              <Badge tone={safetyOk ? 'success' : 'danger'}>
                {safetyOk ? 'Safety clear' : 'Safety warnings'}
              </Badge>
            }
          />
          <CardBody className="flex flex-col gap-4">
          <StatusBanner
            tone={safetyOk ? 'ok' : 'failed'}
            title={safetyOk ? 'All safety counters are zero' : 'Safety thresholds not met'}
            description={
              safetyOk
                ? 'No unsafe actions, false orders, or false payments were produced.'
                : 'Do not promote to pilot until unsafe actions, false orders, and false payments are resolved.'
            }
          />

          <div className="flex flex-col gap-6">
            <div>
              <h3 className="mb-3 text-sm font-semibold text-fg">Automation mix</h3>
              <div className="grid gap-3 sm:grid-cols-3">
                <StatCard label="Automation handled" value={formatRate(metrics.automation_handled_rate)} />
                <StatCard label="LLM fallback" value={formatRate(metrics.llm_fallback_rate)} />
                <StatCard label="Handoff" value={formatRate(metrics.handoff_rate)} />
              </div>
            </div>

            <div>
              <h3 className="mb-3 text-sm font-semibold text-fg">Accuracy</h3>
              <div className="grid gap-3 sm:grid-cols-3">
                <StatCard
                  label="Scenario accuracy (handler match)"
                  value={formatRate(metrics.scenario_accuracy)}
                  tone={metrics.scenario_accuracy >= 0.8 ? 'success' : 'warning'}
                />
                <StatCard
                  label="Reference resolution accuracy"
                  value={formatRate(metrics.reference_resolution_accuracy)}
                />
                <StatCard
                  label="Product discovery accuracy"
                  value={formatRate(metrics.product_discovery_accuracy)}
                />
              </div>
            </div>

            <div>
              <h3 className="mb-3 text-sm font-semibold text-fg">Safety counters</h3>
              <div className="grid gap-3 sm:grid-cols-3">
                <StatCard
                  label="Unsafe actions"
                  value={String(metrics.unsafe_action_count)}
                  tone={metrics.unsafe_action_count === 0 ? 'success' : 'warning'}
                />
                <StatCard
                  label="False orders"
                  value={String(metrics.false_order_count)}
                  tone={metrics.false_order_count === 0 ? 'success' : 'warning'}
                />
                <StatCard
                  label="False payments"
                  value={String(metrics.false_payment_count)}
                  tone={metrics.false_payment_count === 0 ? 'success' : 'warning'}
                />
              </div>
            </div>
          </div>
          </CardBody>
        </Card>
      ) : null}

      {/* Previous vs current comparison */}
      {selectedShopId ? (
        <Card>
          <CardHeader
            title="Previous vs current"
            description="Compares the two most recent completed replay runs. Scenario-pack metric deltas use the last cached run."
          />
          <CardBody>
            {!currentRun || !previousRun ? (
              <EmptyState
                title="Not enough history yet"
                description="Run the regression suite at least twice (with replay runs recorded) to see a comparison."
              />
            ) : (
              <div className="grid gap-3 sm:grid-cols-3">
                <KpiCard
                  label="Total scenarios"
                  value={deltaLabel(comparison?.total)}
                  tone={deltaTone(comparison?.total)}
                  hint={`current ${currentRun.total_items} · previous ${previousRun.total_items}`}
                />
                <KpiCard
                  label="Passed"
                  value={deltaLabel(comparison?.passed)}
                  tone={deltaTone(comparison?.passed)}
                  hint={`current ${currentRun.passed_items} · previous ${previousRun.passed_items}`}
                />
                <KpiCard
                  label="Failed"
                  value={deltaLabel(comparison?.failed)}
                  tone={deltaTone(comparison?.failed)}
                  hint={`current ${currentRun.failed_items} · previous ${previousRun.failed_items}`}
                />
              </div>
            )}

            {metrics && previousMetrics ? (
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <KpiCard
                  label="Scenario accuracy (Δ)"
                  value={deltaLabel(
                    Math.round((metrics.scenario_accuracy - previousMetrics.scenario_accuracy) * 100),
                  )}
                  tone={deltaTone(
                    Math.round((metrics.scenario_accuracy - previousMetrics.scenario_accuracy) * 100),
                  )}
                />
                <KpiCard
                  label="Unsafe actions (Δ)"
                  value={deltaLabel(metrics.unsafe_action_count - previousMetrics.unsafe_action_count)}
                  tone={deltaTone(previousMetrics.unsafe_action_count - metrics.unsafe_action_count)}
                />
                <KpiCard
                  label="False orders (Δ)"
                  value={deltaLabel(metrics.false_order_count - previousMetrics.false_order_count)}
                  tone={deltaTone(previousMetrics.false_order_count - metrics.false_order_count)}
                />
              </div>
            ) : null}
          </CardBody>
        </Card>
      ) : null}

      {/* Recent runs history */}
      {selectedShopId ? (
        <Card>
          <CardHeader
            title="Recent runs"
            description="Replay runs recorded for this shop. Select a run to inspect failed scenarios."
            actions={<Badge>{runs.length}</Badge>}
          />
          <CardBody className="flex flex-col gap-3">
            <DataTable
              columns={runColumns}
              rows={runs}
              rowKey={(run) => run.id}
              onRowClick={(run) => setSelectedRunId(run.id)}
              isLoading={runsQuery.isLoading}
              error={runsQuery.error instanceof Error ? runsQuery.error.message : null}
              emptyTitle="No replay runs recorded"
              emptyDescription="Run the regression suite or replay a scenario pack to populate history."
              rowClassName={(run) => (run.id === selectedRunId ? 'bg-accent-soft/40' : undefined)}
            />
          </CardBody>
        </Card>
      ) : null}

      {/* Failed scenarios for the selected run */}
      {selectedShopId && selectedRunId ? (
        <Card>
          <CardHeader
            title="Failed scenarios"
            description={`Item-level failures for the selected replay run (${selectedRunId}).`}
            actions={<Badge tone="danger">{failedItems.length}</Badge>}
          />
          <CardBody className="flex flex-col gap-3">
            {runDetailQuery.isLoading ? <LoadingState label="Loading run detail…" /> : null}
            {runDetailQuery.error ? (
              <p className="text-sm text-danger" role="alert">
                {runDetailQuery.error instanceof Error ? runDetailQuery.error.message : 'Failed to load run detail'}
              </p>
            ) : null}
            {runDetailQuery.data ? (
              <DataTable
                columns={failedColumns}
                rows={failedItems}
                rowKey={(item) => item.id}
                emptyTitle="No failed scenarios in this run"
                emptyDescription="Every scenario in this replay run passed."
              />
            ) : null}
          </CardBody>
        </Card>
      ) : null}
    </Page>
  );
}

/* ───────────────────────────── Admin AI Tasks ───────────────────────────── */

const AI_TASKS: Array<{ id: string; label: string; description: string }> = [
  { id: 'suggest_reply', label: 'Suggest reply', description: 'Draft a reply to the current conversation for operator review.' },
  { id: 'summarize_conversation', label: 'Summarize conversation', description: 'Condense a long thread into the key facts and open questions.' },
  { id: 'faq_mining', label: 'FAQ mining', description: 'Surface frequently asked questions from recent conversations.' },
  { id: 'draft_post_caption', label: 'Draft post caption', description: 'Generate a caption for a product post or new arrival.' },
  { id: 'draft_story_text', label: 'Draft story text', description: 'Write short story copy for a promotion or restock.' },
  { id: 'draft_campaign_message', label: 'Draft campaign message', description: 'Compose a broadcast message for a campaign segment.' },
];

function draftStatusBadge(status: string): { tone: 'success' | 'danger' | 'warning' | 'neutral'; label: string } {
  if (status === 'approved') {
    return { tone: 'success', label: 'Approved' };
  }
  if (status === 'rejected') {
    return { tone: 'danger', label: 'Rejected' };
  }
  if (status === 'completed') {
    return { tone: 'warning', label: 'Awaiting approval' };
  }
  return { tone: 'neutral', label: status.replace(/_/g, ' ') };
}

export function AdminAITasksPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [selectedTask, setSelectedTask] = useState(AI_TASKS[0].id);
  const [context, setContext] = useState('');
  const [activeDraft, setActiveDraft] = useState<AdminTask | null>(null);

  const tasksQuery = useQuery({
    queryKey: ['admin-tasks', selectedShopId],
    queryFn: () => apiClient.listAdminTasks(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      apiClient.createAdminTask(selectedShopId!, {
        task_type: selectedTask,
        context: context.trim(),
      }),
    onSuccess: (task) => {
      setActiveDraft(task);
      showToast('Draft generated — awaiting approval', 'success');
      void queryClient.invalidateQueries({ queryKey: ['admin-tasks', selectedShopId] });
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const approveMutation = useMutation({
    mutationFn: (taskId: string) => apiClient.approveAdminTask(selectedShopId!, taskId),
    onSuccess: (task) => {
      setActiveDraft(task);
      showToast('Draft approved', 'success');
      void queryClient.invalidateQueries({ queryKey: ['admin-tasks', selectedShopId] });
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const rejectMutation = useMutation({
    mutationFn: (taskId: string) => apiClient.rejectAdminTask(selectedShopId!, taskId),
    onSuccess: (task) => {
      setActiveDraft(task);
      showToast('Draft rejected', 'info');
      void queryClient.invalidateQueries({ queryKey: ['admin-tasks', selectedShopId] });
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const activeTask = AI_TASKS.find((task) => task.id === selectedTask) ?? AI_TASKS[0];
  const tasks = tasksQuery.data ?? [];
  const actionsDisabled = approveMutation.isPending || rejectMutation.isPending;

  return (
    <Page
      title="Admin AI Tasks"
      description="Generate approval-gated drafts for replies, summaries, captions, and campaigns. Every output is reviewed by an operator — nothing is published automatically."
    >
      <Card>
        <CardHeader
          title="Create approval-gated draft"
          description="Pick a task, add context, and generate a draft for review."
        />
        <CardBody>
        <div className="grid gap-5">
          <RadioCardGrid label="Task type" aria-label="Task type">
            {AI_TASKS.map((task) => (
              <RadioCard
                key={task.id}
                active={task.id === selectedTask}
                label={task.label}
                description={task.description}
                onClick={() => setSelectedTask(task.id)}
              />
            ))}
          </RadioCardGrid>

          <Field label="Context" className="sm:col-span-2">
            <textarea
              value={context}
              onChange={(event) => setContext(event.target.value)}
              rows={4}
              placeholder="Product, category, campaign, or conversation context"
              className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg"
            />
          </Field>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              disabled={!selectedShopId || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? 'Generating draft…' : 'Generate draft'}
            </Button>
            {!selectedShopId ? (
              <span className="text-sm text-muted">Select a shop to enable draft generation.</span>
            ) : null}
          </div>

          {activeDraft?.output_json.draft ? (
            <div className="grid gap-3 rounded-lg border border-accent/30 bg-accent-soft/30 p-4" aria-live="polite">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-bold uppercase tracking-wide text-accent">
                  Generated draft · {activeTask.label}
                </p>
                <Badge tone={draftStatusBadge(activeDraft.status).tone}>
                  {draftStatusBadge(activeDraft.status).label}
                </Badge>
              </div>
              <div className="max-h-80 overflow-y-auto rounded-lg border border-border bg-surface p-3">
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-fg">{activeDraft.output_json.draft}</p>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    void navigator.clipboard
                      ?.writeText(activeDraft.output_json.draft ?? '')
                      .then(() => showToast('Draft copied to clipboard', 'success'))
                      .catch(() => showToast('Could not copy draft', 'error'));
                  }}
                >
                  Copy
                </Button>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={actionsDisabled || activeDraft.status !== 'completed'}
                    onClick={() => rejectMutation.mutate(activeDraft.id)}
                  >
                    Reject draft
                  </Button>
                  <Button
                    type="button"
                    disabled={actionsDisabled || activeDraft.status !== 'completed'}
                    onClick={() => approveMutation.mutate(activeDraft.id)}
                  >
                    Approve draft
                  </Button>
                </div>
              </div>
            </div>
          ) : null}
        </div>

        <Callout icon="✓" title="Approval gate">
          No task auto-publishes; every generated output requires admin approval before it reaches a
          customer or channel.
        </Callout>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Recent drafts"
          description="Approval-gated tasks created for this shop."
        />
        <CardBody>

        {tasksQuery.isLoading ? <LoadingState label="Loading admin tasks…" /> : null}
        {tasks.length === 0 && !tasksQuery.isLoading ? (
          <EmptyState title="No admin tasks yet" description="Generate a draft above." />
        ) : null}

        {tasks.length > 0 ? (
          <DataTable
            columns={[
              {
                key: 'task',
                header: 'Task',
                render: (task) => task.task_type.replace(/_/g, ' '),
              },
              {
                key: 'status',
                header: 'Status',
                render: (task) => (
                  <Badge
                    tone={
                      task.status === 'approved'
                        ? 'success'
                        : task.status === 'rejected'
                          ? 'danger'
                          : 'warning'
                    }
                  >
                    {task.status}
                  </Badge>
                ),
              },
              {
                key: 'created',
                header: 'Created',
                render: (task) => new Date(task.created_at).toLocaleString(),
              },
            ]}
            rows={tasks}
            rowKey={(task) => task.id}
          />
        ) : null}
        </CardBody>
      </Card>
    </Page>
  );
}

/* ───────────────────────────── Operator Corrections ───────────────────────────── */

const CAPTURE_FIELDS: Array<{ key: string; icon: string; title: string; body: string }> = [
  { key: 'scenario', icon: 'SC', title: 'Scenario', body: 'The intent the agent should have matched (e.g. price request, order confirm).' },
  { key: 'product', icon: 'PR', title: 'Product', body: 'The correct product when the agent resolved the wrong item or none at all.' },
  { key: 'attribute', icon: 'AT', title: 'Attribute', body: 'The right color, size, or variant when normalization missed.' },
  { key: 'reference', icon: 'RF', title: 'Reference', body: 'What “this”, “the story”, or a forwarded post actually referred to.' },
  { key: 'response', icon: 'RS', title: 'Response', body: 'The corrected reply text the customer should have received.' },
  { key: 'decision_channel', icon: 'CH', title: 'Decision channel', body: 'Whether automation, LLM, or a human was the appropriate handler.' },
];

const EMPTY_CORRECTION_FORM = {
  conversation_id: '',
  before: {
    scenario: '',
    product: '',
    attribute: '',
    reference: '',
    response: '',
    decision_channel: '',
  },
  after: {
    scenario: '',
    product: '',
    attribute: '',
    reference: '',
    response: '',
    decision_channel: '',
  },
};

export function OperatorCorrectionsPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState(EMPTY_CORRECTION_FORM);

  const correctionsQuery = useQuery({
    queryKey: ['operator-corrections', selectedShopId],
    queryFn: () => apiClient.listOperatorCorrections(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      apiClient.createOperatorCorrection(selectedShopId!, {
        conversation_id: form.conversation_id,
        before_json: form.before,
        after_json: form.after,
      }),
    onSuccess: (created) => {
      showToast(`Captured ${created.length} correction(s)`, 'success');
      setForm(EMPTY_CORRECTION_FORM);
      void queryClient.invalidateQueries({ queryKey: ['operator-corrections', selectedShopId] });
      void queryClient.invalidateQueries({ queryKey: ['automation-suggestions', selectedShopId] });
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const corrections = correctionsQuery.data ?? [];

  function updateField(
    side: 'before' | 'after',
    key: string,
    value: string,
  ) {
    setForm((current) => ({
      ...current,
      [side]: { ...current[side], [key]: value },
    }));
  }

  return (
    <Page
      title="Operator Corrections"
      description="When an operator overrides the agent, the correction is captured as structured training signal that feeds rule, alias, and regression-test suggestions."
    >
      <Card>
        <CardHeader
          title="Capture correction"
          description="Record what the agent did versus what should have happened. Changed fields generate suggestions automatically."
        />
        <CardBody>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Conversation ID" className="sm:col-span-2">
            <Input
              value={form.conversation_id}
              onChange={(event) => setForm((current) => ({ ...current, conversation_id: event.target.value }))}
              placeholder="UUID of the conversation being corrected"
            />
          </Field>

          {CAPTURE_FIELDS.map((field) => (
            <Field key={field.key} label={`Before — ${field.title}`}>
              <Input
                value={form.before[field.key as keyof typeof form.before]}
                onChange={(event) => updateField('before', field.key, event.target.value)}
                placeholder={`Agent ${field.title.toLowerCase()}`}
              />
            </Field>
          ))}

          {CAPTURE_FIELDS.map((field) => (
            <Field key={`after-${field.key}`} label={`After — ${field.title}`}>
              <Input
                value={form.after[field.key as keyof typeof form.after]}
                onChange={(event) => updateField('after', field.key, event.target.value)}
                placeholder={`Correct ${field.title.toLowerCase()}`}
              />
            </Field>
          ))}

          <Button
            type="button"
            disabled={!selectedShopId || !form.conversation_id || createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            {createMutation.isPending ? 'Saving correction…' : 'Save correction'}
          </Button>
        </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Recent corrections"
          description="Each saved field becomes a structured correction and may spawn automation suggestions."
        />
        <CardBody>

        {correctionsQuery.isLoading ? <LoadingState label="Loading corrections…" /> : null}
        {corrections.length === 0 && !correctionsQuery.isLoading ? (
          <EmptyState title="No corrections captured yet." />
        ) : null}

        {corrections.length > 0 ? (
          <DataTable
            columns={[
              { key: 'type', header: 'Type', render: (row) => row.correction_type },
              {
                key: 'before',
                header: 'Before',
                className: 'hidden sm:table-cell',
                render: (row) => String(Object.values(row.before_json)[0] ?? '—'),
              },
              {
                key: 'after',
                header: 'After',
                render: (row) => String(Object.values(row.after_json)[0] ?? '—'),
              },
              {
                key: 'captured',
                header: 'Captured',
                className: 'hidden sm:table-cell',
                render: (row) => new Date(row.created_at).toLocaleString(),
              },
            ]}
            rows={corrections}
            rowKey={(row) => row.id}
          />
        ) : null}

        <Callout icon="→" title="Review the learning loop">
          Generated improvements appear in{' '}
          <Link className="font-medium text-accent hover:underline" to="/automation-suggestions">
            Automation Suggestions
          </Link>{' '}
          for review before they change agent behavior.
        </Callout>
        </CardBody>
      </Card>
    </Page>
  );
}

/* ───────────────────────────── Automation Suggestions ───────────────────────────── */

const SUGGESTION_TYPES: Array<{ icon: string; title: string; body: string; example: string }> = [
  {
    icon: 'RL',
    title: 'Rule suggestion',
    body: 'Promote a repeated correction into a deterministic keyword or pattern rule.',
    example: 'Add rule: messages containing “size chart” → send sizing guide.',
  },
  {
    icon: 'AL',
    title: 'Alias suggestion',
    body: 'Map a customer phrasing to a known color, size, or product so resolution succeeds next time.',
    example: 'Alias: “navy” → color “dark blue”.',
  },
  {
    icon: 'RT',
    title: 'Regression-test suggestion',
    body: 'Lock in a fixed correction as a scenario so future changes cannot regress it.',
    example: 'New test: forwarded story → resolves to product SKU-1042.',
  },
];

function suggestionTypeLabel(type: string | undefined): string {
  if (type === 'alias') return 'Alias';
  if (type === 'regression_test') return 'Regression test';
  return 'Rule';
}

function suggestionConfidence(suggestion: AutomationSuggestion): 'high' | 'medium' | 'low' | '—' {
  const rule = suggestion.suggested_rule_json;
  // Deterministic: a fully-specified suggestion (rule + test) ranks highest;
  // a partial one (rule or alias only) ranks medium; otherwise unknown.
  const hasRule = Boolean(rule.rule && Object.keys(rule.rule).length > 0);
  const hasTest = Boolean(rule.test && Object.keys(rule.test).length > 0);
  const hasAlias = Boolean(rule.alias && Object.keys(rule.alias).length > 0);
  if (hasRule && hasTest) return 'high';
  if (hasRule || hasAlias) return 'medium';
  if (hasTest) return 'low';
  return '—';
}

function confidenceTone(conf: 'high' | 'medium' | 'low' | '—'): 'success' | 'warning' | 'neutral' {
  if (conf === 'high') return 'success';
  if (conf === 'medium') return 'warning';
  return 'neutral';
}

function statusTone(status: string): 'success' | 'danger' | 'warning' | 'neutral' {
  if (status === 'approved') return 'success';
  if (status === 'rejected') return 'danger';
  if (status === 'pending') return 'warning';
  return 'neutral';
}

function SuggestionPreview({ suggestion }: { suggestion: AutomationSuggestion }) {
  const [open, setOpen] = useState(false);
  const rule = suggestion.suggested_rule_json;
  return (
    <div className="flex flex-col gap-1">
      <Button type="button" variant="ghost" size="sm" onClick={() => setOpen((v) => !v)}>
        {open ? 'Hide impact' : 'Preview impact'}
      </Button>
      {open ? (
        <div className="rounded-lg border border-border bg-surface-sunken p-3 text-xs">
          <p className="text-fg">{rule.summary ?? 'No summary provided.'}</p>
          <pre className="mt-2 max-h-64 overflow-auto rounded bg-surface p-2 text-[11px] text-muted">
            {JSON.stringify({ rule: rule.rule, alias: rule.alias, test: rule.test }, null, 2)}
          </pre>
        </div>
      ) : null}
    </div>
  );
}

export function AutomationSuggestionsPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all');

  const suggestionsQuery = useQuery({
    queryKey: ['automation-suggestions', selectedShopId, statusFilter],
    queryFn: () =>
      apiClient.listAutomationSuggestions(
        selectedShopId!,
        statusFilter === 'all' ? undefined : statusFilter,
      ),
    enabled: Boolean(selectedShopId),
  });

  const queryKeyFor = (filter: 'all' | 'pending' | 'approved' | 'rejected') =>
    ['automation-suggestions', selectedShopId, filter] as const;

  // Optimistically flip a suggestion's status in every relevant cache entry,
  // rolling back on error so the UI never lies about server state.
  const optimisticallySetStatus = (suggestionId: string, nextStatus: string) => {
    const filters: Array<'all' | 'pending' | 'approved' | 'rejected'> = ['all', 'pending', 'approved', 'rejected'];
    const snapshots = new Map<string, AutomationSuggestion[] | undefined>();
    for (const filter of filters) {
      const key = queryKeyFor(filter);
      const current = queryClient.getQueryData<AutomationSuggestion[]>(key);
      snapshots.set(filter, current);
      if (!current) continue;
      queryClient.setQueryData<AutomationSuggestion[]>(key, current.map((s) => (s.id === suggestionId ? { ...s, status: nextStatus } : s)));
    }
    return () => {
      for (const filter of filters) {
        const snapshot = snapshots.get(filter);
        if (snapshot !== undefined) {
          queryClient.setQueryData(queryKeyFor(filter), snapshot);
        }
      }
    };
  };

  const approveMutation = useMutation({
    mutationFn: (suggestionId: string) =>
      apiClient.approveAutomationSuggestion(selectedShopId!, suggestionId),
    onMutate: (suggestionId) => optimisticallySetStatus(suggestionId, 'approved'),
    onSuccess: () => {
      showToast('Suggestion approved', 'success');
      void queryClient.invalidateQueries({ queryKey: ['automation-suggestions', selectedShopId] });
    },
    onError: (error: Error, _suggestionId, rollback) => {
      rollback?.();
      showToast(error.message, 'error');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (suggestionId: string) =>
      apiClient.rejectAutomationSuggestion(selectedShopId!, suggestionId),
    onMutate: (suggestionId) => optimisticallySetStatus(suggestionId, 'rejected'),
    onSuccess: () => {
      showToast('Suggestion rejected', 'info');
      void queryClient.invalidateQueries({ queryKey: ['automation-suggestions', selectedShopId] });
    },
    onError: (error: Error, _suggestionId, rollback) => {
      rollback?.();
      showToast(error.message, 'error');
    },
  });

  const suggestions = suggestionsQuery.data ?? [];
  const actionsDisabled = approveMutation.isPending || rejectMutation.isPending;

  const columns: Column<AutomationSuggestion>[] = [
    {
      key: 'intent',
      header: 'Intent',
      render: (suggestion) => (
        <span className="font-medium text-fg">
          {suggestionTypeLabel(suggestion.suggested_rule_json.type)}
        </span>
      ),
    },
    {
      key: 'confidence',
      header: 'Confidence',
      render: (suggestion) => {
        const conf = suggestionConfidence(suggestion);
        return conf === '—' ? (
          <span className="text-muted">—</span>
        ) : (
          <Badge tone={confidenceTone(conf)}>{conf}</Badge>
        );
      },
    },
    {
      key: 'reason',
      header: 'Reason',
      render: (suggestion) => (
        <span className="line-clamp-2 text-muted">
          {suggestion.suggested_rule_json.summary ?? suggestion.suggested_rule_json.title ?? '—'}
        </span>
      ),
    },
    {
      key: 'created',
      header: 'Created',
      render: (suggestion) => (
        <time className="text-xs text-muted" dateTime={suggestion.created_at}>
          {new Date(suggestion.created_at).toLocaleString()}
        </time>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (suggestion) => <Badge tone={statusTone(suggestion.status)}>{suggestion.status}</Badge>,
    },
    {
      key: 'actions',
      header: 'Actions',
      align: 'right',
      render: (suggestion) => (
        <div className="flex flex-wrap justify-end gap-2">
          {suggestion.status === 'pending' ? (
            <>
              <Button
                type="button"
                size="sm"
                disabled={actionsDisabled}
                onClick={() => approveMutation.mutate(suggestion.id)}
              >
                Approve
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={actionsDisabled}
                onClick={() => rejectMutation.mutate(suggestion.id)}
              >
                Reject
              </Button>
            </>
          ) : (
            <span className="text-xs text-muted">—</span>
          )}
        </div>
      ),
    },
  ];

  return (
    <Page
      title="Automation Suggestions"
      description="Review rule, alias, and regression-test suggestions generated from operator corrections, then apply the ones that improve automation safely."
    >
      <Card>
        <CardHeader
          title="Learning loop"
          description="Corrections become reviewable suggestions — you stay in control of what changes."
        />
        <CardBody>
        <div className="grid gap-4 sm:grid-cols-3">
          {SUGGESTION_TYPES.map((type) => (
            <article key={type.title} className="grid gap-2 rounded-lg border border-border bg-surface-sunken p-4">
              <span
                className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-soft text-xs font-bold text-accent"
                aria-hidden="true"
              >
                {type.icon}
              </span>
              <h3 className="font-semibold text-fg">{type.title}</h3>
              <p className="text-sm leading-relaxed text-muted">{type.body}</p>
              <p className="rounded-md bg-surface px-2.5 py-2 text-xs text-subtle">{type.example}</p>
            </article>
          ))}
        </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Suggestion inbox"
          description="Approve or reject generated improvements before they affect automation."
          actions={<Badge>{suggestions.length}</Badge>}
        />
        <CardBody className="flex flex-col gap-4">

        <div className="flex flex-wrap gap-2" role="group" aria-label="Filter suggestions by status">
          {(['all', 'pending', 'approved', 'rejected'] as const).map((option) => (
            <FilterChip key={option} active={statusFilter === option} onClick={() => setStatusFilter(option)}>
              {option.charAt(0).toUpperCase() + option.slice(1)}
            </FilterChip>
          ))}
        </div>

        {!selectedShopId ? (
          <EmptyState title="Select a shop" description="Use the shop switcher in the top bar to load suggestions." />
        ) : null}

        {suggestions.length > 0 ? (
          <DataTable
            columns={columns}
            rows={suggestions}
            rowKey={(suggestion) => suggestion.id}
            isLoading={suggestionsQuery.isLoading}
            error={suggestionsQuery.error instanceof Error ? suggestionsQuery.error.message : null}
            emptyTitle="No suggestions match this filter"
          />
        ) : (
          <>
            {suggestionsQuery.isLoading ? <LoadingState label="Loading suggestions…" /> : null}
            {suggestionsQuery.error ? (
              <p className="text-sm text-danger" role="alert">
                {suggestionsQuery.error instanceof Error
                  ? suggestionsQuery.error.message
                  : 'Failed to load suggestions'}
              </p>
            ) : null}
            {suggestions.length === 0 && !suggestionsQuery.isLoading ? (
              <EmptyState
                title="No suggestions yet"
                description={
                  <>
                    Suggestions appear here once operators capture corrections in{' '}
                    <Link className="font-medium text-accent hover:underline" to="/operator-corrections">
                      Operator Corrections
                    </Link>
                    .
                  </>
                }
              />
            ) : null}
          </>
        )}

        {suggestions.length > 0 ? (
          <div className="flex flex-col gap-3">
            <h3 className="text-sm font-semibold text-fg">Preview impact</h3>
            {suggestions.map((suggestion) => (
              <SuggestionPreview key={suggestion.id} suggestion={suggestion} />
            ))}
          </div>
        ) : null}
        </CardBody>
      </Card>
    </Page>
  );
}
