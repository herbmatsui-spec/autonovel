import { useLocation } from 'react-router-dom';
import { useUIStore } from '@/store/useUIStore';
import { ErrorBanner } from '@/components/ui/ErrorBanner';

interface HeaderProps {
  setGlobalError: (error: string | null) => void;
}

export function Header({ setGlobalError }: HeaderProps) {
  const location = useLocation();
  const pathname = location.pathname; // e.g., "/books"
  // Remove leading slash and any trailing slash
  const activeTab = pathname.replace(/^\/|\/$/g, '') || 'landing';
  const { globalError } = useUIStore();

  return (
    <>
      {globalError && (
        <ErrorBanner
          message={globalError}
          onClose={() => setGlobalError(null)}
        />
      )}
      {/* MAIN MAIN CONTENT CONTAINER */}
      <main className="flex flex-col h-[100vh] p-[2.5rem] overflow-auto">
        {/* API STATUS BAR */}
        <header className="flex justify-between items-center mb-[2.5rem] border-b pb-[1.25rem] border-[var(--border)]">
          <div>
            <h1 className="text-[2rem] flex items-center gap-[0.75rem]">
              {activeTab === 'landing' && '���🚀 ホーム・ダッシュボード'}
              {activeTab === 'books' && '���📚 作品管理・イージー�ーモード'}
              {activeTab === 'plots' && '���🗺��️ ストーリープロット設計'}
              {activeTab === 'write' && '��✍��️ 自律的エピソード自動�執�筆'}
              {activeTab === 'analytics' && '���📈 AI品質分�析・マーケティング'}
              {activeTab === 'planning' && '���📋 企画立案'}
              {activeTab === 'style-lab' && '���🧬 文体ラボ'}
              {activeTab === 'audit' && '��⚖��️ � 品質監�査'}
              {activeTab === 'strategy' && '���📈 戦略分析'}
              {activeTab === 'monitor' && '���📡 進捗モニター'}
              {activeTab === 'import' && '���📥 インポート'}
              {activeTab === 'easy' && '���🎪 イージーモード'}
              {!activeTab && '��� 不明なタブ'}
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xs">API:</span>
              <span className="text-xs font-mono">
                {/* TODO: API status indicator */}
                ●
              </span>
            </div>
          </div>
        </header>
        {/* PAGE TITLE */}
        <div className="mb-4">
          <h2 className="text-xl font-bold mb-2">
            {activeTab === 'landing' && 'ホーム'}
            {activeTab === 'books' && '作品一覧'}
            {activeTab === 'plots' && 'プロット設計'}
            {activeTab === 'write' && '執筆画面'}
            {activeTab === 'analytics' && '品質・販促分析'}
            {activeTab === 'planning' && '企画立案'}
            {activeTab === 'style-lab' && '文体ラボ'}
            {activeTab === 'audit' && '品質監査'}
            {activeTab === 'strategy' && '戦略分析'}
            {activeTab === 'monitor' && '進捗モニター'}
            {activeTab === 'import' && 'インポート'}
            {activeTab === 'easy' && 'イージーモード'}
          </h2>
          <p className="text-sm text-muted-foreground">
            {activeTab === 'landing' && 'AIがあなたのストーリーを紡ぎ出す'}
            {activeTab === 'books' && '作品の作成・編集・管理を行います'}
            {activeTab === 'plots' && 'プロットを生成・編集・分析します'}
            {activeTab === 'write' && 'エピソードを執筆・推敲・完成させます'}
            {activeTab === 'analytics' && '品質を評価し、販促素材を生成します'}
            {activeTab === 'planning' && 'ストーリーの企画・構造を設計します'}
            {activeTab === 'style-lab' && '文体を分析・調整・統一します'}
            {activeTab === 'audit' && '品質を監査・改善点を提案します'}
            {activeTab === 'strategy' && 'マーケティング戦略を立案します'}
            {activeTab === 'monitor' && 'バックグラウンドタスクの進行状況を監視します'}
            {activeTab === 'import' && '既存作品をインポートします'}
            {activeTab === 'easy' && 'イージーモードで簡単に作品を作成します'}
          </p>
        </div>
        {/* PAGE CONTENT (OUTLET) */}
        <div className="flex-1 overflow-auto">
          {/* The outlet is rendered in AppLayout, so we don't render anything here */}
        </div>
      </main>
    </>
  );
}