import React, { useCallback, useState } from 'react';
import { useBookStore } from '../../store/useBookStore';
import { AxisType } from '../../types/api';

interface PromptCompileResponse {
  compiled: string;
}

export const PromptPreview: React.FC = () => {
  const { axisSelections, setAxisSelection } = useBookStore();
  const [compiled, setCompiled] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCompile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const axesPayload: Record<string, any> = {};
      for (const [key, axis] of Object.entries(axisSelections)) {
        axesPayload[key] = { value: axis.value, locked: axis.locked, default: axis.defaultValue };
      }
      const outputMode = axisSelections.output_mode?.value as string || 'novel';
      const resp = await fetch('/api/prompt/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': '' }, // API key handled by auth middleware
        body: JSON.stringify({ output_mode: outputMode, axes: axesPayload }),
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: PromptCompileResponse = await resp.json();
      setCompiled(data.compiled);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [axisSelections]);

  return (
    <div style={{ border: '1px solid #ccc', borderRadius: '4px', padding: '8px', marginTop: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <strong>コンパイル済みプロンプト プレビュー</strong>
        <button onClick={handleCompile} disabled={loading} style={{ padding: '4px 12px' }}>
          {loading ? '生成中...' : '再コンパイル'}
        </button>
      </div>
      {error && <div style={{ color: 'red', marginBottom: '8px' }}>Error: {error}</div>}
      <pre
        style={{
          background: '#f5f5f5',
          padding: '8px',
          borderRadius: '4px',
          overflow: 'auto',
          maxHeight: '300px',
          fontSize: '0.85em',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {compiled || '（まだ生成されていません）'}
      </pre>
    </div>
  );
};