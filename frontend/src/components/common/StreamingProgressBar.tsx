import React from 'react';

interface ProgressBarProps {
  progress: number; // 0 - 100
  phaseName: string; // 'ContextBuilding' | 'Drafting' | 'Auditing' | 'Complete'
  elapsedSeconds: number;
}

export const StreamingProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  phaseName,
  elapsedSeconds,
}) => {
  return (
    <div className="progress-card w-full p-4 bg-slate-800 rounded-lg border border-slate-700 shadow-sm">
      <div className="flex justify-between text-sm mb-1 text-slate-300">
        <span className="font-semibold text-sky-400">{phaseName}</span>
        <span>{elapsedSeconds}s ({Math.round(progress)}%)</span>
      </div>
      <div className="w-full bg-slate-700 h-2.5 rounded-full overflow-hidden">
        <div
          className="bg-sky-500 h-2.5 rounded-full transition-all duration-300 ease-out"
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
    </div>
  );
};