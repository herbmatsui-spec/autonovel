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

export interface ChapterItem {
  id?: number;
  ep_num: number;
  title: string;
  summary?: string;
  content: string;
  is_catharsis?: boolean;
  status?: "draft" | "writing" | "completed";
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

export * from "./editor";
export * from "./api.generated";

