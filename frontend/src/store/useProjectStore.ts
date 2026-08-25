import { create } from 'zustand';

export type TabId = 'books' | 'plots' | 'write' | 'analytics' | 'planning' | 'style-lab' | 'audit' | 'landing' | 'strategy' | 'monitor' | 'import' | 'easy';

interface ProjectContextState {
  selectedBookId: number | null;
  // activeTab removed; use URL via react-router-dom
  setSelectedBookId: (id: number | null) => void;
  // setActiveTab removed;
}

export const useProjectStore = create<ProjectContextState>((set) => ({
  selectedBookId: null,
  // activeTab: 'landing',
  setSelectedBookId: (id) => set({ selectedBookId: id }),
  // setActiveTab: (tab) => set({ activeTab: tab }),
}));