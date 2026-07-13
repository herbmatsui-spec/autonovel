# 統合テスト・Lint修正 実装計画書 Ver3.0

## 概要

本計画は、以下の2つの優先度高タスクを72の小さなステップに分割して実装するためのものである。

- **即時対応**: `real_db_manager` fixture追加 + 統合テスト再実行
- **短期対応**: lintエラー(F821, E701)修正 + UML(User Story)差分確認

**前提**: 低性能なLLMでも実装できるように、各ステップは独立して検証可能で、1ステップあたりの変更を最小限に抑える。

---

## 前提知識

### 現在のテスト結果

```
ユニットテスト: 34/34 PASSED ✅
統合テスト: 3 ERROR (real_db_manager fixture不足)
```

### 失敗しているテスト

```
tests/integration/test_workflow.py
  - test_full_auto_workflow_easy_mode        ERROR (fixture not found)
  - test_full_auto_workflow_normal_mode      ERROR (fixture not found)
  - test_full_auto_workflow_api_failure      ERROR (fixture not found)
```

### 残存lintエラー

| ファイル | 行 | エラー | 内容 |
|---------|-----|-------|------|
| engine_plot.py | 189 | F821 | Undefined name `EntertainmentCheckResult` |
| engine_utils.py | 107,112,118 | E701 | Multiple statements on one line |
| engine_utils.py | 148 | E402 | Module level import not at top of file |

---

## フェーズA: 統合テスト infrastructure（Step 1-36）

### Step 1: 現在のテストディレクトリ構造を確認する

- タスク: `tests/` ディレクトリ以下のファイル一覧を取得
- 確認コマンド: `ls tests/`
- 期待: `test_workflow.py`, `conftest.py`, `integration/` ディレクトリが存在
- 検証: ファイル一覧を表示して確認

### Step 2: 既存の `conftest.py` の存在を確認する

- タスク: `tests/conftest.py` が存在するかをチェック
- ファイルパス: `tests/conftest.py`
- 検証: ファイルが存在しない場合は Step 3へ、存在する場合は Step 10 へ

### Step 3: `tests/conftest.py` を作成する（空ファイル）

- タスク: `tests/conftest.py` を新規作成
- 内容:
  ```python
  """
  tests/conftest.py
  pytest設定・shared fixtures
  """
  ```
- 検証: ファイルが作成される

### Step 4: `pytest` と `fixtures` についてのコメントを追加する

- タスク: `conftest.py` にdocstringとimportを追加
- 内容:
  ```python
  """
  tests/conftest.py
  pytest設定・shared fixtures
  """
  import pytest
  ```
- 検証: `python -c "import tests.conftest"` でエラーが出ない

### Step 5: `AppContainer` のimportを追加する

- タスク: `conftest.py` に AppContainer import を追加
- 内容:
  ```python
  from src.core.container import AppContainer
  ```
- 検証: `python -c "from src.core.container import AppContainer"` が成功

### Step 6: `real_db_manager` fixtureの骨架を作成する

- タスク: `conftest.py` に fixture skeleton を追加
- 内容:
  ```python
  @pytest.fixture
  def real_db_manager():
      """統合テスト用のデータベースマネージャー"""
      pass  # TODO: 実装
  ```
- 検証: `pytest --fixtures tests/` で `real_db_manager` が表示される

### Step 7: `AppContainer.db` への参照を追加する

- タスク: `real_db_manager` fixture に AppContainer.db を返す実装
- 内容:
  ```python
  @pytest.fixture
  def real_db_manager():
      """統合テスト用のデータベースマネージャー"""
      return AppContainer.db
  ```
- 検証: fixture が AppContainer.db を返すことを確認

### Step 8: `real_db_manager` fixture のdocstringを完善

- タスク: docstring を詳細に記述
- 内容:
  ```python
  @pytest.fixture
  def real_db_manager():
      """
      統合テスト用のデータベースマネージャー
      
      AppContainerからdb instanceを取得して返す。
      実際のデータベース接続を使用するため、テスト後は必ずクリーンアップすること。
      """
      return AppContainer.db
  ```
- 検証: `pytest --fixtures tests/` でdocstringが表示される

