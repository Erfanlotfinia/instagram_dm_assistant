import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { Badge, Button, Callout, Card, CardBody, CardHeader, Dialog } from '../components/ui';
import { DataTable, EmptyState, ErrorState, KpiCard, LoadingState } from '../components/data';
import type { Column } from '../components/data';
import type { BadgeTone } from '../components/ui';
import { HubPage } from '../components/shell/HubPage';
import { useShop } from '../contexts/ShopContext';
import { useRevenueRecovery } from '../lib/useRevenueRecovery';
import { useShopReadiness } from '../lib/useShopReadiness';
import { buildRecoveryMessageDraft } from '../lib/revenueRecovery';
import { LostDemandTable } from '../components/revenue/LostDemandTable';
import { RestockWaitlistPanel } from '../components/revenue/RestockWaitlistPanel';
import { PostRevenueInsightPanel } from '../components/revenue/PostRevenueInsightPanel';
import type {
  RecoveryMessageDraft,
  RevenueRecoveryOpportunity,
  RevenueRecoveryOpportunityType,
  RevenueRecoverySeverity,
} from '../types/sprint4Revenue';

function severityTone(severity: RevenueRecoverySeverity): BadgeTone {
  if (severity === 'high') return 'danger';
  if (severity === 'medium') return 'warning';
  return 'neutral';
}

const TYPE_LABELS: Record<RevenueRecoveryOpportunityType, string> = {
  abandoned_order: 'Abandoned order',
  unavailable_product: 'Unavailable product',
  unavailable_variant: 'Unavailable variant',
  unpaid_order: 'Unpaid order',
  high_intent_no_order: 'High-intent conversation',
  restock_waitlist: 'Restock waitlist',
  post_demand_spike: 'Post demand spike',
};

const SOURCE_LABELS: Record<string, string> = {
  analytics: 'Analytics',
  order: 'Order',
  conversation: 'Conversation',
  catalog: 'Catalog',
  recovery_rule: 'Recovery rule',
};

