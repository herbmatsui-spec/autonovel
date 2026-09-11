export interface OrchestratedGenerateRequest {
  book_id: number;
  branch_id: number;
  ep_num: number;
  title: string;
  synopsis: string;
  target_eps: number;
  concept: string;
  genre: string;
  keywords: string;
  target_word_count: number;
  style_tag?: string;
  llm_config?: Record<string, unknown>;
  correlation_id?: string;
}

export interface OrchestratedGenerateResponse {
  task_id: string;
  status: string;
  message: string;
}

export interface OrchestratedTaskStatus {
  task_id: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  result?: {
    output: string;
    zip_data?: string;
    zip_filename?: string;
    artifacts?: Record<string, unknown>;
  };
  error?: string;
}

export type AgentName = 
  | "planning" | "plot" | "bible" | "context_builder" 
  | "writing" | "enrichment" | "audit" | "illustration" | "marketing";

export interface AgentEvent {
  agent: AgentName;
  payload: Record<string, unknown>;
  correlation_id: string;
  round_id?: string;
  metadata?: Record<string, unknown>;
}

export interface AgentProgress {
  agent: AgentName;
  status: "pending" | "running" | "completed" | "failed";
  startedAt?: number;
  completedAt?: number;
  payload?: Record<string, unknown>;
}

export type GenerationMode = "easy" | "orchestrated";

export interface UnifiedStreamingState {
  mode: GenerationMode;
  isActive: boolean;
  output: string;
  agentProgress: Record<AgentName, { status: string; payload?: any }>;
  error?: string;
}