# 詳細実装計画書: コードレビュー指摘事項の解消

## 概要
コードレビューで特定された重要課題を解消するための、実行可能な最小ステップに分割した実装計画。

**対象課題 (優先度順):**
1. **P0-1**: "DUMMY" API キーフォールバック削除・起動時バリデーション追加
2. **P0-2**: レガシー設定システム非推奨化・移行 (`config/project_context.py`, `schemas/config.py`)
3. **P1-1**: `EngineDeps` をコンテナで使用し 14 明示依存を統合
4. **P1-2**: `mypy --strict` 有効化・`Any` 型排除
5. **P2-1**: `AppContainer2` をサブコンテナに分割
6. **P2-2**: `constants.py` 値を `Settings` に統合

---

## Phase 1: Critical Security & Config (P0) - 完了 ✅

### Step 1-1: "DUMMY" フォールバック削除 - 完了 ✅
- [x] 1-1-1: `src/core/container/app.py` の `api_key` プロバイダから `"DUMMY"` 削除
- [x] 1-1-2: 起動時バリデーション関数 `validate_api_keys()` を `config/settings.py` に追加
- [x] 1-1-3: `src/backend/server.py` の `lifespan` で起動時バリデーション呼出
- [x] 1-1-4: テスト用 `.env.example` に `GEMINI_API_KEY=test-key` 追加
- [x] 1-1-5: `tests/unit/test_container_smoke.py` 等の "DUMMY" 依存テスト修正

### Step 1-2: レガシー設定 `project_context.py` 非推奨化 - 完了 ✅
- [x] 1-2-1: `config/project_context.py` に `DeprecationWarning` 付与
- [x] 1-2-2: `model_router.py` の `get_config()` 呼出を `get_settings()` に置換
- [x] 1-2-3: 他の `get_config()` 使用箇所を全検索・置換 (`grep -r "get_config"`)
- [x] 1-2-4: `schemas/config.py` も同様に非推奨化・移行
- [x] 1-2-5: 移行完了後、レガシーファイルを `archive/` へ移動
- [x] 1-2-6: 後方互換シャム `config/project_context.py` 作成（DeprecationWarning付き）
- [x] 1-2-7: `config/__init__.py` で後方互換エイリアス提供（`get_config`, `set_config`, `PROMPT_TEMPLATES`, `GlobalConfigModel` 等）

## Phase 2: Architecture Refactoring (P1) - 実施中 🔄

### Step 2-1: `EngineDeps` 統合 - 完了 ✅
- [x] 2-1-0: `EngineDeps` データクラス定義済み (`src/backend/engine_deps.py`)
- [x] 2-1-0: `UltimateHegemonyEngine.__init__` が `deps` パラメータ対応済み
- [x] 2-1-1: `src/core/container/app.py` で `EngineDeps` インポート・プロバイダ追加
- [x] 2-1-2: `engine` プロバイダを `deps=engine_deps` 形式に簡素化
- [x] 2-1-3: 不要になった個別プロバイダ (`planner`, `writer`, `pm` 等) の依存解決確認
- [x] 2-1-4: `tests/unit/test_engine_init.py` でコンテナ経由生成テスト追加 (既存テストでカバー)

