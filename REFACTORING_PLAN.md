# インポート統一・リファクタリング 実装計画書

## 背景と目的

現在のプロジェクトは `src/` と `streamlit_app/` の間に薄いラッパー層が存在し、インポート経路が複雑化しています。また `src/progress.run_in_background` がスタブであるためバックグラウンドタスクが動作していません。本計画書は48のステップでこれらを整理・修正します。

---

## フェーズ分割

| フェーズ | ステップ | 概要 |
|---------|---------|------|
| 第1フェーズ | 1-12 | 重複ファイル統合 |
| 第2フェーズ | 13-24 | ラッパー層・再エクスポート除去 |
| 第3フェーズ | 25-36 | バックエンドタスク機構修正 |
| 第4フェーズ | 37-44 | テストスタブのスコープ限定 |
| 第5フェーズ | 45-46 | ドキュメント整備 |
| 第6フェーズ | 47-48 | CI・統合テスト追加 |

---

## ステップ詳細

### 第1フェーズ: 重複ファイル統合（1-12）

#### ステップ1: workflow_types.py の統合
- **対象**: `src/workflow_types.py`, `streamlit_app/workflow_types.py`
- **判断基準**: `streamlit_app/workflow_types.py` には `WORKFLOW_API_MAP` など UI 所需的情報が含まれている
- **アクション**: `streamlit_app/workflow_types.py` を正とし、`src/workflow_types.py` を削除
- **検証**: `src/` からの参照先を確認 → `from src.workflow_types import WorkflowType` が他ファイルにあるか Grep

#### ステップ2: src/workflow_types.py の参照先調査
- **アクション**: Grep で `from src.workflow_types import` を検索し、参照ファイルをリスト化
- **結果**: 参照がない場合はステップ1を実施、参照がある場合はステップ3へ

#### ステップ3: 参照ファイルの修正
- **対象**: ステップ2で見つかった参照ファイル
- **アクション**: `from src.workflow_types import WorkflowType` → `from streamlit_app.workflow_types import WorkflowType` に変更
- **例**: `src/proxy.py`, `src/engine_service.py` などで使用されている可能性

#### ステップ4: async_helper.py の統合
- **対象**: `src/shared/utils/async_helper.py`, `streamlit_app/utils/async_helper.py`
- **判断基準**: ファイル内容が同一か確認（explorer報告では同一）
- **アクション**: `streamlit_app/utils/async_helper.py` を正とし、`src/shared/utils/async_helper.py` を削除
- **備考**: どちらを正とするかは `streamlit_app/` が UI 層の正当な場所のため streamlit_app 側を正とする

#### ステップ5: async_helper.py の src 側参照調査
- **アクション**: Grep で `from src.shared.utils.async_helper import` および `from src.utils.async_helper import` を検索
- **対象ファイル例**: `src/shared/utils/async_manager.py`

#### ステップ6: async_manager.py の統合
- **対象**: `src/shared/utils/async_manager.py`, `streamlit_app/utils/async_manager.py`
- **差異**: インポートパスの相違（`src` vs `streamlit_app`）
- **アクション**: `streamlit_app/utils/async_manager.py` を正とし、インポートを `from streamlit_app.utils.async_helper import run_async` に統一
- **備考**: 統合後の async_helper.py のパスに合わせる

#### ステップ7: async_manager.py の src 側参照調査と修正
- **アクション**: `from src.shared.utils.async_manager import` の参照先を調査
- **修正**: `from streamlit_app.utils.async_manager import` に変更

#### ステップ8: src/shared/utils/ ディレクトリ Cleanup
- **アクション**: async_helper.py, async_manager.py 削除後、`src/shared/utils/` が空になるか確認
- **空になった場合**: `src/shared/utils/` ディレクトリを削除
- **備考**: `__init__.py` も削除対象

