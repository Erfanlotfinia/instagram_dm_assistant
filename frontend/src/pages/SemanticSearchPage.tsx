import { useState } from 'react';

import { apiClient } from '../services/apiClient';
import type { SemanticSearchHit } from '../types/semanticSearch';

export function SemanticSearchPage() {
  const [shopId, setShopId] = useState('');
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState<SemanticSearchHit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    if (!shopId.trim() || !query.trim()) {
      setError('Shop ID and query are required.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.semanticProductSearch(shopId.trim(), query.trim());
      setHits(response.hits);
    } catch (err) {
      setHits([]);
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="dashboard-card">
        <p className="dashboard-card__eyebrow">Admin tool</p>
        <h1>Product semantic search</h1>
        <p>Test Qdrant-backed product matching for a shop.</p>
        <form className="form-grid" onSubmit={handleSearch}>
          <label>
            Shop ID
            <input value={shopId} onChange={(event) => setShopId(event.target.value)} />
          </label>
          <label>
            Query
            <input value={query} onChange={(event) => setQuery(event.target.value)} />
          </label>
          <button className="button" type="submit" disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>
        {error ? <p className="form-error">{error}</p> : null}
      </section>

      <section className="dashboard-card">
        <h2>Results</h2>
        {hits.length === 0 ? <p className="empty-state">No results yet.</p> : null}
        <ul className="simple-list">
          {hits.map((hit) => (
            <li key={hit.product_id}>
              <strong>{hit.title}</strong> · score {hit.score.toFixed(3)}
              {hit.description ? <p>{hit.description}</p> : null}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
