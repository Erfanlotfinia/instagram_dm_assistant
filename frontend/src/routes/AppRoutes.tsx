import { Navigate, Route, Routes } from 'react-router-dom';

import { DashboardPage } from '../pages/DashboardPage';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
