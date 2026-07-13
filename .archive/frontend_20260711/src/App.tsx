import React, { useEffect, useRef } from 'react';
import { useUserSettingsStore } from './store/useUserSettingsStore';
import { useProjectStore } from './store/useProjectStore';
import { useTaskStore } from './store/useTaskStore';
import { useBookStore } from './store/useBookStore';
import { useUIStore } from './store/useUIStore';
import { useWritingStore } from './store/useWritingStore';
import { useEasyModeStore } from './store/useEasyModeStore';
import {
  getPlots,
  getChapters,
  getBible,
  getOptHistory,
  connectTaskStream,
  stopTask,
  generateEasy,
  generateEpisodes,
  expandPlots,
  critiqueOptimize,
  importChapter,
  generateMarketing,
  getExportPackageUrl,
  getPendingPatches,
  getPromptVersions,
  getNarrativeMetricsTrend,
} from './api';
import type {
  Plot,
  Chapter,
  Bible,
  OptimizationHistory,
  PendingPatch,
  PromptVersion,
  NarrativeMetricTrend,
  TaskStatus,
} from './types';
import { toast } from 'sonner';
import { ErrorBanner } from '@/components/ui/ErrorBanner';
import { useBooks } from './hooks/useBooks';
import { Sidebar } from './components/Sidebar';
import { BooksTab } from './components/tabs/BooksTab';
import { PlotsTab } from './components/tabs/PlotsTab';
import { WriteTab } from './components/tabs/WriteTab';
import { AnalyticsTab } from './components/tabs/AnalyticsTab';
import { CreateNovelModal } from './components/dialogs/CreateNovelModal';
import { TaskMonitor } from './components/panels/TaskMonitor';