### Step 9: `integration/` ディレクトリ内の `conftest.py` を確認

- タスク: `tests/integration/conftest.py` が存在するかをチェック
- ファイルパス: `tests/integration/conftest.py`
- 検証: ファイルが存在しない場合は Step 10、存在する場合は Step 15 へ

### Step 10: `tests/integration/` 用に `conftest.py` を作成

- タスク: `tests/integration/conftest.py` を新規作成
- 内容:
  ```python
  """
  tests/integration/conftest.py
  統合テスト用のpytest設定・fixtures
  """
  import pytest
  ```
- 検証: ファイルが作成される

### Step 11: `integration/conftest.py` に親プロジェクトのimportを追加

- タスク: `src/` 以下のモジュールをimport可能にする
- 内容:
  ```python
  import sys
  from pathlib import Path
  
  # src/ をsys.pathに追加
  src_path = Path(__file__).parent.parent.parent / "src"
  if str(src_path) not in sys.path:
      sys.path.insert(0, str(src_path))
  ```
- 検証: `python -c "from src.core.container import AppContainer"` が成功

### Step 12: `integration/conftest.py` に `real_db_manager` fixtureを追加

- タスク: `tests/integration/conftest.py` に fixture を追加
- 内容:
  ```python
  @pytest.fixture
  def real_db_manager():
      """統合テスト用のデータベースマネージャー"""
      from src.core.container import AppContainer
      return AppContainer.db
  ```
- 検証: `pytest --fixtures tests/integration/` で `real_db_manager` が表示される

### Step 13: `mock_llm` fixtureの骨架を作成

- タスク: `mock_llm` fixture skeleton を追加
- 内容:
  ```python
  @pytest.fixture
  def mock_llm():
      """LLM応答のモック"""
      pass  # TODO: 実装
  ```
- 検証: `pytest --fixtures tests/` で `mock_llm` が表示される

### Step 14: `mock_llm` fixtureにMockオブジェクトを返すように実装

- タスク: `unittest.mock.Mock` を使った実装
- 内容:
  ```python
  from unittest.mock import Mock
  
  @pytest.fixture
  def mock_llm():
      """LLM応答のモック"""
      mock = Mock()
      return mock
  ```
- 検証: fixtureがMockオブジェクトを返すことを確認

### Step 15: `test_workflow.py` の先頭を確認

- タスク: `tests/integration/test_workflow.py` のimportとfixture参照を確認
- ファイルパス: `tests/integration/test_workflow.py`
- 期待: `real_db_manager`, `mock_llm` がパラメータとして参照されている
- 検証: ファイルを読んでfixture参照を確認

### Step 16: `test_workflow.py` の fixture 依存関係を追跡

- タスク: `real_db_manager` と `mock_llm` が 어떻게 사용되는지分析
- 期待:
  ```python
  async def test_full_auto_workflow_easy_mode(real_db_manager, mock_llm):
  ```
- 検証: テスト関数シグネチャを確認

### Step 17: `test_workflow.py` に `AppContainer` override処理を追加

- タスク: `test_full_auto_workflow_easy_mode` にoverride処理があるか確認
- 内容確認: `AppContainer.llm.override(...)` の呼び出し
- 検証: override処理が存在することを確認（なければ追加）

### Step 18: `test_workflow.py` の `real_db_manager` 使用箇所を確認

- タスク: `test_full_auto_workflow_easy_mode` 内の `real_db_manager` 使用を確認
- 期待: `AppContainer.db.override(real_db_manager)` または同様の処理
- 検証: 使用箇所を特定

### Step 19: `AppContainer.repo` と `AppContainer.uow` のoverrideを確認

- タスク: `test_workflow.py` 内の `AppContainer.repo.reset_override()` 呼び出しを確認
- 期待: `repo` と `uow` のoverride解除処理がある
- 検証: 処理が存在することを確認

### Step 20: `test_workflow.py` の `DummyReporter` を確認

- タスク: `DummyReporter` クラスが定義されているか確認
- 期待: テストファイル下部に `class DummyReporter` が定義されている
- 検証: クラス定義を探す

### Step 21: `DummyReporter` の実装を確認する

