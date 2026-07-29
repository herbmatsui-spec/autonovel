# AutoNovel プロジェクト修復 実装計画（48ステップ）— 現状ベース改訂版

> 作成日: 2026-07-27
> 前版 `autonovel/plans/repair_plan_48steps.md` は前提崩壊により廃止。本版が正。

## 0. 現状の実態（精査結果 2026-07-27 時点）

### 本番ルート: `D:\autonovel\` （`.git` あり、Initial commit 1件のみ）
```
D:\autonovel\
├ .git/                       # 履歴: Initial commit のみ
├ .kilo/                      (node_modules, agent-manager.json, .gitignore[npm用], package.json, package-lock.json)
├ .mypy_cache/                ← git追跡中（要除外）
├ .pytest_cache/              ← 同上
├ .ruff_cache/                ← 同上
├ frontend/                   ← 空ディレクトリ
├ output/                      ← 空ディレクトリ
├ plans/                      (7個の md ファイル: backend_startup_optimization, debug_remediation_48steps, duplicate-store-subscriptions, easy_mode_flow_validation, illustration_agent, refactor-app-tsx-god-component-12steps, remaining_issues_12steps)
├ src/                         (3ファイルのみ)
│   ├ models/easy_mode_schemas.py     (12行)
│   ├ backend/routers/easy_mode.py    (45行)
│   └ services/digest_service.py      (10行)
├ アプリ起動.bat                       (cd autonovel → docker compose up; ※cd先が存在しない)
├ autonovel.code-workspace            (path: "." の空構成)
├ docker-compose.yml                  (frontendサービス参照だがDockerfileなし即エラー)
├ mypy_errors.txt / mypy_out.txt / ruff_e722.txt / ruff_f841_src.txt  (旧作業ログ)
└ tmp_replace_normalize.py           (旧作業スクリプト)
```

### 残骸サブ: `D:\autonovel\autonovel\` （`.git` なし）
```
autonovel\
├ .mypy_cache/
├ plans/repair_plan_48steps.md   (前回計画、廃止)
├ temp/test_models.py           (★ステップ1でガード化済・存続)
├ src/backend/, src/engine/     (空)
└ tests/fixtures/               (空)
```

### 欠落している中核資産（両方に存在しない）
- `pyproject.toml` / `setup.cfg` / `mypy.ini`
- `Dockerfile`（backend / frontend）
- `requirements*.txt` / `package.json`（frontend 用）
- `src/backend/server.py`（FastAPI本体）/ `src/backend/tasks/huey.py`（worker）
- `streamlit_app/`, `models/`, `prompts/`, `schemas/`, `services/`, `kernels/`, `plugins/`
- pytest テスト本体（tests/ は空 fixtures のみ）

## 1. 前提・方針の明文化

