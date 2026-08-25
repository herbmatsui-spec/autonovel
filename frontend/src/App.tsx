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
import { LandingTab } from '@/components/tabs/LandingTab';
import { BooksTab } from '@/components/tabs/BooksTab';
import { PlotsTab } from '@/components/tabs/PlotsTab';
import { WriteTab } from '@/components/tabs/WriteTab';
import { AnalyticsTab } from '@/components/tabs/AnalyticsTab';
import { PlanningTab } from '@/components/tabs/PlanningTab';
import { StyleLabTab } from '@/components/tabs/StyleLabTab';
import { AuditTab } from '@/components/tabs/AuditTab';
import { HealthGate } from '@/components/HealthGate';
import { EasyModeDialog } from '@/components/dialogs/EasyModeDialog';
import { TaskMonitor } from '@/components/panels/TaskMonitor';
import { useAppActions } from '@/hooks/useAppActions';
import { PageHeader } from '@/components/layout/PageHeader';


export default function App() {
  // Global Settings (existing store)
  const {
    apiKey,
    setIsExpertMode,
  } = useUserSettingsStore();

  // Project context (existing store)
  const {
    activeTab,
    setActiveTab,
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

   // ----- Local UI/cached (analytics-specific) state kept in App -----

   const [, setLoading] = React.useState<boolean>(false);


   // Book details loading delegated to useBookDetails hook (Step 12)
   const { loadBookDetails } = useBookDetails(selectedBook?.id ?? null, activeTab);

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
    if (selectedBook) {
      loadBookDetails(selectedBook.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBook, activeTab]);

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

      {/* MAIN MAIN CONTENT CONTAINER */}
      <main className="flex flex-col h-[100vh] p-[2.5rem] overflow-auto">

         <PageHeader activeTab={activeTab} globalError={globalError} />

        {globalError && (
          <ErrorBanner
            message={globalError}
            onClose={() => setGlobalError(null)}
          />
        )}

        {/* -------------------- TAB 0: LANDING -------------------- */}
        {activeTab === 'landing' && (
          <LandingTab
            setActiveTab={setActiveTab}
            setCreateModalOpen={setCreateModalOpen}
            setIsExpertMode={setIsExpertMode}
          />
        )}

        {/* -------------------- TAB 1: BOOKS LIST -------------------- */}
        {activeTab === 'books' && (
          <BooksTab
            selectedBook={selectedBook}
            setSelectedBook={setSelectedBook}
            setShowCreateModal={setCreateModalOpen}
          />
        )}

        {/* -------------------- TAB 2: PLOTS TIMELINE -------------------- */}
{activeTab === 'plots' && selectedBook && (
           <PlotsTab
             selectedBook={selectedBook}
             handleExpandPlots={handleExpandPlots}
             plots={plots}
           />
         )}

        {/* -------------------- TAB 3: WRITE & STREAMING LOGS -------------------- */}
          {activeTab === 'write' && selectedBook && (
            <div className="animate-fade-in grid grid-cols-[1fr_350px] gap-[2rem]">
            {/* Left Column: Chapters browse & controls */}
                <div className="flex flex-col gap-[2rem]">
                <WriteTab
                  selectedBook={selectedBook}
                  handleTriggerWriting={handleTriggerWriting}
                  handleImportChapter={handleImportChapter}
                  handleRefineErotic={handleRefineErotic}
                  chapters={chapters}
                  bible={bible}
                  writeFrom={writeFrom}
                  setWriteFrom={setWriteFrom}
                  writeTo={writeTo}
                  setWriteTo={setWriteTo}
                  writePassion={writePassion}
                  setWritePassion={setWritePassion}
                  importEpNum={importEpNum}
                  setImportEpNum={setImportEpNum}
                  importText={importText}
                  setImportText={setImportText}
                  importDoRefine={importDoRefine}
                  setImportDoRefine={setImportDoRefine}
                  activeTaskId={activeTaskId}
                  genre={genre}
                  setGenre={setGenre}
                  title={title}
                  setTitle={setTitle}
                  wordCount={wordCount}
                  setWordCount={setWordCount}
                  platform={platform}
                  setPlatform={setPlatform}
                  showPreview={showPreview}
                  setShowPreview={setShowPreview}
                />
            </div>
          </div>
        )}

        {/* -------------------- TAB 4: CRITIQUE AND MARKETING -------------------- */}
        {activeTab === 'analytics' && selectedBook && (
          <AnalyticsTab
              selectedBook={selectedBook}
              metricTrend={metricTrend}
              optHistory={optHistory}
              pendingPatches={pendingPatches}
              promptVersions={promptVersions}
              handleCritiqueOptimize={handleCritiqueOptimize}
              handleGenerateMarketing={handleGenerateMarketing}
              getExportPackageUrl={getExportPackageUrl}
              apiKey={apiKey}
              onRefresh={() => loadBookDetails(selectedBook.id)}
              setActiveTab={setActiveTab}
            />
          )}

        {/* -------------------- TAB 5: PLANNING -------------------- */}
        {activeTab === 'planning' && (
          <PlanningTab
            selectedBook={selectedBook}
            handlePlanGeneration={async () => {
              await loadBookDetails(selectedBook?.id ?? 0);
              setActiveTab('plots');
            }}
          />
        )}

        {/* -------------------- TAB 6: STYLE LAB -------------------- */}
        {activeTab === 'style-lab' && (
          <StyleLabTab />
        )}

{/* -------------------- TAB 7: AUDIT -------------------- */}
        {activeTab === 'audit' && selectedBook && (
          <AuditTab selectedBook={selectedBook} apiKey={apiKey} />
        )}
      </main>

      {/* -------------------- FLOATING TASK MONITOR OVERLAY -------------------- */}
      {activeTaskId && taskStatus && (
        <TaskMonitor
          logEndRef={logEndRef}
          onStop={handleStopTask}
          connectionState={connectionState}
        />
      )}

      {/* -------------------- NEW NOVEL (EASY MODE) MODAL DIALOG -------------------- */}
          {isCreateModalOpen && (
             <EasyModeDialog
               isOpen={isCreateModalOpen}
               onClose={() => setCreateModalOpen(false)}
               onSubmit={() => {
                 handleCreateEasyMode();
                 setActiveTab('books');
               }}
             />
          )}
      </div>
    </HealthGate>
  );
}
