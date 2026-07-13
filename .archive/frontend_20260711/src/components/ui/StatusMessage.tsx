import React from 'react';

interface StatusMessageProps {
  type: 'success' | 'error' | 'info' | 'warning';
  message: string;
  onClose?: () => void;
}

const typeStyles: Record<StatusMessageProps['type'], { bg: string; border: string; color: string; icon: string }> = {
  success: { bg: 'rgba(16, 185, 129, 0.1)', border: 'rgba(16, 185, 129, 0.35)', color: 'var(--accent-emerald)', icon: '✓' },
  error: { bg: 'rgba(244, 63, 94, 0.1)', border: 'rgba(244, 63, 94, 0.35)', color: 'var(--accent-rose)', icon: '✕' },
  info: { bg: 'rgba(99, 102, 241, 0.1)', border: 'rgba(99, 102, 241, 0.35)', color: 'var(--accent-indigo)', icon: 'ℹ' },
  warning: { bg: 'rgba(245, 158, 11, 0.1)', border: 'rgba(245, 158, 11, 0.35)', color: '#f59e0b', icon: '⚠' },
};

export function StatusMessage({ type, message, onClose }: StatusMessageProps) {
  const styles = typeStyles[type];

  return (
    <div
      role="alert"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        padding: '0.75rem 1rem',
        margin: '0 1rem',
        backgroundColor: styles.bg,
        border: `1px solid ${styles.border}`,
        borderLeft: `3px solid ${styles.color}`,
        borderRadius: '6px',
        color: '#e5e7eb',
        fontSize: '0.8rem',
      }}
    >
      <span style={{ color: styles.color, fontWeight: 'bold' }}>{styles.icon}</span>
      <span style={{ flex: 1, lineHeight: 1.4, wordBreak: 'break-word' }}>{message}</span>
      {onClose && (
        <button
          onClick={onClose}
          aria-label="閉じる"
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: '1rem',
            padding: '0 0.25rem',
            lineHeight: 1,
          }}
        >
          ×
        </button>
      )}
    </div>
  );
}
