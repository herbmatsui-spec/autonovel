# 案1: CI 多重ゲート化 実装計画書

## 1. 目的

現状の `.github/workflows/ci.yml` は **ガードが緩く、リファクタリングのリグレッションをマージ前に止められない**。

| 現状の問題 | 影響 |
|---|---|
| `mypy src --ignore-missing-imports \|\| true` | 型エラーが CI で fail しない(警告止まり) |
| `pytest ... --cov-fail-under=20` | カバレッジゲートが事実上無効(pyproject.toml は 80% を要求) |
| `tests/contract/`・`tests/perf/` が CI で実行されない | スキーマ変更・性能劣化を検出できない |
| `alembic check` / モデル↔マイグレーション整合テストが無い | マイグレーション忘れ/モデル定義忘れを検出できない |
| `black --check` が `pyproject.toml` 未設定でデフォルト 88 | ruff(line-length 100)と衝突し formatter が fail する事故リスク |
| `lint-and-typecheck` 1ジョブに密結合 | 1つの失敗で他が分からない、所見時間が長い |
| `frontend-test` が CI に存在しない | フロントの回帰を CI で検出できない |
| `.pre-commit-config.yaml` の `mypy` が `--ignore-missing-imports` | ローカルでも型が緩い |
| `Makefile` の `verify` ターゲットと CI が乖離 | PR 前チェックと CI チェックが一致しない |

本計画ではこれらを解消し、**「CI を多重ゲートの検問所にする」**ことで、大規模リファクタ時のリグレッション検出力を強化する。

---

## 2. ゴール / 非ゴール

### ゴール

1. CI を 7ジョブに分割し、各ジョブが独立に fail できる構造にする。
2. すべてのゲートがローカル (`make verify` / pre-commit) と CI で同じ閾値・同じコマンドを使う。
3. 既存の `tests/contract/`・`tests/perf/` を CI に組み込み、スキーマ/性能のリグレッションを検出する。
4. mypy を **strict 化**(段階的に)し、CI で fail させる。
5. alembic ↔ ORM の往復整合テストを CI に追加する。
6. フロントエンドテスト(vitest)を CI に追加する。
7. 段階的にカバレッジ閾値を 20→40→60→80% と引き上げるロードマップを提示する。

### 非ゴール(本計画では扱わない)

- 個別のテストケース追加(案3「的を絞ったカバレッジ向上」で扱う)
- 契約テスト・スナップショットテストの中身整備(案2で扱う)
- LLM 出力 JSON-schema バリデーション(案2で扱う)
- `pyproject.toml` の依存関係の統一(別タスク)

---

## 3. アーキテクチャ(after)

```
PR / push ──┬──► lint              (ruff check + ruff format --check)
            ├──► typecheck         (mypy src --strict-fail)
            ├──► test-unit         (pytest tests/unit, --cov-fail-under=40 段階引き上げ)
            ├──► test-integration  (pytest tests/integration, PG+Redis サービス)
            ├──► test-contract     (pytest tests/contract, OpenAPI スナップショット比較)
            ├──► test-perf         (pytest tests/perf --benchmark-compare、ベースライン比較)
            ├──► test-migration    (alembic upgrade↔downgrade 往復 + alembic check)
            └──► frontend-test     (npm run test:ci + lint + typecheck)
                                  │
                                  ▼
                          build (main のみ)
```

- 各ジョブは **独立に fail 可能**(`needs` を持たせず fan-out)
- `test-unit` と `test-integration` は DB 依存の有無で分割(統合はサービスコンテナ必須、単体は不要)
- すべてのジョブで **キャッシュ**(pip / node_modules)を効かせる
- PR コメントに **カバレッジ差分**(coverage.py の `--cov-report=xml` + `diff-cover` または `github-action-report-lcov`)を表示

---

## 4. フェーズ分割

| Phase | 内容 | 期間目安 | リスク |
|---|---|---|---|
| **Phase 1** | CI のジョブ分割 + ローカル/CI 統一(黒 formatter 衝突解消含む) | 1〜2日 | 低 |
| **Phase 2** | contract / perf / migration ジョブ追加 + frontend-test 追加 | 2〜4日 | 中 |
| **Phase 3** | mypy strict 化(段階導入)+ カバレッジ閾値引き上げ | 1〜2週間 | 高(エラー大量発生時の対応) |
| **Phase 4** | 観察・調整(キャッシュ/並列度/失敗時のログ整備) | 継続 | 低 |

