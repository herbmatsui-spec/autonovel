import { useLocation } from 'react-router-dom';

interface PageHeaderProps {
  globalError: string | null;
}

export function PageHeader({ globalError }: PageHeaderProps) {
  const location = useLocation();
  const pathname = location.pathname; // e.g., "/books"
  // Remove leading slash and any trailing slash
  const activeTab = pathname.replace(/^\/|\/$/g, '') || 'landing';

  return (
    <>
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
          </h1>
        </div>
        <div className="flex items-center gap-[1rem]">
          <div className="flex items-center gap-[0.5rem] text-[0.8rem] bg-[rgba(255,255,255,0.05)] px-[0.8rem] py-[0.4rem] rounded-[20px] border border-[var(--border)]">
            <span className={`w-[8px] h-[8px] rounded-full inline-block ${globalError ? 'bg-[var(--accent-rose)]' : 'bg-[var(--accent-emerald)]'}`} />
            <span className="text-[var(--text-secondary)]">API Status: {globalError ? 'Offline' : 'Connected'}</span>
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
        </p>
      </div>
    </>
  );
}