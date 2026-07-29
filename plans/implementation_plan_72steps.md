# AutoNovel 詳細実装計画書（72ステップ）

## 1. システム概要とデータフロー

### 全体像
- **バックエンド**: FastAPI (Python 3.12) – ルーター `easy_mode`、サービス層 (`marketing`, `digest_service`)、Huey タスクキュー、SQLAlchemy ORM (未実装)。
- **フロントエンド**: Vite + React 18 + TypeScript – 現状 `App.tsx` のみスタブ。
- **インフラ**: Docker Compose で `backend` (uvicorn), `worker` (huey consumer), `frontend-dev` (vite) を起動。ヘルスチェックで依存順序制御。
- **データフロー (かんたんモード)**
  1. フロント → `POST /easy_mode/generate` (JSON: `EasyModeInput`)。
  2. ルーター `generate_content` が `process_chapter` で章要約 → `generate_with_llm` (stub) 呼出 → `GenerationResponse` 返却。
  3. フロント → `GET /easy_mode/export/{book_id}` → `MarketingAgent.create_export_package` が ZIP (本文/設定/プロット/JSON) を生成し `Response` で返却。
  4. 非同期処理が必要な場合は Huey 経由でワーカーにタスク投入 (未実装)。

### コンポーネント間インターフェース
- **API 契約**: `EasyModeInput` / `GenerationResponse` (pydantic)。
- **サービス契約**: `MarketingAgent.create_export_package(book_id, book_data?) -> (bytes, str)`。
- **タスク契約**: `huey.task` デコレータ関数 (未定義)。

---

## 2. 完全なインターフェースと型定義

### 2.1 Python 型定義 (src/models/easy_mode_schemas.py)
```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any

class EasyModeInput(BaseModel):
    chapter_history: List[str] = Field(default_factory=list)
    current_chapter: str = ""
    character_params: Dict[str, Any] = Field(default_factory=dict)
    content_length_limit: int = 2000

class GenerationResponse(BaseModel):
    output: str = ""
    completion_time_ms: int = 0
    error: str = ""
    suggestions: List[str] = Field(default_factory=list)
```

### 2.2 サービス層シグネチャ
```python
# src/services/digest_service.py
def process_chapter(chapter: str) -> str: ...
def generate_suggestions(chapter: str) -> List[str]: ...

# src/services/marketing.py
from typing import Optional, Tuple, Dict, Any, List
class MarketingAgent:
    def __init__(self, repo: Any = None) -> None: ...
    async def create_export_package(
        self,
        book_id: int,
        book_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bytes, str]: ...
```

### 2.3 ルーターシグネチャ (src/backend/routers/easy_mode.py)
```python
from fastapi import APIRouter, HTTPException
from src.models.easy_mode_schemas import EasyModeInput, GenerationResponse

router = APIRouter()

async def generate_with_llm(**kwargs: Any) -> Dict[str, Any]: ...  # 実装時に置換

@router.post("/generate", response_model=GenerationResponse)
async def generate_content(input_data: EasyModeInput) -> GenerationResponse: ...

@router.get("/export/{book_id}")
async def export_easy_mode_package(book_id: int): ...
```

### 2.4 Huey タスク定義 (src/backend/tasks/huey.py)
```python
from huey import Huey
huey = Huey("autonovel", immediate=False)  # 本番は RedisHuey 等に差替

# 例: 非同期生成タスク
@huey.task()
async def generate_chapter_task(payload: Dict[str, Any]) -> Dict[str, Any]: ...
```

### 2.5 フロントエンド型定義 (frontend/src/types/easyMode.ts)
```ts
export interface EasyModeInput {
  chapter_history: string[];
  current_chapter: string;
  character_params: Record<string, unknown>;
  content_length_limit: number;
}
export interface GenerationResponse {
  output: string;
  completion_time_ms: number;
  error: string;
  suggestions: string[];
}
export interface ExportPackage {
  zipBlob: Blob;
  filename: string;
}
```

