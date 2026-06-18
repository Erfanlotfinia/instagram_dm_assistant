import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { HubPage } from '../components/shell/HubPage';
import { Card, CardBody, CardHeader } from '../components/ui';
import { EmptyState, LoadingState } from '../components/data';
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
    <HubPage
      eyebrow="Fashion agent setup"
      title="Onboarding checklist"
      description="Complete these steps before enabling autonomous Instagram fashion ordering."
    >
      {!selectedShopId ? (
        <Card>
          <CardBody>
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          </CardBody>
        </Card>
      ) : null}

      {statusQuery.isLoading && selectedShopId ? (
        <Card>
          <CardBody>
            <LoadingState label="Loading onboarding status…" />
          </CardBody>
        </Card>
      ) : null}

      {statusQuery.isError ? (
        <Card>
          <CardBody>
            <p className="text-sm text-danger">Could not load onboarding status. Try again shortly.</p>
          </CardBody>
        </Card>
      ) : null}

      {status ? (
        <Card>
          <CardHeader
            title={`${status.completed_steps.length} of ${status.total_steps} steps complete`}
            description={`${status.progress_percent}% complete`}
          />
          <CardBody>
            <div className="onboarding-progress">
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
              <div className="onboarding-next-action mt-4">
                <p className="onboarding-next-action__label text-xs font-medium text-muted">Next recommended action</p>
                <p className="onboarding-next-action__text mt-1 text-sm text-fg">{status.next_recommended_action}</p>
                {nextStep ? (
                  <Link className="mt-3 inline-flex h-10 items-center rounded-lg bg-accent px-4 text-sm font-medium text-accent-fg hover:opacity-90" to={nextStep.href}>
                    {nextStep.label}
                  </Link>
                ) : null}
              </div>
            ) : (
              <p className="onboarding-progress__complete mt-4 text-sm text-muted">
                All setup steps are complete. You can enable autonomous ordering when ready.
              </p>
            )}

            <div className="table-wrap mt-6">
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
                        <Link className="font-medium text-accent hover:underline" to={step.href}>
                          {step.completed ? 'Review' : 'Complete step'}
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>
      ) : null}
    </HubPage>
  );
}
