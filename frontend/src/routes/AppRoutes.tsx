import { Navigate, Outlet, Route, Routes } from 'react-router-dom';

import { AppShell } from '../components/shell/AppShell';
import { HubLayout } from '../components/shell/HubLayout';
import { HUBS } from '../components/shell/navConfig';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { LegacyRedirect } from './LegacyRedirect';
import {
  AdminAITasksPage,
  AIFallbacksPage,
  AIControlOverviewPage,
  AISafetyPage,
  AnalyticsOverviewPage,
  AutomationRulesPage,
  CatalogCopilotPage,
  ChannelAccountsPage,
  ChannelAnalyticsPage,
  ConversationIntelligencePage,
  DMSimulatorPage,
  FailedJobsPage,
  FashionDictionaryPage,
  HandoffQueuePage,
  InboxPage,
  InstagramProductMappingPage,
  LLMLogsPage,
  LoginPage,
  OperatorCorrectionsPage,
  OrderDetailPage,
  OrdersHubPage,
  OverviewPage,
  PostRevenueAnalyticsPage,
  ProductDetailPage,
  ProductsPage,
  RecoveryRulesPage,
  RiskSettingsPage,
  RolloutPage,
  ScenarioCoveragePage,
  ScenarioSimulatorPage,
  SemanticSearchPage,
  SettingsPage,
  ShopsPage,
  SystemHealthPage,
  TriggerRulesPage,
  UnavailableDemandPage,
  UpsellRulesPage,
  VariantResolverPage,
} from './lazyPages';
import { RouteSuspense } from './RouteSuspense';

function tabsFor(hubId: string) {
  return HUBS.find((hub) => hub.id === hubId)?.tabs ?? [];
}

