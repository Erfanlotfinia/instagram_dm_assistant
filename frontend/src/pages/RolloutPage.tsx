import { useSearchParams } from 'react-router-dom';

import { IncidentTimelinePage } from './IncidentTimelinePage';
import { OnboardingPage } from './OnboardingPage';
import { PilotControlCenterPage } from './PilotControlCenterPage';
import { PilotReadinessPage } from './PilotReadinessPage';
import { TRLValidationPage } from './TRLValidationPage';
import { cn } from '../lib/cn';

type View = 'control' | 'readiness' | 'onboarding' | 'incidents' | 'trl';

const VIEWS: Array<{ id: View; label: string }> = [
  { id: 'control', label: 'Pilot Control' },
  { id: 'readiness', label: 'Readiness' },
  { id: 'onboarding', label: 'Onboarding' },
  { id: 'incidents', label: 'Incidents' },
  { id: 'trl', label: 'TRL Validation' },
];

export function RolloutPage() {
  const [params, setParams] = useSearchParams();
  const view = (params.get('view') as View | null) ?? 'control';

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-1.5">
        {VIEWS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => {
              const next = new URLSearchParams(params);
              next.set('view', item.id);
              setParams(next, { replace: true });
            }}
            className={cn(
              'rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors',
              view === item.id ? 'border-accent bg-accent-soft text-accent' : 'border-border text-muted hover:text-fg',
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div>
        {view === 'control' ? <PilotControlCenterPage /> : null}
        {view === 'readiness' ? <PilotReadinessPage /> : null}
        {view === 'onboarding' ? <OnboardingPage /> : null}
        {view === 'incidents' ? <IncidentTimelinePage /> : null}
        {view === 'trl' ? <TRLValidationPage /> : null}
      </div>
    </div>
  );
}
