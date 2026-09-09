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
  style_id?: string;
  style_profile?: any;
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
   status?: "draft" | "writing" | "completed" | "polished";
}

export interface GenerationState {
  isGenerating: boolean;
  statusText: string;
  progressPercent?: number;
  suggestions: string[];
  currentTaskId: string | null;
  error: string | null;
}

export * from "./editor";
export * from "./api.generated";
export * from "./history";
export * from "./graphInspector";
export * from "./styleComparison";
export * from "./marketingShowcase";
export * from "./books";
export * from "./editorSettings";

