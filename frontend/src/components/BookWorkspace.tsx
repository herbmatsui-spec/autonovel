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

export default function BookWorkspace() {
  const { id: bookIdParam } = useParams<{ id: string }>();
  const { step: stepParam } = useParams<{ step: string }>();
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

  // Sync step from URL to workspace store
  useEffect(() => {
    if (stepParam) {
      setCurrentStep(stepParam);
    }
  }, [stepParam, setCurrentStep]);

  // When step changes in store, update URL
  useEffect(() => {
    if (currentStep && bookId && !isNaN(bookId) && bookId > 0) {
      navigate(`/book/${bookId}/${currentStep}`, { replace: true });
    }
  }, [currentStep, bookId, navigate]);

  // Determine step to display (fallback to theme)
  const displayStep = stepParam || currentStep || 'theme';

  // Map step to component
  const StepComponent = () => {
    switch (displayStep) {
      case 'theme':
        return <ThemeStep bookId={bookId} />;
      case 'outline':
        return <OutlineStep bookId={bookId} />;
      case 'write':
        return <WriteStep bookId={bookId} />;
      case 'finish':
        return <FinishStep bookId={bookId} />;
      case 'publish':
        return <PublishStep bookId={bookId} />;
      default:
        return <div>Unknown step</div>;
    }
  };

  return (
    <div className="flex h-[100vh] bg-[var(--bg-main)]">
      {/* Left: Step Bar */}
      <StepBar bookId={bookId} currentStep={displayStep} />

      {/* Center: Step Content */}
      <div className="flex-1 overflow-hidden">
        <StepShell>
          <StepComponent />
        </StepShell>
      </div>

      {/* Right: Progress Panel */}
      <ProgressPanel />
    </div>
  );
}