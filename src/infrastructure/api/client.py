import json
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)
API_BASE_URL = "http://127.0.0.1:8000/api"

def _request(method: str, path: str, timeout: float = 10.0, **kwargs: Any) -> Any:
    import urllib.request
    url = f"{API_BASE_URL}{path}"
    try:
        req = urllib.request.Request(url, method=method, data=json.dumps(kwargs).encode("utf-8") if kwargs else None)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.error(f"API request failed {method} {path}: {exc}")
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
