export interface GraphNode {
  id: string;
  label?: string;
  properties?: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  properties?: Record<string, unknown>;
}

export interface GraphDataResponse {
  graph_name: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  error?: string;
}

export interface ChapterChunkItem {
  id: string;
  chapter_id: number;
  chunk_index: number;
  content: string;
  has_embedding: boolean;
  created_at: string | null;
}
