import React from 'react';
import { LoadingSpinner } from './LoadingSpinner';

interface LoadingStateProps {
  message?: string;
  icon?: string;
}

export function LoadingState({ message = '読み込み中...', icon }: LoadingStateProps) {
  return (
    <div
      className="flex flex-col justify-center items-center py-20"
      style={{ gap: '1rem', color: 'var(--text-muted)' }}
      role="status"
      aria-label={message}
    >
      <LoadingSpinner size="lg" />
      {icon && <span style={{ fontSize: '1.5rem' }}>{icon}</span>}
      {message && <p style={{ fontSize: '0.9rem' }}>{message}</p>}
    </div>
  );
}
