import React from 'react';
import { ReactFlow, ReactFlowInstance, Background, Controls, MiniMap, FitView } from 'reactflow';
import { useBranchTree } from '@/hooks/useBranchTree';
import { BranchNode } from './BranchNode';
import { BranchEdge } from './BranchEdge';
import { computeTreeLayout } from '@/lib/branches';
import { BranchTreeData } from '@/types/branches';

export const BranchTree: React.FC<{ bookId: number }> = ({ bookId }) => {
  const { data, isLoading, isError, error } = useBranchTree(bookId);
  const [reactFlowInstance, setReactFlowInstance] = React.useState<ReactFlowInstance | null>(null);

  React.useEffect(() => {
    if (data && reactFlowInstance) {
      // Compute layout and update positions
      const layoutNodes = computeTreeLayout(data.nodes, data.edges);
      
      // Update node positions in React Flow instance
      layoutNodes.forEach(node => {
        reactFlowInstance.updateNode(node.id, { position: node.position });
      });
      
      // Fit view to show all nodes
      reactFlowInstance.fitView();
    }
  }, [data, reactFlowInstance]);

  if (isLoading) return <div>Loading branch tree...</div>;
  if (isError) return <div>Error: {error?.message}</div>;

  return (
    <div style={{ height: '100%', width: '100%' }}>
      <ReactFlow
        nodes={data.nodes}
        edges={data.edges}
        onInitialized={setReactFlowInstance}
        nodeTypes={{ custom: BranchNode }}
        edgeTypes={{ custom: BranchEdge }}
        defaultNodeType="custom"
        defaultEdgeType="custom"
        zoomOnScroll={true}
        panOnScroll={true}
        panOnDrag={true}
        enableContextMenu={true}
        minZoom={0.5}
        maxZoom={2}
      >
        <Background />
        <Controls />
        <MiniMap />
        <FitView />
      </ReactFlow>
    </div>
  );
};
