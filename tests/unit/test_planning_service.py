"""PlanningService のユニットテスト。

対象: UltimateHegemonyEngine の肥大化解消に向けた PlanningService 抽出。

Phase 3: PlanningService 抽出 (Steps 56-80)

"""

from typing import Any
from src.backend.planning_service import PlanningService
from src.backend.protocols import PlanningPort
from src.shared.utils import StatusReporter


class _FakePlanningService:
    def __init__(self):
        self.called_methods = []

    async def create_hegemony_plan(self, *args, **kwargs):
        self.called_methods.append(("create_hegemony_plan", args, kwargs))
        return 1, "fake_bible"

    async def audit_bible_completeness(self, book_id: int, reporter: Any = None) -> bool:
        self.called_methods.append(("audit_bible_completeness", book_id, reporter))
        return True


def test_planning_service_creation():
    # Mock dependencies
    planning_agent = object()
    bible_generator = object()
    repo = object()
    pm = object()
    ctx_mgr = object()
    reporter_factory = lambda: object()
    
    service = PlanningService(
        planner=planning_agent,
        bible_generator=bible_generator,
        repo=repo,
        pm=pm,
        ctx_mgr=ctx_mgr,
        reporter_factory=reporter_factory,
    )

    # Verify attributes
    assert service.planning_agent is planning_agent
    assert service.bible_generator is bible_generator
    assert service.repo is repo
    assert service.pm is pm
    assert service.ctx_mgr is ctx_mgr
    assert service.reporter_factory is reporter_factory


def test_planning_service_methods_exist():
    # Check that the service has the required methods
    assert hasattr(PlanningService, "execute")
    assert hasattr(PlanningService, "create_hegemony_plan")
    assert hasattr(PlanningService, "audit_bible_completeness")
    assert hasattr(PlanningService, "expand_plots")
    assert hasattr(PlanningService, "rebuild_plots")
    assert hasattr(PlanningService, "audit_bible_completeness")


def test_planning_service_instantiation():
    # Test that PlanningService can be instantiated with the expected arguments
    planning_service = PlanningService(
        planning_agent=object(),
        bible_generator=object(),
        repo=object(),
        pm=object(),
        ctx_mgr=object(),
        reporter_factory=object(),
    )
    assert planning_service is not None


def test_planning_service_delegation():
    # Test that the service delegates to its dependencies
    fake_service = _FakePlanningService()
    
    # Test create_hegemony_plan delegation
    fake_service.create_hegemony_plan()
    assert ("create_hegemony_plan",) in fake_service.called_methods
    
    # Test audit_bible_completeness delegation
    fake_service.audit_bible_completeness(1, object())
    assert ("audit_bible_completeness", 1, object()) in fake_service.called_methods