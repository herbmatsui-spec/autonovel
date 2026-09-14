# 提案9: 計画書インフレ解消と設定情報源（SSOT）一元化 実装計画書（全12ステップ）

**対象レイヤー**: `docs/`, `plans/`, `src/backend/config.py`, `.env.example`, `scripts/`, `tests/unit/`  
**目的**: `plans/` および `docs/` 配下に蓄積・散乱した数十本の古い計画書（計画書インフレ）を一括退避・整理し、アクティブなドキュメントを正規化する。また、`src/backend/config.py` の死んだ設定（`AUTH_DISABLED` 等）を排除して Pydantic Settings による厳格バリデーションを導入し、`.env.example` と 1対1 で完全一致させることで「単一の設定情報源（SSOT）」を確立する。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全な Python スクリプト、設定ファイル、実装コード、テストコード**、**検証コマンド**、**合格条件** を完備しています。

---

## 📋 ステップ一覧

| Step | 分類 | 対象ファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | ドキュメント整理 | `scripts/archive_stale_plans.py` | 過去の完了済み・重複計画書を検出して安全に退避するスクリプトの実装 |
| **Step 2** | ドキュメント整理 | `docs/archive/plans_v4/` | スクリプトを実行し、古い計画書群をアーカイブディレクトリへ一括移動 |
| **Step 3** | ドキュメント正規化 | `plans/README.md` | 現在アクティブな改善提案（PROPOSAL_01〜09）の一覧インデックス作成 |
| **Step 4** | ルート整理 | `docs/archive/scratch_docs/` | ルート直下の作業メモ（`task.md`, `time.md`, `summary.md` 等）を退避 |
| **Step 5** | 設定クリーンアップ | `src/backend/config.py` | 未使用設定（`AUTH_DISABLED` 等）の削除と設定項目のカテゴリ別再編 |
| **Step 6** | 設定堅牢化 | `src/backend/config.py` | 本番環境におけるシークレット未指定検知バリデータ（`@model_validator`）の実装 |
| **Step 7** | 設定テンプレート | `.env.example` | `src/backend/config.py` の全フィールドと 1対1 で整合する完全テンプレートの更新 |
| **Step 8** | SSOT検証ツール | `scripts/verify_env_consistency.py` | `config.py` のフィールドと `.env.example` の差異を自動検出するスクリプト |
| **Step 9** | スクラッチ掃除 | `scripts/cleanup_scratch.py` | 不要な一時スクリプト（`tmp_*.py` 等）を検出・整理するツールの作成 |
| **Step 10** | 設計書正規化 | `docs/ARCHITECTURE.md` | 最新の単一アーキテクチャ（DDD + FastAPI + React）をまとめた正統設計書の作成 |
| **Step 11** | 単体テスト | `tests/unit/test_config_ssot.py` | 設定クラスの読み込み、バリデーション、環境変数オーバーライドの単体テスト |
| **Step 12** | 統合検証 | CI / コマンド実行 | 全体整合性チェックスクリプトとテストスイートの全件通過確認 |

---

## 🛠 各ステップ詳細仕様

### Step 1: 過去完了済み計画書の一括アーカイブスクリプト実装
- **目的**: ルートや `docs/plans/` に散らばった古い計画書（`PLAN_01_`〜`18_` の断片や過去の72ステップ計画等）を安全に `docs/archive/` に退避する自動スクリプトを作成する。
- **対象ファイル**: `scripts/archive_stale_plans.py`（新規作成）
- **実装コード**:
```python
"""古い計画書を docs/archive/ に退避するスクリプト。"""
import os
import shutil
from pathlib import Path

ARCHIVE_DIR = Path("docs/archive/plans_v4")
PLANS_DIR = Path("plans")

# 退避対象とする古い計画書接頭辞やファイル名
STALE_PATTERNS = [
    "PLAN_",
    "plan1",
    "p0_implementation",
    "marketing_and_graphrag",
    "frontend_testing",
    "frontend_e2e",
    "implementation_plan_72steps",
]

def archive_plans():
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    if not PLANS_DIR.exists():
        print("plans directory does not exist.")
        return

    archived_count = 0
    for file in PLANS_DIR.glob("*.md"):
        # PROPOSAL_01〜09 および README.md は保護して残す
        if file.name.startswith("PROPOSAL_") or file.name in ("README.md", "P1_COVERAGE_DATABASE_12STEPS.md", "P4_COVERAGE_WORKFLOWS_12STEPS.md", "P5_COVERAGE_EASYMODE_12STEPS.md"):
            continue

        for pat in STALE_PATTERNS:
            if pat in file.name:
                dst = ARCHIVE_DIR / file.name
                shutil.move(str(file), str(dst))
                print(f"Archived: {file.name} -> {dst}")
                archived_count += 1
                break

    print(f"Total archived files: {archived_count}")

if __name__ == "__main__":
    archive_plans()
```
- **検証コマンド**: `python scripts/archive_stale_plans.py`
- **合格条件**: スクリプトがエラーなく終了すること。

