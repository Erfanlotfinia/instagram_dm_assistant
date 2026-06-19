import { useQueryClient } from '@tanstack/react-query';
import { FormEvent, useEffect, useState } from 'react';

import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input } from '../components/ui';
import { DataTable } from '../components/data';
import type { Column } from '../components/data';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { Shop } from '../types/shop';

export function ShopsPage() {
  const queryClient = useQueryClient();
  const [shops, setShops] = useState<Shop[]>([]);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  async function loadShops() {
    const data = await apiClient.listShops();
    setShops(data);
  }

  useEffect(() => {
    loadShops()
      .catch(() => setShops([]))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await apiClient.createShop({ name, slug: slug || undefined });
      setName('');
      setSlug('');
      await loadShops();
      await queryClient.invalidateQueries({ queryKey: queryKeys.shops });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create shop');
    } finally {
      setIsSubmitting(false);
    }
  }

  const columns: Column<Shop>[] = [
    { key: 'name', header: 'Name', render: (shop) => <span className="font-medium">{shop.name}</span> },
    { key: 'slug', header: 'Slug', render: (shop) => <span className="font-mono text-xs text-muted">{shop.slug}</span> },
    { key: 'status', header: 'Status', render: (shop) => <Badge tone="neutral">{shop.status}</Badge> },
    { key: 'currency', header: 'Currency', align: 'right', render: (shop) => shop.default_currency },
  ];

  return (
    <HubPage eyebrow="System" title="Shops" description="Manage storefronts and create new shops.">
      <Card>
        <CardHeader title="Create shop" />
        <CardBody>
          <form className="flex flex-wrap items-end gap-3" onSubmit={handleCreate}>
            <Field label="Name">
              <Input value={name} onChange={(event) => setName(event.target.value)} required />
            </Field>
            <Field label="Slug (optional)">
              <Input value={slug} onChange={(event) => setSlug(event.target.value)} />
            </Field>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Creating…' : 'Create shop'}
            </Button>
          </form>
          {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Your shops" description={`${shops.length} shops you belong to.`} />
        <DataTable
          columns={columns}
          rows={shops}
          rowKey={(shop) => shop.id}
          isLoading={loading}
          emptyTitle="No shops yet"
        />
      </Card>
    </HubPage>
  );
}
