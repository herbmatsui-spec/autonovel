# OpenAPI型生成パイプライン有効化：72ステップ実装計画書

**対象**: 改善案5「OpenAPI型生成パイプラインの有効化」  
**目的**: `npm run generate-types` をCI必須ステップ化し、`frontend/src/types/api.ts` の手書き型を `api.generated.ts` の生成型へ完全置換  
**完了判定**: `npm run generate-types` 実行後差分ゼロ、手書き型の破棄  

---

## 前提条件・現状整理

| 項目 | 値 |
|------|-----|
| OpenAPI仕様書 | `docs/openapi.json` (2201行, OpenAPI 3.1.0) |
| 生成型ファイル | `frontend/src/types/api.generated.ts` (2315行, 未使用) |
| 手書き型ファイル | `frontend/src/types/api.ts` (184行, 現在使用中) |
| 重複型ファイル | `frontend/src/types/index.ts` (93行, 部分的重複) |
| バックエンドPydantic | `src/models/api_schemas.py` (228行, 18+モデル) |
| CI設定 | `.github/workflows/ci.yml` (41行, フロントエンドのjobなし) |
| npmスクリプト | `frontend/package.json:11` に `generate-types` あり |

### 型対応の現状

| Pydanticモデル (backend) | 手書きTS型 (api.ts) | 生成TS型 (api.generated.ts) |
|------------------------|-------------------|---------------------------|
| BookSchema | Book | `components["schemas"]` 内に同名 |
| PlotSchema | Plot | `components["schemas"]` 内に同名 |
| ChapterSchema | Chapter | `components["schemas"]` 内に同名 |
| BibleSchema | Bible | `components["schemas"]` 内に同名 |
| TaskStatusSchema | TaskStatus | `components["schemas"]` 内に同名 |
| EasyModeRequest | EasyModeParams | `components["schemas"]` 内に同名 |
| EpisodeGenerateRequest | EpisodeGenerateParams | `components["schemas"]` 内に同名 |
| PlanGenerationRequest | PlanGenerationParams | `components["schemas"]` 内に同名 |
| RetryFailedRequest | RetryFailedParams | `components["schemas"]` 内に同名 |
| PlotExpandRequest | PlotExpandParams | `components["schemas"]` 内に同名 |
| PlotRebuildRequest | PlotRebuildParams | `components["schemas"]` 内に同名 |
| CritiqueOptimizeRequest | CritiqueOptimizeParams | `components["schemas"]` 内に同名 |
| AuditPlanRequest | AuditPlanParams | `components["schemas"]` 内に同名 |
| ChapterImportRequest | ChapterImportParams | `components["schemas"]` 内に同名 |
| MarketingGenerateRequest | MarketingGenerateParams | `components["schemas"]` 内に同名 |
| PatchActionRequest | PendingPatch | 名前不同注意 |
| PromptVersion | PromptVersion | `components["schemas"]` 内に同名 |
| NarrativeMetricTrend | NarrativeMetricTrend | `operations` 応答型に存在 |

---

## Phase 1: 現状把握・バックアップ (Steps 1-12)

### Step 1: リポジトリの現状快照取得
- 対象: `frontend/src/types/` ディレクトリ全体のバックアップ取得
- 実行: 現在の `api.ts`, `index.ts`, `api.generated.ts` の内容を記録
- 確認: 各ファイルの行数、export されている型一覧

### Step 2: api.ts の全export一覧作成
- 対象: `frontend/src/types/api.ts`
- 実行: 184行から全export interface/export typeを抽出
- 出力: 対応表（TS型名 ↔ フィールド数・フィールド型）

### Step 3: api.generated.ts の全export一覧作成
- 対象: `frontend/src/types/api.generated.ts`
- 実行: 2315行から `paths`, `components.schemas`, `operations` の全キーを抽出
- 出力: 生成型名一覧とapi.tsとの対応関係

### Step 4: index.ts と api.ts の重複確認
- 対象: `frontend/src/types/index.ts` (93行) と `frontend/src/types/api.ts` (184行)
- 実行: 両ファイルに同名exportがあるかどうか確認
- 判定: index.ts が api.ts の完全部分集合かどうか

