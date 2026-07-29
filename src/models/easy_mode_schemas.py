from pydantic import BaseModel, Field


class EasyModeInput(BaseModel):
    chapter_history: list[str] = Field(default_factory=list)
    current_chapter: str = ""
    character_params: dict = Field(default_factory=dict)
    content_length_limit: int = Field(default=2000, ge=1, le=10000)

class GenerationResponse(BaseModel):
    output: str = ""
    completion_time_ms: int = 0
    error: str = ""
    suggestions: list[str] = Field(default_factory=list)
