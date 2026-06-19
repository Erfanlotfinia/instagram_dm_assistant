import { useEffect, useState } from 'react';

import { HubPage } from '../components/shell/HubPage';
import { Callout, Card, CardBody, CardHeader } from '../components/ui';
import { EmptyState, LoadingState } from '../components/data';
import { ChannelAccountCard } from '../components/channels/ChannelAccountCard';
import { ChannelAccountCreateForm } from '../components/channels/ChannelAccountCreateForm';
import { ChannelCredentialsDialog } from '../components/channels/ChannelCredentialsDialog';
import { useAuth } from '../contexts/AuthContext';
import { useShop } from '../contexts/ShopContext';
import { apiClient } from '../services/apiClient';
import type { ChannelAccount, ChannelProvider } from '../types/channel';

export function ChannelAccountsPage() {
  const { user } = useAuth();
  const { selectedShopId, selectedShop } = useShop();
  const [accounts, setAccounts] = useState<ChannelAccount[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [credentialsAccount, setCredentialsAccount] = useState<ChannelAccount | null>(null);

  const canManageCredentials = user?.role === 'owner' || user?.role === 'admin';

  async function loadAccounts() {
    if (!selectedShopId) {
      setAccounts([]);
      return;
    }
    setIsLoading(true);
    try {
      setAccounts(await apiClient.listChannelAccounts(selectedShopId));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load channel accounts');
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadAccounts();
  }, [selectedShopId]);

  async function handleCreate(payload: {
    provider: ChannelProvider;
    displayName: string;
    externalAccountId: string;
    phoneNumberId: string;
    botUsername: string;
    botId: string;
    pageId: string;
    webhookVerifyToken: string;
    webhookSecret: string;
    accessToken: string;
    botToken: string;
    defaultLanguageCode: string;
    templateNamespace: string;
  }) {
    if (!selectedShopId) {
      return;
    }
    setError(null);
    try {
      const settings: Record<string, unknown> = {};
      if (payload.provider === 'instagram' && payload.pageId) {
        settings.page_id = payload.pageId;
      }
      if (payload.provider === 'telegram') {
        settings.allowed_updates_json = ['message', 'callback_query'];
        settings.use_local_bot_api = false;
      }
      if (payload.provider === 'whatsapp') {
        settings.default_language_code = payload.defaultLanguageCode;
        if (payload.templateNamespace) {
          settings.message_template_namespace = payload.templateNamespace;
        }
      }

      const account = await apiClient.createChannelAccount(selectedShopId, {
        provider: payload.provider,
        display_name: payload.displayName,
        external_account_id: payload.externalAccountId || undefined,
        phone_number_id: payload.phoneNumberId || undefined,
        bot_username: payload.botUsername || undefined,
        bot_id: payload.botId || undefined,
        webhook_verify_token: payload.webhookVerifyToken || undefined,
        settings,
      });

      await apiClient.updateChannelCredentials(selectedShopId, account.id, {
        webhook_secret: payload.webhookSecret || undefined,
        access_token: payload.accessToken || undefined,
        bot_token: payload.botToken || undefined,
        webhook_verify_token: payload.webhookVerifyToken || undefined,
      });

      await loadAccounts();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create channel account');
      throw err;
    }
  }

  return (
    <HubPage
      eyebrow="Multi-channel"
      title="Channel Accounts"
      description={`Connect messaging channels to the same normalized order pipeline for ${selectedShop?.name ?? 'your shop'}.`}
    >
      <Callout title="Credential security">
        <ul className="list-disc space-y-1 pl-4">
          <li>Credentials are encrypted at rest in the database.</li>
          <li>Tokens are write-only in this admin UI and are never shown again after save.</li>
          <li>Only shop owners and admins can create or replace channel credentials.</li>
        </ul>
      </Callout>

      {error ? (
        <Card>
          <CardBody>
            <p className="text-sm text-danger">{error}</p>
          </CardBody>
        </Card>
      ) : null}

      {!selectedShopId ? (
        <Card>
          <CardBody>
            <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
          </CardBody>
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader
              title="Add channel account"
              description={
                canManageCredentials
                  ? 'Create a new channel connection and save encrypted credentials.'
                  : 'View-only access. Contact an owner or admin to add channels.'
              }
            />
            <CardBody>
              {canManageCredentials ? (
                <ChannelAccountCreateForm onSubmit={handleCreate} />
              ) : (
                <EmptyState
                  title="Credential changes restricted"
                  description="Operators can view channel status below but cannot add or edit credentials."
                />
              )}
            </CardBody>
          </Card>

          <div className="flex flex-col gap-4">
            <div>
              <h2 className="text-lg font-semibold text-fg">Connected channels</h2>
              <p className="text-sm text-muted">Status, webhook readiness, and setup progress per account.</p>
            </div>

            {isLoading ? (
              <Card>
                <CardBody>
                  <LoadingState label="Loading channel accounts…" />
                </CardBody>
              </Card>
            ) : accounts.length === 0 ? (
              <Card>
                <CardBody>
                  <EmptyState title="No channel accounts connected yet" />
                </CardBody>
              </Card>
            ) : (
              accounts.map((account) => (
                <ChannelAccountCard
                  key={account.id}
                  account={account}
                  shopId={selectedShopId}
                  canManage={canManageCredentials}
                  onRefresh={() => void loadAccounts()}
                  onReplaceCredentials={setCredentialsAccount}
                />
              ))
            )}
          </div>

          <ChannelCredentialsDialog
            open={credentialsAccount !== null}
            account={credentialsAccount}
            shopId={selectedShopId}
            canManage={canManageCredentials}
            onClose={() => setCredentialsAccount(null)}
            onSaved={() => void loadAccounts()}
          />
        </>
      )}
    </HubPage>
  );
}
