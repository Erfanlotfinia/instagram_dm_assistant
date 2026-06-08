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

function SimulatorMessagePreview({
  username,
  messageText,
  postUrl,
}: {
  username: string | null;
  messageText: string;
  postUrl: string;
}) {
  const trimmedMessage = messageText.trim();
  const hasPost = Boolean(postUrl.trim());

  return (
    <aside className="dm-simulator-preview" aria-label="Message preview">
      <div className="dm-simulator-preview__header">
        <div className="dm-simulator-preview__avatar" aria-hidden="true">
          {username ? username.charAt(0).toUpperCase() : '?'}
        </div>
        <div>
          <p className="dm-simulator-preview__title">Customer preview</p>
          <p className="dm-simulator-preview__subtitle">
            {username ? `@${username}` : 'Select an account to preview'}
          </p>
        </div>
      </div>

      <div className="message-thread dm-simulator-preview__thread">
        {hasPost ? (
          <div className="dm-simulator-preview__post">
            <span className="dm-simulator-preview__post-label">Shared post</span>
            <p className="dm-simulator-preview__post-url">{postUrl.trim()}</p>
          </div>
        ) : null}

        {trimmedMessage ? (
          <div className="message-bubble message-bubble--inbound">
            <p className="message-bubble__meta">Customer</p>
            <p className="message-bubble__text" dir="auto">
              {trimmedMessage}
            </p>
          </div>
        ) : (
          <p className="dm-simulator-preview__placeholder">
            Your fake customer message will appear here as you type.
          </p>
        )}
      </div>

      <p className="dm-simulator-preview__footnote">
        Nothing is sent to Instagram — this is a local preview only.
      </p>
    </aside>
  );
}

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

      <div className="match-panel simulator-reply-panel">
        <div className="section-header">
          <h3>Suggested reply</h3>
          {result.suggested_reply ? (
            <button className="button button--ghost-dark" type="button" onClick={() => void copyReply()}>
              Copy reply
            </button>
          ) : null}
        </div>
        {result.suggested_reply ? (
          <div className="message-thread">
            <div className="message-bubble message-bubble--outbound">
              <p className="message-bubble__meta">Suggested assistant reply</p>
              <p className="message-bubble__text simulator-reply" dir="auto">
                {result.suggested_reply}
              </p>
            </div>
          </div>
        ) : (
          <p className="empty-state">No reply generated</p>
        )}
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

  const selectedAccount = accountsQuery.data?.find((account) => account.id === instagramAccountId);
  const messageLength = messageText.trim().length;

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

      <section className="dashboard-card dashboard-card--wide dm-simulator-card">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Run a simulated DM</h2>
            <p className="dashboard-card__subtitle">
              Pick an Instagram account, enter a fake customer message, and optionally attach a
              shared post URL.
            </p>
          </div>
          <span className="priority-badge priority-badge--medium">Test harness</span>
        </div>

        {!selectedShopId ? (
          <div className="empty-state-panel dm-simulator-empty">
            <p className="empty-state-panel__title">Select a shop first</p>
            <p className="empty-state-panel__hint">
              Choose a shop above to load Instagram accounts and run simulations.
            </p>
          </div>
        ) : accountsQuery.isLoading ? (
          <p className="loading-state dm-simulator-loading">Loading Instagram accounts…</p>
        ) : (accountsQuery.data?.length ?? 0) === 0 ? (
          <div className="empty-state-panel dm-simulator-empty">
            <p className="empty-state-panel__title">No Instagram accounts connected</p>
            <p className="empty-state-panel__hint">
              Add an account under Instagram Accounts, then return here to test DM flows.
            </p>
            <Link className="button button--ghost-dark" to="/instagram-accounts">
              Go to Instagram Accounts
            </Link>
          </div>
        ) : (
          <form className="dm-simulator-form" onSubmit={submit}>
            <div className="dm-simulator-layout">
              <div className="dm-simulator-form__main">
                <div className="dm-simulator-panel">
                  <p className="dm-simulator-panel__label">Setup</p>
                  <div className="filter-grid dm-simulator-setup">
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
                      <span>
                        Shared Instagram post URL
                        <span className="dm-simulator-optional">Optional</span>
                      </span>
                      <input
                        value={postUrl}
                        onChange={(event) => setPostUrl(event.target.value)}
                        placeholder="https://www.instagram.com/p/…"
                        inputMode="url"
                        autoComplete="off"
                      />
                      <span className="dm-simulator-field-hint">
                        Simulates a customer DM that references a specific post.
                      </span>
                    </label>
                  </div>
                </div>

                <div className="dm-simulator-panel dm-simulator-panel--compose">
                  <div className="dm-simulator-panel__header">
                    <p className="dm-simulator-panel__label">Compose message</p>
                    <span className="dm-simulator-char-count" aria-live="polite">
                      {messageLength} {messageLength === 1 ? 'character' : 'characters'}
                    </span>
                  </div>

                  <label className="form-field dm-simulator-compose">
                    <span className="visually-hidden">Fake customer message</span>
                    <textarea
                      value={messageText}
                      onChange={(event) => setMessageText(event.target.value)}
                      rows={5}
                      dir="auto"
                      placeholder="Type what a customer might send in DM…"
                      required
                    />
                  </label>

                  <div className="form-field dm-simulator-form__examples">
                    <span>Quick examples</span>
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
                </div>
              </div>

              <SimulatorMessagePreview
                username={selectedAccount?.username ?? null}
                messageText={messageText}
                postUrl={postUrl}
              />
            </div>

            {runMutation.isPending ? (
              <p className="loading-state dm-simulator-status" role="status">
                Running simulation through the orchestrator…
              </p>
            ) : null}

            {runMutation.error ? (
              <p className="form-error dm-simulator-status">
                {runMutation.error instanceof Error ? runMutation.error.message : 'Simulation failed'}
              </p>
            ) : null}

            <div className="dm-simulator-actions">
              <div className="button-row dm-simulator-actions__primary">
                <button className="button button--primary" type="submit" disabled={!canRun}>
                  {runMutation.isPending ? 'Running…' : 'Run simulator'}
                </button>
                <button className="button button--ghost-dark" type="button" onClick={resetForm}>
                  Clear form
                </button>
              </div>
              <div className="button-row dm-simulator-actions__secondary">
                <button
                  className="button button--ghost-dark"
                  type="button"
                  disabled={resetMutation.isPending || !selectedShopId}
                  onClick={() => setResetDialogOpen(true)}
                >
                  Reset simulation data
                </button>
              </div>
            </div>
          </form>
        )}
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
