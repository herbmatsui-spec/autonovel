import { create } from 'zustand';

interface WritingState {
  writeFrom: number;
  writeTo: number;
  writePassion: number;
  importEpNum: number;
  importText: string;
  importDoRefine: boolean;
  genre: string;
  title: string;
  wordCount: number;
  platform: string;
  showPreview: boolean;
  error: string | null;
  setWriteFrom: (val: number) => void;
  setWriteTo: (val: number) => void;
  setWritePassion: (val: number) => void;
  setImportEpNum: (val: number) => void;
  setImportText: (val: string) => void;
  setImportDoRefine: (val: boolean) => void;
  setGenre: (val: string) => void;
  setTitle: (val: string) => void;
  setWordCount: (val: number) => void;
  setPlatform: (val: string) => void;
  setShowPreview: (val: boolean) => void;
  setError: (msg: string | null) => void;
  clearError: () => void;
  resetImport: () => void;
}

const DEFAULT_IMPORT = {
  importEpNum: 1,
  importText: '',
  importDoRefine: true,
};

export const useWritingStore = create<WritingState>((set) => ({
  writeFrom: 1,
  writeTo: 5,
  writePassion: 0.85,
  genre: 'fantasy',
  title: '無題の小説',
  wordCount: 3000,
  platform: 'kakuyomu',
  showPreview: false,
  error: null,
  ...DEFAULT_IMPORT,
  setWriteFrom: (val) => set({ writeFrom: val }),
  setWriteTo: (val) => set({ writeTo: val }),
  setWritePassion: (val) => set({ writePassion: val }),
  setImportEpNum: (val) => set({ importEpNum: val }),
  setImportText: (val) => set({ importText: val }),
  setImportDoRefine: (val) => set({ importDoRefine: val }),
  setGenre: (val) => set({ genre: val }),
  setTitle: (val) => set({ title: val }),
  setWordCount: (val) => set({ wordCount: val }),
  setPlatform: (val) => set({ platform: val }),
  setShowPreview: (val) => set({ showPreview: val }),
  setError: (msg) => set({ error: msg }),
  clearError: () => set({ error: null }),
  resetImport: () => set({ ...DEFAULT_IMPORT }),
}));