- **本番ルート**: `D:\autonovel\` に一本化。残骸サブ `autonovel\` は内容を回収後に削除。
- **操作原則**: 各ステップは 1ファイル / 1コマンド完結。低性能 LLM でも Read → Edit/Write → 確認コマンド の3手順で実行可能。
- **Git運用**: `.gitignore` 整備後、小まめに commit（ステップごと可）。Initial commit のみなので安全に再構築可能。
- **取扱注意**: `tmp_replace_normalize.py` 等の旧スクリプト、ログtxt群は `.gitignore` 対象または `backup/` 退避。削除しない。
- **未実装資産**: 本計画では「推奨設計の最小構成ファイル」を新規作成し、レポート指摘項目（state.py 重複 等）は存在しないため対象外と明記。新規作成コードは後続サイクルで実装する前提の stub。

## 2. フェーズ構成

| フェーズ | ステップ | 目的 |
|---|---|---|
| A | 1–6  | 残骸サブの回収と `.gitignore` 整備 |
| B | 7–12 | プロジェクト設定ファイル新規整備 |
| C |13–18 | backend 最小構成の復元 |
| D |19–24 | frontend 最小構成の復元（Vite+React）|
| E |25–30 | Docker 設定の整合化 |
| F |31–36 | 静的解析/pytest 環境の整備 |
| G |37–42 | 残骸・旧ログの退避 |
| H |43–48 | 結合検証と CIスクリプト作成 |

---

## フェーズ A: 残骸サブの回収と `.gitignore` 整備

### ステップ1: 残骸サブ `autonovel/temp/test_models.py` の確認とガード維持
- **対象**: `D:\autonovel\autonovel\temp\test_models.py`
- **作業**: Read で内容確認。既に `if __name__ == "__main__":` ガード付きなら維持、無ければ Write で下記に差し替え。
  ```python
  import os, sys
  sys.path.append(os.getcwd())
  def _run() -> None:
      try:
          print("Starting model rebuild test...")
          from models import rebuild_models
          rebuild_models()
          print("✅ ok")
      except Exception as e:
          print(f"❌ {e}"); import traceback; traceback.print_exc(); sys.exit(1)
  if __name__ == "__main__":
      _run()
  ```
- **確認**: Read で `__main__` ガードが末尾にあること。

### ステップ2: 残骸サブ `autonovel/temp/` をルートへ移動
- **対象**: `D:\autonovel\autonovel\temp\`
- **作業**: PowerShell:
  ```powershell
  New-Item -ItemType Directory -Path "D:\autonovel\temp" -Force | Out-Null
  Copy-Item "D:\autonovel\autonovel\temp\test_models.py" "D:\autonovel\temp\test_models.py" -Force
  ```
  ※ Copy（移動でなく複製）で安全確保。元は残骸削除時まで残す。
- **確認**: `Test-Path "D:\autonovel\temp\test_models.py"` → True。

### ステップ3: 残骸サブ `autonovel/plans/` の回収
- **対象**: `D:\autonovel\autonovel\plans\repair_plan_48steps.md`
- **作業**: 前版は廃止だが参照用として保持。名前衝突回避のため改名コピー:
  ```powershell
  Copy-Item "D:\autonovel\autonovel\plans\repair_plan_48steps.md" "D:\autonovel\plans\repair_plan_48steps_deprecated.md" -Force
  ```
- **確認**: `Test-Path "D:\autonovel\plans\repair_plan_48steps_deprecated.md"` → True。

### ステップ4: 本計画ファイル自身のavenue保存確認
- **対象**: 本ファイル `D:\autonovel\plans\repair_plan_48steps_revised.md`
- **作業**: 本ステップ完了後、Write で保存済み。Read で末尾まで存在確認。
- **確認**: Read で内容が表示される。

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

- **確認**: `git status` で cache/legacy が untracked から外れる。

### ステップ6: 旧キャッシュを一旦削除して git 追跡解除
- **作業**:
  ```powershell
  git rm -r --cached .mypy_cache .pytest_cache .ruff_cache 2>$null
  Remove-Item -Recurse -Force "D:\autonovel\.mypy_cache" -ErrorAction SilentlyContinue
  Remove-Item -Recurse -Force "D:\autonovel\.pytest_cache" -ErrorAction SilentlyContinue
  Remove-Item -Recurse -Force "D:\autonovel\.ruff_cache" -ErrorAction SilentlyContinue
  ```
- **確認**: `git status --short` が短縮される。

---

## フェーズ B: プロジェクト設定ファイル新規整備

### ステップ7: `pyproject.toml` 新規作成
- **対象**: `D:\autonovel\pyproject.toml`（新規）
- **作業**: Write で下記最小構成:
  ```toml
  [tool.mypy]
  python_version = "3.12"
  mypy_path = ["src"]
  files = ["src"]
  exclude = ["temp/", "backup/", "archive/", ".*egg-info/"]
  explicit_package_bases = true
  ignore_missing_imports = true
  strict = false

  [tool.ruff]
  line-length = 100
  target-version = "py312"
  extend-exclude = ["temp", "backup", "archive", ".kilo", "node_modules"]

  [tool.ruff.lint]
  select = ["E", "F", "W", "I", "C90"]
  ignore = ["E501"]

  [tool.ruff.lint.mccabe]
  max-complexity = 15

  [tool.pytest.ini_options]
  testpaths = ["tests"]
  norecursedirs = ["temp", "backup", "archive", "frontend", "node_modules"]
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
    "sqlalchemy>=2.0",
    "huey>=2.5",
    "httpx>=0.27",
  ]

  [project.optional-dependencies]
  dev = ["mypy>=1.8", "ruff>=0.3", "pytest>=8.0", "pytest-asyncio>=0.23"]

  [tool.setuptools]
  package-dir = {"" = "src"}

  [tool.setuptools.packages.find]
  where = ["src"]
  ```

- **確認**: `Test-Path pyproject.toml` → True。`py -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"` で構文エラーなし。

