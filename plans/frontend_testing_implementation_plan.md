# フロントエンド自動テスト導入 詳細実装計画書

## 1. 概要・目的

| 項目 | 内容 |
|------|------|
| 対象リポジトリ | `frontend/` (Vite + React 18 + TypeScript) |
| 導入ツール | Vitest, React Testing Library (RTL), @testing-library/user-event, axe-core (a11y), @vitest/coverage-v8 |
| テスト種別 | 単体テスト (hooks / utils / API client), コンポーネントテスト (UI), 統合テスト (API モック), E2E 的シナリオ (MSW), アクセシビリティテスト |
| 目標カバレッジ | 行・分岐・関数 80 % 以上 |
| CI 組み込み | `npm run test:ci` (GitHub Actions / 既存 `verify_all.ps1` へ追加) |

---

## 2. 現状ギャップ分析

| 観点 | 現状 | 必要対応 |
|------|------|----------|
| テストランナー | なし | Vitest 導入 |
| テストユーティリティ | なし | RTL, user-event, jest-dom, msw, axe-core 導入 |
| テストファイル | 0 件 | `src/**/*.test.tsx`, `src/**/*.spec.ts` 配置 |
| コンポーネント分割 | `App.tsx` モノリス | Phase: `GeneratePanel`, `ExportPanel`, `ui/*` へ分割 (既存計画 Step 35-36 と連携) |
| API クライアント | `App.tsx` 内に inline fetch | `src/api/easyMode.ts` へ分離 (既存計画 Step 105-126 と連携) |
| 型定義 | 共有なし | `src/types/easyMode.ts` 新規作成 (既存計画 Step 85-103 と連携) |
| lint / typecheck | 未設定 | ESLint (flat config) + `npm run lint`, `npm run typecheck` 追加 |
| CI スクリプト | `verify_all.ps1` のみ (Python) | `frontend/` 用 `test:ci`, `lint`, `typecheck` 追加 |

---

## 3. 導入手順 (全 18 ステップ)

> 番号は既存 72 ステップ計画の **Phase 3 (Step 40-42) / Phase 5 (Step 54-60)** と連動させる。

| # | ファイル / 対象 | 作業内容 | 既存計画対応 |
|---|----------------|----------|--------------|
| 1 | `frontend/package.json` | **devDependencies 追加**:<br>`vitest@2`, `@vitest/coverage-v8`, `@testing-library/react@16`, `@testing-library/user-event@14`, `@testing-library/jest-dom@6`, `msw@2`, `axe-core@4`, `vitest-axe@0.1`, `eslint@9`, `eslint-plugin-react-hooks@5`, `eslint-plugin-jsx-a11y@6`, `@typescript-eslint/eslint-plugin@8`, `@typescript-eslint/parser@8`, `eslint-plugin-testing-library@6` | Step 40 `scripts` 追加と同期 |
| 2 | `frontend/vite.config.ts` | `defineConfig({ test: { environment: 'jsdom', globals: true, setupFiles: ['./tests/setup.ts'], coverage: { provider: 'v8', reporter: ['text', 'json', 'html'], thresholds: { lines: 80, branches: 80, functions: 80, statements: 80 } } } })` | Step 39 `vite.config.ts` 拡張 |
| 3 | `frontend/tests/setup.ts` | **新規作成**:<br>`import '@testing-library/jest-dom'; import { cleanup } from '@testing-library/react'; import { afterEach, vi } from 'vitest'; afterEach(() => { cleanup(); vi.clearAllMocks(); });` | - |
| 4 | `frontend/tsconfig.json` | `"include": ["src", "tests"]`, `"types": ["vitest/globals", "@testing-library/jest-dom", "node"]` 追加 | Step 41 `tsconfig.json` 連携 |
| 5 | `frontend/tsconfig.node.json` | **新規作成** (Vite 設定用): `compilerOptions: { composite: true, module: 'ESNext', moduleResolution: 'Bundler', allowSyntheticDefaultImports: true, strict: true, skipLibCheck: true, esModuleInterop: true, resolveJsonModule: true, isolatedModules: true, noEmit: true, lib: ['ES2022'], types: ['node'] }, include: ['vite.config.ts', 'vitest.config.ts']` | - |
| 6 | `frontend/.eslintrc.cjs` | **新規作成** (flat config): `module.exports = [ { files: ['**/*.{ts,tsx}'], languageOptions: { parser: require('@typescript-eslint/parser'), parserOptions: { ecmaVersion: 2022, sourceType: 'module', ecmaFeatures: { jsx: true }, project: './tsconfig.json' }, settings: { react: { version: '18.2' } }, plugins: { react: require('eslint-plugin-react'), 'react-hooks': require('eslint-plugin-react-hooks'), 'jsx-a11y': require('eslint-plugin-jsx-a11y'), '@typescript-eslint': require('@typescript-eslint/eslint-plugin'), testing-library' ), testing-library: require('eslint-plugin-testing-library') }, rules: { ...推奨セット } } ]` | Step 40 lint 追加 |
| 7 | `frontend/src/types/easyMode.ts` | **新規作成** (既存計画 Step 85-103 準拠) | Step 85-103 |
| 8 | `frontend/src/api/easyMode.ts` | **新規作成** (既存計画 Step 105-126 準拠、MSW ハンドラ用 `export const handlers = [...]` も同梱) | Step 105-126 |
| 9 | `frontend/src/components/GeneratePanel.tsx` | **新規作成** (App.tsx から抽出、単体テスト容易化) | Step 35-36 |
| 10 | `frontend/src/components/ExportPanel.tsx` | **新規作成** (App.tsx から抽出) | Step 43-44 |
| 11 | `frontend/src/components/ui/*` | 必要に応じ `Button`, `Input`, `Select`, `Textarea`, `Chip`, `Card` 等を分離 (Storybook 非依存) | - |
| 12 | `frontend/tests/api/easyMode.test.ts` | **API クライアント単体テスト** (MSW で `/generate` `/export` モック) | - |
| 13 | `frontend/tests/hooks/*.test.ts` | カスタムフック (`useGeneration`, `useExport` 等) があれば単体テスト | - |
| 14 | `frontend/tests/components/GeneratePanel.test.tsx` | **コンポーネントテスト**: 入力→生成ボタン→ローディング→成功/失敗表示、a11y (axe) | - |
| 15 | `frontend/tests/components/ExportPanel.test.tsx` | **コンポーネントテスト**: book_id 入力→エクスポート→ダウンロードトリガー、a11y | - |
| 16 | `frontend/tests/integration/easyModeFlow.test.tsx` | **統合テスト**: GeneratePanel → 成功 → ExportPanel 連携 (MSW 全モック) | Step 57 `test_generate_flow.py` 対応 |
| 17 | `frontend/package.json` | **scripts 追加**:<br>`"test": "vitest", "test:ci": "vitest run --coverage", "lint": "eslint . --ext ts,tsx --max-warnings 0", "typecheck": "tsc --noEmit"` | Step 40, 42 |
| 18 | `scripts/verify_all.ps1` | **フロントエンド検証追加**: `Push-Location frontend; npm ci; npm run lint; npm run typecheck; npm run test:ci; Pop-Location` | Step 42, 49, 60 |

