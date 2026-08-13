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
      className="flex items-center gap-[0.75rem] px-[1rem] py-[0.75rem] mx-[1rem] rounded-[6px] text-[0.8rem] text-[#e5e7eb]"
      style={{
        backgroundColor: styles.bg,
        border: `1px solid ${styles.border}`,
        borderLeft: `3px solid ${styles.color}`,
      }}
    >
      <span className="font-bold" style={{ color: styles.color }}>{styles.icon}</span>
      <span className="flex-1 leading-[1.4] break-words">{message}</span>
      {onClose && (
        <button
          onClick={onClose}
          aria-label="閉じる"
          className="bg-transparent border-none text-[var(--text-muted)] cursor-pointer text-[1rem] px-[0.25rem] leading-none"
        >
          ×
        </button>
      )}
    </div>
  );
}
