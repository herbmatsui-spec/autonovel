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
}

export const useUserSettingsStore = create<UserSettingsState>()(
  persist(
    (set) => ({
      apiKey: '',
      temperature: 0.7,
      modelType: 'gemini-2.5-pro',
      isExpertMode: false,
      setApiKey: (key) => set({ apiKey: key }),
      setTemperature: (temp) => set({ temperature: temp }),
      setModelType: (model) => set({ modelType: model }),
      setIsExpertMode: (val) => set({ isExpertMode: val }),
    }),
    {
      name: 'user-settings',
    }
  )
);
