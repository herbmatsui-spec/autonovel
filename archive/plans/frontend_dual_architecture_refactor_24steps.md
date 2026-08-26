# フロントエンド二重構造リファクタリング実装計画書

## 現状理解

### 重要な修正前提
ユーザーの前提（「frontend/ は足場のみ」）は**現時点と一致しません**。調査によると：

| レイヤー | 实际情况 |
|---------|---------|
| `streamlit_app/` | 約5,000 LOC の実運用コード（Controller/EventBus/Proxy/Store/Actions 全層保持） |
| `frontend/src/` | 約3,600 LOC・50ファイルのReact+Zustand app（`api.ts` の API メソッドは実在） |
| Streamlit 状態 | `pages_config.py` で React 移行通知に抑制済み（ADR Phase 4 済み） |
| React 状態 | `plans/STREAMLIT_TO_REACT_MIGRATION_72_STEPS.md` によれば Step 72 完了声称（ただし build 未検証） |

### 発見されたAPI Contract 不整合

| # | 不整合箇所 | 詳細 |
|---|-----------|------|
| 1 | `/api/chapters/import` vs `/api/episodes/chapters/import` | Streamlit `api_client.py:252` と React `api.ts:191` が `/api/chapters/import` を呼ぶが、バックエンドルートは `/api/episodes/chapters/import` |
| 2 | `/commercial/run` path 欠落 | バックエンドは `/commercial/run`（prefix `/commercial`、`<API prefixなし`）。Streamlit `api_client.py:117-131` は正常呼び出し。React `api.ts` には `runCommercialPipeline` メソッドが存在しない（status doc Step 30 声称と矛盾） |
| 3 | `/api/refine_erotic` React 未対応 | バックエンド有此Endpoint。React `api.ts` 欠落 |
| 4 | TypeScript 型が手書きで管理 | `frontend/src/types/api.ts` は手書きSSOT而非自動生成。`OptimizationReport ↔ OptimizationHistory` リネーム問題が docs に記録済み |

### 技術的負債

| # | 項目 | 詳細 |
|---|-----|------|
| T1 | Streamlitデッドコード | Controller/EventBus/Proxy/Stores/Actions 層は全使用されていないがコードは存在（~5,000 LOC） |
| T2 | React テスト不足 | Vitest 66行1ファイルのみ（`api.test.ts`）。コンポーネントテスト0件。@testing-library/react は導入済み |
| T3 | E2E テスト欠落 | Playwright 導入计划のみ、实际的テストなし |
| T4 | Frontend Build 未検証 | `tsc` が PATH にない问题でビルド確認不可 |
| T5 | ADR-0003 旧atos | ADR は「React 実装空」と记载だが現実は違う。更新が必要 |

---

## 24ステップ実装手順

### Phase 1: 现状記録・ベースライン作成（Step 1-3）

**Step 1** — 現在の git 状態を記録する
```bash
cd I:\autonovel\autonovel
git status --short
git log --oneline -3
```
**目的**: リファクタリング前後の差分比較用baseline

**Step 2** — API endpoint の実際の動きを两人前のフロントエンドで_TRACE する
```bash
# Streamlit API client から呼ばれる実際のパスを確認
grep -n "def.*import\|chapters/import\|/commercial" streamlit_app/api_client.py

# React API client から呼ばれる実際のパスを確認
grep -n "chapters/import\|commercial" frontend/src/api.ts
```
**目的**: バックエンド route と各クライアントのパスが本当にずれているかを確認（Step 3 の修正対象特定）

**Step 3** — バックエンド router 注册状況を確認する
```bash
grep -n "import.*router\|APIRouter\|/chapters\|/commercial\|/episodes" src/backend/server.py
grep -n "chapters/import\|commercial" src/backend/routers/episodes.py src/backend/routers/commercial.py
```
**目的**: バックエンド actual route path を确定し、Step 2 と突合して不整合を特定

---

### Phase 2: API Contract 不整合の修正（Step 4-8）

**Step 4** — `/api/chapters/import` → `/api/episodes/chapters/import` の不整合を React 側で修正する
```typescript
// frontend/src/api.ts の import_chapter 関数内
// 変更前:
const res = await fetch('/api/chapters/import', {

// 変更後:
const res = await fetch('/api/episodes/chapters/import', {
```
**目的**: React クライアントとバックエンド route を一致させる

**Step 5** — `/commercial/run` の React API メソッドを追加する
```typescript
// frontend/src/api.ts に以下を追加（他の run* メソッド参考に）
export const runCommercialPipeline = async (bookId: string, config: object) => {
  const res = await fetch('/commercial/run', {  // 注意: /api なし
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ book_id: bookId, config }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
};
```
**目的**: `refineErotic` 同様、バックエンド direct endpoint を React から呼べるようにする。Streamlit `api_client.py:117-131` を参考にすること