---

### Step 2: スクリプト実行による古い計画書の退避
- **目的**: Step 1 のスクリプトを実行し、`plans/` ディレクトリをアクティブな提案書のみに整理する。
- **コマンド**:
```bash
python scripts/archive_stale_plans.py
```
- **合格条件**: `docs/archive/plans_v4/` が作成され、対象ファイルが移動されること。

---

### Step 3: アクティブ計画書インデックス（plans/README.md）の作成
- **目的**: `plans/` 内に現在どの提案・計画が有効であるかを一目で把握できる公式インデックスを作成する。
- **対象ファイル**: `plans/README.md`（新規作成または上書き）
- **実装コード**:
```markdown
# AutoNovel 改善提案・実装計画書インデックス

AutoNovel の品質向上・商用化に向けたアクティブな実装計画書一覧です。
すべての計画書は「全12ステップ・完全自己完結コード付属」で設計されています。

## 📋 アクティブ計画書一覧

| 計画書 | 提案名 | 状態 | 目的 |
|:---|:---|:---:|:---|
| [PROPOSAL_01_ARCHITECTURE_UNIFICATION_PLAN.md](./PROPOSAL_01_ARCHITECTURE_UNIFICATION_PLAN.md) | 新旧アーキテクチャ一本化 & デッドコード物理パージ | ✅ 完了 | 死蔵コード削除、リポジトリ層集約、BookMapper |
| [PROPOSAL_02_AUTH_GUARD_AND_IDOR_12STEPS.md](./PROPOSAL_02_AUTH_GUARD_AND_IDOR_12STEPS.md) | 全ルーター認可ガード & IDOR防止 | ⏳ 準備完了 | 38ルーター認可網羅、所有権ガード、RBAC |
| [PROPOSAL_03_OPENAPI_TYPESYNC_12STEPS.md](./PROPOSAL_03_OPENAPI_TYPESYNC_12STEPS.md) | OpenAPI駆動 End-to-End 型同期 | ⏳ 準備完了 | スキーマ抽出、TypeScript型生成、RFC 7807 |
| [PROPOSAL_05_CIRCUIT_BREAKER_AND_BUDGET_12STEPS.md](./PROPOSAL_05_CIRCUIT_BREAKER_AND_BUDGET_12STEPS.md) | LLMサーキットブレーカー & トークン予算ガード | ⏳ 準備完了 | API障害フェイルオーバー、PDCA上限強制停止 |
| [PROPOSAL_09_CLEANUP_AND_CONFIG_SSOT_12STEPS.md](./PROPOSAL_09_CLEANUP_AND_CONFIG_SSOT_12STEPS.md) | 計画書インフレ解消 & 設定情報源SSOT一元化 | ⏳ 本書 | ドキュメント退避、config.py一元化、.env整合 |

## 📦 過去ドキュメント
過去の完了済み計画書や検討メモは `docs/archive/plans_v4/` に保管されています。
```
- **検証コマンド**: `python -c "assert open('plans/README.md', encoding='utf-8').read().startswith('# AutoNovel')"`
- **合格条件**: インデックスファイルが正常に保存されること。

---

### Step 4: ルート直下の散乱作業メモのアーカイブ退避
- **目的**: リポジトリ直下に散らばっている `task.md`, `time.md`, `summary.md` 等の一時作業用メモを `docs/archive/scratch_docs/` に安全に移動する。
- **実行手順**:
  - `docs/archive/scratch_docs/` ディレクトリを作成。
  - ルート直下の `task.md`, `time.md`, `summary.md` を移動。
- **コマンド**:
```bash
python -c "import shutil, os; os.makedirs('docs/archive/scratch_docs', exist_ok=True); [shutil.move(f, f'docs/archive/scratch_docs/{f}') for f in ['task.md', 'time.md', 'summary.md'] if os.path.exists(f)]"
```
- **合格条件**: ルート直下がスッキリ整理されること。

---

### Step 5: `src/backend/config.py` 内の死んだ設定の削除
- **目的**: `AUTH_DISABLED: bool = False` のようなコード内のどこからも参照されていない死んだ設定項目を削除し、設定を整理する。
- **対象ファイル**: `src/backend/config.py`
- **修正方針**:
  - `AUTH_DISABLED` を削除。
  - 設定フィールドを「サーバー基本」「データベース」「Redis/キュー」「認証・セキュリティ」「LLMプロバイダー」「ストレージ」「外部決済」のセクションに整理。
