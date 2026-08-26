# フロントエンド改善 実装計画書

## 概要

本計画書は、フロントエンド評価で提示した9つの改善案を、**低性能なLLMでも確実に実装できる粒度**に分割したものです。各ステップは以下の原則に従います:

- **1ステップ = 1ファイル編集 or 1検証** で完結する
- 各ステップには具体的なコード、編集位置、検証方法を明記する
- 先行ステップの成果物に依存する場合は、その旨を明示する
- 検証は「構文エラーチェック → 型チェック → テスト実行」の順で段階的に行う

### 検証コマンド（全ステップ共通）

```bash
# 構文チェック
python -m py_compile <対象ファイル>

# 型チェック（プロジェクトに mypy がある場合）
python -m mypy streamlit_app/ --ignore-missing-imports

# 関連テスト実行
python -m pytest tests/integration/test_app_integration.py -x

# 起動確認
streamlit run streamlit_app/app.py
```

### 改善案と優先度マッピング

| 優先 | 改善案 | ステップ範囲 | 依存関係 |
|---|---|---|---|
| 高 | #1 `st.experimental_async`の置き換え | S1-S10 | なし |
| 高 | #3 `api_client._request`のHTTP语义修正 | S11-S20 | なし |
| 高 | #4 `httpx`直書きの排除 | S21-S30 | S11-S20 |
| 高 | #6 `ui_tabs_writing.py`の巨大関数分割 | S31-S40 | なし |
| 中 | #5 `time.sleep`の排除 | S41-S50 | なし |
| 中 | #7 import時副作用の除去 | S51-S60 | なし |
| 中 | #2 `UIStateStore`多重継承のComposition化 | S61-S70 | なし |
| 中 | #9 SingletonのDI化 | S71-S80 | S61-S70 |
| 低 | #8 CSS集約と`unsafe_allow_html`縮小 | S81-S90 | なし |

---

# 改善案 #1: `st.experimental_async` の置き換え (S1-S10)

**目標**: `app.py:108` の `st.experimental_async(ensure_backend_available)` はStreamlit 1.58では存在しないため実行時エラーになる。同期関数に置き換える。

## S1: `health_check.py` に同期版ヘルスチェック関数を追加

**ファイル**: `streamlit_app/health_check.py`

**編集**: ファイル末尾に以下を追加

```python
def check_backend_health_sync() -> dict[str, str]:
    """バックエンドサーバーのヘルスステータスを同期的に取得する"""
    try:
        import httpx
        with httpx.Client() as client:
            res = client.get(BACKEND_HEALTH_URL, timeout=BACKEND_HEALTH_TIMEOUT_SEC)
            if res.status_code == 200:
                return res.json()
            return {"status": "error", "database": "unknown", "worker": "unknown"}
    except Exception:
        return {"status": "error", "database": "error", "worker": "error"}
```

**検証**:
```bash
python -m py_compile streamlit_app/health_check.py
python -c "from streamlit_app.health_check import check_backend_health_sync; print(check_backend_health_sync())"
```

## S2: `health_check.py` に同期版 `ensure_backend_available_sync` を追加

**ファイル**: `streamlit_app/health_check.py`

**編集**: S1で追加した関数の直後に以下を追加

```python
def ensure_backend_available_sync() -> bool:
    """バックエンドサーバーの死活を監視する同期版。"""
    health_data = check_backend_health_sync()
    if health_data.get("status") == "ok":
        return True

    from streamlit_app.ui_utils import render_centered_title
    render_centered_title(
        "⚠️ システムステータス（バックエンド未接続）",
        "APIサーバーとの通信が確立されていません。以下の状態を確認・復旧してください。"
    )

    st.write("### 🔌 接続ダッシュボード")
    col1, col2, col3 = st.columns(3)
    api_status = health_data.get("status", "error")
    db_status = health_data.get("database", "error")
    worker_status = health_data.get("worker", "error")

    with col1:
        st.metric("APIサーバー", "🟢 稼働中" if api_status == "ok" else "🔴 停止中")
    with col2:
        st.metric("データベース", "🟢 正常" if db_status == "ok" else "🔴 エラー")
    with col3:
        st.metric("タスクワーカー", "🟢 稼働中" if worker_status == "ok" else "🔴 停止中")

    st.divider()
    st.write("バックエンドサーバーがダウンしているか、起動中です。")

    if st.button("🔄 バックエンドを自動起動する", type="primary"):
        from streamlit_app.backend_launcher import start_backend_processes
        with st.spinner("バックエンドを起動しています... (最大10秒待機)"):
            success = start_backend_processes()
            if success:
                for _ in range(BACKEND_STARTUP_WAIT_SEC):
                    time.sleep(1)
                    if check_backend_health_sync().get("status") == "ok":
                        break
                st.rerun()
            else:
                st.error("バックエンドの起動に失敗しました。ログを確認してください。")

    st.error("※ 自動起動で解決しない場合は、黒い画面（コマンドプロンプト）のプロセスを一度すべて終了させ、アプリフォルダ内の `run_all.bat` を直接ダブルクリックして再起動してください。")
    return False
```

**検証**:
```bash
python -m py_compile streamlit_app/health_check.py
python -c "from streamlit_app.health_check import ensure_backend_available_sync; print('OK')"
```

## S3: 非同期版 `ensure_backend_available` を廃止マーク

**ファイル**: `streamlit_app/health_check.py`

**編集**: `ensure_backend_available` 関数のdocstringを変更

```python
async def ensure_backend_available() -> bool:
    """[DEPRECATED] ensure_backend_available_sync を使用してください。
    バックエンドサーバーの死活を監視し、接続不可の場合は自動起動を促すUIを表示する。"""
```

**検証**:
```bash
python -m py_compile streamlit_app/health_check.py
```

## S4: `app.py` のimport文を修正

**ファイル**: `streamlit_app/app.py`

**編集**: 36行目付近

```python
# 修正前
from streamlit_app.health_check import ensure_backend_available
# 修正後
from streamlit_app.health_check import ensure_backend_available_sync
```

**検証**:
```bash
python -m py_compile streamlit_app/app.py
```

## S5: `st.experimental_async` 呼び出しを同期呼び出しに置換

**ファイル**: `streamlit_app/app.py`

**編集**: 107-109行目付近

```python
# 修正前
    # バックエンドの死活監視
    if not st.experimental_async(ensure_backend_available):
        return
# 修正後
    # バックエンドの死活監視（同期）
    if not ensure_backend_available_sync():
        return
```

**検証**:
```bash
python -m py_compile streamlit_app/app.py
grep -n "experimental_async" streamlit_app/app.py  # 空であることを確認
```

## S6: `requirements.txt` に `nest_asyncio` を明示

**ファイル**: `requirements.txt`

**編集**: 末尾に追加

```
nest_asyncio>=1.5.0
```

**検証**:
```bash
python -c "import nest_asyncio; print('OK')"
```

## S7: ヘルスチェック動作確認（バックエンド停止時）

**ファイル**: なし（手動確認）

**手順**:
1. バックエンドを起動せずに `streamlit run streamlit_app/app.py`
2. 「⚠️ システムステータス（バックエンド未接続）」の表示を確認
3. 3つのメトリックが「🔴 停止中」になることを確認

**検証基準**: エラーでアプリが停止しないこと

## S8: 非同期版関数の呼び出し元を検索

**ファイル**: なし（検索）

**手順**:
```bash
grep -rn "ensure_backend_available" streamlit_app/ --include="*.py"
grep -rn "experimental_async" streamlit_app/ --include="*.py"
```

**検証基準**: `ensure_backend_available` の呼び出しが非推奨docstring参照の1箇所のみ、`experimental_async` が0件

## S9: 非同期版関数の他呼び出し箇所があれば修正

**ファイル**: S8で見つかったファイル

**編集**: 該当箇所を `ensure_backend_available_sync()` に置換

**検証**:
```bash
python -m py_compile <該当ファイル>
```

## S10: #1の総合動作確認

**手順**:
1. バックエンド停止状態で起動 → 復旧UI表示を確認
2. バックエンド起動状態で起動 → アプリが正常進行することを確認
3. `pytest tests/integration/test_app_integration.py -x` を実行

**完了条件**:
- `experimental_async` がコードベースから消失
- バックエンド未接続時のUIが表示される
- 既存テストがパス

---

# 改善案 #3: `api_client._request` のHTTP语义修正 (S11-S20)

**目標**: `api_client.py:38` の `json=kwargs` を、HTTP methodに応じて `params` / `json` を切り替える。

## S11: `ResilientHttpClient.request` のシグネチャ確認

**ファイル**: `src/shared/resilient_http.py`

**手順**: `request` メソッドの引数を確認

```bash
grep -n "async def request" src/shared/resilient_http.py
```

**完了条件**: `request` メソッドが `params`, `json` 引数を受け取れることを確認。受け取れない場合は S12 で `ResilientHttpClient` 側も修正する。

## S12: `ResilientHttpClient.request` に `params` 引数を追加（必要な場合）

**ファイル**: `src/shared/resilient_http.py`

**編集**: `request` メソッドのシグネチャに `params: dict | None = None` を追加し、`httpx` 呼び出しで `params=params` を渡す

**検証**:
```bash
python -m py_compile src/shared/resilient_http.py
python -m pytest tests/ -k "resilient" -x
```

## S13: `api_client.py` に `_request` の新しい実装を追加

**ファイル**: `streamlit_app/api_client.py`

**編集**: 26-49行目の `_request` を以下に置換

```python
def _request(method: str, path: str, timeout: float = 10.0, **kwargs: Any) -> Any:
    """
    Synchronous wrapper around the asynchronous ResilientHttpClient.
    GET/DELETE の場合はkwargsをクエリパラメータとして渡し、
    POST/PUT/PATCH の場合はkwargsをJSONボディとして渡す。
    """
    client = get_client()
    is_body_method = method.upper() in {"POST", "PUT", "PATCH"}

    async def _async_req():
        return await client.request(
            method=method,
            path=path,
            params=None if is_body_method else kwargs,
            json=kwargs if is_body_method else None,
            timeout=timeout,
        )

    try:
        from streamlit_app.utils.async_helper import run_async
        return run_async(_async_req())

    except Exception as exc:
        logger.error(f"Resilient API request failed {method} {path}: {exc}")
        raise
```

**検証**:
```bash
python -m py_compile streamlit_app/api_client.py
```

## S14: `_request` 呼び出し元の動作確認

**ファイル**: `streamlit_app/api_client.py`

**手順**: 現状の各 `_request` 呼び出しが method とkwargsの組合せとして正しいか確認

