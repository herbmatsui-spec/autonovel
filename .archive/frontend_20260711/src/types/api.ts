// frontend/src/types/api.ts
// ===================================
// 対応するバックエンド型 (src/models/api_schemas.py):
//   BookSchema       → Book
//   PlotSchema       → Plot
//   ChapterSchema    → Chapter
//   BibleSchema      → Bible
//   TaskStatusSchema → TaskStatus
// ===================================

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

export interface EasyModeParams {
  api_key: string;
  config: any;
  genre: string;
  keywords: string;
  archetype_key: string;
  target_eps: number;
  initial_limit: number;
  word_count: number;
  concept?: string;
  tone_vibe?: number;
}

export interface EpisodeGenerateParams {
  api_key: string;
  config: any;
  book_id: number;
  write_from: number;
  write_to: number;
  passion: number;
  word_count: number;
  do_refine: boolean;
  env_state: Record<string, string>;
  pipeline_mode: boolean;
}

export interface PlanGenerationParams {
  api_key: string;
  config: any;
  params: Record<string, any>;
}

export interface RetryFailedParams {
  api_key: string;
  config: any;
  book_id: number;
  passion: number;
  word_count: number;
}

export interface PlotExpandParams {
  api_key: string;
  config: any;
  book_id: number;
  gen_from: number;
  gen_to: number;
}

export interface PlotRebuildParams {
  api_key: string;
  config: any;
  params: Record<string, any>;
}

export interface CritiqueOptimizeParams {
  api_key: string;
  config: any;
  book_id: number;
}

export interface AuditPlanParams {
  api_key: string;
  genre: string;
  keywords: string;
  trend_memo: string;
}

export interface ChapterImportParams {
  api_key: string;
  book_id: number;
  ep_num: number;
  import_text: string;
  do_refine: boolean;
}

export interface MarketingGenerateParams {
  api_key: string;
  book_id: number;
  latest_ep: number;
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
