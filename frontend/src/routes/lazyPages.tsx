import { lazy, type ComponentType } from 'react';

function lazyPage<T extends ComponentType<unknown>>(
  loader: () => Promise<Record<string, T>>,
  exportName: string,
) {
  return lazy(() => loader().then((module) => ({ default: module[exportName] as T })));
}

// Command-center pages
export const OverviewPage = lazyPage(() => import('../pages/OverviewPage'), 'OverviewPage');
export const InboxPage = lazyPage(() => import('../pages/InboxPage'), 'InboxPage');
export const ConversationIntelligencePage = lazyPage(
  () => import('../pages/ConversationIntelligencePage'),
  'ConversationIntelligencePage',
);
export const HandoffQueuePage = lazyPage(() => import('../pages/HandoffQueuePage'), 'HandoffQueuePage');
export const OrdersHubPage = lazyPage(() => import('../pages/OrdersHubPage'), 'OrdersHubPage');
export const AnalyticsOverviewPage = lazyPage(
  () => import('../pages/AnalyticsOverviewPage'),
  'AnalyticsOverviewPage',
);
export const ChannelAnalyticsPage = lazyPage(
  () => import('../pages/ChannelAnalyticsPage'),
  'ChannelAnalyticsPage',
);
export const RolloutPage = lazyPage(() => import('../pages/RolloutPage'), 'RolloutPage');

export const AIControlOverviewPage = lazyPage(
  () => import('../pages/AIControlPages'),
  'AIControlOverviewPage',
);
export const LLMLogsPage = lazyPage(() => import('../pages/AIControlPages'), 'LLMLogsPage');
export const AIFallbacksPage = lazyPage(() => import('../pages/AIControlPages'), 'AIFallbacksPage');
export const AISafetyPage = lazyPage(() => import('../pages/AIControlPages'), 'AISafetyPage');

// Existing pages
export const CatalogCopilotPage = lazyPage(() => import('../pages/CatalogCopilotPage'), 'CatalogCopilotPage');
export const ChannelAccountsPage = lazyPage(() => import('../pages/ChannelAccountsPage'), 'ChannelAccountsPage');
export const OrderDetailPage = lazyPage(() => import('../pages/OrderDetailPage'), 'OrderDetailPage');
export const DMSimulatorPage = lazyPage(() => import('../pages/DMSimulatorPage'), 'DMSimulatorPage');
export const FashionDictionaryPage = lazyPage(
  () => import('../pages/FashionDictionaryPage'),
  'FashionDictionaryPage',
);
export const FailedJobsPage = lazyPage(() => import('../pages/FailedJobsPage'), 'FailedJobsPage');
export const InstagramProductMappingPage = lazyPage(
  () => import('../pages/InstagramProductMappingPage'),
  'InstagramProductMappingPage',
);
export const LoginPage = lazyPage(() => import('../pages/LoginPage'), 'LoginPage');
export const ProductDetailPage = lazyPage(() => import('../pages/ProductDetailPage'), 'ProductDetailPage');
export const ProductsPage = lazyPage(() => import('../pages/ProductsPage'), 'ProductsPage');
export const PostRevenueAnalyticsPage = lazyPage(
  () => import('../pages/PostRevenueAnalyticsPage'),
  'PostRevenueAnalyticsPage',
);
export const RecoveryRulesPage = lazyPage(() => import('../pages/RecoveryRulesPage'), 'RecoveryRulesPage');
export const RiskSettingsPage = lazyPage(() => import('../pages/RiskSettingsPage'), 'RiskSettingsPage');
export const SystemHealthPage = lazyPage(() => import('../pages/SystemHealthPage'), 'SystemHealthPage');
export const UpsellRulesPage = lazyPage(() => import('../pages/UpsellRulesPage'), 'UpsellRulesPage');
export const SemanticSearchPage = lazyPage(() => import('../pages/SemanticSearchPage'), 'SemanticSearchPage');
export const SettingsPage = lazyPage(() => import('../pages/SettingsPage'), 'SettingsPage');
export const TriggerRulesPage = lazyPage(() => import('../pages/TriggerRulesPage'), 'TriggerRulesPage');
export const UnavailableDemandPage = lazyPage(
  () => import('../pages/UnavailableDemandPage'),
  'UnavailableDemandPage',
);
export const VariantResolverPage = lazyPage(() => import('../pages/VariantResolverPage'), 'VariantResolverPage');
export const ShopsPage = lazyPage(() => import('../pages/ShopsPage'), 'ShopsPage');

export const AdminAITasksPage = lazyPage(() => import('../pages/SocialAdminPages'), 'AdminAITasksPage');
export const AutomationRulesPage = lazyPage(() => import('../pages/SocialAdminPages'), 'AutomationRulesPage');
export const OperatorCorrectionsPage = lazyPage(
  () => import('../pages/SocialAdminPages'),
  'OperatorCorrectionsPage',
);
export const ScenarioCoveragePage = lazyPage(
  () => import('../pages/SocialAdminPages'),
  'ScenarioCoveragePage',
);
export const ScenarioSimulatorPage = lazyPage(
  () => import('../pages/SocialAdminPages'),
  'ScenarioSimulatorPage',
);
