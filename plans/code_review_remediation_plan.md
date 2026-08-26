# コードレビュー 修正実装計画（v3.7 Remediation）

この計画は「前半＋後半のコードレビュー」で検出した 21 項目を、低性能な LLM でも 1 ステップずつ確実に実装できるよう **72 のマイクロステップ** に分解したものです。各ステップは「ファイル」「操作」「検証」を明示し、コピペレベルの指示とします。

優先度: 🔴=即対応 / 🟠=高 / 🟡=中 / 🟢=低

---

## A. バックグラウンドタスクの enqueue 化（Critical #1）— 手順 1‑8

**1.** `src/backend/server.py` を開き、286‑385 行を読む。`execute_service_workflow(` と `execute_easy_mode_generation(` の直接呼び出しを全て見つける（行: 296, 342, 372）。
**2.** 行 296・372 付近の `execute_service_workflow(` を `execute_service_workflow.delay(` に変更。引数（task_id=, api_key=, config_dict=, method_name=, kwargs=, trace_id=）はそのまま維持。
**3.** 行 342 付近の `execute_easy_mode_generation(` を `execute_easy_mode_generation.delay(` に変更。引数は `tasks.py:254` のシグネチャと一致させる。
**4.** `src/backend/tasks.py:130` と `:252` の `@huey.task` シグネチャと、server.py の引数名が一致することを目視確認（不一致ならキーワード名を合わせる）。
**5.** `docker-compose.yml` / `start_app.sh` を開き、Huey ワーカ起動コマンド（`huey_consumer src.backend.worker_config.huey` 等）が存在し、バックエンドと同時に起動することを確認・追加。
**6.** `refine_erotic` エンドポイント（server.py:296）と `critique_optimize`（server.py:372）の両呼び出しが `.delay(` になったことを grep で確認: `grep -n "execute_service_workflow(\|execute_easy_mode_generation(" src/backend/server.py` → 0 件（全て `.delay(` に）。
**7.** `get_task_status_endpoint`（server.py:312）は変更不要（DB 読み取り）。SSE プログレス（`sse.py`）が引き続き使われることを確認。
**8.** 検証: Huey ワーカを起動し `POST /api/easy_mode/generate` を送り、`task_id` が即座に返り、ワーカ側で完了することを確認（イベントループがブロックしない）。

---

## B. illustrations ルーター認証（Critical #2）— 手順 9‑13

**9.** `src/backend/routers/illustrations.py` を開く。
**10.** 行 4 の import 群に `from src.backend.auth import require_api_key` を追加。
**11.** `generate_illustration`（行 22）の引数に `api_key: str = Depends(require_api_key)` を追加。同様に `batch_generate_illustrations`（行 53）にも追加。
**12.** （最小修正）本文の `request: Dict[str, Any]` は一旦残すが、後で Pydantic モデル化する TODO コメントを置く。まず認証だけを入れる。
**13.** 検証: `curl -X POST localhost:8200/api/illustrations/generate -d '{}' -H "Content-Type: application/json"` で `401` になること。次に `-H "X-API-Key: dev-key-1"` を付けると通ること。

---

## C. エピソードタイトルのパストラバーサル修正（Critical #3）— 手順 14‑17

**14.** `src/easy_mode/phase3/asset_pack.py` を開き、上部 import で `sanitize_filename` が使えるか確認（`from src.shared.utils import sanitize_filename` を追加、または `src.shared.utils` に存在しないなら `import re; sanitize_filename = lambda s: re.sub(r'[^\\w\\-]+','_', s)[:120]` を定義）。
**15.** 行 266 を `ep_path = output_dir / f"ep{ep.episode_num:03d}_{sanitize_filename(ep.title)}.txt"` に変更。
**16.** 行 269 の `files` 辞書キーも同じサニタイズ済み名にする: `files[f"ep{ep.episode_num:03d}_{sanitize_filename(ep.title)}.txt"] = ...`。
**17.** 検証: タイトルに `../../etc/cron.d/x` を含むエピソードで asset_pack を生成し、出力ファイルが `output_dir` 内に留まる（親ディレクトリに書かれない）ことを assert する単体テストを追加。

