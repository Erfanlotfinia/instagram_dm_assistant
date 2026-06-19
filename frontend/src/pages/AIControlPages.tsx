import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { AreaTrend } from '../components/charts/ChartKit';
import { Card, CardBody, CardHeader, Badge } from '../components/ui';
import { KpiCard, DataTable, FilterBar, LoadingState, ErrorState, EmptyState } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { AgentDecisionTrace } from '../types/conversation';

function useDecisionTraces() {
  const { selectedShopId } = useShop();
  return useQuery({
    queryKey: ['ai-decision-traces', selectedShopId],
    queryFn: () => apiClient.listDecisionTraces(selectedShopId),
    enabled: Boolean(selectedShopId),
  });
}

function classify(trace: AgentDecisionTrace): 'automated' | 'llm' | 'handoff' {
  if (trace.human_handoff_required) return 'handoff';
  if (trace.auto_send_allowed) return 'automated';
  return 'llm';
}

function riskTone(level?: string): 'success' | 'warning' | 'danger' | 'neutral' {
  if (level === 'critical' || level === 'high') return 'danger';
  if (level === 'medium') return 'warning';
  if (level === 'low') return 'success';
  return 'neutral';
}

function traceColumns(): Column<AgentDecisionTrace>[] {
  return [
    {
      key: 'outcome',
      header: 'Outcome',
      render: (trace) => {
        const kind = classify(trace);
        const tone = kind === 'automated' ? 'success' : kind === 'llm' ? 'info' : 'danger';
        return <Badge tone={tone} dot>{kind === 'llm' ? 'LLM' : kind}</Badge>;
      },
    },
    { key: 'intent', header: 'Intent', render: (trace) => trace.intent ?? '—' },
    {
      key: 'risk',
      header: 'Risk',
      render: (trace) => <Badge tone={riskTone(trace.risk_score?.risk_level)}>{trace.risk_score?.risk_level ?? 'n/a'}</Badge>,
    },
    {
      key: 'model',
      header: 'Model run',
      render: (trace) => (trace.agent_run_id ? 'LLM' : 'Deterministic'),
    },
    {
      key: 'summary',
      header: 'Summary',
      render: (trace) => <span className="line-clamp-1 text-muted">{trace.reasoning_summary ?? '—'}</span>,
    },
    {
      key: 'conversation',
      header: '',
      align: 'right',
      render: (trace) => (
        <Link className="text-accent hover:underline" to={`/inbox/${trace.conversation_id}/intelligence`}>
          Trace
        </Link>
      ),
    },
  ];
}

