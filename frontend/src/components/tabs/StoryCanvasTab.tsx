import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { useBookStore } from '@/store/useBookStore';
import { useStoryCanvasStore } from '@/store/useStoryCanvasStore';
import { seedStoryCanvas, createStoryNode, deleteStoryNode, createStoryEdge, deleteStoryEdge, saveStoryNode, updateNodeData } from '@/api';
import { useUserSettingsStore } from '@/store/useUserSettingsStore';
import { StoryNode, StoryEdge } from '@/types/storyCanvas';

const NODE_COLORS: Record<string, string> = {
  premise: '#fbbf24',  // amber
  act: '#a855f7',      // purple
  episode: '#3b82f6',  // blue
  scene: '#10b981',    // emerald
  character: '#ec4899', // pink
  foreshadow: '#f43f5e', // rose
};

export function StoryCanvasTab() {
  const { selectedBook } = useBookStore();
  const { 
    nodes, 
    edges, 
    selectedId, 
    loading, 
    setLoading,
    panX,
    panY,
    scale,
    setPan,
    setScale,
    resetViewport,
    addNode,
    moveNode,
    renameNode,
    updateNodeData,
    removeNode,
    addEdge,
    removeEdge,
    setSelected,
    dirty,
  } = useStoryCanvasStore();
  const { isExpertMode } = useUserSettingsStore();

  const canvasRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartPos, setDragStartPos] = useState<{ x: number; y: number } | null>(null);
  const [dragStartPan, setDragStartPan] = useState<{ x: number; y: number } | null>(null);
  const [linkingFrom, setLinkingFrom] = useState<string | null>(null);
  const [linkingLineEnd, setLinkingLineEnd] = useState<{ x: number; y: number } | null>(null);
  const [debounceTimer, setDebounceTimer] = useState<NodeJS.Timeout | null>(null);
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);

  const handleSeed = async () => {
    if (!selectedBook) return;
    setLoading(true);
    try {
      const result = await seedStoryCanvas(selectedBook.id);
      // Store will be updated via useBookDetails hook
    } finally {
      setLoading(false);
    }
  };

  const handleCanvasMouseDown = (e: MouseEvent) => {
    if (!canvasRef.current) return;
    
    const rect = canvasRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left - panX) / scale;
    const y = (e.clientY - rect.top - panY) / scale;
    
    // Right click for panning
    if (e.button === 2) { // right click
      e.preventDefault();
      setIsDragging(true);
      setDragStartPos({ x, y });
      setDragStartPan({ x: panX, y: panY });
      return;
    }
    
    // Left click - check if clicking on empty space to clear selection
    // In a full implementation we'd check if click hit a node
    // For simplicity, we'll clear selection on canvas click (would need refinement)
    // setSelected(null);
  };

  const handleCanvasMouseMove = (e: MouseEvent) => {
    if (!canvasRef.current) return;
    
    const rect = canvasRef.current.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const clientY = e.clientY - rect.top;
    
    // Update linking line end point
    if (linkingFrom) {
      setLinkingLineEnd({
        x: (clientX - panX) / scale,
        y: (clientY - panY) / scale
      });
    }
    
    // Handle panning
    if (isDragging && dragStartPos && dragStartPan) {
      const x = (clientX - panX) / scale;
      const y = (clientY - panY) / scale;
      
      const dx = x - dragStartPos.x;
      const dy = y - dragStartPos.y;
      
      setPan(dragStartPan.x + dx, dragStartPan.y + dy);
    }
  };

  const handleCanvasMouseUp = (e: MouseEvent) => {
    if (isDragging) {
      setIsDragging(false);
      // Actually move the selected node to the new position
      if (selectedId && dragStartPos && dragStartPan) {
        const rect = canvasRef.current?.getBoundingClientRect();
        if (rect) {
          const clientX = e.clientX - rect.left;
          const clientY = e.clientY - rect.top;
          const x = (clientX - panX) / scale;
          const y = (clientY - panY) / scale;
          
          // Update node position in store
          moveNode(selectedId, x, y);
          // Actually save to backend
          saveStoryNode(selectedBook.id, {
            id: selectedId,
            x,
            y,
          }).catch(console.error);
        }
      }
      setDragStartPos(null);
      setDragStartPan(null);
    }
    
    // Complete linking on mouse up if in linking mode
    if (linkingFrom && e.button === 0) { // left click
      // Find target node under cursor (simplified - would need hit detection)
      // For now, we'll complete the link - real implementation would check what's under cursor
      setLinkingFrom(null);
      setLinkingLineEnd(null);
      // In a full implementation: create edge from linkingFrom to target node
    }
  };

  const handleCanvasWheel = (e: WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.1 : -0.1;
    setScale(scale + delta);
  };

  const handleNodeMouseDown = (e: React.MouseEvent<HTMLDivElement>, nodeId: string) => {
    e.stopPropagation(); // Prevent canvas drag/panning
    setSelected(nodeId);
  };

  const handleNodeDragStart = (e: React.DragEvent<HTMLDivElement>, nodeId: string) => {
    // Store the node ID being dragged
    e.dataTransfer.setData('text/plain', nodeId);
    // Store initial position for potential snapping
  };

  const handleNodeDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    // Allow drop
  };

  const handleNodeDrop = (e: React.DragEvent<HTMLDivElement>, targetNodeId: string) => {
    e.preventDefault();
    const sourceId = e.dataTransfer.getData('text/plain');
    if (sourceId && sourceId !== targetNodeId) {
      // Create edge from source to target
      createStoryEdge(selectedBook.id, {
        source: sourceId,
        target: targetNodeId,
        kind: 'flow',
      }).then(() => {
        // Clear selection after creating edge
        setSelected(null);
      });
    }
  };

  const handleNodeContextMenu = (e: React.MouseEvent<HTMLDivElement>, nodeId: string) => {
    e.preventDefault();
    setLinkingFrom(nodeId);
    // Visual feedback will be handled by linkingLineEnd state
  };

  const handleDeleteNode = async (nodeId: string) => {
    await deleteStoryNode(selectedBook.id, nodeId);
    removeNode(nodeId);
    if (selectedId === nodeId) {
      setSelected(null);
    }
  };

  const handleDeleteEdge = async (edgeId: string) => {
    await deleteStoryEdge(selectedBook.id, edgeId);
    removeEdge(edgeId);
  };

  const handleNodeDoubleClick = async (e: React.MouseEvent<HTMLDivElement>, nodeId: string) => {
    e.preventDefault();
    e.stopPropagation();
    const node = nodes.find(n => n.id === nodeId);
    if (node && node.ep_num !== undefined) {
      // Navigate to the episode detail page
      // In a real app, we'd use navigate or update URL
      // For now, we'll just show a toast or focus on the plots tab
      console.log(`Navigate to episode ${node.ep_num}`);
    }
  };

  const handleCreateNode = async (kind: string) => {
    if (!selectedBook) return;
    // Create node at center of viewport
    const centerX = (canvasRef.current?.clientWidth || 800) / 2 / scale - panX / scale;
    const centerY = (canvasRef.current?.clientHeight || 600) / 2 / scale - panY / scale;
    
    const labelMap: Record<string, string> = {
      episode: '新しいエピソード',
      character: '新しいキャラクター',
      premise: '作品の核',
      act: '新しい幕',
      scene: '新しいシーン',
      foreshadow: '新しい伏線',
    };
    
    await createStoryNode(selectedBook.id, {
      kind,
      label: labelMap[kind] || '新しいノード',
      x: centerX,
      y: centerY,
    });
  };

  const handleNodeDoubleClick = async (e: React.MouseEvent<HTMLDivElement>, nodeId: string) => {
    e.preventDefault();
    e.stopPropagation();
    const node = nodes.find(n => n.id === nodeId);
    if (node && node.ep_num !== undefined) {
      // Navigate to the episode detail page
      // In a real app, we'd use navigate or update URL
      // For now, we'll just show a toast or focus on the plots tab
      console.log(`Navigate to episode ${node.ep_num}`);
    }
  };

  // Handle auto-saving dirty state with debounce
  useEffect(() => {
    if (dirty) {
      if (debounceTimer) {
        clearTimeout(debounceTimer);
      }
      const timer = setTimeout(async () => {
        // Save node positions to backend
        // In a real implementation, we'd call saveStoryNode for each moved node
        // For now, we'll just clear the dirty flag
        setDirty(false);
      }, 1000); // 1 second debounce
      setDebounceTimer(timer);
    }
    
    return () => {
      if (debounceTimer) {
        clearTimeout(debounceTimer);
      }
    };
  }, [dirty]);

  // Load initial data when book changes
  useEffect(() => {
    if (selectedBook.id) {
      // This would normally come from useBookDetails hook
      // For now, we'll seed if empty
      if (nodes.length === 0 && edges.length === 0) {
        handleSeed();
      }
    }
  }, [selectedBook.id]);

  if (!selectedBook) {
    return <div className="text-center py-8">作品を選択してください。</div>;
  }

  // Helper function to check if a point is inside a node (simplified)
  const isPointInNode = (x: number, y: number, node: StoryNode) => {
    const nodeSize = 60; // Approximate node diameter
    const dx = x - (node.x * scale + panX);
    const dy = y - (node.y * scale + panY);
    return Math.sqrt(dx * dx + dy * dy) < nodeSize / 2;
  };

  return (
    <div className="animate-fade-in flex flex-col gap-6 h-full">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold">ストーリーキャンバス - {selectedBook.title}</h2>
          <p className="text-xs text-muted-foreground mt-1">
            エピソード・キャラクター・構造を視覚的に編集
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="default" onClick={handleSeed} disabled={loading}>
            {loading ? '初期化中...' : '🌱 キャンバスを初期化 (Seed)'}
          </Button>
          <Button 
            variant="outline" 
            onClick={() => {
              resetViewport();
              setDirty(false);
            }}
          >
            ビューポートリセット
          </Button>
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              onClick={() => handleCreateNode('episode')}
              size="sm"
            >
              +エピソード
            </Button>
            <Button 
              variant="outline" 
              onClick={() => handleCreateNode('character')}
              size="sm"
            >
              +キャラクター
            </Button>
          </div>
          <Button
            variant="outline"
            onClick={() => setLinkingFrom(null)}
            disabled={!linkingFrom}
            className={linkingFrom ? 'bg-blue-500 text-white' : 'bg-transparent'}
          >
            {linkingFrom ? 'リンクモード解除 (Esc)' : 'リンクモード (L)'}
          </Button>
          {isExpertMode && (
            <span className="text-xs text-muted-foreground">Expert Mode</span>
          )}
        </div>
      </div>

      {/* Canvas container */}
      <div 
        className="relative flex-1 min-h-[500px] bg-[var(--bg-muted)]/50 rounded-lg p-4 overflow-hidden"
        ref={canvasRef}
        onMouseDown={handleCanvasMouseDown}
        onMouseMove={handleCanvasMouseMove}
        onMouseUp={handleCanvasMouseUp}
        onWheel={handleCanvasWheel}
        onContextMenu={(e) => e.preventDefault()}
        onKeyDown={(e) => {
          if (e.key === 'Escape' && linkingFrom) {
            e.preventDefault();
            setLinkingFrom(null);
            setLinkingLineEnd(null);
          }
          if (e.key === 'Delete' && selectedId) {
            e.preventDefault();
            handleDeleteNode(selectedId);
          }
          if (e.key === 'l' || e.key === 'L') {
            e.preventDefault();
            // Toggle linking mode - would need current selected node
          }
        }}
        tabIndex={0} // Allow receiving keyboard events
      >
        {/* SVG layer for edges */}
        <svg 
          ref={svgRef}
          className="absolute inset-0 pointer-events-none"
          width="100%"
          height="100%"
        >
          {/* Temporary linking line */}
          {linkingFrom && linkingLineEnd && (
            <line
              x1={nodes.find(n => n.id === linkingFrom)?.x * scale + panX || 0}
              y1={nodes.find(n => n.id === linkingFrom)?.y * scale + panY || 0}
              x2={linkingLineEnd.x * scale + panX}
              y2={linkingLineEnd.y * scale + panY}
              stroke="#3b82f6"
              strokeWidth="2"
              strokeDasharray="4 2"
            />
          )}
          
          {/* Permanent edges */}
          {edges.map(edge => {
            const sourceNode = nodes.find(n => n.id === edge.source);
            const targetNode = nodes.find(n => n.id === edge.target);
            
            if (!sourceNode || !targetNode) return null;
            
            // Apply pan and zoom
            const sourceX = (sourceNode.x * scale) + panX;
            const sourceY = (sourceNode.y * scale) + panY;
            const targetX = (targetNode.x * scale) + panX;
            const targetY = (targetNode.y * scale) + panY;
            
            // Different stroke styles based on edge kind
            return (
              <g key={edge.id}>
                <line 
                  x1={sourceX}
                  y1={sourceY}
                  x2={targetX}
                  y2={targetY}
                  stroke={edge.kind === 'dependency' || edge.kind === 'relationship' 
                    ? '#ec4899' 
                    : edge.kind === 'foreshadow'
                      ? '#f43f5e'
                      : '#6b7280'}
                  strokeWidth={2}
                  strokeDasharray={ 
                    edge.kind === 'dependency' || edge.kind === 'relationship' 
                      ? '4 2' 
                    : edge.kind === 'foreshadow' 
                      ? '8 4' 
                      : 'none' 
                  }
                />
                {/* Delete button for edge (×) */}
                {(hoveredEdgeId === edge.id) && (
                  <foreignObject x={Math.min(sourceX, targetX) - 10} y={Math.min(sourceY, targetY) - 10} width="20" height="20">
                    <button 
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteEdge(edge.id);
                      }}
                      className="absolute -top-1 -left-1 h-4 w-4 rounded-full bg-red-500 text-white text-xs flex items-center justify-center"
                    >
                      ✕
                    </button>
                  </foreignObject>
                )}
              </g>
            );
          })}
        </svg>

        {/* Nodes layer */}
        {nodes.map(node => {
          const color = NODE_COLORS[node.kind] || '#6b7280';
          const isSelected = selectedId === node.id;
          const isSourceForLink = linkingFrom === node.id;
          
          return (
            <div
              key={node.id}
              className={`absolute left-[${node.x * scale + panX}px] top-[${node.y * scale + panY}px] transform translate-x-[-50%] translate-y-[-50%] 
                p-2 rounded border border-[${isSelected ? 'var(--accent)' : isSourceForLink ? '#3b82f6' : 'transparent'}] border-2 
                bg-[${color}]/20 hover:bg-[${color}]/30 cursor-pointer transition-all
                ${isSourceForLink ? 'animate-pulse' : ''}`}
              ref={el => {
                // Store ref for potential hit detection
              }}
              onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
              onMouseUp={(e) => {
                // Handle click to select (separate from drag)
                if (!isDragging) {
                  setSelected(node.id);
                }
              }}
              onContextMenu={(e) => handleNodeContextMenu(e, node.id)}
              onDragStart={(e) => handleNodeDragStart(e, node.id)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => handleNodeDrop(e, node.id)}
              onDoubleClick={(e) => handleNodeDoubleClick(e, node.id)}
            >
              <div className="relative">
                <div className="flex items-center gap-2 text-[{isSelected ? 'var(--accent)' : isSourceForLink ? '#3b82f6' : color}] font-medium">
                  {/* Node type icon */}
                  <span 
                    title={node.kind}
                    className="text-xs"
                  >
                    {node.kind === 'premise' ? '🎯' 
                     : node.kind === 'act' ? '🎪' 
                     : node.kind === 'episode' ? '📖' 
                     : node.kind === 'scene' ? '🎬' 
                     : node.kind === 'character' ? '👤' 
                     : node.kind === 'foreshadow' ? '⚡' 
                     : '⬤'}
                  </span>
                  <span className="truncate w-[120px]">{node.label}</span>
                  {node.ep_num !== undefined && (
                    <span className="text-xs ml-1">#{node.ep_num}</span>
                  )}
                </div>
                {/* Show character arc sparkline if expert mode and character node */}
                {isExpertMode && node.kind === 'character' && node.data?.arc_stages && Array.isArray(node.data.arc_stages) && node.data.arc_stages.length > 0 && (
                  <svg 
                    className="absolute bottom-[-18px] left-[-50%] w-[60px] h-[12px]"
                    viewBox="0 0 60 12"
                    preserveAspectRatio="none"
                  >
                    <polyline 
                      points={node.data.arc_stages.map((stage, i) => `${i * (60 / Math.max(node.data.arc_stages.length - 1, 1))},${12 - (stage * 10)}`).join(' ')}
                      fill="none"
                      stroke={color}
                      strokeWidth="1.5"
                    />
                  </svg>
                )}
                {/* Show tension badge for episode nodes */}
                {node.kind === 'episode' && node.data?.tension !== undefined && (
                  <div className="absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold">
                    <span className={node.data.tension >= 70 ? 'bg-red-500' : node.data.tension >= 40 ? 'bg-yellow-500' : 'bg-green-500'} text-white">
                      {Math.round(node.data.tension)}
                    </span>
                  </div>
                )}
                {/* Show catharsis badge */}
                {node.kind === 'episode' && node.data?.is_catharsis && (
                  <div className="absolute -top-2 left-2 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold bg-purple-500 text-white">
                    †
                  </div>
                )}
                {/* Selection indicator */}
                {isSelected && (
                  <div className="absolute -left-4 -top-4 flex h-6 w-6 items-center justify-center rounded-full border-2 border-[var(--accent)] bg-[var(--accent)]/20">
                    <span className="text-[var(--accent)] font-bold">●</span>
                  </div>
                )}
                {/* Create edge button (+) */}
                <div className="absolute -top-2 right-2 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold bg-[color]/30 hover:bg-[color]/40">
                  +
                </div>
                {/* Delete node button (🗑) */}
                <div className="absolute bottom-2 left-2 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold bg-red-500/20 hover:bg-red-500/30">
                  𗚖
                </div>
              </div>
            </div>
          );
        })}

        {/* Visual hint for linking mode */}
        {linkingFrom && !linkingLineEnd && (
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute inset-0 bg-[var(--accent)]/20 pointer-events-none" />
          </div>
        )}
      </div>

      {/* Node inspector panel */}
      {selectedId && (
        <div className="w-64 border-l border-[var(--border)] pl-4">
          <h3 className="font-semibold mb-2">ノード詳細</h3>
          <div className="space-y-2">
            {nodes.find(n => n.id === selectedId) && (
              <>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">ラベル:</span>
                  <input 
                    type="text"
                    className="border rounded px-2 py-1 w-full"
                    value={nodes.find(n => n.id === selectedId)?.label || ''}
                    onChange={(e) => {
                      const newLabel = e.target.value;
                      renameNode(selectedId, newLabel);
                      updateNodeData(selectedId, { label: newLabel });
                    }}
                  />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">種別:</span>
                  <span className="text-xs px-2 py-0.5 rounded 
                    {nodes.find(n => n.id === selectedId)?.kind === 'premise' ? 'bg-amber-100 text-amber-800'
                     : nodes.find(n => n.id === selectedId)?.kind === 'act' ? 'bg-purple-100 text-purple-800'
                     : nodes.find(n => n.id === selectedId)?.kind === 'episode' ? 'bg-blue-100 text-blue-800'
                     : nodes.find(n => n.id === selectedId)?.kind === 'scene' ? 'bg-green-100 text-green-800'
                     : nodes.find(n => n.id === selectedId)?.kind === 'character' ? 'bg-pink-100 text-pink-800'
                     : nodes.find(n => n.id === selectedId)?.kind === 'foreshadow' ? 'bg-rose-100 text-rose-800'
                     : 'bg-gray-100 text-gray-800'}
                  ">
                    {nodes.find(n => n.id === selectedId)?.kind}
                  </span>
                </div>
                {nodes.find(n => n.id === selectedId)?.ep_num !== undefined && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">エピソード:</span>
                    <span className="text-sm">{nodes.find(n => n.id === selectedId)?.ep_num}</span>
                  </div>
                )}
                {/* Character-specific fields */}
                {nodes.find(n => n.id === selectedId)?.kind === 'character' && (
                  <>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">役割:</span>
                      <input 
                        type="text"
                        className="border rounded px-2 py-1 w-full"
                        value={nodes.find(n => n.id === selectedId)?.data?.role || ''}
                        onChange={(e) => {
                          updateNodeData(selectedId, { role: e.target.value });
                        }}
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">特徴:</span>
                      <input 
                        type="text"
                        className="border rounded px-2 py-1 w-full"
                        value={Array.isArray(nodes.find(n => n.id === selectedId)?.data?.traits) 
                          ? nodes.find(n => n.id === selectedId)?.data?.traits.join(', ') 
                          : ''}
                        onChange={(e) => {
                          updateNodeData(selectedId, { 
                            traits: e.target.value.split(',').map(t => t.trim()).filter(t => t.length > 0)
                          });
                        }}
                      />
                    </div>
                  </>
                )}
                {/* Episode-specific fields */}
                {nodes.find(n => n.id === selectedId)?.kind === 'episode' && (
                  <>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">テンション:</span>
                      <input 
                        type="number"
                        className="border rounded px-2 py-1 w-full"
                        min="0"
                        max="100"
                        value={nodes.find(n => n.id === selectedId)?.data?.tension || 50}
                        onChange={(e) => {
                          updateNodeData(selectedId, { tension: parseInt(e.target.value) || 50 });
                        }}
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">カタルシス:</span>
                      <label className="flex items-center gap-1">
                        <input 
                          type="checkbox"
                          className="h-4 w-4"
                          checked={nodes.find(n => n.id === selectedId)?.data?.is_catharsis || false}
                          onChange={(e) => {
                            updateNodeData(selectedId, { is_catharsis: e.target.checked });
                          }}
                        />
                        <span className="text-xs">有</span>
                      </label>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* Status bar */}
      <div className="flex justify-between items-center text-xs text-muted-foreground px-4 pt-2">
        <div>
          {dirty && <span className="mr-2 animate-pulse">● 未保存の変更があります</span>}
          ノード: {nodes.length} | エッジ: {edges.length}
          {linkingFrom && <span className="ml-2">リンク元: {nodes.find(n => n.id === linkingFrom)?.label ?? 'unknown'}</span>}
        </div>
        <div>
          <span>パン: ({panX.toFixed(0)}, {panY.toFixed(0)}) | ズーム: {(scale * 100).toFixed(0)}%</span>
          {[linkingFrom, linkingLineEnd].some(Boolean) && <span className="ml-2">リンクモード中</span>}
        </div>
      </div>
    </div>
  );
}

export default StoryCanvasTab;