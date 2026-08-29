import React from 'react';
import { useBookStore } from '../../store/useBookStore';
import { AxisType } from '../../types/api';

const MODES: { key: string; label: string }[] = [
  { key: '4koma', label: '4コマ' },
  { key: '4koma_scenario', label: '4コマシナリオ' },
  { key: 'short_short', label: 'ショート' },
  { key: 'novel', label: '小説' },
  { key: 'medium', label: '中編' },
  { key: 'long_10000', label: '長編' },
  { key: 'scenario', label: '脚本' },
  { key: 'manga', label: '漫画' },
  { key: 'essay', label: 'エッセイ' },
  { key: 'poem', label: '詩' },
  { key: 'fairy', label: '童話' },
  { key: 'letter', label: '手紙' },
  { key: 'diary', label: '日記' },
  { key: 'documentary', label: 'ドキュメンタリー' },
  { key: 'radio', label: 'ラジオドラマ' },
];

export const OutputModeSelector: React.FC = () => {
  const { axisSelections, setAxisSelection } = useBookStore();
  const current = axisSelections[AxisType.OUTPUT_MODE]?.value as string | null;

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', margin: '8px 0' }}>
      {MODES.map((m) => (
        <button
          key={m.key}
          onClick={() => setAxisSelection(AxisType.OUTPUT_MODE, m.key)}
          style={{
            padding: '4px 8px',
            borderRadius: '4px',
            border: '1px solid #ccc',
            background: current === m.key ? '#007bff' : '#fff',
            color: current === m.key ? '#fff' : '#000',
            cursor: 'pointer',
            fontSize: '0.85em',
          }}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
};