export function AIControlOverviewPage() {
  const { selectedShopId } = useShop();
  const tracesQuery = useDecisionTraces();
  const trendsQuery = useQuery({
    queryKey: queryKeys.dashboardTrends(selectedShopId, '30d'),
    queryFn: () => apiClient.getDashboardTrends(selectedShopId, '30d'),
    enabled: Boolean(selectedShopId),
  });
  const perfQuery = useQuery({
    queryKey: ['ai-agent-performance', selectedShopId],
    queryFn: () => apiClient.getAnalyticsAgentPerformance(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const traces = tracesQuery.data ?? [];
  const counts = useMemo(() => {
    const total = traces.length;
    const automated = traces.filter((trace) => classify(trace) === 'automated').length;
    const llm = traces.filter((trace) => classify(trace) === 'llm').length;
    const handoff = traces.filter((trace) => classify(trace) === 'handoff').length;
    return {
      total,
      automated: total > 0 ? Math.round((automated / total) * 100) : 0,
      llm: total > 0 ? Math.round((llm / total) * 100) : 0,
      handoff: total > 0 ? Math.round((handoff / total) * 100) : 0,
    };
  }, [traces]);

  const trendPoints = trendsQuery.data?.points ?? [];
  const hasTrendData = trendPoints.some(
    (point) => point.automated + point.llm + point.handoff > 0,
  );

  const perf = perfQuery.data;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Decisions traced" value={counts.total.toLocaleString()} />
        <KpiCard label="Automated" value={`${counts.automated}%`} tone="success" />
        <KpiCard label="LLM handled" value={`${counts.llm}%`} tone="warning" />
        <KpiCard label="Human handoff" value={`${counts.handoff}%`} tone="danger" />
        <KpiCard label="Invalid LLM outputs" value={perfQuery.isLoading ? '…' : (perf?.invalid_llm_outputs ?? 0)} tone="danger" />
        <KpiCard label="Failed agent runs" value={perfQuery.isLoading ? '…' : (perf?.failed_agent_runs ?? 0)} tone="danger" />
        <KpiCard
          label="Avg intent confidence"
          value={
            perfQuery.isLoading
              ? '…'
              : perf?.average_intent_confidence != null
                ? `${Math.round(perf.average_intent_confidence * 100)}%`
                : '—'
          }
        />
        <KpiCard
          label="Avg product confidence"
          value={
            perfQuery.isLoading
              ? '…'
              : perf?.average_product_confidence != null
                ? `${Math.round(perf.average_product_confidence * 100)}%`
                : '—'
          }
        />
      </div>

      <Card>
        <CardHeader
          title="Decision distribution"
          description="Automated vs LLM-handled vs human handoff, by day (last 30 days)."
        />
        <CardBody>
          {trendsQuery.isLoading ? (
            <LoadingState />
          ) : !hasTrendData ? (
            <EmptyState title="No decisions yet" />
          ) : (
            <AreaTrend
              data={trendPoints as unknown as Array<Record<string, number | string>>}
              xKey="date"
              stacked
              series={[
                { key: 'automated', label: 'Automated', color: 'var(--c-success)' },
                { key: 'llm', label: 'LLM handled', color: 'var(--c-warning)' },
                { key: 'handoff', label: 'Human handoff', color: 'var(--c-danger)' },
              ]}
              height={240}
            />
          )}
        </CardBody>
      </Card>
    </div>
  );
}

function TraceTablePage({
  title,
  description,
  filterFn,
  emptyTitle,
}: {
  title: string;
  description: string;
  filterFn: (trace: AgentDecisionTrace) => boolean;
  emptyTitle: string;
}) {
  const tracesQuery = useDecisionTraces();
  const [search, setSearch] = useState('');
  const rows = (tracesQuery.data ?? [])
    .filter(filterFn)
    .filter((trace) =>
      search ? `${trace.intent ?? ''} ${trace.reasoning_summary ?? ''}`.toLowerCase().includes(search.toLowerCase()) : true,
    );

  return (
    <Card>
      <CardHeader title={title} description={description} actions={<Badge>{rows.length}</Badge>} />
      <div className="px-5 py-3">
        <FilterBar search={search} onSearch={setSearch} searchPlaceholder="Filter by intent or summary…" />
      </div>
      <DataTable
        columns={traceColumns()}
        rows={rows}
        rowKey={(trace) => trace.id}
        isLoading={tracesQuery.isLoading}
        error={tracesQuery.error instanceof Error ? tracesQuery.error.message : null}
        emptyTitle={emptyTitle}
      />
    </Card>
  );
}

export function LLMLogsPage() {
  return (
    <TraceTablePage
      title="LLM usage logs"
      description="All agent decisions backed by a model run, with the audit summary kept for each."
      filterFn={(trace) => Boolean(trace.agent_run_id)}
      emptyTitle="No LLM runs recorded"
    />
  );
}

export function AIFallbacksPage() {
  return (
    <TraceTablePage
      title="LLM fallbacks"
      description="Cases where deterministic scenarios did not match and the LLM took over."
      filterFn={(trace) => classify(trace) === 'llm'}
      emptyTitle="No fallbacks recorded"
    />
  );
}

export function AISafetyPage() {
  const tracesQuery = useDecisionTraces();
  const blocked = (tracesQuery.data ?? []).filter(
    (trace) => !trace.auto_send_allowed || ['high', 'critical'].includes(trace.risk_score?.risk_level ?? ''),
  );

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader
          title="Safety & blocked actions"
          description="High-risk decisions and blocked auto-sends that required review or handoff."
          actions={<Badge tone="danger">{blocked.length}</Badge>}
        />
        {tracesQuery.isLoading ? (
          <LoadingState />
        ) : tracesQuery.error ? (
          <ErrorState message={tracesQuery.error instanceof Error ? tracesQuery.error.message : 'Failed to load'} />
        ) : blocked.length === 0 ? (
          <EmptyState title="No unsafe actions detected" description="Every decision passed safety thresholds." />
        ) : (
          <CardBody className="flex flex-col gap-2">
            {blocked.map((trace) => (
              <div key={trace.id} className="rounded-lg border border-border p-3">
                <div className="flex items-center justify-between gap-2">
                  <Badge tone={riskTone(trace.risk_score?.risk_level)} dot>
                    {trace.risk_score?.risk_level ?? 'blocked'}
                  </Badge>
                  <Link className="text-xs text-accent hover:underline" to={`/inbox/${trace.conversation_id}/intelligence`}>
                    View trace
                  </Link>
                </div>
                {Array.isArray(trace.risk_score?.risk_reasons) && trace.risk_score.risk_reasons.length > 0 ? (
                  <p className="mt-1.5 text-sm text-warning">{trace.risk_score.risk_reasons.join(' · ')}</p>
                ) : (
                  <p className="mt-1.5 text-sm text-muted">{trace.reasoning_summary ?? 'Auto-send blocked.'}</p>
                )}
              </div>
            ))}
          </CardBody>
        )}
      </Card>
    </div>
  );
}
