# 72ステップ実装計画書：リファクタリング・技術的負債解消・テスト強化

**作成日**: 2026-07-07  
**対象プロジェクト**: cR15 (覇権小説自動生成エンジン)  
**目的**: 複雑性の軽減、技術的負債解消、ドキュメント整備、テストカバレッジ強化、CI/CD整備

---

## 概要

| カテゴリ | 問題点 | 対応フェーズ |
|---------|--------|-------------|
| 複雑性 | UltimateHegemonyEngineの責任過多 | Phase 4-5 (ステップ25-48) |
| 技術的負債 | コメント残存・循環参照リスク | Phase 2-3 (ステップ13-36) |
| ドキュメント不足 | 内部API・データフロー未文書化 | Phase 1 (ステップ1-12) |
| テストカバレッジ | 統合テスト・E2Eテスト不足 | Phase 6 (ステップ49-60) |
| CI/CD整備 | mypy/pytest自動化なし | Phase 7 (ステップ61-72) |

---

## Phase 1: ドキュメント・データフロー整備（ステップ1-12）

### ステップ1: アーキテクチャ図の現状確認
- **対象ファイル**: `docs/architecture_analysis.md`, `docs/di_graph_20260707.svg`
- **アクション**: 既存の図を確認し、何が古いかを更新
- **検証**: 図とコードの整合性を確認

### ステップ2: UltimateHegemonyEngineのメソッド一覧作成
- **対象ファイル**: `src/backend/engine.py`
- **アクション**: 全publicメソッドをリスト化し、各メソッドの責任を記述
- **出力**: `docs/engine_methods_inventory.md` (既存ファイルを更新)

### ステップ3: データフロー図の作成
- **アクション**: プロンプト生成→LLM呼び出し→結果パース→DB保存のフローを図示
- **出力**: `docs/data_flow_diagram.md`
- **形式**: MermaidまたはPlantUML

### ステップ4: Container依存関係図の更新
- **対象ファイル**: `src/core/container.py`
- **アクション**: DIグラフが最新か確認し、更新
- **出力**: `docs/di_graph_latest.svg`

### ステップ5: APIエンドポイント一覧の作成
- **対象ファイル**: `src/backend/server.py`
- **アクション**: 全APIエンドポイントをリスト化
- **出力**: `docs/api_endpoints.md`

### ステップ6: エージェント間相互作用図の作成
- **対象ファイル**: `src/agents/`
- **アクション**: PlanningAgent, WritingAgent, CritiqueAgent等の相互作用を文書化
- **出力**: `docs/agent_interaction.md`

### ステップ7: ワークフロー一覧の作成
- **対象ファイル**: `src/backend/workflows/`
- **アクション**: 各ワークフローの入出力を文書化
- **出力**: `docs/workflows_inventory.md`

### ステップ8: データモデル図の作成
- **対象ファイル**: `src/backend/database/models.py`, `src/models/`
- **アクション**: 主要エンティティとリレーションを文書化
- **出力**: `docs/data_model.md`

### ステップ9: 例外階層図の作成
- **対象ファイル**: `src/core/exceptions.py`, `src/services/errors.py`
- **アクション**: 既存の例外クラスを整理し階層図を作成
- **出力**: `docs/exception_hierarchy.md`

### ステップ10: 設定ファイル一覧の作成
- **対象ファイル**: `config/`
- **アクション**: 各設定ファイルの役割と依存関係を文書化
- **出力**: `docs/config_files.md`

### ステップ11: テストカバレッジレポートの作成
- **アクション**: `pytest --cov` を実行し、 coverage report を生成
- **出力**: `docs/test_coverage_report.md`

### ステップ12: 技術的負債一覧の作成
- **アクション**: コード中の `# TODO`, `# FIXME`, `# XXX`, `# HACK` をリスト化
- **出力**: `docs/technical_debt_list.md`

---

## Phase 2: 技術的負債 - コメント・循環参照解消（ステップ13-24）

### ステップ13: TODOコメントの分類
- **対象**: ステップ12で作成した一覧
- **アクション**: 各TODOを「削除」「延期」「実装」に分類
- **基準**: 30分以内に解決できるものは即対応

### ステップ14: 緊急度の高いTODOの解決（1-5）
- **アクション**: 削除可能なコメントを削除、実装可能なものは実装
- **例**: `# TODO: Move errors to src/shared/utils` → エラーを移動

### ステップ15: 緊急度の高いTODOの解決（6-10）
- **アクション**: 引き続きTODOを解決

