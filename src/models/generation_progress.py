from __future__ import annotations
from pydantic import BaseModel, Field
from src.models.base import MODEL_CONFIG_DEFAULTS

class AgentThoughtStep(BaseModel):
    phase: str = Field(..., description="フェーズ（planning, rag_retrieval, writing, refining 等）")
    step_name: str = Field(..., description="ステップ名（例: 伏線の照合中）")
    detail_thought: str = Field(..., description="詳細な思考内容やエージェントのログメッセージ")
    progress_percent: int = Field(..., ge=0, le=100, description="進捗率（0-100）")
    timestamp: float = Field(..., description="タイムスタンプ（Epoch秒）")

    model_config = MODEL_CONFIG_DEFAULTS
