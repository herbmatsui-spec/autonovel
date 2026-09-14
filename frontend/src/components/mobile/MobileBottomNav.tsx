import React from 'react';

interface MobileBottomNavProps {
  activeTab: 'books' | 'plots' | 'writing' | 'settings';
  onTabChange: (tab: 'books' | 'plots' | 'writing' | 'settings') => void;
}

export const MobileBottomNav: React.FC<MobileBottomNavProps> = ({ activeTab, onTabChange }) => {
  const tabs = [
    { id: 'books', label: '作品一覧', icon: '📚' },
    { id: 'plots', label: 'プロット', icon: '🗺️' },
    { id: 'writing', label: '執筆・推敲', icon: '✍️' },
    { id: 'settings', label: '設定', icon: '⚙️' },
  ] as const;

  return (
    <nav aria-label="モバイルナビゲーション" className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-slate-950/95 backdrop-blur-md border-t border-slate-800/80 px-4 pb-[var(--safe-bottom)] shadow-2xl">
      <div className="flex items-center justify-around h-[var(--mobile-nav-height)]">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`flex flex-col items-center justify-center flex-1 h-full touch-target transition-colors ${
                isActive ? 'text-indigo-400 font-bold' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="text-lg mb-0.5">{tab.icon}</span>
              <span className="text-[10px] tracking-tight">{tab.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
