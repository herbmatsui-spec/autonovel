"""Tests for Commercial Publishing Asynchronous Tasks and Scheduling (Phase 5 / Steps 49-60)."""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from src.backend.tasks.commercial_tasks import (
    schedule_commercial_publish,
    get_scheduled_commercial_tasks,
    cancel_commercial_task,
)


def test_schedule_commercial_publish_future_time():
    """Step 50, 58: Schedule publish with future timestamp computes correct delay and registers as scheduled."""
    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    iso_future = future_time.isoformat()

    job = schedule_commercial_publish(
        book_id=1,
        platforms=["narou"],
        credentials={"narou": {"email": "test@example.com", "password": "pass"}},
        publish_at=iso_future,
    )

    assert job["book_id"] == 1
    assert job["status"] == "scheduled"
    assert job["delay_seconds"] > 7000  # approximately 7200 seconds
    assert "task_id" in job
    assert job["platforms"] == ["narou"]


def test_schedule_commercial_publish_immediate():
    """Step 50: Schedule publish with no schedule time defaults to immediate queued task."""
    job = schedule_commercial_publish(
        book_id=2,
        platforms=["kakuyomu"],
        credentials={"kakuyomu": {"api_token": "token-123"}},
        publish_at=None,
    )

    assert job["book_id"] == 2
    assert job["status"] == "queued"
    assert job["delay_seconds"] == 0
    assert "task_id" in job


def test_list_and_cancel_scheduled_tasks():
    """Step 56, 57: List scheduled tasks and cancel by task_id."""
    future_time = datetime.now(timezone.utc) + timedelta(days=1)
    job = schedule_commercial_publish(
        book_id=99,
        platforms=["narou", "kakuyomu"],
        credentials={},
        publish_at=future_time.isoformat(),
    )
    tid = job["task_id"]

    # List tasks for book 99
    book_tasks = get_scheduled_commercial_tasks(book_id=99)
    assert any(t["task_id"] == tid for t in book_tasks)

    # Cancel task
    cancelled = cancel_commercial_task(tid)
    assert cancelled is True

    # Check status changed to cancelled
    updated_tasks = get_scheduled_commercial_tasks(book_id=99)
    target = next(t for t in updated_tasks if t["task_id"] == tid)
    assert target["status"] == "cancelled"


