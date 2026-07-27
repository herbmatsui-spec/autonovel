# AutoNovel プロジェクト修復 最終実装計画（48ステップ）

> 作成日: 2026-07-27
> 前版 `repair_plan_48steps_revised.md` をベースに、レポート指摘の全5項目を確実に網羅し、低性能LLMでも確実に実装できるよう各ステップを「1ファイル作成 / 1コマンド実行」に極限細分化した最終版。

## 0. 本計画の位置づけと原則

### 0.1 レポート指摘5項目と対応フェーズ
| # | レポート指摘 | 対応フェーズ | 対象ステップ |
|---|---|---|---|
| 1 | 二重フォルダ構成 + `アプリ起動.bat` のcd先不整合 | A + E | 1–8, 28 |
| 2 | Dockerfile欠損・frontend全欠損・エントリポイント欠損 | C + D + E | 13–16, 19–27 |
| 3 | コア機能コード（agents/services等）の大規模欠損 | C | 13–18 |
| 4 | 静的解析ログのエラー痕跡（mypy重複/Powershell引数） | B + G | 7, 12, 36–39 |
| 5 | plans/ ドキュメントの分散 | A | 3, 4 |

### 0.2 実行原則（低性能LLM向け）
- **1ステップ＝1ツール呼び出し完結**：Read → Write/Edit → 確認コマンド の3手順以内。
- **コードブロックはそのままWrite**の内容にする（推論不要）。
- **確認コマンドは必ず実行**し、成功(True/0件)を確認してから次ステップへ。
- **失敗時は同じステップを再実行**（次ステップに進まない）。
- **Git commitは各フェーズ終了時のみ**（過剰commit回避）。

---

## フェーズ A: 残骸サブ回収とパス不整合の解消（ステップ1–8）

### ステップ1: 残骸サブ `temp/test_models.py` の中身確認
- **対象**: `D:\autonovel\autonovel\temp\test_models.py`
- **作業**: Read で内容確認。
- **確認**: ファイルが読めること。`__main__` ガードがなければ次ステップで差し替え、あれば維持。
- ** Lazy LLMメモ**: 確認のみ、編集は次ステップ。

### ステップ2: `temp/test_models.py` をルートへ複製
- **対象**: `D:\autonovel\autonovel\temp\test_models.py` → `D:\autonovel\temp\test_models.py`
- **作業**（Bash）:
  ```powershell
  New-Item -ItemType Directory -Path "D:\autonovel\temp" -Force | Out-Null
  Copy-Item "D:\autonovel\autonovel\temp\test_models.py" "D:\autonovel\temp\test_models.py" -Force
  ```
- **確認**（Bash）: `Test-Path "D:\autonovel\temp\test_models.py"` → True。

### ステップ3: 旧版 `repair_plan_48steps.md` をルートplans/へ退避コピー
- **対象**: `D:\autonovel\autonovel\plans\repair_plan_48steps.md` → `D:\autonovel\plans\repair_plan_48steps_deprecated.md`
- **作業**（Bash）:
  ```powershell
  Copy-Item "D:\autonovel\autonovel\plans\repair_plan_48steps.md" "D:\autonovel\plans\repair_plan_48steps_deprecated.md" -Force
  ```
- **確認**（Bash）: `Test-Path "D:\autonovel\plans\repair_plan_48steps_deprecated.md"` → True。

### ステップ4: 本計画ファイルの存在確認（自己保存済み）
- **対象**: `D:\autonovel\plans\repair_plan_48steps_final.md`
- **作業**: Read で先頭1行確認。
- **確認**: `# AutoNovel プロジェクト修復 最終実装計画` が表示される。

### ステップ5: `.gitignore` 新規作成（ルート）
- **対象**: `D:\autonovel\.gitignore`（新規）
- **作業**: Write で下記内容:
  ```gitignore
  # caches
  .mypy_cache/
  .pytest_cache/
  .ruff_cache/
  .kilo/node_modules/

  # build artifacts
  *.egg-info/
  __pycache__/
  *.pyc

  # legacy work files
  tmp_replace_normalize.py
  mypy_errors.txt
  mypy_out.txt
  ruff_e722.txt
  ruff_f841_src.txt
  backup/

  # frontend
  frontend/node_modules/
  frontend/dist/
  ```
