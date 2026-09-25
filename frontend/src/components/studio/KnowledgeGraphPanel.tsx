import React from 'react';
import GraphVisualization from '../GraphVisualization';

interface KnowledgeGraphPanelProps {
  bookId?: number | string;
  className?: string;
}

export const KnowledgeGraphPanel: React.FC<KnowledgeGraphPanelProps> = ({
  className = '',
}) => {
  return (
    <div className={`knowledge-graph-panel h-full w-full flex flex-col ${className}`}>
      <div className="p-3 border-b border-gray-700 bg-gray-900/60 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
          <span>🕸️</span>
          <span>ナレッジグラフ・伏線関係図</span>
        </h3>
        <span className="text-xs text-indigo-400 bg-indigo-950/80 px-2 py-0.5 rounded border border-indigo-700/50">
          Relational Memory v5.2
        </span>
      </div>
      <div className="flex-1 relative overflow-hidden">
        <GraphVisualization />
      </div>
    </div>
  );
};

export default KnowledgeGraphPanel;
