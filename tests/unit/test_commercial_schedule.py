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