**Step 6** — `/api/refine_erotic` の React API メソッドを追加する
```typescript
// frontend/src/api.ts に以下を追加
export const refineErotic = async (params: {
  book_id: string;
  intensity: number;
  platform_preset: string;
}) => {
  const res = await fetch('/api/refine_erotic', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
};
```
**目的**: バックエンド有此Endpoint を React から利用可能に

**Step 7** — `frontend/src/types/api.ts` の `OptimizationHistory` と `OptimizationReport` 不整合を調査・修正する
```bash
# 現在の型定義を確認
grep -n "OptimizationReport\|OptimizationHistory" frontend/src/types/api.ts

# バックエンド schema を確認
grep -n "class OptimizationReportSchema" src/models/api_schemas.py
```
**目的**: 命名の食い違いが实际问题 일으げているか确认（API response のフィールドマッピング错误の可能性）

**Step 8** — OpenAPI contract 出一貫性をチェックする
```bash
python scripts/export_openapi.py  # 可能在
# または
cd I:\autonovel\autonovel
python -c "from src.backend.server import app; import json; print(json.dumps(app.openapi(), indent=2))" > /tmp/openapi_current.json
# frontend/src/types/api.ts と突合
```
**目的**: OpenAPI定義と実際のTS型のドリフトを可視化

---

### Phase 3: ADR-0003 更新（Step 9-10）

**Step 9** — `docs/adr/0003-streamlit-coexistence-strategy.md` の现状を追記・更新する
```markdown
<!-- ファイルの冒頭に STATUS を更新 -->


## Status
- **Superseded** by `plans/STREAMLIT_TO_REACT_MIGRATION_72_STEPS.md` (Step 72 完成: 2026-07-22)

<!-- 最終更新セクションを末尾に追加 -->


## Update History
- 2026-07-22: Superseded. React frontend (~3,600 LOC) is operational at `frontend/src/`.
  Streamlit is suppressed (migration notice only) but Phase 4 full deletion is pending.
  ADR Phase tables no longer reflect actual state.
```
**目的**: ADR が現状とかけ離れた情報を提供し続けることを防止

**Step 10** — `plans/STREAMLIT_TO_REACT_MIGRATION_72_STEPS.md` を .gitignore から除外する（または内容を `docs/adr/` に移動する）
```bash
# 現在 .gitignore に记载济みか確認
grep "STREAMLIT_TO_REACT" .gitignore
# 移动先として docs/adr/0006-streamlit-react-completion-report.md などへの統合を検討
```
**目的**: 移行完了报告が git 管理下にあることでチーム全員が参照可能に

---

### Phase 4: Streamlit デッドコードの段階的整理（Step 11-16）

**Step 11** — `streamlit_app/` のうち「使用されているもの」と「使用されていないもの」を分類する
```bash
# React への移行が完了しているTab对应的 Streamlit ファイルを確認
# pages_config.py が render する page から逆にたどる
cat streamlit_app/pages_config.py

# EventBus の全ハンドラ登録状況を確認
grep -n "subscribe\|handle_event\|UIControllerManager" streamlit_app/event_bus.py streamlit_app/controllers/manager.py
```
**目的**: Phase 4 deletion のため、「まだ生きているコード」と「完全に死んだコード」を峻別

**Step 12** — 空ファイル2件を削除する
```bash
rm streamlit_app/background.py   # 0 lines
rm streamlit_app/engine.py       # 0 lines
```
**目的**: Vestigial stub の削除（ADR Phase 4 に記載済み）

**Step 13** — 完全に死んだ Streamlit 層のファイルを特定し、アーカイブに移動する
```bash
# pages_config.py が migration notice のみを返しているなら、
# ui_tabs_*.py, sidebar_sections/*.py, controllers/, event_bus.py,
# actions.py, proxy.py, state.py, stores/ は現在実行されていない
# これらを archive/streamlit_retired/ に移動
mkdir -p archive/streamlit_retired
git mv streamlit_app/ui_tabs_*.py archive/streamlit_retired/
git mv streamlit_app/sidebar_sections archive/streamlit_retired/
git mv streamlit_app/controllers archive/streamlit_retired/
git mv streamlit_app/actions.py archive/streamlit_retired/
git mv streamlit_app/proxy.py archive/streamlit_retired/
git mv streamlit_app/state.py archive/streamlit_retired/
git mv streamlit_app/stores archive/streamlit_retired/
git mv streamlit_app/event_bus.py archive/streamlit_retired/
```
**目的**: ~5,000 LOCのデッドコードをgit履歴残しつつ実働コードから分離。注意：`streamlit_app/api_client.py` と `streamlit_app/app.py` はバックエンド接続検証用途で当面保持

