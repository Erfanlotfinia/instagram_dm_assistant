import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { ShopSelector } from '../components/ShopSelector';
import { useAuth } from '../contexts/AuthContext';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';

function formatPayload(payload: Record<string, unknown>): string {
  return JSON.stringify(payload, null, 2);
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

  const totalPages = jobs.data ? Math.max(1, Math.ceil(jobs.data.total / jobs.data.page_size)) : 1;

  return (
    <div className="page-stack">
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

      <section className="dashboard-card dashboard-card--wide">
        {!selectedShopId ? <p className="empty-state">Select a shop to view failed jobs.</p> : null}
        {!canManage && selectedShopId ? (
          <p className="empty-state">Admin access is required to view failed jobs.</p>
        ) : null}
        {canManage ? (
          <div className="analytics-toolbar failed-jobs-toolbar">
            <label className="form-field">
              Status
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="failed">Failed</option>
                <option value="retried">Retried</option>
                <option value="ignored">Ignored</option>
              </select>
            </label>
            <label className="form-field">
              Queue
              <input value={queueFilter} onChange={(e) => setQueueFilter(e.target.value)} placeholder="queue name" />
            </label>
            <label className="form-field">
              Job type
              <input value={jobTypeFilter} onChange={(e) => setJobTypeFilter(e.target.value)} placeholder="job type" />
            </label>
            <label className="form-field">
              From
              <input type="datetime-local" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
            </label>
            <label className="form-field">
              To
              <input type="datetime-local" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
            </label>
          </div>
        ) : null}
        {jobs.isLoading ? <p className="empty-state">Loading failed jobs…</p> : null}
        {jobs.error ? (
          <p className="form-error">{jobs.error instanceof Error ? jobs.error.message : 'Failed to load jobs'}</p>
        ) : null}
        {!jobs.isLoading && !jobs.error && canManage && (jobs.data?.items.length ?? 0) === 0 ? (
          <p className="empty-state">No unresolved failed jobs.</p>
        ) : null}

        {(jobs.data?.items.length ?? 0) > 0 ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Queue</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Retries</th>
                  <th>Error</th>
                  <th>Redacted payload</th>
                  {canManage ? <th>Actions</th> : null}
                </tr>
              </thead>
              <tbody>
                {jobs.data?.items.map((job) => (
                  <tr key={job.id}>
                    <td>{job.queue_name}</td>
                    <td>{job.job_type}</td>
                    <td>{job.status}</td>
                    <td>
                      {job.retry_count}/{job.max_retries}
                    </td>
                    <td>{job.error_message || '—'}</td>
                    <td>
                      <details>
                        <summary>View redacted payload</summary>
                        <pre className="code-block">{formatPayload(job.redacted_payload)}</pre>
                      </details>
                    </td>
                    {canManage ? (
                      <td>
                        <div className="button-row">
                          <button
                            className="button button--primary"
                            type="button"
                            disabled={retry.isPending || job.status !== 'failed'}
                            onClick={() => setPendingAction({ type: 'retry', jobId: job.id })}
                          >
                            Retry
                          </button>
                          <button
                            className="button button--ghost-dark"
                            type="button"
                            disabled={ignore.isPending || job.status !== 'failed'}
                            onClick={() => setPendingAction({ type: 'ignore', jobId: job.id })}
                          >
                            Ignore
                          </button>
                        </div>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}

        {jobs.data && jobs.data.total > jobs.data.page_size ? (
          <div className="button-row">
            <button className="button button--ghost-dark" type="button" disabled={page <= 1} onClick={() => setPage((v) => Math.max(1, v - 1))}>
              Previous
            </button>
            <span>
              Page {page} of {totalPages}
            </span>
            <button className="button button--ghost-dark" type="button" disabled={page >= totalPages} onClick={() => setPage((v) => v + 1)}>
              Next
            </button>
          </div>
        ) : null}
      </section>

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
