"""Common DTOs for pagination and responses."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

MODEL_CONFIG_DEFAULTS = ConfigDict(populate_by_name=True, extra="allow", protected_namespaces=())


class PaginationDTO(BaseModel):
    """Pagination parameters."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    model_config = MODEL_CONFIG_DEFAULTS


class PaginatedResponseDTO(BaseModel, Generic[T]):
    """Paginated response wrapper."""

    items: list[T] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0

    model_config = MODEL_CONFIG_DEFAULTS

    @property
    def has_more(self) -> bool:
        return self.offset + self.limit < self.total


class ErrorResponseDTO(BaseModel):
    """Standard error response."""

    error: str
    detail: str | None = None
    code: str | None = None

    model_config = MODEL_CONFIG_DEFAULTS


class SuccessResponseDTO(BaseModel):
    """Standard success response."""

    success: bool = True
    message: str | None = None
    data: Any = None

    model_config = MODEL_CONFIG_DEFAULTS


@dataclass
class ValidationErrorDTO:
    """Validation error detail."""

    field: str
    message: str
    code: str | None = None
