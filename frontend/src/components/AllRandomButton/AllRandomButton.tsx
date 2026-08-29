import React, { useCallback } from 'react';
import { useBookStore } from '../../store/useBookStore';
import { AxisType } from '../../types/api';

const ALL_AXES: AxisType[] = [
  'theme',
  'genre',
  'worldview',
  'audience',
  'era',
  'ending_style',
  'narrator',
  'characters',
  'universal_input',
  'supplemental_note',
  // output_mode is usually not randomized globally
];

export const AllRandomButton: React.FC = () => {
  const { axisSelections, setAxisSelection } = useBookStore();

  const handleAllRandom = useCallback(async () => {
    for (const axis of ALL_AXES) {
      if (axisSelections[axis].locked) continue;
      try {
        const resp = await fetch(`/api/prompt/randomize/${axis}`);
        if (resp.ok) {
          const data = await resp.json();
          setAxisSelection(axis, data.value);
        }
      } catch (e) {
        console.error(`Randomize ${axis} failed`, e);
      }
    }
  }, [axisSelections, setAxisSelection]);

  return (
    <button
      onClick={handleAllRandom}
      style={{
        padding: '8px 16px',
        background: '#28a745',
        color: '#fff',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontWeight: 'bold',
      }}
    >
      🎲 全項目ランダム
    </button>
  );
};