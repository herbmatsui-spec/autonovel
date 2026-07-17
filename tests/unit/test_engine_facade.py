"""EngineFacade のユニットテスト。

既存の UltimateHegemonyEngine インスタンスを内包し、engine.* 呼び出しを
そのまま委譲することを確認する。
"""
from typing import Any, Optional, Tuple

import pytest

from src.backend.engine_config import EngineConfig
from src.backend.engine_facade import EngineFacade


class _FakeEngine:
    """engine.* の委譲先としての疑似エンジン。"""

    def __init__(self) -> None:
        self.planner = object()
        self.writer = object()
        self.repo = object()
        self.sync_bible_calls: list[tuple] = []
        self.resolve_calls: list[tuple] = []
        self.determine_calls: list[tuple] = []
        self.validate_calls: list[tuple] = []

    async def sync_bible(self, book_id: int, reporter: Optional[Any] = None) -> str:
        self.sync_bible_calls.append((book_id, reporter))
        return f"bible:{book_id}"

    async def resolve_bible_setting(self, setting_id: int, status: str) -> None:
        self.resolve_calls.append((setting_id, status))

    async def determine_target_tension(
        self, book_id: int, ep_num: int, genre: str, story_type: Optional[str] = None
    ) -> float:
        self.determine_calls.append((book_id, ep_num, genre, story_type))
        return 0.5

    async def validate_tension_deviation(
        self, ep_num: int, generated_tension: float, book_id: int, tolerance: float = 0.2
    ) -> Tuple[bool, float]:
        self.validate_calls.append((ep_num, generated_tension, book_id, tolerance))
        return (True, 0.1)


@pytest.fixture
def facade() -> EngineFacade:
    cfg = EngineConfig.create(api_key="k")
    return EngineFacade(config=cfg, engine=_FakeEngine())


@pytest.mark.asyncio
async def test_sync_bible_delegates(facade: EngineFacade) -> None:
    rep = object()
    res = await facade.sync_bible(7, reporter=rep)
    assert res == "bible:7"
    assert facade.engine_impl.sync_bible_calls == [(7, rep)]


@pytest.mark.asyncio
async def test_resolve_bible_setting_delegates(facade: EngineFacade) -> None:
    await facade.resolve_bible_setting(3, "approved")
    assert facade.engine_impl.resolve_calls == [(3, "approved")]


@pytest.mark.asyncio
async def test_determine_target_tension_delegates(facade: EngineFacade) -> None:
    val = await facade.determine_target_tension(1, 2, "fantasy", "arc")
    assert val == 0.5
    assert facade.engine_impl.determine_calls == [(1, 2, "fantasy", "arc")]


@pytest.mark.asyncio
async def test_validate_tension_deviation_delegates(facade: EngineFacade) -> None:
    ok, dev = await facade.validate_tension_deviation(2, 0.4, 1, 0.3)
    assert (ok, dev) == (True, 0.1)
    assert facade.engine_impl.validate_calls == [(2, 0.4, 1, 0.3)]


def test_unknown_attr_delegates_to_engine(facade: EngineFacade) -> None:
    # engine.planner / engine.writer / engine.repo 等の深いアクセスを委譲
    assert facade.planner is facade.engine_impl.planner
    assert facade.writer is facade.engine_impl.writer
    assert facade.repo is facade.engine_impl.repo


def test_config_exposed(facade: EngineFacade) -> None:
    assert facade.api_key == "k"
    from src.backend.engine_utils import AdaptiveCooldown

    assert isinstance(facade.cooldown, AdaptiveCooldown)
