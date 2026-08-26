import React, { useEffect, useState } from 'react';
import { useTaskStore } from '@/store/useTaskStore';
import type { StreamConnectionState } from '@/api';
import type { TaskError } from '@/types/api';
import { TaskErrorDialog } from '@/components/dialogs/TaskErrorDialog';

interface TaskMonitorProps {
  logEndRef: React.RefObject<HTMLDivElement>;
  onStop: () => void;
  connectionState: StreamConnectionState;
}

function ConnectionIndicator({ state }: { state: StreamConnectionState }) {
  const config = {
    connecting: { color: 'text-yellow-400', label: '接続中...', pulse: true },
    connected: { color: 'text-emerald-400', label: '接続済み', pulse: false },
    reconnecting: { color: 'text-yellow-400', label: '再接続中...', pulse: true },
    closed: { color: 'text-gray-400', label: '切断', pulse: false },
    failed: { color: 'text-red-400', label: '接続失敗', pulse: false },
  }[state];

  return (
    <span className={`flex items-center gap-1.5 text-[0.7rem] font-mono ${config.pulse ? 'animate-pulse' : ''} ${config.color}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {config.label}
    </span>
  );
}

function ErrorBanner({ error, recoverable, resumeAvailable, onRetry, onResume, onClose }: {
  error: TaskError;
  recoverable: boolean;
  resumeAvailable: boolean;
  onRetry: () => void;
  onResume: () => void;
  onClose: () => void;
}) {
  return (
    <div className="p-4 border-b border-border bg-red-500/10">
      <div className="flex items-start gap-2 text-sm">
        <span className="text-red-400 mt-0.5">⚠</span>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-red-300">{error.message}</p>
          {error.detail && <p className="text-xs text-text-muted mt-0.5">{error.detail}</p>}
          <p className="text-xs text-text-muted mt-1">
            コード: <code className="font-mono bg-white/5 px-1 rounded">{error.code}</code>
            {' | '}
            発生: <code className="font-mono bg-white/5 px-1 rounded">{new Date(error.timestamp).toLocaleTimeString()}</code>
          </p>
        </div>
        <div className="flex gap-1 flex-wrap">
          {recoverable && (
            <button onClick={onRetry} className="btn btn-primary text-xs py-1 px-2">再試行</button>
          )}
          {resumeAvailable && (
            <button onClick={onResume} className="btn btn-secondary text-xs py-1 px-2">続きから再開</button>
          )}
          <button onClick={onClose} className="btn btn-ghost text-xs py-1 px-2">閉じる</button>
        </div>
      </div>
    </div>
  );
}

export function TaskMonitor({ logEndRef, onStop, connectionState }: TaskMonitorProps) {
  const { activeTaskId, taskStatus, clearTask } = useTaskStore();
  const [showErrorDialog, setShowErrorDialog] = useState(false);

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [taskStatus?.logs, logEndRef]);

  if (!activeTaskId || !taskStatus) return null;

  const hasTaskError = !!taskStatus.task_error;
  const isErrorState = connectionState === 'failed' || hasTaskError || !taskStatus.is_running && taskStatus.error;

  const handleRetry = () => {
    // Clear task so user can manually restart
    clearTask();
    setShowErrorDialog(false);
  };

  const handleResume = () => {
    // Clear task so user can manually restart (resume needs backend support)
    clearTask();
    setShowErrorDialog(false);
  };

  const handleCloseError = () => {
    setShowErrorDialog(false);
    // Clear the entire task when user dismisses error
    clearTask();
  };

  const handleShowErrorDialog = () => {
    setShowErrorDialog(true);
  };

  return (
    <>
      <div 
        className={`glass-panel animate-fade-in fixed bottom-8 right-8 w-[380px] max-h-[450px] flex flex-col z-[1000] task-monitor-panel ${
          isErrorState ? 'border-red-400' : 'border-accent-indigo'
        }`}
        role="log"
        aria-live="polite"
      >
        {/* Header */}
        <div className="p-4 border-b border-border flex justify-between items-center">
          <div className="flex flex-col gap-1">
            <h4 className={`text-[0.95rem] ${isErrorState ? 'text-red-300' : ''} ${!isErrorState ? 'animate-pulse' : ''}`}>
              {isErrorState ? '⚠ タスクエラー' : '⚡ タスク実行中...'}
            </h4>
            <div className="flex items-center gap-2">
              <span className="text-[0.7rem] text-text-muted font-mono">{activeTaskId}</span>
              <ConnectionIndicator state={connectionState} />
            </div>
          </div>
          <button 
            className="btn btn-danger transition-colors duration-200 py-[0.3rem] px-[0.6rem] text-xs"
            onClick={onStop}
            aria-label="タスクを停止"
          >
            停止
          </button>
        </div>

        {/* Error Banner */}
        {hasTaskError && (
          <ErrorBanner
            error={taskStatus.task_error!}
            recoverable={taskStatus.recoverable ?? true}
            resumeAvailable={!!taskStatus.resume_from_step}
            onRetry={handleRetry}
            onResume={handleResume}
            onClose={handleCloseError}
          />
        )}

        {/* Progress Indicator */}
        {!hasTaskError && (
          <div className="p-4 border-b border-border">
            <div className="flex justify-between text-[0.8rem] mb-1">
              <span>{taskStatus.message || '処理を実行中'}</span>
              <span>{taskStatus.current_step} / {taskStatus.total_steps || 1}話</span>
            </div>
            <div className="progress-track h-1.5 bg-white/10 rounded-sm">
              <div 
                className={`h-full transition-all duration-400 ${
                  connectionState === 'reconnecting' ? 'bg-yellow-400 animate-pulse' : 'bg-accent-indigo'
                }`}
                style={{ 
                  width: `${taskStatus.total_steps ? (taskStatus.current_step / taskStatus.total_steps) * 100 : 0}%`, 
                }} 
              />
            </div>
            {taskStatus.sub_message && (
              <p className="text-xs text-text-secondary mt-1.5">{taskStatus.sub_message}</p>
            )}
          </div>
        )}

        {hasTaskError && (
          <div className="p-4 border-b border-border text-center">
            <p className="text-sm text-text-secondary">進捗: {taskStatus.current_step} / {taskStatus.total_steps || 1} 話</p>
            <p className="text-xs text-text-muted mt-1">エラーが発生したため進捗バーを非表示にしています</p>
          </div>
        )}

        {/* Realtime Text Preview */}
        {!hasTaskError && taskStatus.streaming_text && (
          <div className="px-6 py-3 border-b border-border max-h-[120px] overflow-y-auto task-monitor-preview">
            <span className="text-[0.7rem] text-accent-indigo font-bold block mb-1">リアルタイム執筆プレビュー:</span>
            <div className="text-[0.8rem] text-gray-200 whitespace-pre-wrap leading-relaxed font-serif">
              {taskStatus.streaming_text}
            </div>
          </div>
        )}

        {hasTaskError && taskStatus.streaming_text && (
          <div className="px-6 py-3 border-b border-border max-h-[120px] overflow-y-auto task-monitor-preview bg-red-500/5">
            <span className="text-[0.7rem] text-red-400 font-bold block mb-1">エラー発生直前のプレビュー:</span>
            <div className="text-[0.8rem] text-gray-300 whitespace-pre-wrap leading-relaxed font-serif line-through">
              {taskStatus.streaming_text}
            </div>
          </div>
        )}

        {/* Scrolling log container */}
        <div className="flex-1 p-4 overflow-y-auto max-h-[200px] flex flex-col gap-1 task-monitor-log">
          {taskStatus.logs.map((log, index) => (
            <div key={log} className="text-[0.72rem] font-mono whitespace-pre-wrap leading-snug text-log-line">
              {log}
            </div>
          ))}
          <div ref={logEndRef} />
        </div>

        {/* Error detail button when no task_error but connection failed */}
        {!hasTaskError && connectionState === 'failed' && (
          <div className="p-4 border-t border-border text-center">
            <button
              onClick={handleShowErrorDialog}
              className="btn btn-ghost text-sm w-full"
            >
              接続エラーの詳細を表示
            </button>
          </div>
        )}
      </div>

      <TaskErrorDialog
        isOpen={showErrorDialog}
        onClose={handleCloseError}
        onRetry={handleRetry}
        onResume={handleResume}
        error={taskStatus.task_error ?? {
          code: 'CONNECTION_FAILED',
          message: 'SSE 接続が失敗しました',
          detail: 'サーバーとの接続が予期せず切断されました。ネットワーク環境を確認してください。',
          timestamp: new Date().toISOString(),
        }}
        recoverable={taskStatus.recoverable ?? true}
        resumeAvailable={!!taskStatus.resume_from_step}
      />
    </>
  );
}
