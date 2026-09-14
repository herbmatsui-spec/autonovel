from dataclasses import dataclass, field
from typing import Any

@dataclass
class LLMRequest:
    prompt: str
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int | None = None
    model: str | None = None
    json_mode: bool = False
    response_schema: type | None = None
    extra_params: dict[str, Any] = field(default_factory=dict)

@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

@dataclass
class LLMResponse:
    content: str
    model: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    parsed_json: dict | None = None

@dataclass
class StreamChunk:
    text: str
    is_final: bool = False
    finish_reason: str | None = None
