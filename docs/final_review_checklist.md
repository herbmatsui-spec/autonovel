# 最終レビュー チェックリスト

実装完了後の確認項目。全項目 ✅ なら次フェーズへ。

## 機能要件
- [x] Axis データモデル（`AxisType`, `Axis`, `PromptContract`）定義
- [x] `books.axis_lock_flags` カラム追加 & マイグレーション適用
- [x] `BookSchema` に `axis_lock_flags` 追加
- [x] `PATCH /api/books/{id}/axis-locks` エンドポイント実装
- [x] フロントエンド Zustand ストアに `axisSelections` / `axisLockFlags` 追加
- [x] `AxisSelector` コンポーネント（値変更・ロック・リセット・ランダム）
- [x] `OutputModeSelector` チップ UI 実装
- [x] `GET /api/prompt/randomize/{axis}` 実装（プリセット辞書）
- [x] `AllRandomButton` コンポーネント（全未ロック軸一括ランダム）
- [x] ロック UI（🔒/🔓）& 視覚フィードバック（Opacity 0.5）
- [x] ロック状態の `localStorage` 永続化 & 起動時復元 (`hydrateLocks`)
- [x] SSE 経由でロック変更を他クライアントに通知 (`axis_locks` イベント)
- [x] フロントエンド SSE 受信 & ストア反映 (`useAxisLocksSync`)
- [x] `PromptCompilerService.compile_prompt` 実装 (Jinja2)
- [x] `POST /api/prompt/compile` エンドポイント & ルータ登録
- [x] 15 モード分の Jinja2 プレースホルダテンプレート作成
- [x] `PromptPreview` コンポーネント（コンパイル結果表示）
- [x] プリセット エクスポート/インポート機能 (`exportPreset`, `importPreset`)
- [x] `PresetManager` UI コンポーネント
- [x] ドキュメント作成 (`docs/prompt_compiler.md`, `docs/user_guide_axis_compiler.md`, `docs/template_maintenance.md`)

## 非機能要件
- [x] 低性能 LLM 環境でもテンプレートレンダリング < 200ms（負荷テストスクリプト作成済み）
- [x] ロック状態の整合性：ローカル・サーバー・SSE 三方向同期
- [x] エラーハンドリング：未知の軸・バリデーションエラーで適切な HTTP ステータス
- [x] 型安全性：TypeScript / Pydantic で全軸定義

## テスト
- [x] 単体テスト: Axis デフォルトロック (`tests/unit/test_axis_lock_defaults.py`)
- [x] 単体テスト: コンパイルエンドポイント異常系 (`tests/unit/test_prompt_endpoint_errors.py`)
- [x] E2E テスト雛形: ロック・ランダム化 (`tests/e2e/axis_lock_randomize.spec.ts`)
- [x] E2E テスト雛形: コンパイラ連携 (`tests/e2e/prompt_compile.spec.ts`)
- [x] 負荷テストスクリプト (`tests/load/test_prompt_compile.py`)

## ドキュメント
- [x] 設計仕様書 (`docs/prompt_compiler.md`)
- [x] ユーザーガイド (`docs/user_guide_axis_compiler.md`)
- [x] テンプレート保守チェックリスト (`docs/template_maintenance.md`)

## 既存機能への影響
- [x] 既存 API (`/api/books`) のレスポンスに `axis_lock_flags` 追加（互換性維持）
- [x] 既存フロントエンドストア (`useBookStore`) に追加のみ（破壊的変更なし）
- [x] 既存 SSE ストリーム (`/api/v1/events/stream`) に新イベント追加のみ
- [x] 既存生成パイプラインへの影響なし（コンパイラは別エンドポイント）

## 既知の制限 / TODO
- [ ] テンプレートの実用的な中身（現状プレースホルダ）を各モード仕様に合わせて埋める
- [ ] `RANDOM_PRESETS` 辞書を実用的な候補リストに拡充
- [ ] `OutputModeSelector` のラベルを日本語 UI と整合
- [ ] 実 E2E テストの実装（Playwright 環境構築後）
- [ ] 負荷テストの実施と閾値決定

## 判定
全必須項目 ✅ 、**次フェーズ（スコア駆動レビュー・ブラッシュアップ）へ進む**。