- **確認**（Bash）: `Test-Path "D:\autonovel\.gitignore"` → True。

### ステップ6: 旧キャッシュをgit追跡から解除＋物理削除
- **作業**（Bash）:
  ```powershell
  git rm -r --cached .mypy_cache .pytest_cache .ruff_cache 2>$null
  Remove-Item -Recurse -Force "D:\autonovel\.mypy_cache","D:\autonovel\.pytest_cache","D:\autonovel\.ruff_cache" -ErrorAction SilentlyContinue
  ```
- **確認**（Bash）: `git status --short` が短縮される。キャッシュdirが存在しない。

### ステップ7: `output/` に `.gitkeep` 追加
- **対象**: `D:\autonovel\output\.gitkeep`（0バイト）
- **作業**: Write（内容空）。
- **確認**（Bash）: `Test-Path "D:\autonovel\output\.gitkeep"` → True。

### ステップ8: フェーズAのGit commit
- **作業**（Bash）:
  ```powershell
  git add -A
  git commit -m "chore(phaseA): 残骸サブ回収とgitignore整備"
  ```
- **確認**（Bash）: `git log --oneline -1` で新commit表示。

---

## フェーズ B: プロジェクト設定ファイル新規整備（ステップ9–14）

### ステップ9: `pyproject.toml` 新規作成（mypy重複エラー対策含む）
- **対象**: `D:\autonovel\pyproject.toml`（新規）
- **作業**: Write で下記内容（`explicit_package_bases=true`＋`mypy_path=["src"]`で重複モジュール問題を解消）:
  ```toml
  [tool.mypy]
  python_version = "3.12"
  mypy_path = ["src"]
  files = ["src"]
  exclude = ["temp/", "backup/", ".*egg-info/"]
  explicit_package_bases = true
  namespace_packages = false
  ignore_missing_imports = true
  strict = false

  [tool.ruff]
  line-length = 100
  target-version = "py312"
  extend-exclude = ["temp", "backup", ".kilo", "node_modules"]

  [tool.ruff.lint]
  select = ["E", "F", "I", "W"]
  ignore = ["E501"]

  [tool.pytest.ini_options]
  testpaths = ["tests"]
  norecursedirs = ["temp", "backup", "frontend", "node_modules"]
  addopts = "-p no:cacheprovider --import-mode=importlib"

  [build-system]
  requires = ["setuptools>=61.0"]
  build-backend = "setuptools.build_meta"

  [project]
  name = "autonovel"
  version = "0.1.0"
  requires-python = ">=3.12"
  dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "pydantic>=2.6",
    "huey>=2.5",
    "httpx>=0.27",
  ]

  [project.optional-dependencies]
  dev = ["mypy>=1.8", "ruff>=0.3", "pytest>=8.0"]

  [tool.setuptools]
  package-dir = {"" = "src"}

  [tool.setuptools.packages.find]
  where = ["src"]
  ```
- **確認**（Bash）: `py -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` で無出力（構文OK）。

### ステップ10: `requirements.txt` 新規作成
- **対象**: `D:\autonovel\requirements.txt`（新規）
- **作業**: Write:
  ```
  fastapi>=0.110
  uvicorn[standard]>=0.27
  pydantic>=2.6
  huey>=2.5
  httpx>=0.27
  ```
- **確認**: Read で5行確認。

### ステップ11: `requirements-dev.txt` 新規作成
- **対象**: `D:\autonovel\requirements-dev.txt`（新規）
- **作業**: Write:
  ```
  -r requirements.txt
  mypy>=1.8
  ruff>=0.3
  pytest>=8.0
  ```
- **確認**: Read で4行確認。

### ステップ12: Python仮想環境 `.venv` 作成と依存インストール
- **作業**（Bash、逐次実行）:
  ```powershell
  py -m venv .venv
  .\.venv\Scripts\python.exe -m pip install --upgrade pip
  .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
  ```
