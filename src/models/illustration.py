from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IllustrationType(Enum):
    COVER = "cover"  # 表紙
    EPISODE = "episode"  # 話数ごと


class IllustrationModel(Enum):
    FAST = "imagen-4.0-fast-generate-001"
    QUALITY = "imagen-4.0-generate-001"


class SafetyLevel(Enum):
    BLOCK_MOST = "BLOCK_MOST"
    BLOCK_SOME = "BLOCK_SOME"
    BLOCK_FEW = "BLOCK_FEW"
    R15_CONTENT = "R15_CONTENT"  # 官能モード用


@dataclass
class IllustrationRequest:
    book_id: int
    illustration_type: IllustrationType
    episode_number: Optional[int] = None
    model: IllustrationModel = IllustrationModel.QUALITY
    safety_level: SafetyLevel = SafetyLevel.BLOCK_SOME
    prompt_override: Optional[str] = None


@dataclass
class IllustrationResult:
    request: IllustrationRequest
    image_url: str
    prompt: str
    model_used: str
    generation_time_ms: int