@pytest.mark.asyncio
async def test_commercial_router_schedule_request():
    """Step 51, 59: Router endpoint delegates scheduled publish to Huey without blocking."""
    from src.backend.routers.commercial import publish_commercial, PublishRequest
    from unittest.mock import MagicMock, AsyncMock

    req = PublishRequest(
        book_id=1,
        platforms=["narou"],
        credentials={"narou": {"email": "user@test.com", "password": "secret"}},
        schedule={"target_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()},
    )

    mock_book = MagicMock()
    mock_book.title = "テスト小説"
    mock_book.synopsis = "あらすじ"
    mock_book.concept = None
    mock_book.genre = "general"
    mock_book.tags = []
    mock_book.sanctuary_integrity = 100

    mock_ch = MagicMock()
    mock_ch.ep_num = 1
    mock_ch.title = "第1話"
    mock_ch.content = "本文です。"
    mock_ch.summary = ""

    mock_session = AsyncMock()
    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = mock_book
    mock_ch_result = MagicMock()
    mock_ch_result.scalars.return_value.all.return_value = [mock_ch]

    mock_session.execute.side_effect = [mock_book_result, mock_ch_result]

    with patch("src.backend.database.uow.UnitOfWork") as mock_uow_cls, \
         patch("src.core.container.AppContainer.db") as mock_db:
        mock_uow_inst = AsyncMock()
        mock_uow_inst.session = mock_session
        mock_uow_cls.return_value.__aenter__.return_value = mock_uow_inst
        mock_uow_cls.return_value.__aexit__.return_value = None

        res = await publish_commercial(request=req, api_key="test-key")
        assert res["success"] is True
        assert res["status"] == "scheduled"
        assert "task_id" in res["data"]
        assert res["data"]["book_id"] == 1


@pytest.mark.asyncio
async def test_commercial_router_cancel_schedule():
    """Step 6: Router endpoint cancels a pending schedule and prevents cancelling non-pending ones."""
    from src.backend.routers.commercial import cancel_schedule
    from unittest.mock import MagicMock, AsyncMock
    from src.backend.database.models import PublicationScheduleModel

    mock_session = AsyncMock()
    
    # Case 1: Schedule not found
    mock_result_none = MagicMock()
    mock_result_none.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result_none
    
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await cancel_schedule(schedule_id=999, db=mock_session, api_key="test-key")
    assert exc.value.status_code == 404

    # Case 2: Schedule not pending (e.g., completed)
    mock_schedule_completed = MagicMock(spec=PublicationScheduleModel)
    mock_schedule_completed.status = "completed"
    mock_result_completed = MagicMock()
    mock_result_completed.scalar_one_or_none.return_value = mock_schedule_completed
    mock_session.execute.return_value = mock_result_completed
    
    with pytest.raises(HTTPException) as exc:
        await cancel_schedule(schedule_id=123, db=mock_session, api_key="test-key")
    assert exc.value.status_code == 400
    assert "Only pending schedules can be cancelled" in exc.value.detail

    # Case 3: Successful cancellation
    mock_schedule_pending = MagicMock(spec=PublicationScheduleModel)
    mock_schedule_pending.status = "pending"
    mock_result_pending = MagicMock()
    mock_result_pending.scalar_one_or_none.return_value = mock_schedule_pending
    mock_session.execute.return_value = mock_result_pending
    
    res = await cancel_schedule(schedule_id=123, db=mock_session, api_key="test-key")
    assert res["success"] is True
    assert mock_schedule_pending.status == "cancelled"
    mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_commercial_router_create_schedule():
    """Step 4: Router endpoint creates a publication schedule."""
    from src.backend.routers.commercial import create_schedule, PublicationScheduleCreate
    from unittest.mock import MagicMock, AsyncMock
    from src.backend.database.models import PublicationScheduleModel
    from datetime import datetime, timezone

    mock_session = AsyncMock()
    
    # Mock the created schedule object
    mock_schedule = MagicMock(spec=PublicationScheduleModel)
    mock_schedule.id = 123
    mock_schedule.book_id = 1
    mock_schedule.platform = "narou"
    mock_schedule.episode_range_start = 1
    mock_schedule.episode_range_end = 5
    mock_schedule.scheduled_at = datetime.now(timezone.utc)
    mock_schedule.status = "pending"
    mock_schedule.error_message = None
    mock_schedule.created_at = datetime.now(timezone.utc)

    # Mock db.add, commit, refresh
    # db.add is synchronous, so we use a regular MagicMock to avoid RuntimeWarning
    mock_session.add = MagicMock(return_value=None)
    mock_session.commit = AsyncMock(return_value=None)
    mock_session.refresh = AsyncMock(return_value=None)

    # We need to mock the actual object creation if we want to be strict,
    # but since create_schedule instantiates PublicationScheduleDbModel,
    # we can't easily mock the constructor without patching.
    # Instead, we'll patch the model class.
    with patch("src.backend.routers.commercial.PublicationScheduleDbModel") as mock_model_cls:
        mock_model_cls.return_value = mock_schedule
        
        req = PublicationScheduleCreate(
            book_id=1,
            platform="narou",
            episode_range=(1, 5),
            scheduled_at=datetime.now(timezone.utc)
        )
        
        res = await create_schedule(req=req, db=mock_session, api_key="test-key")
        
        assert res.id == 123
        assert res.book_id == 1
        assert res.platform == "narou"
        assert res.episode_range == (1, 5)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_commercial_router_get_schedules():
    """Step 5: Router endpoint retrieves schedules for a book."""
    from src.backend.routers.commercial import get_schedules
    from unittest.mock import MagicMock, AsyncMock
    from src.backend.database.models import PublicationScheduleModel
    from datetime import datetime, timezone

    mock_session = AsyncMock()
    
    # Mock schedule data
    mock_schedule = MagicMock(spec=PublicationScheduleModel)
    mock_schedule.id = 123
    mock_schedule.book_id = 1
    mock_schedule.platform = "narou"
    mock_schedule.episode_range_start = 1
    mock_schedule.episode_range_end = 5
    mock_schedule.scheduled_at = datetime.now(timezone.utc)
    mock_schedule.status = "pending"
    mock_schedule.error_message = None
    mock_schedule.created_at = datetime.now(timezone.utc)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_schedule]
    mock_session.execute.return_value = mock_result
    
    res = await get_schedules(book_id=1, db=mock_session, api_key="test-key")
    
    assert len(res) == 1
    assert res[0].id == 123
    assert res[0].book_id == 1
    assert res[0].episode_range == (1, 5)
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_commercial_router_run_schedule_now():
    """Step 10: Router endpoint triggers immediate execution of a schedule."""
    from src.backend.routers.commercial import run_schedule_now
    from unittest.mock import MagicMock, AsyncMock, patch
    from src.backend.database.models import PublicationScheduleModel

    mock_session = AsyncMock()
    
    # Mock schedule
    mock_schedule = MagicMock(spec=PublicationScheduleModel)
    mock_schedule.id = 123
    mock_schedule.status = "pending"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_schedule
    mock_session.execute.return_value = mock_result
    
    with patch("src.backend.tasks.commercial_tasks.execute_publication_task") as mock_task:
        res = await run_schedule_now(schedule_id=123, db=mock_session, api_key="test-key")
        
        assert res["success"] is True
        assert "triggered successfully" in res["message"]
        mock_task.assert_called_once_with(123)

    # Test already running
    mock_schedule.status = "running"
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await run_schedule_now(schedule_id=123, db=mock_session, api_key="test-key")
    assert exc.value.status_code == 400
    assert "already running" in exc.value.detail