- タスク: `DummyReporter` のメソッド一覧を確認
- 期待: `reporter` オブジェクトが必要とするメソッドが空実装されている
- 検証: メソッド一覧を確認

### Step 22: `test_full_auto_workflow_easy_mode` を1つ選んで実行

- タスク: 修正した fixture を使って1つのテストを実行
- コマンド: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_easy_mode -v`
- 期待: fixture error が解消し、テストが実行される（成功または別のエラー）
- 検証: エラーが fixture not found から別のものに変わったか確認

### Step 23: テスト実行結果のエラーを分析

- タスク: Step 22 のエラー内容を確認
- 期待: fixture error → 実際のテストロジックエラー に変化
- 検証: エラーの種類を特定

### Step 24: もし `AttributeError` が出たら `AppContainer.db` を調査

- タスク: `AppContainer.db` が実際に存在するか確認
- 確認コマンド: `python -c "from src.core.container import AppContainer; print(AppContainer.db)"`
- 検証: `AppContainer.db` が Vial instance を返すことを確認

### Step 25: `AppContainer` の DI register 構造を確認

- タスク: `src/core/container.py` 内の db 登録を確認
- 期待: `AppContainer.db` が Vial instance として登録されている
- 検証: `container.py` のregister処理を確認

### Step 26: `real_db_manager` が返すオブジェクトの型を確認

- タスク: fixture が返すオブジェクトの型をprintして確認
- 追加コード:
  ```python
  @pytest.fixture
  def real_db_manager():
      from src.core.container import AppContainer
      db = AppContainer.db
      print(f"db type: {type(db)}")
      return db
  ```
- 検証: 型情報が表示される

### Step 27: `AppContainer.db` が Vial instance でない場合の対処

- タスク: Vial instance を作成する方法を調査
- 期待: Vial instance が必要
- 代替案: `container.get_database_manager()` 等のメソッドを使用

### Step 28: Vial instance の作成方法を調査

- タスク: `container.py` に Vial instance 作成メソッドがあるか確認
- 期待: `create_db()`, `get_database_manager()` 等のメソッド
- 検証: メソッドを探す

### Step 29:  Vial instance を直接作成して返す実装

- タスク: `real_db_manager` fixture を修正
- 内容:
  ```python
  @pytest.fixture
  def real_db_manager():
      """統合テスト用のデータベースマネージャー"""
      from src.core.container import AppContainer
      # Vial instanceを直接作成
      from src.core.db import DatabaseManager
      db = DatabaseManager()
      return db
  ```
- 検証: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_easy_mode` を実行

### Step 30: もし `DatabaseManager` import 失敗したら `src.core.db` を確認

- タスク: `src/core/db.py` または同等のファイルが存在するか確認
- 確認コマンド: `ls src/core/` で db 関連ファイルを探す
- 検証: ファイルが存在することを確認

### Step 31: `src/core/db.py` の `DatabaseManager` クラスを確認

- タスク: `DatabaseManager` クラスの signature を確認
- 期待: `__init__` で database connection を受け取る
- 検証: クラス定義を確認

### Step 32: `real_db_manager` fixture を `DatabaseManager` を使用するよう修正

- タスク: fixture を修正
- 内容:
  ```python
  @pytest.fixture
  def real_db_manager():
      """統合テスト用のデータベースマネージャー"""
      from src.core.db import DatabaseManager
      from src.repositories.repo import (
          BookRepository, PlotRepository, CharacterRepository
      )
      db = DatabaseManager()
      return db
  ```
- 検証: テストを実行して確認

### Step 33: Repository instances の確認

- タスク: `src/repositories/repo.py` 内の Repository クラス達を確認
- 期待: `BookRepository`, `PlotRepository`, `CharacterRepository` が存在
- 検証: ファイルを読んで確認

### Step 34: Repository instances を `real_db_manager` に渡すよう修正

- タスク: Repository instances を作成して返す fixture に修正
- 内容:
  ```python
  @pytest.fixture
  def real_db_manager():
      """統合テスト用のデータベースマネージャー"""
      from src.core.db import DatabaseManager
      from src.repositories.repo import (
          BookRepository, PlotRepository, CharacterRepository
      )
      db = DatabaseManager(
          book_repo=BookRepository(),
          plot_repo=PlotRepository(),
          character_repo=CharacterRepository()
      )
      return db
  ```
