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
      {statusQuery.isLoading && selectedShopId ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="loading-state">Loading onboarding status...</p>
        </section>
      ) : null}
      {!selectedShopId ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="empty-state">Select a shop to view onboarding progress.</p>
        </section>
      ) : null}
      {status ? (
        <section className="dashboard-card dashboard-card--wide">
          <div className="onboarding-progress">
            <div className="onboarding-progress__meta">
              <h2>
                {status.completed_steps} of {status.total_steps} steps complete
              </h2>
              <span className="onboarding-progress__percent">{status.progress_percent}%</span>
            </div>
            <div
              className="onboarding-progress__track"
              role="progressbar"
              aria-valuenow={status.progress_percent}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Onboarding progress"
            >
              <div
                className="onboarding-progress__fill"
                style={{ width: `${status.progress_percent}%` }}
              />
            </div>
          </div>
          {status.progress_percent === 100 ? (
            <p className="onboarding-progress__complete">All setup steps are complete. You can enable autonomous ordering when ready.</p>
          ) : null}
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
