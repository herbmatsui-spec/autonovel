# 未実装部分 実装計画書 Ver4.0

## 概要

本計画は、以下の未実装タスクを72の小さなステップに分割して実装するためのものである。

- **Phase C (Step 55-72)**: 統合テスト実行 + UML/User Story検証
- **総ステップ数**: 18ステップ（Step 55-72）

**前提**:
- 以前的优势已实现34个单元测试通过
- Phase A (fixtures) と Phase B (lint fixes) 已完成
- 現在の環境问题是 Python import ハングアップ

---

## Phase C: 統合テスト実行（Step 55-63）

### Step 55: 環境問題切り分け - Python interpreter 確認

- タスク: Python が正常に動作するか確認
- コマンド: `python --version`
- 期待: `Python 3.14.0` 等正常表示
- 検証: バージョン情報が表示される

### Step 56: pytest 单独起動確認

- タスク: pytest だけが起動するか確認
- コマンド: `python -m pytest --version`
- 期待: `pytest 9.0.3` 等正常表示
- 検証: pytestバージョン情報が表示される

### Step 57: pytest collection 单独確認

- タスク: pytest collection だけが動作するか確認
- コマンド: `python -m pytest tests/integration/test_workflow.py --collect-only`
- 期待: `3 tests collected` 等、collection のみ完了
- 検証: テスト数が表示される

### Step 58: collection ハング原因的調査（切り分け）

- タスク: 原因が conftest.py の import か test_workflow.py の import か切り分け
- 方法: tests/integration/ だけに移動して再試行
- コマンド: `cd tests/integration && python -m pytest test_workflow.py --collect-only`
- 期待: collection が動作すれば integration/ の import が原因
- 検証: 原因を特定

### Step 59: conftest.py の読み込み確認

- タスク: tests/conftest.py だけを読み込んで error が出ないか確認
- 方法: tests/conftest.py のみでminimal test実行
- 期待: error が出ない
- 検証: 結果を確認

### Step 60: real_db_manager fixture の实际的動作確認

- タスク: `get_db_manager()` の実際の返回値を調査
- 方法: Python script内で直接実行
- 追加コード:
  ```python
  from src.backend.database.core import get_db_manager
  db = get_db_manager()
  print(f"db type: {type(db)}")
  print(f"db: {db}")
  ```
- 期待: DatabaseManager instance が返る
- 検証: 型と值为確認

### Step 61: mock_llm fixture の动作确认

- タスク: Mock object が正しく作成されるか確認
- 方法: Python script内で直接実行
- 追加コード:
  ```python
  from unittest.mock import Mock
  mock = Mock()
  mock.add_json_response = Mock()
  mock.add_text_response = Mock()
  mock.add_exception = Mock()
  print(f"mock type: {type(mock)}")
  ```
- 期待: Mock object が正常に作成される
- 検証: 型と值为確認

### Step 62: 1つだけの統合テスト选定

- タスク: test_workflow.py から1つだけのテストを選んで隔离実行
- 対象: `test_full_auto_workflow_easy_mode`
- 方法: `@pytest.mark.skip` で他のテストをスキップ
- コマンド: `pytest tests/integration/test_workflow.py::test_full_auto_workflow_easy_mode -v`
- 期待: テストが実行される（pass/fail は別として）
- 検証: エラーが fixture error から别的エラーに变化

### Step 63: fixture error の实际的解决

- タスク: Step 62 のエラー内容に応じて fixture を修正
- 期待エラー: `real_db_manager` か `mock_llm` が見つからない
- 修正方法:
  - `real_db_manager`: DatabaseManager instance を直接作成
  - `mock_llm`: Mock method を正しく設定
- 検証: fixture error が解消

### Step 64: test_full_auto_workflow_easy_mode の完全的通線

- タスク: test_full_auto_workflow_easy_mode が PASS する状态に修正
- 対象エラー:
  - Mock 設定不備
  - Assertion エラー
  - 实际的ロジックエラー
- 修正: エラーに応じた適切な対応
- 検証: `PASSED` が表示される

### Step 65: test_full_auto_workflow_normal_mode の通線確認

- タスク: test_full_auto_workflow_normal_mode が PASS する状态に修正
- 方法: Step 64 と同じ対応
- 期待: `PASSED` が表示される
- 検証: エラーが解消

### Step 66: test_full_auto_workflow_api_failure の通線確認

