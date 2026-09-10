import React from 'react';
import { EdgeProps, getBezierPath } from 'reactflow';

export const BranchEdge: React.FC<EdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  data,
  selected,
}) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const edgeType = data?.type;
  const isParentChild = edgeType === 'parent_child';
  const isMerge = edgeType === 'merge';

  const strokeWidth = selected ? 3 : 1.5;
  const strokeColor = isMerge ? '#ffb74d' : isParentChild ? '#4dd0e1' : '#71717a';
  const strokeDasharray = isMerge ? '5,5' : undefined;

  return (
    <>
      <path
        id={id}
        style={{ ...style, strokeWidth, stroke: strokeColor, strokeDasharray }}
        className="react-flow__edge-path"
        d={edgePath}
      />
      {(isMerge || isParentChild) && (
        <text
          x={labelX}
          y={labelY - 8}
          textAnchor="middle"
          fill={strokeColor}
          fontSize={10}
          fontWeight="bold"
          pointerEvents="none"
        >
          {isMerge ? 'MERGE' : 'CHILD'}
        </text>
      )}
    </>
  );
};
