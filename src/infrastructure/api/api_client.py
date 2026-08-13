"""
src/infrastructure/api/api_client.py — 非同期対応APIクライアント

バックエンドAPIへHTTPアクセスするためのクライアント層。

- 同期エントリポイント ``get_client`` / ``_request`` は、テスト
  (``tests/integration/test_api_client_http_semantics.py``) との互換性を
  維持するため、HTTPセマンティクス (GET/DELETE/HEAD -> params,
  POST/PUT/PATCH -> json) に従ってリクエストを振り分ける。
- 非同期APIメソッド (``list_books`` 等) は ``_async_request`` を介して
  共有の ``httpx.AsyncClient`` を使い、接続を再利用する。
"""

import asyncio
import inspect
import logging
import os
import threading
from typing import Any, Dict, List, Optional

import httpx

from src.core.exceptions import APIError as APIException

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 定数管理 (マジックナンバーの排除)
# -----------------------------------------------------------------------------
DEFAULT_API_BASE_URL = "http://localhost:8200/api"
SYNC_REQUEST_TIMEOUT = 10.0
ASYNC_REQUEST_TIMEOUT = 30.0

_api_base_url_env = os.environ.get("API_BASE_URL")
API_BASE_URL = _api_base_url_env if _api_base_url_env else DEFAULT_API_BASE_URL

# HTTP メソッドがリクエストボディ(json)を使うか Queryパラメータ(params)を使うか。
# HTTP セマンティクスに基づき、GET/DELETE/HEAD は params、
# POST/PUT/PATCH は json で kwargs を渡す。
_PARAMS_METHODS = {"GET", "DELETE", "HEAD"}
_JSON_METHODS = {"POST", "PUT", "PATCH"}


# -----------------------------------------------------------------------------
# 同期版クライアント (tests/integration/test_api_client_http_semantics.py 互換)
# -----------------------------------------------------------------------------
# ref: テストは `get_client`/`_request`/`_resilient_client` の同期APIを想定。
#      非同期版 `_async_request` とは別に、HTTPセマンティクスを検証可能な
#      同期エントリポイントを提供する。


def get_client() -> httpx.Client:
    """共有HTTPクライアントを取得する (テスト用の同期エントリポイント)。

    プロセス内で再利用可能な ``httpx.Client`` を遅延生成して返す。
    すでに ``_resilient_client`` が設定されている場合はそれをそのまま返す
    (テストからモック差し替え可能にするため)。

    Returns:
        生成済みまたは共有の ``httpx.Client`` インスタンス。
    """
    global _resilient_client
    if _resilient_client is not None:
        return _resilient_client
    _resilient_client = httpx.Client(timeout=ASYNC_REQUEST_TIMEOUT)
    return _resilient_client


# 共有クライアント。テストから直接代入可能なモジュール属性。
_resilient_client: Optional[httpx.Client] = None


def _resolve_if_coroutine(result: Any) -> Any:
    """コルーチンなら同期的に解決してその値を返す。

    テスト等で ``client.request`` が async 関数としてモックされるケースや、
    同期クライアントの ``request`` がコルーチンを返す実装へ対応するため、
    戻り値がコルーチンなら同期的に待機して実体を取り出す。

    Args:
        result: ``client.request`` の戻り値 (``Response`` またはコルーチン)。

    Returns:
        解決済みの戻り値。コルーチンでなければそのまま返す。
    """
    if not inspect.iscoroutine(result):
        return result

    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop is not None and running_loop.is_running():
        # 既に実行中のイベントループ内からは await できないため、
        # 別スレッドで新規ループを立てて解決する。
        result_box: Dict[str, Any] = {}

        def _runner() -> None:
            new_loop = asyncio.new_event_loop()
            try:
                result_box["value"] = new_loop.run_until_complete(result)
            except Exception as exc:  # noqa: BLE001
                result_box["error"] = exc
            finally:
                new_loop.close()

        worker = threading.Thread(target=_runner)
        worker.start()
        worker.join()
        if "error" in result_box:
            raise result_box["error"]
        return result_box["value"]

    # 実行中のループがない通常の同期コンテキスト。
    return asyncio.run(result)


