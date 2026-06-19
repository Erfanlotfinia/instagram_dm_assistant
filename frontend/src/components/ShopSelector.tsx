import { Field, Select } from './ui';
import { useShop } from '../contexts/ShopContext';
import { LoadingState, ErrorState } from './data';

interface ShopSelectorProps {
  label?: string;
  /** Hide when the top-bar shop switcher is sufficient (default for hub pages). */
  compact?: boolean;
}

/**
 * Inline shop picker for forms that need an explicit shop context.
 * Most hub pages rely on the TopBar ShopSwitcher instead.
 */
export function ShopSelector({ label = 'Shop', compact = false }: ShopSelectorProps) {
  const { shops, selectedShopId, setSelectedShopId, isLoading, error } = useShop();

  if (isLoading) {
    return <LoadingState label="Loading shops…" />;
  }

  if (error) {
    return <ErrorState message={`Failed to load shops: ${error}`} />;
  }

  if (shops.length === 0) {
    return <p className="text-sm text-muted">No shops available. Create a shop in System → Shops.</p>;
  }

  if (compact && shops.length === 1) {
    return null;
  }

  return (
    <Field label={label} htmlFor="shop-selector" className="max-w-xs">
      <Select id="shop-selector" value={selectedShopId} onChange={(event) => setSelectedShopId(event.target.value)}>
        {shops.map((shop) => (
          <option key={shop.id} value={shop.id}>
            {shop.name}
          </option>
        ))}
      </Select>
    </Field>
  );
}
