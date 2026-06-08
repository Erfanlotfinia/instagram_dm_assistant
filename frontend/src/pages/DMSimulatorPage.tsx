import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import type { DMSimulatorResponse } from '../types/competitive';

const EXAMPLE_MESSAGES = [
  {
    label: 'Persian order (black L)',
    text: 'این کارو مشکی سایز L می‌خوام',
  },
  {
    label: 'Price question',
    text: 'قیمت این لباس چنده؟',
  },
  {
    label: 'English size check',
    text: 'Do you have this hoodie in medium?',
  },
  {
    label: 'Payment follow-up',
    text: 'پرداخت کردم، رسید رو فرستادم',
  },
] as const;

function SimulationResultPanel({ result }: { result: DMSimulatorResponse }) {
  const autoSendAllowed = Boolean(result.auto_send_decision?.auto_send_allowed);
  const requiresPreview = Boolean(result.auto_send_decision?.requires_preview);
  const requiresHandoff = Boolean(result.auto_send_decision?.requires_handoff);

  async function copyReply() {
    if (!result.suggested_reply) {
      return;
    }
    await navigator.clipboard.writeText(result.suggested_reply);
  }

  return (
    <section className="dashboard-card dashboard-card--wide">
      <div className="section-header">
        <h2>Simulation result</h2>
        <span className="priority-badge priority-badge--medium">Simulation</span>
      </div>

      <div className="stats-grid">
        <article className="stat-card">
          <p className="stat-card__label">Intent</p>
          <p className="stat-card__value">{result.intent ?? '—'}</p>
        </article>
        <article className="stat-card">
          <p className="stat-card__label">Next state</p>
          <p className="stat-card__value">{result.next_state}</p>
        </article>
        <article className="stat-card">
          <p className="stat-card__label">Preview</p>
          <p className="stat-card__value">{requiresPreview ? 'Required' : 'No'}</p>
        </article>
        <article className="stat-card">
          <p className="stat-card__label">Handoff</p>
          <p className="stat-card__value">{requiresHandoff || result.handoff_reason ? 'Yes' : 'No'}</p>
        </article>
      </div>

      <dl className="detail-grid">
        <div>
          <dt>Conversation ID</dt>
          <dd>{result.conversation_id}</dd>
        </div>
        <div>
          <dt>Message ID</dt>
          <dd>{result.message_id}</dd>
        </div>
        <div>
          <dt>Auto-send allowed</dt>
          <dd>{autoSendAllowed ? 'Yes' : 'No'}</dd>
        </div>
        {result.handoff_reason ? (
          <div>
            <dt>Handoff reason</dt>
            <dd>{result.handoff_reason}</dd>
          </div>
        ) : null}
      </dl>

      <div className="match-panel">
        <div className="section-header">
          <h3>Suggested reply</h3>
          {result.suggested_reply ? (
            <button className="button button--ghost-dark" type="button" onClick={() => void copyReply()}>
              Copy reply
            </button>
          ) : null}
        </div>
        <p className={result.suggested_reply ? 'simulator-reply' : 'empty-state'}>
          {result.suggested_reply ?? 'No reply generated'}
        </p>
      </div>

      {result.draft_order ? (
        <div className="match-panel">
          <h3>Draft order</h3>
          <pre className="resolver-raw-json">{JSON.stringify(result.draft_order, null, 2)}</pre>
        </div>
      ) : null}

      <div className="button-row">
        <Link className="button button--ghost-dark" to={`/conversations/${result.conversation_id}`}>
          Open simulation conversation
        </Link>
      </div>

      <details className="match-panel resolver-raw-details">
        <summary>Decision trace & resolution details</summary>
        <pre className="resolver-raw-json">
          {JSON.stringify(
            {
              decision_trace: result.decision_trace,
              slots: result.extracted_slots,
              product: result.product_resolution,
              variant: result.variant_resolution,
              inventory: result.inventory_result,
              auto_send_decision: result.auto_send_decision,
            },
            null,
            2,
          )}
        </pre>
      </details>
    </section>
  );
}