- 検証: テストを実行して確認

### Step 35: `test_full_auto_workflow_normal_mode` を実行

- タスク: 2つ目のテストを実行
- コマンド: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_normal_mode -v`
- 検証: テストが実行される（成功または別のエラー）

### Step 36: `test_full_auto_workflow_api_failure` を実行

- タスク: 3つ目のテストを実行
- コマンド: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_api_failure -v`
- 検証: テストが実行される（成功または別のエラー）

---

## フェーズB: Lintエラー修正（Step 37-54）

### Step 37: engine_plot.py の F821 エラーを確認

- タスク: `src/backend/engine_plot.py:189` のエラー内容を確認
- コマンド: `python -m ruff check src/backend/engine_plot.py --output-format concise`
- 期待: `F821 Undefined name 'EntertainmentCheckResult'`
- 検証: エラーが表示されること

### Step 38: `EntertainmentCheckResult` の定義場所を調査

- タスク: プロジェクト内で `EntertainmentCheckResult` を検索
- 検索コマンド: `grep -r "class EntertainmentCheckResult" src/`
- 期待: 定義場所が見つかる（例: `src/backend/entertainment_loop.py`）
- 検証: 定義ファイルの-path と行番号を特定

### Step 39: engine_plot.py に import を追加

- タスク: `EntertainmentCheckResult` を import
- 追加場所: `src/backend/engine_plot.py` の import 部
- 内容:
  ```python
  from src.backend.entertainment_loop import EntertainmentCheckResult
  ```
- 検証: `python -m ruff check src/backend/engine_plot.py --output-format concise` で F821 が消える

### Step 40: import の循環参照がないか確認

- タスク: `python -c "from src.backend.engine_plot import *"` を実行
- 期待: import が成功（F821 は解決済み）
- 検証: エラーが出ないことを確認

### Step 41: engine_utils.py の E701 エラーを確認

- タスク: `src/backend/engine_utils.py:107,112,118` のエラー内容を確認
- コマンド: `python -m ruff check src/backend/engine_utils.py --select E701 --output-format concise`
- 期待: `E701 Multiple statements on one line`
- 検証: エラーが表示されること

### Step 42: engine_utils.py:107 のコードを確認

- タスク: 107行目の multiple statements を確認
- 期待: `if condition: statement` の1行スタイル
- 検証: コードを読んで確認

### Step 43: engine_utils.py:107 を複数行に修正

- タスク: 1行if文を複数行に展開
- 修正前: `if condition: statement`
- 修正後:
  ```python
  if condition:
      statement
  ```
- 検証: `python -m ruff check src/backend/engine_utils.py --select E701 --output-format concise` で107行のエラーが消える

### Step 44: engine_utils.py:112 を修正

- タスク: 112行の multiple statements を修正
- 修正前: `if condition: statement`
- 修正後: 複数行形式
- 検証: 112行のエラーが消える

### Step 45: engine_utils.py:118 を修正

- タスク: 118行の multiple statements を修正
- 修正前: `if condition: statement`
- 修正後: 複数行形式
- 検証: 118行のエラーが消える

### Step 46: engine_utils.py:148 の E402 エラーを確認

- タスク: `src/backend/engine_utils.py:148` のエラー内容を確認
- コマンド: `python -m ruff check src/backend/engine_utils.py --select E402 --output-format concise`
- 期待: `E402 Module level import not at top of file`
- 検証: エラーが表示されること

### Step 47: engine_utils.py:148 のコードを調査

- タスク: 148行目の import 文を確認
- 期待: 関数の内部にある import（条件付きimport等）
- 検証: コードを読んで確認

### Step 48: 148行の import をトップレベルに移動できるかを検討

- タスク: import が本当に条件付きかを確認
- 期待: `if` ブロック内有りのimport
- 検証: import 文の前後を確認

### Step 49: 条件付きimportをトップレベルに移動

- タスク: import をファイルの先頭（他のimportと同じ位置）に移動
- 注意: 移動先で循環参照が発生しないか注意
- 検証: `python -c "from src.backend.engine_utils import *"` が成功

