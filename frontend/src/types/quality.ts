/**
 * 品質診断・スコアリング関連の型定義
 */

export interface LineScore {
  line: number;
  score: number;
  level: "error" | "warning" | "info" | "good";
  message?: string;
}
