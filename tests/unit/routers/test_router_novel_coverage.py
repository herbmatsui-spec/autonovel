"""Novel router coverage: produce/status/episodes/report/score/promotion/pdca/alerts."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

import src.backend.routers.novel as novel_module
from src.backend.routers.novel import (
    BookScoreResponse,
    check_promotion_eligibility,
    get_book_alerts,
    get_chapter_book_score,
    get_novel_social_journals,
    get_novel_social_relationships,
    get_novel_social_trends,
    get_pdca_report,
    get_report,
    get_novel_status,
    list_episodes,
    produce_novel,
)


def make_score(chapter=1, overall=85.0, structure=90.0, coherency=88.0,
               factual=85.0, visual=86.0, reader=87.0):
    s = SimpleNamespace(book_id=1, chapter_number=chapter, overall_score=overall,
                        structure_score=structure, coherency_score=coherency,
                        factual_grounding_score=factual,
                        visual_textual_synergy_score=visual,
                        reader_experience_score=reader,
                        evaluated_at=SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00"))
    return s


# ============================================================================
# produce_novel
# ============================================================================


@pytest.mark.asyncio
async def test_produce_novel_success(monkeypatch):
    from src.models.production_config import NovelProject
    req = SimpleNamespace(title="T", genre="g", synopsis="s", keywords="k",
                          target_episodes=3, target_word_count=2000,
                          style_key="web", engine_key="default")

    with pytest.MonkeyPatch.context() as m:
        created = []

        def fake_create(project):
            created.append(project)

        m.setattr(novel_module.producer, "create_project", fake_create)
        m.setattr(novel_module.producer, "generate_all_episodes",
                  AsyncMock(return_value=None))
        result = await produce_novel(req, api_key="key")
    assert result.project_id == 1
    assert result.status == "completed"
    assert len(created) == 1


@pytest.mark.asyncio
async def test_produce_novel_generation_error(monkeypatch):
    req = SimpleNamespace(title="T", genre="g", synopsis="s", keywords="k",
                          target_episodes=3, target_word_count=2000,
                          style_key="web", engine_key="default")
    with pytest.MonkeyPatch.context() as m:
        m.setattr(novel_module.producer, "create_project", MagicMock())
        m.setattr(novel_module.producer, "generate_all_episodes",
                  AsyncMock(side_effect=RuntimeError("gen fail")))
        with pytest.raises(HTTPException) as exc:
            await produce_novel(req, api_key="key")
    assert exc.value.status_code == 500


# ============================================================================
# get_novel_status / list_episodes / get_report
# ============================================================================


@pytest.mark.asyncio
async def test_get_novel_status_found_and_missing(monkeypatch):
    progress = SimpleNamespace(status="running", current_episode=2, total_episodes=5,
                               progress_percent=40.0, message="msg", completed_eps=[1])
    with pytest.MonkeyPatch.context() as m:
        m.setattr(novel_module.producer, "get_progress", lambda: progress)
        result = await get_novel_status(1)
    assert result.status == "running"
    assert result.current_episode == 2

    with pytest.MonkeyPatch.context() as m:
        m.setattr(novel_module.producer, "get_progress", lambda: None)
        with pytest.raises(HTTPException) as exc:
            await get_novel_status(999)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_episodes(monkeypatch):
    episodes = [SimpleNamespace(ep_num=1, title="第1話", word_count=100,
                                quality_score=90.0)]
    with pytest.MonkeyPatch.context() as m:
        m.setattr(novel_module.producer, "get_episodes", lambda: episodes)
        result = await list_episodes(1)
    assert result.episodes[0]["ep_num"] == 1
    assert result.episodes[0]["title"] == "第1話"


@pytest.mark.asyncio
async def test_get_report_success_and_error(monkeypatch):
    report = MagicMock()
    report.dict.return_value = {"chapters": 5}
    with pytest.MonkeyPatch.context() as m:
        m.setattr(novel_module.producer, "generate_report", lambda: report)
        result = await get_report(1)
    assert result.report == {"chapters": 5}

    with pytest.MonkeyPatch.context() as m:
        m.setattr(novel_module.producer, "generate_report",
                  MagicMock(side_effect=RuntimeError("report fail")))
        with pytest.raises(HTTPException) as exc:
            await get_report(1)
    assert exc.value.status_code == 500


# ============================================================================
# get_chapter_book_score
# ============================================================================


@pytest.mark.asyncio
async def test_get_chapter_book_score_found_with_trend():
    score = make_score(chapter=5, overall=85.0)
    all_scores = [make_score(chapter=3, overall=80.0),
                  make_score(chapter=4, overall=82.0),
                  make_score(chapter=5, overall=85.0)]

    calculator = MagicMock()
    calculator.get_latest_score = AsyncMock(return_value=score)

    uow = make_async_uow(all_scores)

    with pytest.MonkeyPatch.context() as m:
        # 関数内で UnitOfWork が再 import されるためソース側もパッチ
        m.setattr(novel_module, "UnitOfWork", lambda db=None: uow)
        import src.backend.database.uow as uow_source
        m.setattr(uow_source, "UnitOfWork", lambda db=None: uow)
        m.setattr(novel_module.AppContainer, "db", lambda: None)
        m.setattr("src.services.book_score_service.BookScoreCalculator",
                  lambda repository=None: calculator)
        result = await get_chapter_book_score(1, 5)
    assert result.book_id == 1
    assert result.overall_score == 85.0
    assert result.trend_3ch is not None
    assert result.trend_3ch["chapters_count"] == 3
    assert result.trend_3ch["trend_slope"] == 5.0
    assert result.trend_3ch["recent_scores"][0]["chapter"] == 3


@pytest.mark.asyncio
async def test_get_chapter_book_score_not_found():
    calculator = MagicMock()
    calculator.get_latest_score = AsyncMock(return_value=None)
    uow = MagicMock()
    with pytest.MonkeyPatch.context() as m:
        m.setattr(novel_module, "UnitOfWork", lambda db=None: uow)
        m.setattr(novel_module.AppContainer, "db", lambda: None)
        m.setattr("src.services.book_score_service.BookScoreCalculator",
                  lambda repository=None: calculator)
        with pytest.raises(HTTPException) as exc:
            await get_chapter_book_score(1, 1)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_chapter_book_score_error_wrapped():
    with pytest.MonkeyPatch.context() as m:
        uow = make_failing_uow()
        m.setattr(novel_module, "UnitOfWork", lambda db=None: uow)
        import src.backend.database.uow as uow_source
        m.setattr(uow_source, "UnitOfWork", lambda db=None: uow)
        m.setattr(novel_module.AppContainer, "db", lambda: None)
        with pytest.raises(HTTPException) as exc:
            await get_chapter_book_score(1, 1)
    assert exc.value.status_code == 500
    assert "db" in exc.value.detail


@pytest.mark.asyncio
async def test_get_chapter_book_score_no_trend_single_score():
    score = make_score(chapter=1, overall=85.0)
    calculator = MagicMock()
    calculator.get_latest_score = AsyncMock(return_value=score)
    uow = MagicMock()
    uow.book_scores.get_all_for_book = AsyncMock(return_value=[score])
    with pytest.MonkeyPatch.context() as m:
        m.setattr(novel_module, "UnitOfWork", lambda db=None: uow)
        m.setattr(novel_module.AppContainer, "db", lambda: None)
        m.setattr("src.services.book_score_service.BookScoreCalculator",
                  lambda repository=None: calculator)
        result = await get_chapter_book_score(1, 1)
    assert result.trend_3ch is None


# ============================================================================
# check_promotion_eligibility
# ============================================================================


def make_async_uow(scores):
    """async context manager 対応の uow モック。"""
    uow = MagicMock()
    uow.book_scores.get_all_for_book = AsyncMock(return_value=scores)
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    return uow


@pytest.mark.asyncio
@pytest.mark.parametrize("scores,expected_eligible,reason_hint", [
    ([], False, "3章以上の評価が必要です"),
    ([make_score(chapter=1, overall=80.0), make_score(chapter=2, overall=82.0)],
     False, "3章以上の評価が必要です"),
    ([make_score(chapter=1, overall=85.0), make_score(chapter=2, overall=86.0),
      make_score(chapter=3, overall=87.0)], True, None),
    ([make_score(chapter=1, overall=70.0), make_score(chapter=2, overall=71.0),
      make_score(chapter=3, overall=72.0)], False, "80.0 未満"),
    ([make_score(chapter=1, overall=90.0), make_score(chapter=2, overall=85.0),
      make_score(chapter=3, overall=80.0)], False, "上昇していません"),
])
async def test_check_promotion_eligibility(scores, expected_eligible, reason_hint):
    uow = make_async_uow(scores)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(novel_module, "UnitOfWork", lambda db=None: uow)
        import src.backend.database.uow as uow_source
        m.setattr(uow_source, "UnitOfWork", lambda db=None: uow)
        m.setattr(novel_module.AppContainer, "db", lambda: None)
        result = await check_promotion_eligibility(1)
    assert result.eligible is expected_eligible
    if reason_hint:
        assert reason_hint in (result.reason or "")
    else:
        assert result.reason is None
        assert result.chapters_evaluated == 3
        assert result.avg_score == 86.0
        assert result.trend_slope == 2.0


def make_failing_uow():
    """__aenter__ で失敗する uow モック。"""
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(side_effect=RuntimeError("db"))
    uow.__aexit__ = AsyncMock(return_value=False)
    return uow


@pytest.mark.asyncio
async def test_check_promotion_eligibility_error():
    with pytest.MonkeyPatch.context() as m:
        uow = make_failing_uow()
        m.setattr(novel_module, "UnitOfWork", lambda db=None: uow)
        import src.backend.database.uow as uow_source
        m.setattr(uow_source, "UnitOfWork", lambda db=None: uow)
        m.setattr(novel_module.AppContainer, "db", lambda: None)
        with pytest.raises(HTTPException) as exc:
            await check_promotion_eligibility(1)
    assert exc.value.status_code == 500
    assert "db" in exc.value.detail


# ============================================================================
# get_pdca_report / get_book_alerts
# ============================================================================


@pytest.mark.asyncio
async def test_get_pdca_report_success():
    report = {"book_id": 1, "plan": {}, "do": {}, "check": {}, "act": {}}
    with pytest.MonkeyPatch.context() as m:
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        db_manager = MagicMock()
        db_manager.get_session = lambda: session
        m.setattr("src.backend.database.core.get_db_manager", lambda: db_manager)
        calculator = MagicMock()
        calculator.generate_pdca_report = AsyncMock(return_value=report)
        m.setattr("src.services.book_score_service.BookScoreCalculator",
                  lambda repository=None: calculator)
        import src.backend.database.repositories.book_score as bsr
        m.setattr(bsr, "BookScoreRepository", lambda s: MagicMock())
        result = await get_pdca_report(1)
    assert result == report


@pytest.mark.asyncio
async def test_get_pdca_report_not_found_and_error():
    with pytest.MonkeyPatch.context() as m:
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        db_manager = MagicMock()
        db_manager.get_session = lambda: session
        m.setattr("src.backend.database.core.get_db_manager", lambda: db_manager)
        calculator = MagicMock()
        calculator.generate_pdca_report = AsyncMock(return_value={"error": "not found"})
        m.setattr("src.services.book_score_service.BookScoreCalculator",
                  lambda repository=None: calculator)
        import src.backend.database.repositories.book_score as bsr
        m.setattr(bsr, "BookScoreRepository", lambda s: MagicMock())
        with pytest.raises(HTTPException) as exc:
            await get_pdca_report(1)
    assert exc.value.status_code == 404

    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.backend.database.core.get_db_manager",
                  MagicMock(side_effect=RuntimeError("db")))
        with pytest.raises(HTTPException) as exc:
            await get_pdca_report(1)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_book_alerts_all_types():
    trend = {"changepoints": [{"chapter_index": 4, "change": -20.0}],
             "slope": -0.1, "avg_score": 60.0, "latest_score": 40.0,
             "chapters_evaluated": 6}
    with pytest.MonkeyPatch.context() as m:
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        db_manager = MagicMock()
        db_manager.get_session = lambda: session
        m.setattr("src.backend.database.core.get_db_manager", lambda: db_manager)
        calculator = MagicMock()
        calculator.analyze_trend = AsyncMock(return_value=trend)
        m.setattr("src.services.book_score_service.BookScoreCalculator",
                  lambda repository=None: calculator)
        import src.backend.database.repositories.book_score as bsr
        m.setattr(bsr, "BookScoreRepository", lambda s: MagicMock())
        result = await get_book_alerts(1)
    types = [a["type"] for a in result["alerts"]]
    assert "score_drop" in types
    assert "stagnation" in types
    assert "anomaly" in types
    assert "no_improvement" in types


@pytest.mark.asyncio
async def test_get_book_alerts_no_trend():
    with pytest.MonkeyPatch.context() as m:
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        db_manager = MagicMock()
        db_manager.get_session = lambda: session
        m.setattr("src.backend.database.core.get_db_manager", lambda: db_manager)
        calculator = MagicMock()
        calculator.analyze_trend = AsyncMock(return_value={"error": "no data"})
        m.setattr("src.services.book_score_service.BookScoreCalculator",
                  lambda repository=None: calculator)
        import src.backend.database.repositories.book_score as bsr
        m.setattr(bsr, "BookScoreRepository", lambda s: MagicMock())
        result = await get_book_alerts(1)
    assert result == {"book_id": 1, "alerts": []}


@pytest.mark.asyncio
async def test_get_book_alerts_healthy():
    trend = {"changepoints": [], "slope": 2.0, "avg_score": 85.0,
             "latest_score": 90.0, "chapters_evaluated": 5}
    with pytest.MonkeyPatch.context() as m:
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        db_manager = MagicMock()
        db_manager.get_session = lambda: session
        m.setattr("src.backend.database.core.get_db_manager", lambda: db_manager)
        calculator = MagicMock()
        calculator.analyze_trend = AsyncMock(return_value=trend)
        m.setattr("src.services.book_score_service.BookScoreCalculator",
                  lambda repository=None: calculator)
        import src.backend.database.repositories.book_score as bsr
        m.setattr(bsr, "BookScoreRepository", lambda s: MagicMock())
        result = await get_book_alerts(1)
    assert result["alerts"] == []


# ============================================================================
# Social endpoints
# ============================================================================


@pytest.mark.asyncio
async def test_get_novel_social_relationships(monkeypatch):
    rel = SimpleNamespace(trust_score=80, tension_score=30, affinity_score=60,
                          last_interaction_ep=3, dynamics_state="warm")
    db = MagicMock()
    repo = MagicMock()
    repo.get_all_relationships = AsyncMock(
        return_value={("A", "B"): rel, ("C", "A"): rel})  # C>A filtered out

    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.backend.database.core.DatabaseManager", lambda url: db)
        m.setattr("src.backend.database.social_repository.SocialRepository",
                  lambda d: repo)
        result = await get_novel_social_relationships(1, api_key="key")
    assert result["book_id"] == 1
    assert len(result["relationships"]) == 1
    assert result["relationships"][0]["char_a"] == "A"
    assert result["relationships"][0]["dynamics_state"] == "warm"


@pytest.mark.asyncio
async def test_get_novel_social_journals(monkeypatch):
    db = MagicMock()
    repo = MagicMock()
    repo.get_journals = AsyncMock(return_value=[{"id": 1}])
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.backend.database.core.DatabaseManager", lambda url: db)
        m.setattr("src.backend.database.social_repository.SocialRepository",
                  lambda d: repo)
        result = await get_novel_social_journals(1, ep_num=2, character_name="A",
                                                 limit=10, api_key="key")
    assert result["journals"] == [{"id": 1}]
    repo.get_journals.assert_awaited_once_with(book_id=1, episode_num=2,
                                               character_name="A", limit=10)


@pytest.mark.asyncio
async def test_get_novel_social_trends(monkeypatch):
    db = MagicMock()
    repo = MagicMock()
    repo.get_relationship_trends_summary = AsyncMock(return_value="trend text")
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.backend.database.core.DatabaseManager", lambda url: db)
        m.setattr("src.backend.database.social_repository.SocialRepository",
                  lambda d: repo)
        result = await get_novel_social_trends(1, api_key="key")
    assert result["trends_summary"] == "trend text"
