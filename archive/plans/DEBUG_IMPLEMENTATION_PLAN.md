# エラー握り潰し根絶＆デバッグ実装計画書

## 1. 背景と目的

プロジェクト全体を精査し、エラーを握り潰さずに正しく可視化・伝搬させるデバッグ基盤を整える。これにより：

- バックエンド起動・Hueyタスク実行・テスト実行時に潜む**隠れたバグを即座に検出**できる状態にする
- `except Exception: pass` 等のエラー握り潰しを排除し、ログ・トレースで追跡可能にする
- 失敗時の根本原因を即座に特定できる状態にする

## 2. 調査結果サマリ

### 2.1 検出されたテスト失敗・エラー（実行ベース）

| # | 種別 | 場所 | 症状 |
|---|------|------|------|
| 1 | ImportError | [`src/kernels/dialogue.py:11`](src/kernels/dialogue.py:11) | `DialogueManager` クラス未定義 → `src/kernels/__init__.py:11` が失敗 |
| 2 | ImportError | [`src/kernels/connection_kernel.py:8`](src/kernels/connection_kernel.py:8) | `from ..shared.network import NetworkUtils` → 相対importの上限超過 |
| 3 | TypeError | [`src/backend/engine.py:44`](src/backend/engine.py:44) | `PlotService(repo=repo, llm=llm)` → `PlotService.__init__` は `repo` のみ |
| 4 | AssertionError | [`tests/test_config.py:47`](tests/test_config.py:47) | `gemini-3.5-flash-lite` 期待 vs `gemini-3.1-flash-lite` 実際 |
| 5 | ImportError | `tests/test_outbox_worker.py` | `connection_kernel.py:8` の相対import崩れ |
| 6 | ImportError | `tests/test_vector_store_lifecycle.py` | 同上（カスケード） |
| 7 | AttributeError系 | `src/backend/server.py:46` | `except Exception` → `import traceback` を内側で行うが冗長 |

### 2.2 エラー握り潰し箇所（grep で 70 件以上）

- **握り潰しCore**: [`src/backend/database/core.py:112,174,338,373`](src/backend/database/core.py:112), [`src/backend/routers/tasks.py:26,62,86`](src/backend/routers/tasks.py:26), [`src/backend/background.py:152`](src/backend/background.py:152)
- **warn-and-continue**: [`src/backend/sanitizer.py:134,148,197,206`](src/backend/sanitizer.py:134), [`src/backend/entertainment_loop.py:72,80,110`](src/backend/entertainment_loop.py:72), [`src/backend/engine_plot.py:56,83,141,160`](src/backend/engine_plot.py:56)
- **Repository層**: [`src/backend/database/repo_plot.py:180,311`](src/backend/database/repo_plot.py:180), [`src/agents/writing.py:546`](src/agents/writing.py:546), [`src/agents/erotic_integrity.py:1520`](src/agents/erotic_integrity.py:1520), [`src/llm/model_router.py:74`](src/llm/model_router.py:74), [`src/core/llm_gateway.py:466`](src/core/llm_gateway.py:466)
- **print文**: [`src/backend/workflows/plot_expansion_workflow.py:19`](src/backend/workflows/plot_expansion_workflow.py:19), [`src/backend/database/core.py:309`](src/backend/database/core.py:309), [`src/backend/background.py:283`](src/backend/background.py:283), [`src/shared/circuit_breaker.py:41,53,65,70`](src/shared/circuit_breaker.py:41)

### 2.3 ログ基盤の状態

- [`config/logging_config.py`](config/logging_config.py) に `setup_logging()` が存在
- [`src/backend/server.py:35`](src/backend/server.py:35) で初期化済み
- 一方、[`src/shared/circuit_breaker.py`](src/shared/circuit_breaker.py) は `print` で状態遷移を出力
- [`src/backend/background.py:283`](src/backend/background.py:283) の `BackgroundReporter.report()` は `print` で代用

## 3. 実装フェーズ

### フェーズ1（即時・1コミット）：クリティカルバグ修正

#### 1.1 `PlotService` 引数不一致の修正
- **対象**: [`src/backend/engine.py:44`](src/backend/engine.py:44)
- **現状**: `PlotService(repo=repo, llm=llm)` を呼んでいるが [`src/services/plot_service.py:9`](src/services/plot_service.py:9) は `__init__(self, repo: IRepository)` のみ
- **修正**: `llm=llm` 引数を削除（PlotService 内部で `self.repo` 経由でアクセスする設計）
- **検証**: `pytest tests/unit/test_container.py -k test_all_providers_resolved` が PASS

#### 1.2 `connection_kernel.py` の相対import修正
- **対象**: [`src/kernels/connection_kernel.py:7-8`](src/kernels/connection_kernel.py:7)
- **現状**: `from ..shared.network import NetworkUtils` → `src/kernels/` から見て `src/shared/` への相対importは範囲外
- **修正**: `from src.shared.network import NetworkUtils` 等の絶対importに置換
- **検証**: `python -c "from src.kernels.connection_kernel import ConnectionKernel"` が成功

#### 1.3 `DialogueManager` の未実装問題
- **対象**: [`src/kernels/dialogue.py`](src/kernels/dialogue.py) + [`src/kernels/__init__.py:11`](src/kernels/__init__.py:11)
- **現状**: `DialogueManager` が `__init__.py` で export されているがクラスが存在しない
- **修正**: `DialogueManager` クラスを `dialogue.py` に新規追加（最低限のスタブ実装）
- **検証**: `pytest tests/unit/test_infra_container.py` が ImportError なく collect できる

