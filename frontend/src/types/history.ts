export interface EditorSnapshot {
  id: string;
  ep_num: number;
  timestamp: number;
  label: string; // 例: "AI推敲前", "逆算プロット反映前", "手動保存"
  text: string;
  charCount: number;
  source: "manual" | "ai_assist" | "ai_generate" | "autosave";
}