### Step 50: E402 エラーが解消されたことを確認

- タスク: `python -m ruff check src/backend/engine_utils.py --select E402 --output-format concise`
- 期待: エラーがでない
- 検証: 出力がないことを確認

### Step 51: 全体の lint チェック（全ファイル）

- タスク: 全ファイルに対して lint チェックを実行
- コマンド: `python -m ruff check src/ --output-format concise`
- 期待: 本件関連ファイルの F821, E701, E402 がすべて解消
- 検証: 出力がないことを確認

### Step 52: lint fix 後のコードレビュー（engine_plot.py）

- タスク: `EntertainmentCheckResult` import が正しく追加されたか確認
- 期待: import 文が Top-level に存在
- 検証: ファイルを読んで確認

### Step 53: lint fix 後のコードレビュー（engine_utils.py）

- タスク: E701, E402 修正が正しく適用されたか確認
- 期待: 1行ifが複数行に展開され、importがトップレベルに
- 検証: ファイルを読んで確認

### Step 54: lint 再実行（全ファイル）

- タスク: 最終 lint チェック
- コマンド: `python -m ruff check src/backend/sharp_edge_preserver.py src/backend/engine_plot.py src/backend/engine_utils.py src/agents/audit.py src/core/container.py prompts/plotting.py --output-format concise`
- 期待: 本件関連のエラーがすべて解消
- 検証: 出力がないことを確認

---

## フェーズC: 統合テスト再実行（Step 55-63）

### Step 55: 統合テスト全体の実行（全3テスト）

- タスク: `test_workflow.py` の全テストを実行
- コマンド: `pytest tests/integration/test_workflow.py -v --tb=short`
- 期待: 3テスト 모두実行される（PASS/FAIL は別として fixture error は解消）
- 検証: ERROR が PASS/FAIL に変化

### Step 56: テスト結果の分析（PASS/FAIL判定）

- タスク: テスト結果を確認
- 期待: PASSED / FAILED のいずれか（ERRORではない）
- 検証: 結果サマリーを確認

### Step 57: もし FAILED が出たら原因を調査

- タスク: FAILED の原因を特定
- 確認項目:
  - Mock の設定不備
  - Assertion エラー
  - 実際のロジックエラー
- 検証: 失敗原因を記録

### Step 58: Mock設定の修正（必要に応じて）

- タスク: `mock_llm` fixture に詳細な Mock 設定を追加
- 内容:
  ```python
  from unittest.mock import Mock, AsyncMock
  
  @pytest.fixture
  def mock_llm():
      """LLM応答のモック"""
      mock = Mock()
      mock.add_json_response = Mock()
      mock.add_text_response = Mock()
      mock.add_exception = Mock()
      return mock
  ```
- 検証: テストを再実行

### Step 59: テスト別のMock response設定を確認

- タスク: 各テストが使用する mock response の設定方法を確認
- 期待: `mock_llm.add_json_response()` 等が正しく呼ばれている
- 検証: テストコードを読んで確認

### Step 60: `test_full_auto_workflow_easy_mode` を再度実行

- タスク: 修正後の一番目のテストを再実行
- コマンド: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_easy_mode -v`
- 検証: PASSED を確認

### Step 61: `test_full_auto_workflow_normal_mode` を再度実行

- タスク: 2番目のテストを再実行
- コマンド: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_normal_mode -v`
- 検証: PASSED を確認

### Step 62: `test_full_auto_workflow_api_failure` を再度実行

