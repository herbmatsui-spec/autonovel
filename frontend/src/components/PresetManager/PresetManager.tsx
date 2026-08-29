import React, { useRef } from 'react';
import { useBookStore } from '../../store/useBookStore';

export const PresetManager: React.FC = () => {
  const { exportPreset, importPreset } = useBookStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleExport = () => {
    const json = exportPreset();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `axis-preset-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      importPreset(text);
    };
    reader.readAsText(file);
    // reset input
    e.target.value = '';
  };

  return (
    <div style={{ display: 'flex', gap: '8px', margin: '8px 0' }}>
      <button onClick={handleExport} style={{ padding: '4px 12px', background: '#17a2b8', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
        📤 プリセット出力
      </button>
      <button onClick={handleImportClick} style={{ padding: '4px 12px', background: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
        📥 プリセット読込
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />
    </div>
  );
};