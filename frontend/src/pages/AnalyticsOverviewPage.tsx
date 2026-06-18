import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { BarSeries, FunnelBars } from '../components/charts/ChartKit';
import { Card, CardBody, CardHeader } from '../components/ui';
import { KpiCard, LoadingState, EmptyState } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';

type Preset = '7d' | '30d' | '90d' | 'all';

function rangeFor(preset: Preset): { from?: string; to?: string } {
  if (preset === 'all') return {};
  const days = preset === '7d' ? 7 : preset === '30d' ? 30 : 90;
  const to = new Date();
  const from = new Date();
  from.setDate(to.getDate() - (days - 1));
  return { from: from.toISOString(), to: to.toISOString() };
}

const PRESETS: Preset[] = ['7d', '30d', '90d', 'all'];

export function AnalyticsOverviewPage() {
  const { selectedShopId } = useShop();
  const [preset, setPreset] = useState<Preset>('30d');
  const range = rangeFor(preset);

  const funnel = useQuery({
    queryKey: ['analytics-funnel', selectedShopId, range.from, range.to],
    queryFn: () => apiClient.getAnalyticsFunnel(selectedShopId, range.from, range.to),
    enabled: Boolean(selectedShopId),
  });
  const agent = useQuery({
    queryKey: ['analytics-agent', selectedShopId, range.from, range.to],
    queryFn: () => apiClient.getAnalyticsAgentPerformance(selectedShopId, range.from, range.to),
    enabled: Boolean(selectedShopId),
  });
  const handoff = useQuery({
    queryKey: ['analytics-handoff', selectedShopId, range.from, range.to],
    queryFn: () => apiClient.getAnalyticsHandoff(selectedShopId, range.from, range.to),
    enabled: Boolean(selectedShopId),
  });
  const responseTime = useQuery({
    queryKey: ['analytics-response', selectedShopId, range.from, range.to],
    queryFn: () => apiClient.getAnalyticsResponseTime(selectedShopId, range.from, range.to),
    enabled: Boolean(selectedShopId),
  });

  const funnelData = funnel.data;
  const handoffRows = handoff.data ?? [];

  function fmtSeconds(value?: number | null): string {
    if (value == null) return '—';
    if (value < 60) return `${Math.round(value)}s`;
    if (value < 3600) return `${Math.round(value / 60)}m`;
    return `${(value / 3600).toFixed(1)}h`;
  }

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

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard
          label="Payment conversion"
          value={funnelData ? `${Math.round(funnelData.payment_conversion_rate * 100)}%` : '—'}
          tone="success"
        />
        <KpiCard label="Auto-sent messages" value={agent.data?.auto_sent_messages ?? '—'} />
        <KpiCard
          label="Handoff rate"
          value={agent.data ? `${Math.round(agent.data.handoff_rate * 100)}%` : '—'}
          tone="danger"
        />
        <KpiCard label="Avg first response" value={fmtSeconds(responseTime.data?.average_first_response_time_seconds)} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Conversion funnel" description="From inbound message to paid order." />
          <CardBody>
            {funnel.isLoading ? (
              <LoadingState />
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
          <CardHeader title="Handoff reasons" description="Why conversations escalate to humans." />
          <CardBody>
            {handoff.isLoading ? (
              <LoadingState />
            ) : handoffRows.length === 0 ? (
              <EmptyState title="No handoffs recorded" />
            ) : (
              <BarSeries
                data={handoffRows.map((row) => ({ reason: row.reason.replace(/_/g, ' '), count: row.count }))}
                xKey="reason"
                series={[{ key: 'count', label: 'Handoffs' }]}
                layout="vertical"
                height={Math.max(handoffRows.length * 44, 160)}
              />
            )}
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader title="Response time" description="Average time across the order lifecycle." />
        <CardBody>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-border p-4">
              <p className="text-xs text-subtle">First response</p>
              <p className="mt-1 text-xl font-semibold text-fg">{fmtSeconds(responseTime.data?.average_first_response_time_seconds)}</p>
            </div>
            <div className="rounded-lg border border-border p-4">
              <p className="text-xs text-subtle">Time to draft order</p>
              <p className="mt-1 text-xl font-semibold text-fg">{fmtSeconds(responseTime.data?.average_time_to_draft_order_seconds)}</p>
            </div>
            <div className="rounded-lg border border-border p-4">
              <p className="text-xs text-subtle">Time to payment</p>
              <p className="mt-1 text-xl font-semibold text-fg">{fmtSeconds(responseTime.data?.average_time_to_payment_seconds)}</p>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
