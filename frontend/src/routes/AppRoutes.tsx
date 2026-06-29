import { Navigate, Outlet, Route, Routes, useLocation, useParams } from 'react-router-dom';

import { AppShell } from '../components/shell/AppShell';
import { HubLayout } from '../components/shell/HubLayout';
import { HUBS } from '../components/shell/navConfig';
import { ProtectedRoute } from '../components/ProtectedRoute';
import {
  AdminAITasksPage,
  AIFallbacksPage,
  AIControlOverviewPage,
  AISafetyPage,
  AnalyticsOverviewPage,
  AutomationRulesPage,
  AutomationSuggestionsPage,
  AttributeDictionaryPage,
  ChannelAccountsPage,
  ChannelAnalyticsPage,
  ChannelOnboardingPage,
  InstagramAccountSelectPage,
  InstagramConnectCallbackPage,
  ConversationIntelligencePage,
  DMSimulatorPage,
  FailedJobsPage,
  HandoffQueuePage,
  InboxPage,
  IncidentTimelinePage,
  InstagramProductMappingPage,
  LLMLogsPage,
  LoginPage,
  ProfilePage,
  OperatorCorrectionsPage,
  OrderDetailPage,
  OrdersHubPage,
  OverviewPage,
  PostRevenueAnalyticsPage,
  ProductDetailPage,
  ProductsPage,
  RecoveryRulesPage,
  RevenueRecoveryPage,
  RiskSettingsPage,
  RolloutPage,
  ScenarioCoveragePage,
  ScenarioSimulatorPage,
  SettingsPage,
  ShopReadinessPage,
  ShopsPage,
  SystemHealthPage,
  TriggerRulesPage,
  UnavailableDemandPage,
  UpsellRulesPage,
  VariantResolverPage,
} from './lazyPages';
import { RouteSuspense } from './RouteSuspense';

function LegacyConversationRedirect() {
  const { conversationId } = useParams<{ conversationId?: string }>();
  const location = useLocation();
  const inboxPath = conversationId ? `/inbox/${conversationId}` : '/inbox';

  return <Navigate to={`${inboxPath}${location.search}${location.hash}`} replace />;
}

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
        <Route path="/profile" element={<ProfilePage />} />

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
          <Route path="resolver" element={<VariantResolverPage />} />
          <Route path="attributes" element={<AttributeDictionaryPage />} />
        </Route>

        {/* Automation */}
        <Route path="/automation" element={<HubLayout tabs={tabsFor('automation')} />}>
          <Route index element={<Navigate to="/automation/rules" replace />} />
          <Route path="rules" element={<AutomationRulesPage />} />
          <Route path="coverage" element={<ScenarioCoveragePage />} />
          <Route path="triggers" element={<TriggerRulesPage />} />
          <Route path="recovery" element={<RecoveryRulesPage />} />
          <Route path="upsell" element={<UpsellRulesPage />} />
          <Route path="suggestions" element={<AutomationSuggestionsPage />} />
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
          <Route path="recovery" element={<RevenueRecoveryPage />} />
          <Route path="channels" element={<ChannelAnalyticsPage />} />
        </Route>

        {/* System */}
        <Route path="/system" element={<HubLayout tabs={tabsFor('system')} />}>
          <Route index element={<Navigate to="/system/health" replace />} />
          <Route path="health" element={<SystemHealthPage />} />
          <Route path="jobs" element={<FailedJobsPage />} />
          <Route path="channels" element={<ChannelAccountsPage />} />
          <Route path="channels/onboarding" element={<ChannelOnboardingPage />} />
          <Route path="channels/instagram/connect" element={<InstagramConnectCallbackPage />} />
          <Route path="channels/instagram/select" element={<InstagramAccountSelectPage />} />
          <Route path="shops" element={<ShopsPage />} />
          <Route path="rollout" element={<RolloutPage />} />
          <Route path="readiness" element={<ShopReadinessPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>

        {/* Legacy in-app links kept while callers migrate to the final hub routes. */}
        <Route path="/conversations" element={<LegacyConversationRedirect />} />
        <Route path="/conversations/:conversationId" element={<LegacyConversationRedirect />} />
        <Route path="/incidents" element={<IncidentTimelinePage />} />
        <Route path="/incidents/:incidentId" element={<IncidentTimelinePage />} />
        <Route path="/system-health" element={<Navigate to="/system/health" replace />} />
        <Route path="/operator-corrections" element={<Navigate to="/ai/corrections" replace />} />

        {/* Unknown paths return to the Overview hub. */}

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