**Step 14** — 保持する Streamlit ファイルを确认する
```bash
# 以下は当面残すファイル（React が不安定な時のフォールバック用途）
ls streamlit_app/app.py          # エントリポイント
ls streamlit_app/api_client.py   # API 検証用クライアント
ls streamlit_app/health_check.py # バックエンド生存確認
ls streamlit_app/backend_launcher.py  # バックエンド自動起動
ls streamlit_app/state_keys.py   # キー名定義（streamlit_app/ がまだ読み込む場合あり）
ls streamlit_app/pages_config.py # React 移行通知ページ
ls streamlit_app/sidebar.py     # 移行通知用サイドバー
ls streamlit_app/styles.py      # CSS
```
**目的**: フォールバック能力を保ちつつ、不要ファイルの删除范围を明確化

**Step 15** — `streamlit_app/` の `.gitignore` を更新して `archive/streamlit_retired/` 配下を除外する（または逆で、 retiring ファイルは .gitignore に追加しない）
```bash
# streamlit_retired/ を残す場合、gitignore に追加して忘却する
echo "streamlit_app/ui_tabs_*.py" >> .gitignore  # 既に archive に移動済みなので不要
# 实际操作: archive/streamlit_retired/ ごと git 管理から除外したい場合
# git rm -r --cached streamlit_app/ui_tabs_*.py など
```
**目的**: アーカイブファイルが git status に表示され続けることを防止

**Step 16** — `streamlit_app/` 内に読み込みが残っている場合に備えて、削除したファイルを import している箇所を最后確認する
```bash
grep -rn "from.*ui_tabs\|from.*actions\|from.*proxy\|from.*stores\|from.*event_bus\|from.*controllers\|from.*state\s" streamlit_app/*.py --include="*.py" | grep -v "archive/streamlit_retired"
```
**目的**: 残留参照查找してエラー preventable にする

---

### Phase 5: React テスト不足への対応（Step 17-20）

**Step 17** — `frontend/src/test/api.test.ts` を拡張し、重要な API メソッド全ての正常系・異常系テストを追加する
```typescript
// 追加対象: getBooks, deleteBook, generatePlan, getPlots, getChapters,
// getTaskStatus, stopTask, checkBackendHealth
// 参考: 既存の api.test.ts 形式
import { describe, it, expect, vi } from 'vitest';
import { getBooks, deleteBook, checkBackendHealth } from '@/api';

describe('API client', () => {
  it('getBooks returns array', async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve([{ id: '1', title: 'Test' }]),
    })) as any;
    const books = await getBooks('test-key');
    expect(Array.isArray(books)).toBe(true);
  });
  // 以下 similarly for other methods...
});
```
**目的**: 現在66行のテストを、主要API全メソッドのカバレッジに拡充

**Step 18** — React コンポーネントテストの雛形を作成する
```typescript
// frontend/src/test/components/BooksTab.test.tsx
// Vitest + @testing-library/react を使用
// import { render, screen, fireEvent } from '@testing-library/react';
// import { BooksTab } from '@/components/tabs/BooksTab';
// 雛形作成のみ。実際のテストは Phase 6 で継続

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BooksTab } from '@/components/tabs/BooksTab';

describe('BooksTab', () => {
  it('renders without crash', () => {
    // TODO: 実際の component props を確認してから実装
    expect(true).toBe(true); // placeholder
  });
});
```
**目的**: コンポーネントテストの基盤を作成（Step 17 で追加した api.test.ts 形式に準ずる）

**Step 19** — `frontend/src/test/setup.ts` に streamlit mock と同等の React テスト環境を整備する
```typescript
// setup.ts は現時点で1行のみ: import '@testing-library/jest-dom/vitest';
// 必要に応じて global fetch mock, localStorage mock, console.error suppress などを追加

// 追加例:
import { vi } from 'vitest';

beforeEach(() => {
  vi.clearAllMocks();
  globalThis.fetch = vi.fn();
});
```
**目的**: 各テストファイルで fetch mock の繰り返しを防止

**Step 20** — `playwright` 導入と E2E テストの第一歩を作成する
```bash
cd frontend
npm install --save-dev @playwright/test
npx playwright install --with-deps chromium
# e2e/app.spec.ts を作成（Books 一覧、Plot 編集基本的操作のテスト）
```
**目的**: ADR-0003 Phase 3 「E2E (Playwright)」を始める

