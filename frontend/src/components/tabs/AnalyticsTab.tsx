import { Tooltip } from '@/components/Tooltip';
import type { Book, OptimizationHistory, PendingPatch, PromptVersion, NarrativeMetricTrend } from '@/types';
import { PatchReviewPanel } from '../PatchReviewPanel';
import { PromptVersionTimeline } from '../PromptVersionTimeline';
import { NarrativeGraph } from '../NarrativeGraph';

interface AnalyticsTabProps {
  selectedBook: Book;
  optHistory: OptimizationHistory[];
  pendingPatches: PendingPatch[];
  promptVersions: PromptVersion[];
  metricTrend: NarrativeMetricTrend[];
  handleCritiqueOptimize: () => void;
  handleGenerateMarketing: () => void;
  getExportPackageUrl: (bookId: number, apiKey: string) => string;
  apiKey: string;
  onRefresh: () => void;
  setActiveTab: (tab: 'books' | 'plots' | 'write' | 'analytics') => void;
}

export function AnalyticsTab({
  selectedBook,
  optHistory,
  pendingPatches,
  promptVersions,
  metricTrend,
  handleCritiqueOptimize,
  handleGenerateMarketing,
  getExportPackageUrl,
  apiKey,
  onRefresh,
  setActiveTab,
}: AnalyticsTabProps) {
  return (
    <div className="animate-fade-in flex flex-col gap-8">

      {/* Narrative Metrics Graph */}
      <div className="glass-panel p-7 h-[500px]">
        <h3 className="mb-4 text-lg font-bold">📈 物語指標推移 (Narrative Metrics Trend)</h3>
        <p className="text-secondary text-sm mb-6">
          シーンごとの緊張感、感情的充足度、謎密度を可視化します。点をクリックすると該当シーンへジャンプします（実装予定）。
        </p>
        <NarrativeGraph
          data={metricTrend}
          onSceneClick={(ep, sc) => {
            console.log(`Jump to Ep${ep} Scene${sc}`);
            setActiveTab('write');
            setTimeout(() => {
              const element = document.getElementById(`chapter-${ep}`);
              if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            }, 100);
          }}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Left: Quality Critique */}
        <div className="flex flex-col gap-8">
          <div className="glass-panel p-7">
            <h3 className="mb-2 text-base font-bold">🕵️ AI品質・<Tooltip termKey="catharsis">カタルシス</Tooltip>分析 (Critique)</h3>
            <p className="text-secondary text-sm mb-6">
              AIプロデューサーが全エピソードの応力バランス、ストレス展開、カタルシス回収の強度を分析します。
            </p>
            <button className="btn btn-primary" onClick={handleCritiqueOptimize}>
              🔍 分析エンジン起動
            </button>
          </div>

          {/* Optimization History list */}
          <div>
            <h3 className="text-xl font-bold mb-4">📜 品質監査レポート履歴</h3>
            {optHistory.length === 0 ? (
              <div className="glass-panel p-12 text-center text-muted">
                監査データがありません。
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                {optHistory.map((hist) => (
                  <div key={hist.id} className="glass-panel p-5">
                    <div className="flex justify-between text-sm text-muted mb-2">
                      <span>監査ID: #{hist.id}</span>
                      <span>{new Date(hist.created_at).toLocaleString()}</span>
                    </div>
                    <pre className="text-sm whitespace-pre-wrap max-h-[200px]">
                      {JSON.stringify(hist.report_json, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Marketing & Patch Reviews & Version Timelines */}
        <div className="flex flex-col gap-8">
          <div className="glass-panel p-7 flex flex-col gap-5">
            <h3 className="text-base font-bold">📢 マーケティングパッケージの生成</h3>
            <p className="text-secondary text-sm">
              SNS投稿用のあらすじ紹介、キャッチコピー、キャラクター設定パッケージを自動構築します。
            </p>
            <button className="btn btn-secondary w-full" onClick={handleGenerateMarketing}>
              🎁 パッケージの自動生成
            </button>

            {apiKey && (
              <a
                href={getExportPackageUrl(selectedBook.id, apiKey)}
                target="_blank"
                rel="noreferrer"
                className="btn btn-primary w-full text-center no-underline text-white"
              >
                📥 生成済みZIPパッケージのダウンロード
              </a>
            )}
          </div>

          {/* HITL Pending Patches */}
          <div className="glass-panel p-7">
            <PatchReviewPanel
              patches={pendingPatches}
              onRefresh={onRefresh}
            />
          </div>

          {/* Prompt Versions History */}
          <div className="glass-panel p-7">
            <PromptVersionTimeline
              bookId={selectedBook.id}
              versions={promptVersions}
              onRefresh={onRefresh}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
