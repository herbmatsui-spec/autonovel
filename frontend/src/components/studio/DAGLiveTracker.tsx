import React from 'react';
import { usePipelineWebSocket } from '../../hooks/usePipelineWebSocket';

interface DAGLiveTrackerProps {
  bookId: number | null;
}

export const DAGLiveTracker: React.FC<DAGLiveTrackerProps> = ({ bookId }) => {
  const { tasks } = usePipelineWebSocket(bookId);

  const taskList = Object.entries(tasks);

  return (
    <div className="bg-slate-900/90 border border-slate-700/60 rounded-xl p-5 text-slate-100 shadow-xl backdrop-blur-md">
      <h3 className="text-base font-bold mb-4 pb-3 border-b border-slate-800 flex items-center justify-between">
        <span>DAG ライブタスクトラッカー</span>
        <span className="text-xs text-indigo-400">{taskList.length} ノード</span>
      </h3>

      <div className="space-y-3">
        {taskList.length === 0 ? (
          <div className="text-xs text-slate-500 text-center py-6 bg-slate-800/20 rounded-lg border border-dashed border-slate-800">
            実行中のDAGタスクはありません。
          </div>
        ) : (
          taskList.map(([taskId, data]) => {
            const state = data.state;
            let badgeColor = 'bg-slate-700 text-slate-300';
            if (state === 'running') badgeColor = 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 animate-pulse';
            else if (state === 'completed' || state === 'success') badgeColor = 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
            else if (state === 'failed' || state === 'error') badgeColor = 'bg-rose-500/20 text-rose-300 border border-rose-500/40';
            else if (state === 'retry') badgeColor = 'bg-amber-500/20 text-amber-300 border border-amber-500/40';

            return (
              <div key={taskId} className="bg-slate-800/60 border border-slate-700/50 p-3 rounded-lg flex items-center justify-between">
                <div>
                  <div className="text-xs font-bold text-slate-200">{taskId}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    {data.payload?.description || data.payload?.node_type || 'タスク実行中'}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${badgeColor}`}>
                    {state}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
