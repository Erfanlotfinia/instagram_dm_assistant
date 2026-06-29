import { Badge, Card, CardBody, CardHeader } from '../ui';
import { EmptyState, ErrorState, LoadingState } from '../data';
import type { BadgeTone } from '../ui';
import type { PostRevenueInsight } from '../../types/sprint4Revenue';

export interface PostRevenueInsightPanelProps {
  insights: PostRevenueInsight[];
  isLoading?: boolean;
  error?: string | null;
}

function classifyInsight(insight: string): { label: string; tone: BadgeTone } {
  if (/high revenue/i.test(insight)) return { label: 'High revenue', tone: 'success' };
  if (/low conversion/i.test(insight)) return { label: 'Low conversion', tone: 'warning' };
  if (/lost demand/i.test(insight)) return { label: 'Lost demand', tone: 'danger' };
  return { label: 'Revenue', tone: 'accent' };
}

function formatMoney(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function formatPercent(rate: number | null | undefined): string {
  if (rate == null || Number.isNaN(rate)) return '—';
  return `${(rate * 100).toFixed(1)}%`;
}

function InsightRow({ insight }: { insight: PostRevenueInsight }) {
  const cls = classifyInsight(insight.insight);
  return (
    <li className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-border bg-surface px-3 py-2.5">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={cls.tone}>{cls.label}</Badge>
          {insight.post_url ? (
            <a
              href={insight.post_url}
              target="_blank"
              rel="noreferrer"
              className="truncate text-sm font-medium text-accent hover:underline"
            >
              {insight.post_url}
            </a>
          ) : (
            <span className="text-sm text-muted">Unknown post</span>
          )}
        </div>
        <p className="mt-1 text-sm text-fg">{insight.insight}</p>
        <p className="mt-0.5 text-xs text-muted">
          Recommended action: {insight.recommended_action}
        </p>
      </div>
      <div className="shrink-0 text-right text-xs text-muted">
        <p>
          Revenue: <span className="tabular-nums text-fg">{formatMoney(insight.revenue)}</span>
        </p>
        <p>
          Orders: <span className="tabular-nums text-fg">{insight.order_count ?? 0}</span>
        </p>
        <p>
          Demand: <span className="tabular-nums text-fg">{insight.demand_count ?? 0}</span>
        </p>
        <p>
          Lost: <span className="tabular-nums text-fg">{insight.lost_demand_count ?? 0}</span>
        </p>
        <p>
          Conv: <span className="tabular-nums text-fg">{formatPercent(insight.conversion_rate)}</span>
        </p>
      </div>
    </li>
  );
}

/**
 * Post-to-revenue insights. Surfaces top revenue posts, high-demand
 * low-conversion posts, and posts with high lost demand, each with a
 * deterministic recommended action. Reused by the Revenue Recovery page and
 * the existing Post Revenue analytics page (additive).
 */
export function PostRevenueInsightPanel({ insights, isLoading, error }: PostRevenueInsightPanelProps) {
  const topRevenue = insights.filter((i) => /high revenue|revenue post/i.test(i.insight)).slice(0, 5);
  const lowConversion = insights.filter((i) => /low conversion/i.test(i.insight)).slice(0, 5);
  const lostDemand = insights.filter((i) => /lost demand/i.test(i.insight)).slice(0, 5);

  return (
    <Card>
      <CardHeader
        title="Post-to-revenue insights"
        description="High revenue posts, high-demand / low-conversion posts, and posts with high lost demand."
      />
      <CardBody className="flex flex-col gap-5">
        {isLoading ? (
          <LoadingState label="Loading post insights…" />
        ) : error ? (
          <ErrorState message={error} />
        ) : insights.length === 0 ? (
          <EmptyState
            title="No post insights yet"
            description="Insights appear once posts generate conversations, orders, or unfulfillable demand."
          />
        ) : (
          <>
            <section>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Top revenue posts</h3>
              {topRevenue.length === 0 ? (
                <p className="text-xs text-subtle">No revenue-attributed posts yet.</p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {topRevenue.map((insight) => (
                    <InsightRow key={insight.post_url ?? insight.insight} insight={insight} />
                  ))}
                </ul>
              )}
            </section>
            <section>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">High demand, low conversion</h3>
              {lowConversion.length === 0 ? (
                <p className="text-xs text-subtle">No low-conversion posts detected.</p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {lowConversion.map((insight) => (
                    <InsightRow key={insight.post_url ?? insight.insight} insight={insight} />
                  ))}
                </ul>
              )}
            </section>
            <section>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">High lost demand</h3>
              {lostDemand.length === 0 ? (
                <p className="text-xs text-subtle">No high-lost-demand posts detected.</p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {lostDemand.map((insight) => (
                    <InsightRow key={insight.post_url ?? insight.insight} insight={insight} />
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </CardBody>
    </Card>
  );
}
