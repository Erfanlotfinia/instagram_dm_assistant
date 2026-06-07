import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';

export function OnboardingPage() {
  const { selectedShopId } = useShop();
  const statusQuery = useQuery({
    queryKey: ['onboarding-status', selectedShopId],
    queryFn: () => apiClient.getOnboardingStatus(selectedShopId),
    enabled: Boolean(selectedShopId),
  });
  const status = statusQuery.data;
  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Fashion agent setup</p>
        <h1>Onboarding checklist</h1>
        <p>Complete these steps before enabling autonomous Instagram fashion ordering.</p>
        <ShopSelector />
      </section>
      {status ? (
        <section className="dashboard-card dashboard-card--wide">
          <h2>{status.progress_percent}% complete</h2>
          <progress value={status.completed_steps} max={status.total_steps} />
          <div className="table-wrap">
            <table className="data-table">
              <tbody>
                {status.steps.map((step) => (
                  <tr key={step.key} className={step.completed ? 'row-success' : 'row-warning'}>
                    <td>{step.completed ? '✅' : '○'}</td>
                    <td>{step.label}</td>
                    <td><Link className="table-link" to={step.href}>{step.completed ? 'Review' : 'Complete step'}</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </div>
  );
}
