import React, { useEffect } from 'react';
import { sseClient } from '../lib/sseClient';
import { useAgentLiveStore } from '../store/useAgentLiveStore';

interface AgentDashboardProps {
  apiKey?: string;
  className?: string;
}

const AGENT_CONFIGS: Record<string, { label: string; icon: string; color: string }> = {
  PlotPlanner: { label: 'プロットプランナー', icon: '📝', color: 'border-blue-500 text-blue-400 bg-blue-500/10' },
  PlotCritic: { label: 'プロット監査編集長', icon: '🧐', color: 'border-amber-500 text-amber-400 bg-amber-500/10' },
  ContextBuilder: { label: '設定資料・RAG抽出', icon: '📚', color: 'border-indigo-500 text-indigo-400 bg-indigo-500/10' },
  WriterActor: { label: '執筆作家エージェント', icon: '✍️', color: 'border-emerald-500 text-emerald-400 bg-emerald-500/10' },
  WriterCritic: { label: '文脈・整合性監査', icon: '🔍', color: 'border-purple-500 text-purple-400 bg-purple-500/10' },
  PacingReviewer: { label: 'テンポ・構成レビュアー', icon: '⚡', color: 'border-cyan-500 text-cyan-400 bg-cyan-500/10' },
  CharacterSupervisor: { label: 'キャラクター監修', icon: '🎭', color: 'border-pink-500 text-pink-400 bg-pink-500/10' },
  ReviewSynthesizer: { label: '最終推敲シンセサイザー', icon: '✨', color: 'border-yellow-500 text-yellow-400 bg-yellow-500/10' },
};

export const AgentDashboard: React.FC<AgentDashboardProps> = ({ apiKey, className = '' }) => {
  const {
    isConnected,
    currentAgent,
    overallProgress,
    statusMessage,
    logs,
    setConnected,
    handleAgentStatus,
    handlePipelineProgress,
    clearLogs,
  } = useAgentLiveStore();

  useEffect(() => {
    sseClient.connect(apiKey);

    const unsubscribe = sseClient.subscribe((eventType, data) => {
      if (eventType === 'connection_status') {
        setConnected(data.status === 'connected');
      } else if (eventType === 'agent_status') {
        handleAgentStatus(data);
      } else if (eventType === 'pipeline_progress') {
        handlePipelineProgress(data);
      }
    });

    return () => {
      unsubscribe();
    };
  }, [apiKey, setConnected, handleAgentStatus, handlePipelineProgress]);

  const activeConfig = currentAgent ? AGENT_CONFIGS[currentAgent] || { label: currentAgent, icon: '🤖', color: 'border-primary-500 text-primary-400 bg-primary-500/10' } : null;

  return (
    <div className={`flex flex-col bg-slate-900/90 border border-slate-800 rounded-xl backdrop-blur-md overflow-hidden shadow-2xl p-5 ${className}`}>
      {/* ヘッダー */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <span className="animate-pulse">🔮</span>
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
              LangGraph 自律エージェント協調モニター
            </h3>
            <p className="text-xs text-slate-400">マルチエージェントの思考・推敲ループをリアルタイム表示</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${isConnected ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border-rose-500/30'}`}>
            <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${isConnected ? 'bg-emerald-400 animate-ping' : 'bg-rose-400'}`} />
            {isConnected ? 'LIVE CONNECTED' : 'OFFLINE'}
          </span>
          {logs.length > 0 && (
            <button
              onClick={clearLogs}
              className="text-xs text-slate-500 hover:text-slate-300 transition-colors px-2 py-1 rounded bg-slate-800/50 hover:bg-slate-800"
            >
              クリア
            </button>
          )}
        </div>
      </div>

      {/* 現在のステータス & 進捗バー */}
      <div className="mb-4 bg-slate-950/60 border border-slate-800/80 rounded-lg p-4">
        <div className="flex items-center justify-between text-xs mb-2">
          <span className="text-slate-400 font-medium">パイプライン総合進捗</span>
          <span className="text-indigo-400 font-bold font-mono">{overallProgress}%</span>
        </div>
        <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden mb-3">
          <div
            className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 h-full transition-all duration-500 ease-out"
            style={{ width: `${overallProgress}%` }}
          />
        </div>

        {/* アクティブエージェント表示 */}
        <div className="flex items-center gap-3">
          {activeConfig ? (
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-md border text-xs font-semibold ${activeConfig.color} animate-pulse`}>
              <span>{activeConfig.icon}</span>
              <span>{activeConfig.label}</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-slate-700 text-slate-400 bg-slate-800/40 text-xs">
              <span>💤</span>
              <span>エージェント待機中</span>
            </div>
          )}
          <span className="text-xs text-slate-300 truncate font-mono">{statusMessage}</span>
        </div>
      </div>

      {/* 思考・推敲タイムライン */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">思考・監査ログタイムライン</span>
        <div className="flex-1 overflow-y-auto space-y-2 max-h-60 pr-1 select-text scrollbar-thin scrollbar-thumb-slate-700">
          {logs.length === 0 ? (
            <div className="text-center py-6 text-xs text-slate-500">
              エージェントの実行が開始されると、リアルタイムの推敲プロセスがここに表示されます。
            </div>
          ) : (
            logs.map((log) => {
              const conf = AGENT_CONFIGS[log.agent] || { label: log.agent, icon: '🤖', color: 'border-slate-700 text-slate-300' };
              return (
                <div
                  key={log.id}
                  className="flex items-start gap-2.5 p-2 rounded bg-slate-950/40 border border-slate-800/50 hover:border-slate-700 text-xs transition-colors"
                >
                  <span className="text-[10px] text-slate-500 font-mono mt-0.5 whitespace-nowrap">{log.timestamp}</span>
                  <span className="px-1.5 py-0.5 rounded border text-[10px] whitespace-nowrap" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
                    {conf.icon} {conf.label}
                  </span>
                  <span className="text-slate-300 flex-1">{log.message}</span>
                  {log.score !== undefined && (
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${log.isApproved !== false ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                      Score: {(log.score * 100).toFixed(0)}
                    </span>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