---

## 5. Phase 1 詳細: CI ジョブ分割 + ローカル統一

### 5.1 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `.github/workflows/ci.yml` | 全面書き換え(下記テンプレート) |
| `pyproject.toml` | `[tool.black]` セクション追加(line-length 100, target-version py312) |
| `Makefile` | `verify` ターゲットを新ジョブ構成と一致させる |
| `run_tests.sh` | mypy から `\|\| true` を削除、black check を維持 |

### 5.2 `.github/workflows/ci.yml` テンプレート(差分イメージ)

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

# PR では同時実行上限を緩和
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # ----------------------------------------------------------------------
  # 1. Lint (ruff + ruff format --check)
  # ----------------------------------------------------------------------
  lint:
    name: Lint (ruff)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[dev]"
      - run: ruff check src tests
      - run: ruff format --check src tests

  # ----------------------------------------------------------------------
  # 2. Type check (mypy, strict 化は Phase 3)
  # ----------------------------------------------------------------------
  typecheck:
    name: Type Check (mypy)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[dev]"
      # Phase 1: ignore_missing_imports は残しつつ strict=false を維持
      # Phase 3 で strict 化(下記メモ)
      - name: mypy
        run: mypy src --ignore-missing-imports
        # Phase 3 で `|| true` を削除し fail させる

  # ----------------------------------------------------------------------
  # 3. Unit tests + coverage gate
  # ----------------------------------------------------------------------
  test-unit:
    name: Unit Tests (coverage gate)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[dev]"
      # Phase 1 開始値: 40% (現状 ~25% から段階引き上げ)
      # pyproject.toml の fail_under=80 と揃えるのは Phase 3 末
      - name: pytest tests/unit
        run: |
          pytest tests/unit \
            --cov=src --cov-report=xml --cov-report=term-missing \
            --cov-fail-under=40
      - uses: actions/upload-artifact@v4
        with:
          name: coverage-unit
          path: coverage.xml

  # ----------------------------------------------------------------------
  # 4. Integration tests (PostgreSQL + Redis サービス)
  # ----------------------------------------------------------------------
  test-integration:
    name: Integration Tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: autonovel_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U test"
          --health-interval 10s --health-timeout 5s --health-retries 5
      redis:
        image: redis:7
        ports: ["6379:6379"]
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[dev]"
      - name: alembic upgrade
        run: |
          cd src/backend
          alembic upgrade head
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/autonovel_test
      - name: pytest tests/integration
        run: pytest tests/integration -v --tb=short
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/autonovel_test
          REDIS_URL: redis://localhost:6379/0

  # ----------------------------------------------------------------------
  # 5. Contract tests (Phase 2 で実装)
  # ----------------------------------------------------------------------
  test-contract:
    name: Contract Tests
    runs-on: ubuntu-latest
    needs: [lint, typecheck]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[dev]"
      - name: pytest tests/contract
        run: pytest tests/contract -v --tb=short

  # ----------------------------------------------------------------------
  # 6. Performance regression tests (Phase 2 で実装)
  # ----------------------------------------------------------------------
  test-perf:
    name: Performance Regression
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test; POSTGRES_PASSWORD: test; POSTGRES_DB: autonovel_test
        ports: ["5432:5432"]
        options: --health-cmd "pg_isready -U test" --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[dev]"
      - name: pytest tests/perf
        # ベースライン比較は pytest-benchmark の --benchmark-compare を使用
        run: |
          pytest tests/perf -v \
            --benchmark-only \
            --benchmark-columns=mean,stddev,median \
            --benchmark-autosave

  # ----------------------------------------------------------------------
  # 7. Migration integrity (alembic check + 往復)
  # ----------------------------------------------------------------------
  test-migration:
    name: Migration Integrity
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test; POSTGRES_PASSWORD: test; POSTGRES_DB: autonovel_test
        ports: ["5432:5432"]
        options: --health-cmd "pg_isready -U test" --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[dev]"
      - name: alembic upgrade head
        run: |
          cd src/backend
          alembic upgrade head
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/autonovel_test
      - name: alembic check (model drift detection)
        run: |
          cd src/backend
          alembic check
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/autonovel_test
      - name: alembic round-trip (downgrade -1 -> upgrade head)
        run: |
          cd src/backend
          alembic downgrade -1
          alembic upgrade head
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/autonovel_test

  # ----------------------------------------------------------------------
  # 8. Frontend tests (vitest)
  # ----------------------------------------------------------------------
  frontend-test:
    name: Frontend Tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm run test:ci

  # ----------------------------------------------------------------------
  # 9. Build (main push のみ)
  # ----------------------------------------------------------------------
  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: [lint, typecheck, test-unit, test-integration, test-contract, frontend-test]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t autonovel:latest .
      - run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker tag autonovel:latest ${{ secrets.DOCKER_REGISTRY }}/autonovel:${{ github.sha }}
          docker push ${{ secrets.DOCKER_REGISTRY }}/autonovel:${{ github.sha }}
