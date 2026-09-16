# P10: コードレビュー改善 — 技術的負債解消・商用化品質達成 実装計画書（全24ステップ）

**作成日**: 2026-09-16
**対象**: AutoNovel v4.9.3（`e:/hhh`）
**目的**: コードレビューで検出された技術的負債を体系的に解消し、商用リリースに耐える品質基盤を構築する。

**低性能LLM向け設計方針**:
- **全24ステップの極小分割**: 1ステップにつき1〜3ファイルのみの変更。
- **完全自己完結コード**: コピペで動作する完全なコード、インポート文を記載。
- **検証コマンドと合否基準**: ステップごとにワンライナー検証コマンドとPass条件を明記。
- **依存関係ゼロ**: 各ステップは単独で実行可能（前ステップの完了は推奨だが必須ではない）。

---

## 📋 全24ステップ 実装マトリクス

### Phase A: セキュリティ・衛生（Step 1-4）
| Step | 分類 | 対象ファイル | 主な作業内容 | 検証コマンド |
|:---:|:---|:---|:---|:---|
| **1** | セキュリティ | [`.gitignore`](file:///e:/hhh/.gitignore) | `.env`/`autonovel.db`/`coverage.json` の除外パターン強化 | `python -c "lines=open('.gitignore').read(); assert 'autonovel.db' in lines; print('OK')"` |
| **2** | セキュリティ | [`src/backend/auth.py`](file:///e:/hhh/src/backend/auth.py) | API Key → admin 無条件昇格の修正（Role ベース制御） | `pytest tests/unit/backend/test_auth_rbac.py -o addopts="" --no-cov` |
| **3** | バージョン統一 | [`src/backend/config.py`](file:///e:/hhh/src/backend/config.py), [`README.md`](file:///e:/hhh/README.md) | `APP_VERSION` を `pyproject.toml` から動的取得に変更 | `python -c "from src.backend.config import settings; assert settings.APP_VERSION == '4.9.3'; print('OK')"` |
| **4** | セキュリティ | [`src/backend/config.py`](file:///e:/hhh/src/backend/config.py) | コメント重複行の除去・本番環境の JWT/DB 検証テスト追加 | `pytest tests/unit/backend/test_config_production_validation.py -o addopts="" --no-cov` |

### Phase B: ルートディレクトリ浄化（Step 5-8）
| Step | 分類 | 対象ファイル | 主な作業内容 | 検証コマンド |
|:---:|:---|:---|:---|:---|
| **5** | 整理 | ルート直下デバッグスクリプト群 | `debug_*.py` / `fix_*.py` / `check_*.py` を `scripts/debug/` に移動 | `python -c "import os; assert not os.path.exists('debug_context.py'); print('OK')"` |
| **6** | 整理 | ルート直下テストランナー群 | `run_*_test*.py` / `test_audio.py` を `scripts/runners/` に移動 | `python -c "import os; assert not os.path.exists('run_three_tests.py'); print('OK')"` |
| **7** | 整理 | ルート直下計画書 | `P0.md`〜`P2.md` / `P*_COVERAGE.md` / `改善提案*.md` 等を `plans/archive/` に移動 | `python -c "import os; assert not os.path.exists('P0.md'); assert os.path.exists('plans/archive/P0.md'); print('OK')"` |
| **8** | 整理 | ルート直下残存ファイル | `test_output.txt`/`benchmark_results.json`/`coverage.json`/`episodes.md` 等を適切な場所に移動または削除 | `python -c "import os; root_files=[f for f in os.listdir('.') if f.endswith('.txt') and 'test_' in f]; assert len(root_files)==0; print('OK')"` |

### Phase C: デッドコード除去・レガシー統合（Step 9-14）
| Step | 分類 | 対象ファイル | 主な作業内容 | 検証コマンド |
|:---:|:---|:---|:---|:---|
| **9** | デッドコード | [`src/services/vector_store.py`](file:///e:/hhh/src/services/vector_store.py) | レガシー単体ファイル(1,428行)を `pyproject.toml` の omit に追加し、パッケージ版への完全移行を確認 | `python -c "from src.services.vector_store import get_default_store; print('OK')"` |
| **10** | デッドコード | [`pyproject.toml`](file:///e:/hhh/pyproject.toml) | coverage omit リストの未参照100+ファイルのうち明確なデッドコード20件を物理削除 | `py -m pytest --co -q 2>&1` |
| **11** | レガシー統合 | [`src/services/writing_services.py`](file:///e:/hhh/src/services/writing_services.py) | import時の即時 `warnings.warn()` を削除し、関数レベルの遅延警告に変更 | `python -c "import src.services.writing_services; print('No immediate warning')"` |
| **12** | レガシー統合 | [`src/backend/engine_context.py`](file:///e:/hhh/src/backend/engine_context.py), [`src/core/container/app.py`](file:///e:/hhh/src/core/container/app.py) | `engine_context.py` の import時即時警告を遅延化 | `python -c "import src.backend.engine_context; print('No immediate warning')"` |
| **13** | デッドコード | [`pyproject.toml`](file:///e:/hhh/pyproject.toml) | 空スタブファイル3件を omit に追加 | `python -c "import tomllib; print('OK')"` |
| **14** | 品質 | [`src/backend/config.py`](file:///e:/hhh/src/backend/config.py) | 重複コメント行（4箇所）の除去 | `python -c "from src.backend.config import settings; print('OK')"` |

### Phase D: config 統一・巨大ファイル分割（Step 15-18）
| Step | 分類 | 対象ファイル | 主な作業内容 | 検証コマンド |
|:---:|:---|:---|:---|:---|
| **15** | config統一 | [`src/services/redis_cache.py`](file:///e:/hhh/src/services/redis_cache.py) | `from config import get_config` を `from src.backend.config import settings` に統一 | `python -c "from src.services.redis_cache import RedisCacheService; print('OK')"` |
| **16** | config統一 | [`src/services/bible_service.py`](file:///e:/hhh/src/services/bible_service.py) | `from config import MODEL_PLANNING` 等を `src.backend.config.settings` 経由に変更 | `python -c "from src.services.bible_service import WorldBibleGenerator; print('OK')"` |
| **17** | 巨大ファイル | [`src/agents/audit.py`](file:///e:/hhh/src/agents/audit.py) (1,113行) | `FastPlotScreener` と `AbilityConsistencyChecker` を `src/agents/audit_screeners.py` に分離 | `python -c "from src.agents.audit import PlotIntegrityMonitor; from src.agents.audit_screeners import FastPlotScreener; print('OK')"` |
| **18** | 巨大ファイル | [`src/services/book_score_service.py`](file:///e:/hhh/src/services/book_score_service.py) (1,047行) | `BookScore` dataclass と `BookScoreRepository` Protocol を `src/services/book_score_models.py` に分離 | `python -c "from src.services.book_score_models import BookScore, BookScoreRepository; print('OK')"` |

### Phase E: コード品質・ロギング改善（Step 19-22）
| Step | 分類 | 対象ファイル | 主な作業内容 | 検証コマンド |
|:---:|:---|:---|:---|:---|
| **19** | ロギング | [`pyproject.toml`](file:///e:/hhh/pyproject.toml) | ruff に `G004` (logging-f-string) ルールを追加 | `py -m ruff check src/services/retry_decorator.py --select G004` |
| **20** | ロギング | [`src/services/retry_decorator.py`](file:///e:/hhh/src/services/retry_decorator.py) | f-string ロギング (6箇所) を `%s` 形式に変換（模範実装） | `py -m ruff check src/services/retry_decorator.py --select G004` |
| **21** | UseCase | [`src/application/use_cases/writing_use_cases.py`](file:///e:/hhh/src/application/use_cases/writing_use_cases.py) | 5箇所の TODO ハードコード値を `NotImplementedError` に置換 | `pytest tests/unit/application/test_writing_usecase_not_implemented.py -o addopts="" --no-cov` |
| **22** | UseCase | [`src/application/use_cases/branch_use_cases.py`](file:///e:/hhh/src/application/use_cases/branch_use_cases.py), [`src/application/use_cases/audit_use_cases.py`](file:///e:/hhh/src/application/use_cases/audit_use_cases.py) | 4箇所の TODO を `NotImplementedError` に置換 | `pytest tests/unit/application/ -o addopts="" --no-cov` |

### Phase F: カバレッジ・最終検証（Step 23-24）
| Step | 分類 | 対象ファイル | 主な作業内容 | 検証コマンド |
|:---:|:---|:---|:---|:---|
| **23** | カバレッジ | [`pyproject.toml`](file:///e:/hhh/pyproject.toml) | `--cov-fail-under` を 35 → 45 に引き上げ | `py -m pytest -q --tb=short` |
| **24** | 最終検証 | 全体 | `make verify` 相当の全検証を実行し全パスを確認 | `py -m ruff check src tests && py -m mypy src --ignore-missing-imports && py -m pytest -q --tb=short` |

---

## 🛠 各ステップ詳細仕様

### Step 1: `.gitignore` セキュリティ強化
- **目的**: `autonovel.db`、`coverage.json`、`benchmark_results.json` がリポジトリに含まれないよう `.gitignore` を強化し、Git 追跡済みファイルを解除する。
- **対象ファイル**: [`.gitignore`](file:///e:/hhh/.gitignore)
- **編集内容**:
  `.gitignore` の `# storage & local dbs` セクションに以下を追加：
```gitignore
# storage & local dbs
storage/
*.db
*.db-shm
*.db-wal
*.db-journal
*.bak_*.db
coverage.xml
coverage.json
benchmark_results.json
```
- **追加作業**: `.env` が既に `.gitignore` L11 に存在することを確認済み。Git 追跡済みファイルを解除する：
```powershell
git rm --cached autonovel.db coverage.json benchmark_results.json 2>$null
git rm --cached .env 2>$null
```
- **検証コマンド**:
```powershell
python -c "lines=open('.gitignore').read(); assert 'coverage.json' in lines; assert 'benchmark_results.json' in lines; print('Step 1 OK')"
```
- **合否基準**: `Step 1 OK` と出力されること。

---

### Step 2: API Key の Role ベースアクセス制御
- **目的**: `require_admin_user_or_key()` で API Key 保持者に無条件 admin 権限が付与される問題を修正する。
- **対象ファイル**: [`src/backend/auth.py`](file:///e:/hhh/src/backend/auth.py)
- **編集内容**:

  **変更前** (L138-139):
```python
    key = await require_api_key(authorization)
    if key:
        return _get_dev_mock_user()
```
  **変更後**:
```python
    key = await require_api_key(authorization)
    if key:
        # API Key 保持者には読み取り専用ロールを付与（admin 昇格しない）
        api_user = _get_dev_mock_user()
        api_user.role = "api_readonly"
        return api_user
```
- **テストファイル作成**: `tests/unit/backend/test_auth_rbac.py`
```python
"""API Key が admin 権限を付与しないことを検証するテスト"""
import pytest
from unittest.mock import AsyncMock, patch
from src.backend.auth import require_admin_user_or_key, _get_dev_mock_user


@pytest.mark.asyncio
async def test_api_key_does_not_grant_admin():
    """API Key 認証が admin ロールを返さないことを確認"""
    with patch("src.backend.auth.settings") as mock_settings:
        mock_settings.AUTH_DISABLED = False
        mock_settings.ALLOWED_API_KEYS = ""
        with patch("src.backend.auth.require_api_key", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = "valid-key"
            with patch("src.backend.auth.decode_token", return_value=None):
                user = await require_admin_user_or_key(
                    token=None, authorization="Bearer valid-key", db=AsyncMock()
                )
                assert user.role != "admin", "API Key should not grant admin role"


def test_dev_mock_user_has_admin_role():
    """開発用モックユーザーは admin ロールを持つ（AUTH_DISABLED時のみ使用）"""
    user = _get_dev_mock_user()
    assert user.role == "admin"
```
- **検証コマンド**:
```powershell
pytest tests/unit/backend/test_auth_rbac.py -o addopts="" --no-cov -v
```
- **合否基準**: 2テスト全パス。

---

### Step 3: バージョン番号の SSOT 化
- **目的**: `pyproject.toml` (4.9.3) / `README.md` (4.9.6) / `config.py` (4.9.0) で異なるバージョンを `pyproject.toml` に一本化する。
- **対象ファイル**: [`src/backend/config.py`](file:///e:/hhh/src/backend/config.py), [`README.md`](file:///e:/hhh/README.md)
- **編集内容**:

  ファイル冒頭（`class Settings` の前）に以下のヘルパーを追加:
```python
def _get_package_version() -> str:
    """pyproject.toml からバージョンを動的取得する。"""
    try:
        from importlib.metadata import version
        return version("autonovel")
    except Exception:
        return "4.9.3"
```

  **変更前** (config.py L37):
```python
    APP_VERSION: str = "4.9.0"
```
  **変更後**:
```python
    APP_VERSION: str = Field(default_factory=lambda: _get_package_version())
```

  **README.md L21**: バージョンバッジを `4.9.3` に統一。
- **検証コマンド**:
```powershell
python -c "from src.backend.config import settings; v=settings.APP_VERSION; print(f'Version: {v}'); assert v != '4.9.0', 'Still hardcoded'"
```
- **合否基準**: `Version: 4.9.3` と表示されアサーション通過。

---

### Step 4: 本番環境バリデーションテスト追加
- **目的**: `validate_production_secrets` のカバレッジを確保する。
- **テストファイル作成**: `tests/unit/backend/test_config_production_validation.py`
```python
"""config.py の本番環境バリデーション検証テスト"""
import pytest
from pydantic import ValidationError


def test_production_rejects_auth_disabled():
    from src.backend.config import Settings
    with pytest.raises(ValidationError, match="AUTH_DISABLED"):
        Settings(APP_ENV="production", AUTH_DISABLED=True,
                 JWT_SECRET_KEY="a" * 64, DATABASE_URL="postgresql://test")


def test_production_rejects_weak_jwt():
    from src.backend.config import Settings
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(APP_ENV="production", JWT_SECRET_KEY="change-in-prod",
                 DATABASE_URL="postgresql://test")


def test_production_rejects_sqlite():
    from src.backend.config import Settings
    with pytest.raises(ValidationError, match="SQLite"):
        Settings(APP_ENV="production", JWT_SECRET_KEY="a" * 64,
                 DATABASE_URL="sqlite:///test.db")


def test_development_allows_defaults():
    from src.backend.config import Settings
    s = Settings(APP_ENV="development")
    assert s.APP_ENV == "development"
```
- **検証コマンド**:
```powershell
pytest tests/unit/backend/test_config_production_validation.py -o addopts="" --no-cov -v
```
- **合否基準**: 4テスト全パス。

---

### Step 5: デバッグスクリプトの移動
- **目的**: ルート直下の `debug_*.py` / `fix_*.py` / `check_*.py` / `add_*.py` (計10ファイル) を `scripts/debug/` に移動。
- **対象ファイル**: `debug_context.py`, `debug_marketing.py`, `debug_sanitize.py`, `debug_sanitize2.py`, `debug_set_final.py`, `fix_taxonomy.py`, `fix_test_file.py`, `check_import.py`, `check_module.py`, `add_magic_sword.py`
- **実行コマンド**:
```powershell
New-Item -ItemType Directory -Force -Path scripts/debug
Move-Item -Force debug_context.py, debug_marketing.py, debug_sanitize.py, debug_sanitize2.py, debug_set_final.py, fix_taxonomy.py, fix_test_file.py, check_import.py, check_module.py, add_magic_sword.py -Destination scripts/debug/
```
- **検証コマンド**:
```powershell
python -c "import os; assert not os.path.exists('debug_context.py'); assert os.path.exists('scripts/debug/debug_context.py'); print('Step 5 OK')"
```
- **合否基準**: `Step 5 OK` と出力されること。

---

### Step 6: テストランナーの移動
- **目的**: ルート直下の `run_*_test*.py` / `test_audio.py` / `run_tests.sh` を `scripts/runners/` に移動。
- **対象ファイル**: `run_exporter_tests.py`, `run_marketing_test.py`, `run_marketing_tests.py`, `run_three_tests.py`, `test_audio.py`, `run_tests.sh`
- **実行コマンド**:
```powershell
New-Item -ItemType Directory -Force -Path scripts/runners
Move-Item -Force run_exporter_tests.py, run_marketing_test.py, run_marketing_tests.py, run_three_tests.py, test_audio.py, run_tests.sh -Destination scripts/runners/
```
- **検証コマンド**:
```powershell
python -c "import os; assert not os.path.exists('run_three_tests.py'); print('Step 6 OK')"
```
- **合否基準**: `Step 6 OK` と出力されること。

---

### Step 7: 計画書のアーカイブ移動
- **目的**: ルート直下の巨大計画書ファイル (`P0.md`=46KB, `P1.md`=46KB, `P2.md`=44KB) およびカバレッジ報告書を `plans/archive/` に移動。
- **対象ファイル**: `P0.md`, `P1.md`, `P2.md`, `P1_COVERAGE.md`〜`P6_COVERAGE.md`, `改善提案実装計画書.md`, `p4_implementation_summary.md`, `IMPLEMENTATION_SUMMARY.md`, `ENGINE_MODULE_TEST_SUMMARY.md`, `BRANCH_FEATURE_SUMMARY.md`, `PROJECT_EVALUATION_AND_IMPROVEMENT_PROPOSALS.md`
- **実行コマンド**:
```powershell
New-Item -ItemType Directory -Force -Path plans/archive
Move-Item -Force P0.md, P1.md, P2.md -Destination plans/archive/
Move-Item -Force P1_COVERAGE.md, P2_COVERAGE.md, P3_COVERAGE.md, P4_COVERAGE.md, P5_COVERAGE.md, P6_COVERAGE.md -Destination plans/archive/
Move-Item -Force "改善提案実装計画書.md", p4_implementation_summary.md, IMPLEMENTATION_SUMMARY.md, ENGINE_MODULE_TEST_SUMMARY.md, BRANCH_FEATURE_SUMMARY.md, PROJECT_EVALUATION_AND_IMPROVEMENT_PROPOSALS.md -Destination plans/archive/
```
- **検証コマンド**:
```powershell
python -c "import os; assert not os.path.exists('P0.md'); assert os.path.exists('plans/archive/P0.md'); print('Step 7 OK')"
```
- **合否基準**: `Step 7 OK` と出力されること。

---

### Step 8: その他ルート残存ファイルの整理
- **目的**: `test_output.txt`(87KB), `coverage.json`(5.7MB), `benchmark_results.json`(22KB), `never_referenced_modules.txt` 等の一時ファイルを整理。
- **対象**:
  - 削除: `test_output.txt`, `coverage.json`, `benchmark_results.json`, `never_referenced_modules.txt`
  - 移動: `episodes.md` → `docs/`, ビジネスモデル MD → `plans/`
- **実行コマンド**:
```powershell
Remove-Item -Force test_output.txt, coverage.json, benchmark_results.json, never_referenced_modules.txt -ErrorAction SilentlyContinue
Move-Item -Force episodes.md -Destination docs/ -ErrorAction SilentlyContinue
Move-Item -Force FREEMIUM_10YEN_MODEL.md, PLOT_CREDIT_MODEL.md, PROFITABILITY_DETAIL.md, PROFITABILITY_PROPOSALS.md -Destination plans/ -ErrorAction SilentlyContinue
```
- **検証コマンド**:
```powershell
python -c "import os; txt=[f for f in os.listdir('.') if f=='test_output.txt']; assert len(txt)==0; print('Step 8 OK')"
```
- **合否基準**: `Step 8 OK` と出力されること。

---

### Step 9: レガシー `vector_store.py` の coverage omit 登録
- **目的**: `src/services/vector_store.py` (1,428行) はパッケージ版 `src/services/vector_store/` と二重存在。レガシー単体ファイルを omit に追加。
- **対象ファイル**: [`pyproject.toml`](file:///e:/hhh/pyproject.toml)
- **編集内容**: `[tool.coverage.run]` の `omit` セクション末尾に追加:
```toml
    # レガシー vector_store 単体ファイル（パッケージ版に完全移行済み）
    "src/services/vector_store.py",
```
- **影響確認**: `from src.services.vector_store import` は全てパッケージ `__init__.py` を参照（grep 確認済み）。
- **検証コマンド**:
```powershell
python -c "from src.services.vector_store import get_default_store, BaseVectorStore, InMemoryFallbackStore; print('Step 9 OK')"
```
- **合否基準**: `Step 9 OK` と出力されること。

---

### Step 10: デッドモジュールの物理削除（20件）
- **目的**: `pyproject.toml` omit に列挙済みかつ参照ゼロの20ファイルを物理削除し、コードベース母数を削減。
- **対象ファイル**: 以下の20ファイル:
```
src/agents/plot_rebuild_helpers.py
src/agents/social/__init__.py
src/backend/database/connection_protocol.py
src/backend/database/repo_inmemory.py
src/backend/engine_reader.py
src/backend/tension_utils.py
src/backend/zamaa_validator.py
src/core/ab_testing.py
src/core/audit_logger.py
src/core/null_objects.py
src/core/plugin_schema.py
src/core/state/desires.py
src/domain/book.py
src/services/amplifier_router.py
src/services/content_processor.py
src/services/healing_pipeline.py
src/services/novel_service.py
src/services/parallel_audit.py
src/services/writing_services_utils.py
src/services/tracing_service.py
```
- **削除前の安全確認**: 各ファイルに対し `grep -r "from src.<module> import" src/ tests/` でゼロヒットを確認。
- **実行コマンド**:
```powershell
$files = @(
    "src/agents/plot_rebuild_helpers.py",
    "src/agents/social/__init__.py",
    "src/backend/database/connection_protocol.py",
    "src/backend/database/repo_inmemory.py",
    "src/backend/engine_reader.py",
    "src/backend/tension_utils.py",
    "src/backend/zamaa_validator.py",
    "src/core/ab_testing.py",
    "src/core/audit_logger.py",
    "src/core/null_objects.py",
    "src/core/plugin_schema.py",
    "src/core/state/desires.py",
    "src/domain/book.py",
    "src/services/amplifier_router.py",
    "src/services/content_processor.py",
    "src/services/healing_pipeline.py",
    "src/services/novel_service.py",
    "src/services/parallel_audit.py",
    "src/services/writing_services_utils.py",
    "src/services/tracing_service.py"
)
foreach ($f in $files) { Remove-Item -Force $f -ErrorAction SilentlyContinue }
```
- **pyproject.toml 更新**: 削除ファイルを `omit` リストから除去（存在しないファイルは omit 不要）。
- **検証コマンド**:
```powershell
python -c "import os; assert not os.path.exists('src/services/novel_service.py'); print('Step 10 OK')"
```
- **合否基準**: 削除対象ファイルが存在しないこと。`py -m pytest --co -q` でコレクションエラーなし。

---

### Step 11: `writing_services.py` の import 時即時警告を遅延化
- **目的**: モジュール import 時の即座の `DeprecationWarning` を関数呼び出し時の遅延警告に変更。
- **対象ファイル**: [`src/services/writing_services.py`](file:///e:/hhh/src/services/writing_services.py)
- **編集内容**:

  **変更前** (L15-19):
```python
warnings.warn(
    "src.services.writing_services は非推奨です。src.backend.writing_service を使用してください。",
    DeprecationWarning,
    stacklevel=2,
)
```
  **変更後**:
```python
# 遅延警告: import時ではなくクラス初期化時に非推奨警告を発する
_DEPRECATION_WARNING_ISSUED = False

def _emit_deprecation_warning():
    global _DEPRECATION_WARNING_ISSUED
    if not _DEPRECATION_WARNING_ISSUED:
        warnings.warn(
            "src.services.writing_services は非推奨です。"
            "src.backend.writing_service を使用してください。",
            DeprecationWarning,
            stacklevel=3,
        )
        _DEPRECATION_WARNING_ISSUED = True
```
  各公開クラスの `__init__` 冒頭に `_emit_deprecation_warning()` を追加。
- **検証コマンド**:
```powershell
python -c "import warnings; warnings.filterwarnings('error', category=DeprecationWarning); import src.services.writing_services; print('Step 11 OK')"
```
- **合否基準**: DeprecationWarning が発されず `Step 11 OK` と出力。

---

### Step 12: `engine_context.py` の import 時即時警告を遅延化
- **目的**: `src/backend/engine_context.py` L13 の即時警告を削除し、`ContextManager.__init__` 内の警告のみ残す。`container/app.py` の参照を切り替え。
- **対象ファイル**: [`src/backend/engine_context.py`](file:///e:/hhh/src/backend/engine_context.py), [`src/core/container/app.py`](file:///e:/hhh/src/core/container/app.py)
- **編集内容**:

  **`engine_context.py` L13 を削除**:
```python
warnings.warn("src.backend.engine_context is deprecated, ...", DeprecationWarning, stacklevel=2)
```

  **`container/app.py` L15 を変更**:
```python
# 変更前
from src.backend.engine_context import ContextManager
# 変更後
try:
    from src.agents.context_builder_agent import ContextBuilderAgent as ContextManager
except ImportError:
    from src.backend.engine_context import ContextManager
```
- **検証コマンド**:
```powershell
python -c "import warnings; warnings.filterwarnings('error', category=DeprecationWarning); import src.backend.engine_context; print('Step 12 OK')"
```
- **合否基準**: `Step 12 OK` と出力されること。

---

### Step 13: 空スタブファイルの omit 追加
- **目的**: ほぼ空またはスタブのみの3ファイルを `omit` に追加。
- **対象ファイル**: [`pyproject.toml`](file:///e:/hhh/pyproject.toml)
- **追加エントリ**:
```toml
    "src/services/plot_service.py",
    "src/services/state_manager.py",
    "src/services/narrative_scoring_service.py",
```
- **検証コマンド**:
```powershell
python -c "t=open('pyproject.toml').read(); assert 'src/services/plot_service.py' in t; print('Step 13 OK')"
```
- **合否基準**: `Step 13 OK` と出力されること。

---

### Step 14: `config.py` の重複コメント行除去
- **目的**: 重複コメント行4箇所を除去。
- **対象ファイル**: [`src/backend/config.py`](file:///e:/hhh/src/backend/config.py)
- **編集内容**: 以下の重複行を削除:
  - L35: `    # サーバー基本設定` → 削除（L34 が正）
  - L43: `    # データベース設定` → 削除（L42 が正）
  - L123: `    # LLMプロバイダー設定` → 削除（L121-122 が正）
  - L171: `    # ストレージ設定` → 削除（L170 が正）
- **検証コマンド**:
```powershell
python -c "from src.backend.config import settings; print('Step 14 OK')"
```
- **合否基準**: `Step 14 OK` と出力されること。

---

### Step 15: `redis_cache.py` の config import 統一
- **目的**: `from config import get_config` を標準の `src.backend.config.settings` に統一。
- **対象ファイル**: [`src/services/redis_cache.py`](file:///e:/hhh/src/services/redis_cache.py)
- **編集内容**:

  **変更前** (L20):
```python
from config import get_config
```
  **変更後**:
```python
from src.backend.config import settings as _app_settings
```

  **変更前** (L66-67):
```python
            config = get_config()
            redis_url = getattr(config, "redis_url", None) or "redis://localhost:6379/0"
```
  **変更後**:
```python
            redis_url = getattr(_app_settings, "REDIS_URL", None) or "redis://localhost:6379/0"
```
- **検証コマンド**:
```powershell
python -c "from src.services.redis_cache import RedisCacheService; print('Step 15 OK')"
```
- **合否基準**: ImportError なしで `Step 15 OK` 出力。

---

### Step 16: `bible_service.py` の config import 統一
- **目的**: `from config import MODEL_PLANNING` を標準パスに統一。
- **対象ファイル**: [`src/services/bible_service.py`](file:///e:/hhh/src/services/bible_service.py)
- **編集内容**:

  **変更前** (L7-8):
```python
from config import MODEL_PLANNING, MODEL_PLOT_EXPANSION
from config.domain_profile_manager import DomainProfileService
```
  **変更後**:
```python
from src.backend.config import settings as _settings

MODEL_PLANNING = getattr(_settings, "GEMINI_MODEL", "gemini-1.5-flash")
MODEL_PLOT_EXPANSION = getattr(_settings, "GEMINI_MODEL", "gemini-1.5-flash")

try:
    from config.domain_profile_manager import DomainProfileService
except ImportError:
    from src.config.domain_profile_manager import DomainProfileService
```
- **検証コマンド**:
```powershell
python -c "from src.services.bible_service import WorldBibleGenerator; print('Step 16 OK')"
```
- **合否基準**: `Step 16 OK` と出力されること。

---

### Step 17: `audit.py` の巨大ファイル分割
- **目的**: `src/agents/audit.py` (1,113行) から2クラスを分離してSRPを適用。
- **新規作成ファイル**: `src/agents/audit_screeners.py`
- **編集内容**:
  1. `audit.py` から `FastPlotScreener` (L27-38) と `AbilityConsistencyChecker` (L41-62) をカット
  2. `src/agents/audit_screeners.py` に移動（必要な import 含む）
  3. `audit.py` 冒頭に互換 import 追加:
```python
from src.agents.audit_screeners import FastPlotScreener, AbilityConsistencyChecker  # noqa: F401
```
- **`src/agents/audit_screeners.py` の内容**:
```python
"""audit.py から分離されたプロット・能力スクリーニングクラス群"""
from __future__ import annotations
import logging
from typing import Any
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class FastPlotScreener:
    """プロット快速スクリーニング。"""
    def __init__(self, llm: LLMService, prompt_manager: Any):
        self.llm = llm
        self.prompt_manager = prompt_manager

    async def screen_plot(self, blueprint: str) -> tuple[bool, str]:
        prompt = self.prompt_manager.build_fast_plot_screen_prompt(blueprint)
        result = await self.llm.generate_json(purpose="audit", prompt=prompt)
        metadata = result.get("metadata", {})
        return metadata.get("is_valid", True), metadata.get("feedback", "OK")


class AbilityConsistencyChecker:
    """能力整合性チェック"""
    def __init__(self, llm: LLMService, prompt_manager: Any = None):
        self.llm = llm
        self.prompt_manager = prompt_manager

    async def audit_ability_consistency(
        self, blueprint: str, settings_json: str, characters_json: str
    ) -> tuple[bool, str, str]:
        if self.prompt_manager is None:
            return True, "OK", ""
        prompt = self.prompt_manager.build_ability_audit_prompt(
            blueprint, settings_json, characters_json
        )
        result = await self.llm.generate_json(purpose="audit", prompt=prompt)
        metadata = result.get("metadata", {})
        return (
            metadata.get("is_consistent", True),
            metadata.get("feedback", "OK"),
            metadata.get("suggestions", ""),
        )
```
- **検証コマンド**:
```powershell
python -c "from src.agents.audit import PlotIntegrityMonitor, FastPlotScreener; from src.agents.audit_screeners import AbilityConsistencyChecker; print('Step 17 OK')"
```
- **合否基準**: 両方の import パスが動作すること。

---

### Step 18: `book_score_service.py` のモデル分離
- **目的**: `src/services/book_score_service.py` (1,047行) からモデル定義を分離。
- **新規作成ファイル**: `src/services/book_score_models.py`
- **編集内容**:
  1. `book_score_service.py` から `BookScore` (L17-35) と `BookScoreRepository` (L38-45) をカット
  2. `src/services/book_score_models.py` に移動
  3. `book_score_service.py` 冒頭に互換 import 追加:
```python
from src.services.book_score_models import BookScore, BookScoreRepository  # noqa: F401
```
- **`src/services/book_score_models.py` の内容**:
```python
"""BookScore のデータクラスとリポジトリプロトコル定義"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol
from src.infrastructure.database.models.book_score import BookScore as BookScoreModel


@dataclass
class BookScore:
    overall_score: float
    structure_score: float
    coherency_score: float
    factual_grounding_score: float
    visual_textual_synergy_score: float
    reader_experience_score: float
    specialist_breakdown: Optional[Dict[str, Any]] = None

    def lowest_dimension(self) -> str:
        dims = {
            "structure_score": self.structure_score,
            "coherency_score": self.coherency_score,
            "factual_grounding_score": self.factual_grounding_score,
            "visual_textual_synergy_score": self.visual_textual_synergy_score,
            "reader_experience_score": self.reader_experience_score,
        }
        return min(dims, key=dims.get)


class BookScoreRepository(Protocol):
    async def save(self, score: BookScoreModel) -> None: ...
    async def get_latest(self, book_id: int, chapter_number: int) -> Optional[BookScoreModel]: ...
```
- **検証コマンド**:
```powershell
python -c "from src.services.book_score_models import BookScore; s=BookScore(80,75,85,70,65,90); assert s.lowest_dimension()=='visual_textual_synergy_score'; print('Step 18 OK')"
```
- **合否基準**: `Step 18 OK` と出力されること。

---

### Step 19: ruff に G004 ルール追加
- **目的**: f-string ロギング検出ルールを有効化。
- **対象ファイル**: [`pyproject.toml`](file:///e:/hhh/pyproject.toml)
- **編集内容**: `[tool.ruff.lint]` セクションを追加または拡張:
```toml
[tool.ruff.lint]
extend-select = ["G004"]

[tool.ruff.lint.per-file-ignores]
"src/services/vector_store/*.py" = ["G004"]
"src/services/semantic_cache.py" = ["G004"]
"src/services/spice_guard_adapter.py" = ["G004"]
"src/backend/*.py" = ["G004"]
"src/shared/*.py" = ["G004"]
```
- **検証コマンド**:
```powershell
py -m ruff check src/services/retry_decorator.py --select G004
```
- **合否基準**: G004 違反が検出されること（Step 20 で修正）。

---

### Step 20: `retry_decorator.py` の f-string ロギング修正
- **目的**: f-string ロギング6箇所を `%s` 形式に変換。
- **対象ファイル**: [`src/services/retry_decorator.py`](file:///e:/hhh/src/services/retry_decorator.py)
- **編集パターン**:

  **変更前**:
```python
logger.error(f"❌ Fatal LLM error detected. Fail-Fast. Error: {e}")
```
  **変更後**:
```python
logger.error("❌ Fatal LLM error detected. Fail-Fast. Error: %s", e)
```
  対象行: L177, L196, L218, L245, L249 等。
- **検証コマンド**:
```powershell
py -m ruff check src/services/retry_decorator.py --select G004; if ($LASTEXITCODE -eq 0) { Write-Output "Step 20 OK" }
```
- **合否基準**: G004 違反ゼロ。

---

### Step 21: `writing_use_cases.py` の TODO を NotImplementedError に置換
- **目的**: Application 層 UseCase の未実装箇所を明示化。
- **対象ファイル**: [`src/application/use_cases/writing_use_cases.py`](file:///e:/hhh/src/application/use_cases/writing_use_cases.py)
- **編集内容**: L184 の `# TODO: Use plot domain service` と L212-215 の TODO ハードコード値を `raise NotImplementedError(...)` に置換。
- **テストファイル**: `tests/unit/application/test_writing_usecase_not_implemented.py`
```python
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_expand_plot_raises_not_implemented():
    from src.application.use_cases.writing_use_cases import ExpandPlotUseCase
    from src.application.dtos.episode_dto import ExpandPlotDTO
    uc = ExpandPlotUseCase(episode_repo=AsyncMock(), novel_repo=AsyncMock(), uow=AsyncMock())
    with pytest.raises(NotImplementedError):
        await uc.execute(ExpandPlotDTO(novel_id="test", chapter_id="ch", episode_id="ep"))
```
- **検証コマンド**:
```powershell
pytest tests/unit/application/test_writing_usecase_not_implemented.py -o addopts="" --no-cov -v
```
- **合否基準**: テストパス。

---

### Step 22: `branch_use_cases.py` / `audit_use_cases.py` の TODO 修正
- **目的**: 残りの UseCase TODO を `NotImplementedError` に置換。
- **対象ファイル**: [`branch_use_cases.py`](file:///e:/hhh/src/application/use_cases/branch_use_cases.py), [`audit_use_cases.py`](file:///e:/hhh/src/application/use_cases/audit_use_cases.py)
- **編集内容**:
  - `branch_use_cases.py` L40: 親ブランチ検証コメントを pass に（リポジトリ依存のため暫定）
  - `branch_use_cases.py` L140: `raise NotImplementedError("MergeBranchUseCase は未実装")`
  - `audit_use_cases.py`: 4箇所の TODO を同様に処理
- **検証コマンド**:
```powershell
pytest tests/unit/application/ -o addopts="" --no-cov -v 2>&1 | Select-String "passed|error"
```
- **合否基準**: コレクションエラーなし。

---

### Step 23: カバレッジゲート引き上げ（35% → 45%）
- **目的**: デッドコード削除によりカバレッジ母数が減少したため、ゲートを引き上げ。
- **対象ファイル**: [`pyproject.toml`](file:///e:/hhh/pyproject.toml)
- **編集内容**:

  **変更前** (L66):
```toml
addopts = "... --cov-fail-under=35"
```
  **変更後**:
```toml
addopts = "... --cov-fail-under=45"
```
- **検証コマンド**:
```powershell
python -c "t=open('pyproject.toml').read(); assert 'fail-under=45' in t; print('Step 23 OK')"
```
- **合否基準**: `Step 23 OK` と出力されること。

---

### Step 24: 最終統合検証
- **目的**: 全24ステップの変更が既存テストを破壊していないことを確認。
- **実行コマンド**:
```powershell
# 1. Lint
py -m ruff check src tests --fix
# 2. 型チェック
py -m mypy src --ignore-missing-imports
# 3. テスト
py -m pytest -q --tb=short
# 4. カバレッジゲート
py -m pytest --cov=src --cov-report=term-missing --cov-fail-under=45
```
- **合否基準**:
  - ruff: エラーゼロ
  - mypy: Fatal error なし
  - pytest: `passed` のみ
  - カバレッジ: 45% 以上

---

## 📊 期待される改善効果

| 指標 | Before | After | 改善幅 |
|---|---|---|---|
| ルート直下ファイル数 | 66 | ~30 | **-55%** |
| デッドファイル (物理削除) | 100+ omit | 80 omit + 20削除 | **-20件** |
| バージョン不整合 | 3箇所 | 0 | **解消** |
| import時DeprecationWarning | 2モジュール | 0 | **解消** |
| カバレッジゲート | 35% | 45% | **+10pt** |
| API Key → admin 昇格 | あり | なし | **セキュリティ修正** |
| 巨大ファイル (1,000行超) | 5ファイル | 3ファイル | **-2分割** |
| f-string ロギング | 491箇所 | ~485 + ルール導入 | **模範+検出** |

---

## 🔗 関連ドキュメント

- コードレビュー結果: `code_review.md`
- [`plans/P7_COVERAGE_80_PERCENT_12STEPS.md`](file:///e:/hhh/plans/P7_COVERAGE_80_PERCENT_12STEPS.md)
- [`plans/P9_COMPRESSION_REVERSIBILITY_AND_METRICS_18STEPS.md`](file:///e:/hhh/plans/P9_COMPRESSION_REVERSIBILITY_AND_METRICS_18STEPS.md)
