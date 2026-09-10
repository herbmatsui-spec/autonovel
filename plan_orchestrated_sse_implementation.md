# 実装計画書: 解決案2 統合ストリーミングアプローチ

**対象**: フロントエンド（Studio）の新オーケストレーション遮断と easy_mode への固定化の解消
**方式**: 統合ストリーミングアプローチ（リアルタイム重視・SSE完全対応）
**ステップ数**: 72ステップ（各ステップは単一の明確な動作のみ）

---

## Phase 1: バックエンド - SSEエンドポイント追加 (Step 1-18)

### Step 1
`src/backend/routers/orchestrated.py` を開き、ファイル冒頭のインポートセクションに `EventSourceResponse` と `asyncio` と `json` と `os` を追加する

### Step 2
`src/backend/routers/orchestrated.py` のインポートセクションに `from src.agents.event_bus import EventBus, AgentEvent` を追加する

### Step 3
`src/backend/routers/orchestrated.py` のインポートセクションに `from sse_starlette.sse import EventSourceResponse` を追加する

### Step 4
`src/backend/routers/orchestrated.py` の `export_orchestrated_package` 関数の直後（ファイル末尾）に新しい関数 `orchestrated_events` を定義する位置を確保する

### Step 5
`orchestrated_events` 関数のシグネチャを `async def orchestrated_events(correlation_id: str, request: Request) -> EventSourceResponse:` として定義する

### Step 6
関数内で `use_redis = os.environ.get("USE_REDIS_EVENTS", "false").lower() == "true"` を記述する

### Step 7
関数内で `event_bus = EventBus(use_redis=use_redis)` を記述する

### Step 8
関数内で `if use_redis: await event_bus.start_redis()` を記述する

### Step 9
関数内で `queue: asyncio.Queue = asyncio.Queue()` を記述する

### Step 10
関数内で `handler` 関数を定義し、受信した `AgentEvent` を `queue.put_nowait(event)` でキューに入れる処理を記述する

### Step 11
関数内で `event_bus.subscribe(correlation_id, handler)` を記述して購読を開始する

### Step 12
関数内で非同期ジェネレータ `event_generator` を定義し、`while True:` ループで `asyncio.wait_for(queue.get(), timeout=30.0)` でイベントを待機する

### Step 13
`event_generator` 内で `if await request.is_disconnected(): break` を記述して切断検知する

### Step 14
`event_generator` 内で取得した `event` を `yield {"event": "agent_event", "data": json.dumps(event.__dict__)}` で SSE 形式で出力する

### Step 15
`event_generator` 内で `asyncio.TimeoutError` をキャッチし、`yield {"event": "heartbeat", "data": "{}"}` でハートビートを送信する

### Step 16
`event_generator` の `finally` ブロックで `event_bus._subs.get(correlation_id, []).remove(handler)` と `if use_redis: await event_bus.stop_redis()` を記述してクリーンアップする

### Step 17
`orchestrated_events` 関数の最後に `return EventSourceResponse(event_generator())` を記述する

### Step 18
`orchestrated_events` 関数に `@router.get("/events/{correlation_id}")` デコレータを付与する

---

## Phase 2: フロントエンド - 型定義作成 (Step 19-28)

### Step 19
`frontend/src/types/orchestrated.ts` ファイルを新規作成する

### Step 20
`OrchestratedGenerateRequest` インターフェースを定義し、バックエンドの `OrchestratedGenerateRequest` と同一フィールド（book_id, branch_id, ep_num, title, synopsis, target_eps, concept, genre, keywords, target_word_count, style_tag, llm_config）を記述する

### Step 21
`OrchestratedGenerateResponse` インターフェースを定義し、task_id, status, message フィールドを記述する

### Step 22
`OrchestratedTaskStatus` インターフェースを定義し、task_id, status ("pending" | "running" | "completed" | "failed" | "cancelled"), result?, error? フィールドを記述する

### Step 23
`AgentName` 型を `"planning" | "plot" | "bible" | "context_builder" | "writing" | "enrichment" | "audit" | "illustration" | "marketing"` として定義する

### Step 24
`AgentEvent` インターフェースを定義し、agent, payload, correlation_id, round_id?, metadata? フィールドを記述する

