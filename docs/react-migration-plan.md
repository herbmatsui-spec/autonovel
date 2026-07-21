# React移行 48ステップ実装計画

## 前提知識

### バックエンドAPIエンドポイント一覧

| Method | Path | React対応状況 | Streamlit対応状況 |
|--------|------|---------------|-------------------|
| GET | `/api/books/` | ✅ あり | ✅ あり |
| GET | `/api/books/{id}` | ✅ あり | ✅ あり |
| DELETE | `/api/books/{id}` | ✅ あり | ✅ あり |
| GET | `/api/plots/{book_id}` | ✅ あり | ✅ あり |
| POST | `/api/plots/plan_generation` | ✅ あり | ✅ あり |
| POST | `/api/plots/expand` | ✅ あり | ✅ あり |
| POST | `/api/plots/expand_candidates` | ❌ なし | ❌ なし |
| POST | `/api/plots/rebuild` | ✅ あり | ✅ あり |
| POST | `/api/plots/audit` | ✅ あり | ✅ あり |
| GET | `/api/episodes/chapters/{book_id}` | ✅ あり | ✅ あり |
| POST | `/api/episodes/generate` | ✅ あり | ✅ あり |
| POST | `/api/episodes/generate_candidates` | ❌ なし | ❌ なし |
| POST | `/api/episodes/retry_failed` | ✅ あり | ✅ あり |
| POST | `/api/episodes/chapters/import` | ✅ あり | ✅ あり |
| GET | `/api/tasks/{id}/status` | ✅ あり | ✅ あり |
| GET | `/api/tasks/{id}/stream` (SSE) | ✅ あり | ❌ REST polling |
| POST | `/api/tasks/{id}/stop` | ✅ あり | ✅ あり |
| GET | `/api/patches/{book_id}/pending` | ✅ あり | ✅ あり |
| POST | `/api/patches/{id}/approve` | ✅ あり | ✅ あり |
| POST | `/api/patches/{id}/reject` | ✅ あり | ✅ あり |
| POST | `/api/patches/{id}/edit` | ✅ あり | ✅ あり |
| GET | `/api/issues/books/{book_id}` | ✅ あり | ✅ あり |
| POST | `/api/issues/{id}/resolve` | ✅ あり | ✅ あり |
| POST | `/api/marketing/generate` | ✅ あり | ✅ あり |
| GET | `/api/marketing/export_package/{book_id}` | ✅ あり | ✅ あり |
| GET | `/api/bibles/{book_id}` | ✅ あり | ✅ あり |
| GET | `/api/optimization_history/{book_id}` | ✅ あり | ✅ あり |
| GET | `/api/narrative_metrics/{book_id}/{branch_id}` | ✅ あり | ✅ あり |
| GET | `/api/prompt_versions/{book_id}` | ✅ あり | ✅ あり |
| POST | `/api/prompt_versions/{book_id}/rollback` | ✅ あり | ✅ あり |
| GET | `/health` | ❌ なし | ✅ あり |
| POST | `/api/refine_erotic` | ❌ なし | ❌ なし |
| POST | `/api/easy_mode/generate` | ✅ あり | ✅ あり |
| POST | `/api/critique/optimize` | ✅ あり | ✅ あり |
| POST | `/api/commercial/run` | ❌ なし | ❌ なし |

---

## フェーズ0: 環境整備・基盤完成（ステップ1-10）

### ステップ1: Vite環境変数の正式設定
**ファイル:** `frontend/src/vite-env.d.ts` (新規作成)

```typescript
/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_API_URL: string
}
interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

**作業内容:**
- `frontend/src/vite-env.d.ts` を作成して `VITE_API_URL` の型を宣言
- `frontend/.env` を作成し `VITE_API_URL=http://localhost:8200/api` を設定
- `frontend/.env.production` を作成し `VITE_API_URL=/api` を設定（プロダクション用）

**検証:** `npm run build` が型エラーなしで完了すること

---

### ステップ2: APIクライアントのURL修正
**ファイル:** `frontend/src/api.ts:45`

**作業内容:**
```typescript
// Before
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
// After
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8200/api';
```

**検証:** バックエンド接続テスト（curl -s http://localhost:8200/health が `{"status":"ok",...}` を返すこと）

---

### ステップ3: Vite開発プロキシ設定
**ファイル:** `frontend/vite.config.ts`