### 2.6 API クライアント (frontend/src/api/easyMode.ts)
```ts
import { EasyModeInput, GenerationResponse, ExportPackage } from "../types/easyMode";
const BASE = "/easy_mode";

export async function generateContent(input: EasyModeInput): Promise<GenerationResponse> {
  const res = await fetch(`${BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
export async function exportPackage(bookId: number): Promise<ExportPackage> {
  const res = await fetch(`${BASE}/export/${bookId}`);
  if (!res.ok) throw new Error(await res.text());
  const blob = await res.blob();
  const filename = res.headers.get("Content-Disposition")?.split("filename=")[1]?.replace(/"/g, "") ?? `export_${bookId}.zip`;
  return { zipBlob: blob, filename };
}
```

---

## 3. エッジケースと例外処理の要件定義

| # | 発生箇所 | エラーパターン | 検知条件 | 具体的処理 |
|---|----------|----------------|----------|------------|
| 1 | `generate_content` 入力バリデーション | `ValidationError` (pydantic) | `EasyModeInput` モデル検証失敗 | `HTTPException(422, detail=e.errors())` を raise |
| 2 | `generate_with_llm` タイムアウト | `asyncio.TimeoutError` / `TimeoutError` | 30 秒以上応答なし (設定値) | `logger.error("Generation timeout")` → `HTTPException(504, "Generation timeout")` |
| 3 | `generate_with_llm` 予期せぬ例外 | 任意の `Exception` | try/except で捕捉 | `logger.exception("LLM generation failed")` → `HTTPException(500, "Internal generation error")` |
| 4 | `export_easy_mode_package` DB 取得失敗 | `SQLAlchemyError` / リポジトリ例外 | `repo.get_book` 等が例外送出 | `logger.warning("DB fetch failed, using fallback")` → フォールバックデータで継続 (例外は握り潰さずログのみ) |
| 5 | `MarketingAgent.create_export_package` ZIP 生成失敗 | `zipfile.BadZipFile`, `OSError` | `ZipFile` 操作中に例外 | `logger.exception("ZIP creation failed")` → `raise RuntimeError("Export package creation failed")` (上位で 500) |
| 6 | フロント `generateContent` ネットワークエラー | `TypeError` (fetch 失敗) / 非 2xx | `res.ok === false` または catch | UI に「生成サーバーに接続できません」表示、リトライボタン提供 |
| 7 | フロント `exportPackage` ファイル名デコード失敗 | `Content-Disposition` ヘッダ不在/不正 | ヘッダ解析で filename 取得不可 | デフォルト `export_${bookId}.zip` を使用 |
| 8 | Huey タスクキュー未接続 | `huey.HueyException` / 接続拒否 | `huey.enqueue` 実行時 | 起動時ヘルスチェックで Redis 疎通確認、失敗時は `immediate=True` フォールバックで同期実行 |
| 9 | 入力文字列長超過 | `content_length_limit` 超過 | `len(input.current_chapter) > input.content_length_limit` | `process_chapter` 側で切り詰め、警告ログ出力 |
|10| 空チャプター入力 | `current_chapter == ""` | バリデーション通過後 | `process_chapter` は空文字を返し、`generate_suggestions` はデフォルト提案を返す |

すべての例外は **構造化ログ (JSON)** で出力し、Sentry 等へ連携可能な形式とする。

---

## 4. ステップ・バイ・ステップ実装タスク分割 (全72ステップ)

> 各ステップは「ファイル名」「関数/クラス名」「処理ロジック箇条書き」を含む。1ステップ=1コミット粒度。

### Phase 0: 環境・共通整備 (1-4)
1. **`scripts/verify_all.ps1`** – `ruff check --fix src tests` 追加し自動整形をCI化。
2. **`pyproject.toml`** – `[tool.ruff.lint]` に `select = ["E","F","W","I","C90","UP"]` 追加、`ignore = ["E501"]` 維持。
3. **`requirements.txt`** – `pyproject.toml` の `[project.dependencies]` と同期スクリプト `scripts/sync_reqs.py` 作成 (pip-compile 代替)。
4. **`src/backend/tasks/huey.py`** – `immediate=False` 維持、環境変数 `HUEY_BACKEND` で `RedisHuey` / `SqliteHuey` 切替ロジック追加。

### Phase 1: バックエンド コア修正 (5-18)
5. **`src/backend/routers/easy_mode.py`** – `generate_content` シグネチャから `current_chapter: str` 削除、`input_data.current_chapter` 使用。
6. **同ファイル** – `generate_with_llm` を `async def generate_with_llm(payload: Dict[str, Any]) -> Dict[str, Any]` に型付け、stub 実装を `raise NotImplementedError` に変更。
7. **同ファイル** – `except ValidationError` ブロックで `e.errors()` 呼出し修正。
8. **同ファイル** – `except Exception as e:` 追加し `logger.exception` → `HTTPException(500, "Internal generation error")`。
9. **同ファイル** – 関数内 import (`Response`, `MarketingAgent`) をモジュール先頭に移動 (ruff I001 解消)。
9. **同ファイル** – `export_easy_mode_package` に `book_id` 存在チェック (repo があれば `repo.get_book`、なければ 404)。
10. **同ファイル** – `Content-Disposition` ヘッダを RFC6266 対応 (`filename*=UTF-8''{quote(zip_filename)}` 併記)。
11. **`src/services/digest_service.py`** – `process_chapter` 三項式に括弧追加、docstring 拡充。
12. **同ファイル** – `generate_suggestions` を `async def` 化し、将来 LLM 呼出し可能に。
13. **`src/services/marketing.py`** – `except Exception: pass` を `logger.warning("DB fetch failed, using fallback", exc_info=True)` に変更。
14. **同ファイル** – 行末空白 (W293) 全行削除。
15. **同ファイル** – `create_export_package` のフォールバックデータを定数 `DEFAULT_FALLBACK` としてモジュールレベルに抽出。
16. **同ファイル** – `zipfile.ZipFile` 操作を `try/except zipfile.BadZipFile/OSError` で囲み `RuntimeError` 送出。
17. **`src/models/easy_mode_schemas.py`** – `content_length_limit` に `ge=1, le=10000` バリデーション追加。
18. **`tests/integration/test_easy_mode_export.py`** – `book_data` なしでフォールバック ZIP 検証ケース追加。

### Phase 2: データベース・リポジトリ層 (19-30)
19. **`src/models/__init__.py`** – SQLAlchemy `DeclarativeBase` 継承ベースクラス `Base` 定義。
20. **`src/models/book.py`** – `Book`, `Chapter`, `Character`, `Plot`, `Bible` ORM モデル定義 (id, title, genre, ep_num, content, …)。
21. **`src/models/__init__.py`** – モデル公開 (`from .book import Book, Chapter, …`).
22. **`src/backend/database/__init__.py`** – 新規作成、`engine`, `SessionLocal`, `init_db()` 実装。
23. **`src/backend/database/repository.py`** – `BookRepository` クラス (CRUD + `get_all_non_anchor_chapters`, `get_all_characters`, `get_latest_bible`, `get_all_plots`) 実装。
24. **`src/backend/tasks/huey.py`** – `huey` インスタンスに `huey.storage` 設定 (Redis URL 環境変数)。
25. **`src/backend/routers/easy_mode.py`** – `MarketingAgent` 初期化時に `repo=BookRepository(SessionLocal())` 注入。
26. **`tests/conftest.py`** – `real_db_manager` fixture で `init_db()` 実行し `SessionLocal` 返却。
27. **`tests/integration/test_easy_mode_export.py`** – fixture 利用し実 DB 経由のエクスポートテスト追加。
28. **`src/backend/server.py`** – `app.on_event("startup")` で `init_db()` 呼出し。
29. **`docker-compose.yml`** – `backend` / `worker` に `depends_on: db` 追加、`db` サービス (postgres:16) 定義。
30. **`.env.example`** – `DATABASE_URL`, `REDIS_URL`, `HUEY_BACKEND` 例示。

### Phase 3: 非同期生成タスク (31-42)
31. **`src/backend/tasks/generation_tasks.py`** – 新規作成、`@huey.task() async def generate_chapter_task(payload: Dict) -> Dict` 実装 (中身は `generate_with_llm` 呼出し)。
32. **`src/backend/routers/easy_mode.py`** – `generate_content` 内で `generate_chapter_task` を `huey.enqueue` し、即座に `GenerationResponse(output="", completion_time_ms=0, error="", suggestions=["生成をキューに投入しました"])` 返却 (ポーリング方式)。
33. **同ファイル** – `/easy_mode/status/{task_id}` エンドポイント追加 (Huey `result(task_id)` 取得)。
34. **`frontend/src/api/easyMode.ts`** – `pollGenerationStatus(taskId)` 実装 (5秒間隔、完了まで再帰)。
35. **`frontend/src/components/GeneratePanel.tsx`** – 新規作成、入力フォーム・生成ボタン・ステータス表示・結果表示。
36. **`frontend/src/App.tsx`** – `GeneratePanel` インポート・描画。
37. **`frontend/src/main.tsx`** – React 18 `createRoot` マウント、CSS インポート。
38. **`frontend/index.html`** – `<div id="root"></div>` 確認、タイトル修正。
39. **`frontend/vite.config.ts`** – `proxy` 設定確認 (`/easy_mode` → `http://localhost:8200`)。
40. **`frontend/package.json`** – `scripts` に `"lint": "eslint src --ext ts,tsx"`, `"typecheck": "tsc --noEmit"` 追加。
41. **`frontend/tsconfig.json`** – `strict: true`, `jsx: "react-jsx"` 設定。
42. **`scripts/verify_all.ps1`** – フロント `npm run lint && npm run typecheck` 追加。

### Phase 4: エクスポート UI (43-50)
43. **`frontend/src/components/ExportPanel.tsx`** – `book_id` 入力・エクスポートボタン・ダウンロード処理 (`URL.createObjectURL` + `<a download>`).
44. **`frontend/src/App.tsx`** – `ExportPanel` 追加配置。
45. **`src/backend/routers/easy_mode.py`** – `export_easy_mode_package` に `book_id` バリデーション (正の整数) 追加。
46. **同ファイル** – レスポンスヘッダ `Cache-Control: no-store` 追加。
47. **`tests/integration/test_easy_mode_export.py`** – 実 DB データで ZIP 中身検証 (章数・文字数) 追加。
48. **`tests/test_health.py`** – `/easy_mode/generate` 422/200 ケース追加。
49. **`scripts/verify_all.ps1`** – `pytest -q --tb=short` 実行確認。
50. **`README.md`** – 開発手順・API エンドポイント一覧・環境変数説明更新。

### Phase 5: 品質・観測・ドキュメント (51-62)
51. **`src/backend/logging_config.py`** – 新規作成、JSON ログフォーマッタ (`python-json-logger`) 設定、uvicorn/gunicorn 統合。
52. **`src/backend/server.py`** – `logging_config.configure()` 呼出し。
53. **`docker-compose.yml`** – `backend` / `worker` に `logging` ドライバ `json-file` 設定。
54. **`pyproject.toml`** – `[tool.pytest.ini_options]` に `addopts = "-p no:cacheprovider --import-mode=importlib --tb=short"` 追加。
55. **`requirements-dev.txt`** – `pytest-cov`, `httpx`, `pytest-asyncio` 追加。
56. **`tests/__init__.py`** – `pytest.mark.asyncio` 自動適用設定 (`pytest_asyncio.auto_mode = True`)。
57. **`tests/integration/test_generate_flow.py`** – 新規作成、生成→ステータスポーリング→結果取得の統合テスト。
58. **`docs/api.md`** – 新規作成、OpenAPI から自動生成 (`fastapi openapi > docs/openapi.json` スクリプト追加)。
59. **`scripts/generate_openapi.py`** – 新規作成、CI で実行。
60. **`.github/workflows/ci.yml`** – 新規作成、lint/typecheck/test/docker build を GitHub Actions で実行。
61. **`Dockerfile`** – マルチステージで `builder` → `runtime` 分離、非 root ユーザー実行。
62. **`frontend/Dockerfile`** – `production` ステージで `nginx` 静的配信に切替、ヘルスチェック追加。

### Phase 6: 仕上げ・リリース準備 (63-72)
63. **`CHANGELOG.md`** – 新規作成、Keep a Changelog 形式でバージョン履歴開始。
64. **`pyproject.toml`** – `[project]` `version = "0.2.0"` 更新。
65. **`scripts/release.ps1`** – タグ打ち・Docker イメージ push・GitHub Release 作成自動化。
66. **`SECURITY.md`** – 脆弱性報告窓口・依存スキャン (`pip-audit`, `npm audit`) 手順記載。
67. **`CONTRIBUTING.md`** – ブランチ戦略・コミットメッセージ規約・PR チェックリスト。
68. **`Makefile`** – よく使うコマンド (`make lint`, `make test`, `make build`, `make up`) 定義。
69. **`docker-compose.prod.yml`** – 本番用 (nginx リバプロ、TLS 証明書マウント、レプリカ数) 定義。
70. **`scripts/smoke_test.ps1`** – デプロイ後ヘルスチェック・主要 API 疎通確認スクリプト。
71. **`README.md`** – 本番デプロイ手順・アーキテクチャ図 (Mermaid) 追加。
72. **最終確認** – `./scripts/verify_all.ps1` 全緑、`docker compose -f docker-compose.prod.yml up --build -d` 成功、スモークテストパス → 完了。

---

## 5. 単体テスト要件 (テストケース)

| テストID | 対象 | 入力 | 期待結果 |
|----------|------|------|----------|
| TC-01 | `EasyModeInput` バリデーション | `chapter_history=["a"], current_chapter="b", character_params={}, content_length_limit=2000` | パース成功、オブジェクト生成 |
| TC-02 | `EasyModeInput` 異常 | `content_length_limit=0` | `ValidationError` (ge=1) |
| TC-03 | `process_chapter` 正常 | `"あ"*2000` | 先頭1500文字 + `"..."` |
| TC-04 | `process_chapter` 短文 | `"短い"` | `"短い"` (変更なし) |
| TC-05 | `generate_suggestions` | `"冒頭テキスト"` | `["続行: 冒頭テキスト...", "調査が必要な未確認な要素を指摘"]` |
| TC-06 | `MarketingAgent.create_export_package` フォールバック | `book_id=1, book_data=None` | ZIP 4ファイル含む、ファイル名 `export_1.zip` |
| TC-07 | 同・book_data 指定 | `book_data={title:"T", chapters:[{ep_num:1,title:"t",content:"c"}]}` | ZIP 内 `01_本文.txt` に "T" と "t" "c" 含む |
| TC-08 | 同・repo 例外時 | `repo.get_book` が `SQLAlchemyError` 送出 | 警告ログ出力、フォールバックデータで ZIP 生成継続 |
| TC-09 | `generate_content` 正常 (stub) | `EasyModeInput` 有効 | `GenerationResponse` 返却、`output="stub response"` |
| TC-10 | `generate_content` バリデーション失敗 | `current_chapter` 欠如 | `422` + `detail` 配列 |
| TC-11 | `generate_content` タイムアウト | `generate_with_llm` が 30秒超 | `504` + `"Generation timeout"` |
| TC-12 | `export_easy_mode_package` 存在しない book_id | `book_id=9999, repo=None` | フォールバック ZIP 返却 (404 にしない仕様) |
| TC-13 | フロント `generateContent` 成功 | モック `fetch` 200 + JSON | `GenerationResponse` 型オブジェクト解決 |
| TC-14 | フロント `generateContent` 失敗 | モック `fetch` 500 | `Error` throw、メッセージ含む |
| TC-15 | フロント `exportPackage` ダウンロード | モック `fetch` 200 + blob + header | `{zipBlob: Blob, filename: "export_1.zip"}` 解決 |
| TC-16 | 統合: 生成→ポーリング→完了 | `generate_chapter_task` が即時完了するモック | ポーリング終了後 `output` 取得 |
| TC-17 | 統合: エクスポート実 DB | `real_db_manager` fixture で 1冊登録後 export | ZIP に登録チャプター数分の本文含む |

すべてのテストは `pytest -q` で実行し、**カバレッジ 80% 以上** を目標とする。

---