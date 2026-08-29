# 継続的改善 実装計画書（24 ステップ）

対象: コードベースの信頼性・保守性向上
- CI で `ruff --check` / `mypy --strict` を失敗させる（段階的）
- pre-commit フック（ruff / isort / black）の導入と運用
- `log_exception` の開発者ガイド整備
- ドメイン固有例外クラス（`src/backend/exceptions.py`）の集約と利用

設計方針: 各ステップは **1 ファイルの作成・編集、または 1 コマンドの実行** に収め、検証コマンドも明示。
ステップ間に依存関係は最小限。順番通りに進めれば、低性能な LLM でも迷わず実装できる。

> 既存状況（調査済み）:
> - `.github/workflows/ci.yml` は存在。`lint` / `typecheck` ジョブは `continue-on-error: true`（非ブロッキング）。
>   `format-check` / `lint-new` ジョブで「変更ファイルのみ」ブロッキング化済み。
> - `.pre-commit-config.yaml` は存在（ruff / ruff-format / mypy / bandit 等）。`black` は未導入。
> - `src/backend/error_utils.py` に `log_exception` は存在。
> - `src/backend/exceptions.py` は存在しない。

---

## Phase 1: CI 強化（ステップ 1〜6）

### ステップ 1: 現在の CI 動作を文書化する
- 変更ファイル: `docs/ci_current_state.md`（新規）
- 操作: 既存 `ci.yml` の要点（非ブロッキングjobs、変更ファイルブロッキングjobs）を箇条書きで記述。
- 検証: `cat docs/ci_current_state.md` で内容を確認。
- ロールバック: ファイルを削除。

### ステップ 2: ブロッキング化ポリシー文書を作成
- 変更ファイル: `docs/ci_gate_policy.md`（新規）
- 操作: 「新規ファイルは常にブロック」「全量は ruff=0, mypy=0 でブロック化」というルールを記述。
- 検証: ファイルが存在することを確認。
- ロールバック: ファイルを削除。

### ステップ 3: 新規ファイル向け mypy ブロッキングジョブを追加
- 変更ファイル: `.github/workflows/ci.yml`
- 操作: `lint-new` ジョブの直後に以下を追加（新規 Python ファイルのみ `mypy --strict` を実行）。
```yaml
  typecheck-new:
    runs-on: ubuntu-latest
    needs: [changed-files]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
      - run: pip install -r requirements.txt mypy
      - name: Type check (mypy, changed files only)
        run: |
          FILES="${{ needs.changed-files.outputs.files }}"
          if [ -z "$FILES" ]; then
            echo "No changed Python files; skipping type check."
            exit 0
          fi
          mypy --config-file pyproject.toml --strict $FILES
```
- 検証: `yamllint .github/workflows/ci.yml` または `python -c "import yaml;yaml.safe_load(open('.github/workflows/ci.yml'))"` で構文確認。
- ロールバック: 追加したブロックを削除。

### ステップ 4: バーンダウン目標ファイルを作成
- 変更ファイル: `docs/lint_burn_down.md`（新規）
- 操作: 現在の ruff/mypy エラー数（ruff: 約1008, mypy: 約1769）と「0 になったら全量ブロック」の目標を記載。
- 検証: ファイル存在確認。
- ロールバック: 削除。

### ステップ 5: 全量ブロッキング化の手順をコメントで予約
- 変更ファイル: `.github/workflows/ci.yml`
- 操作: `lint` ジョブの `continue-on-error: true` の上にコメントを追加:
```yaml
      # バーンダウン完了後（docs/lint_burn_down.md 参照）は以下を削除しブロッキング化:
      # continue-on-error: true
```
- 検証: コメントが追加されたことを `grep "バーンタウン" .github/workflows/ci.yml` で確認（実際は「バーンダウン」）。
- ロールバック: コメントを削除。

### ステップ 6: CI ドキュメントへのリンク集約
- 変更ファイル: `README.md`（既存セクション「CI」または「開発」に追記）
- 操作: `docs/ci_current_state.md`, `docs/ci_gate_policy.md`, `docs/lint_burn_down.md` へのリンクを追加。
- 検証: `grep "ci_gate_policy" README.md`
- ロールバック: 追記を削除。

---

## Phase 2: pre-commit フック（ステップ 7〜12）