---

### Phase 6: Frontend Build 検証（Step 21-22）

**Step 21** — TypeScript build を実行し、エラーを全て解消する
```bash
cd I:\autonovel\autonovel\frontend
npm install  # 依存関係確認
npx tsc -p tsconfig.app.json --noEmit
# エラー一覧を修正（型エラー、未使用変数など）
```
**目的**: `frontend/docs/react-migration-status.md` で報告された「tsc not recognized」問題の排查。PATH 问题が实际的か切り分ける

**Step 22** — `npm run build` が成功することを確認する
```bash
cd I:\autonovel\autonovel\frontend
npm run build
# dist/ ディレクトリにプロダクションビルドが生成されることを確認
ls dist/
```
**目的**: プロダクション可用性を保証（Vite build ＋ TypeScript compile 両方の成功）

---

### Phase 7: 最終統合検証（Step 23-24）

**Step 23** — React アプリとバックエンドの実際の通信を確認する
```bash
# 1) バックエンド起動確認
cd I:\autonovel\autonovel
python -c "from src.backend.server import app; print('backend import OK')"

# 2) React 開発サーバーがバックエンドに接続できることを確認
# frontend/.env の VITE_API_URL が http://localhost:8200 になっているか確認
cat frontend/.env

# 3) 実際の HTTP 通信テスト
curl http://localhost:8200/health
curl http://localhost:8200/api/books/  # 빈 배열即可

# 4) バックエンド route 注册确认
python -c "
from src.backend.server import app
for route in app.routes:
    if hasattr(route, 'path'):
        print(route.path)
" | grep -E "commercial|refine_erotic|episodes.*import"
```
**目的**: API contract が Step 4-6 の修正で実際に整合取了ことを確認

**Step 24** — リファクタリング完了後の git diff を記録し、成果物をまとめる
```bash
cd I:\autonovel\autonovel
git status --short
git diff --stat

# 記録すべき成果物:
# - docs/adr/0003-streamlit-coexistence-strategy.md (STATUS 更新)
# - frontend/src/api.ts (3メソッド追加: refineErotic, runCommercialPipeline, import修正)
# - frontend/src/test/api.test.ts (テスト拡充)
# - frontend/src/test/components/*.test.tsx (雛形)
# - archive/streamlit_retired/ (デッドコードのアーカイブ)
# - streamlit_app/ (削減後、残ったのは app.py, api_client.py, health_check.py, backend_launcher.py 等のみ)

# 最終コミットメッセージ例:
git add -A
git commit -m "refactor(frontend): unify Streamlit/React dual-layer architecture

- Fix API contract mismatches (chapters/import → episodes/chapters/import, add refineErotic and runCommercialPipeline to React api.ts)
- Update ADR-0003 status to Superseded
- Archive dead Streamlit layers to streamlit_retired/ (Controller/EventBus/Proxy/Stores/Actions)
- Delete vestigial empty files (background.py, engine.py)
- Expand React api.test.ts coverage and add component test scaffold
- Add Playwright for E2E testing
- Verify frontend build (npm run build)"
```
**目的**: 全変更を文書化してチームに情報提供。24ステップ完了。

---

## 想定成果物まとめ

| Phase | ステップ範囲 | 主要成果 |
|-------|------------|---------|
| 1 | 1-3 | API不整合の箇所を特定（2-3件の確認済み） |
| 2 | 4-8 | API contract 修正（3-4件）、OpenAPI整合性確認 |
| 3 | 9-10 | ADR-0003 更新、移动計画书の git 管理化 |
| 4 | 11-16 | Streamlitデッドコード ~5,000 LOC → archive化、保持ファイル明確化 |
| 5 | 17-20 | React Vitest 拡充、Playwright 導入 |
| 6 | 21-22 | TypeScript build 成功、dist/ 生成確認 |
| 7 | 23-24 | 実際のHTTP通信確認、git コミット |

## 注意事項

- **Step 13** で `git mv` を使うのは git 履歴を保つため（完全削除ではない）
- **Step 21** の `tsc` エラーが大量に出る場合は、Step 11-16 のデッドコードアーカイブによる import 切れではなく、既存の TypeScript エラーの可能性あり。その場合はエラー逐一対応
- **React の api.ts** は手書き管理のため、Step 8 の OpenAPI 型整合チェック結果を次回以降 `openapi-typescript` での自動生成に置換えるのが理想（`plans/openapi_type_pipeline_72step_plan.md` が既に存在）
- `archive/streamlit_retired/` は `.gitignore` に追加して良いが、削除はしない（git 履歴として有价值）