---

## D. 認証の定数時間比較（Critical #4）— 手順 18‑21

**18.** `src/backend/auth.py` を開き、`import hmac`（行 12）が未使用であることを確認。
**19.** `APIKeyService.validate`（行 38‑55）の `return api_key in allowed` を以下に置換:
```python
for k in allowed:
    if hmac.compare_digest(api_key, k):
        return True
return False
```
（リストが空の場合は既存の早期 return を維持。）
**20.** `validate_api_key_or_raise`（行 101）は `service.validate` を呼ぶため変更不要だが、同メソッド内の比較も上記パスを通ることを確認。
**21.** 検証: `pytest` で API キー検証の既存テストが通ること。README.md:16 の記述が実装と一致するか再確認し、不一致なら README を事実に合わせる。

---

## E. マウント済みルーター認証監査（High #5）— 手順 22‑24

**22.** コマンド実行: `grep -rn "require_api_key" src/backend/routers/ | grep -c` と、状態変化するルート（POST/PUT/DELETE/PATCH）の一覧を `grep -rn "@router.\(post\|put\|delete\|patch\)" src/backend/routers/` で取得。
**23.** 差分を確認し、マウント済み（server.py:259‑274）のうち認証が抜けているのは `illustrations` のみであったことを記録（他は既に付与済み）。
**24.** 検証: 今後追加されたルートで認証漏れを防ぐため、`src/backend/routers/__init__.py` か CI に「状態変化ルートは `require_api_key` を含む」という lint チェックを追加（簡易: grep ベースのシェルスクリプト）。

---

## F. SSE クライアント切断検知（High #6）— 手順 25‑29

**25.** `src/backend/sse.py` を開き、Redis ループ（~64 行）と SQLite ループ（~119 行）の `while True` を読む。
**26.** 各 SSE エンドポイント関数に `request: Request`（fastapi の `Request`）引数を追加。
**27.** Redis ループ内で yield の直後に `if await request.is_disconnected(): break` を追加。
**28.** SQLite ループ内も同様に追加。例外時の `continue` の前にも同一チェックを入れる。
**29.** 検証: クライアントを途中で切断し、サーバ側のコルーチンが無限ループせず終了することをログで確認。

---

## G. AsyncOpenAI クライアント再利用（High #7）— 手順 30‑35

**30.** `src/core/llm_clients/openai.py` を開き、`__init__` と `generate_json`（行 50）・`generate_text`（行 181）を読む。
**31.** クラスに `self._client = None` を追加し、プライベートメソッド `_get_client(self, base_url, api_key)` を追加（既存なら再利用、無ければ `openai.AsyncOpenAI(...)` を生成してキャッシュ）。
**32.** `generate_json` 内の `client = openai.AsyncOpenAI(...)` を `client = self._get_client(base_url, api_key)` に置換。
**33.** `generate_text` 内も同様に置換。
**34.** `async def aclose(self) -> None:` を追加: `if self._client: await self._client.aclose()`。
**35.** 検証: `server.py` の `lifespan` の `finally` に `await AppContainer.llm().aclose()` 等の呼び出しを追加（コンテナの公開メソッドに合わせる）。負荷テストで接続数が増えないことを確認。

---

## H. 生成コンテキストキャッシュのキー修正（High #8）— 手順 36‑39

**36.** `src/backend/workflows/writing_langgraph.py` を開き、`_gen_ctx_cache`（行 73）と `_get/_set_cached_gen_ctx`（134‑152）を読む。
**37.** キャッシュをクラス変数からインスタンス変数（`self._gen_ctx_cache = {}` in `__init__`）に変更、またはキーに `book_id`/`series_id` を含める。
**38.** キー構築（171‑173）を `f"{book_id}:{ep_num}:{genre}:{easy_mode}"` のように一意化。
**39.** 検証: 同一ジャンル＋話数の異なる 2 作品でキャッシュが共有されないことを assert する単体テストを追加。

