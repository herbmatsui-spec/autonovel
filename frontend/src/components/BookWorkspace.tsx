import { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useBookStore } from '@/store/useBookStore';
import { useBookDetails } from '@/hooks/useBookDetails';
import { getBook } from '@/api';
import StepBar from './StepBar';
import StepShell from './StepShell';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { ThemeStep } from './steps/ThemeStep';
import { OutlineStep } from './steps/OutlineStep';
import { WriteStep } from './steps/WriteStep';
import { FinishStep } from './steps/FinishStep';
import { PublishStep } from './steps/PublishStep';
import { ProgressPanel } from './ProgressPanel';
import { lazy } from 'react';
// Lazy load tab components
const StyleLabTab = lazy(() => import('./tabs/StyleLabTab'));
const PlotsTab = lazy(() => import('./tabs/PlotsTab'));
const AnalyticsTab = lazy(() => import('./tabs/AnalyticsTab'));
// Import the tab bar component
import BookTabBar from './BookTabBar';
// Add more tabs as needed

export default function BookWorkspace() {
  const { id: bookIdParam } = useParams<{ id: string }>();
  const { step: stepParam } = useParams<{ step: string }>();
  const { tab: tabParam } = useParams<{ tab: string }>();
  const bookId = Number(bookIdParam);
  const navigate = useNavigate();
  const { selectedBook, setSelectedBook } = useBookStore();
  const { loadBookDetails } = useBookDetails(bookId || null);
  const { currentStep, setCurrentStep } = useWorkspaceStore();

  // If no book selected, redirect to landing
  useEffect(() => {
    if (!selectedBook) {
      navigate('/landing', { replace: true });
    }
  }, [selectedBook, navigate]);

  // Load book metadata and details when bookId changes
  useEffect(() => {
    if (!isNaN(bookId) && bookId > 0) {
      // Fetch book metadata (title, genre, etc.)
      getBook(bookId)
        .then((book) => {
          setSelectedBook(book);
        })
        .catch((err) => {
          console.error('Failed to fetch book metadata:', err);
        });
      // Load related data (plots, chapters, etc.)
      loadBookDetails(bookId);
    }
  }, [bookId, loadBookDetails, setSelectedBook]);

  // Sync step from URL to workspace store (only if no tab is specified, to avoid overriding step when viewing a tab)
  useEffect(() => {
    if (stepParam && !tabParam) {
      setCurrentStep(stepParam);
    }
  }, [stepParam, tabParam, setCurrentStep]);

  // When step changes in store, update URL (only if no tab is specified)
  useEffect(() => {
    if (currentStep && bookId && !isNaN(bookId) && bookId > 0 && !tabParam) {
      navigate(`/book/${bookId}/${currentStep}`, { replace: true });
    }
  }, [currentStep, bookId, navigate]);

  // Determine step to display (fallback to theme)
  const displayStep = stepParam || currentStep || 'theme';

  // Map step component
  const StepComponent = () => {
    switch (displayStep) {
      case 'theme':
        return <ThemeStep bookId={bookId} step={displayStep} />;
      case 'outline':
        return <OutlineStep bookId={bookId} step={displayStep} />;
      case 'write':
        return <WriteStep bookId={bookId} step={displayStep} />;
      case 'finish':
        return <FinishStep bookId={bookId} step={displayStep} />;
      case 'publish':
        return <PublishStep bookId={bookId} step={displayStep} />;
      default:
        return <div>Unknown step</div>;
    }
  };

  // Map tab to component
  const TabComponent = () => {
    switch (tabParam) {
      case 'style-lab':
        return <StyleLabTab bookId={bookId} />;
      case 'plots':
        return <PlotsTab bookId={bookId} />;
      case 'analytics':
        return <AnalyticsTab bookId={bookId} />;
      default:
        return <div>Unknown tab</div>;
    }
  };

  // Handler for changing tab
  const handleTabChange = (tabId: string) => {
    navigate(`/book/${bookId}/${displayStep}/${tabId}`, { replace: true });
  };

  return (
    <div className="flex h-[100vh] bg-[var(--bg-main)]">
      {/* Left: Step Bar */}
      <StepBar bookId={bookId} currentStep={displayStep} currentTab={tabParam} />

      {/* Center: Step Content */}
      <div className="flex-1 overflow-hidden">
        {tabParam ? (
          <>
            {/* Tab bar when viewing a tab */}
            <BookTabBar
              bookId={bookId}
              currentStep={displayStep}
              currentTab={tabParam}
              onTabChange={handleTabChange}
            />
            <StepShell>
              <TabComponent />
            </StepShell>
          </>
        ) : (
          <StepShell>
            <StepComponent />
          </StepShell>
        )}
      </div>

      {/* Right: Progress Panel */}
      <ProgressPanel />
    </div>
  );
}