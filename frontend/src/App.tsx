import React, { useEffect, useRef, useCallback } from 'react';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { useProjectStore } from '@/store/useProjectStore';
import { useTaskStore } from '@/store/useTaskStore';
import { useBookStore } from '@/store/useBookStore';
import { useUIStore } from '@/store/useUIStore';
import { useWritingStore } from '@/store/useWritingStore';
import { getExportPackageUrl } from '@/api';
import { toast } from 'sonner';
import type { TaskStatus } from '@/types';
import { ErrorBanner } from '@/components/ui/ErrorBanner';
import { useBooks } from '@/hooks/useBooks';
import { useTaskStream, type StreamError } from '@/hooks/useTaskStream';
import { useBookDetails } from '@/hooks/useBookDetails';
import { useTaskMonitor } from '@/hooks/useTaskMonitor';
import { useTaskRestore } from '@/hooks/useTaskRestore';
import { Sidebar } from '@/components/Sidebar';
import { HealthGate } from '@/components/HealthGate';
import { EasyModeDialog } from '@/components/dialogs/EasyModeDialog';
import { TaskMonitor } from '@/components/panels/TaskMonitor';
import { useAppActions } from '@/hooks/useAppActions';
import { PageHeader } from '@/components/layout/PageHeader';
import AppRouter from './router';
import { useLocation } from 'react-router-dom';

export default function App() {
  // Global Settings (existing store)
  const {
    apiKey,
    setIsExpertMode,
  } = useUserSettingsStore();

  // Project context (existing store) - only selectedBookId remains
  const {
    selectedBookId,
    // activeTab and setActiveTab removed
  } = useProjectStore();

  // Books list state (hook handles fetch/delete only now)
  const { books } = useBooks();

  // ----- New Zustand stores -----
   const { selectedBook, setSelectedBook, chapters, bible, plots } = useBookStore();
   const { setCreateModalOpen, optHistory, pendingPatches, promptVersions, metricTrend } = useUIStore();
   const globalError = useUIStore((s) => s.globalError);
   const setGlobalError = useUIStore((s) => s.setGlobalError);
   const isCreateModalOpen = useUIStore((s) => s.isCreateModalOpen);
   const { activeTaskId, setActiveTaskId, taskStatus, setTaskStatus } = useTaskStore();
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
     } = useWritingStore();

  // For book details loading, we need to know the current tab (from URL)
  const location = useLocation();
  const pathname = location.pathname; // e.g., "/books"
  const activeTab = pathname.replace(/^\/|\/$/g, '') || 'landing';

  // ----- Local UI/cached (analytics-specific) state kept in App -----

  const [, setLoading] = React.useState<boolean>(false);

  // Book details loading delegated to useBookDetails hook (Step 12)
  // Note: useBookDetails now only needs selectedBookId; we'll update the hook later.
  const { loadBookDetails } = useBookDetails(selectedBookId ?? null);

  // ----- Refs ----
  const selectedBookRef = useRef(selectedBook);
  selectedBookRef.current = selectedBook;

  // Task monitoring (log scroll + stop) delegated to useTaskMonitor hook (Step 14)
     const { logEndRef, handleStopTask } = useTaskMonitor();

     // Task persistence restoration (restore active task on page reload)
     useTaskRestore();

     // Auto-select the first book into the store once the list is loaded.
   useEffect(() => {
     if (books.length > 0 && !selectedBook) {
       setSelectedBook(books[0]);
     }
   }, [books, selectedBook, setSelectedBook]);

   // Load Book Details when selected book or active tab changes
   useEffect(() => {
     if (selectedBookId) {
       loadBookDetails(selectedBookId);
     }
     // eslint-disable-next-line react-hooks/exhaustive-deps
   }, [selectedBookId, location.pathname]); // change location.pathname triggers reload

 // Task SSE Stream Connection Control (Step 13)
     const handleTaskStatus = useCallback((status: TaskStatus) => {
       setTaskStatus(status);
     }, [setTaskStatus]);

     const handleTaskComplete = useCallback((status: TaskStatus) => {
       const book = selectedBookRef.current;
       if (book) loadBookDetails(book.id);
       
       // Only clear task on success - keep it for error display
       const hasError = status.error || status.task_error;
       if (!hasError) {
         setActiveTaskId(null);
         toast.success('バックグラウンドタスクが正常に完了しました！');
       } else {
         toast.error(`タスクエラーが発生しました: ${status.task_error?.message ?? status.error ?? '不明なエラー'}`);
       }
     }, [setActiveTaskId, loadBookDetails]);

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

   // Triggering actions consolidated in a custom hook
   const {
     handleCreateEasyMode,
     handleTriggerWriting,
     handleExpandPlots,
     handleCritiqueOptimize,
     handleImportChapter,
     handleGenerateMarketing,
     handleRefineErotic,
   } = useAppActions(setLoading);

  return (
    <HealthGate>
      <div className="flex w-full min-h-screen bg-[var(--bg-main)]">
        <Sidebar />
        <main className="flex flex-col h-[100vh] p-[2.5rem] overflow-auto">
          <PageHeader globalError={globalError} />
          {globalError && (
            <ErrorBanner
              message={globalError}
              onClose={() => setGlobalError(null)}
            />
          )}
          <AppRouter />
        </main>
        <TaskMonitor
          logEndRef={logEndRef}
          onStop={handleStopTask}
          connectionState={connectionState}
        />
        <EasyModeDialog
          isOpen={isCreateModalOpen}
          onClose={() => setCreateModalOpen(false)}
          onSubmit={() => {
            handleCreateEasyMode();
            // Navigate to books tab after creating
            // We don't have navigate here; we'll use a workaround: set a state and useEffect?
            // For simplicity, we'll just close the modal and let user navigate manually.
            // TODO: Fix navigation from dialog.
          }}
        />
      </div>
    </HealthGate>
  );
}