---

## I. 不足マイグレーション追加（High #9）— 手順 40‑44

**40.** `src/backend/database/models.py` で `NarrativeMetric` / `CostRecord` / `GenerationRun`（または該当クラス名）の列定義を特定。
**41.** コマンド: `cd src/backend && alembic revision -m "add metrics cost runs tables"` を実行（DB 接続不要な offline 生成）。生成されたファイルを開く。
**42.** `upgrade()` に 3 テーブルの `op.create_table(...)` をモデル列と一致させて記述。
**43.** `downgrade()` に `op.drop_table(...)` を 3 件記述。
**44.** 検証: ローカル SQLite で `alembic upgrade head` を実行し `SELECT name FROM sqlite_master` で 3 テーブルが出来ることを確認。`init_db` の本番パス（core.py:349）が成功することを確認。

---

## J. フロントエンド: 状態・APIキー・リダイレクト（High #10）— 手順 45‑52

**45.** `frontend/src/store/useProjectStore.ts` を開き `selectedBookId`（行 15）を確認。
**46.** `frontend/src/App.tsx` の自動選択（98‑102）で `setSelectedBookId(books[0].id)` を呼ぶよう追加。
**47.** 代替として `selectedBookId` を削除しロードを一箇所に集約する場合は、`App.tsx:105‑110` のガードを外して `bookStore` の選択に依存するよう書き換える（いずれか一方を選択）。
**48.** `frontend/src/api/api.ts` を開き、`fetch` ヘルパーに関数 `withAuth(opts, apiKey)` を追加し、`headers["X-API-Key"] = apiKey` を設定。
**49.** `frontend/src/store/useAppActions.ts` の `api_key: apiKey` を含む箇所（行 60,92,120,140,161,189）から `api_key` を削除し、`withAuth` 経由でヘッダ送信に変更。
**50.** `frontend/src/components/EasyMode/EasyModeContainer.tsx:79` の `window.location.href = res.redirect_url` を、同じオリジンまたは相対パスのみ許可する `isSafeRedirect(url)` ユーティリティで検証してから代入するよう変更。
**51.** `frontend/src/utils/` に `isSafeRedirect(url: string): boolean` を追加（先頭が `/` で始まり `//` でない、または `window.location.origin` と一致する場合のみ true）。
**52.** 検証: `npm run build` が通り、ブラウザの Network タブでリクエスト body に `api_key` が含まれないことを確認。

---

## K. レート制限ミドルウェアの整合（Medium #11）— 手順 53‑55

**53.** `src/backend/server.py` の `rate_limit_middleware`（162‑196）を開く。`fail-closed`（Redis 障害時 503）に決定し、行 194 の誤ったコメント「Don't block the request...」を削除。
**54.** `import redis.exceptions` を追加し、`except (ConnectionError, TimeoutError, OSError)` を `except (ConnectionError, TimeoutError, OSError, redis.exceptions.RedisError)` に拡張して一貫して 503 を返す。
**55.** 検証: `auth.py` の `get_rate_limit_key`（行 57）を使い、API キー付きリクエストはキー単位、無しは IP 単位でカウントされるようキー生成を修正。

---

## L. ネストした UnitOfWork の修正（Medium #12）— 手順 56‑58

**56.** `src/backend/database/uow.py` の `__aenter__`（163‑166）と `__aexit__`（195‑219）を読む。
**57.** 既に `in_transaction()` の場合、`connection.begin()` で SAVEPOINT を開始し、その savepoint オブジェクトを保持するよう変更。
**58.** `__aexit__` で成功時は savepoint の `release()`、失敗時は `rollback()` のみを行い、親トランザクションを commit しないよう修正。検証: ネスト UoW の単体テストで親の変更が子の失敗でロールバックしないことを確認。