### ステップ16: 循環参照の検出
- **アクション**: `python -c "import ast; ..."` で循環インポートを検出
- **対象ファイル**: `src/backend/engine.py`, `src/core/container.py`

### ステップ17: 循環参照の解決（その1）
- **対象**: `TYPE_CHECKING` ブロックで解決可能なもの
- **アクション**: タイプヒントだけのインポートを `if TYPE_CHECKING:` に移動

### ステップ18: 循環参照の解決（その2）
- **対象**: 遅延インポートで解決可能なもの
- **アクション**: 関数内でのインポートに移動

### ステップ19: 未使用インポートの削除
- **アクション**: `ruff check --select=F401` または `pyflakes` で検出
- **対象ディレクトリ**: `src/`

### ステップ20: 未使用変数の削除
- **アクション**: `ruff check --select=F841` で検出
- **対象ディレクトリ**: `src/`

### ステップ21: コメントアウトされたコードの削除
- **アクション**: `# # ` で始まるコメントアウトされたコードを削除
- **対象ディレクトリ**: `src/`

### ステップ22: ドキュメント文字列の追加（主要クラス）
- **対象**: `UltimateHegemonyEngine`, `AppContainer`, `DataRepository`
- **アクション**: 不足しているdocstringを追加

### ステップ23: ドキュメント文字列の追加（エージェント）
- **対象**: `PlanningAgent`, `WritingAgent`, `CritiqueAgent`, `MarketingAgent`
- **アクション**: 各エージェントのdocstringを追加

### ステップ24: ドキュメント文字列の追加（サービス）
- **対象**: `src/services/` の主要ファイル
- **アクション**: 各サービスのdocstringを追加

---

## Phase 3: 技術的負債 - 重複ファイル統合（ステップ25-36）

### ステップ25: 重複ファイル調査
- **アクション**: 同一名のファイルを検索
- **対象**: `workflow_types.py`, `async_helper.py`, `async_manager.py`

### ステップ26: workflow_types.py の統合
- **対象**: `src/workflow_types.py`, `streamlit_app/workflow_types.py`
- **アクション**: `streamlit_app/workflow_types.py` を正とし、`src/workflow_types.py` を削除
- **参照修正**: `from src.workflow_types` → `from streamlit_app.workflow_types`

### ステップ27: async_helper.py の統合
- **対象**: `src/shared/utils/async_helper.py`, `streamlit_app/utils/async_helper.py`
- **アクション**: `streamlit_app/utils/async_helper.py` を正とし、他方を削除

### ステップ28: async_manager.py の統合
- **対象**: `src/shared/utils/async_manager.py`, `streamlit_app/utils/async_manager.py`
- **アクション**: `streamlit_app/utils/async_manager.py` を正とし、他方を削除

### ステップ29: src/shared/utils/ のクリーンアップ
- **アクション**: 空になったディレクトリを削除

### ステップ30: ui_tabs_*.py の統合確認
- **対象**: `src/ui_tabs_*.py`, `streamlit_app/ui_tabs_*.py`
- **アクション**: 再エクスポートだけのファイルを削除

### ステップ31: src/progress.py の分析
- **対象ファイル**: `src/progress.py`, `streamlit_app/progress.py`
- **アクション**: `run_in_background` の実装を確認

### ステップ32: src/progress.py の処理
- **判断**: スタブであれば削除し、`streamlit_app/progress.py` を使用
- **アクション**: 参照先を修正

### ステップ33: src/proxy.py の分析
- **対象ファイル**: `src/proxy.py`, `streamlit_app/proxy.py`
- **アクション**: `UltimateHegemonyEngineProxy` の実装を確認

### ステップ34: src/proxy.py の処理
- **判断**: 薄いラッパーであれば削除
- **アクション**: 参照先を修正

### ステップ35: src/state.py の分析
- **対象ファイル**: `src/state.py`, `streamlit_app/state.py`
- **アクション**: UI state かビジネスロジックか判定

### ステップ36: src/state.py の処理
- **判断基準**: UI state → streamlit_app に統合、ビジネスロジック → src に残す
- **アクション**: 判定結果に従い処理

---

## Phase 4: UltimateHegemonyEngine リファクタリング - 分析（ステップ37-48）

### ステップ37: UltimateHegemonyEngine の責任リスト作成
- **対象ファイル**: `src/backend/engine.py`
- **アクション**: `__init__` で初期化している全コンポーネントをリスト化
- **出力**: 責任一覧表