### Step 2-2: 型安全性強化 (`mypy --strict`) - 進行中 🔄
- [x] 2-2-1: `pyproject.toml` に `mypy --strict` 設定追加・除外設定調整
- [x] 2-2-2: `config/erotic_vocabulary.py` - 戻り値型 `Dict[str, List[str]]` 修正
- [x] 2-2-2: `config/erotic_parameters.py` - `Dict[str, Any]` 型引数追加、`Any` import追加、`__post_init__` に `-> None` 追加
- [x] 2-2-2: `config/validator.py` - `Dict` import追加、`Callable` import追加、`tomllib` 重複import解消、`_safe_load` 関数に型アノテーション追加
- [x] 2-2-2: `prompts/manager.py` - `BASE_DIR` import修正、`Environment` 型修正
- [x] 2-2-2: `prompts/registry.py` - `PromptTemplateNotFoundError` import追加、`logger` 追加、`BASE_DIR` 追加、戻り値型アノテーション追加（4メソッド）、`get_active_version` → `get_active_prompt_version` 修正
- [x] 2-2-3: `src/core/llm_gateway.py` の `Any` 型修正 (`UsageProtocol` 追加、`_usage_metric` 型修正、ファクトリ型修正、`cast` 使用、`genai.Client` 修正)
- [x] 2-2-4: `src/easy_mode/` 以下の型アノテーション補完 (progress_reporter, models, series_finalizer, spice_guard/marker, spice_guard/extractor, spice_guard/pattern_registry, episode_writer, episode_rewriter, episode_auditor)
- [ ] 2-2-4: `src/easy_mode/` 以下の残りの型アノテーション補完 (bible_generator, episode_generator, pipeline, plot_generator, episode_writer, episode_rewriter, phase3/*, 等)
- [ ] 2-2-5: CI に `mypy --strict src/` 追加

## Phase 3: Container Modularization (P2) - 未着手
### Step 3-1: `AppContainer2` 分割
- [ ] 3-1-1: `src/core/container/engine.py` (EngineContainer) 新規作成
- [ ] 3-1-2: `src/core/container/agents.py` (AgentsContainer) 新規作成
- [ ] 3-1-3: `src/core/container/services.py` (ServicesContainer) 新規作成
- [ ] 3-1-4: `AppContainer2` を薄いアグリゲートにリファクタ
- [ ] 3-1-5: 各サブコンテナの独立テスト追加

### Step 3-2: `constants.py` 統合
- [ ] 3-2-1: `config/constants.py` の全定数を `config/settings.py` の `Settings` フィールドに移植
- [ ] 3-2-2: `constants.py` 参照箇所を `get_settings().FIELD_NAME` に置換 (`grep -r "constants\."`)
- [ ] 3-2-3: `constants.py` を後方互換エイリアスのみ残して非推奨化
- [ ] 3-2-4: 移行検証テスト追加

---

## 実行ルール

1. **1ステップ = 1つの小さなアクション** (5-10分で完了)
2. **各ステップ後に**: 
   - `python -m py_compile <変更ファイル>` で構文チェック
   - `ruff check <変更ファイル>` でリント
   - 関連テスト実行 (`pytest tests/unit/test_<関連>.py -x -q`)
3. **コミット単位**: 論理的なまとまりごと (例: Step 1-1 完了後コミット)
4. **ブロッカー発生時**: 即座に記録し、次の独立ステップへ進む

---

## 進捗管理

```markdown
- [x] Step 1-1-1: DUMMY削除
- [x] Step 1-1-2: 起動時バリデーション追加
- [x] Step 1-1-3: lifespan呼出追加
- [x] Step 1-1-4: .env.example更新
- [x] Step 1-1-5: テスト修正
- [x] Step 1-2-1: project_context.py非推奨化
- [x] Step 1-2-2: model_router.py修正
- [x] Step 1-2-3: 全get_config()置換
- [x] Step 1-2-4: schemas/config.py非推奨化
- [x] Step 1-2-5: archive移動
- [x] Step 1-2-6: 後方互換シャム作成
- [x] Step 1-2-7: config/__init__.py後方互換対応
- [x] Step 2-1-1: EngineDepsプロバイダ追加
- [x] Step 2-1-2: engineプロバイダ簡素化
- [x] Step 2-1-3: 依存解決確認
- [x] Step 2-1-4: テスト追加
- [x] Step 2-2-1: mypy strict設定
- [x] Step 2-2-2: config/erotic_vocabulary.py 型修正完了
- [x] Step 2-2-2: config/erotic_parameters.py 型修正完了
- [x] Step 2-2-2: config/validator.py 型修正完了
- [x] Step 2-2-2: prompts/manager.py 型修正完了
- [x] Step 2-2-2: prompts/registry.py 型修正完了
- [x] Step 2-2-3: llm_gateway.py 型修正完了
- [ ] Step 2-2-4: easy_mode/ 型補完
- [ ] Step 2-2-5: CI に mypy --strict 追加
- [ ] Step 3-1-1: EngineContainer作成
- [ ] Step 3-1-2: AgentsContainer作成
- [ ] Step 3-1-3: ServicesContainer作成
- [ ] Step 3-1-4: AppContainer2リファクタ
- [ ] Step 3-1-5: サブコンテナテスト
- [ ] Step 3-2-1: constants.py移植
- [ ] Step 3-2-2: 参照置換
- [ ] Step 3-2-3: 非推奨化
- [ ] Step 3-2-4: 検証テスト
```

---

## 完了基準 (Definition of Done)

- [ ] 全テストパス (`pytest tests/ -x --ignore=tests/integration` 3分以内)
- [ ] `mypy --strict src/` エラー 0 件
- [ ] `ruff check src/` エラー 0 件
- [ ] "DUMMY" キーで起動不可 (明示的エラー)
- [ ] `get_config()` 呼出 0 件 (`grep -r "get_config\(\)" src/`)
- [ ] `constants.` 参照 0 件 (`grep -r "constants\." src/`)
- [ ] `Any` 型 0 件 (`grep -r ": Any" src/ --include="*.py" | grep -v test`)
- [ ] CI パイプライン全グリーン