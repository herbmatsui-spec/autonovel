# AutoNovel v5.0 実装計画書 T5: 商用出力・整形コピー・マルチメディア (全12ステップ)

**対象領域**: コア設計 5 (Commercial Publishing, Platform Copy & Media Mix)  
**目的**: 「小説家になろう」「カクヨム」「アルファポリス」向けのワンクリック整形コピーボタンをメイン画面へ統合し、ヘッダーの「画像生成（アセットパック）」のラベリングと実態の乖離を解消する。  
**前提条件**: 各ステップは単一ファイル・単一責任で完結し、低性能なLLMでも1ステップずつ順番に適用可能。  
**リグレッション防止**: 各コード変更ステップでは既存機能のリグレッションテストを作成し、CIパイプラインで自動検証を行う。

---

## 📋 ステップ一覧マトリクス

| ステップ | 種別 | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Formatter | `src/services/formatters/platform_copy_formatter.py` | [MODIFY] 前書き・後書き・各サイト固有ルビ記法の変換精度向上 |
| **Step 2** | Router | `src/backend/routers/platform_export.py` | [MODIFY] `POST /api/export/copy/` のエラーハンドリングと文字数カウント返却強化 |
| **Step 3** | Test | `tests/unit/api/test_platform_export.py` | [NEW] プラットフォーム整形APIの単体テスト |
| **Step 4** | Component | `frontend/src/components/common/PlatformCopyButton.tsx` | [MODIFY] トースト通知連携、コピー成功アニメーション強化 |
| **Step 5** | Editor | `frontend/src/components/editor/EditorToolbar.tsx` | [MODIFY] エディタ上部ツールバーに `PlatformCopyButton` を配置 |
| **Step 6** | Panel | `frontend/src/components/ExportPanel.tsx` | [MODIFY] エクスポートパネルに `PlatformCopyButton` を配置 |
| **Step 7** | Panel | `frontend/src/components/commercial/CommercialPublishPanel.tsx` | [MODIFY] 商用投稿タブに `PlatformCopyButton` を配置 |
| **Step 8** | App | `frontend/src/App.tsx` | [MODIFY] ヘッダー「🖼️ 画像生成」ボタンの表記を「📦 アセットパック」へ改名 |
| **Step 9** | Modal | `frontend/src/components/illustrations/IllustrationModal.tsx` | [NEW] `src/backend/routers/illustrations.py` を呼ぶ画像生成専用モーダル新設 |
| **Step 10** | Preview | `frontend/src/components/editor/MultimediaPreviewPanel.tsx` | [MODIFY] `placehold.co` 固定ダミーを廃止し、生成済み画像または画像生成ボタンを表示 |
| **Step 11** | Test | `frontend/tests/components/PlatformCopyButton.test.tsx` | [NEW] クリップボードコピー動作のVitest単体テスト |
| **Step 12** | E2E | `tests/integration/test_publishing_export_lifecycle.py` | [NEW] 執筆本文からEPUB生成・整形コピーまでの結合テスト |

---

## 🛠️ 各ステップ詳細手順

### Step 1: プラットフォーム整形エンジンの強化 (`src/services/formatters/platform_copy_formatter.py`)
- **目的**:
  - なろう: `|漢字《ルビ》`
  - カクヨム: `《《傍点》》`, `｜漢字《ルビ》`
  - アルファポリス: `#漢字(ルビ)#`
  各プラットフォームの公式規約に準拠した変換を確実に行う。
- **リグレッション防止**: 
  - 既存のフォーマッターモジュールのインターフェースが変更されないことを確認するため、関連するユニットテストを作成または更新
  - 各プラットフォーム固有の変換ロジックが変更されないことを検証するためのテストケースを追加
- **検証コマンド**: 
  - `pytest tests/unit/publishers/test_narou.py`
  - `python -m pytest tests/unit/services/formatters/ -k platform_copy_formatter -v` (フォーマッターテスト実行)

---

### Step 2: 整形ルーターの改修 (`src/backend/routers/platform_export.py`)
- **目的**: タイトル・前書き・本文・後書きを整形し、総文字数とともにJSON返却。
- **検証コマンド**: `python -c "from src.backend.routers.platform_export import router; print(router)"`
- **リグレッション防止**: 
  - 既存のエンドポイントのインターフェースが変更されないことを確認するため、API契約テストを作成
  - レスポンスフォーマットとステータスコードの互換性を維持するためのテストケースを追加
