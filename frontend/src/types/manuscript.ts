export type CountMode = 'body' | 'withRuby' | 'publishing';

export interface ManuscriptCountResult {
  body: number;           // ルビタグ・読み・媒介記号を除いた純本文文字数
  withRuby: number;       // ルビ読み込み総文字数
  publishing: number;     // 400字詰め換算ページ数 (小数点1位)
  pages: number;          // publishing を切り上げ
  lines: number;          // 1行40字換算
  readingTimeMinutes: number; // 400字/分換算
}

export interface ManuscriptTargetPreset {
  id: string;
  label: string;          // "新人賞標準 (400字×30枚)"
  targetPages: number;    // 30
  targetChars: number;    // 12000 (400*30)
  warningThreshold: number; // 0.9 (90%で警告)
  maxPages?: number;      // 上限がある場合
}