import { create } from 'zustand';

interface EasyModeState {
  easyGenre: string;
  easyKeywords: string;
  easyArchetype: string;
  easyStyleKey: string;
  easyTargetEps: number;
  easyWordCount: number;
  easyConcept: string;
  enableErotic: boolean;
  eroticIntensity: number;
  enableIllustration: boolean;
  illustrationType: 'cover' | 'episode' | 'both';
  illustrationModel: 'fast' | 'quality';
  generateCover: boolean;
  generateEpisodeIllustrations: boolean;
  episodeInterval: number;
  setEasyGenre: (val: string) => void;
  setEasyKeywords: (val: string) => void;
  setEasyArchetype: (val: string) => void;
  setEasyStyleKey: (val: string) => void;
  setEasyTargetEps: (val: number) => void;
  setEasyWordCount: (val: number) => void;
  setEasyConcept: (val: string) => void;
  setEnableErotic: (val: boolean) => void;
  setEroticIntensity: (val: number) => void;
  setEnableIllustration: (val: boolean) => void;
  setIllustrationType: (val: 'cover' | 'episode' | 'both') => void;
  setIllustrationModel: (val: 'fast' | 'quality') => void;
  setGenerateCover: (val: boolean) => void;
  setGenerateEpisodeIllustrations: (val: boolean) => void;
  setEpisodeInterval: (val: number) => void;
}

export const useEasyModeStore = create<EasyModeState>((set) => ({
  easyGenre: 'ダークファンタジー',
  easyKeywords: '追放, 復讐, システムハック',
  easyArchetype: 'avenger',
  easyStyleKey: 'style_web_standard',
  easyTargetEps: 10,
  easyWordCount: 3000,
  easyConcept: '',
  enableErotic: false,
  eroticIntensity: 2,
  enableIllustration: false,
  illustrationType: 'both',
  illustrationModel: 'quality',
  generateCover: true,
  generateEpisodeIllustrations: false,
  episodeInterval: 3,
  setEasyGenre: (val) => set({ easyGenre: val }),
  setEasyKeywords: (val) => set({ easyKeywords: val }),
  setEasyArchetype: (val) => set({ easyArchetype: val }),
  setEasyStyleKey: (val) => set({ easyStyleKey: val }),
  setEasyTargetEps: (val) => set({ easyTargetEps: val }),
  setEasyWordCount: (val) => set({ easyWordCount: val }),
  setEasyConcept: (val) => set({ easyConcept: val }),
  setEnableErotic: (val) => set({ enableErotic: val }),
  setEroticIntensity: (val) => set({ eroticIntensity: val }),
  setEnableIllustration: (val) => set({ enableIllustration: val }),
  setIllustrationType: (val) => set({ illustrationType: val }),
  setIllustrationModel: (val) => set({ illustrationModel: val }),
  setGenerateCover: (val) => set({ generateCover: val }),
  setGenerateEpisodeIllustrations: (val) => set({ generateEpisodeIllustrations: val }),
  setEpisodeInterval: (val) => set({ episodeInterval: val }),
}));