export function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <RouteSuspense>
            <LoginPage />
          </RouteSuspense>
        }
      />

      <Route
        element={
          <ProtectedRoute>
            <AppShell>
              <RouteSuspense>
                <Outlet />
              </RouteSuspense>
            </AppShell>
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<OverviewPage />} />

        {/* Inbox */}
        <Route path="/inbox" element={<InboxPage />} />
        <Route path="/inbox/:conversationId" element={<InboxPage />} />
        <Route path="/inbox/:conversationId/intelligence" element={<ConversationIntelligencePage />} />

        {/* Handoffs */}
        <Route path="/handoffs" element={<HandoffQueuePage />} />

        {/* Orders */}
        <Route path="/orders" element={<OrdersHubPage />} />
        <Route path="/orders/:orderId" element={<OrderDetailPage />} />

        {/* Catalog */}
        <Route path="/catalog" element={<HubLayout tabs={tabsFor('catalog')} />}>
          <Route index element={<Navigate to="/catalog/products" replace />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="products/:productId" element={<ProductDetailPage />} />
          <Route path="mapping" element={<InstagramProductMappingPage />} />
          <Route path="copilot" element={<CatalogCopilotPage />} />
          <Route path="resolver" element={<VariantResolverPage />} />
          <Route path="attributes" element={<FashionDictionaryPage />} />
          <Route path="search" element={<SemanticSearchPage />} />
        </Route>

        {/* Automation */}
        <Route path="/automation" element={<HubLayout tabs={tabsFor('automation')} />}>
          <Route index element={<Navigate to="/automation/rules" replace />} />
          <Route path="rules" element={<AutomationRulesPage />} />
          <Route path="coverage" element={<ScenarioCoveragePage />} />
          <Route path="triggers" element={<TriggerRulesPage />} />
          <Route path="recovery" element={<RecoveryRulesPage />} />
          <Route path="upsell" element={<UpsellRulesPage />} />
          <Route path="simulator" element={<DMSimulatorPage />} />
          <Route path="scenario-simulator" element={<ScenarioSimulatorPage />} />
          <Route path="risk" element={<RiskSettingsPage />} />
        </Route>

        {/* AI Control */}
        <Route path="/ai" element={<HubLayout tabs={tabsFor('ai')} />}>
          <Route index element={<Navigate to="/ai/overview" replace />} />
          <Route path="overview" element={<AIControlOverviewPage />} />
          <Route path="logs" element={<LLMLogsPage />} />
          <Route path="fallbacks" element={<AIFallbacksPage />} />
          <Route path="safety" element={<AISafetyPage />} />
          <Route path="corrections" element={<OperatorCorrectionsPage />} />
          <Route path="tasks" element={<AdminAITasksPage />} />
        </Route>

        {/* Analytics */}
        <Route path="/analytics" element={<HubLayout tabs={tabsFor('analytics')} />}>
          <Route index element={<Navigate to="/analytics/overview" replace />} />
          <Route path="overview" element={<AnalyticsOverviewPage />} />
          <Route path="revenue" element={<PostRevenueAnalyticsPage />} />
          <Route path="demand" element={<UnavailableDemandPage />} />
          <Route path="channels" element={<ChannelAnalyticsPage />} />
        </Route>

        {/* System */}
        <Route path="/system" element={<HubLayout tabs={tabsFor('system')} />}>
          <Route index element={<Navigate to="/system/health" replace />} />
          <Route path="health" element={<SystemHealthPage />} />
          <Route path="jobs" element={<FailedJobsPage />} />
          <Route path="channels" element={<ChannelAccountsPage />} />
          <Route path="shops" element={<ShopsPage />} />
          <Route path="rollout" element={<RolloutPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>

        {/* Legacy redirects (bookmark compatibility) */}
        <Route path="/conversations" element={<LegacyRedirect to="/inbox" />} />
        <Route path="/conversations/:conversationId" element={<LegacyRedirect to="/inbox" param="conversationId" />} />
        <Route path="/products" element={<LegacyRedirect to="/catalog/products" />} />
        <Route path="/products/:productId" element={<LegacyRedirect to="/catalog/products" param="productId" />} />
        <Route path="/instagram-mapping" element={<LegacyRedirect to="/catalog/mapping" />} />
        <Route path="/catalog-copilot" element={<LegacyRedirect to="/catalog/copilot" />} />
        <Route path="/variant-resolver" element={<LegacyRedirect to="/catalog/resolver" />} />
        <Route path="/product-resolver" element={<LegacyRedirect to="/catalog/resolver" />} />
        <Route path="/fashion-dictionary" element={<LegacyRedirect to="/catalog/attributes" />} />
        <Route path="/semantic-search" element={<LegacyRedirect to="/catalog/search" />} />
        <Route path="/automation-rules" element={<LegacyRedirect to="/automation/rules" />} />
        <Route path="/scenario-coverage" element={<LegacyRedirect to="/automation/coverage" />} />
        <Route path="/scenario-simulator" element={<LegacyRedirect to="/automation/scenario-simulator" />} />
        <Route path="/triggers" element={<LegacyRedirect to="/automation/triggers" />} />
        <Route path="/recovery-rules" element={<LegacyRedirect to="/automation/recovery" />} />
        <Route path="/upsell-rules" element={<LegacyRedirect to="/automation/upsell" />} />
        <Route path="/simulator" element={<LegacyRedirect to="/automation/simulator" />} />
        <Route path="/risk-settings" element={<LegacyRedirect to="/automation/risk" />} />
        <Route path="/admin-ai-tasks" element={<LegacyRedirect to="/ai/tasks" />} />
        <Route path="/operator-corrections" element={<LegacyRedirect to="/ai/corrections" />} />
        <Route path="/automation-suggestions" element={<LegacyRedirect to="/ai/overview" />} />
        <Route path="/agent-studio" element={<LegacyRedirect to="/system/settings" />} />
        <Route path="/trl-validation" element={<Navigate to="/system/rollout?view=trl" replace />} />
        <Route path="/post-revenue" element={<LegacyRedirect to="/analytics/revenue" />} />
        <Route path="/unavailable-demand" element={<LegacyRedirect to="/analytics/demand" />} />
        <Route path="/system-health" element={<LegacyRedirect to="/system/health" />} />
        <Route path="/failed-jobs" element={<LegacyRedirect to="/system/jobs" />} />
        <Route path="/channels" element={<LegacyRedirect to="/system/channels" />} />
        <Route path="/instagram-accounts" element={<LegacyRedirect to="/system/channels" />} />
        <Route path="/shops" element={<LegacyRedirect to="/system/shops" />} />
        <Route path="/settings" element={<LegacyRedirect to="/system/settings" />} />
        <Route path="/onboarding" element={<Navigate to="/system/rollout?view=onboarding" replace />} />
        <Route path="/pilot-control" element={<Navigate to="/system/rollout?view=control" replace />} />
        <Route path="/pilot-readiness" element={<Navigate to="/system/rollout?view=readiness" replace />} />
        <Route path="/incidents" element={<Navigate to="/system/rollout?view=incidents" replace />} />
        <Route path="/incidents/:incidentId" element={<Navigate to="/system/rollout?view=incidents" replace />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