#### ステップ9: ui_tabs_*.py src 側再エクスポートの削除対象特定
- **対象ファイル**: `src/ui_tabs_analytics.py`, `src/ui_tabs_audit.py`, `src/ui_tabs_marketing.py`, `src/ui_tabs_monitor.py`, `src/ui_tabs_planning.py`, `src/ui_tabs_writing.py`
- **アクション**: 各ファイルの中身を Grep で確認し、どれが再エクスポートのみか判定

#### ステップ10: src/ui_tabs_*.py の削除
- **判断**: 再エクスポートだけのファイルは削除
- **アクション**: 6ファイルの `src/` 側をすべて削除
- **備考**: `src/ui_tabs_writing.py` だけは複数エクスポートのため注意（ステップ9で判定）

#### ステップ11: src/ui_tabs_* 参照先の修正
- **アクション**: Grep で `from src.ui_tabs_` を検索し、`from streamlit_app.ui_tabs_` に変更
- **対象**: おそらく `src/proxy.py` や `src/engine_service.py` などで参照されている可能性

#### ステップ12: src/ 直下の ui_components.py, state.py, proxy.py, progress.py の扱い確認
- **対象ファイル**: `src/ui_components.py`, `src/state.py`, `src/proxy.py`, `src/progress.py`
- **アクション**: これらが何をしているか、streamlit_app 側に同名ファイルがあるかどうか確認
- **判断基準**:
  - 薄いラッパー → 削除して streamlit_app 側を参照
  - 実質的な実装 → streamlit_app 側にマージまたは src 側に残す

---

### 第2フェーズ: ラッパー層・再エクスポート除去（13-24）

#### ステップ13: src/progress.py の分析
- **確認項目**: `run_in_background` がスタブか否か
- **アクション**: ファイルを読んで実装を確認
- **備考**: 報告によりスタブであることが判明済み

#### ステップ14: src/progress.py の削除判定
- **判断**: スタブであれば削除し、streamlit_app/progress.py に完全移行
- **アクション**: `src/progress.py` を削除

#### ステップ15: src/proxy.py の分析
- **確認項目**: `UltimateHegemonyEngineProxy` が何をしているか
- **アクション**: ファイルを読んで streamlit_app/proxy.py との違いを調査

#### ステップ16: src/proxy.py のラッパー削除
- **判断**: 薄いラッパーの場合
- **アクション**: `src/proxy.py` を削除し、streamlit_app/proxy.py を正とする
- **備考**: 循環参照がないか確認

#### ステップ17: src/state.py の分析
- **確認項目**: UI state 管理かビジネスロジック state か
- **アクション**: ファイルを読んで streamlit_app/state.py との違いを調査

#### ステップ18: src/state.py の処理
- **判断基準**:
  - UI state のみ → streamlit_app/state.py に統合、src 側は削除
  - ビジネスロジック → src に残す（streamlit_app は参照）
- **アクション**: 判断結果に従って処理

#### ステップ19: src/ui_components.py の分析
- **確認項目**: streamlit_app/ui_components.py との違い
- **アクション**: ファイルを読んで比較

#### ステップ20: src/ui_components.py の処理
- **判断**: 薄いラッパーは削除し、streamlit_app/ui_components.py を正とする
- **アクション**: 判断結果に従って削除またはマージ

#### ステップ21: src/engine_service.py の分析
- **確認項目**: ビジネスロジックか UI 向けか
- **アクション**: ファイルを読んで streamlit_app/engine_service.py と比較

#### ステップ22: src/engine_service.py の処理
- **判断**: ビジネスロジックの場合は残し、薄いラッパーは削除
- **アクション**: 判断結果に従う

#### ステップ23: src/__init__.py の整理
- **アクション**: `src/__init__.py` が何もエクスポートしていないか確認
- **備考**: 現在のところ空であることを explorer が確認済み

#### ステップ24: src/agents/__init__.py, src/models/__init__.py の __all__ 確認
- **アクション**: `__all__` が適切に定義されているか確認
- **目的**: 不必要な再エクスポートを防ぐ

---

### 第3フェーズ: バックエンドタスク機構修正（25-36）

