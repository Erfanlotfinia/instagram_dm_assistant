import { apiClient } from '../services/apiClient';
import type { ChannelAccount, WebhookTestResponse } from '../types/channel';
import type { Product } from '../types/product';
import type { AgentRiskSettings } from '../types/conversation';
import type { PilotReadinessResponse, PilotSettings } from '../types/pilot';
import type { SimulatorRunSummary } from '../types/trust';
import type {
  ChannelOnboardingState,
  ChannelOnboardingStep,
  ChannelOnboardingStepKey,
  CatalogCompletenessScore,
  ShopReadinessArea,
  ShopReadinessCheck,
  ShopReadinessScore,
  ProductColorValidationResult,
} from '../types/sprint2Readiness';
import {
  getCapabilityLabels,
  getPrimaryTokenConfigured,
  getWebhookStatusLabel,
} from './channelAccounts';
import { evaluateRolloutGate } from './rolloutGate';
import { validateProductColor } from './productColors';

// Re-export so callers can import readiness and color validation from one place.
export { validateProductColor } from './productColors';
export type { ProductColorValidationResult } from '../types/sprint2Readiness';

/* ───────────────────────────── Channel onboarding ───────────────────────────── */

export interface ChannelOnboardingInput {
  channel: ChannelAccount;
  /** Optional provider-specific readiness result (e.g. InstagramReadiness). */
  providerReadiness?: Record<string, unknown> | null;
  /** Optional webhook test result; when absent, the webhook_tested step is "unknown". */
  webhookTest?: WebhookTestResponse | null;
}

const STEP_META: Record<
  ChannelOnboardingStepKey,
  { label: string; description: string; severity: 'required' | 'recommended' }
> = {
  account_created: {
    label: 'Channel account created',
    description: 'A channel account record exists for this provider.',
    severity: 'required',
  },
  credentials_added: {
    label: 'Credentials added',
    description: 'Primary token and required identifiers are configured.',
    severity: 'required',
  },
  credentials_validated: {
    label: 'Credentials validated',
    description: 'Provider accepted the credentials on the last validation.',
    severity: 'required',
  },
  webhook_configured: {
    label: 'Webhook configured',
    description: 'Webhook URL and verification tokens are set.',
    severity: 'required',
  },
  webhook_tested: {
    label: 'Webhook tested',
    description: 'A webhook test request succeeded.',
    severity: 'recommended',
  },
  message_window_ready: {
    label: 'Messaging window ready',
    description: 'Provider messaging window or service window is configured.',
    severity: 'recommended',
  },
  provider_capabilities_detected: {
    label: 'Provider capabilities detected',
    description: 'At least one provider capability flag is set to true.',
    severity: 'recommended',
  },
  connection_healthy: {
    label: 'Connection healthy',
    description: 'Channel is connected or webhook-configured with no last error.',
    severity: 'required',
  },
};

function step(
  key: ChannelOnboardingStepKey,
  passed: boolean,
  detail: string | null,
  actionLabel?: string,
  actionTo?: string,
): ChannelOnboardingStep {
  const meta = STEP_META[key];
  return {
    key,
    label: meta.label,
    description: meta.description,
    passed,
    severity: meta.severity,
    detail,
    actionLabel,
    actionTo,
  };
}

function channelActionTarget(channel: ChannelAccount): string {
  if (channel.provider === 'instagram') return '/system/channels/instagram/connect';
  return '/system/channels';
}

/**
 * Evaluate channel onboarding for a single channel account.
 * Pure function — no I/O. Caller passes the channel account plus optional
 * provider readiness / webhook test results.
 */
