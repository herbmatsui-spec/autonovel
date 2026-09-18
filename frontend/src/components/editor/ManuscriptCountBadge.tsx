import React from 'react';
import { CountMode, ManuscriptCountResult } from '../../types/manuscript';

export interface ManuscriptCountBadgeProps {
  count: ManuscriptCountResult;
  mode: CountMode;
  onModeChange: (mode: CountMode) => void;
  compact?: boolean;
}

export const ManuscriptCountBadge: React.FC<ManuscriptCountBadgeProps> = ({
  count,
  mode,
  onModeChange,
  compact = false,
}) => {
  const getDisplayText = () => {
    switch (mode) {
      case 'body':
        return `本文 ${count.body.toLocaleString()} 字`;
      case 'withRuby':
        return `ルビ込 ${count.withRuby.toLocaleString()} 字`;
      case 'publishing':
        return `原稿 ${count.publishing.toFixed(1)} 枚 (${count.pages}枚)`;
      default:
        return `${count.body.toLocaleString()} 字`;
    }
  };

  const getTooltip = () => {
    return `純本文: ${count.body.toLocaleString()}字 | ルビ込: ${count.withRuby.toLocaleString()}字 | 400字原稿: 約${count.pages}枚 (読了: 約${count.readingTimeMinutes}分)`;
  };

  return (
    <div
      className="manuscript-count-badge"
      role="group"
      aria-label="文字数カウントモード"
      title={getTooltip()}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        background: 'var(--bg-card, rgba(255, 255, 255, 0.05))',
        border: '1px solid var(--border-color, rgba(255, 255, 255, 0.1))',
        borderRadius: '6px',
        padding: compact ? '2px 6px' : '3px 8px',
        fontSize: compact ? '0.75rem' : '0.82rem',
        gap: '6px',
        userSelect: 'none',
      }}
    >
      <div
        style={{
          display: 'flex',
          background: 'var(--bg-secondary, rgba(0, 0, 0, 0.2))',
          borderRadius: '4px',
          padding: '1px',
          gap: '2px',
        }}
      >
        <button
          type="button"
          onClick={() => onModeChange('body')}
          aria-pressed={mode === 'body'}
          style={{
            background: mode === 'body' ? 'var(--accent-primary, #6366f1)' : 'transparent',
            color: mode === 'body' ? '#fff' : 'var(--text-muted, #94a3b8)',
            border: 'none',
            borderRadius: '3px',
            padding: '1px 5px',
            fontSize: '0.7rem',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          data-testid="mode-body-btn"
        >
          本文
        </button>
        <button
          type="button"
          onClick={() => onModeChange('withRuby')}
          aria-pressed={mode === 'withRuby'}
          style={{
            background: mode === 'withRuby' ? 'var(--accent-primary, #6366f1)' : 'transparent',
            color: mode === 'withRuby' ? '#fff' : 'var(--text-muted, #94a3b8)',
            border: 'none',
            borderRadius: '3px',
            padding: '1px 5px',
            fontSize: '0.7rem',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          data-testid="mode-with-ruby-btn"
        >
          ルビ込
        </button>
        <button
          type="button"
          onClick={() => onModeChange('publishing')}
          aria-pressed={mode === 'publishing'}
          style={{
            background: mode === 'publishing' ? 'var(--accent-primary, #6366f1)' : 'transparent',
            color: mode === 'publishing' ? '#fff' : 'var(--text-muted, #94a3b8)',
            border: 'none',
            borderRadius: '3px',
            padding: '1px 5px',
            fontSize: '0.7rem',
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          data-testid="mode-publishing-btn"
        >
          出版用
        </button>
      </div>

      <span
        style={{
          fontWeight: 600,
          color: 'var(--text-primary, #e2e8f0)',
          minWidth: compact ? '70px' : '90px',
        }}
        data-testid="manuscript-count-value"
      >
        {getDisplayText()}
      </span>
    </div>
  );
};
