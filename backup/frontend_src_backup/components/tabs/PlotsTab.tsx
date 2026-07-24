import { Tooltip } from '@/components/Tooltip';
import type { Book, Plot } from '@/types';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { StatusMessage } from '@/components/ui/StatusMessage';

interface PlotsTabProps {
  selectedBook: Book;
  plots: Plot[];
  handleExpandPlots: () => void;
  plotsLoading?: boolean;
  plotsError?: string | null;
}

export function PlotsTab({
  selectedBook,
  plots,
  handleExpandPlots,
  plotsLoading = false,
  plotsError = null,
}: PlotsTabProps) {
  return (
    <div className="animate-fade-in flex flex-col gap-8">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-xl text-white">🗺️ プロットストーリーライン: {selectedBook.title}</h3>
          <p className="text-text-secondary text-sm">全エピソードの進行と感情曲線（テンション）の設定です。</p>
        </div>
        <div className="flex gap-3">
          <button className="btn btn-secondary" onClick={handleExpandPlots}>
            🔄 プロット全話自動展開
          </button>
        </div>
      </div>

      {plotsError && (
        <StatusMessage type="error" message={`プロットの読み込みに失敗しました: ${plotsError}`} />
      )}

      {plotsLoading ? (
        <LoadingState message="プロットを読み込み中..." icon="🗺️" />
      ) : plots.length === 0 ? (
        <EmptyState
          icon="🗺️"
          title="プロットデータがまだ生成されていません"
          description="「プロット全話自動展開」を実行してストーリーラインを作成してください。"
          action={{ label: 'プロットデータを初期生成する', onClick: handleExpandPlots }}
        />
      ) : (
        <div className="flex flex-col gap-4">
          {plots.map((plot) => (
            <div key={plot.ep_num} className="glass-panel p-6 flex gap-6 items-start">
              <div className="flex flex-col items-center min-w-[60px]">
                <span className="text-xs text-text-muted">EPISODE</span>
                <span className="text-3xl font-extrabold text-accent-indigo">{plot.ep_num}</span>
              </div>
              
              <div className="flex-1">
                <div className="flex gap-3 items-center mb-2">
                  <h4 className="text-white text-lg">{plot.title}</h4>
                  {plot.is_catharsis && (
                    <span className="badge badge-purple">
                      🔥 <Tooltip termKey="catharsis">カタルシス回</Tooltip>
                    </span>
                  )}
                  <span className={`badge ${
                    plot.status === 'completed'
                      ? 'border-emerald-500/20 bg-accent-emerald/15 text-accent-emerald'
                      : 'border-white/[0.08] bg-white/5 text-text-muted'
                  }`}>
                    {plot.status}
                  </span>
                </div>
                <p className="text-sm text-text-secondary leading-relaxed mb-2">
                  {plot.summary}
                </p>
                {plot.detailed_blueprint && (
                  <details className="text-xs text-text-muted cursor-pointer">
                    <summary className="py-1 font-bold">詳細プロット設計書を展開</summary>
                    <pre className="mt-2 whitespace-pre-wrap max-h-[200px]">{plot.detailed_blueprint}</pre>
                  </details>
                )}
              </div>

              <div className="w-[100px] flex flex-col items-center bg-white/[0.02] p-3 rounded-lg border border-border">
                <span className="text-[0.7rem] text-text-muted">緊張度</span>
                <span className={`text-xl font-bold ${plot.tension > 70 ? 'text-accent-rose' : 'text-accent-cyan'}`}>{plot.tension}</span>
                <div className="w-full h-1 bg-white/10 rounded-sm mt-1.5 overflow-hidden">
                  <div className={`h-full ${plot.tension > 70 ? 'bg-accent-rose' : 'bg-accent-cyan'}`} style={{ width: `${plot.tension}%` }} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
