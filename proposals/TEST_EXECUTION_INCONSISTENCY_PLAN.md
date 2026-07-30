# テスト／実行時の不整合を解消する実装計画書

- 作成日: 2026-07-16
- 対象リポジトリ: `autonovel` (kaku-hegemony v3.0.0)
- 目的: ローカル・CI・pre-commit の各実行経路の不整合、およびテストと実装のインターフェース乖離を解消し、全域テストが安定して green になる状態を確立する。

---

## 1. 現状認識（計測結果）

### 1.1 テスト実行結果（ローカル `pytest`）

| 項目 | 値 |
| --- | --- |
| 収集数 | 882 |
| 全体実行 (`pytest`) | **50 failed / 823 passed / 8 skipped / 1 error** (109.6s) |
| 単体のみ (`tests/unit`) | 255 passed / 4 skipped (67.3s) — green |

> 単体テスト群は通過するが、`tests/` 全体では 50 件が失敗。CI が一部経路しか実行していないため、失敗が**発見されないまま放置**されている。

### 1.2 実行経路ごとのテスト対象の不一致

| 実行経路 | 対象 | 乖離 |
| --- | --- | --- |
| `pytest.ini` (`testpaths=tests`) | `tests/**` | ルート直下の `test_*.py` 6 ファイルを**収集しない**（`testpaths` で制限） |
| pre-commit `pytest-unit` | `tests/unit` のみ | `tests/` 配下の結合・E2E・UI・state が未カバー |
| CI `unit-test` | `tests/unit` のみ | 同上 |
| CI `integration-test` | `tests/integration` + `tests/test_vector_store_lifecycle.py` のみ | `tests/integration` 以外の `tests/test_*.py`（商用E2E等）が未カバー |
| ルート直下 `test_*.py` 6個 | （どこからも実行されない） | 完全に孤立。`test_api.py` は collection error（接続先サーバ不足） |

### 1.3 失敗テストの分類（根因別）

根因別に 4 クラスターに集約される。

#### A. 実装・テスト間のAPI仕様乖離（恒常的失敗）

- `tests/test_structured_logging.py`（4件）
  - `StructuredLogger` (`src/core/observability.py:33`) が `extra` 辞書前提で実装されているが、テストは `logger.info(msg, book_id=...)` のような **kwargs 呼び出し**を期待。
  - エラー: `TypeError: Logger._log() got an unexpected keyword argument 'book_id'`
- `tests/test_trace_context.py::test_trace_context_isolation`
  - `TraceContext` (`src/core/observability.py:8`) が **クラス変数（プロセスグローバル）** で実装されているが、テストは **非同期タスク間の独立性（コンテキストローカル）** を期待。
  - エラー: `AssertionError: assert 'trace-ccc' == 'trace-aaa'`
- `tests/test_episode_writer.py::test_write_fallback_mode`
  - `WritingAgent.__init__` (`src/services/episode_writer.py:18`) が `PromptManager` を要求していないのに、実行時ログが `PromptManager is not injected into WritingAgent` で fallback する。DI契約の不整合。
- `tests/test_narrative_engineering.py::test_narrative_logic`
  - `NameError`：参照シンボル未定義。実装側の未定義参照 or テスト側の stale import。

#### B. 実行順序・グローバル状態依存（Flaky・全体実行時のみ失敗）

- `tests/unit/test_connection_kernel.py`（2件）
  - **単独実行では pass**、全体実行時のみ fail。グローバル／モジュール状態のリークが原因。
- `tests/test_scene_continuity_tracker.py`（8件）・`tests/test_continuity_tracker.py`（1件）
  - 同様に状態汚染の疑いが強い。

#### C. DI／設定コンテナの不整合

- `tests/test_backend/test_engine.py::test_engine_init_properties`（10件、parametrize）
  - エンジンの初期化プロパティ期待値と実装乖離。
- `tests/test_api_integration.py`（4件）
  - APIエンドポイントとテストクライアントの期待不一致。
- `tests/test_commercial_*.py`（3件）・`tests/test_background_worker.py`（1件）
  - パイプラインのDI/設定不整合。
- `tests/test_phase4to5_e2e.py`・`tests/test_quality_scorer.py` 等：E2E 経路の契約不一致。

#### D. UIレイヤ・CORS・モックfixture不整合

