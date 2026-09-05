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