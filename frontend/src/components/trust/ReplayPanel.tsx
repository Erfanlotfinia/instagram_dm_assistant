import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';

import { DecisionTraceDrawer } from './DecisionTraceDrawer';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input, Select } from '../ui';
import { DataTable, EmptyState, KpiCard } from '../data';
import type { Column } from '../data';
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

type ReplayRunRow = {
  id: string;
  label?: string | null;
  status: string;
  passed_items: number;
  total_items: number;
  model_version: string | null;
};

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

  const runColumns: Column<ReplayRunRow>[] = [
    { key: 'label', header: 'Label', render: (row) => row.label ?? row.id.slice(0, 8) },
    { key: 'status', header: 'Status', render: (row) => <Badge tone="neutral">{row.status}</Badge> },
    {
      key: 'pass',
      header: 'Pass rate',
      render: (row) => (
        <span className="tabular-nums">
          {row.passed_items}/{row.total_items}
        </span>
      ),
    },
    { key: 'model', header: 'Model', render: (row) => row.model_version ?? '—' },
    {
      key: 'action',
      header: 'Action',
      render: (row) => (
        <Button variant="ghost" size="sm" type="button" onClick={() => setSelectedRunId(row.id)}>
          View diff
        </Button>
      ),
    },
  ];

  const itemColumns: Column<SimulatorRunItem>[] = [
    { key: 'key', header: 'Scenario', render: (item) => item.item_key },
    {
      key: 'result',
      header: 'Result',
      render: (item) => <Badge tone={item.passed ? 'success' : 'danger'}>{item.passed ? 'Pass' : 'Fail'}</Badge>,
    },
    { key: 'actual', header: 'Actual intent', render: (item) => String(item.actual_json.intent ?? '—') },
    { key: 'expected', header: 'Expected intent', render: (item) => String(item.expected_json.intent ?? '—') },
    {
      key: 'diff',
      header: 'Diff',
      render: (item) => (item.diff_json.mismatches?.length ? item.diff_json.mismatches.join('; ') : '—'),
    },
    {
      key: 'trace',
      header: 'Trace',
      render: (item) =>
        item.trace_id ? (
          <Button variant="ghost" size="sm" type="button" onClick={() => setTraceId(item.trace_id!)}>
            Trace
          </Button>
        ) : (
          '—'
        ),
    },
  ];

  if (!selectedShopId) {
    return (
      <Card>
        <CardBody>
          <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
        </CardBody>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <Card>
        <CardHeader
          title="Deterministic replay"
          description="Replays golden scenarios against frozen catalog snapshot and deterministic orchestrator."
        />
        <CardBody>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Model version">
              <Input value={modelVersion} onChange={(e) => setModelVersion(e.target.value)} placeholder="gpt-4o-mini" />
            </Field>
            <Field label="Prompt version">
              <Input value={promptVersion} onChange={(e) => setPromptVersion(e.target.value)} placeholder="trust-layer-v1" />
            </Field>
            <Field label="Campaign filter">
              <Input value={campaign} onChange={(e) => setCampaign(e.target.value)} placeholder="Optional" />
            </Field>
          </div>
          <div className="mt-4">
            <Button type="button" disabled={replayMutation.isPending} onClick={() => replayMutation.mutate(GOLDEN_SCENARIOS)}>
              {replayMutation.isPending ? 'Running replay…' : 'Run golden replay pack'}
            </Button>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Scenario packs" description="Save and replay handcrafted or synthetic scenario collections." />
        <CardBody>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Pack name">
              <Input value={packName} onChange={(e) => setPackName(e.target.value)} />
            </Field>
            <Field label="Run from pack">
              <Select value={selectedPackId ?? ''} onChange={(e) => setSelectedPackId(e.target.value || null)}>
                <option value="">Select saved pack</option>
                {scenarioPacksQuery.data?.map((pack) => (
                  <option key={pack.id} value={pack.id}>
                    {pack.name} ({pack.scenarios_json.length} scenarios)
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button
              variant="secondary"
              type="button"
              disabled={!packName.trim() || createPackMutation.isPending}
              onClick={() => createPackMutation.mutate()}
            >
              {createPackMutation.isPending ? 'Saving…' : 'Save golden pack'}
            </Button>
            <Button
              type="button"
              disabled={!selectedPack || replayMutation.isPending}
              onClick={() => selectedPack && replayMutation.mutate(packToScenarios(selectedPack))}
            >
              {replayMutation.isPending ? 'Running replay…' : 'Run selected pack'}
            </Button>
          </div>
        </CardBody>
      </Card>

      {replayRunsQuery.data && replayRunsQuery.data.length > 0 ? (
        <Card>
          <CardHeader title="Replay runs" />
          <DataTable
            columns={runColumns}
            rows={replayRunsQuery.data}
            rowKey={(row) => row.id}
            emptyTitle="No replay runs"
          />
        </Card>
      ) : null}

      {run ? (
        <Card>
          <CardHeader title={`Regression diff — ${run.label ?? run.id}`} />
          <CardBody className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <KpiCard label="Passed" value={String(run.passed_items)} tone="success" />
              <KpiCard label="Failed" value={String(run.failed_items)} tone="danger" />
              <KpiCard label="Catalog hash" value={`${run.catalog_snapshot_hash.slice(0, 12)}…`} />
            </div>
            <DataTable columns={itemColumns} rows={run.items} rowKey={(item) => item.id} emptyTitle="No items" />
          </CardBody>
        </Card>
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
