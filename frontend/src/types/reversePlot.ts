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

export interface ReversePlotAnswers {
  emotionalGoal: string;
  sacrifice: string;
  coreConflict: string;
  openingHook: string;
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