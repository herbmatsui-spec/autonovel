import React from 'react';
import { toast } from 'sonner';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { useEasyModeStore } from '@/store/useEasyModeStore';
import { useProjectStore } from '@/store/useProjectStore';
import { useBookStore } from '@/store/useBookStore';
import { useUIStore } from '@/store/useUIStore';
import { useWritingStore } from '@/store/useWritingStore';
import { useTaskStore } from '@/store/useTaskStore';
import {
  generateEasy,
  generateEpisodes,
  expandPlots,
  critiqueOptimize,
  importChapter,
  generateMarketing,
  getPlots,
  getChapters,
  getBible,
  getOptHistory,
  getPendingPatches,
  getPromptVersions,
  getNarrativeMetricsTrend,
  stopTask,
} from '@/api';
import type { EasyModeParams } from '@/types';

/**
 * Hook that encapsulates all action handlers previously defined in App.tsx.
 * It receives the `setLoading` function from the component (App) to manage the
 * local loading spinner, and returns the same handler signatures for direct use
 * in the component.
 */
export function useAppActions(setLoading: (b: boolean) => void) {
  // Global settings
  const { apiKey, temperature, modelType } = useUserSettingsStore();

  // Project / tab state
  const { activeTab, setActiveTab } = useProjectStore();

  // Book store (selected book, plots, chapters, bible)
  const {
    selectedBook,
    setSelectedBook,
    setPlots,
    setChapters,
    setBible,
    chapters,
    bible,
    plots,
  } = useBookStore();

  // UI store (modal open/close, global error)
  const { setCreateModalOpen, setGlobalError, setOptHistory, setPendingPatches, setPromptVersions, setMetricTrend } = useUIStore();
  const { easyWordCount } = useEasyModeStore();

  // Writing store (writing params & import form)
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
    resetImport,
  } = useWritingStore();

  // Task store (active task id & status)
  const { setActiveTaskId, activeTaskId, setTaskStatus, taskStatus } = useTaskStore();

  const getConfig = () => ({
    temperature,
    model_type: modelType,
  });

  // ---------- Handlers ----------
  const handleCreateEasyMode = async (_params: EasyModeParams) => {
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
        tone_vibe: 0.65,
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
        pipeline_mode: true,
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
        gen_to: selectedBook.target_eps,
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
        book_id: selectedBook.id,
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
        do_refine: importDoRefine,
      });
      toast.success('エピソードのインポートに成功しました。');
      resetImport();
      await loadBookDetails(selectedBook.id);
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
        latest_ep: (useBookStore.getState().chapters.length) || selectedBook.target_eps,
      });
      toast.success('マーケティングパッケージの生成が完了しました！');
      await loadBookDetails(selectedBook.id);
    } catch (err: any) {
      setGlobalError('マーケティング生成に失敗しました: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

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

  return {
    handleCreateEasyMode,
    handleTriggerWriting,
    handleExpandPlots,
    handleCritiqueOptimize,
    handleImportChapter,
    handleGenerateMarketing,
    loadBookDetails,
    handleStopTask,
  };
}
