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
}: ImportFormProps) {
  return (
    <form
      className="glass-panel p-6"
      onSubmit={onSubmit}
      style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}
    >
      <h4 className="m-0 text-base">📥 手動チャプターインポート</h4>
      <NumberInput label="話数" value={importEpNum} onChange={setImportEpNum} min={1} />
      <div>
        <label className="block text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
          本文テキスト
        </label>
        <textarea
          value={importText}
          onChange={(e) => setImportText(e.target.value)}
          placeholder="インポートするエピソード本文を入力..."
          rows={6}
          required
        />
      </div>
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