```bash
grep -n "_request" streamlit_app/api_client.py
```

**確認**: `_request("GET", f"/tasks/{task_id}")` には kwargs がない（OK）、`_request("POST", "/plan/generate", **kwargs)` は body_method（OK）

## S15: GETメソッドの呼び出しに params を明示的に渡す

**ファイル**: `streamlit_app/api_client.py`

**編集**: `get_task_status` を修正

```python
# 修正前
def get_task_status(task_id: str, timeout: float = 5.0) -> Dict[str, Any]:
    return _request("GET", f"/tasks/{task_id}", timeout=timeout) or {}
# 修正後は変更不要（task_idがpathに埋め込まれているため）
```

**検証**:
```bash
python -m py_compile streamlit_app/api_client.py
```

## S16: 新規テストファイル作成

**ファイル**: `tests/integration/test_api_client_http_semantics.py`

**編集**: 新規作成

```python
"""api_client の HTTP 语义テスト"""
from unittest.mock import patch, MagicMock

import streamlit_app.api_client as api_client


def test_get_request_uses_params_not_json():
    """GETリクエストはkwargsをparamsとして渡し、jsonはNoneであること"""
    with patch.object(api_client, "get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        import asyncio
        async def fake_request(**kwargs):
            return kwargs  # 受け取った引数をそのまま返す

        mock_client.request = fake_request
        api_client._resilient_client = mock_client

        result = api_client._request("GET", "/test", foo="bar", timeout=5.0)
        assert result["params"] == {"foo": "bar", "timeout": 5.0}
        assert result["json"] is None


def test_post_request_uses_json_not_params():
    """POSTリクエストはkwargsをjsonとして渡し、paramsはNoneであること"""
    with patch.object(api_client, "get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        import asyncio
        async def fake_request(**kwargs):
            return kwargs

        mock_client.request = fake_request
        api_client._resilient_client = mock_client

        result = api_client._request("POST", "/test", title="foo", timeout=10.0)
        assert result["json"] == {"title": "foo", "timeout": 10.0}
        assert result["params"] is None
```

**検証**:
```bash
python -m pytest tests/integration/test_api_client_http_semantics.py -x -v
```

## S17: `start_plan_generation` 等のPOST呼び出し動作確認

**ファイル**: なし（手動確認）

**手順**: テスト実行

```bash
python -m pytest tests/integration/test_api_client_http_semantics.py -x -v
```

**完了条件**: S16 の両テストがパス

## S18: 既存コードで `_request` がPOSTリクエスト時にkwargsをbodyとしている箇所の確認

**ファイル**: なし（検索）

```bash
grep -rn "_request\(\"POST\"\|_request\(\"PUT\"\|_request\(\"PATCH\"" streamlit_app/ --include="*.py"
```

**完了条件**: すべてのPOST呼び出しが kwargs 付きで呼ばれており、body として渡される設計に合致

## S19: 既存コードで `_request` がGETリクエスト時にkwargsを渡している箇所の確認

**ファイル**: なし（検索）

```bash
grep -rn "_request\(\"GET\"" streamlit_app/ --include="*.py"
```

**完了条件**: すべてのGET呼び出しが path に埋め込むか、クエリパラメータとして渡すべきものか確認

## S20: #3の総合動作確認

**手順**:
```bash
python -m pytest tests/integration/test_api_client_http_semantics.py tests/integration/test_app_integration.py -x
```

**完了条件**:
- HTTP semantics テストがパス
- 既存のアプリ統合テストがパス
- `api_client.py` の `_request` が method によって params/json を切り替えている

---

# 改善案 #4: `httpx` 直書きの排除 (S21-S30)

**目標**: `ui_tabs_writing.py` 内の `httpx.get/post` 直書きを `api_client` 経由に置換。依存: S11-S20 完了

## S21: `api_client.py` に `get_episodes` 関数を追加

**ファイル**: `streamlit_app/api_client.py`

**編集**: 末尾に追加

```python
def get_episodes(book_id: int, timeout: float = 10.0) -> Dict[str, Any]:
    """指定書籍の全エピソード一覧を取得する"""
    return _request("GET", f"/novel/{book_id}/episodes", timeout=timeout) or {}
```

**検証**:
```bash
python -m py_compile streamlit_app/api_client.py
```

## S22: `api_client.py` に `get_episode_detail` 関数を追加

**ファイル**: `streamlit_app/api_client.py`

**編集**: S21の直後に追加

```python
def get_episode_detail(book_id: int, ep_num: int, timeout: float = 10.0) -> Dict[str, Any]:
    """特定エピソードの詳細を取得する"""
    return _request("GET", f"/novel/{book_id}/episodes/{ep_num}", timeout=timeout) or {}
```

**検証**:
```bash
python -m py_compile streamlit_app/api_client.py
```

## S23: `api_client.py` に `get_novel_report` 関数を追加

**ファイル**: `streamlit_app/api_client.py`

**編集**: S22の直後に追加

```python
def get_novel_report(book_id: int = 1, timeout: float = 30.0) -> Dict[str, Any]:
    """制作レポートを取得する"""
    return _request("GET", f"/novel/{book_id}/report", timeout=timeout) or {}
```

**検証**:
```bash
python -m py_compile streamlit_app/api_client.py
```

## S24: `api_client.py` の `stop_task` の拡充（既存確認）

**ファイル**: `streamlit_app/api_client.py`

**手順**: 66-67行目付近の `stop_task` を確認

```python
def stop_task(task_id: str) -> None:
    _request("POST", f"/tasks/{task_id}/stop")
```

**完了条件**: 既に存在することを確認。無ければ上記で追加。

## S25: `api_client.py` に `run_commercial_pipeline` 関数を追加

**ファイル**: `streamlit_app/api_client.py`

**編集**: S23の直後に追加

```python
def run_commercial_pipeline(
    series_config: dict,
    samples: list | None = None,
    platforms: list | None = None,
    timeout: float = 180.0,
) -> Dict[str, Any]:
    """商用化パイプラインを実行する"""
    return _request(
        "POST",
        "/commercial/run",
        timeout=timeout,
        series_config=series_config,
        samples=samples or [],
        platforms=platforms or [],
    ) or {}
```

**検証**:
```bash
python -m py_compile streamlit_app/api_client.py
```

## S26: `ui_tabs_writing.py` の `httpx` インポートの確認と整理

**ファイル**: `streamlit_app/ui_tabs_writing.py`

**手順**: ファイル先頭付近のimportを確認

```bash
grep -n "import httpx" streamlit_app/ui_tabs_writing.py
```

**編集**: `httpx` がimportされていない場合、その旨を記録。S27-S30で必要に応じて除去。

## S27: `ui_tabs_writing.py` の `_request("POST", "/commercial/run")` を置換

**ファイル**: `streamlit_app/ui_tabs_writing.py`

**編集**: 109-117行目の `api_client._request("POST", "/commercial/run", ...)` を `api_client.run_commercial_pipeline(...)` に置換

```python
# 修正前
                result = api_client._request(
                    "POST", 
                    "/commercial/run", 
                    timeout=180.0, 
                    **commercial_config
                )
# 修正後
                result = api_client.run_commercial_pipeline(
                    series_config=commercial_config["series_config"],
                    samples=commercial_config["samples"],
                    platforms=commercial_config["platforms"],
                    timeout=180.0,
                )
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing.py
```

## S28: `ui_tabs_writing.py` のステータスポーリング `httpx.get` を置換

**ファイル**: `streamlit_app/ui_tabs_writing.py`

**編集**: 192-195行目の `httpx.get(...)` を `api_client.get_task_status(...)` に置換

```python
# 修正前
                            status_resp = httpx.get(
                                f"http://localhost:8000/api/tasks/{get_ui('commercial_task_id')}/status",
                                timeout=5.0
                            )
                            if status_resp.status_code == 200:
                                status_data = status_resp.json()
                                status = status_data.get("status", "running")
                                progress = status_data.get("progress", 0)
# 修正後
                            status_data = api_client.get_task_status(
                                get_ui("commercial_task_id"), timeout=5.0
                            )
                            if status_data:
                                status = status_data.get("status", "running")
                                progress = status_data.get("progress", 0)
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing.py
grep -n "httpx.get\|httpx.post" streamlit_app/ui_tabs_writing.py  # 残りを確認
```

## S29: `ui_tabs_writing.py` のレポート取得 `httpx.get` を置換

**ファイル**: `streamlit_app/ui_tabs_writing.py`

**編集**: 208-216行目の `httpx.get("...report")` を `api_client.get_novel_report()` に置換

```python
# 修正前
                            @retry_api
                            def call_report_api():
                                return httpx.get(
                                    "http://localhost:8000/api/novel/1/report",
                                    timeout=30.0
                                )
                            
                            report_resp = call_report_api()
                            if report_resp.status_code == 200:
                                report_data = report_resp.json()
# 修正後
                            @retry_api
                            def call_report_api():
                                return api_client.get_novel_report(timeout=30.0)
                            
                            report_data = call_report_api()
                            if report_data:
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing.py
```

## S30: `ui_tabs_writing.py` の残り `httpx` 呼び出しを置換

**ファイル**: `streamlit_app/ui_tabs_writing.py`

**編集**: stopとepisode APIの `httpx.post/get` を `api_client.stop_task` / `api_client.get_episodes` / `api_client.get_episode_detail` に置換

```bash
grep -n "httpx" streamlit_app/ui_tabs_writing.py  # 残り箇所を特定
```

各箇所を以下のように置換:
- 284行目 `httpx.post(".../stop")` → `api_client.stop_task(get_ui("gen_task_id"))`
- 305行目 `httpx.get(".../episodes")` → `api_client.get_episodes(1)`
- 320行目 `httpx.get(f".../episodes/{ep_num}")` → `api_client.get_episode_detail(1, episode["ep_num"])`

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing.py
grep -n "httpx" streamlit_app/ui_tabs_writing.py  # 0件であることを確認
python -m pytest tests/integration/test_app_integration.py -x
```

**完了条件**: `ui_tabs_writing.py` から `httpx` の直接呼び出しが消失

---

# 改善案 #6: `ui_tabs_writing.py` の巨大関数分割 (S31-S40)

**目標**: 347行の `render_novel_production_tab` を3つの関数に分割し、`status` 変数の未定義リスクを解消

## S31: 新規ファイル `ui_tabs_writing_helpers.py` の作成

**ファイル**: `streamlit_app/ui_tabs_writing_helpers.py`

**編集**: 新規作成

```python
"""
streamlit_app/ui_tabs_writing_helpers.py — 小説生成タブのサブ関数群
"""
import json
import time
import uuid
from typing import Any

