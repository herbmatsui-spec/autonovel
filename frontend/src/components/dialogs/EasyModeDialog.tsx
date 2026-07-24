import React, { useState, useEffect } from 'react';
import { useEasyModeStore } from '@/store/useEasyModeStore';
import { getPlanningOptions } from '@/api';
import type { EasyModeParams, PlanningOptions } from '@/types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (params: EasyModeParams) => void;
}

export function EasyModeDialog({ isOpen, onClose, onSubmit }: Props) {
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

  const [easyGenres, setEasyGenres] = useState<PlanningOptions['easy_genres'] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedGenreKey, setSelectedGenreKey] = useState('');

  useEffect(() => {
    if (!isOpen) return;
    getPlanningOptions()
      .then(data => {
        setEasyGenres(data.easy_genres);
        const firstKey = Object.keys(data.easy_genres)[0] || '';
        setSelectedGenreKey(firstKey);
        if (firstKey && data.easy_genres[firstKey]) {
          setEasyGenre(data.easy_genres[firstKey].genre);
          setEasyArchetype(data.easy_genres[firstKey].archetype);
        }
        setIsLoading(false);
      })
      .catch(err => {
        console.error('Failed to load easy genres:', err);
        setIsLoading(false);
      });
  }, [isOpen]);

  if (!isOpen) return null;

  const handleGenreChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const key = e.target.value;
    setSelectedGenreKey(key);
    const preset = easyGenres?.[key];
    if (preset) {
      setEasyGenre(preset.genre);
      setEasyArchetype(preset.archetype);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      api_key: '',
      config: {},
      initial_limit: 1,
      genre: easyGenre,
      keywords: easyKeywords,
      archetype_key: easyArchetype,
      target_eps: easyTargetEps,
      word_count: easyWordCount,
      concept: easyConcept,
      tone_vibe: 0.65,
    });
  };

  const genreOptions = easyGenres ? Object.keys(easyGenres) : [];
  const archetypeOptions = easyGenres
    ? Array.from(new Set(Object.values(easyGenres).map(v => v.archetype)))
    : ['avenger', 'reincarnation', 'villainess', 'struggler'];

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
        onSubmit={handleSubmit}
        style={{ backgroundColor: 'var(--bg-sidebar)' }}
      >
        <h3 id="modal-title" className="border-b border-border pb-3">⚔️ 小説を自動生成 (かんたんモード)</h3>
        
        <div>
          <label htmlFor="easy-genre" className="block text-sm text-text-secondary mb-1">ジャンル</label>
          <select
            id="easy-genre"
            value={selectedGenreKey}
            onChange={handleGenreChange}
            disabled={isLoading || !easyGenres}
            required
          >
            {isLoading || !easyGenres ? (
              <option value="">読み込み中...</option>
            ) : (
              genreOptions.map(key => (
                <option key={key} value={key}>{key}</option>
              ))
            )}
          </select>
        </div>
        
        <div>
          <label htmlFor="easy-keywords" className="block text-sm text-text-secondary mb-1">キーワード (カンマ区切り)</label>
          <input id="easy-keywords" type="text" value={easyKeywords} onChange={(e) => setEasyKeywords(e.target.value)} required />
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="easy-archetype" className="block text-sm text-text-secondary mb-1">主人公タイプ (アーキタイプ)</label>
            <select id="easy-archetype" value={easyArchetype} onChange={(e) => setEasyArchetype(e.target.value)}>
              {archetypeOptions.map(arch => (
                <option key={arch} value={arch}>{arch}</option>
              ))}
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
          <button type="button" className="btn btn-secondary transition-colors duration-200" onClick={onClose}>
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
