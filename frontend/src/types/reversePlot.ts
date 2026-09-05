import { LLMConfigOverride } from "./easyMode";

export interface ReversePlotStep {
  step: 1 | 2 | 3 | 4;
  title: string;
  question: string;
  options: ReversePlotOption[];
  aiHint: string;
}

export interface ReversePlotOption {
  label: string;
  value: string;
  example: string;
}

/**
 * 逆算プロットビルダーの 4 ステップ回答データ。
 * バックエンド ReversePlotGeneratePayload.answers (dict[str, Any]) のキー仕様と整合させる。
 * 最低 4 つの主要キーを保持し、未入力ステップは空文字で送信する。
 */
export interface ReversePlotAnswers {
  /** Step 1: 感情的ゴール (triumph / bittersweet / catharsis / growth) */
  emotionalGoal: string;
  /** Step 2: 犠牲・代償 (peace / memory / relationship / status) */
  sacrifice: string;
  /** Step 3: 核心対立 (ideal_vs_reality / order_vs_chaos / self_vs_society / man_vs_nature) */
  coreConflict: string;
  /** Step 4: オープニングフック (isekai_awakening / revenge_return / confession_seal / mystery_arrival) */
  openingHook: string;
  /** 各ステップで自由入力された追加テキスト */
  customInputs?: Record<string, string>;
}

export interface GeneratedPlotStructure {
  arcs: ArcBlueprint[];
  episodes: PlotEpisodeInit[];
  catharsisPattern?: CatharsisPatternInit;
  catharsis_pattern?: CatharsisPatternInit;
}

export interface ReversePlotGenerateRequest {
  answers: ReversePlotAnswers | Partial<ReversePlotAnswers>;
  target_episodes?: number;
  targetEpisodes?: number;
  genre: string;
  llm_config?: LLMConfigOverride;
}

export interface ArcBlueprint {
  arc_num: number;
  start_ep: number;
  end_ep: number;
  title: string;
  summary: string;
  conflictType: string;
}

export interface PlotEpisodeInit {
  ep_num: number;
  title: string;
  one_line_summary: string;
  tension: number;
  catharsis: number;
  is_catharsis: boolean;
  thematic_milestone: string;
  burned_cost_or_loot: string;
  antagonist_status: string;
  resolution_style: 'Cheat' | 'Logic' | 'Focus_Drama';
}

export interface CatharsisPatternInit {
  pattern_type: string;
  catharsis_points: number[];
  tension_wave: number[];
}