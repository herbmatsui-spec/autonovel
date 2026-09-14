import React from 'react';
import { ProgressDelight } from './ProgressDelight';

interface ProgressDelightModalProps {
  isOpen: boolean;
  onClose?: () => void;
  onComplete?: () => void;
}

export const ProgressDelightModal: React.FC<ProgressDelightModalProps> = ({
  isOpen,
  onClose,
  onComplete,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-fadeIn">
      <div className="relative w-full max-w-2xl bg-slate-900 border border-slate-700/80 rounded-3xl p-6 shadow-2xl text-slate-100 overflow-hidden">
        {onClose && (
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-slate-400 hover:text-white p-2 rounded-lg touch-target"
          >
            ✕
          </button>
        )}
        <div className="text-center mb-6">
          <h2 className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
            🧠 AI思考プロセス・リアルタイム可視化
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            AI作家が物語のプロットと感情描写を構築している瞬間をお楽しみください
          </p>
        </div>

        <ProgressDelight isVisible={isOpen} {...(onComplete ? { onComplete } : {})} />
      </div>
    </div>
  );
};