export default function App() {
  // Global Settings (existing store)
  const {
    apiKey,
    temperature,
    modelType,
  } = useUserSettingsStore();

  // Project context (existing store)
  const {
    activeTab,
    setActiveTab,
  } = useProjectStore();

  // Books list state (hook handles fetch/delete only now)
  const { books, loading: booksLoading } = useBooks();

  // ----- New Zustand stores -----
  const { selectedBook, setSelectedBook, setPlots, setChapters, setBible } = useBookStore();
  const { setCreateModalOpen } = useUIStore();
  const globalError = useUIStore((s) => s.globalError);
  const setGlobalError = useUIStore((s) => s.setGlobalError);
  const isCreateModalOpen = useUIStore((s) => s.isCreateModalOpen);
  const { activeTaskId, setActiveTaskId, taskStatus, setTaskStatus } = useTaskStore();
  const {
    writeFrom,
    writeTo,
    writePassion,
    importEpNum,
    importText,
    setImportText,
    importDoRefine,
    resetImport,
  } = useWritingStore();
  const { easyWordCount } = useEasyModeStore();

  // ----- Local UI/cached (analytics-specific) state kept in App -----
  const [optHistory, setOptHistory] = React.useState<OptimizationHistory[]>([]);
  const [pendingPatches, setPendingPatches] = React.useState<PendingPatch[]>([]);
  const [promptVersions, setPromptVersions] = React.useState<PromptVersion[]>([]);
  const [metricTrend, setMetricTrend] = React.useState<NarrativeMetricTrend[]>([]);
  const [loading, setLoading] = React.useState<boolean>(false);

  // ----- Refs -----
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const logEndRef = useRef<HTMLDivElement | null>(null);

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

  // Task SSE Stream Connection Control
  useEffect(() => {
    let disconnect: (() => void) | null = null;
    if (activeTaskId) {
      disconnect = connectTaskStream(
        activeTaskId,
        (status: TaskStatus) => {
          setTaskStatus(status);
        },
        (status: TaskStatus) => {
          // Task completed or failed
          setActiveTaskId(null);
          if (selectedBook) {
            loadBookDetails(selectedBook.id);
          }
          if (status.error) {
            toast.error(`タスクエラーが発生しました: ${status.error}`);
          } else {
            toast.success('バックグラウンドタスクが正常に完了しました！');
          }
        },
        (error: any) => {
          console.error('Task stream connection error:', error);
        }
      );
    }
    return () => {
      if (disconnect) disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTaskId, selectedBook]);

  // Auto scroll task logs to bottom
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [taskStatus?.logs]);

  const loadBookDetails = async (bookId: number) => {
    try {
      if (activeTab === 'plots') {
        const data = await getPlots(bookId);
        setPlots(data);
      } else if (activeTab === 'write') {
        const chData = await getChapters(bookId);
        setChapters(chData);
        const bibleData = await getBible(bookId);
        setBible(bibleData);
      } else if (activeTab === 'analytics') {
        const histData = await getOptHistory(bookId);
        setOptHistory(histData);
        const patchesData = await getPendingPatches(bookId);
        setPendingPatches(patchesData);
        const versionsData = await getPromptVersions(bookId);
        setPromptVersions(versionsData);

        // 指標推移の取得 (デフォルトでブランチ1)
        try {
          const trendData = await getNarrativeMetricsTrend(bookId, 1);
          setMetricTrend(trendData);
        } catch (e) {
          console.error('Error loading narrative metrics:', e);
        }
      }
    } catch (err: any) {
      console.error('Error loading book details:', err);
    }
  };

  const handleStopTask = async () => {
    if (!activeTaskId) return;
    try {
      await stopTask(activeTaskId);
      setActiveTaskId(null);
      setTaskStatus(null);
      toast.success('タスクの停止要求を送信しました。');
    } catch (err: any) {
      toast.error('タスクの停止に失敗しました: ' + err.message);
    }
  };

  // Triggering actions
  const getConfig = () => ({
    temperature,
    model_type: modelType
  });

  const handleCreateEasyMode = async (e: React.FormEvent) => {
    e.preventDefault();
    // Pull latest easy-mode form values directly from the store
    const easy = useEasyModeStore.getState();
    if (!apiKey || apiKey.length < 10) {
      toast.error('有効なAPIキーを入力してください。');
      return;
    }
    try {
      setLoading(true);
      const taskId = await generateEasy({
        api_key: apiKey,
        config: getConfig(),
        genre: easy.easyGenre,
        keywords: easy.easyKeywords,
        archetype_key: easy.easyArchetype,
        target_eps: easy.easyTargetEps,
        initial_limit: 1,
        word_count: easy.easyWordCount,
        concept: easy.easyConcept,
        tone_vibe: 0.65
      });
      setActiveTaskId(taskId);
      setCreateModalOpen(false);
    } catch (err: any) {
      toast.error('自動生成タスクの起動に失敗しました: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerWriting = async () => {
    if (!selectedBook) return;
    if (!apiKey) {
      toast.warning('APIキーを入力してください。');
      return;
    }
    try {
      const taskId = await generateEpisodes({
        api_key: apiKey,
        config: getConfig(),
        book_id: selectedBook.id,
        write_from: writeFrom,
        write_to: writeTo,
        passion: writePassion,
        word_count: easyWordCount,
        do_refine: true,
        env_state: {},
        pipeline_mode: true
      });
      setActiveTaskId(taskId);
    } catch (err: any) {
      toast.error('執筆タスクの起動に失敗しました: ' + err.message);
    }
  };

  const handleExpandPlots = async () => {
    if (!selectedBook) return;
    if (!apiKey) {
      toast.warning('APIキーを入力してください。');
      return;
    }
    try {
      const taskId = await expandPlots({
        api_key: apiKey,
        config: getConfig(),
        book_id: selectedBook.id,
        gen_from: 1,
        gen_to: selectedBook.target_eps
      });
      setActiveTaskId(taskId);
    } catch (err: any) {
      toast.error('プロット拡張タスクの起動に失敗しました: ' + err.message);
    }
  };

  const handleCritiqueOptimize = async () => {
    if (!selectedBook) return;
    if (!apiKey) {
      toast.warning('APIキーを入力してください。');
      return;
    }
    try {
      const taskId = await critiqueOptimize({
        api_key: apiKey,
        config: getConfig(),
        book_id: selectedBook.id
      });
      setActiveTaskId(taskId);
    } catch (err: any) {
      setGlobalError('品質分析タスクの起動に失敗しました: ' + err.message);
    }
  };

  const handleImportChapter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBook) return;
    if (!apiKey) {
      toast.warning('APIキーを入力してください。');
      return;
    }
    try {
      setLoading(true);
      await importChapter({
        api_key: apiKey,
        book_id: selectedBook.id,
        ep_num: importEpNum,
        import_text: importText,
        do_refine: importDoRefine
      });
      toast.success('エピソードのインポートに成功しました。');
      resetImport();
      loadBookDetails(selectedBook.id);
    } catch (err: any) {
      setGlobalError('インポートに失敗しました: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateMarketing = async () => {
    if (!selectedBook) return;
    if (!apiKey) {
      toast.warning('APIキーを入力してください。');
      return;
    }
    try {
      setLoading(true);
      await generateMarketing({
        api_key: apiKey,
        book_id: selectedBook.id,
        latest_ep: (useBookStore.getState().chapters.length) || selectedBook.target_eps
      });
      toast.success('マーケティングパッケージの生成が完了しました！');
      loadBookDetails(selectedBook.id);
    } catch (err: any) {
      setGlobalError('マーケティング生成に失敗しました: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', width: '100%', minHeight: '100vh', background: 'var(--bg-main)' }}>

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
            loadBookDetails={loadBookDetails}
            activeTaskId={activeTaskId}
          />
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
        <CreateNovelModal
          onSubmit={handleCreateEasyMode}
        />
      )}
    </div>
  );
}
