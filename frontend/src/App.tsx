import { useEffect, useRef, useCallback } from 'react';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { useProjectStore } from '@/store/useProjectStore';
import { useTaskStore } from '@/store/useTaskStore';
import { useBookStore } from '@/store/useBookStore';
import { useUIStore } from '@/store/useUIStore';
import { getBooks } from '@/api';
import { toast } from 'sonner';
import type { TaskStatus } from '@/types';
import { ErrorBanner } from '@/components/ui/ErrorBanner';
import { useBooks } from '@/hooks/useBooks';
import { useTaskStream, type StreamError } from '@/hooks/useTaskStream';
import { useBookDetails } from '@/hooks/useBookDetails';
import { useTaskRestore } from '@/hooks/useTaskRestore';
import { useAppActions } from '@/hooks/useAppActions';
import { useAxisLocksSync } from '@/hooks/useAxisLocksSync';
import { Outlet, useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { Header } from '@/components/layout/Header';
import { HealthGate } from '@/components/HealthGate';

export default function App() {
  // Global Settings
  const { apiKey } = useUserSettingsStore();

  const { setSelectedBookId } = useProjectStore();

  // Books list state
  const { books, handleDeleteBook } = useBooks();

  // Book Store
  const { selectedBook, selectBook, hydrateLocks } = useBookStore();

  // UI Store
  const { globalError, setGlobalError } = useUIStore();

  // Task Store
  const { activeTaskId, setActiveTaskId, setTaskStatus } = useTaskStore();

  // Workspace Store
  const { setIsFirstRun, pendingEasyMode, setPendingEasyMode } = useWorkspaceStore();

  // Navigation
  const navigate = useNavigate();

  // Sync axis locks via SSE
  useAxisLocksSync();

  // Task restore on mount
  useTaskRestore();

  // Hydrate axis locks from localStorage
  useEffect(() => {
    hydrateLocks();
  }, [hydrateLocks]);

  // Book details loading (based on selectedBook.id)
  const { loadBookDetails } = useBookDetails(selectedBook?.id ?? null);

  // Auto-select first book if none selected and list loaded
  useEffect(() => {
    if (books.length > 0 && !selectedBook) {
      selectBook(books[0]);
      setSelectedBookId(books[0].id);
    }
  }, [books, selectedBook, selectBook, setSelectedBookId]);

  // Load book details when selected book changes
  useEffect(() => {
    if (selectedBook?.id) {
      loadBookDetails(selectedBook.id);
    }
  }, [selectedBook?.id, loadBookDetails]);

  // Task SSE Stream Connection Control
  const handleTaskStatus = useCallback((status: TaskStatus) => {
    setTaskStatus(status);
  }, [setTaskStatus]);

  const handleTaskComplete = useCallback(async (status: TaskStatus) => {
    if (pendingEasyMode) {
      try {
        const allBooks = await getBooks();
        if (allBooks.length > 0) {
          const newest = allBooks.slice().sort((a, b) => 
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          )[0];
          selectBook(newest);
          setSelectedBookId(newest.id);
          navigate(`/book/${newest.id}/theme`, { replace: true });
        }
      } catch (err) {
        console.error('Failed to fetch books after easy mode:', err);
      }
      setPendingEasyMode(false);
    }

    const book = selectedBookRef.current;
    if (book) {
      loadBookDetails(book.id);
    }
    const hasError = status.error || status.task_error;
    if (!hasError) {
      setActiveTaskId(null);
      toast.success('バックグラウンドタスクが正常に完了しました！');
    } else {
      toast.error(`タスクエラーが発生しました: ${status.task_error?.message ?? status.error ?? '不明なエラー'}`);
    }
  }, [loadBookDetails, pendingEasyMode, setPendingEasyMode, navigate, selectBook, setSelectedBookId, setActiveTaskId]);

  const handleTaskError = useCallback((error: StreamError) => {
    console.error('Task stream connection error:', error);
    if (!error.recoverable) {
      toast.error(`接続エラー: ${error.message}`);
    }
  }, []);

  useTaskStream(activeTaskId, {
    onStatus: handleTaskStatus,
    onComplete: handleTaskComplete,
    onError: handleTaskError,
  });

  // Triggering actions
  const { handleCreateEasyMode } = useAppActions(() => {});

  // Initialize isFirstRun based on whether apiKey is set (do once)
  useEffect(() => {
    const isFirst = !apiKey || apiKey.trim().length < 10;
    setIsFirstRun(isFirst);
  }, [apiKey, setIsFirstRun]);

  const handleCreateEasyModeWithFlag = useCallback(async () => {
    setPendingEasyMode(true);
    await handleCreateEasyMode();
  }, [handleCreateEasyMode, setPendingEasyMode]);

  // Ref for selectedBook to use in callbacks
  const selectedBookRef = useRef(selectedBook);
  selectedBookRef.current = selectedBook;

  return (
    <HealthGate>
      <div className="flex flex-col w-full min-h-screen bg-[var(--bg-main)] text-[var(--text-primary)]">
        {/* Always visible header */}
        <Header
          books={books}
          selectedBook={selectedBook}
          onSelectBook={selectBook}
          onDeleteBook={handleDeleteBook}
          apiKey={apiKey}
          onCreateEasyMode={handleCreateEasyModeWithFlag}
        />
        <main className="flex-1 flex flex-col p-4 sm:p-6 lg:p-8 overflow-y-auto max-w-7xl w-full mx-auto">
          {globalError && (
            <ErrorBanner
              message={globalError}
              onClose={() => setGlobalError(null)}
            />
          )}
          <Outlet />
        </main>
      </div>
    </HealthGate>
  );
}