import { create } from 'zustand';

interface UIState {
  isCreateModalOpen: boolean;
  globalError: string | null;
  setCreateModalOpen: (open: boolean) => void;
  setGlobalError: (error: string | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  isCreateModalOpen: false,
  globalError: null,
  setCreateModalOpen: (open) => set({ isCreateModalOpen: open }),
  setGlobalError: (error) => set({ globalError: error }),
}));