- **検証コマンド追加**: `python -m pytest tests/unit/routers/test_platform_export.py -v`

---

### Step 3: 整形API単体テスト (`tests/unit/api/test_platform_export.py`)
- **目的**: なろう・カクヨム・アルファポリス形式への変換結果を検証。さらに、既存のプラットフォーム整形APIに対するリグレッションテストを追加。
- **実装内容**: 
  - 正常系テスト（各プラットフォームでの変換）
  - 異常系テスト（不正な入力、空のテキストなど）
  - リグレッションテスト（既存の変換ロジックが変更されないことを確認）
  - エッジケーステスト（特殊文字、長文など）
- **検証コマンド**: `pytest tests/unit/api/test_platform_export.py`
- **リグレッション防止強化**: 
  - テストカバレッジを80%以上維持することを確認
  - CIパイプラインで自動的にリグレッションテストを実行
  - テスト失敗時はブランチマージを防止する設定を追加

---

### Step 4: `PlatformCopyButton.tsx` の機能強化 (`frontend/src/components/common/PlatformCopyButton.tsx`)
- **目的**: コピー完了時に「✨ カクヨム形式でコピーしました」とトースト通知を表示し、生 `fetch` を `apiFetch` へ切り替える。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - UIコンポーネントの変更が既存のスタイルやレイアウトに影響しないことを確認するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のコンポーネントインターフェース（props）が変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm test src/components/common/PlatformCopyButton.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 5: エディタツールバー配備 (`frontend/src/components/editor/EditorToolbar.tsx`)
- **目的**: 執筆中のエディタ上部から、いつでもワンクリックで各サイト形式でコピーできるようにする。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - ツールバーコンポーネントの変更が既存のレイアウトや機能に影響しないことを確認するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のコンポーネントインターフェース（props）が変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm test src/components/editor/EditorToolbar.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 6: エクスポートパネル配備 (`frontend/src/components/ExportPanel.tsx`)
- **目的**: ZIPダウンロードの横に「ワンクリック投稿コピー」セクションを追加。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - エクスポートパネルの変更が既存のスタイルやレイアウトに影響しないことを確認するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のコンポーネントインターフェース（props）が変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm test src/components/ExportPanel.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 7: 商用投稿パネル配備 (`frontend/src/components/commercial/CommercialPublishPanel.tsx`)
- **目的**: 商用投稿管理画面からも即座に整形コピーができるように配置。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - 商用投稿パネルの変更が既存のスタイルやレイアウトに影響しないことを確認するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のコンポーネントインターフェース（props）が変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm test src/components/commercial/CommercialPublishPanel.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 8: ヘッダーボタン表記是正 (`frontend/src/App.tsx`)
- **目的**: 「🖼️ 画像生成」ボタンの表記を「📦 アセットパック」に修正し、モーダルタイトルも統一。
- **検証コマンド**: `cd frontend && npm run build`
- **リグレッション防止**: 
  - メインアプリケーションコンポーネントの変更が既存のナビゲーションやレイアウトに影響しないことを確認するため、包括的なUIテストを実行
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のルーティング機能が変更されないことを確認するためのテストケースを追加
- **検証コマンド追加**: 
  - `cd frontend && npm test src/App.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 9: 画像生成専用モーダル新設 (`frontend/src/components/illustrations/IllustrationModal.tsx`)
- **目的**: 本物の画像生成（キャラクター立ち絵・シーン挿絵・表紙）を行うモーダルを新設し、`POST /api/illustrations/batch` を呼び出す。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - モーダルコンポーネントの変更が既存のスタイルやレイアウトに影響しないことを確認するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のコンポーネントインターフェース（props）が変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm test src/components/illustrations/IllustrationModal.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 10: シーンプレビューのダミー廃止 (`frontend/src/components/editor/MultimediaPreviewPanel.tsx`)
- **目的**: `placehold.co` のダミーURLを全廃し、画像未生成時は「🎨 このシーンの挿絵を生成」ボタンを表示。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`
- **リグレッション防止**: 
  - マルチメディアプレビューパネルの変更が既存のスタイルやレイアウトに影響しないことを確認するため、ビジュアル回帰テストを追加検討
  - アクセシビリティ（a11y）のリグレッションテストを実施
  - 既存のコンポーネントインターフェース（props）が変更されないことを確認
