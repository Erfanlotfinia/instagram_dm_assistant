import { useState } from 'react';

import { HubPage } from '../components/shell/HubPage';
import { Button, Card, CardBody, CardHeader, Field, Input } from '../components/ui';
import { EmptyState } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';
import type { SemanticSearchHit } from '../types/semanticSearch';

export function SemanticSearchPage() {
  const { selectedShopId } = useShop();
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<SemanticSearchHit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedShopId || !query.trim()) {
      setError('Select a shop and enter a query.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.semanticProductSearch(selectedShopId, query.trim());
      setHits(response.hits);
    } catch (err) {
      setHits([]);
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <HubPage
      eyebrow="Catalog"
      title="Semantic search"
      description="Test Qdrant-backed product matching for the selected shop."
    >
      <Card>
        <CardHeader title="Search" description="Uses the shop switcher in the top bar for context." />
        <CardBody>
          <form className="flex flex-wrap items-end gap-3" onSubmit={handleSearch}>
            <Field label="Query" className="min-w-[16rem] flex-1">
              <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. red summer dress" />
            </Field>
            <Button type="submit" disabled={loading || !selectedShopId}>
              {loading ? 'Searching…' : 'Search'}
            </Button>
          </form>
          {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Results" />
        <CardBody>
          {hits.length === 0 ? (
            <EmptyState title="No results yet" description="Run a search to see semantic matches." />
          ) : (
            <ul className="divide-y divide-border">
              {hits.map((hit) => (
                <li key={hit.product_id} className="py-3 first:pt-0 last:pb-0">
                  <p className="font-medium text-fg">
                    {hit.title} <span className="text-xs text-muted">· score {hit.score.toFixed(3)}</span>
                  </p>
                  {hit.description ? <p className="mt-0.5 text-sm text-muted">{hit.description}</p> : null}
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </HubPage>
  );
}