#### ステップ25: streamlit_app/progress.py の実装確認
- **確認項目**: `run_in_background` の実装がスタブでないか
- **アクション**: ファイルを読んで実際のバックグラウンドタスク処理を確認

#### ステップ26: streamlit_app/progress.py の run_in_background 修正
- **判断**: スタブの場合の実装
- **アクション**: 実際のバックグラウンドタスク機構（ThreadPoolExecutor, asyncio, または huey/RQ 等のタスクキュー）を実装

#### ステップ27: src/progress の全参照元調査
- **アクション**: Grep で `from src.progress import` および `import src.progress` を検索
- **対象ファイルリスト作成**

#### ステップ28: streamlit_app/ 内の src.progress 参照を streamlit_app.progress に置換
- **対象**: ステップ27で見つかった streamlit_app/ 内のファイル
- **アクション**: `from src.progress import` → `from streamlit_app.progress import` に変更

#### ステップ29: src/ 内の src.progress 参照調査
- **アクション**: src/ ファイルで `from src.progress import` を検索
- **備考**: src/ からは参照がないはずだが確認

#### ステップ30: streamlit_app/background.py の分析
- **確認項目**: バックグラウンドタスク処理の既存実装
- **アクション**: ファイルを読んで streamlit_app/progress.py との関係を確認

#### ステップ31: background.py と progress.py の統合判断
- **判断**: 両方の機能が必要か、一方に統合できるか
- **アクション**: 判断結果に従って統合または整理

#### ステップ32: streamlit_app/actions.py の分析
- **確認項目**: アクションフックの実装
- **アクション**: ファイルを読んで `run_in_background` を使用しているか確認

#### ステップ33: streamlit_app/actions.py の src.progress 参照置換
- **アクション**: `from src.progress import` → `from streamlit_app.progress import` に変更

#### ステップ34: streamlit_app/api_client.py の分析
- **確認項目**: バックエンド API 通信の実装
- **アクション**: ファイルを読んで HTTP クライアントとして使用されているか確認

#### ステップ35: streamlit_app/proxy.py の run_in_background 参照確認
- **アクション**: `src.proxy` ではなく `streamlit_app.proxy` を使うように修正
- **備考**: proxy.py が内部で `run_in_background` を使っているか確認

#### ステップ36: 手動検証ポイントの確認
- **検証項目**:
  1. `streamlit_app.progress.run_in_background` でタスクが起動すること
  2. タスクのステータス取得ができること
  3. UI が正しく進捗を表示できること
- **アクション**: テストコマンドまたは手動テスト手順の文書化

---

### 第4フェーズ: テストスタブのスコープ限定（37-44）

#### ステップ37: src/actions.py の存在確認
- **アクション**: `ls src/` で actions.py の存在確認
- **備考**: explorer の報告では src/ 直下に actions.py はなかったが、再確認

#### ステップ38: src/api_client.py の存在確認
- **アクション**: 同上
- **備考**: explorer の報告では src/ 直下に api_client.py もなかった

#### ステップ39: src/agents/ 内の test 用スタブ調査
- **アクション**: `src/agents/` にテスト専用のコードがないか確認
- **備考**: 多くの場合、agents は直接テストされない

#### ステップ40: tests/ から src/ へのインポート調査
- **アクション**: Grep で `from src.` を tests/ ファイル内で検索
- **目的**: テストが src をどのように参照しているか把握

#### ステップ41: テストスタブの配置場所確認
- **アクション**: `tests/mocks/` にスタブが既にあるか確認
- **備考**: tests/mocks/__init__.py は空

#### ステップ42: src/actions.py の新規作成または確認（必要に応じて）
- **判断**: テスト専用アクションスタブが必要か
- **アクション**: 必要であれば `tests/mocks/actions.py` を作成し、`src/` には配置しない
- **備考**: ユーザーが明示的に `src/actions.py` をテストスタブとして指定しているため、このファイルが存在する場合は __all__ で隠すか削除

