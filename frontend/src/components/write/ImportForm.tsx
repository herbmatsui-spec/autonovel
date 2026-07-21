import { NumberInput } from '../ui/NumberInput';

interface ImportFormProps {
  importEpNum: number;
  setImportEpNum: (val: number) => void;
  importText: string;
  setImportText: (val: string) => void;
  importDoRefine: boolean;
  setImportDoRefine: (val: boolean) => void;
  onSubmit: (e: React.FormEvent) => void;
  disabled: boolean;
  showPreview: boolean;
  setShowPreview: (val: boolean) => void;
}

export function ImportForm({
  importEpNum,
  setImportEpNum,
  importText,
  setImportText,
  importDoRefine,
  setImportDoRefine,
  onSubmit,
  disabled,
  showPreview,
  setShowPreview,
}: ImportFormProps) {
  return (
    <form
      className="glass-panel p-6"
      onSubmit={onSubmit}
      style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}
    >
      <h4 className="m-0 text-base">📥 手動チャプターインポート</h4>
      <NumberInput label="話数" value={importEpNum} onChange={setImportEpNum} min={1} />
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <input
          type="checkbox"
          id="previewImport"
          checked={showPreview}
          onChange={(e) => setShowPreview(e.target.checked)}
          style={{ width: 'auto' }}
        />
        <label htmlFor="previewImport" className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          インポート前にプレビューを表示
        </label>
      </div>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <label className="block text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
            本文テキスト
          </label>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {importText.length.toLocaleString()}文字
          </span>
        </div>
        <textarea
          value={importText}
          onChange={(e) => setImportText(e.target.value)}
          placeholder="インポートするエピソード本文を入力..."
          rows={6}
          required
        />
      </div>
      {showPreview && importText && (
        <div className="glass-panel p-4" style={{ marginTop: '0.5rem' }}>
          <strong>プレビュー（冒頭200文字）:</strong>
          <pre style={{ fontSize: '0.85rem', whiteSpace: 'pre-wrap', maxHeight: '200px', overflowY: 'auto' }}>
            {importText.slice(0, 200)}...
          </pre>
        </div>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <input
          type="checkbox"
          id="doRefine"
          checked={importDoRefine}
          onChange={(e) => setImportDoRefine(e.target.checked)}
          style={{ width: 'auto' }}
        />
        <label htmlFor="doRefine" className="text-sm" style={{ color: 'var(--text-secondary)' }}>
          AIによる推敲・リファインを実行する
        </label>
      </div>
      <button type="submit" className="btn btn-secondary w-full" disabled={disabled}>
        インポート実行
      </button>
    </form>
  );
}