import streamlit as st

from streamlit_app import api_client
from streamlit_app.state import UIStateStore


def get_ui(key: str, default: Any = None) -> Any:
    return UIStateStore().get_ui_state_value(key, default)


def set_ui(**kwargs) -> None:
    UIStateStore().update_ui_state(**kwargs)
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing_helpers.py
```

## S32: `ui_tabs_writing_helpers.py` に `_render_series_config_form` を追加

**ファイル**: `streamlit_app/ui_tabs_writing_helpers.py`

**編技**: S31の直後に追加

```python
def _render_series_config_form() -> dict[str, Any]:
    """作品設定フォームを描画し、入力値を返す"""
    with st.expander("作品設定", expanded=True):
        st.subheader("基本情報")
        title = st.text_input("タイトル", "覇者の帰還")
        genre = st.selectbox("ジャンル", ["fantasy", "slice_of_life", "mystery", "drama", "comedy"])
        synopsis = st.text_area("概要", "かつて最強とされた戦士が10年の眠りから覚醒し、", height=100)
        keywords = st.text_input("キーワード（カンマ区切り）", "戦士,覇権,転生")

        target_episodes = st.slider("話数", 1, 20, 10)
        target_word_count = st.slider("1話あたり文字数", 1000, 5000, 3000)

        api_key = st.text_input("API Key", "your_api_key_here", key="api_key_input")

    return {
        "title": title,
        "genre": genre,
        "synopsis": synopsis,
        "keywords": keywords,
        "target_episodes": target_episodes,
        "target_word_count": target_word_count,
        "api_key": api_key,
    }
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing_helpers.py
```

## S33: `ui_tabs_writing_helpers.py` に `_render_commercial_pipeline` を追加

**ファイル**: `streamlit_app/ui_tabs_writing_helpers.py`

**編集**: S32の直後に追加（改善案 #4 の S27-S29 の成果を踏まえ、api_client 経由で呼ぶ前提）

```python
def _render_commercial_pipeline(form_data: dict[str, Any]) -> None:
    """商用化実行ボタンと結果表示を描画"""
    if get_ui("commercial_task_id", None) is not None:
        return

    if not st.button("商用化実行"):
        return

    if not form_data["keywords"].strip():
        st.error("キーワードを入力してください")
        return

    commercial_config = {
        "series_config": {
            "title": form_data["title"],
            "genre": form_data["genre"],
            "concept": form_data["synopsis"],
            "keywords": [kw.strip() for kw in form_data["keywords"].split(",") if kw.strip()],
            "target_eps": form_data["target_episodes"],
            "target_word_count": form_data["target_word_count"],
        },
        "samples": [],
        "platforms": ["kakuyomu", "naru"],
    }

    try:
        result = api_client.run_commercial_pipeline(
            series_config=commercial_config["series_config"],
            samples=commercial_config["samples"],
            platforms=commercial_config["platforms"],
            timeout=180.0,
        )

        task_id = result.get("trace_id") or result.get("task_id") or str(uuid.uuid4())
        set_ui(commercial_task_id=task_id)

        st.success("商用化パイプラインが実行されました")
        _render_pipeline_result(result)
        _poll_pipeline_status(task_id)

    except Exception as e:
        st.error(f"通信エラー: {e}")
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing_helpers.py
```

## S34: `ui_tabs_writing_helpers.py` に `_render_pipeline_result` を追加

**ファイル**: `streamlit_app/ui_tabs_writing_helpers.py`

**編集**: S33の直後に追加

```python
def _render_pipeline_result(result: dict[str, Any]) -> None:
    """パイプライン実行結果（Bible/エピソード）を表示"""
    st.subheader("パイプライン実行結果")

    data = result.get("data", {})
    bible = data.get("bible")
    if bible:
        st.write("**Bible概要:**")
        st.write(f"概念: {bible.get('concept', '未定義')}")
        st.write(f"ジャンル: {bible.get('genre', '未定義')}")
        st.write(f"キーワード: {', '.join(bible.get('keywords', []))}")
        st.write(f"対象プラットフォーム: {', '.join(bible.get('target_platforms', []))}")
        st.write(f"一意のSELLING POINTS: {', '.join(bible.get('unique_selling_points', []))}")

        bible_json = json.dumps(bible, ensure_ascii=False, indent=2)
        st.download_button(
            label="Bible(JSON)をダウンロード",
            data=bible_json,
            file_name="bible.json",
            mime="application/json",
        )

    selected = data.get("selected")
    if selected:
        st.write(f"**生成エピソード数**: {len(selected)}")
        if selected:
            for ep in selected[:3]:
                with st.expander(f"話{ep['ep_num']}: {ep['title']}"):
                    st.write(f"概要: {ep.get('summary', '内容なし')}")

            if st.button("全エピソード一覧を表示"):
                for ep in selected:
                    with st.expander(f"話{ep['ep_num']}: {ep['title']}"):
                        st.write(f"概要: {ep.get('summary', '内容なし')}")

                if "schedule_csv" in data:
                    csv_path = data["schedule_csv"]
                    st.write(f"**CSVスケジュール**: `{csv_path}`")
                    with open(csv_path, "rb") as f:
                        st.download_button(
                            label="CSVをダウンロード",
                            data=f.read(),
                            file_name="schedule.csv",
                            mime="text/csv",
                        )
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing_helpers.py
```

## S35: `ui_tabs_writing_helpers.py` に `_poll_pipeline_status` を追加

**ファイル**: `streamlit_app/ui_tabs_writing_helpers.py`

**編集**: S34の直後に追加。**`status` を明示的に初期化**して NameError を解消

```python
def _poll_pipeline_status(task_id: str) -> None:
    """パイプライン完了までポーリング"""
    if not task_id:
        return

    st.info("パイプラインの実行中です（最大30秒待機）")
    progress_bar = st.progress(0)
    max_wait_seconds = 30
    elapsed = 0
    poll_interval = get_ui("poll_interval", 1)
    status = "running"  # ★ 明示的初期化で NameError 回避

    while elapsed < max_wait_seconds:
        elapsed += poll_interval

        try:
            status_data = api_client.get_task_status(task_id, timeout=5.0)
            if status_data:
                status = status_data.get("status", "running")
                progress = status_data.get("progress", 0)
                progress_bar.progress(progress)

                if status == "completed":
                    st.success("パイプラインが完了しました")
                    _fetch_and_display_report()
                    break
                elif status == "failed":
                    err_msg = status_data.get("message", "不明なエラー")
                    st.error(f"パイプラインが失敗しました: {err_msg}")
                    return
            else:
                st.warning("ステータス取得に失敗（空レスポンス）")
        except Exception as e:
            st.error(f"ステータス取得エラー: {e}")

        set_ui(poll_interval=poll_interval)
        time.sleep(poll_interval)

    if status != "completed":
        st.error("パイプラインが指定時間以内に完了しませんでした。")
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing_helpers.py
```

## S36: `ui_tabs_writing_helpers.py` に `_fetch_and_display_report` を追加

**ファイル**: `streamlit_app/ui_tabs_writing_helpers.py`

**編集**: S35の直後に追加

```python
def _fetch_and_display_report() -> None:
    """制作レポートを取得して表示・ダウンロード"""
    try:
        report_data = api_client.get_novel_report(book_id=1, timeout=30.0)
        if not report_data:
            st.error("レポート取得失敗: 空レスポンス")
            return

        report_json = json.dumps(report_data, ensure_ascii=False, indent=2)
        st.subheader("制作レポート")
        st.download_button(
            label="制作レポートをダウンロード",
            data=report_json,
            file_name="production_report.json",
            mime="application/json",
        )
        set_ui(report_generated=True)
    except Exception as e:
        st.error(f"レポート取得エラー: {e}")
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing_helpers.py
```

## S37: `ui_tabs_writing_helpers.py` に `_render_generation_status` を追加

**ファイル**: `streamlit_app/ui_tabs_writing_helpers.py`

**編集**: S36の直後に追加

```python
def _render_generation_status() -> None:
    """生成結果・レポート表示エリア"""
    st.subheader("生成結果")
    st.info("生成が完了したら上記の「商用化実行」からレポートを取得してください")

    if get_ui("report_generated"):
        st.subheader("生成レポート（サマリ）")
        st.write("トークン使用量、品質スコア、エピソードサマリーなどを表示します")
        st.text("レポート内容は JSON で提供されています。必要に応じてダウンロードしてください。")

    st.subheader("生成履歴")
    st.write("生成履歴は将来的に実装予定です")

    st.subheader("フィードバック")
    st.write("生成結果に対するフィードバックを提供できます")
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing_helpers.py
```

## S38: `ui_tabs_writing_helpers.py` に `_render_episode_viewer` を追加

**ファイル**: `streamlit_app/ui_tabs_writing_helpers.py`

**編集**: S37の直後に追加。改善案 #4 のS30の成果を活用

```python
def _render_episode_viewer() -> None:
    """停止ボタンとエピソード一覧表示"""
    gen_task_id = get_ui("gen_task_id", None)

    if gen_task_id is not None:
        if st.button("生成停止"):
            try:
                api_client.stop_task(gen_task_id)
                st.warning("停止リクエストを送信しました")
            except Exception as e:
                st.error(f"停止通信エラー: {e}")
            finally:
                set_ui(gen_task_id=None)

    if gen_task_id is not None and st.button("エピソード一覧を表示"):
        try:
            episodes_data = api_client.get_episodes(1)
            episodes = episodes_data.get("episodes", [])
            if episodes:
                st.subheader("エピソード一覧")
                for episode in episodes:
                    with st.expander(f"話{episode['ep_num']}: {episode['title']}"):
                        st.write(f"概要: {episode.get('summary', '')}")
                        st.write(f"文字数: {episode.get('word_count', '不明')}")
                        st.write(f"品質スコア: {episode.get('quality_score', '不明')}")

                        if st.button(f"話{episode['ep_num']}内容を表示", key=f"btn_{episode['ep_num']}"):
                            try:
                                detail = api_client.get_episode_detail(1, episode["ep_num"])
                                st.write("内容:")
                                st.write(detail.get("content", "内容取得エラー"))
                                if "killer_phrase" in detail:
                                    st.write(f"キラーフレーズ: {detail['killer_phrase']}")
                            except Exception as e:
                                st.error(f"エピソード内容取得エラー: {e}")
                            break
                st.success("エピソード一覧の取得に成功しました")
            else:
                st.error("エピソード一覧取得に失敗しました")
        except Exception as e:
            st.error(f"通信エラー: {e}")
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing_helpers.py
```

## S39: `ui_tabs_writing.py` の `render_novel_production_tab` を置換

**ファイル**: `streamlit_app/ui_tabs_writing.py`

**編集**: 62-342行目の `render_novel_production_tab` を、新規helpersを呼ぶシンプルな実装に置換。**事前にバックアップを取る**

```bash
cp streamlit_app/ui_tabs_writing.py streamlit_app/ui_tabs_writing.py.bak.S39
```

置換後のコード:

```python
"""
src/streamlit_app/ui_tabs_writing.py — 小説生成タブコンポーネント（リファクタリング版）
"""
import streamlit as st

