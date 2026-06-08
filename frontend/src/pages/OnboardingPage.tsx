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
  const nextStep = status?.steps.find((step) => !step.completed);

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
      {statusQuery.isError ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="form-error">Could not load onboarding status. Try again shortly.</p>
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
                {status.completed_steps.length} of {status.total_steps} steps complete
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

          {status.missing_steps.length > 0 ? (
            <div className="onboarding-next-action">
              <p className="onboarding-next-action__label">Next recommended action</p>
              <p className="onboarding-next-action__text">{status.next_recommended_action}</p>
              {nextStep ? (
                <Link className="button button--primary" to={nextStep.href}>
                  {nextStep.label}
                </Link>
              ) : null}
            </div>
          ) : (
            <p className="onboarding-progress__complete">
              All setup steps are complete. You can enable autonomous ordering when ready.
            </p>
          )}

          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Status</th>
                  <th scope="col">Step</th>
                  <th scope="col">Action</th>
                </tr>
              </thead>
              <tbody>
                {status.steps.map((step) => (
                  <tr
                    key={step.key}
                    className={
                      step.completed
                        ? 'row-success'
                        : step.key === nextStep?.key
                          ? 'row-warning row-highlight'
                          : 'row-warning'
                    }
                  >
                    <td>{step.completed ? '✅' : '○'}</td>
                    <td>{step.label}</td>
                    <td>
                      <Link className="table-link" to={step.href}>
                        {step.completed ? 'Review' : 'Complete step'}
                      </Link>
                    </td>
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
