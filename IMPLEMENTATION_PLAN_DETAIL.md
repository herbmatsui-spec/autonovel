# 詳細実装計画書：テストカバレッジ向上プロジェクト

## 目的
プロジェクト全体のテストカバレッジを現在の56%から80%以上に引き上げる。これにより、リグレッション検知能力を向上させ、品質を確保する。

## 現状分析（ベースライン）
- **全体カバレッジ**: 56%（23,898 文／未実行 10,533 文）
- **テスト結果**: 867 パス / 82 フェイル / 106 スキップ
- **主な失原因**: フィクスチャ／モックの不足（DB セッション、LLM クライアント、Hueu、ChromaDB など）
- **低カバレッジホットスポット**（30% 未満）：
  - `src/agents/context_builder.py` (9%)
  - `src/agents/scheduler_coordinator.py` (13%)
  - `src/agents/episode_pipeline.py` (22%)
  - `src/agents/plot.py` (17%)
  - `src/agents/marketing.py` (23%)
  - `src/agents/base.py` (32%)
  - `src/agents/audit.py` (44%)
  - `src/backend/sse.py` (24%)
  - `src/backend/tasks.py` (19%)
  - `src/backend/repository.py` (22%)
- **強み**: `rate_limit.py` 100%、多くのモデル・インフラストラクチャが高カバレッジ。

## 戦略的アプローチ
1. **テスト基盤の整備**（フェーズ0）：失敗テストの根本原因であるモック不足を解消し、テストスイートをグリーンに近づける。
2. **カバレッジの底上げ**（フェーズ1）：カバレッジが低いモジュールを優先的にテストし、全体平均を引き上げる。
3. **品質ゲートの導入**（フェーズ2）：CI にカバレッジ閾値を組み込み、今後のリグレッションを防止する。

## フェーズ別実装計画

### フェーズ0：テスト基盤の整備（目標：フェイル数を 82 → 20 以下）
| ステップ | 説明 | ファイル | コマンド |
|----------|------|----------|----------|
| 0-1 | `conftest.py` に DB セッションモックフィクスチャを追加 | `tests/conftest.py` | フィクスチャ追加後、`pytest tests/unit/test_uow.py -q` を実行し、`AttributeError` が解消されることを確認 |
| 0-2 | `AppContainer.db()` をモックに差し替えるオートユースフィクスチャを追加 | 同上 | 同上 |
| 0-3 | Huey モックフィクスチャを作成し、タスク関連テストをパスさせる | `tests/mocks/mock_huey.py`、`tests/conftest.py` | `pytest tests/unit/test_background_worker.py -q` |
| 0-4 | ChromaDB モックフィクスチャを作成し、ベクターストアテストをパスさせる | `tests/mocks/mock_chroma.py`、`tests/conftest.py` | `pytest tests/unit/test_vector_store_lifecycle.py -q` |
| 0-5 | LLM クライアントモックフィクスチャを強化し、ヘルスチェックテストをパスさせる | `tests/mocks/mock_llm_client.py`、`tests/conftest.py` | `pytest tests/unit/test_health.py -q` |
| 0-6 | 全テストを実行し、フェイル数を測定 | - | `pytest -q` （目標：フェイル 20 以下） |
| 0-7 | カバレッジを測定しベースラインを記録 | - | `coverage run -m pytest && coverage report` （目標：60% 超え） |

### フェーズ1：カバレッジの底上げ（目標：全体カバレッジ 80%+）
#### ステップ1-1：バックエンド中核（sse, tasks, repository）
| ステップ | 説明 | ファイル | コマンド |
|----------|------|----------|----------|
| 1-1 | `sse.py` のフォールバックパス（Redis=None）をテスト | `tests/unit/test_sse_fallback.py` 新規作成 | `pytest tests/unit/test_sse_fallback.py -q` |
| 1-2 | `tasks.py` のヘルパー関数（`generate_task_id` 等）をテスト | `tests/unit/test_tasks_helpers.py` 新規作成 | `pytest tests/unit/test_tasks_helpers.py -q` |
| 1-3 | `repository.py` の基本 CRUD 操作をモック DB でテスト | `tests/unit/test_repository_crud.py` 新規作成 | `pytest tests/unit/test_repository_crud.py -q` |
| 1-4 | 上記テストをパスさせた後、カバレッジ測定 | - | `coverage run -m pytest && coverage report` （目標：70% 超え） |