### Step 5: api.ts の import 使用箇所一覧作成
- 対象: `frontend/src/` 全体
- 実行: `grep -r "from.*types/api" frontend/src/` と `grep -r "from.*types/index" frontend/src/`
- 出力: import元のファイル名と行番号一覧

### Step 6: api.ts の各型が如何使用われているか確認
- 対象: Step 5 で特定した全ファイル
- 実行: 各importが戻り値型・引数型・props型として使用されているか確認
- 出力: 型ごとの使用箇所マトリクス

### Step 7: package.json の generate-types スクリプト確認
- 対象: `frontend/package.json`
- 実行: `"generate-types": "openapi-typescript ../docs/openapi.json -o src/types/api.generated.ts"` を確認
- 確認: openapi-typescript パッケージが devDependencies に存在するか

### Step 8: docs/openapi.json の基本構造確認
- 対象: `docs/openapi.json`
- 実行: paths数、components/schemas数、operations数を確認
- 出力: エンドポイント一覧と応答型の種類数

### Step 9: src/models/api_schemas.py の全モデル確認
- 対象: `src/models/api_schemas.py`
- 実行: 全Pydanticモデルのフィールド定義を確認
- 出力: 各モデルのフィールド名・型・デフォルト値一覧

### Step 10: server.py のエンドポイント戻り値型確認
- 対象: `src/backend/server.py`
- 実行: 各 `@app.get` / `@app.post` の戻り値の型注釈を確認
- 判定: Pydanticモデルを戻り値としているか、Dict[Any, Any]等か

### Step 11: CI設定の現在構造確認
- 対象: `.github/workflows/ci.yml`
- 実行: jobs, steps, runs-on, cache設定を確認
- 判定: フロントエンド用のjob是否存在

### Step 12: Git作業ブランチの作成
- 実行: `git checkout -b feature/openapi-type-generation`
- 確認: 作業ブランチに切り替え完了

---

## Phase 2: OpenAPI仕様書の検証と修正 (Steps 13-24)

### Step 13: OpenAPI仕様書のJSON妥当性確認
- 対象: `docs/openapi.json`
- 実行: `python -c "import json; json.load(open('docs/openapi.json'))"` でパース確認
- 判定: 有効なJSONかどうか

### Step 14: OpenAPI仕様書の必須フィールド確認
- 対象: `docs/openapi.json`
- 実行: `openapi`, `info`, `paths`, `components/schemas` の存在確認
- 判定: OpenAPI 3.xの必須フィールド欠缺なし

### Step 15: 各pathsのoperationId重複確認
- 対象: `docs/openapi.json` の paths 内全 operationId
- 実行: operationId がすべて一意かどうか確認
- 修正対象: 重複があれば operationId を一意に改名

### Step 16: 各pathsのresponses定義確認
- 対象: 全pathsのresponses
- 実行: 各responsesに `200` 応答が存在するか確認
- 判定: 応答型のschemaがcomponents/schemas参照か匿名か

### Step 17: components/schemas の全モデル確認
- 対象: `docs/openapi.json` の components/schemas
- 実行: 全モデルのフィールド定義がPydanticと一致するか確認
- 不一致: フィールド名・型・requiredの不一致を記録

### Step 18: requestBody の content-type 確認
- 対象: POST/PUT/PATCH endpoints
- 実行: requestBody の content-type が `application/json` か確認
- 修正: 缺失があれば追加

### Step 19: path parameters の型確認
- 対象: `{book_id}`, `{task_id}`, `{patch_id}` 等のpath parameter
- 実行: type が `integer` or `string` で正しく設定されているか確認
- 修正: 型不正があれば修正

### Step 20: query parameters の型確認
- 対象: `branch_id`, `ep_num` 等のquery parameter
- 実行: type が正しく設定されているか確認
- 修正: 型不正があれば修正

### Step 21: anyOf/oneOf スキーマの確認
- 対象: `RefineEroticRequest`, `PatchActionRequest` 等の anyOf
- 実行: anyOf の各候補が components/schemas に定義済みか確認
- 修正: 未定義のschema参照があれば追加

