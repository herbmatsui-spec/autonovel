import { useState } from 'react';
import type { Book } from '../../types';
import { useBookStore } from '@/store/useBookStore';
import { useAppActions } from '@/hooks/useAppActions';
import { Button } from '@/components/ui/button';

interface ImportTabProps {
  selectedBook?: Book;
  handleImportChapter: (e: React.FormEvent) => Promise<void>;
}

export function ImportTab({ handleImportChapter }: ImportTabProps) {
  const [epNum, setEpNum] = useState<number>(1);
  const [importText, setImportText] = useState('');
  const [doRefine, setDoRefine] = useState(true);

  if (!selectedBook) {
    return <div className="text-center py-8">作品を選択してください。</div>;
  }

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
            value={epNum}
            onChange={(e) => setEpNum(parseInt(e.target.value) || 1)}
            min={1}
            className="block w-full px-3 py-2 border rounded"
          />
        </div>
        <div>
          <label htmlFor="import-text" className="block text-xs font-semibold text-muted-foreground mb-1">
            インポートするテキスト
          </label>
          <textarea
            id="import-text"
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            rows={6}
            className="block w-full px-3 py-2 border rounded"
            placeholder="ここにインポートしたいテキストを貼り付けてください..."
          />
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm font-medium">
            <input
              type="checkbox"
              checked={doRefine}
              onChange={(e) => setDoRefine(e.target.checked)}
            />
            インポート後に自動で推敲を行う
          </label>
        </div>
        <div className="flex justify-end">
          <Button
            variant="default"
            type="submit"
          >
            インポートを実行
          </Button>
        </div>
      </form>
    </div>
  );
}