# 覇権小説エンジン v3.0 リファクタリング実装計画：48ステップ

## 前提

- **対象**: `streamlit_app/app.py` を含むツール群全体
- **問題**: 評価で判明した技術的負債（参照エラー、スタブ、未完成コード）
- **前提**: Python 3.11+, Pydantic v2, Streamlit, FastAPI, asyncio
- **方式**: 低性能LLMでも実装可能な48の小さな反復ステップ

---

## 評価で判明した技術的負債

| # | 問題 | 重大度 |
|---|------|--------|
| 1 | `streamlit_app/engine.py` が1行のみ・参照エラー | 高 |
| 2 | `src/api/client.py` へのアクセス不可 | 高 |
| 3 | `PlannerProxy.create_hegemony_plan()` 空実装 | 中 |
| 4 | `src/infrastructure/api/__init__.py` が空 | 中 |
| 5 | `_container_cache` スレッドセーフ未対応 | 中 |
| 6 | `st.experimental_async` 実験的API依存 | 中 |
| 7 | `server.py` 961行の巨大ファイル | 低〜中 |
| 8 | CORS `allow_origins=["*"]` | 中 |

---

## Phase 1: 参照エラー修正とスタブ除去 (Step 1-8)

### Step 1: `streamlit_app/engine.py` を修正
```
現在の状態: from proxy import UltimateHegemonyEngineProxy as UltimateHegemonyEngine
修正後: from streamlit_app.proxy import UltimateHegemonyEngineProxy
```
- `streamlit_app/proxy.py` の `UltimateHegemonyEngineProxy` を正しくインポート
- `__all__` を追加して公開APIを明示

### Step 2: `src/api/client.py` のアクセス権問題を解決
```
原因: ファイルパーミッションまたはロック状態
対応: ファイル内容を確認して再作成
```
- ファイルが存在しない場合は `src/infrastructure/api/client.py` からコピー
- または `streamlit_app/api_client.py` を `src/api/client.py` として複製

### Step 3: `src/infrastructure/api/__init__.py` にAPIクライアントを配置
```
現在の状態: 空ファイル
修正後: src/infrastructure/api/__init__.py に api_client オブジェクトを配置
```
- `src/infrastructure/api/client.py` を作成
- `API_BASE_URL`, `_request()`, `start_plan_generation()` などを実装

### Step 4: `streamlit_app/api_client.py` と `src/infrastructure/api/` の統合
```
streamlit_app/api_client.py → src/infrastructure/api/client.py へ統合
streamlit_app/api_client.py は src.infrastructure.api.client をインポートするラッパーへ変更
```

### Step 5: `PlannerProxy.create_hegemony_plan()` の空実装を修正
```
現在の状態: pass のみ
修正後: api_client.plan_generation() を呼び出す実装修正
```
- `src/infrastructure/api/client.py` に `plan_generation()` メソッドを追加
- `PlannerProxy.create_hegemony_plan()` から呼び出し

### Step 6: `streamlit_app/progress.py` の `api_client` インポート修正
```
現在の状態: from src.infrastructure.api import api_client
修正後: 正しいモジュールパスを設定
```

### Step 7: `streamlit_app/workflow_types.py` の `WORKFLOW_API_MAP` 整合性確認
```
確認項目:
- api_client に定義された全関数名が WORKFLOW_API_MAP と一致するか
- 不足している関数がないか
```

### Step 8: インポート循環の検出と解決
```
tools: Python -c "import streamlit_app.app" で起動確認
問題があれば import 順を修正
```

---

## Phase 2: スレッド安全性とキャッシュ修正 (Step 9-16)

### Step 9: `streamlit_app/proxy.py` の `_container_cache` をスレッドセーフに修正
```python
# 現在: _container_cache: dict[str, AppContainer] = {}
# 修正後: import threading
_container_cache: dict[str, AppContainer] = {}
_cache_lock = threading.Lock()

def get_di_container(api_key: str = "DUMMY") -> AppContainer:
    global _container_cache
    with _cache_lock:
        if api_key not in _container_cache:
            container = AppContainer(api_key=api_key)
            container.wire(modules=[__name__])
            _container_cache[api_key] = container
        return _container_cache[api_key]
```

