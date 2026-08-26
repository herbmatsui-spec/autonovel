import React, { useEffect, useState } from 'react';
import { useBookStore } from '@/store/useBookStore';
import { useAppActions } from '@/hooks/useAppActions';
import { getChapters, getPlots } from '@/api';
import { toast } from 'sonner';

export default function ProgressPanel() {
  const { selectedBook } = useBookStore();
  const { handleStopTask } = useAppActions((_) => {});
  const [chapters, setChapters] = useState([]);
  const [plots, setPlots] = useState([]);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [log, setLog] = useState<string[]>([]);
  const [isFetching, setIsFetching] = useState(false);

  // Fetch data when selectedBook changes
  useEffect(() => {
    if (selectedBook?.id) {
      fetchData();
    }
  }, [selectedBook?.id]);

  const fetchData = async () => {
    if (!selectedBook?.id) return;
    setIsFetching(true);
    try {
      const [ch, pl] = await Promise.all([
        getChapters(selectedBook.id),
        getPlots(selectedBook.id),
      ]);
      setChapters(ch);
      setPlots(pl);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to load monitoring data:', err);
    } finally {
      setIsFetching(false);
    }
  };

  // Set up interval to refresh every 30 seconds
  useEffect(() => {
    if (selectedBook?.id) {
      fetchData();
      const interval = setInterval(fetchData, 30000);
      return () => clearInterval(interval);
    }
  }, [selectedBook?.id]);

  // Task log subscription (we need to subscribe to task stream to get logs)
  // For simplicity, we'll just show a placeholder; we can later integrate useTaskStream.
  // We'll skip log for now and just show a placeholder.

  if (!selectedBook) {
    return (
      <div className="text-center py-8">
        <p>本を選択してください。</p>
      </div>
    );
  }

  const completedChapters = chapters.filter((ch) => ch.status === 'completed').length;
  const totalChapters = chapters.length;
  const completionRate = totalChapters > 0 ? (completedChapters / totalChapters) * 100 : 0;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="text-center">
          <p className="text-xs text-muted-foreground">総合進捗</p>
          <p className="text-2xl font-bold font-mono">{completionRate.toFixed(1)}%</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-muted-foreground">完了エピソード</p>
          <p className="text-2xl font-bold font-mono">
            {completedChapters} / {totalChapters}
          </p>
        </div>
        <div className="text-center">
          <p className="text-xs text-muted-foreground">プロット数</p>
          <p className="text-2xl font-bold font-mono">{plots.length}</p>
        </div>
      </div>

      {/* Task log and controls */}
      <div className="border rounded-lg p-4">
        <h3 className="font-semibold mb-2">タスクログ</h3>
        {isFetching ? (
          <p className="text-sm text-muted-foreground">データ取得中...</p>
        ) : (
          <div className="space-y-2">
            <p className="text-sm">{log.length > 0 ? log.join('\n') : 'ログがありません。'}</p>
            <button
              onClick={handleStopTask}
              className="w-full px-4 py-2 bg-[var(--accent-rose)]/20 text-[var(--accent-rose)] rounded hover:bg-[var(--accent-rose)]/30"
            >
              タスクを停止
            </button>
          </div>
        )}
      </div>
    </div>
  );
}