- タスク: test_full_auto_workflow_api_failure が PASS する状态に修正
- 方法: Step 64 と同じ対応
- 期待: `PASSED` が表示される
- 検証: エラーが解消

### Step 67: 全統合テスト同时実行

- タスク: tests/integration/test_workflow.py 全体を1コマンドで実行
- コマンド: `pytest tests/integration/test_workflow.py -v`
- 期待: `3 passed`
- 検証: 3/3 PASSED が表示される

---

## Phase D: UML/User Story 検証（Step 68-72）

### Step 68: プロジェクト構造の全体確認

- タスク: プロジェクトのディレクトリ構造を確認
- 対象:
  ```
  docs/
  planning/
  *.md
  ```
- 期待: 企画・要件関連ファイルが見つかる
- 検証: ファイル一覧

### Step 69: 見出されたファイルの確認

- タスク: Step 68で見つかったファイルの内容を確認
- 対象ファイル:
  - `docs/` 内のmarkdown
  - `planning/` 内のファイル
  - README.md 等
- 期待: User Story、要件定義、企画書等が見つかる
- 検証: ファイル内容を軽く確認

### Step 70: 実装要件との突き合わせ（一覧）

- タスク: Step 69で見つかった要件と現在の実装を一覧にまとめる
- 比較項目:
  - [ ] key_phrase による角検出
  - [ ] 大文字小文字無視一致
  - [ ] 空白正規化
  - [ ] N-gram フォールバック
  - [ ] DI コンテナ統合
  - [ ] SemanticEdgePreserver
  - [ ] DeAIAuditor 統合
  - [ ] CritiqueAgent 統合
- 期待: 各項目の実装状況が明確になる
- 検証: 比較表を作成

### Step 71: 不足機能の特定と対応方針

- タスク: Step 70で不足が見つかった場合に何をすべきか決定
- 方針:
  - 優先度高: 即座に実装
  - 優先度中: 別途タスクとして管理
  - 優先度低: 後で対応
- 期待: 不足機能への対応方針が明确
- 検証: 対応方針文書

### Step 72: 最終的全テストスイート実行

- タスク: 全テスト（ユニット + 統合）を実行して完了確認
- コマンド:
  ```bash
  pytest tests/test_sharp_edge.py tests/test_sharp_edge_preserver.py tests/test_engine_sharp_edge_proposal.py -v
  pytest tests/integration/test_workflow.py -v
  ```
- 期待:
  - ユニット: 34 passed
  - 統合: 3 passed
- 検証: 全テスト PASSED

---

## 付録: テストコマンド一覧

```bash
# individual test
python -m pytest tests/integration/test_workflow.py::test_full_auto_workflow_easy_mode -v

# all integration tests
python -m pytest tests/integration/test_workflow.py -v

# unit tests (sharp edge related)
python -m pytest tests/test_sharp_edge.py tests/test_sharp_edge_preserver.py tests/test_engine_sharp_edge_proposal.py -v
```

## 付録: 環境問題対処フロー

```
Python コマンドがハング →
  ↓
Step 55: python --version が反応するか確認
  ↓ しない場合
Python 自体が問題 → PC 再起動後再試行
  ↓ する場合
Step 56: pytest --version が反応するか確認
  ↓ しない場合
pytest 自体が問題 → pip reinstall pytest
  ↓ する場合
Step 57: pytest --collect-only でcollection を確認
  ↓ collection だけが動作する場合
Step 58-61: import の原因を突き止める
  ↓
Step 62-67: fixture とテスト本体を修正
```

## 付録: fixture 問題早見表

| 問題 | 原因 | 対処 |
|-----|------|------|
| `real_db_manager not found` | fixture 未定義 | conftest.py に追加 |
| `real_db_manager not callable` | Vial instance を返していない | DatabaseManager instance を直接生成 |
| `mock_llm not found` | fixture 未定義 | conftest.py に追加 |
| `mock_llm.add_json_response not callable` | Mock method 未設定 | Mock().add_json_response = Mock() を追加 |
| import hang | conftest.py の import が重い | import を遅延化（fixture 内に移動）|

## 変更履歴

- Ver 1.0: 初期72ステップ計画（全体）
- Ver 2.0: Phase A-B (fixtures + lint)
- Ver 3.0: Phase A-D 全体72ステップ
- Ver 4.0: 未実装部分のみ18ステップ（Step 55-72）に焦点を当てた計画