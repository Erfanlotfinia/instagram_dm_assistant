import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input, Select } from '../components/ui';
import { DataTable, EmptyState, LoadingState } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { cn } from '../lib/cn';
import { apiClient } from '../services/apiClient';
import type { TriggerRule } from '../types/competitive';

type SourceType = TriggerRule['source_type'];

const SOURCE_OPTIONS: { value: SourceType; label: string; hint: string }[] = [
  { value: 'comment', label: 'Comment', hint: 'Keyword on a post comment' },
  { value: 'story_reply', label: 'Story reply', hint: 'Reply to an Instagram story' },
  { value: 'reel_comment', label: 'Reel comment', hint: 'Comment on a reel' },
  { value: 'direct_dm', label: 'Direct DM', hint: 'Incoming DM keyword match' },
  { value: 'ad_comment', label: 'Ad comment', hint: 'Comment on a boosted post or ad' },
];

const KEYWORD_EXAMPLES = ['price', 'order', 'سایز', 'رنگ', 'available'] as const;

function formatSourceType(value: string): string {
  return SOURCE_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

function Chip({ active, onClick, children }: { active?: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
        active ? 'border-accent bg-accent-soft text-accent' : 'border-border bg-surface text-muted hover:text-fg',
      )}
    >
      {children}
    </button>
  );
}

interface PerformanceRow {
  trigger_id: string;
  keyword: string;
  impressions: number;
  dm_sent: number;
  paid_orders: number;
  conversion_rate: number;
  revenue: string | number;
}

