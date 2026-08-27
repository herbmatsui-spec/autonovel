import { Routes, Route, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';

// Lazy load new components
const LandingWizard = lazy(() => import('./components/LandingWizard'));
const Setup = lazy(() => import('./components/Setup'));
const BookWorkspace = lazy(() => import('./components/BookWorkspace'));
const BooksTab = lazy(() => import('./components/tabs/BooksTab'));

const LoadingSpinner = () => (
  <div className="flex items-center justify-center py-8">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
  </div>
);

function AppRouter() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        {/* New routes */}
        <Route path="/" element={<Navigate to="/landing" replace />} />
        <Route path="/setup" element={<Setup />} />
        <Route path="/landing" element={<LandingWizard />} />
        <Route path="/books" element={<BooksTab />} />
        <Route path="/book/:id" element={<BookWorkspace />} />
        <Route path="/book/:id/:step" element={<BookWorkspace />} />
        {/* Existing routes - redirect to appropriate new locations */}
        <Route path="/landing/*" element={<Navigate to="/landing" replace />} />
        <Route path="/books/*" element={<Navigate to="/books" replace />} />
        <Route path="/plots" element={<Navigate to="/books" replace />} />
        <Route path="/write" element={<Navigate to="/books" replace />} />
        <Route path="/analytics" element={<Navigate to="/books" replace />} />
        <Route path="/planning" element={<Navigate to="/books" replace />} />
        <Route path="/style-lab" element={<Navigate to="/books" replace />} />
        <Route path="/audit" element={<Navigate to="/books" replace />} />
        <Route path="/monitor" element={<Navigate to="/books" replace />} />
        <Route path="/strategy" element={<Navigate to="/books" replace />} />
        <Route path="/import" element={<Navigate to="/books" replace />} />
        <Route path="*" element={<Navigate to="/landing" replace />} />
      </Routes>
    </Suspense>
  );
}

export default AppRouter;