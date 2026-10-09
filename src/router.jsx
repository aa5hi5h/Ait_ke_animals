// Application router.
//
// The app previously switched views with local state inside main.jsx. These
// routes are additive: "/" still renders the untouched Landing / Citizen
// pre-check flow, and the new reviewer-dashboard routes live beside it.

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { App } from './main.jsx';
import './styles/dashboard.css';
import DashboardPage from './pages/dashboard/DashboardPage.jsx';
import NewCasePage from './pages/dashboard/NewCasePage.jsx';
import CaseWorkspacePage from './pages/dashboard/CaseWorkspacePage.jsx';

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/cases/new" element={<NewCasePage />} />
        <Route path="/cases/:caseId" element={<CaseWorkspacePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
