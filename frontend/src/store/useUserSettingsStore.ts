import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UserSettingsState {
  apiKey: string;
  temperature: number;
  modelType: string;
  isExpertMode: boolean;
  setApiKey: (key: string) => void;
  setTemperature: (temp: number) => void;
  setModelType: (model: string) => void;
  setIsExpertMode: (val: boolean) => void;
  // added config placeholder
  config: Record<string, unknown>;
  // NSFW consent flag
  nsfwConsented: boolean;
  setNsfwConsented: (val: boolean) => void;
}

export const useUserSettingsStore = create<UserSettingsState>()(
  persist(
    (set) => ({
      apiKey: '',
      temperature: 0.7,
      modelType: 'gpt-4',
      isExpertMode: false,
      setApiKey: (key) => set({ apiKey: key }),
      setTemperature: (temp) => set({ temperature: temp }),
      setModelType: (model) => set({ modelType: model }),
      setIsExpertMode: (val) => set({ isExpertMode: val }),
      // initialize empty config to avoid undefined
      config: {},
      nsfwConsented: false,
      setNsfwConsented: (val) => set({ nsfwConsented: val }),
    }),
    {
      name: 'user-settings',
      // apiKey は XSS での盗難を防ぐため localStorage に永続化しない
      partialize: (state) => ({
        temperature: state.temperature,
        modelType: state.modelType,
        isExpertMode: state.isExpertMode,
        config: state.config,
        nsfwConsented: state.nsfwConsented,
      }),
    }
  )
);