#### ステップ43: src/api_client.py の __all__ 設定（存在する場合）
- **アクション**: ファイルが存在し、プロダクションコードから参照される場合、`__all__ = []` を設定して非公開化
- **備考**: テストからは直接インポート可能にする

#### ステップ44: src/ のプロダクションからの参照クリーンアップ
- **アクション**: Grep で `from src.actions import` および `from src.api_client import` をプロダクションコード（streamlit_app/, src/ のビジネスロジック層）で検索
- **修正**: プロダクションからの参照を削除

---

### 第5フェーズ: ドキュメント整備（45-46）

#### ステップ45: README.md の確認
- **アクション**: README.md を読み、src/ のラッパーについて言及があるか確認
- **問題箇所**: があればメモ

#### ステップ46: docs/ 内のアーキテクチャドキュメント更新
- **対象ファイル**:
  - `docs/ui_partitioning_policy.md`
  - `docs/ui_dependency_map.md`
  - `docs/di_architecture.md`
  - `docs/architecture_refactoring_plan.md`
- **アクション**: ラッパー層の削除を反映するよう更新
- **備考**: 実際のコードとドキュメントの不一致を防ぐ

---

### 第6フェーズ: CI・統合テスト追加（47-48）

#### ステップ47: インテグレーションテスト用のテストファイル作成
- **ファイル名**: `tests/integration/test_ui_backend_communication.py`
- **テスト内容**:
  1. UI がバックエンド API と通信できるか
  2. タスク生成是否能
  3. ステータス取得是否能
  4. プログレス更新是否能
- **アクション**: 新規テストファイル作成

#### ステップ48: CI 設定の確認とテスト実行コマンド追加
- **対象ファイル**: `pytest.ini`, `pyproject.toml`, `mypy.ini`
- **アクション**:
  1. 統合テストが CI で実行されるか確認
  2. lint/typecheck コマンド確認
  3. 必要に応じて pytest.ini に統合テストのpaths を追加
- **備考**: ユーザーは lint/typecheck コマンドを明示的に提供していないため `./start_app.bat` や `pyproject.toml` を参照して確認

---

## 完了条件チェックリスト

- [ ] `src/workflow_types.py` が削除され、`streamlit_app/workflow_types.py` だけが存続
- [ ] `src/shared/utils/async_helper.py`, `src/shared/utils/async_manager.py` が削除
- [ ] `src/ui_tabs_*.py` がすべて削除され、`streamlit_app/ui_tabs_*.py` だけが存続
- [ ] `src/progress.py`, `src/proxy.py` の薄いラッパーが削除
- [ ] `streamlit_app/` からの `from src.` インポートが `from streamlit_app.` に置換
- [ ] `streamlit_app/progress.py` の `run_in_background` がスタブから実装に置き換え
- [ ] `src/actions.py`, `src/api_client.py` がテスト専用として `__all__` で非公開化（存在する場合）
- [ ] README.md, docs/ が更新され、コードとドキュメントが一致
- [ ] インテグレーションテストが追加され、UI とバックエンド API の通信をテスト
- [ ] `pytest` が通過し、lint/typecheck が通過

---

## リスクと注意事項

1. **循環参照**: `streamlit_app/utils/async_manager.py` が `src/shared/utils/async_helper.py` を参照していた。統合時にこのインポートを修正する必要がある。
2. **src.engine_service.py**: ビジネスロジックなのかラッパーなのか判断が必要
3. **バックグラウンドタスク**: huey.db, huey タスクキューが既にある場合、streamlit_app/progress.py はこれを活用すべき
4. **テスト依存**: 既存のテストが src をインポートしている場合、修正が必要

---

## 前提条件

本計画を実行する前に以下を確認すること:
1. Python 3.11+ 環境
2. すべてのソースファイルを Git でコミット済み（作業前のスナップショット）
3. pytest, mypy, ruff (または pyproject.toml 内の lint/typecheck ツール) が利用可能