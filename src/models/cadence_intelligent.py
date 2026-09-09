"""Intelligent Cadence Reformatter Models and Configurations."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class CadenceMode(str, Enum):
    """Operation modes for intelligent cadence reformation."""
    RULE_SAFE = "rule_safe"            # 安全なルールベース置換のみ（時制混在なし、ダッシュなし）
    COMPOUND_MERGE = "compound_merge"  # 複文結合（連用形マージ）で文末重複を削減
    LOCAL_LLM = "local_llm"            # 違反スパンのみ軽量LLMで局所推敲
    HYBRID = "hybrid"                  # 通常はcompound_merge、難所はlocal_llmへ自動ルーティング


class CadenceIntelligentConfig(BaseModel):
    """Configuration for intelligent cadence reformation."""
    mode: CadenceMode = Field(default=CadenceMode.HYBRID, description="動作モード")
    max_consecutive_ta: int = Field(default=3, ge=2, le=5, description="許容する最大連続『〜た』数")
    enable_llm_refine: bool = Field(default=True, description="局所LLM推敲の有効化")
    enable_verifier: bool = Field(default=True, description="Do No Harmベリファイアの有効化")
    llm_model_name: str = Field(default="gemini-1.5-flash", description="局所推敲用軽量LLMモデル名")
    llm_temperature: float = Field(default=0.3, ge=0.0, le=1.0, description="推敲時温度（低めで安定）")
    llm_timeout_seconds: float = Field(default=2.0, ge=0.5, le=10.0, description="LLM推敲のタイムアウト秒数")
    max_compound_chars: int = Field(default=60, ge=30, le=120, description="複文結合後の最大文字数上限")
    min_content_ratio: float = Field(default=0.6, ge=0.2, le=1.0, description="推敲後の最小文字数比率")
    max_content_ratio: float = Field(default=1.4, ge=1.0, le=2.0, description="推敲後の最大文字数比率")

    model_config = {
        "use_enum_values": True,
        "extra": "ignore",
    }
