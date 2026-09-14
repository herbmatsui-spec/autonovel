"""Illustration DTOs."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

MODEL_CONFIG_DEFAULTS = ConfigDict(populate_by_name=True, extra="allow", protected_namespaces=())


class GenerateCharacterIllustrationDTO(BaseModel):
    """DTO for generating character illustration."""
    character_id: str = Field(..., min_length=1)
    novel_id: str = Field(..., min_length=1)
    description: Optional[str] = None
    style: Optional[str] = None
    pose: Optional[str] = None
    expression: Optional[str] = None
    outfit: Optional[str] = None
    background: Optional[str] = None

    model_config = MODEL_CONFIG_DEFAULTS


class GenerateCoverIllustrationDTO(BaseModel):
    """DTO for generating cover illustration."""
    novel_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    author: Optional[str] = None
    genre: Optional[str] = None
    style: Optional[str] = None
    elements: List[str] = Field(default_factory=list)

    model_config = MODEL_CONFIG_DEFAULTS


class GenerateSceneIllustrationDTO(BaseModel):
    """DTO for generating scene illustration."""
    novel_id: str = Field(..., min_length=1)
    episode_number: int = Field(..., ge=1)
    scene_description: str = Field(..., min_length=1)
    style: Optional[str] = None
    characters: List[str] = Field(default_factory=list)
    setting: Optional[str] = None
    mood: Optional[str] = None

    model_config = MODEL_CONFIG_DEFAULTS


class IllustrationResponseDTO(BaseModel):
    """DTO for illustration response."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    novel_id: str
    illustration_type: str  # "character", "cover", "scene"
    prompt: str
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def create_character(cls, novel_id: str, prompt: str, image_url: Optional[str] = None) -> "IllustrationResponseDTO":
        return cls(
            novel_id=novel_id,
            illustration_type="character",
            prompt=prompt,
            image_url=image_url,
        )

    @classmethod
    def create_cover(cls, novel_id: str, prompt: str, image_url: Optional[str] = None) -> "IllustrationResponseDTO":
        return cls(
            novel_id=novel_id,
            illustration_type="cover",
            prompt=prompt,
            image_url=image_url,
        )

    @classmethod
    def create_scene(cls, novel_id: str, prompt: str, image_url: Optional[str] = None) -> "IllustrationResponseDTO":
        return cls(
            novel_id=novel_id,
            illustration_type="scene",
            prompt=prompt,
            image_url=image_url,
        )


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from uuid import uuid4