### Step 10: `streamlit_app/state.py` の `UIStateStore._subscribers` をスレッドセーフに修正
```python
# 追加: _subscriber_lock = threading.Lock()
# subscribe() と _notify() でロックを使用
```

### Step 11: `SessionManager._save_to_disk()` の排他処理確認
```python
# ファイル書き込み時の race condition 対策
# fcntl (Linux) または msvcrt (Windows) を使用
```

### Step 12: `config/file_watcher.py` の実装確認
```python
# 設定ファイル変更監視の実装確認
# なければ実装、あればスレッド安全性確認
```

### Step 13: `src/core/rate_limiter.py` の実装確認
```python
# レートリミット管理机构の確認
# スレッドセーフな実装か確認
```

### Step 14: `src/core/llm_gateway.py` の実装確認
```python
# 複数のLLMプロバイダー抽象化の実装確認
# Gemini / GPT等のprovider切替機能確認
```

### Step 15: `src/core/container.py` のDI設定確認
```python
# AppContainer の wire() 設定確認
# 各プロバイダーのライフサイクル確認
```

### Step 16: キャッシュ・並行処理の統合テスト
```bash
# 10並列リクエストを投げて race condition が発生しないか確認
```

---

## Phase 3: Streamlit実験的APIの置換 (Step 17-24)

### Step 17: `st.experimental_async` の使用箇所を調査
```bash
grep -r "experimental_async" streamlit_app/
```

### Step 18: `ensure_backend_available` の非同期実装を同期版に置き換え
```python
# 現在: st.experimental_async(ensure_backend_available)
# 修正後: st.cache_data または st.cache_resource を使用
@st.cache_resource(ttl=5)
def check_backend_health():
    return ensure_backend_available_sync()
```

### Step 19: `streamlit_app/health_check.py` の実装確認
```python
# ensure_backend_available() の実装確認
# 同期版 ensure_backend_available_sync() を追加
```

### Step 20: `streamlit_app/backend_launcher.py` の実装
```python
# バックエンドサーバー自動起動機能
# subprocess でバックエンドプロセスを管理
```

### Step 21: `streamlit_app/event_bus.py` の実装
```python
# アプリ内イベントバス
# subscribe / publish メカニズム
```

### Step 22: `streamlit_app/background.py` の実装確認
```python
# バックグラウンドタスク処理の実装確認
# st.session_state との統合確認
```

### Step 23: Streamlit コンポーネントの `st.rerun()` 代替案実装
```python
# st.rerun() の代わりに st.elements.form.form_submit_button を使用
# または st.fragment を使用 (Streamlit 1.27+)
```

### Step 24: Streamlit バージョン互換性テスト
```bash
# 異なるStreamlitバージョンでの動作確認
# pip show streamlit でバージョン確認
```

---

## Phase 4: バックエンドserver.pyのリファクタリング (Step 25-32)

### Step 25: `src/backend/server.py` の分割計画作成
```
現在の状態: 961行の巨大ファイル
分割案:
  - routes/health.py
  - routes/tasks.py
  - routes/books.py
  - routes/plots.py
  - routes/chapters.py
  - routes/generation.py
```

### Step 26: `src/backend/routes/` パッケージの作成
```python
# src/backend/routes/__init__.py
# src/backend/routes/health.py
# src/backend/routes/tasks.py
```

### Step 27: 健康診断エンドポイントの分離
```python
# src/backend/routes/health.py
@app.get("/health")
async def health_check():
    ...
```

### Step 28: タスク管理エンドポイントの分離
```python
# src/backend/routes/tasks.py
# /tasks/{task_id}, /tasks/{task_id}/stop
```

### Step 29: 書籍管理エンドポイントの分離
```python
# src/backend/routes/books.py
# /books, /books/{book_id}
```

### Step 30: プロット管理エンドポイントの分離
```python
# src/backend/routes/plots.py
# /plots, /plots/expand, /plots/rebuild
```

