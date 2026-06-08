import { FormEvent, useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
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
    onError: (error) =>
      showToast(error instanceof Error ? error.message : 'Failed to create trigger', 'error'),
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
    setResponseTemplate(
      'Thanks! I sent you product details here. Which color and size do you want?',
    );
    setInstagramMediaId('');
    setTargetProductId('');
    setSourceType('comment');
  }

  const selectedSource = SOURCE_OPTIONS.find((option) => option.value === sourceType);
  const canSubmit = Boolean(selectedShopId && instagramAccountId && keyword.trim() && !create.isPending);

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Instagram growth-to-order</p>
        <h1>Trigger rules</h1>
        <p>
          Turn comments, story replies, reels, ads, and direct DM keywords into order-ready
          conversations.
        </p>
        <ShopSelector />
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Create trigger</h2>
        <p className="analytics-toolbar__summary">
          Match a keyword on a specific Instagram source, then send a templated DM to start the order
          flow.
        </p>

        {!selectedShopId ? (
          <p className="empty-state">Select a shop to configure trigger rules.</p>
        ) : accounts.isLoading ? (
          <p className="loading-state">Loading Instagram accounts...</p>
        ) : (accounts.data?.length ?? 0) === 0 ? (
          <p className="empty-state">
            No Instagram accounts connected. Add one under Instagram Accounts before creating
            triggers.
          </p>
        ) : (
          <form className="trigger-rules-form" onSubmit={submit}>
            <div className="filter-grid">
              <label className="form-field">
                <span>Instagram account</span>
                <select
                  value={instagramAccountId}
                  onChange={(event) => setInstagramAccountId(event.target.value)}
                  required
                >
                  <option value="">Select account</option>
                  {accounts.data?.map((account) => (
                    <option key={account.id} value={account.id}>
                      @{account.username}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                <span>Source</span>
                <select
                  value={sourceType}
                  onChange={(event) => setSourceType(event.target.value as SourceType)}
                >
                  {SOURCE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                <span>Keyword</span>
                <input
                  value={keyword}
                  onChange={(event) => setKeyword(event.target.value)}
                  placeholder="price"
                  required
                />
              </label>

              <label className="form-field">
                <span>Instagram media ID</span>
                <input
                  value={instagramMediaId}
                  onChange={(event) => setInstagramMediaId(event.target.value)}
                  placeholder="Optional post or reel ID"
                />
              </label>

              <label className="form-field">
                <span>Target product</span>
                <select
                  value={targetProductId}
                  onChange={(event) => setTargetProductId(event.target.value)}
                  disabled={products.isLoading}
                >
                  <option value="">
                    {products.isLoading ? 'Loading products…' : 'No product attached'}
                  </option>
                  {products.data?.map((product) => (
                    <option key={product.id} value={product.id}>
                      {product.title}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field form-field--wide">
                <span>DM response template</span>
                <textarea
                  value={responseTemplate}
                  onChange={(event) => setResponseTemplate(event.target.value)}
                  rows={4}
                  placeholder="Thanks! Which color and size do you want?"
                  required
                />
              </label>
            </div>

            {selectedSource ? (
              <p className="analytics-toolbar__summary">{selectedSource.hint}</p>
            ) : null}

            <div className="form-field trigger-rules-form__examples">
              <span>Example keywords</span>
              <div className="filter-chips" role="group" aria-label="Example keywords">
                {KEYWORD_EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    className={`filter-chip${keyword === example ? ' filter-chip--active' : ''}`}
                    aria-pressed={keyword === example}
                    onClick={() => setKeyword(example)}
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>

            <div className="button-row">
              <button className="button button--primary" type="submit" disabled={!canSubmit}>
                {create.isPending ? 'Creating…' : 'Create trigger'}
              </button>
              <button className="button button--ghost-dark" type="button" onClick={resetForm}>
                Reset form
              </button>
            </div>
          </form>
        )}

        {create.error ? (
          <p className="form-error">
            {create.error instanceof Error ? create.error.message : 'Failed to create trigger'}
          </p>
        ) : null}
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Active rules</h2>
        {rules.isLoading ? <p className="loading-state">Loading trigger rules...</p> : null}
        {rules.error ? (
          <p className="form-error">
            {rules.error instanceof Error ? rules.error.message : 'Failed to load trigger rules'}
          </p>
        ) : null}
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Keyword</th>
                <th>Media scope</th>
                <th>Product</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rules.data?.map((rule) => (
                <tr key={rule.id}>
                  <td>{formatSourceType(rule.source_type)}</td>
                  <td>{rule.keyword}</td>
                  <td>{rule.instagram_media_id ?? 'All media'}</td>
                  <td>
                    {rule.target_product_id
                      ? (products.data?.find((product) => product.id === rule.target_product_id)
                          ?.title ?? rule.target_product_id)
                      : 'No product attached'}
                  </td>
                  <td>{rule.is_active ? 'Active' : 'Paused'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rules.isLoading && (rules.data?.length ?? 0) === 0 ? (
            <p className="empty-state">No trigger rules yet. Create one above.</p>
          ) : null}
        </div>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <h2>Trigger performance</h2>
        {performance.isLoading ? <p className="loading-state">Loading performance...</p> : null}
        {performance.error ? (
          <p className="form-error">
            {performance.error instanceof Error
              ? performance.error.message
              : 'Failed to load performance'}
          </p>
        ) : null}
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Keyword</th>
                <th>Matches</th>
                <th>DMs sent</th>
                <th>Paid orders</th>
                <th>Conversion</th>
                <th>Revenue</th>
              </tr>
            </thead>
            <tbody>
              {performance.data?.map((row) => (
                <tr key={row.trigger_id}>
                  <td>{row.keyword}</td>
                  <td>{row.impressions}</td>
                  <td>{row.dm_sent}</td>
                  <td>{row.paid_orders}</td>
                  <td>{Math.round(row.conversion_rate * 100)}%</td>
                  <td>{row.revenue}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!performance.isLoading && (performance.data?.length ?? 0) === 0 ? (
            <p className="empty-state">No performance data yet.</p>
          ) : null}
        </div>
      </section>
    </div>
  );
}
