# 実装計画書：テスト修正・技術的負債削除（48ステップ詳細版）

## 概要

本計画書は以下2つの課題を、低性能LLMでも実装可能な **48個の小さなステップ** に分解したものです。

1. **失敗テストの全グリーン化** 🔴 Critical - 7失敗(state) + 接続エラー(integration) + 1失敗(async_ui)
2. **技術的負債の物理的削除** 🟠 High - kernels/移動、リポジトリ統合、plugin_loader重複解消

---

## パートA: 失敗テストの全グリーン化（ステップ 1〜24）

### A-1: stateテスト 7失敗の修正（ステップ 1〜10）

#### ステップ 1: `schemas/app_state.py` の `AppRuntimeState` に `active_job_id` プロパティを追加
- **ファイル**: `schemas/app_state.py`
- **変更**: `active_job_ids` dict を保持しつつ、`active_job_id` プロパティ（最初の値を返す）を `@property` で追加
- **理由**: テストが `state.active_job_id` を期待しているが、実装は `active_job_ids` dict のみ
- **所要時間**: 5分

#### ステップ 2: `schemas/app_state.py` の `TokenStats` に `total_tokens` プロパティを追加
- **ファイル**: `schemas/app_state.py`
- **変更**: `prompt` + `completion` を返す `@property` `total_tokens` を追加
- **理由**: テストが `stats.total_tokens == 300` を期待しているが、フィールドは `prompt`/`completion` のみ
- **所要時間**: 5分

#### ステップ 3: `tests/state/test_app_state.py` の確認・実行
- **コマンド**: `python -m pytest tests/state/test_app_state.py -v`
- **期待**: 2テストがパス（`test_runtime_state_defaults`, `test_token_stats_validation`）
- **所要時間**: 2分

#### ステップ 4: `kernels/interaction_manager.py` の `__init__` を `InteractionConfig` オブジェクト受け取り対応に変更
- **ファイル**: `kernels/interaction_manager.py`
- **変更**: 
  - `__init__(self, config: Union[str, InteractionConfig])` に変更
  - `isinstance(config, str)` なら YAML 読み込み、そうでなければ直接使用
- **理由**: テストが `InteractionConfig` オブジェクトを直接渡すが、実装はファイルパス文字列のみ受け付ける
- **所要時間**: 10分

#### ステップ 5: `kernels/interaction_manager.py` の `_load_config` を内部メソッド化（オプション）
- **ファイル**: `kernels/interaction_manager.py`
- **変更**: 文字列パス受け取り時のみ呼び出されるヘルパーとして残す
- **所要時間**: 5分

#### ステップ 6: `tests/state/test_interaction_manager.py` の確認・実行
- **コマンド**: `python -m pytest tests/state/test_interaction_manager.py -v`
- **期待**: 3テストがパス
- **所要時間**: 2分

#### ステップ 7: `tests/state/test_interaction_simulation.py` の確認・実行
- **コマンド**: `python -m pytest tests/state/test_interaction_simulation.py -v`
- **期待**: 2テストがパス
- **所要時間**: 2分

#### ステップ 8: stateテスト全体の実行・確認
- **コマンド**: `python -m pytest tests/state/ -v`
- **期待**: 10テスト全パス（7失敗→0失敗）
- **所要時間**: 3分

#### ステップ 9: もしまだ失敗あればデバッグ・修正
- **アクション**: 個別テスト実行でエラー内容確認、必要に応じてスキーマやカーネル修正
- **所要時間**: 10分

#### ステップ 10: stateテスト修正完了の記録
- **アクション**: git diff で変更確認、コミットメッセージ準備
- **所要時間**: 3分

---

### A-2: integrationテスト 接続エラーの修正（ステップ 11〜17）

#### ステップ 11: `tests/integration/test_api.py` の問題確認
- **現状**: モジュールレベルで `requests.post()` を実行し、サーバー未起動時に Collection Error になる
- **ファイル**: `tests/integration/test_api.py`
- **所要時間**: 3分（読解）

