import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { Pagination } from '../components/Pagination';
import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input, Select } from '../components/ui';
import { EmptyState, LoadingState } from '../components/data';
import { useAuth } from '../contexts/AuthContext';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { cn } from '../lib/cn';
import { apiClient } from '../services/apiClient';
import type { FailedJob } from '../types/health';

function formatPayload(payload: Record<string, unknown>): string {
  return JSON.stringify(payload, null, 2);
}

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const diffMs = Date.now() - then;
  const minutes = Math.round(diffMs / 60000);
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

const STATUS_TONE: Record<FailedJob['status'], 'danger' | 'success' | 'neutral'> = {
  failed: 'danger',
  retried: 'success',
  ignored: 'neutral',
};

function JobCard({
  job,
  canManage,
  actionsBusy,
  onRetry,
  onIgnore,
}: {
  job: FailedJob;
  canManage: boolean;
  actionsBusy: boolean;
  onRetry: () => void;
  onIgnore: () => void;
}) {
  const resolved = job.status !== 'failed';
  const retriesExhausted = job.retry_count >= job.max_retries;

  return (
    <article className="rounded-lg border border-border bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="neutral">{job.queue_name}</Badge>
            <span className="font-mono text-xs text-muted">{job.job_type}</span>
          </div>
        </div>
        <Badge tone={STATUS_TONE[job.status]}>{job.status}</Badge>
      </div>

      <div className="mt-3 flex flex-wrap gap-4 text-xs text-muted">
        <span>
          <span className="font-medium text-subtle">Retries </span>
          <span className={cn(retriesExhausted && 'text-danger')}>
            {job.retry_count}/{job.max_retries}
            {retriesExhausted ? ' · exhausted' : ''}
          </span>
        </span>
        <span>
          <span className="font-medium text-subtle">Failed </span>
          <time dateTime={job.created_at} title={new Date(job.created_at).toLocaleString()}>
            {formatRelativeTime(job.created_at)}
          </time>
        </span>
      </div>

      {job.error_message ? (
        <div className="mt-3 rounded-md border border-danger/20 bg-danger-soft/30 px-3 py-2" role="note">
          <span className="text-xs font-semibold uppercase text-danger">Error</span>
          <p className="mt-1 text-sm text-fg">{job.error_message}</p>
        </div>
      ) : null}

      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-accent hover:underline">View redacted payload</summary>
        <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-surface-sunken p-3 text-xs text-subtle">
          {formatPayload(job.redacted_payload)}
        </pre>
      </details>

      {canManage ? (
        <div className="mt-3 flex gap-2">
          <Button type="button" size="sm" disabled={actionsBusy || resolved} onClick={onRetry}>
            Retry
          </Button>
          <Button type="button" variant="secondary" size="sm" disabled={actionsBusy || resolved} onClick={onIgnore}>
            Ignore
          </Button>
        </div>
      ) : null}
    </article>
  );
}

