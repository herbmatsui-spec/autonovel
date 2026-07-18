"""PlanningService のユニットテスト。

対象: UltimateHegemonyEngine の肥大化解消に向けた PlanningService 抽出 (Phase 3)。
PlanningService は WorldBibleGenerator を内包し、create_hegemony_plan /
audit_bible_completeness を委譲する。
"""
from typing import Any, Tuple

import pytest

from src.backend.planning_service import PlanningService

pytest_mark_async = pytest.mark.asyncio


class _FakeAuditor:
    def __init__(self) -> None:
        self.calls: list[Tuple] = []

    async def audit_bible_completeness(self, book_id: int, reporter: Any = None) -> bool:
        self.calls.append(("audit_bible_completeness", book_id))
        return True


class _FakeBibleGenerator:
    def __init__(self) -> None:
        self.auditor = _FakeAuditor()
        self.calls: list[Tuple] = []

    async def create_hegemony_plan(self, *args: Any, **kwargs: Any):
        self.calls.append(("create_hegemony_plan", kwargs))
        return 7, {"title": "demo"}


def _make_service() -> Tuple[PlanningService, _FakeBibleGenerator]:
    bible_gen = _FakeBibleGenerator()
    svc = PlanningService(
        bible_generator=bible_gen,
        repo=object(),
        pm=object(),
        ctx_mgr=object(),
        reporter_factory=lambda: object(),
    )
    return svc, bible_gen


def test_init_attributes() -> None:
    svc, bible_gen = _make_service()
    assert svc.bible_generator is bible_gen
    assert svc.reporter_factory is not None


@pytest_mark_async
async def test_create_hegemony_plan_delegates() -> None:
    svc, bible_gen = _make_service()
    book_id, bible = await svc.create_hegemony_plan(
        genre="fantasy", keywords="勇者", target_eps=10
    )
    assert book_id == 7
    assert bible == {"title": "demo"}
    assert bible_gen.calls[0][0] == "create_hegemony_plan"


@pytest_mark_async
async def test_audit_bible_completeness_delegates() -> None:
    svc, bible_gen = _make_service()
    ok = await svc.audit_bible_completeness(7, reporter=None)
    assert ok is True
    assert bible_gen.auditor.calls == [("audit_bible_completeness", 7)]