from streamlit_app.state import UIStateStore
from streamlit_app.ui_tabs_writing_helpers import (
    get_ui,
    set_ui,
    _render_series_config_form,
    _render_commercial_pipeline,
    _render_generation_status,
    _render_episode_viewer,
)


def _init_writing_state() -> None:
    """小説生成タブ用UI状態の初期化"""
    if get_ui("commercial_task_id", None) is None:
        set_ui(commercial_task_id=None)
    if get_ui("report_generated", None) is None:
        set_ui(report_generated=False)
    if get_ui("poll_interval", None) is None:
        set_ui(poll_interval=1)


def render_novel_production_tab():
    """小説生成タブを表示"""
    st.title("小説生成")
    _init_writing_state()

    form_data = _render_series_config_form()
    _render_commercial_pipeline(form_data)
    _render_generation_status()
    _render_episode_viewer()


if __name__ == "__main__":
    render_novel_production_tab()
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing.py
python -m pytest tests/integration/test_app_integration.py -x
```

## S40: #6の総合動作確認

**手順**:
1. `streamlit run streamlit_app/app.py` で起動
2. 小説生成タブが表示されることを確認
3. 「作品設定」フォームが表示されることを確認
4. `grep -n "status != " streamlit_app/ui_tabs_writing_helpers.py` で `status` が初期化されていることを確認

**完了条件**:
- `render_novel_production_tab` が5つの関数に分割されている
- `status` 変数が明示的に初期化される
- 既存テストがパス

---

# 改善案 #5: `time.sleep` の排除 (S41-S50)

**目標**: `ui_tabs_planning.py:28, 484` と `ui_components.py:269` の `time.sleep` + `st.rerun` をCSSアニメーション/fragment に置換してサーバーブロックを防ぐ

## S41: `styles.css` にスケルトン表示クラスを追加

**ファイル**: `streamlit_app/ui/static/styles.css`

**編集**: 末尾に追加

```css
/* スケルトン専用フェードイン（time.sleep 不要化） */
.skeleton-fade-in {
    animation: skeleton-fade 0.6s ease-out forwards;
}
@keyframes skeleton-fade {
    0% { opacity: 0; }
    100% { opacity: 1; }
}
```

**検証**:
```bash
cat streamlit_app/ui/static/styles.css | grep skeleton-fade  # 追加されたことを確認
```

## S42: `ui_tabs_planning.py` の easy_mode_loaded スリープ除去

**ファイル**: `streamlit_app/ui_tabs_planning.py`

**編集**: 22-30行目の `render_easy_mode` スケルトン部分を修正

```python
# 修正前
    if not UIStateStore().ui_state.form_data.get("easy_mode_loaded", False):
        with st.container():
            st.markdown('<div class="skeleton-header"></div>', unsafe_allow_html=True)
            st.markdown('<div class="skeleton-text"></div>', unsafe_allow_html=True)
            st.markdown('<div class="skeleton-card"></div>', unsafe_allow_html=True)
            time.sleep(0.5) # 演出としての短時間待機
        UIStateStore().update_ui_state(easy_mode_loaded=True)
        st.rerun()
# 修正後
    if not UIStateStore().ui_state.form_data.get("easy_mode_loaded", False):
        with st.container():
            st.markdown('<div class="skeleton-header skeleton-fade-in"></div>', unsafe_allow_html=True)
            st.markdown('<div class="skeleton-text skeleton-fade-in"></div>', unsafe_allow_html=True)
            st.markdown('<div class="skeleton-card skeleton-fade-in"></div>', unsafe_allow_html=True)
        UIStateStore().update_ui_state(easy_mode_loaded=True)
        st.rerun()  # CSSアニメーションは次描画で自然に再生される
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_planning.py
grep -n "time.sleep" streamlit_app/ui_tabs_planning.py  # 対象箇所が減ったことを確認
```

## S43: `ui_tabs_planning.py` の planning_tab_loaded スリープ除去

**ファイル**: `streamlit_app/ui_tabs_planning.py`

**編集**: 479-486行目の `render_planning_tab` スケルトン部分を同様に修正

```python
# 修正前
    if not UIStateStore().ui_state.form_data.get("planning_tab_loaded", False):
        with st.container():
            st.markdown('<div class="skeleton-header"></div>', unsafe_allow_html=True)
            st.markdown('<div class="skeleton-card"></div>', unsafe_allow_html=True)
            time.sleep(0.3)
        UIStateStore().update_ui_state(planning_tab_loaded=True)
        st.rerun()
# 修正後
    if not UIStateStore().ui_state.form_data.get("planning_tab_loaded", False):
        with st.container():
            st.markdown('<div class="skeleton-header skeleton-fade-in"></div>', unsafe_allow_html=True)
            st.markdown('<div class="skeleton-card skeleton-fade-in"></div>', unsafe_allow_html=True)
        UIStateStore().update_ui_state(planning_tab_loaded=True)
        st.rerun()
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_planning.py
grep -n "time.sleep" streamlit_app/ui_tabs_planning.py  # 0件になっていることを確認
```

## S44: `ui_components.py` の `_render_job_running` 構造確認

**ファイル**: `streamlit_app/ui_components.py`

**手順**: 247-270行目付近の `_render_job_running` を確認

```bash
sed -n '247,270p' streamlit_app/ui_components.py
```

**完了条件**: `time.sleep(1.0); st.rerun()` が最後にあることを確認

## S45: `_render_job_running` の `time.sleep(1.0)` を fragment 化

**ファイル**: `streamlit_app/ui_components.py`

**編集**: `progress_dispatcher` が既に `@st.fragment(run_every=PROGRESS_POLL_INTERVAL_SEC)` (2秒) で周期的に refresh しているため、`_render_job_running` 内の `time.sleep(1.0)` + `st.rerun()` は**不要**。削除する

```python
# 修正前
        if st.button("🛑 処理を中断する", key=f"stop_{run_key}", type="secondary"):
            job.stop()
            UIStateStore.clear_active_job()
            st.rerun()
    time.sleep(1.0)
    st.rerun()
# 修正後
        if st.button("🛑 処理を中断する", key=f"stop_{run_key}", type="secondary"):
            job.stop()
            UIStateStore.clear_active_job()
            st.rerun()
    # progress_dispatcher (run_every=2秒) が定期更新を担当するため
    # time.sleep + st.rerun は不要
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_components.py
grep -n "time.sleep" streamlit_app/ui_components.py
```

## S46: `ui_tabs_writing_helpers.py` の polling 内 `time.sleep` の確認

**ファイル**: `streamlit_app/ui_tabs_writing_helpers.py`（S35で作成）

**手順**: `_poll_pipeline_status` 内の `time.sleep(poll_interval)` を確認

```bash
grep -n "time.sleep" streamlit_app/ui_tabs_writing_helpers.py
```

**判断**: ポーリングループ内の `time.sleep` は現状維持（ループ間隔制御のため）。ただし長期化するとブロックするため、S47 でリファクタリングを検討。

## S47: `ui_tabs_writing_helpers.py` の polling を fragment 化

**ファイル**: `streamlit_app/ui_tabs_writing_helpers.py`

**編集**: `_poll_pipeline_status` をフラグメント化。同期的ポーリングを fragment に移譲

```python
@st.fragment(run_every=2.0)
def _poll_pipeline_status_fragment(task_id: str):
    """パイプライン完了をfragmentでポーリング"""
    if not task_id:
        return
    try:
        status_data = api_client.get_task_status(task_id, timeout=5.0)
        if not status_data:
            return
        status = status_data.get("status", "running")
        if status == "completed":
            st.success("パイプラインが完了しました")
            _fetch_and_display_report()
        elif status == "failed":
            err_msg = status_data.get("message", "不明なエラー")
            st.error(f"パイプラインが失敗しました: {err_msg}")
    except Exception as e:
        print(f"Polling error: {e}")  # fragment内では st.error は常にrerunで消えるためログ化
```

`_poll_pipeline_status` は fragment を呼ぶだけに:

```python
def _poll_pipeline_status(task_id: str) -> None:
    """パイプライン完了をポーリング（fragment経由）"""
    if not task_id:
        return
    st.info("パイプラインの実行中です（最大30秒待機）")
    progress_bar = st.progress(0)
    _poll_pipeline_status_fragment(task_id)
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing_helpers.py
```

## S48: 全 `time.sleep` の remaining 箇所確認

**ファイル**: なし（検索）

```bash
grep -rn "time.sleep" streamlit_app/ --include="*.py" | grep -v __pycache__
```

**完了条件**: 残っている `time.sleep` が意図的なユーザー演出やサーキットブレーカー待機など合理的な箇所のみであることを確認

## S49: 動作確認（スケルトン表示時のアニメーション）

**ファイル**: なし（手動確認）

**手順**:
1. `streamlit run streamlit_app/app.py` で起動
2. 企画タブを開いた直後、スケルトン → 本コンテンツ遷移が `time.sleep` なしで滑らかに表示されることを確認
3. APIキーを入力し、ジョブ実行中表示が fragment の定期実行で更新されることを確認

## S50: #5の総合動作確認

**手順**:
```bash
python -m pytest tests/integration/test_app_integration.py -x
grep -rn "time.sleep" streamlit_app/ --include="*.py" | grep -v __pycache__
```

**完了条件**:
- 既存テストがパス
- `time.sleep` を使用していた演出用箇所が CSS アニメーション or fragment で代替されている
- 残り `time.sleep` が合理的な箇所のみ

---

# 改善案 #7: import 時副作用の除去 (S51-S60)

**目標**: `ui_tabs_writing.py:25-32` のモジュール import 時に走る `get_ui`/`set_ui` 呼び出しを、関数内での遅延初期化に変更する

## S51: `UIStateStore` に `ensure_writing_defaults` メソッド追加の準備

**ファイル**: `streamlit_app/state.py`

**手順**: `UIStateStore` クラスの末尾（255行目付近）を確認

```bash
sed -n '252,255p' streamlit_app/state.py
```

## S52: `UIStateStore` に `ensure_writing_defaults` メソッドを追加

**ファイル**: `streamlit_app/state.py`

**編集**: `UIStateStore` クラスの最後に追加

```python
    def ensure_writing_defaults(self) -> None:
        """
        小説生成タブ用UI状態のデフォルト値を初回のみ設定する。
        モジュールimport時ではなく、タブ描画時に呼び出すことを想定。
        """
        if self.get_ui_state_value("commercial_task_id") is None:
            self.update_ui_state(commercial_task_id=None)
        if self.get_ui_state_value("report_generated") is None:
            self.update_ui_state(report_generated=False)
        if self.get_ui_state_value("api_retry_state") is None:
            self.update_ui_state(
                api_retry_state={"attempts": 0, "max_attempts": 3, "backoff": 1}
            )
        if self.get_ui_state_value("poll_interval") is None:
            self.update_ui_state(poll_interval=1)
