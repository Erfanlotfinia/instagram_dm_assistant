import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { FunnelBars, HandoffReasonBars } from '../components/charts/ChartKit';
import { Badge, Button, Card, CardBody, CardHeader } from '../components/ui';
import { KpiCard, LoadingState, EmptyState, ErrorState } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';

type Preset = '7d' | '30d' | '90d' | 'all';

function rangeFor(preset: Preset): { from?: string; to?: string } {
  if (preset === 'all') return {};
  const days = preset === '7d' ? 7 : preset === '30d' ? 30 : 90;
  const to = new Date();
  const from = new Date();
  from.setDate(to.getDate() - (days - 1));
  from.setHours(0, 0, 0, 0);
  to.setHours(23, 59, 59, 999);
  return { from: from.toISOString(), to: to.toISOString() };
}

const PRESETS: Preset[] = ['7d', '30d', '90d', 'all'];

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function fmtSeconds(value?: number | null, loading = false): string {
  if (loading) return '…';
  if (value == null) return '—';
  if (value < 60) return `${Math.round(value)}s`;
  if (value < 3600) return `${Math.round(value / 60)}m`;
  return `${(value / 3600).toFixed(1)}h`;
}

function kpiValue(loading: boolean, loaded: boolean, render: () => string | number): string | number {
  if (loading) return '…';
  if (!loaded) return '—';
  return render();
}

export function AnalyticsOverviewPage() {
  const { selectedShopId } = useShop();
  const [preset, setPreset] = useState<Preset>('30d');
  const range = rangeFor(preset);
  const queriesEnabled = Boolean(selectedShopId);

  const funnel = useQuery({
    queryKey: ['analytics-funnel', selectedShopId, range.from, range.to],
    queryFn: () => apiClient.getAnalyticsFunnel(selectedShopId, range.from, range.to),
    enabled: queriesEnabled,
  });
  const agent = useQuery({
    queryKey: ['analytics-agent', selectedShopId, range.from, range.to],
    queryFn: () => apiClient.getAnalyticsAgentPerformance(selectedShopId, range.from, range.to),
    enabled: queriesEnabled,
  });
  const handoff = useQuery({
    queryKey: ['analytics-handoff', selectedShopId, range.from, range.to],
    queryFn: () => apiClient.getAnalyticsHandoff(selectedShopId, range.from, range.to),
    enabled: queriesEnabled,
  });
  const responseTime = useQuery({
    queryKey: ['analytics-response', selectedShopId, range.from, range.to],
    queryFn: () => apiClient.getAnalyticsResponseTime(selectedShopId, range.from, range.to),
    enabled: queriesEnabled,
  });

  const funnelData = funnel.data;
  const handoffRows = handoff.data ?? [];
  const totalHandoffs = useMemo(
    () => handoffRows.reduce((sum, row) => sum + row.count, 0),
    [handoffRows],
  );
  const isLoading = funnel.isLoading || agent.isLoading || handoff.isLoading || responseTime.isLoading;
  const queryError =
    funnel.error ?? agent.error ?? handoff.error ?? responseTime.error ?? null;
  const errorMessage =
    queryError instanceof Error ? queryError.message : queryError ? 'Failed to load analytics' : null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <div className="inline-flex rounded-lg border border-border p-0.5">
          {PRESETS.map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setPreset(value)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                preset === value ? 'bg-accent text-accent-fg' : 'text-muted hover:text-fg'
              }`}
            >
              {value === 'all' ? 'All time' : `Last ${value.replace('d', ' days')}`}
            </button>
          ))}
        </div>
      </div>

      {!selectedShopId ? (
        <EmptyState title="Select a shop" description="Choose a shop to view analytics." />
      ) : null}

      {errorMessage ? <ErrorState message={errorMessage} /> : null}

      {selectedShopId ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <KpiCard
              label="Payment conversion"
              value={kpiValue(funnel.isLoading, Boolean(funnelData), () =>
                pct(funnelData?.payment_conversion_rate ?? 0),
              )}
              tone="success"
            />
            <KpiCard
              label="Auto-sent messages"
              value={kpiValue(agent.isLoading, agent.isSuccess, () => agent.data?.auto_sent_messages ?? 0)}
            />
            <KpiCard
              label="Handoff rate"
              value={kpiValue(agent.isLoading, agent.isSuccess, () => pct(agent.data?.handoff_rate ?? 0))}
              tone="danger"
            />
            <KpiCard
              label="Avg first response"
              value={fmtSeconds(responseTime.data?.average_first_response_time_seconds, responseTime.isLoading)}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader title="Conversion funnel" description="From inbound message to paid order." />
              <CardBody>
                {funnel.isLoading ? (
                  <LoadingState />
                ) : funnel.isError ? (
                  <EmptyState title="Could not load funnel" />
                ) : funnelData ? (
                  <FunnelBars
                    steps={[
                      { label: 'Inbound messages', value: funnelData.inbound_messages },
                      { label: 'Product resolved', value: funnelData.product_resolved_count ?? 0 },
                      { label: 'Variant resolved', value: funnelData.variant_resolved_count ?? 0 },
                      { label: 'Draft orders', value: funnelData.draft_orders ?? 0 },
                      { label: 'Paid orders', value: funnelData.paid_orders },
                    ]}
                  />
                ) : (
                  <EmptyState title="No funnel data" />
                )}
              </CardBody>
            </Card>

            <Card>
              <CardHeader
                title="Handoff reasons"
                description="Why conversations escalate to humans."
                actions={
                  handoff.isSuccess && totalHandoffs > 0 ? (
                    <div className="flex items-center gap-2">
                      <Badge tone="danger" dot>
                        {totalHandoffs.toLocaleString()}
                      </Badge>
                      <Link to="/handoffs">
                        <Button variant="secondary" size="sm">
                          View queue
                        </Button>
                      </Link>
                    </div>
                  ) : null
                }
              />
              <CardBody>
                {handoff.isLoading ? (
                  <LoadingState label="Loading handoffs…" />
                ) : handoff.isError ? (
                  <EmptyState title="Could not load handoffs" description="Try refreshing the page." />
                ) : handoffRows.length === 0 ? (
                  <EmptyState
                    title="No handoffs recorded"
                    description="Automation handled every conversation in this period."
                  />
                ) : (
                  <HandoffReasonBars rows={handoffRows} />
                )}
              </CardBody>
            </Card>
          </div>

          <Card>
            <CardHeader title="Response time" description="Average time across the order lifecycle." />
            <CardBody>
              {responseTime.isLoading ? (
                <LoadingState />
              ) : (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-lg border border-border p-4">
                    <p className="text-xs text-subtle">First response</p>
                    <p className="mt-1 text-xl font-semibold text-fg">
                      {fmtSeconds(responseTime.data?.average_first_response_time_seconds)}
                    </p>
                  </div>
                  <div className="rounded-lg border border-border p-4">
                    <p className="text-xs text-subtle">Time to draft order</p>
                    <p className="mt-1 text-xl font-semibold text-fg">
                      {fmtSeconds(responseTime.data?.average_time_to_draft_order_seconds)}
                    </p>
                  </div>
                  <div className="rounded-lg border border-border p-4">
                    <p className="text-xs text-subtle">Time to payment</p>
                    <p className="mt-1 text-xl font-semibold text-fg">
                      {fmtSeconds(responseTime.data?.average_time_to_payment_seconds)}
                    </p>
                  </div>
                </div>
              )}
            </CardBody>
          </Card>

          {isLoading && !errorMessage ? (
            <p className="text-center text-xs text-subtle">Refreshing analytics…</p>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
