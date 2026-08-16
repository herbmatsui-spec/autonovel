# E2E テスト自動化戦略 - Playwright 採用

## 概要
フロントエンド (Streamlit/React) を含むエンドツーエンドテストを Playwright で自動化し、CI/CD パイプラインに組み込む。

## なぜ Playwright か

| 観点 | Playwright | Cypress | Selenium |
|------|-----------|---------|----------|
| **クロスブラウザ** | ✅ Chromium/Firefox/WebKit | ❌ Chromium のみ | ✅ 全対応 |
| **並列実行** | ✅ ネイティブサポート | ⚠️ 有料機能 | ⚠️ Grid 必要 |
| **自動待機** | ✅ スマート待機 | ✅ 自動待機 | ❌ 明示的待機必要 |
| **ネットワーク制御** | ✅ インターセプト・モック | ✅ インターセプト | ⚠️ 限定的 |
| **モバイルエミュレ** | ✅ デバイスエミュレ | ❌ なし | ✅ 可能 |
| **TypeScript サポート** | ✅ ファーストクラス | ✅ 良好 | ✅ 可能 |
| **CI/CD 統合** | ✅ GitHub Actions 対応 | ✅ 対応 | ⚠️ 設定複雑 |
| **学習コスト** | 低 | 低 | 高 |
| **コミュニティ** | 急成長中 | 成熟 | 成熟 |

**結論**: Playwright を採用。モダンで高速、CI/CD 統合が容易、モバイルテストも将来的に可能。

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    Playwright Test Runner                    │
├─────────────────────────────────────────────────────────────┤
│  Test Suite (tests/e2e/)                                     │
│  ├── spec/                                                    │
│  │   ├── auth.spec.ts           # 認証フロー                 │
│  │   ├── easy_mode.spec.ts      # かんたんモード生成         │
│  │   ├── advanced_mode.spec.ts  # 上級者モード               │
│  │   ├── bible_sync.spec.ts     # Bible 同期                 │
│  │   └── asset_export.spec.ts   # アセットエクスポート       │
│  ├── fixtures/                                                 │
│  │   ├── test-data.ts           # テストデータ生成           │
│  │   └── api-mocks.ts           # API モック                 │
│  ├── pages/                                                    │
│  │   ├── LoginPage.ts           # POM: ログイン              │
│  │   ├── DashboardPage.ts       # POM: ダッシュボード        │
│  │   ├── EasyModePage.ts        # POM: かんたんモード        │
│  │   └── AdvancedModePage.ts    # POM: 上級者モード          │
│  └── utils/                                                    │
│      ├── api-helpers.ts         # API ヘルパー               │
│      └── db-helpers.ts          # DB ヘルパー                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  Test Environment │
                    │  ┌─────────────┐  │
                    │  │ Frontend      │  │
                    │  │ (Streamlit/   │  │
                    │  │  React)       │  │
                    │  └─────────────┘  │
                    │  ┌─────────────┐  │
                    │  │ Backend API   │  │
                    │  │ (FastAPI)     │  │
                    │  └─────────────┘  │
                    │  ┌─────────────┐  │
                    │  │ PostgreSQL    │  │
                    │  └─────────────┘  │
                    │  ┌─────────────┐  │
                    │  │ Redis         │  │
                    │  └─────────────┘  │
                    │  ┌─────────────┐  │
                    │  │ ChromaDB      │  │
                    │  └─────────────┘  │
                    └───────────────────┘
```

## ページオブジェクトモデル (POM)

### 基底クラス
```typescript
// tests/e2e/pages/BasePage.ts
export abstract class BasePage {
  constructor(protected page: Page) {}
  
  async goto(path: string) {
    await this.page.goto(`${process.env.BASE_URL}${path}`);
    await this.page.waitForLoadState('networkidle');
  }
  
  async waitForSelector(selector: string) {
    await this.page.waitForSelector(selector, { state: 'visible' });
  }
  
