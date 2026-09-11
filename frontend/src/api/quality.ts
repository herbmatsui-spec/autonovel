import { apiFetch, handleResponse } from './client';

export interface BookScore {
  book_id: number;
  chapter_number: number;
  overall_score: number;
  structure_score: number;
  coherency_score: number;
  factual_grounding_score: number;
  visual_textual_synergy_score: number;
  reader_experience_score: number;
  evaluated_at: string | null;
  trend_3ch: {
    avg_overall_score: number;
    trend_slope: number;
    chapters_count: number;
    recent_scores: { chapter: number; overall: number }[];
  } | null;
}

export interface BookScoreHistoryResponse {
  history: {
    book_id: number;
    chapter_number: number;
    overall_score: number;
    structure_score: number;
    coherency_score: number;
    factual_grounding_score: number;
    visual_textual_synergy_score: number;
    reader_experience_score: number;
    evaluated_at: string;
    evaluator_version: string;
  }[];
  benchmarks: {
    target_genre: string;
    target_overall: number;
    target_structure: number;
    target_coherency: number;
    target_factual: number;
    target_visual: number;
    target_reader: number;
    is_gap_significant: boolean;
  } | null;
}

export interface PDCACycleSnapshot {
  id: number;
  cycle_number: number;
  stage: string;
  score: number;
  scores_by_specialist: Record<string, number>;
  calibrated_scores: Record<string, number>;
  lowest_dimension: string | null;
  directives_count: number;
  delta: number;
  converged: boolean;
  created_at: string;
}

export async function fetchChapterBookScore(bookId: number, chapterNumber: number): Promise<BookScore> {
  const res = await apiFetch(`/api/novel/books/${bookId}/chapters/${chapterNumber}/score`);
  return handleResponse<BookScore>(res, 'Failed to fetch chapter book score');
}

export async function fetchBookScoreHistory(bookId: number): Promise<BookScoreHistoryResponse> {
  const res = await apiFetch(`/api/books/${bookId}/book-scores/history`);
  return handleResponse<BookScoreHistoryResponse>(res, 'Failed to fetch book score history');
}

export async function fetchPDCACycles(bookId: number, chapterNumber: number): Promise<PDCACycleSnapshot[]> {
  const res = await apiFetch(`/api/books/${bookId}/pdca/cycles/${chapterNumber}`);
  return handleResponse<PDCACycleSnapshot[]>(res, 'Failed to fetch PDCA cycles');
}
