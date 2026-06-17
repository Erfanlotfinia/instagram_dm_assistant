import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { ContactPage } from './pages/ContactPage';
import { AboutPage } from './pages/AboutPage';
import { HomePage } from './pages/HomePage';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/about-us" element={<AboutPage />} />
        <Route path="/about-modira" element={<AboutPage />} />
        <Route path="/contact" element={<ContactPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