export function FailedJobsPage() {
  const { selectedShopId } = useShop();
  const { user } = useAuth();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('failed');
  const [queueFilter, setQueueFilter] = useState('');
  const [jobTypeFilter, setJobTypeFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [pendingAction, setPendingAction] = useState<{ type: 'retry' | 'ignore'; jobId: string } | null>(null);

  const canManage = user?.role === 'owner' || user?.role === 'admin';

  const filters = useMemo(
    () => ({
      page,
      status: statusFilter || undefined,
      queue_name: queueFilter || undefined,
      job_type: jobTypeFilter || undefined,
      date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
      date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
    }),
    [page, statusFilter, queueFilter, jobTypeFilter, dateFrom, dateTo],
  );

  const jobs = useQuery({
    queryKey: ['failed-jobs', selectedShopId, filters],
    queryFn: () => apiClient.listFailedJobs(selectedShopId, filters),
    enabled: Boolean(selectedShopId) && canManage,
  });

  const retry = useMutation({
    mutationFn: (jobId: string) => apiClient.retryFailedJob(selectedShopId, jobId),
    onSuccess: () => {
      showToast('Failed job requeued.', 'success');
      queryClient.invalidateQueries({ queryKey: ['failed-jobs', selectedShopId] });
      setPendingAction(null);
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Retry failed', 'error'),
  });

  const ignore = useMutation({
    mutationFn: (jobId: string) => apiClient.ignoreFailedJob(selectedShopId, jobId),
    onSuccess: () => {
      showToast('Failed job ignored.', 'success');
      queryClient.invalidateQueries({ queryKey: ['failed-jobs', selectedShopId] });
      setPendingAction(null);
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Ignore failed', 'error'),
  });

  const hasFilters = Boolean(queueFilter || jobTypeFilter || dateFrom || dateTo) || statusFilter !== 'failed';

  function clearFilters() {
    setPage(1);
    setStatusFilter('failed');
    setQueueFilter('');
    setJobTypeFilter('');
    setDateFrom('');
    setDateTo('');
  }

  const items = jobs.data?.items ?? [];
  const totalItems = jobs.data?.total ?? 0;
  const pageSize = jobs.data?.page_size ?? 20;
  const actionsBusy = retry.isPending || ignore.isPending;

  return (
    <HubPage
      eyebrow="Reliability"
      title="Failed jobs"
      description="Review dead-lettered worker jobs and safely retry or ignore them. Payloads are redacted by the API."
    >
      {!selectedShopId ? (
        <Card>
          <CardBody>
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          </CardBody>
        </Card>
      ) : null}

      {!canManage && selectedShopId ? (
        <Card>
          <CardBody>
            <EmptyState title="Admin access required" description="Only owners and admins can view failed jobs." />
          </CardBody>
        </Card>
      ) : null}

      {canManage && selectedShopId ? (
        <>
          <Card>
            <CardHeader title="Filters" />
            <CardBody className="flex flex-col gap-4">
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <Field label="Status">
                  <Select
                    value={statusFilter}
                    onChange={(e) => { setPage(1); setStatusFilter(e.target.value); }}
                  >
                    <option value="failed">Failed</option>
                    <option value="retried">Retried</option>
                    <option value="ignored">Ignored</option>
                  </Select>
                </Field>
                <Field label="Queue">
                  <Input value={queueFilter} onChange={(e) => setQueueFilter(e.target.value)} placeholder="queue name" />
                </Field>
                <Field label="Job type">
                  <Input value={jobTypeFilter} onChange={(e) => setJobTypeFilter(e.target.value)} placeholder="job type" />
                </Field>
                <Field label="From">
                  <Input type="datetime-local" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
                </Field>
                <Field label="To">
                  <Input type="datetime-local" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
                </Field>
              </div>
              {hasFilters ? (
                <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
                  Clear filters
                </Button>
              ) : null}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Results"
              description={
                !jobs.isLoading && !jobs.error
                  ? `${totalItems} ${totalItems === 1 ? 'job' : 'jobs'} matching “${statusFilter}”`
                  : undefined
              }
            />
            <CardBody className="flex flex-col gap-4">
              {jobs.isLoading ? <LoadingState label="Loading failed jobs…" /> : null}

              {jobs.error ? (
                <p className="text-sm text-danger">
                  {jobs.error instanceof Error ? jobs.error.message : 'Failed to load jobs'}
                </p>
              ) : null}

              {!jobs.isLoading && !jobs.error && items.length === 0 ? (
                <EmptyState
                  title={`No ${statusFilter} jobs found`}
                  description={hasFilters ? 'Try adjusting your filters.' : undefined}
                  action={
                    hasFilters ? (
                      <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
                        Reset filters
                      </Button>
                    ) : undefined
                  }
                />
              ) : null}

              {items.length > 0 ? (
                <div className="flex flex-col gap-3">
                  {items.map((job) => (
                    <JobCard
                      key={job.id}
                      job={job}
                      canManage={canManage}
                      actionsBusy={actionsBusy}
                      onRetry={() => setPendingAction({ type: 'retry', jobId: job.id })}
                      onIgnore={() => setPendingAction({ type: 'ignore', jobId: job.id })}
                    />
                  ))}
                </div>
              ) : null}

              <Pagination page={page} pageSize={pageSize} totalItems={totalItems} onPageChange={setPage} />
            </CardBody>
          </Card>
        </>
      ) : null}

      <ConfirmDialog
        open={pendingAction?.type === 'retry'}
        title="Retry failed job?"
        message="This will requeue the job for processing."
        confirmLabel="Retry"
        onConfirm={() => pendingAction && retry.mutate(pendingAction.jobId)}
        onCancel={() => setPendingAction(null)}
      />
      <ConfirmDialog
        open={pendingAction?.type === 'ignore'}
        title="Ignore failed job?"
        message="Ignored jobs will not be retried automatically."
        confirmLabel="Ignore"
        onConfirm={() => pendingAction && ignore.mutate(pendingAction.jobId)}
        onCancel={() => setPendingAction(null)}
      />
    </HubPage>
  );
}
