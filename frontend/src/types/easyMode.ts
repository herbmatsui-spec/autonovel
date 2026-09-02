export interface CharacterParams {
  name: string;
  personality: string;
  ability: string;
  genre: string;
}

export interface EasyModeInput {
  chapter_history: string[];
  current_chapter: string;
  character_params: CharacterParams | Record<string, unknown>;
  content_length_limit: number;
}

export interface GenerationResponse {
  task_id?: string;
  output: string;
  completion_time_ms: number;
  error: string;
  suggestions: string[];
}

export interface ExportPackage {
  zipBlob: Blob;
  filename: string;
}

export interface ExportRequestPayload {
  title?: string;
  genre?: string;
  current_text?: string;
  character?: CharacterParams | Record<string, unknown>;
  plots?: Array<{ ep_num: number; title: string; one_line_summary: string }>;
}

export type TaskStatus = "pending" | "running" | "completed" | "failed";

export interface TaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  result?: unknown;
  error?: string;
}

export type GachaPlanType = "royal" | "curveball" | "dark";

export interface GachaPlan {
  plan_id: string;
  plan_type: GachaPlanType;
  title: string;
  logline: string;
  protagonist_summary: string;
  charm_point: string;
}

export interface GachaRequest {
  genre: string;
  keywords: string[];
  temperature?: number;
}

export interface GachaResponse {
  request_id: string;
  plans: GachaPlan[];
}

export interface DigestRequest {
  request_id: string;
  selected_plan_id: string;
}

export interface DigestResponse {
  book_id: string;
  title: string;
  synopsis: string;
  episode_1_text: string;
  climax_preview_text: string;
  status: "processing" | "completed" | "failed";
}

export interface PromotionRequest {
  book_id: string;
}

export interface PromotionResponse {
  success: boolean;
  redirect_url: string;
  state_token: string;
}

