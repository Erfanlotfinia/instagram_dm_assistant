import { useEffect, useState } from 'react';

import { Badge, Callout, Card, CardBody, CardHeader } from '../ui';
import { apiClient } from '../../services/apiClient';
import type { InstagramReadiness } from '../../types/channel';

interface InstagramReadinessPanelProps {
  shopId: string;
}

export function InstagramReadinessPanel({ shopId }: InstagramReadinessPanelProps) {
  const [readiness, setReadiness] = useState<InstagramReadiness | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void apiClient
      .getInstagramReadiness(shopId)
      .then(setReadiness)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : 'Failed to load readiness checklist');
      });
  }, [shopId]);

  if (error) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-danger">{error}</p>
        </CardBody>
      </Card>
    );
  }

  if (!readiness) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-muted">Loading Instagram readiness checklist…</p>
        </CardBody>
      </Card>
    );
  }

  const missingRequired =
    !readiness.meta_app_id_configured ||
    !readiness.meta_app_secret_configured ||
    !readiness.webhook_callback_reachable;

  const items = [
    { label: 'Meta App ID configured', ok: readiness.meta_app_id_configured },
    { label: 'Meta App Secret configured', ok: readiness.meta_app_secret_configured },
    { label: 'OAuth redirect URI configured', ok: Boolean(readiness.oauth_redirect_uri) },
    { label: 'Data deletion callback configured', ok: readiness.data_deletion_callback_configured },
    { label: 'Privacy policy URL configured', ok: Boolean(readiness.privacy_policy_url) },
    { label: 'Required permissions configured', ok: readiness.required_scopes.length > 0 },
    { label: `App mode: ${readiness.app_mode}`, ok: true },
    { label: 'Webhook callback reachable', ok: readiness.webhook_callback_reachable },
    { label: `App review: ${readiness.app_review_status}`, ok: true },
  ];

  return (
    <Card>
      <CardHeader
        title="Instagram connection readiness"
        description="Internal checklist for owners, admins, and support. Does not block local development."
      />
      <CardBody className="flex flex-col gap-4">
        {missingRequired ? (
          <Callout title="Production warning">
            Some required Meta configuration items are missing. Instagram connection may fail until they are
            resolved.
          </Callout>
        ) : null}
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.label} className="flex items-center justify-between gap-2 text-sm">
              <span className="text-fg">{item.label}</span>
              <Badge tone={item.ok ? 'success' : 'neutral'}>{item.ok ? 'OK' : 'Missing'}</Badge>
            </li>
          ))}
        </ul>
        <div className="text-xs text-muted">
          <p>OAuth redirect: {readiness.oauth_redirect_uri}</p>
          <p>Webhook callback: {readiness.webhook_callback_url}</p>
          <p>Scopes: {readiness.required_scopes.join(', ')}</p>
        </div>
      </CardBody>
    </Card>
  );
}
