from __future__ import annotations
from typing import Optional
from pydantic import Field
from src.domain.schemas.base import TimestampedSchema, AutoNovelBaseSchema

class ForeshadowingSchema(TimestampedSchema):
    id: int
    book_id: int
    title: str = Field(..., max_length=100)
    description: str = Field(...)
    planted_episode: int = Field(..., ge=1)
    target_episode: Optional[int] = None
    resolved_episode: Optional[int] = None
    status: str = Field(default="planted")  # planted, progressed, resolved, abandoned

class ForeshadowingCreateRequest(AutoNovelBaseSchema):
    book_id: int
    title: str = Field(..., min_length=1, max_length=100)
    description: str
    planted_episode: int = Field(..., ge=1)
    target_episode: Optional[int] = None


class GraphNodeSchema(AutoNovelBaseSchema):
    id: str
    label: str  # "Character", "Foreshadowing", "Location"
    properties: dict = {}


class GraphEdgeSchema(AutoNovelBaseSchema):
    source: str
    target: str
    type: str  # "PLANTED_IN", "RESOLVED_BY", "RELATED_TO"
    properties: dict = {}


class ForeshadowingGraphResponse(AutoNovelBaseSchema):
    graph_name: str
    nodes: list[GraphNodeSchema]
    edges: list[GraphEdgeSchema]
