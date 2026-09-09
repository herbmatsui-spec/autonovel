import React from 'react';
import { BranchTreeNode } from '../../types/branches';

type BranchNodeProps = {
  node: BranchTreeNode;
  selected: boolean;
  dragging: boolean;
};

export const BranchNode: React.FC<BranchNodeProps> = ({
  node,
  selected,
  dragging
}) => {
  const isSelected = selected || dragging;
  const { label, bookId, parentId, forkEpNum, createdAt } = node.data;
  
  return (
    <div
style={{
         position: 'absolute',
         left: node.position.x,
         top: node.position.y,
         transform: 'translate(-50%, -50%)',
         width: 200,
         height: 80,
         border: isSelected ? '2px solid var(--accent-color)' : '1px solid var(--border-color)',
         borderRadius: 8,
         backgroundColor: 'var(--bg-card)',
         boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
         padding: 12,
         cursor: 'move'
       }}
    >
      <div style={{ fontWeight: 'bold', fontSize: 16, marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>
        Chapter: {forkEpNum ?? 0}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
        Created: {new Date(createdAt || 0).toLocaleDateString()}
      </div>
    </div>
  );
};
