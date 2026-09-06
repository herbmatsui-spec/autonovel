# フロントエンド E2E/統合テスト基盤 実装計画書 (Playwright + Vitest + CI)

## 1. 概要・目的

| 項目 | 内容 |
|------|------|
| 対象リポジトリ | `frontend/` (Vite + React 18 + TypeScript) |
| 既存テスト基盤 | Vitest + React Testing Library + MSW (単体・コンポーネント・統合テスト 6ファイル) |
| 導入ツール | **Playwright** (E2E), Vitest (既存継続), MSW (API モック継続) |
| テスト種別追加 | E2E テスト (ブラウザ実ブラウザ), 視覚回帰テスト (任意), パフォーマンス計測 |
| 目標ユーザーフロー | **ガチャ → 執筆 → 納品** (企画生成 → ストリーミング/標準執筆 → ZIPエクスポート or Studio昇格) |
| CI 組み込み | GitHub Actions: `lint` → `typecheck` → `test:ci` (Vitest) → `test:e2e` (Playwright) |
| 実行環境 | ヘッドレス Chromium (CI), 開発時は headed/デバッグ可 |

---

## 2. 現状ギャップ分析

| 観点 | 現状 | 必要対応 |
|------|------|----------|
| E2E テストランナー | なし | **Playwright 導入** |
| 実ブラウザテスト | なし (jsdomのみ) | Chromium/Firefox/WebKit 実行環境 |
| ユーザーフロー自動化 | なし | **ガチャ→執筆→納品** の E2E シナリオ実装 |
| CI パイプライン | なし (verify_all.ps1 のみ Python) | GitHub Actions ワークフロー新規作成 |
| テストデータ管理 | MSW ハンドラ分散 | テスト用フィクスチャ/シナリオデータ集約 |
| 視覚確認 | なし | スクリーンショット比較 (任意・将来拡張) |

---

## 3. 導入手順 (全 24 ステップ)

> 各ステップは **1 つのコミット/ PR 単位** で完結する粒度。低性能 LLM でも順番に実行するだけで迷わない設計。

