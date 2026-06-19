import { useState } from 'react';

import { Button, Card, CardBody, CardHeader, Field, Input } from '../ui';
import { useToast } from '../../contexts/ToastContext';
import { apiClient } from '../../services/apiClient';
import type { ChannelProvider } from '../../types/channel';

interface InstagramAdvancedSetupProps {
  shopId: string;
  disabled?: boolean;
  onSaved: () => void;
}

export function InstagramAdvancedSetup({
  shopId,
  disabled = false,
  onSaved,
}: InstagramAdvancedSetupProps) {
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [displayName, setDisplayName] = useState('Instagram');
  const [externalAccountId, setExternalAccountId] = useState('');
  const [pageId, setPageId] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [webhookVerifyToken, setWebhookVerifyToken] = useState('');
  const [webhookSecret, setWebhookSecret] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const account = await apiClient.createChannelAccount(shopId, {
        provider: 'instagram' as ChannelProvider,
        display_name: displayName,
        external_account_id: externalAccountId || undefined,
        webhook_verify_token: webhookVerifyToken || undefined,
        settings: pageId ? { page_id: pageId } : {},
      });
      await apiClient.updateChannelCredentials(shopId, account.id, {
        access_token: accessToken || undefined,
        webhook_secret: webhookSecret || undefined,
        webhook_verify_token: webhookVerifyToken || undefined,
      });
      showToast('Advanced Instagram setup saved.', 'success');
      setExternalAccountId('');
      setPageId('');
      setAccessToken('');
      setWebhookVerifyToken('');
      setWebhookSecret('');
      onSaved();
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Advanced setup failed', 'error');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Advanced / developer setup only"
        description="Manual tokens and IDs for debugging. Normal shop owners should use Connect Instagram above."
        actions={
          <Button type="button" variant="secondary" size="sm" onClick={() => setOpen((value) => !value)}>
            {open ? 'Hide' : 'Show'}
          </Button>
        }
      />
      {open ? (
        <CardBody>
          <form
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault();
              void handleSubmit();
            }}
          >
            <Field label="Display name">
              <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} disabled={disabled} />
            </Field>
            <Field label="Instagram Business Account ID">
              <Input
                value={externalAccountId}
                onChange={(e) => setExternalAccountId(e.target.value)}
                required
                disabled={disabled}
              />
            </Field>
            <Field label="Facebook Page ID">
              <Input value={pageId} onChange={(e) => setPageId(e.target.value)} disabled={disabled} />
            </Field>
            <Field label="Page access token">
              <Input
                type="password"
                autoComplete="new-password"
                value={accessToken}
                onChange={(e) => setAccessToken(e.target.value)}
                disabled={disabled}
              />
            </Field>
            <Field label="Webhook verify token">
              <Input
                type="password"
                autoComplete="new-password"
                value={webhookVerifyToken}
                onChange={(e) => setWebhookVerifyToken(e.target.value)}
                disabled={disabled}
              />
            </Field>
            <Field label="Webhook secret">
              <Input
                type="password"
                autoComplete="new-password"
                value={webhookSecret}
                onChange={(e) => setWebhookSecret(e.target.value)}
                disabled={disabled}
              />
            </Field>
            <div className="sm:col-span-2">
              <Button type="submit" disabled={disabled || isSubmitting}>
                Save advanced setup
              </Button>
            </div>
          </form>
        </CardBody>
      ) : null}
    </Card>
  );
}
