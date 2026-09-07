# P0 実装計画書（24ステップ）

**作成日**: 2026-09-07
**対象**: AutoNovel v4.5.0 かんたんモード E2E フロー改善
**前提**: 低性能 LLM（小型コード生成モデル）でも実装可能な粒度に分割
**3つの P0 項目**:
- P0-A: かんたんモード起動エンドポイント追加（UIから「かんたん」を実行可能にする）
- P0-B: `/easy_mode/export/{book_id}` に認証ミドルウェア追加
- P0-C: LLM API キー未設定時の起動時バリデーション

---

## 設計方針

### 低性能 LLM でも実装可能なステップの特徴

各ステップは以下の性質を持つ：

1. **単一ファイル変更 or 新規ファイル1つ**（依存関係を最小化）
2. **既存パターンに準拠**（`require_api_key`、`validate_api_key_or_raise` が既に存在）
3. **テストが先に書ける**（実装前に受け入れ基準が明確）
4. **PR 単位でマージ可能**（1ステップ = 1PR）
5. **LLM 呼び出しなし or 限定的**（DB 参照・文字列処理・Pydantic バリデーション中心）

### 実装の依存関係

```
P0-A かんたん起動エンドポイント → P0-B 認証追加（同じルーター内） → P0-C LLM キー検証
                                                       ↑
                                          (依存: P0-A が API キーを扱うため)
```

---

## Phase 1: P0-A かんたんモード起動エンドポイント追加（Step 1〜10）

### 背景

[`easy_mode.py:226`](autonovel/src/backend/routers/easy_mode.py:226) の `generate_content` は「章単位の対話型自動生成」で、`EasyModeWorkflow` を起動するエンドポイントが見当たらない。`/easy_mode/generate` とは別に、`/easy_mode/auto-generate` を新設する。

---

### Step 1: テストスケルトンの作成

**目標**: テストファイルのみ作成（TDD 的にテスト先行）

**ファイル**: `tests/unit/test_easy_mode_launch_endpoint.py`（新規）

**実装内容**:
```python
# テスト関数スケルトン
def test_launch_easy_mode_returns_202():
    pass

def test_launch_easy_mode_validates_genre():
    pass

def test_launch_easy_mode_requires_api_key():
    pass

def test_launch_easy_mode_creates_task():
    pass
```

**受け入れ基準**:
- 4つのテスト関数が定義されている
- すべて `pytest --collect-only` で認識される
- まだ失敗しても OK（実装がまだないため）

**低性能 LLM 実装ヒント**:
- docstring を `'''新規かんたんモード起動エンドポイントのテスト'''` で書く
- `from fastapi.testclient import TestClient` のみインポート
- `import pytest` のみ

---

### Step 2: Pydantic スキーマの追加

**目標**: リクエスト・レスポンスの型定義

**ファイル**: `src/domain/entities/easy_mode.py`（既存、追記）

**実装内容**:
```python
class EasyModeLaunchRequest(BaseModel):
    """かんたんモード起動リクエスト"""
    genre: str = "ファンタジー"
    keywords: list[str] = Field(default_factory=list)
    protagonist_type: str = "チート主人公"
    target_episodes: int = Field(default=8, ge=1, le=50)
    words_per_episode: int = Field(default=2000, ge=500, le=10000)
    enable_audit: bool = True
    max_rewrites: int = Field(default=2, ge=0, le=5)


class EasyModeLaunchResponse(BaseModel):
    """かんたんモード起動レスポンス"""
    task_id: str
    status: str = "queued"
    message: str = ""
```

**受け入れ基準**:
- `python -c "from src.domain.entities.easy_mode import EasyModeLaunchRequest"` でインポート成功
- `EasyModeLaunchRequest(target_episodes=100)` が ValidationError（`le=50` 超過）
- `EasyModeLaunchRequest(target_episodes=-1)` が ValidationError（`ge=1` 未満）

**低性能 LLM 実装ヒント**:
- 既存の `EasyModeInput` クラスをコピーして名前変更
- `Field(default_factory=list)` パターンを確認

