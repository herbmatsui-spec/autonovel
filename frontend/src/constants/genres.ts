/**
 * バックエンド preset とマッピングされた UI ジャンル選択肢。
 * resolve_genre_to_preset のキーワード (src/backend/routers/easy_mode.py) と整合すること。
 */
export interface GenreOption {
  value: string;
  presetKey: string | null;
}

export const GENRE_OPTIONS: GenreOption[] = [
  { value: "ハイファンタジー (R15)", presetKey: null },
  { value: "ダークファンタジー (R15)", presetKey: "cheat_tensei" },
  { value: "異世界転生・バトル (R15)", presetKey: "cheat_tensei" },
  { value: "ざまぁ・追放・無双 (R15)", presetKey: "zarma" },
  { value: "悪役令嬢・婚約破棄", presetKey: "aku_reijo" },
  { value: "追放後スローライフ", presetKey: "slow_life" },
  { value: "VRMMO・ゲーム世界", presetKey: "vrmmo" },
];

// ==========================================
// ジャンルバッジ設定
// ==========================================

export interface GenreBadgeConfig {
  bg: string;
  text: string;
  border: string;
  emoji: string;
}

export const GENRE_BADGE_CONFIG: Record<string, GenreBadgeConfig> = {
  "ハイファンタジー (R15)": { bg: "rgba(167, 139, 250, 0.2)", text: "#a78bfa", border: "#a78bfa", emoji: "🏰" },
  "ダークファンタジー (R15)": { bg: "rgba(124, 58, 237, 0.2)", text: "#7c3aed", border: "#7c3aed", emoji: "🌑" },
  "異世界転生・バトル (R15)": { bg: "rgba(34, 197, 94, 0.2)", text: "#22c55e", border: "#22c55e", emoji: "🌀" },
  "ざまぁ・追放・無双 (R15)": { bg: "rgba(249, 115, 22, 0.2)", text: "#f97316", border: "#f97316", emoji: "⚔️" },
  "悪役令嬢・婚約破棄": { bg: "rgba(236, 72, 153, 0.2)", text: "#ec4899", border: "#ec4899", emoji: "👑" },
  "追放後スローライフ": { bg: "rgba(234, 179, 8, 0.2)", text: "#eab308", border: "#eab308", emoji: "🍃" },
  "VRMMO・ゲーム世界": { bg: "rgba(6, 182, 212, 0.2)", text: "#06b6d4", border: "#06b6d4", emoji: "🎮" },
  "デフォルト": { bg: "rgba(161, 161, 170, 0.2)", text: "#a1a1aa", border: "#a1a1aa", emoji: "📚" },
};

export function getGenreBadgeConfig(genre: string): GenreBadgeConfig {
   return GENRE_BADGE_CONFIG[genre] ?? GENRE_BADGE_CONFIG["デフォルト"]!;
 }