import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';
import type { TRLValidationRun, TRLValidationScenarioResult } from '../types/trlValidation';

function percent(value: unknown) {
  return typeof value === 'number' ? `${Math.round(value * 100)}%` : '—';
}

export function TRLValidationPage() {
  const { selectedShop } = useShop();
  const [runs, setRuns] = useState<TRLValidationRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<TRLValidationRun | null>(null);
  const [scenarios, setScenarios] = useState<TRLValidationScenarioResult[]>([]);
  const [filter, setFilter] = useState<'all' | 'passed' | 'failed'>('all');
  const [detail, setDetail] = useState<TRLValidationScenarioResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadRuns() {
    if (!selectedShop) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.listTRLValidationRuns(selectedShop.id);
      setRuns(data);
      setSelectedRun(data[0] ?? null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Failed to load TRL validation runs');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadRuns(); }, [selectedShop?.id]);

  useEffect(() => {
    if (!selectedShop || !selectedRun) {
      setScenarios([]);
      return;
    }
    const passed = filter === 'all' ? undefined : filter === 'passed';
    apiClient.listTRLValidationScenarios(selectedShop.id, selectedRun.id, passed)
      .then(setScenarios)
      .catch((exc) => setError(exc instanceof Error ? exc.message : 'Failed to load scenarios'));
  }, [selectedShop?.id, selectedRun?.id, filter]);

  const metrics = selectedRun?.metrics_json ?? {};
  const thresholdRows = useMemo(() => Object.entries((metrics.thresholds_passed ?? {}) as Record<string, boolean>), [metrics]);

  async function runValidation() {
    if (!selectedShop) return;
    setLoading(true); setError(null);
    try {
      const run = await apiClient.runTRLValidation(selectedShop.id, { reset_demo_data: false });
      await loadRuns();
      setSelectedRun(run);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Failed to run validation');
    } finally { setLoading(false); }
  }

  async function resetValidation() {
    if (!selectedShop) return;
    setLoading(true); setError(null);
    try {
      await apiClient.resetTRLValidation(selectedShop.id);
      setRuns([]); setSelectedRun(null); setScenarios([]); setDetail(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Failed to reset validation data');
    } finally { setLoading(false); }
  }

  if (!selectedShop) return <section className="card"><h2>TRL Validation</h2><p>Select a shop to run validation.</p></section>;

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <h1>TRL 5 Validation</h1>
          <p>Run a repeatable relevant-environment simulator without sending real Instagram messages.</p>
        </div>
        <div className="button-row">
          <button className="button" type="button" onClick={runValidation} disabled={loading}>Run validation</button>
          <button className="button button--ghost" type="button" onClick={resetValidation} disabled={loading}>Reset validation data</button>
        </div>
      </header>
      {error ? <div role="alert" className="alert alert--error">{error}</div> : null}
      {loading ? <p>Loading TRL validation…</p> : null}
      {!loading && !selectedRun ? <div className="card"><h2>No validation runs yet</h2><p>Run validation to generate TRL 5 metrics.</p></div> : null}
      {selectedRun ? (
        <>
          <div className="card">
            <h2>Latest run summary</h2>
            <p>Status: <strong>{selectedRun.status}</strong></p>
            <p>{selectedRun.passed_scenarios}/{selectedRun.total_scenarios} scenarios passed · {selectedRun.failed_scenarios} failed</p>
            <div className="metric-grid">
              <div><span>Intent accuracy</span><strong>{percent(metrics.intent_accuracy)}</strong></div>
              <div><span>Slot accuracy</span><strong>{percent(metrics.slot_extraction_accuracy)}</strong></div>
              <div><span>Product resolution</span><strong>{percent(metrics.product_resolution_accuracy)}</strong></div>
              <div><span>Variant resolution</span><strong>{percent(metrics.variant_resolution_accuracy)}</strong></div>
              <div><span>False sends</span><strong>{String(metrics.false_auto_send_count ?? 0)}</strong></div>
              <div><span>False orders</span><strong>{String(metrics.false_order_creation_count ?? 0)}</strong></div>
            </div>
          </div>
          <div className="card">
            <h2>Acceptance thresholds</h2>
            {thresholdRows.length ? <ul>{thresholdRows.map(([name, ok]) => <li key={name}>{ok ? '✅' : '❌'} {name}</li>)}</ul> : <p>No threshold evaluation yet.</p>}
          </div>
          <div className="card">
            <div className="table-toolbar">
              <h2>Scenario results</h2>
              <select aria-label="Filter scenarios" value={filter} onChange={(event) => setFilter(event.target.value as typeof filter)}>
                <option value="all">All</option><option value="passed">Passed</option><option value="failed">Failed</option>
              </select>
            </div>
            <table className="data-table">
              <thead><tr><th>ID</th><th>Status</th><th>Intent</th><th>State</th><th>Time</th><th>Links</th></tr></thead>
              <tbody>{scenarios.map((row) => <tr key={row.id} onClick={() => setDetail(row)}>
                <td>{row.scenario_id}</td><td>{row.passed ? 'Passed' : 'Failed'}</td><td>{String(row.actual_json.intent ?? '—')}</td><td>{String(row.actual_json.state ?? '—')}</td><td>{row.processing_time_ms}ms</td>
                <td>{row.conversation_id ? <Link to={`/conversations/${row.conversation_id}`}>Conversation</Link> : null} {row.conversation_id ? <Link to={`/conversations/${row.conversation_id}#decision-trace`}>Decision trace</Link> : null}</td>
              </tr>)}</tbody>
            </table>
          </div>
          {detail ? <div className="card" role="dialog" aria-label="Scenario detail"><h2>Scenario detail: {detail.scenario_id}</h2><p>{detail.passed ? 'Passed' : 'Failed scenario detail'}</p><pre>{JSON.stringify({ input: detail.input_json, expected: detail.expected_json, actual: detail.actual_json, failure_reasons: detail.failure_reasons }, null, 2)}</pre><button className="button button--ghost" onClick={() => setDetail(null)}>Close</button></div> : null}
        </>
      ) : null}
    </section>
  );
}
