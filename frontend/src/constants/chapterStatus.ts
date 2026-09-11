export const chapterStatusMap = {
  draft: { label: "プロット構想", icon: "⚪", color: "#94a3b8" },
  writing: { label: "執筆中", icon: "🟡", color: "#f59e0b" },
  completed: { label: "初稿脱稿", icon: "🟢", color: "#10b981" },
  polished: { label: "推敲完了", icon: "✨", color: "#a855f7" }
} as const;

export type ChapterStatus = keyof typeof chapterStatusMap;