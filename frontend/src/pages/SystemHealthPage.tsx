import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { Pagination } from '../components/Pagination';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import type { FailedJob, ReadinessCheckStatus, ReadinessResponse } from '../types/health';

const CHECK_LABELS: Record<keyof ReadinessResponse['checks'], string> = {
  postgres: 'PostgreSQL',
  redis: 'Redis',
  rabbitmq: 'RabbitMQ',
  qdrant: 'Qdrant',
  openai_config: 'OpenAI config',
};

const STATUS_LABELS: Record<ReadinessResponse['status'], string> = {
  ok: 'All systems operational',
  degraded: 'Degraded performance',
  failed: 'Critical failures detected',
};

function statusClass(status: ReadinessCheckStatus): string {
  return status === 'ok' ? 'health-check__status health-check__status--ok' : 'health-check__status health-check__status--error';
}

function shopLabel(shopId: string | null, shopsById: Map<string, string>): string {
  if (!shopId) {
    return 'Unscoped';
  }
  return shopsById.get(shopId) ?? shopId.slice(0, 8);
}

function shopBadgeClass(shopId: string | null): string {
  return shopId
    ? 'failed-job-badge failed-job-badge--shop'
    : 'failed-job-badge failed-job-badge--unscoped';
}

function formatJobType(jobType: string): string {
  return jobType.replace(/_/g, ' ');
}

type ShopFilter = 'all' | 'unscoped' | string;

function filterSummary(filter: ShopFilter, shopsById: Map<string, string>): string {
  if (filter === 'all') {
    return 'Showing failed jobs from all accessible shops, including unscoped worker payloads.';
  }
  if (filter === 'unscoped') {
    return 'Showing unscoped worker failures only (jobs without a shop assignment).';
  }
  const shopName = shopsById.get(filter);
  return shopName
    ? `Showing failed jobs for ${shopName} only.`
    : 'Showing failed jobs for the selected shop only.';
}

function FailedJobCard({
  job,
  shopsById,
  onRetry,
  onIgnore,
  actionsDisabled,
}: {
  job: FailedJob;
  shopsById: Map<string, string>;
  onRetry: (jobId: string) => void;
  onIgnore: (jobId: string) => void;
  actionsDisabled: boolean;
}) {
  const [showTrace, setShowTrace] = useState(false);
  const label = shopLabel(job.shop_id, shopsById);
  const retriesExhausted = job.retry_count >= job.max_retries;

  return (
    <article className="failed-job-card">
      <div className="failed-job-card__header">
        <div className="failed-job-card__title-row">
          <h3 className="failed-job-card__title">{formatJobType(job.job_type)}</h3>
          <time className="failed-job-card__time" dateTime={job.created_at}>
            {new Date(job.created_at).toLocaleString()}
          </time>
        </div>
        <div className="failed-job-card__meta">
          <span className={shopBadgeClass(job.shop_id)}>{label}</span>
          <span className="failed-job-badge failed-job-badge--queue">{job.queue_name}</span>
          <span
            className={`failed-job-badge${retriesExhausted ? ' failed-job-badge--danger' : ' failed-job-badge--warn'}`}
          >
            {job.retry_count}/{job.max_retries} retries
          </span>
        </div>
      </div>

      <div className="failed-job-card__error-panel">
        <p className="failed-job-card__error">{job.error_message ?? 'No error message recorded'}</p>
      </div>

      {job.traceback ? (
        <div className="failed-job-card__trace-section">
          <button
            type="button"
            className="failed-job-card__trace-toggle"
            aria-expanded={showTrace}
            onClick={() => setShowTrace((current) => !current)}
          >
            {showTrace ? 'Hide traceback' : 'Show traceback'}
          </button>
          {showTrace ? <pre className="failed-job-card__trace">{job.traceback}</pre> : null}
        </div>
      ) : null}

      <div className="failed-job-card__actions">
        <button
          type="button"
          className="button button--primary"
          disabled={actionsDisabled}
          onClick={() => onRetry(job.id)}
        >
          Retry
        </button>
        <button
          type="button"
          className="button button--ghost-dark"
          disabled={actionsDisabled}
          onClick={() => onIgnore(job.id)}
        >
          Ignore
        </button>
      </div>
    </article>
  );
}

