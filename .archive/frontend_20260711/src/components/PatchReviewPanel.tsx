import React, { useState } from 'react';
import { PendingPatch, approvePatch, rejectPatch, editPatch } from '../api';

interface PatchReviewPanelProps {
  bookId: number;
  patches: PendingPatch[];
  onRefresh: () => void;
}

export const PatchReviewPanel: React.FC<PatchReviewPanelProps> = ({ bookId, patches, onRefresh }) => {
  const [editingPatchId, setEditingPatchId] = useState<number | null>(null);
  const [editText, setEditText] = useState<string>('');
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleApprove = async (patchId: number) => {
    setLoading(true);
    setStatusMsg(null);
    try {
      await approvePatch(patchId);
      setStatusMsg({ type: 'success', text: 'パッチが承認され、適用されました！' });
      onRefresh();
    } catch (e: any) {
      setStatusMsg({ type: 'error', text: `承認失敗: ${e.message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async (patchId: number) => {
    setLoading(true);
    setStatusMsg(null);
    try {
      await rejectPatch(patchId);
      setStatusMsg({ type: 'success', text: 'パッチを却下しました。' });
      onRefresh();
    } catch (e: any) {
      setStatusMsg({ type: 'error', text: `却下失敗: ${e.message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleStartEdit = (patch: PendingPatch) => {
    setEditingPatchId(patch.id);
    setEditText(patch.patch_content);
  };

  const handleSaveEdit = async (patchId: number) => {
    setLoading(true);
    setStatusMsg(null);
    try {
      await editPatch(patchId, editText);
      setStatusMsg({ type: 'success', text: '修正内容を保存しました。' });
      setEditingPatchId(null);
      onRefresh();
    } catch (e: any) {
      setStatusMsg({ type: 'error', text: `保存失敗: ${e.message}` });
    } finally {
      setLoading(false);
    }
  };

  // 簡易的な行単位の差分（Diff）生成ロジック
  const renderDiff = (content: string, type: 'config' | 'prompt') => {
    // プロンプトや設定の差分を擬似的に見やすくハイライト
    const lines = content.split('\n');
    return (
      <div className="bg-gray-900 text-gray-100 p-4 rounded font-mono text-sm overflow-x-auto max-h-60 border border-gray-700">
        {lines.map((line, idx) => {
          let lineClass = 'text-gray-300';
          let prefix = ' ';
          if (type === 'config') {
            if (line.includes('=') || line.includes(':')) {
              lineClass = 'text-emerald-400 font-semibold';
              prefix = '+';
            }
          } else {
            lineClass = 'text-emerald-300';
            prefix = '+';
          }
          return (
            <div key={idx} className={`py-0.5 px-2 rounded hover:bg-gray-800 flex gap-2`}>
              <span className="text-gray-600 select-none w-6 text-right">{idx + 1}</span>
              <span className="text-emerald-500 font-bold select-none">{prefix}</span>
              <span className={lineClass}>{line}</span>
            </div>
          );
        })}
      </div>
    );
  };

  if (patches.length === 0) {
    return (
      <div className="bg-gray-800/40 backdrop-blur-md border border-gray-700/50 p-6 rounded-2xl text-center text-gray-400">
        現在、承認待ちのパッチはありません。AI分析からパッチが生成されるのをお待ちください。
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold text-white flex items-center gap-2">
        <span>🛡️</span> 承認待ちパッチの確認 (Human-in-the-Loop)
      </h3>

      {statusMsg && (
        <div className={`p-4 rounded-xl border ${
          statusMsg.type === 'success' 
            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
            : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
        }`}>
          {statusMsg.text}
        </div>
      )}

      <div className="space-y-4">
        {patches.map((patch) => (
          <div 
            key={patch.id} 
            className="bg-gray-800/50 backdrop-blur-md border border-gray-700/60 p-6 rounded-2xl shadow-xl transition-all duration-300 hover:border-violet-500/40"
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <span className={`inline-block px-3 py-1 text-xs font-semibold rounded-full uppercase tracking-wider ${
                  patch.patch_type === 'config' 
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' 
                    : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                }`}>
                  {patch.patch_type === 'config' ? '⚙️ CONFIG PATCH' : '✍️ PROMPT PATCH'}
                </span>
                <span className="ml-3 text-xs text-gray-400 font-mono">作成: {patch.created_at}</span>
              </div>
              <div className="flex gap-2">
                {editingPatchId === patch.id ? (
                  <>
                    <button 
                      onClick={() => handleSaveEdit(patch.id)}
                      disabled={loading}
                      className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium rounded-lg text-sm transition-colors"
                    >
                      保存
                    </button>
                    <button 
                      onClick={() => setEditingPatchId(null)}
                      disabled={loading}
                      className="px-4 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-300 font-medium rounded-lg text-sm transition-colors"
                    >
                      キャンセル
                    </button>
                  </>
                ) : (
                  <>
                    <button 
                      onClick={() => handleStartEdit(patch)}
                      disabled={loading}
                      className="px-3 py-1.5 bg-violet-600/30 hover:bg-violet-600/50 border border-violet-500/40 text-violet-300 font-medium rounded-lg text-sm transition-colors"
                    >
                      📝 編集
                    </button>
                    <button 
                      onClick={() => handleApprove(patch.id)}
                      disabled={loading}
                      className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg text-sm transition-all duration-200 hover:shadow-lg hover:shadow-emerald-500/20"
                    >
                      👍 承認して適用
                    </button>
                    <button 
                      onClick={() => handleReject(patch.id)}
                      disabled={loading}
                      className="px-4 py-1.5 bg-rose-600/20 hover:bg-rose-600/40 border border-rose-500/30 text-rose-300 font-medium rounded-lg text-sm transition-colors"
                    >
                      👎 却下
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* A/B テスト事前評価スコアの表示 */}
            {patch.ab_test_result?.scores && (
              <div className="mb-4 bg-gray-900/40 p-4 rounded-xl border border-gray-700/40 grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-xs text-gray-400">プロット追従性</div>
                  <div className="text-lg font-bold text-amber-400">{patch.ab_test_result.scores.plot_adherence || 0}%</div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">文体一貫性</div>
                  <div className="text-lg font-bold text-indigo-400">{patch.ab_test_result.scores.style_consistency || 0}%</div>
                </div>
                <div>
                  <div className="text-xs text-gray-400">詳細描写度</div>
                  <div className="text-lg font-bold text-emerald-400">{patch.ab_test_result.scores.detail_density || 0}%</div>
                </div>
              </div>
            )}

            {editingPatchId === patch.id ? (
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                rows={8}
                className="w-full bg-gray-900 text-gray-100 p-4 rounded-xl font-mono text-sm border border-violet-500 focus:outline-none focus:ring-2 focus:ring-violet-500/30"
              />
            ) : (
              <div className="mt-2">
                {renderDiff(patch.patch_content, patch.patch_type)}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
