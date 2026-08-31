export interface ToastNotification {
  id: string;
  type: "success" | "error" | "info";
  message: string;
  durationMs?: number;
}

export interface CharacterParams {
  name: string;
  personality: string;
  ability: string;
  genre: string;
}

export interface Chapter {
  id?: number;
  ep_num: number;
  title: string;
  content: string;
}

export interface GenerationState {
  isGenerating: boolean;
  statusText: string;
  progressPercent?: number;
  currentOutput: string;
  suggestions: string[];
  currentTaskId: string | null;
  error: string | null;
}