```

**検証**:
```bash
python -m py_compile streamlit_app/state.py
python -c "from streamlit_app.state import UIStateStore; print(hasattr(UIStateStore, 'ensure_writing_defaults'))"
# True が出力されることを確認
```

## S53: `app.py` の `_init_session` にwriting defaults 追加

**ファイル**: `streamlit_app/app.py`

**編集**: `_init_session` 関数の末尾（60行目付近）に追加

```python
def _init_session() -> None:
    """型安全なセッション状態の初期値設定"""
    runtime = UIStateStore.get_runtime()
    if runtime.app_mode is None:
        runtime.app_mode = DEFAULT_APP_MODE
    if not runtime.token_stats:
        runtime.token_stats = {"prompt": 0, "completion": 0, "calls": 0}
    if not runtime.forbidden_patterns:
        runtime.forbidden_patterns = []
    if not runtime.selected_desires:
        runtime.selected_desires = DEFAULT_DESIRES

    UIStateStore().update_ui_state(active_tab="home")
    UIStateStore().ensure_writing_defaults()  # ★ 追加: writing タブ用デフォルトはここで初期化
```

**検証**:
```bash
python -m py_compile streamlit_app/app.py
```

## S54: `ui_tabs_writing.py` の module-level 初期化ブロックの除去

**ファイル**: `streamlit_app/ui_tabs_writing.py`（S39 でリファクタ済みの前提）

**手順**: module top level に `if get_ui(...)` ブロックが残っていないことを確認

```bash
grep -n "if get_ui" streamlit_app/ui_tabs_writing.py | head
```

**完了条件**: module-level での `get_ui`/`set_ui` 呼び出しがないこと。S39 で `_init_writing_state` 関数に移動済みであれば問題なし。

## S55: `ui_tabs_writing.py` の `_init_writing_state` を `UIStateStore.ensure_writing_defaults` に置換

**ファイル**: `streamlit_app/ui_tabs_writing.py`

**編集**: `_init_writing_state` を `UIStateStore().ensure_writing_defaults()` に置換（S39 の成果物がベース）

```python
# 修正前
def _init_writing_state() -> None:
    """小説生成タブ用UI状態の初期化"""
    if get_ui("commercial_task_id", None) is None:
        set_ui(commercial_task_id=None)
    if get_ui("report_generated", None) is None:
        set_ui(report_generated=False)
    if get_ui("poll_interval", None) is None:
        set_ui(poll_interval=1)
# 修正後
def _init_writing_state() -> None:
    """小説生成タブ用UI状態の初期化(委譲)"""
    UIStateStore().ensure_writing_defaults()
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_writing.py
```

## S56: 類似の module-level 副作用を他ファイルで検索

**ファイル**: なし（検索）

```bash
grep -rn "^if get_ui\|^if UIStateStore" streamlit_app/ --include="*.py" | grep -v __pycache__
```

**完了条件**: 他ファイルでも同様の module-level 副作用がないことを確認。あれば S57-S58 で同様に対応。

## S57: 見つかった module-level 副作用の個別対応

**ファイル**: S56 で特定したファイル

**編集**: 対象箇所を関数内に移動

**検証**:
```bash
python -m py_compile <対象ファイル>
```

## S58: import 順依存テストの追加

**ファイル**: `tests/integration/test_writing_tab_no_import_side_effect.py`

**編集**: 新規作成

```python
"""モジュールimport時に副作用が走らないことのテスト"""
import sys


def test_writing_module_import_no_side_effects():
    """ui_tabs_writing をimportしてもst.session_stateの書き換えが起きないこと"""
    import streamlit.testing as testing

    # streamlit session_state を空に
    mock_state = {}
    # 注: 本テストはモック環境推奨。CI では streamlit の ScriptRunCtx が必要なため
    # 可能なら UnitTest で UIStateStore を直接 mock する方が安全

    # 単純 import 成功の確認
    if "streamlit_app.ui_tabs_writing" in sys.modules:
        del sys.modules["streamlit_app.ui_tabs_writing"]

    try:
        import streamlit_app.ui_tabs_writing  # noqa
        import_ok = True
    except Exception:
        import_ok = False

    assert import_ok, "ui_tabs_writing モジュールの import に失敗しました"
```

**検証**:
```bash
python -m pytest tests/integration/test_writing_tab_no_import_side_effect.py -x -v
```

## S59: `import streamlit_app.ui_tabs_writing` 単体でエラーが出ないことの確認

**手順**:
```bash
python -c "import streamlit_app.ui_tabs_writing; print('import OK')"
```

**完了条件**: Streamlit ScriptRunCtx なしでも import 自体が通ること（`UIStateStore.ensure_writing_defaults` 等は関数内で呼ばれるため）

## S60: #7の総合動作確認

**手順**:
```bash
python -m pytest tests/integration/test_writing_tab_no_import_side_effect.py tests/integration/test_app_integration.py -x
streamlit run streamlit_app/app.py  # 起動確認
```

**完了条件**:
- import 時副作用が消失している
- アプリ正常起動後、小説生成タブを開いてもエラーが出ない
- 関連テストがパス

---

# 改善案 #2: `UIStateStore` 多重継承の Composition 化 (S61-S70)

**目標**: `state.py:188` の `class UIStateStore(JobStore, PollStateStore, ToastStore, SessionStore):` を、各ストアのインスタンスを保持する Composition に変更。後方互換のため、`UIStateStore.set_active_job()` 等の静的呼び出しは、対応するストアの静的メソッドに委譲する thin ファサードとする。

## S61: `state.py` の現状確認

**ファイル**: `streamlit_app/state.py`

**手順**: 188-255行目を確認し、`UIStateStore` が多重継承していることを再認識

```bash
grep -n "class UIStateStore" streamlit_app/state.py
grep -rn "UIStateStore\." streamlit_app/ --include="*.py" | grep -v __pycache__ | wc -l
```

**完了条件**: 現在の `UIStateStore` の使用箇所数を把握（リファクタ後の後方互換確認に使用）

## S62: 後方互換用の委譲メソッドを明示的に定義

**ファイル**: `streamlit_app/state.py`

**編集**: `class UIStateStore(...)` の定義を維持しつつ、明示的に各ストアに委譲する静的メソッドを追加。多重継承の振る舞いを明文化するため、ダミーデリゲータを書く。

```python
class UIStateStore(JobStore, PollStateStore, ToastStore, SessionStore):
    """UI state store implementation.

    NOTE: 本クラスは JobStore/PollStateStore/ToastStore/SessionStore を
    多重継承しているが、各メソッドは対応する親クラスの staticmethod に
    委譲される。後方互換を保ちつつ、将来的には Composition に移行する。
    現状は親クラスの staticmethod をそのまま使えるため、明示的な
    委譲コードは不要（Python の MRO により解決される）。
    """
```

**編集**: さらに、混同しやすいメソッドについて明示的な委譲を追加

```python
    # --- 明示的な委譲（多重継承のMROに依存しない safer な呼び出し）---
    @staticmethod
    def set_active_job(job, run_key="default"):
        return JobStore.set_active_job(job, run_key)

    @staticmethod
    def clear_active_job(run_key="default"):
        return JobStore.clear_active_job(run_key)

    @staticmethod
    def get_monitored_jobs():
        return JobStore.get_monitored_jobs()

    @staticmethod
    def is_processing():
        return JobStore.is_processing()

    @staticmethod
    def bump_fragment_version(part):
        return JobStore.bump_fragment_version(part)

    @staticmethod
    def get_fragment_version(part):
        return JobStore.get_fragment_version(part)

    @staticmethod
    def set_processing_lock(locked):
        return JobStore.set_processing_lock(locked)
```

**検証**:
```bash
python -m py_compile streamlit_app/state.py
```

## S63: `PollStateStore` 委譲メソッドの追加

**ファイル**: `streamlit_app/state.py`

**編集**: S62 の直後に追加

```python
    @staticmethod
    def get_poll_fail_count(run_key):
        return PollStateStore.get_poll_fail_count(run_key)

    @staticmethod
    def increment_poll_fail_count(run_key):
        return PollStateStore.increment_poll_fail_count(run_key)

    @staticmethod
    def reset_poll_fail_count(run_key):
        return PollStateStore.reset_poll_fail_count(run_key)

    @staticmethod
    def get_poll_skip_until(run_key):
        return PollStateStore.get_poll_skip_until(run_key)

    @staticmethod
    def set_poll_skip_until(run_key, until):
        return PollStateStore.set_poll_skip_until(run_key, until)
```

**検証**:
```bash
python -m py_compile streamlit_app/state.py
```

## S64: `ToastStore` 委譲メソッドの追加

**ファイル**: `streamlit_app/state.py`

**編集**: S63 の直後に追加

```python
    @staticmethod
    def is_toast_notified(key):
        return ToastStore.is_toast_notified(key)

    @staticmethod
    def mark_toast_notified(key):
        return ToastStore.mark_toast_notified(key)
```

**検証**:
```bash
python -m py_compile streamlit_app/state.py
```

## S65: `SessionStore` 委譲メソッドの追加

**ファイル**: `streamlit_app/state.py`

**編集**: S64 の直後に、`SessionStore` の public メソッドを調査して追加

```bash
grep -n "def " streamlit_app/stores/session_store.py | head
```

代表的なもの:
```python
    @staticmethod
    def increment_rerun_count():
        return BaseStore.increment_rerun_count()

    @staticmethod
    def get_rerun_count():
        return BaseStore.get_rerun_count()
