import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';

import { BarSeries } from '../components/charts/ChartKit';
import { Card, CardBody, CardHeader } from '../components/ui';
import { DataTable, LoadingState, EmptyState } from '../components/data';
import type { Column } from '../components/data';
import { ChannelBadge } from '../components/inbox/ChannelBadge';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';
import { queryKeys } from '../lib/queryClient';

interface ChannelRow {
  channel: string;
  conversations: number;
  handoffs: number;
  withOrders: number;
  automationRate: number;
}

export function ChannelAnalyticsPage() {
  const { selectedShopId } = useShop();

  const conversationsQuery = useQuery({
    queryKey: queryKeys.conversations(selectedShopId, { is_simulation: false }),
    queryFn: () => apiClient.listConversations(selectedShopId, {}),
    enabled: Boolean(selectedShopId),
  });

  const rows = useMemo<ChannelRow[]>(() => {
    const map = new Map<string, ChannelRow>();
    for (const conversation of conversationsQuery.data ?? []) {
      const channel = conversation.channel_provider ?? 'instagram';
      const row = map.get(channel) ?? {
        channel,
        conversations: 0,
        handoffs: 0,
        withOrders: 0,
        automationRate: 0,
      };
      row.conversations += 1;
      if (conversation.handoff_required) row.handoffs += 1;
      if (conversation.linked_order) row.withOrders += 1;
      map.set(channel, row);
    }
    return [...map.values()]
      .map((row) => ({
        ...row,
        automationRate: row.conversations > 0 ? Math.round(((row.conversations - row.handoffs) / row.conversations) * 100) : 0,
      }))
      .sort((a, b) => b.conversations - a.conversations);
  }, [conversationsQuery.data]);

  const columns: Column<ChannelRow>[] = [
    {
      key: 'channel',
      header: 'Channel',
      render: (row) => <ChannelBadge channel={row.channel} showLabel />,
    },
    { key: 'conversations', header: 'Conversations', align: 'right', render: (row) => row.conversations.toLocaleString() },
    { key: 'withOrders', header: 'With orders', align: 'right', render: (row) => row.withOrders.toLocaleString() },
    { key: 'handoffs', header: 'Handoffs', align: 'right', render: (row) => row.handoffs.toLocaleString() },
    { key: 'automationRate', header: 'Automation', align: 'right', render: (row) => `${row.automationRate}%` },
  ];

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader title="Channel performance" description="Conversation volume and automation health per channel." />
        <CardBody>
          {conversationsQuery.isLoading ? (
            <LoadingState />
          ) : rows.length === 0 ? (
            <EmptyState title="No channel activity" />
          ) : (
            <BarSeries
              data={rows.map((row) => ({ channel: row.channel, Conversations: row.conversations, Orders: row.withOrders }))}
              xKey="channel"
              series={[
                { key: 'Conversations', label: 'Conversations' },
                { key: 'Orders', label: 'With orders', color: 'var(--c-success)' },
              ]}
              height={260}
            />
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Channel breakdown" />
        <DataTable columns={columns} rows={rows} rowKey={(row) => row.channel} isLoading={conversationsQuery.isLoading} emptyTitle="No channels" />
      </Card>
    </div>
  );
}
