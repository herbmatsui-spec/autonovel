import { useState, useEffect } from 'react';
import type { Book, Plot, Bible } from '../../types';
import { getPlots, getBible } from '../../api';
import { useBookStore } from '@/store/useBookStore';
import { Button } from '@/components/ui/button';

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
  const [activeSubTab, setActiveSubTab] = useState(0);
  const [plots, setPlots] = useState<Plot[]>([]);
  const [bible, setBible] = useState<Bible | null>(null);

  useEffect(() => {
    if (selectedBook?.id) {
      Promise.all([
        getPlots(selectedBook.id),
        getBible(selectedBook.id),
      ]).then(([plotsData, bibleData]) => {
        setPlots(plotsData);
        setBible(bibleData);
      }).catch(err => {
        console.error('Failed to load strategy data:', err);
      });
    }
  }, [selectedBook?.id]);

  if (!selectedBook) {
    return <div className="text-center py-8">作品を選択してください。</div>;
  }

  return (
    <div className="animate-fade-in flex flex-col gap-6">
      <h2 className="text-xl font-bold">戦略分析 - {selectedBook.title}</h2>
      <div className="border-b border-[var(--border)] mb-4">
        <div className="flex">
          <SubTabButton
            active={activeSubTab === 0}
            onClick={() => setActiveSubTab(0)}
          >
            プロット分析
          </SubTabButton>
          <SubTabButton
            active={activeSubTab === 1}
            onClick={() => setActiveSubTab(1)}
          >
            聖書分析
          </SubTabButton>
        </div>
      </div>
      {activeSubTab === 0 && (
        <div className="space-y-4">
          <h3 className="font-semibold">プロット概要</h3>
          {plots.length === 0 ? (
            <p className="text-sm text-muted-foreground">プロットデータはまだありません。</p>
          ) : (
            <div className="space-y-2">
              {plots.map((plot) => (
                <div key={plot.id} className="p-3 bg-[var(--muted)] rounded">
                  <h4 className="font-medium mb-2">エピソード {plot.episode_no}: {plot.title}</h4>
                  <p className="text-sm">{plot.summary}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {activeSubTab === 1 && (
        <div className="space-y-4">
          <h3 className="font-semibold">ストーリーバイブル</h3>
          {!bible ? (
            <p className="text-sm text-muted-foreground">聖書データはまだありません。</p>
          ) : (
            <div className="space-y-4">
              {bible.characters && (
                <div>
                  <h4 className="font-medium mb-2">キャラクター</h4>
                  <div className="space-y-2">
                    {bible.characters.map((char, index) => (
                      <div key={index} className="p-2 bg-[var(--accent)]/10 rounded">
                        <strong>{char.name}</strong>: {char.description}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {bible.world_setting && (
                <div>
                  <h4 className="font-medium mb-2">世界観設定</h4>
                  <p>{bible.world_setting}</p>
                </div>
              )}
              {bible.themes && (
                <div>
                  <h4 className="font-medium mb-2">テーマ</h4>
                  <div className="flex flex-wrap gap-2">
                    {bible.themes.map((theme, index) => (
                      <span key={index} className="px-2 py-1 bg-[var(--accent)]/20 text-xs rounded">
                        {theme}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}