**作業内容:**
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8200',
        changeOrigin: true,
        rewrite: (path) => path, // パスをそのまま転送
      },
      '/health': {
        target: 'http://localhost:8200',
        changeOrigin: true,
      },
    },
  },
})
```

**検証:** `npm run dev` 起動後、`fetch('/api/books')` が正常応答を返すこと

---

### ステップ4: 不要ファイルの削除
**作業内容:**
- `frontend/src/components/dialogs/CreateNovelModal.tsx` を削除（未使用）
- `frontend/src/App.css` を削除（未使用）
- `frontend/src/components/layout.css` を削除（未インポート）

**検証:** `npm run build` が成功すること

---

### ステップ5: TypeScript設定の厳格化
**ファイル:** `frontend/tsconfig.json`

**作業内容:**
- `strict: true` を有効化
- `noUnusedLocals: true`, `noUnusedParameters: true` を有効化
- 発見された未使用変数を全て削除

**検証:** `npm run build` が成功すること（型和ifera警告は許容）

---

### ステップ6: ESLint/Prettier設定確認
**ファイル:** `frontend/eslint.config.js`, `frontend/package.json`

**作業内容:**
- ESLint ルールの確認と適用
- Prettier 設定の確認（`.prettierrc` が無ければ作成）

**検証:** `npm run lint` がエラーなしで完了すること

---

### ステップ7: 依存関係確認とロック
**ファイル:** `frontend/package.json`, `frontend/package-lock.json`

**作業内容:**
- `npm install` が最新バージョンを反映していることを確認
- `react-router-dom` が不使用のため削除：`npm uninstall react-router-dom`（`package.json`からも削除されていることを確認）

**検証:** `npm run build` が成功すること

---

### ステップ8: 開発スクリプト動作確認
**ファイル:** `frontend/package.json`

**作業内容:**
- `npm run dev` がport 5173で起動することを確認
- `npm run build` が `frontend/dist/` にプロダクションビルドを生成することを確認
- `npm run preview` がビルド結果をプレビューできること確認

**検証:** 全スクリプトがエラーなく動作すること

---

### ステップ9: Docker構成の予備調査
**ファイル:** `frontend/Dockerfile`, `docker-compose.yml`

**作業内容:**
- 現在の `frontend/Dockerfile` を調査（node:20-alpine, port 5173）
- バックエンドの `/health` エンドポイントの存在確認
- Reactが producción 時に必要とする環境変数 (`VITE_API_URL`) の特定

**検証:** バックエンドAPI仕様書の作成

---

### ステップ10: .gitignore確認
**ファイル:** `frontend/.gitignore`

**作業内容:**
- `node_modules/`, `dist/`, `.env` が無視設定されていることを確認
- `.env.production` の追跡は任意（リポジトリ次第）

**検証:** `git status` で `node_modules/` が表示されないこと

---

## フェーズ1: コアバグ修正と状態管理整顿（ステップ11-20）

### ステップ11: BooksTabのany型を修正
**ファイル:** `frontend/src/components/tabs/BooksTab.tsx`

**作業内容:**
```typescript
// Before
selectedBook: any

// After - 型を正確に定義
import type { Book } from '@/types/api';
interface BooksTabProps {
  selectedBook: Book | null;
  setSelectedBook: (book: Book | null) => void;
  setShowCreateModal: (open: boolean) => void;
}
```

**検証:** `npm run build` が型エラーなしで成功すること

---

### ステップ12: selectedBook重複管理の統一
**ファイル:** `frontend/src/hooks/useBooks.ts`, `frontend/src/store/useBookStore.ts`

**作業内容:**
- `useBooks` hook内の `selectedBook` stateを削除
- `useBookStore.selectedBook` を唯一の参照元にする
- `Sidebar.tsx` が `useBookStore` を 直接参照하도록修正
- `App.tsx` の `useBooks` hook解体：`const { books, loading: booksLoading } = useBooks();` → `const { books, loading: booksLoading } = useBooks();` は維持するが、内部stateをuseBookStoreに集中

**検証:** 作品選択→タブ移動→作品選択に戻っても選択状態が維持されること

---

### ステップ13: loadBookDetails重複定義の統合
**ファイル:** `frontend/src/hooks/useBookDetails.ts`, `frontend/src/hooks/useAppActions.ts`

**作業内容:**
- `useAppActions.ts:loadBookDetails` を削除
- `useBookDetails.ts:loadBookDetails` のみを使用
- `App.tsx` で `useAppActions` から import している `loadBookDetails` を `useBookDetails` hook に切り替え

**検証:** Plot/Write/Analyticsタブ切り替え時にデータが正しく load されること

---

### ステップ14: useTaskStreamの再接続ロジック追加
**ファイル:** `frontend/src/hooks/useTaskStream.ts`

**作業内容:**
```typescript
// onerror時に即座に閉じるのではなく、指数バックオフで再接続
// 現在の実装: eventSource.onerror で即 close()
// 改善後: 最大3回の再接続を試みる

