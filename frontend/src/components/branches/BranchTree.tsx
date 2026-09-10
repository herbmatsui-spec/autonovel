import React, { useMemo } from 'react';
import { ReactFlow, ReactFlowInstance, Background, Controls, MiniMap, Node, Edge } from 'reactflow';
import { useBranchTree } from '../../hooks/useBranchTree';
import { BranchNode } from './BranchNode';
import { BranchEdge } from './BranchEdge';
import { computeTreeLayout } from '../../lib/branches';

const nodeTypes = { custom: BranchNode };
const edgeTypes = { custom: BranchEdge };

export const BranchTree: React.FC<{ bookId: number }> = ({ bookId }) => {
  const { data, isLoading, isError, error } = useBranchTree(bookId);
  const [reactFlowInstance, setReactFlowInstance] = React.useState<ReactFlowInstance | null>(null);

  const flowNodes: Node[] = useMemo(() => {
    if (!data?.nodes) return [];
    const layoutNodes = computeTreeLayout(data.nodes, data.edges || []);
    return layoutNodes.map(node => ({
      id: String(node.id),
      type: 'custom',
      position: node.position,
      data: node.data,
    }));
  }, [data]);

  const flowEdges: Edge[] = useMemo(() => {
    if (!data?.edges) return [];
    return data.edges.map(edge => ({
      id: edge.id || `e-${edge.source}-${edge.target}`,
      source: String(edge.source),
      target: String(edge.target),
      type: 'custom',
      data: { type: edge.type },
    }));
  }, [data]);

  React.useEffect(() => {
    if (reactFlowInstance && flowNodes.length > 0) {
      reactFlowInstance.fitView({ padding: 0.2 });
    }
  }, [reactFlowInstance, flowNodes]);

  if (isLoading) return <div>Loading branch tree...</div>;
  if (isError) return <div>Error: {error?.message}</div>;

  return (
    <div style={{ height: '100%', width: '100%' }}>
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onInit={setReactFlowInstance}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        zoomOnScroll={true}
        panOnScroll={true}
        panOnDrag={true}
        fitView
        minZoom={0.5}
        maxZoom={2}
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
};
