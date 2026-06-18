import { OrderPipeline } from '../components/orders/OrderPipeline';
import { OrdersPage } from './OrdersPage';

/** Orders hub: pipeline summary above the full orders table. */
export function OrdersHubPage() {
  return (
    <div className="flex flex-col gap-5">
      <OrderPipeline />
      <OrdersPage />
    </div>
  );
}