### ステップ38: 責任の分類（その1）
- **分類**: Container管理、DB管理、Agent管理、LLM管理、Formatter/Validator
- **アクション**: 各責任をカテゴリに分類

### ステップ39: 責任の分類（その2）
- **分類**: サービス層への委譲、 직접実装
- **アクション**: 委譲可能なものを特定

### ステップ40: インターフェース抽出の計画
- **アクション**: 各責任のインターフェースを定義
- **対象**: `ILlmClient`, `IDatabase`, `IFormatter`, `IValidator`

### ステップ41: Agent抽出の計画
- **アクション**: `bible_agent`, `plot_agent`, `planner`, `writer` を独立したサービスに抽出
- **出力**: 抽出後のアーキテクチャ図

### ステップ42: Container の現状分析
- **対象ファイル**: `src/core/container.py`
- **アクション**: Provider定義を確認し、不足分を特定

### ステップ43: Container リファクタリング計画
- **アクション**: ステップ37-41を基にContainer再構成計画を文書化
- **出力**: `docs/container_refactoring_plan.md`

### ステップ44: 委譲メソッドの特定
- **対象ファイル**: `src/backend/engine.py`
- **アクション**: `self.xxx = self.container.xxx()` のパターンをリスト化

### ステップ45: 冗長なゲッターの特定
- **アクション**: `engine.xxx` で直接アクセス可能なものを確認
- **対象**: `engine.repo`, `engine.planner`, `engine.writer` など

### ステップ46: エンジン呼び出しの依存関係調査
- **アクション**: `UltimateHegemonyEngine` をインポートしているファイルをリスト化
- **対象**: `src/backend/`, `src/services/`, `src/workflows/`

### ステップ47: ワークフローからの依存関係分析
- **対象ファイル**: `src/backend/workflows/base_workflow.py`
- **アクション**: `engine` パラメータの使用方法を分析

### ステップ48: リファクタリングのリスク評価
- **アクション**: 循環参照リスク、テスト影響、API互換性を評価
- **出力**: `docs/refactoring_risk_assessment.md`

---

## Phase 5: UltimateHegemonyEngine リファクタリング - 実装（ステップ49-60）

### ステップ49: インターフェース定義ファイルの作成
- **出力ファイル**: `src/core/interfaces.py`
- **アクション**: `ILlmClient`, `IDatabase`, `IFormatter`, `IValidator` を定義

### ステップ50: Agentサービスへの抽出（その1）
- **対象**: `bible_agent` → `BibleService`
- **アクション**: `src/services/bible_service.py` として抽出
- **備考**: 低性能LLMでも実装可能な小さな変更

### ステップ51: Agentサービスへの抽出（その2）
- **対象**: `plot_agent` → `PlotService`
- **アクション**: `src/services/plot_service.py` として抽出

### ステップ52: Agentサービスへの抽出（その3）
- **対象**: `planner` → `PlanningService`
- **アクション**: `src/services/planning_service.py` として抽出

### ステップ53: Agentサービスへの抽出（その4）
- **対象**: `writer` → `WritingService`
- **アクション**: `src/services/writing_service.py` として抽出

### ステップ54: Container へのサービス登録
- **対象ファイル**: `src/core/container.py`
- **アクション**: 新サービスをProviderとして登録

### ステップ55: Engine からの委譲削除（その1）
- **対象**: `bible_agent`, `plot_agent` の直接委譲を削除
- **アクション**: 呼び出し元を直接サービスを使用するよう修正

### ステップ56: Engine からの委譲削除（その2）
- **対象**: `planner`, `writer` の直接委譲を削除
- **アクション**: 呼び出し元を直接サービスを使用するよう修正

### ステップ57: Engine の __init__ 簡素化
- **対象ファイル**: `src/backend/engine.py`
- **アクション**: Container初期化のみに简化

### ステップ58: ワークフローの更新
- **対象ファイル**: `src/backend/workflows/base_workflow.py`
- **アクション**: `engine` の代わりに必要なサービスを直接注入

### ステップ59: バックエンドタスクの更新
- **対象ファイル**: `src/backend/tasks.py`
- **アクション**: `UltimateHegemonyEngine` の代わりにサービスを使用

### ステップ60: リグレッションテスト実行
- **アクション**: `pytest tests/` を実行し、既存機能が動作することを確認
- **修正**: 失敗したテストを修正

---

## Phase 6: テストカバレッジ強化（ステップ61-66）

