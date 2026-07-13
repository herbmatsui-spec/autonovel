import { create } from 'zustand';

interface WritingState {
  writeFrom: number;
  writeTo: number;
  writePassion: number;
  importEpNum: number;
  importText: string;
  importDoRefine: boolean;
  setWriteFrom: (val: number) => void;
  setWriteTo: (val: number) => void;
  setWritePassion: (val: number) => void;
  setImportEpNum: (val: number) => void;
  setImportText: (val: string) => void;
  setImportDoRefine: (val: boolean) => void;
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
  ...DEFAULT_IMPORT,
  setWriteFrom: (val) => set({ writeFrom: val }),
  setWriteTo: (val) => set({ writeTo: val }),
  setWritePassion: (val) => set({ writePassion: val }),
  setImportEpNum: (val) => set({ importEpNum: val }),
  setImportText: (val) => set({ importText: val }),
  setImportDoRefine: (val) => set({ importDoRefine: val }),
  resetImport: () => set({ ...DEFAULT_IMPORT }),
}));
