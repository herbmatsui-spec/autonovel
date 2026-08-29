import React, { useCallback } from 'react';
import { useBookStore } from '../../store/useBookStore';
import { AxisType, AxisValue } from '../../types/api';

interface AxisSelectorProps {
  axis: AxisType;
  label: string;
  options?: string[]; // optional predefined options for select
  renderCustom?: (value: AxisValue, onChange: (v: AxisValue) => void) => React.ReactNode;
}

export const AxisSelector: React.FC<AxisSelectorProps> = ({
  axis,
  label,
  options,
  renderCustom,
}) => {
  const { axisSelections, setAxisSelection, setAxisLock, resetAxis } = useBookStore();
  const { value, locked, defaultValue } = axisSelections[axis];

  const handleChange = (newVal: AxisValue) => {
    if (!locked) setAxisSelection(axis, newVal);
  };

  const handleLockToggle = () => setAxisLock(axis, !locked);
  const handleReset = () => resetAxis(axis);

  const handleRandom = useCallback(async () => {
    if (locked) return;
    try {
      const resp = await fetch(`/api/prompt/randomize/${axis}`);
      if (resp.ok) {
        const data = await resp.json();
        setAxisSelection(axis, data.value);
      }
    } catch (e) {
      console.error('Randomize failed', e);
    }
  }, [axis, locked, setAxisSelection]);

  const inputStyle = {
    opacity: locked ? 0.5 : 1,
    pointerEvents: locked ? 'none' : 'auto',
    transition: 'opacity 0.2s',
  };

  return (
    <div style={{ border: '1px solid #ccc', padding: '8px', margin: '8px 0', borderRadius: '4px', background: locked ? '#f9f9f9' : 'white' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
        <strong>{label}</strong>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button onClick={handleLockToggle} title={locked ? 'Unlock' : 'Lock'} style={{ fontSize: '1.2em' }}>
            {locked ? '🔒' : '🔓'}
          </button>
          <button onClick={handleRandom} title="Randomize" disabled={locked} style={{ fontSize: '1.2em' }}>
            🎲
          </button>
          <button onClick={handleReset} title="Reset to default" disabled={locked} style={{ fontSize: '1.2em' }}>
            ↩
          </button>
        </div>
      </div>
      {locked && <div style={{ opacity: 0.5, fontSize: '0.85em', color: '#666', marginBottom: '4px' }}>Locked</div>}
      <div style={inputStyle}>
        {renderCustom ? (
          renderCustom(value, handleChange)
        ) : options ? (
          <select value={value as string} onChange={(e) => handleChange(e.target.value)} disabled={locked} style={{ width: '100%', padding: '4px' }}>
            <option value="">-- select --</option>
            {options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        ) : (
          <textarea
            value={typeof value === 'string' ? value : ''}
            onChange={(e) => handleChange(e.target.value)}
            disabled={locked}
            rows={3}
            style={{ width: '100%', fontFamily: 'monospace', fontSize: '0.9em', padding: '4px' }}
          />
        )}
      </div>
    </div>
  );
};