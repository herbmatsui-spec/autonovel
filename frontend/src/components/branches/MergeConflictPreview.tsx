import React from 'react';
import {
  ConflictChunk,
  MergePreviewResponse,
  BranchMergeCommitRequest,
  BranchMergeCommitResponse,
  ResolvedChapterPayload,
} from '../../types/branches';
import { useCommitBranchMerge } from '../../hooks/useMergePreview';

export type ResolutionAction = 'accept-source' | 'accept-target' | 'accept-base' | 'accept-manual';

export interface MergeConflictPreviewProps {
  previewData: MergePreviewResponse | null;
  bookId?: number;
  sourceBranchId?: number;
  targetBranchId?: number;
  mergeEpNum?: number;
  onResolveConflict?: (chunkId: string, action: ResolutionAction, manualContent?: string) => void;
  onExecuteMerge?: () => void;
  onClose?: () => void;
  onSuccess?: (response: BranchMergeCommitResponse) => void;
}

export const MergeConflictPreview: React.FC<MergeConflictPreviewProps> = ({
  previewData,
  bookId = 1,
  sourceBranchId,
  targetBranchId,
  mergeEpNum = 1,
  onResolveConflict,
  onExecuteMerge,
  onClose,
  onSuccess,
}) => {
  if (!previewData) return null;

  const [resolutions, setResolutions] = React.useState<Record<string, ResolutionAction>>({});
  const [manualContents, setManualContents] = React.useState<Record<string, string>>({});
  const [toastMessage, setToastMessage] = React.useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const commitMutation = useCommitBranchMerge();

  const handleResolve = (
    chunkId: string,
    action: ResolutionAction,
    manualContent?: string
  ) => {
    setResolutions((prev) => ({ ...prev, [chunkId]: action }));
    if (manualContent !== undefined) {
      setManualContents((prev) => ({ ...prev, [chunkId]: manualContent }));
    }
    if (onResolveConflict) {
      onResolveConflict(chunkId, action, manualContent);
    }
  };

  const conflicts = previewData.conflict_chunks || [];
  const allResolved = conflicts.length === 0 || conflicts.every((chunk) => !!resolutions[chunk.id]);

  // マージコミットの実行ハンドラ (Step 63, 64)
  const handleCommit = async () => {
    if (onExecuteMerge) {
      onExecuteMerge();
      return;
    }

    const sBranchId = sourceBranchId ?? previewData.source_branch_id ?? 0;
    const tBranchId = targetBranchId ?? previewData.target_branch_id ?? 0;

    // 解決済み章ペイロードの作成
    const resolvedChapters: ResolvedChapterPayload[] = [];

    // コンフリクトが複数章にまたがる場合、または1つの章にまとめる場合の解決文字列の抽出
    if (conflicts.length > 0) {
      for (const chunk of conflicts) {
        const action = resolutions[chunk.id] || 'accept-source';
        let resolvedText = chunk.source;
        if (action === 'accept-target') resolvedText = chunk.target;
        else if (action === 'accept-base') resolvedText = chunk.base;
        else if (action === 'accept-manual') resolvedText = manualContents[chunk.id] || chunk.source;

        resolvedChapters.push({
          chapter_number: mergeEpNum,
          resolved_content: resolvedText,
          resolution_strategy: action,
        });
      }
    } else if (previewData.merged_content) {
      resolvedChapters.push({
        chapter_number: mergeEpNum,
        resolved_content: previewData.merged_content,
        resolution_strategy: 'clean_merge',
      });
    }

    const payload: BranchMergeCommitRequest = {
      source_branch_id: sBranchId,
      target_branch_id: tBranchId,
      merge_ep_num: mergeEpNum,
      resolved_chapters: resolvedChapters,
      commit_message: `Merged branch ${sBranchId} into ${tBranchId} at ep ${mergeEpNum}`,
    };

    try {
      const result = await commitMutation.mutateAsync({ bookId, payload });
      setToastMessage({
        text: `ブランチのマージが正常に完了しました！（更新章数: ${result.updated_chapters_count}件）`,
        type: 'success',
      });
      if (onSuccess) {
        onSuccess(result);
      }
      // 少し待ってから閉じる
      setTimeout(() => {
        if (onClose) onClose();
      }, 1500);
    } catch (err: any) {
      setToastMessage({
        text: `マージコミットに失敗しました: ${err.message || 'Unknown error'}`,
        type: 'error',
      });
    }
  };

  return (
    <div style={{ border: '1px solid #ddd', borderRadius: '8px', overflow: 'hidden', backgroundColor: '#fff' }}>
      {/* トースト通知 (Step 64) */}
      {toastMessage && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: toastMessage.type === 'success' ? '#d4edda' : '#f8d7da',
            color: toastMessage.type === 'success' ? '#155724' : '#721c24',
            borderBottom: '1px solid rgba(0,0,0,0.1)',
            fontWeight: 'bold',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>{toastMessage.text}</span>
          <button
            onClick={() => setToastMessage(null)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px' }}
          >
            ×
          </button>
        </div>
      )}

      <div style={{ padding: '16px', backgroundColor: '#f8f9fa', borderBottom: '1px solid #eee', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ margin: 0 }}>マージプレビュー & コンフリクト解決</h3>
          <div style={{ marginTop: '8px', fontSize: '14px', color: '#666' }}>
            {previewData.can_merge ? '✅ マージ可能（自動解決）' : '⚠️ コンフリクトが発生しています。解決策を選択してください。'}
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '20px',
              cursor: 'pointer',
              color: '#888',
            }}
          >
            &times;
          </button>
        )}
      </div>

      <div style={{ padding: '16px', maxHeight: '500px', overflowY: 'auto' }}>
        {conflicts.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: '#28a745' }}>
            <h4>コンフリクトはありません。</h4>
            <p style={{ color: '#666', fontSize: '14px' }}>
              自動マージ可能です。「マージを実行」ボタンをクリックしてコミットを確定してください。
            </p>
          </div>
        ) : (
          conflicts.map((chunk) => (
            <div key={chunk.id} style={{ border: '1px solid #eee', marginBottom: '16px', padding: '12px', borderRadius: '4px' }}>
              <div style={{ fontWeight: 'bold', marginBottom: '12px', display: 'flex', justifyContent: 'space-between' }}>
                <span>コンフリクトチャンク {chunk.id.substring(0, 8)}...</span>
                <span style={{ fontSize: '12px', color: resolutions[chunk.id] ? '#28a745' : '#dc3545' }}>
                  {resolutions[chunk.id] ? `解決済み (${resolutions[chunk.id]})` : '未解決'}
                </span>
              </div>

              <div style={{ display: 'flex', gap: '16px', marginBottom: '12px' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Base（共通祖先）</div>
                  <pre style={{ backgroundColor: '#f8f9fa', padding: '8px', borderRadius: '4px', fontSize: '12px', height: '80px', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                    {chunk.base}
                  </pre>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Source（分岐元）</div>
                  <pre style={{ backgroundColor: '#f8f9fa', padding: '8px', borderRadius: '4px', fontSize: '12px', height: '80px', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                    {chunk.source}
                  </pre>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>Target（マージ先）</div>
                  <pre style={{ backgroundColor: '#f8f9fa', padding: '8px', borderRadius: '4px', fontSize: '12px', height: '80px', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                    {chunk.target}
                  </pre>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={() => handleResolve(chunk.id, 'accept-base')}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: resolutions[chunk.id] === 'accept-base' ? '#007bff' : '#f8f9fa',
                    color: resolutions[chunk.id] === 'accept-base' ? '#fff' : '#333',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  Baseを採用
                </button>
                <button
                  type="button"
                  onClick={() => handleResolve(chunk.id, 'accept-source')}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: resolutions[chunk.id] === 'accept-source' ? '#007bff' : '#f8f9fa',
                    color: resolutions[chunk.id] === 'accept-source' ? '#fff' : '#333',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  Sourceを採用
                </button>
                <button
                  type="button"
                  onClick={() => handleResolve(chunk.id, 'accept-target')}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: resolutions[chunk.id] === 'accept-target' ? '#007bff' : '#f8f9fa',
                    color: resolutions[chunk.id] === 'accept-target' ? '#fff' : '#333',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  Targetを採用
                </button>
                <button
                  type="button"
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
                    color: resolutions[chunk.id] === 'accept-manual' ? '#fff' : '#333',
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  手動解決
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div style={{ padding: '16px', textAlign: 'right', borderTop: '1px solid #eee', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '8px 16px',
              backgroundColor: '#e2e6ea',
              color: '#333',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            キャンセル
          </button>
        )}
        <button
          type="button"
          onClick={handleCommit}
          disabled={!allResolved || commitMutation.isPending}
          style={{
            padding: '8px 16px',
            backgroundColor: allResolved && !commitMutation.isPending ? '#28a745' : '#6c757d',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: allResolved && !commitMutation.isPending ? 'pointer' : 'not-allowed',
            fontWeight: 'bold',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          {commitMutation.isPending ? (
            <>
              <span style={{ display: 'inline-block', width: '12px', height: '12px', border: '2px solid #fff', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
              マージコミット中...
            </>
          ) : allResolved ? (
            'マージを実行'
          ) : (
            'すべてのコンフリクトを解決してください'
          )}
        </button>
      </div>
    </div>
  );
};
