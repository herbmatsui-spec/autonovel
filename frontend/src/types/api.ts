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
  detailed_blueprint?: string;
  tension?: number;
  is_catharsis?: boolean;
  status?: string;
  next_hook?: string;
  plot_variants?: Array<Record<string, unknown>>;
}

export interface Chapter {
  ep_num: number;
  title: string;
  content: string;
  summary: string;
  created_at: string;
  quality_score?: number;
  event_density?: number;
  commercial_score?: number;
  commercial_breakdown?: {
    opening_hook?: number;
    cadence_pull?: number;
    emotional_amplitude?: number;
    mystery_foreshadowing?: number;
    cliffhanger_tension?: number;
  };
  killer_phrase?: string;
  requires_revision?: boolean;
}

export interface Bible {
  id?: number;
  book_id?: number;
  settings?: Record<string, unknown>;
  revealed?: Record<string, unknown>;
  version?: number;
}

export interface OptimizationHistory {
  id: number;
  report_json: Record<string, unknown>;
  created_at: string;
}

export interface TaskError {
  code: string;
  message: string;
  detail?: string;
  timestamp: string;
  retry_after_ms?: number;
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
  task_error?: TaskError;
  recoverable?: boolean;
  resume_from_step?: number;
  partial_result?: Record<string, unknown>;
  result_data?: Record<string, unknown>;
}

export interface EasyModeParams {
  api_key?: string;
  config: Record<string, unknown>;
  genre: string;
  keywords: string;
  archetype_key: string;
  target_eps: number;
  initial_limit: number;
  word_count: number;
  concept?: string;
  tone_vibe?: number;
  style_key?: string;
  enable_erotic?: boolean;
  erotic_intensity?: number;
  // Illustration settings
  enableIllustration?: boolean;
  illustrationType?: 'cover' | 'episode' | 'both';
  illustrationModel?: 'fast' | 'quality';
  generateCover?: boolean;
  generateEpisodeIllustrations?: boolean;
  episodeInterval?: number;
}

export interface EpisodeGenerateParams {
  api_key?: string;
  config: Record<string, unknown>;
  book_id: number;
  write_from: number;
  write_to: number;
  passion: number;
  word_count: number;
  do_refine: boolean;
  env_state: Record<string, string>;
  pipeline_mode: boolean;
  mode?: 'final' | 'candidates';
}

export interface EpisodeGenerateCandidatesParams extends EpisodeGenerateParams {
  mode: 'candidates';
}

export interface PlanGenerationParams {
  api_key?: string;
  config: Record<string, unknown>;
  params: Record<string, unknown>;
}

export interface RetryFailedParams {
  api_key?: string;
  config: Record<string, unknown>;
  book_id: number;
  passion: number;
  word_count: number;
}

export interface PlotExpandParams {
  api_key?: string;
  config: Record<string, unknown>;
  book_id: number;
  gen_from: number;
  gen_to: number;
  mode?: 'final' | 'candidates';
}

export interface PlotRebuildParams {
  api_key?: string;
  config: Record<string, unknown>;
  params: Record<string, unknown>;
}

export interface CritiqueOptimizeParams {
  api_key?: string;
  config: Record<string, unknown>;
  book_id: number;
}

export interface AuditPlanParams {
  api_key?: string;
  genre: string;
  keywords: string;
  trend_memo: string;
}

export interface ChapterImportParams {
  api_key?: string;
  book_id: number;
  ep_num: number;
  import_text: string;
  do_refine: boolean;
}

export interface MarketingGenerateParams {
  api_key?: string;
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

export interface HealthStatus {
  status: string;
  database: string;
  worker: string;
  huey_backend: string;
  queue_depth: number;
}

export interface PlanningOptions {
  easy_genres: Record<string, { genre: string; archetype: string; desc: string }>;
  story_archetypes: string[];
  style_definitions: Record<string, { name: string; description: string }>;
  planning_presets: Record<string, { name: string; description: string }>;
}

export interface StyleDnaResult {
  // Placeholder for style DNA analysis results
  // Actual structure would be defined based on backend API
  analysis: Record<string, unknown>;
  contradictions: string[];
  suggestions: string[];
}

export interface ExportPackageResult {
  // Placeholder for export package result
  // Actual structure would be defined based on backend API
  package_id: string;
  download_url: string;
  expires_at: string;
}

export interface AuditPlanResult {
  // Placeholder for audit plan results
  // Actual structure would be defined based on backend API
  score: number;
  recommendations: string[];
  issues_found: string[];
}

export interface Issue {
  id: number;
  category: string;
  severity: 'high' | 'medium' | 'low';
  ep_num: number;
  created_at: string;
  contradiction_content: string;
  evidence_past?: string;
  evidence_current?: string;
  constraint_for_next_ep?: string;
  status: string;
  resolved_note?: string;
}