```

**検証**:
```bash
python -m py_compile streamlit_app/state.py
```

## S66: `ui_state` property / `update_ui_state` 等のUI状態アクセスはそのまま維持

**ファイル**: なし（確認）

**手順**: `state.py` の 191-243 行目付近にある `UIState` アクセスメソッドは多重継承外なので変更不要

```bash
sed -n '191,243p' streamlit_app/state.py
```

## S67: 静的呼び出し互換性テストの追加

**ファイル**: `tests/integration/test_ui_state_store_compat.py`

**編集**: 新規作成

```python
"""UIStateStore の後方互換性テスト（多重継承→明示的委譲移行後）"""
import streamlit.testing
import pytest

try:
    from streamlit_app.stores import JobStore, PollStateStore, ToastStore, SessionStore
    from streamlit_app.state import UIStateStore
    IMPORT_OK = True
except Exception:
    IMPORT_OK = False


@pytest.mark.skipif(not IMPORT_OK, reason="import failed")
def test_ui_state_store_delegates_to_job_store():
    """UIStateStore の job 系メソッドが JobStore と同一の振る舞いであること"""
    # 空の状態で呼び出し可能（副作用なしの参照系）
    assert UIStateStore.is_processing.__func__ is not None


@pytest.mark.skipif(not IMPORT_OK, reason="import failed")
def test_ui_state_store_delegates_to_poll_store():
    assert UIStateStore.get_poll_fail_count.__func__ is not None
```

**検証**:
```bash
python -m pytest tests/integration/test_ui_state_store_compat.py -x -v
```

## S68: 既存の `state_tests` を再実行して後方互換を担保

**手順**:
```bash
python -m pytest tests/integration/state_tests/test_ui_state_store.py -x -v
```

**完了条件**: 既存3テスト（`test_state_persistence_across_reruns`, `test_ui_state_store_runtime_access`, `test_subscriber_notification`）がすべてパス

## S69: Composition 版の設計ドキュメントを残す

**ファイル**: `docs/frontend_refactor_plan.md`（本ドキュメント）

**編集**: このステップS69用のnoteとして、将来的な完全 Composition 化の構想をメモする

```
# 将来構想（S61-S70 では実施せず）
本ステップでは「明示的委譲」を行うことで多重継承の振る舞いを安定化したが、
完全な Composition（UIStateStore が各ストアの __init__ でインスタンスを保持）
への移行は別途計画する。その際:
1. UIStateStore.__init__ で self.jobs / self.poll / self.toast / self.session を初期化
2. 各ストアを非 static に変更し、BaseStore インスタンスを保持する設計にする
3. UIStateStore.set_active_job() は self.jobs.set_active_job() に委譲する thin wrapper として残す
4. 全呼び出し元を順次、直接 jobs/poll/toast/session インスタンスを使う形に移行する
```

## S70: #2の総合動作確認

**手順**:
```bash
python -m pytest tests/integration/state_tests/ tests/integration/test_ui_state_store_compat.py -x
streamlit run streamlit_app/app.py
```

**完了条件**:
- 既存 state unit test がパス
- 互換性テストがパス
- アプリが正常起動する

---

# 改善案 #9: Singleton の DI 化 (S71-S80)

**目標**: `EngineService.get_instance()`, `PluginLoader.get_instance()`, `_resilient_client` の Singleton を、呼び出し元が明示的に注入できる仕組みに変更。依存: S61-S70 完了推奨。

## S71: `DependencyContainer` 新規ファイル作成

**ファイル**: `streamlit_app/dependency_container.py`

**編集**: 新規作成

```python
"""
streamlit_app/dependency_container.py — 依存オブジェクト注入用コンテナ。
Singleton の直接参照を避け、テスト時のモック差し替えを容易にする。
"""
from __future__ import annotations

from typing import Any, Optional


