import { useQuery } from '@tanstack/react-query';

import { HubPage } from '../components/shell/HubPage';
import { Card, CardHeader } from '../components/ui';
import { DataTable } from '../components/data';
import type { Column } from '../components/data';
import { PostRevenueInsightPanel } from '../components/revenue/PostRevenueInsightPanel';
import { buildPostRevenueInsights } from '../lib/revenueRecovery';
import type { RevenueRecoveryAggregationInput } from '../types/sprint4Revenue';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';

interface PostRevenueRow {
  instagram_post_url: string;
  conversations: number;
  draft_orders: number;
  paid_orders: number;
  revenue: string | number;
  conversion_rate: number;
  abandoned_rate: number;
}

export function PostRevenueAnalyticsPage() {
  const { selectedShopId } = useShop();

  const revenue = useQuery({
    queryKey: ['post-revenue', selectedShopId],
    queryFn: () => apiClient.getPostRevenueAnalytics(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const columns: Column<PostRevenueRow>[] = [
    {
      key: 'post',
      header: 'Post',
      render: (row) => (
        <a href={row.instagram_post_url} target="_blank" rel="noreferrer" className="text-accent hover:underline">
          {row.instagram_post_url}
        </a>
      ),
    },
    { key: 'conversations', header: 'Conversations', align: 'right', render: (row) => row.conversations },
    { key: 'drafts', header: 'Draft orders', align: 'right', className: 'hidden sm:table-cell', render: (row) => row.draft_orders },
    { key: 'paid', header: 'Paid', align: 'right', render: (row) => row.paid_orders },
    { key: 'revenue', header: 'Revenue', align: 'right', render: (row) => <span className="tabular-nums font-medium">{row.revenue}</span> },
    {
      key: 'conversion',
      header: 'Conversion',
      align: 'right',
      className: 'hidden md:table-cell',
      render: (row) => <span className="tabular-nums">{(row.conversion_rate * 100).toFixed(1)}%</span>,
    },
    {
      key: 'abandoned',
      header: 'Abandoned',
      align: 'right',
      className: 'hidden lg:table-cell',
      render: (row) => <span className="tabular-nums">{(row.abandoned_rate * 100).toFixed(1)}%</span>,
    },
  ];

  return (
    <HubPage
      eyebrow="Analytics"
      title="Post revenue"
      description="Conversations, orders, revenue, conversion, and abandonment by Instagram post."
    >
      <Card>
        <CardHeader title="Performance by post" />
        <DataTable
          columns={columns}
          rows={revenue.data ?? []}
          rowKey={(row) => row.instagram_post_url}
          isLoading={revenue.isLoading}
          error={revenue.error instanceof Error ? revenue.error.message : null}
          emptyTitle="No post-attributed conversations yet"
        />
      </Card>

      {/* Sprint 4 (additive): post-to-revenue insights from the same query. */}
      <PostRevenueInsightPanel
        insights={buildPostRevenueInsights({
          shopId: selectedShopId ?? '',
          postRevenue: revenue.data ?? null,
        } as Pick<RevenueRecoveryAggregationInput, 'shopId' | 'postRevenue'>)}
        isLoading={revenue.isLoading}
        error={revenue.error instanceof Error ? revenue.error.message : null}
      />
    </HubPage>
  );
}
