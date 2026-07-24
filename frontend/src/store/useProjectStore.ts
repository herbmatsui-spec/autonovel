import { create } from 'zustand';

export type TabId = 'books' | 'plots' | 'write' | 'analytics' | 'planning' | 'style-lab' | 'audit' | 'landing' | 'strategy' | 'monitor' | 'import' | 'easy';

interface ProjectContextState {
  selectedBookId: number | null;
  activeTab: TabId;
  setSelectedBookId: (id: number | null) => void;
  setActiveTab: (tab: TabId) => void;
}

export const useProjectStore = create<ProjectContextState>((set) => ({
  selectedBookId: null,
  activeTab: 'books',
  setSelectedBookId: (id) => set({ selectedBookId: id }),
  setActiveTab: (tab) => set({ activeTab: tab }),
}));
