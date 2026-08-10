from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class IllustrationType(Enum):
    COVER = "cover"  # 表紙
    EPISODE = "episode"  # 話数ごとの挿絵（シーン抽出）
    CHARACTER = "character"  # キャラクター立ち絵


class IllustrationModel(Enum):
    AUTO = "auto"  # コンテキストに応じ自動選択
    FAST = "fast"
    QUALITY = "quality"
    ULTRA = "ultra"


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
    character_id: Optional[int] = None
    scene_text: Optional[str] = None
    book_context: Dict[str, str] = field(default_factory=dict)
    model: IllustrationModel = IllustrationModel.AUTO
    safety_level: SafetyLevel = SafetyLevel.BLOCK_SOME
    aspect_ratio: str = "3:4"
    prompt_override: Optional[str] = None


@dataclass
class IllustrationResult:
    request: IllustrationRequest
    image_url: str
    prompt: str
    model_used: str
    generation_time_ms: int
    illustration_id: Optional[int] = None
