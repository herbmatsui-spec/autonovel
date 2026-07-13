import React, { useEffect, useRef } from 'react';
import { useTaskStore } from '../store/useTaskStore';
import { stopTask } from '../api';

export function TaskMonitor() {
  const { activeTaskId, taskStatus } = useTaskStore();
  const { setActiveTaskId, setTaskStatus } = useTaskStore();
  const logEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [taskStatus?.logs]);

  const handleStopTask = async () => {
    if (!activeTaskId) return;
    try {
      await stopTask(activeTaskId);
      setActiveTaskId(null);
      setTaskStatus(null);
    } catch (e) {
      console.error('Stop task failed:', e);
      setActiveTaskId(null);
      setTaskStatus(null);
    }
  };

  if (!activeTaskId || !taskStatus) return null;

  return (
    <div 
      className="glass-panel animate-fade-in fixed bottom-8 right-8 w-[380px] max-h-[450px] flex flex-col z-[1000] border-accent-indigo task-monitor-panel"
      role="log"
      aria-live="polite"
    >
      {/* Header */}
      <div className="p-4 border-b border-border flex justify-between items-center">
        <div>
          <h4 className="text-[0.95rem] animate-pulse">⚡ タスク実行中...</h4>
          <span className="text-[0.7rem] text-text-muted font-mono">{activeTaskId}</span>
        </div>
        <button 
          className="btn btn-danger transition-colors duration-200 py-[0.3rem] px-[0.6rem] text-xs" 
          onClick={handleStopTask} 
          aria-label="タスクを停止"
        >
          停止
        </button>
      </div>

      {/* Progress Indicator */}
      <div className="p-4 border-b border-border">
        <div className="flex justify-between text-[0.8rem] mb-1">
          <span>{taskStatus.message || '処理を実行中'}</span>
          <span>{taskStatus.current_step} / {taskStatus.total_steps || 1}話</span>
        </div>
        <div className="progress-track h-1.5 bg-white/10 rounded-sm">
          <div 
            className="h-full bg-accent-indigo [transition:width_0.4s]"
            style={{ 
              width: `${taskStatus.total_steps ? (taskStatus.current_step / taskStatus.total_steps) * 100 : 0}%`, 
            }} 
          />
        </div>
        {taskStatus.sub_message && (
          <p className="text-xs text-text-secondary mt-1.5">{taskStatus.sub_message}</p>
        )}
      </div>

      {/* Realtime Text Preview */}
      {taskStatus.streaming_text && (
        <div className="px-6 py-3 border-b border-border max-h-[120px] overflow-y-auto task-monitor-preview">
          <span className="text-[0.7rem] text-accent-indigo font-bold block mb-1">リアルタイム執筆プレビュー:</span>
          <div className="text-[0.8rem] text-gray-200 whitespace-pre-wrap leading-relaxed font-serif">
            {taskStatus.streaming_text}
          </div>
        </div>
      )}

      {/* Scrolling log container */}
      <div className="flex-1 p-4 overflow-y-auto max-h-[200px] flex flex-col gap-1 task-monitor-log">
        {taskStatus.logs.map((log, index) => (
          <div key={index} className="text-[0.72rem] font-mono whitespace-pre-wrap leading-snug text-log-line">
            {log}
          </div>
        ))}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}