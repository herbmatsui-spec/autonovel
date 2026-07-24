import type { TabId } from '../../store/useProjectStore';
import { useEffect, useState } from 'react';
import { checkBackendHealth } from '../../api';

interface LandingTabProps {
  setActiveTab: (tab: TabId) => void;
}

export function LandingTab({ setActiveTab }: LandingTabProps) {
  const [health, setHealth] = useState<{ status: string; database: string; worker: string } | null>(null);

  useEffect(() => {
    checkBackendHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  return (
    <div className="flex flex-col gap-6">
      {/* Hero */}
      <div className="text-center py-12 glass-sm rounded-xl">
        <h2 className="text-3xl font-extrabold gradient-text mb-3">
          ⚔️ 異世界小説生成プラットフォーム
        </h2>
        <p className="text-muted-foreground text-sm max-w-xl mx-auto">
          AI による完全自動執筆エンジン。企画・プロット・本文執筆・マーケティングまで、ワンストップで小説制作を支援します。
        </p>
        <div className="flex justify-center gap-3 mt-6">
          <button
            onClick={() => setActiveTab('easy')}
            className="px-6 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
          >
            ⚡ かんたんモードで開始
          </button>
          <button
            onClick={() => setActiveTab('planning')}
            className="px-6 py-2.5 bg-secondary text-secondary-foreground rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
          >
            📋 上級者モード
          </button>
        </div>
      </div>

      {/* システムステータス */}
      <div className="glass-sm p-5 rounded-xl">
        <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground mb-3">🔌 接続ダッシュボード</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className={`w-3 h-3 rounded-full mx-auto mb-1 ${health?.status === 'ok' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
            <div className="text-xs text-muted-foreground">API Server</div>
            <div className="text-xs font-mono mt-0.5">{health?.status ?? 'offline'}</div>
          </div>
          <div className="text-center">
            <div className={`w-3 h-3 rounded-full mx-auto mb-1 ${health?.database === 'ok' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
            <div className="text-xs text-muted-foreground">Database</div>
            <div className="text-xs font-mono mt-0.5">{health?.database ?? 'offline'}</div>
          </div>
          <div className="text-center">
            <div className={`w-3 h-3 rounded-full mx-auto mb-1 ${health?.worker === 'ok' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
            <div className="text-xs text-muted-foreground">Task Worker</div>
            <div className="text-xs font-mono mt-0.5">{health?.worker ?? 'offline'}</div>
          </div>
        </div>
      </div>

      {/* Feature Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass-sm p-5 rounded-xl text-center">
          <div className="text-3xl mb-2">📋</div>
          <h3 className="font-bold text-sm mb-1">企画立案</h3>
          <p className="text-xs text-muted-foreground">AIが市場トレンドを分析し、最適な企画書を生成します</p>
        </div>
        <div className="glass-sm p-5 rounded-xl text-center">
          <div className="text-3xl mb-2">✍️</div>
          <h3 className="font-bold text-sm mb-1">自動執筆</h3>
          <p className="text-xs text-muted-foreground">プロットに沿ってエピソードを自動生成。こだわり設定で世界観を維持</p>
        </div>
        <div className="glass-sm p-5 rounded-xl text-center">
          <div className="text-3xl mb-2">📈</div>
          <h3 className="font-bold text-sm mb-1">品質分析</h3>
          <p className="text-xs text-muted-foreground">文体DNAの解析、矛盾検知、最適化提案まで一貫サポート</p>
        </div>
      </div>

      {/* Step cards */}
      <div>
        <h3 className="text-sm font-bold mb-3 text-muted-foreground">📋 ご利用の流れ</h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="glass-sm p-4 rounded-lg text-center text-xs">
            <div className="text-2xl mb-1">Step 1</div>
            <h4 className="font-bold mb-0.5">APIキー設定</h4>
            <p className="text-muted-foreground">左サイドバーでGemini APIキーを入力します</p>
          </div>
          <div className="glass-sm p-4 rounded-lg text-center text-xs">
            <div className="text-2xl mb-1">Step 2</div>
            <h4 className="font-bold mb-0.5">プロット設定</h4>
            <p className="text-muted-foreground">企画を立ててプロットを生成します</p>
          </div>
          <div className="glass-sm p-4 rounded-lg text-center text-xs">
            <div className="text-2xl mb-1">Step 3</div>
            <h4 className="font-bold mb-0.5">執筆開始</h4>
            <p className="text-muted-foreground">自動生成してテキストをエクスポートします</p>
          </div>
        </div>
      </div>
    </div>
  );
}