import { FormEvent, useState } from 'react';
import { useMutation } from '@tanstack/react-query';

import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';

export function VariantResolverPage() {
  const { selectedShop } = useShop();
  const [productId, setProductId] = useState('');
  const [rawColor, setRawColor] = useState('');
  const [rawSize, setRawSize] = useState('');
  const [quantity, setQuantity] = useState(1);
  const resolver = useMutation({ mutationFn: () => apiClient.testVariantResolver(selectedShop!.id, { product_id: productId, raw_color: rawColor, raw_size: rawSize, quantity }) });
  function submit(event: FormEvent) { event.preventDefault(); if (selectedShop) resolver.mutate(); }
  return <div className="page-stack"><header><p className="eyebrow">Sprint A</p><h1>Variant Resolver Test</h1><p>Test backend-only normalization, variant matching, stock checks, and alternatives without using the LLM.</p></header><section className="dashboard-card"><form onSubmit={submit} className="form-grid"><label>Product ID<input value={productId} onChange={(e) => setProductId(e.target.value)} required /></label><label>Raw color<input value={rawColor} onChange={(e) => setRawColor(e.target.value)} placeholder="سیاه" /></label><label>Raw size<input value={rawSize} onChange={(e) => setRawSize(e.target.value)} placeholder="L" /></label><label>Quantity<input type="number" min={1} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} /></label><button type="submit">Run resolver</button></form>{resolver.data && <pre className="code-block">{JSON.stringify(resolver.data, null, 2)}</pre>}</section></div>;
}