function formatMoney(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

/**
 * Deterministic recovery-rule suggestion keyed off the top opportunity type.
 * Links to /automation/recovery only — no rule builder in this sprint.
 */
function ruleSuggestionFor(type: RevenueRecoveryOpportunityType | undefined): {
  label: string;
  detail: string;
} {
  switch (type) {
    case 'abandoned_order':
    case 'unpaid_order':
      return { label: 'Payment reminder rule', detail: 'Send a payment reminder to abandoned / unpaid orders.' };
    case 'unavailable_product':
    case 'unavailable_variant':
    case 'restock_waitlist':
      return { label: 'Restock notification rule', detail: 'Notify customers when an unavailable item is back in stock.' };
    case 'high_intent_no_order':
      return { label: 'Human follow-up rule', detail: 'Route high-intent conversations without an order to a human.' };
    case 'post_demand_spike':
      return { label: 'Campaign / stock review', detail: 'Review stock and consider a restock campaign for spike posts.' };
    default:
      return { label: 'Configure recovery rules', detail: 'Set up deterministic recovery automation.' };
  }
}

export function RevenueRecoveryPage() {
  const { selectedShopId } = useShop();
  const { dashboard, isLoading, error, warnings, refetch } = useRevenueRecovery(selectedShopId);
  // Non-blocking readiness context (Sprint 2). Failure does not stop the page.
  const { shopReadiness, channelStates } = useShopReadiness(selectedShopId);
  const [draft, setDraft] = useState<RecoveryMessageDraft | null>(null);
  const [draftCopied, setDraftCopied] = useState(false);

  const readyChannels = channelStates.filter((c) => c.ready).length;
  const noChannelsReady = shopReadiness != null && readyChannels === 0;

  const topOpportunityType = useMemo<RevenueRecoveryOpportunityType | undefined>(
    () => dashboard?.opportunities[0]?.type,
    [dashboard],
  );
  const ruleSuggestion = ruleSuggestionFor(topOpportunityType);

  const opportunityColumns: Column<RevenueRecoveryOpportunity>[] = [
    {
      key: 'priority',
      header: 'Priority',
      render: (row) => <Badge tone={severityTone(row.severity)}>{row.severity}</Badge>,
    },
    {
      key: 'type',
      header: 'Type',
      render: (row) => <span className="text-sm text-fg">{TYPE_LABELS[row.type]}</span>,
    },
    {
      key: 'opportunity',
      header: 'Opportunity',
      render: (row) => (
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-fg">{row.title}</p>
          <p className="truncate text-xs text-muted">{row.reason}</p>
        </div>
      ),
    },
    {
      key: 'value',
      header: 'Est. value',
      align: 'right',
      render: (row) => <span className="tabular-nums">{formatMoney(row.estimated_value)}</span>,
    },
    {
      key: 'action',
      header: 'Suggested action',
      render: (row) => <span className="text-sm text-muted">{row.suggested_action}</span>,
    },
    {
      key: 'source',
      header: 'Source',
      render: (row) => <Badge tone="neutral">{SOURCE_LABELS[row.source] ?? row.source}</Badge>,
    },
    {
      key: 'links',
      header: 'Action',
      align: 'right',
      render: (row) => (
        <div className="flex flex-wrap items-center justify-end gap-2">
          {row.conversation_id ? (
            <Link className="text-xs text-accent hover:underline" to={`/inbox/${row.conversation_id}`}>
              Conversation →
            </Link>
          ) : null}
          {row.order_id ? (
            <Link className="text-xs text-accent hover:underline" to={`/orders/${row.order_id}`}>
              Order →
            </Link>
          ) : null}
          {row.product_id ? (
            <Link className="text-xs text-accent hover:underline" to={`/catalog/products/${row.product_id}`}>
              Product →
            </Link>
          ) : null}
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => {
              setDraft(buildRecoveryMessageDraft(row));
              setDraftCopied(false);
            }}
          >
            Create draft
          </Button>
        </div>
      ),
    },
  ];

  const hasOpportunities = Boolean(dashboard && dashboard.opportunities.length > 0);

  return (
    <HubPage
      eyebrow="Analytics"
      title="Revenue Recovery"
      description="Prioritized opportunities to recover missed sales from conversations, unavailable products, unpaid orders, and high-demand posts."
      actions={
        <Button type="button" variant="secondary" size="sm" onClick={() => refetch()}>
          Refresh
        </Button>
      }
    >
      {!selectedShopId ? (
        <Card>
          <CardBody>
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          </CardBody>
        </Card>
      ) : isLoading ? (
        <Card>
          <CardBody>
            <LoadingState label="Loading revenue recovery…" />
          </CardBody>
        </Card>
      ) : error ? (
        <Card>
          <CardBody>
            <ErrorState message={error instanceof Error ? error.message : 'Failed to load revenue recovery data'} />
          </CardBody>
        </Card>
      ) : !dashboard || !hasOpportunities ? (
        <Card>
          <CardBody>
            <EmptyState
              title="No recovery opportunities yet"
              description="As conversations, orders, and demand analytics accumulate, Modira will surface missed revenue here."
            />
          </CardBody>
        </Card>
      ) : (
        <>
          {/* KPI row */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <KpiCard
              label="Recoverable value"
              value={formatMoney(dashboard.totalEstimatedRecoverableValue)}
              tone="accent"
              hint={dashboard.totalEstimatedRecoverableValue == null ? 'Value unavailable' : undefined}
            />
            <KpiCard
              label="High-priority opportunities"
              value={String(dashboard.highPriorityCount)}
              tone={dashboard.highPriorityCount > 0 ? 'danger' : 'success'}
            />
            <KpiCard label="Lost demand items" value={String(dashboard.lostDemand.length)} tone="warning" />
            <KpiCard
              label="Restock waitlist customers"
              value={String(dashboard.restockWaitlist.length)}
              tone="warning"
            />
            <KpiCard
              label="Recovery drafts ready"
              value={String(dashboard.opportunities.length)}
              tone="accent"
            />
          </div>

          {/* Non-blocking channel readiness warning (Sprint 2) */}
          {noChannelsReady ? (
            <Callout title="Connect at least one channel" icon="!">
              Connect at least one channel to recover revenue through conversations. Recovery data is still shown
              below, but automated reach-out requires a healthy channel.
            </Callout>
          ) : null}

          {/* Partial-data warnings */}
          {warnings.length > 0 ? (
            <div className="rounded-md border border-warning/30 bg-warning-soft/20 px-3 py-2 text-sm text-fg" role="note">
              <p className="font-medium">Notes:</p>
              <ul className="mt-1 list-inside list-disc space-y-0.5 text-muted">
                {warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {/* Priority opportunities */}
          <Card>
            <CardHeader
              title="Priority opportunities"
              description="Sorted by severity then estimated recoverable value. Drafts are preview-only — nothing is sent automatically."
            />
            <DataTable<RevenueRecoveryOpportunity>
              columns={opportunityColumns}
              rows={dashboard.opportunities}
              rowKey={(row) => row.id}
              emptyTitle="No recovery opportunities yet"
            />
          </Card>

          {/* Recovery rule CTA */}
          <Callout title="Recommended recovery rule" icon="→">
            <p>
              {ruleSuggestion.label}: {ruleSuggestion.detail}{' '}
              <Link className="text-accent hover:underline" to="/automation/recovery">
                Open recovery rules →
              </Link>
            </p>
          </Callout>

          {/* Lost demand */}
          <LostDemandTable insights={dashboard.lostDemand} />

          {/* Restock waitlist */}
          <RestockWaitlistPanel items={dashboard.restockWaitlist} />

          {/* Post-to-revenue insights */}
          <PostRevenueInsightPanel insights={dashboard.postInsights} />
        </>
      )}

      {/* Recovery message draft preview — never auto-sent */}
      <Dialog
        open={draft != null}
        onClose={() => setDraft(null)}
        title="Recovery message preview"
        footer={
          <>
            <Button type="button" variant="ghost" size="sm" onClick={() => setDraft(null)}>
              Close
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                if (draft) {
                  void navigator.clipboard?.writeText(draft.message);
                  setDraftCopied(true);
                  window.setTimeout(() => setDraftCopied(false), 1500);
                }
              }}
            >
              {draftCopied ? 'Copied' : 'Copy'}
            </Button>
            {draft?.conversation_id ? (
              <Link
                className="inline-flex h-8 items-center rounded-lg bg-accent px-3 text-xs font-medium text-accent-fg hover:opacity-90"
                to={`/inbox/${draft.conversation_id}`}
                onClick={() => setDraft(null)}
              >
                Go to conversation →
              </Link>
            ) : null}
          </>
        }
      >
        {draft ? (
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="info">{draft.tone}</Badge>
              <Badge tone="warning">Requires human approval</Badge>
              {draft.customer_label ? (
                <span className="text-xs text-muted">To: {draft.customer_label}</span>
              ) : null}
            </div>
            <pre className="whitespace-pre-wrap rounded-md bg-surface-sunken px-3 py-2 text-sm text-fg">
              {draft.message}
            </pre>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted">Why this customer / product</p>
              <p className="mt-0.5 text-sm text-fg">{draft.reason}</p>
            </div>
            <p className="text-xs text-subtle">
              This is a deterministic preview. No message is sent automatically. Copy it into the conversation to send
              manually.
            </p>
          </div>
        ) : null}
      </Dialog>
    </HubPage>
  );
}
