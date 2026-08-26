import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';

// Lazy load tabs
const LandingTab = lazy(() => import('./components/tabs/LandingTab'));
const BooksTab = lazy(() => import('./components/tabs/BooksTab'));
const PlotsTab = lazy(() => import('./components/tabs/PlotsTab'));
const WriteTab = lazy(() => import('./components/tabs/WriteTab'));
const AnalyticsTab = lazy(() => import('./components/tabs/AnalyticsTab'));
const PlanningTab = lazy(() => import('./components/tabs/PlanningTab'));
const StyleLabTab = lazy(() => import('./components/tabs/StyleLabTab'));
const AuditTab = lazy(() => import('./components/tabs/AuditTab'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center py-8">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

function AppRouter() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          <Route path="/" element={<Navigate to="/landing" replace />} />
          <Route path="/landing" element={<LandingTab />} />
          <Route path="/books" element={<BooksTab />} />
          <Route path="/plots" element={<PlotsTab />} />
          <Route path="/write" element={<WriteTab />} />
          <Route path="/analytics" element={<AnalyticsTab />} />
          <Route path="/planning" element={<PlanningTab />} />
          <Route path="/style-lab" element={<StyleLabTab />} />
          <Route path="/audit" element={<AuditTab />} />
          <Route path="*" element={<Navigate to="/landing" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default AppRouter;