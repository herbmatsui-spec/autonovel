"""Task state helper functions."""
import json
import time

from config.container import Container

async def create_task(task_id: str, message: str, total_steps: int = 1) -> None:
    """タスクの初期状態をDBに保存する。"""
    db = Container.db()
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
        "last_updated": time.time()
    }
    await db.save_internal_state(
        f"task_status:{task_id}",
        json.dumps(initial_state),
        time.strftime('%Y-%m-%d %H:%M:%S')
    )
