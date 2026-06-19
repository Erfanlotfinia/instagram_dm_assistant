import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { HubPage } from '../components/shell/HubPage';
import { Badge, Button, Card, CardBody, CardHeader, Field, Input, Select } from '../components/ui';
import { DataTable, LoadingState } from '../components/data';
import type { Column } from '../components/data';
import { useShop } from '../contexts/ShopContext';
import { useToast } from '../contexts/ToastContext';
import { queryKeys } from '../lib/queryClient';
import { apiClient } from '../services/apiClient';
import type { HandoffMode, ShopAgentSettings } from '../types/shop';

const profileSchema = z.object({
  name: z.string().min(1, 'Shop name is required'),
  default_currency: z.string().length(3, 'Use a 3-letter currency code'),
});

const agentSettingsSchema = z.object({
  auto_reply_enabled: z.boolean(),
  intent_confidence_threshold: z.number().min(0).max(1),
  slots_confidence_threshold: z.number().min(0).max(1),
  handoff_mode: z.enum(['automatic', 'manual_only']),
  default_language: z.string().min(2),
  low_stock_threshold: z.number().min(0),
});

type ProfileFormValues = z.infer<typeof profileSchema>;
type AgentSettingsFormValues = z.infer<typeof agentSettingsSchema>;

interface InstagramAccountRow {
  id: string;
  username: string;
  status: string;
  webhook_enabled: boolean;
  token_expires_at: string | null;
}

export function SettingsPage() {
  const { selectedShopId } = useShop();
  const { showToast } = useToast();
  const queryClient = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: queryKeys.shopSettings(selectedShopId),
    queryFn: () => apiClient.getShopSettings(selectedShopId),
    enabled: Boolean(selectedShopId),
  });

  const settings = settingsQuery.data;

  const profileForm = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    values: {
      name: settings?.shop.name ?? '',
      default_currency: settings?.shop.default_currency ?? 'USD',
    },
  });

  const agentForm = useForm<AgentSettingsFormValues>({
    resolver: zodResolver(agentSettingsSchema),
    values: {
      auto_reply_enabled: settings?.shop.agent_settings?.auto_reply_enabled ?? true,
      intent_confidence_threshold: settings?.shop.agent_settings?.intent_confidence_threshold ?? 0.65,
      slots_confidence_threshold: settings?.shop.agent_settings?.slots_confidence_threshold ?? 0.6,
      handoff_mode: (settings?.shop.agent_settings?.handoff_mode ?? 'automatic') as HandoffMode,
      default_language: settings?.shop.agent_settings?.default_language ?? 'fa',
      low_stock_threshold: settings?.shop.agent_settings?.low_stock_threshold ?? 5,
    },
  });

  const updateProfileMutation = useMutation({
    mutationFn: (values: ProfileFormValues) => apiClient.updateShop(selectedShopId, values),
    onSuccess: () => {
      showToast('Shop profile updated.', 'success');
      queryClient.invalidateQueries({ queryKey: queryKeys.shopSettings(selectedShopId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.shops });
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Update failed', 'error'),
  });

  const updateAgentMutation = useMutation({
    mutationFn: (values: Partial<ShopAgentSettings>) => apiClient.updateAgentSettings(selectedShopId, values),
    onSuccess: () => {
      showToast('Agent settings saved.', 'success');
      queryClient.invalidateQueries({ queryKey: queryKeys.shopSettings(selectedShopId) });
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Save failed', 'error'),
  });

  const accountColumns: Column<InstagramAccountRow>[] = [
    { key: 'username', header: 'Username', render: (row) => `@${row.username}` },
    { key: 'status', header: 'Status', render: (row) => <Badge tone="neutral">{row.status}</Badge> },
    {
      key: 'webhook',
      header: 'Webhook',
      render: (row) => <Badge tone={row.webhook_enabled ? 'success' : 'warning'}>{row.webhook_enabled ? 'enabled' : 'disabled'}</Badge>,
    },
    {
      key: 'expires',
      header: 'Token expires',
      align: 'right',
      render: (row) => (row.token_expires_at ? new Date(row.token_expires_at).toLocaleString() : '—'),
    },
  ];

  return (
    <HubPage
      eyebrow="System"
      title="Settings"
      description="Manage shop profile, Instagram connectivity, and agent behavior."
    >
      {settingsQuery.isLoading ? (
        <Card>
          <CardBody>
            <LoadingState label="Loading settings…" />
          </CardBody>
        </Card>
      ) : null}

      {settingsQuery.error ? (
        <Card>
          <CardBody>
            <p className="text-sm text-danger">
              {settingsQuery.error instanceof Error ? settingsQuery.error.message : 'Failed to load settings'}
            </p>
          </CardBody>
        </Card>
      ) : null}

      {settings ? (
        <>
          <Card>
            <CardHeader title="Shop profile" />
            <CardBody>
              <form
                className="flex flex-wrap items-end gap-3"
                onSubmit={profileForm.handleSubmit((values) => updateProfileMutation.mutate(values))}
              >
                <Field label="Shop name">
                  <Input {...profileForm.register('name')} />
                </Field>
                <Field label="Default currency">
                  <Input maxLength={3} {...profileForm.register('default_currency')} />
                </Field>
                <Button type="submit" disabled={updateProfileMutation.isPending}>
                  Save profile
                </Button>
              </form>
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Instagram & webhook status"
              description={`Webhook: ${settings.webhook_active ? 'active' : 'inactive'}`}
            />
            <DataTable
              columns={accountColumns}
              rows={settings.instagram_accounts}
              rowKey={(row) => row.id}
              emptyTitle="No Instagram accounts connected"
            />
          </Card>

          <Card>
            <CardHeader title="Agent settings" />
            <CardBody>
              <form
                className="flex flex-col gap-4"
                onSubmit={agentForm.handleSubmit((values) => updateAgentMutation.mutate(values))}
              >
                <label className="flex items-center gap-2 text-sm text-fg">
                  <input type="checkbox" className="rounded border-border" {...agentForm.register('auto_reply_enabled')} />
                  Enable auto reply
                </label>

                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  <Field label="Intent confidence threshold">
                    <Input type="number" step="0.01" min="0" max="1" {...agentForm.register('intent_confidence_threshold', { valueAsNumber: true })} />
                  </Field>
                  <Field label="Slots confidence threshold">
                    <Input type="number" step="0.01" min="0" max="1" {...agentForm.register('slots_confidence_threshold', { valueAsNumber: true })} />
                  </Field>
                  <Field label="Handoff mode">
                    <Select {...agentForm.register('handoff_mode')}>
                      <option value="automatic">Automatic</option>
                      <option value="manual_only">Manual only</option>
                    </Select>
                  </Field>
                  <Field label="Default language">
                    <Select {...agentForm.register('default_language')}>
                      <option value="fa">Persian (fa)</option>
                      <option value="en">English (en)</option>
                    </Select>
                  </Field>
                  <Field label="Low stock threshold">
                    <Input type="number" min="0" {...agentForm.register('low_stock_threshold', { valueAsNumber: true })} />
                  </Field>
                </div>

                <Button type="submit" disabled={updateAgentMutation.isPending}>
                  Save agent settings
                </Button>
              </form>
            </CardBody>
          </Card>
        </>
      ) : null}
    </HubPage>
  );
}