  async clickAndWait(selector: string) {
    await this.page.click(selector);
    await this.page.waitForLoadState('networkidle');
  }
}
```

### 具象ページ
```typescript
// tests/e2e/pages/EasyModePage.ts
export class EasyModePage extends BasePage {
  private readonly genreSelect = '[data-testid="genre-select"]';
  private readonly generateButton = '[data-testid="generate-btn"]';
  private readonly progressBar = '[data-testid="progress-bar"]';
  private readonly resultContainer = '[data-testid="result-container"]';
  
  async selectGenre(genre: string) {
    await this.page.selectOption(this.genreSelect, genre);
  }
  
  async startGeneration() {
    await this.clickAndWait(this.generateButton);
  }
  
  async waitForCompletion(timeout = 300000) {
    await this.page.waitForSelector(
      `${this.resultContainer}:has-text("完了")`,
      { timeout }
    );
  }
  
  async getResult() {
    return await this.page.textContent(this.resultContainer);
  }
}
```

## テストシナリオ

### 1. 認証フロー
```typescript
// tests/e2e/spec/auth.spec.ts
test.describe('認証フロー', () => {
  test('ログイン→ダッシュボードアクセス', async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto('/login');
    await loginPage.login('test@example.com', 'password');
    await expect(page).toHaveURL('/dashboard');
  });
  
  test('APIキー認証でAPIアクセス', async ({ request }) => {
    const response = await request.get('/api/books', {
      headers: { 'X-API-Key': process.env.TEST_API_KEY }
    });
    expect(response.status()).toBe(200);
  });
});
```

### 2. かんたんモード生成
```typescript
// tests/e2e/spec/easy_mode.spec.ts
test.describe('かんたんモード生成', () => {
  test('ジャンル選択→生成完了→結果確認', async ({ page }) => {
    const easyPage = new EasyModePage(page);
    await easyPage.goto('/easy-mode');
    
    await easyPage.selectGenre('zarma');
    await easyPage.startGeneration();
    
    // 進捗バー確認
    await expect(page.locator('[data-testid="progress-bar"]')).toBeVisible();
    
    // 完了待ち (最大5分)
    await easyPage.waitForCompletion();
    
    // 結果確認
    const result = await easyPage.getResult();
    expect(result).toContain('タイトル');
    expect(result).toContain('あらすじ');
    expect(result).toContain('エピソード');
  });
  
  test('進捗コールバックでリアルタイム更新', async ({ page }) => {
    // WebSocket 経由で進捗受信確認
    const wsMessages: string[] = [];
    page.on('websocket', ws => {
      ws.on('framereceived', frame => wsMessages.push(frame.payload));
    });
    
    const easyPage = new EasyModePage(page);
    await easyPage.goto('/easy-mode');
    await easyPage.selectGenre('zarma');
    await easyPage.startGeneration();
    
    // 進捗メッセージ受信確認
    await expect.poll(() => wsMessages.filter(m => m.includes('progress')).length).toBeGreaterThan(0);
  });
});
```

### 3. Bible 同期
```typescript
// tests/e2e/spec/bible_sync.spec.ts
test.describe('Bible 同期', () => {
  test('仮設定提案→承認→同期実行', async ({ page, request }) => {
    // 1. 仮設定作成
    const settingResp = await request.post('/api/bible/settings', {
      data: { book_id: 1, type: 'character', content: { name: 'テスト' } }
    });
    expect(settingResp.status()).toBe(201);
    const settingId = (await settingResp.json()).id;
    
    // 2. 承認
    const approveResp = await request.post(`/api/bible/settings/${settingId}/resolve`, {
      data: { status: 'approved' }
    });
    expect(approveResp.status()).toBe(200);
    
    // 3. 同期実行
    const syncResp = await request.post('/api/bible/sync', { data: { book_id: 1 } });
    expect(syncResp.status()).toBe(200);
    const syncResult = await syncResp.json();
    expect(syncResult.changes).toBeGreaterThan(0);
  });
});
```

## CI/CD 統合

### GitHub Actions ワークフロー
```yaml
# .github/workflows/e2e.yml
name: E2E Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # 毎日午前2時

jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_autonovel
        ports: [5432:5432]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7-alpine
        ports: [6379:6379]
      
      chromadb:
        image: chromadb/chroma:0.4.22
        ports: [8000:8000]
        env:
          CHROMA_SERVER_HOST: 0.0.0.0
          CHROMA_SERVER_HTTP_PORT: 8000

    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
        working-directory: ./frontend  # または ./tests/e2e
      
      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium
        working-directory: ./tests/e2e
      
      - name: Start backend
        run: |
          cd backend
          pip install -r requirements.txt
          uvicorn src.backend.server:app --host 0.0.0.0 --port 8200 &
          sleep 10  # 起動待ち
      
      - name: Run E2E tests
        run: npx playwright test
        working-directory: ./tests/e2e
        env:
          BASE_URL: http://localhost:8501  # Streamlit またはフロントエンド
          API_BASE_URL: http://localhost:8200
          TEST_API_KEY: ${{ secrets.TEST_API_KEY }}
      
      - name: Upload test artifacts
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: tests/e2e/playwright-report/
          retention-days: 7
      
      - name: Upload screenshots/videos
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-screenshots
          path: tests/e2e/test-results/
          retention-days: 7
```

### Playwright 設定
```typescript
// tests/e2e/playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './spec',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/results.xml' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:8501',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    // モバイル
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
    { name: 'mobile-safari', use: { ...devices['iPhone 12'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:8501',
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
```

## テストデータ管理

```typescript
// tests/e2e/fixtures/test-data.ts
export const testUsers = {
  admin: { email: 'admin@test.com', password: 'admin123', role: 'admin' },
  author: { email: 'author@test.com', password: 'author123', role: 'author' },
  viewer: { email: 'viewer@test.com', password: 'viewer123', role: 'viewer' },
};

export const testGenres = ['zarma', 'aku_reijo', 'cheat_tensei', 'slow_life'];

export async function createTestBook(api: APIRequestContext, genre = 'zarma') {
  const response = await api.post('/api/books', {
    data: { title: `E2Eテスト_${Date.now()}`, genre, target_episodes: 2 }
  });
  return response.json();
}

export async function cleanupTestData(api: APIRequestContext) {
  // テストデータクリーンアップ
  const books = await api.get('/api/books').then(r => r.json());
  for (const book of books.filter(b => b.title.startsWith('E2Eテスト_'))) {
    await api.delete(`/api/books/${book.id}`);
  }
}
```

## 実行コマンド

```bash
# インストール
cd tests/e2e
npm ci
npx playwright install --with-deps chromium

# ローカル実行
npx playwright test                    # 全テスト
npx playwright test --project=chromium  # Chromiumのみ
npx playwright test --headed           # ヘッドモード
npx playwright test --debug            # デバッグモード
npx playwright test --ui               # UI モード

# レポート
npx playwright show-report             # HTMLレポート表示
npx playwright show-trace trace.zip    # トレース表示
```

## 導入優先順位

| 優先度 | テストケース | 理由 |
|--------|-------------|------|
| **P0** | かんたんモード生成 (zarma) | コア機能 |
| **P0** | API キー認証 | セキュリティ必須 |
| **P1** | Bible 同期フロー | 上級者モード核心 |
| **P1** | アセットエクスポート (EPUB/PDF) | 収益機能 |
| **P2** | 上級者モード分岐 | 機能拡張 |
| **P2** | Bible 同期フロー | 運用必須 |
| **P3** | モバイル表示確認 | 将来対応 |

## 導入チェックリスト

- [ ] `npm init` で `tests/e2e` 初期化
- [ ] `playwright.config.ts` 作成
- [ ] `pages/` に POM クラス作成
- [ ] `spec/` にテストケース作成
- [ ] `.github/workflows/e2e.yml` 作成
- [ ] `package.json` にスクリプト追加
- [ ] CI で実行確認
- [ ] アーティファクトアップロード確認
- [ ] 並列実行最適化 (workers 調整)
- [ ] フレークテスト対策 (retry 設定)