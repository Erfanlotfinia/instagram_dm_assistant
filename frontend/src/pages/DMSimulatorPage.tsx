import { FormEvent, ReactNode, useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { ReplayPanel } from '../components/trust/ReplayPanel';
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
        Nothing is sent to any provider — this is a local preview only.
      </p>
    </aside>
  );
}

function humanizeToken(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }
  const cleaned = value.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
  if (!cleaned) {
    return '—';
  }
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

type PillTone = 'neutral' | 'success' | 'warning' | 'danger' | 'accent';

function SimulationStatusPill({ tone, children }: { tone: PillTone; children: ReactNode }) {
  return <span className={`status-pill status-pill--${tone}`}>{children}</span>;
}

type HandoffReason = {
  label: string;
  metric: number | null;
  threshold: number | null;
  raw: string;
};

function parseHandoffReasons(reason: string): HandoffReason[] {
  return reason
    .split(';')
    .map((segment) => segment.trim())
    .filter(Boolean)
    .map((segment) => {
      const match = segment.match(/^([^:]+):\s*([\d.]+)\s*<\s*([\d.]+)\s*$/);
      if (match) {
        const metric = Number.parseFloat(match[2]);
        const threshold = Number.parseFloat(match[3]);
        return {
          label: humanizeToken(match[1]),
          metric: Number.isFinite(metric) ? metric : null,
          threshold: Number.isFinite(threshold) ? threshold : null,
          raw: segment,
        };
      }
      return { label: humanizeToken(segment), metric: null, threshold: null, raw: segment };
    });
}

