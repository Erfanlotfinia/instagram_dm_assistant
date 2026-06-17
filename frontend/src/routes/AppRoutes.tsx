import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import { AppLayout } from '../components/AppLayout';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { CatalogCopilotPage } from '../pages/CatalogCopilotPage';
import { ChannelAccountsPage } from '../pages/ChannelAccountsPage';
import { ConversationDetailPage } from '../pages/ConversationDetailPage';
import { ConversationsPage } from '../pages/ConversationsPage';
import { AgentStudioSettingsPage } from '../pages/AgentStudioSettingsPage';
import { AnalyticsPage } from '../pages/AnalyticsPage';
import { EnterpriseDashboardPage } from '../pages/EnterpriseDashboardPage';
import { DMSimulatorPage } from '../pages/DMSimulatorPage';
import { FashionDictionaryPage } from '../pages/FashionDictionaryPage';
import { FailedJobsPage } from '../pages/FailedJobsPage';
import { InstagramAccountsPage } from '../pages/InstagramAccountsPage';
import {
  InstagramProductMappingPage,
  ProductResolverPage,
} from '../pages/InstagramProductMappingPage';
import { LoginPage } from '../pages/LoginPage';
import { OnboardingPage } from '../pages/OnboardingPage';
import { OrderDetailPage } from '../pages/OrderDetailPage';
import { OrdersPage } from '../pages/OrdersPage';
import { ProductDetailPage } from '../pages/ProductDetailPage';
import { ProductsPage } from '../pages/ProductsPage';
import { PostRevenueAnalyticsPage } from '../pages/PostRevenueAnalyticsPage';
import { PilotReadinessPage } from '../pages/PilotReadinessPage';
import { PilotControlCenterPage } from '../pages/PilotControlCenterPage';
import { IncidentTimelinePage } from '../pages/IncidentTimelinePage';
import { RecoveryRulesPage } from '../pages/RecoveryRulesPage';
import { RiskSettingsPage } from '../pages/RiskSettingsPage';
import { SystemHealthPage } from '../pages/SystemHealthPage';
import { UpsellRulesPage } from '../pages/UpsellRulesPage';
import { SemanticSearchPage } from '../pages/SemanticSearchPage';
import { SettingsPage } from '../pages/SettingsPage';
import { TriggerRulesPage } from '../pages/TriggerRulesPage';
import { TRLValidationPage } from '../pages/TRLValidationPage';
import { UnavailableDemandPage } from '../pages/UnavailableDemandPage';
import { VariantResolverPage } from '../pages/VariantResolverPage';
import { ShopsPage } from '../pages/ShopsPage';
import { AdminAITasksPage, AutomationRulesPage, AutomationSuggestionsPage, OperatorCorrectionsPage, ScenarioCoveragePage, ScenarioSimulatorPage } from '../pages/SocialAdminPages';

function AuthenticatedShell({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute>
      <AppLayout>{children}</AppLayout>
    </ProtectedRoute>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <AuthenticatedShell>
            <EnterpriseDashboardPage />
          </AuthenticatedShell>
        }
      />

      <Route
        path="/onboarding"
        element={
          <AuthenticatedShell>
            <OnboardingPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/simulator"
        element={
          <AuthenticatedShell>
            <DMSimulatorPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/pilot-readiness"
        element={
          <AuthenticatedShell>
            <PilotReadinessPage />
          </AuthenticatedShell>
        }
      />

      <Route
        path="/pilot-control"
        element={
          <AuthenticatedShell>
            <PilotControlCenterPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/incidents"
        element={
          <AuthenticatedShell>
            <IncidentTimelinePage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/incidents/:incidentId"
        element={
          <AuthenticatedShell>
            <IncidentTimelinePage />
          </AuthenticatedShell>
        }
      />

      <Route
        path="/trl-validation"
        element={
          <AuthenticatedShell>
            <TRLValidationPage />
          </AuthenticatedShell>
        }
      />


      <Route
        path="/catalog-copilot"
        element={
          <AuthenticatedShell>
            <CatalogCopilotPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/fashion-dictionary"
        element={
          <AuthenticatedShell>
            <FashionDictionaryPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/variant-resolver"
        element={
          <AuthenticatedShell>
            <VariantResolverPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/unavailable-demand"
        element={
          <AuthenticatedShell>
            <UnavailableDemandPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/triggers"
        element={
          <AuthenticatedShell>
            <TriggerRulesPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/risk-settings"
        element={
          <AuthenticatedShell>
            <RiskSettingsPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/agent-studio"
        element={
          <AuthenticatedShell>
            <AgentStudioSettingsPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/analytics"
        element={
          <AuthenticatedShell>
            <AnalyticsPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/shops"
        element={
          <AuthenticatedShell>
            <ShopsPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/instagram-accounts"
        element={
          <AuthenticatedShell>
            <InstagramAccountsPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/channels"
        element={
          <AuthenticatedShell>
            <ChannelAccountsPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/recovery-rules"
        element={
          <AuthenticatedShell>
            <RecoveryRulesPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/upsell-rules"
        element={
          <AuthenticatedShell>
            <UpsellRulesPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/post-revenue"
        element={
          <AuthenticatedShell>
            <PostRevenueAnalyticsPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/products"
        element={
          <AuthenticatedShell>
            <ProductsPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/products/:productId"
        element={
          <AuthenticatedShell>
            <ProductDetailPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/instagram-mapping"
        element={
          <AuthenticatedShell>
            <InstagramProductMappingPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/product-resolver"
        element={
          <AuthenticatedShell>
            <ProductResolverPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/semantic-search"
        element={
          <AuthenticatedShell>
            <SemanticSearchPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/orders"
        element={
          <AuthenticatedShell>
            <OrdersPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/orders/:orderId"
        element={
          <AuthenticatedShell>
            <OrderDetailPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/conversations"
        element={
          <AuthenticatedShell>
            <ConversationsPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/conversations/:conversationId"
        element={
          <AuthenticatedShell>
            <ConversationDetailPage />
          </AuthenticatedShell>
        }
      />
      <Route
        path="/system-health"
        element={
          <AuthenticatedShell>
            <SystemHealthPage />
          </AuthenticatedShell>
        }
      />

      <Route
        path="/failed-jobs"
        element={
          <AuthenticatedShell>
            <FailedJobsPage />
          </AuthenticatedShell>
        }
      />

      <Route path="/scenario-coverage" element={<AuthenticatedShell><ScenarioCoveragePage /></AuthenticatedShell>} />
      <Route path="/automation-rules" element={<AuthenticatedShell><AutomationRulesPage /></AuthenticatedShell>} />
      <Route path="/scenario-simulator" element={<AuthenticatedShell><ScenarioSimulatorPage /></AuthenticatedShell>} />
      <Route path="/admin-ai-tasks" element={<AuthenticatedShell><AdminAITasksPage /></AuthenticatedShell>} />
      <Route path="/operator-corrections" element={<AuthenticatedShell><OperatorCorrectionsPage /></AuthenticatedShell>} />
      <Route path="/automation-suggestions" element={<AuthenticatedShell><AutomationSuggestionsPage /></AuthenticatedShell>} />
      <Route
        path="/settings"
        element={
          <AuthenticatedShell>
            <SettingsPage />
          </AuthenticatedShell>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
