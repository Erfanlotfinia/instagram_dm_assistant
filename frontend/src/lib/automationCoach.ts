import type { AgentDecisionTrace } from '../types/conversation';
import type { AutomationCoachInsight, BlockedReasonCategory, CoachSeverity } from '../types/sprint3Automation';

/**
 * Deterministic "Why was this blocked?" coach.
 *
 * No LLM. Maps existing AgentDecisionTrace fields (risk_score, auto_send_allowed,
 * human_handoff_required, selected_product_id, risk_reasons, reasoning_summary)
 * to a stable set of insights operators can act on.
 *
 * Evaluation order matters: more specific blockers first, then broader ones.
 * Insights are deduplicated by category so a single root cause surfaces once.
 */

/**
 * Optional readiness-derived action context. When supplied, action links on
 * insights are refined to point at the most useful Sprint 2 surface
 * (catalog resolver, shop readiness, channel onboarding). When absent,
 * `explainBlockedDecision` keeps its original action links — so the coach
 * still works without Sprint 2 readiness loaded.
 */
export interface CoachActionContext {
  /** Catalog completeness score 0-100. When < 80, missing-product-data links to /system/readiness. */
  catalogScore?: number | null;
  /** When true, channel/policy issues link to the onboarding wizard. */
  channelOnboardingAvailable?: boolean;
}

const LOW_CONFIDENCE_PATTERN = /low_(intent|slot|product|variant|address)_confidence/i;

function severityForCategory(category: BlockedReasonCategory): CoachSeverity {
  if (category === 'human_handoff_required') return 'danger';
  if (category === 'risk') return 'danger';
  if (category === 'missing_product_data') return 'warning';
  if (category === 'low_confidence') return 'warning';
  return 'info';
}

function isBlocked(trace: AgentDecisionTrace): boolean {
  if (trace.human_handoff_required) return true;
  if (!trace.auto_send_allowed) return true;
  const level = trace.risk_score?.risk_level;
  return level === 'high' || level === 'critical';
}

function handoffInsight(trace: AgentDecisionTrace): AutomationCoachInsight {
  const reasons = trace.risk_score?.risk_reasons ?? [];
  const reason = reasons.some((r) => /payment_dispute|angry_or_complaint/i.test(r))
    ? 'Customer intent requires a human (payment dispute or complaint)'
    : 'Conversation was flagged for human handoff';
  return {
    category: 'human_handoff_required',
    severity: 'danger',
    reason,
    impact: 'Auto-send was blocked so a human operator can take over before any reply or order action.',
    recommendedFix:
      'Open the conversation, resolve the customer issue, then clear the handoff to resume automation.',
    actionLabel: 'Open conversation',
    actionTo: `/inbox/${trace.conversation_id}/intelligence`,
  };
}

function riskInsight(trace: AgentDecisionTrace): AutomationCoachInsight {
  const level = trace.risk_score?.risk_level ?? 'high';
  const score = trace.risk_score?.score;
  const scoreLabel = typeof score === 'number' ? ` (score ${score.toFixed(2)})` : '';
  return {
    category: 'risk',
    severity: 'danger',
    reason: `Risk level is ${level}${scoreLabel}`,
    impact:
      'Auto-send was blocked to avoid a risky action on a high-value, suspicious, or sensitive request.',
    recommendedFix:
      'Tighten risk thresholds in Risk settings, or keep this conversation on manual review.',
    actionLabel: 'Open Risk settings',
    actionTo: '/automation/risk',
  };
}

function lowConfidenceInsight(trace: AgentDecisionTrace, token: string): AutomationCoachInsight {
  const dimension = (token.match(LOW_CONFIDENCE_PATTERN)?.[1] ?? 'value').toLowerCase();
  const label = dimension.charAt(0).toUpperCase() + dimension.slice(1);
  return {
    category: 'low_confidence',
    severity: 'warning',
    reason: `${label} confidence is below the configured threshold`,
    impact:
      'Auto-send was blocked because the agent was not confident enough about the extracted value.',
    recommendedFix:
      'Add catalog aliases, refine extraction rules, or lower the confidence threshold in Risk settings.',
    actionLabel: 'Open Risk settings',
    actionTo: '/automation/risk',
  };
}

