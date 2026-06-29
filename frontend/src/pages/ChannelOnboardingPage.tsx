import { HubPage } from '../components/shell/HubPage';
import { ChannelOnboardingWizard } from '../components/onboarding/ChannelOnboardingWizard';
import { useShop } from '../contexts/ShopContext';

export function ChannelOnboardingPage() {
  const { selectedShopId } = useShop();
  return (
    <HubPage
      eyebrow="System"
      title="Channel onboarding"
      description="Connect and verify messaging channels. Each provider shows its readiness score, current step, and next action."
    >
      <ChannelOnboardingWizard shopId={selectedShopId ?? ''} />
    </HubPage>
  );
}
