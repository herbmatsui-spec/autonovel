"""Result型: 成否を表現する代数的データ型"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")
E = TypeVar("E", bound=Exception)
U = TypeVar("U")


@dataclass
class Result[T, E: Exception]:
    value: T | None = None
    error: E | None = None

    @property
    def is_ok(self) -> bool:
        return self.error is None

    @property
    def is_err(self) -> bool:
        return self.error is not None

    @staticmethod
    def ok(value: T) -> Result[T, E]:
        return Result(value=value)

    @staticmethod
    def err(error: E) -> Result[T, E]:
        return Result(error=error)

    def unwrap(self) -> T:
        if self.is_err:
            raise self.error  # type: ignore[misc]
        return self.value  # type: ignore[return-value]

    def map(self, f: Callable[[T], U]) -> Result[U, E]:
        if self.is_err:
            return Result(error=self.error)
        return Result.ok(f(self.value))  # type: ignore[arg-type]

    def map_err(self, f: Callable[[E], E]) -> Result[T, E]:
        if self.is_ok:
            return Result(value=self.value)
        return Result.err(f(self.error))  # type: ignore[arg-type]
