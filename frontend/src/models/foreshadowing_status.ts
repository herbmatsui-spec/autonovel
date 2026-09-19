/**
 * 伏線スコープのステータス定義（フロントエンド用）。
 *
 * ForeshadowingScopeBadge コンポーネントが参照する enum。
 * バックエンドの src/config における伏線スコープ分類と整合する。
 */
export enum ForeshadowingScope {
  /** 即回収（短期的伏線） */
  SHORT_TERM = 'short_term',
  /** 1巻クライマックス（長期的伏線） */
  LONG_TERM = 'long_term',
}