### Step 22: default 値の OpenAPI 表現確認
- 対象: `EasyModeRequest.tone_vibe: 0.6`, `RefineEroticRequest.intensity: 2` 等
- 実行: OpenAPI spec 上で default 値が正しく設定されているか確認
- 修正: 缺失があれば追加

### Step 23: nullable フィールドの表現確認
- 対象: `RollbackRequest.reason` (string | null)
- 実行: OpenAPI上で `nullable: true` または `type: ["string", "null"]` になっているか確認
- 修正: 缺失があれば修正

### Step 24: OpenAPI仕様書の再生成テスト
- 対象: `docs/openapi.json`
- 実行: FastAPIサーバから `/openapi.json` を取得し、ファイルと比較
- 判定: ファイルとリアルタイム生成が一致するか

---

## Phase 3: 型生成パイプラインの準備 (Steps 25-36)

### Step 25: openapi-typescript のバージョン確認
- 対象: `frontend/node_modules/openapi-typescript` または `frontend/package.json`
- 実行: `cd frontend && npm list openapi-typescript`
- 判定: 最新バージョンかどうか

### Step 26: generate-types スクリプトの手動実行テスト
- 対象: `frontend/package.json`
- 実行: `cd frontend && npm run generate-types`
- 確認: `src/types/api.generated.ts` が再生成されること

### Step 27: 生成された api.generated.ts の差分確認
- 対象: `frontend/src/types/api.generated.ts`
- 実行: `git diff frontend/src/types/api.generated.ts`
- 判定: 差分があるかないか

### Step 28: 生成型のpaths インターフェース確認
- 対象: `frontend/src/types/api.generated.ts` の `export interface paths`
- 実行: 全35エンドポイントのパスとHTTPメソッドが含まれているか確認
- 缺失: 不足があればOpenAPI specまたは生成コマンドを調査

### Step 29: 生成型のcomponents/schemas 確認
- 対象: `frontend/src/types/api.generated.ts` の `export interface components`
- 実行: Book, Plot, Chapter, Bible, TaskStatus, 全Request型が含まれているか確認
- 缺失: 不足があればOpenAPI specを確認

### Step 30: 生成型のoperations インターフェース確認
- 対象: `frontend/src/types/api.generated.ts` の `export interface operations`
- 実行: 各operationIdに対応するparametersとresponsesが正しいか確認
- 缺失: 不足があればOpenAPI specを確認

### Step 31: api.ts の型と api.generated.ts の型のフィールド比較（Book）
- 対象: `api.ts` の `Book` と `api.generated.ts` の `components["schemas"]["Book"]`
- 実行: フィールド名・型・必須性が一致するか比較
- 不一致: あれば記録

### Step 32: api.ts の型と api.generated.ts の型のフィールド比較（Plot/Chapter/Bible）
- 対象: `api.ts` の `Plot`, `Chapter`, `Bible` と生成型
- 実行: Step 31同样的比較
- 不一致: あれば記録

### Step 33: api.ts の型と api.generated.ts の型のフィールド比較（TaskStatus）
- 対象: `api.ts` の `TaskStatus` と生成型
- 実行: Step 31同样的比較
- 不一致: あれば記録

### Step 34: api.ts のParams型と生成Request型の比較
- 対象: `EasyModeParams` ↔ `EasyModeRequest`, `EpisodeGenerateParams` ↔ `EpisodeGenerateRequest` 等
- 実行: 全Params型と対応Request型の比較
- 不一致: あれば記録（名前マッピング表作成）

### Step 35: PendingPatch と PatchActionRequest の対応確認
- 対象: `api.ts` の `PendingPatch` と `api.generated.ts` の `PatchActionRequest`
- 実行: フィールド名が異なるためマッピング表を作成
- 判定: 使用箇所での変換が必要かどうか

### Step 36: NarrativeMetricTrend の生成型での存在確認
- 対象: `api.ts` の `NarrativeMetricTrend` と生成型
- 実行: `api.generated.ts` 内で同型または同等の型を検索
- 判定: 応答型として `get_narrative_metrics_*` operations に含まれているか

