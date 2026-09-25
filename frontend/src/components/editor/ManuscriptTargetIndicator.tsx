import React from 'react';
import { ManuscriptCountResult, ManuscriptTargetPreset } from '../../types/manuscript';
import { MANUSCRIPT_PRESETS } from '../../constants/manuscript';
import { checkTarget } from '../../utils/manuscriptCount';

export interface ManuscriptTargetIndicatorProps {
  count: ManuscriptCountResult;
  selectedPresetId: string;
  onPresetChange: (presetId: string) => void;
  customTargetChars?: number;
  onCustomTargetChange?: (chars: number) => void;
}

export const ManuscriptTargetIndicator: React.FC<ManuscriptTargetIndicatorProps> = ({
  count,
  selectedPresetId,
  onPresetChange,
  customTargetChars = 10000,
  onCustomTargetChange,
}) => {
  const currentPreset =
    MANUSCRIPT_PRESETS.find((p) => p.id === selectedPresetId) || MANUSCRIPT_PRESETS[0];

  const activePreset: ManuscriptTargetPreset =
    currentPreset.id === 'custom'
      ? {
          ...currentPreset,
          targetChars: customTargetChars,
          targetPages: Math.ceil(customTargetChars / 400),
        }
      : currentPreset;

  const targetState =
    activePreset.targetChars > 0 ? checkTarget(count, activePreset) : null;

  const getProgressBarColor = () => {
    if (!targetState) return 'var(--accent-primary, #6366f1)';
    if (targetState.isOver || targetState.isMaxOver) return 'var(--accent-danger, #ef4444)';
    if (targetState.isWarning) return 'var(--accent-yellow, #eab308)';
    return 'var(--accent-green, #10b981)';
  };

  const percent = targetState
    ? Math.min(100, Math.round(targetState.ratio * 100))
    : 0;

  return (
    <div
      className="manuscript-target-indicator"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        fontSize: '0.8rem',
        color: 'var(--text-muted, #94a3b8)',
        flexWrap: 'wrap',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
        <span>🎯 目標規定:</span>
        <select
          value={selectedPresetId}
          onChange={(e) => onPresetChange(e.target.value)}
          style={{
            background: 'var(--bg-secondary, #1e293b)',
            color: 'var(--text-primary, #e2e8f0)',
            border: '1px solid var(--border-color, rgba(255, 255, 255, 0.15))',
            borderRadius: '4px',
            padding: '2px 6px',
            fontSize: '0.78rem',
            cursor: 'pointer',
          }}
          data-testid="preset-select"
        >
          {MANUSCRIPT_PRESETS.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {activePreset.id === 'custom' && onCustomTargetChange && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <input
            type="number"
            min={100}
            step={500}
            value={customTargetChars}
            onChange={(e) => onCustomTargetChange(Number(e.target.value))}
            style={{
              width: '80px',
              background: 'var(--bg-secondary, #1e293b)',
              color: 'var(--text-primary, #e2e8f0)',
              border: '1px solid var(--border-color, rgba(255, 255, 255, 0.15))',
              borderRadius: '4px',
              padding: '2px 4px',
              fontSize: '0.78rem',
            }}
          />
          <span>字</span>
        </div>
      )}

      {targetState && activePreset.targetChars > 0 && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            minWidth: '220px',
            flex: '1 1 auto',
          }}
        >
          <div
            role="progressbar"
            aria-valuenow={count.body}
            aria-valuemin={0}
            aria-valuemax={activePreset.targetChars}
            style={{
              flex: 1,
              height: '6px',
              background: 'rgba(255, 255, 255, 0.1)',
              borderRadius: '3px',
              overflow: 'hidden',
              minWidth: '80px',
            }}
          >
            <div
              style={{
                width: `${percent}%`,
                height: '100%',
                background: getProgressBarColor(),
                transition: 'width 0.2s ease, background 0.2s ease',
              }}
            />
          </div>

          <span
            style={{
              fontWeight: 500,
              color: getProgressBarColor(),
              whiteSpace: 'nowrap',
            }}
            data-testid="target-progress-text"
          >
            {targetState.isMaxOver ? (
              <span>上限 {activePreset.maxPages}枚 超過 (現在 {count.pages}枚)</span>
            ) : targetState.isOver ? (
              <span>目標超過 +{(count.body - activePreset.targetChars).toLocaleString()} 字</span>
            ) : targetState.isWarning ? (
              <span>
                {count.body.toLocaleString()} / {activePreset.targetChars.toLocaleString()} 字 ({percent}%)
                (あと {targetState.remainingChars.toLocaleString()} 字)
              </span>
            ) : (
              <span>
                {count.body.toLocaleString()} / {activePreset.targetChars.toLocaleString()} 字 ({percent}%)
              </span>
            )}
          </span>
        </div>
      )}
    </div>
  );
};