- `tests/ui/test_controllers.py`（2件）・`tests/ui/test_event_bus.py`（2件）
  - `AttributeError`：コントローラ/イベントバスの属性不一致。
- `tests/ui/test_api_client_mock.py`（1件: collection ERROR）
  - fixture解決失敗。
- `tests/test_cors_endpoints.py::test_health_cors_header`
  - CORSヘッダ期待不一致。

### 1.4 その他の構造的問題

- **`.coverage` / `huey.db` / `*.db-wal` 等の実行時成果物がリポジトリに混入**（gitignoreの不備）。
- ルート直下の `test_*.py` 6 ファイルがどこからも実行されず腐敗させるテスト資産。
- `pytest.ini` のみに `asyncio_mode = auto` / `function` スコープ設定。CI・pre-commit もそれに依存しているが明示的に共有されていない。
- CI の lint/typecheck が `continue-on-error: true`（非ブロッキング）で、新規債務は変更ファイル gate で止めているが、テスト全体は `tests/unit` 限定のため、テスト階層の乖離が放置されている。

---

## 2. 解消方針

1. **実行経路の標準化**：`pytest.ini` を唯一の真実のソースとし、CI・pre-commit も同じスコープ・マーカー体系に追従させる。
2. **テスト階層の再編**：`tests/` 直下に散在する `test_*.py` を `unit/integration/e2e/ui` 配下へ整理。ルートの孤立 `test_*.py` を廃棄または移設。
3. **実ロジックの修正**：実装を正とするかテストを正とするかを仕様に照らして判定し、乖離している側を整合させる（A/D クラスター）。グローバル状態は `contextvars` 化等でローカライズ（B クラスター）。
4. **CI ゲートの段階強化**：全レイヤを即ブロッキング化せず、Phase ごとに gate を強化。
5. **成果物 Playing の排除**：`.coverage`/DBファイル等を gitignore に追加し、CI アーティファクト化。

---

## 3. 実装フェーズ

### Phase 0 — 計測と基準の確立（0.5d）

- [ ] `pytest -q --junitxml=baseline.xml` で全失敗リストを XML 化し、CI の act/fail の基準ファイルとして `tests/baseline/` に固定。
- [ ] `pytest --collect-only` で 882 件の収集元一覧を `tests/inventory.md` に出力（ルート `test_*.py` が未収集であることを文書化）。
- [ ] `.gitignore` に `.coverage*`, `*.db`, `*.db-wal`, `*.db-shm`, `huey.db`, `coverage.xml` を追加し、既存混入物を `git rm --cached`。

**完了条件**: 不整合が数値化され、成果物汚染が解消。

---

### Phase 1 — 実行設定の標準化（1d）

#### 1.1 pytest 設定の一本化

- [ ] `pyproject.toml` に `[tool.pytest.ini_options]` を追加し、`pytest.ini` の内容を統合して `pytest.ini` は削除（設定散在の解消）。
- [ ] マーカーを定義: `unit`, `integration`, `e2e`, `ui`, `slow`。`addopts = "--strict-markers -ra"`。
- [ ] `testpaths` を `tests` のみとし、**ルート直下 `test_*.py` を収集しない構成を明示**（後述の Phase 2 で移設）。
- [ ] `asyncio_mode = auto` は維持しつつ、`filterwarnings` で既存非ブロッキング警告を `ignore` 明示。

#### 1.2 CI/pre-commit の追従

- [ ] CI `unit-test` を `pytest -n auto tests/unit -m "not slow" --cov --junitxml=unit.xml` に明示化（現状と同等だが marker gate）。
- [ ] CI `integration-test` に `tests/e2e` を追加し、`-m "integration or e2e"` で実行。chroma/redis service は維持。
- [ ] CI に **`full-test`** ジョブ（warning・順序依存検出用、`continue-on-error`）を追加: `pytest tests -p randomly -q` で順序無依存性を監視（`pytest-randomly` を dev 依存に追加）。
- [ ] pre-commit `pytest-unit` の `entry` を `pytest -m "unit and not slow"` に変更（marker準拠）。

**完了条件**: `pytest` 単体・CI 両経路の対象が `pyproject.toml` で宣言通りに一致。

---

### Phase 2 — テスト階層の統合と腐敗ファイルの整理（1d）

