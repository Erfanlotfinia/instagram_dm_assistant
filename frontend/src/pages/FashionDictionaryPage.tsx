import { FormEvent, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';

export function FashionDictionaryPage() {
  const { selectedShop } = useShop();
  const shopId = selectedShop?.id;
  const queryClient = useQueryClient();
  const colors = useQuery({ queryKey: ['color-aliases', shopId], queryFn: () => apiClient.listColorAliases(shopId!), enabled: Boolean(shopId) });
  const sizes = useQuery({ queryKey: ['size-aliases', shopId], queryFn: () => apiClient.listSizeAliases(shopId!), enabled: Boolean(shopId) });
  const [colorRaw, setColorRaw] = useState('');
  const [colorNormalized, setColorNormalized] = useState('');
  const [sizeRaw, setSizeRaw] = useState('');
  const [sizeNormalized, setSizeNormalized] = useState('');

  const createColor = useMutation({
    mutationFn: () => apiClient.createColorAlias(shopId!, { raw_value: colorRaw, normalized_value: colorNormalized, language: 'und' }),
    onSuccess: () => { setColorRaw(''); setColorNormalized(''); queryClient.invalidateQueries({ queryKey: ['color-aliases', shopId] }); },
  });
  const createSize = useMutation({
    mutationFn: () => apiClient.createSizeAlias(shopId!, { raw_value: sizeRaw, normalized_value: sizeNormalized, category: null }),
    onSuccess: () => { setSizeRaw(''); setSizeNormalized(''); queryClient.invalidateQueries({ queryKey: ['size-aliases', shopId] }); },
  });

  function submitColor(event: FormEvent) { event.preventDefault(); if (shopId) createColor.mutate(); }
  function submitSize(event: FormEvent) { event.preventDefault(); if (shopId) createSize.mutate(); }

  return (
    <div className="page-stack">
      <header><p className="eyebrow">Sprint A</p><h1>Fashion Dictionary</h1><p>Manage deterministic color and size aliases. Shop aliases override global defaults.</p></header>
      <section className="dashboard-grid">
        <div className="dashboard-card"><h2>Color Aliases</h2><form onSubmit={submitColor} className="inline-form"><input aria-label="Raw color" value={colorRaw} onChange={(e) => setColorRaw(e.target.value)} placeholder="مشکی" /><input aria-label="Normalized color" value={colorNormalized} onChange={(e) => setColorNormalized(e.target.value)} placeholder="black" /><button type="submit">Add color alias</button></form><table className="data-table"><tbody>{colors.data?.map((alias) => <tr key={alias.id}><td>{alias.raw_value}</td><td>{alias.normalized_value}</td><td>{alias.shop_id ? 'Shop' : 'Global'}</td></tr>)}</tbody></table></div>
        <div className="dashboard-card"><h2>Size Aliases</h2><form onSubmit={submitSize} className="inline-form"><input aria-label="Raw size" value={sizeRaw} onChange={(e) => setSizeRaw(e.target.value)} placeholder="فری سایز" /><input aria-label="Normalized size" value={sizeNormalized} onChange={(e) => setSizeNormalized(e.target.value)} placeholder="FREE" /><button type="submit">Add size alias</button></form><table className="data-table"><tbody>{sizes.data?.map((alias) => <tr key={alias.id}><td>{alias.raw_value}</td><td>{alias.normalized_value}</td><td>{alias.category ?? 'Any category'}</td></tr>)}</tbody></table></div>
      </section>
    </div>
  );
}