export function SystemHealthPage() {
  const { shops } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [shopFilter, setShopFilter] = useState<ShopFilter>('all');
  const shopsById = new Map(shops.map((shop) => [shop.id, shop.name]));

  const readiness = useQuery({
    queryKey: ['readiness'],
    queryFn: () => apiClient.getReady(),
    refetchInterval: 30_000,
  });

  const failedJobs = useQuery({
    queryKey: ['failed-jobs-accessible', page, shopFilter],
    queryFn: () =>
      apiClient.listAccessibleFailedJobs({
        shopId: shopFilter !== 'all' && shopFilter !== 'unscoped' ? shopFilter : undefined,
        unscopedOnly: shopFilter === 'unscoped',
        page,
      }),
  });

  const retryMutation = useMutation({
    mutationFn: (jobId: string) => apiClient.retryFailedJobById(jobId),
    onSuccess: () => {
      showToast('Failed job requeued', 'success');
      void queryClient.invalidateQueries({ queryKey: ['failed-jobs-accessible'] });
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const ignoreMutation = useMutation({
    mutationFn: (jobId: string) => apiClient.ignoreFailedJobById(jobId),
    onSuccess: () => {
      showToast('Failed job ignored', 'success');
      void queryClient.invalidateQueries({ queryKey: ['failed-jobs-accessible'] });
    },
    onError: (error: Error) => showToast(error.message, 'error'),
  });

  const readinessStats = useMemo(() => {
    if (!readiness.data) {
      return { healthy: 0, total: 0 };
    }
    const checks = Object.values(readiness.data.checks);
    return {
      healthy: checks.filter((status) => status === 'ok').length,
      total: checks.length,
    };
  }, [readiness.data]);

  const jobStats = useMemo(() => {
    const items = failedJobs.data?.items ?? [];
    return {
      total: failedJobs.data?.total ?? 0,
      unscoped: items.filter((job) => job.shop_id === null).length,
      shopScoped: items.filter((job) => job.shop_id !== null).length,
    };
  }, [failedJobs.data]);

  const actionsDisabled = retryMutation.isPending || ignoreMutation.isPending;

  function applyShopFilter(nextFilter: ShopFilter) {
    setShopFilter(nextFilter);
    setPage(1);
  }

  return (
    <div className="page-stack page-stack--wide system-health-page">
      <section className="dashboard-card dashboard-card--wide system-health-hero">
        <div className="system-health-hero__intro">
          <p className="dashboard-card__eyebrow">Operations</p>
          <h1>System health</h1>
          <p className="system-health-hero__description">
            Dependency readiness, worker queue failures, and retry controls for pilot operations.
          </p>
        </div>

        <div className="system-health-kpis">
          <article
            className={`system-health-kpi system-health-kpi--${readiness.data?.status ?? 'loading'}`}
          >
            <p className="system-health-kpi__label">Platform status</p>
            {readiness.isLoading ? (
              <p className="system-health-kpi__value">Checking…</p>
            ) : readiness.error ? (
              <p className="system-health-kpi__value system-health-kpi__value--error">Unavailable</p>
            ) : readiness.data ? (
              <>
                <p className="system-health-kpi__value">{STATUS_LABELS[readiness.data.status]}</p>
                <p className={`health-overall health-overall--${readiness.data.status}`}>
                  Overall status: {readiness.data.status}
                </p>
              </>
            ) : null}
          </article>

          <article className="system-health-kpi">
            <p className="system-health-kpi__label">Dependencies</p>
            {readiness.isLoading ? (
              <p className="system-health-kpi__value">Checking…</p>
            ) : readiness.data ? (
              <p className="system-health-kpi__value">
                {readinessStats.healthy}/{readinessStats.total} healthy
              </p>
            ) : (
              <p className="system-health-kpi__value">—</p>
            )}
          </article>

          <article
            className={`system-health-kpi${jobStats.total > 0 ? ' system-health-kpi--alert' : ' system-health-kpi--clear'}`}
          >
            <p className="system-health-kpi__label">Failed jobs</p>
            {failedJobs.isLoading ? (
              <p className="system-health-kpi__value">Loading…</p>
            ) : (
              <>
                <p className="system-health-kpi__value">
                  {jobStats.total > 0 ? `${jobStats.total} waiting` : 'Queue clear'}
                </p>
                {jobStats.total > 0 ? (
                  <p className="system-health-kpi__hint">Requires retry or ignore</p>
                ) : null}
              </>
            )}
          </article>
        </div>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header">
          <div>
            <h2>Platform readiness</h2>
            <p className="section-header__subtitle">Live dependency checks refreshed every 30 seconds.</p>
          </div>
        </div>

        {readiness.isLoading ? <p className="loading-state">Checking dependencies...</p> : null}
        {readiness.error ? (
          <p className="form-error">
            {readiness.error instanceof Error ? readiness.error.message : 'Failed to load readiness'}
          </p>
        ) : null}

        {readiness.data ? (
          <>
            <div className={`health-status-banner health-status-banner--${readiness.data.status}`}>
              <div className="health-status-banner__indicator" aria-hidden="true" />
              <div>
                <p className="health-status-banner__title">{STATUS_LABELS[readiness.data.status]}</p>
                <p className="health-status-banner__meta">
                  {readinessStats.healthy} of {readinessStats.total} dependencies reporting OK
                </p>
              </div>
            </div>

            <div className="health-checks-grid">
              {(Object.entries(readiness.data.checks) as [keyof ReadinessResponse['checks'], ReadinessCheckStatus][]).map(
                ([name, status]) => (
                  <article
                    key={name}
                    className={`health-check health-check--${status}`}
                  >
                    <span className="health-check__dot" aria-hidden="true" />
                    <div className="health-check__body">
                      <p className="health-check__name">{CHECK_LABELS[name]}</p>
                      <p className={statusClass(status)}>{status}</p>
                    </div>
                  </article>
                ),
              )}
            </div>
          </>
        ) : null}
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header">
          <div>
            <h2>Failed jobs</h2>
            <p className="section-header__subtitle">
              Queue failures across all shops you can access, including unscoped worker payloads.
            </p>
          </div>
        </div>

        {failedJobs.isLoading ? <p className="loading-state">Loading failed jobs...</p> : null}
        {failedJobs.error ? (
          <p className="form-error">
            {failedJobs.error instanceof Error ? failedJobs.error.message : 'Failed to load jobs'}
          </p>
        ) : null}

        {!failedJobs.isLoading && !failedJobs.error && failedJobs.data ? (
          <>
            <div className="analytics-toolbar failed-jobs-toolbar">
              <div className="form-field failed-jobs-toolbar__filters">
                <span>Filter by shop</span>
                <div className="filter-chips analytics-toolbar__chips" role="group" aria-label="Shop filter">
                  <button
                    type="button"
                    className={`filter-chip${shopFilter === 'all' ? ' filter-chip--active' : ''}`}
                    aria-pressed={shopFilter === 'all'}
                    onClick={() => applyShopFilter('all')}
                  >
                    All shops
                  </button>
                  <button
                    type="button"
                    className={`filter-chip${shopFilter === 'unscoped' ? ' filter-chip--active' : ''}`}
                    aria-pressed={shopFilter === 'unscoped'}
                    onClick={() => applyShopFilter('unscoped')}
                  >
                    Unscoped
                  </button>
                  {shops.map((shop) => (
                    <button
                      key={shop.id}
                      type="button"
                      className={`filter-chip${shopFilter === shop.id ? ' filter-chip--active' : ''}`}
                      aria-pressed={shopFilter === shop.id}
                      onClick={() => applyShopFilter(shop.id)}
                    >
                      {shop.name}
                    </button>
                  ))}
                </div>
              </div>
              <p className="analytics-toolbar__summary">{filterSummary(shopFilter, shopsById)}</p>
            </div>

            <div className="failed-jobs-stats">
              <article className="failed-jobs-stat">
                <p className="failed-jobs-stat__label">On this page</p>
                <p className="failed-jobs-stat__value">{failedJobs.data.items.length}</p>
              </article>
              <article className="failed-jobs-stat">
                <p className="failed-jobs-stat__label">Shop-scoped</p>
                <p className="failed-jobs-stat__value">{jobStats.shopScoped}</p>
              </article>
              <article className="failed-jobs-stat">
                <p className="failed-jobs-stat__label">Unscoped</p>
                <p className="failed-jobs-stat__value">{jobStats.unscoped}</p>
              </article>
            </div>
          </>
        ) : null}

        {failedJobs.data?.items.length ? (
          <div className="failed-jobs-list">
            {failedJobs.data.items.map((job) => (
              <FailedJobCard
                key={job.id}
                job={job}
                shopsById={shopsById}
                actionsDisabled={actionsDisabled}
                onRetry={(jobId) => retryMutation.mutate(jobId)}
                onIgnore={(jobId) => ignoreMutation.mutate(jobId)}
              />
            ))}
          </div>
        ) : null}

        {!failedJobs.isLoading && !failedJobs.error && (failedJobs.data?.items.length ?? 0) === 0 ? (
          <div className="empty-state-panel system-health-empty">
            <div className="system-health-empty__icon" aria-hidden="true">✓</div>
            <p className="empty-state-panel__title">No failed jobs are waiting for action</p>
            <p className="empty-state-panel__hint">
              When workers exhaust retries, failed payloads appear here with retry and ignore controls.
            </p>
          </div>
        ) : null}

        {failedJobs.data ? (
          <Pagination
            page={page}
            pageSize={failedJobs.data.page_size}
            totalItems={failedJobs.data.total}
            onPageChange={setPage}
          />
        ) : null}
      </section>
    </div>
  );
}
