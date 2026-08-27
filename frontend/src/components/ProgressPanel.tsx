import { useCallback, useEffect, useState } from 'react';
import { useBookStore } from '@/store/useBookStore';
import { useAppActions } from '@/hooks/useAppActions';
import { getChapters, getPlots } from '@/api';
import type { Chapter, Plot } from '@/types';
import { AgentDashboard } from './AgentDashboard';

export function ProgressPanel() {
  const { selectedBook } = useBookStore();
  const { handleStopTask } = useAppActions(() => {});
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [plots, setPlots] = useState<Plot[]>([]);

  const fetchData = useCallback(async () => {
    if (!selectedBook?.id) return;
    try {
      const [ch, pl] = await Promise.all([
        getChapters(selectedBook.id),
        getPlots(selectedBook.id),
      ]);
      setChapters(ch || []);
      setPlots(pl || []);
    } catch (err) {
      console.error('Failed to load monitoring data:', err);
    }
  }, [selectedBook?.id]);

  // Fetch initial data and set up interval to refresh every 30 seconds
  useEffect(() => {
    if (selectedBook?.id) {
      fetchData();
      const interval = setInterval(fetchData, 30000);
      return () => clearInterval(interval);
    }
  }, [selectedBook?.id, fetchData]);

  if (!selectedBook) {
    return (
      <div className="w-96 border-l border-slate-800 bg-slate-950/80 p-6 flex items-center justify-center text-slate-500 text-sm">
        <p>本を選択してください。</p>
      </div>
    );
  }

  const completedChapters = chapters.length;
  const targetEps = selectedBook.target_eps || Math.max(plots.length, chapters.length, 1);
  const completionRate = targetEps > 0 ? Math.min((completedChapters / targetEps) * 100, 100) : 0;

  return (
    <div className="w-96 border-l border-slate-800 bg-slate-950/80 flex flex-col h-full overflow-y-auto p-4 space-y-4">
      {/* リアルタイム自律エージェントモニター (LangGraph SSE) */}
      <AgentDashboard />

      {/* 原稿統計 */}
      <div className="grid grid-cols-3 gap-2 bg-slate-900/60 border border-slate-800 p-3 rounded-lg text-center">
        <div>
          <p className="text-[10px] text-slate-400">執筆進捗</p>
          <p className="text-base font-bold font-mono text-indigo-400">{completionRate.toFixed(0)}%</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-400">完了話数</p>
          <p className="text-base font-bold font-mono text-emerald-400">
            {completedChapters}/{targetEps}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-slate-400">プロット数</p>
          <p className="text-base font-bold font-mono text-cyan-400">{plots.length}</p>
        </div>
      </div>

      {/* タスク停止操作 */}
      <div className="pt-2">
        <button
          onClick={handleStopTask}
          className="w-full py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-lg text-xs font-semibold transition-all"
        >
          現在実行中のAIタスクを緊急停止
        </button>
      </div>
    </div>
  );
}