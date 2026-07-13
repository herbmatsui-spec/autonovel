import logging
import streamlit as st
from typing import Any, Dict, Optional

from src.shared.resilience_config import ResilienceConfigLoader
from src.shared.resilient_http import ResilientHttpClient

logger = logging.getLogger(__name__)
API_BASE_URL = "http://127.0.0.1:8000/api"

# Singleton instance of the resilient client
# It uses the "backend_api" policy from config/resilience.yaml
_resilient_client: Optional[ResilientHttpClient] = None

def get_client() -> ResilientHttpClient:
    global _resilient_client
    if _resilient_client is None:
        config = ResilienceConfigLoader().get_policy("backend_api")
        _resilient_client = ResilientHttpClient(
            base_url=API_BASE_URL,
            retry_policy=config.retry_policy,
            circuit_breaker=config.circuit_breaker
        )
    return _resilient_client

def _request(method: str, path: str, timeout: float = 10.0, **kwargs: Any) -> Any:
    """
    Synchronous wrapper around the asynchronous ResilientHttpClient.
    Since streamlit_app/api_client.py is used synchronously in many places,
    we use asyncio.run or a similar mechanism to bridge the gap.
    """
    client = get_client()

    async def _async_req():
        return await client.request(
            method=method,
            path=path,
            json=kwargs,
            timeout=timeout
        )

    try:
        # Use the utility async_helper for running async code in sync context
        from streamlit_app.utils.async_helper import run_async
        return run_async(_async_req())

    except Exception as exc:
        logger.error(f"Resilient API request failed {method} {path}: {exc}")
        raise

def start_plan_generation(**kwargs) -> str:
    data = _request("POST", "/plan/generate", **kwargs)
    return data.get("task_id", "unknown")

def start_plot_expansion(**kwargs) -> str:
    data = _request("POST", "/plot/expand", **kwargs)
    return data.get("task_id", "unknown")

def start_episode_writing(**kwargs) -> str:
    data = _request("POST", "/writing/start", **kwargs)
    return data.get("task_id", "unknown")

def get_task_status(task_id: str, timeout: float = 5.0) -> Dict[str, Any]:
    return _request("GET", f"/tasks/{task_id}", timeout=timeout) or {}

def stop_task(task_id: str) -> None:
    _request("POST", f"/tasks/{task_id}/stop")

def start_erotic_refinement(api_key: str, config: dict, book_id: int, ep_num: int, intensity: int = 2, platform_preset: str = "kakuyomu_romance") -> str:
    """官能研磨タスクを開始する。task_idを返す。"""
    data = _request(
        "POST",
        "/refine_erotic",
        api_key=api_key,
        config=config,
        book_id=book_id,
        ep_num=ep_num,
        intensity=intensity,
        platform_preset=platform_preset
    )
    return data.get("task_id", "unknown")
