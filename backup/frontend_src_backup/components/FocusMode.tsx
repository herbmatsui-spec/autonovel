import { useEffect } from 'react';

interface FocusModeProps {
  enabled: boolean;
}

export function FocusMode({ enabled }: FocusModeProps) {
  useEffect(() => {
    if (!enabled) return;

    const style = document.createElement('style');
    style.id = 'focus-mode-styles';
    style.textContent = `
      header, aside, .task-monitor-overlay, .easy-mode-dialog {
        display: none !important;
      }
      body {
        background: var(--bg-main) !important;
      }
      main {
        max-width: 800px !important;
        margin: 0 auto !important;
        padding: 2rem !important;
      }
    `;
    document.head.appendChild(style);

    return () => {
      const existing = document.getElementById('focus-mode-styles');
      if (existing) existing.remove();
    };
  }, [enabled]);

  if (!enabled) return null;

  return (
    <div className="fixed top-4 right-4 z-50">
      <button
        onClick={() => {/* toggled by parent */}}
        className="px-3 py-1.5 text-xs bg-secondary text-secondary-foreground rounded-lg"
      >
        集中執筆モード ON (明朝体)
      </button>
    </div>
  );
}