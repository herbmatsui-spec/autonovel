import { create } from 'zustand';

interface WorkspaceState {
  currentStep: string | null;
  isFirstRun: boolean;
  pendingEasyMode: boolean;
  setCurrentStep: (step: string | null) => void;
  setIsFirstRun: (bool: boolean) => void;
  setPendingEasyMode: (bool: boolean) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  currentStep: null,
  isFirstRun: true,
  pendingEasyMode: false,
  setCurrentStep: (step) => set({ currentStep: step }),
  setIsFirstRun: (bool) => set({ isFirstRun: bool }),
  setPendingEasyMode: (bool) => set({ pendingEasyMode: bool }),
}));