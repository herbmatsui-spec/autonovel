from typing import Any, Dict

from pydantic import BaseModel


class ImmutableInput(BaseModel):
    """実行中に変更されない入力データ"""
    book_id: int
    genre: str
    initial_concept: Dict[str, Any]

class SystemSettings(BaseModel):
    """システム設定（ProjectContextから移行予定）"""
    model_writing: str
    model_planning: str
    max_history_len: int = 30
    safe_append_mode: str = "auto"

class RunState(BaseModel):
    """実行状態（可変）"""
    current_episode: int
    context_data: Dict[str, Any] = {}
    history: list = []