| # | フェーズ | 対象ファイル/作業 | 詳細内容 | 成果物/確認コマンド |
|---|---------|-----------------|---------|-------------------|
| 1 | **準備** | `frontend/package.json` | Playwright 依存追加: `@playwright/test`, `@playwright/experimental-ct-react` (コンポーネントテスト用・任意), `playwright` (ブラウザインストール用) | `npm i -D @playwright/test` 成功 |
| 2 | **準備** | `frontend/playwright.config.ts` | **新規作成**: `defineConfig({ testDir: './tests/e2e', fullyParallel: true, retries: process.env.CI ? 2 : 0, workers: process.env.CI ? 1 : undefined, reporter: [['html', { open: 'never' }], ['json', { outputFile: 'test-results/results.json' }]], use: { baseURL: 'http://localhost:5173', trace: 'on-first-retry', screenshot: 'only-on-failure', video: 'retain-on-failure' }, projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }, { name: 'firefox', use: { ...devices['Desktop Firefox'] } }, { name: 'webkit', use: { ...devices['Desktop Safari'] } }], webServer: { command: 'npm run dev', url: 'http://localhost:5173', reuseExistingServer: !process.env.CI, timeout: 120000 } })` | ファイル作成確認 |
| 3 | **準備** | `frontend/tests/e2e/` | ディレクトリ作成: `mkdir -p frontend/tests/e2e/fixtures frontend/tests/e2e/utils` | ディレクトリ存在確認 |
| 4 | **準備** | `frontend/tests/e2e/fixtures/test-data.ts` | **新規作成**: テスト用固定データ (ジャンル、キャラクター、ガチャ案、期待出力等) を一元管理。MSW ハンドラと共有可能な形で定義 | ファイル作成確認 |
| 5 | **準備** | `frontend/tests/e2e/utils/test-helpers.ts` | **新規作成**: 共通ユーティリティ (待機ヘルパー、セレクタ取得、認証回避、ログインモック、スクリーンショット命名規則) | ファイル作成確認 |
| 6 | **準備** | `frontend/tests/e2e/utils/msw-handlers.ts` | **新規作成**: E2E 用 MSW ハンドラ (Vitest 用と分離・統合も可)。`/easy_mode/gacha`, `/easy_mode/digest`, `/easy_mode/generate/stream`, `/easy_mode/export-with-data`, `/easy_mode/promote` をモック | ファイル作成確認 |
| 7 | **準備** | `frontend/tests/e2e/global-setup.ts` | **新規作成**: Playwright グローバルセットアップ (テスト用データベース初期化、認証状態保存、ブラウザコンテキスト設定) | ファイル作成確認 |
| 8 | **準備** | `frontend/tests/e2e/global-teardown.ts` | **新規作成**: グローバルティアダウン (クリーンアップ、レポート収集) | ファイル作成確認 |
| 9 | **準備** | `frontend/playwright.config.ts` | `globalSetup: './tests/e2e/global-setup.ts', globalTeardown: './tests/e2e/global-teardown.ts'` 追加 | 設定反映確認 |
| 10 | **準備** | `frontend/package.json` | scripts 追加: `"test:e2e": "playwright test", "test:e2e:ui": "playwright test --ui", "test:e2e:headed": "playwright test --headed", "test:e2e:debug": "playwright test --debug", "playwright:install": "playwright install --with-deps chromium"` | `npm run test:e2e` でヘルプ表示 |
| 11 | **実装** | `frontend/tests/e2e/gacha.spec.ts` | **ガチャ E2E テスト**: 1) かんたんモード選択 2) 「企画ガチャ」ボタンクリック 3) 3案表示待機 4) 案選択クリック 5) フォームに反映確認 6) ダイジェスト生成ボタン押下 7) 第1話草案表示確認 | `npm run test:e2e -- gacha.spec.ts` 成功 |
| 12 | **実装** | `frontend/tests/e2e/writing-streaming.spec.ts` | **ストリーミング執筆 E2E テスト**: 1) ガチャ完了状態から開始 2) 「リアルタイム速筆 (SSE)」クリック 3) ストリーミングコントロールバー表示確認 4) 一時停止/再開/中止ボタン動作確認 5) 完了後エディタに本文反映確認 | `npm run test:e2e -- writing-streaming.spec.ts` 成功 |
| 13 | **実装** | `frontend/tests/e2e/writing-standard.spec.ts` | **標準執筆 E2E テスト**: 1) ガチャ完了状態から開始 2) 「かんたん執筆開始」クリック 3) ポーリング完了待機 4) 出力・提案表示確認 5) エディタ同期確認 | `npm run test:e2e -- writing-standard.spec.ts` 成功 |
| 14 | **実装** | `frontend/tests/e2e/export-zip.spec.ts` | **ZIP エクスポート E2E テスト**: 1) 執筆完了状態から開始 2) book_id 入力 3) 「納品パッケージ (ZIP) ダウンロード」クリック 4) ダウンロード発火確認 (blob URL 作成・a タグ click) 5) ファイル名確認 | `npm run test:e2e -- export-zip.spec.ts` 成功 |
| 15 | **実装** | `frontend/tests/e2e/promote-studio.spec.ts` | **Studio 昇格 E2E テスト**: 1) 執筆完了状態から開始 2) 「Studioへ昇格」クリック 3) 成功メッセージ確認 4) URL 遷移確認 (`/studio/:bookId?token=xxx`) 5) StudioWorkspace 表示確認 | `npm run test:e2e -- promote-studio.spec.ts` 成功 |
| 16 | **実装** | `frontend/tests/e2e/full-flow.spec.ts` | **フルフロー E2E テスト (統合)**: ガチャ → ダイジェスト → ストリーミング執筆 → ZIPエクスポート の一連フローを 1 テストで実行 (所要時間考慮し CI では分割実行も可) | `npm run test:e2e -- full-flow.spec.ts` 成功 |
| 17 | **実装** | `frontend/tests/e2e/accessibility.spec.ts` | **アクセシビリティ E2E テスト**: `axe-playwright` 導入し、主要ページ (GeneratePanel, ExportPanel, StudioWorkspace) で自動 a11y チェック (色コントラスト、ARIA、キーボードナビ) | `npm run test:e2e -- accessibility.spec.ts` 成功 |
| 18 | **実装** | `frontend/tests/e2e/visual-regression.spec.ts` | **視覚回帰テスト (任意・将来)**: `@playwright/test` 標準機能でスクリーンショット比較。初回はベースライン生成のみ (`npx playwright test --update-snapshots`) | ベースライン画像生成確認 |
| 19 | **CI** | `.github/workflows/ci.yml` | **新規作成**: GitHub Actions ワークフロー。jobs: `lint-typecheck` → `unit-integration` (Vitest) → `e2e` (Playwright, matrix: chromium/firefox/webkit)。artifacts: coverage, test-results, playwright-report, traces | ワークフロー実行成功 (green) |
| 20 | **CI** | `.github/workflows/ci.yml` | `e2e` ジョブで `npm run playwright:install` 実行、並列実行最適化 (shard 対応)、失敗時 trace/screenshot/video アップロード | CI ログ確認 |
| 21 | **CI** | `scripts/verify_all.ps1` | PowerShell スクリプトにフロントエンド検証追加: `Push-Location frontend; npm ci; npm run lint; npm run typecheck; npm run test:ci; npm run playwright:install; npm run test:e2e; Pop-Location` | `./scripts/verify_all.ps1` 成功 |
| 22 | **品質** | `frontend/playwright.config.ts` | 閾値設定: `expect(page).toHaveNoViolations()` (axe), パフォーマンス予算 (FCP < 2s, TTI < 3s) を `test:ci` に統合または別ジョブで監視 | 閾値違反で CI 失敗確認 |
| 23 | **品質** | `frontend/tests/e2e/README.md` | **新規作成**: E2E テスト運用ガイド (実行コマンド、デバッグ方法、フィクスチャ追加ルール、セレクタ命名規則 `data-testid` 推奨、CI での並列/シャード設定) | ドキュメント存在確認 |
| 24 | **完了** | 全体 | **Definition of Done 確認**: 1) `npm run test:e2e` 全緑 2) CI (GitHub Actions) 全緑 3) `verify_all.ps1` パス 4) ガチャ→執筆→納品フロー手動確認不要化 5) 新規機能追加時 `tests/e2e/*.spec.ts` 作成が運用ルール化 | 全項目チェック完了 |

