import { useShop } from '../contexts/ShopContext';

interface ShopSelectorProps {
  label?: string;
}

export function ShopSelector({ label = 'Shop' }: ShopSelectorProps) {
  const { shops, selectedShopId, setSelectedShopId, isLoading, error } = useShop();

  if (isLoading) {
    return <p className="loading-state">Loading shops...</p>;
  }

  if (error) {
    return <p className="form-error">Failed to load shops: {error}</p>;
  }

  if (shops.length === 0) {
    return <p className="empty-state">No shops available. Create a shop first.</p>;
  }

  return (
    <label className="form-field">
      <span>{label}</span>
      <select value={selectedShopId} onChange={(event) => setSelectedShopId(event.target.value)}>
        {shops.map((shop) => (
          <option key={shop.id} value={shop.id}>
            {shop.name}
          </option>
        ))}
      </select>
    </label>
  );
}
