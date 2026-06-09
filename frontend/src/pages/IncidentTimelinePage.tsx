import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';

import { ShopSelector } from '../components/ShopSelector';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';

export function IncidentTimelinePage() {
  const { incidentId } = useParams<{ incidentId?: string }>();
  const { selectedShopId } = useShop();

  const listQuery = useQuery({
    queryKey: ['incidents', selectedShopId],
    queryFn: () => apiClient.listIncidents(selectedShopId!),
    enabled: Boolean(selectedShopId),
  });

  const detailQuery = useQuery({
    queryKey: ['incident', selectedShopId, incidentId],
    queryFn: () => apiClient.getIncident(selectedShopId!, incidentId!),
    enabled: Boolean(selectedShopId && incidentId),
  });

  const incident = detailQuery.data;
  const incidents = listQuery.data ?? [];

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Trust layer</p>
        <h1>Incident Timeline</h1>
        <p>Audit trail of mode changes, emergency stops, and affected conversations.</p>
        <ShopSelector />
      </section>

      {!incidentId ? (
        <section className="dashboard-card dashboard-card--wide">
          <h2>Recent incidents</h2>
          {listQuery.isLoading ? <p className="loading-state">Loading incidents…</p> : null}
          {!listQuery.isLoading && incidents.length === 0 ? (
            <p className="empty-state">No incidents recorded yet.</p>
          ) : null}
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Title</th>
                  <th scope="col">Severity</th>
                  <th scope="col">Status</th>
                  <th scope="col">Trigger</th>
                  <th scope="col">Opened</th>
                  <th scope="col">Action</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((row) => (
                  <tr key={row.id}>
                    <td>{row.title}</td>
                    <td>{row.severity}</td>
                    <td>{row.status}</td>
                    <td>{row.trigger}</td>
                    <td>{new Date(row.opened_at).toLocaleString()}</td>
                    <td>
                      <Link className="table-link" to={`/incidents/${row.id}`}>
                        Timeline
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {incidentId && detailQuery.isLoading ? <p className="loading-state">Loading incident…</p> : null}
      {incident ? (
        <section className="dashboard-card dashboard-card--wide">
          <div className="section-header">
            <h2>{incident.title}</h2>
            <span className={`priority-badge priority-badge--${incident.severity === 'critical' ? 'urgent' : 'high'}`}>
              {incident.status}
            </span>
          </div>
          <dl className="detail-grid">
            <div>
              <dt>Trigger</dt>
              <dd>{incident.trigger}</dd>
            </div>
            <div>
              <dt>Opened</dt>
              <dd>{new Date(incident.opened_at).toLocaleString()}</dd>
            </div>
            <div>
              <dt>Summary</dt>
              <dd>
                <pre className="resolver-raw-json">{JSON.stringify(incident.summary_json, null, 2)}</pre>
              </dd>
            </div>
          </dl>
          <h3>Timeline</h3>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Time</th>
                  <th scope="col">Event</th>
                  <th scope="col">Description</th>
                  <th scope="col">Affected conversations</th>
                </tr>
              </thead>
              <tbody>
                {(incident.events ?? []).map((event) => (
                  <tr key={event.id}>
                    <td>{new Date(event.created_at).toLocaleString()}</td>
                    <td>{event.event_type}</td>
                    <td>{event.description ?? '—'}</td>
                    <td>{event.affected_conversation_ids.length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Link className="button button--ghost-dark" to="/incidents">
            Back to incidents
          </Link>
        </section>
      ) : null}
    </div>
  );
}
