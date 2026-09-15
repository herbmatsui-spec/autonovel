/**
 * 原稿ローカルキャッシュスナップショット型定義
 */
export interface EditorSnapshot {
  key: string;
  bookId: string | number;
  episodeId: string | number;
  content: string;
  charCount: number;
  updatedAt: number; // UNIX timestamp (ms)
}

export type AutoSaveStatus = "saved" | "saving" | "unsaved" | "offline";

export interface RecoveryCheckResult {
  hasRecoveryCandidate: boolean;
  localSnapshot: EditorSnapshot | null;
  serverContent: string;
  serverUpdatedAt?: number;
}