- **確認**（Bash）: `Test-Path "D:\autonovel\.venv\Scripts\python.exe"` → True。以後の Python 実行は `.\.venv\Scripts\py` を使用（エイリアス推奨）。
- **Lazy LLMメモ**: venv作成失敗時は `py -m` で代用可。本ステップは省略可能だが推奨。

### ステップ13: `src/__init__.py` 群を5個作成（空ファイル）
- **対象**: `src/__init__.py`, `src/backend/__init__.py`, `src/backend/routers/__init__.py`, `src/models/__init__.py`, `src/services/__init__.py`
- **作業**（Bash）: 各パスに空ファイル Write（1個ずつWrite呼び出し5回、または下記Bash）:
  ```powershell
  @("src","src\backend","src\backend\routers","src\models","src\services") | % { New-Item -ItemType File -Path "D:\autonovel\$_\__init__.py" -Force | Out-Null }
  ```
- **確認**（Bash）: `Get-ChildItem D:\autonovel\src -Recurse -Filter __init__.py | Measure-Object | % Count` → 5。

### ステップ14: `tests/__init__.py` と `tests/conftest.py` 新規作成
- **対象**: `tests/__init__.py`(空), `tests/conftest.py`
- **作業**:
  - `tests/__init__.py`: 空ファイル Write。
  - `tests/conftest.py`: Write で:
    ```python
    import os
    import sys

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    ```
- **確認**（Bash）: `Test-Path "D:\autonovel\tests\conftest.py"` → True。

---

## フェーズ C: backend 最小構成の復元（エントリポイント欠損解消）（ステップ15–22）

### ステップ15: `src/backend/server.py` 新規作成（FastAPI本体 + /health）
- **対象**: `D:\autonovel\src\backend\server.py`（新規）
- **作業**: Write で下記内容:
  ```python
  from fastapi import FastAPI

  from src.backend.routers import easy_mode

  app = FastAPI(title="AutoNovel Backend")
  app.include_router(easy_mode.router, prefix="/easy_mode", tags=["easy_mode"])


  @app.get("/health")
  async def health() -> dict[str, str]:
      return {"status": "ok"}
  ```
- **確認**（Bash）: `.\.venv\Scripts\python.exe -c "from src.backend.server import app; print(app.title)"` → `AutoNovel Backend`。
  - venv未使用時は `py -c` で代用（PYTHONPATH未設定なら `set PYTHONPATH=.` を先頭に付加）。

### ステップ16: `easy_mode.py` を router 定義に差し替え（app = FastAPI() 削除）
- **対象**: `D:\autonovel\src\backend\routers\easy_mode.py`
- **作業**: Write で既存内容を下記に置換（`app = FastAPI()` → `router = APIRouter()`、`@app.post` → `@router.post`、型注記補完）:
  ```python
  import logging
  from typing import Any

  from fastapi import APIRouter, HTTPException
  from pydantic import ValidationError

  from src.models.easy_mode_schemas import EasyModeInput, GenerationResponse
  from src.services.digest_service import generate_suggestions, process_chapter

  router = APIRouter()
  logger = logging.getLogger(__name__)


  async def generate_with_llm(**kwargs: Any) -> dict[str, Any]:
      """Stub function to satisfy mypy until implementation is clarified."""
      return {"text": "stub response", "time": 0}


  @router.post("/generate")
  async def generate_content(input_data: EasyModeInput, current_chapter: str) -> GenerationResponse:
      try:
          processed_chapter = process_chapter(current_chapter)
          params = {
              "chapter_history": input_data.chapter_history,
              "current_chapter": processed_chapter,
              "character": input_data.character_params,
          }
          response = await generate_with_llm(**params)
          return GenerationResponse(
              output=response["text"],
              completion_time_ms=response["time"],
              suggestions=generate_suggestions(processed_chapter),
          )
      except ValidationError as e:
          logger.error("Validation failed: %s", e.errors)
          raise HTTPException(status_code=422, detail=e.errors) from e
  ```