- **検証コマンド追加**: 
  - `cd frontend && npm test src/components/editor/MultimediaPreviewPanel.test.tsx`
  - `cd frontend && npm run test:a11y` (アクセシビリティテスト実行、存在する場合)

---

### Step 11: コピーボタン単体テスト (`frontend/tests/components/PlatformCopyButton.test.tsx`)
- **目的**: ボタンクリックで各形式に変換されたテキストが `navigator.clipboard.writeText` に渡ることをテスト。さらに、既存のコピーボタン機能に対するリグレッションテストを追加。
- **実装内容**: 
  - 正常系テスト（各プラットフォーム形式への変換とコピー）
  - 異常系テスト（クリップボードアクセス失敗時の挙動）
  - リグレッションテスト（既存のコピーロジックが変更されないことを確認）
  - エッジケーステスト（空のテキスト、特殊文字など）
- **検証コマンド**: `cd frontend && npm test frontend/tests/components/PlatformCopyButton.test.tsx`
- **リグレッション防止強化**: 
  - コンポーネントのテストカバレッジを90%以上維持することを確認
  - ビジュアル回帰テストツール（例: Chromatic, Percy）の導入を検討
  - テスト失敗時に詳細なレポートを生成する設定を追加

---

### Step 12: 出版・整形結合E2Eテスト (`tests/integration/test_publishing_export_lifecycle.py`)
- **目的**: 執筆本文からEPUB 3生成および投稿サイト形式テキスト取得の全結合テスト。さらに、システム全体のリグレッション防止のためのベースラインテストとして機能させる。
- **実装内容**: 
  - 正常系E2Eテスト（執筆本文からEPUB生成・整形コピーまでの完全フロー）
  - エラーケースE2Eテスト（ネットワークエラー、バックエンドエラー時の挙動）
  - パフォーマンスリグレッションテスト（応答時間が一定の閾値を超えないことを確認）
  - データ整合性リグレッションテスト（出版データがデータベースに正しく保存されることを確認）
  - クロスブラウザ互換性テスト（フロントエンド描画のリグレッションを検出）
- **検証コマンド**: `pytest tests/integration/test_publishing_export_lifecycle.py`
- **リグレッション防止強化**: 
  - E2EテストをCIパイプラインの必須チェック項目に追加
  - テスト結果のトレンドを監視し、パフォーマンスの劣化を早期検出
  - 本番環境と同等のデータ量でテストを実行し、スケーラビリティのリグレッションを防止
  - テストカバレッジレポートを生成し、重要なパスの見落としがないことを確認

---
### 🛡️ リグレッション防止戦略（全ステップ共通）

本実装計画では、以下のリグレッション防止策を全ステップにわたって実施します：

1. **段階的テスト追加**：各実装ステップにおいて、変更箇所に関するユニットテスト・統合テストを必ず追加または更新
2. **自動検証パイプライン**： 
   - プルリクエスト時に自動的にテストスイートを実行
   - テストカバレッジが基準値（80%）を下回る場合はマージをブロック
   - ビルド失敗時はデプロイを防止
3. **テスト種類の多様化**：
   - ユニットテスト：個別関数・クラスの動作検証
   - 統合テスト：モジュール間の連携検証
   - E2Eテスト：ユーザー視点での完全なワークフロー検証
   - ビジュアル回帰テスト：UIの意図しない変更検出（フロントエンド）
   - アクセシビリティテスト：a11y準拠のリグレッション防止
4. **継続的監視**：
   - テスト実行時間のトレンド監視（パフォーマンスリグレッション検出）
   - テスト失敗パターンの分析と予防的保守
   - 本番環境でのエラーレート監視とテストギャップの特定

この戦略により、商用出力・整形コピー・マルチメディア機能の追加による既存機能への影響を最小限に抑え、高品質なリリースを継続的に実現します。
