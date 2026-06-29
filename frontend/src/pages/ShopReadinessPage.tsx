import { HubPage } from '../components/shell/HubPage';
import { ShopReadinessPanel } from '../components/onboarding/ShopReadinessPanel';
import { useShop } from '../contexts/ShopContext';

export function ShopReadinessPage() {
  const { selectedShopId } = useShop();
  return (
    <HubPage
      eyebrow="System"
      title="Shop readiness"
      description="Aggregated readiness across channel, catalog, automation, policy, regression, and operations."
    >
      <ShopReadinessPanel shopId={selectedShopId} />
    </HubPage>
  );
}