def _request(method: str, path: str, timeout: float = SYNC_REQUEST_TIMEOUT, **kwargs: Any) -> Any:
    """HTTPセマンティクスに従って kwargs を振り分けてリクエストを発行する。

    - GET / DELETE / HEAD : kwargs を ``params`` として送信 (``json=None``)
    - POST / PUT / PATCH  : kwargs を ``json`` として送信 (``params=None``)

    Args:
        method: HTTPメソッド。
        path: API_BASE_URL からの相対パス。
        timeout: リクエストタイムアウト(秒)。
        **kwargs: メソッドに応じて params または json に振り分けられる。

    Returns:
        クライアントの ``request()`` が返す結果 (``Response`` または
        モックがコルーチンを返した場合はその解決値)。
    """
    client = get_client()
    url = f"{API_BASE_URL}{path}"
    method_upper = (method or "").upper()

    if method_upper in _JSON_METHODS:
        params: Optional[Dict[str, Any]] = None
        json_body: Optional[Dict[str, Any]] = dict(kwargs) if kwargs else None
    else:
        # GET/DELETE/HEAD および未知メソッドは query params として扱う。
        params = dict(kwargs) if kwargs else {}
        json_body = None

    logger.debug("API sync request %s %s (timeout=%.1f)", method_upper, url, timeout)
    result = client.request(
        method_upper,
        url,
        params=params,
        json=json_body,
        timeout=timeout,
    )
    return _resolve_if_coroutine(result)


# -----------------------------------------------------------------------------
# 非同期クライアント (接続再利用)
# -----------------------------------------------------------------------------

# 共有の非同期クライアント。遅延生成し、同じ接続プールを再利用する。
_async_client: Optional[httpx.AsyncClient] = None


def _get_async_client() -> httpx.AsyncClient:
    """共有の ``httpx.AsyncClient`` を取得・遅延生成する。"""
    global _async_client
    if _async_client is None or _async_client.is_closed:
        _async_client = httpx.AsyncClient(timeout=ASYNC_REQUEST_TIMEOUT)
    return _async_client


async def close_async_client() -> None:
    """共有の非同期クライアントをクローズする。"""
    global _async_client
    if _async_client is not None and not _async_client.is_closed:
        await _async_client.aclose()
    _async_client = None


async def _async_request(method: str, url: str, **kwargs: Any) -> Optional[httpx.Response]:
    """内部的な非同期リクエスト処理。

    UI層への直接的な依存 (st.toast など) を排除し、例外で通知する。
    共有の ``httpx.AsyncClient`` を使い、接続を再利用する。

    Args:
        method: HTTPメソッド。
        url: 絶対URL。
        **kwargs: ``httpx.AsyncClient.request`` にそのまま渡される。

    Returns:
        成功時は ``httpx.Response``。通信不可等の場合は ``APIException`` を送出。

    Raises:
        APIException: 接続エラー/HTTPエラー/予期せぬエラー時に送出。
    """
    # 監査ログの取得はDIコンテナ経由で行う想定 (後でリファクタリング)
    audit_logger = None
    try:
        from src.infrastructure.proxy import get_di_container

        container = get_di_container()
        audit_logger = container.audit_logger()
    except Exception:
        pass

    try:
        timeout = kwargs.pop("timeout", ASYNC_REQUEST_TIMEOUT)

        client = _get_async_client()
        logger.debug("API async request %s %s (timeout=%.1f)", method, url, timeout)
        response = await client.request(method, url, timeout=timeout, **kwargs)
        response.raise_for_status()

        # 成功ログの記録
        if audit_logger:
            audit_logger.log(
                user_id="system_user",
                action=f"API_{method}_{url.split('/')[-1]}",
                resource_id=url,
                status="SUCCESS",
                details={
                    "params": kwargs.get("params", {}),
                    "payload": kwargs.get("json", {}),
                },
            )
        return response
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.error(f"Connection error requesting {method} {url}: {e}")
        raise APIException(
            f"バックエンドAPIサーバーに接続できません。 (詳細: {e})", recoverable=False
        )
    except httpx.HTTPStatusError as e:
        if audit_logger:
            audit_logger.log(
                user_id="system_user",
                action=f"API_{method}_{url.split('/')[-1]}",
                resource_id=url,
                status="HTTP_ERROR",
                details={"status_code": e.response.status_code, "error": str(e)},
            )
        logger.error(f"HTTP error requesting {method} {url}: {e}")
        raise APIException(f"APIエラーが発生しました: {e.response.status_code}", detail=str(e))
    except Exception as e:
        if audit_logger:
            audit_logger.log(
                user_id="system_user",
                action=f"API_{method}_{url.split('/')[-1]}",
                resource_id=url,
                status="SYSTEM_ERROR",
                details={"error": str(e)},
            )
        logger.error(f"Unexpected error requesting {method} {url}: {e}")
        raise APIException(f"予期せぬエラーが発生しました: {str(e)}")