export function evaluateChannelOnboarding(input: ChannelOnboardingInput): ChannelOnboardingState {
  const { channel, webhookTest } = input;
  const capabilities = getCapabilityLabels(channel);
  const tokenConfigured = getPrimaryTokenConfigured(channel);
  const webhookStatusLabel = getWebhookStatusLabel(channel);
  const actionTarget = channelActionTarget(channel);

  const validated =
    (channel.status === 'connected' || channel.status === 'webhook_configured') ||
    (Boolean(channel.last_validation_at) && !channel.last_error);

  const webhookConfigured =
    channel.status === 'webhook_configured' ||
    Boolean(channel.webhook_url) ||
    (channel.webhook_secret_configured && Boolean(channel.webhook_verify_token_configured));

  const webhookTested = webhookTest == null ? false : webhookTest.status === 'ok' || webhookTest.status === 'success';

  const healthy =
    (channel.status === 'connected' || channel.status === 'webhook_configured') && !channel.last_error;

  // message_window_ready: only meaningful for WhatsApp (24h window). We treat it
  // as passed for other providers unless capabilities explicitly say otherwise.
  const messageWindowReady =
    channel.provider === 'whatsapp'
      ? Boolean(channel.capabilities_json?.supports_customer_service_window)
      : true;

  const steps: ChannelOnboardingStep[] = [
    step('account_created', true, null),
    step(
      'credentials_added',
      tokenConfigured,
      tokenConfigured ? null : 'Add the provider credentials for this channel.',
      'Configure credentials',
      actionTarget,
    ),
    step(
      'credentials_validated',
      validated,
      validated ? null : 'Validate the credentials with the provider.',
      'Validate credentials',
      actionTarget,
    ),
    step(
      'webhook_configured',
      webhookConfigured,
      webhookConfigured ? null : `Webhook status: ${webhookStatusLabel}.`,
      'Set up webhook',
      actionTarget,
    ),
    step(
      'webhook_tested',
      webhookTested,
      webhookTest == null
        ? 'Webhook has not been tested yet.'
        : webhookTested
          ? null
          : 'Last webhook test did not succeed.',
      'Test webhook',
      actionTarget,
    ),
    step('message_window_ready', messageWindowReady, messageWindowReady ? null : 'Configure the messaging window.'),
    step(
      'provider_capabilities_detected',
      capabilities.length > 0,
      capabilities.length > 0 ? null : 'No provider capabilities detected yet.',
      'Open channel settings',
      actionTarget,
    ),
    step(
      'connection_healthy',
      healthy,
      healthy ? null : channel.last_error ?? `Channel status: ${channel.status}.`,
      'Reconnect channel',
      actionTarget,
    ),
  ];

  const requiredSteps = steps.filter((s) => s.severity === 'required');
  const passedSteps = steps.filter((s) => s.passed).length;
  const ready = requiredSteps.every((s) => s.passed);
  const score = steps.length > 0 ? Math.round((passedSteps / steps.length) * 100) : 0;
  const blockingReasons = steps
    .filter((s) => !s.passed && s.severity === 'required')
    .map((s) => s.detail ?? s.label);

  return {
    provider: channel.provider,
    channelAccountId: channel.id,
    displayName: channel.display_name,
    status: channel.status,
    score,
    ready,
    steps,
    blockingReasons,
  };
}

/* ───────────────────────────── Catalog completeness ───────────────────────────── */

export interface CatalogCompletenessInput {
  products: Product[];
  /** Attribute aliases (color/size/etc.) configured for the shop. */
  attributeAliases?: unknown[] | null;
  /** Instagram product mappings configured for the shop. */
  productMappings?: unknown[] | null;
  /** Optional variant probe result. When absent, variants are "unknown". */
  variantProbe?: { checked: number; missingVariants: number } | null;
}

/**
 * Compute catalog completeness purely from frontend-available data.
 * Variant counts are treated as "unknown" unless `variantProbe` is supplied
 * by the optional user-triggered "Analyze variants" action.
 */
export function evaluateCatalogCompleteness(input: CatalogCompletenessInput): CatalogCompletenessScore {
  const { products, attributeAliases, productMappings, variantProbe } = input;
  const productsTotal = products.length;
  const productsActive = products.filter((p) => p.status === 'active').length;
  const productsMissingPrice = products.filter((p) => !p.base_price || p.base_price.trim() === '').length;
  const productsMissingImage = products.filter((p) => !p.main_image_url).length;

  const aliasesConfigured = attributeAliases?.length ?? 0;
  const mappingsConfigured = productMappings?.length ?? 0;

  const blockingReasons: string[] = [];
  const warnings: string[] = [];

  if (productsTotal === 0) {
    blockingReasons.push('No products in the catalog. Add products before enabling automation.');
  } else if (productsActive === 0) {
    blockingReasons.push('No active products. Activate at least one product.');
  }

  if (productsMissingPrice > 0) {
    blockingReasons.push(
      `${productsMissingPrice} product(s) missing a base price — order automation depends on price.`,
    );
  }

  const variantsUnknown = variantProbe == null;
  if (variantProbe && variantProbe.missingVariants > 0) {
    warnings.push(
      `${variantProbe.missingVariants} of ${variantProbe.checked} checked product(s) have no variants.`,
    );
  } else if (variantsUnknown && productsActive > 0) {
    warnings.push('Variant completeness is unknown — run "Analyze variants" to verify.');
  }

  if (productsMissingImage > 0) {
    warnings.push(`${productsMissingImage} product(s) missing a main image.`);
  }
  if (aliasesConfigured === 0) {
    warnings.push('No attribute aliases configured — resolver accuracy may suffer.');
  }
  if (mappingsConfigured === 0) {
    warnings.push('No Instagram product mappings configured.');
  }

  // Score: weighted blend of product completeness + alias/mapping presence.
  const activeRatio = productsTotal === 0 ? 0 : productsActive / productsTotal;
  const priceRatio = productsActive === 0 ? 1 : (productsActive - Math.min(productsMissingPrice, productsActive)) / productsActive;
  const imageRatio = productsTotal === 0 ? 1 : (productsTotal - productsMissingImage) / productsTotal;
  const aliasRatio = aliasesConfigured > 0 ? 1 : 0.5;
  const mappingRatio = mappingsConfigured > 0 ? 1 : 0.7;
  const variantRatio = variantsUnknown ? 0.85 : 1;

  const score = Math.round(
    (activeRatio * 0.2 +
      priceRatio * 0.3 +
      imageRatio * 0.1 +
      variantRatio * 0.15 +
      aliasRatio * 0.1 +
      mappingRatio * 0.15) *
      100,
  );

  return {
    score: Math.max(0, Math.min(100, score)),
    productsTotal,
    productsActive,
    productsMissingImage,
    productsMissingPrice,
    productsMissingVariants: variantProbe?.missingVariants,
    variantsChecked: variantProbe?.checked,
    variantsUnknown,
    attributesConfigured: aliasesConfigured,
    aliasesConfigured: aliasesConfigured,
    mappingsConfigured,
    blockingReasons,
    warnings,
  };
}