---

## 4. ディレクトリ構成 (導入後)

```
frontend/
├── src/
│   ├── api/
│   │   └── easyMode.ts            # API クライアント + MSW handlers
│   ├── components/
│   │   ├── GeneratePanel.tsx
│   │   ├── ExportPanel.tsx
│   │   └── ui/                    # Button, Input, Select, ...
│   ├── hooks/                     # useGeneration, useExport 等
│   ├── types/
│   │   └── easyMode.ts
│   ├── App.tsx                    # 2 パネルを配置するのみ
│   └── main.tsx
├── tests/
│   ├── setup.ts                   # Vitest グローバルセットアップ
│   ├── api/
│   │   └── easyMode.test.ts
│   ├── hooks/
│   ├── components/
│   │   ├── GeneratePanel.test.tsx
│   │   └── ExportPanel.test.tsx
│   └── integration/
│       └── easyModeFlow.test.tsx
├── vite.config.ts                 # test 設定含む
├── tsconfig.json
├── tsconfig.node.json
├── .eslintrc.cjs
└── package.json
```

---

## 5. テストケース設計 (抜粋)

### 5.1 API クライアント (`easyMode.test.ts`)

| ID | ケース | 入力 (MSW) | 期待 |
|----|--------|------------|------|
| API-01 | `generateContent` 成功 | 200 + `{ output: "…", suggestions: ["a"] }` | `GenerationResponse` 解決 |
| API-02 | `generateContent` 失敗 | 500 + `"Internal error"` | `Error` throw / message 含む |
| API-03 | `exportPackage` 成功 | 200 + blob + `Content-Disposition` | `{ zipBlob, filename }` 解決 |
| API-04 | `exportPackage` ヘッダ不在 | 200 + blob (no header) | デフォルト `export_${id}.zip` |
| API-05 | ネットワークエラー | `fetch` reject | `TypeError` 捕捉・再throw |

### 5.2 GeneratePanel (`GeneratePanel.test.tsx`)

