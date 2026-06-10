import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { DecisionTraceDrawer } from './DecisionTraceDrawer';
import { useShop } from '../../contexts/ShopContext';
import { useToast } from '../../contexts/ToastContext';
import { apiClient } from '../../services/apiClient';
import type { AssembledDecisionTrace, ReplayScenarioInput, ScenarioPack, SimulatorRunItem } from '../../types/trust';

const GOLDEN_SCENARIOS: ReplayScenarioInput[] = [
  { item_key: 'buy-black-l', message_text: 'می‌خوام مشکی سایز L', expected_json: { intent: 'buy_product' } },
  { item_key: 'ask-price', message_text: 'قیمت چنده؟', expected_json: { intent: 'ask_price' } },
  {
    item_key: 'handoff',
    message_text: 'با مدیر صحبت کنم، عصبانیم',
    expected_json: { intent: 'human_help', requires_handoff: true },
  },
];

function packToScenarios(pack: ScenarioPack): ReplayScenarioInput[] {
  return pack.scenarios_json.map((scenario, index) => ({
    item_key: String(scenario.item_key ?? `pack-${index + 1}`),
    message_text: String(scenario.message_text ?? ''),
    shared_post_url: scenario.shared_post_url ? String(scenario.shared_post_url) : null,
    expected_json: (scenario.expected_json as Record<string, unknown> | undefined) ?? {},
  }));
}

function ReplayItemRow({
  item,
  onInspectTrace,
}: {
  item: SimulatorRunItem;
  onInspectTrace: (traceId: string) => void;
}) {
  const mismatches = item.diff_json.mismatches ?? [];
  return (
    <tr className={item.passed ? undefined : 'data-table__row--attention'}>
      <td>{item.item_key}</td>
      <td>
        <span className={item.passed ? 'priority-badge priority-badge--low' : 'priority-badge priority-badge--high'}>
          {item.passed ? 'Pass' : 'Fail'}
        </span>
      </td>
      <td>{String(item.actual_json.intent ?? '—')}</td>
      <td>{String(item.expected_json.intent ?? '—')}</td>
      <td>{mismatches.length ? mismatches.join('; ') : '—'}</td>
      <td>
        {item.trace_id ? (
          <button className="button button--ghost-dark" type="button" onClick={() => onInspectTrace(item.trace_id!)}>
            Trace
          </button>
        ) : (
          '—'
        )}
      </td>
    </tr>
  );
}

