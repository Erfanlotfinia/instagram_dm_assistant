import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { ShopSelector } from '../components/ShopSelector';
import { useAuth } from '../contexts/AuthContext';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import type { FailedJob } from '../types/health';

function formatPayload(payload: Record<string, unknown>): string {
  return JSON.stringify(payload, null, 2);
}

const STATUS_TONE: Record<FailedJob['status'], string> = {
  failed: 'status-pill--danger',
  retried: 'status-pill--success',
  ignored: 'status-pill--neutral',
};

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) {
    return iso;
  }
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

interface JobCardProps {
  job: FailedJob;
  canManage: boolean;
  actionsBusy: boolean;
  onRetry: () => void;
  onIgnore: () => void;
}

function JobCard({ job, canManage, actionsBusy, onRetry, onIgnore }: JobCardProps) {
  const resolved = job.status !== 'failed';
  const retriesExhausted = job.retry_count >= job.max_retries;

  return (
    <article className="job-card">
      <div className="job-card__head">
        <div className="job-card__identity">
          <span className="job-card__queue">{job.queue_name}</span>
          <span className="job-card__type">{job.job_type}</span>
        </div>
        <span className={`status-pill ${STATUS_TONE[job.status] ?? 'status-pill--neutral'}`}>
          {job.status}
        </span>
      </div>

      <div className="job-card__meta">
        <span className="job-card__meta-item">
          <span className="job-card__meta-label">Retries</span>
          <span className={retriesExhausted ? 'job-card__meta-value job-card__meta-value--alert' : 'job-card__meta-value'}>
            {job.retry_count}/{job.max_retries}
            {retriesExhausted ? ' · exhausted' : ''}
          </span>
        </span>
        <span className="job-card__meta-item">
          <span className="job-card__meta-label">Failed</span>
          <time className="job-card__meta-value" dateTime={job.created_at} title={new Date(job.created_at).toLocaleString()}>
            {formatRelativeTime(job.created_at)}
          </time>
        </span>
      </div>

      {job.error_message ? (
        <div className="job-card__error" role="note">
          <span className="job-card__error-label">Error</span>
          <p className="job-card__error-text">{job.error_message}</p>
        </div>
      ) : null}

      <details className="job-card__payload">
        <summary>View redacted payload</summary>
        <pre className="code-block">{formatPayload(job.redacted_payload)}</pre>
      </details>

      {canManage ? (
        <div className="job-card__actions">
          <button
            className="button button--primary"
            type="button"
            disabled={actionsBusy || resolved}
            onClick={onRetry}
          >
            Retry
          </button>
          <button
            className="button button--ghost-dark"
            type="button"
            disabled={actionsBusy || resolved}
            onClick={onIgnore}
          >
            Ignore
          </button>
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
  const totalPages = jobs.data ? Math.max(1, Math.ceil(jobs.data.total / jobs.data.page_size)) : 1;
  const actionsBusy = retry.isPending || ignore.isPending;

  return (
    <div className="page-stack page-stack--wide failed-jobs">
      <div className="page-header">
        <div>
          <p className="dashboard-card__eyebrow">Reliability</p>
          <h1>Failed jobs</h1>
          <p className="dashboard-card__subtitle">
            Review dead-lettered worker jobs and safely retry or ignore them. Payloads are redacted by the API.
          </p>
        </div>
        <ShopSelector />
      </div>

      {!selectedShopId ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="empty-state">Select a shop to view failed jobs.</p>
        </section>
      ) : null}

      {!canManage && selectedShopId ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="empty-state">Admin access is required to view failed jobs.</p>
        </section>
      ) : null}

      {canManage && selectedShopId ? (
        <>
          <section className="dashboard-card dashboard-card--wide failed-jobs__filters">
            <div className="failed-jobs__filter-grid">
              <label className="form-field">
                <span>Status</span>
                <select
                  value={statusFilter}
                  onChange={(e) => {
                    setPage(1);
                    setStatusFilter(e.target.value);
                  }}
                >
                  <option value="failed">Failed</option>
                  <option value="retried">Retried</option>
                  <option value="ignored">Ignored</option>
                </select>
              </label>
              <label className="form-field">
                <span>Queue</span>
                <input value={queueFilter} onChange={(e) => setQueueFilter(e.target.value)} placeholder="queue name" />
              </label>
              <label className="form-field">
                <span>Job type</span>
                <input value={jobTypeFilter} onChange={(e) => setJobTypeFilter(e.target.value)} placeholder="job type" />
              </label>
              <div className="failed-jobs__date-range">
                <label className="form-field">
                  <span>From</span>
                  <input type="datetime-local" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
                </label>
                <label className="form-field">
                  <span>To</span>
                  <input type="datetime-local" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
                </label>
              </div>
            </div>
            {hasFilters ? (
              <button className="button button--ghost-dark" type="button" onClick={clearFilters}>
                Clear filters
              </button>
            ) : null}
          </section>

          <section className="dashboard-card dashboard-card--wide failed-jobs__results">
            {!jobs.isLoading && !jobs.error ? (
              <div className="failed-jobs__summary">
                <span className="failed-jobs__count">{jobs.data?.total ?? 0}</span>
                <span className="failed-jobs__count-label">
                  {(jobs.data?.total ?? 0) === 1 ? 'job' : 'jobs'} matching “{statusFilter}”
                </span>
              </div>
            ) : null}

            {jobs.isLoading ? (
              <div className="failed-jobs__list" aria-busy="true">
                {[0, 1, 2].map((key) => (
                  <article className="job-card job-card--skeleton" key={key}>
                    <div className="skeleton-line skeleton-line--title" />
                    <div className="skeleton-line skeleton-line--short" />
                    <div className="skeleton-line" />
                  </article>
                ))}
              </div>
            ) : null}

            {jobs.error ? (
              <p className="form-error">
                {jobs.error instanceof Error ? jobs.error.message : 'Failed to load jobs'}
              </p>
            ) : null}

            {!jobs.isLoading && !jobs.error && items.length === 0 ? (
              <div className="failed-jobs__empty">
                <p className="empty-state">No {statusFilter} jobs found.</p>
                {hasFilters ? (
                  <button className="button button--ghost-dark" type="button" onClick={clearFilters}>
                    Reset filters
                  </button>
                ) : null}
              </div>
            ) : null}

            {items.length > 0 ? (
              <div className="failed-jobs__list">
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

            {jobs.data && jobs.data.total > jobs.data.page_size ? (
              <div className="failed-jobs__pagination">
                <button
                  className="button button--ghost-dark"
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((v) => Math.max(1, v - 1))}
                >
                  Previous
                </button>
                <span className="failed-jobs__page-indicator">
                  Page {page} of {totalPages}
                </span>
                <button
                  className="button button--ghost-dark"
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((v) => v + 1)}
                >
                  Next
                </button>
              </div>
            ) : null}
          </section>
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
    </div>
  );
}
