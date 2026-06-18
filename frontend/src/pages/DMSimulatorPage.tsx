import { FormEvent, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ConfirmDialog } from '../components/ConfirmDialog';
import { DataTable, EmptyState, KpiCard, LoadingState } from '../components/data';
import type { Column } from '../components/data';
import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, FilterChip, Input, SectionPanel, Select } from '../components/ui';
import { ReplayPanel } from '../components/trust/ReplayPanel';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import type { DMSimulatorResponse, SimulatorRunSummary } from '../types/competitive';

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
    <aside
      className="grid gap-3 rounded-lg border border-accent/25 bg-gradient-to-b from-accent-soft/40 to-surface p-4 lg:order-first lg:min-h-full"
      aria-label="Message preview"
    >
      <div className="flex items-center gap-3">
        <div
          className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-[#833ab4] via-[#fd1d1d] to-[#fcb045] text-sm font-bold text-white"
          aria-hidden="true"
        >
          {username ? username.charAt(0).toUpperCase() : '?'}
        </div>
        <div>
          <p className="text-sm font-semibold text-fg">Customer preview</p>
          <p className="text-xs text-muted">{username ? `@${username}` : 'Select an account to preview'}</p>
        </div>
      </div>

      <div className="min-h-36 rounded-lg border border-border bg-surface p-3">
        {hasPost ? (
          <div className="mb-3 rounded-lg border border-dashed border-accent/40 bg-accent-soft/30 px-3 py-2">
            <span className="text-[10px] font-bold uppercase tracking-wide text-muted">Shared post</span>
            <p className="mt-0.5 break-all text-xs text-accent">{postUrl.trim()}</p>
          </div>
        ) : null}

        {trimmedMessage ? (
          <div className="flex max-w-[90%] flex-col gap-1 self-start">
            <p className="px-1 text-xs text-subtle">Customer</p>
            <div className="rounded-2xl rounded-bl-md bg-surface-sunken px-3 py-2 text-sm leading-relaxed text-fg" dir="auto">
              {trimmedMessage}
            </div>
          </div>
        ) : (
          <p className="py-6 text-center text-sm text-subtle">
            Your fake customer message will appear here as you type.
          </p>
        )}
      </div>

      <p className="text-center text-xs text-muted">
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

function SimulationStatusBadge({ tone, children }: { tone: PillTone; children: ReactNode }) {
  return <Badge tone={tone}>{children}</Badge>;
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
    <section className="rounded-lg border border-danger/30 bg-danger-soft p-4" aria-label="Handoff required">
      <div className="mb-3 flex flex-col gap-2">
        <Badge tone="danger">Handoff required</Badge>
        <p className="text-sm text-muted">
          Auto-send was blocked because one or more confidence checks fell below their threshold.
        </p>
      </div>

      <ul className="grid gap-2">
        {reasons.map((item) => {
          const hasScores = item.metric !== null && item.threshold !== null;
          const pct =
            hasScores && item.threshold ? Math.min(100, (item.metric! / item.threshold) * 100) : 0;
          return (
            <li className="rounded-lg border border-border bg-surface p-3" key={item.raw}>
              <div className="flex items-center justify-between gap-2 text-sm">
                <span className="font-medium text-fg">{item.label}</span>
                {hasScores ? (
                  <span className="font-mono text-xs text-muted">
                    {item.metric!.toFixed(2)} / {item.threshold!.toFixed(2)}
                  </span>
                ) : null}
              </div>
              {hasScores ? (
                <div
                  className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-sunken"
                  role="meter"
                  aria-valuenow={item.metric!}
                  aria-valuemin={0}
                  aria-valuemax={item.threshold!}
                  aria-label={`${item.label}: ${item.metric!.toFixed(2)} of required ${item.threshold!.toFixed(2)}`}
                >
                  <span className="block h-full rounded-full bg-warning" style={{ width: `${pct}%` }} />
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
    <div className="grid gap-1 text-sm">
      <dt className="text-xs font-medium text-muted">{label}</dt>
      <dd className="flex flex-wrap items-center gap-2">
        <code className="rounded bg-surface-sunken px-2 py-0.5 font-mono text-xs">{value}</code>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => onCopy(value, label)}
          aria-label={`Copy ${label}`}
        >
          Copy
        </Button>
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
    <Card>
      <CardHeader
        title="Simulation result"
        description="Outcome from the orchestrator. Nothing was sent to any provider."
        actions={isSimulation ? <Badge tone="accent">Simulation</Badge> : undefined}
      />
      <CardBody className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2" role="list" aria-label="Send decision summary">
        <SimulationStatusBadge tone={autoSendAllowed ? 'success' : 'neutral'}>
          {autoSendAllowed ? 'Auto-send allowed' : 'Auto-send blocked'}
        </SimulationStatusBadge>
        <SimulationStatusBadge tone={requiresPreview ? 'warning' : 'neutral'}>
          {requiresPreview ? 'Preview required' : 'No preview needed'}
        </SimulationStatusBadge>
        <SimulationStatusBadge tone={requiresHandoff ? 'danger' : 'neutral'}>
          {requiresHandoff ? 'Handoff required' : 'No handoff'}
        </SimulationStatusBadge>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Intent" value={humanizeToken(result.intent)} hint={result.intent ?? undefined} />
        <KpiCard
          label="Next state"
          value={humanizeToken(result.next_state)}
          hint={result.next_state ?? undefined}
          tone={requiresHandoff ? 'warning' : 'accent'}
        />
        <KpiCard
          label="Auto-send"
          value={autoSendAllowed ? 'Allowed' : 'Blocked'}
          tone={autoSendAllowed ? 'success' : 'accent'}
        />
        <KpiCard
          label="Handoff"
          value={requiresHandoff ? 'Required' : 'No'}
          tone={requiresHandoff ? 'warning' : 'accent'}
        />
      </div>

      {result.handoff_reason ? <HandoffReasonPanel reason={result.handoff_reason} /> : null}

      <dl className="grid gap-3 sm:grid-cols-2">
        <SimulationIdRow label="Conversation ID" value={result.conversation_id} onCopy={copyToClipboard} />
        <SimulationIdRow label="Message ID" value={result.message_id} onCopy={copyToClipboard} />
      </dl>

      <div className="rounded-lg border border-border bg-surface-sunken p-4">
        <div className="mb-3 flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-fg">Suggested reply</h3>
          {result.suggested_reply ? (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => void copyToClipboard(result.suggested_reply ?? '', 'Suggested reply')}
            >
              Copy reply
            </Button>
          ) : null}
        </div>
        {result.suggested_reply ? (
          <div className="flex flex-col items-end gap-1">
            <p className="px-1 text-xs text-subtle">Suggested assistant reply</p>
            <div className="max-w-[90%] rounded-2xl rounded-br-md bg-accent px-3 py-2 text-sm leading-relaxed text-accent-fg" dir="auto">
              {result.suggested_reply}
            </div>
          </div>
        ) : (
          <EmptyState title="No suggested reply" />
        )}
      </div>

      {result.draft_order ? (
        <div className="rounded-lg border border-border bg-surface-sunken p-4">
          <h3 className="mb-2 text-sm font-semibold text-fg">Draft order</h3>
          <pre className="overflow-x-auto rounded-lg bg-fg p-3 text-xs text-canvas">{JSON.stringify(result.draft_order, null, 2)}</pre>
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Link to={`/conversations/${result.conversation_id}`}>
          <Button type="button" variant="secondary">
            Open simulation conversation
          </Button>
        </Link>
      </div>
      </CardBody>
    </Card>
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

  const runColumns: Column<SimulatorRunSummary>[] = useMemo(
    () => [
      {
        key: 'message',
        header: 'Message',
        render: (run) => run.message_preview ?? '—',
      },
      {
        key: 'intent',
        header: 'Intent',
        render: (run) => run.intent ?? '—',
      },
      {
        key: 'state',
        header: 'State',
        render: (run) => run.next_state ?? '—',
      },
      {
        key: 'action',
        header: 'Action',
        render: (run) => (
          <Link className="font-medium text-accent hover:underline" to={`/conversations/${run.conversation_id}`}>
            Open
          </Link>
        ),
      },
    ],
    [],
  );

  return (
    <HubPage
      eyebrow="Safe test mode"
      title="DM Simulator"
      description="Runs through the production orchestrator but never sends a real Instagram message. Use this to test intents, product resolution, and reply drafting."
    >
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Simulator mode">
        <FilterChip
          role="tab"
          aria-selected={activeTab === 'live'}
          active={activeTab === 'live'}
          onClick={() => setActiveTab('live')}
        >
          Live simulate
        </FilterChip>
        <FilterChip
          role="tab"
          aria-selected={activeTab === 'replay'}
          active={activeTab === 'replay'}
          onClick={() => setActiveTab('replay')}
        >
          Deterministic replay
        </FilterChip>
      </div>

      {activeTab === 'replay' ? <ReplayPanel /> : null}

      {activeTab === 'live' ? (
      <>
      <Card>
        <CardHeader
          title="Run a simulated DM"
          description="Pick a provider/channel account, enter a fake customer message, and optionally attach a shared post URL. Non-Instagram choices stay in simulation mode and never send real messages."
          actions={<Badge tone="warning">Test harness</Badge>}
        />
        <CardBody>
        {!selectedShopId ? (
          <EmptyState
            title="Select a shop first"
            description="Use the shop switcher in the top bar to load Instagram accounts and run simulations."
          />
        ) : accountsQuery.isLoading ? (
          <LoadingState label="Loading Instagram accounts…" />
        ) : (accountsQuery.data?.length ?? 0) === 0 ? (
          <EmptyState
            title="No Instagram accounts connected"
            description="Add an account under Instagram Accounts, then return here to test DM flows."
            action={
              <Link to="/instagram-accounts">
                <Button type="button" variant="secondary">
                  Go to Instagram Accounts
                </Button>
              </Link>
            }
          />
        ) : (
          <form className="flex flex-col gap-4" onSubmit={submit}>
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,360px)]">
              <div className="flex flex-col gap-4">
                <SectionPanel title="Setup">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Field label="Provider">
                      <Select
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
                      </Select>
                    </Field>

                    <Field label={provider === 'instagram' ? 'Instagram account' : 'Channel account'}>
                      {provider === 'instagram' ? (
                        <Select
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
                        </Select>
                      ) : (
                        <Select
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
                        </Select>
                      )}
                    </Field>

                    <Field
                      label={
                        <>
                          Shared Instagram post URL
                          <span className="ml-1 text-xs font-normal text-subtle">Optional</span>
                        </>
                      }
                      className="sm:col-span-2"
                      hint="Simulates a customer DM that references a specific post."
                    >
                      <Input
                        value={postUrl}
                        onChange={(event) => setPostUrl(event.target.value)}
                        placeholder="https://www.instagram.com/p/…"
                        inputMode="url"
                        autoComplete="off"
                      />
                    </Field>
                  </div>
                </SectionPanel>

                <SectionPanel
                  variant="compose"
                  title="Compose message"
                  actions={
                    <span className="text-xs text-muted" aria-live="polite">
                      {messageLength} {messageLength === 1 ? 'character' : 'characters'}
                    </span>
                  }
                >
                  <Field label={<span className="visually-hidden">Fake customer message</span>}>
                    <textarea
                      value={messageText}
                      onChange={(event) => setMessageText(event.target.value)}
                      rows={5}
                      dir="auto"
                      placeholder="Type what a customer might send in DM…"
                      required
                      className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg"
                    />
                  </Field>

                  <Field label="Quick examples">
                    <div className="flex flex-wrap gap-2" role="group" aria-label="Example customer messages">
                      {EXAMPLE_MESSAGES.map((example) => (
                        <FilterChip
                          key={example.label}
                          active={messageText === example.text}
                          onClick={() => setMessageText(example.text)}
                        >
                          {example.label}
                        </FilterChip>
                      ))}
                    </div>
                  </Field>
                </SectionPanel>
              </div>

              <SimulatorMessagePreview
                username={selectedAccount?.username ?? null}
                messageText={messageText}
                postUrl={postUrl}
              />
            </div>

            {runMutation.isPending ? (
              <LoadingState label="Running simulation through the orchestrator…" />
            ) : null}

            {runMutation.error ? (
              <p className="text-sm text-danger" role="alert">
                {runMutation.error instanceof Error ? runMutation.error.message : 'Simulation failed'}
              </p>
            ) : null}

            <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={!canRun}>
                  {runMutation.isPending ? 'Running…' : 'Run simulator'}
                </Button>
                <Button type="button" variant="secondary" onClick={resetForm}>
                  Clear form
                </Button>
              </div>
              <Button
                type="button"
                variant="secondary"
                disabled={resetMutation.isPending || !selectedShopId}
                onClick={() => setResetDialogOpen(true)}
              >
                Reset simulation data
              </Button>
            </div>
          </form>
        )}
        </CardBody>
      </Card>

      {runMutation.data ? <SimulationResultPanel result={runMutation.data} /> : null}

      {selectedShopId && runsQuery.data && runsQuery.data.length > 0 ? (
        <Card>
          <CardHeader title="Recent simulation runs" />
          <CardBody>
            <DataTable
              columns={runColumns}
              rows={runsQuery.data}
              rowKey={(run) => run.conversation_id}
            />
          </CardBody>
        </Card>
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
    </HubPage>
  );
}
