import { create } from 'zustand';

interface ProjectContextState {
  selectedBookId: number | null;
  activeTab: 'books' | 'plots' | 'write' | 'analytics';
  setSelectedBookId: (id: number | null) => void;
  setActiveTab: (tab: 'books' | 'plots' | 'write' | 'analytics') => void;
}

export const useProjectStore = create<ProjectContextState>((set) => ({
  selectedBookId: null,
  activeTab: 'books',
  setSelectedBookId: (id) => set({ selectedBookId: id }),
  setActiveTab: (tab) => set({ activeTab: tab }),
}));
