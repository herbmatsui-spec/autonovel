import React, { useEffect, useRef, useCallback } from 'react';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { useProjectStore } from '@/store/useProjectStore';
import { useTaskStore } from '@/store/useTaskStore';
import { useBookStore } from '@/store/useBookStore';
import { useUIStore } from '@/store/useUIStore';
import { useWritingStore } from '@/store/useWritingStore';
import { useEasyModeStore } from '@/store/useEasyModeStore';
import { getExportPackageUrl } from '@/api';
import { toast } from 'sonner';
import { ErrorBanner } from '@/components/ui/ErrorBanner';
import { useBooks } from '@/hooks/useBooks';
import { useTaskStream } from '@/hooks/useTaskStream';
import { useBookDetails } from '@/hooks/useBookDetails';
import { useTaskMonitor } from '@/hooks/useTaskMonitor';
import { Sidebar } from '@/components/Sidebar';
import { BooksTab } from '@/components/tabs/BooksTab';
import { PlotsTab } from '@/components/tabs/PlotsTab';
import { WriteTab } from '@/components/tabs/WriteTab';
import { AnalyticsTab } from '@/components/tabs/AnalyticsTab';
import { PlanningTab } from '@/components/tabs/PlanningTab';
import { StyleLabTab } from '@/components/tabs/StyleLabTab';
import { AuditTab } from '@/components/tabs/AuditTab';
import { EasyModeDialog } from '@/components/dialogs/EasyModeDialog';
import { TaskMonitor } from '@/components/panels/TaskMonitor';
import { useAppActions } from '@/hooks/useAppActions';


export default function App() {
  // Global Settings (existing store)
  const {
    apiKey,
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
  const { easyWordCount: _easyWordCount } = useEasyModeStore();

  // ----- Local UI/cached (analytics-specific) state kept in App -----

   const [_loading, _setLoading] = React.useState<boolean>(false);

   // Book details loading delegated to useBookDetails hook (Step 12)
   const { loadBookDetails } = useBookDetails(selectedBook?.id ?? null, activeTab);

   // ----- Refs ----
   const selectedBookRef = useRef(selectedBook);
   selectedBookRef.current = selectedBook;

   // Task monitoring (log scroll + stop) delegated to useTaskMonitor hook (Step 14)
   const { logEndRef, handleStopTask } = useTaskMonitor();

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
   const handleTaskStatus = useCallback((status: any) => {
     setTaskStatus(status);
   }, [setTaskStatus]);

   const handleTaskComplete = useCallback((status: any) => {
     setActiveTaskId(null);
     const book = selectedBookRef.current;
     if (book) loadBookDetails(book.id);
     if (status.error) {
       toast.error(`タスクエラーが発生しました: ${status.error}`);
     } else {
       toast.success('バックグラウンドタスクが正常に完了しました！');
     }
   }, [setActiveTaskId, loadBookDetails]);

   const handleTaskError = useCallback((error: any) => {
     console.error('Task stream connection error:', error);
   }, []);

   useTaskStream(activeTaskId, {
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
  } = useAppActions(_setLoading);

  return (
    <HealthGate>
      <div className="flex w-full min-h-screen bg-[var(--bg-main)]">

      <Sidebar />

      {/* MAIN MAIN CONTENT CONTAINER */}
      <main style={{ flex: 1, padding: '2.5rem', display: 'flex', flexDirection: 'column', height: '100vh', overflowY: 'auto' }}>

        {/* API STATUS BAR */}
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem', borderBottom: '1px solid var(--border)', paddingBottom: '1.25rem' }}>
          <div>
            <h1 style={{ fontSize: '2rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {activeTab === 'books' && '📚 作品管理・イージーモード'}
              {activeTab === 'plots' && '🗺️ ストーリープロット設計'}
              {activeTab === 'write' && '✍️ 自律的エピソード自動執筆'}
              {activeTab === 'analytics' && '📈 AI品質分析・マーケティング'}
              {activeTab === 'planning' && '📋 企画立案'}
              {activeTab === 'style-lab' && '🧬 文体ラボ'}
              {activeTab === 'audit' && '⚖️ 品質監査'}
            </h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', background: 'rgba(255, 255, 255, 0.05)', padding: '0.4rem 0.8rem', borderRadius: '20px', border: '1px solid var(--border)' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: globalError ? 'var(--accent-rose)' : 'var(--accent-emerald)', display: 'inline-block' }} />
              <span style={{ color: 'var(--text-secondary)' }}>API Status: {globalError ? 'Offline' : 'Connected'}</span>
            </div>
          </div>
        </header>

        {globalError && (
          <ErrorBanner
            message={globalError}
            onClose={() => setGlobalError(null)}
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
          <div className="animate-fade-in" style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '2rem' }}>
            {/* Left Column: Chapters browse & controls */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                <WriteTab
                  selectedBook={selectedBook}
                  handleTriggerWriting={handleTriggerWriting}
                  handleImportChapter={handleImportChapter}
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
            handlePlanGeneration={() => loadBookDetails(selectedBook?.id ?? 0)}
          />
        )}

        {/* -------------------- TAB 6: STYLE LAB -------------------- */}
        {activeTab === 'style-lab' && (
          <StyleLabTab />
        )}

        {/* -------------------- TAB 7: AUDIT -------------------- */}
        {activeTab === 'audit' && (
          <AuditTab />
        )}
      </main>

      {/* -------------------- FLOATING TASK MONITOR OVERLAY -------------------- */}
      {activeTaskId && taskStatus && (
        <TaskMonitor
          logEndRef={logEndRef}
          onStop={handleStopTask}
        />
      )}

      {/* -------------------- NEW NOVEL (EASY MODE) MODAL DIALOG -------------------- */}
      {isCreateModalOpen && (
         <EasyModeDialog
           isOpen={isCreateModalOpen}
           onClose={() => setCreateModalOpen(false)}
           onSubmit={handleCreateEasyMode}
         />
      )}
      </div>
    </HealthGate>
  );
}
