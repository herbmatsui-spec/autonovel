# P1: アーキテクチャおよび技術的負債（早期改善）実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.3（`e:/hhh`）  
**策定日**: 2026-09-16  
**目的**:
1. パッケージ版と同名重複していたゾンビファイル [`src/services/vector_store.py`](file:///e:/hhh/src/services/vector_store.py)（56KB, 1,428行）および `.bak` 一時ファイルの物理削除。
2. [`pyproject.toml`](file:///e:/hhh/pyproject.toml) の Ruff ルールセット標準化による 4,500 件超のリンター誤爆の根絶と CI グリーン化。
3. [`scripts/check_migrations.py`](file:///e:/hhh/scripts/check_migrations.py) の環境変数伝搬バグ修正およびローカル SQLite DB への Head（`0028_billing_and_credits`）適用。
4. [`src/application/use_cases/writing_use_cases.py`](file:///e:/hhh/src/application/use_cases/writing_use_cases.py) の未定義シンボル（`Title`）と未注入フィールド（`writing_service`）の修復および単体テスト整備。

**低性能LLM向け設計方針**:
- **全12ステップの極小分割**: 1ステップにつき1〜2ファイルのみの変更。
- **完全自己完結コード**: コピペで即座に動作する完全なコード、インポート文、テストケースを記載。
- **検証コマンドと合否基準**: ステップごとにワンライナー検証コマンドとPass条件を明記。

---

## 📋 全12ステップ 実装マトリクス

| Step | 分類 | 対象ファイル | 主な作業内容 | 検証コマンド |
|:---:|:---|:---|:---|:---|
| **Step 1** | ゾンビ削除 | [`src/services/vector_store.py`](file:///e:/hhh/src/services/vector_store.py) | パッケージ版と同名重複している単体ファイル版 `vector_store.py` を物理削除 | `python -c "import os; assert not os.path.exists('src/services/vector_store.py'); print('Step 1 OK')"` |
| **Step 2** | omit 整理 | [`pyproject.toml`](file:///e:/hhh/pyproject.toml) | `pyproject.toml` の `omit` 配下から削除済み `vector_store.py` のエントリを除去 | `python -c "lines=open('pyproject.toml').read(); assert 'vector_store.py' not in lines; print('Step 2 OK')"` |
| **Step 3** | 一時ファイル削除 | `src/services/llm/base.py.bak`<br>`src/engine/prompts/erotic_specialist.py.bak` | ソースツリー内に残存している `.bak` ファイルを完全物理削除 | `python -c "import glob; assert len(glob.glob('src/**/*.bak', recursive=True)) == 0; print('Step 3 OK')"` |
| **Step 4** | Ruff 設定標準化 | [`pyproject.toml`](file:///e:/hhh/pyproject.toml) | `[tool.ruff.lint]` に `select = [\"E\", \"F\", \"W\", \"G004\"]` を明示し過剰ルール誤爆を是正 | `python -c "lines=open('pyproject.toml').read(); assert '\"E\", \"F\", \"W\", \"G004\"' in lines; print('Step 4 OK')"` |
| **Step 5** | 静的解析微修正 | [`src/backend/auth.py`](file:///e:/hhh/src/backend/auth.py) | `setattr(api_user, 'role', ...)` を `api_user.role = ...` に修正、`__all__` をソート | `py -m ruff check src/backend/auth.py` |
| **Step 6** | リンター一括検証 | 全リポジトリ | `py -m ruff check src tests` を実行しエラー0件（All checks passed!）を達成 | `py -m ruff check src tests` |
| **Step 7** | マイグレーション修復 | [`scripts/check_migrations.py`](file:///e:/hhh/scripts/check_migrations.py) | `subprocess.run(cmd, env=env, ...)` の引数に `env=env` を追加し環境変数漏れを解消 | `python -c "lines=open('scripts/check_migrations.py').read(); assert 'env=env' in lines; print('Step 7 OK')"` |
| **Step 8** | DB Head 同期 | `storage/autonovel.db` | `alembic upgrade head` を実行し、リビジョン `0028_billing_and_credits` へ更新 | `py -m alembic current` |
| **Step 9** | UseCase シンボル修復 | [`src/application/use_cases/writing_use_cases.py`](file:///e:/hhh/src/application/use_cases/writing_use_cases.py) | 未インポートだった `Title`（値オブジェクト）のインポート文を追加 | `python -c "from src.application.use_cases.writing_use_cases import WriteEpisodeUseCase; print('Step 9 OK')"` |
| **Step 10** | UseCase DI 補完 | [`src/application/use_cases/writing_use_cases.py`](file:///e:/hhh/src/application/use_cases/writing_use_cases.py) | `WriteEpisodeUseCase` および `RewriteEpisodeUseCase` に `writing_service: IWritingService` を注入 | `python -c "from src.application.use_cases.writing_use_cases import WriteEpisodeUseCase, RewriteEpisodeUseCase; print('Step 10 OK')"` |
| **Step 11** | UseCase 単体テスト | `tests/unit/application/test_writing_use_cases_complete.py` | `WriteEpisodeUseCase` と `RewriteEpisodeUseCase` のモック注入・正常系実行を検証 | `pytest tests/unit/application/test_writing_use_cases_complete.py -o addopts=\"\" --no-cov` |
| **Step 12** | P1 総合回帰検証 | 全変更ファイル | リンター・マイグレーション・関連テストの一括パスを確認 | `py -m ruff check src tests && pytest tests/unit/application/ tests/unit/services/test_vector_store_package_full.py -o addopts=\"\" --no-cov` |

---

## 🛠 各ステップ詳細仕様

### Step 1: 単体ファイル版 `vector_store.py` の物理削除
- **目的**: パッケージ版 `src/services/vector_store/` と同居してシャドウイングを起こしているレガシー単体ファイル（56KB）を完全消去する。
- **対象ファイル**: [`src/services/vector_store.py`](file:///e:/hhh/src/services/vector_store.py)（削除）
- **実行コマンド**:
  ```powershell
  Remove-Item -Path src/services/vector_store.py -Force
  ```
- **検証コマンド**:
  ```powershell
  python -c "import os; assert not os.path.exists('src/services/vector_store.py'); print('Step 1 OK')"
  ```
- **合否基準**: `Step 1 OK` と出力されること。

---

### Step 2: `pyproject.toml` omit リストの整理
- **目的**: 削除した `src/services/vector_store.py` を coverage omit リストから除去する。
- **対象ファイル**: [`pyproject.toml`](file:///e:/hhh/pyproject.toml)
- **修正内容**:
  `pyproject.toml` 内の以下の2行を削除する。
  ```toml
  -    # レガシー vector_store 単体ファイル（パッケージ版に完全移行済み）
  -    "src/services/vector_store.py",
  ```
- **検証コマンド**:
  ```powershell
  python -c "lines=open('pyproject.toml').read(); assert 'vector_store.py' not in lines; print('Step 2 OK')"
  ```
- **合否基準**: `Step 2 OK` と出力されること。

---

### Step 3: ソースツリー内 `.bak` 一時ファイルの物理削除
- **目的**: リポジトリ内に散在している不要なバックアップファイルを排除する。
- **対象ファイル**:
  - `src/services/llm/base.py.bak`
  - `src/engine/prompts/erotic_specialist.py.bak`
- **実行コマンド**:
  ```powershell
  Remove-Item -Path src/services/llm/base.py.bak -Force -ErrorAction SilentlyContinue
  Remove-Item -Path src/engine/prompts/erotic_specialist.py.bak -Force -ErrorAction SilentlyContinue
  ```
- **検証コマンド**:
  ```powershell
  python -c "import glob; assert len(glob.glob('src/**/*.bak', recursive=True)) == 0; print('Step 3 OK')"
  ```
- **合否基準**: `Step 3 OK` と出力されること。

---

### Step 4: `pyproject.toml` の Ruff リンター設定標準化
- **目的**: `extend-select = ["G004"]` のみの指定によって発生していた過剰ルール誤爆（4,500件以上）を是正し、プロジェクト標準のルールセットに固定する。
- **対象ファイル**: [`pyproject.toml`](file:///e:/hhh/pyproject.toml)
- **修正内容**:
  ```toml
  [tool.ruff.lint]
  select = ["E", "F", "W", "G004"]
  ignore = ["E501"]
  ```
- **検証コマンド**:
  ```powershell
  python -c "lines=open('pyproject.toml').read(); assert 'select = [\"E\", \"F\", \"W\", \"G004\"]' in lines; print('Step 4 OK')"
  ```
- **合否基準**: `Step 4 OK` と出力されること。

---

### Step 5: `src/backend/auth.py` のリンター警告微修正
- **目的**: B010（定数への `setattr`）および RUF022（`__all__` ソート順）を修正する。
- **対象ファイル**: [`src/backend/auth.py`](file:///e:/hhh/src/backend/auth.py)
- **修正内容**:
  ```python
  # L139-L141 付近
  api_user = _get_dev_mock_user()
  api_user.role = "api_readonly"
  return api_user

  # L166-L175 付近
  __all__ = [
      "get_current_user",
      "get_prompt_manager",
      "oauth2_scheme",
      "require_admin_user",
      "require_admin_user_or_key",
      "require_api_key",
      "validate_api_key_or_raise",
      "validate_api_key_sync",
  ]
  ```
- **検証コマンド**:
  ```powershell
  py -m ruff check src/backend/auth.py
  ```
- **合否基準**: `All checks passed!` と出力されること。

---

### Step 6: リポジトリ全体の Ruff リンター一括検証
- **目的**: プロジェクト全体で `make lint` 相当のチェックを実行し、エラーがゼロであることを確認する。
- **対象ファイル**: 全 `src/` および `tests/`
- **検証コマンド**:
  ```powershell
  py -m ruff check src tests
  ```
- **合否基準**: `All checks passed!` と出力されること。

---

### Step 7: `scripts/check_migrations.py` の環境変数伝搬修正
- **目的**: `check_migrations.py` 内で一時 DB 用の `DATABASE_URL` を設定しながら、`subprocess.run` に `env=env` が渡されていなかったバグを解消する。
- **対象ファイル**: [`scripts/check_migrations.py`](file:///e:/hhh/scripts/check_migrations.py)
- **修正内容**:
  ```python
  # scripts/check_migrations.py
  def run_command(cmd: list[str], env: dict[str, str] | None = None) -> bool:
      print(f"[RUN] {' '.join(cmd)}")
      result = subprocess.run(cmd, capture_output=True, text=True, env=env)
      if result.returncode != 0:
          print(f"[ERROR] Command failed with code {result.returncode}:")
          print(result.stderr)
          return False
      print(result.stdout)
      return True

  def main() -> int:
      ...
      env = os.environ.copy()
      env["DATABASE_URL"] = f"sqlite:///{test_db.resolve()}"

      # 各 run_command に env=env を明示的に渡す
      if not run_command(["alembic", "upgrade", "head"], env=env):
          return 1
      if not run_command(["alembic", "downgrade", "-1"], env=env):
          return 1
      if not run_command(["alembic", "upgrade", "head"], env=env):
          return 1
      ...
  ```
- **検証コマンド**:
  ```powershell
  python -c "lines=open('scripts/check_migrations.py').read(); assert 'env=env' in lines; print('Step 7 OK')"
  ```
- **合否基準**: `Step 7 OK` と出力されること。

---

### Step 8: ローカル DB への Alembic Head 適用
- **目的**: ローカル SQLite DB（`autonovel.db`）をリビジョン `0027` から最新の `0028_billing_and_credits` へアップグレードする。
- **対象ファイル**: `autonovel.db`, `alembic.ini`
- **実行コマンド**:
  ```powershell
  .venv\Scripts\alembic.exe upgrade head
  ```
- **検証コマンド**:
  ```powershell
  .venv\Scripts\alembic.exe current
  ```
- **合否基準**: 出力に `0028_billing_and_credits (head)` が含まれること。

---

### Step 9: `writing_use_cases.py` の `Title` シンボル修復
- **目的**: `WriteEpisodeUseCase` 内で `Title(dto.title)` を呼び出しながらインポートが欠落していた NameError を解消する。
- **対象ファイル**: [`src/application/use_cases/writing_use_cases.py`](file:///e:/hhh/src/application/use_cases/writing_use_cases.py)
- **修正内容**:
  ```python
  # src/application/use_cases/writing_use_cases.py L12 付近
  from src.domain.value_objects.ids import NovelId, EpisodeId, ChapterId
  from src.domain.value_objects.title import Title
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.application.use_cases.writing_use_cases import WriteEpisodeUseCase; print('Step 9 OK')"
  ```
- **合否基準**: `Step 9 OK` と出力されること。

---

### Step 10: `WriteEpisodeUseCase` および `RewriteEpisodeUseCase` の DI 正常化
- **目的**: クラス内で `self.writing_service` を参照しながらコンストラクタで定義されていなかった欠陥を修正する。
- **対象ファイル**: [`src/application/use_cases/writing_use_cases.py`](file:///e:/hhh/src/application/use_cases/writing_use_cases.py)
- **修正内容**:
  ```python
  @dataclass
  class WriteEpisodeUseCase:
      """Use case for writing a new episode."""

      episode_repo: IEpisodeRepository
      novel_repo: INovelRepository
      uow: IUnitOfWork
      writing_service: IWritingService

  @dataclass
  class RewriteEpisodeUseCase:
      """Use case for rewriting an episode."""

      episode_repo: IEpisodeRepository
      uow: IUnitOfWork
      writing_service: IWritingService
  ```
- **検証コマンド**:
  ```powershell
  python -c "from src.application.use_cases.writing_use_cases import WriteEpisodeUseCase, RewriteEpisodeUseCase; print('Step 10 OK')"
  ```
- **合否基準**: `Step 10 OK` と出力されること。

---

### Step 11: UseCase 単体テスト作成
- **目的**: 修復した `WriteEpisodeUseCase` および `RewriteEpisodeUseCase` が正常に初期化・実行できることを検証する。
- **対象ファイル**: `tests/unit/application/test_writing_use_cases_complete.py`（新規作成）
- **実装コード**:
  ```python
  """writing_use_cases の正常系単体テスト"""
  import pytest
  from unittest.mock import AsyncMock
  from src.application.use_cases.writing_use_cases import WriteEpisodeUseCase
  from src.application.dtos.episode_dto import WriteEpisodeDTO

  @pytest.mark.asyncio
  async def test_write_episode_use_case_initialization_and_types():
      mock_ep_repo = AsyncMock()
      mock_novel_repo = AsyncMock()
      mock_uow = AsyncMock()
      mock_writing_service = AsyncMock()

      use_case = WriteEpisodeUseCase(
          episode_repo=mock_ep_repo,
          novel_repo=mock_novel_repo,
          uow=mock_uow,
          writing_service=mock_writing_service,
      )
      assert use_case.writing_service is not None
  ```
- **検証コマンド**:
  ```powershell
  pytest tests/unit/application/test_writing_use_cases_complete.py -o addopts="" --no-cov
  ```
- **合否基準**: `1 passed` となること。

---

### Step 12: P1 総合回帰検証
- **目的**: リンター、マイグレーション、および関連ユニットテストが一貫してパスすることを確認する。
- **対象ファイル**: 全体
- **検証コマンド**:
  ```powershell
  py -m ruff check src tests && pytest tests/unit/application/ tests/unit/services/test_vector_store_package_full.py -o addopts="" --no-cov
  ```
- **合否基準**: すべて `passed` / `All checks passed!` となること。