---

## 4. ディレクトリ構成 (導入後)

```
frontend/
├── src/
│   ├── components/
│   │   ├── GeneratePanel.tsx
│   │   ├── ExportPanel.tsx
│   │   ├── studio/StudioWorkspace.tsx
│   │   └── ...
│   ├── api/easyMode.ts
│   ├── hooks/useNovelGeneration.ts, useStreamingWriter.ts, useNovelExport.ts
│   └── ...
├── tests/
│   ├── setup.ts                    # Vitest グローバルセットアップ
│   ├── components/                 # Vitest コンポーネントテスト (既存)
│   ├── integration/                # Vitest 統合テスト (既存)
│   ├── api/                        # Vitest API テスト (既存)
│   └── e2e/                        # ★ Playwright E2E テスト (新規)
│       ├── fixtures/
│       │   └── test-data.ts        # 共通テストデータ
│       ├── utils/
│       │   ├── test-helpers.ts     # 共通ヘルパー
│       │   └── msw-handlers.ts     # E2E用 MSW ハンドラ
│       ├── global-setup.ts         # グローバルセットアップ
│       ├── global-teardown.ts      # グローバルティアダウン
│       ├── gacha.spec.ts           # ガチャフロー
│       ├── writing-streaming.spec.ts
│       ├── writing-standard.spec.ts
│       ├── export-zip.spec.ts
│       ├── promote-studio.spec.ts
│       ├── full-flow.spec.ts       # 統合フルフロー
│       ├── accessibility.spec.ts   # a11y チェック
│       └── visual-regression.spec.ts (任意)
├── playwright.config.ts            # ★ Playwright 設定
├── vite.config.ts                  # Vitest 設定 (既存)
├── tsconfig.json
├── package.json
└── .github/workflows/ci.yml        # ★ CI 定義
```

---

## 5. 主要ユーザーフロー E2E シナリオ詳細

### 5.1 ガチャ → ダイジェスト (企画生成フェーズ)

```typescript
// tests/e2e/gacha.spec.ts のシナリオ
test('ガチャからダイジェスト生成まで完了する', async ({ page }) => {
  // 1. かんたんモード選択
  await page.click('[data-testid="btn-mode-easy"]');
  
  // 2. 企画ガチャ実行
  await page.click('[data-testid="btn-open-gacha"]');
  await page.waitForSelector('[data-testid^="gacha-plan-"]', { timeout: 30000 });
  
  // 3. 3案表示確認
  const plans = page.locator('[data-testid^="gacha-plan-"]');
  await expect(plans).toHaveCount(3);
  
  // 4. 最初の案を採用
  await page.click('[data-testid^="btn-select-plan-"]:first-child');
  
  // 5. フォーム反映確認 (主人公名、冒頭テキスト等)
  await expect(page.locator('[data-testid="style-select"]')).toBeVisible();
  await expect(page.locator('textarea')).toContainText(/第1話/);
  
  // 6. ダイジェスト生成
  await page.click('button:has-text("ダイジェスト生成")');
  await page.waitForSelector('textarea:has-text("第1話")', { timeout: 60000 });
});
```

