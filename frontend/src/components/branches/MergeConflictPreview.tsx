import React from 'react';
import { ConflictChunk, MergePreviewResponse } from '@/types/branches';

type MergeConflictPreviewProps = {
  previewData: MergePreviewResponse | null;
  onResolveConflict: (chunkId: string, action: 'accept-source' | 'accept-target' | 'accept-base' | 'accept-manual', manualContent?: string) => void;
  onExecuteMerge: () => void;
};

export const MergeConflictPreview: React.FC<MergeConflictPreviewProps> = ({
  previewData,
  onResolveConflict,
  onExecuteMerge
}) => {
  if (!previewData) return null;

  const [resolutions, setResolutions] = React.useState<Record<string, string>>({});
  const [manualContents, setManualContents] = React.useState<Record<string, string>>({});

  const handleResolve = (chunkId: string, action: 'accept-source' | 'accept-target' | 'accept-base' | 'accept-manual', manualContent?: string) => {
    setResolutions(prev => ({ ...prev, [chunkId]: action }));
    if (manualContent) {
      setManualContents(prev => ({ ...prev, [chunkId]: manualContent }));
    }
    onResolveConflict(chunkId, action, manualContent);
  };

  const allResolved = previewData.conflict_chunks.every(chunk => !!resolutions[chunk.id]);

  return (
    <div style={{ border: '1px solid #ddd', borderRadius: '8px', overflow: 'hidden' }}>
      <div style={{ padding: '16px', backgroundColor: '#f8f9fa', borderBottom: '1px solid #eee' }}>
        <h3 style={{ margin: 0 }}>マージプレビュー</h3>
        <div style={{ marginTop: '8px', fontSize: '14px', color: '#666' }}>
          {previewData.can_merge ? 'マージ可能' : 'コンフリクトがあります'}
        </div>
      </div>
      <div style={{ padding: '16px', maxHeight: '500px', overflowY: 'auto' }}>
        {previewData.conflict_chunks.map(chunk => (
          <div key={chunk.id} style={{ border: '1px solid #eee', marginBottom: '16px', padding: '12px', borderRadius: '4px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '12px' }}>
              コンフリクトチャンク {chunk.id.substring(0, 8)}...
            </div>
            
            <div style={{ display: 'flex', gap: '16px', marginBottom: '12px' }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Base</div>
                <pre style={{ backgroundColor: '#f8f9fa', padding: '8px', borderRadius: '4px', fontSize: '12px', height: '80px', overflow: 'auto' }}>
                  {chunk.base}
                </pre>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Source</div>
                <pre style={{ backgroundColor: '#f8f9fa', padding: '8px', borderRadius: '4px', fontSize: '12px', height: '80px', overflow: 'auto' }}>
                  {chunk.source}
                </pre>
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Target</div>
                <pre style={{ backgroundColor: '#f8f9fa', padding: '8px', borderRadius: '4px', fontSize: '12px', height: '80px', overflow: 'auto' }}>
                  {chunk.target}
                </pre>
              </div>
            </div>
            
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                onClick={() => handleResolve(chunk.id, 'accept-base')}
                style={{
                  padding: '6px 12px',
                  backgroundColor: resolutions[chunk.id] === 'accept-base' ? '#007bff' : '#f8f9fa',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Baseを採用
              </button>
              <button
                onClick={() => handleResolve(chunk.id, 'accept-source')}
                style={{
                  padding: '6px 12px',
                  backgroundColor: resolutions[chunk.id] === 'accept-source' ? '#007bff' : '#f8f9fa',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Sourceを採用
              </button>
              <button
                onClick={() => handleResolve(chunk.id, 'accept-target')}
                style={{
                  padding: '6px 12px',
                  backgroundColor: resolutions[chunk.id] === 'accept-target' ? '#007bff' : '#f8f9fa',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Targetを採用
              </button>
              <button
                onClick={() => {
                  const manualContent = window.confirm('手動で内容を入力しますか？\nOK: 手動入力\nCancel: 現在のソース内容を使用');
                  if (manualContent) {
                    const content = window.prompt('マージ後の内容を入力してください:', chunk.source);
                    if (content !== null) {
                      handleResolve(chunk.id, 'accept-manual', content);
                    }
                  } else {
                    handleResolve(chunk.id, 'accept-source');
                  }
                }}
                style={{
                  padding: '6px 12px',
                  backgroundColor: resolutions[chunk.id] === 'accept-manual' ? '#007bff' : '#f8f9fa',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                手動解決
              </button>
            </div>
          </div>
        ))}
      </div>
      <div style={{ padding: '16px', textAlign: 'right', borderTop: '1px solid #eee' }}>
        <button
          onClick={onExecuteMerge}
          disabled={!allResolved}
          style={{
            padding: '8px 16px',
            backgroundColor: allResolved ? '#28a745' : '#6c757d',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: allResolved ? 'pointer' : 'not-allowed',
            fontWeight: 'bold'
          }}
        >
          {allResolved ? 'マージを実行' : 'すべてのコンフリクトを解決してください'}
        </button>
      </div>
    </div>
  );
};
