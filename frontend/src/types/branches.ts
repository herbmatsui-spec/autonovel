/** ブランチ関連のTypeScript型定義 */

/** ブランチタイプ（バックエンドのBranchTypeと同期） */
export enum BranchType {
  ROYAL = 'royal',          // 王道・カタルシス・主人公の活躍
  TWIST = 'twist',          // サスペンス・急展開・どんでん返し
  PSYCHOLOGY = 'psychology' // 日常・心情深化・キャラクターの掛け合い
}

/** 単一ブランチのレスポンス */
export interface BranchResponse {
  id: number;
  book_id: number;
  name: string;
  parent_id: number | null;
  fork_ep_num: number | null;
  created_at: string | null; // ISO datetime string
}

/** ブランチ配下の IF グラフ JSON レスポンス */
export interface BranchGraphResponse {
  branch_id: number;
  graph: Record<string, any>;
}

/** フォーク（分岐作成）リクエスト */
export interface BranchForkRequest {
  parent_id: number;
  name: string;
  fork_ep_num: number;
}

/** マージ（合流）リクエスト */
export interface BranchMergeRequest {
  source_branch_id: number;
  target_branch_id: number;
  merge_ep_num: number;
  name?: string | null;
}

/** 差分ビューア用の章レベル差分 */
export interface ChapterDiff {
  chapter_number: number;
  content_a: string; // ブランチAの内容
  content_b: string; // ブランチBの内容
  diff_unified: string; // 統一フォーマットの差分
}

/** マージコンフリクトプレビュー用 */
export interface ConflictChunk {
  id: string;
  base: string; // 基底テキスト
  source: string; // ソースブランチのテキスト
  target: string; // ターゲットブランチのテキスト
}

/** ブランチツリー可視化用（バックエンドからの実際のレスポンス形式） */
export interface BranchTreeNode {
  id: number;
  data: {
    label: string;
    bookId: number;
    parentId: number | null;
    forkEpNum: number | null;
    createdAt: string | null;
  };
  position: { x: number; y: number };
}

export interface BranchTreeEdge {
  id: string;
  source: number;
  target: number;
  type: string;
}

export interface BranchTreeData {
  nodes: BranchTreeNode[];
  edges: BranchTreeEdge[];
}

/** ブランチツリーAPIレスポンス */
export interface BranchTreeResponse {
  nodes: BranchTreeNode[];
  edges: BranchTreeEdge[];
}

/** 章レベル差分APIレスポンス */
export interface ChapterDiffResponse {
  chapter_number: number;
  branch_a_name: string;
  branch_b_name: string;
  content_a: string;
  content_b: string;
  diff_unified: string;
  diff_side_by_side: {
    left: string[];
    right: string[];
  };
}

/** マージコンフリクトプレビューAPIレスポンス */
export interface MergePreviewResponse {
  can_merge: boolean;
  has_conflicts: boolean;
  conflict_chunks: ConflictChunk[];
  merged_content?: string;
  // 追加情報
  source_branch_id?: number;
  target_branch_id?: number;
  base_branch_id?: number | null; // 共通祖先ブランチID
}

/** マージ実行リクエスト */
export interface MergeRequest {
  source_branch_id: number;
  target_branch_id: number;
  merge_ep_num: number;
  name?: string | null;
}

/** マージ実行レスポンス */
export interface MergeResponse {
  success: boolean;
  branch_id: number; // マージ後のブランチID
  message: string;
  // コンフリクトがある場合の詳細
  conflict_chunks?: ConflictChunk[];
}

/** コンフリクト解決済み章コンテンツ (Step 49 / Step 61) */
export interface ResolvedChapterPayload {
  chapter_number: number;
  resolved_content: string;
  resolution_strategy: 'base' | 'source' | 'target' | 'manual' | string;
}

/** マージ確定コミットリクエスト (Step 49 / Step 61) */
export interface BranchMergeCommitRequest {
  source_branch_id: number;
  target_branch_id: number;
  merge_ep_num: number;
  resolved_chapters: ResolvedChapterPayload[];
  commit_message?: string;
}

/** マージ確定コミッドレスポンス (Step 49 / Step 61) */
export interface BranchMergeCommitResponse {
  success: boolean;
  target_branch_id: number;
  updated_chapters_count: number;
  committed_at: string;
}