---

## Phase 4: api.ts から api.generated.ts への移行 (Steps 37-48)

### Step 37: types/index.ts の削除判断
- 対象: `frontend/src/types/index.ts`
- 実行: index.ts が api.ts の完全部分集合か確認（Step 4 の結果）
- 判定: 完全部分集合なら削除対象

### Step 38: types/index.ts の削除
- 対象: `frontend/src/types/index.ts`
- 実行: `rm frontend/src/types/index.ts`
- 確認: `grep -r "from.*types/index" frontend/src/` で参照がなくなったことを確認

### Step 39: api.ts の import 文的修正準備
- 対象: `frontend/src/types/api.ts`
- 実行: `api.generated.ts` から import する型を特定
- 方針: `import type { Book } from './api.generated'` の形式

### Step 40: api.ts の Book 型を置換
- 対象: `frontend/src/types/api.ts` の `export interface Book`
- 実行: `import type { components } from './api.generated'` に変更し `Book = components["schemas"]["Book"]` として再定義
- 確認: `type Book = components["schemas"]["Book"]` の形

### Step 41: api.ts の Plot 型を置換
- 対象: `frontend/src/types/api.ts` の `export interface Plot`
- 実行: Step 40同样的置換

### Step 42: api.ts の Chapter 型を置換
- 対象: `frontend/src/types/api.ts` の `export interface Chapter`
- 実行: Step 40同样的置換

### Step 43: api.ts の Bible 型を置換
- 対象: `frontend/src/types/api.ts` の `export interface Bible`
- 実行: Step 40同样的置換

### Step 44: api.ts の TaskStatus 型を置換
- 対象: `frontend/src/types/api.ts` の `export interface TaskStatus`
- 実行: Step 40同样的置換

### Step 45: api.ts の全Params型を置換
- 対象: `EasyModeParams`, `EpisodeGenerateParams`, `PlanGenerationParams`, `RetryFailedParams`, `PlotExpandParams`, `PlotRebuildParams`, `CritiqueOptimizeParams`, `AuditPlanParams`, `ChapterImportParams`, `MarketingGenerateParams`
- 実行: それぞれ対応する `*Request` 型として再定義
- 注意: `EasyModeParams` → `EasyModeRequest` 等の名前マッピング

### Step 46: api.ts の PendingPatch 型を置換または維持判断
- 対象: `frontend/src/types/api.ts` の `export interface PendingPatch`
- 実行: `PatchActionRequest` とフィールドが異なるため、生成型に合わせて再定義
- 方針: `PendingPatch` は生成型に同名がないため、手書きで維持するが、生成型の `PatchActionRequest` を参照する形に変更

### Step 47: api.ts の PromptVersion 型を置換
- 対象: `frontend/src/types/api.ts` の `export interface PromptVersion`
- 実行: `type PromptVersion = components["schemas"]["PromptVersion"]` に変更

### Step 48: api.ts の NarrativeMetricTrend 型を置換
- 対象: `frontend/src/types/api.ts` の `export interface NarrativeMetricTrend`
- 実行: 生成型の応答型から適切な型を割り当て
- 方針: 手書き維持または `operations` 応答型から抽出

---

## Phase 5: Streamlit側のPydantic整合性確認 (Steps 49-60)

### Step 49: Streamlit の api_client.py が返す型の確認
- 対象: `streamlit_app/api_client.py`
- 実行: `_request` 関数の戻り値の型注釈を確認
- 判定: Pydanticモデルでパースしているか、dictのままか

### Step 50: Streamlit が Pydantic モデルを戻り値としているか確認
- 対象: `streamlit_app/` 全体
- 実行: `from pydantic import BaseModel` の import と使用箇所を確認
- 判定: Streamlit が Pydantic モデルを直接使用しているか

### Step 51: Streamlit の API 応答型の整理
- 対象: `streamlit_app/api_client.py` の `_request` 戻り値
- 実行: 可能なら `from src.models.api_schemas import BookSchema` 等を import して型付け
- 方針: Streamlit は Pydantic を唯一の型源とする