- **確認**（Bash）: `py -c "from src.backend.routers.easy_mode import router; print(router.prefix)"` → エラーなし（prefix未設定なので空も可、ImportErrorが出なければOK）。

### ステップ17: `models/easy_mode_schemas.py` 型注記補完（pydantic v2準拠）
- **対象**: `D:\autonovel\src\models\easy_mode_schemas.py`
- **作業**: Write で下記に置換（`dict` → `dict[str, Any]`、model_config追加）:
  ```python
  from typing import Any

  from pydantic import BaseModel, ConfigDict, Field


  class EasyModeInput(BaseModel):
      model_config = ConfigDict(extra="forbid")

      chapter_history: list[str] = Field(default_factory=list)
      current_chapter: str = ""
      character_params: dict[str, Any] = Field(default_factory=dict)
      content_length_limit: int = 2000


  class GenerationResponse(BaseModel):
      output: str = ""
      completion_time_ms: int = 0
      error: str = ""
      suggestions: list[str] = Field(default_factory=list)
  ```
- **確認**（Bash）: `py -c "from src.models.easy_mode_schemas import EasyModeInput; print(EasyModeInput().model_fields.keys())"` でエラーなし。

### ステップ18: `services/digest_service.py` 型注記補完
- **対象**: `D:\autonovel\src\services\digest_service.py`
- **作業**: Write で下記に置換:
  ```python
  def process_chapter(chapter: str) -> str:
      """章の中身から主要テキストを抽出"""
      max_length = 1500
      if len(chapter) > max_length:
          return chapter[:max_length].rstrip() + "..."
      return chapter


  def generate_suggestions(chapter: str) -> list[str]:
      """章の文脈から意味的な提案を生成"""
      return [
          f"続行: {chapter[:100]}...",
          "調査が必要な未確認な要素を指摘",
      ]
  ```
- **確認**（Bash）: `py -c "from src.services.digest_service import process_chapter, generate_suggestions; print(process_chapter('x'*1600)[:20])"` で出力あり。

### ステップ19: `src/backend/tasks/__init__.py` 新規作成（空）
- **作業**（Bash）: `New-Item -ItemType File -Path "D:\autonovel\src\backend\tasks\__init__.py" -Force | Out-Null`
- **確認**（Bash）: `Test-Path "D:\autonovel\src\backend\tasks\__init__.py"` → True。

### ステップ20: `src/backend/tasks/huey.py` 新規作成（worker用stub）
- **対象**: `D:\autonovel\src\backend\tasks\huey.py`（新規）
- **作業**: Write:
  ```python
  from huey import SqliteHuey

  huey = SqliteHuey(filename="/tmp/autonovel_huey.db", name="autonovel", immediate=False)
  ```
- **確認**（Bash）: `py -c "from src.backend.tasks.huey import huey; print(huey.name)"` → `autonovel`。

### ステップ21: `src/backend/tasks/sample_task.py` 新規作成（huey動作確認stub）
- **対象**: `D:\autonovel\src\backend\tasks\sample_task.py`（新規）
- **作業**: Write:
  ```python
  from src.backend.tasks.huey import huey


  @huey.task()
  def ping() -> str:
      return "pong"
  ```
- **確認**（Bash）: `py -c "from src.backend.tasks.sample_task import ping; print(ping.call())"` → `pong`（immediate=Falseでも`call()`は即時実行）。

### ステップ22: フェーズCのGit commit
- **作業**（Bash）:
  ```powershell
  git add -A
  git commit -m "feat(phaseC): backend最小構成復元(server/tasks/routers)"
  ```
- **確認**（Bash）: `git log --oneline -1` で新commit表示。

---

## フェーズ D: frontend 最小構成の復元（Vite + React）（ステップ23–28）

