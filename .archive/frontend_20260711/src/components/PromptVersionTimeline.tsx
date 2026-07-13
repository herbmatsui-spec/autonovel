import React, { useState } from 'react';
import { PromptVersion, rollbackPromptVersion } from '../api';

interface PromptVersionTimelineProps {
  bookId: number;
  versions: PromptVersion[];
  onRefresh: () => void;
}

export const PromptVersionTimeline: React.FC<PromptVersionTimelineProps> = ({ bookId, versions, onRefresh }) => {
  const [rollbackReason, setRollbackReason] = useState<string>('');
  const [rollingBackId, setRollingBackId] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleRollback = async (versionId: number) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const reason = rollbackReason.strip ? rollbackReason.trim() : '手動ロールバック';
      await rollbackPromptVersion(bookId, versionId, reason || '手動ロールバック');
      setRollingBackId(null);
      setRollbackReason('');
      onRefresh();
    } catch (e: any) {
      setErrorMsg(`ロールバックに失敗しました: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (versions.length === 0) {
    return (
      <div className="bg-gray-800/40 backdrop-blur-md border border-gray-700/50 p-6 rounded-2xl text-center text-gray-400">
        プロンプトの更新履歴がありません。
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold text-white flex items-center gap-2">
        <span>🕒</span> プロンプト バージョン管理と履歴 (A/B テスト)
      </h3>

      {errorMsg && (
        <div className="p-4 rounded-xl border bg-rose-500/10 border-rose-500/30 text-rose-400">
          {errorMsg}
        </div>
      )}

      <div className="relative border-l border-gray-700 ml-4 pl-6 space-y-8">
        {versions.map((ver) => {
          const isRollback = !!ver.rollback_reason;
          return (
            <div key={ver.id} className="relative">
              {/* タイムラインのインジケータードット */}
              <div className={`absolute -left-[31px] top-1.5 w-4 h-4 rounded-full border-2 ${
                ver.is_active 
                  ? 'bg-emerald-500 border-emerald-300 shadow-lg shadow-emerald-500/50 scale-125' 
                  : isRollback 
                    ? 'bg-rose-500 border-rose-400' 
                    : 'bg-gray-600 border-gray-500'
              }`} />

              <div className={`bg-gray-800/40 backdrop-blur-md border p-5 rounded-2xl transition-all duration-300 hover:border-violet-500/30 ${
                ver.is_active ? 'border-emerald-500/30 ring-1 ring-emerald-500/10' : 'border-gray-700/50'
              }`}>
                <div className="flex justify-between items-start flex-wrap gap-2 mb-3">
                  <div>
                    <span className="text-lg font-bold text-white font-mono">{ver.version_tag}</span>
                    {ver.is_active && (
                      <span className="ml-3 px-2 py-0.5 text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full">
                        ACTIVE (適用中)
                      </span>
                    )}
                    {isRollback && (
                      <span className="ml-3 px-2 py-0.5 text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-full">
                        ROLLED BACK (無効)
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-400 font-mono">{ver.created_at}</div>
                </div>

                {/* スコア・A/Bテスト評価の表示 */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-4 bg-gray-900/30 p-3 rounded-xl border border-gray-700/30 text-xs">
                  <div>
                    <span className="text-gray-400">事前スコア (Critique): </span>
                    <span className="font-bold text-amber-400">
                      {ver.score_before !== undefined && ver.score_before !== null ? `${ver.score_before.toFixed(1)}` : '評価なし'}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">適用後スコア (執筆評価): </span>
                    <span className={`font-bold ${
                      ver.score_after !== undefined && ver.score_after !== null
                        ? ver.score_before !== undefined && ver.score_after < ver.score_before - 5
                          ? 'text-rose-400'
                          : 'text-emerald-400'
                        : 'text-gray-400'
                    }`}>
                      {ver.score_after !== undefined && ver.score_after !== null ? `${ver.score_after.toFixed(1)}` : '評価待ち'}
                    </span>
                  </div>
                  {isRollback && (
                    <div className="col-span-2 sm:col-span-1 text-rose-300 font-semibold italic">
                      ⚠️ 劣化により自動ロールバックされました
                    </div>
                  )}
                </div>

                {ver.rollback_reason && (
                  <div className="mb-3 p-2 text-xs bg-rose-950/20 border border-rose-900/30 rounded-lg text-rose-300 font-mono">
                    <strong>理由:</strong> {ver.rollback_reason}
                  </div>
                )}

                <div className="bg-gray-900/60 p-3 rounded-lg font-mono text-xs text-gray-300 max-h-32 overflow-y-auto border border-gray-800">
                  {ver.content}
                </div>

                {/* ロールバック操作ボタン */}
                {!ver.is_active && !isRollback && (
                  <div className="mt-4 flex justify-end">
                    {rollingBackId === ver.id ? (
                      <div className="flex gap-2 w-full max-w-md">
                        <input
                          type="text"
                          placeholder="ロールバック理由を入力してください"
                          value={rollbackReason}
                          onChange={(e) => setRollbackReason(e.target.value)}
                          className="flex-grow px-3 py-1.5 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-200 focus:outline-none focus:border-violet-500"
                        />
                        <button
                          onClick={() => handleRollback(ver.id)}
                          disabled={loading}
                          className="px-4 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-sm font-medium transition-colors"
                        >
                          確定
                        </button>
                        <button
                          onClick={() => setRollingBackId(null)}
                          className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm font-medium transition-colors"
                        >
                          戻る
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setRollingBackId(ver.id)}
                        disabled={loading}
                        className="px-4 py-1.5 bg-rose-600/20 hover:bg-rose-600/40 border border-rose-500/30 text-rose-300 rounded-lg text-sm font-medium transition-colors"
                      >
                        ⏪ このバージョンへ強制ロールバック
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
