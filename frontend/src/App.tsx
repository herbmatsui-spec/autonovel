import React, { useEffect, useRef, useCallback } from 'react';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { useProjectStore } from '@/store/useProjectStore';
import { useTaskStore } from '@/store/useTaskStore';
import { useBookStore } from '@/store/useBookStore';
import { useUIStore } from '@/store/useUIStore';
import { useWritingStore } from '@/store/useWritingStore';
import { getExportPackageUrl, getBooks } from '@/api';
import { toast } from 'sonner';
import type { TaskStatus, Book } from '@/types';
import { ErrorBanner } from '@/components/ui/ErrorBanner';
import { useBooks } from '@/hooks/useBooks';
import { useTaskStream, type StreamError } from '@/hooks/useTaskStream';
import { useBookDetails } from '@/hooks/useBookDetails';
import { useTaskRestore } from '@/hooks/useTaskRestore';
import { useAppActions } from '@/hooks/useAppActions';
import { Outlet } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { Header } from '@/components/layout/Header';
import { EasyModeDialog } from '@/components/dialogs/EasyModeDialog';

export default function App() {
  // Global Settings
  const {
    apiKey,
    setApiKey,
    modelType,
    setModelType,
    isExpertMode,
    setIsExpertMode,
  } = useUserSettingsStore();

  // Project context (keep selectedBookId for compatibility, but we'll use useBookStore.selectedBook as source)
  const {
    selectedBookId,
    setSelectedBookId,
  } = useProjectStore();

  // Books list state
  const { books, loading: booksLoading, error: booksError, handleDeleteBook } = useBooks();

  // Book Store (selectedBook object, chapters, plots, bible)
  const { selectedBook, setSelectedBook, chapters, bible, plots } = useBookStore();

  // UI Store
  const { setCreateModalOpen, optHistory, pendingPatches, promptVersions, metricTrend, globalError, setGlobalError, setOptHistory, setPendingPatches, setPromptVersions, setMetricTrend } = useUIStore();
  const isCreateModalOpen = useUIStore((s) => s.isCreateModalOpen);

  // Task Store
  const { activeTaskId, setActiveTaskId, taskStatus, setTaskStatus } = useTaskStore();

  // Writing Store
  const {
    writeFrom,
    setWriteFrom,
    writeTo,
    setWriteTo,
    writePassion,
    setWritePassion,
    importEpNum,
    setImportEpNum,
    importText,
    setImportText,
    importDoRefine,
    setImportDoRefine,
    genre,
    setGenre,
    title,
    setTitle,
    wordCount,
    setWordCount,
    platform,
    setPlatform,
    showPreview,
    setShowPreview,
    resetImport,
    error: writeError,
    clearError: clearWriteError,
  } = useWritingStore();

  // Workspace Store
  const { currentStep, setCurrentStep, isFirstRun, setIsFirstRun, pendingEasyMode, setPendingEasyMode } = useWorkspaceStore();

  // Navigation
  const navigate = useNavigate();

  // Task monitoring and restore
  const { logEndRef, handleStopTask } = useTaskMonitor();
  useTaskRestore();

  // Book details loading (based on selectedBook.id)
  const { loadBookDetails } = useBookDetails(selectedBook?.id ?? null);

  // Auto-select first book if none selected and list loaded
  useEffect(() => {
    if (books.length > 0 && !selectedBook) {
      setSelectedBook(books[0]);
      setSelectedBookId(books[0].id);
    }
  }, [books, selectedBook, setSelectedBook, setSelectedBookId]);

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
    // If this completion is from an easy mode task, select the newest book and navigate to its workspace
    if (pendingEasyMode) {
      try {
        const allBooks = await getBooks();
        if (allBooks.length > 0) {
          // Sort by created_at descending to get the newest
          const newest = allBooks.slice().sort((a, b) => 
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          )[0];
          setSelectedBook(newest);
          setSelectedBookId(newest.id);
          // Navigate to the workspace of this book, starting at theme step
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
  }, [loadBookDetails, pendingEasyMode, setPendingEasyMode, navigate]);

  const handleTaskError = useCallback((error: StreamError) => {
    console.error('Task stream connection error:', error);
    if (!error.recoverable) {
      toast.error(`接続エラー: ${error.message}`);
    }
  }, []);

  const { connectionState } = useTaskStream(activeTaskId, {
    onStatus: handleTaskStatus,
    onComplete: handleTaskComplete,
    onError: handleTaskError,
  });

  // Triggering actions
  const {
    handleCreateEasyMode,
    handleTriggerWriting,
    handleExpandPlots,
    handleCritiqueOptimize,
    handleImportChapter,
    handleGenerateMarketing,
    handleRefineErotic,
  } = useAppActions(setLoading);

  // Initialize isFirstRun based on whether apiKey is set (do once)
  useEffect(() => {
    const isFirst = !apiKey || apiKey.trim().length < 10;
    setIsFirstRun(isFirst);
  }, [apiKey, setIsFirstRun]);

  // When we start an easy mode task, set pendingEasyMode to true
  // We'll wrap handleCreateEasyMode to set the flag before calling the original.
  const handleCreateEasyModeWithFlag = useCallback(async () => {
    setPendingEasyMode(true);
    await handleCreateEasyMode();
  }, [handleCreateEasyMode, setPendingEasyMode]);

  // Ref for selectedBook to use in callbacks
  const selectedBookRef = useRef(selectedBook);
  selectedBookRef.current = selectedBook;

  return (
    <>
      <HealthGate>
        <div className="flex w-full min-h-screen bg-[var(--bg-main)]">
          {/* Always visible header */}
          <Header
            books={books}
            selectedBook={selectedBook}
            onSelectBook={setSelectedBook}
            onDeleteBook={handleDeleteBook}
            apiKey={apiKey}
            setApiKey={setApiKey}
            modelType={modelType}
            setModelType={setModelType}
            isExpertMode={isExpertMode}
            setIsExpertMode={setIsExpertMode}
            isFirstRun={isFirstRun}
            onCreateEasyMode={handleCreateEasyModeWithFlag}
          />
          <main className="flex flex-col h-[100vh] p-[2.5rem] overflow-auto">
            {globalError && (
              <ErrorBanner
                message={globalError}
                onClose={() => setGlobalError(null)}
              />
            )}
            <Outlet />
          </main>
          {/* TaskMonitor removed; we'll put its functionality in Header or BookWorkspace later */}
        </div>
      </HealthGate>
      {/* EasyModeDialog removed; we'll integrate its functionality into LandingWizard and BookWorkspace */}
    </>
  );
}