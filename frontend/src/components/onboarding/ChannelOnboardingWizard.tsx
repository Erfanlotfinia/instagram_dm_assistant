import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { Badge, Button, Card, CardBody, CardHeader } from '../ui';
import { ErrorState, EmptyState, LoadingState } from '../data';
import { ChannelTroubleshootingChecklist } from './ChannelTroubleshootingChecklist';
import { useToast } from '../../contexts/ToastContext';
import { apiClient } from '../../services/apiClient';
import { evaluateChannelOnboarding } from '../../lib/readiness';
import { providerLabel } from '../../lib/channelAccounts';
import type { ChannelAccount, ChannelProvider } from '../../types/channel';
import type { ChannelOnboardingState } from '../../types/sprint2Readiness';

const ALL_PROVIDERS: ChannelProvider[] = ['instagram', 'telegram', 'whatsapp', 'bale', 'rubika'];

const PROVIDER_HINTS: Record<ChannelProvider, string> = {
  instagram: 'Instagram Business messaging via Meta Graph API.',
  telegram: 'Bot API or Business connection with webhook verification.',
  whatsapp: 'WhatsApp Cloud API (phone number ID, verify token, templates).',
  bale: 'Bale bot endpoint with token and webhook limits.',
  rubika: 'HTTPS endpoint mode (receiveUpdate / receiveInlineMessage).',
};

const MANUAL_SETUP_PROVIDERS: ReadonlySet<ChannelProvider> = new Set(['whatsapp', 'bale', 'rubika']);

export interface ChannelOnboardingWizardProps {
  shopId: string;
  /** Optional focus provider/card. */
  provider?: ChannelProvider;
  /** Optional specific channel account id to highlight. */
  channelAccountId?: string;
}

function statusTone(state: ChannelOnboardingState): 'success' | 'warning' | 'danger' | 'neutral' {
  if (state.ready) return 'success';
  if (state.steps.some((s) => !s.passed && s.severity === 'required')) return 'danger';
  if (state.steps.some((s) => !s.passed)) return 'warning';
  return 'neutral';
}

function firstBlockingStep(state: ChannelOnboardingState) {
  return state.steps.find((s) => !s.passed && s.severity === 'required') ?? null;
}

