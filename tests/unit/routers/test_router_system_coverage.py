"""System router coverage: status, models info, skills, circuit breaker, priorities."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

import src.backend.routers.system as system_module
from src.backend.routers.system import (
    CircuitResetRequest,
    SkillVersionSwitchRequest,
    get_improvement_priorities,
    get_models_info,
    get_skill_version,
    get_huey_health_status,
    get_llm_provider_status,
    offline_flag,
    recalc_all_book_scores,
    reset_llm_circuit_breaker,
    switch_skill_version,
    system_status,
)


@pytest.fixture(autouse=True)
def reset_globals():
    system_module._llm_gateway = None
    system_module._llm_circuit_breaker = None
    system_module._shared_orchestrator = None
    yield
    system_module._llm_gateway = None
    system_module._llm_circuit_breaker = None
    system_module._shared_orchestrator = None


# ============================================================================
# Basic endpoints
# ============================================================================


@pytest.mark.asyncio
async def test_system_status():
    with pytest.MonkeyPatch.context() as m:
        import src.services.resilience as resilience
        m.setattr(resilience, "get_system_status", lambda: {"status": "ok", "db": True})
        result = await system_status()
    assert result == {"status": "ok", "db": True}


@pytest.mark.asyncio
async def test_offline_flag():
    with pytest.MonkeyPatch.context() as m:
        import src.services.resilience as resilience
        m.setattr(resilience, "is_offline_mode_enabled", lambda: True)
        result = await offline_flag()
    assert result == {"offline_mode_enabled": True, "cache_first": True}


@pytest.mark.asyncio
async def test_get_huey_health_status():
    """check_huey_health は src.backend.tasks.huey から遅延 import される。"""
    # huey モジュールの check_huey_health は関数として存在するため、
    # モジュール属性を直接パッチする
    with pytest.MonkeyPatch.context() as m:
        import sys as sys_module
        fake_huey = MagicMock()
        fake_huey.check_huey_health = lambda: {"healthy": True}
        m.setitem(sys_module.modules, "src.backend.tasks.huey", fake_huey)
        result = await get_huey_health_status()
    assert result == {"healthy": True}


@pytest.mark.asyncio
async def test_get_models_info():
    result = await get_models_info()
    assert result["status"] == "success"
    assert "current_provider" in result
    assert "server_defaults" in result
    assert "configured_keys" in result
    assert "gemini" in result["available_providers"]


# ============================================================================
# LLM gateway endpoints
# ============================================================================


@pytest.mark.asyncio
async def test_get_llm_provider_status():
    with pytest.MonkeyPatch.context() as m:
        gateway = MagicMock()
        gateway.status.return_value = {"gemini": "open"}
        m.setattr(system_module, "_get_llm_gateway", lambda: gateway)
        result = await get_llm_provider_status()
    assert result == {"providers": {"gemini": "open"}}


@pytest.mark.asyncio
async def test_get_llm_gateway_initialization():
    with pytest.MonkeyPatch.context() as m:
        import src.llm.circuit_breaker as cb_module
        import src.llm.resilient_gateway as rg_module
        cb = MagicMock()
        gw = MagicMock()
        m.setattr(cb_module, "LLMCircuitBreaker", lambda: cb)
        m.setattr(rg_module, "ResilientLLMGateway", lambda **kw: gw)
        result = system_module._get_llm_gateway()
        assert result is gw
        # Second call reuses the cached gateway
        assert system_module._get_llm_gateway() is gw


@pytest.mark.asyncio
async def test_reset_llm_circuit_breaker():
    with pytest.MonkeyPatch.context() as m:
        gateway = MagicMock()
        gateway.status.return_value = {"all": "open"}
        m.setattr(system_module, "_get_llm_gateway", lambda: gateway)
        # No request -> reset all
        result = await reset_llm_circuit_breaker(None)
        gateway.reset.assert_called_once_with(None)
        assert result == {"status": "success", "providers": {"all": "open"}}

        # With provider name
        result2 = await reset_llm_circuit_breaker(CircuitResetRequest(provider_name="gemini"))
        gateway.reset.assert_called_with("gemini")
        assert result2["status"] == "success"


# ============================================================================
# Skills endpoints
# ============================================================================


def make_orchestrator(active="v1", skills=None):
    orch = MagicMock()
    orch.get_active_version.return_value = active
    orch._skill_registry = skills or {"skill1": MagicMock(), "skill2": MagicMock()}
    return orch


@pytest.mark.asyncio
async def test_switch_skill_version_invalid():
    with pytest.raises(HTTPException) as exc:
        await switch_skill_version(SkillVersionSwitchRequest(version="v3"))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_switch_skill_version_success():
    orch = make_orchestrator()
    with pytest.MonkeyPatch.context() as m:
        m.setattr(system_module, "get_shared_orchestrator", lambda: orch)
        result = await switch_skill_version(SkillVersionSwitchRequest(version="v2"))
    assert result["status"] == "success"
    assert result["active_version"] == "v1"  # mock returns v1
    assert "skill1" in result["registered_skills"]
    orch.set_skill_version.assert_called_once_with("v2")


@pytest.mark.asyncio
async def test_switch_skill_version_error_wrapped():
    orch = make_orchestrator()
    orch.set_skill_version = MagicMock(side_effect=RuntimeError("switch fail"))
    with pytest.MonkeyPatch.context() as m:
        m.setattr(system_module, "get_shared_orchestrator", lambda: orch)
        with pytest.raises(HTTPException) as exc:
            await switch_skill_version(SkillVersionSwitchRequest(version="v1"))
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_skill_version():
    orch = make_orchestrator(active="v2")
    with pytest.MonkeyPatch.context() as m:
        m.setattr(system_module, "get_shared_orchestrator", lambda: orch)
        result = await get_skill_version()
    assert result == {"active_version": "v2", "registered_skills": ["skill1", "skill2"]}


def test_get_shared_orchestrator_singleton():
    with pytest.MonkeyPatch.context() as m:
        created = []

        class FakeOrchestrator:
            def __init__(self, nodes):
                self.nodes = nodes
                self._skill_registry = {}
                created.append(self)

            def register_discovered_skills(self, path):
                self._skill_registry["fake"] = MagicMock()

        import src.agents.orchestrator as orch_module
        m.setattr(orch_module, "Orchestrator", FakeOrchestrator)
        r1 = system_module.get_shared_orchestrator()
        r2 = system_module.get_shared_orchestrator()
        assert r1 is r2
        assert len(created) == 1


# ============================================================================
# Book score endpoints
# ============================================================================


@pytest.mark.asyncio
async def test_recalc_all_book_scores():
    """全書籍のBookScore再計算。"""
    # DB session モック（async context manager をサポート）
    from sqlalchemy import Delete, Select

    class FakeSession:
        def __init__(self):
            books_result = MagicMock()
            books_result.fetchall.return_value = [(1,), (2,)]
            chapters_result = MagicMock()
            chapters_result.fetchall.return_value = [(1,), (2,), (3,)]
            self.books_result = books_result
            self.chapters_result = chapters_result

            def execute_side_effect(stmt, *args, **kwargs):
                if isinstance(stmt, Select):
                    # Book select vs Chapter select
                    compiled = str(stmt)
                    if "id" in compiled and "ep_num" not in compiled:
                        return books_result
                    return chapters_result
                return MagicMock()  # delete statements

            self.execute = AsyncMock(side_effect=execute_side_effect)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    session = FakeSession()

    with pytest.MonkeyPatch.context() as m:
        db_manager = MagicMock()
        db_manager.get_session = lambda: session
        m.setattr("src.backend.database.core.get_db_manager", lambda: db_manager)
        # Book/Chapter は select() に実 SQLAlchemy モデルが必要なため実モデルを使用
        # （sys.modules への差し替えは不要。実装の import 先は src.backend.database.models）
        # BookScoreCalculator / Repository のみ差し替え
        import src.services.book_score_service as bss_module
        calculator = MagicMock()
        calculator.calculate = AsyncMock(return_value=MagicMock())
        m.setattr(bss_module, "BookScoreCalculator",
                  lambda repository=None: calculator)
        import src.backend.database.repositories.book_score as bsr_module
        m.setattr(bsr_module, "BookScoreRepository", lambda s: MagicMock())

        result = await recalc_all_book_scores()
    assert result["status"] == "success"
    assert result["recalculated_count"] == 6
    calculator.calculate.assert_awaited()
    # 各章で delete が実行される
    session.execute.assert_awaited()


@pytest.mark.asyncio
async def test_recalc_all_book_scores_error():
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.backend.database.core.get_db_manager",
                  MagicMock(side_effect=RuntimeError("db fail")))
        result = await recalc_all_book_scores()
    assert result["status"] == "error"
    assert "detail" in result
    assert "db fail" in result["detail"]


@pytest.mark.asyncio
async def test_get_improvement_priorities_empty():
    with pytest.MonkeyPatch.context() as m:
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        db_manager = MagicMock()
        db_manager.get_session = lambda: session
        m.setattr("src.backend.database.core.get_db_manager", lambda: db_manager)

        repo = MagicMock()
        repo.get_all_for_book = AsyncMock(return_value=[])
        import src.backend.database.repositories.book_score as bsr_module
        m.setattr(bsr_module, "BookScoreRepository", lambda s: repo)

        result = await get_improvement_priorities(1)
    assert result["priorities"] == []
    assert "スコアデータがありません" in result["message"]


@pytest.mark.asyncio
async def test_get_improvement_priorities_with_scores():
    scores = []
    for i in range(3):
        s = SimpleNamespace(structure_score=50.0, coherency_score=80.0,
                            factual_grounding_score=60.0,
                            visual_textual_synergy_score=75.0,
                            reader_experience_score=85.0)
        scores.append(s)

    with pytest.MonkeyPatch.context() as m:
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        db_manager = MagicMock()
        db_manager.get_session = lambda: session
        m.setattr("src.backend.database.core.get_db_manager", lambda: db_manager)

        repo = MagicMock()
        repo.get_all_for_book = AsyncMock(return_value=scores)
        import src.backend.database.repositories.book_score as bsr_module
        m.setattr(bsr_module, "BookScoreRepository", lambda s: repo)

        result = await get_improvement_priorities(1)
    assert result["priorities"]
    # priorities are ImprovementPriorityItem pydantic models
    dims_in_result = [p.dimension for p in result["priorities"]]
    assert "structure" in dims_in_result  # lowest score first
    # sorted by gain descending
    assert result["priorities"][0].dimension == "structure"
    first = result["priorities"][0]
    assert first.current_score == 50.0
    assert first.suggested_action
    assert first.expected_gain
    assert first.target_agent
