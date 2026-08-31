export interface EasyModeInput {
  chapter_history: string[];
  current_chapter: string;
  character_params: Record<string, unknown>;
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

export type TaskStatus = "pending" | "running" | "completed" | "failed";

export interface TaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  result?: unknown;
}