```

### 5.3 `pyproject.toml` への追加

```toml
[tool.black]
line-length = 100
target-version = ["py312"]
```

### 5.4 `Makefile` の `verify` ターゲット更新

```makefile
verify: lint typecheck test-unit test-contract test-migration frontend-test  ## PR 前のフル検証
	@echo "All checks passed."
```

(必要に応じて `test-unit`, `test-contract`, `test-migration` ターゲットも個別追加)

### 5.5 `run_tests.sh` の更新

```bash
# 旧: mypy src --ignore-missing-imports || true
mypy src --ignore-missing-imports
# `|| true` を削除し、型エラーでスクリプト全体を fail させる
```

### 5.6 `.pre-commit-config.yaml` の更新

```yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v2.3.1
  hooks:
    - id: mypy
      args: [--ignore-missing-imports, src/]
      # Phase 3 で --strict を追加し、CI と pre-commit の閾値を一致させる
```

### 5.7 Phase 1 完了条件(DoD)

- [ ] `.github/workflows/ci.yml` のジョブが 7 個(lint / typecheck / test-unit / test-integration / test-contract / test-perf / test-migration / frontend-test)に分割されている
- [ ] `black --check` が CI から消え、`ruff format --check` に統一されている
- [ ] `pyproject.toml` の `[tool.black]` が `line-length = 100` で設定されている
- [ ] `mypy ... || true` が CI / `run_tests.sh` の両方から削除されている
- [ ] `Makefile` の `verify` が新ジョブと同じコマンドで構成されている
- [ ] CI で `--cov-fail-under=40` が fail 条件として機能している(現状 25.83% なので、まずテスト追加 or 閾値調整が必要)
- [ ] ローカルで `make verify` を実行すると、CI と同じ順序・同じ結果になる

---

## 6. Phase 2 詳細: contract / perf / migration / frontend-test 導入

### 6.1 test-contract ジョブ

**目的:** OpenAPI / Pydantic スキーマの意図しない変更を検出。

**必要な追加実装(案2 と連携):**

1. `tests/contract/snapshots/openapi.json` を初回生成し、リポジトリにコミット
2. `tests/contract/test_openapi_snapshot.py` を追加(下記スケッチ):

```python
"""OpenAPI スキーマのスナップショットテスト.

破壊的変更(エンドポイント削除・必須フィールド追加・型変更)を検知する。
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SNAPSHOT = Path(__file__).parent / "snapshots" / "openapi.json"


@pytest.fixture(scope="module")
def openapi_schema():
    from src.backend.server import app
    return app.openapi()


def test_openapi_matches_snapshot(openapi_schema):
    """OpenAPI 仕様がスナップショットと一致すること."""
    expected = json.loads(SNAPSHOT.read_text())
    assert openapi_schema == expected, (
        "OpenAPI 仕様がスナップショットと一致しません。\n"
        "意図的な変更の場合:\n"
        "  pytest tests/contract/test_openapi_snapshot.py --snapshot-update"
    )


def test_no_endpoint_removed(openapi_schema):
    """エンドポイントの削除を検知."""
    expected = json.loads(SNAPSHOT.read_text())
    current_paths = set(openapi_schema["paths"].keys())
    baseline_paths = set(expected["paths"].keys())
    removed = baseline_paths - current_paths
    assert not removed, f"エンドポイントが削除されました: {removed}"
```

3. `pytest --snapshot-update` でスナップショットを更新できる仕組みを用意(`pytest-snapshot` プラグイン)。

### 6.2 test-perf ジョブ

**目的:** 性能回帰の検出。`tests/perf/benchmarks.json` の閾値ベースラインからの劣化を遮断。

**必要な追加実装:**

1. `pytest-benchmark` を `pyproject.toml` の `dev` 依存に追加:
   ```toml
   dev = [
       ...
       "pytest-benchmark>=4.0",
   ]
   ```
2. `tests/perf/test_performance_regression.py` を `--benchmark-compare` 付きで実行可能に拡張。
3. CI で `pytest-benchmark` が `benchmarks.json` の値をベースラインとして比較するように設定。
4. 閾値は `benchmarks.json` の `thresholds_ms` を上限として、超えたら fail。

### 6.3 test-migration ジョブ

**目的:** マイグレーションと ORM モデルの乖離検出、往復整合性確認。

**実装:**

1. `alembic check` を CI で実行 → モデルと最新マイグレーションのスキーマ差分を検出。
2. `alembic downgrade -1 && alembic upgrade head` の往復で全マイグレーションが可逆であることを検証。
3. 失敗時は「該当リビジョンの `downgrade()` が未実装/壊れている」と表示。

### 6.4 frontend-test ジョブ

**目的:** React/Vite フロントの回帰を CI で検出。

**実装:**

1. `frontend/package.json` の `scripts` に `lint`, `typecheck`, `test:ci` が揃っているか確認(揃っていれば `npm ci` → 3コマンド実行するだけ)。
2. キャッシュ:`actions/setup-node@v4` の `cache: npm` + `cache-dependency-path: frontend/package-lock.json`。

### 6.5 Phase 2 完了条件(DoD)

- [ ] `tests/contract/snapshots/openapi.json` がリポジトリにコミットされている
- [ ] `pytest tests/contract` が CI で実行され、スナップショット差分で fail する
- [ ] `pytest tests/perf --benchmark-only --benchmark-autosave` が CI で実行され、ベースラインからの劣化で fail する
- [ ] `alembic check` が CI で成功する(モデルとマイグレーションが一致)
- [ ] `alembic downgrade -1 && upgrade head` が CI で成功する
- [ ] `frontend-test` ジョブが CI で成功する
- [ ] `Makefile` に個別ターゲット(`test-contract`, `test-perf`, `test-migration`)が追加されている

---

## 7. Phase 3 詳細: mypy strict 化 + カバレッジ閾値引き上げ

### 7.1 mypy strict 化ロードマップ

`# type: ignore` 多用・`type: ignore[misc]` だらけの現状でいきなり `--strict` は現実的でない。**段階導入**:

| Step | pyproject.toml | 効果 |
|---|---|---|
| 7.1.1 | `ignore_missing_imports = true` のまま `\|\| true` を削除 | 型エラーを CI で fail させる(警告から遮断に格上げ) |
| 7.1.2 | `disallow_untyped_defs = true` を追加 | 型注釈のない関数定義を禁止 |
| 7.1.3 | `warn_unused_ignores = true` を追加 | 不要な `# type: ignore` を検出 |
| 7.1.4 | `disallow_incomplete_defs = true` を追加 | 引数の型注釈漏れを禁止 |
| 7.1.5 | `no_implicit_optional = true` を追加 | `Optional[T]` を明示 |
| 7.1.6 | `warn_return_any = true` を追加 | `Any` 戻り値を警告 |
| 7.1.7 | `strict = true` に到達(最終ゴール) | strict モード完全準拠 |

各 Step 後に `mypy src` でエラー箇所を確認し、都度 `# type: ignore[xxx]` の付与 or コード修正で吸収する。

### 7.2 カバレッジ閾値引き上げロードマップ

| 期間 | `--cov-fail-under` | 目標 |
|---|---|---|
| Phase 1 開始 | 40% | 0% モジュールを 1 つずつ潰す |
| Phase 1 終了 | 50% | state_manager / resilience / event_bus / network をカバー |
| Phase 2 終了 | 60% | routers / workflows / agents を重点カバー |
| Phase 3 終了 | 80% | pyproject.toml の `fail_under=80` と完全一致 |

各段階でカバレッジが下回ったらマージ不可。**目標未達の場合は PR を reject**(リファクタのテスト追加とセット)。

### 7.3 PR コメントへのカバレッジ差分表示

```yaml
- uses: douglasdrumond/markdown-table-formatter-action@v1
- uses: codecov/codecov-action@v4
  with:
    file: coverage.xml
    flags: unit
    fail_ci_if_error: false
```

Codecov もしくは `diff-cover` を導入し、PR に「変更行は 80% 以上カバーされていないと fail」と表示。

### 7.4 Phase 3 完了条件(DoD)

- [ ] `pyproject.toml` の `[tool.mypy]` に `strict = true` が設定されている
- [ ] CI の `mypy` が `|| true` なしで実行され、型エラーが fail する
- [ ] `.pre-commit-config.yaml` の mypy が `--strict` で実行される
- [ ] `run_tests.sh` の mypy が `|| true` なしで fail する
- [ ] CI の `--cov-fail-under` が 80% で fail する
- [ ] PR コメントにカバレッジ差分が表示される
- [ ] `Makefile` の `verify` がこれらすべてを含む

---

## 8. Phase 4 詳細: 観察・調整(継続)

| 観測項目 | 対応 |
|---|---|
| CI 全体の所要時間 | ジョブ並列度見直し、キャッシュ最適化、pytest-xdist 導入検討 |
| キャッシュヒット率 | `actions/cache` の key を依存ファイル単位に細分化 |
| flake テスト | `pytest-rerunfailures` 導入 + flaky テストの個別対処 |
| mypy strict 後の新規 `type: ignore` | PR レビューで「理由コメント必須」運用 |
| カバレッジ目標未達 PR | レビューで「テスト追加 or テスト計画提示」必須化 |
| 失敗ログの可読性 | `--tb=long` を PR コメントに添付する action 追加 |

---

## 9. テスト戦略

本計画は「テストを増やす」計画ではないが、各フェーズで以下を検証する:

| Phase | 検証方法 |
|---|---|
| Phase 1 | ローカルで `make verify` → CI で同ジョブを実行 → 結果一致を確認 |
| Phase 2 | OpenAPI スナップショットを意図的に変更して CI が fail することを確認 → 戻して pass |
| Phase 2 | perf テストの閾値を意図的に低くして CI が fail することを確認 → 戻して pass |
| Phase 2 | `alembic check` がモデル変更で fail することを確認 |
| Phase 3 | mypy strict を有効化して大量エラーが出る場合、段階導入で 0 → 1 ずつ吸収 |
| Phase 3 | `--cov-fail-under` を高くして fail → テスト追加で pass を確認 |

---

## 10. リスクと緩和策

| リスク | 影響 | 緩和策 |
|---|---|---|
| mypy strict 化で大量のエラーが一度に出る | CI が常に fail、リファクタ着手不能 | Phase 3 を 7 段階に分割し、各 Step ごとにエラー数を計測・対応 |
| カバレッジ閾値引き上げで既存 PR が軒並み fail | マージ不可、開発停滞 | 閾値引き上げと「テスト追加」を同一 PR に含める運用ルール化 |
| contract スナップショットの初回生成が既存 API と乖離 | 初回コミット時に大量 diff | スナップショットを `--snapshot-update` で生成し、レビューで全差分を確認 |
| perf テストのベースラインが CI 環境で不安定 | flaky fail | 環境変数でベースライン値を調整可能に、`pytest-benchmark` の許容範囲(±20%)を設定 |
| alembic check が偽陽性 | モデル変更と関係ないマイグレーションで fail | `alembic check` の exit code を確認し、`ignore` リストの運用ルールを決める |
| GitHub Actions の無料枠消費 | 月 2000 分制限 | self-hosted runner 検討、ジョブ並列度最適化、必須ジョブのみ main/develop にトリガー |
| pre-commit と CI の閾値乖離 | ローカル pass・CI fail | Phase 1 DoD で「ローカル/CI 同値」を必須化 |

---

## 11. ロールアウト計画

### Day 1〜2: Phase 1

1. `pyproject.toml` に `[tool.black]` 追加
2. `.github/workflows/ci.yml` を新テンプレートで全面書き換え
3. `Makefile` の `verify` 更新
4. `run_tests.sh` から `|| true` 削除
5. `.pre-commit-config.yaml` の `mypy` 設定更新
6. **ブランチ: `chore/ci-multi-gate-phase1`** で作業
7. PR レビュー → main へマージ
8. CI が 7 ジョブで並列に走ることを確認

### Day 3〜6: Phase 2

1. `pytest-benchmark` を `pyproject.toml` の `dev` に追加
2. `tests/contract/snapshots/openapi.json` を初回生成・コミット
3. `tests/contract/test_openapi_snapshot.py` 実装
4. `tests/perf/test_performance_regression.py` を `--benchmark-compare` 対応に拡張
5. `tests/migration/` を新設(必要なら)し、`test_alembic_roundtrip.py` 実装
6. `frontend-test` ジョブを CI に追加
7. **ブランチ: `chore/ci-multi-gate-phase2`** で作業
8. PR レビュー → マージ

### Week 2〜3: Phase 3

1. mypy 7 段階導入(7.1.1 → 7.1.7)
2. 各段階で `mypy src` を CI から `|| true` を外して実行
3. 大量エラー時は別 PR で対応(「型修正」専用 PR を許可)
4. `--cov-fail-under` を 40 → 50 → 60 → 80 と段階引き上げ
5. Codecov または `diff-cover` を PR コメントに追加
6. **ブランチ: `chore/ci-multi-gate-phase3a`(mypy)/ `phase3b`(coverage)** で分割

### Week 4+: Phase 4

- 観察・調整の継続
- 失敗パターン分析 → flake テスト対処
- 必要に応じてジョブ並列度・キャッシュキー調整

---

## 12. 成功指標(KPI)

| 指標 | 現状 | 目標 |
|---|---|---|
| CI ジョブ数 | 3 | 7 以上 |
| CI 全体の平均所要時間 | (測定) | 10 分以内 |
| mypy strict 準拠率 | 0% | 95% 以上 |
| カバレッジ | 25.83% | 80% |
| CI の fail-through 率(検出できたリグレッション/全リグレッション) | (測定不能) | 80% 以上 |
| flake テスト率 | (測定) | 1% 以下 |
| PR レビューで「テスト追加忘れ」が指摘される頻度 | 頻発 | 月 5 件以下 |

---

## 13. 参照ファイル一覧

| ファイル | 役割 |
|---|---|
| `.github/workflows/ci.yml` | CI パイプライン定義(本計画の中心) |
| `pyproject.toml` | `[tool.mypy]` / `[tool.ruff]` / `[tool.black]` / `[tool.pytest.ini_options]` |
| `Makefile` | `verify` / `lint` / `typecheck` / `test` ターゲット |
| `run_tests.sh` | ローカル手動実行スクリプト |
| `.pre-commit-config.yaml` | pre-commit フック定義 |
| `tests/contract/test_api_contracts.py` | 既存契約テスト(本計画で CI 組み込み) |
| `tests/perf/benchmarks.json` | 性能ベースライン |
| `src/backend/alembic/env.py` | マイグレーション環境設定 |
| `frontend/package.json` | npm scripts(lint / typecheck / test:ci) |
| `REGRESSION_PREVENTION_PLAN.md` | 既存のリグレッション防止計画(本計画と整合) |
| `TEST_COVERAGE_PLAN.md` | 既存のカバレッジ向上計画(Phase 3 で参照) |

---

## 14. 次のアクション(即着手)

1. **PR 作成:** `chore(ci): multi-gate CI pipeline (Phase 1)`
   - 変更: `.github/workflows/ci.yml`, `pyproject.toml`, `Makefile`, `run_tests.sh`, `.pre-commit-config.yaml`
2. **マージ前チェック:**
   - [ ] ローカル `make verify` が新ジョブ構成で pass
   - [ ] GitHub Actions のジョブ一覧が 7 個になっている
   - [ ] `black --check` が ruff format --check に置き換わっている
   - [ ] mypy が CI で fail する(意図的にエラーを入れて確認)
3. **マージ後:** README の "Development" セクションに新 CI ジョブ構成図を追記