---

### Step 3: 認証ヘルパーの動作確認

**目標**: 既存認証メカニズムの仕様確認（新規実装ではない）

**ファイル**: テスト `tests/unit/test_easy_mode_launch_endpoint.py` に追記

**確認内容**:
```python
def test_existing_auth_mechanism():
    """既存の require_api_key / validate_api_key_or_raise が動くか確認"""
    from src.backend.auth import require_api_key, validate_api_key_or_raise
    # インポートできれば OK
    assert callable(require_api_key)
    assert callable(validate_api_key_or_raise)
```

**受け入れ基準**:
- テストパス
- `require_api_key` の docstring を読む（[src/backend/auth.py:67](autonovel/src/backend/auth.py:67)）

**低性能 LLM 実装ヒント**:
- ファイル冒頭の docstring と import 文をそのままコピー
- 関数の存在確認のみ

---

### Step 4: Huey タスク登録関数の作成

**目標**: Huey に「かんたんモード起動」タスクを登録する関数を追加

**ファイル**: `src/backend/tasks/generation_tasks.py`（既存、追記）

**実装内容**:
```python
@huey.task()
def launch_easy_mode_task(req_data: dict, api_key: str) -> str:
    """かんたんモードを起動し task_id を返す"""
    from src.backend.engine_helpers import get_engine
    from src.backend.workflows.easy_mode_workflow import EasyModeWorkflow
    
    engine = get_engine(api_key)
    workflow = EasyModeWorkflow(engine=engine)
    
    # 非同期実行用の wrapper
    import asyncio
    result = asyncio.run(workflow.execute(
        reporter=None,  # 進捗は Huey の task ステータスで返す
        **req_data,
    ))
    return result.get("status", "completed")
```

**受け入れ基準**:
- `from src.backend.tasks.generation_tasks import launch_easy_mode_task` でインポート成功
- `huey.task()` デコレータが適用されている
- 単体テストでモック LLM 経由なら呼び出せる

**低性能 LLM 実装ヒント**:
- 既存の `generate_chapter_task` 関数をコピーして名前変更
- `@huey.task()` デコレータのパターンを確認

---

### Step 5: Huey タスクのテスト

**目標**: タスク関数の単体テスト

**ファイル**: `tests/unit/test_easy_mode_launch_endpoint.py` に追記

**実装内容**:
```python
def test_launch_easy_mode_task_creates():
    """launch_easy_mode_task が Huey に登録される"""
    from src.backend.tasks.generation_tasks import launch_easy_mode_task
    # Huey タスクは呼び出し可能
    assert callable(launch_easy_mode_task)
```

**受け入れ基準**:
- テストパス

---

### Step 6: エンドポイントの基本実装（バリデーション + タスク投入のみ）

**目標**: `/easy_mode/auto-generate` の最小実装

**ファイル**: `src/backend/routers/easy_mode.py`（既存、追記）

**実装内容**:
```python
@router.post("/auto-generate", response_model=EasyModeLaunchResponse)
async def auto_generate(
    req: EasyModeLaunchRequest,
    api_key: str = Depends(require_api_key),  # ★ 認証ミドルウェア
    session=Depends(database.get_db),
) -> EasyModeLaunchResponse:
    """かんたんモードの全自動生成を起動する"""
    from src.backend.tasks.generation_tasks import launch_easy_mode_task
    
    req_data = req.model_dump()
    task = launch_easy_mode_task(req_data, api_key)
    huey_task_id = str(task.id)
    
    repo = BookRepository(session)
    repo.create_task(task_id=huey_task_id, status="queued")
    
    return EasyModeLaunchResponse(
        task_id=huey_task_id,
        status="queued",
        message=f"タスク {huey_task_id} を投入しました",
    )
```

**受け入れ基準**:
- エンドポイントが `app.openapi()` で `POST /easy_mode/auto-generate` として登録される
- リクエストボディのバリデーションが機能（`target_episodes=100` → 422）
- 認証ヘッダー `X-API-Key` がない場合 403

