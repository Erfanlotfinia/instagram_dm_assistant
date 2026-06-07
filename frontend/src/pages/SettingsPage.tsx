import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { ShopSelector } from '../components/ShopSelector';
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
    mutationFn: (values: ShopAgentSettings) => apiClient.updateAgentSettings(selectedShopId, values),
    onSuccess: () => {
      showToast('Agent settings saved.', 'success');
      queryClient.invalidateQueries({ queryKey: queryKeys.shopSettings(selectedShopId) });
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Save failed', 'error'),
  });

  return (
    <div className="page-stack page-stack--wide">
      <section className="dashboard-card dashboard-card--wide">
        <p className="dashboard-card__eyebrow">Configuration</p>
        <h1>Settings</h1>
        <p>Manage shop profile, Instagram connectivity, and agent behavior.</p>
        <ShopSelector />
      </section>

      {settingsQuery.isLoading ? <p className="loading-state">Loading settings...</p> : null}
      {settingsQuery.error ? (
        <section className="dashboard-card dashboard-card--wide">
          <p className="form-error">
            {settingsQuery.error instanceof Error ? settingsQuery.error.message : 'Failed to load settings'}
          </p>
        </section>
      ) : null}

      {settings ? (
        <>
          <section className="dashboard-card dashboard-card--wide">
            <h2>Shop profile</h2>
            <form
              className="inline-form"
              onSubmit={profileForm.handleSubmit((values) => updateProfileMutation.mutate(values))}
            >
              <label className="form-field">
                <span>Shop name</span>
                <input {...profileForm.register('name')} />
              </label>
              <label className="form-field">
                <span>Default currency</span>
                <input {...profileForm.register('default_currency')} />
              </label>
              <button className="button button--primary" type="submit" disabled={updateProfileMutation.isPending}>
                Save profile
              </button>
            </form>
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>Instagram & webhook status</h2>
            <p>
              Webhook: <strong>{settings.webhook_active ? 'active' : 'inactive'}</strong>
            </p>
            {settings.instagram_accounts.length === 0 ? (
              <p className="empty-state">No Instagram accounts connected.</p>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Username</th>
                      <th>Status</th>
                      <th>Webhook</th>
                      <th>Token expires</th>
                    </tr>
                  </thead>
                  <tbody>
                    {settings.instagram_accounts.map((account) => (
                      <tr key={account.id}>
                        <td>{account.username}</td>
                        <td>{account.status}</td>
                        <td>{account.webhook_enabled ? 'enabled' : 'disabled'}</td>
                        <td>
                          {account.token_expires_at
                            ? new Date(account.token_expires_at).toLocaleString()
                            : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="dashboard-card dashboard-card--wide">
            <h2>Agent settings</h2>
            <form
              className="inline-form"
              onSubmit={agentForm.handleSubmit((values) => updateAgentMutation.mutate(values))}
            >
              <label className="form-field form-field--checkbox">
                <input type="checkbox" {...agentForm.register('auto_reply_enabled')} />
                <span>Enable auto reply</span>
              </label>

              <div className="filter-grid">
                <label className="form-field">
                  <span>Intent confidence threshold</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    {...agentForm.register('intent_confidence_threshold', { valueAsNumber: true })}
                  />
                </label>
                <label className="form-field">
                  <span>Slots confidence threshold</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    {...agentForm.register('slots_confidence_threshold', { valueAsNumber: true })}
                  />
                </label>
                <label className="form-field">
                  <span>Handoff mode</span>
                  <select {...agentForm.register('handoff_mode')}>
                    <option value="automatic">Automatic</option>
                    <option value="manual_only">Manual only</option>
                  </select>
                </label>
                <label className="form-field">
                  <span>Default language</span>
                  <select {...agentForm.register('default_language')}>
                    <option value="fa">Persian (fa)</option>
                    <option value="en">English (en)</option>
                  </select>
                </label>
                <label className="form-field">
                  <span>Low stock threshold</span>
                  <input
                    type="number"
                    min="0"
                    {...agentForm.register('low_stock_threshold', { valueAsNumber: true })}
                  />
                </label>
              </div>

              <button className="button button--primary" type="submit" disabled={updateAgentMutation.isPending}>
                Save agent settings
              </button>
            </form>
          </section>
        </>
      ) : null}
    </div>
  );
}
