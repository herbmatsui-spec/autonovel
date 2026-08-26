import { Tooltip } from '@/components/Tooltip';
import type { Book, OptimizationHistory, PendingPatch, PromptVersion, NarrativeMetricTrend } from '@/types';
import { PatchReviewPanel } from '../PatchReviewPanel';
import { PromptVersionTimeline } from '../PromptVersionTimeline';
import { NarrativeGraph } from '../NarrativeGraph';
import { Button } from '@/components/ui/button';
import { useBookStore } from '@/store/useBookStore';
import { useUIStore } from '@/store/useUIStore';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { useAppActions } from '@/hooks/useAppActions';
import { useBookDetails } from '@/hooks/useBookDetails';
import { useNavigate } from 'react-router-dom';

export default function AnalyticsTab() {
  const { selectedBook, optHistory, pendingPatches, promptVersions, metricTrend } = useBookStore();
  const { handleCritiqueOptimize, handleGenerateMarketing } = useAppActions((_) => {});
  const { apiKey, isExpertMode } = useUserSettingsStore();
  const navigate = useNavigate();
  const { loadBookDetails } = useBookDetails(selectedBook?.id ?? null);

  const handleRefresh = () => {
    if (selectedBook?.id) {
      loadBookDetails(selectedBook.id);
    }
  };

  const handleExport = () => {
    if (!selectedBook?.id) return;
    // We can use the getExportPackageUrl function from the api, but we don't have it here.
    // We'll just show a toast for now, or we can navigate to a export page.
    toast.info('エクスポート機能は実装中です。');
  };

  if (!selectedBook) {
    return <div className="text-center py-8">作品を選択してください。</div>;
  }

  return (
    <div className="animate-fade-in flex flex-col gap-8">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">品質＆販促分析 - {selectedBook.title}</h2>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            onClick={handleRefresh}
          >
            🔄 更新
          </Button>
          <Button
            variant="default"
            onClick={handleExport}
          >
            📦 エクスポート
          </Button>
          <Button
            variant="default"
            onClick={handleCritiqueOptimize}
          >
            🔍 品質分析実行
          </Button>
          <Button
            variant="secondary"
            onClick={handleGenerateMarketing}
          >
            📣 マーケティング生成
          </Button>
        </div>
      </div>

      {/* Optimization History (always visible) */}
      <div className="border rounded-lg p-4">
        <h3 className="font-semibold mb-2">最適化履歴</h3>
        {optHistory.length === 0 ? (
          <p className="text-sm text-muted-foreground">最適化履歴はまだありません。</p>
        ) : (
          <div className="space-y-2">
            {optHistory.map((entry, index) => (
              <div key={entry.version} className="flex justify-between items-center p-2 bg-[var(--accent)]/10 rounded">
                <span className="text-xs">バージョン {entry.version}</span>
                <span className="text-xs">{new Date(entry.timestamp).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {isExpertMode && (
        <>
          {/* Pending Patches */}
          <div className="border rounded-lg p-4">
            <h3 className="font-semibold mb-2">保留中のパッチ</h3>
            {pendingPatches.length === 0 ? (
              <p className="text-sm text-muted-foreground">保留中のパッチはありません。</p>
            ) : (
              <PatchReviewPanel
                patches={pendingPatches}
                // We don't have the onApprove and onReject functions here; we would need to implement them.
                // For now, we'll just display.
              />
            )}
          </div>

          {/* Prompt Versions */}
          <div className="border rounded-lg p-4">
            <h3 className="font-semibold mb-2">プロンプトバージョン</h3>
            {promptVersions.length === 0 ? (
              <p className="text-sm text-muted-foreground">プロンプトバージョンはまだありません。</p>
            ) : (
              <PromptVersionTimeline versions={promptVersions} />
            )}
          </div>

          {/* Narrative Graph */}
          <div className="border rounded-lg p-4">
            <h3 className="font-semibold mb-2">ナラティブグラフ</h3>
            {metricTrend.length === 0 ? (
              <p className="text-sm text-muted-foreground">ナラティブメトリクスのトレンドデータはまだありません。</p>
            ) : (
              <NarrativeGraph trendData={metricTrend} />
            )}
          </div>
        </>
      )}
    </div>
  );
}