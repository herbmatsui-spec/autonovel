# AutoNovel v5.0 (Ver 2.0: Hybrid-Lean Novel Engine) Release Notes

## 概要
AutoNovel v5.0 は、「30秒生成・1話数円・直感共創」をコンセプトとする大幅刷新バージョンです。
肥大化したインフラ・負債を一掃しつつ、**創作論的キャラクタープロファイル（Save The Cat、内なる葛藤、Truth Ledger、鉄の禁忌）**および**プロットアイデア出しアルゴリズム（五感ビートシート、クリフハンガー3分類、成長曲線）**を100%継承・昇華しました。

## 4大柱（Pillars）の実装ハイライト
1. **Pillar 1: Streamlined Agent Flow (A1)**
   - 8専門オーディターを統合し、「静的ルール解析（キャラ語尾・禁忌・NG表現・0ms/0円）」＋「単一LLM定性判定」の二層監査へ刷新。
   - 複数回リトライを廃止し、差分のみを修正する「1パッチPDCA」を確立。
   - 早期離脱（Early Exit）により合格原稿は即時完了。
2. **Pillar 2: Relational Simplicity & Foreshadowing (A2)**
   - Apache AGE（openCypher/グラフDB）を完全撤廃し、シンプルなRDBMS伏線ステートマシンへ移行。
   - 3層ローリング記憶（100字事実ダイジェスト＋直前話＋Truth Ledger）により、100話の超長編でもトークン増加率0.00%（完全プラトー化）を達成。
3. **Pillar 3: Zero-Cost Infra & Pure Creative Pipeline (A3)**
   - ComfyUI/VOICEVOXの自前常駐GPUサーバーを完全廃止し、オンデマンド外部従量API（fal.ai / DALL-E 3 / ElevenLabs）へ移行。
   - 小説投稿サイトのスクレイピング投稿を全廃し、なろう・カクヨム・アルファポリス対応「ワンクリック整形コピー機能」を提供。
   - 外部コマンド不要の純Python商用縦書きEPUB 3組版エンジンを統合（ルビ・圏点・縦中横KDP完全対応）。
   - 1話あたりのトークン/コスト上限サーキットブレーカーを導入。
4. **Pillar 4: Unified Domain Model & Type-Safe UX (A4)**
   - `src/models/` と `src/domain/` の重複を解消し、心理プロファイル・五感ビートを含むPydantic v2統一スキーマへ一本化。
   - OpenAPIスキーマ駆動の自動型同期（TypeSync）を導入し、フロントエンドの8GBメモリ枯渇を解決。
   - 直感的な3ステップ共創UI（企画設計 → 五感ビート・引き確認 → 対話執筆）とSSEリアルタイム進捗配信を実装。
