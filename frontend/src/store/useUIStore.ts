import { create } from 'zustand';

import type { OptimizationHistory, PendingPatch, PromptVersion, NarrativeMetricTrend } from '@/types';

interface UIState {
  isCreateModalOpen: boolean;
  globalError: string | null;
  // Analytics specific state
  optHistory: OptimizationHistory[];
  pendingPatches: PendingPatch[];
  promptVersions: PromptVersion[];
  metricTrend: NarrativeMetricTrend[];
  // Setters
  setCreateModalOpen: (open: boolean) => void;
  setGlobalError: (error: string | null) => void;
  setOptHistory: (data: OptimizationHistory[]) => void;
  setPendingPatches: (data: PendingPatch[]) => void;
  setPromptVersions: (data: PromptVersion[]) => void;
  setMetricTrend: (data: NarrativeMetricTrend[]) => void;
}

export const useUIStore = create<UIState>((set) => ({
  isCreateModalOpen: false,
  globalError: null,
  // Analytics state defaults
  optHistory: [],
  pendingPatches: [],
  promptVersions: [],
  metricTrend: [],
  // Setters
  setCreateModalOpen: (open) => set({ isCreateModalOpen: open }),
  setGlobalError: (error) => set({ globalError: error }),
  setOptHistory: (data) => set({ optHistory: data }),
  setPendingPatches: (data) => set({ pendingPatches: data }),
  setPromptVersions: (data) => set({ promptVersions: data }),
  setMetricTrend: (data) => set({ metricTrend: data }),
}));