### Step 25
`AgentProgress` インターフェースを定義し、agent, status ("pending" | "running" | "completed" | "failed"), startedAt?, completedAt?, payload? フィールドを記述する

### Step 26
`GenerationMode` 型を `"easy" | "orchestrated"` として定義する

### Step 27
`UnifiedStreamingState` インターフェースを定義し、mode, isActive, output, agentProgress, error? フィールドを記述する

### Step 28
`frontend/src/types/index.ts` に `export * from "./orchestrated"` を追加して型を再エクスポートする

---

## Phase 3: フロントエンド - APIクライアント作成 (Step 29-38)

### Step 29
`frontend/src/api/orchestratedApi.ts` ファイルを新規作成する

### Step 30
`import { apiFetch } from "./client"` と `import type { ... } from "../types/orchestrated"` を記述する

### Step 31
`const BASE = "/orchestrated"` 定数を定義する

### Step 32
`generateOrchestrated` 関数を実装：POST `${BASE}/generate` にリクエストボディを送信し、レスポンスを `OrchestratedGenerateResponse` として返す

### Step 33
`getOrchestratedStatus` 関数を実装：GET `${BASE}/status/${taskId}` を呼び出し、レスポンスを `OrchestratedTaskStatus` として返す

### Step 34
`cancelOrchestratedTask` 関数を実装：DELETE `${BASE}/task/${taskId}` を呼び出し、結果を返す

### Step 35
`exportOrchestratedPackage` 関数を実装：GET `${BASE}/export/${bookId}` を呼び出し、Blob と filename を含むオブジェクトを返す

### Step 36
`subscribeToAgentEvents` 関数を実装：`new EventSource(\`${BASE}/events/${correlationId}\`)` で接続し、onmessage で JSON.parse してコールバックを呼ぶ

### Step 37
`subscribeToAgentEvents` の onerror でエラーコールバックを呼ぶ処理を記述する

### Step 38
`subscribeToAgentEvents` 関数の戻り値として EventSource インスタンスを返す

---

## Phase 4: フロントエンド - 統合ストリーミングフック作成 (Step 39-52)

### Step 39
`frontend/src/hooks/useUnifiedStreaming.ts` ファイルを新規作成する

### Step 40
必要なインポートを記述：`useState`, `useCallback`, `useRef`, `useEffect`, `generateContentStream`, `generateOrchestrated`, `getOrchestratedStatus`, `subscribeToAgentEvents`, `useNovelContext`, 型定義

### Step 41
`useUnifiedStreaming` 関数を定義し、内部で `useNovelContext` から必要な値を取得する

### Step 42
`state` state を `useState<UnifiedStreamingState>` で初期化（mode: "easy", isActive: false, output: "", agentProgress: {}, error: undefined）

### Step 43
`abortRef` と `esRef` を `useRef` で作成する

### Step 44
`start` 関数を `useCallback` で定義し、引数に `mode: GenerationMode` と `orchestratedInput?: OrchestratedGenerateRequest` を取る

### Step 45
`start` 内で `abortRef.current = new AbortController()` と `esRef.current?.close()` を実行する

### Step 46
`start` 内で state をリセット：mode 設定、isActive: true, output: "", agentProgress: {}, error: undefined

### Step 47
`start` 内で `setGenerationState` を呼び、isGenerating: true, statusText 設定（mode による分岐）

### Step 48
`start` 内で `mode === "easy"` の場合：`generateContentStream` を呼び、ReadableStream から chunk を読み取り、SSE パースして output に追記する処理を記述する

### Step 49
`start` 内で `mode === "orchestrated"` の場合：`generateOrchestrated(orchestratedInput!)` を呼び、返ってきた task_id で `subscribeToAgentEvents` を開始する処理を記述する

### Step 50
`mode === "orchestrated"` の場合：`subscribeToAgentEvents` のコールバックで `setState` を使い agentProgress を更新する処理を記述する

### Step 51
`mode === "orchestrated"` の場合：ポーリングループで `getOrchestratedStatus` を呼び、status が completed/failed なら終了、pending なら待機する処理を記述する

### Step 52
`cancel` 関数を `useCallback` で定義し、`abortRef.current?.abort()`, `esRef.current?.close()`, state の isActive を false にする処理を記述する

---

## Phase 5: フロントエンド - GeneratePanel 統合 (Step 53-60)

