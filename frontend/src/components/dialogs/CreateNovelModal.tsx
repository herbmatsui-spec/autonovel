import React from 'react';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/store/useUIStore';
import { useEasyModeStore } from '@/store/useEasyModeStore';

interface CreateNovelModalProps {
  onSubmit: (e: React.FormEvent) => void;
}

export function CreateNovelModal({
  onSubmit,
}: CreateNovelModalProps) {
  const { isCreateModalOpen, setCreateModalOpen } = useUIStore();
  const {
    easyGenre,
    setEasyGenre,
    easyKeywords,
    setEasyKeywords,
    easyArchetype,
    setEasyArchetype,
    easyTargetEps,
    setEasyTargetEps,
    easyWordCount,
    setEasyWordCount,
    easyConcept,
    setEasyConcept,
  } = useEasyModeStore();

  if (!isCreateModalOpen) return null;

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      setCreateModalOpen(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      setCreateModalOpen(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="modal-overlay animate-fade-in"
      onClick={handleOverlayClick}
      onKeyDown={handleKeyDown}
      tabIndex={-1}
    >
<form
        className="glass-panel animate-slide-up w-[500px] p-8 flex flex-col gap-5"
        onSubmit={onSubmit}
        style={{ backgroundColor: 'var(--bg-sidebar)' }}
      >
        <h3 id="modal-title" className="border-b border-border pb-3">⚔️ 小説を自動生成 (かんたんモード)</h3>
        
        <div>
          <label htmlFor="easy-genre" className="block text-sm text-text-secondary mb-1">ジャンル</label>
          <input id="easy-genre" type="text" value={easyGenre} onChange={(e) => setEasyGenre(e.target.value)} required />
        </div>
        
        <div>
          <label htmlFor="easy-keywords" className="block text-sm text-text-secondary mb-1">キーワード (カンマ区切り)</label>
          <input id="easy-keywords" type="text" value={easyKeywords} onChange={(e) => setEasyKeywords(e.target.value)} required />
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="easy-archetype" className="block text-sm text-text-secondary mb-1">主人公タイプ (アーキタイプ)</label>
            <select id="easy-archetype" value={easyArchetype} onChange={(e) => setEasyArchetype(e.target.value)}>
              <option value="avenger">アヴェンジャー型（復讐・暗黒）</option>
              <option value="reincarnation">転生賢者型（俺TUEEE・無双）</option>
              <option value="villainess">悪役令嬢型（破滅回避・心理戦）</option>
              <option value="struggler">ストラグラー型（泥臭い成長）</option>
            </select>
          </div>
          <div>
            <label htmlFor="easy-target-eps" className="block text-sm text-text-secondary mb-1">全体目標話数</label>
            <input id="easy-target-eps" type="number" value={easyTargetEps} onChange={(e) => setEasyTargetEps(parseInt(e.target.value) || 10)} min={3} max={30} />
          </div>
        </div>
        
        <div>
          <label htmlFor="easy-word-count" className="block text-sm text-text-secondary mb-1">一話あたりの想定文字数</label>
          <input id="easy-word-count" type="number" value={easyWordCount} onChange={(e) => setEasyWordCount(parseInt(e.target.value) || 3000)} step={500} min={1000} />
        </div>
        
        <div>
          <label htmlFor="easy-concept" className="block text-sm text-text-secondary mb-1">コンセプト詳細 (チート強度や設定など)</label>
          <textarea
            id="easy-concept"
            value={easyConcept}
            onChange={(e) => setEasyConcept(e.target.value)}
            placeholder="例: 主人公は最強のハッカーだが異世界で魔法回路をハックする..."
            rows={3}
            aria-label="コンセプト詳細"
          />
        </div>
        
        <div className="flex gap-4 mt-2 justify-end">
          <button type="button" className="btn btn-secondary transition-colors duration-200" onClick={() => setCreateModalOpen(false)}>
            キャンセル
          </button>
          <button type="submit" className="btn btn-primary transition-colors duration-200">
            🚀 生成開始
          </button>
        </div>
      </form>
    </div>
  );
}