#### ステップ 12: `tests/integration/test_api.py` を pytest フィクスチャ化
- **変更**: 
  - モジュールレベルの実行コードを削除
  - `@pytest.fixture(scope="session")` でバックエンドサーバー起動フィクスチャを作成（または `pytest.mark.skipif` でサーバー未起動時スキップ）
  - テスト関数内で `requests.post` する形にリファクタ
- **所要時間**: 20分

#### ステップ 13: `tests/integration/conftest.py` にバックエンド起動フィクスチャ追加
- **ファイル**: `tests/integration/conftest.py`
- **追加**: `backend_server` フィクスチャ（`subprocess.Popen` で uvicorn 起動、yield 後 terminate）
- **ポート**: 8200（test_api.py と合わせる）
- **所要時間**: 15分

#### ステップ 14: `tests/integration/test_api.py` のインポート修正
- **変更**: `requests` インポート追加、フィクスチャ使用に書き換え
- **所要時間**: 5分

#### ステップ 15: integrationテスト全体の実行・確認
- **コマンド**: `python -m pytest tests/integration/ -v --tb=short`
- **期待**: Collection Error なし、テストが実行される（一部失敗してもOK、接続エラーは解消）
- **所要時間**: 30秒

#### ステップ 16: 個別のintegrationテスト失敗があれば修正（モック不足等）
- **アクション**: 各失敗テストを個別実行し、モック・フィクスチャ不足を補完
- **所要時間**: 20分

#### ステップ 17: integrationテスト修正完了の記録
- **アクション**: git diff 確認
- **所要時間**: 3分

---

### A-3: async_ui_sync テスト 1失敗の修正（ステップ 18〜24）

#### ステップ 18: `tests/unit/test_async_ui_sync.py` のエラー確認
- **エラー**: `NameError: name 'MagicMock' is not defined` （行18）
- **原因**: `from unittest.mock import MagicMock` が不足
- **所要時間**: 2分

#### ステップ 19: `tests/unit/test_async_ui_sync.py` に `MagicMock` インポート追加
- **ファイル**: `tests/unit/test_async_ui_sync.py`
- **変更**: 行2付近に `from unittest.mock import MagicMock` 追加
- **所要時間**: 2分

#### ステップ 20: 変数名 `mock_progress_state` の未定義エラー確認・修正
- **現状**: 行27で `mock_progress_state` 使用だが定義なし（`mock_state` との typo 可能性）
- **修正**: `mock_state` に統一、または適切に定義
- **所要時間**: 5分

#### ステップ 21: `mock_db` 未定義エラー確認・修正
- **現状**: 行37で `mock_db.save_internal_state.assert_called()` だが `mock_db` 未定義
- **修正**: `MagicMock()` でモック作成、またはフィクスチャから取得
- **所要時間**: 5分

#### ステップ 22: `test_background_reporter_streaming_persistence` テスト単体実行
- **コマンド**: `python -m pytest tests/unit/test_async_ui_sync.py::test_background_reporter_streaming_persistence -v`
- **期待**: パス（または別のエラーが出ればそれも修正）
- **所要時間**: 3分

#### ステップ 23: async_ui_sync 全テスト実行
- **コマンド**: `python -m pytest tests/unit/test_async_ui_sync.py -v`
- **期待**: 2テスト全パス
- **所要時間**: 2分

#### ステップ 24: 全テストスイート実行・最終確認
- **コマンド**: `python -m pytest tests/state/ tests/integration/ tests/unit/test_async_ui_sync.py -v`
- **期待**: 全テストパス（失敗0）
- **所要時間**: 1分

---

## パートB: 技術的負債の物理的削除（ステップ 25〜48）

### B-1: `kernels/` ディレクトリを `archive/kernels/` へ移動（ステップ 25〜30）

#### ステップ 25: `kernels/` の使用箇所を全検索・リスト化
- **コマンド**: `grep -r "from kernels" --include="*.py" src/ tests/ | grep -v "__pycache__" | cut -d: -f1 | sort -u`
- **出力**: 影響ファイル一覧をメモ
- **所要時間**: 3分

#### ステップ 26: `archive/kernels/` ディレクトリ作成
- **コマンド**: `mkdir -p archive/kernels`
- **所要時間**: 1分