### ステップ8: `requirements.txt` 新規作成（固定版）
- **対象**: `D:\autonovel\requirements.txt`（新規）
- **作業**: Write:
  ```
  fastapi>=0.110
  uvicorn[standard]>=0.27
  pydantic>=2.6
  sqlalchemy>=2.0
  huey>=2.5
  httpx>=0.27
  ```
- **確認**: Read で6行確認。

### ステップ9: `requirements-dev.txt` 新規作成
- **対象**: `D:\autonovel\requirements-dev.txt`（新規）
- **作業**: Write:
  ```
  -r requirements.txt
  mypy>=1.8
  ruff>=0.3
  pytest>=8.0
  pytest-asyncio>=0.23
  ```
- **確認**: Read で5行確認。

### ステップ10: Python 仮想環境 `.venv` 作成（推奨、省略可）
- **作業**:
  ```powershell
  py -m venv .venv
  .\.venv\Scripts\Activate.ps1
  py -m pip install --upgrade pip
  py -m pip install -r requirements-dev.txt
  ```
- **確認**: `Test-Path .venv\Scripts\python.exe` → True。`py -m pytest --version` でバージョン表示。
- **メモ**: 実行環境次第でスキップ可。各ステップの確認は `py -m` 形式で代替。

### ステップ11: `src/__init__.py` 群の作成
- **対象**: `src/__init__.py`, `src/backend/__init__.py`, `src/backend/routers/__init__.py`, `src/models/__init__.py`, `src/services/__init__.py`
- **作業**: 各パスに空ファイルを Write（0バイトでも可）。
- **確認**: `Get-ChildItem src -Recurse -Filter __init__.py | Measure-Object | % Lines` → 5。

### ステップ12: `tests/__init__.py` と `tests/conftest.py` 新規作成
- **対象**: `D:\autonovel\tests\__init__.py`(空), `D:\autonovel\tests\conftest.py`
- **作業**: conftest.py は:
  ```python
  import os, sys
  ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  if ROOT not in sys.path:
      sys.path.insert(0, ROOT)
  ```
- **確認**: `Test-Path tests/conftest.py` → True。

---

## フェーズ C: backend 最小構成の復元

### ステップ13: `src/backend/server.py` 新規作成（FastAPI 本体 + /health）
- **対象**: `src/backend/server.py`（新規）
- **作業**: Write:
  ```python
  from fastapi import FastAPI
  from src.backend.routers import easy_mode

  app = FastAPI(title="AutoNovel Backend")
  app.include_router(easy_mode.router, prefix="/easy_mode", tags=["easy_mode"])


  @app.get("/health")
  async def health() -> dict[str, str]:
      return {"status": "ok"}
  ```
- **確認**: `py -c "from src.backend.server import app; print(app.title)"` で "AutoNovel Backend" 表示（venv 有効時）。

### ステップ14: `easy_mode.py` に router 定義を追加
- **対象**: `src/backend/routers/easy_mode.py`
- **作業**: Edit で `app = FastAPI()` 行を削除し、上位 import と router を追加:
  ```python
  from fastapi import APIRouter, HTTPException
  from pydantic import ValidationError
  from typing import Dict, Any
  from src.models.easy_mode_schemas import EasyModeInput, GenerationResponse
  from src.services.digest_service import process_chapter, generate_suggestions
  from sqlalchemy.exc import SQLAlchemyError
  import logging

  router = APIRouter()
  logger = logging.getLogger(__name__)

  async def generate_with_llm(**kwargs: Any) -> Dict[str, Any]:
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
          logger.error(f"Validation failed: {e.errors}")
          raise HTTPException(status_code=422, detail=e.errors)
      except TimeoutError:
          logger.error("Generation timeout")
          raise HTTPException(status_code=504, detail="Generation timeout")
      except SQLAlchemyError as e:
          logger.error(f"Database error: {str(e)}")
          raise HTTPException(status_code=500, detail="Database error")
  ```
