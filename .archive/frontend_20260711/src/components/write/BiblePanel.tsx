import { Bible } from '../types';

interface BiblePanelProps {
  bible: Bible | null;
}

export function BiblePanel({ bible }: BiblePanelProps) {
  return (
    <div className="glass-panel p-5">
      <h4 style={{ marginBottom: '0.75rem' }}>📘 世界観・キャラクター設定 (Bible)</h4>
      {bible && bible.settings ? (
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          <p style={{ marginBottom: '0.5rem' }}>
            <strong>バージョン:</strong> {bible.version}
          </p>
          <details>
            <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>
              キャラクター設定を表示
            </summary>
            <pre style={{ fontSize: '0.75rem', marginTop: '0.5rem', maxHeight: '150px' }}>
              {JSON.stringify(bible.settings.characters, null, 2)}
            </pre>
          </details>
        </div>
      ) : (
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          設定ファイル未検出
        </p>
      )}
    </div>
  );
}
