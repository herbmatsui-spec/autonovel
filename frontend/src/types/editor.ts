/**
 * 上級者エディタ（Studio Mode）型定義
 */

// ==========================================
// 1. インライン AI & 五感・Show Don't Tell 拡張
// ==========================================

export type SensoryType =
  | "visual"     // 視覚
  | "auditory"   // 聴覚
  | "olfactory"  // 嗅覚
  | "tactile"    // 触覚
  | "gustatory"  // 味覚
  | "metaphor";  // 比喩

export type ToneType =
  | "tension"     // 緊迫感
  | "erotic"      // 官能的ニュアンス
  | "fast_paced"  // テンポ加速
  | "formal"      // 重厚・格調高い文体
  | "lyrical";    // 叙情的・情緒的文体

export type AssistAction =
  | "describe"        // 五感描写拡張
  | "show_dont_tell"  // Show, Don't Tell 変換
  | "rewrite"         // トーン書き換え
  | "expand";         // 続きの展開・肉付け

export interface AssistRequest {
  text: string;
  action: AssistAction;
  sensory_type?: SensoryType | null;
  tone_type?: ToneType | null;
  genre?: string;
  context_before?: string;
  context_after?: string;
  custom_instruction?: string;
}

export interface AssistResponse {
  original_text: string;
  result_text: string;
  action: AssistAction;
  diff_summary: string;
}

// ==========================================
// 2. GraphRAG 専属 AI 編集者 (Ask Bible & 矛盾診断)
// ==========================================

export interface GraphEvidenceNode {
  id: string;
  label: string;
  properties: Record<string, any>;
  source_reference: string;
}

export interface AskBibleRequest {
  book_id?: number;
  query: string;
  current_chapter?: number;
}

export interface AskBibleResponse {
  answer: string;
  evidence_nodes: GraphEvidenceNode[];
  related_characters: string[];
}

export interface ConsistencyIssue {
  id?: string | number;
  issue_type: string;
  severity: "error" | "warning" | "info";
  description: string;
  conflicting_text: string;
  suggested_fix: string;
}

export interface ActiveAuditHighlight {
  issueId: string;
  conflictingText: string;
  suggestedFix: string;
  issueType?: string;
}

export interface ResolveIssueRequest {
  action: "Auto-Fix" | "Foreshadowing" | "Ignore";
  note?: string;
}

export interface ResolveIssueResponse {
  status: string;
  message: string;
}

export interface ConsistencyAuditRequest {
  book_id?: number;
  content: string;
  current_chapter?: number;
}

export interface ConsistencyAuditResponse {
  has_issues: boolean;
  issues: ConsistencyIssue[];
  confidence_score: number;
}

// ==========================================
// 3. Next Beats 3バリエーション分岐生成
// ==========================================

export type BranchType = "royal" | "twist" | "psychology";

export interface BeatCard {
  card_id: string;
  branch_type: BranchType;
  title: string;
  summary: string;
  content: string;
  hook_text: string;
}

export interface NextBeatsRequest {
  book_id?: number;
  current_text: string;
  genre?: string;
  character_context?: string;
  temperature?: number;
}

export interface NextBeatsResponse {
  beats: BeatCard[];
  original_tail: string;
}
