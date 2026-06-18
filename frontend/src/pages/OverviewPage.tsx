import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { AreaTrend, FunnelBars } from '../components/charts/ChartKit';
import { Card, CardBody, CardHeader, Button } from '../components/ui';
import { KpiCard, PageHeader, LoadingState, ErrorState, EmptyState } from '../components/data';
import { useAuth } from '../contexts/AuthContext';
import { useShop } from '../contexts/ShopContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function money(value: string): string {
  const amount = Number(value);
  if (Number.isNaN(amount)) {
    return value;
  }
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
}

export function OverviewPage() {
  const { user } = useAuth();
  const { selectedShopId } = useShop();
  const [period, setPeriod] = useState<'7d' | '30d'>('7d');

  const metricsQuery = useQuery({
    queryKey: queryKeys.dashboardMetrics(selectedShopId),
    queryFn: () => apiClient.getDashboardMetrics(selectedShopId),
    enabled: Boolean(selectedShopId),
    refetchInterval: 30_000,
  });

  const trendsQuery = useQuery({
    queryKey: queryKeys.dashboardTrends(selectedShopId, period),
    queryFn: () => apiClient.getDashboardTrends(selectedShopId, period),
    enabled: Boolean(selectedShopId),
  });

  const metrics = metricsQuery.data;
  const points = trendsQuery.data?.points ?? [];
  const messageTrend = points.map((point) => point.messages);

  const funnel = metrics?.conversion_funnel;
  const conversionRate =
    funnel && funnel.inbound_messages > 0 ? funnel.paid_orders / funnel.inbound_messages : 0;

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow="Operations"
        title={`Welcome back, ${user?.full_name ?? 'operator'}`}
        description="Live snapshot of conversations, automation health, and commerce across all channels."
        actions={
          <div className="inline-flex rounded-lg border border-border p-0.5">
            {(['7d', '30d'] as const).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setPeriod(value)}
                className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                  period === value ? 'bg-accent text-accent-fg' : 'text-muted hover:text-fg'
                }`}
              >
                {value === '7d' ? 'Last 7 days' : 'Last 30 days'}
              </button>
            ))}
          </div>
        }
      />

      {metricsQuery.isLoading ? <LoadingState label="Loading metrics…" /> : null}
      {metricsQuery.error ? (
        <ErrorState message={metricsQuery.error instanceof Error ? metricsQuery.error.message : 'Failed to load metrics'} />
      ) : null}

      {metrics ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <KpiCard
              label="Messages today"
              value={metrics.messages_today.toLocaleString()}
              hint={`${metrics.messages_week.toLocaleString()} in last 7 days`}
              trend={messageTrend}
            />
            <KpiCard label="Automation success" value={pct(metrics.automation_success_rate)} tone="success" />
            <KpiCard label="LLM fallback" value={pct(metrics.llm_fallback_rate)} tone="warning" />
            <KpiCard label="Human handoff" value={pct(metrics.handoff_rate)} tone="danger" />
            <KpiCard label="Conversion (chat→order)" value={pct(conversionRate)} tone="accent" />
            <KpiCard label="Active conversations" value={metrics.active_conversations.toLocaleString()} />
            <KpiCard label="Pending orders" value={metrics.waiting_for_payment.toLocaleString()} />
            <KpiCard
              label="Failed jobs"
              value={metrics.failed_jobs_count.toLocaleString()}
              tone={metrics.failed_jobs_count > 0 ? 'danger' : 'success'}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader
                title="Message volume & automation mix"
                description="Inbound message volume by day for the selected period."
              />
              <CardBody>
                {trendsQuery.isLoading ? (
                  <LoadingState />
                ) : points.length === 0 ? (
                  <EmptyState title="No activity yet" description="Trends populate as conversations come in." />
                ) : (
                  <AreaTrend
                    data={points as unknown as Array<Record<string, number | string>>}
                    xKey="date"
                    series={[{ key: 'messages', label: 'Inbound messages' }]}
                    height={260}
                  />
                )}
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Conversion funnel" description="Chat to paid order." />
              <CardBody>
                {funnel ? (
                  <FunnelBars
                    steps={[
                      { label: 'Inbound messages', value: funnel.inbound_messages },
                      { label: 'Product resolved', value: funnel.product_resolved },
                      { label: 'Draft orders', value: funnel.draft_orders },
                      { label: 'Paid orders', value: funnel.paid_orders },
                    ]}
                  />
                ) : null}
              </CardBody>
            </Card>
          </div>

          <Card>
            <CardHeader
              title="Decision mix over time"
              description="Automated vs LLM-handled vs human handoff, by day."
            />
            <CardBody>
              {points.length === 0 ? (
                <EmptyState title="No decisions recorded yet" />
              ) : (
                <AreaTrend
                  data={points as unknown as Array<Record<string, number | string>>}
                  xKey="date"
                  stacked
                  series={[
                    { key: 'automated', label: 'Automated', color: 'var(--c-success)' },
                    { key: 'llm', label: 'LLM handled', color: 'var(--c-warning)' },
                    { key: 'handoff', label: 'Human handoff', color: 'var(--c-danger)' },
                  ]}
                  height={240}
                />
              )}
            </CardBody>
          </Card>

          <div className="grid gap-4 lg:grid-cols-3">
            <Card>
              <CardHeader title="Recovered revenue" />
              <CardBody>
                <p className="text-2xl font-semibold text-fg">{money(metrics.recovered_revenue)}</p>
                <p className="mt-1 text-xs text-muted">
                  {metrics.recovered_orders} recovered of {metrics.abandoned_orders} abandoned
                </p>
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="Upsell acceptance" />
              <CardBody>
                <p className="text-2xl font-semibold text-fg">
                  {metrics.upsell_suggestions > 0
                    ? pct(metrics.upsell_accepted / metrics.upsell_suggestions)
                    : '—'}
                </p>
                <p className="mt-1 text-xs text-muted">
                  {metrics.upsell_accepted} accepted of {metrics.upsell_suggestions} offered
                </p>
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="Needs attention" actions={<Link to="/handoffs"><Button variant="secondary" size="sm">View queue</Button></Link>} />
              <CardBody>
                <p className="text-2xl font-semibold text-fg">{metrics.handoff_conversations}</p>
                <p className="mt-1 text-xs text-muted">Conversations escalated to a human</p>
              </CardBody>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
