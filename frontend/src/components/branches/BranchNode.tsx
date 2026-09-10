import React from 'react';
import { NodeProps, Handle, Position } from 'reactflow';

export const BranchNode: React.FC<NodeProps> = ({
  data,
  selected,
  dragging
}) => {
  const isSelected = selected || dragging;
  const { label, forkEpNum, createdAt } = data || {};
  
  return (
    <div
      style={{
        width: 200,
        minHeight: 80,
        border: isSelected ? '2px solid var(--accent-color)' : '1px solid var(--border-color)',
        borderRadius: 8,
        backgroundColor: 'var(--bg-card, #1e1e24)',
        color: 'var(--text-main, #f0f0f0)',
        boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
        padding: 12,
        cursor: 'move'
      }}
    >
      <Handle type="target" position={Position.Top} />
      <div style={{ fontWeight: 'bold', fontSize: 14, marginBottom: 6 }}>
        {label || 'Branch'}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted, #a0a0a0)', marginBottom: 4 }}>
        Chapter: {forkEpNum ?? 0}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted, #808080)' }}>
        Created: {createdAt ? new Date(createdAt).toLocaleDateString() : '-'}
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};
