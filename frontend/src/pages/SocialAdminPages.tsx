import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import type {
  AdminTask,
  AutomationSuggestion,
  OperatorCorrection,
  ScenarioCoverageRow,
  ScenarioRegressionMetrics,
} from '../types/socialAdmin';

const PROVIDER_LABELS = ['Instagram', 'WhatsApp', 'Telegram', 'Bale', 'Rubika'];

function Page({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide sa-hero">
        <div className="sa-hero__intro">
          <p className="dashboard-card__eyebrow">Social admin automation</p>
          <h1>{title}</h1>
          <p className="sa-hero__description">{description}</p>
        </div>
        {actions ? <div className="sa-hero__actions">{actions}</div> : null}
      </section>
      {children}
    </div>
  );
}

function formatRate(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function StatCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: 'success' | 'warning' | 'accent';
}) {
  const toneClass =
    tone === 'success'
      ? ' stat-card--success'
      : tone === 'warning'
        ? ' stat-card--warning'
        : tone === 'accent'
          ? ' stat-card--accent'
          : '';
  return (
    <article className={`stat-card${toneClass}`}>
      <p className="stat-card__label">{label}</p>
      <p className="stat-card__value">{value}</p>
      {hint ? <p className="stat-card__hint">{hint}</p> : null}
    </article>
  );
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

function statusPill(status: string): { className: string; label: string } {
  if (status === 'implemented') {
    return { className: 'status-pill status-pill--success', label: 'Implemented' };
  }
  if (status === 'partially_implemented') {
    return { className: 'status-pill status-pill--warning', label: 'Partial' };
  }
  return { className: 'status-pill status-pill--neutral', label: status.replace(/_/g, ' ') };
}

function priorityBadgeClass(priority: string): string {
  switch (priority) {
    case 'P0':
      return 'priority-badge priority-badge--urgent';
    case 'P1':
      return 'priority-badge priority-badge--medium';
    default:
      return 'priority-badge priority-badge--low';
  }
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
        <section className="dashboard-card dashboard-card--wide sa-prompt-card">
          <p className="empty-state">Select a shop to load its scenario coverage matrix.</p>
          <ShopSelector />
        </section>
      </Page>
    );
  }

  return (
    <Page
      title="Scenario Coverage"
      description="Track which social-admin scenarios are automated, where LLM fallback applies, and which still rely on human handoff."
      actions={<ShopSelector label="Shop" />}
    >
      {coverageQuery.isLoading ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="loading-state">Loading scenario coverage…</p>
        </section>
      ) : null}

      {coverageQuery.error ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="form-error" role="alert">
            {coverageQuery.error instanceof Error
              ? coverageQuery.error.message
              : 'Failed to load scenario coverage'}
          </p>
        </section>
      ) : null}

      {coverageQuery.data ? (
        <>
          <section className="dashboard-card dashboard-card--wide">
            <div className="section-header section-header--stacked">
              <div>
                <h2>Coverage summary</h2>
                <p className="section-header__subtitle">
                  Every scenario is exercised across {PROVIDER_LABELS.join(' · ')}.
                </p>
              </div>
            </div>
            <div className="stats-grid">
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
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <div className="section-header section-header--stacked">
              <div>
                <h2>Coverage matrix</h2>
                <p className="section-header__subtitle">
                  Filter by scenario group to inspect status, automation layers, and priority.
                </p>
              </div>
            </div>

            <div className="filter-chips" role="group" aria-label="Filter scenarios by group">
              <button
                type="button"
                className={`filter-chip${groupFilter === 'all' ? ' filter-chip--active' : ''}`}
                aria-pressed={groupFilter === 'all'}
                onClick={() => setGroupFilter('all')}
              >
                All ({stats.total})
              </button>
              {groups.map(([key, count]) => (
                <button
                  key={key}
                  type="button"
                  className={`filter-chip${groupFilter === key ? ' filter-chip--active' : ''}`}
                  aria-pressed={groupFilter === key}
                  onClick={() => setGroupFilter(key)}
                >
                  {GROUP_LABELS[key] ?? key} ({count})
                </button>
              ))}
            </div>

            <div className="sa-legend" aria-hidden="true">
              {CAPABILITIES.map((cap) => (
                <span key={cap.key} className="sa-legend__item">
                  <span className="sa-cap sa-cap--on">{cap.short}</span>
                  {cap.label}
                </span>
              ))}
            </div>

            <div className="table-wrap">
              <table className="data-table data-table--compact">
                <thead>
                  <tr>
                    <th scope="col">Scenario</th>
                    <th scope="col" className="col-hide-md">Group</th>
                    <th scope="col">Status</th>
                    <th scope="col" className="col-hide-md">Automation layers</th>
                    <th scope="col" className="col-hide-md">Priority</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleRows.map((row) => {
                    const status = statusPill(row.current_status);
                    const group = groupOf(row);
                    return (
                      <tr key={row.scenario_code}>
                        <td>
                          <div className="sa-scenario">
                            <span className="sa-scenario__name">{row.scenario_name}</span>
                            <span className="sa-scenario__code">{row.scenario_code}</span>
                          </div>
                        </td>
                        <td className="col-hide-md">
                          <span className="sa-group-tag">{GROUP_LABELS[group] ?? group}</span>
                        </td>
                        <td>
                          <span className={status.className}>{status.label}</span>
                        </td>
                        <td className="col-hide-md">
                          <span className="sa-caps">
                            {CAPABILITIES.map((cap) => {
                              const on = row[cap.key as keyof ScenarioCoverageRow] === true;
                              return (
                                <span
                                  key={cap.key}
                                  className={`sa-cap ${on ? 'sa-cap--on' : 'sa-cap--off'}`}
                                  title={`${cap.label}: ${on ? 'yes' : 'no'}`}
                                >
                                  {cap.short}
                                </span>
                              );
                            })}
                          </span>
                        </td>
                        <td className="col-hide-md">
                          <span className={priorityBadgeClass(row.priority)}>{row.priority}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {visibleRows.length === 0 ? (
              <p className="empty-state">No scenarios match this group.</p>
            ) : null}
          </section>
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
      actions={<ShopSelector label="Shop" />}
    >
      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Handler priority ladder</h2>
            <p className="section-header__subtitle">
              Evaluated in order — deterministic handlers are always preferred over the LLM, and the
              LLM is always preferred over interrupting a human.
            </p>
          </div>
        </div>

        {rulesQuery.isLoading ? <p className="loading-state">Loading handler priority…</p> : null}
        {rulesQuery.error ? (
          <p className="form-error" role="alert">
            {rulesQuery.error instanceof Error ? rulesQuery.error.message : 'Failed to load rules'}
          </p>
        ) : null}

        {rulesQuery.data ? (
          <>
            <ol className="sa-ladder">
              {rulesQuery.data.map((step) => (
                <li key={step.order} className="sa-ladder__item">
                  <span className="sa-ladder__num">{step.order}</span>
                  <div className="sa-ladder__body">
                    <p className="sa-ladder__label">{step.label}</p>
                    <p className="sa-ladder__detail">{step.detail}</p>
                  </div>
                  <span className={`sa-tier sa-tier--${step.tier}`}>
                    {TIER_LABELS[step.tier] ?? step.tier}
                  </span>
                </li>
              ))}
            </ol>

            <div className="sa-pipeline" aria-hidden="true">
              <span className="sa-pipeline__step sa-tier sa-tier--deterministic">Deterministic</span>
              <span className="sa-pipeline__arrow">→</span>
              <span className="sa-pipeline__step sa-tier sa-tier--llm">LLM fallback</span>
              <span className="sa-pipeline__arrow">→</span>
              <span className="sa-pipeline__step sa-tier sa-tier--human">Human handoff</span>
            </div>
          </>
        ) : null}
      </section>
    </Page>
  );
}

/* ───────────────────────────── Scenario Simulator ───────────────────────────── */

export function ScenarioSimulatorPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const [metrics, setMetrics] = useState<ScenarioRegressionMetrics | null>(null);

  const runMutation = useMutation({
    mutationFn: () => apiClient.runScenarioRegression(selectedShopId!),
    onSuccess: (data) => {
      setMetrics(data);
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

  const safetyOk =
    metrics &&
    metrics.unsafe_action_count === 0 &&
    metrics.false_order_count === 0 &&
    metrics.false_payment_count === 0;

  return (
    <Page
      title="Scenario Simulator"
      description="Run the social-admin regression pack against the selected shop and inspect automation rate, LLM fallback rate, handoff rate, accuracy, and safety counters."
      actions={<ShopSelector label="Shop for regression run" />}
    >
      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Regression pack</h2>
            <p className="section-header__subtitle">
              Replays the full 150-scenario pack and scores handler accuracy alongside safety
              guardrails. Nothing is sent to customers.
            </p>
          </div>
        </div>

        <div className="button-row">
          <button
            type="button"
            className="button button--primary"
            disabled={!selectedShopId || runMutation.isPending}
            onClick={() => runMutation.mutate()}
          >
            {runMutation.isPending ? 'Running scenario pack…' : 'Run scenario pack'}
          </button>
        </div>

        {!selectedShopId ? (
          <p className="empty-state">Select a shop above to enable the regression run.</p>
        ) : null}

        {runMutation.isError ? (
          <p className="form-error" role="alert">
            {runMutation.error instanceof Error ? runMutation.error.message : 'Regression failed'}
          </p>
        ) : null}
      </section>

      {metrics ? (
        <section className="dashboard-card dashboard-card--wide" aria-live="polite">
          <div className="section-header section-header--stacked">
            <div>
              <h2>Regression results</h2>
              <p className="section-header__subtitle">Latest run for the selected shop.</p>
            </div>
            <span
              className={
                safetyOk
                  ? 'priority-badge priority-badge--low'
                  : 'priority-badge priority-badge--urgent'
              }
            >
              {safetyOk ? 'Safety clear' : 'Safety warnings'}
            </span>
          </div>

          <div
            className={`health-status-banner sa-safety-banner health-status-banner--${safetyOk ? 'ok' : 'failed'}`}
          >
            <div className="health-status-banner__indicator" aria-hidden="true" />
            <div>
              <p className="health-status-banner__title">
                {safetyOk
                  ? 'All safety counters are zero'
                  : 'Safety thresholds not met'}
              </p>
              <p className="health-status-banner__meta">
                {safetyOk
                  ? 'No unsafe actions, false orders, or false payments were produced.'
                  : 'Do not promote to pilot until unsafe actions, false orders, and false payments are resolved.'}
              </p>
            </div>
          </div>

          <div className="pilot-metrics-groups">
            <div className="pilot-metrics-group">
              <h3>Automation mix</h3>
              <div className="stats-grid">
                <StatCard label="Automation handled" value={formatRate(metrics.automation_handled_rate)} />
                <StatCard label="LLM fallback" value={formatRate(metrics.llm_fallback_rate)} />
                <StatCard label="Handoff" value={formatRate(metrics.handoff_rate)} />
              </div>
            </div>

            <div className="pilot-metrics-group">
              <h3>Accuracy</h3>
              <div className="stats-grid">
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

            <div className="pilot-metrics-group">
              <h3>Safety counters</h3>
              <div className="stats-grid">
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
        </section>
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

function draftStatusPill(status: string): { className: string; label: string } {
  if (status === 'approved') {
    return { className: 'status-pill status-pill--success', label: 'Approved' };
  }
  if (status === 'rejected') {
    return { className: 'status-pill status-pill--danger', label: 'Rejected' };
  }
  if (status === 'completed') {
    return { className: 'status-pill status-pill--warning', label: 'Awaiting approval' };
  }
  return { className: 'status-pill status-pill--neutral', label: status.replace(/_/g, ' ') };
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
      actions={<ShopSelector label="Shop" />}
    >
      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Create approval-gated draft</h2>
            <p className="section-header__subtitle">Pick a task, add context, and generate a draft for review.</p>
          </div>
        </div>

        <div className="sa-composer">
          <div className="sa-composer__field">
            <p className="sa-composer__field-label">Task type</p>
            <div className="agent-mode-grid" role="radiogroup" aria-label="Task type">
              {AI_TASKS.map((task) => {
                const active = task.id === selectedTask;
                return (
                  <button
                    key={task.id}
                    type="button"
                    role="radio"
                    aria-checked={active}
                    className={`agent-mode-card${active ? ' agent-mode-card--active' : ''}`}
                    onClick={() => setSelectedTask(task.id)}
                  >
                    <span className="agent-mode-card__label">{task.label}</span>
                    <span className="agent-mode-card__description">{task.description}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <label className="form-field form-field--wide sa-composer__field">
            <span>Context</span>
            <textarea
              value={context}
              onChange={(event) => setContext(event.target.value)}
              rows={4}
              placeholder="Product, category, campaign, or conversation context"
            />
          </label>

          <div className="sa-composer__submit">
            <button
              type="button"
              className="button button--primary sa-composer__generate"
              disabled={!selectedShopId || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending ? 'Generating draft…' : 'Generate draft'}
            </button>
            {!selectedShopId ? (
              <span className="sa-composer__hint">Select a shop to enable draft generation.</span>
            ) : null}
          </div>

          {activeDraft?.output_json.draft ? (
            <div className="sa-composer__preview" aria-live="polite">
              <div className="sa-composer__preview-header">
                <p className="sa-composer__preview-label">
                  Generated draft · {activeTask.label}
                </p>
                <span className={draftStatusPill(activeDraft.status).className}>
                  {draftStatusPill(activeDraft.status).label}
                </span>
              </div>
              <div className="sa-composer__preview-scroll">
                <p className="sa-composer__preview-body">{activeDraft.output_json.draft}</p>
              </div>
              <div className="sa-composer__preview-actions">
                <button
                  type="button"
                  className="button button--ghost-dark sa-composer__copy"
                  onClick={() => {
                    void navigator.clipboard
                      ?.writeText(activeDraft.output_json.draft ?? '')
                      .then(() => showToast('Draft copied to clipboard', 'success'))
                      .catch(() => showToast('Could not copy draft', 'error'));
                  }}
                >
                  Copy
                </button>
                <div className="button-row">
                  <button
                    type="button"
                    className="button button--ghost-dark"
                    disabled={actionsDisabled || activeDraft.status !== 'completed'}
                    onClick={() => rejectMutation.mutate(activeDraft.id)}
                  >
                    Reject draft
                  </button>
                  <button
                    type="button"
                    className="button button--primary"
                    disabled={actionsDisabled || activeDraft.status !== 'completed'}
                    onClick={() => approveMutation.mutate(activeDraft.id)}
                  >
                    Approve draft
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </div>

        <div className="sa-callout">
          <span className="sa-callout__icon" aria-hidden="true">✓</span>
          <div>
            <p className="sa-callout__title">Approval gate</p>
            <p className="sa-callout__text">
              No task auto-publishes; every generated output requires admin approval before it reaches a
              customer or channel.
            </p>
          </div>
        </div>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Recent drafts</h2>
            <p className="section-header__subtitle">Approval-gated tasks created for this shop.</p>
          </div>
        </div>

        {tasksQuery.isLoading ? <p className="loading-state">Loading admin tasks…</p> : null}
        {tasks.length === 0 && !tasksQuery.isLoading ? (
          <p className="empty-state">No admin tasks yet. Generate a draft above.</p>
        ) : null}

        {tasks.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table data-table--compact">
              <thead>
                <tr>
                  <th scope="col">Task</th>
                  <th scope="col">Status</th>
                  <th scope="col">Created</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.id}>
                    <td>{task.task_type.replace(/_/g, ' ')}</td>
                    <td>
                      <span className={`status-pill status-pill--${task.status === 'approved' ? 'success' : task.status === 'rejected' ? 'danger' : 'warning'}`}>
                        {task.status}
                      </span>
                    </td>
                    <td>{new Date(task.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
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
      actions={<ShopSelector label="Shop" />}
    >
      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Capture correction</h2>
            <p className="section-header__subtitle">
              Record what the agent did versus what should have happened. Changed fields generate suggestions automatically.
            </p>
          </div>
        </div>

        <div className="inline-form">
          <label className="form-field form-field--wide">
            <span>Conversation ID</span>
            <input
              value={form.conversation_id}
              onChange={(event) => setForm((current) => ({ ...current, conversation_id: event.target.value }))}
              placeholder="UUID of the conversation being corrected"
            />
          </label>

          {CAPTURE_FIELDS.map((field) => (
            <label key={field.key} className="form-field">
              <span>Before — {field.title}</span>
              <input
                value={form.before[field.key as keyof typeof form.before]}
                onChange={(event) => updateField('before', field.key, event.target.value)}
                placeholder={`Agent ${field.title.toLowerCase()}`}
              />
            </label>
          ))}

          {CAPTURE_FIELDS.map((field) => (
            <label key={`after-${field.key}`} className="form-field">
              <span>After — {field.title}</span>
              <input
                value={form.after[field.key as keyof typeof form.after]}
                onChange={(event) => updateField('after', field.key, event.target.value)}
                placeholder={`Correct ${field.title.toLowerCase()}`}
              />
            </label>
          ))}

          <button
            type="button"
            className="button button--primary"
            disabled={!selectedShopId || !form.conversation_id || createMutation.isPending}
            onClick={() => createMutation.mutate()}
          >
            {createMutation.isPending ? 'Saving correction…' : 'Save correction'}
          </button>
        </div>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Recent corrections</h2>
            <p className="section-header__subtitle">
              Each saved field becomes a structured correction and may spawn automation suggestions.
            </p>
          </div>
        </div>

        {correctionsQuery.isLoading ? <p className="loading-state">Loading corrections…</p> : null}
        {corrections.length === 0 && !correctionsQuery.isLoading ? (
          <p className="empty-state">No corrections captured yet.</p>
        ) : null}

        {corrections.length > 0 ? (
          <div className="table-wrap">
            <table className="data-table data-table--compact">
              <thead>
                <tr>
                  <th scope="col">Type</th>
                  <th scope="col" className="col-hide-sm">Before</th>
                  <th scope="col">After</th>
                  <th scope="col" className="col-hide-sm">Captured</th>
                </tr>
              </thead>
              <tbody>
                {corrections.map((row: OperatorCorrection) => (
                  <tr key={row.id}>
                    <td>{row.correction_type}</td>
                    <td className="col-hide-sm">{String(Object.values(row.before_json)[0] ?? '—')}</td>
                    <td>{String(Object.values(row.after_json)[0] ?? '—')}</td>
                    <td className="col-hide-sm">{new Date(row.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        <div className="sa-callout">
          <span className="sa-callout__icon" aria-hidden="true">→</span>
          <div>
            <p className="sa-callout__title">Review the learning loop</p>
            <p className="sa-callout__text">
              Generated improvements appear in{' '}
              <Link className="table-link" to="/automation-suggestions">
                Automation Suggestions
              </Link>{' '}
              for review before they change agent behavior.
            </p>
          </div>
        </div>
      </section>
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

  const approveMutation = useMutation({
    mutationFn: (suggestionId: string) =>
      apiClient.approveAutomationSuggestion(selectedShopId!, suggestionId),
    onSuccess: () => {
      showToast('Suggestion approved', 'success');
      void queryClient.invalidateQueries({ queryKey: ['automation-suggestions', selectedShopId] });
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const rejectMutation = useMutation({
    mutationFn: (suggestionId: string) =>
      apiClient.rejectAutomationSuggestion(selectedShopId!, suggestionId),
    onSuccess: () => {
      showToast('Suggestion rejected', 'info');
      void queryClient.invalidateQueries({ queryKey: ['automation-suggestions', selectedShopId] });
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const suggestions = suggestionsQuery.data ?? [];
  const actionsDisabled = approveMutation.isPending || rejectMutation.isPending;

  return (
    <Page
      title="Automation Suggestions"
      description="Review rule, alias, and regression-test suggestions generated from operator corrections, then apply the ones that improve automation safely."
      actions={<ShopSelector label="Shop" />}
    >
      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Learning loop</h2>
            <p className="section-header__subtitle">
              Corrections become reviewable suggestions — you stay in control of what changes.
            </p>
          </div>
        </div>

        <div className="sa-info-grid">
          {SUGGESTION_TYPES.map((type) => (
            <article key={type.title} className="sa-info-card">
              <span className="sa-info-card__icon" aria-hidden="true">{type.icon}</span>
              <h3 className="sa-info-card__title">{type.title}</h3>
              <p className="sa-info-card__body">{type.body}</p>
              <p className="sa-info-card__example">{type.example}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Suggestion inbox</h2>
            <p className="section-header__subtitle">Approve or reject generated improvements before they affect automation.</p>
          </div>
        </div>

        <div className="filter-chips" role="group" aria-label="Filter suggestions by status">
          {(['all', 'pending', 'approved', 'rejected'] as const).map((option) => (
            <button
              key={option}
              type="button"
              className={`filter-chip${statusFilter === option ? ' filter-chip--active' : ''}`}
              aria-pressed={statusFilter === option}
              onClick={() => setStatusFilter(option)}
            >
              {option.charAt(0).toUpperCase() + option.slice(1)}
            </button>
          ))}
        </div>

        {suggestionsQuery.isLoading ? <p className="loading-state">Loading suggestions…</p> : null}
        {suggestionsQuery.error ? (
          <p className="form-error" role="alert">
            {suggestionsQuery.error instanceof Error
              ? suggestionsQuery.error.message
              : 'Failed to load suggestions'}
          </p>
        ) : null}

        {suggestions.length === 0 && !suggestionsQuery.isLoading ? (
          <div className="empty-state-panel">
            <p className="empty-state-panel__title">No suggestions yet</p>
            <p className="empty-state-panel__hint">
              Suggestions appear here once operators capture corrections in{' '}
              <Link className="table-link" to="/operator-corrections">
                Operator Corrections
              </Link>
              .
            </p>
          </div>
        ) : null}

        {suggestions.length > 0 ? (
          <div className="failed-jobs-list">
            {suggestions.map((suggestion: AutomationSuggestion) => (
              <article key={suggestion.id} className="failed-job-card">
                <div className="failed-job-card__header">
                  <div className="failed-job-card__title-row">
                    <h3 className="failed-job-card__title">
                      {suggestion.suggested_rule_json.title ?? 'Automation suggestion'}
                    </h3>
                    <time className="failed-job-card__time" dateTime={suggestion.created_at}>
                      {new Date(suggestion.created_at).toLocaleString()}
                    </time>
                  </div>
                  <div className="failed-job-card__meta">
                    <span className="failed-job-badge failed-job-badge--shop">
                      {suggestionTypeLabel(suggestion.suggested_rule_json.type)}
                    </span>
                    <span
                      className={`failed-job-badge ${suggestion.status === 'approved' ? 'failed-job-badge--warn' : suggestion.status === 'rejected' ? 'failed-job-badge--danger' : 'failed-job-badge--queue'}`}
                    >
                      {suggestion.status}
                    </span>
                  </div>
                </div>
                <div className="failed-job-card__error-panel">
                  <p className="failed-job-card__error">
                    {suggestion.suggested_rule_json.summary ?? 'No summary provided.'}
                  </p>
                </div>
                {suggestion.status === 'pending' ? (
                  <div className="failed-job-card__actions">
                    <button
                      type="button"
                      className="button button--primary"
                      disabled={actionsDisabled}
                      onClick={() => approveMutation.mutate(suggestion.id)}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="button button--ghost-dark"
                      disabled={actionsDisabled}
                      onClick={() => rejectMutation.mutate(suggestion.id)}
                    >
                      Reject
                    </button>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        ) : null}
      </section>
    </Page>
  );
}