#### ステップ 27: `kernels/` 全ファイルを `archive/kernels/` へ移動
- **コマンド**: `mv kernels/* archive/kernels/ && mv kernels/.* archive/kernels/ 2>/dev/null; rmdir kernels`
- **所要時間**: 2分

#### ステップ 28: 影響ファイルの import パスを `archive.kernels` に一括置換
- **対象**: ステップ25で特定したファイル
- **ツール**: `sed -i 's/from kernels/from archive.kernels/g' <file>` 等
- **所要時間**: 15分

#### ステップ 29: 移動後のテスト実行（stateテスト等）
- **コマンド**: `python -m pytest tests/state/ -v`
- **期待**: パス（import パス修正済みなら）
- **所要時間**: 5分

#### ステップ 30: 全テスト実行・確認
- **コマンド**: `python -m pytest tests/ -v --tb=short -x` （最初の失敗で止まる）
- **所要時間**: 2分

---

### B-2: `src/backend/database/repositories/` を `src/infrastructure/repository/` に統合（ステップ 31〜38）

#### ステップ 31: 現状の二重構造を確認
- **コマンド**: `ls -la src/backend/database/repositories/ && ls -la src/backend/database/repo_*.py`
- **所要時間**: 2分

#### ステップ 32: `src/infrastructure/repository/` ディレクトリ作成
- **コマンド**: `mkdir -p src/infrastructure/repository`
- **所要時間**: 1分

#### ステップ 33: `src/backend/database/repositories/` 全ファイルを `src/infrastructure/repository/` にコピー
- **コマンド**: `cp -r src/backend/database/repositories/* src/infrastructure/repository/`
- **所要時間**: 2分

#### ステップ 34: `src/backend/database/repo_*.py` の内容を `src/infrastructure/repository/` 対応ファイルにマージ・統合
- **対象ペア例**:
  - `repo_character.py` → `character.py`
  - `repo_book.py` → `book.py`
  - `repo_plot.py` → `plot.py`
  - `repo_chapter.py` → `chapter.py`
  - `repo_bible.py` → `bible.py`
  - `repo_misc.py` → `misc.py`
  - `repo_branch.py` → `branch.py`
  - `repo_rules.py` → `rules.py`
- **方針**: `repositories/` 版を正とし、`repo_*.py` 独自のロジックがあれば移植
- **所要時間**: 30分

#### ステップ 35: `src/backend/database/__init__.py` で `infrastructure.repository` を再エクスポート
- **ファイル**: `src/backend/database/__init__.py`
- **追加**: `from src.infrastructure.repository import *` （後方互換性維持）
- **所要時間**: 5分

#### ステップ 36: 全ソースコードの import パスを `src.infrastructure.repository` に一括置換
- **コマンド**: `grep -rl "from src.backend.database.repositories" src/ | xargs sed -i 's/from src.backend.database.repositories/from src.infrastructure.repository/g'`
- **同様に**: `src.backend.database.repo_` → `src.infrastructure.repository` も置換
- **所要時間**: 10分

#### ステップ 37: テストコードの import パスも同様に置換
- **コマンド**: `grep -rl "from src.backend.database.repositories" tests/ | xargs sed -i 's/from src.backend.database.repositories/from src.infrastructure.repository/g'`
- **所要時間**: 5分

#### ステップ 38: 全テスト実行・確認
- **コマンド**: `python -m pytest tests/ -v --tb=short -x`
- **期待**: 全パス
- **所要時間**: 2分

---

### B-3: `src/core/plugin_loader.py` 重複解消（ステップ 39〜42）

#### ステップ 39: 重複箇所の特定
- **コマンド**: `grep -r "PluginLoader" --include="*.py" src/ | grep -v "__pycache__"`
- **確認**: 他に同等機能を持つローダーが存在するか（`src/core/container.py` 等）
- **所要時間**: 3分

#### ステップ 40: 使用側の import を統一
- **現状**: `src.core.plugin_loader.PluginLoader` を使用している箇所を特定
- **変更**: 正規のローダー（例: `src.core.container.PluginLoader` 等）に import 変更
- **所要時間**: 10分

