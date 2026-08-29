import { create } from 'zustand';
import type { StoryNode, StoryEdge, CreateNodeRequest, CreateEdgeRequest, UpdateNodeRequest } from '@/types/storyCanvas';

interface StoryCanvasState {
  nodes: StoryNode[];
  edges: StoryEdge[];
  selectedId: string | null;
  loading: boolean;
  dirty: boolean;
  panX: number;
  panY: number;
  scale: number;

  // Actions
  setNodes: (nodes: StoryNode[]) => void;
  setEdges: (edges: StoryEdge[]) => void;
  setLoading: (loading: boolean) => void;
  setSelected: (id: string | null) => void;
  setDirty: (dirty: boolean) => void;

  // Node operations
  addNode: (req: CreateNodeRequest) => void;
  moveNode: (id: string, x: number, y: number) => void;
  renameNode: (id: string, label: string) => void;
  updateNodeData: (id: string, data: Record<string, unknown>) => void;
  removeNode: (id: string) => void;

  // Edge operations
  addEdge: (req: CreateEdgeRequest) => void;
  removeEdge: (id: string) => void;

  // Viewport
  setPan: (x: number, y: number) => void;
  setScale: (scale: number) => void;
  resetViewport: () => void;

  // Bulk update (from server)
  applyServerNodes: (nodes: StoryNode[]) => void;
  applyServerEdges: (edges: StoryEdge[]) => void;
}

const MIN_SCALE = 0.3;
const MAX_SCALE = 2.0;

export const useStoryCanvasStore = create<StoryCanvasState>((set, get) => ({
  nodes: [],
  edges: [],
  selectedId: null,
  loading: false,
  dirty: false,
  panX: 0,
  panY: 0,
  scale: 1,

  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  setLoading: (loading) => set({ loading }),
  setSelected: (selectedId) => set({ selectedId }),
  setDirty: (dirty) => set({ dirty }),

  addNode: (req) => set((state) => {
    const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const newNode: StoryNode = {
      id: tempId,
      book_id: 0, // will be set by server
      kind: req.kind,
      label: req.label,
      ep_num: req.ep_num,
      character_id: req.character_id,
      x: req.x,
      y: req.y,
      data: req.data || {},
    };
    return { nodes: [...state.nodes, newNode], dirty: true };
  }),

  moveNode: (id, x, y) => set((state) => ({
    nodes: state.nodes.map((n) => (n.id === id ? { ...n, x, y } : n)),
    dirty: true,
  })),

  renameNode: (id, label) => set((state) => ({
    nodes: state.nodes.map((n) => (n.id === id ? { ...n, label } : n)),
    dirty: true,
  })),

  updateNodeData: (id, data) => set((state) => ({
    nodes: state.nodes.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...data } } : n)),
    dirty: true,
  })),

  removeNode: (id) => set((state) => ({
    nodes: state.nodes.filter((n) => n.id !== id),
    edges: state.edges.filter((e) => e.source !== id && e.target !== id),
    selectedId: state.selectedId === id ? null : state.selectedId,
    dirty: true,
  })),

  addEdge: (req) => set((state) => {
    const tempId = `temp-edge-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const newEdge: StoryEdge = {
      id: tempId,
      book_id: 0,
      source: req.source,
      target: req.target,
      kind: req.kind,
      data: req.data || {},
    };
    return { edges: [...state.edges, newEdge], dirty: true };
  }),

  removeEdge: (id) => set((state) => ({
    edges: state.edges.filter((e) => e.id !== id),
    dirty: true,
  })),

  setPan: (panX, panY) => set({ panX, panY }),
  setScale: (scale) => set({ scale: Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale)) }),
  resetViewport: () => set({ panX: 0, panY: 0, scale: 1 }),

  applyServerNodes: (nodes) => set({ nodes, dirty: false }),
  applyServerEdges: (edges) => set({ edges, dirty: false }),
}));