function ProviderCard({
  provider,
  account,
  shopId,
  onConnect,
  isConnecting,
}: {
  provider: ChannelProvider;
  account: ChannelAccount | null;
  shopId: string;
  onConnect: () => void;
  isConnecting: boolean;
}) {
  const state = useMemo<ChannelOnboardingState>(
    () => (account ? evaluateChannelOnboarding({ channel: account }) : {
      provider,
      status: 'missing',
      score: 0,
      ready: false,
      steps: [],
      blockingReasons: ['No channel account configured.'],
    }),
    [account, provider],
  );

  const blockingStep = firstBlockingStep(state);
  const isManual = MANUAL_SETUP_PROVIDERS.has(provider);

  const primaryAction = account
    ? state.ready
      ? { label: 'Manage channel', to: '/system/channels' }
      : { label: blockingStep?.actionLabel ?? 'Open channel settings', to: blockingStep?.actionTo ?? '/system/channels' }
    : provider === 'instagram'
      ? { label: 'Connect Instagram', to: '/system/channels/instagram/connect' }
      : provider === 'telegram'
        ? { label: 'Connect Telegram', to: '/system/channels' }
        : null;

  return (
    <Card>
      <CardHeader
        title={providerLabel(provider)}
        description={PROVIDER_HINTS[provider]}
        actions={
          account ? (
            <Badge tone={statusTone(state)}>{state.score}%</Badge>
          ) : (
            <Badge tone="neutral">Not connected</Badge>
          )
        }
      />
      <CardBody className="flex flex-col gap-3">
        {account ? (
          <>
            <div className="text-sm text-muted">
              <span className="font-medium text-fg">{account.display_name || providerLabel(provider)}</span>
              {' · '}
              <span>{account.status.replace(/_/g, ' ')}</span>
            </div>
            {blockingStep ? (
              <p className="text-xs text-muted">
                <span className="font-medium text-fg">Next step: </span>
                {blockingStep.label}. {blockingStep.detail ?? ''}
              </p>
            ) : (
              <p className="text-xs text-muted">All required onboarding steps are passing.</p>
            )}
            {state.blockingReasons.length > 0 ? (
              <ul className="list-inside list-disc space-y-0.5 text-xs text-muted">
                {state.blockingReasons.slice(0, 3).map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            ) : null}
          </>
        ) : isManual ? (
          <p className="text-xs text-muted">
            Full connect flow is coming soon. Manual setup is required — add the channel
            account on the Channels page, then return here to track readiness.
          </p>
        ) : (
          <p className="text-xs text-muted">No channel account configured yet.</p>
        )}

        <div className="flex flex-wrap gap-2">
          {primaryAction ? (
            provider === 'instagram' && !account ? (
              <Button type="button" size="sm" onClick={onConnect} disabled={isConnecting}>
                {isConnecting ? 'Redirecting…' : primaryAction.label}
              </Button>
            ) : (
              <Link
                className="inline-flex h-9 items-center rounded-lg border border-border bg-surface px-3 text-sm font-medium text-fg hover:bg-surface-sunken"
                to={primaryAction.to}
              >
                {primaryAction.label} →
              </Link>
            )
          ) : null}
          {account ? (
            <Link
              className="text-xs text-accent hover:underline"
              to="/system/channels"
            >
              Open channels →
            </Link>
          ) : null}
        </div>

        {account ? <ChannelTroubleshootingChecklist state={state} /> : null}
      </CardBody>
    </Card>
  );
}

/**
 * Channel onboarding wizard. Renders one card per supported provider with
 * connection status, readiness score, current step, blocking reason, and a
 * primary action. Instagram uses the existing OAuth connect flow; Telegram
 * links to the existing connect flow; WhatsApp/Bale/Rubika show "manual
 * setup required" but still render a troubleshooting checklist when an
 * account exists. Does not fake working integrations.
 */
export function ChannelOnboardingWizard({ shopId, provider, channelAccountId }: ChannelOnboardingWizardProps) {
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const [connectingProvider, setConnectingProvider] = useState<ChannelProvider | null>(null);

  const channelsQuery = useQuery({
    queryKey: ['channel-accounts', shopId],
    queryFn: () => apiClient.listChannelAccounts(shopId),
    enabled: Boolean(shopId),
  });

  const instagramConnectMutation = useMutation({
    mutationFn: () => apiClient.startInstagramConnect(shopId),
    onSuccess: (response) => {
      window.location.assign(response.authorization_url);
    },
    onError: (error: Error) => {
      showToast(error.message, 'error');
      setConnectingProvider(null);
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['channel-accounts', shopId] });
    },
  });

  const channels = channelsQuery.data ?? [];
  const accountFor = (p: ChannelProvider): ChannelAccount | null => {
    const matches = channels.filter((c) => c.provider === p);
    if (channelAccountId) {
      const focused = matches.find((c) => c.id === channelAccountId);
      if (focused) return focused;
    }
    // Prefer the healthiest account for this provider.
    const preferred =
      matches.find((c) => c.status === 'connected') ??
      matches.find((c) => c.status === 'webhook_configured') ??
      matches[0] ??
      null;
    return preferred;
  };

  const orderedProviders = useMemo(() => {
    if (!provider) return ALL_PROVIDERS;
    return [provider, ...ALL_PROVIDERS.filter((p) => p !== provider)];
  }, [provider]);

  if (!shopId) {
    return (
      <Card>
        <CardBody>
          <EmptyState title="Select a shop" description="Use the shop switcher in the top bar." />
        </CardBody>
      </Card>
    );
  }

  if (channelsQuery.isLoading) {
    return (
      <Card>
        <CardBody>
          <LoadingState label="Loading channel accounts…" />
        </CardBody>
      </Card>
    );
  }

  if (channelsQuery.isError) {
    return (
      <Card>
        <CardBody>
          <ErrorState
            message={channelsQuery.error instanceof Error ? channelsQuery.error.message : 'Failed to load channel accounts'}
          />
        </CardBody>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {orderedProviders.map((p) => (
        <ProviderCard
          key={p}
          provider={p}
          account={accountFor(p)}
          shopId={shopId}
          isConnecting={connectingProvider === 'instagram' && instagramConnectMutation.isPending}
          onConnect={() => {
            setConnectingProvider('instagram');
            instagramConnectMutation.mutate();
          }}
        />
      ))}
    </div>
  );
}
