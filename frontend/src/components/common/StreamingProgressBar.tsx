import React, { useEffect, useRef, useState } from 'react';

type PhaseName = 'ContextBuilding' | 'Drafting' | 'Auditing' | 'Complete' | 'Error' | 'Connecting';
type ConnectionStatus = 'connecting' | 'connected' | 'receiving' | 'completed' | 'error' | 'disconnected';

interface ProgressBarProps {
  progress: number; // 0 - 100
  phaseName: PhaseName;
  elapsedSeconds?: number;
  connectionStatus?: ConnectionStatus;
  onElapsedChange?: (seconds: number) => void;
}

const PHASE_LABELS: Record<PhaseName, string> = {
  ContextBuilding: 'コンテキスト構築',
  Drafting: '本文執筆',
  Auditing: '二層監査',
  Complete: '完了',
  Error: 'エラー',
  Connecting: '接続中...',
};

const STATUS_LABELS: Record<ConnectionStatus, { label: string; className: string }> = {
  connecting: { label: '接続中', className: 'text-amber-400' },
  connected: { label: '接続済み', className: 'text-sky-400' },
  receiving: { label: '受信中', className: 'text-emerald-400 animate-pulse' },
  completed: { label: '完了', className: 'text-emerald-400' },
  error: { label: 'エラー', className: 'text-red-400' },
  disconnected: { label: '切断', className: 'text-slate-500' },
};

const PHASE_ORDER: PhaseName[] = ['ContextBuilding', 'Drafting', 'Auditing', 'Complete'];
const PHASE_WEIGHTS: Partial<Record<PhaseName, number>> = {
  ContextBuilding: 25,
  Drafting: 40,
  Auditing: 25,
  Complete: 10,
};

export const StreamingProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  phaseName,
  elapsedSeconds: initialElapsedSeconds = 0,
  connectionStatus = 'connecting',
  onElapsedChange,
}) => {
  const [elapsedSeconds, setElapsedSeconds] = useState(initialElapsedSeconds);
  const [displayPhase, setDisplayPhase] = useState<PhaseName>(phaseName);
  const [displayProgress, setDisplayProgress] = useState(progress);
  const intervalRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(Date.now());

  // Auto-count elapsed time when receiving
  useEffect(() => {
    if (connectionStatus === 'receiving' || connectionStatus === 'connected') {
      startTimeRef.current = Date.now() - elapsedSeconds * 1000;
      intervalRef.current = window.setInterval(() => {
        const newElapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
        setElapsedSeconds(newElapsed);
        onElapsedChange?.(newElapsed);
      }, 1000);
    } else if (connectionStatus === 'completed' || connectionStatus === 'error') {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [connectionStatus, elapsedSeconds, onElapsedChange]);

  // Smooth progress animation
  useEffect(() => {
    setDisplayProgress(progress);
  }, [progress]);

  useEffect(() => {
    setDisplayPhase(phaseName);
  }, [phaseName]);

  const phaseIndex = PHASE_ORDER.indexOf(displayPhase);
  const totalPhases = PHASE_ORDER.length;

  return (
    <div className="progress-card w-full p-4 bg-slate-800 rounded-lg border border-slate-700 shadow-sm">
      <div className="flex flex-col gap-2">
        <div className="flex justify-between items-center text-sm">
          <div className="flex items-center gap-3">
            <span className="font-semibold text-sky-400 min-w-[100px]">
              {PHASE_LABELS[displayPhase] || displayPhase}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded ${STATUS_LABELS[connectionStatus]?.className || 'text-slate-500'}`}>
              {STATUS_LABELS[connectionStatus]?.label || connectionStatus}
            </span>
          </div>
          <div className="flex items-center gap-4 text-slate-300">
            <span className="font-mono">{elapsedSeconds}s</span>
            <span className="font-mono">{Math.round(displayProgress)}%</span>
          </div>
        </div>

        {/* Phase indicator bar */}
        <div className="flex gap-1">
          {PHASE_ORDER.map((phase, i) => (
            <div
              key={phase}
              className={`flex-1 h-1.5 rounded transition-all duration-300 ${
                i < phaseIndex
                  ? 'bg-emerald-500'
                  : i === phaseIndex
                  ? 'bg-sky-500'
                  : 'bg-slate-700'
              }`}
            />
          ))}
        </div>

        {/* Main progress bar */}
        <div className="w-full bg-slate-700 h-2.5 rounded-full overflow-hidden relative">
          <div
            className="bg-gradient-to-r from-sky-500 to-emerald-500 h-2.5 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${Math.min(100, Math.max(0, displayProgress))}%` }}
          />
          {/* Phase markers */}
          {PHASE_ORDER.slice(0, -1).map((phase, i) => {
            const weight = PHASE_WEIGHTS[phase] ?? 0;
            const prevWeights = PHASE_ORDER.slice(0, i).reduce((sum, p) => sum + (PHASE_WEIGHTS[p] ?? 0), 0);
            const position = prevWeights + weight;
            return (
              <div
                key={phase}
                className="absolute top-full left-0 translate-x-[-50%] mt-1"
                style={{ left: `${position}%` }}
              >
                <div className="w-px h-2 bg-slate-600" />
              </div>
            );
          })}
        </div>

        {/* Phase labels */}
        <div className="flex justify-between text-xs text-slate-500 mt-1">
          {PHASE_ORDER.map((phase) => (
            <span key={phase} className={phase === displayPhase ? 'text-sky-400 font-medium' : ''}>
              {PHASE_LABELS[phase]}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};