#### 1.4 設定モデル名の不整合
- **対象**: [`tests/test_config.py:47`](tests/test_config.py:47)
- **現状**: 期待値 `'gemini-3.1-flash-lite'` vs 実際 `'gemini-3.5-flash-lite'`
- **修正**: 設定値側を期待値に合わせる、または期待値を実装に合わせる（後者を推奨：コメントに依存関係を明記）
- **検証**: `pytest tests/test_config.py` が PASS

#### 1.5 `plot_service.update_plot_blueprint` の引数順整合
- **対象**: [`src/services/plot_service.py:18`](src/services/plot_service.py:18) と [`src/backend/database/repositories/plot.py:308`](src/backend/database/repositories/plot.py:308)
- **現状**: `services` 側は `update_plot_blueprint(self, branch_id, ep_num, blueprint)`、`repositories/plot.py` も同じシグネチャ。`protocols.py` と `repo_inmemory.py` は `update_plot_blueprint(self, book_id, blueprint)` で**不一致**
- **修正**: `protocols.py` および `repo_inmemory.py` を `branch_id, ep_num, blueprint` シグネチャに統一
- **検証**: `python -c "from src.backend.database.repo_protocols import IRepository; print(IRepository.update_plot_blueprint)"` で整合確認

### フェーズ2（短期）：エラー握り潰し根絶

#### 2.1 エラー握り潰し箇所の可視化ルール
- **`except Exception:` 直下の `pass` / 黙殺を禁止** するヘルパー `log_and_reraise()` を `src/core/error_handling.py` に新設
- 既存の `except Exception: pass` 箇所を順次置換（少なくともログ＋tracebackを出力）
- 該当箇所:
  - [`src/backend/database/core.py:112,174,338,373`](src/backend/database/core.py:112) → SQLite接続close時の実害は無いが、ログ追加
  - [`src/backend/routers/tasks.py:26,62,86`](src/backend/routers/tasks.py:26) → Redis取得失敗のフォールバック、ログ追加
  - [`src/backend/background.py:152`](src/backend/background.py:152) → Redis停止確認失敗のフォールバック、ログ追加

#### 2.2 print文の logger 化
- [`src/shared/circuit_breaker.py:41,53,65,70`](src/shared/circuit_breaker.py:41) → `logger.warning` に変更
- [`src/backend/background.py:283`](src/backend/background.py:283) → `BackgroundReporter` に `logging` フォールバック追加
- [`src/backend/workflows/plot_expansion_workflow.py:19`](src/backend/workflows/plot_expansion_workflow.py:19) → `logger.debug` 化（既存コメントアウト済みdebug printも除去）

#### 2.3 `except Exception` の具体化
- 影響範囲が広い（253件）ため、以下の方針で優先順位付け：
  - **P0**: 本番パスのクリティカル箇所（`server.py`, `tasks.py`, `engine.py`）
  - **P1**: データ整合性に関わる箇所（`repo_*.py`, `database/core.py`）
  - **P2**: 補助的な箇所（マイグレーション、サニタイザ等）

### フェーズ3（中期）：観測性の強化

#### 3.1 構造化ログの確認
- [`config/logging_config.py`](config/logging_config.py) に `setup_logging()` が既に存在
- 開発環境で TRACE_ID / リクエストパスがJSONログに含まれることを保証
- 検証: `pytest tests/test_structured_logging.py` で構造化ログのスキーマ確認

#### 3.2 失敗時のトレース情報付与
- [`src/core/observability.py`](src/core/observability.py) の `with_trace_context` デコレータが既に存在
- 既存の `except Exception` 箇所すべてに `trace_id` をログに含める

### フェーズ4（中期）：テスト品質向上

#### 4.1 既存テスト修正
- 上記 1.1〜1.4 の修正に連動して、関連するテストを全て PASS させる
- `pytest tests/unit/ --ignore=tests/unit/test_infra_container.py` が 100% PASS することを目標

#### 4.2 デバッグ用テストの追加
- `tests/debug/test_error_logging.py` を新規作成
- `except Exception: pass` パターンを含む関数について、`caplog` でログが出力されることを確認

## 4. 実行順序

1. フェーズ1 を実施（1.1→1.2→1.3→1.4→1.5）
2. 各修正後に対応するテストを実行し、PASS を確認
3. フェーズ2 のコア部分（2.1 ヘルパー導入）を実施
4. フェーズ2.2, 2.3 を順次適用（影響範囲の小さい順に）
5. フェーズ3 で観測性を確認
6. フェーズ4 でテスト整備

## 5. 検証基準

| 項目 | 基準 |
|------|------|
| テスト合格率 | `pytest tests/unit/ --ignore=tests/unit/test_infra_container.py` で 100% PASS |
| Import エラー | `python -c "from src.backend.server import app"` 成功 |
| エラー握り潰し | `grep -rn "except Exception:" src/ \| grep -v test_` のうち `pass` のみが減少し、各箇所でログ出力が存在 |
| print文 | `grep -rn "print(" src/ \| grep -v test_` のうち デバッグ用の裸 print がゼロ |

## 6. リスクと緩和策

- **リスク**: 1.5 の引数順修正は `protocols.py` の利用箇所に影響する
- **緩和**: `grep -rn "update_plot_blueprint" src/` で全利用箇所を事前に確認し、シグネチャを揃える
- **リスク**: フェーズ2 で握り潰しを変えると、これまで隠れていたエラーが顕在化する
- **緩和**: 握り潰し変更時はコミット単位で全テスト実行し、リグレッションを即座に検知

## 7. 成功時のゴール

- 全テストが PASS し、`except Exception: pass` のような**握り潰しが一切存在しない**コードベース
- 失敗時に必ずログ + トレースID が出力され、運用時に根本原因まで 5 分以内に到達可能
- CI で `pytest` が緑になり、リグレッションが自動検出される

---

*作成日: 2026-08-10*
