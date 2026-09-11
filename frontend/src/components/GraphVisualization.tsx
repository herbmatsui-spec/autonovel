import React, { useEffect, useState, useRef, useMemo, useCallback } from "react";
import ForceGraph2D, { ForceGraphMethods } from "react-force-graph-2d";
import { fetchGraphData } from "../api/graph";
import { NodeInspector } from "./graph/NodeInspector";
import { GraphNodeDetail } from "../types/graphInspector";
import { GraphEdge as InspectorGraphEdge } from "../types/graph";

export interface GraphNode {
  id: string;
  label?: string;
  properties?: Record<string, unknown>;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphEdge {
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
  properties?: Record<string, unknown>;
}

export interface GraphData {
  graph_name: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  error?: string;
}

interface GraphVisualizationProps {
  onClose?: () => void;
}

const LABEL_COLORS: Record<string, string> = {
  Character: "#38bdf8", // Sky blue
  Location: "#34d399",  // Emerald green
  Item: "#fbbf24",      // Amber
  Faction: "#a78bfa",   // Purple
  Event: "#f43f5e",     // Rose
  Concept: "#94a3b8",   // Slate
};

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({ onClose }) => {
  const [rawData, setRawData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [filterType, setFilterType] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState<string>("");

  const fgRef = useRef<ForceGraphMethods<GraphNode, GraphEdge>>();
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 450 });

