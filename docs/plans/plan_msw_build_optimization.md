# 実装計画書: MSW v2移行とビルドメモリ最適化

**対象**: フロントエンド（Studio）のテスト環境・ビルド環境改善
**方式**: 段階的実装・3ステップごと検証
**ステップ数**: 18ステップ（各ステップは単一の明確な動作のみ）

---

## Phase 1: MSW v2 移行 (Step 1-12)

### Step 1
`frontend/tests/setup.ts` を開き、ファイル冒頭のインポートセクションから `import * as rest from "msw/lib/handlers"` を削除する

### Step 2
`frontend/tests/setup.ts` のインポートセクションに `import { http, HttpResponse } from "msw"` を追加する

### Step 3
`frontend/tests/setup.ts` の `setupWorker` の引数を配列から `http.get`, `http.post`, `http.delete` を使ったハンドラ配列に書き換える（`/api/books/:id` エンドポイント）

### Step 4
`/api/books` エンドポイントを `http.get("/api/books", ...)` 形式でモックする

### Step 5
`/orchestrated/generate` エンドポイントを `http.post("/orchestrated/generate", ...)` 形式でモックする

### Step 6
`/orchestrated/status/:task_id` エンドポイントを `http.get("/orchestrated/status/:task_id", ...)` 形式でモックする

### Step 7
`/orchestrated/events/:correlation_id` エンドポイントを `http.get("/orchestrated/events/:correlation_id", ...)` 形式でモックし、EventSource 用の SSE 形式レスポンスを返す実装にする

### Step 8
`/api/easy_mode/generate_gacha_plans` エンドポイントを `http.post("/api/easy_mode/generate_gacha_plans", ...)` 形式でモックする

### Step 9
`/api/easy_mode/generate_digest` エンドポイントを `http.post("/api/easy_mode/generate_digest", ...)` 形式でモックする

### Step 10
`/api/editor/assist` エンドポイントを `http.post("/api/editor/assist", ...)` 形式でモックする

### Step 11
`/api/branches/:bookId/fork`, `/api/branches/:bookId`, `/api/branches/diff` エンドポイントを `http.get` 形式でモックする

### Step 12
`worker.start()`, `worker.resetHandlers()`, `worker.stop()` の呼び出し箇所はそのまま残す

---

## Phase 2: ビルドメモリ最適化 (Step 13-18)

### Step 13
`frontend/package.json` を開き、`"typecheck": "node --max-old-space-size=8192 ./node_modules/typescript/bin/tsc --noEmit"` に書き換える

### Step 14
`frontend/vite.config.ts` を開き、`build` オプションに `rollupOptions: { output: { manualChunks: { vendor: ["react", "react-dom", "react-router-dom"] } } }` を追加する

### Step 15
`vite.config.ts` の `build` オプションに `chunkSizeWarningLimit: 1000` を追加する

### Step 16
`vite.config.ts` の `build` オプションに `minify: "terser"` と `terserOptions: { compress: { drop_console: true, drop_debugger: true } }` を追加する（本番ビルド最適化）

### Step 17
`frontend/tsconfig.json` が存在する場合、`"skipLibCheck": true` を compilerOptions に追加する（存在しない場合はスキップ）

### Step 18
ターミナルで `cd frontend && npm run typecheck` を実行し、エラーがゼロになるまで修正を繰り返す。その後 `npm run build` を実行し、ビルドが成功することを確認する

---

## 実行上の注意事項

1. **各ステップは独立して実行可能** - 前のステップが完了してから次に進む
2. **検証コマンドを各ステップ後に実行** - 例えば Step 2 後は `grep "http" frontend/tests/setup.ts` でインポート確認
3. **エラー時は直前のステップのみ再実行** - 遡って修正しない
4. **ファイル編集前には必ず Read ツールで現状確認** - 上書き事故防止
5. **MSW v2 移行は公式ドキュメント準拠** - `http.get()` / `HttpResponse.json()` 形式に統一
6. **SSE モックは `HttpResponse.text()` で `text/event-stream` を返す** 実装にする

## 完了条件

- [ ] `frontend/tests/setup.ts` が MSW v2 記法（`http`, `HttpResponse`）のみで動作する
- [ ] `npm run test:ci` が全パスする（カバレッジ閾値を満たす）
- [ ] `npm run typecheck` がメモリエラーなしで完了する
- [ ] `npm run build` がメモリエラーなしで完了する
- [ ] ビルド成果物のサイズが最適化されている（manualChunks が効いている）

---

## MSW v2 移行の詳細仕様

### 変更前（MSW v1）:
```typescript
import * as rest from "msw/lib/handlers";
rest.get("/api/books/:id", (req, res, ctx) => {
  return res(ctx.json({...}));
});
```

### 変更後（MSW v2）:
```typescript
import { http, HttpResponse } from "msw";
http.get("/api/books/:id", ({ params }) => {
  return HttpResponse.json({...});
});
```

### SSE エンドポイントのモック実装:
```typescript
http.get("/orchestrated/events/:correlation_id", () => {
  // EventSource は接続確立後にイベントを送信するため、text/event-stream を返す
  return new HttpResponse(
    `data: ${JSON.stringify({ event: "agent_event", data: JSON.stringify({ agent: "planning", status: "running" }) })}\n\n`,
    {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    }
  );
});
```

---

## ビルド最適化の詳細仕様

### package.json 変更:
```json
"typecheck": "node --max-old-space-size=8192 ./node_modules/typescript/bin/tsc --noEmit"
```

### vite.config.ts 変更:
```typescript
build: {
  outDir: "dist",
  rollupOptions: {
    output: {
      manualChunks: {
        vendor: ["react", "react-dom", "react-router-dom"]
      }
    }
  },
  chunkSizeWarningLimit: 1000,
  minify: "terser",
  terserOptions: {
    compress: {
      drop_console: true,
      drop_debugger: true
    }
  }
}
```

---

## 検証コマンド一覧

| Phase | Step | 検証コマンド |
|-------|------|-------------|
| MSW | 1-2 | `grep -E "http|HttpResponse" frontend/tests/setup.ts` |
| MSW | 3-11 | `npm run test:ci` |
| MSW | 12 | `grep "worker\." frontend/tests/setup.ts` |
| Build | 13 | `cat frontend/package.json \| grep typecheck` |
| Build | 14-16 | `cat frontend/vite.config.ts \| grep -A 10 "build:"` |
| Build | 17 | `cat frontend/tsconfig.json \| grep skipLibCheck` |
| Build | 18 | `cd frontend && npm run typecheck && npm run build` |