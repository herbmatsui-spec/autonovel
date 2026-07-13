"""
src/infrastructure/api/api_client.py — 非同期対応APIクライアント
"""
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from src.core.exceptions import APIError as APIException

logger = logging.getLogger(__name__)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8200/api")

async def _async_request(method: str, url: str, **kwargs) -> Optional[httpx.Response]:
    """
    内部的な非同期リクエスト処理。
    UI層への直接的な依存（st.toastなど）を排除し、例外で通知する。
    """
    # 監査ログの取得はDIコンテナ経由で行う想定（後でリファクタリング）
    audit_logger = None
    try:
        from src.infrastructure.proxy import get_di_container
        container = get_di_container()
        audit_logger = container.audit_logger()
    except Exception:
        pass

    try:
        DEFAULT_TIMEOUT = 30.0  # seconds
        timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()

            # 成功ログの記録
            if audit_logger:
                audit_logger.log(
                    user_id="system_user",
                    action=f"API_{method}_{url.split('/')[-1]}",
                    resource_id=url,
                    status="SUCCESS",
                    details={"params": kwargs.get("params", {}), "payload": kwargs.get("json", {})}
                )
            return response
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.error(f"Connection error requesting {method} {url}: {e}")
        raise APIException(f"バックエンドAPIサーバーに接続できません。 (詳細: {e})", recoverable=False)
    except httpx.HTTPStatusError as e:
        if audit_logger:
            audit_logger.log(
                user_id="system_user",
                action=f"API_{method}_{url.split('/')[-1]}",
                resource_id=url,
                status="HTTP_ERROR",
                details={"status_code": e.response.status_code, "error": str(e)}
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
                details={"error": str(e)}
            )
        logger.error(f"Unexpected error requesting {method} {url}: {e}")
        raise APIException(f"予期せぬエラーが発生しました: {str(e)}")

# -----------------------------------------------------------------------------
# APIメソッド定義 (すべてasync)
# -----------------------------------------------------------------------------

async def list_books() -> List[Dict[str, Any]]:
    response = await _async_request("GET", f"{API_BASE_URL}/books")
    return response.json() if response else []

async def get_book(book_id: int) -> Optional[Dict[str, Any]]:
    response = await _async_request("GET", f"{API_BASE_URL}/books/{book_id}")
    return response.json() if response else None

async def delete_book(book_id: int) -> bool:
    response = await _async_request("DELETE", f"{API_BASE_URL}/books/{book_id}")
    return True if response else False

async def get_plots(book_id: int) -> List[Dict[str, Any]]:
    response = await _async_request("GET", f"{API_BASE_URL}/plots/{book_id}")
    return response.json() if response else []

async def get_chapters(book_id: int) -> List[Dict[str, Any]]:
    response = await _async_request("GET", f"{API_BASE_URL}/chapters/{book_id}")
    return response.json() if response else []

async def get_bible(book_id: int) -> Dict[str, Any]:
    response = await _async_request("GET", f"{API_BASE_URL}/bibles/{book_id}")
    return response.json() if response else {}

async def get_opt_history(book_id: int) -> List[Dict[str, Any]]:
    response = await _async_request("GET", f"{API_BASE_URL}/optimization_history/{book_id}")
    return response.json() if response else []

async def get_task_status(task_id: str, timeout: float = 30.0) -> Dict[str, Any]:
    try:
        response = await _async_request("GET", f"{API_BASE_URL}/tasks/{task_id}/status", timeout=timeout)
        return response.json() if response else {
            "is_running": False,
            "message": "通信エラー",
            "logs": [],
            "error": "バックエンドとの通信エラー"
        }
    except Exception as e:
        logger.error("Error getting task status: %s", e)
        return {
            "is_running": False,
            "message": "通信エラー",
            "logs": [],
            "error": f"バックエンドとの通信エラー、またはタスクが消失しました。\n詳細: {str(e)}"
        }

async def stop_task(task_id: str) -> bool:
    response = await _async_request("POST", f"{API_BASE_URL}/tasks/{task_id}/stop")
    return True if response else False

async def generate_easy(api_key: str, config: dict, genre: str, keywords: str, archetype_key: str, target_eps: int, initial_limit: int, word_count: int, concept: str, tone_vibe: float) -> Optional[str]:
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
        "tone_vibe": tone_vibe
    }
    response = await _async_request("POST", f"{API_BASE_URL}/easy_mode/generate", json=payload)
    return response.json().get("task_id") if response else None

async def generate_episodes(api_key: str, config: dict, book_id: int, write_from: int, write_to: int, passion: float, word_count: int, do_refine: bool, env_state: Dict[str, str], pipeline_mode: bool) -> Optional[str]:
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
        "pipeline_mode": pipeline_mode
    }
    response = await _async_request("POST", f"{API_BASE_URL}/episodes/generate", json=payload)
    return response.json().get("task_id") if response else None

async def plan_generation(api_key: str, config: dict, params: Dict[str, Any]) -> Optional[str]:
    payload = {
        "api_key": api_key,
        "config": config,
        "params": params
    }
    response = await _async_request("POST", f"{API_BASE_URL}/plots/plan_generation", json=payload)
    return response.json().get("task_id") if response else None

async def retry_failed_episodes(api_key: str, config: dict, book_id: int, passion: float, word_count: int) -> Optional[str]:
    payload = {
        "api_key": api_key,
        "config": config,
        "book_id": book_id,
        "passion": passion,
        "word_count": word_count
    }
    response = await _async_request("POST", f"{API_BASE_URL}/episodes/retry_failed", json=payload)
    return response.json().get("task_id") if response else None