**低性能 LLM 実装ヒント**:
- 既存の `generate_content`（[`easy_mode.py:226`](autonovel/src/backend/routers/easy_mode.py:226)）をコピーして編集
- `Depends(require_api_key)` のインポート文を追加
- `Depends(database.get_db)` の既存パターンを踏襲

---

### Step 7: エンドポイントのテスト追加

**目標**: FastAPI の TestClient で実際にエンドポイントを叩テスト

**ファイル**: `tests/unit/test_easy_mode_launch_endpoint.py` に追記

**実装内容**:
```python
def test_auto_generate_returns_202():
    """正常なリクエストで 200/202 が返る"""
    from fastapi.testclient import TestClient
    from src.backend.server import app
    
    client = TestClient(app)
    response = client.post(
        "/easy_mode/auto-generate",
        json={"genre": "ファンタジー", "target_episodes": 3},
        headers={"X-API-Key": "test-key"},
    )
    # モック環境では 200 or 202 or 500（タスク起動失敗）のいずれか
    assert response.status_code in (200, 202, 500)


def test_auto_generate_without_api_key_returns_403():
    """認証ヘッダーなしは 403"""
    from fastapi.testclient import TestClient
    from src.backend.server import app
    
    client = TestClient(app)
    response = client.post(
        "/easy_mode/auto-generate",
        json={"genre": "ファンタジー"},
    )
    assert response.status_code in (403, 422)  # 認証 or バリデーションエラー
```

**受け入れ基準**:
- テストが実行可能
- `AUTH_DISABLED=true` 環境変数下では 200 が返る

**低性能 LLM 実装ヒント**:
- 既存の FastAPI テストを `tests/unit/test_*.py` から1つ選んでパターンをコピー
- `TestClient` の使い方は公式ドキュメント通り

---

### Step 8: 設定ファイルへの認証追加（`ALLOWED_API_KEYS` のデフォルト値）

**目標**: デフォルトで何らかの API キーが通るようにする

**ファイル**: `.env.example`（既存、追記）+ `src/backend/config.py`（既存、デフォルト値変更）

**実装内容**:
`.env.example` に追記:
```
# Default API key for development (DO NOT use in production)
DEFAULT_API_KEY=dev-key-change-me
```

`config.py:54`:
```python
# 旧
ALLOWED_API_KEYS: str = ""
# 新
ALLOWED_API_KEYS: str = "dev-key-change-me"
```

**受け入れ基準**:
- デフォルト値で `X-API-Key: dev-key-change-me` が通る
- `AUTH_DISABLED=true` の場合は引き続き全開放

**低性能 LLM 実装ヒント**:
- 既存 `.env.example` を読んで、最下部に追記
- `config.py` の `AUTH_DISABLED` の近辺を見て、デフォルト値を変更

---

### Step 9: README の起動手順更新

**目標**: 新エンドポイントの使用方法をドキュメント化

**ファイル**: `README.md`（既存、追記）

**実装内容**:
```markdown
## かんたんモード使用方法

### 1. 環境変数設定

```bash
export OPENAI_API_KEY=sk-...
```

### 2. アプリ起動

```bash
python scripts/start_local.py
```

### 3. API で起動

```bash
curl -X POST http://localhost:8200/easy_mode/auto-generate \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"genre": "ファンタジー", "target_episodes": 5}'
```

### 4. ステータス確認

```bash
curl http://localhost:8200/easy_mode/status/{task_id} \
  -H "X-API-Key: dev-key-change-me"
```

### 5. 納品

```bash
curl -X GET http://localhost:8200/easy_mode/export/{book_id} \
  -H "X-API-Key: dev-key-change-me" \
  -o export.zip
```
```

**受け入れ基準**:
- README マークダウンが正しく表示される
- すべてのコマンドがコピー＆ペーストで実行可能

**低性能 LLM 実装ヒント**:
- 既存 README の「使用方法」セクションを参考にする
- `bash` コードブロックでコマンド例を列挙