export function DMSimulatorPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const [instagramAccountId, setInstagramAccountId] = useState('');
  const [messageText, setMessageText] = useState<string>(EXAMPLE_MESSAGES[0].text);
  const [postUrl, setPostUrl] = useState('');
  const [resetDialogOpen, setResetDialogOpen] = useState(false);

  const accountsQuery = useQuery({
    queryKey: ['instagram-accounts', selectedShopId],
    queryFn: () => apiClient.listInstagramAccounts(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const runsQuery = useQuery({
    queryKey: ['simulator-runs', selectedShopId],
    queryFn: () => apiClient.listSimulatorRuns(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  useEffect(() => {
    if (!instagramAccountId && accountsQuery.data?.length) {
      setInstagramAccountId(accountsQuery.data[0].id);
    }
  }, [accountsQuery.data, instagramAccountId]);

  const runMutation = useMutation({
    mutationFn: () =>
      apiClient.runDMSimulator(selectedShopId, {
        instagram_account_id: instagramAccountId || accountsQuery.data?.[0]?.id || '',
        message_text: messageText.trim(),
        shared_post_url: postUrl || null,
      }),
    onSuccess: () => {
      void runsQuery.refetch();
    },
    onError: (error) =>
      showToast(error instanceof Error ? error.message : 'Simulation failed', 'error'),
  });

  const resetMutation = useMutation({
    mutationFn: () => apiClient.resetDMSimulator(selectedShopId),
    onSuccess: (data) => {
      showToast(`Removed ${data.deleted_conversations} simulation conversation(s).`, 'success');
      runMutation.reset();
      setResetDialogOpen(false);
      void runsQuery.refetch();
    },
    onError: (error) =>
      showToast(error instanceof Error ? error.message : 'Reset failed', 'error'),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!messageText.trim()) {
      showToast('Enter a customer message before running the simulator.', 'error');
      return;
    }
    if (!instagramAccountId && !accountsQuery.data?.length) {
      showToast('Connect an Instagram account before running the simulator.', 'error');
      return;
    }
    runMutation.mutate();
  }

  function resetForm() {
    setMessageText(EXAMPLE_MESSAGES[0].text);
    setPostUrl('');
    runMutation.reset();
  }

  const canRun =
    Boolean(selectedShopId && messageText.trim() && (instagramAccountId || accountsQuery.data?.length)) &&
    !runMutation.isPending;

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Safe test mode</p>
        <h1>DM Simulator</h1>
        <p>
          Runs through the production orchestrator but never sends a real Instagram message. Use
          this to test intents, product resolution, and reply drafting.
        </p>
        <ShopSelector />
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Run a simulated DM</h2>
        <p className="analytics-toolbar__summary">
          Pick an Instagram account, enter a fake customer message, and optionally attach a shared
          post URL.
        </p>

        {!selectedShopId ? (
          <p className="empty-state">Select a shop to run simulations.</p>
        ) : accountsQuery.isLoading ? (
          <p className="loading-state">Loading Instagram accounts...</p>
        ) : (accountsQuery.data?.length ?? 0) === 0 ? (
          <p className="empty-state">
            No Instagram accounts connected. Add one under Instagram Accounts first.
          </p>
        ) : (
          <form className="dm-simulator-form" onSubmit={submit}>
            <div className="filter-grid">
              <label className="form-field">
                <span>Instagram account</span>
                <select
                  value={instagramAccountId}
                  onChange={(event) => setInstagramAccountId(event.target.value)}
                  required
                >
                  <option value="">Select account</option>
                  {accountsQuery.data?.map((account) => (
                    <option key={account.id} value={account.id}>
                      @{account.username}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field form-field--wide">
                <span>Shared Instagram post URL</span>
                <input
                  value={postUrl}
                  onChange={(event) => setPostUrl(event.target.value)}
                  placeholder="https://www.instagram.com/p/… (optional)"
                />
              </label>

              <label className="form-field form-field--wide">
                <span>Fake customer message</span>
                <textarea
                  value={messageText}
                  onChange={(event) => setMessageText(event.target.value)}
                  rows={4}
                  dir="auto"
                  placeholder="Type what a customer might send in DM…"
                  required
                />
              </label>
            </div>

            <div className="form-field dm-simulator-form__examples">
              <span>Example messages</span>
              <div className="filter-chips" role="group" aria-label="Example customer messages">
                {EXAMPLE_MESSAGES.map((example) => (
                  <button
                    key={example.label}
                    type="button"
                    className={`filter-chip${messageText === example.text ? ' filter-chip--active' : ''}`}
                    aria-pressed={messageText === example.text}
                    onClick={() => setMessageText(example.text)}
                  >
                    {example.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="button-row">
              <button className="button button--primary" type="submit" disabled={!canRun}>
                {runMutation.isPending ? 'Running…' : 'Run simulator'}
              </button>
              <button className="button button--ghost-dark" type="button" onClick={resetForm}>
                Clear form
              </button>
              <button
                className="button button--ghost-dark"
                type="button"
                disabled={resetMutation.isPending || !selectedShopId}
                onClick={() => setResetDialogOpen(true)}
              >
                Reset simulation data
              </button>
            </div>
          </form>
        )}

        {runMutation.isPending ? (
          <p className="loading-state">Running simulation through the orchestrator…</p>
        ) : null}

        {runMutation.error ? (
          <p className="form-error">
            {runMutation.error instanceof Error ? runMutation.error.message : 'Simulation failed'}
          </p>
        ) : null}
      </section>

      {runMutation.data ? <SimulationResultPanel result={runMutation.data} /> : null}

      {selectedShopId && runsQuery.data && runsQuery.data.length > 0 ? (
        <section className="dashboard-card dashboard-card--wide">
          <h2>Recent simulation runs</h2>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Message</th>
                  <th scope="col">Intent</th>
                  <th scope="col">State</th>
                  <th scope="col">Action</th>
                </tr>
              </thead>
              <tbody>
                {runsQuery.data.map((run) => (
                  <tr key={run.conversation_id}>
                    <td>{run.message_preview ?? '—'}</td>
                    <td>{run.intent ?? '—'}</td>
                    <td>{run.next_state ?? '—'}</td>
                    <td>
                      <Link className="table-link" to={`/conversations/${run.conversation_id}`}>
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <ConfirmDialog
        open={resetDialogOpen}
        title="Reset simulation data?"
        message="This removes all simulation conversations, messages, and related test records for the selected shop. Real customer data is not affected."
        confirmLabel="Reset simulation data"
        onConfirm={() => resetMutation.mutate()}
        onCancel={() => setResetDialogOpen(false)}
        isLoading={resetMutation.isPending}
      />
    </div>
  );
}
