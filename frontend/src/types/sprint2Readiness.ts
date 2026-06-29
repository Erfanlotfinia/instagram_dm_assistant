/**
 * Sprint 2 — Onboarding & Readiness
 *
 * Frontend-only types. These derive purely from existing backend responses
 * (ChannelAccount, Product, PilotReadinessResponse, AgentRiskSettings,
 * SimulatorRunSummary, FailedJobListResponse) — no new backend contracts.
 *
 * Sprint 3 types live in `sprint3Automation.ts` and are imported where useful
 * rather than redefined here.
 */

export type ChannelOnboardingStepKey =
  | 'account_created'
  | 'credentials_added'
  | 'credentials_validated'
  | 'webhook_configured'
  | 'webhook_tested'
  | 'message_window_ready'
  | 'provider_capabilities_detected'
  | 'connection_healthy';

export type OnboardingSeverity = 'required' | 'recommended';

export interface ChannelOnboardingStep {
  key: ChannelOnboardingStepKey;
  label: string;
  description: string;
  passed: boolean;
  severity: OnboardingSeverity;
  detail?: string | null;
  actionLabel?: string;
  actionTo?: string;
}

export interface ChannelOnboardingState {
  provider: string;
  channelAccountId?: string;
  displayName?: string;
  status: string;
  score: number;
  ready: boolean;
  steps: ChannelOnboardingStep[];
  blockingReasons: string[];
}

export type ShopReadinessArea =
  | 'channel'
  | 'catalog'
  | 'automation'
  | 'policy'
  | 'regression'
  | 'operations';

export type ReadinessSeverity = 'blocker' | 'warning' | 'info';

export interface ShopReadinessCheck {
  key: string;
  area: ShopReadinessArea;
  label: string;
  passed: boolean;
  severity: ReadinessSeverity;
  detail?: string | null;
  actionTo?: string;
}

export interface ShopReadinessScore {
  score: number;
  readyForPilot: boolean;
  readyForAutomation: boolean;
  checks: ShopReadinessCheck[];
  blockingReasons: string[];
  warnings: string[];
}

export interface CatalogCompletenessScore {
  score: number;
  productsTotal: number;
  productsActive: number;
  productsMissingImage?: number;
  productsMissingPrice?: number;
  productsMissingVariants?: number;
  variantsChecked?: number;
  variantsUnknown?: boolean;
  attributesConfigured: number;
  aliasesConfigured: number;
  mappingsConfigured: number;
  blockingReasons: string[];
  warnings: string[];
}

export interface ChannelTroubleshootingItem {
  key: string;
  title: string;
  passed: boolean;
  severity: ReadinessSeverity;
  detail?: string | null;
  fixLabel?: string;
  fixTo?: string;
}

export interface ProductColorValidationResult {
  raw: string;
  normalized?: string;
  valid: boolean;
  reason?: string;
}