### 5.2 ストリーミング執筆 (リアルタイム速筆)

```typescript
// tests/e2e/writing-streaming.spec.ts
test('ストリーミング執筆がリアルタイムで完了する', async ({ page }) => {
  // 前提: ガチャ・ダイジェスト完了状態 (global-setup で事前準備)
  
  // 1. ストリーミングボタン押下
  await page.click('[data-testid="btn-stream-generate"]');
  
  // 2. ストリーミングコントロールバー表示
  await expect(page.locator('[data-testid="streaming-control-bar"]')).toBeVisible();
  await expect(page.locator('text=リアルタイム執筆中')).toBeVisible();
  
  // 3. 文字数増加確認 (非同期待機)
  await expect(page.locator('[data-testid="streaming-control-bar"]')).toContainText(/文字/);
  
  // 4. 一時停止/再開テスト
  await page.click('[data-testid="btn-pause-stream"]');
  await expect(page.locator('text=一時停止中')).toBeVisible();
  await page.click('[data-testid="btn-pause-stream"]'); // 再開
  
  // 5. 完了待機 (ストリーミングバー消滅)
  await expect(page.locator('[data-testid="streaming-control-bar"]')).toBeHidden({ timeout: 120000 });
  
  // 6. エディタに本文反映確認
  await expect(page.locator('[data-testid="editor-textarea"]')).toContainText(/./);
});
```

### 5.3 納品パッケージ (ZIP エクスポート)

```typescript
// tests/e2e/export-zip.spec.ts
test('ZIP パッケージがダウンロードされる', async ({ page }) => {
  // 前提: 執筆完了状態
  
  // 1. book_id 入力
  await page.fill('input[type="number"]', '42');
  
  // 2. ダウンロード発火待機
  const downloadPromise = page.waitForEvent('download');
  await page.click('[data-testid="btn-export-zip"]');
  const download = await downloadPromise;
  
  // 3. ファイル名確認
  expect(download.suggestedFilename()).toMatch(/export_\d+\.zip/);
  
  // 4. 成功トースト確認
  await expect(page.locator('text=納品パッケージをダウンロード')).toBeVisible();
});
```

### 5.4 Studio 昇格

```typescript
// tests/e2e/promote-studio.spec.ts
test('Studio モードへ昇格してリダイレクトする', async ({ page }) => {
  // 1. 昇格ボタン押下
  await page.click('[data-testid="btn-promote-studio"]');
  
  // 2. 成功メッセージ
  await expect(page.locator('text=上級者 Studio へ昇格')).toBeVisible();
  
  // 3. URL 変化確認
  await expect(page).toHaveURL(/\/studio\/\d+\?token=/);
  
  // 4. StudioWorkspace 表示
  await expect(page.locator('[data-testid="studio-workspace"]')).toBeVisible();
});
```

---

## 6. CI / CD 組み込み詳細

### 6.1 GitHub Actions (`.github/workflows/ci.yml`)

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint-typecheck:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck

  unit-integration:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    needs: lint-typecheck
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:ci
      - uses: codecov/codecov-action@v4
        with:
          directory: ./coverage
          flags: frontend-unit

  e2e:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    needs: lint-typecheck
    strategy:
      matrix:
        shard: [1, 2]  # 並列化 (必要に応じて増減)
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run playwright:install
      - run: npm run test:e2e -- --shard=${{ matrix.shard }}/2
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report-${{ matrix.shard }}
          path: |
            test-results/
            playwright-report/
            coverage/
          retention-days: 7

  e2e-merge-report:
    runs-on: ubuntu-latest
    needs: [e2e]
    if: always()
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: playwright-report-*
          path: all-reports
      - run: npx playwright merge-reports --reporter=html all-reports/playwright-report-*/
      - uses: actions/upload-artifact@v4
        with:
          name: playwright-report-merged
          path: playwright-report/
          retention-days: 7
