import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import { AppLayout } from '../components/AppLayout';
import { ProtectedRoute } from '../components/ProtectedRoute';
import { ConversationDetailPage } from '../pages/ConversationDetailPage';
import { ConversationsPage } from '../pages/ConversationsPage';
import { AnalyticsPage } from '../pages/AnalyticsPage';
import { DashboardPage } from '../pages/DashboardPage';
import { DMSimulatorPage } from '../pages/DMSimulatorPage';
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
import { SemanticSearchPage } from '../pages/SemanticSearchPage';
import { SettingsPage } from '../pages/SettingsPage';
import { ShopsPage } from '../pages/ShopsPage';

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
            <DashboardPage />
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
