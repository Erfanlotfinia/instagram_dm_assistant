import { QueryClientProvider } from '@tanstack/react-query';

import { AuthProvider } from '../contexts/AuthContext';
import { ShopProvider } from '../contexts/ShopContext';
import { ToastProvider, ToastContainer } from '../contexts/ToastContext';
import { queryClient } from '../lib/queryClient';
import { AppRoutes } from '../routes/AppRoutes';

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ShopProvider>
          <ToastProvider>
            <AppRoutes />
            <ToastContainer />
          </ToastProvider>
        </ShopProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
