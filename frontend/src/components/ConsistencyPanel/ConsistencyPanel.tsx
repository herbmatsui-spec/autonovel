import React, { useState } from 'react';
import { useConsistencyCheck } from '@/hooks/useConsistencyCheck';

export const ConsistencyPanel: React.FC = () => {
  const { findings, summary, loading, error, runCheck, dismiss } = useConsistencyCheck();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  if (!findings.length && !loading && !error) {
    return (
      <div style={{ padding: '16px', color: '#666' }}>
        整合性チェックを実行してください
      </div>
    );
  }

  const toggleExpand = (key: string) => {
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleDismiss = (f: any) => {
    if (window.confirm(`この指摘を却下しますか？\n理由: ${prompt('理由を入力:') || '意図的'}`)) {
      dismiss(f.key(), '意図的');
    }
  };

  return (
    <div style={{ padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
        <h3>整合性チェック結果</h3>
        <button onClick={() => runCheck()} disabled={loading} style={{ padding: '6px 12px' }}>
          {loading ? 'チェック中...' : '再チェック'}
        </button>
      </div>

      {error && <div style={{ color: 'red', marginBottom: '8px' }}>Error: {error}</div>}

      <div style={{ display: 'flex', gap: '16px', marginBottom: '12px', fontSize: '14px' }}>
        <span style={{ color: '#dc3545' }}>高: {summary.high}</span>
        <span style={{ color: '#ffc107' }}>中: {summary.medium}</span>
        <span style={{ color: '#17a2b8' }}>低: {summary.low}</span>
      </div>

      {findings.map((f, idx) => {
        const key = f.key || `${f.category}-${idx}`;
        const isExp = expanded[key];
        return (
          <div
            key={key}
            style={{
              border: '1px solid #ddd',
              borderLeft: `4px solid ${f.severity === 'high' ? '#dc3545' : f.severity === 'medium' ? '#ffc107' : '#17a2b8'}`,
              borderRadius: '4px',
              marginBottom: '8px',
              background: '#fff',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '8px 12px',
                cursor: 'pointer',
                background: '#f8f9fa',
              }}
              onClick={() => toggleExpand(key)}
            >
              <span style={{ fontWeight: 'bold', textTransform: 'capitalize' }}>
                {f.category}
              </span>
              <span
                style={{
                  background:
                    f.severity === 'high'
                      ? '#dc3545'
                      : f.severity === 'medium'
                      ? '#ffc107'
                      : '#17a2b8',
                  color: '#fff',
                  padding: '2px 6px',
                  borderRadius: '3px',
                  fontSize: '11px',
                }}
              >
                {f.severity.toUpperCase()}
              </span>
            </div>
            {isExp && (
              <div style={{ padding: '12px' }}>
                <div style={{ marginBottom: '8px' }}>{f.description}</div>
                {f.evidence &&
                  f.evidence.length > 0 && (
                    <div style={{ marginBottom: '8px', fontSize: '13px', color: '#666' }}>
                      <strong>証拠:</strong>
                      <ul>
                        {f.evidence.map((e: any, i: number) => (
                          <li key={i}>
                            {e.source}: {e.text}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                {f.suggestion && (
                  <div style={{ marginBottom: '8px', fontSize: '13px', color: '#28a745' }}>
                    <strong>提案:</strong> {f.suggestion}
                  </div>
                )}
                <button
                  onClick={() => handleDismiss({ ...f, key })}
                  style={{
                    padding: '4px 10px',
                    background: '#6c757d',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer',
                  }}
                >
                  却下する
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};