---

## M. DB ラッパーのノンブロッキング化（Medium #13）— 手順 59‑61

**59.** `src/backend/database/core.py` の `DatabaseConnectionWrapper`（104‑121）と `release_read_conn`（201）を読む。
**60.** 同期 sqlite3 DBAPI の直接呼び出しを `AsyncConnection` + `text()` + `execute()` に置換し、イベントループをブロックしないよう修正。
**61.** `await self.dbapi_conn.rollback()` を非同期接続の `await conn.rollback()` に修正し、接続が確実に返却・クローズされることを確認。検証: 読み取り取得で接続リークが起きない単体テスト。

---

## N. LLM サイレント劣化とデッドリトライ（Medium #14）— 手順 62‑65

**62.** `src/backend/workflows/writing_langgraph.py` の `node_drafting`（~276）・`node_audit`（~359）を開く。最終リトライ後、空文字/False を返すのではなく `from src.core.exceptions import PipelineError; raise PipelineError(...)` を投げるよう変更。
**63.** `run()`（~673）で該当エピソードを「失敗」とマークし、空エピソードを成功として流さないよう修正。
**64.** `src/core/llm_clients/gemini.py:264‑272` の `if not await self._handle_error(...): raise e / raise e` のデッドブロックを削除（リトライは外側のデコレータに委ねる）。
**65.** 検証: リトライ上限に達した場合に例外が伝播する単体テストを追加。

---

## O. エラーハンドラの情報漏洩防止（Medium #15）— 手順 66‑67

**66.** `src/backend/error_handlers.py:56` を開く。`detail=str(exc)` を汎用メッセージ（例: `"内部エラーが発生しました。詳細はログを参照してください。"`）に置き換え、元の例外は `logger.error(..., exc_info=True)` のみにする。
**67.** 検証: 意図的な 500 を発生させ、レスポンス body にファイルパス/SQL が含まれないことを確認するテスト。

---

## P. フロントエンドその他（Medium #16）— 手順 68‑70

**68.** `frontend/src/api/api.ts:200` の `EventSource` はヘッダを付けられないため、`/tasks/{id}/stream` を `fetch` + ReadableStream に変更し `X-API-Key` ヘッダを付けるか、ゲートウェイで署名クッキーを発行する方式にする（最小修正: クエリにキーを乗せるのは非推奨のため、設計メモを残し `fetch` ストリーム化を実装）。
**69.** `frontend/src/components/ErrorBoundary.tsx:67` の `localStorage.clear()` を、アプリのプレフィックス付きキーのみを `removeItem` するよう変更（全オリジン破壊を防止）。
**70.** `PlotsTab.tsx:48` / `StrategyTab.tsx:179,197` / `AnalyticsTab.tsx:77` / `TaskMonitor.tsx:194` / `PatchReviewPanel.tsx:70,119` の React `key` を配列インデックスから安定 ID（item.id 等）に置換。

---

## Q. マウントされていないデッドルーターの削除（Low #17）— 手順 71

**71.** `src/backend/routers/collab.py`・`cost.py`・`trace.py`・`prompt_compare.py`・`hooks.py` を確認し、`server.py` の router_modules（259‑274）から参照されていないことを grep で確認後、未使用なら `archive/` へ移動（または本当に公開するなら `require_api_key` を付けてマウント）。

---

## R. 片付け・計画同期・except 整理（Low #18‑20）— 手順 72

**72.** ルート直下の `find_try.py` / `fix_server.py` / `fix_server_simple.py` / `replace_retry.py` を `archive/` へ移動。併せて `plans/v3.6_implementation_plan.md` に「React Query 未導入・Zustand 継続」の実態を追記し、`except Exception` が多い上位ファイル（tasks.py, writing_langgraph.py, database/core.py）の 10 件を `trace_id` 付きログに絞り修正する TODO を `CODE_REVIEW_3X.md` にまとめる。

---