function HandoffReasonPanel({ reason }: { reason: string }) {
  const reasons = parseHandoffReasons(reason);

  return (
    <section className="handoff-panel" aria-label="Handoff required">
      <div className="handoff-panel__header">
        <span className="status-pill status-pill--danger">Handoff required</span>
        <p className="handoff-panel__intro">
          Auto-send was blocked because one or more confidence checks fell below their threshold.
        </p>
      </div>

      <ul className="handoff-panel__list">
        {reasons.map((item) => {
          const hasScores = item.metric !== null && item.threshold !== null;
          const pct =
            hasScores && item.threshold ? Math.min(100, (item.metric! / item.threshold) * 100) : 0;
          return (
            <li className="handoff-reason" key={item.raw}>
              <div className="handoff-reason__top">
                <span className="handoff-reason__label">{item.label}</span>
                {hasScores ? (
                  <span className="handoff-reason__scores">
                    <span className="handoff-reason__value">{item.metric!.toFixed(2)}</span>
                    <span className="handoff-reason__divider">/</span>
                    <span className="handoff-reason__threshold">{item.threshold!.toFixed(2)}</span>
                  </span>
                ) : null}
              </div>
              {hasScores ? (
                <div
                  className="handoff-reason__meter"
                  role="meter"
                  aria-valuenow={item.metric!}
                  aria-valuemin={0}
                  aria-valuemax={item.threshold!}
                  aria-label={`${item.label}: ${item.metric!.toFixed(2)} of required ${item.threshold!.toFixed(2)}`}
                >
                  <span className="handoff-reason__meter-fill" style={{ width: `${pct}%` }} />
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function SimulationIdRow({
  label,
  value,
  onCopy,
}: {
  label: string;
  value: string;
  onCopy: (value: string, label: string) => void;
}) {
  return (
    <div className="simulation-result__id">
      <dt>{label}</dt>
      <dd>
        <code className="simulation-result__id-value">{value}</code>
        <button
          type="button"
          className="simulation-result__id-copy"
          onClick={() => onCopy(value, label)}
          aria-label={`Copy ${label}`}
        >
          Copy
        </button>
      </dd>
    </div>
  );
}

function SimulationResultPanel({ result }: { result: DMSimulatorResponse }) {
  const { showToast } = useToast();
  const autoSendAllowed = Boolean(result.auto_send_decision?.auto_send_allowed);
  const requiresPreview = Boolean(result.auto_send_decision?.requires_preview);
  const requiresHandoff = Boolean(result.auto_send_decision?.requires_handoff) || Boolean(result.handoff_reason);
  const isSimulation = result.is_simulation !== false;

  async function copyToClipboard(value: string, label: string) {
    if (!value) {
      return;
    }
    try {
      await navigator.clipboard.writeText(value);
      showToast(`${label} copied to clipboard.`, 'success');
    } catch {
      showToast(`Could not copy ${label}.`, 'error');
    }
  }

  return (
    <section className="dashboard-card dashboard-card--wide simulation-result">
      <div className="section-header">
        <div>
          <h2>Simulation result</h2>
          <p className="dashboard-card__subtitle">
            Outcome from the orchestrator. Nothing was sent to any provider.
          </p>
        </div>
        {isSimulation ? (
          <span className="status-pill status-pill--accent">Simulation</span>
        ) : null}
      </div>

      <div className="simulation-result__pills" role="list" aria-label="Send decision summary">
        <SimulationStatusPill tone={autoSendAllowed ? 'success' : 'neutral'}>
          {autoSendAllowed ? 'Auto-send allowed' : 'Auto-send blocked'}
        </SimulationStatusPill>
        <SimulationStatusPill tone={requiresPreview ? 'warning' : 'neutral'}>
          {requiresPreview ? 'Preview required' : 'No preview needed'}
        </SimulationStatusPill>
        <SimulationStatusPill tone={requiresHandoff ? 'danger' : 'neutral'}>
          {requiresHandoff ? 'Handoff required' : 'No handoff'}
        </SimulationStatusPill>
      </div>

      <div className="stats-grid">
        <article className="stat-card">
          <p className="stat-card__label">Intent</p>
          <p className="stat-card__value">{humanizeToken(result.intent)}</p>
          {result.intent ? <code className="stat-card__token">{result.intent}</code> : null}
        </article>
        <article className={`stat-card${requiresHandoff ? ' stat-card--warning' : ''}`}>
          <p className="stat-card__label">Next state</p>
          <p className="stat-card__value">{humanizeToken(result.next_state)}</p>
          {result.next_state ? <code className="stat-card__token">{result.next_state}</code> : null}
        </article>
        <article className={`stat-card${autoSendAllowed ? ' stat-card--success' : ''}`}>
          <p className="stat-card__label">Auto-send</p>
          <p className="stat-card__value">{autoSendAllowed ? 'Allowed' : 'Blocked'}</p>
        </article>
        <article className={`stat-card${requiresHandoff ? ' stat-card--warning' : ''}`}>
          <p className="stat-card__label">Handoff</p>
          <p className="stat-card__value">{requiresHandoff ? 'Required' : 'No'}</p>
        </article>
      </div>

      {result.handoff_reason ? <HandoffReasonPanel reason={result.handoff_reason} /> : null}

      <dl className="detail-grid simulation-result__id-grid">
        <SimulationIdRow label="Conversation ID" value={result.conversation_id} onCopy={copyToClipboard} />
        <SimulationIdRow label="Message ID" value={result.message_id} onCopy={copyToClipboard} />
      </dl>

      <div className="match-panel simulator-reply-panel">
        <div className="section-header">
          <h3>Suggested reply</h3>
          {result.suggested_reply ? (
            <button
              className="button button--ghost-dark"
              type="button"
              onClick={() => void copyToClipboard(result.suggested_reply ?? '', 'Suggested reply')}
            >
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
    </section>
  );
}

export function DMSimulatorPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState<'live' | 'replay'>('live');
  const [provider, setProvider] = useState<'instagram' | 'whatsapp' | 'telegram' | 'bale' | 'rubika'>(
    'instagram',
  );
  const [channelAccountId, setChannelAccountId] = useState('');
  const [instagramAccountId, setInstagramAccountId] = useState('');
  const [messageText, setMessageText] = useState<string>(EXAMPLE_MESSAGES[0].text);
  const [postUrl, setPostUrl] = useState('');
  const [resetDialogOpen, setResetDialogOpen] = useState(false);

  const accountsQuery = useQuery({
    queryKey: ['instagram-accounts', selectedShopId],
    queryFn: () => apiClient.listInstagramAccounts(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const channelAccountsQuery = useQuery({
    queryKey: ['channel-accounts', selectedShopId],
    queryFn: () => apiClient.listChannelAccounts(selectedShopId),
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

  useEffect(() => {
    const matching = channelAccountsQuery.data?.filter((account) => account.provider === provider) ?? [];
    if (!channelAccountId && matching.length) {
      setChannelAccountId(matching[0].id);
    }
  }, [channelAccountsQuery.data, channelAccountId, provider]);

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
        <div className="filter-chips" role="tablist" aria-label="Simulator mode">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'live'}
            className={`filter-chip${activeTab === 'live' ? ' filter-chip--active' : ''}`}
            onClick={() => setActiveTab('live')}
          >
            Live simulate
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'replay'}
            className={`filter-chip${activeTab === 'replay' ? ' filter-chip--active' : ''}`}
            onClick={() => setActiveTab('replay')}
          >
            Deterministic replay
          </button>
        </div>
      </section>

      {activeTab === 'replay' ? <ReplayPanel /> : null}

      {activeTab === 'live' ? (
      <>
      <section className="dashboard-card dashboard-card--wide dm-simulator-card">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Run a simulated DM</h2>
            <p className="dashboard-card__subtitle">
              Pick a provider/channel account, enter a fake customer message, and optionally attach a
              shared post URL. Non-Instagram choices stay in simulation mode and never send real messages.
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
                      <span>Provider</span>
                      <select
                        value={provider}
                        onChange={(event) => {
                          setProvider(event.target.value as typeof provider);
                          setChannelAccountId('');
                        }}
                      >
                        <option value="instagram">Instagram</option>
                        <option value="whatsapp">WhatsApp</option>
                        <option value="telegram">Telegram</option>
                        <option value="bale">Bale</option>
                        <option value="rubika">Rubika</option>
                      </select>
                    </label>

                    <label className="form-field">
                      <span>{provider === 'instagram' ? 'Instagram account' : 'Channel account'}</span>
                      {provider === 'instagram' ? (
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
                      ) : (
                        <select
                          value={channelAccountId}
                          onChange={(event) => setChannelAccountId(event.target.value)}
                          required
                        >
                          <option value="">Select channel account</option>
                          {channelAccountsQuery.data?.filter((account) => account.provider === provider).map((account) => (
                            <option key={account.id} value={account.id}>
                              {account.display_name}
                            </option>
                          ))}
                        </select>
                      )}
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
      </>
      ) : null}
    </div>
  );
}