const MAX_RETRIES = 3;
const BASE_DELAY = 1000; // ms

// onerror 内:
let retryCount = 0;
const reconnect = () => {
  if (retryCount < MAX_RETRIES) {
    retryCount++;
    const delay = BASE_DELAY * Math.pow(2, retryCount - 1);
    setTimeout(() => {
      disconnect();
      eventSource = new EventSource(sseUrl);
      // イベントハンドラを再設定
    }, delay);
  } else {
    onError(new Error('SSE connection failed after max retries'));
  }
};
```

**検証:** バックエンド再起動時に自動で再接続されること

---

### ステップ15: ErrorBanner componentの存在確認
**ファイル:** `frontend/src/components/ui/ErrorBanner.tsx` (存在確認)

**作業内容:**
- `src/components/ui/` ディレクトリに `ErrorBanner.tsx` が存在することを確認
- 存在しなければ新規作成:
```typescript
import { AlertTriangle, X } from 'lucide-react';

interface ErrorBannerProps {
  message: string;
  onClose?: () => void;
}

export function ErrorBanner({ message, onClose }: ErrorBannerProps) {
  return (
    <div className="flex items-center gap-2 p-3 bg-red-900/30 border border-red-700 rounded-lg mb-4">
      <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
      <span className="flex-1 text-sm text-red-200">{message}</span>
      {onClose && (
        <button onClick={onClose} className="text-red-400 hover:text-red-300">
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
```

**検証:** `npm run build` が成功すること

---

### ステップ16: LoadingSpinnerとEmptyStateの確認
**ファイル:** `frontend/src/components/ui/LoadingSpinner.tsx`, `EmptyState.tsx`

**作業内容:**
- 存在しないファイルは新規作成
- 既存ものは内容が正しいか確認

**検証:** 各コンポーネントが正しくimport/exportされていること

---

### ステップ17: useAppActionsの型安全化
**ファイル:** `frontend/src/hooks/useAppActions.ts`

**作業内容:**
- `handleBookDelete` の `bookId: any` を `bookId: number` に修正
- 全ての `any` 型を適切な型に置き換える
- `setLoading` の型確認

**検証:** `npm run build` が成功すること

---

### ステップ18: Zustand persist設定の確認
**ファイル:** `frontend/src/store/useUserSettingsStore.ts`

**作業内容:**
- `persist` middlewareの設定確認
- localStorageへの保存がapiKey, temperature, modelTypeのみであることを確認

**検証:** ブラウザリロード後にapiKeyが保持されていること

---

### ステップ19: index.cssの整理
**ファイル:** `frontend/src/index.css`

**作業内容:**
- 使用されていないCSSクラスの削除
- CSS変数の整理（`--bg-main`, `--accent-*` 等が実際に使われているか確認）
- `App.css` と `layout.css` の内容がすでにindex.cssに統合されていることを確認

**検証:** ブラウザでダークテーマが正しく適用されていること

---

### ステップ20: React Frontendの全体的な動作確認
**作業内容:**
- `npm run dev` で全タブ（Books, Plots, Write, Analytics）を手動操作
- API接続エラーが出ないか確認
- console.error がないか確認

**検証:** 全タブで基本操作が完了すること

---

## フェーズ2: APIクライアント強化（ステップ21-26）

### ステップ21: fetch wrapperの共通エラー処理追加
**ファイル:** `frontend/src/lib/apiClient.ts`

**作業内容:**
```typescript
export async function apiRequest<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `HTTP ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}
```

**検証:** APIエラー時に適切な例外がthrowされること

---

### ステップ22: APIクライアントのベースURL管理クラス作成
**ファイル:** `frontend/src/lib/apiClient.ts` (新規関数追加)

**作業内容:**
```typescript
class ApiConfig {
  private baseUrl: string;

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8200/api';
  }

  getBaseUrl(): string {
    return this.baseUrl;
  }

  getUrl(path: string): string {
    return `${this.baseUrl}${path}`;
  }
}

export const apiConfig = new ApiConfig();
```

**検証:** `api.ts` で `apiConfig.getUrl('/books')` が正しくパスを生成すること

---

### ステップ23: expand_candidates APIの追加
**ファイル:** `frontend/src/api.ts`, `frontend/src/types/api.ts`

**作業内容:**
- `PlotExpandParams` typeを確認（`mode?: 'final' | 'candidates'` があればOK、なければ追加）
- `expandPlotsCandidates` 関数を追加:
```typescript
export async function expandPlotsCandidates(params: PlotExpandParams): Promise<string> {
  const body = { ...params, mode: 'candidates' };
  const response = await fetch(apiConfig.getUrl('/plots/expand'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error('Failed to generate plot candidates');
  const data = await response.json();
  return data.task_id;
}
```

**検証:** `npm run build` が成功すること

---

### ステップ24: generate_candidates APIの追加
**ファイル:** `frontend/src/api.ts`

**作業内容:**
- `EpisodeGenerateParams` に `mode?: 'final' | 'candidates'` を追加（または確認）
- `generateEpisodesCandidates` 関数を追加:
```typescript
export async function generateEpisodesCandidates(params: EpisodeGenerateParams): Promise<string> {
  const body = { ...params, mode: 'candidates' };
  const response = await fetch(apiConfig.getUrl('/episodes/generate'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error('Failed to generate episode candidates');
  const data = await response.json();
  return data.task_id;
}
```

**検証:** `npm run build` が成功すること

---

### ステップ25: retry_failed APIの追加確認
**ファイル:** `frontend/src/api.ts`, `src/types/api.ts`

**作業内容:**
- `retryFailedEpisodes` 関数が存在することを確認
- `RetryFailedParams` typeを確認

**検証:** `npm run build` が成功すること

---

### ステップ26: audit APIの型整合確認
**ファイル:** `frontend/src/api.ts`, `frontend/src/types/api.ts`

**作業内容:**
- `AuditPlanParams` typeの確認
- `auditPlan` 関数の引数・戻り値の型確認

**検証:** `npm run build` が成功すること

---

## フェーズ3: Streamlit差分機能のReact実装（ステップ27-38）

### ステップ27: ヘルスチェックAPI connectTaskStream対応
**ファイル:** `frontend/src/api.ts` (新規追加)

**作業内容:**
```typescript
export async function checkBackendHealth(): Promise<{
  status: string;
  database: string;
  worker: string;
  huey_backend: string;
  queue_depth: number;
}> {
  const response = await fetch(`${API_BASE_URL.replace('/api', '')}/health`);
  if (!response.ok) throw new Error('Health check failed');
  return response.json();
}
```

**検証:** `npm run build` が成功すること

---

### ステップ28: グローバルエラーバナーUI改善
**ファイル:** `frontend/src/App.tsx`, `frontend/src/store/useUIStore.ts`

**作業内容:**
- `useUIStore.globalError` を利用し、APIエラー時にApp.tsx上部にエラーバーを表示
- エラーバーに「再試行」ボタンを追加
- バックエンド未接続時に赤色表示、接続回復時に緑色→消える

**検証:** バックエンドを落とした時にエラーが表示され、上げた時に消えること

---

### ステップ29: 作品選択ドロップダウンの改善
**ファイル:** `frontend/src/components/Sidebar.tsx`

**作業内容:**
- 現在の作品一覧をドロップダウンではなくカードグリッド表示に変更
- 各作品の synopsis を表示
- アクティブな作品をハイライト

**検証:** 作品一覧が見やすく、操作しやすいこと

---

### ステップ30: WriteTabにBiblePanel統合確認
**ファイル:** `frontend/src/components/tabs/WriteTab.tsx`

**作業内容:**
- WriteTab 右側に `BiblePanel` が正しく表示されているか確認
- なければ既存のBiblePanelをimportして配置

**検証:** Writeタブで世界观设定(Bible)が表示されること

---

### ステップ31: バックエンド起動時のローディング画面
**ファイル:** `frontend/src/components/ui/LoadingState.tsx` (確認・必要なら作成)

**作業内容:**
- 初回アクセス時にバックエンド接続確認（`/health`）
- 接続中はローディングスピナー表示
- 接続エラー時にエラー画面＋「再試行」ボタン

**検証:** ブラウザキャッシュクリア後にアクセスした時の動作確認

---

### ステップ32: Planning Tabの基本実装
**ファイル:** `frontend/src/components/tabs/PlanningTab.tsx` (新規作成)

**作業内容:**
- 4ステップウィザードのUI実装:
  - Step 1: ジャンル・キーワード選択（Planning Wizard）
  - Step 2: 主人公・敵対者設定
  - Step 3: 話数・プラットフォーム設定
  - Step 4: AI診断結果表示＋生成開始
- 各ステップの状態を `usePlanningWizardStore` (新規作成) で管理

**検証:**  Planning Wizardの各ステップが正しく遷移すること

---

### ステップ33: Monitor Panel (進捗モニター) の改善
**ファイル:** `frontend/src/components/panels/TaskMonitor.tsx`

**作業内容:**
- `streaming_text` の表示改善（逐次更新）
- プログレスバー表示（`current_step / total_steps`）
- ログの自動スクロール
- 「停止」ボタン押下時の確認ダイアログ

**検証:** エピソード生成中にリアルタイムで進捗が更新されること

---

### ステップ34: Analytics TabのChart.js設定確認
**ファイル:** `frontend/src/components/NarrativeGraph.tsx`

**作業内容:**
- Chart.js のライングラフが正しく表示されるか確認
-期間フィルター（7日/30日/全期間）の動作確認
-指標の切り替え（ストレス、カタルシス等）の動作確認

**検証:** Analyticsタブでグラフが表示されること

---

### ステップ35: Patch Review Panelの確認
**ファイル:** `frontend/src/components/PatchReviewPanel.tsx`

**作業内容:**
- Approve/Reject/Edit ボタンが正しく動作するか確認
- パッチ適用後の画面更新

**検証:** パッチの承認・拒否ができること

---

### ステップ36: Prompt Version Timelineの確認
**ファイル:** `frontend/src/components/PromptVersionTimeline.tsx`

**作業内容:**
- バージョン列表示の確認
- Rollback ボタン押下時の確認ダイアログ

**検証:** プロンプトバージョンの一覧とロールバックができること

---

### ステップ37: Style Lab Tab のStub実装
**ファイル:** `frontend/src/components/tabs/StyleLabTab.tsx` (新規作成)

**作業内容:**
- 「準備中」画面を表示するだけのStub実装
- 将来的な機能のための Platzhalter

**検証:** Style Lab タブがエラーなく表示されること

---

### ステップ38: Audit Tab のStub実装
**ファイル:** `frontend/src/components/tabs/AuditTab.tsx` (新規作成)

**作業内容:**
- 「準備中」画面を表示するだけのStub実装
- 品質監査の詳細UIは今後実装

**検証:** Audit タブがエラーなく表示されること

---

## フェーズ4: Docker / デプロイ対応（ステップ39-44）

### ステップ39: React 用プロダクション Dockerfile 作成
**ファイル:** `frontend/Dockerfile` (書き直し)

**作業内容:**
```dockerfile
# Build stage
FROM node:20-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

**新規ファイル:** `frontend/nginx.conf`
```nginx
server {
    listen 3000;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8200/api/;
        proxy_set_header Host $host;
    }

    location /health {
        proxy_pass http://backend:8200/health;
    }
}
```

**検証:** Docker buildが成功すること

---

### ステップ40: docker-compose.yml に React サービスを追加
**ファイル:** `docker-compose.yml`

**作業内容:**
```yaml
services:
  # ...existing backend and streamlit...
  
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: kaku_frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=/api
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**検証:** `docker compose up --build` で全サービスが起動すること

---

### ステップ41: Streamlit サービスの条件付き起動
**ファイル:** `docker-compose.yml`

**作業内容:**
- Streamlit サービスを `profiles` を使ってオプトインに変更:
```yaml
streamlit:
  profiles:
    - streamlit-only
```
- デフォルトでは `backend` + `frontend` のみ起動
- `docker compose --profile streamlit-only up` でStreamlit起動可

**検証:** `docker compose up` で Streamlit が起動しないこと

---

### ステップ42: CORS設定の確認
**ファイル:** `src/config/cors_config.py`

**作業内容:**
- バックエンドのCORS設定が `http://localhost:3000` (開発) と `http://frontend:3000` (本番) を受け入れることを確認
- 必要に応じて `config/cors_config.py` を修正

**検証:** localhost:3000 から localhost:8200 へのAPI呼び出しがCORSエラーなく成功すること

---

### ステップ43: healthcheck intervalの調整
**ファイル:** `docker-compose.yml`

**作業内容:**
- バックエンドのhealthcheck間隔を30s→10sに短縮（起動待時間を短縮）
- Reactのhealthcheckを追加

**検証:** サービス起動から利用可能なまでの時間が短縮されること

---

### ステップ44: 本番環境用 .env.production の作成
**ファイル:** `frontend/.env.production`

**作業内容:**
```
VITE_API_URL=/api
```

**検証:** プロダクションビルド時に `/api` が使われること

---

## フェーズ5: テスト基盤と品質保証（ステップ45-48）

### ステップ45: Vitest + React Testing Library の導入
**ファイル:** `frontend/package.json`, `frontend/vitest.config.ts` (新規作成)

**作業内容:**
```bash
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom
```

**vitest.config.ts:**
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
});
```

**package.json scripts に追加:**
```json
"test": "vitest",
"test:ui": "vitest --ui"
```

**検証:** `npm run test` がエラーなく動作すること

---

### ステップ46: 基本テストの作成
**ファイル:** `frontend/src/test/setup.ts` (新規作成), `frontend/src/test/*.test.tsx`

**作業内容:**
- `setup.ts` で Testing Library の Jest DOM をインポート
- `api.ts` のfetch wrapper 基本テスト
- `useBooks` hook の基本テスト
- `BooksTab` component の基本テスト

**検証:** `npm run test` が全テストをパスすること

---

### ステップ47: E2Eテスト環境 (Playwright) の整備
**ファイル:** `frontend/playwright.config.ts` (新規作成), `frontend/tests/e2e/` (新規ディレクトリ)

**作業内容:**
```bash
npm install -D @playwright/test
npx playwright install chromium
```

**playwright.config.ts:**
```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
  },
});
```

**テストファイル例:** `frontend/tests/e2e/books.spec.ts`

**検証:** `npx playwright test` が動作すること

---

### ステップ48: Lighthouse CI / パフォーマンス測定
**ファイル:** `frontend/lighthouserc.json` (新規作成), `.github/workflows/lighthouse.yml` (新規作成)

**作業内容:**
- Lighthouse CI 設定ファイル作成
- GitHub Actions workflow で PR 時に Lighthouse 測定を実行
- ターゲット指標:
  - Performance: 70以上
  - Accessibility: 90以上
  - Best Practices: 90以上
  - SEO: 90以上

**検証:** Lighthouse CI workflow がエラーなく実行されること

---

## 実装優先度サマリー

| 優先度 | ステップ | 概要 | 工数 |
|--------|----------|------|------|
| **P0** | 1-8, 11-14, 21-22 | 基盤完成・核心バグ修正 | 1-2週間 |
| **P1** | 27-29, 31-33 | UX向上・主要機能 | 1週間 |
| **P2** | 39-44 | Docker/デプロイ対応 | 3-5日 |
| **P3** | 23-26, 34-38 | 差分機能・Analytics強化 | 1週間 |
| **P4** | 45-48 | テスト基盤 | 3-5日 |

---

## チェックリスト

### 毎日確認 (各ステップ完了後)
- [ ] `npm run build` が成功
- [ ] `npm run lint` がエラーなし
- [ ] 変更した機能が手動で動作確認済み

### 週次確認
- [ ] docker-compose 全体起動テスト
- [ ] Lighthouse スコア確認

### 移行完了条件
- [ ] Streamlit を利用しなくなった（profiles で起動しない）
- [ ] 全タブ (Books, Plots, Write, Analytics, Planning, StyleLab, Audit) がエラーなく動作
- [ ] SSE によるリアルタイム更新が動作
- [ ] Lighthouse Performance スコアが70以上
- [ ] `docker compose up` で production 環境が完成