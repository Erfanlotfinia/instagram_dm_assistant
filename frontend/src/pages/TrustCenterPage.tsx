import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import { Badge, Button, Card, CardBody, CardHeader } from '../components/ui';
import { EmptyState, ErrorState, KpiCard, LoadingState } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '../services/apiClient';
import { BUILTIN_TRUST_TEST_PACKS } from '../lib/trustTestPacks';
import {
  buildTrustReadinessSignals,
  clearCachedTrustRun,
  evaluateRunResults,
  loadCachedTrustRun,
  mapTrustPackToScenarioPackInput,
  saveCachedTrustRun,
  summarizeTrustResults,
} from '../lib/trustEvaluation';
import { useShopReadiness } from '../lib/useShopReadiness';
import type {
  TrustEvaluationRun,
  TrustEvaluationSummary,
} from '../types/sprint6Trust';
import type { ReplayScenarioInput, ScenarioPack, SimulatorRunDetail } from '../types/trust';

import { TrustEvaluationSummaryPanel } from '../components/trust/TrustEvaluationSummaryPanel';
import { TrustFailureTable } from '../components/trust/TrustFailureTable';
import { TrustReadinessPanel } from '../components/trust/TrustReadinessPanel';
import { TrustTestPackCard } from '../components/trust/TrustTestPackCard';

const TRUST_PACK_PREFIX = '[Trust] ';

function packToScenarios(pack: ScenarioPack): ReplayScenarioInput[] {
  return pack.scenarios_json.map((scenario, index) => ({
    item_key: String(scenario.item_key ?? `pack-${index + 1}`),
    message_text: String(scenario.message_text ?? ''),
    shared_post_url: scenario.shared_post_url ? String(scenario.shared_post_url) : null,
    expected_json: (scenario.expected_json as Record<string, unknown> | undefined) ?? {},
  }));
}

