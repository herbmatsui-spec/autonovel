/**
 * AutoNovel v5.0 Frontend Domain Types
 * 心理学的キャラクター造形および五感ビート・クリフハンガーを含む完全版型定義
 */

export interface SceneBeat {
  beat_num: number;
  physical_action: string;
  sensory_tags: Array<'smell' | 'sound' | 'touch' | 'taste' | 'sight'>;
  emotion_phase: 'buildup' | 'explosion' | 'aftermath' | 'neutral';
  word_budget: number;
}

export interface CliffhangerDef {
  type: 'New Crisis' | 'Shocking Truth' | 'Quiet Foreshadowing';
  description: string;
}

export interface EmotionalHookSpec {
  hook_type: string;
  target_scene: string;
  appeal_point: string;
}

export interface CharacterRelation {
  target_character_name: string;
  relationship_type: string;
  description: string;
  intensity: number;
  secret_aspect?: string;
}

export interface Character {
  id: number;
  book_id: number;
  name: string;
  role: 'protagonist' | 'antagonist' | 'sub';
  gender: string;
  age: string;
  appearance: string;
  personality: string;

  // 心理・葛藤プロファイル (Save The Cat)
  surface_persona: string;
  inner_conflict: string;
  core_trauma: string;
  save_the_cat_event: string;
  social_mask_vs_truth: string;
  iron_constraint: string;

  // 口調・語尾
  first_person: string;
  second_person: string;
  suffix_style: string;
  suffix_patterns: string[];
  dialogue_samples: string[];

  // Truth Ledger
  known_facts: string[];
  unknown_facts: string[];

  relations: CharacterRelation[];
}

export interface Chapter {
  id: number;
  book_id: number;
  episode_number: number;
  title: string;
  content: string;
  digest: string;
  word_count: number;
  status: 'draft' | 'writing' | 'completed' | 'archived';
  scene_beats?: SceneBeat[];
  cliffhanger?: CliffhangerDef;
  emotional_hook?: EmotionalHookSpec;
}

export interface Project {
  id: number;
  name: string;
  description: string;
  genre: string;
  target_chapters: number;
  cheat_scale: number;
  growth_curve: string;
  system_assist: number;
  cost_severity: number;
  thematic_core: string;
}