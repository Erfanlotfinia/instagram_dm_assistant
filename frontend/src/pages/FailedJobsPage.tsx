import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';

function formatPayload(payload: Record<string, unknown>): string {
  return JSON.stringify(payload, null, 2);
}

export function FailedJobsPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);

  const jobs = useQuery({
    queryKey: ['failed-jobs', selectedShopId, page],
    queryFn: () => apiClient.listFailedJobs(selectedShopId, page),
    enabled: Boolean(selectedShopId),
  });

  const retry = useMutation({
    mutationFn: (jobId: string) => apiClient.retryFailedJob(selectedShopId, jobId),
    onSuccess: () => {
      showToast('Failed job requeued.', 'success');
      queryClient.invalidateQueries({ queryKey: ['failed-jobs', selectedShopId] });
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Retry failed', 'error'),
  });

  const ignore = useMutation({
    mutationFn: (jobId: string) => apiClient.ignoreFailedJob(selectedShopId, jobId),
    onSuccess: () => {
      showToast('Failed job ignored.', 'success');
      queryClient.invalidateQueries({ queryKey: ['failed-jobs', selectedShopId] });
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
            Review dead-lettered worker jobs and safely retry or ignore them. Payloads are masked by the API.
          </p>
        </div>
        <ShopSelector />
      </div>

      <section className="dashboard-card dashboard-card--wide">
        {!selectedShopId ? <p className="empty-state">Select a shop to view failed jobs.</p> : null}
        {jobs.isLoading ? <p className="empty-state">Loading failed jobs…</p> : null}
        {jobs.error ? (
          <p className="form-error">{jobs.error instanceof Error ? jobs.error.message : 'Failed to load jobs'}</p>
        ) : null}
        {!jobs.isLoading && !jobs.error && (jobs.data?.items.length ?? 0) === 0 ? (
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
                  <th>Payload</th>
                  <th>Actions</th>
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
                        <summary>View masked payload</summary>
                        <pre className="code-block">{formatPayload(job.payload)}</pre>
                      </details>
                    </td>
                    <td>
                      <div className="button-row">
                        <button
                          className="button button--primary"
                          type="button"
                          disabled={retry.isPending || job.status !== 'failed'}
                          onClick={() => retry.mutate(job.id)}
                        >
                          Retry
                        </button>
                        <button
                          className="button button--ghost-dark"
                          type="button"
                          disabled={ignore.isPending || job.status !== 'failed'}
                          onClick={() => ignore.mutate(job.id)}
                        >
                          Ignore
                        </button>
                      </div>
                    </td>
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
    </div>
  );
}
