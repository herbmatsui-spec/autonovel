# UI/UX画像生成強化計画（24ステップ）

## 1. 背景
AutoNovel は既に画像生成基盤（Unified Illustration Engine）を備えているが、UI/UX 上では画像生成が「オプション機能」として扱われており、ユーザー体験への統合が不十分である。画像生成をストーリー体験の中心に据え、見栄えと機能性を両立させ、さらに商業的成功（フリーミアム転換・アップセル）に結びつけることを目的とする。

## 2. 目的
- 画像生成を執筆・閲覧ワークフローにシームレスに組み込む
- ユーザーのエンゲージメントと滞在時間を向上させる
- フリーミアムモデルによるアップセル経路を明確化する
- SNSシェアを促進し、オーガニックマーケティングを強化する

## 3. 対象範囲
- フロントエンド：縦書きリーダー（VerticalReader.tsx）、ブックショーケース（BookShowcaseModal.tsx）、AssetPackPanel、Studio ワークスペース
- バックエンド：画像生成 API（/api/illustrations/*）、マルチメディアエンドポイント
- データベース：イラストメタデータの拡張（ウォーターマーク設定、解像度 tier、コレクションフラグ）
- マーケティング：プロモーションカード生成機能の強化

## 4. 前提条件
- Unified Illustration Engine が正常に動作していること（src/services/illustration/*）
- フロントエンドは React 18 + TypeScript + Vite で構築されていること
- 認証・クレジットシステムが既に実装済みであること（src/backend/routers/billing.py 等）

## 5. 用語定義
- ウォーターマーク：無料版画像に付与される「AutoNovelで生成」のテキストまたはロゴ
- ティア：画像の解像度・品質レベル（free: 512px, pro: 1024px, enterprise: 2048px+）
- コレクション：ユーザーが取得したイラストをカード形式で保存・表示する機能

## 6. ステップ詳細

### フェーズ1: 基盤整備（Step 1-6）
**Step 1**: データベーススキーマ拡張
- `illustrations` テーブルに `watermark_enabled` (boolean), `resolution_tier` (enum: free/pro/enterprise), `is_collectible` (boolean) カラムを追加
- マイグレーションスクリプトを作成し、既存データにデフォルト値を設定

**Step 2**: バックエンド画像生成エンドポイント強化
- `/api/illustrations/generate` に `watermark: boolean?`, `tier: string?` パラメータを追加
- 画像生成後にウォーターマーク付与処理（Pillow を使用）を実装
- ティアに応じて解像度を調整（設定ファイルから参照）

**Step 3**: フロントエンド画像生成フック拡張
- `useMultimedia.ts` に `generateIllustrationWithOptions` 関数を追加（watermark, tier オプション対応）
- エラーハンドリングとローディング状態を改善

**Step 4**: 設定ファイル統一
- `src/config/image_tiers.py` を新規作成し、各ティアの解像度・価格・ウォーターマーク有無を定義
- `src/config/billing_plans.py` と連携し、プランごとの利用可能ティアを設定

**Step 5**: テスト追加
- バックエンド：ウォーターマーク付与・ティア別解像度のユニットテスト
- フロントエンド：フックのオプション渡しをモックでテスト

**Step 6**: ドキュメント更新
- API 仕様書（OpenAPI）に新パラメータを追加
- 開発者向けガイドに画像生成オプションの使い方を記載

### フェーズ2: 縦書きリーダーへのインライン画像統合（Step 7-12）
**Step 7**: 縦書きリーダーのデータ構造拡張
- `VerticalReaderProps` に `illustrations: Array<{id:string, url:string, position:number}>` を追加（position: 本文中の挿入位置）

**Step 8**: バックエンド：章ごとのイラスト取得エンドポイント作成
- `/api/illustrations/by-chapter/{bookId}/{chapterIndex}` を実装し、該当章のイラストを位置情報付きで返却

**Step 9**: フロントエンド：章ロード時にイラストも取得
- `VerticalReader.tsx` で `useEffect` を追加し、章コンテンツと同時にイラストリストをフェッチ

**Step 10**: インラインレンダーロジック実装
- 本文をブロック（段落）に分割し、各ブロックの後に対応位置のイラストを挿入
- 画像は `object-fit: contain; max-width: 100%; border-radius: 8px;` で表示

**Step 11**: 画像インタラクション機能
- 画像をクリックするとモーダル（IllustrationModal の簡易版）を開き、プロンプト表示・再生成ボタンを表示
- 再生成時は同じプロンプト・ティアで新しい画像を取得し、差し替える

**Step 12**: テスト・検証
- 縦書きリーダーにイラストが正しく挿入されるかの E2E テスト（Cypress または Playwright）
- パフォーマンステスト：画像遅延読み込み（loading="lazy"）を実装し、初期描画速度を測定

### フェーズ3: 表紙・プロモーションカードAI強化（Step 13-18）
**Step 13**: 表紙生成バックエンド統合
- `/api/illustrations/cover-generate` エンドポイントを作成し、ジャンル・キーワード・スタイルから表紙プロンプトを自動生成
- スタイルプリセットを `src/config/cover_styles.yaml` に定義（anime, lightnovel, literary, retro 等）

**Step 14**: フロントエンド表紙プレビュー強化
- `BookCoverPreview.tsx` に「AI表紙生成」ボタンを追加
- ボタンクリックで上記エンドポイントを呼び出し、結果をプレビューに反映
- 生成後は「ダウンロード」「再生成」「スタイル変更」ボタンを表示

**Step 15**: プロモーションカードバリエーション拡張
- `PromoCardGenerator.tsx` にレイアウト選択肢（縦長・横長・ストーリー形式）を追加
- 各レイアウトごとに最適なフォントサイズ・色彩をプリセット

**Step 16**: 有料ティア向け機能ロック
- ウォーターマーク除去、高解像度ダウンロード、商用利用ライセンス付与をプロプラン以上に制限
- フロントエンドでプランチェックを行い、制限機能はグレーアウトしツールチップでアップセル案内を表示

**Step 17**: テスト追加
- 表紙・プロモーションカード生成の統合テスト（バックエンドAPI + フロントエンド表示）
- 有料ティア制御のユニットテスト

**Step 18**: ドキュメント・ツールチップ整備
- 各ボタンにツールチップを追加し、有料機能の利点を説明
- FAQ に「画像生成の商用利用について」を追加

### フェーズ4: イラストガチャ＆コレクション機能（Step 19-24）
**Step 19**: コレクションデータモデル設計
- `user_illustration_collections` テーブルを新規作成（user_id, illustration_id, obtained_at, rarity）
- `rarity` 列は enum (common, rare, epic, legendary) とし、獲得確率を設定

**Step 20**: ガチャバックエンド実装
- `/api/illustrations/gacha/pull` エンドポイントを作成し、クレジット消費とともにランダムなイラストを1枚付与
- レアリティ別排出率を設定可能にし、デフォルトは common: 70%, rare: 20%, epic: 8%, legendary: 2%
- 付与時にコレクションテーブルに記録

**Step 21**: フロントエンドガチャUI
- `src/components/generate/GachaIllustrationModal.tsx` を新規作成（既存 GachaModal をベースに）
- スロットアニメーション、レアリティ別エフェクト（光沢・音効果）を実装
- 結果表示時に「コレクションに追加」「シェア」ボタンを表示

**Step 22**: コレクションビューア実装
- Studio ワークスペースに新規タブ「イラストコレクション」を追加
- カードグリッドで所持イラストを表示し、フィルタ（レアリティ・種類）・ソート機能を提供
- カードをクリックすると詳細モーダル（大きな画像・プロンプト・取得日時）を表示

**Step 23**: ボーナスシステム連携
- 特定のコレクション達成条件（例：レアリティ別コンプリート）を満たすと、自動的にクレジット付与または限定アイテム（フォント・BGM）を付与
- 達成条件は `src/config/collection_bonuses.yaml` に定義

**Step 24**: テスト・ローンチ準備
- ガチャ確率の統計テスト（10000回シミュレーションで期待値と誤差を検証）
- コレクションビューアのパフォーマンステスト（1000枚以上でもスムーズに表示）
- リリースノート作成およびベータテスト計画を策定

## 7. 期待効果
- ユーザー滞在時間：縦書きリーダーでの画像挿入により平均滞在時間 20% 向上
- アップセル率：ウォーターマーク除去・高解像度オプションによりフリーミアムからプロへの転換率 15% 向上
- SNS拡散：プロモーションカード生成機能によりシェア数 2倍増加
- コレクション要素によるリテンション：月間アクティブユーザーの 30-day リテンション率 10% 向上

## 8. リスクと対策
| リスク | 影響 | 対策 |
|--------|------|------|
| 画像生成コスト増加 | 変動費がかさむ | ティア別コスト管理、無料版は下位モデル・低解像度に制限 |
| ウォーターマーク除去の不正利用 | ブランド毀損 | 有料プランでのログイン認証＋利用規約同意を必須 |
| ガチャのギャンブル性懸念 | 法規制リスク | 排出率を公開し、有料クレジットは「消耗品」として位置付け、賞品はゲーム内アイテムに限定 |
| 実装工数の増大 | リリース遅れ | 各ステップを小さな PR に分割し、段階的にマージしていく |

## 9. 成功指標（KPIs）
- 画像生成リクエスト数（日次）
- ウォーターマーク除去利用率（有料プランユーザー中）
- ガチャ引き回数（日次）
- コレクションビューア訪問率（Studio ユーザー中）
- SNSシェア経由流入数
- アップセル転換率（free → pro）

## 10. リリース計画
- フェーズ1（基盤整備）：2週間
- フェーズ2（縦書きリーダー）：3週間
- フェーズ3（表紙・プロモーションカード）：2週間
- フェーズ4（ガチャ・コレクション）：3週間
- 各フェーズ終了後に内部 QA とベータテストを実施し、フィードバックを反映

## 11. 関連ファイル一覧
- データベース：`src/infrastructure/database/models/illustration.py`（拡張予定）
- バックエンド：`src/backend/routers/illustrations.py`, `src/services/illustration/unified_generator.py`, `src/services/illustration/clients/*`
- フロントエンド：`frontend/src/components/showcase/VerticalReader.tsx`, `frontend/src/components/showcase/BookCoverPreview.tsx`, `frontend/src/components/showcase/PromoCardGenerator.tsx`, `frontend/src/components/generate/GachaIllustrationModal.tsx`（新規）, `frontend/src/components/studio/StudioWorkspace.tsx`（タブ追加）
- 設定：`src/config/image_tiers.py`, `src/config/cover_styles.yaml`, `src/config/collection_bonuses.yaml`
- テスト：`tests/unit/services/test_illustration_tiers.py`, `tests/frontend/verticalReader.integration.tsx` 等

## 12. 付録：参考実装スニペット
（省略：実際のコードは別途チケットに分割）

---
以上