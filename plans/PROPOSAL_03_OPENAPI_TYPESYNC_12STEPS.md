# 提案3: OpenAPI駆動による End-to-End 型同期（スキーマファースト連携）実装計画書（全12ステップ）

**対象レイヤー**: `scripts/`, `src/backend/schemas/`, `frontend/src/api/`, `frontend/src/types/`  
**目的**: バックエンド（FastAPI / Pydantic）の変更を単一の真実（Single Source of Truth）として、フロントエンドのTypeScript型定義（`api.generated.ts`）を自動生成・完全同期させる。また、エラーレスポンスを [RFC 7807 Problem Details](https://datatracker.ietf.org/doc/html/rfc7807) 規格に統一し、API仕様変更時のランタイムエラーをゼロにする。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全な実装コード、スクリプト、設定ファイル、検証コマンド** を完備しています。

---

## 📋 ステップ一覧

| Step | 分類 | 対象ファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | OpenAPI抽出 | `scripts/export_openapi.py` | FastAPIアプリから静的 `docs/openapi.json` を生成するスクリプト |
| **Step 2** | エラー規格化 | `src/backend/schemas/problem_details.py` | RFC 7807 Problem Details 準拠のPydanticモデル定義 |
| **Step 3** | 例外統一 | `src/backend/error_handlers.py` | 全HTTPExceptionを RFC 7807 形式に変換するグローバル例外ハンドラ |
| **Step 4** | サーバー統合 | `src/backend/server.py` | OpenAPIメタデータ設定（Title/Version）と例外ハンドラの登録 |
| **Step 5** | 型生成スクリプト | `frontend/package.json` | バックエンド起動不要で型生成を行う `npm run generate:types` の改修 |
| **Step 6** | 型自動生成実行 | `frontend/src/types/api.generated.ts` | 実際にOpenAPIからTypeScript型を自動生成しコミット |
| **Step 7** | 型安全クライアント | `frontend/src/api/client.ts` | 自動生成型をバインドした型安全fetch/Axiosクライアント基盤 |
| **Step 8** | フロント側エラー型 | `frontend/src/types/problemDetails.ts` | フロントエンド用 ProblemDetails 型定義と判別ガード |
| **Step 9** | エラーToast連動 | `frontend/src/api/errorHandler.ts` | RFC 7807 レスポンスをパースし適切なToastメッセージを出す共通処理 |
| **Step 10** | 型安全Hook | `frontend/src/api/hooks/useBooks.ts` | 生成型を適用した書籍一覧・取得用 React Query カスタムフック |
| **Step 11** | バックエンド検証 | `tests/unit/test_problem_details.py` | RFC 7807 エラーレスポンス形式が正しく返るかの単体テスト |
| **Step 12** | フロント検証 | `frontend/package.json` | `npm run typecheck` によるフロントエンド型検査の全通過確認 |

---

## 🛠 各ステップ詳細仕様

### Step 1: FastAPI から OpenAPI JSON を自動抽出するスクリプト
- **目的**: バックエンドサーバーを起動することなく、コードベースから直接最新の `docs/openapi.json` を出力する。
- **対象ファイル**: `scripts/export_openapi.py`（新規作成）
- **実装コード**:
```python
"""FastAPI アプリケーションから openapi.json をエクスポートするスクリプト。"""
import json
import os
import sys
from pathlib import Path

# ルートディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.backend.server import app

def export_openapi():
    output_path = Path("docs/openapi.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    openapi_schema = app.openapi()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"OpenAPI schema successfully exported to: {output_path}")

if __name__ == "__main__":
    export_openapi()
```
- **検証コマンド**: `python scripts/export_openapi.py`
- **合格条件**: `docs/openapi.json` が生成され、JSONとして妥当であること。

---

### Step 2: RFC 7807 Problem Details Pydantic モデルの定義
- **目的**: 統一されたAPIエラーレスポンス構造を定義する。
- **対象ファイル**: `src/backend/schemas/problem_details.py`（新規作成）
- **実装コード**:
```python
"""RFC 7807 Problem Details スキーマ。"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


class ProblemDetails(BaseModel):
    """RFC 7807 に準拠した構造化エラーレスポンス。"""
    type: str = Field(
        default="about:blank",
        description="エラー種別を識別するURI参照",
    )
    title: str = Field(
        ...,
        description="人間が読める簡潔なエラー要約",
    )
    status: int = Field(
        ...,
        description="HTTPステータスコード",
    )
    detail: Optional[str] = Field(
        default=None,
        description="この発生インスタンスに特有の人道的な詳細説明",
    )
    instance: Optional[str] = Field(
        default=None,
        description="エラーが発生した具体的なリソースまたはリクエストパス",
    )
    invalid_params: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="バリデーションエラー時のフィールド別詳細",
    )
```
- **検証コマンド**: `python -c "from src.backend.schemas.problem_details import ProblemDetails; print('ProblemDetails schema valid')"`
- **合格条件**: インポート成功。

---

### Step 3: グローバル例外ハンドラの実装
- **目的**: `HTTPException` や `RequestValidationError` を自動的に `ProblemDetails` 形式に整形して返却する。
- **対象ファイル**: `src/backend/error_handlers.py`（新規作成）
- **実装コード**:
```python
"""グローバル例外ハンドラ (RFC 7807 準拠)。"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.backend.schemas.problem_details import ProblemDetails


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTPException を RFC 7807 形式に変換"""
    problem = ProblemDetails(
        type=f"https://autonovel.local/errors/http-{exc.status_code}",
        title=exc.detail if isinstance(exc.detail, str) else "HTTP Error",
        status=exc.status_code,
        detail=str(exc.detail),
        instance=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic バリデーションエラーを RFC 7807 形式に変換"""
    invalid_params = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        invalid_params.append({
            "name": loc,
            "reason": err.get("msg", "Invalid value"),
        })

    problem = ProblemDetails(
        type="https://autonovel.local/errors/validation-error",
        title="リクエストパラメータの検証に失敗しました",
        status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="送信されたデータに形式または値の不正があります",
        instance=request.url.path,
        invalid_params=invalid_params,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )
```
- **検証コマンド**: `python -c "from src.backend.error_handlers import http_exception_handler; print('Error handlers valid')"`
- **合格条件**: インポート成功。

---

### Step 4: FastAPI アプリケーションへの例外ハンドラ登録
- **目的**: `src/backend/server.py` にハンドラを登録し、全エラーレスポンスを統一する。
- **対象ファイル**: `src/backend/server.py`
- **修正内容**:
```python
# server.py の FastAPI インスタンス作成箇所に追加
from fastapi.exceptions import RequestValidationError
from src.backend.error_handlers import http_exception_handler, validation_exception_handler

app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
```
- **検証コマンド**: `python -m ruff check src/backend/server.py`
- **合格条件**: 構文チェック通過。

---

### Step 5: frontend/package.json の型生成コマンド改修
- **目的**: バックエンドの抽出スクリプト実行とTypeScript型生成を1コマンドで一括実行できるようにする。
- **対象ファイル**: `frontend/package.json`
- **修正内容**:
```json
{
  "scripts": {
    "export:openapi": "python ../scripts/export_openapi.py",
    "generate:api-types": "npm run export:openapi && npx openapi-typescript ../docs/openapi.json -o src/types/api.generated.ts"
  }
}
```
- **検証コマンド**: `cat frontend/package.json | grep generate:api-types`
- **合格条件**: スクリプトが登録されていること。

---

### Step 6: OpenAPI から TypeScript 型の自動生成実行
- **目的**: 最新のバックエンド定義から `frontend/src/types/api.generated.ts` を実際に生成する。
- **コマンド**:
```bash
python scripts/export_openapi.py
cd frontend && npx openapi-typescript ../docs/openapi.json -o src/types/api.generated.ts
```
- **合格条件**: `frontend/src/types/api.generated.ts` が正常に出力され、`paths` や `components` が定義されていること。

---

### Step 7: 型安全 API クライアント基盤の実装
- **目的**: 自動生成された型定義と連動する軽量型安全 fetch ラッパーを作成。
- **対象ファイル**: `frontend/src/api/client.ts`（新規作成）
- **実装コード**:
```typescript
/**
 * 型安全 API クライアント基盤
 */
import type { paths } from "../types/api.generated";

export async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const token = localStorage.getItem("auth_token");
  const headers = new Headers(options?.headers || {});
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw errorData;
  }

  return response.json() as Promise<T>;
}
```
- **合格条件**: エラーなく保存されること。

---

### Step 8: フロントエンド用 ProblemDetails 型定義
- **目的**: バックエンドの RFC 7807 形式をフロントエンドで安全に型安全処理できるようにする。
- **対象ファイル**: `frontend/src/types/problemDetails.ts`（新規作成）
- **実装コード**:
```typescript
/**
 * RFC 7807 Problem Details フロントエンド型定義
 */
export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  invalid_params?: Array<{
    name: string;
    reason: string;
  }>;
}

export function isProblemDetails(error: unknown): error is ProblemDetails {
  return (
    typeof error === "object" &&
    error !== null &&
    "title" in error &&
    "status" in error
  );
}
```
- **合格条件**: ファイル作成完了。

---

### Step 9: エラーToast通知・フォームエラー共通連動処理
- **目的**: APIエラー発生時に、RFC 7807 の `title` や `detail` を自動抽出して分かりやすいメッセージを表示するハンドラ。
- **対象ファイル**: `frontend/src/api/errorHandler.ts`（新規作成）
- **実装コード**:
```typescript
import { isProblemDetails } from "../types/problemDetails";

export function getErrorMessage(error: unknown): string {
  if (isProblemDetails(error)) {
    if (error.invalid_params && error.invalid_params.length > 0) {
      const details = error.invalid_params.map((p) => `${p.name}: ${p.reason}`).join(", ");
      return `${error.title} (${details})`;
    }
    return error.detail || error.title;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "予期せぬエラーが発生しました";
}
```
- **合格条件**: ファイル作成完了。

---

### Step 10: 生成型を適用した React Query カスタムフック
- **目的**: 書籍データ取得（`GET /api/books`）に生成型を適用し、補完が完全に効くフックを作成。
- **対象ファイル**: `frontend/src/api/hooks/useBooks.ts`（新規作成）
- **実装コード**:
```typescript
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../client";
import type { paths } from "../../types/api.generated";

// /api/books のレスポンス型を自動生成型から抽出
type BooksResponse = paths["/api/books"]["get"]["responses"]["200"]["content"]["application/json"];

export function useBooks() {
  return useQuery<BooksResponse>({
    queryKey: ["books"],
    queryFn: () => apiFetch<BooksResponse>("/api/books"),
  });
}
```
- **合格条件**: ファイル作成完了。

---

### Step 11: RFC 7807 エラーレスポンスの単体テスト
- **目的**: バックエンドのエラーハンドラが規格通りのJSONキーを返すことを検証。
- **対象ファイル**: `tests/unit/test_problem_details.py`（新規作成）
- **実装コード**:
```python
import pytest
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport
from src.backend.server import app

@pytest.mark.asyncio
async def test_rfc7807_error_response_format():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 存在しないパスへのアクセスで 404
        res = await ac.get("/api/books/9999999")
        assert res.status_code in (401, 403, 404)
        data = res.json()
        
        # RFC 7807 の必須・推奨フィールドの存在検証
        assert "status" in data
        assert "title" in data
        assert "type" in data
        assert res.headers.get("content-type") == "application/problem+json"
```
- **検証コマンド**: `pytest tests/unit/test_problem_details.py -v --no-cov`
- **合格条件**: テストPASS。

---

### Step 12: フロントエンド型チェック検証
- **目的**: 新規追加したフックやクライアントがTypeScript型エラーなく完全にビルドできることを検証。
- **検証コマンド**:
```bash
cd frontend && npm run typecheck
```
- **合格条件**: TypeScriptコンパイルがエラー0件で完了すること。