### ステップ 7: isort 設定を pyproject.toml に追加
- 変更ファイル: `pyproject.toml`
- 操作: 末尾に以下を追記。
```toml
[tool.isort]
profile = "black"
line_length = 100
known_first_party = ["src", "config", "schemas", "services", "prompts", "formatters", "models", "plugins", "kernels"]
```
- 検証: `python -c "import tomllib;tomllib.load(open('pyproject.toml','rb'))"` で構文確認。
- ロールバック: 追記を削除。

### ステップ 8: black 設定を pyproject.toml に追加
- 変更ファイル: `pyproject.toml`
- 操作: 末尾に以下を追記（ruff-format と併用しても矛盾しない設定）。
```toml
[tool.black]
line-length = 100
target-version = ["py312"]
```
- 検証: 同上構文確認。
- ロールバック: 追記を削除。

### ステップ 9: pre-commit に black リポジトリを追加
- 変更ファイル: `.pre-commit-config.yaml`
- 操作: `repos:` 内の `isort` ブロックの直後に以下を追加。
```yaml
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
```
- 検証: `pre-commit validate-config` を実行（失敗したら YAML を確認）。
- ロールバック: 追加ブロックを削除。

### ステップ 10: pre-commit のリビジョンを最新化
- 変更ファイル: `.pre-commit-config.yaml`
- 操作: `pre-commit autoupdate` を実行（ネットワーク必要）。失敗する場合はスキップ可。
- 検証: `git diff .pre-commit-config.yaml` で rev が更新されたか確認。
- ロールバック: `git checkout .pre-commit-config.yaml`。

### ステップ 11: インストール手順を README に追記
- 変更ファイル: `README.md`
- 操作: 「開発環境セットアップ」に以下を追記。
```
pre-commit install
pre-commit run --all-files
```
- 検証: `grep "pre-commit install" README.md`
- ロールバック: 追記削除。

### ステップ 12: ローカルで pre-commit を全ファイル実行（報告のみ）
- 変更ファイル: なし（確認のみ）
- 操作: `pre-commit run --all-files` を実行し、出力を `docs/precommit_first_run.txt` に保存。
- 検証: `test -s docs/precommit_first_run.txt`
- ロールバック: 不要。

---

## Phase 3: log_exception ガイド（ステップ 13〜18）

### ステップ 13: log_exception の docstring を拡充
- 変更ファイル: `src/backend/error_utils.py`
- 操作: `log_exception` 関数の docstring に使用例を追加。
```python
def log_exception(
    logger: logging.Logger,
    msg: str,
    exc: BaseException,
    *args,
) -> None:
    """trace_id を自動付与して例外をログ出力。

    使用例:
        try:
            ...
        except ValueError as e:
            log_exception(logger, "処理失敗", e)
            raise
    """
```
- 検証: `python -c "import ast;ast.parse(open('src/backend/error_utils.py').read())"`
- ロールバック: docstring を元に戻す。

### ステップ 14: エラー処理ガイド文書を作成
- 変更ファイル: `docs/error_handling.md`（新規）
- 操作: 「広範な except を避ける」「具体的例外を捕捉」「log_exception でログ」「必要ならドメイン例外へ変換」を記述。
- 検証: ファイル存在確認。
- ロールバック: 削除。

### ステップ 15: 推奨 try/except パターンをガイドに追記
- 変更ファイル: `docs/error_handling.md`
- 操作: 以下のコード例を追記。
```python
try:
    result = await redis.eval(script, keys, args)
except RedisError as e:
    log_exception(logger, "Redis Lua 実行失敗", e)
    raise CacheError("cache operation failed") from e
```
- 検証: ファイル存在確認。
- ロールバック: 追記削除。

### ステップ 16: log_exception の単体テストを作成
- 変更ファイル: `tests/backend/test_error_utils.py`（新規）
- 操作: 以下を作成。
```python
import logging
from src.backend.error_utils import log_exception


def test_log_exception_emits_error(caplog):
    logger = logging.getLogger("test_err")
    try:
        raise ValueError("boom")
    except ValueError as e:
        with caplog.at_level(logging.ERROR):
            log_exception(logger, "failed", e)
    assert "failed" in caplog.text
    assert "boom" in caplog.text
```
- 検証: `pytest tests/backend/test_error_utils.py -q`
- ロールバック: ファイル削除。

### ステップ 17: CHANGELOG に方針を追記
- 変更ファイル: `CHANGELOG.md`
- 操作: 先頭に `## [Unreleased]` セクションを追加し、「エラー処理ガイドを追加（docs/error_handling.md）」と記載。
- 検証: `grep "error_handling" CHANGELOG.md`
- ロールバック: 追記削除。

