export interface Book {
  id: number;
  title: string;
  genre: string;
  concept: string;
  synopsis: string;
  target_eps: number;
  cumulative_stress?: number;
  created_at: string;
}

export interface Plot {
  ep_num: number;
  title: string;
  summary: string;
  detailed_blueprint: string;
  tension: number;
  is_catharsis: boolean;
  status: string;
}

export interface Chapter {
  ep_num: number;
  title: string;
  content: string;
  summary: string;
  created_at: string;
}

export interface Bible {
  id?: number;
  book_id?: number;
  settings?: any;
  revealed?: any;
  version?: number;
}

export interface OptimizationHistory {
  id: number;
  report_json: any;
  created_at: string;
}

export interface TaskStatus {
  is_running: boolean;
  current_step: number;
  total_steps: number;
  message: string;
  sub_message: string;
  streaming_text: string;
  logs: string[];
  error?: string;
  result_data?: any;
}

export interface PendingPatch {
  id: number;
  book_id: number;
  patch_type: 'config' | 'prompt';
  patch_content: string;
  ab_test_result: {
    scores?: Record<string, number>;
    habits?: string;
    style_gap?: string;
  };
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  reviewed_at?: string;
}

export interface PromptVersion {
  id: number;
  book_id?: number;
  prompt_key: string;
  version_tag: string;
  content: string;
  score_before?: number;
  score_after?: number;
  ab_test_metrics: {
    scores?: Record<string, number>;
    pending_patch_id?: number;
  };
  rollback_reason?: string;
  is_active: boolean;
  created_at: string;
}

export interface NarrativeMetricTrend {
  ep_num: number;
  scene_num: number;
  scores: Record<string, number>;
}

export interface EasyModeParams {
  genre: string;
  keywords: string;
  archetype_key: string;
  target_eps: number;
  word_count: number;
  concept: string;
  tone_vibe: number;
}

// Re-export API types
export * from './api';
