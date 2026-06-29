import { Icons } from '../icons';
import { useShop } from '../../contexts/ShopContext';

/** Compact shop selector for the top bar. */
export function ShopSwitcher() {
  const { shops, selectedShopId, setSelectedShopId, isLoading, error } = useShop();

  if (isLoading) {
    return <span className="text-xs text-muted">Loading shops…</span>;
  }

  if (error) {
    return <span className="text-xs text-danger" title={error}>Shops unavailable</span>;
  }

  if (shops.length === 0) {
    return <span className="text-xs text-muted">No shops</span>;
  }

  return (
    <div className="relative">
      <select
        value={selectedShopId}
        onChange={(event) => setSelectedShopId(event.target.value)}
        aria-label="Active shop"
        className="h-9 appearance-none rounded-lg border border-border bg-surface pl-3 pr-8 text-sm font-medium text-fg focus:border-accent focus:outline-none"
      >
        {shops.map((shop) => (
          <option key={shop.id} value={shop.id}>
            {shop.name}
          </option>
        ))}
      </select>
      <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-subtle">
        <Icons.chevronDown size={15} />
      </span>
    </div>
  );
}