### ステップ 18: README からガイドへリンク
- 変更ファイル: `README.md`
- 操作: 「ドキュメント」セクションに `- [エラー処理ガイド](docs/error_handling.md)` を追加。
- 検証: `grep "error_handling.md" README.md`
- ロールバック: 追記削除。

---

## Phase 4: ドメイン例外（ステップ 19〜24）

### ステップ 19: 例外基底モジュールを作成
- 変更ファイル: `src/backend/exceptions.py`（新規）
- 操作: 以下を作成。
```python
"""バックエンド共通のドメイン例外。"""

from typing import Optional


class BackendError(Exception):
    """すべてのバックエンド例外の基底。"""

    def __init__(self, message: str, *, cause: Optional[BaseException] = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause
```
- 検証: `python -c "import src.backend.exceptions"`
- ロールバック: ファイル削除。

### ステップ 20: RateLimitExceeded を追加
- 変更ファイル: `src/backend/exceptions.py`
- 操作: `BackendError` の後に以下を追記。
```python
class RateLimitExceeded(BackendError):
    """レート制限を超過した。"""
```
- 検証: `python -c "from src.backend.exceptions import RateLimitExceeded"`
- ロールバック: 追記削除。

### ステップ 21: CacheError / CacheMiss を追加
- 変更ファイル: `src/backend/exceptions.py`
- 操作: 以下を追記。
```python
class CacheError(BackendError):
    """Redis/キャッシュ操作の失敗。"""


class CacheMiss(BackendError):
    """キャッシュにキーが存在しない。"""
```
- 検証: `python -c "from src.backend.exceptions import CacheError, CacheMiss"`
- ロールバック: 追記削除。

### ステップ 22: DatabaseError を追加し database/core.py で利用
- 変更ファイル: `src/backend/exceptions.py`, `src/backend/database/core.py`
- 操作:
  1. `exceptions.py` に追記:
```python
class DatabaseError(BackendError):
    """DB 操作中の失敗。"""
```
  2. `database/core.py` の `except Exception` を `except DatabaseError` 等の具体的例外に置換し、必要なら `raise DatabaseError(...) from e`。
- 検証: `python -c "from src.backend.exceptions import DatabaseError"` と `ruff check src/backend/database/core.py`
- ロールバック: 変更を元に戻す。

### ステップ 23: rate_limit.py / redis_cache.py をドメイン例外に置換
- 変更ファイル: `src/backend/rate_limit.py`, `src/services/redis_cache.py`
- 操作: Redis 関連の `except Exception` / `raise` を `CacheError` または `RateLimitExceeded` に置換。`from src.backend.exceptions import CacheError, RateLimitExceeded` を追加。
- 検証: `ruff check src/backend/rate_limit.py src/services/redis_cache.py`
- ロールバック: 変更を元に戻す。

### ステップ 24: ドメイン例外の単体テストを作成し CI で実行
- 変更ファイル: `tests/backend/test_exceptions.py`（新規）
- 操作: 以下を作成。
```python
from src.backend.exceptions import (
    BackendError,
    CacheError,
    CacheMiss,
    DatabaseError,
    RateLimitExceeded,
)


def test_hierarchy():
    assert issubclass(RateLimitExceeded, BackendError)
    assert issubclass(CacheError, BackendError)
    assert issubclass(CacheMiss, BackendError)
    assert issubclass(DatabaseError, BackendError)


def test_cause_chain():
    cause = ValueError("x")
    err = DatabaseError("db failed", cause=cause)
    assert err.cause is cause
    assert "db failed" in str(err)
```
- 検証: `pytest tests/backend/test_exceptions.py -q`
- ロールバック: ファイル削除。

---

## 完了後の全体検証コマンド

```bash
# Lint / Format
ruff check src/ tests/
ruff format --check src/ tests/
isort --check-only src/ tests/
black --check src/ tests/   # 導入した場合

# 型チェック（新規ファイル）
mypy --config-file pyproject.toml --strict src/backend/exceptions.py src/backend/error_utils.py

# テスト
pytest tests/backend/test_error_utils.py tests/backend/test_exceptions.py -q

# pre-commit 全体
pre-commit run --all-files
```

## 進捗管理のコツ（低性能 LLM 向け）
- 各ステップ終了ごとに上記「検証」コマンドを 1 つだけ実行し、成功を確認してから次へ。
- エラーが出たら「ロールバック」列の操作で元に戻し、原因を 1 つずつ潰す。
- 一度に複数ステップをまとめない（コンフリクト検出が難しくなるため）。