### ステップ61: 統合テストの追加（その1）
- **対象**: `tests/integration/test_workflow.py`
- **アクション**: `FullAutoWorkflow` の正常系テストを追加

### ステップ62: 統合テストの追加（その2）
- **対象**: `tests/integration/test_repo_book.py`, `test_repo_character.py`
- **アクション**: Repository のCRUDテストを追加

### ステップ63: E2Eテストの追加
- **対象**: `tests/e2e/`
- **アクション**: 主要ユーザーフローのE2Eテストを作成
- **例**: 「作品作成→プロット生成→執筆開始→完了」

### ステップ64: モック戦略の標準化
- **対象**: `tests/mocks/`
- **アクション**: 共通モッククラスを作成
- **例**: `MockLlmClient`, `MockRepository`

### ステップ65: テストフィクスチャの整理
- **対象**: `tests/conftest.py`
- **アクション**: 共通フィクスチャを整理・文書化

### ステップ66: カバレッジレポートの生成
- **アクション**: `pytest --cov=src --cov-report=html` を実行
- **出力**: `htmlcov/index.html`
- **目標**: カバレッジ80%以上

---

## Phase 7: CI/CD整備（ステップ67-72）

### ステップ67: mypy設定の確認
- **対象ファイル**: `mypy.ini`
- **アクション**: 既存設定を確認し、不足分を補完

### ステップ68: mypy_baselineの作成
- **アクション**: `mypy src/ > mypy_baseline.txt` を実行
- **目的**: 既存のエラーを記録し、増加を防止

### ステップ69: pytest設定の確認
- **対象ファイル**: `pytest.ini`, `pyproject.toml`
- **アクション**: テストパス、オプションを確認

### ステップ70: CIワークフローの作成
- **出力ファイル**: `.github/workflows/ci.yml`
- **アクション**: pytest, mypy, ruff の実行を追加

### ステップ71: pre-commitフックの設定
- **対象ファイル**: `.pre-commit-config.yaml`
- **アクション**: ruff, mypy, pytest の自動実行を設定

### ステップ72: CI/CDドキュメントの更新
- **対象ファイル**: `docs/ci_pipeline.md`
- **アクション**: CI/CD流程を文書化

---

## 完了条件チェックリスト

### ドキュメント整備
- [ ] アーキテクチャ図が最新
- [ ] データフロー図が作成済み
- [ ] APIエンドポイント一覧が完成
- [ ] 技術的負債一覧が作成済み

### 技術的負債解消
- [ ] TODO/FIXMEコメントが解決済み
- [ ] 循環参照が解消済み
- [ ] 重複ファイルが統合済み
- [ ] 未使用インポート・変数が削除済み

### UltimateHegemonyEngine リファクタリング
- [ ] エンジンが単一責任原則に従う
- [ ] Agentが独立したサービスに抽出済み
- [ ] ワークフローがサービスを直接使用
- [ ] 既存テストが通過

### テストカバレッジ
- [ ] 統合テストが追加済み
- [ ] E2Eテストが追加済み
- [ ] カバレッジ80%以上

### CI/CD
- [ ] mypyが実行可能
- [ ] pytestが実行可能
- [ ] CIワークフローが動作
- [ ] pre-commitフックが設定済み

---

## リスクと注意事項

1. **リファクタリング中の機能破壊**: ステップ60で必ずテストを実行し、機能を維持
2. **循環参照の潜在的リスク**: ステップ16-18で必ず検出・解決
3. **低性能LLMでの実行**: 各ステップは独立して実行可能で、30分以内に完了する粒度
4. **段階的なデプロイ**: ステップ61以降でテストを追加しながら進める

---

## スケジュール目安

| Phase | ステップ | 推定時間 |
|-------|---------|----------|
| Phase 1 | 1-12 | 4-6時間 |
| Phase 2 | 13-24 | 3-4時間 |
| Phase 3 | 25-36 | 2-3時間 |
| Phase 4 | 37-48 | 3-4時間 |
| Phase 5 | 49-60 | 6-8時間 |
| Phase 6 | 61-66 | 4-5時間 |
| Phase 7 | 67-72 | 2-3時間 |

**合計**: 約24-33時間

---

## 付録: ステップ実行記録

| ステップ | 実行日 | 実行者 | 結果 | 備考 |
|---------|--------|--------|------|------|
| 1 | | | | |
| 2 | | | | |
| ... | | | | |
| 72 | | | | |