### Step 31: 世代管理エンドポイントの分離
```python
# src/backend/routes/generation.py
# /writing/start, /plan/generate, /marketing/generate
```

### Step 32: `src/backend/server.py` からルート登録への移行
```python
# server.py で各ルートを include_router
from src.backend.routes import health, tasks, books, plots, generation
app.include_router(health.router)
app.include_router(tasks.router)
...
```

---

## Phase 5: CORSとセキュリティ強化 (Step 33-40)

### Step 33: CORS設定の修正
```python
# 現在: allow_origins=["*"]
# 修正後: 環境変数または設定ファイルから許可originリストを取得
allow_origins = config.allowed_origins.split(",") if config.allowed_origins else ["http://localhost:8501"]
```

### Step 34: APIキーの安全な取り扱い
```python
# api_key の平文保存問題を解決
# セッションJSONにapi_keyを保存しない
# 代わりにハッシュ化された識別子のみ保存
```

### Step 35: `src/shared/utils/errors.py` の実装確認
```python
# AppErrorHandler の実装確認
# 统一的エラー処理の確認
```

### Step 36: 入力サニタイズの実装確認
```python
# src/backend/sanitizer.py
# OutputSanitizer, ContentValidator 等確認
```

### Step 37: レートリミットmiddlewareの実装
```python
# src/backend/middleware/rate_limit.py
# from fastapi import Request, HTTPException
# @app.middleware("http") で実装
```

### Step 38: リクエストタイムアウトの設定
```python
# 各エンドポイントに timeout 設定
# default timeout: 30秒
```

### Step 39: セキュリティヘッダーの追加
```python
# X-Content-Type-Options, X-Frame-Options 等
# @app.middleware("http") で実装
```

### Step 40: セキュリティテストの実施
```bash
# CORS, XSS, CSRF 等のテスト
```

---

## Phase 6: ワークフロー・パイプライン完成 (Step 41-48)

### Step 41: `src/backend/workflows/` の実装確認
```python
# 各ワークフロータイプ確認:
# - full_auto_workflow.py
# - episode_writing_workflow.py
# - plot_expansion_workflow.py
# - plan_generation_workflow.py
# 等
```

### Step 42: `src/backend/tasks.py` の実装確認
```python
# execute_service_workflow() の実装確認
# ワークフロータイプ別の処理確認
```

### Step 43: `src/backend/engine.py` のメソッド確認
```python
# UltimateHegemonyEngine の全メソッド確認
# 未実装メソッドの実装
```

### Step 44: `src/agents/` エージェント群の実装確認
```python
# WritingAgent, PlanningAgent, MarketingAgent 等
# 未実装メソッドの実装
```

### Step 45: `src/services/` サービス層の実装確認
```python
# writing_pipeline.py, bible_service.py, plot_service.py 等
# 未実装メソッドの実装
```

### Step 46: `src/core/plugin_loader.py` の実装確認
```python
# PluginLoader.get_instance().load_all_plugins() の実装確認
# 動的機能ロードの確認
```

### Step 47: `streamlit_app/pages_config.py` の完成確認
```python
# 全タブの実装確認
# Stub 関数の実装修正
```

### Step 48: エンドツーエンド統合テスト
```bash
# 書籍作成 → プロット生成 → 小説執筆 → 監査 → エクスポート
# streamlit run streamlit_app/app.py から完全動作確認
# pytest の実行確認
```

---

## 完了条件

1. 全48ステップがエラーなく通過
2. `python -c "import streamlit_app.app"` がエラーなく完了
3. `streamlit run streamlit_app/app.py` が起動
4. `pytest` テストが通過（または既知の失敗のみ）
5. `mypy` による型チェックが通過
6. CORS設定が本番環境対応

---

## リスク・制約

- **LLM API**: Gemini API キーが必要。実APIない場合はモック利用
- **並列処理**: `asyncio` 利用箇所は Streamlit の制約あり
- **状態永続化**: `active_job` (プロキシ) はシリアライズ不可のため `exclude` 対応済み
- **インポート循環**: `src/` ↔ `streamlit_app/` 間の import 循環を随時チェック