#### ステップ 41: `src/core/plugin_loader.py` を `archive/` に移動
- **コマンド**: `mkdir -p archive/core && mv src/core/plugin_loader.py archive/core/`
- **所要時間**: 2分

#### ステップ 42: 全テスト実行・確認
- **コマンド**: `python -m pytest tests/ -v --tb=short -x`
- **期待**: 全パス
- **所要時間**: 2分

---

### B-4: `src/backend/engine_utils.py` の未使用関数削除・整理（ステップ 43〜46）

#### ステップ 43: `engine_utils.py` の使用箇所検索
- **コマンド**: `grep -r "from src.backend.engine_utils" --include="*.py" src/ tests/ | grep -v "__pycache__"`
- **所要時間**: 2分

#### ステップ 44: 未使用関数の特定・削除
- **対象候補**: `compute_ngram_similarity`, `compute_cosine_similarity`, `is_light_style`, `safe_model_validate`, `verify_character_tone`, `AdaptiveCooldown`, `safe_get`, `extract_markdown_content` 等
- **方針**: インポートされていない関数を削除、使用されているもののみ残す
- **所要時間**: 15分

#### ステップ 45: 残った関数が適切な場所（`src/core/utils.py` 等）にあるか確認・移動
- **アクション**: 重複機能が `src/core/` にあれば統合
- **所要時間**: 10分

#### ステップ 46: 全テスト実行・確認
- **コマンド**: `python -m pytest tests/ -v --tb=short -x`
- **期待**: 全パス
- **所要時間**: 2分

---

### B-5: 最終検証・クリーンアップ（ステップ 47〜48）

#### ステップ 47: 全テストスイート実行・カバレッジ確認
- **コマンド**: `python -m pytest tests/ --tb=short -q`
- **確認**: 
  - 失敗0
  - エラー0（Collection Errorなし）
  - 警告のみ許容
- **所要時間**: 1分

#### ステップ 48: 型チェック・Lint 実行・修正
- **コマンド**: 
  - `mypy --config-file pyproject.toml src/ streamlit_app/`
  - `ruff check src/ streamlit_app/ tests/`
- **修正**: エラーがあれば最小限修正
- **所要時間**: 10分

---

## 実行順序の推奨

```
Phase 1 (最優先):  Step 1-10  (stateテスト修正)      → 約40分
Phase 2 (優先):    Step 11-17 (integrationテスト修正)  → 約60分
Phase 3 (優先):    Step 18-24 (async_uiテスト修正)    → 約20分
Phase 4 (重要):    Step 25-30 (kernels移動)           → 約30分
Phase 5 (重要):    Step 31-38 (リポジトリ統合)        → 約60分
Phase 6 (重要):    Step 39-42 (plugin_loader削除)     → 約20分
Phase 7 (整理):    Step 43-46 (engine_utils整理)      → 約30分
Phase 8 (最終):    Step 47-48 (全体検証)             → 約15分
```

**総所要時間目安: 約4.5時間**（実装熟練度により変動）

---

## 低性能LLM向け実装のコツ

1. **1ステップ1ファイル・1変更** の原則を徹底
2. 各ステップ完了後に `pytest` 実行で即座に確認
3. エラーが出たらそのステップ内で完結させ、次に進まない
4. `grep` で影響範囲を必ず事前確認してから編集
4. 置換は `sed` 等の一括ツールを使わず、ファイルごと手動確認しながら実施

---

## 完了定義 (Definition of Done)

- [ ] `pytest tests/state/` - 10 passed, 0 failed
- [ ] `pytest tests/integration/` - Collection Error 0, テスト実行可能
- [ ] `pytest tests/unit/test_async_ui_sync.py` - 2 passed, 0 failed
- [ ] `kernels/` ディレクトリが存在しない（`archive/kernels/` に移動済み）
- [ ] `src/backend/database/repositories/` が `src/infrastructure/repository/` に統合済み
- [ ] `src/core/plugin_loader.py` が `archive/core/` に移動済み
- [ ] `src/backend/engine_utils.py` が必要最小限のみ残存
- [ ] `mypy` エラー増加なし
- [ ] `ruff` エラー増加なし