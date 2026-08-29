// frontend/src/types/storyCanvas.ts
// ストーリーキャンバス用型定義（草稿・ステップ5）
// SSOT: src/models/api_schemas.py と合わせる

export type NodeKind =
  | 'premise'
  | 'act'
  | 'episode'
  | 'scene'
  | 'character'
  | 'foreshadow';

export type EdgeKind =
  | 'flow'
  | 'part_of'
  | 'pov'
  | 'dependency'
  | 'relationship';

export interface StoryNode {
  id: string;
  book_id: number;
  kind: NodeKind;
  label: string;
  ep_num?: number;
  character_id?: number;
  x: number;
  y: number;
  data: Record<string, unknown>;
}

export interface StoryEdge {
  id: string;
  book_id: number;
  source: string;
  target: string;
  kind: EdgeKind;
  data?: Record<string, unknown>;
}

// API レスポンス型
export interface StoryCanvasResponse {
  nodes: StoryNode[];
  edges: StoryEdge[];
}

// リクエスト型
export interface CreateNodeRequest {
  kind: NodeKind;
  label: string;
  ep_num?: number;
  character_id?: number;
  x: number;
  y: number;
  data?: Record<string, unknown>;
}

export interface UpdateNodeRequest {
  id: string;
  x?: number;
  y?: number;
  label?: string;
  data?: Record<string, unknown>;
}

export interface CreateEdgeRequest {
  source: string;
  target: string;
  kind: EdgeKind;
  data?: Record<string, unknown>;
}