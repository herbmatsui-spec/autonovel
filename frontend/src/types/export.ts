export type ExportVersion = 'saved' | 'current';
export type ExportDestination = 'zip' | 'epub' | 'clipboard' | 'publish';

export interface ExportTarget {
  bookId: string;
  chapterId: string;
  branchId: string;
  version: ExportVersion;
  destination: ExportDestination;
  label: string;          // 表示用 "第3話 (mainブランチ・現在編集版)"
  wordCount: number;
  lastSavedAt: string;    // ISO string
}

export interface ExportHandoffSummary {
  targets: ExportTarget[];
  primaryTarget: ExportTarget;
  warnings: string[];     // 例: ["保存版と現在編集版で 1,200 字の差分があります"]
}