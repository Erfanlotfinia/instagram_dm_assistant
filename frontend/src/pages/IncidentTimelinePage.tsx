import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';

import { HubPage } from '../components/shell/HubPage';
import { Badge, Card, CardBody, CardHeader } from '../components/ui';
import { DataTable, EmptyState, LoadingState } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';
import type { Incident } from '../types/trust';

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

  const listColumns: Column<Incident>[] = [
    { key: 'title', header: 'Title', render: (row) => row.title },
    { key: 'severity', header: 'Severity', render: (row) => <Badge tone={row.severity === 'critical' ? 'danger' : 'warning'}>{row.severity}</Badge> },
    { key: 'status', header: 'Status', render: (row) => <Badge tone="neutral">{row.status}</Badge> },
    { key: 'trigger', header: 'Trigger', render: (row) => row.trigger },
    { key: 'opened', header: 'Opened', render: (row) => new Date(row.opened_at).toLocaleString() },
    {
      key: 'action',
      header: 'Action',
      render: (row) => (
        <Link className="font-medium text-accent hover:underline" to={`/incidents/${row.id}`}>
          Timeline
        </Link>
      ),
    },
  ];

  return (
    <HubPage
      eyebrow="Trust layer"
      title="Incident Timeline"
      description="Audit trail of mode changes, emergency stops, and affected conversations."
    >
      {!selectedShopId ? (
        <Card>
          <CardBody>
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          </CardBody>
        </Card>
      ) : null}

      {!incidentId && selectedShopId ? (
        <Card>
          <CardHeader title="Recent incidents" />
          <DataTable
            columns={listColumns}
            rows={incidents}
            rowKey={(row) => row.id}
            isLoading={listQuery.isLoading}
            emptyTitle="No incidents recorded yet"
          />
        </Card>
      ) : null}

      {incidentId && detailQuery.isLoading ? (
        <Card>
          <CardBody>
            <LoadingState label="Loading incident…" />
          </CardBody>
        </Card>
      ) : null}

      {incident ? (
        <Card>
          <CardHeader
            title={incident.title}
            actions={<Badge tone={incident.severity === 'critical' ? 'danger' : 'warning'}>{incident.status}</Badge>}
          />
          <CardBody className="space-y-4">
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

            <div>
              <h3 className="mb-3 text-sm font-semibold text-fg">Timeline</h3>
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
            </div>

            <Link className="inline-flex h-10 items-center rounded-lg border border-border bg-surface px-4 text-sm font-medium text-fg hover:bg-surface-sunken" to="/incidents">
              Back to incidents
            </Link>
          </CardBody>
        </Card>
      ) : null}
    </HubPage>
  );
}
