import React, { useEffect, useRef } from 'react';
import { usePipelineWebSocket, ConnectionStatus } from '../../hooks/usePipelineWebSocket';

interface PDCALiveMonitorProps {
  bookId: number | null;
}

export const PDCALiveMonitor: React.FC<PDCALiveMonitorProps> = ({ bookId }) => {
  const { status, scoreData, actionableDiffs, latestEvent } = usePipelineWebSocket(bookId);
  const audioPlayedRef = useRef(false);

  // Audio notification on completion (Step 44)
  useEffect(() => {
    if (latestEvent && (latestEvent.event_type === 'completed' || latestEvent.payload?.converged) && !audioPlayedRef.current) {
      try {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
        osc.frequency.setValueAtTime(880, ctx.currentTime + 0.15); // A5
        gain.gain.setValueAtTime(0.1, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.4);
        audioPlayedRef.current = true;
      } catch (e) {
        // AudioContext not allowed or supported without user gesture
      }
    }
  }, [latestEvent]);

  const renderStatusBadge = (s: ConnectionStatus) => {
    switch (s) {
      case 'connected':
        return <span className="px-2 py-0.5 text-xs bg-emerald-500/20 text-emerald-400 rounded-full flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>ライブ接続中</span>;
      case 'connecting':
        return <span className="px-2 py-0.5 text-xs bg-amber-500/20 text-amber-400 rounded-full">接続中...</span>;
      case 'reconnecting':
        return <span className="px-2 py-0.5 text-xs bg-amber-500/20 text-amber-400 rounded-full animate-pulse">再接続中...</span>;
      default:
        return <span className="px-2 py-0.5 text-xs bg-slate-500/20 text-slate-400 rounded-full">未接続</span>;
    }
  };

  const initial = scoreData.initialScore ?? 0;
  const current = scoreData.currentScore ?? initial;
  const delta = scoreData.delta ?? (current - initial);

  return (
    <div className="bg-slate-900/90 border border-slate-700/60 rounded-xl p-5 text-slate-100 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
        <h3 className="text-base font-bold flex items-center gap-2">
          <span>PDCA & リアルタイムライブモニター</span>
        </h3>
        {renderStatusBadge(status)}
      </div>

      {/* Score Improvement Grid (Step 39) */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-slate-800/60 p-3 rounded-lg border border-slate-700/40 text-center">
          <div className="text-xs text-slate-400 mb-1">初期スコア</div>
          <div className="text-2xl font-black text-slate-300">{initial > 0 ? initial.toFixed(1) : '---'}</div>
        </div>
        <div className="bg-slate-800/60 p-3 rounded-lg border border-slate-700/40 text-center">
          <div className="text-xs text-slate-400 mb-1">現在スコア</div>
          <div className="text-2xl font-black text-indigo-400">{current > 0 ? current.toFixed(1) : '---'}</div>
        </div>
        <div className="bg-slate-800/60 p-3 rounded-lg border border-slate-700/40 text-center">
          <div className="text-xs text-slate-400 mb-1">改善差分</div>
          <div className={`text-2xl font-black ${delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {delta > 0 ? `+${delta.toFixed(1)}` : delta.toFixed(1)}
          </div>
        </div>
      </div>

      {/* Specialists breakdown */}
      {scoreData.specialists && Object.keys(scoreData.specialists).length > 0 && (
        <div className="mb-6">
          <div className="text-xs font-semibold text-slate-400 mb-2">専門家オーディター評価</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(scoreData.specialists).map(([spec, score]) => (
              <div key={spec} className="bg-slate-800/40 px-3 py-2 rounded border border-slate-700/30 flex justify-between items-center text-xs">
                <span className="text-slate-300 truncate">{spec}</span>
                <span className="font-bold text-indigo-300">{Number(score).toFixed(1)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actionable Diffs Timeline (Step 40) */}
      <div>
        <div className="text-xs font-semibold text-slate-400 mb-2 flex items-center justify-between">
          <span>リアルタイム監査ディレクティブ</span>
          <span className="text-xs text-indigo-400">{actionableDiffs.length}件</span>
        </div>
        <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
          {actionableDiffs.length === 0 ? (
            <div className="text-xs text-slate-500 text-center py-6 bg-slate-800/20 rounded-lg border border-dashed border-slate-800">
              まだ監査ディレクティブはありません。執筆またはPDCAを実行してください。
            </div>
          ) : (
            actionableDiffs.map((diff, idx) => (
              <div key={idx} className="bg-slate-800/50 border border-slate-700/40 p-2.5 rounded-lg text-xs flex flex-col gap-1">
                <div className="flex justify-between items-center text-[10px] text-indigo-300 font-medium">
                  <span className="uppercase px-1.5 py-0.5 bg-indigo-500/20 rounded">{diff.dimension}</span>
                  <span className="text-slate-500">{new Date(diff.timestamp).toLocaleTimeString()}</span>
                </div>
                <div className="text-slate-200">{diff.directive}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