- **確認**: ruff/mypy をかけて引っかからない（ステップFで統合確認）。

### ステップ15: `models/easy_mode_schemas.py` の型注記補完
- **対象**: `src/models/easy_mode_schemas.py`
- **作業**: Read 後、pydantic BaseModel のフィールドに型注記がなければ補完。Pydantic v2 構文 `model_config = ConfigDict(...)` 推奨。
- **確認**: mypy で `easy_mode_schemas` にエラーなし。

### ステップ16: `services/digest_service.py` の型注記補完
- **対象**: `src/services/digest_service.py`
- **作業**: Read 後、`def process_chapter(...)` / `def generate_suggestions(...)` に戻り値型・引数型を付与。
- **確認**: mypy で当該ファイル0エラー。

### ステップ17: `src/backend/tasks/huey.py` 新規作成（worker用 stub）
- **対象**: `src/backend/tasks/__init__.py`(空), `src/backend/tasks/huey.py`
- **作業**: huey.py は:
  ```python
  from huey import Huey

  huey = Huey("autonovel", immediate=False)
  ```
- **確認**: `py -c "from src.backend.tasks.huey import huey; print(huey.name)"` で "autonovel" 表示。

### ステップ18: `src/backend/tasks/__init__.py` 作成
- **作業**: 空ファイル Write。
- **確認**: Test-Path True。

---

## フェーズ D: frontend 最小構成の復元（Vite + React）