async def expand_plots(api_key: str, config: dict, book_id: int, gen_from: int, gen_to: int) -> Optional[str]:
    payload = {
        "api_key": api_key,
        "config": config,
        "book_id": book_id,
        "gen_from": gen_from,
        "gen_to": gen_to
    }
    response = await _async_request("POST", f"{API_BASE_URL}/plots/expand", json=payload)
    return response.json().get("task_id") if response else None

async def rebuild_plots(api_key: str, config: dict, params: Dict[str, Any]) -> Optional[str]:
    payload = {
        "api_key": api_key,
        "config": config,
        "params": params
    }
    response = await _async_request("POST", f"{API_BASE_URL}/plots/rebuild", json=payload)
    return response.json().get("task_id") if response else None

async def critique_optimize(api_key: str, config: dict, book_id: int) -> Optional[str]:
    payload = {
        "api_key": api_key,
        "config": config,
        "book_id": book_id
    }
    response = await _async_request("POST", f"{API_BASE_URL}/critique/optimize", json=payload)
    return response.json().get("task_id") if response else None

async def import_chapter(api_key: str, book_id: int, ep_num: int, import_text: str, do_refine: bool) -> Optional[str]:
    payload = {
        "api_key": api_key,
        "book_id": book_id,
        "ep_num": ep_num,
        "import_text": import_text,
        "do_refine": do_refine
    }
    response = await _async_request("POST", f"{API_BASE_URL}/chapters/import", json=payload)
    return response.json().get("task_id") if response else None

async def generate_marketing(api_key: str, book_id: int, latest_ep: int) -> Optional[str]:
    payload = {
        "api_key": api_key,
        "book_id": book_id,
        "latest_ep": latest_ep
    }
    response = await _async_request("POST", f"{API_BASE_URL}/marketing/generate", json=payload)
    return response.json().get("task_id") if response else None

async def analyze_style_dna(api_key: str, sample: str) -> Dict[str, Any]:
    payload = {
        "api_key": api_key,
        "sample": sample
    }
    response = await _async_request("POST", f"{API_BASE_URL}/marketing/analyze_style", json=payload)
    return response.json() if response else {}

async def create_chapter(book_id: int, ep_num: int, title: str, content: str, summary: str, killer_phrase: str, ai_insight: str, world_state: dict, trinity_review_log: dict, created_at: str) -> bool:
    payload = {
        "ep_num": ep_num,
        "title": title,
        "content": content,
        "summary": summary,
        "killer_phrase": killer_phrase,
        "ai_insight": ai_insight,
        "world_state": world_state,
        "trinity_review_log": trinity_review_log,
        "created_at": created_at
    }
    response = await _async_request("POST", f"{API_BASE_URL}/chapters/{book_id}", json=payload)
    return True if response else False

async def delete_chapter(book_id: int, ep_num: int) -> bool:
    response = await _async_request("DELETE", f"{API_BASE_URL}/chapters/{book_id}/{ep_num}")
    return True if response else False

async def get_issues(book_id: int) -> List[Dict[str, Any]]:
    response = await _async_request("GET", f"{API_BASE_URL}/books/{book_id}/issues")
    return response.json() if response else []

async def resolve_issue(issue_id: int, action: str, api_key: str) -> Dict[str, Any]:
    payload = {
        "action": action,
        "api_key": api_key
    }
    response = await _async_request("POST", f"{API_BASE_URL}/issues/{issue_id}/resolve", json=payload)
    return response.json() if response else {"status": "error", "message": "No response"}

async def save_pending_patch(book_id: int, patch_type: str, patch_content: str, ab_test_result: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "book_id": book_id,
        "patch_type": patch_type,
        "patch_content": patch_content,
        "ab_test_result": ab_test_result
    }
    response = await _async_request("POST", f"{API_BASE_URL}/patches/pending", json=payload)
    return response.json() if response else {"success": False, "error": "No response"}

async def get_pending_patches(book_id: int) -> List[Dict[str, Any]]:
    response = await _async_request("GET", f"{API_BASE_URL}/patches/pending/{book_id}")
    return response.json() if response else []

async def approve_patch(patch_id: int) -> Dict[str, Any]:
    response = await _async_request("POST", f"{API_BASE_URL}/patches/{patch_id}/approve")
    return {"success": True} if response else {"success": False, "error": "No response"}

async def reject_patch(patch_id: int) -> Dict[str, Any]:
    response = await _async_request("POST", f"{API_BASE_URL}/patches/{patch_id}/reject")
    return {"success": True} if response else {"success": False, "error": "No response"}

async def get_prompt_versions(book_id: int) -> List[Dict[str, Any]]:
    response = await _async_request("GET", f"{API_BASE_URL}/prompts/versions/{book_id}")
    return response.json() if response else []

async def rollback_prompt_version(book_id: int, version_id: int) -> Dict[str, Any]:
    payload = {"version_id": version_id}
    response = await _async_request("POST", f"{API_BASE_URL}/prompts/rollback/{book_id}", json=payload)
    return response.json() if response else {"success": False, "error": "No response"}

async def audit_producer_plan(api_key: str, genre: str, keywords: str, trend_memo: str, sanctuary: str = "", originality_score: int = 50, platform: str = "カクヨム/なろう") -> Dict[str, Any]:
    payload = {
        "api_key": api_key,
        "genre": genre,
        "keywords": keywords,
        "trend_memo": trend_memo,
        "sanctuary": sanctuary,
        "originality_score": originality_score,
        "platform": platform
    }
    response = await _async_request("POST", f"{API_BASE_URL}/plots/audit", json=payload)
    return response.json() if response else {}

async def export_package(api_key: str, book_id: int) -> Optional[httpx.Response]:
    return await _async_request("GET", f"{API_BASE_URL}/marketing/export_package/{book_id}", params={"api_key": api_key})
