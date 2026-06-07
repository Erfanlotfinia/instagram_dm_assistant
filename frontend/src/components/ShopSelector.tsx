import { useShop } from '../contexts/ShopContext';

interface ShopSelectorProps {
  label?: string;
}

export function ShopSelector({ label = 'Shop' }: ShopSelectorProps) {
  const { shops, selectedShopId, setSelectedShopId, isLoading } = useShop();

  if (isLoading) {
    return <p className="loading-state">Loading shops...</p>;
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
