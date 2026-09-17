# AutoNovel v5.0 (Ver 2.0: Hybrid-Lean Novel Engine) Release Notes

## 概要
AutoNovel v5.0 は、「30秒生成・1話数円・直感共創」をコンセプトとする大幅刷新バージョンです。
肥大化したインフラ・負債を一掃しつつ、**創作論的キャラクタープロファイル（Save The Cat、内なる葛藤、Truth Ledger、鉄の禁忌）**および**プロットアイデア出しアルゴリズム（五感ビートシート、クリフハンガー3分類、成長曲線）**を100%継承・昇華しました。

## 4大柱（Pillars）の実装ハイライト
1. **Pillar 1: Streamlined Agent Flow (A1)**
    - 8専門オーディターを統合し、「静的ルール解析（キャラ語尾・禁忌・NG表現・0ms/0円）」＋「単一LLM定性判定」の二層監査へ刷新。
    - 複数回リトライを廃止し、差分のみを修正する「1パッチPDCA」を確立。
2. **Pillar 2: Relational Simplicity & Foreshadowing (A2)**
    - Apache AGE（openCypher/グラフDB）を完全撤廃し、シンプルなRDBMS伏線ステートマシンへ移行。
    - 3層ローリング記憶（100字事実ダイジェスト＋直前話＋Truth Ledger）により、長編でもトークン消費を固定化。
3. **Pillar 3: Zero-Cost Infra & Pure Creative Pipeline (A3)**
    - ComfyUI/VOICEVOXの自前GPUサーバーを完全廃止し、外部従量API（fal.ai / DALL-E / ElevenLabs）へ移行。
    - 小説投稿サイトのスクレイピング投稿を全廃し、なろう・カクヨム・アルファポリス対応「ワンクリック整形コピー機能」を提供。
    - 商用KDP/楽天Kobo準拠の純Python縦書きEPUB 3組版エンジンを統合。
    - 1話あたりのトークン/コスト上限サーキットブレーカーを導入。
4. **Pillar 4: Unified Domain Model & Type-Safe UX (A4)**
    - `src/models/` と `src/domain/` の重複を解消し、心理プロファイル・五感ビートを含むPydantic v2統一スキーマへ一本化。
    - OpenAPIスキーマ駆動の自動型同期（TypeSync）を導入し、フロントエンドの8GBメモリ枯渇を解決。
    - 直感的な3ステップ共創UI（企画設計 → 五感ビート・引き確認 → 対話執筆）とSSE進捗配信を実装.

## 仕様検証完了チェックリスト
- [x] Step 1: Pydantic v2 共通ドメイン基底スキーマ定義
- [x] Step 2: Project & Book 統一スキーマ（チート度・成長曲線・代償パラメータ完全網羅）
- [x] Step 3: Chapter & Plot 統一スキーマ（五感ビートシート・クリフハンガー3分類完全網羅）
- [x] Step 4: Character 統一スキーマ（Save The Cat・内なる葛藤・Truth Ledger・語尾完全網羅）
- [x] Step 5: Foreshadowing 統一ドメインスキーマ
- [x] Step 6: Two-Tier Audit 統一レポートスキーマ
- [x] Step 7: 統一ドメインスキーマのエクスポート集約
- [x] Step 8: 新しい統一スキーマへの移行とレスポンス正規化
- [x] Step 9: Projects ルーターの統一スキーマ移行
- [x] Step 10: 最新FastAPIから正確なOpenAPI JSONを安定出力
- [x] Step 11: openapi-typescript による高速型自動生成スクリプト
- [x] Step 12: package.json の type:sync コマンド追加とメモリ最適化
- [x] Step 13: 型チェックのメモリ消費を抑制するコンパイラ設定最適化
- [x] Step 14: 詳細心理プロファイル・五感ビートを含むフロントエンド型定義
- [x] Step 15: 3ステップUI Step 1: 企画アイデア創出フォーム（チート度・成長曲線UI）
- [x] Step 16: 3ステップUI Step 2: 章立て・五感ビート・クリフハンガー3分類プレビュー
- [x] Step 17: 3ステップUI Step 3: 対話型執筆・プレビュー
- [x] Step 18: リアルタイム生成プログレスバー（SSE連動）
- [x] Step 19: なろう/カクヨム/アルファポリス整形コピーUI
- [x] Step 20: 3ステップ共創ワークフロー統合ページ
- [x] Step 21: Server-Sent Events (SSE) 執筆ストリーミングAPI
- [x] Step 22: SSEストリーミングAPIの単体テスト
- [x] Step 23: プロット入力〜章生成〜監査〜EPUB出力の全結合テスト
- [x] Step 24: v5.0リリースノート・仕様検証完了チェックリスト

## 今後の展望
- フロントエンドの型安全性をさらに強化し、バックエンドとの完全な型同期を維持
- SSEストリーミングの実際のAI執筆プロセスとの連携を深化
- プラットフォーム別整形ルールの拡張とカスタマイズ性の向上