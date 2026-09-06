import React from 'react';
import { BranchTreeEdge } from '../../types/branches';

type BranchEdgeProps = {
  edge: BranchTreeEdge;
  selected: boolean;
};

export const BranchEdge: React.FC<BranchEdgeProps> = ({
  edge,
  selected
}) => {
  const isParentChild = edge.type === 'parent_child';
  const isMerge = edge.type === 'merge';
  
  const strokeWidth = selected ? 3 : 1.5;
  const strokeColor = isMerge ? '#ff9f1c' : isParentChild ? '#2ec4b6' : '#6c757d';
  const strokeDasharray = isMerge ? '5,5' : 'none';
  
  // Calculate midpoint for label
  const midpointX = (Number(edge.source) + Number(edge.target)) / 2;
  const midpointY = (Number(edge.source) + Number(edge.target)) / 2;
  
  return (
    <g>
      {/* The actual edge line is drawn by React Flow, we're just adding a label */}
      <text
        x={midpointX}
        y={midpointY - 10}
        textAnchor="middle"
        fill={strokeColor}
        fontSize={10}
        fontWeight="bold"
        pointerEvents="none"
      >
        {isMerge ? 'MERGE' : isParentChild ? 'CHILD' : ''}
      </text>
    </g>
  );
};
