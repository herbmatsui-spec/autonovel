import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UserSettingsState {
  apiKey: string;
  temperature: number;
  modelType: string;
  setApiKey: (key: string) => void;
  setTemperature: (temp: number) => void;
  setModelType: (model: string) => void;
}

export const useUserSettingsStore = create<UserSettingsState>()(
  persist(
    (set) => ({
      apiKey: '',
      temperature: 0.7,
      modelType: 'gemini-2.5-pro',
      setApiKey: (key) => set({ apiKey: key }),
      setTemperature: (temp) => set({ temperature: temp }),
      setModelType: (model) => set({ modelType: model }),
    }),
    {
      name: 'user-settings',
    }
  )
);
