import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';
import type { TriggerRule } from '../types/competitive';

export function TriggerRulesPage() {
  const { selectedShopId } = useShop();
  const queryClient = useQueryClient();
  const accounts = useQuery({ queryKey: ['instagram-accounts', selectedShopId], queryFn: () => apiClient.listInstagramAccounts(selectedShopId), enabled: Boolean(selectedShopId) });
  const rules = useQuery({ queryKey: ['trigger-rules', selectedShopId], queryFn: () => apiClient.listTriggerRules(selectedShopId), enabled: Boolean(selectedShopId) });
  const performance = useQuery({ queryKey: ['trigger-performance', selectedShopId], queryFn: () => apiClient.getTriggerPerformance(selectedShopId), enabled: Boolean(selectedShopId) });
  const [keyword, setKeyword] = useState('price');
  const [responseTemplate, setResponseTemplate] = useState('Thanks! I sent you product details here. Which color and size do you want?');
  const [instagramMediaId, setInstagramMediaId] = useState('');
  const [targetProductId, setTargetProductId] = useState('');
  const [sourceType, setSourceType] = useState('comment');
  const create = useMutation({
    mutationFn: () => apiClient.createTriggerRule(selectedShopId, {
      instagram_account_id: accounts.data?.[0]?.id,
      instagram_media_id: instagramMediaId || null,
      source_type: sourceType as TriggerRule['source_type'],
      keyword,
      response_template: responseTemplate,
      target_product_id: targetProductId || null,
      is_active: true,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trigger-rules', selectedShopId] });
      queryClient.invalidateQueries({ queryKey: ['trigger-performance', selectedShopId] });
    },
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }
  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide"><p className="dashboard-card__eyebrow">Instagram growth-to-order</p><h1>Trigger rules</h1><p>Turn comments, story replies, reels, ads, and direct DM keywords into order-ready conversations.</p><ShopSelector /></section>
      <section className="dashboard-card dashboard-card--wide"><h2>Create trigger</h2><form className="form-grid" onSubmit={submit}>
        <label>Source<select value={sourceType} onChange={(e) => setSourceType(e.target.value)}><option value="comment">Comment</option><option value="story_reply">Story reply</option><option value="reel_comment">Reel comment</option><option value="direct_dm">Direct DM</option><option value="ad_comment">Ad comment</option></select></label>
        <label>Keyword<input value={keyword} onChange={(e) => setKeyword(e.target.value)} /></label>
        <label>Instagram media id<input value={instagramMediaId} onChange={(e) => setInstagramMediaId(e.target.value)} placeholder="optional post/reel id" /></label>
        <label>Target product id<input value={targetProductId} onChange={(e) => setTargetProductId(e.target.value)} placeholder="optional" /></label>
        <label>DM response<textarea value={responseTemplate} onChange={(e) => setResponseTemplate(e.target.value)} /></label>
        <button type="submit" disabled={create.isPending || !accounts.data?.length}>Create trigger</button>
      </form></section>
      <section className="dashboard-card dashboard-card--wide"><h2>Active rules</h2><table className="data-table"><tbody>{rules.data?.map((rule) => <tr key={rule.id}><td>{rule.source_type}</td><td>{rule.keyword}</td><td>{rule.instagram_media_id ?? 'All media'}</td><td>{rule.target_product_id ?? 'No product attached'}</td><td>{rule.is_active ? 'Active' : 'Paused'}</td></tr>)}</tbody></table></section>
      <section className="dashboard-card dashboard-card--wide"><h2>Trigger performance</h2><table className="data-table"><tbody>{performance.data?.map((row) => <tr key={row.trigger_id}><td>{row.keyword}</td><td>{row.impressions} matches</td><td>{row.dm_sent} DMs</td><td>{row.paid_orders} paid</td><td>{Math.round(row.conversion_rate * 100)}%</td><td>{row.revenue}</td></tr>)}</tbody></table></section>
    </div>
  );
}