export function TrustCenterPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const [cachedRun, setCachedRun] = useState<TrustEvaluationRun | null>(null);
  const [runningPackId, setRunningPackId] = useState<string | null>(null);

  const shopReadiness = useShopReadiness(selectedShopId);

  const packsQuery = useQuery({
    queryKey: ['scenario-packs', selectedShopId],
    queryFn: () => apiClient.listScenarioPacks(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });

  const runsQuery = useQuery({
    queryKey: ['replay-runs', selectedShopId],
    queryFn: () => apiClient.listReplayRuns(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });

  useEffect(() => {
    setCachedRun(loadCachedTrustRun(selectedShopId));
  }, [selectedShopId]);

  const trustScenarioPacks = useMemo(() => {
    const all = packsQuery.data ?? [];
    return all.filter((pack) => pack.name.startsWith(TRUST_PACK_PREFIX));
  }, [packsQuery.data]);

  function findTrustScenarioPack(packId: string): ScenarioPack | undefined {
    const builtin = BUILTIN_TRUST_TEST_PACKS.find((p) => p.id === packId);
    if (!builtin) return undefined;
    return trustScenarioPacks.find((p) => p.name === `${TRUST_PACK_PREFIX}${builtin.name}`);
  }

  const createPackMutation = useMutation({
    mutationFn: (packId: string) => {
      const builtin = BUILTIN_TRUST_TEST_PACKS.find((p) => p.id === packId)!;
      return apiClient.createScenarioPack(selectedShopId!, mapTrustPackToScenarioPackInput(builtin));
    },
    onSuccess: () => {
      void packsQuery.refetch();
    },
    onError: (err) => {
      showToast(err instanceof Error ? err.message : 'Failed to create scenario pack', 'error');
    },
  });

  const runMutation = useMutation({
    mutationFn: async (packId: string) => {
      const shopId = selectedShopId!;
      let pack = findTrustScenarioPack(packId);
      if (!pack) {
        pack = await createPackMutation.mutateAsync(packId);
      }
      const { run } = await apiClient.runReplay(shopId, {
        label: `Trust run — ${pack.name}`,
        scenarios: packToScenarios(pack),
      });
      return run;
    },
    onSuccess: (run: SimulatorRunDetail) => {
      void finishRun(run);
    },
    onError: (err) => {
      showToast(err instanceof Error ? err.message : 'Trust run failed', 'error');
      setRunningPackId(null);
    },
  });

  async function finishRun(run: SimulatorRunDetail) {
    const detail = await apiClient.getReplayRun(selectedShopId!, run.id);
    const builtin = BUILTIN_TRUST_TEST_PACKS.find((p) => runningPackId === p.id);
    if (!builtin) {
      setRunningPackId(null);
      return;
    }
    const results = evaluateRunResults(builtin, detail);
    const summary: TrustEvaluationSummary = summarizeTrustResults(results);
    const evaluationRun: TrustEvaluationRun = {
      id: detail.id,
      packId: builtin.id,
      packName: builtin.name,
      startedAt: detail.started_at,
      completedAt: detail.completed_at,
      summary,
      results,
    };
    saveCachedTrustRun(selectedShopId!, evaluationRun);
    setCachedRun(evaluationRun);
    setRunningPackId(null);
    void runsQuery.refetch();
    showToast(
      summary.safeToRollout
        ? `Trust run complete: ${summary.passed}/${summary.total} passed.`
        : `Trust run complete: ${summary.criticalFailures + summary.highFailures} blocker(s).`,
      summary.safeToRollout ? 'success' : 'error',
    );
  }

  function handleRunPack(packId: string) {
    if (!selectedShopId) return;
    setRunningPackId(packId);
    runMutation.mutate(packId);
  }

  if (!selectedShopId) {
    return (
      <Card>
        <CardBody>
          <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
        </CardBody>
      </Card>
    );
  }

  const summary = cachedRun?.summary ?? null;
  const results = cachedRun?.results ?? [];
  const lastRunPassRate = summary && summary.total > 0
    ? `${Math.round((summary.passed / summary.total) * 100)}%`
    : '—';

  const readinessSignals = buildTrustReadinessSignals(
    summary,
    shopReadiness.shopReadiness,
    null,
  );

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-semibold text-fg">Trust Center</h1>
        <p className="mt-1 text-sm text-muted">
          Run safety, policy, and red-team checks before expanding automation.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <KpiCard label="Test packs" value={String(BUILTIN_TRUST_TEST_PACKS.length)} />
        <KpiCard label="Last run pass rate" value={lastRunPassRate} tone="accent" />
        <KpiCard
          label="Critical failures"
          value={summary ? String(summary.criticalFailures) : '—'}
          tone="danger"
        />
        <KpiCard
          label="High-risk failures"
          value={summary ? String(summary.highFailures) : '—'}
          tone="warning"
        />
        <KpiCard
          label="Safe to rollout"
          value={summary ? (summary.safeToRollout ? 'Yes' : 'No') : '—'}
          tone={summary?.safeToRollout ? 'success' : 'danger'}
        />
      </div>

      {packsQuery.isLoading ? (
        <LoadingState />
      ) : packsQuery.error ? (
        <ErrorState message={packsQuery.error instanceof Error ? packsQuery.error.message : 'Failed to load packs'} />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {BUILTIN_TRUST_TEST_PACKS.map((pack) => (
            <TrustTestPackCard
              key={pack.id}
              pack={pack}
              onRun={() => handleRunPack(pack.id)}
              running={runningPackId === pack.id}
              hasScenarioPack={Boolean(findTrustScenarioPack(pack.id))}
              disabled={runMutation.isPending}
            />
          ))}
        </div>
      )}

      {runMutation.isError ? (
        <ErrorState
          message={runMutation.error instanceof Error ? runMutation.error.message : 'Trust run failed'}
        />
      ) : null}

      <TrustEvaluationSummaryPanel
        summary={summary}
        loading={runMutation.isPending}
        packName={cachedRun?.packName ?? null}
      />

      <TrustFailureTable results={results} />

      <TrustReadinessPanel
        signals={readinessSignals}
        loading={shopReadiness.isLoading}
        error={shopReadiness.error instanceof Error ? shopReadiness.error.message : null}
      />

      <Card>
        <CardHeader
          title="Live simulation status"
          description="Replay runs recorded for this shop, including trust runs."
          actions={<Badge tone="neutral">{runsQuery.data?.length ?? 0}</Badge>}
        />
        <CardBody>
          {runsQuery.isLoading ? (
            <LoadingState />
          ) : runsQuery.error ? (
            <ErrorState message={runsQuery.error instanceof Error ? runsQuery.error.message : 'Failed to load runs'} />
          ) : !runsQuery.data || runsQuery.data.length === 0 ? (
            <EmptyState
              title="No replay runs yet"
              description="Run a built-in pack above to record a trust evaluation. Nothing is sent to customers."
            />
          ) : (
            <ul className="flex flex-col gap-1.5 text-sm">
              {runsQuery.data.slice(0, 5).map((run) => (
                <li key={run.id} className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2">
                  <span className="truncate text-fg">{run.label ?? run.id.slice(0, 8)}</span>
                  <span className="tabular-nums text-muted">
                    {run.passed_items}/{run.total_items} passed
                  </span>
                  <Badge tone={run.status === 'completed' ? 'success' : 'neutral'}>{run.status}</Badge>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      <div className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          size="sm"
          type="button"
          onClick={() => {
            if (!summary || !cachedRun) return;
            const json = JSON.stringify(cachedRun, null, 2);
            void navigator.clipboard?.writeText(json);
            showToast('Copied latest trust evaluation JSON', 'info');
          }}
          disabled={!cachedRun}
        >
          Copy latest evaluation JSON
        </Button>
        <Button
          variant="secondary"
          size="sm"
          type="button"
          onClick={() => {
            if (!selectedShopId) return;
            clearCachedTrustRun(selectedShopId);
            setCachedRun(null);
            showToast('Cleared cached trust evaluation', 'info');
          }}
          disabled={!cachedRun}
        >
          Clear cached evaluation
        </Button>
      </div>
    </div>
  );
}