### Step 52: Streamlit の ui_tabs_* ファイルで dict が直接使われているか確認
- 対象: `streamlit_app/ui_tabs_*.py`
- 実行: `.get()`, `["key"]` 等の dict アクセスを検索
- 判定: Pydantic モデルの `.model_validate()` が必要か

### Step 53: Streamlit の state.py が返す型の確認
- 対象: `streamlit_app/state.py`
- 実行: `UIState`, `WizardState` が dict 化される箇所を確認
- 判定: Pydantic の `.model_dump()` が使われているか

### Step 54: backend の server.py 戻り値型のPydantic整合性確認
- 対象: `src/backend/server.py` の全エンドポイント
- 実行: 戻り値の型注釈が Pydantic モデルかどうか確認
- 判定: `List[BookSchema]` 等の型注釈があるか

### Step 55: backend の server.py に 型注釈缺失がある場合の記録
- 対象: `src/backend/server.py`
- 実行: 戻り値に型注釈がないエンドポイントを記録
- 方針: 型注釈缺失は OpenAPI 生成に影響しないが、後で追加を検討

### Step 56: FastAPI の response_model 設定確認
- 対象: `src/backend/server.py`
- 実行: `@app.get(..., response_model=...)` の設定を確認
- 判定: response_model が設定されていれば OpenAPI に正しく反映される

### Step 57: response_model が設定されていないエンドポイントの記録
- 対象: `src/backend/server.py`
- 実行: response_model 缺失のエンドポイントを記録
- 方針: 現時点では放置し、後続タスクで追加を検討

### Step 58: Streamlit が参照する backend エンドポイント一覧
- 対象: `streamlit_app/api_client.py`
- 実行: `_request` で呼び出している path の一覧を作成
- 判定: すべて OpenAPI spec に含まれているか

### Step 59: Streamlit と OpenAPI spec のエンドポイント差分確認
- 対象: Step 58 の結果と `docs/openapi.json` の paths
- 実行: Streamlit が呼ぶが OpenAPI にないエンドポイントを特定
- 判定: 缺失があれば OpenAPI spec に追加

### Step 60: Streamlit 側の Pydantic 利用状況の最終確認
- 対象: `streamlit_app/` 全体
- 実行: `from src.models.api_schemas import` の import 件数確認
- 判定: Streamlit が Pydantic モデルを直接 import して使っているか

---

## Phase 6: CI統合・検証・完了判定 (Steps 61-72)

### Step 61: GitHub Actions CI に frontend job を追加
- 対象: `.github/workflows/ci.yml`
- 実行: `test` job の後に `frontend` job を追加
- 内容: Node.js setup → npm install → npm run generate-types → git diff check

### Step 62: CI の frontend job で generate-types を実行
- 対象: `.github/workflows/ci.yml`
- 実行: `cd frontend && npm run generate-types` step を追加
- 確認: コマンドが成功すること

### Step 63: CI に generate-types の差分チェックを追加
- 対象: `.github/workflows/ci.yml`
- 実行: `git diff --exit-code frontend/src/types/api.generated.ts` step を追加
- 判定: 差分があればCI失敗、差分なければ成功

### Step 64: CI に TypeScript コンパイルチェックを追加
- 対象: `.github/workflows/ci.yml`
- 実行: `cd frontend && npx tsc --noEmit` step を追加
- 判定: 型エラーがあればCI失敗

### Step 65: CI に ESLint チェックを追加（未実施なら）
- 対象: `.github/workflows/ci.yml`
- 実行: `cd frontend && npx eslint src/` step を追加（存在すれば）
- 判定: lint エラーがあればCI失敗

### Step 66: CI 全体の workflow を ローカルで模擬実行
- 対象: `.github/workflows/ci.yml`
- 実行: `act` (GitHub Actions local) でテスト、または手動で各stepを実行
- 判定: すべてのstepが成功すること

### Step 67: generate-types 実行後の api.generated.ts の git 差分確認
- 対象: `frontend/src/types/api.generated.ts`
- 実行: `git diff frontend/src/types/api.generated.ts`
- 判定: 差分ゼロ = 完了条件の一つ