export function TriggerRulesPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const accounts = useQuery({
    queryKey: ['instagram-accounts', selectedShopId],
    queryFn: () => apiClient.listInstagramAccounts(selectedShopId),
    enabled: Boolean(selectedShopId),
  });
  const products = useQuery({
    queryKey: queryKeys.products(selectedShopId),
    queryFn: () => apiClient.listProducts(selectedShopId),
    enabled: Boolean(selectedShopId),
  });
  const rules = useQuery({
    queryKey: ['trigger-rules', selectedShopId],
    queryFn: () => apiClient.listTriggerRules(selectedShopId),
    enabled: Boolean(selectedShopId),
  });
  const performance = useQuery({
    queryKey: ['trigger-performance', selectedShopId],
    queryFn: () => apiClient.getTriggerPerformance(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const [instagramAccountId, setInstagramAccountId] = useState('');
  const [keyword, setKeyword] = useState('price');
  const [responseTemplate, setResponseTemplate] = useState(
    'Thanks! I sent you product details here. Which color and size do you want?',
  );
  const [instagramMediaId, setInstagramMediaId] = useState('');
  const [targetProductId, setTargetProductId] = useState('');
  const [sourceType, setSourceType] = useState<SourceType>('comment');

  useEffect(() => {
    if (!instagramAccountId && accounts.data?.length) {
      setInstagramAccountId(accounts.data[0].id);
    }
  }, [accounts.data, instagramAccountId]);

  const create = useMutation({
    mutationFn: () =>
      apiClient.createTriggerRule(selectedShopId, {
        instagram_account_id: instagramAccountId,
        instagram_media_id: instagramMediaId || null,
        source_type: sourceType,
        keyword,
        response_template: responseTemplate,
        target_product_id: targetProductId || null,
        is_active: true,
      }),
    onSuccess: () => {
      showToast('Trigger rule created.', 'success');
      queryClient.invalidateQueries({ queryKey: ['trigger-rules', selectedShopId] });
      queryClient.invalidateQueries({ queryKey: ['trigger-performance', selectedShopId] });
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to create trigger', 'error'),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!instagramAccountId) {
      showToast('Connect an Instagram account before creating triggers.', 'error');
      return;
    }
    create.mutate();
  }

  function resetForm() {
    setKeyword('price');
    setResponseTemplate('Thanks! I sent you product details here. Which color and size do you want?');
    setInstagramMediaId('');
    setTargetProductId('');
    setSourceType('comment');
  }

  const selectedSource = SOURCE_OPTIONS.find((option) => option.value === sourceType);
  const canSubmit = Boolean(selectedShopId && instagramAccountId && keyword.trim() && !create.isPending);

  const ruleColumns: Column<TriggerRule>[] = [
    { key: 'source', header: 'Source', render: (rule) => formatSourceType(rule.source_type) },
    { key: 'keyword', header: 'Keyword', render: (rule) => <span className="font-medium">{rule.keyword}</span> },
    {
      key: 'media',
      header: 'Media scope',
      className: 'hidden md:table-cell',
      render: (rule) => rule.instagram_media_id ?? 'All media',
    },
    {
      key: 'product',
      header: 'Product',
      render: (rule) =>
        rule.target_product_id
          ? products.data?.find((product) => product.id === rule.target_product_id)?.title ?? rule.target_product_id
          : 'No product attached',
    },
    {
      key: 'status',
      header: 'Status',
      align: 'right',
      render: (rule) => <Badge tone={rule.is_active ? 'success' : 'neutral'}>{rule.is_active ? 'Active' : 'Paused'}</Badge>,
    },
  ];

  const perfColumns: Column<PerformanceRow>[] = [
    { key: 'keyword', header: 'Keyword', render: (row) => row.keyword },
    { key: 'matches', header: 'Matches', align: 'right', render: (row) => row.impressions },
    { key: 'dms', header: 'DMs sent', align: 'right', className: 'hidden sm:table-cell', render: (row) => row.dm_sent },
    { key: 'paid', header: 'Paid orders', align: 'right', render: (row) => row.paid_orders },
    {
      key: 'conversion',
      header: 'Conversion',
      align: 'right',
      className: 'hidden md:table-cell',
      render: (row) => `${Math.round(row.conversion_rate * 100)}%`,
    },
    { key: 'revenue', header: 'Revenue', align: 'right', render: (row) => row.revenue },
  ];

  return (
    <HubPage
      eyebrow="Automation"
      title="Trigger rules"
      description="Turn comments, story replies, reels, ads, and DM keywords into order-ready conversations."
    >
      <Card>
        <CardHeader title="Create trigger" description="Match a keyword on a specific Instagram source, then send a templated DM." />
        <CardBody>
          {!selectedShopId ? (
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          ) : accounts.isLoading ? (
            <LoadingState label="Loading Instagram accounts…" />
          ) : (accounts.data?.length ?? 0) === 0 ? (
            <EmptyState
              title="No Instagram accounts"
              description="Connect an account under System → Channels before creating triggers."
            />
          ) : (
            <form className="flex flex-col gap-4" onSubmit={submit}>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Field label="Instagram account">
                  <Select value={instagramAccountId} onChange={(e) => setInstagramAccountId(e.target.value)} required>
                    <option value="">Select account</option>
                    {accounts.data?.map((account) => (
                      <option key={account.id} value={account.id}>@{account.username}</option>
                    ))}
                  </Select>
                </Field>
                <Field label="Source">
                  <Select value={sourceType} onChange={(e) => setSourceType(e.target.value as SourceType)}>
                    {SOURCE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                  </Select>
                </Field>
                <Field label="Keyword">
                  <Input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="price" required />
                </Field>
                <Field label="Instagram media ID">
                  <Input value={instagramMediaId} onChange={(e) => setInstagramMediaId(e.target.value)} placeholder="Optional post or reel ID" />
                </Field>
                <Field label="Target product">
                  <Select value={targetProductId} onChange={(e) => setTargetProductId(e.target.value)} disabled={products.isLoading}>
                    <option value="">{products.isLoading ? 'Loading products…' : 'No product attached'}</option>
                    {products.data?.map((product) => (
                      <option key={product.id} value={product.id}>{product.title}</option>
                    ))}
                  </Select>
                </Field>
              </div>

              <Field label="DM response template">
                <textarea
                  value={responseTemplate}
                  onChange={(e) => setResponseTemplate(e.target.value)}
                  rows={4}
                  placeholder="Thanks! Which color and size do you want?"
                  required
                  className="w-full resize-y rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg focus:border-accent focus:outline-none"
                />
              </Field>

              {selectedSource ? <p className="text-xs text-muted">{selectedSource.hint}</p> : null}

              <Field label="Example keywords">
                <div className="flex flex-wrap gap-2" role="group" aria-label="Example keywords">
                  {KEYWORD_EXAMPLES.map((example) => (
                    <Chip key={example} active={keyword === example} onClick={() => setKeyword(example)}>
                      {example}
                    </Chip>
                  ))}
                </div>
              </Field>

              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={!canSubmit}>
                  {create.isPending ? 'Creating…' : 'Create trigger'}
                </Button>
                <Button type="button" variant="secondary" onClick={resetForm}>Reset form</Button>
              </div>

              {create.error ? (
                <p className="text-sm text-danger">
                  {create.error instanceof Error ? create.error.message : 'Failed to create trigger'}
                </p>
              ) : null}
            </form>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Active rules" />
        <DataTable
          columns={ruleColumns}
          rows={rules.data ?? []}
          rowKey={(rule) => rule.id}
          isLoading={rules.isLoading}
          error={rules.error instanceof Error ? rules.error.message : null}
          emptyTitle="No trigger rules yet"
        />
      </Card>

      <Card>
        <CardHeader title="Trigger performance" />
        <DataTable
          columns={perfColumns}
          rows={(performance.data ?? []) as PerformanceRow[]}
          rowKey={(row) => row.trigger_id}
          isLoading={performance.isLoading}
          error={performance.error instanceof Error ? performance.error.message : null}
          emptyTitle="No performance data yet"
        />
      </Card>
    </HubPage>
  );
}