### ステップ23: `frontend/package.json` 新規作成
- **対象**: `D:\autonovel\frontend\package.json`（新規）
- **作業**: Write:
  ```json
  {
    "name": "autonovel-frontend",
    "private": true,
    "version": "0.1.0",
    "type": "module",
    "scripts": {
      "dev": "vite",
      "build": "vite build",
      "preview": "vite preview --port 3000"
    },
    "dependencies": {
      "react": "^18.2.0",
      "react-dom": "^18.2.0"
    },
    "devDependencies": {
      "@vitejs/plugin-react": "^4.2.1",
      "@types/react": "^18.2.0",
      "@types/react-dom": "^18.2.0",
      "typescript": "^5.4.0",
      "vite": "^5.1.0"
    }
  }
  ```
- **確認**（Bash）: `Test-Path "D:\autonovel\frontend\package.json"` → True。

### ステップ24: `frontend/index.html` 新規作成
- **対象**: `D:\autonovel\frontend\index.html`（新規）
- **作業**: Write:
  ```html
  <!doctype html>
  <html lang="ja">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>AutoNovel</title>
    </head>
    <body>
      <div id="root"></div>
      <script type="module" src="/src/main.tsx"></script>
    </body>
  </html>
  ```
- **確認**: Test-Path True。

### ステップ25: `frontend/vite.config.ts` と `frontend/tsconfig.json` 新規作成
- **対象**: `frontend/vite.config.ts`, `frontend/tsconfig.json`
- **作業**:
  - `vite.config.ts`: Write:
    ```ts
    import react from "@vitejs/plugin-react";
    import { defineConfig } from "vite";

    export default defineConfig({
      plugins: [react()],
      server: { host: true, port: 5173 },
      preview: { host: true, port: 3000 },
      build: { outDir: "dist" },
    });
    ```
  - `tsconfig.json`: Write:
    ```json
    {
      "compilerOptions": {
        "target": "ES2022",
        "lib": ["ES2022", "DOM", "DOM.Iterable"],
        "module": "ESNext",
        "moduleResolution": "Bundler",
        "jsx": "react-jsx",
        "strict": true,
        "skipLibCheck": true,
        "noEmit": true
      },
      "include": ["src"]
    }
    ```
- **確認**（Bash）: 両ファイル Test-Path True。

### ステップ26: `frontend/src/main.tsx` と `frontend/src/App.tsx` 新規作成
- **対象**: `frontend/src/main.tsx`, `frontend/src/App.tsx`
- **作業**:
  - `main.tsx`: Write:
    ```tsx
    import React from "react";
    import ReactDOM from "react-dom/client";
    import App from "./App";

    ReactDOM.createRoot(document.getElementById("root")!).render(
      <React.StrictMode>
        <App />
      </React.StrictMode>
    );
    ```
  - `App.tsx`: Write:
    ```tsx
    export default function App() {
      return <div>AutoNovel Frontend</div>;
    }
    ```
- **確認**: 両ファイル Test-Path True。

### ステップ27: `frontend/.dockerignore` 新規作成
- **対象**: `D:\autonovel\frontend\.dockerignore`（新規）
- **作業**: Write:
  ```
  node_modules
  dist
  .git
  ```
- **確認**: Test-Path True。

### ステップ28: フェーズDのGit commit
- **作業**（Bash）:
  ```powershell
  git add -A
  git commit -m "feat(phaseD): frontend最小構成復元(Vite+React)"
  ```
- **確認**（Bash）: `git log --oneline -1` で新commit表示。

---

## フェーズ E: Docker 設定とバッチファイルの整合化（ステップ29–34）

### ステップ29: ルート `Dockerfile`（backend/worker共用）新規作成
- **対象**: `D:\autonovel\Dockerfile`（新規）
- **作業**: Write:
  ```dockerfile
  FROM python:3.12-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  ENV PYTHONPATH=/app
  EXPOSE 8200
  CMD ["uvicorn", "src.backend.server:app", "--host", "0.0.0.0", "--port", "8200"]
  ```
- **確認**: Test-Path True。

