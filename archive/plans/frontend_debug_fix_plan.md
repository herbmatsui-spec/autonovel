# フロントエンド デバッグ・修正 実装計画書

**対象**: `streamlit_app/`（Streamlit 1.58.0, バックエンド FastAPI ポート 8200）
**作成日**: 2026-07-18
**目的**: アプリが起動不能な致命的エラーと、バックエンドAPIとの整合矛盾を解消し、UI が実際に動作する状態にする。

---

## 0. 現状サマリ（再現確認済）

- `python -c "import streamlit_app.pages_config"` →
  `ImportError: cannot import name 'render_import_tab' from 'streamlit_app.ui_tabs_writing'`
  ⇒ アプリ起動時に `app.py` → `pages_config` がロードされ即クラッシュ。
- `Streamlit 1.58.0` には `st.experimental_async` が存在しない（`hasattr(st,'experimental_async') == False`）。
- `api_client.py` が持つのは `{get_client, _request, start_plan_generation, start_plot_expansion, start_episode_writing, get_task_status, stop_task, start_erotic_refinement}` のみ。
  `proxy.py` / 各タブが想定する `list_books/get_book/get_plots/...` は未実装。
- バックエンド実エンドポイント（`src/backend/routers/*`, `server.py` + `docker-compose.yml`）は **ポート 8200** で、
  `/api/books`, `/api/tasks/{id}/status`, `/api/novel/{pid}/report`, `/api/novel/{pid}/episodes`,
  `/commercial/run`（response: `{success, data, trace_id}`）等を提供。

---

## 1. エラー・コンフリクト一覧（優先度順）

| ID | 場所 | 問題 | 重要度 |
|----|------|------|--------|
| E1 | `pages_config.py:23-28` | `ui_tabs_writing` から存在しない 4 関数を import | 致命 |
| E2 | `app.py:108` | `st.experimental_async` は存在せず AttributeError | 致命 |
| E3 | `proxy.py:69-101` + `api_client.py` | `api_client` に存在しないメソッド群を呼ぶ | 致命 |
| E4 | `ui_tabs_writing.py:192,209,284,305,320` | `httpx` 未 import で NameError | 致命 |
| E5 | `ui_tabs_writing.py:112-117` | `_request` の引数渡し方が誤り（`**dict` 展開） | 高 |
| E6 | `health_check.py:15` / `backend_launcher.py:16` / `ui_tabs_writing.py` / `ui_tabs_analytics.py:545,587` / `api_client.py:9` | バックエンドポート 8200/8000 混在 | 高 |
| E7 | `health_check.py:80-82` | `start_backend_processes()` は未定義（`start_backend()` のみ） | 高 |
| E8 | `health_check.py:50-94` | 非同期前提の `ensure_backend_available` が同期呼び出しと整合しない | 中 |
| E9 | `ui_tabs_writing.py:25-32,181,243,281,302` | モジュールトップレベルで `UIStateStore()` に直接書き込み／`st.session_state` 参照と `get_ui` 参照が混在 | 中 |

---

## 2. 修正方針

### 2.1 致命的インポート破綻の解消（E1）
`pages_config.py` が期待する `render_writing_tab / render_plot_tab / render_import_tab / render_rebuild_tab`
を `ui_tabs_writing.py` に追加し、既存の `render_novel_production_tab` を `render_writing_tab` として公開する。
（`pages_config` のラッパ `_make_tab_wrapper` は `render_func(state, engine, book_id)` のシグネチャで呼ぶため、
追加関数は同じシグネチャを受け入れ、まだ実装のない `plot/import/rebuild` は「準備中」プレースホルダーを返す。）

### 2.2 バックエンド死活監視の同期化（E2, E8）
- `app.py` の `st.experimental_async(ensure_backend_available)` を削除し、通常の同期呼び出しに変更。
- `health_check.py` の `ensure_backend_available` を同期関数にし、`check_backend_health()` を
  `asyncio.run(...)` で内部実行するよう修正（UI ブロッキングは許容／再描画で更新）。
- `validate_api_key_async` はsidebar 側で `asyncio.run` しており現状維持で問題なし。

### 2.3 api_client の API 実メソッド化（E3, E5）
`proxy.py` およびタブが要求するメソッドを `api_client.py` に追加実装し、`_request`（同期ブリッジ）経由で
実エンドポイントへ正しくルーティングする。ポートは 8200 に統一（E6）。
追加メソッド（いずれも `API_BASE_URL` ベース `/api/...`）：
- `list_books()`, `get_book(book_id)`, `delete_book(book_id)`
- `get_plots(book_id)`, `get_chapters(book_id)`, `create_chapter(...)`, `delete_chapter(...)`
- `get_bible(book_id)`, `get_opt_history(book_id)`
- `analyze_style_dna(api_key, sample)`, `export_package(api_key, book_id)`
- `audit_producer_plan(api_key, genre, keywords, trend_memo, ...)`, `get_issues(book_id)`,
  `resolve_issue(issue_id, action, api_key)`, `import_chapter(api_key, book_id, ep_num, text, do_refine)`,
  `generate_marketing(api_key, book_id, latest_ep)`
