import React, { useState } from 'react';
import { ViralTitleGenerator } from './ViralTitleGenerator';
import { CatchphraseCard } from './CatchphraseCard';

/**
 * Step 22: マーケティングダッシュボードパネル。
 *
 * タイトル生成（ViralTitleGenerator）の下に
 * 「✨ カクヨム用35文字キャッチコピー生成」セクションを統合する。
 */

interface MarketingPanelProps {
  /** 企画設定（ジャンル・コンセプト等のテキスト）。未指定時はタイトル生成の入力から流用 */
  projectSettings?: string;
  onToast?: (msg: string, type: 'success' | 'error' | 'info') => void;
}

type TabKey = 'titles' | 'catchphrase';

export const MarketingPanel: React.FC<MarketingPanelProps> = ({
  projectSettings = '',
  onToast,
}) => {
  const [activeTab, setActiveTab] = useState<TabKey>('titles');
  // タイトル生成の核となる設定をキャッチコピー生成に流用するための状態
  const [derivedSettings, setDerivedSettings] = useState('');
  const effectiveSettings = projectSettings || derivedSettings;

  const handleSelectTitle = (title: string, synopsis?: string) => {
    // 採用されたタイトルとあらすじをキャッチコピー生成の入力に反映
    setDerivedSettings(`採用タイトル: ${title}\nあらすじ: ${synopsis ?? ''}`);
    onToast?.('キャッチコピー生成に入力を反映しました', 'info');
  };

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'titles', label: '🎯 タイトル生成' },
    { key: 'catchphrase', label: '✨ キャッチコピー生成（35字）' },
  ];

  return (
    <div className="space-y-4" data-testid="marketing-panel">
      {/* Step 22: タブ切り替え */}
      <div className="flex items-center gap-2 border-b border-slate-700 pb-2" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={activeTab === tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-1.5 text-sm rounded transition-colors ${
              activeTab === tab.key
                ? 'bg-slate-700 text-white font-semibold'
                : 'bg-transparent text-slate-400 hover:text-slate-200'
            }`}
            data-testid={`marketing-tab-${tab.key}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* タブコンテンツ */}
      <div role="tabpanel">
        {activeTab === 'titles' && (
          <div className="space-y-4">
            <ViralTitleGenerator
              onSelectTitle={handleSelectTitle}
              onToast={onToast}
            />
            {/* タイトル生成の下にキャッチコピーセクションも常時表示（タブ統合） */}
            <div className="p-4 bg-slate-800/40 border border-slate-700 rounded">
              <CatchphraseCard projectSettings={effectiveSettings} />
            </div>
          </div>
        )}
        {activeTab === 'catchphrase' && (
          <div className="p-4 bg-slate-800/40 border border-slate-700 rounded">
            <CatchphraseCard projectSettings={effectiveSettings} />
          </div>
        )}
      </div>
    </div>
  );
};

export default MarketingPanel;