### ステップ30: `frontend/Dockerfile` 新規作成（dev/production多段）
- **対象**: `D:\autonovel\frontend\Dockerfile`（新規）
- **作業**: Write:
  ```dockerfile
  FROM node:20-slim AS base
  WORKDIR /app
  COPY package.json package-lock.json* ./
  RUN npm install
  COPY . .

  FROM base AS dev
  EXPOSE 5173
  CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

  FROM base AS production
  RUN npm run build
  EXPOSE 3000
  CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0"]
  ```
- **確認**: Test-Path True。

### ステップ31: `docker-compose.yml` 差し替え（healthcheck修正）
- **対象**: `D:\autonovel\docker-compose.yml`
- **作業**: Write で既存内容を下記に置換（`curl` → `python urllib`、volumesを `./src` に絞る、frontend-prod削除でcompose upを簡素化）:
  ```yaml
  services:
    backend:
      build:
        context: .
        dockerfile: Dockerfile
      container_name: autonovel_backend
      ports:
        - "8200:8200"
      environment:
        - PYTHONPATH=/app
      volumes:
        - ./src:/app/src
      healthcheck:
        test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8200/health')"]
        interval: 10s
        timeout: 5s
        retries: 5

    worker:
      build:
        context: .
        dockerfile: Dockerfile
      container_name: autonovel_worker
      command: python -m huey.bin.huey_consumer src.backend.tasks.huey
      environment:
        - PYTHONPATH=/app
      volumes:
        - ./src:/app/src
      depends_on:
        backend:
          condition: service_healthy

    frontend-dev:
      build:
        context: ./frontend
        dockerfile: Dockerfile
        target: dev
      container_name: autonovel_frontend_dev
      ports:
        - "5173:5173"
      volumes:
        - ./frontend:/app
        - /app/node_modules
      environment:
        - CHOKIDAR_USEPOLLING=true
      depends_on:
        backend:
          condition: service_healthy
  ```
- **確認**（Bash）: `docker compose config > $null; if ($?) { "OK" } else { "ERR" }` → `OK`。
  - Docker未インストール環境では `Test-Path` のみ確認し、構文は目視。

### ステップ32: `アプリ起動.bat` 修正（cd先をルートに）
- **対象**: `D:\autonovel\アプリ起動.bat`
- **作業**: Edit で `cd /d "%~dp0autonovel"` → `cd /d "%~dp0"` に置換。
- **確認**: Read で `cd /d "%~dp0"` のみ存在、`autonovel` サブパス参照が残っていないこと。

### ステップ33: ルート `.dockerignore` 新規作成
- **対象**: `D:\autonovel\.dockerignore`（新規）
- **作業**: Write:
  ```
  .venv
  .git
  .mypy_cache
  .pytest_cache
  .ruff_cache
  .kilo
  backup
  temp
  output
  frontend/node_modules
  frontend/dist
  ```
- **確認**: Test-Path True。

### ステップ34: フェーズEのGit commit
- **作業**（Bash）:
  ```powershell
  git add -A
  git commit -m "fix(phaseE): Dockerfile/docker-compose/batのパス整合性修正"
  ```
- **確認**（Bash）: `git log --oneline -1` で新commit表示。

---

## フェーズ F: 静的解析・pytest 環境の整備と検証（ステップ35–40）

### ステップ35: ruff 実行と結果確認
- **作業**（Bash）: `py -m ruff check src tests > ruff_after.txt 2>&1`
- **確認**: Read `ruff_after.txt`。エラーがあれば次ステップで対応。

### ステップ36: ruff 自動修正（import順序・未使用importのみ安全セレクタ）
- **作業**（Bash）: `py -m ruff check --select I,F401 --fix src tests`
- **確認**（Bash）: 再実行 `py -m ruff check src tests` でエラー件数減少（0件目標）。

### ステップ37: ruff 残エラーの手動修正（上位3件まで）
- **作業**: `ruff_after.txt` の残エラーを1件ずつ Edit で修正。複雑な場合は該当ファイルを Read → Write で全体置換。
- **確認**（Bash）: `py -m ruff check src tests` で該当行消失。

