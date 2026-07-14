import React from 'react';
import { Button } from '@/components/ui/button';
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
  setActiveTab: (tab: string) => void;
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
      <div className="glass-panel" style={{ padding: '1.75rem', height: '500px' }}>
        <h3 style={{ marginBottom: '1rem' }}>📈 物語指標推移 (Narrative Metrics Trend)</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <div className="glass-panel" style={{ padding: '1.75rem' }}>
            <h3 style={{ marginBottom: '0.5rem' }}>🕵️ AI品質・<Tooltip termKey="catharsis">カタルシス</Tooltip>分析 (Critique)</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.5rem' }}>
              AIプロデューサーが全エピソードの応力バランス、ストレス展開、カタルシス回収の強度を分析します。
            </p>
            <button className="btn btn-primary" onClick={handleCritiqueOptimize}>
              🔍 分析エンジン起動
            </button>
          </div>

          {/* Optimization History list */}
          <div>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '1rem' }}>📜 品質監査レポート履歴</h3>
            {optHistory.length === 0 ? (
              <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                監査データがありません。
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {optHistory.map((hist) => (
                  <div key={hist.id} className="glass-panel" style={{ padding: '1.25rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                      <span>監査ID: #{hist.id}</span>
                      <span>{new Date(hist.created_at).toLocaleString()}</span>
                    </div>
                    <pre style={{ fontSize: '0.8rem', whiteSpace: 'pre-wrap', maxHeight: '200px' }}>
                      {JSON.stringify(hist.report_json, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Marketing & Patch Reviews & Version Timelines */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <div className="glass-panel" style={{ padding: '1.75rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <h3>📢 マーケティングパッケージの生成</h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              SNS投稿用のあらすじ紹介、キャッチコピー、キャラクター設定パッケージを自動構築します。
            </p>
            <button className="btn btn-secondary" onClick={handleGenerateMarketing} style={{ width: '100%' }}>
              🎁 パッケージの自動生成
            </button>
            
            {apiKey && (
              <a 
                href={getExportPackageUrl(selectedBook.id, apiKey)} 
                target="_blank" 
                rel="noreferrer"
                className="btn btn-primary"
                style={{ textDecoration: 'none', color: '#fff', width: '100%', textAlign: 'center' }}
              >
                📥 生成済みZIPパッケージのダウンロード
              </a>
            )}
          </div>

          {/* HITL Pending Patches */}
          <div className="glass-panel" style={{ padding: '1.75rem' }}>
            <PatchReviewPanel
              bookId={selectedBook.id}
              patches={pendingPatches}
              onRefresh={onRefresh}
            />
          </div>

          {/* Prompt Versions History */}
          <div className="glass-panel" style={{ padding: '1.75rem' }}>
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
