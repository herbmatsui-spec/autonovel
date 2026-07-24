import { useState, useEffect, useCallback } from 'react';
import type { Book } from '../../types';
import { getChapters, getPlots } from '../../api';

interface MonitorTabProps {
  selectedBook: Book;
}

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="glass-sm p-4 rounded-lg text-center">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="text-2xl font-bold font-mono">{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  );
}

export function MonitorTab({ selectedBook }: MonitorTabProps) {
  const [chapters, setChapters] = useState<any[]>([]);
  const [plots, setPlots] = useState<any[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const loadData = useCallback(async () => {
    try {
      const [ch, pl] = await Promise.all([
        getChapters(selectedBook.id),
        getPlots(selectedBook.id),
      ]);
      setChapters(ch);
      setPlots(pl);
      setLastUpdated(new Date());
    } catch (e) {
      console.error('Monitor: failed to load data', e);
    }
  }, [selectedBook.id]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30_000); // 30s auto-refresh
    return () => clearInterval(interval);
  }, [loadData]);

  const totalChars = chapters.reduce((sum: number, ch: any) => sum + (ch.content?.length ?? 0), 0);
  const estimatedCost = ((totalChars / 4) * 0.00002).toFixed(4); // rough estimate
  const progressPercent = selectedBook.target_eps > 0
    ? Math.min(Math.round((chapters.length / selectedBook.target_eps) * 100), 100)
    : 0;

  const narrativeStates = ['日常', '事件発生', '葛藤', '前クライマックス', 'クライマックス', '解決'];
  const currentStateIndex = Math.min(
    Math.floor((progressPercent / 100) * (narrativeStates.length - 1)),
    narrativeStates.length - 1
  );

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-base font-bold">📡 パイプライン進捗モニター</h2>

      {/* Metric Cards */}
      <div className="grid grid-cols-3 gap-4">
        <MetricCard label="プロット進捗" value={`${plots.length}/${selectedBook.target_eps}`} sub={`${progressPercent}%`} />
        <MetricCard label="執筆量" value={`${totalChars.toLocaleString()}字`} />
        <MetricCard label="APIコスト概算" value={`$${estimatedCost}`} />
      </div>

      {/* 執筆進捗 bar */}
      <div className="glass-sm p-4 rounded-lg">
        <h4 className="text-xs font-bold mb-2">本文執筆進捗</h4>
        <div className="w-full bg-muted rounded-full h-3 overflow-hidden">
          <div
            className="bg-emerald-500 h-3 rounded-full transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          {chapters.length} / {selectedBook.target_eps} 話 ({progressPercent}%)
        </p>
      </div>

      {/* Narrative State Stepper */}
      <div className="glass-sm p-4 rounded-lg">
        <h4 className="text-xs font-bold mb-3">物語状態遷移</h4>
        <div className="flex justify-between items-center">
          {narrativeStates.map((state, i) => (
            <div key={state} className="flex flex-col items-center flex-1">
              <div
                className={`w-4 h-4 rounded-full transition-colors ${
                  i <= currentStateIndex ? 'bg-primary' : 'bg-muted-foreground/30'
                }`}
              />
              <span className={`text-2xs mt-1 text-center ${i <= currentStateIndex ? 'text-primary font-semibold' : 'text-muted-foreground'}`}>
                {state}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Writing Log */}
      <div className="glass-sm p-4 rounded-lg">
        <h4 className="text-xs font-bold mb-2">最近の執筆ログ（最新5話）</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="p-1">EP</th>
                <th className="p-1">話名</th>
                <th className="p-1">文字数</th>
                <th className="p-1">作成日</th>
              </tr>
            </thead>
            <tbody>
              {chapters.slice(-5).reverse().map((ch) => (
                <tr key={ch.ep_num} className="border-t border-border">
                  <td className="p-1 font-mono">{ch.ep_num}</td>
                  <td className="p-1">{ch.title}</td>
                  <td className="p-1 font-mono">{ch.content?.length?.toLocaleString() ?? '—'}字</td>
                  <td className="p-1 text-muted-foreground">{new Date(ch.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
              {chapters.length === 0 && <tr><td align="center" colSpan={4} className="text-muted-foreground p-2">データなし</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <p className="text-2xs text-muted-foreground text-right">
        最終更新: {lastUpdated.toLocaleTimeString()}
      </p>
    </div>
  );
}