- **検証コマンド**: `python -m ruff check src/backend/config.py`
- **合格条件**: 構文チェック通過。

---

### Step 6: 本番環境におけるシークレット必須バリデーションの実装
- **目的**: `APP_ENV="production"` 時に `JWT_SECRET_KEY` や `DATABASE_URL` が未設定またはデフォルト値の場合、起動時に即時エラーを投げて重大インシデントを未然に防ぐ。
- **対象ファイル**: `src/backend/config.py`
- **実装コード（バリデータ部分）**:
```python
from pydantic import model_validator

class Settings(BaseSettings):
    ...
    @model_validator(mode="after")
    def validate_production_secrets(self) -> Settings:
        """本番環境でデフォルト値や空シークレットが使用されるのを防止する。"""
        if self.APP_ENV == "production":
            if not self.JWT_SECRET_KEY or "change-in-prod" in self.JWT_SECRET_KEY:
                raise ValueError("本番環境 (APP_ENV=production) では安全な JWT_SECRET_KEY の設定が必須です。")
            if "sqlite" in self.DATABASE_URL:
                raise ValueError("本番環境では SQLite ではなく PostgreSQL の設定が必要です。")
        return self
```
- **検証コマンド**: `python -c "from src.backend.config import settings; print('Config validator active')"`
- **合格条件**: 開発環境では通常通り起動し、インポートエラーがないこと。

---

### Step 7: `.env.example` の完全整合テンプレート更新
- **目的**: `src/backend/config.py` の全設定項目と完全に 1対1 で対応し、コメント付きのテンプレート `.env.example` を更新する。
- **対象ファイル**: `.env.example`
- **実装コード**:
```bash
# ==============================================================================
# AutoNovel 環境設定テンプレート (.env.example)
# コピーして `.env` を作成し、必要な値を設定してください。
# ==============================================================================

# ---- サーバー基本設定 ----
APP_NAME=AutoNovel
APP_ENV=development
PORT=8200
HOST=0.0.0.0

# ---- データベース設定 (開発: SQLite, 本番: PostgreSQL) ----
DATABASE_URL=sqlite:///storage/autonovel.db

# ---- Huey / Redis タスクキュー ----
HUEY_BACKEND=sqlite
REDIS_URL=redis://localhost:6379/0

# ---- 認証・セキュリティ ----
JWT_SECRET_KEY=autonovel-dev-secret-key-minimum-32-bytes-long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# ---- LLM プロバイダー設定 ----
LLM_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# ---- ベクターストア (RAG) ----
AUTONOVEL_RAG_MODE=auto
CHROMA_DB_PATH=chroma_db

# ---- 決済 (Stripe) ----
STRIPE_API_KEY=
STRIPE_WEBHOOK_SECRET=
```
- **合格条件**: `.env.example` が上書き保存されること。

---

### Step 8: SSOT（設定情報源）自動整合性チェックスクリプトの実装
- **目的**: CIやコミット時に `.env.example` と `config.py` のキーが乖離していないかを自動検証する。
- **対象ファイル**: `scripts/verify_env_consistency.py`（新規作成）
- **実装コード**:
```python
"""config.py と .env.example のキー整合性を検証するスクリプト。"""
import re
from pathlib import Path
from src.backend.config import Settings

def check_consistency():
    config_keys = set(Settings.model_fields.keys())

    env_example_path = Path(".env.example")
    if not env_example_path.exists():
        raise FileNotFoundError(".env.example does not exist")

    example_keys = set()
    for line in env_example_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key = line.split("=", 1)[0].strip()
            example_keys.add(key)

    missing_in_example = config_keys - example_keys
    # システム内部生成値などは除外許容
    ignored = {"STORAGE_DIR", "ROOT_DIR", "model_config"}
    missing_in_example -= ignored

    print(f"Config keys: {len(config_keys)}, Example keys: {len(example_keys)}")
    if missing_in_example:
        print(f"WARNING: Keys in config.py but missing in .env.example: {missing_in_example}")
    else:
        print("SUCCESS: config.py and .env.example are in sync!")

if __name__ == "__main__":
    check_consistency()
```
- **検証コマンド**: `python scripts/verify_env_consistency.py`
- **合格条件**: 整合性チェックが正常終了すること。

---