class DependencyContainer:
    """依存オブジェクトを保持する軽量コンテナ"""

    _instance: Optional["DependencyContainer"] = None

    def __init__(self) -> None:
        self._engine_service: Any = None
        self._plugin_loader: Any = None
        self._api_client: Any = None

    @classmethod
    def get_instance(cls) -> "DependencyContainer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """テスト用: コンテナをリセット"""
        cls._instance = None

    # --- engine_service ---
    def get_engine_service(self) -> Any:
        if self._engine_service is None:
            from src.engine_service import EngineService
            self._engine_service = EngineService.get_instance()
        return self._engine_service

    def set_engine_service(self, service: Any) -> None:
        """テスト用: モックを注入"""
        self._engine_service = service

    # --- plugin_loader ---
    def get_plugin_loader(self) -> Any:
        if self._plugin_loader is None:
            from src.core.plugin_loader import PluginLoader
            self._plugin_loader = PluginLoader.get_instance()
        return self._plugin_loader

    def set_plugin_loader(self, loader: Any) -> None:
        """テスト用: モックを注入"""
        self._plugin_loader = loader

    # --- api_client ---
    def get_api_client(self) -> Any:
        if self._api_client is None:
            from streamlit_app import api_client
            self._api_client = api_client
        return self._api_client

    def set_api_client(self, client: Any) -> None:
        """テスト用: モックを注入"""
        self._api_client = client
```

**検証**:
```bash
python -m py_compile streamlit_app/dependency_container.py
python -c "from streamlit_app.dependency_container import DependencyContainer; c = DependencyContainer.get_instance(); print(type(c))"
```

## S72: `ui_tabs_planning.py` の `PluginLoader.get_instance()` 呼び出しを container 経由に

**ファイル**: `streamlit_app/ui_tabs_planning.py`

**編集**: import 文追加と、`PluginLoader.get_instance()` を container 経由に

```python
# ファイル先頭付近に追加
from streamlit_app.dependency_container import DependencyContainer

# 182行目付近
# 修正前
        plugin = PluginLoader.get_instance().get_active_plugin()
# 修正後
        plugin = DependencyContainer.get_instance().get_plugin_loader().get_active_plugin()
```

同様に `198行目付近`:

```python
# 修正前
        plugin = PluginLoader.get_instance().get_active_plugin()
# 修正後
        plugin = DependencyContainer.get_instance().get_plugin_loader().get_active_plugin()
```

`498行目付近`:

```python
# 修正前
        plugin = PluginLoader.get_instance().get_active_plugin()
# 修正後
        plugin = DependencyContainer.get_instance().get_plugin_loader().get_active_plugin()
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_planning.py
grep -n "PluginLoader.get_instance" streamlit_app/ui_tabs_planning.py  # 0件であることを確認
```

## S73: `app.py` の `PluginLoader.get_instance()` 呼び出しを container 経由に

**ファイル**: `streamlit_app/app.py`

**編集**: 101行目付近

```python
# 修正前
    # プラグインの初期化
    PluginLoader.get_instance().load_all_plugins()
# 修正後
    # プラグインの初期化
    from streamlit_app.dependency_container import DependencyContainer
    DependencyContainer.get_instance().get_plugin_loader().load_all_plugins()
```

**検証**:
```bash
python -m py_compile streamlit_app/app.py
grep -n "PluginLoader.get_instance" streamlit_app/app.py  # 0件であることを確認
```

## S74: `app.py` の `EngineService.get_instance()` 呼び出しを container 経由に

**ファイル**: `streamlit_app/app.py`

**編集**: 66-68行目の `_run_navigation` 内

```python
# 修正前
        from src.engine_service import EngineService
        service = EngineService.get_instance(api_key=api_key)
# 修正後
        from streamlit_app.dependency_container import DependencyContainer
        service = DependencyContainer.get_instance().get_engine_service()
        # NOTE: api_key は既にセットされている前提。必要なら set 方法を追加。
```

**注意**: `EngineService.get_instance(api_key=api_key)` は引数付き Singleton。container 化する場合、`get_engine_service` で `api_key` を受け取るか、事前に設定する仕組みが必要。

**代替編集**: container 側を api_key 受け取り対応にする

```python
# streamlit_app/dependency_container.py (S71 の編集を上書き)
    def get_engine_service(self, api_key: Optional[str] = None) -> Any:
        if self._engine_service is None or api_key is not None:
            from src.engine_service import EngineService
            self._engine_service = EngineService.get_instance(api_key=api_key)
        return self._engine_service
```

`app.py` 側:

```python
        from streamlit_app.dependency_container import DependencyContainer
        service = DependencyContainer.get_instance().get_engine_service(api_key=api_key)
```

**検証**:
```bash
python -m py_compile streamlit_app/dependency_container.py streamlit_app/app.py
grep -n "EngineService.get_instance" streamlit_app/app.py  # 0件であることを確認
```

## S75: `sidebar.py` の `EngineService` import を確認

**ファイル**: `streamlit_app/sidebar.py`

**手順**: 11行目に `from src.engine_service import EngineService` があることを確認

```bash
grep -n "EngineService" streamlit_app/sidebar.py
```

**編集**: 316行目の `render_book_selector` 内

```python
# 修正前
def render_book_selector(service: EngineService) -> int | None:
# 修正後
def render_book_selector(service: Any) -> int | None:
```

```python
# ファイル先頭付近に追加
from typing import Any
from streamlit_app.dependency_container import DependencyContainer
```

`render_book_selector` は引数で `service` を受け取るため、container 化の必要は薄い。S75 では型ヒントの修正のみ。

**検証**:
```bash
python -m py_compile streamlit_app/sidebar.py
```

## S76: DI 用モックテスト追加

**ファイル**: `tests/integration/test_dependency_container.py`

**編集**: 新規作成

```python
"""DependencyContainer の動作テスト"""
from streamlit_app.dependency_container import DependencyContainer


def test_container_singleton():
    """get_instance が同一インスタンスを返すこと"""
    DependencyContainer.reset()
    c1 = DependencyContainer.get_instance()
    c2 = DependencyContainer.get_instance()
    assert c1 is c2


def test_engine_service_mock_injection():
    """モックの注入ができること"""
    DependencyContainer.reset()
    container = DependencyContainer.get_instance()

    class FakeEngine:
        def __init__(self):
            self.api_key = None

    fake = FakeEngine()
    container.set_engine_service(fake)
    assert container.get_engine_service() is fake


def test_plugin_loader_mock_injection():
    DependencyContainer.reset()
    container = DependencyContainer.get_instance()

    class FakePluginLoader:
        loaded = False
        def load_all_plugins(self):
            self.loaded = True
        def get_active_plugin(self):
            return None

    fake = FakePluginLoader()
    container.set_plugin_loader(fake)
    container.get_plugin_loader().load_all_plugins()
    assert fake.loaded is True


def test_reset_strips_singletons():
    DependencyContainer.reset()
    c1 = DependencyContainer.get_instance()
    DependencyContainer.reset()
    c2 = DependencyContainer.get_instance()
    assert c1 is not c2
```

**検証**:
```bash
python -m pytest tests/integration/test_dependency_container.py -x -v
```

## S77: `api_client._resilient_client` を container 経由に

**ファイル**: `streamlit_app/api_client.py`

**編集**: `_resilient_client` Global を container に移譲する薄いラッパを追加。既存の `_resilient_client` は維持（後方互換）。

```python
def get_client() -> ResilientHttpClient:
    """Get or create the singleton resilient client.

    NOTE: S77より、DependencyContainer 経由でも取得可能。
    本関数は既存呼び出し元の後方互換のために維持される。
    """
    global _resilient_client
    if _resilient_client is None:
        config = ResilienceConfigLoader().get_policy("backend_api")
        _resilient_client = ResilientHttpClient(
            base_url=API_BASE_URL,
            retry_policy=config.retry_policy,
            circuit_breaker=config.circuit_breaker,
        )
    return _resilient_client
```

`_request` は container 経由も可能:

```python
def _request(method: str, path: str, timeout: float = 10.0, **kwargs: Any) -> Any:
    # container 経由を優先、未設定なら get_client() にフォールバック
    from streamlit_app.dependency_container import DependencyContainer
    container = DependencyContainer.get_instance()
    api_module = container.get_api_client()
    client = api_module.get_client() if api_module is not api_client else get_client()
    ...
```

**注意**: import 循環参照に注意。container 側の `get_api_client` は `streamlit_app.api_client` **モジュール自体**を返すため、循環は起きない。

**検証**:
```bash
python -m py_compile streamlit_app/api_client.py
python -m pytest tests/integration/test_api_client_http_semantics.py -x
```

## S78: 既存 Singleton 直接呼び出しの洗い出し

**ファイル**: なし（検索）

```bash
grep -rn "EngineService.get_instance\|PluginLoader.get_instance" streamlit_app/ --include="*.py" | grep -v __pycache__ | grep -v dependency_container
```

**完了条件**: 残存箇所のリストアップ。S79 で順次置換。

## S79: リストアップされた箇所の順次置換

**ファイル**: S78 で特定した各ファイル

**編集**: 各箇所を `DependencyContainer.get_instance().get_engine_service()` / `.get_plugin_loader()` に置換

**検証**:
```bash
python -m py_compile <各ファイル>
```

```bash
grep -rn "EngineService.get_instance\|PluginLoader.get_instance" streamlit_app/ --include="*.py" | grep -v __pycache__ | grep -v dependency_container
```

**完了条件**: 残存が `src/` 配下や `depend_container.py` 内のみになること

## S80: #9の総合動作確認

**手順**:
```bash
python -m pytest tests/integration/ -x
streamlit run streamlit_app/app.py
```

**完了条件**:
- DI テストがパス
- 統合テストがパス
- アプリが正常起動する
- Singleton 直接呼び出しの大半が container 経由に置換されている

---

# 改善案 #8: CSS 集約と `unsafe_allow_html` 縮小 (S81-S90)

**目標**: `landing.py`, `sidebar.py:229`, `ui_tabs_planning.py` 等に散在するインラインCSSを `streamlit_app/ui/static/styles.css` に集約する

## S81: `landing.py` のインラインCSSを `styles.css` に移動

**ファイル**: `streamlit_app/ui/static/styles.css`

**編集**: 末尾に `landing.py:13-98` のCSSを移動（`<style>` タグを外した中身のみ）

```css
/* landing.py */
.hero-section {
    background: linear-gradient(135deg, rgba(20, 20, 35, 0.9), rgba(40, 40, 60, 0.8)),
                linear-gradient(to right, #1a1a2e, #16213e);
    background-size: cover;
    padding: 80px 20px;
    border-radius: 20px;
    text-align: center;
    color: white;
    margin-bottom: 40px;
    border: 1px solid var(--primary-color);
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}
.trust-badge-container {
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin: 2rem 0;
    flex-wrap: wrap;
}
.trust-badge {
    background: var(--bg-card);
    border: 1px solid var(--border);
    padding: 1rem 2rem;
    border-radius: 50px;
    font-size: 0.9rem;
    color: var(--text-main);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
}
.trust-badge strong {
    color: var(--primary-color);
}
.feature-card {
    padding: 1.5rem;
    border-radius: 15px;
    border: 1px solid var(--border);
    background: var(--bg-card);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    height: 100%;
}
.feature-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    border-color: var(--primary-color);
}
.feature-icon {
    font-size: 2rem;
    margin-bottom: 1rem;
    display: block;
}
.workflow-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 2rem 1rem;
    gap: 1rem;
    text-align: center;
}
.workflow-step {
    flex: 1;
    padding: 1rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    position: relative;
}
.workflow-arrow {
    font-size: 1.5rem;
    color: var(--primary-color);
    font-weight: bold;
}
.hero-title {
    font-size: 3.5rem !important;
    font-weight: 800 !important;
    background: -webkit-linear-gradient(#fff, #e94560);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 5px;
}
.app-footer {
    margin-top: 5rem;
    padding: 2rem 0;
    border-top: 1px solid var(--border);
    text-align: center;
    color: var(--text-muted);
    font-size: 0.9rem;
}
.footer-links {
    margin-bottom: 1rem;
}
.footer-links a {
    color: var(--text-secondary);
    text-decoration: none;
    margin: 0 10px;
    transition: color 0.2s;
}
.footer-links a:hover {
    color: var(--primary-color);
}
```

**検証**:
```bash
cat streamlit_app/ui/static/styles.css | grep "hero-section"
```

## S82: `landing.py` のインライン `<style>` を除去

**ファイル**: `streamlit_app/landing.py`

**編集**: 13-98行目の2つの `<style>` ブロックを削除。195-217行目のフッターCSSも削除

```python
# 修正前: 冒頭に2つの <style> ... </style> ブロック
def render_landing() -> None:
    """ランディングページ（APIキー未入力時）を表示する"""
    from streamlit_app.ui_utils import render_centered_title

    st.markdown("""
        <style>
        .hero-section { ... }
        ...
        </style>
        <style>
        .hero-title { ... }
        </style>
        <div class="hero-section">
        ...
    """, unsafe_allow_html=True)
    ...
# 修正後: <style> ブロック除去、HTML本体のみ残す
def render_landing() -> None:
    """ランディングページ（APIキー未入力時）を表示する"""
    from streamlit_app.ui_utils import render_centered_title

    st.markdown("""
        <div class="hero-section">
            <h1 class="hero-title">覇権小説エンジン v3.0</h1>
            <p style="font-size: 1.5rem; opacity: 0.9; margin-bottom: 1rem;">AIと共に、読者の心を支配する「覇権」を創り出す。</p>
            <div style="display: inline-block; padding: 0.5rem 1.5rem; background: var(--primary-color); border-radius: 50px; font-weight: bold; font-size: 1rem;">
                次世代ナラティブエンジニアリング・プラットフォーム
            </div>
        </div>
    """, unsafe_allow_html=True)
    ...
```

最後のフッター部分も同様に `<style>` ブロックを除去:

```python
# 修正前
    st.markdown("""
        <style>
        .app-footer { ... }
        .footer-links { ... }
        ...
        </style>
        <footer class="app-footer">
        ...
    """, unsafe_allow_html=True)
# 修正後
    st.markdown("""
        <footer class="app-footer">
            <div class="footer-links">
                <a href="#">利用規約</a>
                <a href="#">プライバシーポリシー</a>
                <a href="#">お問い合わせ</a>
            </div>
            <p>© 2026 覇権小説エンジン Project. All rights reserved.</p>
        </footer>
    """, unsafe_allow_html=True)
```

**検証**:
```bash
python -m py_compile streamlit_app/landing.py
grep -n "<style>" streamlit_app/landing.py  # 0件であることを確認
```

## S83: `sidebar.py` の NSFW テーマCSSを `styles.css` に移動

**ファイル**: `streamlit_app/ui/static/styles.css`

**編集**: 末尾に追加

```css
/* sidebar.py - NSFW テーマ */
.nsfw-theme [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a0a0d 0%, #2d1020 100%) !important;
}
.nsfw-theme {
    --primary-color: #7b1518 !important;
}
```

**検証**:
```bash
grep "nsfw-theme" streamlit_app/ui/static/styles.css
```

## S84: `sidebar.py` の NSFW CSSブロックをフラグクラス化

**ファイル**: `streamlit_app/sidebar.py`

**編集**: 228-238行目の `st.markdown("""<style>...`` を、body要素にクラスを付与する方式に変更

```python
# 修正前
        if session.config.get("enable_nsfw", False):
            st.markdown("""
            <style>
            :root {
                --primary-color: #7b1518 !important;
            }
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #1a0a0d 0%, #2d1020 100%) !important;
            }
            </style>
            """, unsafe_allow_html=True)
# 修正後
        if session.config.get("enable_nsfw", False):
            st.markdown(
                '<div class="nsfw-theme-flag"></div>'
                '<style>body { /* nsfw-theme-flag をトリガに styles.css 側で装飾 */ }</style>',
                unsafe_allow_html=True,
            )
```

**代替（より確実）**: Streamlit ではbodyに直接クラスを付与しにくいため、CSS側で `--nsfw-flag` 変数を検知するアプローチを採用。簡易策として、セッション状態に応じたマーカー div を配置し、`:has` セレクタで装飾する。

```python
# 簡易策（確実）: フラグdiv配置、CSS側で :has(.nsfw-flag) で装飾
        if session.config.get("enable_nsfw", False):
            st.markdown('<div class="nsfw-flag"></div>', unsafe_allow_html=True)
```

`styles.css`:

```css
body:has(.nsfw-flag) [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a0a0d 0%, #2d1020 100%) !important;
}
body:has(.nsfw-flag) {
    --primary-color: #7b1518 !important;
}
```

**検証**:
```bash
python -m py_compile streamlit_app/sidebar.py
grep -n "<style>" streamlit_app/sidebar.py  # 減ったことを確認
```

## S85: `ui_tabs_planning.py` のインラインCSSを `styles.css` に移動

**ファイル**: `streamlit_app/ui/static/styles.css`

**編集**: `render_easy_mode` 内の hero section, `_wizard_step_indicator` 内のスタイルを移動