/**
 * Bounded variant probe — used by the optional "Analyze variants" button in
 * CatalogCompletenessPanel. Does NOT run automatically on page load.
 *
 * Caps the number of products checked (default 50) and the concurrency of
 * parallel `listVariants` calls (default 4) to avoid hammering the API.
 */
export async function probeVariants(
  shopId: string,
  products: Product[],
  options: { maxProducts?: number; concurrency?: number } = {},
): Promise<{ checked: number; missingVariants: number }> {
  const maxProducts = options.maxProducts ?? 50;
  const concurrency = Math.max(1, options.concurrency ?? 4);
  const targets = products.slice(0, maxProducts);

  let missingVariants = 0;
  let checked = 0;

  for (let i = 0; i < targets.length; i += concurrency) {
    const batch = targets.slice(i, i + concurrency);
    const results = await Promise.allSettled(
      batch.map((product) => apiClient.listVariants(shopId, product.id)),
    );
    for (const result of results) {
      checked += 1;
      if (result.status === 'fulfilled') {
        if (result.value.length === 0) missingVariants += 1;
      } else {
        // Treat a failed fetch as "unknown" — counted as missing for warning
        // purposes since we cannot confirm variants exist.
        missingVariants += 1;
      }
    }
  }

  return { checked, missingVariants };
}

/* ───────────────────────────── Shop readiness ───────────────────────────── */

export interface ShopReadinessInput {
  channelStates: ChannelOnboardingState[];
  catalog: CatalogCompletenessScore;
  /** Backend pilot readiness (checklist + warnings). */
  pilotReadiness?: PilotReadinessResponse | null;
  pilotSettings?: PilotSettings | null;
  riskSettings?: AgentRiskSettings | null;
  /** Latest replay run; null when no run exists. */
  latestRun?: SimulatorRunSummary | null;
  /** Number of active failed jobs for the shop. */
  failedJobsCount: number;
}

const CATALOG_AUTOMATION_THRESHOLD = 80;

function areaCheck(
  key: string,
  area: ShopReadinessArea,
  label: string,
  passed: boolean,
  severity: 'blocker' | 'warning' | 'info',
  detail: string | null,
  actionTo?: string,
): ShopReadinessCheck {
  return { key, area, label, passed, severity, detail, actionTo };
}

/**
 * Aggregate shop readiness across all six areas. Pure function — no I/O.
 *
 * `readyForPilot` tolerates warnings (mirrors Sprint 3 rollout gate semantics).
 * `readyForAutomation` requires zero blockers AND channel ready AND catalog
 * score >= 80 AND regression clean.
 */