export function ReplayPanel() {
  const { selectedShopId, shops } = useShop();
  const { showToast } = useToast();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [traceId, setTraceId] = useState<string | null>(null);
  const [modelVersion, setModelVersion] = useState('');
  const [promptVersion, setPromptVersion] = useState('');
  const [campaign, setCampaign] = useState('');
  const [packName, setPackName] = useState('Golden replay pack');
  const [selectedPackId, setSelectedPackId] = useState<string | null>(null);

  const scenarioPacksQuery = useQuery({
    queryKey: ['scenario-packs', selectedShopId],
    queryFn: () => apiClient.listScenarioPacks(selectedShopId || shops[0]?.id || ''),
    enabled: Boolean(selectedShopId),
  });

  const replayRunsQuery = useQuery({
    queryKey: ['replay-runs', selectedShopId],
    queryFn: () => apiClient.listReplayRuns(selectedShopId || shops[0]?.id || ''),
    enabled: Boolean(selectedShopId),
  });

  const runDetailQuery = useQuery({
    queryKey: ['replay-run', selectedShopId, selectedRunId],
    queryFn: () => apiClient.getReplayRun(selectedShopId!, selectedRunId!),
    enabled: Boolean(selectedShopId && selectedRunId),
  });

  const traceQuery = useQuery({
    queryKey: ['trust-trace', selectedShopId, traceId],
    queryFn: () => apiClient.getTrustTrace(selectedShopId || shops[0]?.id || '', traceId!),
    enabled: Boolean(selectedShopId && traceId),
  });

  const replayMutation = useMutation({
    mutationFn: (scenarios: ReplayScenarioInput[]) =>
      apiClient.runReplay(selectedShopId || shops[0]?.id || '', {
        label: 'Manual replay run',
        model_version: modelVersion || null,
        prompt_version: promptVersion || null,
        campaign: campaign || null,
        scenarios,
      }),
    onSuccess: (data) => {
      showToast(`Replay completed: ${data.run.passed_items}/${data.run.total_items} passed`, 'success');
      setSelectedRunId(data.run.id);
      void replayRunsQuery.refetch();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Replay failed', 'error'),
  });

  const createPackMutation = useMutation({
    mutationFn: () =>
      apiClient.createScenarioPack(selectedShopId || shops[0]?.id || '', {
        name: packName,
        pack_type: 'handcrafted',
        scenarios_json: GOLDEN_SCENARIOS,
        is_golden: true,
      }),
    onSuccess: (pack) => {
      showToast(`Scenario pack saved: ${pack.name}`, 'success');
      setSelectedPackId(pack.id);
      void scenarioPacksQuery.refetch();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Failed to save pack', 'error'),
  });

  const selectedPack = scenarioPacksQuery.data?.find((pack) => pack.id === selectedPackId) ?? null;

  const run = runDetailQuery.data;

  return (
    <div className="page-stack">
      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header section-header--stacked">
          <div>
            <h2>Deterministic replay</h2>
            <p className="dashboard-card__subtitle">
              Replays golden scenarios against frozen catalog snapshot and deterministic orchestrator.
            </p>
          </div>
        </div>
        <div className="filter-grid">
          <label className="form-field">
            <span>Model version</span>
            <input value={modelVersion} onChange={(e) => setModelVersion(e.target.value)} placeholder="gpt-4o-mini" />
          </label>
          <label className="form-field">
            <span>Prompt version</span>
            <input value={promptVersion} onChange={(e) => setPromptVersion(e.target.value)} placeholder="trust-layer-v1" />
          </label>
          <label className="form-field">
            <span>Campaign filter</span>
            <input value={campaign} onChange={(e) => setCampaign(e.target.value)} placeholder="Optional" />
          </label>
        </div>
        <div className="button-row">
          <button
            className="button button--primary"
            type="button"
            disabled={!selectedShopId || replayMutation.isPending}
            onClick={() => replayMutation.mutate(GOLDEN_SCENARIOS)}
          >
            {replayMutation.isPending ? 'Running replay…' : 'Run golden replay pack'}
          </button>
        </div>
      </section>

      <section className="dashboard-card dashboard-card--wide">
        <div className="section-header section-header--stacked">
          <div>
            <h3>Scenario packs</h3>
            <p className="dashboard-card__subtitle">Save and replay handcrafted or synthetic scenario collections.</p>
          </div>
        </div>
        <div className="filter-grid">
          <label className="form-field">
            <span>Pack name</span>
            <input value={packName} onChange={(e) => setPackName(e.target.value)} />
          </label>
          <label className="form-field">
            <span>Run from pack</span>
            <select value={selectedPackId ?? ''} onChange={(e) => setSelectedPackId(e.target.value || null)}>
              <option value="">Select saved pack</option>
              {scenarioPacksQuery.data?.map((pack) => (
                <option key={pack.id} value={pack.id}>
                  {pack.name} ({pack.scenarios_json.length} scenarios)
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="button-row">
          <button
            className="button button--ghost-dark"
            type="button"
            disabled={!selectedShopId || !packName.trim() || createPackMutation.isPending}
            onClick={() => createPackMutation.mutate()}
          >
            {createPackMutation.isPending ? 'Saving…' : 'Save golden pack'}
          </button>
          <button
            className="button button--primary"
            type="button"
            disabled={!selectedShopId || !selectedPack || replayMutation.isPending}
            onClick={() => selectedPack && replayMutation.mutate(packToScenarios(selectedPack))}
          >
            {replayMutation.isPending ? 'Running replay…' : 'Run selected pack'}
          </button>
        </div>
      </section>

      {replayRunsQuery.data && replayRunsQuery.data.length > 0 ? (
        <section className="dashboard-card dashboard-card--wide">
          <h3>Replay runs</h3>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Label</th>
                  <th scope="col">Status</th>
                  <th scope="col">Pass rate</th>
                  <th scope="col">Model</th>
                  <th scope="col">Action</th>
                </tr>
              </thead>
              <tbody>
                {replayRunsQuery.data.map((item) => (
                  <tr key={item.id}>
                    <td>{item.label ?? item.id.slice(0, 8)}</td>
                    <td>{item.status}</td>
                    <td>
                      {item.passed_items}/{item.total_items}
                    </td>
                    <td>{item.model_version}</td>
                    <td>
                      <button className="table-link" type="button" onClick={() => setSelectedRunId(item.id)}>
                        View diff
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {run ? (
        <section className="dashboard-card dashboard-card--wide">
          <h3>Regression diff — {run.label ?? run.id}</h3>
          <div className="stats-grid">
            <article className="stat-card">
              <p className="stat-card__label">Passed</p>
              <p className="stat-card__value">{run.passed_items}</p>
            </article>
            <article className="stat-card">
              <p className="stat-card__label">Failed</p>
              <p className="stat-card__value">{run.failed_items}</p>
            </article>
            <article className="stat-card">
              <p className="stat-card__label">Catalog hash</p>
              <p className="stat-card__value">{run.catalog_snapshot_hash.slice(0, 12)}…</p>
            </article>
          </div>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Scenario</th>
                  <th scope="col">Result</th>
                  <th scope="col">Actual intent</th>
                  <th scope="col">Expected intent</th>
                  <th scope="col">Diff</th>
                  <th scope="col">Trace</th>
                </tr>
              </thead>
              <tbody>
                {run.items.map((item) => (
                  <ReplayItemRow key={item.id} item={item} onInspectTrace={setTraceId} />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <DecisionTraceDrawer
        open={Boolean(traceId)}
        trace={(traceQuery.data as AssembledDecisionTrace | undefined) ?? null}
        loading={traceQuery.isLoading}
        onClose={() => setTraceId(null)}
      />
    </div>
  );
}
