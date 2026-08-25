import { useState, useEffect, useCallback } from 'react';
import type { Book, Chapter, Plot } from '../../types';
import { getChapters, getPlots } from '../../api';
import { useBookStore } from '@/store/useBookStore';
import { Button } from '@/components/ui/button';

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="glass-sm p-4 rounded-lg text-center">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="text-2xl font-bold font-mono">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  );
}

export default function MonitorTab() {
  const { selectedBook } = useBookStore();
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [plots, setPlots] = useState<Plot[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const loadData = useCallback(async () => {
    if (!selectedBook?.id) return;
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
    }
  }, [selectedBook?.id]);

  useEffect(() => {
    loadData();
    // Set up an interval to refresh every 30 seconds
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  if (!selectedBook) {
    return <div className="text-center py-8">作品を選択してください。</div>;
  }

  const completedChapters = chapters.filter(ch => ch.status === 'completed').length;
  const totalChapters = chapters.length;
  const completionRate = totalChapters > 0 ? (completedChapters / totalChapters) * 100 : 0;

  return (
    <div className="animate-fade-in flex flex-col gap-6">
      <h2 className="text-xl font-bold">進捗モニター - {selectedBook.title}</h2>
      <div className="grid gap-4 sm:grid-cols-3">
        <MetricCard
          label="全エピソード数"
          value={totalChapters}
          sub="目標: {selectedBook.target_eps}話"
        />
        <MetricCard
          label="完了エピソード数"
          value={completedChapters}
        />
        <MetricCard
          label="進捗率"
          value={completionRate.toFixed(1) + '%'}
        />
        <MetricCard
          label="プロット数"
          value={plots.length}
        />
        <MetricCard
          label="最終更新"
          value={lastUpdated.toLocaleTimeString()}
          sub={lastUpdated.toLocaleDateString()}
        />
      </div>
      <div className="border rounded-lg p-4">
        <h3 className="font-semibold mb-2">エピソードステータス</h3>
        {chapters.length === 0 ? (
          <p className="text-sm text-muted-foreground">エピソードデータはまだありません。</p>
        ) : (
          <div className="space-y-2">
            {chapters.map((ch) => (
              <div key={ch.id} className="flex justify-between items-center px-3 py-2 bg-[var(--muted)] rounded">
                <span className="text-sm">エピソード {ch.episode_no}: {ch.title}</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${ch.status === 'completed' ? 'bg-accent-emerald/20 text-accent-emerald' : ch.status === 'in_progress' ? 'bg-accent-amber/20 text-accent-amber' : 'bg-accent-rose/20 text-accent-rose'}`}>
                  {ch.status === 'completed' ? '完了' : ch.status === 'in_progress' ? '進行中' : '未開始'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="flex justify-end mt-4">
        <Button
          variant="outline"
          onClick={loadData}
        >
          今すぐ更新
        </Button>
      </div>
    </div>
  );
}