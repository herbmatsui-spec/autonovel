/**
 * Types for Marketing CTR & Viral Title Generator
 */

export interface TitleCandidate {
  title: string;
  score: number;
  structure_breakdown: Record<string, any>;
  length: number;
  syntax_match: boolean;
  high_ctr_keywords: string[];
  critique: string;
  synopsis_snippet?: string;
}

export interface ViralTitleRequest {
  genre: string;
  core_trope: string;
  protagonist_name?: string;
  protagonist_cheat?: string;
  antagonist_or_oppression?: string;
  target_audience?: string;
  num_candidates?: number;
}

export interface ViralTitleResponse {
  genre: string;
  total_generated: number;
  top_recommendations: TitleCandidate[];
  all_candidates: TitleCandidate[];
  recommended_synopsis?: string;
  analysis_summary?: string;
}
