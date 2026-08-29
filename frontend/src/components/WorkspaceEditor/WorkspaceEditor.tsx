import React, { useState, useEffect } from 'react';
import { useWorkspaceFiles } from '@/hooks/useWorkspaceFiles';

const WORKSPACE_FILES = [
  'SOUL.md',
  'WORLD.md',
  'CHARACTERS.md',
  'OUTLINE.md',
  'STORY_SUMMARY.md',
  'MEMORY.md',
];

export const WorkspaceEditor: React.FC = () => {
  const { files, loading, error, loadAll, saveFile } = useWorkspaceFiles();
  const [activeTab, setActiveTab] = useState(WORKSPACE_FILES[0]);
  const [content, setContent] = useState('');

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    setContent(files[activeTab] || '');
  }, [files, activeTab]);

  const handleSave = () => {
    saveFile(activeTab, content);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '16px' }}>
      {error && <div style={{ color: 'red', marginBottom: '8px' }}>Error: {error}</div>}

      <div
        style={{
          display: 'flex',
          gap: '4px',
          marginBottom: '12px',
          borderBottom: '1px solid #ddd',
          paddingBottom: '8px',
        }}
      >
        {WORKSPACE_FILES.map((fname) => (
          <button
            key={fname}
            onClick={() => setActiveTab(fname)}
            style={{
              padding: '6px 12px',
              background: activeTab === fname ? '#007bff' : '#f0f0f0',
              color: activeTab === fname ? '#fff' : '#333',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '13px',
            }}
          >
            {fname.replace('.md', '')}
          </button>
        ))}
      </div>

      {loading ? (
        <div>読み込み中...</div>
      ) : (
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          style={{
            flex: 1,
            width: '100%',
            height: '100%',
            minHeight: '400px',
            fontFamily: 'monospace',
            fontSize: '13px',
            padding: '12px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            resize: 'vertical',
          }}
          placeholder="ファイルが存在しないか空です"
        />
      )}

      <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={handleSave}
          style={{
            padding: '8px 16px',
            background: '#28a745',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
          }}
        >
          保存
        </button>
      </div>
    </div>
  );
};