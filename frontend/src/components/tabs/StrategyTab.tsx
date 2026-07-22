import { useState, useEffect } from 'react';
import type { Book } from '../../types';
import { getPlots, getChapters, getBible } from '../../api';

interface StrategyTabProps {
  selectedBook: Book;
}

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

export function StrategyTab({ selectedBook }: StrategyTabProps) {
  const [activeSubTab, setActiveSubTab] = useState(0);
  const [plots, setPlots] = useState<any[]>([]);
  const [chapters, setChapters] = useState<any[]>([]);
  const [bible, setBible] = useState<any>(null);

  useEffect(() => {
    Promise.all([
      getPlots(selectedBook.id),
      getChapters(selectedBook.id),
      getBible(selectedBook.id),
    ]).then(([p, c, b]) => {
      setPlots(p);
      setChapters(c);
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

  const renderSubTab = () => {
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
                {bible?.settings?.pitch ?? 'ピッチデータがありません。自己最適化を実行すると生成されます。'}
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

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-base font-bold">📈 覇権戦略司令部 <span className="text-xs text-muted-foreground font-normal">— 分析対象: {selectedBook.title}</span></h2>
      <div className="flex gap-1 border-b border-border">
        {subTabs.map((st, i) => (
          <SubTabButton key={st.title} active={activeSubTab === i} onClick={() => setActiveSubTab(i)}>
            {st.title}
          </SubTabButton>
        ))}
      </div>
      {renderSubTab()}
    </div>
  );
}