| ID | ケース | 操作 (user-event) | 期待 (RTL + jest-dom) |
|----|--------|-------------------|------------------------|
| GP-01 | 初期レンダリング | - | フォーム要素・ボタンが表示、ボタン disabled=false |
| GP-02 | 入力変更反映 | `type(input), selectOptions(select)` | state 更新、ボタン enabled |
| GP-03 | 送信中 loading | `click(button)` → MSW delay | ボタン disabled=true, "執筆中…" 表示 |
| GP-04 | 成功時 output 表示 | MSW 200 返却後 | `output-area` に本文、chips に suggestions |
| GP-05 | 失敗時エラー表示 | MSW 500 返却後 | メッセージ領域に "❌ エラー: …" |
| GP-06 | アクセシビリティ | `axe` 自動実行 | violations 0 (色コントラスト, label 等) |

### 5.3 ExportPanel (`ExportPanel.test.tsx`)

| ID | ケース | 操作 | 期待 |
|----|--------|------|------|
| EP-01 | 成功ダウンロード | `click(exportBtn)` → MSW 200 blob | `URL.createObjectURL` 呼出し、`<a download>` click 発火 |
| EP-02 | 失敗エラー表示 | MSW 500 | メッセージ "❌ ダウンロードエラー: …" |
| EP-03 | loading 状態 | 送信中 | ボタン disabled, "パッケージ生成中…" |

### 5.4 統合フロー (`easyModeFlow.test.tsx`)

| ID | シナリオ | 手順 | 期待 |
|----|----------|------|------|
| IF-01 | 生成→エクスポート成功 | 1. GeneratePanel で生成 2. ExportPanel で同 book_id export | 両パネル連携正常、ZIP ダウンロード発火 |
| IF-02 | 生成失敗→リトライ | 1. 生成 500 2. エラー表示 3. 再度生成 200 | エラー消失、output 表示 |

---

## 6. CI / CD 組み込み

### 6.1 GitHub Actions (`.github/workflows/ci.yml` 追記)

```yaml
jobs:
  frontend-test:
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
      - run: npm run test:ci
      - uses: codecov/codecov-action@v4
        with:
          directory: ./coverage
          flags: frontend
```

### 6.2 `scripts/verify_all.ps1` 追記箇所 (抜粋)

```powershell
Write-Host "=== Frontend verification ===" -ForegroundColor Cyan
Push-Location frontend
npm ci
npm run lint
npm run typecheck
npm run test:ci
Pop-Location
```

---

## 7. 実装順序・依存関係 (クリティカルパス)

```
1─2─3─4─5─6   (環境・設定)
      │
      ├─7─8   (型・APIクライアント) ── 12 (APIテスト)
      │
      ├─9─10─11 (コンポーネント分割) ── 14─15 (コンポーネントテスト)
      │
      └──────────────────────────────── 16 (統合テスト)
                              │
                              17 (scripts)
                              │
                              18 (verify_all.ps1 / CI)
```

- **並列化可能**: 7-8 と 9-11 は独立して進行可能。
- **ブロッカー**: コンポーネント分割 (9-11) 完了まで 14-15 は着手不可。

---

## 8. リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| `App.tsx` モノリス分割でリグレッション | 高 | まず **スナップショットテスト** (`toMatchSnapshot`) で現状固定 → 分割 → スナップショット更新 |
| MSW v2 設定 (ESM + Vite) でハマる | 中 | `msw` 公式 `vite` 例を参考、`setup.ts` で `server.listen({ onUnhandledRequest: 'bypass' })` |
| `axe-core` が jsdom で一部ルール誤検知 | 低 | `vitest-axe` の `configureAxe({ rules: { 'color-contrast': { enabled: false } } })` で既知誤検知を抑制 |
| カバレッジ閾値 80% 未達で CI 失敗 | 中 | 最初は `thresholds: { lines: 50, branches: 50, functions: 50, statements: 50 }` で開始、段階的に引き上げ |

---

## 9. 完了基準 (Definition of Done)

1. `npm run test:ci` が **ローカル / CI 共に緑**。
2. カバレッジ **lines / branches / functions / statements ≥ 80%**。
3. `npm run lint` **警告 0 件** (`--max-warnings 0`)。
4. `npm run typecheck` **エラー 0 件**。
5. `scripts/verify_all.ps1` 実行で **フロントエンド検証パス**。
6. GitHub Actions `frontend-test` ジョブが **main ブランチで成功**。
7. 新規コンポーネント追加時に **同ディレクトリへ `*.test.tsx` 作成** が運用ルール化されている。

---

## 10. 次アクション (即実行可能)

1. `frontend/package.json` へ devDependencies 追加 (`npm i -D ...`)  
2. `vite.config.ts` に `test` ブロック追加  
3. `tests/setup.ts` 作成  
4. `tsconfig.json` / `tsconfig.node.json` 修正・追加  
5. `.eslintrc.cjs` 作成  
6. `npm run test` で **テスト実行環境だけ** 先に確認 (テストファイル 0 件でパスすること確認)

以降、コンポーネント分割 (Step 9-11) と並行して API / コンポーネント / 統合テストを充実させる。