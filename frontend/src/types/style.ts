export interface SentenceLengthModel {
  avg: number;
  std_dev: number;
  min: number;
  max: number;
  description: string;
}

export interface SentenceEndDistribution {
  desu_masu: number;
  da_dearu: number;
  nominal: number;
  exclamatory: number;
  interrogative: number;
  description: string;
}

export interface MetaphorFrequency {
  per_1000_chars: number;
  types: Record<string, number>;
  description: string;
}

export interface StyleProfile {
  id: string;
  name: string;
  genre_hint: string;
  category: string;
  tone_description: string;
  sentence_length: SentenceLengthModel;
  sentence_end_distribution: SentenceEndDistribution;
  metaphor_frequency: MetaphorFrequency;
  kerenmi_intensity: number;
  forbidden_patterns: string[];
  required_patterns: string[];
  few_shot_sample: string;
  raw_sample?: string;
}

export interface StylePresetSummary {
  id: string;
  name: string;
  genre: string;
  description: string;
  tone: string;
  profile?: StyleProfile;
}

export interface DistillRequest {
  sample_text: string;
  name_hint?: string;
}

export interface DistillResponse {
  success: boolean;
  profile: StyleProfile;
}

export interface CadenceStats {
  total_sentences: number;
  repeated_endings_fixed: number;
  avg_sentence_length: number;
  paragraph_count: number;
}

export interface ReformatResponse {
  reformatted_text: string;
  stats: CadenceStats;
}

export interface StyleEntry {
  id: string;
  name: string;
  category: string;
  instruction: string;
  dialogue_ratio: string;
  syntax_rhythm: string;
  metaphor_dna: string;
  noise_dna: string;
  is_light: boolean;
}

export interface StyleCategory {
  id: string;
  label: string;
  style_ids: string[];
}