#### ステップ1-2：LLM 関連（0% → 60%+）
| ステップ | 説明 | ファイル | コマンド |
|----------|------|----------|----------|
| 1-5 | `model_router.py` のプロバイダ選択ロジックをテスト | `tests/unit/test_model_router.py` 新規作成 | `pytest tests/unit/test_model_router.py -q` |
| 1-6 | `provider_factory.py` のフォールバック動作をテスト | `tests/unit/test_provider_factory.py` 新規作成 | `pytest tests/unit/test_provider_factory.py -q` |
| 1-7 | `openai_provider.py` の例外ハンドリングをテスト | `tests/unit/test_openai_provider.py` 新規作成 | `pytest tests/unit/test_openai_provider.py -q` |
| 1-8 | 上記テストをパスさせた後、カバレッジ測定 | - | 同上 （目標：75% 超え） |

#### ステップ1-3：Agents パッケージ（0% → 60%+）
| ステップ | 説明 | ファイル | コマンド |
|----------|------|----------|----------|
| 1-9 | `agents/audit.py` のスコア集計純関数をテスト | `tests/unit/test_agents_audit.py` 新規作成 | `pytest tests/unit/test_agents_audit.py -q` |
| 1-10 | `agents/writing/writing.py` の `_build_*` ヘルパーをテスト | `tests/unit/test_writing_builders.py` 新規作成 | `pytest tests/unit/test_writing_builders.py -q` |
| 1-11 | `agents/plot.py` のプロット展開ロジックをテスト | `tests/unit/test_plot_agent.py` 新規作成 | `pytest tests/unit/test_plot_agent.py -q` |
| 1-12 | `agents/context_builder.py` のコンテキストマージロジックをテスト | `tests/unit/test_context_builder.py` 新規作成 | `pytest tests/unit/test_context_builder.py -q` |
| 1-13 | `agents/writing_scheduler.py` のスケジュール計算をテスト | `tests/unit/test_writing_scheduler.py` 新規作成 | `pytest tests/unit/test_writing_scheduler.py -q` |
| 1-14 | 上記テストをパスさせた後、カバレッジ測定 | - | 同上 （目標：80% 超え） |

### フェーズ2：品質ゲートの導入と最終確認
| ステップ | 説明 | ファイル | コマンド |
|----------|------|----------|----------|
| 2-1 | `pytest.ini` にカバレッジオプションを戻す（CI 用） | `pytest.ini` | `addopts = -v --tb=short --cov=src --cov=prompts --cov-report=term-missing` |
| 2-2 | `pyproject.toml` または `setup.cfg` にカバレッジ閾値を追加 | `pyproject.toml` | `[tool.coverage.report]\nfail_under = 80` |
| 2-3 | フロントエンドテスト基盤を導入（Vitest） | `frontend/package.json` | `"devDependencies": { "vitest": "^latest" }`、`"test": "vitest run"` |
| 2-4 | フロントエンドコンポーネントの最低限テストを追加 | `frontend/src/components/dialogs/SettingsModal.test.tsx` | `npm test` （か `pnpm test`） |
| 2-5 | `novel_50ep` のテストをカバレッジ対象に含める | `pytest.ini` の `testpaths` | `testpaths = tests novel_50ep/tests` |
| 2-6 | 最終検証：全テストパスかつカバレッジ 80%+ | - | `pytest -q`、`coverage run -m pytest && coverage report` |

## 成功基準
- **テスト結果**: 0 フェイル（スキップは許容）
- **全体カバレッジ**: 80% 以上（`coverage report` の TOTAL）
- **クリティカル領域カバレッジ**: `src/backend`（Critical/High 項目）で 90% 以上
- **弱点領域カバレッジ**: `src/llm`、`src/agents` 各 60% 以上
- **フロントエンド**: 最低 1 テストが存在し CI で実行される
- **novel_50ep**: テストが収集されパスする

## リスクと緩和策
| リスク | 緩和策 |
|--------|--------|
| モックの過剰による本番挙動乖離 | `autouse` フィクスチャは `tests/` 配下のみに限定し、`conftest.py` のスコープを明示する |
| フィクスチャの競合 | フィクスチャ名は具体的にし、`scope="function"` をデフォルトとする |
| カバレッジ測定のばらつき | 単一の測定方法（`coverage run -m pytest`）に統一し、ドキュメント化 |
| 作業の分散 | 各ステップをチケット化し、進捗をボードで可視化 |
| フロントエンド導入の負荷 | まずは 1 コンポーネントから始め、段階的に拡張 |

## 完了の定義
上記「成功基準」をすべて満たしたら、このプロジェクトは完了とする。完了後は、この計画書をアーカイブし、得られた教訓を `PROJECT_LESSONS.md` に還元する。

---
*この計画書は 2026-08-28 に作成されました。実装進捗は `IMPLEMENTATION_PROGRESS.md` に記録してください。*