import { useQuery } from '@tanstack/react-query';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { ContextGraph } from '../components/intelligence/ContextGraph';
import { Card, CardBody, CardHeader, Badge, Button } from '../components/ui';
import { PageHeader, LoadingState, ErrorState, EmptyState } from '../components/data';
import { Icons } from '../components/icons';
import { useShop } from '../contexts/ShopContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { AgentDecisionTrace } from '../types/conversation';

function riskTone(level?: string): 'success' | 'warning' | 'danger' | 'neutral' {
  if (level === 'critical' || level === 'high') return 'danger';
  if (level === 'medium') return 'warning';
  if (level === 'low') return 'success';
  return 'neutral';
}

function TraceCard({ trace }: { trace: AgentDecisionTrace }) {
  const outcome = trace.human_handoff_required
    ? { label: 'Human handoff', tone: 'danger' as const }
    : trace.auto_send_allowed
    ? { label: 'Automated', tone: 'success' as const }
    : { label: 'LLM / review', tone: 'warning' as const };

  return (
    <div className="rounded-lg border border-border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge tone={outcome.tone} dot>{outcome.label}</Badge>
          {trace.intent ? <span className="text-xs text-muted">intent: {trace.intent}</span> : null}
          <Badge tone={riskTone(trace.risk_score?.risk_level)}>
            risk: {trace.risk_score?.risk_level ?? 'n/a'}
          </Badge>
        </div>
        <time className="text-xs text-subtle">{new Date(trace.created_at).toLocaleString()}</time>
      </div>
      {trace.reasoning_summary ? (
        <p className="mt-2 text-sm text-fg">{trace.reasoning_summary}</p>
      ) : null}
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted sm:grid-cols-3">
        <div>
          <dt className="text-subtle">Next state</dt>
          <dd className="text-fg">{trace.next_state}</dd>
        </div>
        <div>
          <dt className="text-subtle">Auto-send</dt>
          <dd className="text-fg">{trace.auto_send_allowed ? 'Allowed' : 'Blocked'}</dd>
        </div>
        <div>
          <dt className="text-subtle">Model run</dt>
          <dd className="text-fg">{trace.agent_run_id ? 'Yes' : 'Deterministic'}</dd>
        </div>
      </dl>
      {Array.isArray(trace.risk_score?.risk_reasons) && trace.risk_score.risk_reasons.length > 0 ? (
        <p className="mt-2 text-xs text-warning">
          {trace.risk_score.risk_reasons.join(' · ')}
        </p>
      ) : null}
    </div>
  );
}

export function ConversationIntelligencePage() {
  const { conversationId } = useParams<{ conversationId: string }>();
  const [searchParams] = useSearchParams();
  const { selectedShopId } = useShop();
  const shopId = searchParams.get('shopId') ?? selectedShopId;

  const conversationQuery = useQuery({
    queryKey: queryKeys.conversation(shopId, conversationId ?? ''),
    queryFn: () => apiClient.getConversation(shopId, conversationId!),
    enabled: Boolean(shopId && conversationId),
  });

  const tracesQuery = useQuery({
    queryKey: ['decision-traces', shopId, conversationId],
    queryFn: () => apiClient.listConversationDecisionTraces(shopId, conversationId!),
    enabled: Boolean(shopId && conversationId),
  });

  const correctionsQuery = useQuery({
    queryKey: ['operator-corrections', shopId],
    queryFn: () => apiClient.listOperatorCorrections(shopId),
    enabled: Boolean(shopId),
  });

  const conversation = conversationQuery.data;
  const traces = tracesQuery.data ?? [];
  const overrides = (correctionsQuery.data ?? []).filter(
    (correction) => correction.conversation_id === conversationId,
  );
  const agentRuns = conversation?.agent_runs ?? [];

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow="Conversation intelligence"
        title="Why did the system respond this way?"
        description="Full audit trail: resolved context, scenario decisions, LLM usage, and human overrides."
        actions={
          <Link to={conversationId ? `/inbox/${conversationId}?shopId=${shopId}` : '/inbox'}>
            <Button variant="secondary" size="sm" leadingIcon={<Icons.inbox size={14} />}>
              Back to conversation
            </Button>
          </Link>
        }
      />

      {conversationQuery.isLoading ? <LoadingState /> : null}
      {conversationQuery.error ? (
        <ErrorState message={conversationQuery.error instanceof Error ? conversationQuery.error.message : 'Failed to load'} />
      ) : null}

      {conversation ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-1">
            <CardHeader title="Context graph" description="Resolved entities for this thread." />
            <CardBody>
              <ContextGraph conversation={conversation} />
            </CardBody>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader
              title="Decision trace timeline"
              description="Every automation decision, newest first. No private chain-of-thought is stored."
            />
            <CardBody className="flex flex-col gap-3">
              {tracesQuery.isLoading ? (
                <LoadingState />
              ) : traces.length === 0 ? (
                <EmptyState title="No decision traces" description="This conversation has no recorded agent decisions yet." />
              ) : (
                traces.map((trace) => <TraceCard key={trace.id} trace={trace} />)
              )}
            </CardBody>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader title="LLM usage log" description="Model runs invoked for this conversation." />
            <CardBody>
              {agentRuns.length === 0 ? (
                <EmptyState title="No LLM calls" description="Responses were handled deterministically." />
              ) : (
                <div className="flex flex-col gap-2">
                  {agentRuns.map((run) => (
                    <div key={run.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border px-3 py-2 text-xs">
                      <div className="flex items-center gap-2">
                        <Badge tone={run.status === 'success' ? 'success' : 'danger'}>{run.status}</Badge>
                        <span className="font-mono text-fg">{run.model_name}</span>
                        <span className="text-subtle">prompt {run.prompt_version}</span>
                      </div>
                      <time className="text-subtle">{new Date(run.created_at).toLocaleString()}</time>
                      {run.error_message ? <p className="w-full text-danger">{run.error_message}</p> : null}
                    </div>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>

          <Card className="lg:col-span-1">
            <CardHeader title="Human overrides" description="Operator corrections on this thread." />
            <CardBody>
              {overrides.length === 0 ? (
                <EmptyState title="No overrides" description="The agent's decisions were not corrected." />
              ) : (
                <ul className="flex flex-col gap-2">
                  {overrides.map((correction) => (
                    <li key={correction.id} className="rounded-lg border border-border p-2 text-xs">
                      <span className="font-medium text-fg">{correction.correction_type}</span>
                      <time className="ml-2 text-subtle">{new Date(correction.created_at).toLocaleDateString()}</time>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