- タスク: 3番目のテストを再実行
- コマンド: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_api_failure -v`
- 検証: PASSED を確認

### Step 63: 全統合テストの同時実行

- タスク: 全3テストを同時に実行
- コマンド: `pytest tests/integration/test_workflow.py -v`
- 期待: 3/3 PASSED
- 検証: 結果サマリーで全PASSを確認

---

## フェーズD: UML/User Story差分確認（Step 64-72）

### Step 64: UML(User Story Map)ファイルの場所を確認

- タスク: プロジェクト内の User Story 関連ファイルを検索
- 検索対象: `docs/`, `planning/`, `*.md` (readme, planning 等)
- 期待: User Story や Planning ドキュメントが見つかる
- 検証: ファイル一覧を表示

### Step 65: 見つけたUML/Planningドキュメントを読む

- タスク: Step 64で見つけたドキュメントの内容を確認
- 期待: 品質管理・角保全に関する要件が記載されている
- 検証: 主要な要件をメモ

### Step 66: 現在の実装内容とUML要件の突き合わせ

- タスク: Step 65で抽出した要件と実装を比較
- 比較項目:
  - [ ] key_phrase による角検出
  - [ ] 大文字小文字無視の一致
  - [ ] 空白正規化
  - [ ] N-gram フォールバック
  - [ ] DI コンテナ統合
- 検証: 各要件の実装状況をメモ

### Step 67: 不足している機能があればメモ

- タスク: Step 66で見つけた不足機能を文書化
- 期待: 不足機能リスト
- 検証: メモを保存

### Step 68: 不足機能の実装優先度付け

- タスク: 不足機能を priority に分類
- Priority 高: セキュリティ・主要機能
- Priority 中: 便利な機能・改善
- Priority 低: オプション機能
- 検証: 優先度リストを作成

### Step 69: 実装済み機能でUML要件との不一致を確認

- タスク: 実装済みだがUML要件とずれている点を調査
- 期待: もし不一致があれば記録
- 検証: 不一致リストを作成

### Step 70: 不一致の修正方針を決定

- タスク: 不一致の修正方法を選択
- 方針A: UML側を修正（要件変更）
- 方針B: 実装を修正（バグ対応）
- 検証: 方針を選択

### Step 71: 最終的な差分レポートを作成

- タスク: UML vs 実装 の差分レポートを文書化
- 内容:
  - 実装済みで要件満たしている項目
  - 実装済みで要件と不一致の項目
  - 不足している機能
- 検証: レポートを保存

### Step 72: 全体の最終テスト実行

- タスク: 全テスト（ユニット + 統合）を実行
- コマンド: `pytest tests/ -v --tb=short`
- 期待: 全テスト PASSED（または既知のFAILのみ）
- 検証: 最終結果サマリーを表示

---

## 付録: ファイル別担当表

| ファイル | 担当Step |
|---------|---------|
| tests/conftest.py | 1-9 |
| tests/integration/conftest.py | 10-14 |
| tests/integration/test_workflow.py | 15-36, 55-63 |
| src/backend/engine_plot.py | 37-40, 52 |
| src/backend/engine_utils.py | 41-53 |
| docs/planning/ (UML関連) | 64-71 |

## 付録: テスト実行コマンド早見表

```bash
# ユニットテストのみ
pytest tests/test_sharp_edge.py tests/test_sharp_edge_preserver.py tests/test_engine_sharp_edge_proposal.py -v

# 統合テストのみ
pytest tests/integration/test_workflow.py -v

# 全テスト
pytest tests/ -v --tb=short

# Lint チェック
python -m ruff check src/ --output-format concise
```

## 付録: 既知の優先度高问题点

| # | 問題 | 影響 | 推奨対処 |
|---|-----|------|---------|
| 1 | `real_db_manager` fixture 未定義 | 統合テスト全滅 | conftest.py に追加 |
| 2 | `EntertainmentCheckResult` 未import | F821エラー | engine_plot.py に import追加 |
| 3 | E701 (1行if文) | コード品質 | 複数行に展開 |

## 付録: 計画遂行のヒント

1. **1日3〜5ステップ**: 72ステップ全てを1日で終わらせず、毎日数ステップずつ進める
2. **各ステップ後にテスト**: 失敗したらそのステップのやり直し
3. **低性能LLM向け**: 各ステップは1ファイル、少数の変更のみを原則とする
4. **依存関係を重視**: フェーズA→B→C→Dの順に進む（前のステップが完了してから次へ）
5. **テストは各フェーズ末**: フェーズ途中でテストせず、フェーズ完了時にまとめてテスト

---

## 変更履歴

- Ver 1.0: 初期版（72ステップ計画）
- Ver 2.0: 統合テスト・Lint修正向け72ステップに再構成
- Ver 3.0: フェーズA〜Dに分割、各ステップの詳細を追加