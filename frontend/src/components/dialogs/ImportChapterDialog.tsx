import React, { useState } from 'react';
import { Button } from '@/components/ui/button';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (epNum: number, text: string, doRefine: boolean) => void;
}

export function ImportChapterDialog({ isOpen, onClose, onSubmit }: Props) {
  const [epNum, setEpNum] = useState(1);
  const [text, setText] = useState('');
  const [doRefine, setDoRefine] = useState(true);

  if (!isOpen) return null;

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(epNum, text, doRefine);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="import-modal-title"
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
        <h3 id="import-modal-title" className="border-b border-border pb-3">📖 章取り込み</h3>
        
        <div>
          <label htmlFor="import-ep-num" className="block text-sm text-text-secondary mb-1">エピソード番号</label>
          <input
            id="import-ep-num"
            type="number"
            value={epNum}
            onChange={(e) => setEpNum(parseInt(e.target.value) || 1)}
            min={1}
            required
          />
        </div>
        
        <div>
          <label htmlFor="import-text" className="block text-sm text-text-secondary mb-1">原稿テキスト</label>
          <textarea
            id="import-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="原稿を貼り付け..."
            rows={8}
            required
            style={{ width: '100%' }}
          />
        </div>
        
        <div className="flex items-center gap-2">
          <input
            id="import-do-refine"
            type="checkbox"
            checked={doRefine}
            onChange={(e) => setDoRefine(e.target.checked)}
          />
          <label htmlFor="import-do-refine" className="text-sm text-text-secondary">AI研磨を実行する</label>
        </div>
        
        <div className="flex gap-4 mt-2 justify-end">
          <Button type="button" variant="secondary" onClick={onClose}>
            キャンセル
          </Button>
          <Button type="submit">
            📥 取り込み実行
          </Button>
        </div>
      </form>
    </div>
  );
}