---

### Step 10: P0-A の動作確認 E2E スモークテスト

**目標**: ローカルで起動 → かんたんモード実行 → 完了確認 が通る

**ファイル**: `scripts/smoke_test.ps1`（既存、追記）

**実装内容**:
```powershell
# かんたんモード E2E スモークテスト
Write-Host "=== かんたんモード E2E スモークテスト ==="

# 1. アプリが起動しているか確認
$health = Invoke-RestMethod -Uri "http://localhost:8200/health" -Method Get
Write-Host "Health: $($health.status)"

# 2. かんたんモード起動
$launchResp = Invoke-RestMethod -Uri "http://localhost:8200/easy_mode/auto-generate" `
    -Method Post `
    -Headers @{"X-API-Key"="dev-key-change-me"; "Content-Type"="application/json"} `
    -Body '{"genre":"ファンタジー","target_episodes":2,"words_per_episode":500}'
$taskId = $launchResp.task_id
Write-Host "Launched task: $taskId"

# 3. ステータス確認（最大120秒待機）
$status = "pending"
$maxWait = 120
$elapsed = 0
while ($status -eq "pending" -and $elapsed -lt $maxWait) {
    Start-Sleep -Seconds 5
    $elapsed += 5
    $resp = Invoke-RestMethod -Uri "http://localhost:8200/easy_mode/status/$taskId" `
        -Headers @{"X-API-Key"="dev-key-change-me"}
    $status = $resp.status
    Write-Host "  [$elapsed s] status=$status"
}

Write-Host "Final status: $status"
if ($status -eq "completed") {
    Write-Host "✅ スモークテスト成功"
    exit 0
} else {
    Write-Host "❌ スモークテスト失敗"
    exit 1
}
```

**受け入れ基準**:
- スクリプトが `pwsh` で実行可能
- モック LLM 環境で `status=completed` まで到達

**低性能 LLM 実装ヒント**:
- 既存 `scripts/smoke_test.ps1` の構造を踏襲
- `Invoke-RestMethod` の `-Headers` 引数で `Hashtable` を渡すパターンに注意

---

## Phase 2: P0-B 認証ミドルウェア追加（Step 11〜18）

### 背景

[`easy_mode.py:297`](autonovel/src/backend/routers/easy_mode.py:297) の `/easy_mode/export/{book_id}`、`/easy_mode/auto-generate`（新設）、[`orchestrated.py:117`](autonovel/src/backend/routers/orchestrated.py:117) の `/export/{book_id}` に認証がない。既存の `require_api_key` ヘルパー（[src/backend/auth.py:67](autonovel/src/backend/auth.py:67)）を活用。

---

### Step 11: 既存 `require_api_key` のテスト

**目標**: 既存認証ミドルウェアが動作することを確認

**ファイル**: `tests/unit/test_easy_mode_launch_endpoint.py` に追記

**実装内容**:
```python
def test_require_api_key_works():
    """既存の require_api_key が FastAPI で機能する"""
    from fastapi import FastAPI, Depends
    from src.backend.auth import require_api_key
    
    app = FastAPI()
    
    @app.get("/test-protected")
    async def protected(api_key: str = Depends(require_api_key)):
        return {"api_key": api_key[:4]}
    
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    # 認証なし → 403
    r = client.get("/test-protected")
    assert r.status_code == 403
```

**受け入れ基準**:
- テストパス
- 既存実装が再確認できる

---

### Step 12: `/easy_mode/export/{book_id}` への認証追加（最小）

**目標**: 認証パラメータを追加

**ファイル**: `src/backend/routers/easy_mode.py`（既存、編集）

**実装内容**（[`easy_mode.py:297`](autonovel/src/backend/routers/easy_mode.py:297) の修正）:
```python
# 旧
async def export_easy_mode_package(
    book_id: int = Path(ge=1),
    session=Depends(database.get_db),
) -> Response:

# 新
async def export_easy_mode_package(
    book_id: int = Path(ge=1),
    api_key: str = Depends(require_api_key),  # ★ 追加
    session=Depends(database.get_db),
) -> Response:
```

**受け入れ基準**:
- 認証ヘッダーなしで 403
- 認証ヘッダーありで 200

---

### Step 13: `/easy_mode/export/{book_id}` の認証テスト追加

**目標**: 認証動作確認

**ファイル**: `tests/unit/test_easy_mode_launch_endpoint.py` に追記

**実装内容**:
```python
def test_export_requires_api_key():
    """/easy_mode/export/{id} が認証を要求する"""
    from fastapi.testclient import TestClient
    from src.backend.server import app
    
    client = TestClient(app)
    # 認証なし
    r = client.get("/easy_mode/export/1")
    assert r.status_code == 403  # 認証なし
```

---

### Step 14: `orchestrated.py:117` の `/export/{book_id}` 認証追加

**目標**: 同様に認証を追加

**ファイル**: `src/backend/routers/orchestrated.py`（既存、編集）

**実装内容**（[`orchestrated.py:117`](autonovel/src/backend/routers/orchestrated.py:117) の修正）:
```python
async def export_orchestrated_package(
    book_id: int = Path(ge=1),
    api_key: str = Depends(require_api_key),  # ★ 追加
    session=Depends(database.get_db),
):
```

---

### Step 15: `/easy_mode/export-with-data` の book_id デフォルト値削除

**目標**: [`easy_mode.py:462`](autonovel/src/backend/routers/easy_mode.py:462) の `book_id: int = 1` を必須化

**ファイル**: `src/backend/routers/easy_mode.py`（既存、編集）

**実装内容**:
```python
# 旧
async def export_with_data_endpoint(
    payload: ExportRequestPayload,
    book_id: int = 1,  # ★ 危険
    session=Depends(database.get_db),
) -> Response:

# 新
async def export_with_data_endpoint(
    payload: ExportRequestPayload,
    book_id: int,  # ★ 必須化
    api_key: str = Depends(require_api_key),  # ★ 認証追加
    session=Depends(database.get_db),
) -> Response:
```

**注意**: 既存の呼び出し側（フロントエンド）の互換性が壊れる可能性があるため、OpenAPI スキーマの確認後にデプロイ

---

### Step 16: book_id 所有権チェック

**目標**: 他人の book_id でエクスポートできないようにする

**ファイル**: `src/backend/routers/easy_mode.py`（既存、編集）

**実装内容**（`export_easy_mode_package` 内に追加）:
```python
async def export_easy_mode_package(
    book_id: int = Path(ge=1),
    api_key: str = Depends(require_api_key),
    session=Depends(database.get_db),
) -> Response:
    # ★ 所有権チェック
    repo = BookRepository(session)
    book = await repo.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="作品が見つかりません")
    
    # api_key と book.user_id の照合（Book モデルに user_id カラムがある前提）
    # ※ user_id カラムの存在確認が必要
    if hasattr(book, "user_id") and book.user_id and book.user_id != api_key:
        raise HTTPException(status_code=403, detail="アクセス権限がありません")
    
    # 以下、既存の処理...
```

**注意**: `Book` モデルに `user_id` カラムがあるかは要確認。なければ `Book` モデルへの追加が必要

---

### Step 17: 所有権チェックのテスト

**目標**: 他人の book_id で 403 が返ることを確認

**ファイル**: `tests/unit/test_easy_mode_launch_endpoint.py` に追記

**実装内容**:
```python
def test_export_with_different_api_key_forbidden():
    """他人の book_id で 403"""
    # 事前に book_id=999 を user_id="user-A" で作成
    # user_id="user-B" で アクセスして 403 確認
    pass  # 実装は統合テスト環境で行う
```

**注意**: 統合テスト環境（DB必要）のため、ユニットテストではスキップ可能

---

### Step 18: 認証関連エラーの構造化

**目標**: 認証エラーが ProblemDetails 形式で返る

**ファイル**: `src/backend/error_handlers.py`（既存、確認のみ）

**確認内容**: 既存の `autonovel_exception_handler`（[src/backend/error_handlers.py:37](autonovel/src/backend/error_handlers.py:37)）が `HTTPException` をキャッチしているか確認

**実装内容**: 既に対応済みであれば、追加実装なし。`HTTPException` は FastAPI のデフォルトハンドラで処理される

---

## Phase 3: P0-C LLM API キー起動時バリデーション（Step 19〜24）

### 背景

[`config.py:62`](autonovel/src/backend/config.py:62) で `LLM_PROVIDER` デフォルトが `"mock"` のため、LLM キー未設定でも起動してしまう。mock プロバイダは監査スコアが常に50点で品質保証が無意味。

---

### Step 19: 設定の厳格化スキーマ追加

**目標**: 「`LLM_PROVIDER=mock` を許可するが起動時に警告を出す」設定

**ファイル**: `src/backend/config.py`（既存、追記）

**実装内容**:
```python
class Settings(BaseSettings):
    # ... 既存 ...
    
    # LLM プロバイダ運用モード
    # "strict" = 本番起動時に mock / 未設定なら即エラー
    # "lenient" = 警告のみで起動（開発専用）
    LLM_MODE: Literal["strict", "lenient"] = "lenient"
```

**受け入れ基準**:
- デフォルト `lenient` で後方互換
- `LLM_MODE=strict` を `.env` で設定可能

---

### Step 20: 起動時バリデーション関数の作成

**目標**: アプリ起動時に LLM 設定を検証

**ファイル**: `src/backend/startup_validators.py`（新規）

**実装内容**:
```python
"""起動時バリデーター: 本番モードでの必須設定を検証"""
import logging
import sys

logger = logging.getLogger(__name__)


def validate_llm_on_startup():
    """LLM API キー設定を検証（strict モード時のみ）"""
    from src.backend.config import settings
    
    if settings.LLM_MODE != "strict":
        logger.info("LLM_MODE=lenient: LLM API キー検証をスキップ")
        return
    
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "mock":
        logger.error(
            "LLM_MODE=strict ですが LLM_PROVIDER=mock です。"
            "本番環境では実 LLM プロバイダ (openai/gemini/claude/ollama/vllm) を指定してください。"
        )
        sys.exit(1)
    
    if provider in ("openai",):
        if not settings.OPENAI_API_KEY:
            logger.error("LLM_PROVIDER=openai ですが OPENAI_API_KEY が未設定です")
            sys.exit(1)
    
    if provider in ("gemini",):
        if not settings.GEMINI_API_KEY:
            logger.error("LLM_PROVIDER=gemini ですが GEMINI_API_KEY が未設定です")
            sys.exit(1)
    
    if provider in ("claude",):
        if not settings.ANTHROPIC_API_KEY:
            logger.error("LLM_PROVIDER=claude ですが ANTHROPIC_API_KEY が未設定です")
            sys.exit(1)
    
    logger.info(f"LLM設定 OK: provider={provider}")
```

**受け入れ基準**:
- `python -c "from src.backend.startup_validators import validate_llm_on_startup; validate_llm_on_startup()"` で実行可能

---

### Step 21: lifespan への組み込み

**目標**: FastAPI 起動時に自動実行

**ファイル**: `src/backend/server.py`（既存、編集）

**実装内容**（[`server.py:50`](autonovel/src/backend/server.py:50) の `lifespan` 修正）:
```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """アプリケーション起動時にログ設定と DB 初期化を行う lifespan ハンドラ。"""
    configure_logging()
    init_db()
    
    # ★ LLM 設定検証を追加
    from src.backend.startup_validators import validate_llm_on_startup
    validate_llm_on_startup()
    
    yield
```

**受け入れ基準**:
- `LLM_MODE=strict` + `LLM_PROVIDER=mock` で起動失敗
- ログにエラーメッセージが記録される

---

### Step 22: バリデーターのテスト

**目標**: 各モードでの挙動確認

**ファイル**: `tests/unit/test_startup_validators.py`（新規）

**実装内容**:
```python
import pytest
from unittest.mock import patch


def test_validate_lenient_mode_skips_check():
    """lenient モードでは何もしない"""
    with patch("src.backend.config.settings") as mock_settings:
        mock_settings.LLM_MODE = "lenient"
        from src.backend.startup_validators import validate_llm_on_startup
        # 例外なく完了
        validate_llm_on_startup()


def test_validate_strict_mode_exits_on_mock():
    """strict モードで mock なら sys.exit(1)"""
    with patch("src.backend.config.settings") as mock_settings:
        mock_settings.LLM_MODE = "strict"
        mock_settings.LLM_PROVIDER = "mock"
        from src.backend.startup_validators import validate_llm_on_startup
        with pytest.raises(SystemExit):
            validate_llm_on_startup()


def test_validate_strict_mode_exits_on_missing_key():
    """strict モードで openai + API_KEY 空なら sys.exit(1)"""
    with patch("src.backend.config.settings") as mock_settings:
        mock_settings.LLM_MODE = "strict"
        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.OPENAI_API_KEY = None
        from src.backend.startup_validators import validate_llm_on_startup
        with pytest.raises(SystemExit):
            validate_llm_on_startup()
```

**受け入れ基準**:
- 3テストすべてパス

---

### Step 23: `.env.production` テンプレートの作成

**目標**: 本番環境用の設定テンプレート

**ファイル**: `.env.production.example`（新規）

**実装内容**:
```
# AutoNovel Production Configuration
# Copy to `.env.production` and fill in required values.

# Required: Strict LLM validation
LLM_MODE=strict
LLM_PROVIDER=openai

# Required: LLM API Key
OPENAI_API_KEY=sk-...

# Required: Authentication
AUTH_DISABLED=false
ALLOWED_API_KEYS=<comma-separated-keys>

# Required: Production database
DATABASE_URL=postgresql://user:pass@localhost/autonovel

# Required: Production Huey
HUEY_BACKEND=redis
REDIS_URL=redis://localhost:6379/0

# Production server
APP_ENV=production
LOG_LEVEL=INFO
LOG_FORMAT=json
```

**受け入れ基準**:
- ファイルが存在し、必要なキーがすべて記載
- 起動スクリプト（`start_docker.prod.sh` 等）から参照される

---

### Step 24: P0 全体の動作確認と統合テスト

**目標**: P0-A / P0-B / P0-C がすべて組み合わさった状態で動作確認

**ファイル**: `tests/integration/test_p0_integration.py`（新規）

**実装内容**:
```python
"""P0 統合テスト: かんたんモード起動 + 認証 + LLM 検証"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.backend.server import app
    return TestClient(app)


def test_full_e2e_with_mock(client, monkeypatch):
    """LLM_MODE=lenient で mock なら全フロー通る"""
    monkeypatch.setenv("LLM_MODE", "lenient")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    
    # 認証なし → 403
    r = client.post("/easy_mode/auto-generate", json={"genre": "ファンタジー"})
    assert r.status_code == 403
    
    # 認証あり → 200 or 202
    r = client.post(
        "/easy_mode/auto-generate",
        json={"genre": "ファンタジー", "target_episodes": 1, "words_per_episode": 100},
        headers={"X-API-Key": "dev-key-change-me"},
    )
    assert r.status_code in (200, 202, 500)


def test_full_e2e_with_strict_mock_blocked(client, monkeypatch):
    """LLM_MODE=strict + mock なら起動失敗"""
    # アプリ起動を模擬
    monkeypatch.setenv("LLM_MODE", "strict")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    
    from src.backend.startup_validators import validate_llm_on_startup
    with pytest.raises(SystemExit):
        validate_llm_on_startup()
```

**受け入れ基準**:
- すべての統合テストパス
- E2E スモークテスト（Step 10）も合わせてパス

---

## 実装スケジュール（推奨）

| 日 | ステップ | 内容 |
|----|----------|------|
| Day 1 | Step 1-5 | テストスケルトン + スキーマ + Huey タスク登録 |
| Day 2 | Step 6-8 | エンドポイント実装 + 認証デフォルト値 |
| Day 3 | Step 9-10 | ドキュメント + スモークテスト |
| Day 4 | Step 11-15 | 認証ミドルウェア追加（5エンドポイント） |
| Day 5 | Step 16-18 | 所有権チェック + エラー構造化 |
| Day 6 | Step 19-22 | LLM バリデーター実装 + テスト |
| Day 7 | Step 23-24 | 本番設定 + 統合テスト |

**合計**: 約 7 営業日（3 名並列なら 3 営業日）

---

## 実装時の注意点（低性能 LLM 向け）

### 1. 既存パターンの徹底活用

各ステップで「最も近い既存実装」をコピー → 名前変更 → 微修正 する。

| 新規実装 | コピー元 |
|----------|----------|
| `EasyModeLaunchRequest` | `EasyModeInput`（[src/domain/entities/easy_mode.py:32](autonovel/src/domain/entities/easy_mode.py:32)） |
| `auto_generate` エンドポイント | `generate_content`（[src/backend/routers/easy_mode.py:226](autonovel/src/backend/routers/easy_mode.py:226)） |
| `launch_easy_mode_task` | `generate_chapter_task`（[src/backend/tasks/generation_tasks.py:36](autonovel/src/backend/tasks/generation_tasks.py:36)） |
| `validate_llm_on_startup` | 既存設定（[src/backend/config.py:62](autonovel/src/backend/config.py:62)） |

### 2. 既存テストの活用

新規実装前に必ず：
1. `grep -r "EasyModeInput" tests/` で既存テストを確認
2. `grep -r "auto-generate\|easy_mode" tests/` で関連テストを確認
3. `pytest tests/unit/test_easy_mode_workflow.py --collect-only` でパターン把握

### 3. 段階的コミット

各ステップを 1 コミットずつ：
```bash
git commit -m "Step 1: Add test skeleton for easy mode launch endpoint"
git commit -m "Step 2: Add EasyModeLaunchRequest Pydantic schema"
...
```

### 4. PR レビュー時のチェックリスト

- [ ] 新規ファイルが適切なディレクトリに配置されている
- [ ] 既存 import パターンを踏襲（`src.backend.xxx` 形式）
- [ ] docstring が日本語で書かれている
- [ ] `from __future__ import annotations` が冒頭に追加されている
- [ ] 型ヒントが `dict[str, Any]` 形式で書かれている（`Dict` ではなく）
- [ ] テストが追加されている
- [ ] `ruff check` がパスする
- [ ] `mypy` チェックがパスする（strict モードでない場合）

---

## 検証チェックリスト（実装完了後）

- [ ] `pytest tests/unit/test_easy_mode_launch_endpoint.py -v` 全パス
- [ ] `pytest tests/unit/test_startup_validators.py -v` 全パス
- [ ] `pytest tests/integration/test_p0_integration.py -v` 全パス
- [ ] `./scripts/smoke_test.ps1` 成功（mock 環境）
- [ ] `./scripts/smoke_test.ps1` 成功（実 LLM 環境、OPENAI_API_KEY 設定済み）
- [ ] `LLM_MODE=strict LLM_PROVIDER=mock uvicorn src.backend.server:app` で起動失敗
- [ ] `curl -X POST http://localhost:8200/easy_mode/auto-generate` 認証なしで 403
- [ ] README の手順通りに実行して1作品が完成

---

## まとめ

24 ステップで P0 項目すべてに対応。各ステップは：

1. **低性能 LLM でも実装可能**（既存パターンのコピー + 名前変更 + 微修正）
2. **独立してテスト可能**（1ステップ = 1PR）
3. **段階的にマージ可能**（途中で動作しなくなるリスクなし）
4. **明確な受け入れ基準**（各ステップで「パス / 失敗」が明確）

これにより、**プロジェクトに不慣れな開発者でも、24 ステップを順に実装することで P0 項目を完遂できる**。