- [ ] ルート直下の孤立 `test_*.py` 6 ファイルを処分判定:
  - `test_api.py` / `test_db.py` / `test_db_lock.py`: `tests/integration/` 配下へ移設 or `archive/` へ退避（重複機能は統合）。
  - `test_exact_scenario.py` / `test_manual_sharp_edge.py` / `test_new_sharp_edge.py`: `tests/e2e/` 新設へ移設。
- [ ] `tests/` 直下の `test_*.py`（`test_structured_logging.py` 等 30+ 件）を `tests/unit`/`tests/integration` へ分類移動（marker 付与）。移動は rename commit で diff を最小化し、後続 Phase の修正箇所を特定しやすくする。
- [ ] `tests/test_backend/`, `tests/ui/`, `tests/state/` は既存構成を維持（Phase 3 で順次修正）。

**完了条件**: `git ls-files 'test_*.py'` がルートに 0 件。`pytest --collect-only` が `tests/` 配下のみから収集。

---

### Phase 3 — 実装乖離の修正（A/D クラスター）（2d）

#### 3.1 構造化ロガー（`src/core/observability.py`）

- [ ] `StructuredLogger` を **kwargs 受け対応**に拡張: `def info(self, msg, **kwargs)` → `kwargs` を `extra` 辞書にマージ（`book_id`, `kernel` 等を許容）。
- [ ] 既存の `extra=` 辞書呼び出しパスを維持（後方互換）。
- [ ] テスト `tests/test_structured_logging.py` の期待（4件）に対して実装が整合することを確認。

#### 3.2 TraceContext のコンテキストローカル化

- [ ] `TraceContext._current_trace_id` をクラス変数から **`contextvars.ContextVar`** に移行。
- [ ] `set_trace_id` / `get_trace_id` / `clear` を ContextVar ベースに変更。非同期タスク間で独立保持されることを保証。
- [ ] `tests/test_trace_context_isolation` を green に。
- [ ] 呼び出し側（`src/backend/tasks.py`, `server.py`, `engine_style_rag.py` 等）の import/振る舞いが変わらないことを確認（API互換）。

#### 3.3 WritingAgent / PromptManager DI契約の整合

- [ ] `src/services/episode_writer.py` の `WritingAgent.__init__` に `prompt_manager` を注入可能にするか、fallback 分岐の契約をテストと一致させる。
- [ ] `tests/test_episode_writer.py::test_write_fallback_mode` が期待する「DI未注入時のフォールバック動作」を実装側で明示契約化。
- [ ] `tests/test_narrative_engineering.py::test_narrative_logic` の `NameError` を解消（未定義参照の修正 or テストの stale import 更新）。

#### 3.4 UI/CORS/モックfixture

- [ ] `tests/ui/test_controllers.py`, `test_event_bus.py`: `AttributeError` の参照属性を実装側に追加するか、テスト期待を正しく修正。
- [ ] `tests/ui/test_api_client_mock.py` の collection ERROR を fixture 定義から解消。
- [ ] `tests/test_cors_endpoints.py::test_health_cors_header`: CORS ミドルウェア設定と期待ヘッダの整合。

**完了条件**: A/D クラスターの全失敗テストが単独・全体両実行で green。

---

### Phase 4 — 実行順序依存の解消（B クラスター）（1.5d）

- [ ] `tests/unit/test_connection_kernel.py` を起点に、グローバル状態を保持するモジュールを特定（setting/キャッシュ/シングルトン）。
- [ ] 該当モジュールに `reset()` フィクスチャを追加し、`tests/conftest.py` の `autouse` fixture で各テスト前に状態リセット。
- [ ] `tests/test_scene_continuity_tracker.py`（8件）・`test_continuity_tracker.py` について同様に状態リーク箇所を特定・隔離。
- [ ] `pytest-randomly` を CI `full-test` ジョブに導入（Phase 1 で追加済）し、順序無依存を機械的に担保。

**完了条件**: `pytest -p randomly` で全 `tests/` を 3 回連続 green。

---

### Phase 5 — 残存DI/エンジン/API契約の修復（C クラスター）（1.5d）

