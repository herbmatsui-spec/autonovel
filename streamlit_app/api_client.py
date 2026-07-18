import logging
from typing import Any, Dict, Optional

from src.shared.resilience_config import ResilienceConfigLoader
from src.shared.resilient_http import ResilientHttpClient

logger = logging.getLogger(__name__)
# Backend runs on port 8200 (see docker-compose.yml).
API_BASE_URL = "http://127.0.0.1:8200/api"

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


def get_episodes(book_id: int, timeout: float = 10.0) -> Dict[str, Any]:
    """指定書籍の全エピソード一覧を取得する"""
    return _request("GET", f"/novel/{book_id}/episodes", timeout=timeout) or {}


def get_episode_detail(book_id: int, ep_num: int, timeout: float = 10.0) -> Dict[str, Any]:
    """特定エピソードの詳細を取得する"""
    return _request("GET", f"/novel/{book_id}/episodes/{ep_num}", timeout=timeout) or {}


def get_novel_report(book_id: int = 1, timeout: float = 30.0) -> Dict[str, Any]:
    """制作レポートを取得する"""
    return _request("GET", f"/novel/{book_id}/report", timeout=timeout) or {}


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


# -----------------------------------------------------------------------------
# Books / Plots / Chapters / Bible / Optimization history
# -----------------------------------------------------------------------------
def list_books() -> list:
    return _request("GET", "/books") or []


def get_book(book_id: int) -> Optional[dict]:
    return _request("GET", f"/books/{book_id}")


def delete_book(book_id: int) -> None:
    _request("DELETE", f"/books/{book_id}")


def get_plots(book_id: int) -> list:
    data = _request("GET", f"/plots/{book_id}")
    return data.get("plots", []) if isinstance(data, dict) else (data or [])


def get_chapters(book_id: int) -> list:
    data = _request("GET", f"/chapters/{book_id}")
    return data.get("chapters", []) if isinstance(data, dict) else (data or [])


def create_chapter(book_id: int, ep_num: int, title: str, content: str, summary: str,
                  killer_phrase: str = "", ai_insight: str = "", world_state: dict = None,
                  trinity_review_log: dict = None, created_at: str = None) -> None:
    _request(
        "POST",
        f"/chapters/{book_id}",
        ep_num=ep_num,
        title=title,
        content=content,
        summary=summary,
        killer_phrase=killer_phrase,
        ai_insight=ai_insight,
        world_state=world_state or {},
        trinity_review_log=trinity_review_log or {},
        created_at=created_at,
    )


def delete_chapter(book_id: int, ep_num: int) -> None:
    _request("DELETE", f"/chapters/{book_id}/{ep_num}")


def get_bible(book_id: int) -> Optional[dict]:
    return _request("GET", f"/bibles/{book_id}")


def get_opt_history(book_id: int) -> list:
    data = _request("GET", f"/optimization_history/{book_id}")
    return data.get("history", []) if isinstance(data, dict) else (data or [])


# -----------------------------------------------------------------------------
# Marketing / Audit / Issues / Import / Style DNA
# -----------------------------------------------------------------------------
def analyze_style_dna(api_key: str, sample: str) -> dict:
    return _request("POST", "/marketing/analyze_style_dna", api_key=api_key, sample=sample) or {}


def export_package(api_key: str, book_id: int):
    return _request("POST", f"/marketing/export_package/{book_id}", api_key=api_key)


def generate_marketing(api_key: str, book_id: int, latest_ep: int) -> Optional[dict]:
    return _request(
        "POST", "/marketing/generate",
        api_key=api_key, book_id=book_id, latest_ep=latest_ep,
    )


def audit_producer_plan(api_key: str, genre: str, keywords: str, trend_memo: str,
                        sanctuary: str = "", originality_score: int = 50,
                        platform: str = "カクヨム/なろう") -> dict:
    return _request(
        "POST", "/plots/audit",
        api_key=api_key,
        genre=genre,
        keywords=keywords,
        trend_memo=trend_memo,
        sanctuary=sanctuary,
        originality_score=originality_score,
        platform=platform,
    ) or {}


def get_issues(book_id: int) -> list:
    data = _request("GET", f"/issues/books/{book_id}")
    return data.get("issues", []) if isinstance(data, dict) else (data or [])


def resolve_issue(issue_id: int, action: str, api_key: str) -> dict:
    return _request(
        "POST", f"/issues/{issue_id}/resolve",
        action=action, api_key=api_key,
    ) or {}


def import_chapter(api_key: str, book_id: int, ep_num: int, text: str, do_refine: bool) -> dict:
    return _request(
        "POST", "/chapters/import",
        api_key=api_key, book_id=book_id, ep_num=ep_num, text=text, do_refine=do_refine,
    ) or {}


# -----------------------------------------------------------------------------
# Commercial pipeline
# -----------------------------------------------------------------------------
def commercial_run(config: dict) -> dict:
    """
    Run the commercial pipeline.
    Sends ``config`` as the JSON body to ``/commercial/run``.
    Returns the backend response (``{"success": ..., "data": ..., "trace_id": ...}``).
    """
    client = get_client()

    async def _async_req():
        return await client.request(
            method="POST",
            path="/commercial/run",
            json=config,
            timeout=180.0,
        )

    try:
        from streamlit_app.utils.async_helper import run_async
        return run_async(_async_req()) or {}
    except Exception as exc:
        logger.error(f"Commercial pipeline request failed: {exc}")
        raise