export function evaluateShopReadiness(input: ShopReadinessInput): ShopReadinessScore {
  const { channelStates, catalog, pilotReadiness, pilotSettings, riskSettings, latestRun, failedJobsCount } = input;

  const checks: ShopReadinessCheck[] = [];

  // 1. Channel — at least one channel fully onboarded.
  const readyChannel = channelStates.find((state) => state.ready);
  const anyConnected = channelStates.length > 0;
  checks.push(
    areaCheck(
      'channel_ready',
      'channel',
      'At least one channel onboarded',
      Boolean(readyChannel),
      'blocker',
      readyChannel
        ? null
        : anyConnected
          ? 'Connect and validate at least one channel.'
          : 'No channel accounts configured.',
      '/system/channels/onboarding',
    ),
  );

  // 2. Catalog — score >= 80 and no blockers.
  const catalogOk = catalog.score >= CATALOG_AUTOMATION_THRESHOLD && catalog.blockingReasons.length === 0;
  checks.push(
    areaCheck(
      'catalog_complete',
      'catalog',
      'Catalog completeness ≥ 80%',
      catalogOk,
      'blocker',
      catalogOk ? null : `Catalog score ${catalog.score}%. ${catalog.blockingReasons[0] ?? ''}`.trim(),
      '/catalog/products',
    ),
  );

  // 3. Automation — risk settings + pilot readiness present.
  const riskOk =
    !!riskSettings &&
    riskSettings.intent_confidence_threshold > 0 &&
    riskSettings.product_confidence_threshold > 0 &&
    riskSettings.variant_confidence_threshold > 0;
  const pilotChecklistOk = pilotReadiness ? pilotReadiness.checklist.every((item) => item.passed) : false;
  const automationOk = riskOk && (pilotReadiness ? pilotChecklistOk : Boolean(pilotSettings));
  checks.push(
    areaCheck(
      'automation_configured',
      'automation',
      'Risk thresholds and automation settings configured',
      automationOk,
      'blocker',
      automationOk ? null : 'Configure risk thresholds and run the pilot readiness checklist.',
      '/automation/risk',
    ),
  );

  // 4. Policy — pilot settings configured.
  const policyOk = !!pilotSettings && (!!pilotSettings.operating_mode || pilotSettings.pilot_enabled);
  checks.push(
    areaCheck(
      'policy_configured',
      'policy',
      'Pilot mode configured',
      policyOk,
      'warning',
      policyOk ? null : 'Set an operating mode in the Pilot Control Center.',
      '/system/rollout',
    ),
  );

  // 5. Regression — latest replay run has zero failures.
  const regressionOk = !latestRun || latestRun.failed_items === 0;
  checks.push(
    areaCheck(
      'regression_clean',
      'regression',
      'Latest replay run has no failures',
      regressionOk,
      'blocker',
      regressionOk ? null : `${latestRun?.failed_items ?? 0} failed scenario(s) in the latest replay run.`,
      '/automation/scenario-simulator',
    ),
  );

  // 6. Operations — no active failed jobs.
  const operationsOk = failedJobsCount === 0;
  checks.push(
    areaCheck(
      'no_failed_jobs',
      'operations',
      'No active failed jobs',
      operationsOk,
      'blocker',
      operationsOk ? null : `${failedJobsCount} failed job(s) need attention.`,
      '/system/jobs',
    ),
  );

  const blockers = checks.filter((c) => !c.passed && c.severity === 'blocker');
  const warningChecks = checks.filter((c) => !c.passed && c.severity === 'warning');

  const blockingReasons = blockers.map((c) => c.detail ?? c.label);
  const warnings = [
    ...warningChecks.map((c) => c.detail ?? c.label),
    ...catalog.warnings,
    ...(pilotReadiness?.warnings ?? []),
  ];

  const passedChecks = checks.filter((c) => c.passed).length;
  const score = checks.length > 0 ? Math.round((passedChecks / checks.length) * 100) : 0;

  const readyForPilot = blockers.length === 0;
  const readyForAutomation =
    blockers.length === 0 &&
    Boolean(readyChannel) &&
    catalog.score >= CATALOG_AUTOMATION_THRESHOLD &&
    regressionOk;

  return {
    score,
    readyForPilot,
    readyForAutomation,
    checks,
    blockingReasons,
    warnings,
  };
}

/**
 * Bridge Sprint 2 readiness into the Sprint 3 rollout gate. Computes the
 * Sprint 3 `RolloutGateState` from the same inputs that feed
 * `evaluateShopReadiness`, so callers can render both views without
 * duplicating data fetching. Pure function — no circular dependency.
 */
export function rolloutGateFromReadinessInput(input: ShopReadinessInput) {
  return evaluateRolloutGate({
    regression: null,
    latestRun: input.latestRun ?? null,
    riskSettings: input.riskSettings ?? null,
    channels: [],
    pilot: input.pilotSettings ?? null,
    failedJobsCount: input.failedJobsCount,
  });
}

/* ───────────────────────────── Color validation re-export ───────────────────────────── */

export function validateCatalogColor(value: unknown): ProductColorValidationResult {
  return validateProductColor(value);
}
