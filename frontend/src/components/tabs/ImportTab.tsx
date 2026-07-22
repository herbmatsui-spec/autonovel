import { useState } from 'react';
import type { Book } from '../../types';

interface ImportTabProps {
  selectedBook: Book;
  handleImportChapter: (e: React.FormEvent) => Promise<void>;
}

export function ImportTab({ selectedBook, handleImportChapter }: ImportTabProps) {
  const [epNum, setEpNum] = useState<number>(1);
  const [importText, setImportText] = useState('');
  const [doRefine, setDoRefine] = useState(true);

  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-base font-bold">📥 インポート</h2>
      <p className="text-xs text-muted-foreground">
        既存のテキストをエピソードとしてインポートします。
      </p>

      <form
        onSubmit={handleImportChapter}
        className="glass-sm p-6 rounded-lg space-y-4"
      >
        <div>
          <label htmlFor="import-ep-num" className="block text-xs font-semibold text-muted-foreground mb-1">
            エピソード番号
          </label>
          <input
            id="import-ep-num"
            type="number"
            min={1}
            value={epNum}
            onChange={(e) => setEpNum(Number(e.target.value))}
            className="w-full p-2 text-sm rounded bg-background border border-border"
          />
        </div>
        <div>
          <label htmlFor="import-text" className="block text-xs font-semibold text-muted-foreground mb-1">
            インポートテキスト
          </label>
          <textarea
            id="import-text"
            rows={12}
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            className="w-full p-3 text-sm rounded bg-background border border-border resize-y"
            placeholder="ここに本文を貼り付け..."
          />
        </div>
        <div className="flex items-center gap-2">
          <input
            id="import-refine"
            type="checkbox"
            checked={doRefine}
            onChange={(e) => setDoRefine(e.target.checked)}
            className="rounded"
          />
          <label htmlFor="import-refine" className="text-xs text-muted-foreground">
            インポート後にAIリファインメントを実行する
          </label>
        </div>
        <button
          type="submit"
          className="w-full px-4 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          📥 インポート実行
        </button>
      </form>
    </div>
  );
}