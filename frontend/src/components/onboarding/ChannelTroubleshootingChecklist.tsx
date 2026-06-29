import { Link } from 'react-router-dom';

import { Badge, Card, CardBody, CardHeader } from '../ui';
import { EmptyState } from '../data';
import type { BadgeTone } from '../ui';
import type {
  ChannelOnboardingState,
  ChannelTroubleshootingItem,
} from '../../types/sprint2Readiness';

function severityTone(severity: ChannelTroubleshootingItem['severity']): BadgeTone {
  if (severity === 'blocker') return 'danger';
  if (severity === 'warning') return 'warning';
  return 'neutral';
}

function severityLabel(severity: ChannelTroubleshootingItem['severity']): string {
  if (severity === 'blocker') return 'Blocker';
  if (severity === 'warning') return 'Warning';
  return 'Info';
}

function deriveItems(state: ChannelOnboardingState): ChannelTroubleshootingItem[] {
  return state.steps
    .filter((step) => !step.passed)
    .map((step) => ({
      key: step.key,
      title: step.label,
      passed: step.passed,
      severity: step.severity === 'required' ? 'blocker' : 'warning',
      detail: step.detail ?? step.description,
      fixLabel: step.actionLabel,
      fixTo: step.actionTo,
    }));
}

export interface ChannelTroubleshootingChecklistProps {
  state: ChannelOnboardingState;
}

/**
 * Per-channel troubleshooting checklist. Derives `ChannelTroubleshootingItem[]`
 * from a `ChannelOnboardingState` and renders each failed step with a severity
 * badge, pass/fail status, and a fix link. Pure presentational component.
 */
export function ChannelTroubleshootingChecklist({ state }: ChannelTroubleshootingChecklistProps) {
  const items = deriveItems(state);

  return (
    <Card>
      <CardHeader
        title="Troubleshooting checklist"
        description="Required steps must pass before this channel can power automation. Recommended steps improve reliability."
        actions={<Badge tone={state.ready ? 'success' : 'danger'}>{state.score}% ready</Badge>}
      />
      <CardBody>
        {items.length === 0 ? (
          <EmptyState
            title="No issues detected"
            description="All onboarding steps for this channel are passing."
          />
        ) : (
          <ul className="grid gap-2">
            {items.map((item) => (
              <li
                key={item.key}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-surface px-3 py-2"
              >
                <div className="grid gap-0.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={severityTone(item.severity)}>{severityLabel(item.severity)}</Badge>
                    <span className="text-sm font-medium text-fg">{item.title}</span>
                  </div>
                  {item.detail ? (
                    <span className="text-xs text-muted">{item.detail}</span>
                  ) : null}
                </div>
                {item.fixLabel && item.fixTo ? (
                  <Link className="text-xs text-accent hover:underline" to={item.fixTo}>
                    {item.fixLabel} →
                  </Link>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
