import { useShop } from '../contexts/ShopContext';
import { HubPage } from '../components/shell/HubPage';
import { Badge } from '../components/ui';
import { OperatorWorkloadPanel } from '../components/operator/OperatorWorkloadPanel';
import { useOperatorWorkspace } from '../lib/useOperatorWorkspace';

/**
 * Sprint 5 — Operator workload page. Renders the live workload panel derived
 * from the current operator queue, augmented with historical performance.
 */
export function OperatorWorkloadPage() {
  const { selectedShopId } = useShop();
  const { queueItems, summary } = useOperatorWorkspace(selectedShopId);

  return (
    <HubPage
      eyebrow="Operations"
      title="Operator Workload"
      description="Live assigned counts and SLA risk per operator, augmented with historical performance."
      actions={
        <Badge tone={summary.breached_sla_count > 0 ? 'danger' : 'success'}>
          {summary.breached_sla_count} breached
        </Badge>
      }
    >
      <OperatorWorkloadPanel shopId={selectedShopId} queueItems={queueItems} />
    </HubPage>
  );
}