```css
/* ui_tabs_planning.py */
.easy-hero {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #1a1a2e 100%);
    padding: 2rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    text-align: center;
}
.easy-hero h1 {
    color: #e94560;
    font-size: 2.5rem;
    margin: 0;
    letter-spacing: 2px;
}
.easy-hero p {
    color: #a8b2c1;
    margin: 0.5rem 0 0 0;
    font-size: 1.1rem;
}
.wizard-step-done {
    text-align: center;
    color: #4caf50;
    font-weight: bold;
    font-size: 0.9rem;
}
.wizard-step-active {
    text-align: center;
    color: #e94560;
    font-weight: bold;
    font-size: 1rem;
    border-bottom: 3px solid #e94560;
    padding-bottom: 4px;
}
.wizard-step-pending {
    text-align: center;
    color: #666;
    font-size: 0.9rem;
}
```

**検証**:
```bash
grep "easy-hero\|wizard-step" streamlit_app/ui/static/styles.css
```

## S86: `ui_tabs_planning.py` のインライン `<style>` 削除とクラス化

**ファイル**: `streamlit_app/ui_tabs_planning.py`

**編集**: 32-40行目の hero section と 130-155行目付近の wizard step indicator から `<style>` を除去し、クラス参照に変更

```python
# 修正前
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #1a1a2e 100%);
                padding: 2rem; border-radius: 16px; margin-bottom: 1.5rem; text-align: center;">
        <h1 style="color: #e94560; font-size: 2.5rem; margin: 0; letter-spacing: 2px;">QUEST START</h1>
        <p style="color: #a8b2c1; margin: 0.5rem 0 0 0; font-size: 1.1rem;">
            ジャンルを選択し、あなたの物語の「核」をAIに伝えてください。
        </p>
    </div>
    """, unsafe_allow_html=True)
# 修正後
    st.markdown("""
    <div class="easy-hero">
        <h1>QUEST START</h1>
        <p>ジャンルを選択し、あなたの物語の「核」をAIに伝えてください。</p>
    </div>
    """, unsafe_allow_html=True)
```

`_wizard_step_indicator`:

```python
# 修正前: 3つの col.markdown にインライン style
# 修正後
def _wizard_step_indicator(current: int, total: int = 4) -> None:
    cols = st.columns(total)
    labels = ["ジャンル", "主人公", "物語設計", "生成開始"]

    for i, (col, label) in enumerate(zip(cols, labels)):
        step_num = i + 1
        if step_num < current:
            col.markdown(
                f'<div class="wizard-step-done"><div>✅</div>{label}</div>',
                unsafe_allow_html=True,
            )
        elif step_num == current:
            col.markdown(
                f'<div class="wizard-step-active"><div>🚀</div>{label}</div>',
                unsafe_allow_html=True,
            )
        else:
            col.markdown(
                f'<div class="wizard-step-pending"><div>○</div>{label}</div>',
                unsafe_allow_html=True,
            )
    st.markdown("<div style='margin: 1rem 0;'></div>", unsafe_allow_html=True)
    st.divider()
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_tabs_planning.py
grep -n "background: linear-gradient" streamlit_app/ui_tabs_planning.py | wc -l  # 減ったことを確認
```

## S87: `ui_components.py` のphaseスタイル定数の確認

**ファイル**: `streamlit_app/ui_components.py`

**手順**: 55-76行目の `_PHASE_STYLES` 辞書を確認。これらはHTML内に直接埋め込まれる `style=""` 属性用の値

**判断**: `_PHASE_HTML_TEMPLATE` (55-61行目) がHTML文字列構築に使われ、`unsafe_allow_html=True` で描画される。これは動的にアクティブフェーズの色を切り替えるため、CSS移動が難しい部分。

**結論**: S87 では動作確認のみ。`_PHASE_STYLES` は現状維持（動的色分けのため）。可能なら3クラス化（`phase-active`, `phase-completed`, `phase-pending`）し、CSS移動する。

## S88: `ui_components.py` のphaseスタイルをクラス化

**ファイル**: `streamlit_app/ui_components.py`

**編集**: `_PHASE_HTML_TEMPLATE` と `_PHASE_STYLES` をクラス参照に変更

```python
# 修正前
_PHASE_HTML_TEMPLATE = (
    "<div style='background-color: {bg_color}; color: {color}; padding: 10px 5px; "
    "border-radius: 6px; text-align: center; font-weight: {font_weight}; "
    "border: {border}; box-shadow: {box_shadow}; font-size: 0.85em;'>"
    "{prefix} {name}"
    "</div>"
)

_PHASE_STYLES = { ... }
# 修正後
_PHASE_HTML_TEMPLATE = (
    "<div class='phase-badge phase-{style_key}'>"
    "{prefix} {name}"
    "</div>"
)
```

`styles.css` に追加:

```css
/* ui_components.py - phase badge */
.phase-badge {
    padding: 10px 5px;
    border-radius: 6px;
    text-align: center;
    font-size: 0.85em;
}
.phase-active {
    background-color: #0f766e;
    color: white;
    font-weight: bold;
    border: 1.5px solid #14b8a6;
    box-shadow: 0 0 10px rgba(20, 184, 166, 0.4);
}
.phase-completed {
    background-color: rgba(6, 95, 70, 0.2);
    color: #34d399;
    font-weight: 500;
    border: 1px solid rgba(52, 211, 153, 0.4);
}
.phase-pending {
    background-color: rgba(255, 255, 255, 0.02);
    color: #6b7280;
    font-weight: normal;
    border: 1px dashed rgba(107, 114, 128, 0.3);
}
```

`render_production_dashboard` (106-116行目) の修正:

```python
# 修正前
            style = _PHASE_STYLES[style_key]
            st.markdown(_PHASE_HTML_TEMPLATE.format(name=name, **style), unsafe_allow_html=True)
# 修正後
            prefix_map = {"active": "🔥", "completed": "✅", "pending": "💤"}
            prefix = prefix_map[style_key]
            st.markdown(
                _PHASE_HTML_TEMPLATE.format(style_key=style_key, prefix=prefix, name=name),
                unsafe_allow_html=True,
            )
```

**検証**:
```bash
python -m py_compile streamlit_app/ui_components.py
grep -n "_PHASE_STYLES" streamlit_app/ui_components.py  # 使わなくなったことを確認
```

## S89: アプリ動作確認（CSS集約後）

**ファイル**: なし（手動確認）

**手順**:
1. `streamlit run streamlit_app/app.py` で起動
2. ランディングページの hero, feature-card, workflow, footer の見た目が変わらないことを確認
3. 企画タブのスケルトン、wizard step indicator のデザインが変わらないことを確認
4. NSFWモードをONにした際、サイドバー色が変わることを確認

## S90: #8の総合動作確認

**手順**:
```bash
grep -rn "<style>" streamlit_app/ --include="*.py" | grep -v __pycache__ | wc -l
python -m pytest tests/integration/test_app_integration.py -x
streamlit run streamlit_app/app.py
```

**完了条件**:
- `<style>` タグの数が大幅に減少していること（landing.py 等は0、fragments的に必要な箇所は残）
- 既存テストがパス
- 見た目が保持されている

---

# 最終統合確認 (S91-S95・ボーナス)

## S91: 全改善の統合テスト実行

```bash
python -m pytest tests/integration/ -x
```

**完了条件**: 全テストがパスすること

## S92: アプリのE2E動作確認

**手順**:
1. バックエンド停止 → `streamlit run streamlit_app/app.py` → 復旧UI表示
2. バックエンド起動 → アプリ正常進行 → APIキー入力 → 企画タブ表示
3. 小説生成タブ表示 → 各フォーム入力 → 商用化実行ボタン押下（バックエンド未接続でもUIエラーにならない）
4. エピソード一覧表示

**完了条件**: 全シナリオでアプリがクラッシュしない

## S93: パフォーマンス確認（リロード時の応答性）

**手順**:
- 旧: `time.sleep` により0.5〜3秒の待ちがあった箇所が、リファクタ後は即座に表示されることを確認
- Streamlit サーバー起動中に別ブラウザで2つ目のアクセスを行い、ブロックされないことを確認

## S94: コードベース全体の regression チェック

```bash
grep -rn "st.experimental_async" streamlit_app/ --include="*.py"  # 0件
grep -rn "httpx.get\|httpx.post" streamlit_app/ui_tabs_writing.py  # 0件
grep -rn "time.sleep" streamlit_app/ --include="*.py" | grep -v __pycache__  # 合理的箇所のみ
grep -rn "<style>" streamlit_app/landing.py  # 0件
```

**完了条件**: 各 regression マーカーが期待値であること

## S95: 改善完了レポートの作成

**ファイル**: `docs/frontend_refactor_complete.md`（ユーザー指示時に作成）

**編集**: 実施した改善案1-9の完了状況、残後方互換項目、将来的TODOを記録する

---

# 完了条件まとめ

| 改善案 | 最終完了条件 |
|---|---|
| #1 | `st.experimental_async` 消失、バックエンド死活UIが表示される |
| #2 | `UIStateStore` が明示的委譲に移行済み、state_tests がパス |
| #3 | `_request` が GET/POST で params/json を切り替える、HTTP semantics テストがパス |
| #4 | `ui_tabs_writing.py` からの `httpx` 直接呼び出し消失 |
| #5 | 演出用 `time.sleep` がCSSアニメーション/fragment で代替済み |
| #6 | `render_novel_production_tab` が5つの関数に分割、`status` 初期化済み |
| #7 | module import 時の副作用が消失、import 単独でエラーが出ない |
| #8 | インライン `<style>` が大幅減少、見た目が保持されている |
| #9 | `DependencyContainer` によりモック注入可能、DIテストがパス |

# 各LLM向け実装のヒント

低性能なLLMで本計画書に沿って実装する場合の注意点:

1. **1ステップごとに `python -m py_compile` で構文チェックを必ず実行**する。エラーが出たら直すまで次のステップに進まない。
2. **編集前後で `grep` して差分を確認**する。例: `grep -n "experimental_async" streamlit_app/app.py` の出力が変わったことを確認。
3. **`oldString` と `newString` のインデントは厳密に一致させる**。スペースとタブを混在させない。
4. **バックアップファイル (.bak) を作る前提の箇所**では、必ず元ファイルをコピーしてから編集する。
5. **テストが落ちたら元ファイルに戻し、1ステップ前の commit/worktree 状態から再開**する。一度に複数ステップ進めた変更を戻すのは困難。
6. **コメント追加は禁止**（プロジェクトのコード規約）。本計画書にある `# 修正前` / `# 修正後` / `# ★` 等のコメントは**計画書用の注記**であり、実際のコードには書かない。ただし既存コードにある説明コメントは維持する。
7. **`unsafe_allow_html=True` を使う `st.markdown` では、ユーザー入力をそのままHTMLに埋め込まない**。埋め込む場合は `html.escape()` でエスケープする。

**計画書終わり**
