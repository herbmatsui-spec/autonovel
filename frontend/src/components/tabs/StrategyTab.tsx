import { useState, useEffect } from 'react';
import type { Book, Plot, Bible } from '../../types';
import { getPlots, getBible } from '../../api';
import { useBookStore } from '@/store/useBookStore';
import { Button } from '@/components/ui/button';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';

function SubTabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors ${
        active ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground hover:opacity-80'
      }`}
    >
      {children}
    </button>
  );
}

export default function StrategyTab() {
  const { selectedBook } = useBookStore();
  const { isExpertMode } = useUserSettingsStore();
  const [activeSubTab, setActiveSubTab] = useState(0);
  const [plots, setPlots] = useState<Plot[]>([]);
  const [bible, setBible] = useState<Bible | null>(null);

  useEffect(() => {
    Promise.all([
      getPlots(selectedBook.id),
      getBible(selectedBook.id),
    ]).then(([p, b]) => {
      setPlots(p);
      setBible(b);
    }).catch(console.error);
  }, [selectedBook.id]);

  const subTabs = [
    { title: '📉 感情曲線' },
    { title: '🚨 矛盾・整合性' },
    { title: '🎆 ストレスログ' },
    { title: '📄 商用ピッチ' },
    { title: '🤖 自己最適化' },
  ];

  const isTabExpertOnly = (index: number) => index >= 2; // indices 2,3,4 are expert-only

  const renderSubTab = () => {
    // If active tab is hidden and not expert, redirect to first visible tab (index 0)
    if (!isExpertMode && isTabExpertOnly(activeSubTab)) {
      setActiveSubTab(0);
    }
    switch (activeSubTab) {
      case 0:
        return (
          <div className="space-y-4">
            <h4 className="text-sm font-bold">感情曲線</h4>
            <p className="text-xs text-muted-foreground">各エピソードの緊張感・ストレス値の推移</p>
            <div className="glass-sm p-4 rounded-lg">
              <div className="text-xs font-mono space-y-1">
                {plots.map((p) => (
                  <div key={p.ep_num} className="flex justify-between">
                    <span>EP {p.ep_num}: {p.title}</span>
                    <span className="font-semibold">緊張度: {p.tension?.toFixed(1) ?? '—'}</span>
                  </div>
                ))}
                {plots.length === 0 && <p className="text-muted-foreground">読み込み中…</p>}
              </div>
            </div>
          </div>
        );
      case 1:
        return (
          <div className="space-y-4">
            <h4 className="text-sm font-bold">矛盾・整合性チェック</h4>
            <div className="glass-sm p-4 rounded-lg">
              <h5 className="text-xs font-bold mb-2">📖 長期記憶管理</h5>
              <textarea
                className="w-full h-32 text-xs p-2 rounded bg-background border border-border"
                placeholder="AIが管理する物語の長期間記憶…"
                readOnly
              />
            </div>
            <div className="glass-sm p-4 rounded-lg">
              <h5 className="text-xs font-bold mb-2">📏 伏線元帳</h5>
              <p className="text-xs text-muted-foreground">伏線の status 一覧</p>
            </div>
          </div>
        );
      case 2:
        return (
          <div className="space-y-4">
            <h4 className="text-sm font-bold">ストレスログ</h4>
            <div className="glass-sm p-4 rounded-lg text-center">
              <p className="text-3xl font-bold font-mono text-rose-400">{selectedBook.cumulative_stress ?? 0}</p>
              <p className="text-xs text-muted-foreground mt-1">累積ストレス値</p>
              <div className="w-full bg-muted rounded-full h-2 mt-3 overflow-hidden">
                <div
                  className="bg-rose-500 h-2 rounded-full transition-all"
                  style={{ width: `${Math.min((selectedBook.cumulative_stress ?? 0) / 65 * 100, 100)}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground mt-1">しきい値: 65</p>
            </div>
          </div>
        );
      case 3:
        return (
          <div className="space-y-4">
            <h4 className="text-sm font-bold">商用ピッチ</h4>
            <div className="glass-sm p-4 rounded-lg">
              <h5 className="text-xs font-bold mb-2">📝 ピッチ内容</h5>
              <div className="text-xs font-mono bg-background p-3 rounded whitespace-pre-wrap">
                {typeof bible?.settings?.pitch === 'string'
                  ? bible.settings.pitch
                  : (bible?.settings?.pitch ? JSON.stringify(bible.settings.pitch, null, 2) : 'ピッチデータがありません。自己最適化を実行すると生成されます。')}
              </div>
            </div>
          </div>
        );
      case 4:
        return (
          <div className="space-y-4">
            <h4 className="text-sm font-bold">自己最適化</h4>
            <div className="glass-sm p-4 rounded-lg">
              <h5 className="text-xs font-bold mb-2">📊 最適化履歴</h5>
              <p className="text-xs text-muted-foreground">クリティック最適化の結果がここに表示されます</p>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  if (!selectedBook) {
    return <div className="text-center py-8">作品を選択してください。</div>;
  }

  return (
    <div className="animate-fade-in flex flex-col gap-6">
      <h2 className="text-xl font-bold">戦略分析 - {selectedBook.title}</h2>
      <div className="border-b border-[var(--border)] mb-4">
        <div className="flex">
          {subTabs.map((tab, index) => {
            const isExpertOnly = isTabExpertOnly(index);
            // Hide button if expert-only and not expert mode
            if (isExpertOnly && !isExpertMode) return null;
            return (
              <SubTabButton
                key={tab.title}
                active={activeSubTab === index}
                onClick={() => setActiveSubTab(index)}
              >
                {tab.title}
              </SubTabButton>
            );
          })}
        </div>
      </div>
      {renderSubTab()}
    </div>
  );
}