### Step 53
`frontend/src/components/GeneratePanel.tsx` を開き、インポートに `useUnifiedStreaming` を追加する

### Step 54
`useUnifiedStreaming` から返却される `start`, `cancel`, `isActive`, `output`, `agentProgress`, `mode`, `setMode` を受け取る

### Step 55
`mode` state（'simple' | 'reverse' | 'orchestrated'）を `useUnifiedStreaming` の mode と同期させるか、ローカル state として保持する

### Step 56
モード切り替えボタン群に「🤖 8エージェントオーケストレーション」ボタンを追加し、クリックで `setMode('orchestrated')` を呼ぶ

### Step 57
`mode === 'orchestrated'` のとき、エージェント進捗表示コンポーネント（シンプルなリストまたはプログレスバー）を描画する

### Step 58
オーケストレーション実行ボタンを配置し、クリックで `start('orchestrated', { book_id, branch_id, ep_num, title, synopsis, ... })` を呼ぶ

### Step 59
実行中はボタンを無効化し、キャンセルボタンで `cancel()` を呼べるようにする

### Step 60
完了時の `output` をエディタに反映する既存の `onSuccess` コールバック経路を流用する

---

## Phase 6: テスト環境修正 - MSW v2 対応 (Step 61-66)

### Step 61
`frontend/tests/setup.ts` を開き、既存の `import * as rest from "msw/lib/handlers"` を削除する

### Step 62
`import { http, HttpResponse } from "msw"` を追加する

### Step 63
`setupWorker` の引数を配列から `http.get`, `http.post`, `http.delete` を使ったハンドラ配列に書き換える

### Step 64
`/api/books/:id`, `/api/books`, `/orchestrated/generate`, `/orchestrated/status/:task_id`, `/orchestrated/events/:correlation_id` 等のエンドポイントを MSW v2 記法でモックする

### Step 65
EventSource モックは `http.get("/orchestrated/events/:correlation_id", ...)` で SSE 形式のレスポンスを返す実装にする

### Step 66
`worker.start()`, `worker.resetHandlers()`, `worker.stop()` の呼び出し箇所はそのまま残す

---

## Phase 7: ビルド・型チェック修正 (Step 67-72)

### Step 67
`frontend/package.json` を開き、`"typecheck": "node --max-old-space-size=8192 ./node_modules/typescript/bin/tsc --noEmit"` に書き換える

### Step 68
`frontend/vite.config.ts` を開き、`build` オプションに `rollupOptions: { output: { manualChunks: { vendor: ["react", "react-dom", "react-router-dom"] } } }` を追加する

### Step 69
`vite.config.ts` の `build` オプションに `chunkSizeWarningLimit: 1000` を追加する

### Step 70
`frontend/tsconfig.json` が存在する場合、`"skipLibCheck": true` を compilerOptions に追加する（存在しない場合はスキップ）

### Step 71
ターミナルで `cd frontend && npm run typecheck` を実行し、エラーがゼロになるまで修正を繰り返す

### Step 72
ターミナルで `cd frontend && npm run build` を実行し、ビルドが成功することを確認する

---

## 実行上の注意事項

1. **各ステップは独立して実行可能** - 前のステップが完了してから次に進む
2. **検証コマンドを各ステップ後に実行** - 例えば Step 18 後は `python -c "from src.backend.routers.orchestrated import router; print('OK')"` でインポート確認
3. **エラー時は直前のステップのみ再実行** - 遡って修正しない
4. **ファイル編集前には必ず Read ツールで現状確認** - 上書き事故防止
5. **MSW v2 移行は公式ドキュメント準拠** - `http.get()` / `HttpResponse.json()` 形式に統一

## 完了条件

- [ ] `POST /orchestrated/generate` でタスク投入可能
- [ ] `GET /orchestrated/events/{correlation_id}` で AgentEvent ストリーム取得可能
- [ ] フロントエンドで「8エージェントオーケストレーション」モード選択可能
- [ ] リアルタイムでエージェント進捗（planning→plot→bible→...）が表示される
- [ ] 完了時に生成テキストがエディタに反映される
- [ ] `npm run typecheck` がエラーなしで通る
- [ ] `npm run build` がメモリエラーなしで完了する
- [ ] `npm run test:ci` が全パスする