### ステップ19: `frontend/package.json` 新規作成
- **対象**: `D:\autonovel\frontend\package.json`
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
      "vite": "^5.1.0",
      "typescript": "^5.4.0",
      "@types/react": "^18.2.0",
      "@types/react-dom": "^18.2.0"
    }
  }
  ```
- **確認**: Test-Path True。

### ステップ20: `frontend/index.html` 新規作成
- **対象**: `frontend/index.html`
- **作業**: Write Vite 標準 HTML:
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

### ステップ21: `frontend/vite.config.ts` 新規作成
- **対象**: `frontend/vite.config.ts`
- **作業**: Write:
  ```ts
  import { defineConfig } from "vite";
  import react from "@vitejs/plugin-react";

  export default defineConfig({
    plugins: [react()],
    server: { host: true, port: 5173 },
    preview: { host: true, port: 3000 },
    build: { outDir: "dist" },
  });
  ```
- **確認**: Test-Path True。

### ステップ22: `frontend/tsconfig.json` 新規作成
- **対象**: `frontend/tsconfig.json`
- **作業**: Write:
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
- **確認**: Test-Path True。

### ステップ23: `frontend/src/main.tsx` と `frontend/src/App.tsx` 新規作成
- **対象**: `frontend/src/main.tsx`, `frontend/src/App.tsx`
- **作業**:
  - `main.tsx`:
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
  - `App.tsx`:
    ```tsx
    export default function App() {
      return <div>AutoNovel Frontend</div>;
    }
    ```
- **確認**: 両ファイル Test-Path True。

### ステップ24: `frontend/.dockerignore` 新規作成
- **対象**: `frontend/.dockerignore`
- **作業**: Write:
  ```
  node_modules
  dist
  .git
  ```
- **確認**: Test-Path True。

---

## フェーズ E: Docker 設定の整合化

### ステップ25: ルート `Dockerfile`（backend 用）新規作成
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

### ステップ26: `frontend/Dockerfile` 新規作成
- **対象**: `frontend/Dockerfile`（新規）
- **作業**: Write 多段ビルド（dev / production target）:
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

### ステップ27: `docker-compose.yml` 修正（frontend 含む）
- **対象**: `D:\autonovel\docker-compose.yml`
- **作業**: Read 後 Write で下記に差し替え（healthcheck 付き）:
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
- **確認**: `docker compose config > $null` で構文エラーなし。

### ステップ28: `アプリ起動.bat` 修正（cd先をルートに）
- **対象**: `D:\autonovel\アプリ起動.bat`
- **作業**: Read 後、`cd /d "%~dp0autonovel"` 行を `cd /d "%~dp0"` に Edit。また compose up 行から `frontend-prod` を外し `frontend-dev` のみに（28行目相当）:
  ```bat
  docker compose up --build frontend-dev backend worker
  ```
- **確認**: Read で `cd /d "%~dp0"` のみ存在、autonovelパス参照なし。

### ステップ29: `autonovel.code-workspace` 整理
- **対象**: `D:\autonovel\autonovel.code-workspace`
- **作業**: 既存は `path: "."` 1件だけなのでそのまま維持で問題なし。必要なら settings に `files.exclude` 追加（任意）。本ステップは確認のみ。
- **確認**: 変更不要。

### ステップ30: `output/` と `frontend/` 空ディレクトリに `.gitkeep` 追加
- **対象**: `D:\autonovel\output\.gitkeep`, `D:\autonovel\frontend\.gitkeep`
  ※ frontend 配下は既にファイル多数の場合スキップ。空の場合のみ。
- **作業**: 各空 Write（0バイト）。
- **確認**: git で空ディレクトリが追跡される。

---

## フェーズ F: 静的解析 / pytest 環境の整備

### ステップ31: ruff 実行と結果確認
- **作業**: `py -m ruff check src tests > ruff_after.txt 2>&1`
- **確認**: Read `ruff_after.txt`。エラーが残れば次ステップで個別対応。

### ステップ32: ruff 自动修正（安全セレクタのみ）
- **作業**: `py -m ruff check --select I,F404 --fix src tests`
- **確認**: 再実行 `ruff check src tests` で件数減少。

### ステップ33: ruff 残エラーの手動修正（上位5件）
- **作業**: `ruff_after.txt` の上位エラーを1件ずつ Edit で修正。
- **確認**: 再実行で対象行エラー消失。

### ステップ34: mypy 実行と結果確認
- **作業**: `py -m mypy src > mypy_after.txt 2>&1`
- **確認**: Read `mypy_after.txt`。INTERNALERROR なし。

### ステップ35: mypy 残エラーの個別対処（上位5件）
- **作業**: 型注記不足等を1件ずつ Edit で補完。
- **確認**: 再実行で該当エラー消失。

### ステップ36: pytest サンプルテスト新規作成
- **対象**: `D:\autonovel\tests\test_health.py`
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
- **確認**: `py -m pytest tests/test_health.py -q` で 1 passed。`httpx` は requirements に既存。

---

## フェーズ G: 残骸・旧ログの退避

### ステップ37: `backup/` ディレクトリ新規作成
- **作業**: `New-Item -ItemType Directory -Path "D:\autonovel\backup" -Force`
- **確認**: Test-Path True。

### ステップ38: 旧ログtxt群を backup/ に移動
- **作業**:
  ```powershell
  Move-Item "D:\autonovel\mypy_errors.txt" "D:\autonovel\backup\"
  Move-Item "D:\autonovel\mypy_out.txt" "D:\autonovel\backup\"
  Move-Item "D:\autonovel\ruff_e722.txt" "D:\autonovel\backup\"
  Move-Item "D:\autonovel\ruff_f841_src.txt" "D:\autonovel\backup\"
  ```
- **確認**: ルートの txt が消失、backup/ に4ファイル。

### ステップ39: `tmp_replace_normalize.py` を backup/ に移動
- **作業**: `Move-Item "D:\autonovel\tmp_replace_normalize.py" "D:\autonovel\backup\"`
- **確認**: ルートから消失、backup/ に存在。

### ステップ40: 残骸サブ `D:\autonovel\autonovel\` の確認と削除準備
- **作業**: 中身を再点検:
  ```powershell
  Get-ChildItem "D:\autonovel\autonovel" -Recurse -File | Select-Object FullName
  ```
  必要ファイルがなければ次ステップで削除。重要なものがあれば backup/ へ退避。
