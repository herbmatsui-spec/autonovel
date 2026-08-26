import { useState } from 'react';
import { createPortal } from 'react-dom';
import type { TaskError } from '@/types/api';

interface TaskErrorDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onRetry: () => void;
  onResume?: () => void;
  error: TaskError | null;
  recoverable: boolean;
  resumeAvailable: boolean;
}

export function TaskErrorDialog({
  isOpen,
  onClose,
  onRetry,
  onResume,
  error,
  recoverable,
  resumeAvailable,
}: TaskErrorDialogProps) {
  const [showDetail, setShowDetail] = useState(false);

  if (!isOpen || !error) return null;

  const copyErrorDetails = () => {
    const details = JSON.stringify(error, null, 2);
    navigator.clipboard.writeText(details).then(() => {
      toast('エラー詳細をコピーしました');
    }).catch(() => {
      toast('コピーに失敗しました');
    });
  };

  const toast = (message: string) => {
    const el = document.createElement('div');
    el.textContent = message;
    el.style.cssText = `
      position: fixed; bottom: 1rem; left: 50%; transform: translateX(-50%);
      background: var(--bg-card); border: 1px solid var(--border);
      padding: 0.5rem 1rem; border-radius: 0.5rem; z-index: 10000;
      font-size: 0.8rem; color: var(--text);
    `;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2000);
  };

  const content = (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="task-error-title"
      className="fixed inset-0 z-[2000] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose();
      }}
      tabIndex={-1}
    >
      <div className="glass-panel w-full max-w-md rounded-xl overflow-hidden animate-slide-up">
        <div className="p-4 border-b border-border flex justify-between items-center">
          <h3 id="task-error-title" className="text-lg font-bold text-red-400 flex items-center gap-2">
            <span className="text-xl">⚠</span>
            タスクエラー
          </h3>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text p-1 rounded transition-colors"
            aria-label="閉じる"
          >
            ✕
          </button>
        </div>

        <div className="p-4 space-y-4">
          <div className="space-y-2">
            <p className="text-sm font-medium">{error.message}</p>
            {error.detail && (
              <p className="text-xs text-text-muted">{error.detail}</p>
            )}
            <div className="flex items-center gap-2 text-xs text-text-muted">
              <span>コード: <code className="font-mono bg-white/5 px-1 rounded">{error.code}</code></span>
              <span>発生時刻: <code className="font-mono bg-white/5 px-1 rounded">{new Date(error.timestamp).toLocaleString()}</code></span>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setShowDetail(!showDetail)}
            className="w-full text-left text-xs text-text-secondary hover:text-text p-2 rounded bg-white/5 transition-colors flex justify-between items-center"
          >
            <span>技術的詳細 {showDetail ? '▲' : '▼'}</span>
          </button>

          {showDetail && (
            <details className="bg-white/5 rounded p-3 text-[0.65rem] font-mono text-text-secondary max-h-40 overflow-auto">
              <summary className="cursor-pointer mb-1">JSON 詳細</summary>
              <pre>{JSON.stringify(error, null, 2)}</pre>
            </details>
          )}

          <div className="flex gap-2 pt-2">
            {recoverable && (
              <button
                onClick={() => { onRetry(); onClose(); }}
                className="btn btn-primary flex-1 py-2"
              >
                再試行
              </button>
            )}
            {resumeAvailable && onResume && (
              <button
                onClick={() => { onResume(); onClose(); }}
                className="btn btn-secondary flex-1 py-2"
              >
                続きから再開
              </button>
            )}
            <button
              onClick={copyErrorDetails}
              className="btn btn-ghost flex-1 py-2"
            >
              詳細コピー
            </button>
            <button
              onClick={onClose}
              className="btn btn-ghost flex-1 py-2"
            >
              閉じる
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return createPortal(content, document.body);
}