def close_client() -> None:
    """同期・非同期クライアントをクローズしリソースを解放する。

    アプリケーション終了時に呼び出すことを想定。実行中のイベントループが
    ないコンテキストでの呼び出しを前提とする。
    """
    global _resilient_client
    if _resilient_client is not None:
        _resilient_client.close()
        _resilient_client = None

    if _async_client is not None:
        try:
            asyncio.run(close_async_client())
        except RuntimeError:
            # 実行中ループがある環境では非同期クローズを呼び出し側で行う。
            logger.warning("close_client: 実行中のイベントループがあるため非同期クライアントをここではクローズしませんでした。")


# -----------------------------------------------------------------------------
# APIメソッド定義 (すべてasync)
# -----------------------------------------------------------------------------


async def list_books() -> List[Dict[str, Any]]:
    """登録されている本の一覧を取得する。"""
    response = await _async_request("GET", f"{API_BASE_URL}/books")
    return response.json() if response else []


async def get_book(book_id: int) -> Optional[Dict[str, Any]]:
    """指定した本の詳細を取得する。"""
    response = await _async_request("GET", f"{API_BASE_URL}/books/{book_id}")
    return response.json() if response else None


async def delete_book(book_id: int) -> bool:
    """指定した本を削除する。"""
    response = await _async_request("DELETE", f"{API_BASE_URL}/books/{book_id}")
    return True if response else False


async def get_plots(book_id: int) -> List[Dict[str, Any]]:
    """指定した本のプロット一覧を取得する。"""
    response = await _async_request("GET", f"{API_BASE_URL}/plots/{book_id}")
    return response.json() if response else []


async def get_chapters(book_id: int) -> List[Dict[str, Any]]:
    """指定した本のチャプター一覧を取得する。"""
    response = await _async_request("GET", f"{API_BASE_URL}/chapters/{book_id}")
    return response.json() if response else []


async def get_bible(book_id: int) -> Dict[str, Any]:
    """指定した本のバイブル(設定集)を取得する。"""
    response = await _async_request("GET", f"{API_BASE_URL}/bibles/{book_id}")
    return response.json() if response else {}


async def get_opt_history(book_id: int) -> List[Dict[str, Any]]:
    """指定した本の最適化履歴を取得する。"""
    response = await _async_request("GET", f"{API_BASE_URL}/optimization_history/{book_id}")
    return response.json() if response else []


async def get_task_status(task_id: str, timeout: float = ASYNC_REQUEST_TIMEOUT) -> Dict[str, Any]:
    """非同期タスクのステータスを取得する。

    Args:
        task_id: ステータスを確認するタスクID。
        timeout: ステータス取得リクエストのタイムアウト(秒)。

    Returns:
        タスク状態を表す辞書。通信エラー時は ``is_running=False`` 等の
        エラー情報を含む辞書を返す。
    """
    try:
        response = await _async_request(
            "GET", f"{API_BASE_URL}/tasks/{task_id}/status", timeout=timeout
        )
        return (
            response.json()
            if response
            else {
                "is_running": False,
                "message": "通信エラー",
                "logs": [],
                "error": "バックエンドとの通信エラー",
            }
        )
    except Exception as e:
        logger.error("Error getting task status: %s", e)
        return {
            "is_running": False,
            "message": "通信エラー",
            "logs": [],
            "error": f"バックエンドとの通信エラー、またはタスクが消失しました。\n詳細: {str(e)}",
        }


async def stop_task(task_id: str) -> bool:
    """実行中のタスクを停止する。"""
    response = await _async_request("POST", f"{API_BASE_URL}/tasks/{task_id}/stop")
    return True if response else False


async def generate_easy(
    api_key: str,
    config: dict,
    genre: str,
    keywords: str,
    archetype_key: str,
    target_eps: int,
    initial_limit: int,
    word_count: int,
    concept: str,
    tone_vibe: float,
) -> Optional[str]:
    """かんたん生成モードでタスクを起動し、task_id を返す。"""
    payload = {
        "api_key": api_key,
        "config": config,
        "genre": genre,
        "keywords": keywords,
        "archetype_key": archetype_key,
        "target_eps": target_eps,
        "initial_limit": initial_limit,
        "word_count": word_count,
        "concept": concept,
        "tone_vibe": tone_vibe,
    }
    response = await _async_request("POST", f"{API_BASE_URL}/easy_mode/generate", json=payload)
    return response.json().get("task_id") if response else None


