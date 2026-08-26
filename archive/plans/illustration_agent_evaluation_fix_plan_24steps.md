# イラスト作成サブエージェント 改善実装計画書

## 背景

評価レポートに基づき、以下の問題を優先度順に修正する：
1. テスト失敗 (model_used アサーション)
2. モデル解決チェーンの破綻 (AUTO/tier キー → 実モデルID の変換が未統合)
3. ルーター未登録 / DI 未登録
4. 重複ヘルパー関数
5. フォールバックプロンプトの品質
6. 軽微なバグ (regex, 保存パス)

---

## ステップ 1-4: テスト修正 (最優先)

### ステップ 1
`tests/test_illustration_features.py:119-130` の `test_character_illustrator_builds_prompt` を修正。
デフォルトモデルが `AUTO` に変更されたため、テスト内で `model=IllustrationModel.FAST` を明示的に指定する。

### ステップ 2
`tests/test_illustration_agent.py:8-37` の `test_illustration_agent_prompt_generation` を整理。
未使用のモック (`_ = mock.AsyncMock()`) を削除し、`image_service` の `return_value` を明示的に設定する。

### ステップ 3
`tests/test_illustration_features.py` に `model_selector` のユニットテストを追加。
`resolve_model_id()`, `resolve_request_model()` の各ケース（AUTO, FAST, QUALITY, ULTRA, R15）を検証する。

### ステップ 4
`tests/test_illustration_agent.py` に AUTO モデル解決の統合テストを追加。
`IllustrationAgent.run()` が AUTO モデルで正しく実モデルIDに解決されることを検証する。

---

## ステップ 5-12: モデル解決チェーンの統合 (高優先度)

### ステップ 5
`src/services/image_service.py` を修正。
`config.imagen_models.get_imagen_model_id()` をインポートし、`generate()` の先頭で `model` を解決する。
未知のモデル文字列はデフォルト tier にフォールバックする。

### ステップ 6
`src/services/image_service.py` の `__init__` の `default_model` を `"fast"` (tier キー) に変更。
内部で `get_imagen_model_id()` に変換する。

### ステップ 7
`src/agents/illustration_agent.py` を修正。
`model_selector.resolve_request_model()` をインポートし、`run()` 内でリクエストのモデルを解決してから `image_service.generate()` に渡す。

### ステップ 8
`src/services/illustration/cover_service.py` を修正。
`model_selector.resolve_request_model()` を使用してモデルを解決する。

### ステップ 9
`src/services/illustration/character_service.py` を修正。
`model_selector.resolve_request_model()` を使用してモデルを解決する。

### ステップ 10
`src/services/illustration/scene_service.py` を修正。
`model_selector.resolve_request_model()` を使用してモデルを解決する。

### ステップ 11
`src/backend/workflows/illustration_workflow.py` を修正。
`IllustrationModel[settings.get(...).upper()]` を `IllustrationModel(settings.get(...).lower())` に変更する。
`_determine_safety_level` の安全レベル引数も整合させる。

### ステップ 12
`src/backend/routers/illustrations.py` を修正。
`IllustrationModel(request.get("model", "quality"))` のデフォルト値を確認し、整合性を確保する。

---

## ステップ 13-16: ルーター登録 / DI 統合 (中優先度)

### ステップ 13
`src/backend/server.py` の `router_modules` に `"src.backend.routers.illustrations"` を追加する。

### ステップ 14
`src/core/container.py` にイラスト関連プロバイダーを追加。
`image_service`, `illustration_agent`, `illustration_workflow` を登録する。

### ステップ 15
`src/backend/workflows/full_auto_workflow.py` を修正。
イラスト生成部分を DI コンテナから取得するように変更する。

### ステップ 16
`src/backend/routers/illustrations.py` を修正。
`get_illustration_workflow()` を DI コンテナベースに変更する。

---

## ステップ 17-20: コード品質改善 (中優先度)

### ステップ 17
重複する `_type_value()` を統合する。
`src/agents/illustration_agent.py` と `src/services/illustration/model_selector.py` の両方から削除し、
`src/shared/utils.py` または `src/models/illustration.py` に単一実装を置く。

### ステップ 18
重複する `_is_r15()` / `_safety_value()` を統合する。
同様に単一のユーティリティに集約する。

### ステップ 19
`src/agents/illustration_agent.py` の `_generate_episode()` フォールバックプロンプトを改善。
`scene_text` がない場合でも `book_context` (title, genre, concept) を活用したプロンプトを構築する。

### ステップ 20
`src/services/illustration/scene_service.py` の `SceneExtractor.extract_scenes()` の正規表現を修正。
空文字列が発生しないようにフィルタリングする。

---

## ステップ 21-24: 軽微な修正と検証 (低優先度)

### ステップ 21
`src/services/image_service.py` の `_save_image()` のパス返却を統一。
Web サーバーの静的配信設定に依存しない相対パス `/static/illustrations/xxx.png` を返却する。

### ステップ 22
`tests/test_illustration_agent.py` の未使用コードを整理。
`book_context` 変数の未使用を削除する。

### ステップ 23
`tests/test_illustration_features.py` に `extract_scenes_with_llm` のフォールバックテストを追加。
LLM 失敗時にヒューリスティックにフォールバックすることを検証する。

### ステップ 24
全テスト実行 (`pytest`)、Lint (`ruff`)、TypeCheck (`mypy`) を実行し、すべて通過することを確認する。

---

## 検証基準

- 全テストが PASS すること
- `ruff check src/ tests/` がエラー 0 であること
- `mypy src/` がエラー 0 であること
- イラスト生成が Easy Mode 経由で正常に動作すること