- `commercial_run(config: dict)` （`/commercial/run` へ `json=config` で POST、8200）

### 2.4 ポート統一 8200（E6）
- `api_client.py`: `API_BASE_URL = "http://127.0.0.1:8200/api"`
- `backend_launcher.py`: `_BACKEND_PORT = 8200`
- `ui_tabs_writing.py`: 全ハードコード URL を `http://localhost:8200/...` に統一
- `ui_tabs_analytics.py:545,587`: `http://localhost:8200/...` に統一
- `health_check.py`: 既に 8200（維持）

### 2.5 バックエンド起動関数名の統一（E7）
`health_check.py` の `start_backend_processes` 呼び出しを `backend_launcher.start_backend()` に変更。
（`start_backend()` は既に `subprocess.Popen` で uvicorn 起動し、成功時は Popen を返す仕様。
`success` 判定は「プロセスが起動した（None/異常でなければ）」とする。）

### 2.6 ui_tabs_writing の不具合修正（E4, E5, E9）
- `import httpx` を追加（E4）。
- `commercial/run` 呼び出しを `api_client.commercial_run(commercial_config)` に置換（E5）。
- モジュールトップレベルの副作用的な `set_ui(...)` 初期化を `render_writing_tab` 内部の初回ガードに移動（E9）。
- 進捗ポーリング中に `status` 変数が while ループ外（`if status != "completed"`）で参照されるスコープ問題を修正。

---

## 3. 実装ステップ

1. `streamlit_app/api_client.py`
   - `API_BASE_URL` を `:8200/api` に変更。
   - 上記 §2.3 のメソッド群を追加（`_request` ラップ）。
   - `commercial_run(config)` を追加。
2. `streamlit_app/backend_launcher.py`
   - `_BACKEND_PORT = 8200`、`_BACKEND_URL` も 8200 に合わせる。
3. `streamlit_app/health_check.py`
   - `ensure_backend_available` を同期化（`asyncio.run` で `check_backend_health` を実行）。
   - `start_backend_processes` → `start_backend` に変更し、返り値で success 判定。
4. `streamlit_app/app.py`
   - `st.experimental_async(...)` を通常呼び出しに変更。
5. `streamlit_app/ui_tabs_writing.py`
   - `import httpx` 追加。
   - `commercial/run` を `api_client.commercial_run` に置換し、ハードコード URL を 8200 に統一。
   - トップレベル `set_ui` 初期化を関数内ガードに移動。
   - `status` 変数スコープ修正。
   - `render_writing_tab(state=None, engine=None, book_id=None)` を追加（本体は既存ロジック）。
   - `render_plot_tab / render_import_tab / render_rebuild_tab` プレースホルダーを追加。
6. `streamlit_app/pages_config.py`
   - インポート名を変更なし（`render_writing_tab` 等が存在すれば解決）。`render_novel_production_tab` の
     エクスポートは維持（他から参照されないため削除でも可）。
7. `streamlit_app/ui_tabs_analytics.py:545,587`
   - `http://localhost:8200/...` に統一。

---

## 4. 検証

- 構文: 全モジュール `python -m py_compile` でエラーなし。
- インポート: `python -c "import streamlit_app.pages_config"` が ImportError なく通る。
- `python -c "import streamlit_app.proxy"` が AttributeError なく通る。
- `python -c "import streamlit_app.app"` が `st.experimental_async` 由来のエラーなくロードする。
- ポート整合: 全フロント側 URL / BASE_URL が 8200 であることを grep で確認。

---

## 5. リスク・注意

- `proxy.py` の他メソッド（`audit_producer_plan` 等）はバックエンド未実装エンドポイントを呼ぶ可能性があるが、
  今回は「存在しない api_client メソッド」起因のクラッシュを直すのが優先。実エンドポイント不在時は
  `_request` 内で例外が上がり UI 側で捕捉される設計に留める。
- `render_plot_tab/import/rebuild` は暫定プレースホルダー。実機能は別タスク。
- 本修正は UI 層のみ。バックエンド側の挙動・レスポンス形状は現状の実装（`{success,data,trace_id}` 等）に合わせる。