async def generate_episodes(
    api_key: str,
    config: dict,
    book_id: int,
    write_from: int,
    write_to: int,
    passion: float,
    word_count: int,
    do_refine: bool,
    env_state: Dict[str, str],
    pipeline_mode: bool,
) -> Optional[str]:
    """エピソード(章)を生成するタスクを起動し、task_id を返す。"""
    payload = {
        "api_key": api_key,
        "config": config,
        "book_id": book_id,
        "write_from": write_from,
        "write_to": write_to,
        "passion": passion,
        "word_count": word_count,
        "do_refine": do_refine,
        "env_state": env_state,
        "pipeline_mode": pipeline_mode,
    }
    response = await _async_request("POST", f"{API_BASE_URL}/episodes/generate", json=payload)
    return response.json().get("task_id") if response else None


async def plan_generation(api_key: str, config: dict, params: Dict[str, Any]) -> Optional[str]:
    """プロットの計画生成タスクを起動し、task_id を返す。"""
    payload = {"api_key": api_key, "config": config, "params": params}
    response = await _async_request("POST", f"{API_BASE_URL}/plots/plan_generation", json=payload)
    return response.json().get("task_id") if response else None


async def retry_failed_episodes(
    api_key: str, config: dict, book_id: int, passion: float, word_count: int
) -> Optional[str]:
    """失敗したエピソードを再試行するタスクを起動し、task_id を返す。"""
    payload = {
        "api_key": api_key,
        "config": config,
        "book_id": book_id,
        "passion": passion,
        "word_count": word_count,
    }
    response = await _async_request("POST", f"{API_BASE_URL}/episodes/retry_failed", json=payload)
    return response.json().get("task_id") if response else None


async def expand_plots(
    api_key: str, config: dict, book_id: int, gen_from: int, gen_to: int
) -> Optional[str]:
    """プロットを拡張するタスクを起動し、task_id を返す。"""
    payload = {
        "api_key": api_key,
        "config": config,
        "book_id": book_id,
        "gen_from": gen_from,
        "gen_to": gen_to,
    }
    response = await _async_request("POST", f"{API_BASE_URL}/plots/expand", json=payload)
    return response.json().get("task_id") if response else None


async def rebuild_plots(api_key: str, config: dict, params: Dict[str, Any]) -> Optional[str]:
    """プロットを再構築するタスクを起動し、task_id を返す。"""
    payload = {"api_key": api_key, "config": config, "params": params}
    response = await _async_request("POST", f"{API_BASE_URL}/plots/rebuild", json=payload)
    return response.json().get("task_id") if response else None


async def critique_optimize(api_key: str, config: dict, book_id: int) -> Optional[str]:
    """批評最適化タスクを起動し、task_id を返す。"""
    payload = {"api_key": api_key, "config": config, "book_id": book_id}
    response = await _async_request("POST", f"{API_BASE_URL}/critique/optimize", json=payload)
    return response.json().get("task_id") if response else None


async def import_chapter(
    api_key: str, book_id: int, ep_num: int, import_text: str, do_refine: bool
) -> Optional[str]:
    """チャプターを外部テキストから取り込むタスクを起動し、task_id を返す。"""
    payload = {
        "api_key": api_key,
        "book_id": book_id,
        "ep_num": ep_num,
        "import_text": import_text,
        "do_refine": do_refine,
    }
    response = await _async_request("POST", f"{API_BASE_URL}/chapters/import", json=payload)
    return response.json().get("task_id") if response else None


async def generate_marketing(api_key: str, book_id: int, latest_ep: int) -> Optional[str]:
    """マーケティング素材生成タスクを起動し、task_id を返す。"""
    payload = {"api_key": api_key, "book_id": book_id, "latest_ep": latest_ep}
    response = await _async_request("POST", f"{API_BASE_URL}/marketing/generate", json=payload)
    return response.json().get("task_id") if response else None


async def analyze_style_dna(api_key: str, sample: str) -> Dict[str, Any]:
    """文体DNAを解析し、結果の辞書を返す。"""
    payload = {"api_key": api_key, "sample": sample}
    response = await _async_request("POST", f"{API_BASE_URL}/marketing/analyze_style", json=payload)
    return response.json() if response else {}