```

### 6.2 `scripts/verify_all.ps1` 追記

```powershell
Write-Host "=== Frontend verification ===" -ForegroundColor Cyan
Push-Location frontend
npm ci
npm run lint
npm run typecheck
npm run test:ci
npm run playwright:install
npm run test:e2e
Pop-Location
```

---

## 7. 実装順序・依存関係 (クリティカルパス)

```
1─2─3─4─5─6─7─8─9─10   (環境・設定・共通基盤)
                    │
                    ├─11 (ガチャ)
                    ├─12 (ストリーミング執筆)
                    ├─13 (標準執筆)
                    ├─14 (ZIPエクスポート)
                    ├─15 (Studio昇格)
                    │
                    └─16 (フルフロー統合)
                    │
                    ├─17 (a11y)
                    ├─18 (視覚回帰・任意)
                    │
                    └─19─20─21 (CI/CD)
                    │
                    └─22─23─24 (品質・ドキュメント・完了確認)
```

- **並列化可能**: Step 11-15 は独立して実装可能 (共通基盤 Step 1-10 完了後)
- **ブロッカー**: Step 1-10 (Playwright 環境構築) 完了まで 11-18 着手不可
- **CI 統合**: Step 19-21 は Step 11-16 (最低限ガチャ+執筆+エクスポート) 完了後推奨

---

## 8. リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| Playwright ブラウザインストール失敗 (CI) | 高 | `playwright install --with-deps chromium` 明示、キャッシュ活用 |
| ストリーミング (SSE) テストのフレーク | 高 | `waitForEvent('download')` 等の確実な待機、タイムアウト余裕 (120s) |
| MSW ハンドラの E2E/Vitest 共有で競合 | 中 | `tests/e2e/utils/msw-handlers.ts` として分離、必要なら共通化 |
| テスト実行時間超過 (CI タイムアウト) | 中 | `shard` 分割、並列度調整 (`workers: 1` on CI)、重いテストは分離 |
| `data-testid` 不足でセレクタ脆弱 | 低 | 既存コンポーネントに `data-testid` 追加をルール化 (Step 23 で文書化) |
| 視覚回帰テストの誤検知 | 低 | 最初はベースライン生成のみ、閾値調整後から本格運用 |

---

## 9. 完了基準 (Definition of Done)

1. ✅ `npm run test:e2e` が **ローカル / CI 共に全緑** (Chromium/Firefox/WebKit)
2. ✅ **ガチャ → 執筆 (ストリーミング/標準) → 納品 (ZIP/昇格)** の主要フローが自動化済み
3. ✅ GitHub Actions `ci.yml` が **main/develop ブランチで成功**
4. ✅ `scripts/verify_all.ps1` 実行で **フロントエンド検証 (lint/typecheck/unit/e2e) 全パス**
5. ✅ テスト実行時間 **CI で 10 分以内** (shard 含む)
6. ✅ `tests/e2e/README.md` に運用ルール文書化済み
7. ✅ 新規画面/機能追加時に **同等の E2E テスト作成** がチーム規約化

---

## 10. 次アクション (即実行可能)

1. **Step 1 実行**: `cd frontend && npm i -D @playwright/test`
2. **Step 2 実行**: `playwright.config.ts` 作成 (テンプレートからコピペ調整)
3. **Step 3-6 実行**: ディレクトリ・フィクスチャ・ヘルパー・MSWハンドラ作成
4. **Step 10 実行**: `package.json` scripts 追加 → `npm run playwright:install` でブラウザ導入
5. **Step 11 実行**: `gacha.spec.ts` から着手 (最も独立性高くデバッグ容易)

---

## 付録: セレクタ命名規則 (推奨)

| 要素種別 | data-testid パターン | 例 |
|---------|-------------------|-----|
| ボタン | `btn-{action}` | `btn-open-gacha`, `btn-stream-generate` |
| 入力欄 | `input-{field}` | `input-book-id`, `input-character-name` |
| セレクト | `select-{field}` | `select-genre`, `select-style` |
| モーダル | `{feature}-modal` | `gacha-modal`, `style-distiller-modal` |
| リスト項目 | `{feature}-item-{id}` | `gacha-plan-royal`, `gacha-plan-curveball` |
| 状態表示 | `status-{state}` | `status-streaming`, `status-loading` |
| パネル/セクション | `{feature}-panel` | `generate-panel`, `export-panel` |

> 既存コードに `data-testid` が不足している箇所は、E2E テスト実装時に **同時に追加** すること (別 PR 化不要)