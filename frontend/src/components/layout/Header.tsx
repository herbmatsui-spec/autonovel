import { useProjectStore } from '@/store/useProjectStore';
import { useUIStore } from '@/store/useUIStore';
import { ErrorBanner } from '@/components/ui/ErrorBanner';

interface HeaderProps {
  setGlobalError: (error: string | null) => void;
}

export function Header({ setGlobalError }: HeaderProps) {
  const { activeTab } = useProjectStore();
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
            </h1>
          </div>
          <div className="flex items-center gap-[1rem]">
            <div className="flex items-center gap-[0.5rem] text-[0.8rem] bg-[rgba(255,255,255,0.05)] px-[0.8rem] py-[0.4rem] rounded-[20px] border border-[var(--border)]">
              <span className={`w-[8px] h-[8px] rounded-full inline-block ${globalError ? 'bg-[var(--accent-rose)]' : 'bg-[var(--accent-emerald)]'}`} />
              <span className="text-[var(--text-secondary)]">API Status: {globalError ? 'Offline' : 'Connected'}</span>
            </div>
          </div>
        </header>
      </main>
    </>
  );
}