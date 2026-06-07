import { AppRoutes } from '../routes/AppRoutes';
import { AppLayout } from '../components/AppLayout';

export function App() {
  return (
    <AppLayout>
      <AppRoutes />
    </AppLayout>
  );
}