### ステップ38: mypy 実行と結果確認
- **作業**（Bash）: `py -m mypy src > mypy_after.txt 2>&1`
- **確認**: Read `mypy_after.txt`。`INTERNALERROR` がなく、`Source file found twice` エラーも出ないこと（ステップ9の `explicit_package_bases` で解消済みのはず）。

### ステップ39: mypy 残エラーの個別対処（上位3件まで）
- **作業**: `mypy_after.txt` の残エラーを1件ずつ Edit で型注記補完等により修正。
- **確認**（Bash）: `py -m mypy src` で該当エラー消失。

### ステップ40: pytest サンプルテスト新規作成と実行
- **対象**: `D:\autonovel\tests\test_health.py`（新規）
- **作業**: Write:
  ```python
  from fastapi.testclient import TestClient

  from src.backend.server import app

  client = TestClient(app)


  def test_health_ok() -> None:
      resp = client.get("/health")
      assert resp.status_code == 200
      assert resp.json()["status"] == "ok"
  ```
- **確認**（Bash）: `py -m pytest tests/test_health.py -q` → `1 passed`。

---

## フェーズ G: 残骸・旧ログの退避（ステップ41–45）

### ステップ41: `backup/` ディレクトリ新規作成
- **作業**（Bash）: `New-Item -ItemType Directory -Path "D:\autonovel\backup" -Force | Out-Null`
- **確認**: Test-Path True。

### ステップ42: 旧ログtxt群をbackup/に移動
- **作業**（Bash）:
  ```powershell
  Move-Item "D:\autonovel\mypy_errors.txt","D:\autonovel\mypy_out.txt","D:\autonovel\ruff_e722.txt","D:\autonovel\ruff_f841_src.txt" "D:\autonovel\backup\" -ErrorAction SilentlyContinue
  ```
- **確認**（Bash）: `Get-ChildItem D:\autonovel\backup -Filter *.txt | Measure-Object | % Count` → 4（存在した分）。

### ステップ43: `tmp_replace_normalize.py` をbackup/に移動
- **作業**（Bash）: `Move-Item "D:\autonovel\tmp_replace_normalize.py" "D:\autonovel\backup\" -ErrorAction SilentlyContinue`
- **確認**: ルートから消失、backup/に存在。

### ステップ44: 残骸サブ `D:\autonovel\autonovel\` の最終点検
- **作業**（Bash）: `Get-ChildItem "D:\autonovel\autonovel" -Recurse -File | Select-Object FullName`
- **確認**: 重要未回収ファイルが0件であることをメモ。残骸 `.mypy_cache`, `plans/repair_plan_48steps.md`(旧版,既にステップ3で退避), `temp/test_models.py`(ステップ2で複製済), `src/*`(空), `tests/*`(空) のみなら次ステップで削除可。

### ステップ45: 残骸サブ削除とフェーズG commit
- **作業**（Bash）:
  ```powershell
  Remove-Item -Recurse -Force "D:\autonovel\autonovel"
  git add -A
  git commit -m "chore(phaseG): 残骸サブ削除と旧ログ退避"
  ```
- **確認**（Bash）: `Test-Path "D:\autonovel\autonovel"` → False。`git log --oneline -1` で新commit。

---

## フェーズ H: 結合検証とCIスクリプト・ドキュメント作成（ステップ46–48）

### ステップ46: `scripts/` 作成と `verify_all.ps1` / `README.md` 新規作成
- **対象**: `D:\autonovel\scripts\verify_all.ps1`, `D:\autonovel\README.md`
- **作業**:
  - `scripts/` ディレクトリ作成（Bash）: `New-Item -ItemType Directory -Path "D:\autonovel\scripts" -Force | Out-Null`
  - `scripts/verify_all.ps1`: Write:
    ```powershell
    Set-Location $PSScriptRoot\..
    Write-Host "=== ruff ==="
    py -m ruff check src tests
    Write-Host "=== mypy ==="
    py -m mypy src
    Write-Host "=== pytest ==="
    py -m pytest -q
    Write-Host "=== done ==="
    ```
  - `README.md`: Write:
    ```markdown
    # AutoNovel

    小説生成エンジンのリポジトリ。

    ## 構成
    - `src/`      : FastAPI バックエンド（server / tasks / routers / models / services）
    - `frontend/` : Vite + React フロントエンド
    - `tests/`    : pytest
    - `scripts/`  : 検証スクリプト

    ## 開発
    ```powershell
    py -m venv .venv
    .\.venv\Scripts\Activate.ps1
    py -m pip install -r requirements-dev.txt
    cd frontend; npm install; cd ..
    .\scripts\verify_all.ps1
    ```

    ## 実行
    `アプリ起動.bat` または `docker compose up --build`
    ```