- **確認**: 残存重要ファイルが0件であることをメモ。

### ステップ41: 残骸サブ削除
- **作業**:
  ```powershell
  Remove-Item -Recurse -Force "D:\autonovel\autonovel"
  ```
- **確認**: `Test-Path D:\autonovel\autonovel` → False。

### ステップ42: 旧 `backup/repair_plan_48steps_deprecated.md` の移動
- **作業**: 万一残っていれば。通常はステップ3で `D:\autonovel\plans\` にコピー済み、残骸削除でオリジナル消失。問題なし。
- **確認**: 確認のみ、編集不要。

---

## フェーズ H: 結合検証と CI スクリプト作成

### ステップ43: `scripts/` ディレクトリ新規
- **作業**: `New-Item -ItemType Directory -Path "D:\autonovel\scripts"`
- **確認**: Test-Path True。

### ステップ44: `scripts/typecheck.ps1` 新規
- **対象**: `scripts/typecheck.ps1`
- **作業**: Write:
  ```powershell
  Set-Location $PSScriptRoot\..
  py -m mypy src
  ```
- **確認**: `& "D:\autonovel\scripts\typecheck.ps1"` で mypy 完走。

### ステップ45: `scripts/lint.ps1` 新規
- **対象**: `scripts/lint.ps1`
- **作業**: Write:
  ```powershell
  Set-Location $PSScriptRoot\..
  py -m ruff check src tests
  ```
- **確認**: 実行で ruff 完走。

### ステップ46: `scripts/verify_all.ps1` 新規
- **対象**: `scripts/verify_all.ps1`
- **作業**: Write:
  ```powershell
  Set-Location $PSScriptRoot\..
  Write-Host "=== ruff ==="
  py -m ruff check src tests
  Write-Host "=== mypy ==="
  py -m mypy src
  Write-Host "=== pytest collect ==="
  py -m pytest --collect-only -q
  Write-Host "=== done ==="
  ```
- **確認**: 実行で3ツール順次完走。

### ステップ47: `README.md` 新規作成
- **対象**: `D:\autonovel\README.md`
- **作業**: Write:
  ```markdown
  # AutoNovel

  小説生成エンジンのリポジトリ。

  ## 構成
  - `src/`      : FastAPI バックエンド
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

  ##実行
  `アプリ起動.bat` または `docker compose up --build`
  ```
- **確認**: Test-Path True。

### ステップ48: 最終 Git commit と完了レポート
- **作業**:
  ```powershell
  git add -A
  git commit -m "chore: 修復計画適用 (48ステップ整備、枠構成復元)"
  ```
  その後、`D:\autonovel\plans\repair_report.md` を Write で作成:
  ```markdown
  # 修復完了レポート

  - 適用計画: repair_plan_48steps_revised.md
  - 完了日: 2026-07-27
  - 残骸サブ autonovel/ 削除済
  - backend / frontend / Docker / 静的解析環境 整備済
  - 残課題: バックエンド・LLM 本体実装、frontend UI 実装、huey task 本体実装（現在 stub）
  ```
- **確認**: `git log --oneline` で2件目の commit 確認。`scripts/verify_all.ps1` で最終 green。

---

## 完了定義（Definition of Done）
1. `Get-ChildItem D:\autonovel` が `autonovel\`（残骸）を含まない。
2. `py -m pytest --collect-only` が INTERNALERROR なく完走。
3. `py -m mypy src` が INTERNALERROR なく完走。
4. `py -m ruff check src tests` が0件（又は許容範囲）。
5. `docker compose config` が構文 OK。
6. `scripts/verify_all.ps1` が全工程通して完走。

## ロールバック方針
- 各フェーズ終了後に `git commit`。問題が生じたら直前 commit へ `git restore`。
- backup/ への移動は「移動」で「削除」しない。誤移動時は backup/ から戻せる。
- 残骸サブ削除（ステップ41）直前にステップ40で必ず再確認。
