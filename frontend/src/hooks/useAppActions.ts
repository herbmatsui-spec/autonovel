import React from 'react';
import { toast } from 'sonner';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { useEasyModeStore } from '@/store/useEasyModeStore';
import { useProjectStore } from '@/store/useProjectStore';
import { useBookStore } from '@/store/useBookStore';
import { useUIStore } from '@/store/useUIStore';
import { useWritingStore } from '@/store/useWritingStore';
import { useTaskStore } from '@/store/useTaskStore';
import { useBookDetails } from './useBookDetails';
import {
  generateEasy,
  generateEpisodes,
  expandPlots,
  critiqueOptimize,
  importChapter,
  generateMarketing,
  stopTask,
  refineErotic,
} from '@/api';
import { useLocation } from 'react-router-dom';

export function useAppActions(setLoading: (b: boolean) => void) {
  const { apiKey, temperature, modelType } = useUserSettingsStore();
  const { selectedBook } = useBookStore();
  const { setCreateModalOpen, setGlobalError } = useUIStore();
  const { easyWordCount } = useEasyModeStore();
  const {
    writeFrom,
    writeTo,
    writePassion,
    importEpNum,
    importText,
    importDoRefine,
    resetImport,
    wordCount,
  } = useWritingStore();
  const { setError: setWritingError } = useWritingStore();
  const { setActiveTaskId, activeTaskId, setTaskStatus } = useTaskStore();
  const location = useLocation();
  const pathname = location.pathname; // e.g., "/books"
  const activeTab = pathname.replace(/^\/|\/$/g, '') || 'landing';
  const { loadBookDetails } = useBookDetails(selectedBook?.id ?? null);

  const getConfig = () => ({
    temperature,
    model_type: modelType,
  });

  // ---------- Handlers ----------
  const handleCreateEasyMode = async (): Promise<void> => {
    const easy = useEasyModeStore.getState();
    if (!apiKey || apiKey.length < 10) {
      toast.error('有効なAPIキーを入力してください。');
      return;
    }
    try {
      setLoading(true);
      const taskId = await generateEasy({
        config: getConfig(),
        genre: easy.easyGenre,
        keywords: easy.easyKeywords,
        archetype_key: easy.easyArchetype,
        style_key: easy.easyStyleKey,
        target_eps: easy.easyTargetEps,
        initial_limit: 1,
        word_count: easy.easyWordCount,
        concept: easy.easyConcept,
        tone_vibe: 0.65,
        enable_erotic: easy.enableErotic,
        erotic_intensity: easy.eroticIntensity,
      }, apiKey);
      setActiveTaskId(taskId);
      setCreateModalOpen(false);
      toast.success('生成を開始しました！右下のモニターで進捗を確認でき、完成した小説は「作品一覧」に表示されます。');
    } catch (err: unknown) {
      toast.error('自動生成タスクの起動に失敗しました: ' + (err instanceof Error ? err.message : String(err)));
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
        config: getConfig(),
        book_id: selectedBook.id,
        write_from: writeFrom,
        write_to: writeTo,
        passion: writePassion,
        word_count: easyWordCount || wordCount,
        do_refine: true,
        env_state: {},
        pipeline_mode: true,
      }, apiKey);
      setActiveTaskId(taskId);
      setWritingError(null);
    } catch (err: unknown) {
      const msg = '執筆タスクの起動に失敗しました: ' + (err instanceof Error ? err.message : String(err));
      toast.error(msg);
      setWritingError(msg);
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
        config: getConfig(),
        book_id: selectedBook.id,
        gen_from: 1,
        gen_to: selectedBook.target_eps,
      }, apiKey);
      setActiveTaskId(taskId);
    } catch (err: unknown) {
      toast.error('プロット拡張タスクの起動に失敗しました: ' + (err instanceof Error ? err.message : String(err)));
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
        config: getConfig(),
        book_id: selectedBook.id,
      }, apiKey);
      setActiveTaskId(taskId);
    } catch (err: unknown) {
      const msg = '品質分析タスクの起動に失敗しました: ' + (err instanceof Error ? err.message : String(err));
      setGlobalError(msg);
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
        book_id: selectedBook.id,
        ep_num: importEpNum,
        import_text: importText,
        do_refine: importDoRefine,
      }, apiKey);
      toast.success('エピソードのインポートに成功しました。');
      resetImport();
      setWritingError(null);
      await loadBookDetails(selectedBook.id);
    } catch (err: unknown) {
      const msg = 'インポートに失敗しました: ' + (err instanceof Error ? err.message : String(err));
      setGlobalError(msg);
      setWritingError(msg);
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
        book_id: selectedBook.id,
        latest_ep: (useBookStore.getState().chapters.length) || selectedBook.target_eps,
      }, apiKey);
      toast.success('マーケティングパッケージの生成が完了しました！');
      await loadBookDetails(selectedBook.id);
    } catch (err: unknown) {
      setGlobalError('マーケティング生成に失敗しました: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  };

  const handleStopTask = async () => {
    if (!activeTaskId) return;
    try {
      await stopTask(activeTaskId);
      setActiveTaskId(null);
      setTaskStatus(null);
      toast.success('タスクの停止要求を送信しました。');
    } catch (err: unknown) {
      toast.error('タスクの停止に失敗しました: ' + (err instanceof Error ? err.message : String(err)));
    }
  };

const handleRefineErotic = async (params: { intensity: number; platform_preset: string }) => {
    if (!selectedBook) return;
    if (!apiKey) {
      toast.warning('APIキーを入力してください。');
      return;
    }
    try {
      setLoading(true);
      await refineErotic({
        book_id: selectedBook.id,
        ...params,
      }, apiKey);
      toast.success('官能表現の洗練が完了しました。');
    } catch (err: unknown) {
      toast.error('官能表現の洗練に失敗しました: ' + (err instanceof Error ? err.message : String(err)));
    } finally {
      setLoading(false);
    }
  };

  return {
    handleCreateEasyMode,
    handleTriggerWriting,
    handleExpandPlots,
    handleCritiqueOptimize,
    handleImportChapter,
    handleGenerateMarketing,
    handleRefineErotic,
    loadBookDetails,
    handleStopTask,
  };
}