  // Update canvas dimensions based on container
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };
    updateDimensions();
    window.addEventListener("resize", updateDimensions);
    return () => window.removeEventListener("resize", updateDimensions);
  }, [loading, selectedNode]);

  useEffect(() => {
    let isMounted = true;
    fetchGraphData()
      .then((json) => {
        if (isMounted) {
          setRawData(json as GraphData);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setRawData({
            graph_name: "autonovel_graph",
            nodes: [],
            edges: [],
            error: String(err),
          });
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Filtered nodes and edges
  const graphData = useMemo(() => {
    if (!rawData) return { nodes: [], links: [] };

    let nodes = [...rawData.nodes];
    let edges = [...rawData.edges];

    // ノードが空の場合の初期主人公ノード
    if (nodes.length === 0) {
      nodes = [
        {
          id: "アルト",
          label: "Character",
          properties: { role: "主人公", ability: "古代魔導剣術" },
        },
        {
          id: "古代魔導剣",
          label: "Item",
          properties: { type: "秘宝", description: "300年前の剣" },
        },
      ];
      edges = [
        {
          source: "アルト",
          target: "古代魔導剣",
          type: "EQUIPPED_WITH",
        },
      ];
    }

    let filteredNodes = nodes.map((n) => ({ ...n }));
    if (filterType !== "ALL") {
      filteredNodes = filteredNodes.filter((n) => n.label === filterType);
    }
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      filteredNodes = filteredNodes.filter((n) => n.id.toLowerCase().includes(term));
    }

    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    const filteredEdges = edges
      .filter((e) => {
        const srcId = typeof e.source === "object" ? (e.source as GraphNode).id : e.source;
        const tgtId = typeof e.target === "object" ? (e.target as GraphNode).id : e.target;
        return nodeIds.has(srcId) && nodeIds.has(tgtId);
      })
      .map((e) => ({
        ...e,
        source: typeof e.source === "object" ? (e.source as GraphNode).id : e.source,
        target: typeof e.target === "object" ? (e.target as GraphNode).id : e.target,
      }));

    return {
      nodes: filteredNodes,
      links: filteredEdges,
    };
  }, [rawData, filterType, searchTerm]);

  // Connected nodes map for highlighting
  const connectedNodeIds = useMemo(() => {
    const targetNode = hoveredNode || selectedNode;
    if (!targetNode || !rawData) return null;

    const ids = new Set<string>([targetNode.id]);
    rawData.edges.forEach((e) => {
      const srcId = typeof e.source === "object" ? (e.source as GraphNode).id : e.source;
      const tgtId = typeof e.target === "object" ? (e.target as GraphNode).id : e.target;
      if (srcId === targetNode.id) ids.add(tgtId);
      if (tgtId === targetNode.id) ids.add(srcId);
    });
    return ids;
  }, [hoveredNode, selectedNode, rawData]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node);
  }, []);

  const handleResetZoom = useCallback(() => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400, 50);
    }
  }, []);

  const handleAddNewEntity = useCallback(() => {
    const newId = `new_${Date.now()}`;
    const newNode: GraphNode = {
      id: newId,
      label: "Character",
      properties: {},
    };
    // Add to rawData
    setRawData((prev) => {
      if (!prev) {
        return {
          graph_name: "autonovel_graph",
          nodes: [newNode],
          edges: [],
        };
      }
      return {
        ...prev,
        nodes: [...prev.nodes, newNode],
      };
    });
    // Select the new node
    setSelectedNode(newNode);
  }, []);

  const nodeCanvasObject = useCallback(
    (node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;
      const isConnected = connectedNodeIds ? connectedNodeIds.has(node.id) : true;
      const color = (node.label && LABEL_COLORS[node.label]) || "#94a3b8";
      const nx = node.x ?? 0;
      const ny = node.y ?? 0;

      const nodeRadius = isSelected ? 8 : isHovered ? 7 : 5;
      const alpha = isConnected ? 1 : 0.2;

      ctx.save();
      ctx.globalAlpha = alpha;

      // Glow effect for selected/hovered node
      if (isSelected || isHovered) {
        ctx.beginPath();
        ctx.arc(nx, ny, nodeRadius + 4, 0, 2 * Math.PI, false);
        ctx.fillStyle = color + "44";
        ctx.fill();
      }

      // Outer circle border
      ctx.beginPath();
      ctx.arc(nx, ny, nodeRadius, 0, 2 * Math.PI, false);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.lineWidth = isSelected ? 2 : 1;
      ctx.strokeStyle = isSelected ? "#ffffff" : "#18181b";
      ctx.stroke();

      // Label text
      const fontSize = Math.max(12 / globalScale, 3.5);
      ctx.font = `${isSelected ? "bold " : ""}${fontSize}px sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = isConnected ? "#f4f4f5" : "#71717a";
      ctx.fillText(node.id, nx, ny + nodeRadius + fontSize);

      ctx.restore();
    },
    [selectedNode, hoveredNode, connectedNodeIds]
  );

return (
    <div
      data-testid="graph-modal"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(9, 9, 11, 0.85)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        backdropFilter: "blur(6px)",
      }}
    >
      <div
        style={{
          width: "92%",
          maxWidth: "1100px",
          height: "85vh",
          backgroundColor: "#18181b",
          borderRadius: "14px",
          border: "1px solid #27272a",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.7)",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "14px 20px",
            borderBottom: "1px solid #27272a",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background: "#1c1c21",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "1.4rem" }}>🕸️</span>
            <div>
              <h2 style={{ margin: 0, fontSize: "1.15rem", color: "#f4f4f5", fontWeight: 600 }}>
                AutoNovel 物理演算ナレッジグラフ
              </h2>
              <span style={{ fontSize: "0.75rem", color: "#a1a1aa" }}>
                Apache AGE & pgvector によるリアルタイム相関探索 (Force-Directed)
              </span>
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <button
              onClick={handleResetZoom}
              style={{
                padding: "6px 12px",
                borderRadius: "6px",
                backgroundColor: "#27272a",
                color: "#e4e4e7",
                border: "1px solid #3f3f46",
                cursor: "pointer",
                fontSize: "0.8rem",
              }}
              title="グラフを画面に合わせる"
            >
              🎯 全体表示
            </button>
            {onClose && (
              <button
                onClick={onClose}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#a1a1aa",
                  fontSize: "1.4rem",
                  cursor: "pointer",
                  padding: "4px 8px",
                  lineHeight: 1,
                }}
                aria-label="閉じる"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Toolbar / Filters */}
        <div
          style={{
            padding: "10px 20px",
            borderBottom: "1px solid #27272a",
            display: "flex",
            gap: "12px",
            alignItems: "center",
            background: "#18181b",
            fontSize: "0.85rem",
          }}
        >
          <span style={{ color: "#a1a1aa" }}>種別フィルタ:</span>
          {["ALL", "Character", "Location", "Item", "Faction"].map((type) => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              style={{
                padding: "4px 10px",
                borderRadius: "6px",
                border: filterType === type ? "1px solid #38bdf8" : "1px solid #27272a",
                backgroundColor: filterType === type ? "#0369a1" : "#27272a",
                color: "#f4f4f5",
                cursor: "pointer",
                fontSize: "0.75rem",
              }}
            >
              {type === "ALL" ? "全て" : type}
            </button>
          ))}

<input
             type="text"
             placeholder="名前で検索..."
             value={searchTerm}
             onChange={(e) => setSearchTerm(e.target.value)}
             style={{
               marginLeft: "auto",
               padding: "4px 10px",
               borderRadius: "6px",
               border: "1px solid #3f3f46",
               backgroundColor: "#27272a",
               color: "#f4f4f5",
               fontSize: "0.8rem",
               outline: "none",
               width: "160px",
             }}
           />
           <button
             onClick={handleAddNewEntity}
             style={{
               marginLeft: "12px",
               padding: "6px 12px",
               backgroundColor: "#4fc3f7",
               color: "white",
               border: "none",
               borderRadius: "4px",
               cursor: "pointer",
               fontSize: "0.8rem",
             }}
           >
             + 新規エンティティ
           </button>
        </div>

        {/* Main Content Area */}
        <div style={{ flex: 1, display: "flex", position: "relative", overflow: "hidden" }}>
          {loading ? (
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#a1a1aa",
              }}
            >
              ⚡ グラフデータをロード中...
            </div>
          ) : rawData?.error ? (
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#f43f5e",
              }}
            >
              エラー: {rawData.error}
            </div>
          ) : (
            <>
              {/* Force Graph Container */}
              <div
                ref={containerRef}
                style={{
                  flex: 1,
                  background: "#09090b",
                  position: "relative",
                  overflow: "hidden",
                }}
                data-testid="force-graph-container"
              >
                {/* Fallback for testing/non-webgl or ForceGraph2D */}
                <ForceGraph2D
                  ref={fgRef}
                  width={dimensions.width}
                  height={dimensions.height}
                  graphData={graphData}
                  nodeId="id"
                  nodeCanvasObject={nodeCanvasObject}
                  linkDirectionalArrowLength={4}
                  linkDirectionalArrowRelPos={1}
                  linkCurvature={0.15}
                  linkColor={() => "#3f3f46"}
                  linkWidth={(link: GraphEdge) => {
                    const srcId = typeof link.source === "object" ? (link.source as GraphNode).id : link.source;
                    const tgtId = typeof link.target === "object" ? (link.target as GraphNode).id : link.target;
                    const isHovered =
                      (hoveredNode && (srcId === hoveredNode.id || tgtId === hoveredNode.id)) ||
                      (selectedNode && (srcId === selectedNode.id || tgtId === selectedNode.id));
                    return isHovered ? 2 : 1;
                  }}
                  linkDirectionalParticles={1}
                  linkDirectionalParticleSpeed={0.005}
                  linkDirectionalParticleWidth={2}
                  onNodeClick={handleNodeClick}
                  onNodeHover={(node: GraphNode | null) => setHoveredNode(node || null)}
                  cooldownTicks={100}
                />
              </div>

{/* Node Inspector Panel */}
            {selectedNode && rawData && (
              <div
                style={{
                  width: "360px",
                  borderLeft: "1px solid #27272a",
                  backgroundColor: "#18181b",
                  overflowY: "auto",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                {(() => {
                  // Convert selected node to GraphNodeDetail
                  const nodeDetail: GraphNodeDetail = {
                    id: selectedNode.id,
                    label: selectedNode.label || "Unknown",
                    properties: Object.fromEntries(
                      Object.entries(selectedNode.properties || {}).map(([key, value]) => [
                        key,
                        String(value),
                      ])
                    ),
                  };

                  // Convert all nodes to GraphNodeDetail[]
                  const nodesDetail: GraphNodeDetail[] = rawData.nodes.map((node) => ({
                    id: node.id,
                    label: node.label || "Unknown",
                    properties: Object.fromEntries(
                      Object.entries(node.properties || {}).map(([key, value]) => [key, String(value)])
                    ),
                  }));

                  // Convert all edges to GraphEdge[] (with string source/target)
                  const edgesDetail: InspectorGraphEdge[] = rawData.edges.map((edge) => ({
                    source:
                      typeof edge.source === "object"
                        ? (edge.source as GraphNode).id
                        : edge.source,
                    target:
                      typeof edge.target === "object"
                        ? (edge.target as GraphNode).id
                        : edge.target,
                    type: edge.type,
                    properties: edge.properties || {},
                  }));

                  return (
                    <NodeInspector
                      node={nodeDetail}
                      edges={edgesDetail}
                      nodes={nodesDetail}
                      onClose={() => setSelectedNode(null)}
                      onUpdate={(updatedNode) => {
                        // Update the node in rawData
                        if (!rawData) return;
                        const nodeIndex = rawData.nodes.findIndex((n) => n.id === updatedNode.id);
                        if (nodeIndex !== -1) {
                          const updatedRawNode = {
                            ...rawData.nodes[nodeIndex],
                            id: updatedNode.id,
                            label: updatedNode.label,
                            properties: updatedNode.properties,
                          };
                          setRawData({
                            ...rawData,
                            nodes: [
                              ...rawData.nodes.slice(0, nodeIndex),
                              updatedRawNode,
                              ...rawData.nodes.slice(nodeIndex + 1),
                            ],
                          });
                        }
                      }}
                      onAddEdge={(newEdge) => {
                        // Add the new edge to rawData
                        if (!rawData) return;
                        // Find the source and target nodes as GraphNode objects for the edge
                        const sourceNode = rawData.nodes.find((n) => n.id === newEdge.source);
                        const targetNode = rawData.nodes.find((n) => n.id === newEdge.target);
                        if (sourceNode && targetNode) {
                          const edgeToAdd: GraphEdge = {
                            source: sourceNode,
                            target: targetNode,
                            type: newEdge.type,
                            properties: newEdge.properties || {},
                          };
                          setRawData({
                            ...rawData,
                            edges: [...rawData.edges, edgeToAdd],
                          });
                        }
                      }}
                    />
                  );
                })()}
              </div>
            )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default GraphVisualization;