## 完了チェックリスト（自動生成サンプル）

```
- [ ] 1  server.py のタスク呼び出しを .delay() に変更
- [ ] 2  refine_erotic / critique_optimize も .delay()
- [ ] 3  execute_easy_mode_generation.delay() 引数整合
- [ ] 4  Huey ワーカ起動を docker-compose/start_app に追加
- [ ] 5  grep で直接呼び出し 0 件確認
- [ ] 6  SSE プログレス維持確認
- [ ] 7  ワーカ起動スモークテスト
- [ ] 8  イベントループ非ブロック確認
- [ ] 9  illustrations.py import require_api_key
- [ ] 10 illustrations 両エンドポイントに Depends 追加
- [ ] 11 Pydantic 化 TODO 記載
- [ ] 12 401 検証
- [ ] 13 認証通過検証
- [ ] 14 asset_pack sanitize_filename import/定義
- [ ] 15 ep_path サニタイズ
- [ ] 16 files キーもサニタイズ
- [ ] 17 パストラバーサル単体テスト
- [ ] 18 auth.py hmac 未使用確認
- [ ] 19 validate を compare_digest に
- [ ] 20 validate_api_key_or_raise 経路確認
- [ ] 21 README 整合
- [ ] 22 ルーター認証 grep 監査
- [ ] 23 illustrations のみ抜け確認
- [ ] 24 lint チェック追加
- [ ] 25 sse.py ループ読解
- [ ] 26 SSE に Request 引数追加
- [ ] 27 Redis ループ切断検知
- [ ] 28 SQLite ループ切断検知
- [ ] 29 切断テスト
- [ ] 30 openai.py 読解
- [ ] 31 _get_client キャッシュ追加
- [ ] 32 generate_json で再利用
- [ ] 33 generate_text で再利用
- [ ] 34 aclose 追加
- [ ] 35 lifespan finally で aclose
- [ ] 36 writing_langgraph キャッシュ読解
- [ ] 37 インスタンス/一意キー化
- [ ] 38 キー構築一意化
- [ ] 39 キャッシュ共有単体テスト
- [ ] 40 3 モデル列特定
- [ ] 41 alembic revision 生成
- [ ] 42 upgrade に create_table
- [ ] 43 downgrade に drop_table
- [ ] 44 ローカル upgrade 検証
- [ ] 45 useProjectStore selectedBookId 確認
- [ ] 46 App で setSelectedBookId
- [ ] 47 または削除して集約
- [ ] 48 api.ts withAuth 追加
- [ ] 49 useAppActions api_key 削除
- [ ] 50 EasyModeContainer リダイレクト検証
- [ ] 51 isSafeRedirect 実装
- [ ] 52 build + Network 検証
- [ ] 53 rate_limit fail-closed 決定+コメント削除
- [ ] 54 RedisError も捕捉
- [ ] 55 get_rate_limit_key 使用
- [ ] 56 uow.py 読解
- [ ] 57 ネストで SAVEPOINT
- [ ] 58 親 commit しない
- [ ] 59 core.py ラッパ読解
- [ ] 60 AsyncConnection+text 化
- [ ] 61 rollback 非同期化
- [ ] 62 node 最終失敗で raise
- [ ] 63 run() 失敗マーク
- [ ] 64 gemini デッドリトライ削除
- [ ] 65 リトライ例外テスト
- [ ] 66 error_handlers 汎用化
- [ ] 67 漏洩テスト
- [ ] 68 SSE fetch 化/設計メモ
- [ ] 69 ErrorBoundary スコープ削除
- [ ] 70 React key 安定化
- [ ] 71 デッドルーター archive/移動
- [ ] 72 ルートスクリプト移動+計画同期+except TODO
```

このファイルを `plans/code_review_remediation_plan.md` としてコミットし、ステップ順に実装・スモークテストを行ってください。各ステップは独立してコミット可能な大きさにしているため、低性能 LLM でも 1 ステップずつ確実に適用できます。