### Step 68: api.ts から手書き型定義の完全移除
- 対象: `frontend/src/types/api.ts`
- 実行: `Book`, `Plot`, `Chapter`, `Bible`, `TaskStatus` 等の手書き定義を削除
- 確認: `type X = components["schemas"]["X"]` のみ残す

### Step 69: api.ts の import 整合性確認
- 対象: `frontend/src/types/api.ts`
- 実行: `import type { components } from './api.generated'` が正しく機能するか確認
- 判定: TypeScript が エラーなく解決できること

### Step 70: frontend 全ファイルの型整合性確認
- 対象: `frontend/src/` 全体
- 実行: `cd frontend && npx tsc --noEmit`
- 判定: 型エラーゼロ

### Step 71: Streamlit 側の動作確認
- 対象: `streamlit_app/`
- 実行: Streamlit アプリを起動し、API 呼び出しが正常に動作することを確認
- 判定: 画面が正常に表示され、API 応答が正しいこと

### Step 72: 完了判定の最終確認
- 実行: 以下のすべてが成立することを確認
  1. `npm run generate-types` 実行後 `git diff frontend/src/types/api.generated.ts` が差分ゼロ
  2. `frontend/src/types/api.ts` から手書き型定義が完全移除済み
  3. `frontend/src/types/index.ts` が削除済み
  4. `cd frontend && npx tsc --noEmit` が 型エラーゼロ
  5. CI の `generate-types` job が green
- 完了: 全条件満足で本計画完了

---

## 補足: よくある問題と対処

### 問題1: api.generated.ts に Book 型がない
- 原因: OpenAPI spec の components/schemas に Book が定義されていない
- 対処: `src/models/api_schemas.py` の `BookSchema` に `@class BookSchema` で name を追加し、FastAPI の response_model で使用

### 問題2: 生成型のフィールド名が snake_case のまま
- 原因: openapi-typescript のデフォルト設定では camelCase 変換がない
- 対処: `openapi-typescript ../docs/openapi.json -o src/types/api.generated.ts --strict` で生成後、手動で camelCase に揃えるか、スクリプトで変換

### 問題3: api.ts の `any` 型が生成型で `unknown` になる
- 原因: Pydantic の `Any` = OpenAPI の `{}` = TS の `unknown`
- 対処: `unknown` を許容するか、backend で具体的な型に修正

### 問題4: PendingPatch と PatchActionRequest のフィールド不一致
- 原因: `PendingPatch` は DB モデルの射影、`PatchActionRequest` は API リクエスト型
- 対処: `PendingPatch` は生成型に存在しないため手書きで維持し、コメントで `@deprecated` として将来統合を検討

### 問題5: NarrativeMetricTrend が生成型に存在しない
- 原因: OpenAPI spec の `/api/narrative_metrics/{book_id}/{branch_id}` の応答型が `unknown` になっている
- 対処: backend の `get_narrative_metrics_trend` エンドポイントに `response_model=NarrativeMetricTrendSchema` を追加（要Pydanticモデル作成）

---

## 出力ファイル一覧

| ファイル | 役割 |
|---------|------|
| `docs/openapi.json` | OpenAPI 3.1.0 仕様書（入力） |
| `frontend/src/types/api.generated.ts` | openapi-typescript による生成型（出力・唯一の情報源） |
| `frontend/src/types/api.ts` | 移行後の薄いラッパー（生成型への再定義のみ） |
| `frontend/src/types/index.ts` | 削除対象 |
| `.github/workflows/ci.yml` | generate-types CI 必須化 |
| `src/models/api_schemas.py` | Pydantic モデル（backend側の唯一の情報源） |

---

## 完了判定チェックリスト

```
[ ] Step 67: npm run generate-types 実行後 git diff がゼロ
[ ] Step 68: api.ts から手書き型定義が完全移除
[ ] Step 69: api.ts の import 整合性確認済み
[ ] Step 70: tsc --noEmit が 型エラーゼロ
[ ] Step 71: Streamlit 動作確認済み
[ ] Step 72: CI frontend job が green