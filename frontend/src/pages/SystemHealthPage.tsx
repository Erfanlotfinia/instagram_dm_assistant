import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';

import { Pagination } from '../components/Pagination';
import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader } from '../components/ui';
import { EmptyState, KpiCard, LoadingState } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { cn } from '../lib/cn';
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

type ShopFilter = 'all' | 'unscoped' | string;

function shopLabel(shopId: string | null, shopsById: Map<string, string>): string {
  if (!shopId) return 'Unscoped';
  return shopsById.get(shopId) ?? shopId.slice(0, 8);
}

function formatJobType(jobType: string): string {
  return jobType.replace(/_/g, ' ');
}

function filterSummary(filter: ShopFilter, shopsById: Map<string, string>): string {
  if (filter === 'all') {
    return 'Showing failed jobs from all accessible shops, including unscoped worker payloads.';
  }
  if (filter === 'unscoped') {
    return 'Showing unscoped worker failures only (jobs without a shop assignment).';
  }
  const shopName = shopsById.get(filter);
  return shopName ? `Showing failed jobs for ${shopName} only.` : 'Showing failed jobs for the selected shop only.';
}

function statusTone(status: ReadinessResponse['status']): 'success' | 'warning' | 'danger' {
  if (status === 'ok') return 'success';
  if (status === 'degraded') return 'warning';
  return 'danger';
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
    <article className="rounded-lg border border-border bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-fg">{formatJobType(job.job_type)}</h3>
          <time className="text-xs text-muted" dateTime={job.created_at}>
            {new Date(job.created_at).toLocaleString()}
          </time>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Badge tone={job.shop_id ? 'info' : 'neutral'}>{label}</Badge>
          <Badge tone="neutral">{job.queue_name}</Badge>
          <Badge tone={retriesExhausted ? 'danger' : 'warning'}>
            {job.retry_count}/{job.max_retries} retries
          </Badge>
        </div>
      </div>

      <p className="mt-3 rounded-md border border-danger/20 bg-danger-soft/30 px-3 py-2 text-sm text-fg">
        {job.error_message ?? 'No error message recorded'}
      </p>

      {job.traceback ? (
        <div className="mt-3">
          <Button variant="ghost" size="sm" type="button" aria-expanded={showTrace} onClick={() => setShowTrace((c) => !c)}>
            {showTrace ? 'Hide traceback' : 'Show traceback'}
          </Button>
          {showTrace ? (
            <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-surface-sunken p-3 text-xs text-subtle">{job.traceback}</pre>
          ) : null}
        </div>
      ) : null}

      <div className="mt-3 flex gap-2">
        <Button type="button" size="sm" disabled={actionsDisabled} onClick={() => onRetry(job.id)}>
          Retry
        </Button>
        <Button type="button" variant="secondary" size="sm" disabled={actionsDisabled} onClick={() => onIgnore(job.id)}>
          Ignore
        </Button>
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
    if (!readiness.data) return { healthy: 0, total: 0 };
    const checks = Object.values(readiness.data.checks);
    return { healthy: checks.filter((s) => s === 'ok').length, total: checks.length };
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

  const platformStatus = readiness.data?.status;

  return (
    <HubPage
      eyebrow="Operations"
      title="System health"
      description="Dependency readiness, worker queue failures, and retry controls for pilot operations."
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <KpiCard
          label="Platform status"
          value={
            readiness.isLoading
              ? 'Checking…'
              : readiness.error
                ? 'Unavailable'
                : readiness.data
                  ? STATUS_LABELS[readiness.data.status]
                  : '—'
          }
          tone={platformStatus ? statusTone(platformStatus) : 'accent'}
          hint={platformStatus ? `Overall status: ${platformStatus}` : undefined}
        />
        <KpiCard
          label="Dependencies"
          value={readiness.isLoading ? 'Checking…' : readiness.data ? `${readinessStats.healthy}/${readinessStats.total} healthy` : '—'}
          tone={readinessStats.healthy === readinessStats.total ? 'success' : 'warning'}
        />
        <KpiCard
          label="Failed jobs"
          value={failedJobs.isLoading ? 'Loading…' : jobStats.total > 0 ? `${jobStats.total} waiting` : 'Queue clear'}
          tone={jobStats.total > 0 ? 'danger' : 'success'}
          hint={jobStats.total > 0 ? 'Requires retry or ignore' : undefined}
        />
      </div>

      <Card>
        <CardHeader title="Platform readiness" description="Live dependency checks refreshed every 30 seconds." />
        <CardBody>
          {readiness.isLoading ? <LoadingState label="Checking dependencies…" /> : null}
          {readiness.error ? (
            <p className="text-sm text-danger">
              {readiness.error instanceof Error ? readiness.error.message : 'Failed to load readiness'}
            </p>
          ) : null}

          {readiness.data ? (
            <>
              <div
                className={cn(
                  'mb-4 flex items-center gap-3 rounded-lg border px-4 py-3',
                  platformStatus === 'ok' && 'border-success/30 bg-success-soft/40',
                  platformStatus === 'degraded' && 'border-warning/30 bg-warning-soft/40',
                  platformStatus === 'failed' && 'border-danger/30 bg-danger-soft/40',
                )}
              >
                <span
                  className={cn(
                    'h-2.5 w-2.5 rounded-full',
                    platformStatus === 'ok' && 'bg-success',
                    platformStatus === 'degraded' && 'bg-warning',
                    platformStatus === 'failed' && 'bg-danger',
                  )}
                  aria-hidden="true"
                />
                <div>
                  <p className="text-sm font-medium text-fg">{STATUS_LABELS[readiness.data.status]}</p>
                  <p className="text-xs text-muted">
                    {readinessStats.healthy} of {readinessStats.total} dependencies reporting OK
                  </p>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {(Object.entries(readiness.data.checks) as [keyof ReadinessResponse['checks'], ReadinessCheckStatus][]).map(
                  ([name, status]) => (
                    <div
                      key={name}
                      className={cn(
                        'flex items-center gap-3 rounded-lg border px-3 py-2.5',
                        status === 'ok' ? 'border-success/20 bg-success-soft/20' : 'border-danger/20 bg-danger-soft/20',
                      )}
                    >
                      <span
                        className={cn('h-2 w-2 rounded-full', status === 'ok' ? 'bg-success' : 'bg-danger')}
                        aria-hidden="true"
                      />
                      <div>
                        <p className="text-sm font-medium text-fg">{CHECK_LABELS[name]}</p>
                        <p className={cn('text-xs uppercase', status === 'ok' ? 'text-success' : 'text-danger')}>{status}</p>
                      </div>
                    </div>
                  ),
                )}
              </div>
            </>
          ) : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Failed jobs"
          description="Queue failures across all shops you can access, including unscoped worker payloads."
        />
        <CardBody className="flex flex-col gap-4">
          {failedJobs.isLoading ? <LoadingState label="Loading failed jobs…" /> : null}
          {failedJobs.error ? (
            <p className="text-sm text-danger">
              {failedJobs.error instanceof Error ? failedJobs.error.message : 'Failed to load jobs'}
            </p>
          ) : null}

          {!failedJobs.isLoading && !failedJobs.error && failedJobs.data ? (
            <>
              <div className="flex flex-col gap-2">
                <span className="text-xs font-medium text-muted">Filter by shop</span>
                <div className="flex flex-wrap gap-2" role="group" aria-label="Shop filter">
                  <Chip active={shopFilter === 'all'} onClick={() => applyShopFilter('all')}>All shops</Chip>
                  <Chip active={shopFilter === 'unscoped'} onClick={() => applyShopFilter('unscoped')}>Unscoped</Chip>
                  {shops.map((shop) => (
                    <Chip key={shop.id} active={shopFilter === shop.id} onClick={() => applyShopFilter(shop.id)}>
                      {shop.name}
                    </Chip>
                  ))}
                </div>
                <p className="text-xs text-muted">{filterSummary(shopFilter, shopsById)}</p>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <KpiCard label="On this page" value={failedJobs.data.items.length} />
                <KpiCard label="Shop-scoped" value={jobStats.shopScoped} />
                <KpiCard label="Unscoped" value={jobStats.unscoped} />
              </div>
            </>
          ) : null}

          {failedJobs.data?.items.length ? (
            <div className="flex flex-col gap-3">
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
            <EmptyState
              title="No failed jobs are waiting for action"
              description="When workers exhaust retries, failed payloads appear here with retry and ignore controls."
            />
          ) : null}

          {failedJobs.data ? (
            <Pagination
              page={page}
              pageSize={failedJobs.data.page_size}
              totalItems={failedJobs.data.total}
              onPageChange={setPage}
            />
          ) : null}
        </CardBody>
      </Card>
    </HubPage>
  );
}
