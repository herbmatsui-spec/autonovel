import { useState } from 'react';
import { Tooltip } from '@/components/Tooltip';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { StatusMessage } from '@/components/ui/StatusMessage';
import { useBookStore } from '@/store/useBookStore';
import { useAppActions } from '@/hooks/useAppActions';

export function PlotsTab() {
  const { selectedBook, plots } = useBookStore();
  const { handleExpandPlots } = useAppActions(() => {});
  const [selectedVariant, setSelectedVariant] = useState<number>(0);

  const plotsLoading = false;
  const plotsError = null;

  if (!selectedBook) {
    return <div className="text-center py-8">作品を選択してください。</div>;
  }

  return (
    <div className="animate-fade-in flex flex-col gap-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold">プロット設計 - {selectedBook.title}</h2>
          <p className="text-xs text-muted-foreground mt-1">
            複数案を同時生成し、因果関係・引きの強さで最適案を自動選抜
          </p>
        </div>
        <Button
          variant="default"
          onClick={handleExpandPlots}
        >
          プロットを自動生成 (3案比較選抜)
        </Button>
      </div>

      {/* 複数案切り替えバー */}
      <div className="flex items-center gap-2 border-b border-border/50 pb-3">
        <span className="text-xs font-semibold text-muted-foreground mr-2">生成案:</span>
        {['案 A (選抜・最良)', '案 B', '案 C'].map((name, idx) => (
          <button
            key={idx}
            onClick={() => setSelectedVariant(idx)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              selectedVariant === idx
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'bg-muted/50 text-muted-foreground hover:bg-muted'
            }`}
          >
            {name}
            {idx === 0 && (
              <span className="ml-1.5 px-1.5 py-0.2 rounded text-[10px] bg-accent-indigo text-white font-bold">
                採用
              </span>
            )}
          </button>
        ))}
      </div>

      {plotsLoading && <LoadingState message="プロットを読み込み中..." />}
      {plotsError && <StatusMessage type="error" message="プロットの読み込みに失敗しました。" />}
      {plots.length === 0 && (
        <EmptyState
          icon="📝"
          title="まだプロットがありません"
          description="「プロットを自動生成」ボタンをクリックしてプロットを生成してください。"
        />
      )}
      {!plotsLoading && plots.length > 0 && (
        <div className="space-y-4">
          {plots.map((plot) => (
            <div key={plot.ep_num} className="border rounded-lg p-4 bg-card shadow-sm">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-semibold">エピソード {plot.ep_num}: {plot.title}</h3>
                    {plot.next_hook && (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-accent-rose/15 text-accent-rose font-medium">
                        引き: {plot.next_hook}
                      </span>
                    )}
                  </div>
                  <div className="prose prose-sm max-w-none text-muted-foreground">
                    {plot.summary}
                  </div>
                  {plot.detailed_blueprint && (
                    <p className="text-xs text-slate-400 mt-2 bg-slate-900/50 p-2 rounded">
                      {plot.detailed_blueprint}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <Tooltip
                    content="プロットの詳細情報を表示"
                    delay={500}
                  >
                    <Button variant="ghost" size="sm">
                      🔍 詳細
                    </Button>
                  </Tooltip>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default PlotsTab;