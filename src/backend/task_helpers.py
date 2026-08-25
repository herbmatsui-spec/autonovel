"""Task state helper functions."""

import json
import time

from src.core.container import AppContainer


async def create_task(task_id: str, message: str, total_steps: int = 1) -> None:
    """タスクの初期状態をDBに保存する。"""
    db = AppContainer.db()
    initial_state = {
        "is_running": True,
        "current_step": 0,
        "total_steps": total_steps,
        "message": message,
        "sub_message": "キューの待機中",
        "streaming_text": "",
        "logs": [f"[{time.strftime('%H:%M:%S')}] 🚀 タスクを登録しました。"],
        "error": None,
        "result_data": None,
        "token_usage": {"prompt": 0, "completion": 0, "calls": 0},
        "start_time": time.time(),
        "last_updated": time.time(),
    }
    await db.save_internal_state(
        f"task_status:{task_id}", json.dumps(initial_state), time.strftime("%Y-%m-%d %H:%M:%S")
    )

async def update_task_status(
    task_id: str,
    *,
    is_running: Optional[bool] = None,
    current_step: Optional[int] = None,
    total_steps: Optional[int] = None,
    message: Optional[str] = None,
    sub_message: Optional[str] = None,
    streaming_text: Optional[str] = None,
    log: Optional[str] = None,
    error: Optional[str] = None,
    task_error: Optional[dict] = None,
    result_data: Optional[Any] = None,
    token_usage: Optional[dict] = None,
    resume_from_step: Optional[int] = None,
    partial_result: Optional[dict] = None,
) -> None:
    """タスク状態をインクリメンタルに更新するヘルパー。
+
+    すべてのパラメータはオプションで、``None`` の場合は既存の値を保持します。
+    ``log`` が指定された場合は ``logs`` 配列に追記されます。
+    ``task_error`` には ``src.models.api_schemas.TaskErrorDetail`` の JSON 版を渡すことができます。
+    """
+    db = AppContainer.db()
+    raw = await db.get_internal_state(f"task_status:{task_id}")
+    if raw is None:
+        state: dict = {}
+    else:
+        try:
+            state = json.loads(raw)
+        except json.JSONDecodeError:
+            state = {}
+
+    # Apply provided updates
+    if is_running is not None:
+        state["is_running"] = is_running
+    if current_step is not None:
+        state["current_step"] = current_step
+    if total_steps is not None:
+        state["total_steps"] = total_steps
+    if message is not None:
+        state["message"] = message
+    if sub_message is not None:
+        state["sub_message"] = sub_message
+    if streaming_text is not None:
+        state["streaming_text"] = streaming_text
+    if log is not None:
+        state.setdefault("logs", [])
+        state["logs"].append(log)
+    if error is not None:
+        state["error"] = error
+    if task_error is not None:
+        state["task_error"] = task_error
+    if result_data is not None:
+        state["result_data"] = result_data
+    if token_usage is not None:
+        state["token_usage"] = token_usage
+    if resume_from_step is not None:
+        state["resume_from_step"] = resume_from_step
+    if partial_result is not None:
+        state["partial_result"] = partial_result
+
+    # Update timestamps
+    state["last_updated"] = time.time()
+    await db.save_internal_state(
+        f"task_status:{task_id}", json.dumps(state), time.strftime("%Y-%m-%d %H:%M:%S")
+    )


async def get_task_status(task_id: str) -> dict:
    """タスクの状態をDBから取得する。"""
    db = AppContainer.db()
    raw = await db.get_internal_state(f"task_status:{task_id}")
    if raw is None:
        return {"is_running": False, "error": "タスクが見つかりません", "result_data": None}
    try:
        state = json.loads(raw)
    except json.JSONDecodeError:
        state = {"is_running": False, "error": "状態のデコードに失敗", "result_data": None}
    return state