- **確認**: 両ファイル Test-Path True。

### ステップ47: 最終検証スクリプト実行
- **作業**（Bash）: `& "D:\autonovel\scripts\verify_all.ps1"`
- **確認**: ruff/mypy/pytest が順次完走し、pytestが `1 passed`、致命的エラー(`INTERNALERROR`等)が0件であること。失敗時は対応フェーズに戻って修正。

### ステップ48: 最終Git commitと完了レポート作成
- **対象**: `D:\autonovel\plans\repair_report_final.md`（新規）
- **作業**:
  - Bash:
    ```powershell
    git add -A
    git commit -m "chore(phaseH): CIスクリプト/README整備で修復計画完了"
    ```
  - `plans/repair_report_final.md`: Write:
    ```markdown
    # 修復完了レポート（最終版）

    - 適用計画: repair_plan_48steps_final.md
    - 完了日: 2026-07-27

    ## 解消したレポート指摘5項目
    1. 二重フォルダ構成解消（残骸サブ `autonovel/` 削除）+ `アプリ起動.bat` cd先修正
    2. Dockerfile / frontend / エントリポイント(server.py, tasks/huey.py) 復元
    3. コア機能コード stub 復元（server/tasks/routers/services/models）
    4. mypy 重複モジュールエラー解消（pyproject.toml `explicit_package_bases`）+ 旧ログ退避
    5. plans/ ドキュメント集約（旧版 `_deprecated` 付きで退避）

    ## 残課題（後続サイクルで実装）
    - バックエンド LLM 本体実装（現在 `generate_with_llm` は stub）
    - frontend UI 実装（現在 `App.tsx` は最小表示のみ）
    - huey task 本体実装（現在 `sample_task.py` は ping stub）
    - SQLAlchemy データ永続化層の実装
    ```
- **確認**（Bash）: `git log --oneline | Measure-Object | % Count` → 5（Initial + A/C/D/E/G/H）。`Test-Path "D:\autonovel\plans\repair_report_final.md"` → True。

---

## 完了定義（Definition of Done）
1. `Test-Path "D:\autonovel\autonovel"` → False（残骸サブ削除済）。
2. `py -m pytest -q` が INTERNALERROR なく `1 passed`。
3. `py -m mypy src` が INTERNALERROR なく完走。
4. `py -m ruff check src tests` が0件（または許容範囲）。
5. `docker compose config > $null` が成功（Docker未導入環境は目視確認）。
6. `& "D:\autonovel\scripts\verify_all.ps1"` が全工程完走。

## ロールバック方針
- 各フェーズ終了時にGit commit済み。問題発生時は直前commitへ `git restore --source HEAD~1 -- <file>` または `git reset --hard HEAD~1`。
- backup/ への移動は「移動」で「削除」しないため、誤移動時は backup/ から戻せる。
- 残骸サブ削除（ステップ45）直前にステップ44で必ず再点検。

## 低性能LLM向け実行チェックリスト
- [ ] 各ステップは Write/Edit → 確認コマンド の2ツール呼び出しで完結
- [ ] 確認コマンドの出力が期待値(True/0件/指定文字列)でなければ、同じステップを再実行
- [ ] フェーズA–Hを順序通り実行（フェーズ内のステップも飛ばさない）
- [ ] commitは各フェーズ末尾の指定ステップのみ（ステップ8/22/28/34/45/48）