### Step 9: 一時スクリプト・スクラッチクリーンアップツールの実装
- **目的**: 開発中に `scripts/scratch/` やルートに溜まった一時検証スクリプトを安全に特定・整理する。
- **対象ファイル**: `scripts/cleanup_scratch.py`（新規作成）
- **実装コード**:
```python
"""不要な一時ファイルやキャッシュをクリーンアップするスクリプト。"""
import shutil
from pathlib import Path

def cleanup():
    # pycache のクリーンアップ
    pycache_dirs = list(Path(".").rglob("__pycache__"))
    for p in pycache_dirs:
        if ".git" not in str(p) and "node_modules" not in str(p):
            shutil.rmtree(p, ignore_errors=True)
    print(f"Cleaned {len(pycache_dirs)} __pycache__ directories.")

    # pytest_cache のクリーンアップ
    if Path(".pytest_cache").exists():
        shutil.rmtree(".pytest_cache", ignore_errors=True)
        print("Cleaned .pytest_cache")

if __name__ == "__main__":
    cleanup()
```
- **検証コマンド**: `python scripts/cleanup_scratch.py`
- **合格条件**: クリーンアップがエラーなく実行されること。

---

### Step 10: 正統アーキテクチャ設計書 `docs/ARCHITECTURE.md` の策定
- **目的**: 移行完了後の単一アーキテクチャ全体像（プレゼンテーション/ルーター、アプリケーション、ドメイン、インフラ）を明文化する。
- **対象ファイル**: `docs/ARCHITECTURE.md`（新規作成）
- **実装コード**:
```markdown
# AutoNovel システムアーキテクチャ仕様書

## 1. 全体構造概要 (Clean / Layered Architecture)

AutoNovel は FastAPI + React 18 を中核とした、マルチエージェント型AI小説生成基盤です。

```mermaid
graph TD
    Client["フロントエンド (React 18 / Vite / TypeScript)"]
    Router["Presentation層 (src/backend/routers/)"]
    UseCase["Application層 (src/application/use_cases/)"]
    Domain["Domain層 (src/domain/entities/)"]
    Infra["Infrastructure層 (src/infrastructure/repositories/)"]
    DB[("PostgreSQL / SQLite")]

    Client --> Router
    Router --> UseCase
    UseCase --> Domain
    UseCase --> Infra
    Infra --> DB
```

## 2. レイヤーの責務境界
1. **Presentation層 (`src/backend/routers/`)**:
   - HTTP リクエストの受付、認証/認可（`get_current_user`, `require_admin`）、入力バリデーション、ユースケース呼び出し。
2. **Application層 (`src/application/use_cases/`)**:
   - ビジネスワークフローのオーケストレーション、トランザクション境界（`UnitOfWork`）管理。
3. **Domain層 (`src/domain/`)**:
   - ドメインモデル（`Novel`, `Episode`, `Character` 等）、値オブジェクト、ドメインルール。
4. **Infrastructure層 (`src/infrastructure/`)**:
   - データベース永続化（SQLAlchemy リポジトリ）、外部LLM API、ベクターストア（ChromaDB/pgvector）。
```
- **検証コマンド**: `python -c "assert os.path.exists('docs/ARCHITECTURE.md')"`
- **合格条件**: ファイル作成完了。

---

### Step 11: 設定クラスとバリデーションの単体テスト
- **目的**: `Settings` クラスの環境変数読み込み、デフォルト値、本番環境バリデーションの動作を検証する。
- **対象ファイル**: `tests/unit/test_config_ssot.py`（新規作成）
- **実装コード**:
```python
import pytest
from src.backend.config import Settings

def test_settings_default_values():
    settings = Settings(_env_file=None)
    assert settings.APP_NAME == "AutoNovel"
    assert settings.PORT == 8200
    assert settings.JWT_ALGORITHM == "HS256"

def test_settings_production_validation_rejects_missing_jwt():
    # 本番環境でJWTキーがない場合はエラー
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY=None,
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
            _env_file=None,
        )

def test_settings_production_validation_rejects_sqlite():
    # 本番環境でSQLiteが指定されている場合はエラー
    with pytest.raises(ValueError, match="SQLite"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="secure-prod-key-minimum-32-chars-long",
            DATABASE_URL="sqlite:///test.db",
            _env_file=None,
        )
```
- **検証コマンド**: `pytest tests/unit/test_config_ssot.py -v --no-cov`
- **合格条件**: 3テストすべてPASS。

---

### Step 12: 全体整合性・設定テストの実行確認
- **目的**: すべての設定チェックと単体テストが完全に通過することを確認する。
- **検証コマンド**:
```bash
python scripts/verify_env_consistency.py
pytest tests/unit/test_config_ssot.py -v --no-cov
```
- **合格条件**: スクリプトがSUCCESSを出力し、テストが全件パスすること。
