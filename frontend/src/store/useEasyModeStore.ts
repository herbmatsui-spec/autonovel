import { create } from 'zustand';

interface EasyModeState {
  easyGenre: string;
  easyKeywords: string;
  easyArchetype: string;
  easyTargetEps: number;
  easyWordCount: number;
  easyConcept: string;
  setEasyGenre: (val: string) => void;
  setEasyKeywords: (val: string) => void;
  setEasyArchetype: (val: string) => void;
  setEasyTargetEps: (val: number) => void;
  setEasyWordCount: (val: number) => void;
  setEasyConcept: (val: string) => void;
}

export const useEasyModeStore = create<EasyModeState>((set) => ({
  easyGenre: 'ダークファンタジー',
  easyKeywords: '追放, 復讐, システムハック',
  easyArchetype: 'avenger',
  easyTargetEps: 10,
  easyWordCount: 3000,
  easyConcept: '',
  setEasyGenre: (val) => set({ easyGenre: val }),
  setEasyKeywords: (val) => set({ easyKeywords: val }),
  setEasyArchetype: (val) => set({ easyArchetype: val }),
  setEasyTargetEps: (val) => set({ easyTargetEps: val }),
  setEasyWordCount: (val) => set({ easyWordCount: val }),
  setEasyConcept: (val) => set({ easyConcept: val }),
}));