- [ ] `tests/test_backend/test_engine.py::test_engine_init_properties`（parametrize 10件）: エンジン初期化プロパティの期待値を `src/backend/engine.py`（該当実装）に照合し乖離を解消。
- [ ] `tests/test_api_integration.py`（4件）: FastAPI エンドポイント契約（`src/backend/routers/`）とテストクライアントの整合。
- [ ] `tests/test_commercial_*.py`（3件）・`tests/test_background_worker.py`: パイプライン DI/設定の契約整合。
- [ ] `tests/test_phase4to5_e2e.py` / `test_quality_scorer.py` / `test_cors_*.py`: E2E/品質評価/CORS 経路の契約不一致を個別解消。

**完了条件**: C クラスター全失敗が green。`pytest tests/` 全体で 880+ passed / 0 failed。

---

### Phase 6 — CI ゲートの段階強化（0.5d）

- [ ] Phase 3-5 完了後、CI `unit-test`/`integration-test` を **ブロッキング化**（`continue-on-error` 削除）。
- [ ] CI `full-test`（順序無依存検出）を `continue-on-error: true` のままで残し、flaky 監視を継続。
- [ ] pre-commit `pytest-unit` が green であることを `pre-commit run --all-files` で確認。
- [ ] `docs/ci_gates.md` に「新規コードの gate / 既存債務の扱い / 順序無依存監視」を文書化。

**完了条件**: 失敗テストが再発した場合に CI が即ブロックする状態。CI ドキュメント整備。

---

## 4. リスクと対策

| リスク | 影響 | 対策 |
| --- | --- | --- |
| TraceContext の contextvars 化で既存呼び出し経路が破損 | 監査ログ・タスクキューの trace 伝播 | API互換を維持し、`src/backend/` 配下を grep で網羅確認 |
| テスト移動が git history を複雑化する | blame 追跡困難 | rename commit で移動を単独化（`git mv`） |
| 順序無依存化の副作用で新たな状態依存露出 | 追加の flaky 発生 | Phase 4 は Phase 1 の random 実行ジョブと並行検証 |
| CI 全域化で実行時間増大 | PR サイクル悪化 | unit/integration/full ジョブ分離で並列実行 |

---

## 5. 受入基準（Definition of Done）

1. `pytest` をルートで実行し、`0 failed / 0 error / 880+ passed` が**3 回連続**で安定。
2. `pytest -p randomly` で順序を変えても全件 green。
3. CI（`unit-test`, `integration-test`）がブロッキング状態で main ブランch 上で緑。
4. `git ls-files 'test_*.py'` がルート直下で 0 件。
5. `.coverage`, `*.db`, `*.db-shm/wal` が git 管理外（`git status` で未追跡）。
6. `pre-commit run --all-files` が exit 0。
7. `docs/ci_gates.md` が整備され、実行経路の不整合が再発しない運用面が描かれている。

---

## 6. スケジュール概算

| Phase | 工数 | 前提 |
| --- | --- | --- |
| Phase 0 | 0.5d | なし |
| Phase 1 | 1.0d | Phase 0 |
| Phase 2 | 1.0d | Phase 1 |
| Phase 3 | 2.0d | Phase 2 |
| Phase 4 | 1.5d | Phase 3 |
| Phase 5 | 1.5d | Phase 4 |
| Phase 6 | 0.5d | Phase 5 |
| **合計** | **8.0d** | |

---

## 7. 関連ファイル（主要な変更対象）

- 設定類: `pytest.ini` → `pyproject.toml`, `.gitignore`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`
- 実装: `src/core/observability.py`, `src/services/episode_writer.py`, `src/backend/engine.py`, `src/backend/routers/`, `src/core/audit_logger.py`
- テスト: `tests/conftest.py`, `tests/test_structured_logging.py`, `tests/test_trace_context.py`, `tests/ui/`, `tests/state/`, `tests/integration/conftest.py`, ルート直下 `test_*.py` 6 件

---

## 8. 備考

- Phase 3.2（TraceContext contextvars 化）は本件の中で最も影響範囲が大きく、かつ仕様上の「正」がテスト側（非同期独立性）にある点に注意。実装側をテスト期待に寄せる方針とする。
- CI の `continue-on-error` は「非ブロッキング債務追跡」設計であり、本計画はそれを維持しつつ新規 gate を機能させる前提。Phase 6 でテスト保持率が安定次第、段階的にブロッキング化する。
- 本計画は `IMPLEMENTATION_PLAN.md` / `IMPLEMENTATION_PLAN_48_STEPS.md`（既存構想）の前提となる「テスト基盤の健全性」を担保するものであり、上記既存計画と競合しない。