function missingProductInsight(trace: AgentDecisionTrace): AutomationCoachInsight {
  const reasons = trace.risk_score?.risk_reasons ?? [];
  const unavailable = reasons.some((r) => /unavailable_variant/i.test(r));
  const reason = unavailable
    ? 'Selected product variant is unavailable'
    : 'No product could be resolved for this request';
  return {
    category: 'missing_product_data',
    severity: 'warning',
    reason,
    impact:
      'Auto-send was blocked to avoid recommending or ordering the wrong product.',
    recommendedFix:
      'Review catalog aliases and product mapping so the resolver can match this request.',
    actionLabel: 'Open Catalog Resolver',
    actionTo: '/catalog/resolver',
  };
}

function policyInsight(trace: AgentDecisionTrace): AutomationCoachInsight {
  return {
    category: 'policy_restriction',
    severity: 'info',
    reason: 'Policy gate requires operator preview before sending',
    impact:
      'Auto-send was blocked by a policy rule (e.g. explicit confirmation or high-value order preview).',
    recommendedFix:
      'Approve the suggested reply in the inbox, or adjust the policy in Risk settings.',
    actionLabel: 'Open conversation',
    actionTo: `/inbox/${trace.conversation_id}/intelligence`,
  };
}

/**
 * Compute coach insights for a single decision trace.
 * Returns an empty array when the decision was not blocked.
 *
 * Pass an optional `actionContext` to refine action links using Sprint 2
 * readiness (e.g. route missing-product-data to the resolver or readiness
 * page). When omitted, the original action links are used unchanged.
 */
export function explainBlockedDecision(
  trace: AgentDecisionTrace,
  actionContext?: CoachActionContext,
): AutomationCoachInsight[] {
  if (!isBlocked(trace)) return [];

  const insights: AutomationCoachInsight[] = [];
  const seen = new Set<BlockedReasonCategory>();

  const reasons = trace.risk_score?.risk_reasons ?? [];
  const add = (insight: AutomationCoachInsight) => {
    if (seen.has(insight.category)) return;
    seen.add(insight.category);
    insights.push(insight);
  };

  // 1. Handoff (most specific / highest priority)
  if (trace.human_handoff_required || trace.risk_score?.requires_handoff) {
    add(handoffInsight(trace));
  }

  // 2. High / critical risk
  const level = trace.risk_score?.risk_level;
  const score = trace.risk_score?.score;
  if (level === 'high' || level === 'critical' || (typeof score === 'number' && score >= 0.7)) {
    add(riskInsight(trace));
  }

  // 3. Low confidence (one insight per dimension would be noisy; first match wins)
  const lowConfidenceReason = reasons.find((r) => LOW_CONFIDENCE_PATTERN.test(r));
  if (lowConfidenceReason) {
    add(lowConfidenceInsight(trace, lowConfidenceReason));
  }

  // 4. Missing product data
  const hasUnavailableVariant = reasons.some((r) => /unavailable_variant/i.test(r));
  if (!trace.selected_product_id || hasUnavailableVariant) {
    add(missingProductInsight(trace));
  }

  // 5. Policy restriction (preview required, not already covered by handoff/risk)
  if (trace.risk_score?.requires_preview && !seen.has('human_handoff_required') && !seen.has('risk')) {
    add(policyInsight(trace));
  }

  // Fallback: blocked but no specific signal — surface the raw reasoning summary.
  if (insights.length === 0) {
    insights.push({
      category: 'policy_restriction',
      severity: 'info',
      reason: trace.reasoning_summary ?? 'Auto-send was blocked by safety gates',
      impact: 'The decision did not pass all automation safety checks.',
      recommendedFix: 'Review the decision trace and adjust risk or policy settings.',
      actionLabel: 'Open conversation',
      actionTo: `/inbox/${trace.conversation_id}/intelligence`,
    });
  }

  if (actionContext) {
    for (const insight of insights) {
      if (insight.category === 'missing_product_data') {
        const lowCatalog =
          typeof actionContext.catalogScore === 'number' && actionContext.catalogScore < 80;
        insight.actionTo = lowCatalog ? '/system/readiness' : '/catalog/resolver';
        insight.actionLabel = lowCatalog ? 'Open Shop readiness' : 'Open Catalog Resolver';
      } else if (insight.category === 'policy_restriction') {
        insight.actionTo = actionContext.channelOnboardingAvailable
          ? '/system/channels/onboarding'
          : '/system/readiness';
        insight.actionLabel = actionContext.channelOnboardingAvailable
          ? 'Open Channel onboarding'
          : 'Open Shop readiness';
      }
    }
  }

  return insights;
}

export const __testing = { isBlocked, severityForCategory };