async def create_chapter(
    book_id: int,
    ep_num: int,
    title: str,
    content: str,
    summary: str,
    killer_phrase: str,
    ai_insight: str,
    world_state: dict,
    trinity_review_log: dict,
    created_at: str,
) -> bool:
    """チャプターを新規作成する。成功時は True を返す。"""
    payload = {
        "ep_num": ep_num,
        "title": title,
        "content": content,
        "summary": summary,
        "killer_phrase": killer_phrase,
        "ai_insight": ai_insight,
        "world_state": world_state,
        "trinity_review_log": trinity_review_log,
        "created_at": created_at,
    }
    response = await _async_request("POST", f"{API_BASE_URL}/chapters/{book_id}", json=payload)
    return True if response else False


async def delete_chapter(book_id: int, ep_num: int) -> bool:
    """チャプターを削除する。成功時は True を返す。"""
    response = await _async_request("DELETE", f"{API_BASE_URL}/chapters/{book_id}/{ep_num}")
    return True if response else False


async def get_issues(book_id: int) -> List[Dict[str, Any]]:
    """本に紐づく課題(issues)一覧を取得する。"""
    response = await _async_request("GET", f"{API_BASE_URL}/books/{book_id}/issues")
    return response.json() if response else []


async def resolve_issue(issue_id: int, action: str, api_key: str) -> Dict[str, Any]:
    """課題を解決する。結果の辞書を返す。"""
    payload = {"action": action, "api_key": api_key}
    response = await _async_request(
        "POST", f"{API_BASE_URL}/issues/{issue_id}/resolve", json=payload
    )
    return response.json() if response else {"status": "error", "message": "No response"}


async def save_pending_patch(
    book_id: int, patch_type: str, patch_content: str, ab_test_result: Dict[str, Any]
) -> Dict[str, Any]:
    """保留中パッチを保存する。結果の辞書を返す。"""
    payload = {
        "book_id": book_id,
        "patch_type": patch_type,
        "patch_content": patch_content,
        "ab_test_result": ab_test_result,
    }
    response = await _async_request("POST", f"{API_BASE_URL}/patches/pending", json=payload)
    return response.json() if response else {"success": False, "error": "No response"}


async def get_pending_patches(book_id: int) -> List[Dict[str, Any]]:
    """保留中パッチ一覧を取得する。"""
    response = await _async_request("GET", f"{API_BASE_URL}/patches/pending/{book_id}")
    return response.json() if response else []


async def approve_patch(patch_id: int) -> Dict[str, Any]:
    """保留中パッチを承認する。"""
    response = await _async_request("POST", f"{API_BASE_URL}/patches/{patch_id}/approve")
    return {"success": True} if response else {"success": False, "error": "No response"}


async def reject_patch(patch_id: int) -> Dict[str, Any]:
    """保留中パッチを却下する。"""
    response = await _async_request("POST", f"{API_BASE_URL}/patches/{patch_id}/reject")
    return {"success": True} if response else {"success": False, "error": "No response"}


async def get_prompt_versions(book_id: int) -> List[Dict[str, Any]]:
    """プロンプトのバージョン一覧を取得する。"""
    response = await _async_request("GET", f"{API_BASE_URL}/prompts/versions/{book_id}")
    return response.json() if response else []


async def rollback_prompt_version(book_id: int, version_id: int) -> Dict[str, Any]:
    """プロンプトを指定バージョンにロールバックする。"""
    payload = {"version_id": version_id}
    response = await _async_request(
        "POST", f"{API_BASE_URL}/prompts/rollback/{book_id}", json=payload
    )
    return response.json() if response else {"success": False, "error": "No response"}


async def audit_producer_plan(
    api_key: str,
    genre: str,
    keywords: str,
    trend_memo: str,
    sanctuary: str = "",
    originality_score: int = 50,
    platform: str = "カクヨム/なろう",
) -> Dict[str, Any]:
    """プロデューサー監査(企画評価)を実行し、結果の辞書を返す。"""
    payload = {
        "api_key": api_key,
        "genre": genre,
        "keywords": keywords,
        "trend_memo": trend_memo,
        "sanctuary": sanctuary,
        "originality_score": originality_score,
        "platform": platform,
    }
    response = await _async_request("POST", f"{API_BASE_URL}/plots/audit", json=payload)
    return response.json() if response else {}


async def export_package(api_key: str, book_id: int) -> Optional[httpx.Response]:
    """マーケティング用パッケージをエクスポートし、レスポンスを返す。"""
    return await _async_request(
        "GET", f"{API_BASE_URL}/marketing/export_package/{book_id}", params={"api_key": api_key}
    )
