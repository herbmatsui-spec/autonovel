"""Tests for src.backend.routers.easy_mode router functions."""

import asyncio
from unittest.mock import MagicMock

import pytest

import src.backend.tasks.generation_tasks as generation_tasks_mod
import src.backend.tasks.huey as huey_mod
from src.backend.routers import easy_mode


class DummySession:
    """Minimal dummy session object for repository usage."""

    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = None

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed = obj

    def get(self, model, id):
        return None


class DummyTask:

    def __init__(self, id):
        self.id = id


class DummyRepo:

    def __init__(self, session):
        self.session = session
        self.task_id = 42

    def create_task(self, status: str = "pending", result: str | None = None):
        return DummyTask(self.task_id)

    def update_task_status(self, task_id: int, status: str):
        pass

    def get_latest_bible(self, book_id: int):
        return None

    def get_all_non_anchor_chapters(self, *args, **kwargs):
        return []

    def get_all_characters(self, *args, **kwargs):
        return []

    def get_all_plots(self, *args, **kwargs):
        return []

    def get_book(self, *args, **kwargs):
        return None


@pytest.fixture
def dummy_session():
    return DummySession()


@pytest.fixture
def dummy_request():
    req = MagicMock()
    req.client.host = "127.0.0.1"
    return req


def patch_dependencies(monkeypatch):
    monkeypatch.setattr(easy_mode, "process_chapter", lambda x: f"processed:{x}")
    monkeypatch.setattr(easy_mode, "BookRepository", DummyRepo)
    monkeypatch.setattr(generation_tasks_mod, "generate_chapter_task", lambda params: None)
    called = []

    class DummyMetrics:

        @staticmethod
        def increment(name):
            called.append(name)

    monkeypatch.setattr(easy_mode, "metrics", DummyMetrics)
    return called


@pytest.mark.asyncio
async def test_generate_content_success(monkeypatch, dummy_session, dummy_request):
    called_metrics = patch_dependencies(monkeypatch)
    valid_input = easy_mode.EasyModeInput(
        chapter_history=["prev chapter"],
        current_chapter="current content",
        character_params={"name": "hero"},
        content_length_limit=1000,
    )
    response = await easy_mode.generate_content(
        valid_input, request=dummy_request, session=dummy_session
    )
    assert isinstance(response, easy_mode.GenerationResponse)
    assert any("42" in s for s in response.suggestions)
    assert "tasks_enqueued" in called_metrics


@pytest.mark.asyncio
async def test_generate_content_validation_error_path(
    monkeypatch, dummy_session, dummy_request
):
    class DummyValidationError(Exception):

        def errors(self):
            return [{"loc": "field", "msg": "msg", "type": "type"}]

    monkeypatch.setattr(easy_mode, "ValidationError", DummyValidationError)

    def raise_val_err(x):
        raise DummyValidationError()

    monkeypatch.setattr(easy_mode, "process_chapter", raise_val_err)
    valid_input = easy_mode.EasyModeInput(
        chapter_history=["a"],
        current_chapter="content",
        character_params={},
        content_length_limit=1000,
    )
    from src.backend.exceptions import ValidationException

    with pytest.raises(ValidationException):
        await easy_mode.generate_content(
            valid_input, request=dummy_request, session=dummy_session
        )


@pytest.mark.asyncio
async def test_generate_content_service_exception(
    monkeypatch, dummy_session, dummy_request
):
    def raise_runtime(x):
        raise RuntimeError("boom")

    monkeypatch.setattr(easy_mode, "process_chapter", raise_runtime)
    valid_input = easy_mode.EasyModeInput(
        chapter_history=["a"],
        current_chapter="content",
        character_params={},
        content_length_limit=1000,
    )
    from src.backend.exceptions import ServiceException

    with pytest.raises(ServiceException):
        await easy_mode.generate_content(
            valid_input, request=dummy_request, session=dummy_session
        )


class DummyMarketingAgent:

    def __init__(self, repo):
        self.repo = repo

    async def create_export_package(self, book_id: int):
        return b"ZIPDATA", f"book_{book_id}.zip"


def test_export_easy_mode_package(monkeypatch, dummy_session):
    monkeypatch.setattr(easy_mode, "MarketingAgent", DummyMarketingAgent)
    called = []

    class DummyMetrics:

        @staticmethod
        def increment(name):
            called.append(name)

    monkeypatch.setattr(easy_mode, "metrics", DummyMetrics)
    response = asyncio.run(
        easy_mode.export_easy_mode_package(book_id=1, session=dummy_session)
    )
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/zip"
    assert "attachment;" in response.headers["Content-Disposition"]
    assert "book_1.zip" in response.headers["Content-Disposition"]
    assert "exports_attempted" in called
    assert "exports_succeeded" in called


def test_get_task_status_pending(monkeypatch):
    class DummyHuey:

        @staticmethod
        def result(task_id):
            return None

    monkeypatch.setattr(huey_mod, "huey", DummyHuey)
    result = asyncio.run(easy_mode.get_task_status("abc123"))
    assert result["status"] == "pending"
    assert result["task_id"] == "abc123"


def test_get_task_status_completed(monkeypatch):
    class DummyHuey:

        @staticmethod
        def result(task_id):
            return {"output": "done"}

    monkeypatch.setattr(huey_mod, "huey", DummyHuey)
    result = asyncio.run(easy_mode.get_task_status("xyz789"))
    assert result["status"] == "completed"
    assert result["result"] == {"output": "done"}
    assert result["task_id"] == "xyz789"


def test_get_task_status_failed(monkeypatch):
    class DummyHuey:

        @staticmethod
        def result(task_id):
            return {"error": "LLM generation timeout", "text": "", "time": 0}

    monkeypatch.setattr(huey_mod, "huey", DummyHuey)
    result = asyncio.run(easy_mode.get_task_status("err456"))
    assert result["status"] == "failed"
    assert result["error"] == "LLM generation timeout"
    assert result["task_id"] == "err456"
