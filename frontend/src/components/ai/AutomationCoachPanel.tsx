import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { Badge, Card, CardBody, CardHeader } from '../ui';
import { EmptyState, ErrorState, LoadingState } from '../data';
import { apiClient } from '../../services/apiClient';
import { useShop } from '../../contexts/ShopContext';
import { explainBlockedDecision, type CoachActionContext } from '../../lib/automationCoach';
import type { AgentDecisionTrace } from '../../types/conversation';
import type { AutomationCoachInsight, BlockedReasonCategory, CoachSeverity } from '../../types/sprint3Automation';
import type { ShopReadinessScore } from '../../types/sprint2Readiness';

const CATEGORY_LABEL: Record<BlockedReasonCategory, string> = {
  risk: 'Risk',
  missing_product_data: 'Missing product data',
  low_confidence: 'Low confidence',
  policy_restriction: 'Policy restriction',
  human_handoff_required: 'Human handoff',
};

function severityTone(severity: CoachSeverity): 'neutral' | 'info' | 'warning' | 'danger' {
  if (severity === 'danger') return 'danger';
  if (severity === 'warning') return 'warning';
  if (severity === 'info') return 'info';
  return 'neutral';
}

function InsightRow({ insight }: { insight: AutomationCoachInsight }) {
  return (
    <div className="grid gap-1 rounded-lg border border-border bg-surface p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={severityTone(insight.severity)}>{CATEGORY_LABEL[insight.category]}</Badge>
        <span className="text-sm font-semibold text-fg">{insight.reason}</span>
      </div>
      <p className="text-sm text-muted">
        <span className="font-medium text-fg">Impact: </span>
        {insight.impact}
      </p>
      <p className="text-sm text-muted">
        <span className="font-medium text-fg">Recommended fix: </span>
        {insight.recommendedFix}
      </p>
      {insight.actionLabel && insight.actionTo ? (
        <Link className="text-sm text-accent hover:underline" to={insight.actionTo}>
          {insight.actionLabel} →
        </Link>
      ) : null}
    </div>
  );
}

export interface AutomationCoachPanelProps {
  /** Provide the trace directly when already loaded (e.g. from a list). */
  trace?: AgentDecisionTrace;
  /** Provide a trace id to fetch on demand. */
  traceId?: string;
  /** Optional compact variant for inline embedding. */
  compact?: boolean;
  /**
   * Optional Sprint 2 shop readiness. When supplied, action links are refined
   * to point at the resolver, readiness, or onboarding surfaces. When absent,
   * the coach keeps its original action links — so it works without readiness.
   */
  shopReadiness?: ShopReadinessScore | null;
}

/**
 * "Why was this blocked?" coach panel. Deterministic, no LLM.
 * Renders Reason / Impact / Recommended fix / one-click action for each
 * blocked-reason category derived from the decision trace.
 */
export function AutomationCoachPanel({ trace, traceId, compact, shopReadiness }: AutomationCoachPanelProps) {
  const { selectedShopId } = useShop();

  const traceQuery = useQuery({
    queryKey: ['decision-trace', selectedShopId, traceId],
    queryFn: () => apiClient.getDecisionTrace(selectedShopId!, traceId!),
    enabled: !trace && Boolean(traceId) && Boolean(selectedShopId),
  });

  const resolvedTrace = trace ?? traceQuery.data;
  const isLoading = !trace && traceQuery.isLoading;
  const error = !trace && traceQuery.error;

  const actionContext: CoachActionContext | undefined = shopReadiness
    ? {
        // Treat catalog as "low" when the Sprint 2 catalog readiness check is failing.
        catalogScore: shopReadiness.checks.find((c) => c.key === 'catalog_complete')?.passed === false ? 0 : 100,
        channelOnboardingAvailable: true,
      }
    : undefined;

  const insights = resolvedTrace
    ? explainBlockedDecision(resolvedTrace, actionContext)
    : [];

  const header = (
    <CardHeader
      title="Why was this blocked?"
      description="Deterministic breakdown of the safety gates that blocked auto-send, with a recommended fix for each."
      actions={resolvedTrace ? <Badge tone="neutral">{insights.length}</Badge> : undefined}
    />
  );

  if (isLoading) {
    return (
      <Card>
        {header}
        <CardBody>
          <LoadingState label="Loading decision trace…" />
        </CardBody>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        {header}
        <CardBody>
          <ErrorState message={error instanceof Error ? error.message : 'Failed to load decision trace'} />
        </CardBody>
      </Card>
    );
  }

  if (!resolvedTrace) {
    return (
      <Card>
        {header}
        <CardBody>
          <EmptyState title="No trace selected" description="Select a blocked decision to explain it." />
        </CardBody>
      </Card>
    );
  }

  if (insights.length === 0) {
    return (
      <Card>
        {header}
        <CardBody>
          <EmptyState
            title="Automation was not blocked for this decision"
            description="This decision passed all safety gates and was eligible for auto-send."
          />
        </CardBody>
      </Card>
    );
  }

  if (compact) {
    return (
      <div className="flex flex-col gap-2" aria-label="Why was this blocked?">
        {insights.map((insight, index) => (
          <InsightRow key={`${insight.category}-${index}`} insight={insight} />
        ))}
      </div>
    );
  }

  return (
    <Card>
      {header}
      <CardBody className="flex flex-col gap-2">
        {insights.map((insight, index) => (
          <InsightRow key={`${insight.category}-${index}`} insight={insight} />
        ))}
      </CardBody>
    </Card>
  );
}
